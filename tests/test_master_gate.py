"""Final-master acceptance and diagnostics, with short offline synthetic fixtures (ADR 0244)."""

from __future__ import annotations

import json
import subprocess
import wave
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from srstudio import master_gate
from srstudio.master_gate import MasterError, Run
from srstudio.releases import Release
from srstudio.social import InstagramPost

PICTURE = "testsrc2=size=160x284:rate=10:duration={d}"
STEPPED = "sine=f=440:d={d},volume='if(lt(t,{h}),0.14,2.24)':eval=frame"  # two levels: a loudness range of ~9 LU


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def master(path: Path, video: str, audio: str | None, seconds: float = 8.0) -> Path:
    inputs = ["-f", "lavfi", "-i", video]
    if audio is not None:
        inputs += ["-f", "lavfi", "-i", audio]
    codecs = ["-c:v", "libx264", "-pix_fmt", "yuv420p", *(["-c:a", "aac"] if audio else [])]
    ffmpeg(*inputs, *codecs, "-t", str(seconds), str(path))
    return path


@pytest.fixture(scope="module")
def clips(tmp_path_factory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("masters")
    stepped = STEPPED.format(d=8, h=4)
    late = "aevalsrc=0:d=0.5:s=44100[a];" + STEPPED.format(d=7.5, h=3.5) + "[b];[a][b]concat=n=2:v=0:a=1"
    return {
        "clean": master(root / "clean.mp4", PICTURE.format(d=8), stepped),
        "frozen": master(root / "frozen.mp4", PICTURE.format(d=6) + ",tpad=stop_mode=clone:stop_duration=2", stepped),
        "late": master(root / "late.mp4", PICTURE.format(d=8), late),
        "flat": master(root / "flat.mp4", PICTURE.format(d=8), "sine=f=440:d=8"),
        "mute": master(root / "mute.mp4", PICTURE.format(d=8), None),
    }


# -- each measure on its fixture ----------------------------------------------------------------------------------
def test_a_clean_picture_and_loudness_still_require_speech_evidence(clips):
    m = master_gate.measure(clips["clean"])
    assert m.frozen == () and m.still == () and m.first_sound == 0.0 and m.lra > master_gate.MIN_LRA
    assert [f.check for f in master_gate.findings(m)[0]] == ["speech"]


def test_a_two_second_frozen_stretch_fails(clips):
    m = master_gate.measure(clips["frozen"])
    assert m.frozen == (Run(5.9, 8.0),) and m.frozen[0].seconds == 2.1
    f = next(f for f in master_gate.findings(m)[0] if f.check == "frozen")
    assert f.measured == pytest.approx(2.1) and "1.5" in f.note


def test_half_a_second_of_leading_silence_fails(clips):
    m = master_gate.measure(clips["late"])
    assert m.first_sound == pytest.approx(0.5, abs=0.03)
    assert any(f.check == "speech" for f in master_gate.findings(m)[0])


def test_a_flat_tone_has_too_narrow_a_loudness_range(clips):
    m = master_gate.measure(clips["flat"])
    assert m.lra < 1.0
    f = next(f for f in master_gate.findings(m)[0] if f.check == "lra")
    assert "4.5" in f.note


def test_a_master_with_no_sound_cannot_be_measured(clips):
    with pytest.raises(MasterError, match="mute.mp4: silencedetect"):
        master_gate.measure(clips["mute"])


def test_a_file_that_is_no_video_cannot_be_measured(tmp_path):
    (tmp_path / "x.mp4").write_bytes(b"not a video")
    with pytest.raises(MasterError, match="x.mp4: ffprobe: .*x.mp4: Invalid data") as e:
        master_gate.measure(tmp_path / "x.mp4")
    assert "\n" not in str(e.value)  # one line in the report


# -- runs, the bed, the information lines -------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("shares", "expected"),
    [
        ([0.1] * 5, []),
        ([0.1, *[0.0] * 15, 0.1], []),  # 1.5 s exactly is not over
        ([0.1, *[0.0] * 16, 0.1], [Run(0.1, 1.7)]),
        ([*[0.0001] * 20], [Run(0.0, 2.0)]),  # a run to the last frame
        ([*[0.0] * 16, 0.001, *[0.0] * 16], [Run(0.0, 1.6), Run(1.7, 3.3)]),
    ],
)
def test_frozen_runs_are_consecutive_frames_under_the_share(shares, expected):
    assert master_gate.runs(shares, master_gate.FROZEN_SHARE, master_gate.FROZEN_RUN) == expected


def stem(
    path: Path, gap: float, depth_db: float = 20.0, seconds: float = 4.0, rate: int = 8000, fade: float = 0.0
) -> Path:
    """A 220 Hz bed with a ``gap`` at 1.5 s ``depth_db`` down, faded out linearly over its last ``fade`` s, as
    :func:`srstudio.takes.record` cuts a bed."""
    t = np.arange(round(seconds * rate)) / rate
    x = 0.3 * np.sin(2 * np.pi * 220 * t)
    a = round(1.5 * rate)
    x[a : a + round(gap * rate)] *= 10 ** (-depth_db / 20)
    if fade:
        x *= np.clip((seconds - t) / fade, 0.0, 1.0)
    pcm = np.repeat(np.round(x * 32767).astype("<i2")[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return path


@pytest.mark.parametrize(
    ("gap", "depth", "constant"), [(0.0, 20.0, True), (0.6, 20.0, False), (0.4, 20.0, True), (0.6, 6.0, True)]
)
def test_a_bed_is_constant_without_a_half_second_ten_db_down(tmp_path, gap, depth, constant):
    assert master_gate.constant_bed(stem(tmp_path / "m.wav", gap, depth)) is constant


def test_the_beds_fade_out_is_its_ending_not_a_gap(tmp_path):
    faded = stem(tmp_path / "m.wav", 0.0, fade=2.0)  # linear: its last 0.63 s are 10 dB down or more
    assert master_gate.constant_bed(faded) is False
    assert master_gate.constant_bed(faded, fade=2.0) is True
    assert master_gate.constant_bed(stem(tmp_path / "g.wav", 0.6, fade=2.0), fade=2.0) is False
    assert master_gate.constant_bed(stem(tmp_path / "s.wav", 0.0, fade=1.0)) is True  # the default fade: 0.32 s down


def test_a_bed_that_cannot_be_read_is_an_error(tmp_path):
    (tmp_path / "m.wav").write_bytes(b"RIFF")
    with pytest.raises(MasterError, match="m.wav"):
        master_gate.constant_bed(tmp_path / "m.wav")


def test_still_runs_block_and_sound_onset_stays_diagnostic(accepted_measure):
    m = replace(accepted_measure, still=(Run(1, 2.6),), first_sound=0.0, first_word=0.6)
    found, info = master_gate.findings(m)
    assert {f.check for f in found} == {"frozen", "speech"}
    assert 'first sound at 0.0; first speech at 0.6' in info


def test_silent_master_refuses_speech(accepted_measure):
    m = replace(accepted_measure, first_sound=None, first_word=None, speech_evidence=())
    assert [f.check for f in master_gate.findings(m)[0]] == ['speech']


GATED = {
    "items": [
        {"id": "01", "start": 0.4, "duration": 1, "prosody": {"words": [{"text": "hello", "start": 0.1, "end": 0.4}]}}
    ],
    "prosody": {"waive": []},
}


def test_every_master_is_binding_without_legacy_opt_in(clips):
    r = master_gate.judge("Old", clips["frozen"], None)
    assert r.binding and r.refused
    assert {f.check for f in r.failing} >= {'frozen', 'speech'}
    assert master_gate.refusals({"old": r})
    assert 'REFUSED' in '\n'.join(r.lines())


def test_script_waivers_cannot_approve_final_master(clips):
    waived = GATED | {"prosody": {"waive": [{"check": "frozen", "reason": "a held beat"}]}}
    r = master_gate.judge("New", clips["frozen"], waived)
    assert r.refused and any(f.check == 'frozen' for f in r.failing)


def test_unmeasurable_master_refuses_with_or_without_timeline(clips):
    for timeline in (None, GATED):
        r = master_gate.judge('New', clips['mute'], timeline)
        assert r.refused
        assert 'silencedetect' in '\n'.join(r.lines())


def test_read_finds_the_master_the_timeline_and_the_bed(clips, tmp_path):
    renders, episodes = tmp_path / "renders", tmp_path / "episodes"
    renders.mkdir()
    (renders / "New_Reel.mp4").write_bytes(clips["clean"].read_bytes())
    (episodes / "new-reel" / "audio").mkdir(parents=True)
    stem(episodes / "new-reel" / "audio" / "music.wav", 0.0, fade=2.0)
    timeline = GATED | {"music": {"file": "audio/music.wav", "fade": 2.0}}
    (episodes / "new-reel" / "timeline.json").write_text(json.dumps(timeline))
    release = Release("new-reel", InstagramPost(title="t", description="d"), video="New_Reel")
    readings = master_gate.read({"new-reel": release}, episodes, renders, {"new-reel": "New_Reel"})
    r = readings['new-reel']
    assert r.refused and r.acceptance.measured.constant_bed is True
    assert r.acceptance.measured.first_word == pytest.approx(0.5, abs=0.02)
    report = master_gate.lines(readings)
    assert 'sha256=' in '\n'.join(report)
    assert 'constant bed: no gap of 0.5 s 10 dB down in the music' in '\n'.join(report)
    assert r.final_frames.refused
    assert any('REFUSED sha256=' in line for line in report)


def test_a_missing_tool_or_an_unusual_bed_is_an_error_not_a_pass(clips, tmp_path):
    with pytest.raises(MasterError, match="clean.mp4: ffprobe: .*No such file"):
        master_gate.measure(clips["clean"], ffprobe=str(tmp_path / "no-ffprobe"))
    with wave.open(str(tmp_path / "b.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(8000)
        w.writeframes(bytes(800))
    with pytest.raises(MasterError, match="b.wav: expected 16-bit audio"):
        master_gate.constant_bed(tmp_path / "b.wav")


def test_unreadable_timeline_refuses_speech(clips, tmp_path):
    (tmp_path / "renders").mkdir()
    (tmp_path / "renders" / "V.mp4").write_bytes(clips["clean"].read_bytes())
    (tmp_path / "eps" / "s").mkdir(parents=True)
    (tmp_path / "eps" / "s" / "timeline.json").write_text("{not json")
    release = Release("s", InstagramPost(title="t", description="d"), video="V")
    (r,) = master_gate.read({"s": release}, tmp_path / "eps", tmp_path / "renders", {"s": "V"}).values()
    assert r.binding and r.refused
    assert any(f.check == "speech" for f in r.failing)
    assert r.final_frames.refused  # frame review also refuses without usable timeline evidence


def test_the_master_checks_are_waived_on_the_script_with_a_reason_and_no_bounds():
    from srstudio.direction import REEL_CHECKS, DirectionError, Waiver

    assert set(master_gate.CHECKS) <= set(REEL_CHECKS)
    reason = "a deadpan reel stays level"
    assert Waiver("lra", reason).record() == {"check": "lra", "reason": reason}
    with pytest.raises(DirectionError, match="no bounds"):
        Waiver("frozen", "the held frame is the joke", (0.0, 3.0))
    with pytest.raises(DirectionError, match="at least 3 words"):
        Waiver("opening", "because")


# ADR 0244: common final-master acceptance, independent of legacy script waivers.
@pytest.fixture
def accepted_measure(monkeypatch):
    from srstudio import craft_bar

    monkeypatch.setattr(craft_bar, 'measure_voice', lambda *a, **kw: craft_bar.Result(()))
    return master_gate.Measured(
        (),
        (),
        0.0,
        5.0,
        first_word=0.1,
        lufs=-15.0,
        peak_dbtp=-1.1,
        crop=(160, 198, 0, 0),
        detector='crop=160:198:0:0,freezedetect=n=0.003:d=1.5',
        loudness_raw='Summary: measured',
        freeze_raw='decoded to EOF',
        speech_evidence=('cached words audible',),
    )


def test_common_acceptance_reports_hash_values_limits_and_evidence(tmp_path, monkeypatch, accepted_measure):
    import hashlib
    from dataclasses import asdict

    video = tmp_path / 'master.mp4'
    video.write_bytes(b'master identity')
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: accepted_measure)
    result = master_gate.accept_master(video, tmp_path)
    assert result.ok
    assert result.master_sha256 == hashlib.sha256(video.read_bytes()).hexdigest()
    by = {c.check: c for c in result.checks}
    assert set(by) == {'integrated_lufs', 'true_peak', 'lra', 'speech', 'frozen'}
    assert by['integrated_lufs'].value == -15.0
    assert by['integrated_lufs'].limit == '-16..-14 LUFS; approved lower bound -16.6'
    assert by['true_peak'].limit == '<= -1 dBTP'
    assert by['speech'].value == 0.1 and by['speech'].evidence
    assert by['frozen'].evidence
    assert all(c.verdict == 'PASS' and c.master_sha256 == result.master_sha256 for c in result.checks)
    assert asdict(result)['checks']
    assert result.master_sha256 in '\n'.join(result.lines())


@pytest.mark.parametrize(
    ('field', 'value', 'check'),
    [
        ('lufs', -16.1, 'integrated_lufs'),
        ('lufs', -16.7, 'integrated_lufs'),
        ('lufs', -13.9, 'integrated_lufs'),
        ('lufs', -12.5, 'integrated_lufs'),
        ('peak_dbtp', -0.9, 'true_peak'),
        ('lra', 4.4, 'lra'),
        ('first_word', 0.251, 'speech'),
        ('first_word', None, 'speech'),
        ('lufs', None, 'integrated_lufs'),
        ('lufs', float('nan'), 'integrated_lufs'),
        ('peak_dbtp', None, 'true_peak'),
        ('peak_dbtp', float('inf'), 'true_peak'),
        ('lra', float('nan'), 'lra'),
        ('first_word', float('nan'), 'speech'),
        ('frozen', (Run(0, 1.501),), 'frozen'),
        ('crop', None, 'frozen'),
        ('speech_evidence', (), 'speech'),
        ('loudness_raw', '', 'integrated_lufs'),
    ],
)
def test_common_acceptance_refuses(tmp_path, monkeypatch, accepted_measure, field, value, check):
    from dataclasses import replace

    video = tmp_path / 'm.mp4'
    video.write_bytes(b'master')
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: replace(accepted_measure, **{field: value}))
    result = master_gate.accept_master(video, tmp_path)
    assert not result.ok
    assert next(c for c in result.checks if c.check == check).verdict == 'FAIL'


def test_exception_is_typed_hash_and_check_specific(tmp_path, monkeypatch, accepted_measure):
    import hashlib
    from dataclasses import replace

    video = tmp_path / 'm.mp4'
    video.write_bytes(b'master')
    sha = hashlib.sha256(video.read_bytes()).hexdigest()
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: replace(accepted_measure, lufs=-16.6))
    approval = approval_fixture(sha, 'integrated_lufs')
    result = master_gate.accept_master(video, tmp_path, approvals=(approval,))
    assert result.ok and result.checks[0].verdict == 'APPROVED'
    assert result.checks[0].approval == approval
    for invalid in (
        replace(approval, master_sha256='0' * 64),
        replace(approval, check='speech'),
        replace(approval, scope='production'),
        replace(approval, line='other'),
    ):
        assert not master_gate.accept_master(video, tmp_path, approvals=(invalid,)).ok
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: replace(accepted_measure, lufs=-16.61))
    assert not master_gate.accept_master(video, tmp_path, approvals=(approval,)).ok


def test_unreadable_measurement_and_hash_change_refuse(tmp_path, monkeypatch, accepted_measure):
    video = tmp_path / 'm.mp4'
    video.write_bytes(b'master')

    def missing(*a, **kw):
        raise MasterError('missing detector output')

    monkeypatch.setattr(master_gate, 'measure', missing)
    result = master_gate.accept_master(video, tmp_path)
    assert not result.ok and all(c.verdict == 'FAIL' for c in result.checks)
    assert 'missing detector output' in '\n'.join(result.lines())

    def changed(*a, **kw):
        video.write_bytes(b'changed master')
        return accepted_measure

    monkeypatch.setattr(master_gate, 'measure', changed)
    assert not master_gate.accept_master(video, tmp_path).ok


def test_early_sting_is_not_early_speech(clips, tmp_path):
    # Audio starts at zero; only the placed word at 0.6 s is speech evidence.
    (tmp_path / 'timeline.json').write_text(
        json.dumps(
            {
                'items': [
                    {'id': 'sting', 'actor': 'sfx'},
                    {
                        'id': 'voice',
                        'start': 0.5,
                        'duration': 1,
                        'prosody': {'words': [{'text': 'hello', 'start': 0.1, 'end': 0.4}]},
                    },
                ]
            }
        )
    )
    result = master_gate.accept_master(clips['clean'], tmp_path)
    speech = next(c for c in result.checks if c.check == 'speech')
    assert speech.value == pytest.approx(0.6, abs=0.02)
    assert speech.verdict == 'FAIL'
    assert result.measured.first_sound == 0


@pytest.mark.parametrize(('duration', 'fails'), [(1.5, False), (1.7, True)])
def test_c4_eof_boundary_and_moving_overlay(tmp_path, duration, fails):
    # Moving bottom overlay cannot hide frozen content above it.
    path = master(
        tmp_path / 'overlay.mp4',
        f'testsrc2=size=160x284:rate=10:duration={duration},drawbox=x=0:y=0:w=iw:h=198:color=black:t=fill',
        'sine=d=2',
        seconds=duration,
    )
    m = master_gate.measure(path)
    assert m.crop == (160, 198, 0, 0)
    assert bool(m.frozen) is fails
    if fails:
        assert m.frozen[0].end == pytest.approx(duration)
        assert m.frozen[0].seconds > 1.5


def test_unknown_format_requires_validated_crop(tmp_path):
    path = master(tmp_path / 'wide.mp4', 'testsrc2=s=284x160:r=10:d=2', 'sine=d=2', seconds=2)
    with pytest.raises(MasterError, match='content crop'):
        master_gate.measure(path)
    with pytest.raises(MasterError, match='content crop'):
        master_gate.measure(path, crop=(500, 160, 0, 0))
    assert master_gate.measure(path, crop=(284, 160, 0, 0)).crop == (284, 160, 0, 0)


@pytest.mark.parametrize(('lufs', 'peak', 'lra', 'speech'), [(-16, -1, 4.5, 0.25), (-14, -1, 4.5, 0.0)])
def test_inclusive_limits(tmp_path, monkeypatch, accepted_measure, lufs, peak, lra, speech):
    video = tmp_path / 'm.mp4'
    video.write_bytes(b'master')
    monkeypatch.setattr(
        master_gate,
        'measure',
        lambda *a, **kw: replace(accepted_measure, lufs=lufs, peak_dbtp=peak, lra=lra, first_word=speech),
    )
    assert master_gate.accept_master(video, tmp_path).ok


@pytest.mark.parametrize('check', ['speech', 'frozen'])
def test_authorized_exception_does_not_hide_other_failures(tmp_path, monkeypatch, accepted_measure, check):
    import hashlib

    video = tmp_path / 'm.mp4'
    video.write_bytes(b'master')
    sha = hashlib.sha256(video.read_bytes()).hexdigest()
    m = replace(accepted_measure, first_word=0.6, frozen=(Run(0, 2),))
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: m)
    approval = approval_fixture(sha, check)
    result = master_gate.accept_master(video, tmp_path, approvals=(approval,))
    assert not result.ok
    assert next(c for c in result.checks if c.check == check).verdict == 'APPROVED'
    assert sum(c.verdict == 'FAIL' for c in result.checks) == 1


def test_partial_unreadable_measurement_preserves_other_checks(clips, tmp_path, monkeypatch):
    (tmp_path / 'timeline.json').write_text(
        json.dumps(
            {
                'items': [
                    {
                        'id': 'voice',
                        'start': 0,
                        'duration': 1,
                        'prosody': {'words': [{'text': 'hello', 'start': 0.1, 'end': 0.4}]},
                    }
                ]
            }
        )
    )

    def missing(*a, **kw):
        raise MasterError('cannot decode content')

    monkeypatch.setattr(master_gate, 'frozen_content', missing)
    result = master_gate.accept_master(clips['clean'], tmp_path)
    by = {c.check: c for c in result.checks}
    assert by['speech'].verdict == by['integrated_lufs'].verdict == 'PASS'
    assert by['frozen'].verdict == 'FAIL'
    assert by['frozen'].value is None
    assert 'cannot decode content' in '\n'.join(result.lines())


@pytest.mark.parametrize('raw', [b'Summary: no values', b'Summary:\nI: nan LUFS\nLRA: 5 LU\nPeak: -1 dBFS'])
def test_unreadable_ebur128_is_a_typed_error(monkeypatch, raw):
    from subprocess import CompletedProcess

    monkeypatch.setattr(master_gate, '_run', lambda *a: CompletedProcess([], 0, b'', raw))
    with pytest.raises(MasterError, match='lacks a number'):
        master_gate.audio_levels(Path('unused'))


def test_freeze_requires_successful_eof_evidence(monkeypatch):
    from subprocess import CompletedProcess

    monkeypatch.setattr(master_gate, '_size', lambda *a: (160, 284))
    monkeypatch.setattr(master_gate, '_run', lambda *a: CompletedProcess([], 0, b'', b''))
    with pytest.raises(MasterError, match='missing decoded EOF'):
        master_gate.frozen_content(Path('unused'))


def test_actual_master_missing_key_refuses_shared_delivery_result(clips, tmp_path):
    (tmp_path / 'timeline.json').write_text(
        json.dumps(
            {
                'items': [
                    {
                        'id': 'voice',
                        'start': 0,
                        'duration': 1,
                        'prosody': {'words': [{'text': 'hello', 'start': 0.1, 'end': 0.4}]},
                    }
                ]
            }
        )
    )
    acceptance = master_gate.accept_master(clips['clean'], tmp_path)
    assert not acceptance.ok
    assert acceptance.voices[0].stress_status == "FAIL"
    reading = master_gate.judge('clean', clips['clean'], {}, project=tmp_path)
    assert reading.acceptance.master_sha256 == acceptance.master_sha256
    assert [(c.check, c.value, c.verdict) for c in reading.acceptance.checks] == [
        (c.check, c.value, c.verdict) for c in acceptance.checks
    ]
    assert reading.refused
    assert master_gate.findings(acceptance.measured)[0] == []


def test_legacy_master_is_binding(clips):
    assert master_gate.judge("old", clips["late"], None).refused


def test_reason_only_cannot_change_acceptance(clips):
    t = {"prosody": {"waive": [{"check": "opening", "reason": "the held beat matters"}]}}
    assert master_gate.judge("new", clips["late"], t).refused


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_master_measure_is_refused(clips, monkeypatch, value):
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: master_gate.Measured((), (), 0.0, value))
    assert master_gate.judge("new", clips["clean"], GATED).refused


def test_release_api_reports_missing_c7_with_hash(clips, tmp_path):
    from srstudio.master_gate import evaluate_release

    result = evaluate_release(clips["clean"], tmp_path)
    assert result.refused and len(result.master_sha256) == 64
    assert {c.check for c in result.checks if c.verdict == "MISSING"} >= {"c7.pace", "c7.stress"}
    assert "legacy=True" in "\n".join(result.lines())


def c7_result(**changes):
    from srstudio.craft_bar import Measure, Result

    values = dict(integrated_lufs=-16.0, lra=9.0, first_word=0.1, constant_bed=False)
    values.update(changes)
    return Result(tuple(Measure(k, v, "explicit fixture bar", "PASS", "master fixture") for k, v in values.items()))


def test_complete_c7_passes_and_reports_every_value(clips, tmp_path, monkeypatch, accepted_measure):
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: accepted_measure)
    from srstudio import craft_bar

    monkeypatch.setattr(craft_bar, "measure", lambda *a: c7_result())
    r = master_gate.evaluate_release(clips["clean"], tmp_path)
    assert not r.refused
    assert {c.check for c in r.checks} >= {"c7.lra", "c7.first_word", "c7.constant_bed", "c7.integrated_lufs"}
    assert all(c.limit and c.measured is not None for c in r.checks)
    assert "legacy=True" in "\n".join(r.lines())
    assert r.master_sha256 in "\n".join(r.lines())


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), True])
def test_missing_and_nonfinite_c7_cannot_pass(clips, tmp_path, monkeypatch, value):
    from srstudio import craft_bar

    monkeypatch.setattr(craft_bar, "measure", lambda *a: c7_result(lra=value))
    r = master_gate.evaluate_release(clips["clean"], tmp_path)
    assert r.refused
    assert next(c for c in r.checks if c.check == "c7.lra").verdict == "MISSING"


def test_c7_failure_requires_exact_pedro_disposition_for_pilot(clips, tmp_path, monkeypatch, accepted_measure):
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: accepted_measure)
    from dataclasses import replace

    from srstudio import craft_bar
    from srstudio.authority import Disposition, Message
    from srstudio.digest import sha256

    bad = c7_result()
    bad = replace(bad, measures=tuple(replace(m, status="FAIL") if m.name == "lra" else m for m in bad.measures))
    monkeypatch.setattr(craft_bar, "measure", lambda *a: bad)
    assert master_gate.evaluate_release(clips["clean"], tmp_path, scope="new_pilot").refused
    d = Disposition(
        sha256(clips["clean"]),
        "c7.lra",
        None,
        "the held level matters",
        None,
        "new_pilot",
        "builder",
        Message("Pedro", "slack://pedro", "Approved this measured master."),
        "Approved this measured master.",
    )
    r = master_gate.evaluate_release(clips["clean"], tmp_path, scope="new_pilot", dispositions=(d,))
    assert not r.refused
    c = next(c for c in r.checks if c.check == "c7.lra")
    assert c.approver == "Pedro" and c.evidence == "slack://pedro" and c.disabled
    assert c.measured == 9.0 and c.limit == "explicit fixture bar"
    assert "Approved this measured master." in "\n".join(r.lines())
    assert d.reason in "\n".join(r.lines())
    stale = replace(d, master_sha256="a" * 64)
    assert master_gate.evaluate_release(clips["clean"], tmp_path, scope="new_pilot", dispositions=(stale,)).refused


def test_prosody_bound_change_is_visible_and_hash_bound():
    from srstudio import prosody
    from srstudio.authority import Disposition, Message
    from support.prosody import timeline

    t = timeline()
    t["duration"] = 9.0
    reason = "the final held silence matters"
    d = Disposition(
        "a" * 64,
        "end_breath",
        "04",
        reason,
        (0.3, 4.0),
        "production",
        "builder",
        Message("arc4d3", "slack://arc", "Approved this longer ending."),
        "Approved this longer ending.",
    )
    t["items"][3]["direction"]["waive"] = [
        {"check": "end_breath", "reason": reason, "bounds": [0.3, 4.0], "approval": d.record()}
    ]
    (f,) = prosody.gate(t, master_sha256="a" * 64, scope="production")
    assert f.measured == 3.3 and f.default_bounds == (0.3, 1.2) and f.changed_bound == (0.3, 4.0)
    assert f.waived and f.approver == "arc4d3" and f.evidence == "slack://arc"
    with pytest.raises(prosody.ProsodyError, match="stale"):
        prosody.gate(t, master_sha256="b" * 64, scope="production")


def test_outbox_cannot_stage_a_delivered_file_without_c7_project(clips, tmp_path, monkeypatch):
    from srstudio import outbox
    from srstudio.social import Item

    monkeypatch.setattr(outbox, "check_delivery", lambda *a, **kw: [])
    package = tmp_path / "reel.vpkg.zip"
    package.write_bytes(b"fixture package")
    items = {"already-delivered": Item(InstagramPost(title="t", description="d"), clips["clean"])}
    bundles, drift = outbox.ready(items, tmp_path, font=tmp_path / "font.ttf", packages={"already-delivered": package})
    assert not bundles and "missing recording project" in drift[0].reason


def test_outbox_reports_the_shared_gate_and_holds_a_c7_failure(clips, tmp_path, monkeypatch):
    from srstudio import outbox
    from srstudio.social import Item

    monkeypatch.setattr(outbox, "check_delivery", lambda *a, **kw: [])
    reading = master_gate.Reading(
        "reel", False, master_sha256="a" * 64, checks=(master_gate.CheckVerdict("c7.pace:01", 5.0, "<= 4.2", "FAIL"),)
    )
    calls = []

    def gate(master, project, **kwargs):
        calls.append((master, project, kwargs))
        return reading

    monkeypatch.setattr(master_gate, "evaluate_release", gate)
    package = tmp_path / "reel.vpkg.zip"
    package.write_bytes(b"fixture package")
    items = {"reel": Item(InstagramPost(title="t", description="d"), clips["clean"])}
    report = []
    bundles, drift = outbox.ready(
        items,
        tmp_path,
        font=tmp_path / "font.ttf",
        packages={"reel": package},
        projects={"reel": tmp_path},
        scopes={"reel": "new_pilot"},
        release_reports=report,
    )
    assert not bundles and drift and report == reading.lines()
    assert calls == [(clips["clean"], tmp_path, {"scope": "new_pilot", "dispositions": ()})]


def test_authority_is_not_evaluated_when_master_measurement_is_missing(clips, monkeypatch):
    events = []

    def missing(*a, **kw):
        events.append("measure")
        raise MasterError("missing measured master")

    def authority(*a, **kw):
        events.append("authority")
        raise AssertionError("must measure first")

    monkeypatch.setattr(master_gate, "measure", missing)
    monkeypatch.setattr(master_gate, "_checks", authority)
    r = master_gate.judge("reel", clips["clean"], GATED)
    assert r.refused and events == ["measure"]
    assert {c.check for c in r.checks} == set(master_gate._LIMITS)
    assert all(c.verdict == "FAIL" for c in r.checks)


def test_master_changed_during_measurement_refuses(clips, monkeypatch):
    hashes = iter(["a" * 64, "b" * 64])
    monkeypatch.setattr(master_gate, "sha256", lambda path: next(hashes))
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: master_gate.Measured((), (), 0.0, 9.0))
    assert "changed during measurement" in master_gate.judge("reel", clips["clean"], GATED).error


def approval_fixture(sha, check, scope="reserved", author="Pedro"):
    from srstudio.authority import Disposition, Message

    return Disposition(
        sha,
        check,
        None,
        "this measured case approved",
        None,
        scope,
        "fixture-builder",
        Message(author, "fixture://retained-message", "Approved this measured fixture."),
        "Approved this measured fixture.",
    )


@pytest.mark.parametrize("scope,author", [("production", "arc4d3"), ("new_pilot", "Pedro")])
def test_acceptance_and_c7_share_one_disposition(tmp_path, monkeypatch, accepted_measure, scope, author):
    from srstudio import craft_bar
    from srstudio.digest import sha256

    video = tmp_path / "master.mp4"
    video.write_bytes(b"fixture master")
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: replace(accepted_measure, lufs=-16.5))
    bad = c7_result(integrated_lufs=-16.5)
    bad = replace(
        bad, measures=tuple(replace(m, status="FAIL") if m.name == "integrated_lufs" else m for m in bad.measures)
    )
    monkeypatch.setattr(craft_bar, "measure", lambda *a: bad)
    disposition = approval_fixture(sha256(video), "integrated_lufs", scope, author)
    result = master_gate.evaluate_release(video, tmp_path, scope=scope, dispositions=(disposition,))
    assert not result.refused and result.acceptance.ok
    assert result.acceptance.checks[0].approval is disposition
    by = {c.check: c for c in result.checks}
    assert by["integrated_lufs"].verdict == by["c7.integrated_lufs"].verdict == "WAIVED"
    assert by["c7.integrated_lufs"].approver == author
    assert by["c7.integrated_lufs"].measured == -16.5
    if scope == "production":
        assert master_gate.evaluate_release(video, tmp_path, scope="new_pilot", dispositions=(disposition,)).refused


@pytest.mark.parametrize(
    "field,value,check",
    [
        ("first_word", None, "speech"),
        ("crop", None, "frozen"),
        ("lufs", None, "integrated_lufs"),
        ("lufs", -16.7, "integrated_lufs"),
    ],
)
def test_disposition_cannot_approve_missing_or_ineligible_master(
    tmp_path, monkeypatch, accepted_measure, field, value, check
):
    from srstudio.digest import sha256

    video = tmp_path / "master.mp4"
    video.write_bytes(b"fixture master")
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: replace(accepted_measure, **{field: value}))
    d = approval_fixture(sha256(video), check)
    assert not master_gate.accept_master(video, tmp_path, approvals=(d,)).ok


def test_disposition_cannot_approve_missing_c7(tmp_path, monkeypatch, accepted_measure):
    from srstudio import craft_bar
    from srstudio.digest import sha256

    video = tmp_path / "master.mp4"
    video.write_bytes(b"fixture master")
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: accepted_measure)
    monkeypatch.setattr(craft_bar, "measure", lambda *a: c7_result(lra=None))
    d = approval_fixture(sha256(video), "c7.lra")
    result = master_gate.evaluate_release(video, tmp_path, dispositions=(d,))
    assert result.refused
    assert next(c for c in result.checks if c.check == "c7.lra").verdict == "MISSING"
    assert "missing measurements cannot be approved" in result.error


def test_c7_exception_cannot_bypass_accept_master_limit(tmp_path, monkeypatch, accepted_measure):
    from srstudio import craft_bar
    from srstudio.digest import sha256

    video = tmp_path / "master.mp4"
    video.write_bytes(b"fixture master")
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: replace(accepted_measure, lra=3.0))
    monkeypatch.setattr(craft_bar, "measure", lambda *a: c7_result(lra=3.0))
    d = approval_fixture(sha256(video), "c7.lra")
    result = master_gate.evaluate_release(video, tmp_path, dispositions=(d,))
    assert result.refused and not result.acceptance.ok
    assert next(c for c in result.checks if c.check == "lra").verdict == "FAIL"


@pytest.mark.parametrize("invalid", ["stale", "duplicate", "scope", "line", "unknown"])
def test_unused_master_dispositions_still_validate(tmp_path, monkeypatch, accepted_measure, invalid):
    from srstudio.digest import sha256

    video = tmp_path / "master.mp4"
    video.write_bytes(b"fixture master")
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: accepted_measure)
    d = approval_fixture(sha256(video), "speech")
    changes = {
        "stale": {"master_sha256": "a" * 64},
        "scope": {"scope": "production"},
        "line": {"line": "01"},
        "unknown": {"check": "unknown"},
    }
    approvals = (d, d) if invalid == "duplicate" else (replace(d, **changes[invalid]),)
    result = master_gate.accept_master(video, tmp_path, approvals=approvals)
    assert not result.ok and "authority:" in result.error
    assert all(c.verdict == "PASS" for c in result.checks)


def release_approval(sha):
    from srstudio.authority import Message

    return master_gate.ReleaseApproval(
        master_sha256=sha,
        approver="arc4d3",
        approval_message=Message("arc4d3", "slack://1793906449.811309", "Reviewed legacy master stays ready."),
        scope="legacy_reviewed",
        reason="Legacy master already reviewed by arc4d3",
    )


@pytest.mark.parametrize("missing", [False, True])
def test_whole_master_approval_retains_every_check(tmp_path, monkeypatch, accepted_measure, missing):
    from srstudio import craft_bar
    from srstudio.digest import sha256

    master = tmp_path / "legacy.mp4"
    master.write_bytes(b"reviewed master")
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: replace(accepted_measure, lra=1.0))
    monkeypatch.setattr(craft_bar, "measure", lambda *a: c7_result(lra=None if missing else 1.0))
    project = None if missing else tmp_path
    before = master_gate.evaluate_release(master, project)
    approval = release_approval(sha256(master))
    after = master_gate.evaluate_release(master, project, release_approval=approval)
    assert before.refused and not after.refused
    assert after.checks == before.checks
    assert after.acceptance == before.acceptance
    assert after.findings == before.findings and after.error == before.error
    assert after.release_approval is approval
    report = "\n".join(after.lines())
    assert "RELEASED" in report and "arc4d3" in report
    assert approval.master_sha256 in report and approval.approval_message.reference in report
    assert approval.reason in report and approval.approval_message.text in report
    master.write_bytes(b"replacement")
    stale = master_gate.evaluate_release(master, project, release_approval=approval)
    assert stale.refused and "release approval" in stale.error


@pytest.mark.parametrize("frame_state", ["missing", "refused"])
def test_whole_master_approval_releases_despite_frame_review(tmp_path, monkeypatch, accepted_measure, frame_state):
    from srstudio import craft_bar
    from srstudio.digest import sha256
    from srstudio.final_frame_gate import CheckResult, FinalFrameResult

    master = tmp_path / "legacy.mp4"
    master.write_bytes(b"reviewed legacy master")
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: accepted_measure)
    monkeypatch.setattr(craft_bar, "measure", lambda *a: c7_result())
    approval = release_approval(sha256(master))
    before = master_gate.evaluate_release(master, tmp_path)
    after = master_gate.evaluate_release(master, tmp_path, release_approval=approval)
    frame_error = "missing final-frame-review.json" if frame_state == "missing" else ""
    final_frames = (
        None
        if frame_state == "missing"
        else FinalFrameResult(
            "legacy",
            sha256(master),
            64,
            64,
            (),
            (CheckResult("legacy", "anatomy", "FAIL", 1, 0, sha256(master), "reviewed anatomy defect", None),),
        )
    )
    before = replace(before, frame_error=frame_error, final_frames=final_frames)
    after = replace(after, frame_error=frame_error, final_frames=final_frames)
    assert before.refused
    assert not after.refused
    assert after.frame_error == before.frame_error and after.final_frames == before.final_frames
    report = "\n".join(after.lines())
    assert f"whole-master release: RELEASED by {approval!r}" in report
    if frame_state == "missing":
        assert f"frames {after.video}: REFUSED {frame_error}" in report
    else:
        assert "frames legacy: REFUSED" in report
        assert "anatomy: FAIL" in report and "reviewed anatomy defect" in report


def test_stale_approval_refuses_even_clean_master(tmp_path, monkeypatch, accepted_measure):
    from srstudio import craft_bar

    master = tmp_path / "master.mp4"
    master.write_bytes(b"clean master")
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: accepted_measure)
    monkeypatch.setattr(craft_bar, "measure", lambda *a: c7_result())
    assert not master_gate.evaluate_release(master, tmp_path).refused
    assert master_gate.evaluate_release(master, tmp_path, release_approval=release_approval("a" * 64)).refused


@pytest.mark.parametrize(
    "changes",
    [
        {"master_sha256": "a" * 63},
        {"master_sha256": "g" * 64},
        {"approver": " "},
        {"approver": "stranger"},
        {"approval_message": None},
        {"scope": "production"},
        {"reason": " "},
    ],
)
def test_release_approval_rejects_malformed_fields(changes):
    from srstudio.authority import AuthorityError

    with pytest.raises(AuthorityError):
        replace(release_approval("a" * 64), **changes)


def test_release_approval_parse_is_strict():
    from srstudio.authority import AuthorityError

    approval = release_approval("a" * 64)
    record = approval.record()
    assert master_gate.ReleaseApproval.parse(record) == approval
    for changed in (record | {"extra": True}, {k: v for k, v in record.items() if k != "scope"}):
        with pytest.raises(AuthorityError):
            master_gate.ReleaseApproval.parse(changed)
    for key in ("author", "reference", "text"):
        with pytest.raises(AuthorityError):
            master_gate.ReleaseApproval.parse(record | {"approval_message": record["approval_message"] | {key: " "}})
    with pytest.raises(AuthorityError):
        master_gate.ReleaseApproval.parse(record | {"approval_message": record["approval_message"] | {"extra": 1}})


def test_untyped_release_approval_refuses(tmp_path, monkeypatch, accepted_measure):
    from srstudio import craft_bar

    master = tmp_path / "master.mp4"
    master.write_bytes(b"clean master")
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: accepted_measure)
    monkeypatch.setattr(craft_bar, "measure", lambda *a: c7_result())
    result = master_gate.evaluate_release(master, tmp_path, release_approval={"approved": True})
    assert result.refused and "release approval" in result.error


def test_release_approval_never_inferred_from_project(tmp_path, monkeypatch, accepted_measure):
    from srstudio import craft_bar
    from srstudio.digest import sha256

    master = tmp_path / "legacy.mp4"
    master.write_bytes(b"delivered master")
    approval = release_approval(sha256(master))
    (tmp_path / "timeline.json").write_text(
        json.dumps({"release_approval": approval.record(), "waivers": [approval.record()], "delivered": True})
    )
    (tmp_path / "delivery.json").write_text(json.dumps({"drive_id": "present", "approval": approval.record()}))
    monkeypatch.setattr(master_gate, "measure", lambda *a, **kw: replace(accepted_measure, lra=None))
    monkeypatch.setattr(craft_bar, "measure", lambda *a: c7_result(lra=None))
    result = master_gate.evaluate_release(master, tmp_path)
    assert result.refused and result.release_approval is None


@pytest.mark.parametrize("phase", ["master", "c7"])
def test_release_approval_refuses_replacement_during_evaluation(tmp_path, monkeypatch, accepted_measure, phase):
    from srstudio import craft_bar
    from srstudio.digest import sha256

    master = tmp_path / "legacy.mp4"
    master.write_bytes(b"reviewed master")
    approval = release_approval(sha256(master))

    def measured(*args, **kwargs):
        if phase == "master":
            master.write_bytes(b"replaced master")
        return accepted_measure

    def c7(*args):
        if phase == "c7":
            master.write_bytes(b"replaced master")
        return c7_result()

    monkeypatch.setattr(master_gate, "measure", measured)
    monkeypatch.setattr(craft_bar, "measure", c7)
    result = master_gate.evaluate_release(master, tmp_path, release_approval=approval)
    assert result.refused and "release approval" in result.error


def test_release_approval_retains_measurement_errors(tmp_path, monkeypatch):
    from srstudio import craft_bar
    from srstudio.digest import sha256

    master = tmp_path / "legacy.mp4"
    master.write_bytes(b"reviewed master")

    def unavailable(*args, **kwargs):
        raise master_gate.MasterError("fixture measurement unavailable")

    def c7_unavailable(*args):
        raise craft_bar.CraftError("fixture C7 unavailable")

    monkeypatch.setattr(master_gate, "measure", unavailable)
    monkeypatch.setattr(craft_bar, "measure", c7_unavailable)
    before = master_gate.evaluate_release(master, tmp_path)
    after = master_gate.evaluate_release(master, tmp_path, release_approval=release_approval(sha256(master)))
    assert before.refused and not after.refused
    assert before.error == after.error and before.checks == after.checks
    assert "fixture measurement unavailable" in "\n".join(after.lines())
    assert "fixture C7 unavailable" in "\n".join(after.lines())


def test_release_approval_source_author_must_match():
    from srstudio.authority import AuthorityError, Message

    with pytest.raises(AuthorityError):
        replace(release_approval("a" * 64), approval_message=Message("Pedro", "source://1", "approved"))

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
    assert 'sha256=' in '\n'.join(master_gate.lines(readings))


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
def accepted_measure():
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
    approval = master_gate.MasterApproval(sha, 'integrated_lufs', 'arc4d3', 'case reason', 'case stress evidence')
    result = master_gate.accept_master(video, tmp_path, approvals=(approval,))
    assert result.ok and result.checks[0].verdict == 'APPROVED'
    assert result.checks[0].approval == approval
    for invalid in (
        replace(approval, master_sha256='0' * 64),
        replace(approval, check='speech'),
        replace(approval, authorized_by='unknown'),
        replace(approval, evidence=''),
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
    m = replace(accepted_measure, first_word=None, speech_evidence=(), frozen=(Run(0, 2),))
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: m)
    approval = master_gate.MasterApproval(sha, check, 'arc4d3', 'case reason', 'case evidence')
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


def test_actual_passing_master_and_shared_delivery_result(clips, tmp_path):
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
    assert acceptance.ok
    reading = master_gate.judge('clean', clips['clean'], {}, project=tmp_path)
    assert reading.acceptance.master_sha256 == acceptance.master_sha256
    assert [(c.check, c.value, c.verdict) for c in reading.acceptance.checks] == [
        (c.check, c.value, c.verdict) for c in acceptance.checks
    ]
    assert not reading.refused
    assert master_gate.findings(acceptance.measured)[0] == []

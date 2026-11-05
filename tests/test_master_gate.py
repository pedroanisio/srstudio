"""The master gate at first delivery (ADR 0237): a frozen run, an opening silence and a narrow loudness range, each
measured on the finished master, each failing on a fixture that breaks it and passing on a clean one; listed for every
reel, refusing only a reel recorded to the gate, waived only with a reason.

Fixtures are made here with ffmpeg's lavfi sources: no network, no wall-clock."""

from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

from srstudio import master_gate
from srstudio.master_gate import MasterError, Measured, Run
from srstudio.releases import Release
from srstudio.social import InstagramPost

PICTURE = "testsrc2=size=160x284:rate=10:duration={d}"
STEPPED = "sine=f=440:d={d},volume='if(lt(t,{h}),0.05,0.8)':eval=frame"  # two levels: a loudness range of ~9 LU


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
def test_a_clean_master_has_no_finding(clips):
    m = master_gate.measure(clips["clean"])
    assert m.frozen == () and m.still == () and m.first_sound == 0.0 and m.lra > master_gate.MIN_LRA
    assert master_gate.findings(m) == ([], [])


def test_a_two_second_frozen_stretch_fails(clips):
    m = master_gate.measure(clips["frozen"])
    assert m.frozen == (Run(5.9, 7.9),) and m.frozen[0].seconds == 2.0
    (f,), _ = master_gate.findings(m)
    assert (f.check, f.measured, f.bounds) == ("frozen", 2.0, (0.0, 1.5))


def test_half_a_second_of_leading_silence_fails(clips):
    m = master_gate.measure(clips["late"])
    assert m.first_sound == pytest.approx(0.5, abs=0.03)
    (f,), _ = master_gate.findings(m)
    assert f.check == "opening" and f.measured == m.first_sound


def test_a_flat_tone_has_too_narrow_a_loudness_range(clips):
    m = master_gate.measure(clips["flat"])
    assert m.lra < 1.0
    (f,), _ = master_gate.findings(m)
    assert f.check == "lra" and f.bounds[0] == 4.5


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


def test_still_runs_a_constant_bed_and_a_first_word_in_silence_are_information():
    m = Measured((), (Run(1.0, 3.5),), 0.6, 9.0, constant_bed=True, first_word=0.3)
    found, info = master_gate.findings(m)
    assert [f.check for f in found] == ["opening"]
    assert info == [
        "still 2.5 s from 1 s (under 0.5% of pixels)",
        "constant bed: no gap of 0.5 s 10 dB down in the music",
        "first word at 0.3 s in the takes, first sound at 0.6 s on the master",
    ]
    assert master_gate.findings(Measured((), (), 0.2, 9.0, first_word=0.21)) == ([], [])


def test_a_silent_master_fails_its_opening():
    (f,), _ = master_gate.findings(Measured((), (), None, 9.0))
    assert f.check == "opening" and f.measured is None


# -- the policy: advisory before the gate, refusing after, waived with a reason -------------------------------------
GATED = {"items": [{"id": "01", "start": 0.4, "prosody": {"first": 0.1}}], "prosody": {"waive": []}}


def test_a_reel_recorded_before_the_gate_is_listed_and_never_refused(clips):
    r = master_gate.judge("Old", clips["frozen"], None)
    assert not r.binding and not r.refused and r.failing
    assert r.lines()[0] == "master Old: findings (recorded before the gate: advisory)"
    assert master_gate.refusals({"old": r}) == []


def test_a_reel_recorded_to_the_gate_is_refused_on_an_unwaived_finding(clips):
    r = master_gate.judge("New", clips["late"], GATED)
    (d,) = master_gate.refusals({"new": r})
    assert d.name == "New" and d.reason.startswith("master: reel: opening 0.5")
    assert r.lines()[0] == "master New: REFUSED"
    assert "info: first word at 0.5 s in the takes" not in "\n".join(r.lines())


def test_a_waiver_on_the_script_passes_the_finding_with_its_reason(clips):
    waived = GATED | {"prosody": {"waive": [{"check": "opening", "reason": "the cold open is a held beat"}]}}
    r = master_gate.judge("New", clips["late"], waived)
    assert not r.refused and r.lines()[0] == "master New: passes on its waivers"
    assert "(waived: the cold open is a held beat)" in r.lines()[1]


def test_a_master_the_gate_cannot_measure_refuses_a_reel_recorded_to_it(clips):
    r = master_gate.judge("New", clips["mute"], GATED)
    assert r.refused and r.lines()[0].startswith("master New: REFUSED, mute.mp4: silencedetect")
    old = master_gate.judge("Old", clips["mute"], None)
    assert not old.refused and old.lines()[0].startswith("master Old: unmeasured, mute.mp4")


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
    assert master_gate.lines(readings) == [
        "master New_Reel: clean",
        "  info: constant bed: no gap of 0.5 s 10 dB down in the music",
    ]


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


def test_a_timeline_that_cannot_be_read_leaves_the_master_advisory_for_the_prosody_gate_to_refuse(clips, tmp_path):
    (tmp_path / "renders").mkdir()
    (tmp_path / "renders" / "V.mp4").write_bytes(clips["clean"].read_bytes())
    (tmp_path / "eps" / "s").mkdir(parents=True)
    (tmp_path / "eps" / "s" / "timeline.json").write_text("{not json")
    release = Release("s", InstagramPost(title="t", description="d"), video="V")
    (r,) = master_gate.read({"s": release}, tmp_path / "eps", tmp_path / "renders", {"s": "V"}).values()
    assert not r.binding and r.lines() == ["master V: clean (recorded before the gate: advisory)"]


def test_the_master_checks_are_waived_on_the_script_with_a_reason_and_no_bounds():
    from srstudio.direction import REEL_CHECKS, DirectionError, Waiver

    assert set(master_gate.CHECKS) <= set(REEL_CHECKS)
    reason = "a deadpan reel stays level"
    assert Waiver("lra", reason).record() == {"check": "lra", "reason": reason}
    with pytest.raises(DirectionError, match="no bounds"):
        Waiver("frozen", "the held frame is the joke", (0.0, 3.0))
    with pytest.raises(DirectionError, match="at least 3 words"):
        Waiver("opening", "because")


def _noise(path: Path, seconds: float, level: float, seed: int) -> None:
    """Mono 48 kHz noise at ``level`` of full scale: speech-shaped enough for ebur128."""
    rng = np.random.default_rng(seed)
    samples = np.clip(rng.normal(0.0, level, int(48000 * seconds)), -1.0, 1.0)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes((samples * 32767).astype("<i2").tobytes())


def _engine(root: Path, *, fails: bool = False, silent: bool = False) -> Path:
    """A stand-in for ``scene-render encode SCENE -o WAV``: it writes the WAV the scene file names (a test scene is
    one path), or exits 1, or writes nothing. The real engine reads the same on shaken-soda v4 as its master."""
    script = root / "engine"
    script.write_text(
        f"#!{sys.executable}\n"
        "import shutil, sys\n"
        "assert sys.argv[1] == 'encode' and sys.argv[3] == '-o', sys.argv\n"
        f"if {fails!r}: sys.exit('error: the scene does not validate')\n"
        f"if not {silent!r}: shutil.copyfile(open(sys.argv[2]).read().strip(), sys.argv[4])\n"
    )
    script.chmod(0o700)
    return script


def _scene(root: Path, levels: list[float]) -> Path:
    """A scene whose engine mix is one 4 s line per level, back to back."""
    root.mkdir(parents=True)
    rate = 48000
    mix = np.concatenate([np.random.default_rng(k).uniform(-level, level, 4 * rate) for k, level in enumerate(levels)])
    with wave.open(str(root / "mix-source.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    scene = root / "reel.scene.xml"
    scene.write_text(str(root / "mix-source.wav"))
    return scene


def test_the_scene_range_reads_the_engine_s_own_mix_before_any_render(tmp_path):
    engine = _engine(tmp_path)
    flat = master_gate.scene_range(_scene(tmp_path / "flat", [0.2] * 6), engine=engine)
    under = 0.2 * 10 ** (-6 / 20)  # two lines said 6 dB under the rest
    quiet = master_gate.scene_range(_scene(tmp_path / "quiet", [0.2, under, 0.2, 0.2, under, 0.2]), engine=engine)
    assert flat < 1.0 <= master_gate.MIN_LRA <= quiet


def test_a_scene_range_with_no_scene_a_failed_encode_or_no_audio_is_refused(tmp_path):
    with pytest.raises(MasterError, match="no scene"):
        master_gate.scene_range(tmp_path / "gone.scene.xml", engine=_engine(tmp_path))
    scene = _scene(tmp_path / "reel", [0.2, 0.2])
    (tmp_path / "bad").mkdir()
    with pytest.raises(MasterError, match="does not validate"):
        master_gate.scene_range(scene, engine=_engine(tmp_path / "bad", fails=True))
    (tmp_path / "mute").mkdir()
    with pytest.raises(MasterError, match="wrote no audio"):
        master_gate.scene_range(scene, engine=_engine(tmp_path / "mute", silent=True))

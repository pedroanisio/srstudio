"""A master's proof: its measures read from ffprobe and ebur128, and the sheet of frames somebody looks at."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from srstudio import cli, proof

SUMMARY = """
[Parsed_ebur128_0 @ 0x55] Summary:

  Integrated loudness:
    I:         -14.1 LUFS
    Threshold: -24.3 LUFS

  Loudness range:
    LRA:        12.4 LU
    Threshold: -34.1 LUFS
    LRA low:   -24.0 LUFS
    LRA high:  -11.6 LUFS

  True peak:
    Peak:       -1.6 dBFS
"""
PROBE = {
    "format": {"duration": "30.300000", "size": "12278712"},
    "streams": [
        {"codec_type": "video", "width": 1080, "height": 1920, "r_frame_rate": "30/1"},
        {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
    ],
}


def test_the_summary_gives_loudness_range_and_peak():
    assert proof.loudness(SUMMARY) == (-14.1, 12.4, -1.6)


@pytest.mark.parametrize(
    "text", ["", "Integrated loudness:\n I: nan LUFS", SUMMARY.replace("Peak:", "Pk:"), SUMMARY.replace("-14.1", "inf")]
)
def test_a_summary_that_lost_a_number_is_refused(text):
    with pytest.raises(proof.ProofError, match="ebur128"):
        proof.loudness(text)


def test_the_probe_gives_the_picture_and_the_length():
    assert proof.picture(PROBE) == (30.3, 12278712, 1080, 1920, 30.0)


@pytest.mark.parametrize(
    "probe",
    [
        {},
        {"format": PROBE["format"], "streams": []},
        {"format": PROBE["format"], "streams": PROBE["streams"][1:]},
        {"format": PROBE["format"], "streams": PROBE["streams"][:1]},
        {"format": {"duration": "x", "size": "1"}, "streams": PROBE["streams"]},
        {"format": {"duration": "0", "size": "1"}, "streams": PROBE["streams"]},
    ],
)
def test_a_probe_without_a_picture_or_a_sound_is_refused(probe):
    with pytest.raises(proof.ProofError, match="probe"):
        proof.picture(probe)


def test_the_moments_are_the_first_frame_two_seconds_the_asked_ones_and_the_last_in_order():
    assert proof.moments(30.0, 30.0, [14.0, 9.5]) == [0.0, 2.0, 9.5, 14.0, pytest.approx(29.9666, abs=1e-3)]


def test_a_moment_said_twice_is_one_frame():
    assert proof.moments(30.0, 30.0, [2.0, 2.0]) == [0.0, 2.0, pytest.approx(29.9666, abs=1e-3)]


def test_a_reel_under_two_seconds_keeps_the_frames_it_has():
    assert proof.moments(1.0, 30.0, ()) == [0.0, pytest.approx(0.9666, abs=1e-3)]


@pytest.mark.parametrize("at", [-1.0, 31.0, float("nan")])
def test_a_moment_outside_the_master_is_refused(at):
    with pytest.raises(proof.ProofError, match="outside"):
        proof.moments(30.0, 30.0, [at])


@pytest.fixture
def master(tmp_path: Path) -> Path:
    if shutil.which("ffmpeg") is None:
        pytest.fail("ffmpeg is a requirement of this project")
    out = tmp_path / "m.mp4"
    source = ["-f", "lavfi", "-i", "testsrc2=size=108x192:rate=30:duration=3", "-f", "lavfi", "-i"]
    tone = ["sine=frequency=440:duration=3", "-shortest", "-pix_fmt", "yuv420p", str(out)]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *source, *tone], check=True)
    return out


def test_a_real_master_is_measured(master):
    report = proof.measure(master)
    assert (report.width, report.height, report.fps) == (108, 192, 30.0)
    assert report.seconds == pytest.approx(3.0, abs=0.1)
    assert report.size == master.stat().st_size
    assert -60.0 < report.lufs < 0.0


def test_a_sheet_holds_one_cell_per_moment(master, tmp_path):
    sheet = tmp_path / "out" / "sheet.png"
    proof.sheet(master, [0.0, 1.0, 2.0], sheet, width=54)
    size = subprocess.run(
        ["ffprobe", "-v", "error", "-of", "json", "-show_entries", "stream=width,height", str(sheet)],
        check=True,
        capture_output=True,
    )
    assert json.loads(size.stdout)["streams"][0] == {"width": 162, "height": 96}


def test_a_moment_past_the_last_frame_writes_no_sheet_and_says_so(master, tmp_path):
    with pytest.raises(proof.ProofError, match="no frame"):
        proof.sheet(master, [0.0, 9.0], tmp_path / "s.png", width=54)


def test_a_video_that_is_not_there_is_a_proof_error(tmp_path):
    with pytest.raises(proof.ProofError, match="missing"):
        proof.measure(tmp_path / "gone.mp4")


def test_the_command_prints_the_measures_and_writes_the_sheet(master, tmp_path, capsys):
    sheet = tmp_path / "s.png"
    assert cli.main(["proof", str(master), "--at", "1.5", "--sheet", str(sheet), "--json"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["moments"][:3] == [0.0, 1.5, 2.0]
    assert sheet.is_file()


def test_the_command_reports_a_bad_moment(master, capsys):
    assert cli.main(["proof", str(master), "--at", "99"]) == 1
    assert "outside" in capsys.readouterr().err


def _frame(value: int, *, changed: int = 0, to: int = 0) -> bytes:
    return bytes([to] * changed + [value] * (proof.ARM_W * proof.ARM_H - changed))


def test_two_equal_frames_differ_by_nothing():
    assert proof.difference(_frame(90), _frame(90)) == proof.Motion(0.0, 0.0)


def test_a_difference_counts_only_the_pixels_a_viewer_would_see_change():
    pixels = proof.ARM_W * proof.ARM_H
    moved = proof.difference(_frame(90), _frame(90, changed=pixels // 10, to=200))
    assert moved.changed == pytest.approx(0.1, abs=0.001)
    assert moved.mean == pytest.approx(11.0, abs=0.1)
    grain = proof.difference(_frame(90), _frame(90 + proof.NOTICED))
    assert (grain.changed, grain.mean) == (0.0, proof.NOTICED)


@pytest.mark.parametrize("bad", [b"", b"\x00" * 7, _frame(1) + b"\x00"])
def test_a_frame_of_the_wrong_size_is_refused(bad):
    with pytest.raises(proof.ProofError, match="frame"):
        proof.difference(_frame(1), bad)


@pytest.mark.parametrize(
    "motion, arm",
    [
        (proof.Motion(0.0, 0.0), "a"),
        (proof.Motion(0.2, proof.STILL), "a"),
        (proof.Motion(0.3, proof.STILL + 0.0001), "b"),
        (proof.Motion(1.98, 0.016), "b"),
    ],
)
def test_the_arm_is_read_from_what_moved_before_the_hold_ends(motion, arm):
    assert proof.arm_of(motion) == arm


def _clip(path: Path, moves_at: float) -> Path:
    """Two seconds of a white square on grey, the square jumping across the frame at ``moves_at``."""
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=gray:s=1080x1920:r=24:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
            "-filter_complex",
            f"color=c=white:s=300x300:r=24:d=2[sq];[0:v][sq]overlay=x='if(gte(t,{moves_at}),600,100)':y=100",
            "-t", "2", "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
    )  # fmt: skip
    return path


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_a_held_master_reads_as_arm_a_and_a_moving_one_as_arm_b(tmp_path):
    held = proof.hook(_clip(tmp_path / "held.mp4", 1.0), 24.0)
    moving = proof.hook(_clip(tmp_path / "moving.mp4", 0.1), 24.0)
    assert (held["arm"], moving["arm"]) == ("a", "b")
    assert held["changed"] < moving["changed"]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_the_seam_compares_the_last_frame_with_the_first(tmp_path):
    same = proof.seam(_clip(tmp_path / "same.mp4", 5.0), 2.0, 24.0)
    jump = proof.seam(_clip(tmp_path / "jump.mp4", 1.0), 2.0, 24.0)
    assert same["changed"] < proof.STILL
    assert jump["changed"] > 0.02


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg")
def test_a_report_names_the_arm_and_refuses_a_master_of_the_other_one(tmp_path):
    clip = _clip(tmp_path / "held.mp4", 1.0)
    made = proof.report(clip, arm="a")
    assert made["arm"] == "a" and "seam_changed" in made
    with pytest.raises(proof.ProofError, match="arm a, not b"):
        proof.report(clip, arm="b")


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg")
def test_the_command_line_fails_on_the_wrong_arm(tmp_path, capsys):
    clip = _clip(tmp_path / "moving.mp4", 0.1)
    assert cli.main(["proof", str(clip), "--arm", "a"]) == 1
    assert "arm b, not a" in capsys.readouterr().err
    assert cli.main(["proof", str(clip), "--arm", "b"]) == 0
    assert "arm=b" in capsys.readouterr().out


def test_a_report_without_an_arm_stays_as_it_was(monkeypatch):
    monkeypatch.setattr(proof, "measure", lambda _v: proof.Measures(30.0, 1, 1080, 1920, 30.0, -14.0, 3.0, -1.5))
    assert "arm" not in proof.report(Path("x.mp4"))


def test_a_master_too_slow_to_have_a_frame_at_the_hold_is_refused():
    with pytest.raises(proof.ProofError, match="no frame"):
        proof.hook(Path("x.mp4"), 2.0)

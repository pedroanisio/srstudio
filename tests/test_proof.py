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

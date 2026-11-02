"""The Stick dance study (examples/dance_stick): the adapter end to end on a scene the engine can encode.

The study builds two eight-bar shots at 129 beats a minute over a synthesised track, finds nothing to report in the
SDK's own checks, holds the drawn groove to the reference's targets and stays a study: no post, no release."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "examples" / "dance_stick" / "dance_stick_study.py"
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> tuple[Path, dict]:
    if not FONT.exists():
        pytest.skip(f"the study's caption font stands in from {FONT}")
    root = tmp_path_factory.mktemp("dance-stick")
    (root / "assets").mkdir()
    shutil.copy(FONT, root / "assets" / "Inter-Bold.ttf")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    done = subprocess.run([sys.executable, str(SCRIPT), str(root)], env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return root, json.loads(done.stdout[done.stdout.index("{") :])


def test_the_study_builds_two_eight_bar_shots_over_its_own_track(built):
    root, _ = built
    scene = (root / "dance-stick-study.scene.xml").read_text()
    assert scene.index('id="shot-car"') < scene.index('id="shot-room"')
    seconds = 16 * 4 * 60 / 129
    duration = float(re.search(r'<project [^>]*duration="([0-9.]+)"', scene).group(1))
    assert duration == pytest.approx(seconds, abs=1 / 25)
    assert 'fps="25"' in scene and 'src="audio/groove.wav"' in scene and 'role="music"' in scene
    assert json.loads((root / "qa" / "sdk-validation.json").read_text()) == []  # the SDK checks find nothing


def test_the_study_s_drawn_groove_meets_the_reference_targets(built):
    _, record = built
    for who in ("dev", "noor"):
        for channel in ("bob", "sway"):
            reading = record["numbers"][who][channel]
            assert reading["misses"] == [] and reading["cycles_per_beat"] == pytest.approx(1.0, abs=0.02)
    assert record["numbers"]["solo_reach_px"] == 0
    assert record["numbers"]["pictures"] == {"car": 373, "room": 373}


def test_the_raised_hand_moves_no_more_than_the_head(built):
    _, record = built
    hand, head = record["numbers"]["noor_raised_hand"], record["numbers"]["noor"]["bob"]
    assert hand["cycles_per_beat"] == pytest.approx(1.0, abs=0.02)
    assert hand["peak_to_peak"] <= head["peak_to_peak"] + 0.01


def test_the_standing_figure_stands_on_the_floor_clear_of_the_desk(built):
    _, record = built
    room = record["numbers"]["room_clearance"]
    assert room["left_px"] > room["near_leg_right_px"] + 15  # every stroke, the head's edge too, right of the near leg
    assert room["right_px"] < room["frame_right_px"] - 15  # and inside the frame: both arms stay in the picture
    assert room["feet_y_px"][1] == pytest.approx(room["floor_px"], abs=0.5)  # planted feet on the floor line
    assert room["feet_y_px"][0] > room["desk_legs_floor_px"]  # even a lifted foot is in front of the desk's feet


def test_the_study_is_never_a_release():
    text = SCRIPT.read_text()
    assert "InstagramPost" not in text and "register" not in text and "post" not in text.split('"""', 2)[2]
    assert not list((ROOT / "episodes").rglob("dance_stick*"))


def test_master_needs_the_engine(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "SRSTUDIO_ENGINE"}
    env["PYTHONPATH"] = str(ROOT / "src")
    (tmp_path / "assets").mkdir()
    if FONT.exists():
        shutil.copy(FONT, tmp_path / "assets" / "Inter-Bold.ttf")
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "--master", str(tmp_path / "out")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert done.returncode != 0 and "SRSTUDIO_ENGINE" in done.stderr


def test_the_page_is_rewritten_from_the_numbers_with_the_three_plane_views(tmp_path):
    numbers = {"numbers": {}, "rendered": {}}
    reading = {"cycles_per_beat": 1.0, "onto_s": 0.19, "away_s": 0.26, "peak_to_peak": 0.38, "hit": "min"}
    reading["hit_offset_s"] = 0.001
    numbers["numbers"] = {
        "dev": {"bob": reading, "sway": reading},
        "noor": {"bob": reading, "sway": reading},
        "noor_raised_hand": reading,
        "solo": {"bob": {"channel": "head up", **reading}, "sway": {"channel": "hips right", "error": "flat"}},
        "solo_reach_px": 0.0,
        "room_clearance": {
            "left_px": 650.0,
            "right_px": 1060.0,
            "frame_right_px": 1080,
            "near_leg_right_px": 631,
            "feet_y_px": [1790.0, 1830.0],
            "desk_legs_floor_px": 1602,
            "floor_px": 1830.0,
        },
    }
    late = {**reading, "hit_offset_s": 0.0286}
    head = {"bob": reading, "sway": reading}
    numbers["rendered"] = {"frames": 93, "noor": head, "dev": head, "pooled": {"bob": reading, "sway": late}}
    (tmp_path / "numbers.json").write_text(json.dumps(numbers))
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path), "--page", str(tmp_path), "--views", "views.mp4"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    page = (tmp_path / "index.html").read_text()
    assert 'src="./dance-stick-study.mp4"' in page and 'src="./views.mp4"' in page
    assert "Rows are characters" in page and "not read (flat)" in page
    assert "Read pooled, the two heads' shared centre lands its sway extreme +29 ms" in page
    assert (
        "each head alone lands within 1 ms" in page
        and "between x 650 and 1060, right of the near desk leg's edge at 631" in page
    )

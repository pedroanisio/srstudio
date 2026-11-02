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
    }
    numbers["rendered"] = {"frames": 93, "bob": reading, "sway": reading}
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

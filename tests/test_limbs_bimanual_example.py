"""The two-arm showcase must exercise moving shared contact, not merely a static two-hand drawing."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

from srstudio.limbs.serialization import load_motion


def example():
    script = Path(__file__).resolve().parents[1] / "examples" / "limbs_bimanual.py"
    spec = importlib.util.spec_from_file_location("limbs_bimanual", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_two_hands_follow_distinct_anchors_of_one_tray_during_lift_and_seek():
    pair = example().tray_pair()
    expected = {i: pair.sample(i / 24) for i in range(97)}
    for i in reversed(range(97)):
        assert pair.sample(i / 24) == expected[i]
    for time in (1, 1.5, 2.5, 3):
        sample = pair.sample(time)
        for side in ("right", "left"):
            assert getattr(sample, side).hand.frame.origin.distance(pair.props[0].frame(side, time).origin) < 1e-6
    assert pair.props[0].track.sample(2.5).origin.distance(pair.props[0].track.sample(1).origin) > 0.2


def test_bimanual_scene_builds_with_reusable_motion_and_quantitative_qa(tmp_path):
    path = example().build(tmp_path / "two-arms", fps=2)
    report = json.loads(path.with_name("bimanual-qa.json").read_text())
    assert report["tray"]["right"]["max_contact_error"] < 1e-6
    assert report["tray"]["left"]["max_contact_error"] < 1e-6
    for name in ("tray", "crossed"):
        assert report[name]["collision_frames"] == 0
        assert all(report[name][side]["bounds"][3] < 860 for side in ("right", "left"))
    assert load_motion(path.with_name("crossed-right.motion.json")).actions[0].name == "crossed"
    engine = os.environ.get("SRSTUDIO_ENGINE")
    if engine:
        result = subprocess.run([engine, "validate", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


def test_tilted_camera_keeps_the_authored_mouth_visible_in_rendered_pixels(tmp_path):
    import shutil

    import pytest

    engine = os.environ.get("SRSTUDIO_ENGINE")
    if not engine or not shutil.which("ffmpeg"):
        pytest.skip("set SRSTUDIO_ENGINE and install ffmpeg for the showcase pixel check")
    module = example()
    path = module.build(tmp_path / "pixels", fps=2)
    png = path.with_name("mouth.png")
    result = subprocess.run(
        [engine, "render", str(path), "--time", "2", "--output", str(png)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(png), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
        check=True,
    ).stdout
    mouth = next(f for f in module.mannequin().faces if f.name == "mouth")
    from srstudio.limbs import Camera, Frame, Quaternion, Vec3

    centre = sum(mouth.vertices, Vec3()) / len(mouth.vertices)
    camera = Camera(
        projection="perspective",
        distance=6,
        focal=6,
        scale=175,
        origin=(400, 460),
        view=Frame(rotation=Quaternion.axis_angle(Vec3(1, 0, 0), 0.35)),
    )
    x, y = camera.project(centre).xy
    colors = [
        raw[(yy * 1600 + xx) * 3 : (yy * 1600 + xx) * 3 + 3]
        for yy in range(round(y) - 2, round(y) + 3)
        for xx in range(round(x) - 2, round(x) + 3)
    ]
    assert any(all(abs(a - b) < 12 for a, b in zip(color, (124, 68, 56), strict=True)) for color in colors)

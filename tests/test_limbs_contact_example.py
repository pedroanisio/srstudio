"""The prop interaction example carries motion sources and verifies real contact residuals."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

from srstudio.limbs.serialization import load_motion
from srstudio.sample import SYSTEM_FONTS


@pytest.fixture
def system_font():
    if not any(p.is_file() for p in SYSTEM_FONTS):
        pytest.skip("no DejaVu Sans Bold at any srstudio.sample.SYSTEM_FONTS path")


@pytest.mark.usefixtures("system_font")
def test_contact_example_builds_and_validates_moving_press_and_attached_cup(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples" / "limbs_contact.py"
    spec = importlib.util.spec_from_file_location("limbs_contact", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = module.build(tmp_path / "contact", fps=2)
    report = json.loads(path.with_name("contact-qa.json").read_text())
    assert report["press"]["max_contact_error"] < 1e-6
    assert report["cup"]["max_bone_error"] < 1e-6
    assert report["press"]["bounds"][3] < 745
    assert report["cup"]["bounds"][3] < 745
    cup = load_motion(path.with_name("cup.motion.json"))
    assert cup.prop_frame("cup", 3) == cup.prop_frame("cup", 2.1)
    press = load_motion(path.with_name("press.motion.json"))
    assert len(press.sample(1.5).contacts) == 1
    engine = os.environ.get("SRSTUDIO_ENGINE")
    if engine:
        result = subprocess.run([engine, "validate", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


def test_pickup_lifts_the_cup_before_releasing_it():
    script = Path(__file__).resolve().parents[1] / "examples" / "limbs_contact.py"
    spec = importlib.util.spec_from_file_location("limbs_contact", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    motion = module.cup_motion()
    assert motion.prop_frame("cup", 1.9).origin.distance(motion.prop_frame("cup", 1.2).origin) > 0.2
    assert motion.prop_frame("cup", 3) == motion.prop_frame("cup", 2.1)

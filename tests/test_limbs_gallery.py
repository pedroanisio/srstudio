"""The runnable style comparison uses original geometry and ships its motion source and quality evidence."""

import importlib.util
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio.limbs.serialization import load_motion
from srstudio.sample import SYSTEM_FONTS


@pytest.fixture
def system_font():
    if not any(p.is_file() for p in SYSTEM_FONTS):
        pytest.skip("no DejaVu Sans Bold at any srstudio.sample.SYSTEM_FONTS path")


@pytest.mark.usefixtures("system_font")
def test_example_builds_the_same_six_actions_in_three_styles(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples" / "limbs_gallery.py"
    spec = importlib.util.spec_from_file_location("limbs_gallery", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = module.build(tmp_path / "gallery", fps=2)
    xml = ET.parse(path).getroot()
    assert xml.find("project").get("duration") == "12"
    assert xml.find("output").get("codec") == "h264"
    report = json.loads(path.with_name("limbs-qa.json").read_text())
    assert set(report["styles"]) == {"stick", "toon", "gloss"}
    assert all(v["max_bone_error"] < 1e-6 for v in report["styles"].values())
    motion = load_motion(path.with_name("motion.json"))
    assert [a.name for a in motion.actions] == ["point", "present", "shrug", "facepalm", "grasp", "press"]
    engine = os.environ.get("SRSTUDIO_ENGINE")
    if engine:
        result = subprocess.run([engine, "validate", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


@pytest.mark.usefixtures("system_font")
def test_skin_gallery_runs_all_six_planar_actions_in_three_styles(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples" / "limbs_gallery.py"
    spec = importlib.util.spec_from_file_location("limbs_gallery", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = module.build(tmp_path / "skin", fps=2, deformation="skin")
    xml = ET.parse(path).getroot()
    assert len(xml.findall(".//modifier[@type='skin']")) >= 3
    report = json.loads(path.with_name("limbs-qa.json").read_text())
    assert set(report["backends"].values()) == {"native-skin"}
    assert report["deformation"] == "skin"
    engine = os.environ.get("SRSTUDIO_ENGINE")
    if engine:
        result = subprocess.run([engine, "validate", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


@pytest.mark.usefixtures("system_font")
def test_gallery_can_retarget_the_shared_actions_to_a_mechanical_gripper(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples" / "limbs_gallery.py"
    spec = importlib.util.spec_from_file_location("limbs_gallery", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = module.build(tmp_path / "gripper", fps=2, hand="gripper")
    motion = load_motion(path.with_name("motion.json"))
    assert motion.hand.name == "gripper"
    assert motion.hand.digits[0].bend_axis.z == -1
    assert motion.hand.digits[1].bend_axis.z == 1
    assert json.loads(path.with_name("limbs-qa.json").read_text())["hand"] == "gripper"

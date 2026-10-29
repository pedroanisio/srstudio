"""The runnable style comparison uses original geometry and ships its motion source and quality evidence."""

import importlib.util
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from srstudio.limbs.serialization import load_motion


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

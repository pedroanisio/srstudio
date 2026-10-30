"""The starter example builds a validated scene through its documented CLI."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def test_new_episode_example_builds_and_validates(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples" / "new_episode.py"
    result = subprocess.run([sys.executable, str(script), str(tmp_path)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    scene = ET.parse(tmp_path / "coffee-review.scene.xml").getroot()
    ids = {node.get("id") for node in scene.iter()}
    assert "location-cafe-tips" in ids
    assert any(node_id and node_id.startswith("tip-jar") for node_id in ids)
    assert json.loads((tmp_path / "sdk-validation.json").read_text()) == []

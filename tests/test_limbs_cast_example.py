"""A rendered cast example proves the shared gesture is attached to complete style characters."""

import importlib.util
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
def test_cast_example_builds_three_complete_characters_with_reusable_sources(tmp_path):
    script = Path(__file__).resolve().parents[1] / "examples" / "limbs_cast.py"
    spec = importlib.util.spec_from_file_location("limbs_cast", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = module.build(tmp_path / "cast", fps=2)
    for style in ("stick", "toon", "gloss"):
        motion = load_motion(path.with_name(f"{style}.motion.json"))
        assert motion.actions[0].name == "point"
        assert motion.hand.name == ("mitten" if style == "toon" else "human")
    engine = os.environ.get("SRSTUDIO_ENGINE")
    if engine:
        result = subprocess.run([engine, "validate", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

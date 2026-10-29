"""Custom showcase fonts must not silently inherit an unrelated system font's license sidecar."""

import importlib.util
from pathlib import Path

import pytest

from srstudio.limbs import LimbError


@pytest.mark.parametrize("name", ["limbs_gallery", "limbs_contact", "limbs_cast", "limbs_bimanual"])
def test_custom_font_requires_its_own_explicit_license_before_assets_are_copied(tmp_path, name):
    script = Path(__file__).resolve().parents[1] / "examples" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    font = tmp_path / "custom.ttf"
    font.write_bytes(b"an author-provided font")
    out = tmp_path / "out"
    with pytest.raises(LimbError, match="font.*license|license.*font"):
        module.build(out, fps=2, font=font)
    assert not (out / "assets" / "font.ttf").exists()

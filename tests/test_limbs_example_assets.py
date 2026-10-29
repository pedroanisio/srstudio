"""Showcase fonts resolve like the library's and never silently inherit an unrelated license sidecar."""

import importlib.util
from pathlib import Path

import pytest

from srstudio.limbs import LimbError
from srstudio.sample import SYSTEM_FONTS

EXAMPLES = ["limbs_gallery", "limbs_contact", "limbs_cast", "limbs_bimanual"]
# The note srstudio.sample and srstudio.interview ship beside the system DejaVu Sans Bold.
DEJAVU_NOTE = "DejaVu Fonts license; see https://dejavu-fonts.github.io/License.html\n"


def load(name):
    script = Path(__file__).resolve().parents[1] / "examples" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def system_font():
    font = next((p for p in SYSTEM_FONTS if p.is_file()), None)
    if font is None:
        pytest.skip("no DejaVu Sans Bold at any srstudio.sample.SYSTEM_FONTS path")
    return font


@pytest.mark.parametrize("name", EXAMPLES)
def test_custom_font_requires_its_own_explicit_license_before_assets_are_copied(tmp_path, name):
    font = tmp_path / "custom.ttf"
    font.write_bytes(b"an author-provided font")
    out = tmp_path / "out"
    with pytest.raises(LimbError, match="font.*license|license.*font"):
        load(name).build(out, fps=2, font=font)
    assert not (out / "assets" / "font.ttf").exists()


@pytest.mark.parametrize("name", EXAMPLES)
def test_system_font_ships_with_the_library_dejavu_license_note(tmp_path, name, system_font):
    load(name).build(tmp_path / "out", fps=2)
    assets = tmp_path / "out" / "assets"
    assert (assets / "font.ttf").read_bytes() == system_font.read_bytes()
    assert (assets / "FONT-LICENSE.txt").read_text() == DEJAVU_NOTE


@pytest.mark.parametrize("name", EXAMPLES)
def test_an_explicit_license_file_is_copied_verbatim(tmp_path, name, system_font):
    license_file = tmp_path / "LICENSE.txt"
    license_file.write_text("Bitstream Vera Fonts Copyright\n")
    load(name).build(tmp_path / "out", fps=2, font=system_font, license_file=license_file)
    assert (tmp_path / "out" / "assets" / "FONT-LICENSE.txt").read_text() == "Bitstream Vera Fonts Copyright\n"


@pytest.mark.parametrize("name", EXAMPLES)
def test_examples_refuse_cleanly_when_no_system_font_is_installed(tmp_path, monkeypatch, name):
    module = load(name)
    monkeypatch.setattr(module, "SYSTEM_FONTS", (tmp_path / "absent.ttf",))
    out = tmp_path / "out"
    with pytest.raises(LimbError, match="--font"):
        module.build(out, fps=2)
    assert not (out / "assets" / "font.ttf").exists()

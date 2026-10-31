"""The odd props: a pipe, a handwritten sheet, a mosquito, a towel, sheets, a padlock and tasting spoons."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry
from srstudio.styles import STYLES
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


@pytest.mark.parametrize("name", ["toon-pipe", "toon-paper-insert"])
def test_every_prop_is_registered_for_toon(name):
    entry = registry.get("prop", name)
    assert entry.style == "toon" and entry.module == "srstudio.toon_odds"
    assert "toon_odds" in STYLES["toon"].parts


@pytest.mark.parametrize("call", [])
def test_a_prop_refuses_bad_data(call):
    with pytest.raises(ToonDataError):
        call(canvas())

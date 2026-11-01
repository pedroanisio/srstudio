"""A necktie and a lanyard: each stands alone, swings only while it is held up, and refuses what cannot be drawn."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_tie
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


@pytest.mark.parametrize(("name", "builder"), [("toon-necktie", toon_tie.necktie), ("toon-lanyard", toon_tie.lanyard)])
def test_the_parts_are_registered_and_draw_from_their_defaults(name: str, builder) -> None:
    assert registry.get("prop", name).builder is builder
    cv = canvas()
    builder(cv, cv.comp)
    assert len(list(xml(cv).iter())) > 3


def test_a_tie_held_up_swings_and_a_worn_tie_does_not() -> None:
    cv = canvas()
    toon_tie.necktie(cv, cv.comp, swinging=(1.0, 4.0))
    held = cv.scene.to_bytes(layout="pretty").count(b"rotation")
    cv = canvas()
    toon_tie.necktie(cv, cv.comp)
    assert held > cv.scene.to_bytes(layout="pretty").count(b"rotation")


@pytest.mark.parametrize("bad", [0, -1.0, "big"])
def test_a_bad_scale_is_refused(bad: object) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="scale"):
        toon_tie.necktie(cv, cv.comp, scale=bad)  # type: ignore[arg-type]


def test_a_point_that_is_not_a_point_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="reference point"):
        toon_tie.lanyard(cv, cv.comp, at=(1.0,))  # type: ignore[arg-type]

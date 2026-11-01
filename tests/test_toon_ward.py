"""The hospital ward: a room with its bed in front of whoever lies in it, and a bandage that stays on the face."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon, toon_ward
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="fraunces", namer=flat_counter("w"))


def tags(cv: Canvas) -> list[ET.Element]:
    return list(ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter())


def boxes(cv: Canvas) -> list[tuple[float, float]]:
    return [(float(n.get("x", 0)), float(n.get("width", 0))) for n in tags(cv) if n.get("shape") == "rect"]


LOOK = SimpleNamespace(eyes=((200.0, 300.0), (360.0, 300.0)))


@pytest.mark.parametrize(
    ("kind", "name", "builder"),
    [
        ("location", "toon-ward", toon_ward.ward),
        ("prop", "toon-ward-bed", toon_ward.ward_bed),
        ("prop", "toon-bandage", toon_ward.bandage),
    ],
)
def test_the_parts_are_registered(kind, name, builder):
    assert registry.get(kind, name).builder is builder


def test_the_ward_fills_the_frame():
    cv = canvas()
    toon_ward.ward(cv, cv.comp)
    x, wide = boxes(cv)[0]
    assert x == 0.0 and wide == cv.width


def test_the_ward_has_no_words_on_it():
    cv = canvas()
    toon_ward.ward(cv, cv.comp)
    assert not [n for n in tags(cv) if n.tag.endswith("text")]


def test_the_bed_is_as_wide_as_the_frame_and_the_marks_can_step_in():
    cv = canvas()
    toon_ward.ward_bed(cv, cv.comp, 46.0)
    x, wide = boxes(cv)[0]
    assert x < 0.0 and x + wide > cv.width


def test_the_bandage_sits_above_the_eyes_of_the_look_it_is_given():
    cv = canvas()
    toon_ward.bandage(cv, cv.comp, 1.0, 5.0, LOOK)
    first = next(n for n in tags(cv) if n.get("shape") == "rect")
    assert float(first.get("y")) < toon.fy(300.0)
    middle = float(first.get("x")) + float(first.get("width")) / 2
    assert middle == pytest.approx(toon.fx(280.0))


@pytest.mark.parametrize(("start", "end"), [(5.0, 1.0), (1.0, 1.0), (-1.0, 1.0)])
def test_a_bandage_needs_a_span(start, end):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_ward.bandage(cv, cv.comp, start, end, LOOK)


def test_the_blanket_runs_past_the_foot_of_the_frame_with_its_outline():
    cv = canvas()
    toon_ward.ward_bed(cv, cv.comp)
    blanket = next(n for n in tags(cv) if n.get("fill") == toon_ward.BLANKET)
    assert float(blanket.get("y")) + float(blanket.get("height")) > cv.height + float(blanket.get("strokeWidth", 0))

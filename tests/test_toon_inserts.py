"""The small Toon parts: each is registered, each refuses what it cannot draw, and nothing shows before its time."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, specimens, toon_inserts
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def group(cv: Canvas, name: str):
    return next(n for n in tree(cv).iter("group") if n.get("id") == name)


def texts(cv: Canvas) -> list[str]:
    return [n.get("text", "") for n in tree(cv).iter() if n.tag == "text"]


def test_the_drops_fall_on_the_eye_while_the_bottle_is_there():
    specimens.load_parts()
    assert registry.get("prop", "toon-eye-drops").builder is toon_inserts.eye_drops
    cv = canvas()
    toon_inserts.eye_drops(cv, cv.comp, start=1.0, squeezes=(1.5, 2.0), leave=3.0, id="bottle")
    bottle = group(cv, "bottle")
    assert (float(bottle.get("start")), float(bottle.get("end"))) == (1.0, 3.0)
    assert [float(g.get("start")) for g in bottle.iter("group") if g is not bottle] == [1.5, 2.0]


@pytest.mark.parametrize(
    "bad",
    [
        {"squeezes": ()},
        {"start": 1.0, "squeezes": (0.5,)},
        {"squeezes": (1.2, 0.6)},
        {"squeezes": (0.6,), "leave": 0.7},
        {"start": -1.0},
        {"scale": 0.0},
    ],
)
def test_drops_refuse_a_time_they_cannot_keep(bad):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_inserts.eye_drops(cv, cv.comp, **bad)


def test_the_glass_stands_on_the_counter_and_refuses_to_stand_above_nothing():
    specimens.load_parts()
    assert registry.get("prop", "toon-reception-glass").builder is toon_inserts.reception_glass
    cv = canvas()
    toon_inserts.reception_glass(cv, cv.comp)
    assert sum(1 for _ in tree(cv).iter("shape")) > 6
    for bad in ({"left": 300.0, "right": 100.0}, {"top": 900.0}, {"top": float("nan")}):
        with pytest.raises(ToonDataError):
            toon_inserts.reception_glass(cv, cv.comp, **bad)

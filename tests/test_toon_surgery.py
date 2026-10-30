"""The dentist's surgery for Toon sketches: the room, the swinging lamp and what a check-up carries in."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_surgery
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def animated(cv: Canvas, prop: str) -> list:
    return [node for node in tree(cv).iter() if node.tag.endswith("animate") and node.get("property") == prop]


def by_id(cv: Canvas, id: str):
    return next(node for node in tree(cv).iter() if node.get("id") == id)


@pytest.mark.parametrize(
    ("kind", "name", "builder"),
    [
        ("location", "toon-surgery", toon_surgery.surgery),
        ("prop", "toon-dental-lamp", toon_surgery.dental_lamp),
        ("prop", "toon-dental-tray", toon_surgery.dental_tray),
        ("prop", "toon-tooth-photo", toon_surgery.tooth_photo),
        ("prop", "toon-probe", toon_surgery.probe),
        ("prop", "toon-bib-insert", toon_surgery.bib_insert),
    ],
)
def test_the_parts_are_registered(kind, name, builder):
    assert registry.get(kind, name).builder is builder


@pytest.mark.parametrize("view", toon_surgery.VIEWS)
def test_a_surgery_draws_from_either_side(view):
    cv = canvas()
    toon_surgery.surgery(cv, cv.comp, view)
    assert len(tree(cv).findall(".//*")) > 20


def test_the_two_sides_of_a_surgery_differ():
    chair, cupboards = canvas(), canvas()
    toon_surgery.surgery(chair, chair.comp, "chair")
    toon_surgery.surgery(cupboards, cupboards.comp, "cupboards")
    assert chair.scene.to_bytes(layout="pretty") != cupboards.scene.to_bytes(layout="pretty")


def test_a_surgery_refuses_a_view_it_has_not():
    cv = canvas()
    with pytest.raises(ToonDataError, match="a surgery's view is one of"):
        toon_surgery.surgery(cv, cv.comp, "ceiling")


def test_the_lamp_swings_from_the_first_frame():
    cv = canvas()
    toon_surgery.dental_lamp(cv, cv.comp, end=6.0)
    keys = animated(cv, "rotation")[0].findall("./*")
    times = [float(k.get("time")) for k in keys]
    assert times[0] == 0.0 and times[1] < 1.0
    assert keys[0].get("value") != keys[1].get("value")


def test_a_still_lamp_hangs_where_it_is_put():
    cv = canvas()
    toon_surgery.dental_lamp(cv, cv.comp)
    assert animated(cv, "rotation") == []


def test_a_hand_on_the_lamp_adds_to_it():
    bare, held = canvas(), canvas()
    toon_surgery.dental_lamp(bare, bare.comp)
    toon_surgery.dental_lamp(held, held.comp, hand="#f0a35c")
    assert len(tree(held).findall(".//*")) > len(tree(bare).findall(".//*"))


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"pivot": (1,)}, "a lamp's pivot"),
        ({"angle": "up"}, "a lamp's angle"),
        ({"swing": 45.0}, "a lamp's angle"),
        ({"end": -1.0}, "a lamp's end"),
    ],
)
def test_a_lamp_refuses_what_it_cannot_do(kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_surgery.dental_lamp(cv, cv.comp, **kwargs)


def test_a_tray_refuses_a_place_that_is_not_a_point():
    cv = canvas()
    with pytest.raises(ToonDataError, match="a tray stands"):
        toon_surgery.dental_tray(cv, cv.comp, x="left")


@pytest.mark.parametrize("builder", [toon_surgery.tooth_photo, toon_surgery.probe])
def test_a_timed_prop_slides_in_and_a_still_stays(builder):
    timed, still = canvas(), canvas()
    builder(timed, timed.comp, start=2.0, end=5.0)
    builder(still, still.comp)
    assert len(animated(timed, "x")) == 1
    assert animated(still, "x") == []


@pytest.mark.parametrize("builder", [toon_surgery.tooth_photo, toon_surgery.probe])
def test_a_timed_prop_refuses_a_span_that_runs_backwards(builder):
    cv = canvas()
    with pytest.raises(ToonDataError, match="needs 0 <= start < end"):
        builder(cv, cv.comp, start=5.0, end=2.0)


def test_the_probe_refuses_a_tip_that_is_not_a_point():
    cv = canvas()
    with pytest.raises(ToonDataError, match="a probe's tip"):
        toon_surgery.probe(cv, cv.comp, "mouth")


def test_the_drop_falls_then_stays_as_a_mark():
    cv = canvas()
    toon_surgery.bib_insert(cv, cv.comp, 3.0, 4.2)
    drop, mark = by_id(cv, "bib-insert-drop"), by_id(cv, "bib-insert-mark")
    assert float(drop.get("end")) == float(mark.get("start")) == 3.0 + toon_surgery.DROP_FALL


def test_a_bib_refuses_a_hold_shorter_than_the_fall():
    cv = canvas()
    with pytest.raises(ToonDataError, match="a bib holds longer"):
        toon_surgery.bib_insert(cv, cv.comp, 3.0, 3.1)


def test_the_dark_comes_at_start_and_lifts_at_stop():
    cv = canvas()
    toon_surgery.darkness(cv, cv.comp, (176, 500), 2.0, 8.0, 12.0)
    keys = {float(k.get("time")): float(k.get("value")) for k in animated(cv, "opacity")[0].findall("./*")}
    assert keys[2.0] == 0.0 and keys[2.3] == 1.0 and keys[8.0] == 1.0 and keys[8.2] == 0.0


def test_a_dark_that_never_lifts_stays_to_the_end():
    cv = canvas()
    toon_surgery.darkness(cv, cv.comp, (176, 500), 2.0, 12.0, 12.0)
    keys = [float(k.get("value")) for k in animated(cv, "opacity")[0].findall("./*")]
    assert keys[-1] == 1.0


def test_the_pool_of_light_drifts_only_when_asked():
    still, moving = canvas(), canvas()
    toon_surgery.darkness(still, still.comp, (176, 500), 2.0, 8.0, 12.0)
    toon_surgery.darkness(moving, moving.comp, (176, 500), 2.0, 8.0, 12.0, drift=26.0)
    assert animated(still, "x") == []
    assert len(animated(moving, "x")) == 1


@pytest.mark.parametrize(
    ("args", "kwargs", "match"),
    [
        (("mid", 2.0, 8.0, 12.0), {}, "the light's centre"),
        (((176, 500), 8.0, 2.0, 12.0), {}, "a stop after its start"),
        (((176, 500), 2.0, 8.0, 12.0), {"drift": -1.0}, "a stop after its start"),
        (((176, 500), 12.0, 13.0, 2.0), {}, "needs 0 <= start < end"),
    ],
)
def test_darkness_refuses_what_it_cannot_do(args, kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_surgery.darkness(cv, cv.comp, *args, **kwargs)

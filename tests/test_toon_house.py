"""The domestic Toon parts: a signed ledge in place of the desk, the one-line key line, the hallway and the horse each
keep the frame's rules, and each refuses what it cannot draw."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, Signature, flat_counter, registry, signature, toon_house
from srstudio.toon import ToonDataError


def measure(text: str, size: float) -> float:
    return 0.5 * size * len(text)


def canvas(signed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(
        scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"), signature=Signature() if signed else None
    )


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


@pytest.mark.parametrize(
    ("kind", "name", "builder"),
    [
        ("prop", "toon-ledge", toon_house.ledge),
        ("graphic", "toon-key-line", toon_house.key_line),
        ("location", "toon-hallway", toon_house.hallway),
        ("prop", "toon-horse", toon_house.horse),
        ("prop", "toon-thermostat", toon_house.thermostat),
        ("prop", "toon-finger", toon_house.finger),
        ("prop", "toon-vent", toon_house.vent),
        ("location", "toon-bedroom", toon_house.bedroom),
        ("prop", "toon-quilt", toon_house.quilt),
    ],
)
def test_the_parts_are_registered(kind, name, builder):
    assert registry.get(kind, name).builder is builder


@pytest.mark.parametrize("finish", sorted(toon_house.LEDGES))
def test_a_ledge_carries_the_signature_marks_in_every_finish(finish):
    cv = canvas(signed=True)
    toon_house.ledge(cv, cv.comp, finish)
    assert signature.missing(cv.scene.to_bytes(layout="pretty")) == []


def test_a_ledge_refuses_a_finish_it_has_not():
    cv = canvas()
    with pytest.raises(ToonDataError, match="a ledge is one of"):
        toon_house.ledge(cv, cv.comp, "marble")


def test_a_key_line_lasts_from_its_start_to_its_end_and_shows_its_words():
    cv = canvas()
    toon_house.key_line(cv, cv.comp, "Dad is asleep upstairs.", 0.0, 3.0, measure=measure)
    root = tree(cv)
    assert "Dad is asleep upstairs." in [t.get("text") for t in root.iter("text")]


@pytest.mark.parametrize(
    ("text", "start", "end", "match"),
    [
        ("", 0.0, 3.0, "1 to 34"),
        ("   ", 0.0, 3.0, "1 to 34"),
        ("x" * 35, 0.0, 3.0, "1 to 34"),
        ("Fine.", 3.0, 3.0, "start < end"),
        ("Fine.", -1.0, 3.0, "start < end"),
        ("Fine.", float("nan"), 3.0, "start < end"),
    ],
)
def test_a_key_line_refuses_text_or_a_clock_it_cannot_show(text, start, end, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.key_line(cv, cv.comp, text, start, end, measure=measure)


def test_a_key_line_refuses_to_run_past_the_margins():
    cv = canvas()
    with pytest.raises(ToonDataError, match="over the frame's margins"):
        toon_house.key_line(cv, cv.comp, "x" * 34, 0.0, 3.0, measure=lambda _text, size: 2.0 * size * 34)


@pytest.mark.parametrize("door", toon_house.DOORS)
def test_the_hallway_draws_with_its_door_shut_or_open(door):
    cv = canvas()
    toon_house.hallway(cv, cv.comp, door)
    assert list(tree(cv).iter("group"))


def test_the_hallway_door_differs_between_its_states():
    shut, opened = canvas(), canvas()
    toon_house.hallway(shut, shut.comp, "shut")
    toon_house.hallway(opened, opened.comp, "open")
    assert shut.scene.to_bytes(layout="pretty") != opened.scene.to_bytes(layout="pretty")


def test_the_hallway_refuses_a_door_state_it_has_not():
    cv = canvas()
    with pytest.raises(ToonDataError, match="door"):
        toon_house.hallway(cv, cv.comp, "ajar")


def test_a_still_horse_never_blinks_and_a_timed_one_does():
    still, timed = canvas(), canvas()
    toon_house.horse(still, still.comp)
    toon_house.horse(timed, timed.comp, end=8.0)
    assert still.scene.to_bytes(layout="pretty") != timed.scene.to_bytes(layout="pretty")


def test_a_horse_blinks_where_it_is_told():
    told, default = canvas(), canvas()
    toon_house.horse(told, told.comp, end=8.0, blinks=[2.0])
    toon_house.horse(default, default.comp, end=8.0)
    assert told.scene.to_bytes(layout="pretty") != default.scene.to_bytes(layout="pretty")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"scale": 0.1}, "scale"),
        ({"scale": 2.0}, "scale"),
        ({"at": (1,)}, "reference point"),
        ({"at": "here"}, "reference point"),
        ({"start": -1.0}, "start and end"),
        ({"end": -1.0}, "start and end"),
        ({"end": 8.0, "blinks": [3.0, 2.0]}, "blinks"),
    ],
)
def test_a_horse_refuses_what_it_cannot_draw(kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.horse(cv, cv.comp, **kwargs)


READINGS = [(0.0, "68"), (1.3, "69"), (6.0, "68")]


def test_a_thermostat_shows_each_reading_until_the_next():
    cv = canvas()
    toon_house.thermostat(cv, cv.comp, READINGS, 8.0)
    root = tree(cv)
    assert sorted(t.get("text") for t in root.iter("text")) == ["68", "68", "69"]
    spans = [(g.get("start"), g.get("end")) for g in root.iter("group") if g.get("start") is not None]
    assert spans == [("0", "1.3"), ("1.3", "6"), ("6", "8")]


def test_a_still_thermostat_takes_one_reading():
    cv = canvas()
    toon_house.thermostat(cv, cv.comp, [(0.0, "68")])
    assert [t.get("text") for t in tree(cv).iter("text")] == ["68"]


@pytest.mark.parametrize(
    ("readings", "end", "kwargs", "match"),
    [
        ([], 8.0, {}, "pairs"),
        (["68"], 8.0, {}, "pairs"),
        ([(1.0, "68")], 8.0, {}, "start at 0"),
        (READINGS, 0.0, {}, "start at 0"),
        ([(0.0, "68"), (9.0, "69")], 8.0, {}, "start at 0"),
        ([(0.0, "68"), (3.0, "69"), (2.0, "70")], 8.0, {}, "readings"),
        ([(0.0, "6")], 8.0, {}, "two digits"),
        ([(0.0, "hot")], 8.0, {}, "two digits"),
        ([(0.0, 68)], 8.0, {}, "two digits"),
        ([(0.0, "68")], 8.0, {"scale": 9.0}, "scale"),
        ([(0.0, "68")], 8.0, {"at": 3}, "reference point"),
    ],
)
def test_a_thermostat_refuses_what_it_cannot_show(readings, end, kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.thermostat(cv, cv.comp, readings, end, **kwargs)


def test_a_finger_glides_to_each_place_it_is_told():
    cv = canvas()
    toon_house.finger(cv, cv.comp, (300, 500), moves=[(2.0, 320, 480)], end=4.0)
    root = tree(cv)
    assert {a.get("property") for a in root.iter("animate")} >= {"x", "y"}


def test_a_finger_shows_only_from_its_start_to_its_end():
    cv = canvas()
    toon_house.finger(cv, cv.comp, start=2.0, end=3.0)
    group = next(g for g in tree(cv).iter("group") if g.get("id") == "finger")
    assert (group.get("start"), group.get("end")) == ("2", "3")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"tip": (1,)}, "reference point"),
        ({"angle": float("nan")}, "angle"),
        ({"start": -1.0}, "start and end"),
        ({"moves": [(1.0, 2, 3)]}, "still finger"),
        ({"moves": [(2.0, 2, 3), (1.0, 2, 3)], "end": 4.0}, "moves"),
    ],
)
def test_a_finger_refuses_what_it_cannot_draw(kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.finger(cv, cv.comp, **kwargs)


@pytest.mark.parametrize(("kwargs", "match"), [({"at": "x"}, "reference point"), ({"width": 300.0}, "120 to 240")])
def test_a_vent_refuses_what_it_cannot_draw(kwargs, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_house.vent(cv, cv.comp, **kwargs)


@pytest.mark.parametrize("pattern", sorted(toon_house.QUILTS))
def test_a_quilt_carries_the_signature_marks_in_every_pattern(pattern):
    cv = canvas(signed=True)
    toon_house.quilt(cv, cv.comp, pattern)
    assert signature.missing(cv.scene.to_bytes(layout="pretty")) == []


def test_a_quilt_refuses_a_pattern_it_has_not():
    cv = canvas()
    with pytest.raises(ToonDataError, match="a quilt is one of"):
        toon_house.quilt(cv, cv.comp, "tartan")


def test_the_hallway_can_be_plain_wall_with_no_door():
    plain, shut = canvas(), canvas()
    toon_house.hallway(plain, plain.comp, "none")
    toon_house.hallway(shut, shut.comp, "shut")
    assert len(plain.scene.to_bytes(layout="pretty")) < len(shut.scene.to_bytes(layout="pretty"))


def test_the_bedroom_draws():
    cv = canvas()
    toon_house.bedroom(cv, cv.comp)
    assert list(tree(cv).iter("group"))

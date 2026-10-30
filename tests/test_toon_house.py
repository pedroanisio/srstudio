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

"""Soft, a bedtime: each prop draws, is registered, keys on the clock, and refuses what it cannot draw."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import registry, soft_bedtime, soft_props
from srstudio.soft_bedtime import BookSlide, clock_hands
from srstudio.soft_props import SoftPropError
from support.soft_props import canvas


def groups(cv) -> dict:
    return {g.get("id"): g for g in ET.fromstring(cv.scene.to_bytes()).iter("group")}


def keys(group, prop: str) -> list[tuple[float, float]]:
    animate = next(a for a in group.findall("animate") if a.get("property") == prop)
    return [(float(k.get("time")), float(k.get("value"))) for k in animate.iter("key")]


@pytest.mark.parametrize(
    "name",
    [
        "soft-wall-clock",
        "soft-picture-book",
        "soft-bedside-lamp",
        "soft-open-briefcase",
        "soft-handshake",
        "soft-quilt-pull",
    ],
)
def test_each_is_a_registered_soft_prop(name):
    assert registry.get("prop", name)


@pytest.mark.parametrize(
    ("time", "hands"),
    [("12:00", (0.0, 0.0)), ("3:00", (90.0, 0.0)), ("8:30", (255.0, 180.0)), ("9:45", (292.5, 270.0))],
)
def test_clock_hands_read_the_time(time, hands):
    assert clock_hands(time) == hands


def test_a_wall_clock_turns_its_hands_to_the_time():
    cv = canvas()
    soft_bedtime.wall_clock(cv, cv.comp, 300, 400, time="8:30", id="clock")
    found = groups(cv)
    assert float(found["clock-hour"].get("rotation")) == 255.0
    assert float(found["clock-minute"].get("rotation")) == 180.0


def test_a_book_rests_until_it_slides_then_goes_where_it_was_sent():
    cv = canvas()
    slide = BookSlide(4.0, 0.7, 300.0, 180.0, 24.0)
    soft_bedtime.picture_book(cv, cv.comp, 400, 1500, slide=slide, id="book")
    book = groups(cv)["book"]
    assert keys(book, "x") == [(0.0, 400.0), (4.0, 400.0), (4.7, 700.0)]
    assert keys(book, "y") == [(0.0, 1500.0), (4.0, 1500.0), (4.7, 1680.0)]
    assert keys(book, "rotation")[-1] == (4.7, 24.0)


def test_a_book_with_no_slide_has_no_keys():
    cv = canvas()
    soft_bedtime.picture_book(cv, cv.comp, 400, 1500, id="book")
    assert not groups(cv)["book"].findall("animate")


def test_a_lamp_is_lit_only_until_it_goes_off():
    cv = canvas()
    soft_bedtime.bedside_lamp(cv, cv.comp, 980, 1662, off=6.0, id="lamp")
    found = groups(cv)
    assert keys(found["lamp-lit"], "opacity")[:2] == [(0.0, 1.0), (6.0, 0.0)]
    assert "lamp-unlit" in found


def test_a_case_shows_its_lid_only_while_it_is_open_and_shuts_at_its_time():
    cv = canvas()
    soft_bedtime.open_briefcase(cv, cv.comp, 600, 1600, shut=9.0, id="case")
    found = groups(cv)
    assert keys(found["case-open"], "opacity")[:2] == [(0.0, 1.0), (9.0, 0.0)]
    assert (9.0, 1.0) in keys(found["case-shut"], "opacity")


def test_a_handshake_covers_the_frame_only_for_its_span_and_pumps_inside_it():
    cv = canvas()
    soft_bedtime.handshake(cv, cv.comp, 8.0, 9.2, pumps=3, id="deal")
    found = groups(cv)
    assert keys(found["deal"], "opacity")[:2] == [(0.0, 0.0), (8.0, 1.0)]
    assert (9.2, 0.0) in keys(found["deal"], "opacity")
    pumps = keys(found["deal-grip"], "y")
    assert pumps[0][0] >= 8.0 and pumps[-1][0] <= 9.2
    assert len({value for _, value in pumps}) == 2


def test_a_quilt_rises_from_under_the_bed_at_its_time():
    cv = canvas()
    soft_bedtime.quilt_pull(cv, cv.comp, 200, 1540, 1350, 5.0, 0.5, id="quilt")
    assert keys(groups(cv)["quilt"], "y") == [(0.0, 1540.0), (5.0, 1540.0), (5.5, 1350.0)]


@pytest.mark.parametrize(
    "call",
    [
        lambda cv: soft_bedtime.wall_clock(cv, cv.comp, 1, 1, time="25:00"),
        lambda cv: soft_bedtime.wall_clock(cv, cv.comp, 1, 1, time="8:61"),
        lambda cv: soft_bedtime.wall_clock(cv, cv.comp, 1, 1, time="noon"),
        lambda cv: soft_bedtime.wall_clock(cv, cv.comp, 1, 1, scale=0),
        lambda cv: soft_bedtime.wall_clock(cv, cv.comp, float("nan"), 1),
        lambda cv: soft_bedtime.picture_book(cv, cv.comp, 1, 1, scale=-1),
        lambda cv: soft_bedtime.picture_book(cv, cv.comp, 1, 1, slide=BookSlide(-1.0, 1.0, 0.0, 0.0)),
        lambda cv: soft_bedtime.picture_book(cv, cv.comp, 1, 1, slide=BookSlide(1.0, 0.0, 0.0, 0.0)),
        lambda cv: soft_bedtime.bedside_lamp(cv, cv.comp, 1, 1, off=-1.0),
        lambda cv: soft_bedtime.bedside_lamp(cv, cv.comp, 1, 1, scale=0),
        lambda cv: soft_bedtime.open_briefcase(cv, cv.comp, 1, 1, shut=-2.0),
        lambda cv: soft_bedtime.open_briefcase(cv, cv.comp, 1, float("inf")),
        lambda cv: soft_bedtime.handshake(cv, cv.comp, 2.0, 1.0),
        lambda cv: soft_bedtime.handshake(cv, cv.comp, 1.0, 2.0, pumps=0),
        lambda cv: soft_bedtime.quilt_pull(cv, cv.comp, 1, 500, 900, 1.0, 0.5),
        lambda cv: soft_bedtime.quilt_pull(cv, cv.comp, 1, 900, 500, 1.0, 0.0),
    ],
)
def test_each_refuses_what_it_cannot_draw(call):
    with pytest.raises(SoftPropError):
        call(canvas())


def test_the_module_sits_beside_soft_props_with_their_error():
    assert soft_bedtime.SoftPropError is soft_props.SoftPropError

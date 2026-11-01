"""A phone on a table, a map that tells on you, and a dinner to put a fork down on."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_locate
from support.tip_tablet import canvas


def scene(cv) -> str:
    return cv.scene.to_bytes().decode()


def ids(cv) -> list[str]:
    return [e.get("id", "") for e in ET.fromstring(cv.scene.to_bytes()).iter("group")]


def test_a_table_phone_rattles_only_when_it_rings():
    still, ringing = canvas(), canvas()
    cutout_locate.table_phone(still, still.comp, 540, 1220)
    cutout_locate.table_phone(ringing, ringing.comp, 540, 1220, rings=[(0.0, 0.4)])
    assert 'property="x"' not in scene(still).split("table-phone-body", 1)[1]
    assert 'property="x"' in scene(ringing)


def test_a_table_phone_on_speaker_shows_its_arcs():
    cv = canvas()
    cutout_locate.table_phone(cv, cv.comp, 540, 1220, speaker=[(0.4, 8.0)])
    assert "table-phone-speaker" in ids(cv)


@pytest.mark.parametrize(
    "options",
    [
        dict(scale=0),
        dict(scale=float("nan")),
        dict(rings=[(2.0, 1.0)]),
        dict(speaker=[(-1.0, 1.0)]),
        dict(lit=[(3.0, 3.0)]),
    ],
)
def test_a_table_phone_refuses_what_it_cannot_draw(options):
    cv = canvas()
    with pytest.raises(cutout_locate.CutoutLocateError):
        cutout_locate.table_phone(cv, cv.comp, 540, 1220, **options)


def test_a_location_chip_has_one_stop_for_each_place():
    cv = canvas()
    cutout_locate.location_chip(cv, cv.comp, 540, 400, [(1.0, 2.0, "table"), (3.0, 4.0, "cross"), (5.0, 6.0, "moon")])
    assert {"location-chip-stop-0", "location-chip-stop-1", "location-chip-stop-2"} <= set(ids(cv))


def test_a_location_chip_letters_nothing():
    cv = canvas()
    cutout_locate.location_chip(cv, cv.comp, 540, 400, [(1.0, 2.0, "moon")])
    assert "<text" not in scene(cv)


@pytest.mark.parametrize(
    "stops",
    [
        [],
        [(1.0, 2.0, "submarine")],
        [(2.0, 1.0, "table")],
        [(1.0, 1.0, "table")],
        [(-1.0, 1.0, "table")],
        [(1.0, 3.0, "table"), (2.0, 4.0, "moon")],
        [(3.0, 4.0, "table"), (1.0, 2.0, "moon")],
    ],
)
def test_a_location_chip_refuses_stops_it_cannot_show(stops):
    cv = canvas()
    with pytest.raises(cutout_locate.CutoutLocateError):
        cutout_locate.location_chip(cv, cv.comp, 540, 400, stops)


def test_a_notice_phone_letters_its_lines_only_from_its_time():
    cv = canvas()
    cutout_locate.notice_phone(cv, cv.comp, 330, 1000, ("A NAME ADDED", "YOU"), at=2.0, id="notice")
    assert "A NAME ADDED" in scene(cv) and "notice-chip" in ids(cv)


@pytest.mark.parametrize(
    "lines, options",
    [
        ((), {}),
        (("ONE", "TWO", "THREE"), {}),
        (("",), {}),
        (("A LINE MUCH TOO LONG FOR THE CHIP",), {}),
        (("OK",), dict(at=-1.0)),
        (("OK",), dict(scale=0)),
    ],
)
def test_a_notice_phone_refuses_what_its_chip_cannot_hold(lines, options):
    cv = canvas()
    with pytest.raises(cutout_locate.CutoutLocateError):
        cutout_locate.notice_phone(cv, cv.comp, 330, 1000, lines, **options)


@pytest.mark.parametrize("draw", [cutout_locate.dinner_plate, cutout_locate.table_fork, cutout_locate.held_phone])
@pytest.mark.parametrize("scale", [0, -1, float("nan")])
def test_a_small_prop_refuses_a_scale(draw, scale):
    cv = canvas()
    with pytest.raises(cutout_locate.CutoutLocateError):
        draw(cv, cv.comp, 500, 900, scale=scale)

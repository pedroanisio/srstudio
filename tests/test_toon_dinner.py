"""Toon dinner: the restaurant booth, the laid table that stands in for the desk, the dishes on it and the card
reader whose screen changes on cue."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, TOON, Canvas, flat_counter, registry, toon, toon_dinner
from srstudio.canvas import Signature
from srstudio.toon import ToonDataError


def canvas(signed: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=8.0, background=PEACH.background)
    return Canvas(
        scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"), signature=Signature() if signed else None
    )


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas):
    return [t.get("text") for t in tree(cv).iter("text")]


def groups(cv: Canvas):
    return [g.get("id") for g in tree(cv).iter("group")]


def test_the_dinner_parts_are_registered_for_the_toon_style():
    assert "toon_dinner" in TOON.parts
    entries = {e.name: e for e in registry.entries()}
    for name, kind in (
        ("toon-restaurant", "location"),
        ("toon-table", "prop"),
        ("toon-dishes", "prop"),
        ("toon-card-reader", "prop"),
    ):
        assert entries[name].kind == kind and entries[name].style == "toon"


def test_the_restaurant_has_a_booth_and_a_specials_board_and_no_signature():
    cv = canvas()
    toon_dinner.restaurant(cv, cv.comp)
    assert texts(cv) == ["SPECIALS", "LOBSTER", "MARKET\nPRICE"]
    assert not [g for g in groups(cv) if g.startswith("sig-")]  # the table carries the signature, as the desk does


def test_the_specials_board_takes_its_own_dish_and_price():
    cv = canvas()
    toon_dinner.restaurant(cv, cv.comp, special=("OYSTERS", "ASK"))
    assert texts(cv) == ["SPECIALS", "OYSTERS", "ASK"]
    with pytest.raises(ToonDataError, match="special"):
        toon_dinner.restaurant(canvas(), cv.comp, special=("", "ASK"))
    with pytest.raises(ToonDataError, match="special"):
        toon_dinner.restaurant(canvas(), cv.comp, special=("X" * 15, "ASK"))


def test_the_table_replaces_the_desk_and_signs_the_shot():
    cv = canvas()
    toon_dinner.table(cv, cv.comp)
    ids = groups(cv)
    assert any(g.startswith("sig-cactus") for g in ids)
    shapes = len(list(tree(cv).iter("shape")))
    bare = canvas(signed=False)
    toon_dinner.table(bare, bare.comp)
    assert 0 < len(list(tree(bare).iter("shape"))) < shapes


def test_each_dish_is_drawn_where_it_is_placed_in_order():
    cv = canvas()
    toon_dinner.dishes(cv, cv.comp, [("salad", 380), ("water", 470), ("check", 540)])
    ids = groups(cv)
    assert [g for g in ids if g.startswith("dish-")] == ["dish-salad", "dish-water", "dish-check"]
    xs = {g.get("id"): float(g.get("x")) for g in tree(cv).iter("group") if g.get("id", "").startswith("dish-")}
    assert xs["dish-salad"] == toon.fx(380) and xs["dish-check"] == toon.fx(540)
    assert set(toon_dinner.DISHES) >= {"salad", "water", "lobster", "shells", "wine", "glass", "empty", "check"}


def test_dishes_take_their_own_id_and_number_a_second_of_a_kind():
    cv = canvas()
    toon_dinner.dishes(cv, cv.comp, [("glass", 300), ("glass", 360)], id="brock-dish")
    assert [g for g in groups(cv) if "dish" in g] == ["brock-dish-glass", "brock-dish-glass-2"]


def test_a_dish_can_arrive_at_a_time():
    cv = canvas()
    toon_dinner.dishes(cv, cv.comp, [("check", 400, 2.5)])
    check = next(g for g in tree(cv).iter("group") if g.get("id") == "dish-check")
    keys = [(float(k.get("time")), float(k.get("value"))) for a in check.iter("animate") for k in a.iter("key")
            if a.get("property") == "opacity"]  # fmt: skip
    assert keys == [(0.0, 0.0), (2.5, 1.0)]


@pytest.mark.parametrize(
    "items, match",
    [
        ([("soup", 300)], "dish"),
        ([("salad", -20)], "inside"),
        ([("salad", 700)], "inside"),
        ([("salad", 300, -1.0)], "time"),
        ([("salad",)], "dish"),
    ],
)
def test_bad_dishes_are_refused(items, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_dinner.dishes(cv, cv.comp, items)


def test_the_card_reader_shows_one_screen_at_a_time():
    cv = canvas()
    states = [(0.0, "TAP CARD", "idle"), (3.0, "DECLINED", "bad"), (5.0, "APPROVED", "good")]
    toon_dinner.card_reader(cv, cv.comp, states)
    assert [t for t in texts(cv)] == ["TAP CARD", "DECLINED", "APPROVED"]
    screens = [g for g in tree(cv).iter("group") if g.get("id", "").startswith("card-reader-screen-")]
    shown = [
        [(float(k.get("time")), float(k.get("value"))) for a in s.iter("animate") for k in a.iter("key")]
        for s in screens
    ]
    assert shown == [[(0.0, 1.0), (3.0, 0.0)], [(0.0, 0.0), (3.0, 1.0), (5.0, 0.0)], [(0.0, 0.0), (5.0, 1.0)]]


@pytest.mark.parametrize(
    "states, match",
    [
        ([], "at least one"),
        ([(1.0, "TAP CARD", "idle")], "from 0"),
        ([(0.0, "TAP CARD", "idle"), (0.0, "NO", "bad")], "rising"),
        ([(0.0, "X" * 11, "idle")], "screen"),
        ([(0.0, "OK", "purple")], "tone"),
    ],
)
def test_bad_card_reader_screens_are_refused(states, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_dinner.card_reader(cv, cv.comp, states)

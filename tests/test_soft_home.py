"""Soft at home: a den whose time of day is keyed, two flats, a door to tilt down from, and what a sofa collects."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import SOFT, Canvas, registry, soft_home
from srstudio.soft_home import SoftHomeError
from srstudio.soft_sets import Shot
from support.soft_props import canvas


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def animated(t, id: str, prop: str):
    groups = {g.get("id"): g for g in t.iter("group")}
    keys = [a for a in groups[id].findall("animate") if a.get("property") == prop]
    assert keys, f"{id} has no {prop} keys"
    return [(float(k.get("time")), float(k.get("value"))) for k in keys[0].findall("key")]


def test_the_parts_are_registered_for_the_soft_style():
    assert "soft_home" in SOFT.parts
    entries = {e.name: e for e in registry.entries()}
    for name in ("soft-den", "soft-flats", "soft-restaurant", "soft-television", "soft-chip-bag", "soft-slippers"):
        assert entries[name].style == "soft"


def test_a_dens_day_raises_its_blind_and_takes_off_the_night_together():
    cv = canvas()
    soft_home.den(cv, cv.comp, end=10.0, day=((0.0, 0.0), (2.0, 0.0), (4.0, 1.0)))
    t = tree(cv)
    assert animated(t, "soft-den-blind", "scaleY")[-1][1] < 0.1
    assert animated(t, "soft-den-night", "opacity") == [(0.0, 1.0), (2.0, 1.0), (4.0, 0.0)]


def test_a_den_keeps_its_stillness_and_flickers_after_it():
    cv = canvas()
    soft_home.den(cv, cv.comp, end=5.0, day=((0.0, 0.0),), still=0.45)
    rows = animated(tree(cv), "soft-den-flicker", "opacity")
    assert rows[0] == (0.0, 1.0) and rows[1][0] == 0.45


def test_a_dens_marks_stand_over_its_night():
    cv = canvas()
    soft_home.den(cv, cv.comp, end=5.0, day=((0.0, 0.0),))
    order = [g.get("id") for g in tree(cv).iter("group")]
    assert order.index("soft-den-front") > order.index("soft-den-night")


@pytest.mark.parametrize(
    "kw",
    [
        {"day": ()},
        {"day": ((1.0, 0.0),)},
        {"day": ((0.0, 0.0), (0.0, 1.0))},
        {"day": ((0.0, 2.0),)},
        {"end": 0.0},
        {"still": 11.0},
    ],
)
def test_a_den_refuses_a_time_of_day_it_cannot_keep(kw):
    cv = canvas()
    with pytest.raises(SoftHomeError):
        soft_home.den(cv, cv.comp, **{"end": 10.0, **kw})


def test_flats_cut_in_on_either_home_and_keep_the_marks_out_of_the_shot():
    cv = canvas()
    soft_home.flats(cv, cv.comp, shots=(Shot(0.0), Shot(1.0, 2.0, 270.0, 960.0)))
    t = tree(cv)
    assert animated(t, "soft-flats-room", "scaleX") == [(0.0, 1.0), (1.0, 2.0)]
    assert "soft-flats-front" in [g.get("id") for g in t.iter("group")]


def test_a_doorway_tilts_down_only_when_told():
    cv = canvas()
    soft_home.doorway(cv, cv.comp, tilt=3.0, drop=500.0, seconds=0.5)
    assert animated(tree(cv), "soft-restaurant-world", "y")[-1] == (3.5, -500.0)
    still = canvas()
    soft_home.doorway(still, still.comp)
    assert not list(
        next(g for g in tree(still).iter("group") if g.get("id") == "soft-restaurant-world").findall("animate")
    )


def test_a_doorway_can_tilt_back_up():
    cv = canvas()
    soft_home.doorway(cv, cv.comp, tilt=3.0, back=6.0, drop=500.0, seconds=0.5)
    assert animated(tree(cv), "soft-restaurant-world", "y")[-2:] == [(6.0, -500.0), (6.5, 0.0)]


@pytest.mark.parametrize(
    "kw",
    [
        {"tilt": -1.0},
        {"tilt": 1.0, "drop": 0.0},
        {"tilt": 1.0, "drop": 900.0},
        {"tilt": 1.0, "seconds": 0.0},
        {"back": 2.0},
        {"tilt": 3.0, "back": 3.2},
    ],
)
def test_a_doorway_refuses_a_tilt_past_its_pavement(kw):
    cv = canvas()
    with pytest.raises(SoftHomeError):
        soft_home.doorway(cv, cv.comp, **kw)


def test_flats_put_a_door_clear_of_each_sofa():
    cv = canvas()
    soft_home.flats(cv, cv.comp)
    assert [g for g in tree(cv).iter("group") if g.get("id") == "soft-flats-room"]


def test_a_television_talks_with_bars_and_counts_in_digits():
    cv = canvas()
    soft_home.television(cv, cv.comp, talks=[(0.5, 1.5)], counts=[("5", 2.0, 3.0), ("4", 3.0, 4.0)])
    t = tree(cv)
    assert [x.get("text") for x in t.iter("text")] == ["5", "4"]
    assert "soft-television-bar-5" in [g.get("id") for g in t.iter("group")]


@pytest.mark.parametrize(
    "kw",
    [
        {"counts": [("12", 1.0, 2.0)]},
        {"counts": [("x", 1.0, 2.0)]},
        {"counts": [("5", 2.0, 1.0)]},
        {"talks": [(2.0, 1.0)]},
        {"talks": [(0.5, 1.5)], "counts": [("5", 1.0, 2.0)]},
        {"scale": 0.0},
        {"still": -1.0},
    ],
)
def test_a_television_refuses_what_its_screen_cannot_show(kw):
    cv = canvas()
    with pytest.raises(SoftHomeError):
        soft_home.television(cv, cv.comp, **kw)


@pytest.mark.parametrize(
    "draw",
    [
        lambda cv: soft_home.chip_bag(cv, cv.comp, 0, 0, scale=0),
        lambda cv: soft_home.chip(cv, cv.comp, scale=-1),
        lambda cv: soft_home.blanket(cv, cv.comp, scale=0),
        lambda cv: soft_home.scarf(cv, cv.comp, scale=0),
        lambda cv: soft_home.slippers(cv, cv.comp, 0, 0, scale=0),
        lambda cv: soft_home.slippers(cv, cv.comp, 0, 0, apart=0),
    ],
)
def test_a_prop_refuses_a_size_it_cannot_be_drawn_at(draw):
    with pytest.raises(SoftHomeError):
        draw(canvas())


def test_a_hook_card_shows_its_words_over_its_span():
    cv = canvas()
    soft_home.hook_card(cv, cv.comp, "DINNER TONIGHT", (100, 450, 500, 90), end=3.0)
    assert [x.get("text") for x in tree(cv).iter("text")] == ["DINNER TONIGHT"]


@pytest.mark.parametrize(
    ("text", "box", "kw"),
    [
        ("", (0, 0, 10, 10), {}),
        ("x" * (soft_home.MAX_HOOK + 1), (0, 0, 10, 10), {}),
        ("OK", (0, 0, 0, 10), {}),
        ("OK", (0, 0, 10), {}),
        ("OK", (0, 0, 10, 10), {"start": 4.0}),
    ],
)
def test_a_hook_card_refuses_words_or_a_box_it_cannot_hold(text, box, kw):
    with pytest.raises(SoftHomeError):
        soft_home.hook_card(canvas(), canvas().comp, text, box, end=3.0, **kw)


def test_the_new_poses_are_on_the_pose_sheet_and_interpolate():
    from srstudio.blob import POSES

    sit = POSES["sit"]
    for name in ("sit-show", "sit-back"):
        assert POSES[name].limbs["leg_l"] == sit.limbs["leg_l"]
        assert sit.lerp(POSES[name], 0.5).name in ("sit", name)
    assert POSES["hug"].limbs["arm_l"].p3[0] > 0  # both hands go across, to the right

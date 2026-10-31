"""Soft odds: what a sketch hands to its cast, and the ride that keeps a prop in one hand."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import SOFT, Canvas, blob, registry, soft_odds
from srstudio.soft_odds import SoftOddError
from support.soft_props import canvas

END = 8.0


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def groups(cv: Canvas) -> dict:
    return {g.get("id"): g for g in tree(cv).iter("group")}


def keys(group, prop: str) -> list[tuple[float, float]]:
    animate = next(a for a in group if a.tag.endswith("animate") and a.get("property") == prop)
    return [(float(k.get("time")), float(k.get("value"))) for k in animate]


def test_the_module_is_a_part_of_the_soft_style():
    assert "soft_odds" in SOFT.parts
    entries = {e.name: e for e in registry.entries()}
    for name in ("soft-tongs", "soft-grill", "soft-smoke", "soft-pizza-box", "soft-bottle"):
        assert entries[name].kind == "prop" and entries[name].style == "soft"


def test_a_prop_in_one_hand_stays_on_its_side_of_the_frame_through_a_flip():
    spot = (300.0, 1500.0)
    cues = [blob.cue(0, "stand", spot, scale=2.0), blob.cue(1.0, "stand", spot, scale=2.0, flip=True)]
    cv = canvas()
    soft_odds.in_hand(cv, cv.comp, cues, "left", end=END, scale=2.0, id="left")
    soft_odds.in_hand(cv, cv.comp, cues, "right", end=END, scale=2.0, id="right")
    g = groups(cv)
    left, right = [x for _, x in keys(g["left"], "x")], [x for _, x in keys(g["right"], "x")]
    assert all(x < 300 for x in left) and all(x > 300 for x in right)
    assert left[0] == left[-1] and right[0] == right[-1]  # the same place in the frame, on the other arm


def test_a_hand_is_on_a_side_of_the_frame():
    cv = canvas()
    with pytest.raises(SoftOddError, match="left or the right"):
        soft_odds.in_hand(cv, cv.comp, [blob.cue(0, "stand")], "up", end=END, id="x")


def test_tongs_snap_shut_on_each_click_and_open_again():
    cv = canvas()
    soft_odds.tongs(cv, cv.comp, 100, 200, clicks=[1.0, 1.3], id="t")
    arm = groups(cv)["t-right"]
    assert keys(arm, "rotation") == [
        (0.0, soft_odds.TONGS_OPEN),
        (1.0, 0.5),
        (1.0 + soft_odds.SNAP, soft_odds.TONGS_OPEN),
        (1.3, 0.5),
        (1.3 + soft_odds.SNAP, soft_odds.TONGS_OPEN),
    ]


def test_tongs_without_clicks_stand_open_and_refuse_a_click_they_cannot_show():
    cv = canvas()
    soft_odds.tongs(cv, cv.comp, id="still")
    assert not [a for a in groups(cv)["still-left"] if a.tag.endswith("animate")]
    for clicks, message in (([1.0, 1.05], "between clicks"), ([2.0, 1.0], "rising"), ([-1.0], "rising")):
        with pytest.raises(SoftOddError, match=message):
            soft_odds.tongs(canvas(), cv.comp, clicks=clicks)


def test_the_grill_chars_its_burgers_and_shows_each_flame_level_in_its_span():
    cv = canvas()
    soft_odds.grill(cv, cv.comp, 500, 1500, end=END, burgers=2, char=5.0, flames=((0.0, 0), (2.0, 1), (5.0, 3)), id="g")
    g = groups(cv)
    assert "g-flames-1" in g and "g-flames-3" in g and "g-flames-2" not in g
    assert keys(g["g-flames-1"], "opacity") == [(0.0, 0.0), (2.0, 1.0), (5.0, 0.0)]
    assert keys(g["g-burger-2-char"], "opacity") == [(0.0, 0.0), (5.0, 1.0), (END, 0.0)]


def test_the_turned_burger_goes_up_and_comes_down_over():
    cv = canvas()
    soft_odds.grill(cv, cv.comp, 500, 1500, end=END, flip=3.0, id="g")
    burger = groups(cv)["g-burger-2"]
    assert keys(burger, "rotation")[-1] == (3.2, 360.0)
    assert min(y for _, y in keys(burger, "y")) < -314


@pytest.mark.parametrize(
    "kw, message",
    [
        ({"flames": ((1.0, 0),)}, "from 0"),
        ({"flames": ((0.0, 9),)}, "levels"),
        ({"burgers": 9}, "burgers"),
        ({"char": END}, "char"),
        ({"scale": 0}, "positive scale"),
    ],
)
def test_a_grill_refuses_what_it_cannot_draw(kw, message):
    cv = canvas()
    with pytest.raises(SoftOddError, match=message):
        soft_odds.grill(cv, cv.comp, 0, 0, end=END, **kw)


def test_smoke_is_the_same_every_build_and_thicker_at_a_higher_level():
    def built():
        cv = canvas()
        soft_odds.smoke(cv, cv.comp, 500, 900, ((0.0, 1), (4.0, 3)), end=END, id="s")
        return cv

    a, b = built(), built()
    assert a.scene.to_bytes(layout="pretty") == b.scene.to_bytes(layout="pretty")
    ids = list(groups(a))
    assert sum(i.startswith("s-puff-3-") for i in ids) > sum(i.startswith("s-puff-1-") for i in ids) > 0
    assert keys(groups(a)["s-level-3"], "opacity") == [(0.0, 0.0), (4.0, 1.0), (END, 0.0)]


def test_smoke_is_inside_its_levels():
    cv = canvas()
    with pytest.raises(SoftOddError, match="levels"):
        soft_odds.smoke(cv, cv.comp, 0, 0, ((0.0, 7),), end=END)


def test_a_pizza_box_has_no_lettering_to_leave_the_safe_area_and_a_bottle_takes_a_colour():
    cv = canvas()
    soft_odds.pizza_box(cv, cv.comp, 540, 900)
    soft_odds.bottle(cv, cv.comp, 540, 900, color="#E2B64E")
    t = tree(cv)
    assert not list(t.iter("text"))
    assert "#E2B64E" in ET.tostring(t, encoding="unicode")
    with pytest.raises(SoftOddError, match="positive scale"):
        soft_odds.pizza_box(cv, cv.comp, 540, 900, scale=-1)


def test_a_burger_lies_on_the_grate_until_it_is_turned():
    cv = canvas()
    soft_odds.grill(cv, cv.comp, 500, 1500, end=END, flip=4.0, id="g")
    assert keys(groups(cv)["g-burger-2"], "y")[:2] == [(0.0, -314.0), (4.0 - soft_odds.FLIP_LIFT, -314.0)]
    with pytest.raises(SoftOddError, match="turned from"):
        soft_odds.grill(cv, cv.comp, 500, 1500, end=END, flip=soft_odds.FLIP_LIFT / 2)

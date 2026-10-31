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
    for name in ("soft-tongs", "soft-grill", "soft-smoke", "soft-pizza-box", "soft-bottle", "soft-washer", "soft-tv"):
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


def opacity(group) -> list[tuple[float, float]]:
    return keys(group, "opacity")


def test_a_washer_turns_until_it_stops_and_its_light_dies_with_it():
    cv = canvas()
    soft_odds.washer(cv, cv.comp, 300, 1500, end=END, stop=4.0)
    g = groups(cv)
    turn = keys(g["soft-washer-drum"], "rotation")
    assert turn == [(0.0, 0.0), (4.0, 360.0 * 4.0 / soft_odds.DRUM_TURN)]
    assert opacity(g["soft-washer-light"]) == [(0.0, 1.0), (4.0, 0.0)]


def test_a_washer_runs_to_the_end_unless_it_is_told_to_stop():
    cv = canvas()
    soft_odds.washer(cv, cv.comp, 300, 1500, end=END)
    assert keys(groups(cv)["soft-washer-drum"], "rotation")[-1][0] == END


def test_what_goes_into_a_washer_rides_the_drum_from_its_cue_and_the_door_swings():
    cv = canvas()
    loads = [(1.0, "brick"), (2.0, "ball"), (3.0, "coins"), (4.0, "shovel")]
    soft_odds.washer(cv, cv.comp, 300, 1500, end=END, open_at=[(0.5, 1.0), (3.5, 4.0)], loads=loads)
    g = groups(cv)
    for k, (time, _) in enumerate(loads, start=1):
        assert opacity(g[f"soft-washer-load-{k}"])[:2] == [(0.0, 0.0), (time, 1.0)]
    assert opacity(g["soft-washer-door-open"])[1:3] == [(0.5, 1.0), (1.0, 0.0)]
    assert opacity(g["soft-washer-door"])[:3] == [(0.0, 1.0), (0.5, 0.0), (1.0, 1.0)]


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"stop": 99.0}, "stops within"),
        ({"open_at": [(5.0, 2.0)]}, "door opens"),
        ({"loads": [(1.0, "cat")]}, "a load is"),
        ({"loads": [(99.0, "brick")]}, "a load is"),
    ],
)
def test_a_washer_refuses_what_it_cannot_do(kwargs, match):
    cv = canvas()
    with pytest.raises(SoftOddError, match=match):
        soft_odds.washer(cv, cv.comp, 300, 1500, end=END, **kwargs)


def test_a_tv_flickers_until_it_goes_off_and_a_fridge_light_dies():
    cv = canvas()
    soft_odds.tv(cv, cv.comp, 300, 1500, end=END, off=2.0)
    soft_odds.home_fridge(cv, cv.comp, 800, 1500, end=END, off=3.0)
    g = groups(cv)
    assert opacity(g["soft-tv-picture"]) == [(0.0, 1.0), (2.0, 0.0)]
    assert opacity(g["soft-home-fridge-light"]) == [(0.0, 1.0), (3.0, 0.0)]
    steps = opacity(g["soft-tv-flicker"])
    assert len(steps) == 6 and steps[-1][0] <= 2.0 and len({v for _, v in steps}) > 1


@pytest.mark.parametrize("draw", [soft_odds.tv, soft_odds.home_fridge])
def test_a_set_dies_within_the_reel(draw):
    cv = canvas()
    with pytest.raises(SoftOddError, match="within"):
        draw(cv, cv.comp, 300, 1500, end=END, off=END + 1)


def test_dust_falls_from_its_cue_the_same_every_build():
    def built():
        cv = canvas()
        soft_odds.dust(cv, cv.comp, 500, 300, 2.0, end=END, id="d")
        return cv

    a, b = built(), built()
    assert a.scene.to_bytes(layout="pretty") == b.scene.to_bytes(layout="pretty")
    g = groups(a)
    assert sum(i.startswith("d-") for i in g) == soft_odds.DUST_SPECKS
    assert keys(g["d-1"], "y")[0] == (2.0, 0.0)
    assert opacity(g["d"]) == [(0.0, 0.0), (2.0, 1.0), (END, 0.0)]
    cv = canvas()
    with pytest.raises(SoftOddError, match="before its end"):
        soft_odds.dust(cv, cv.comp, 500, 300, END, end=END)


def test_a_dimmer_steps_down_and_refuses_rows_out_of_order():
    cv = canvas()
    soft_odds.dimmer(cv, cv.comp, ((0.0, 0.0), (2.0, 0.3), (4.0, 0.6)))
    assert opacity(groups(cv)["soft-dimmer"]) == [(0.0, 0.0), (2.0, 0.3), (4.0, 0.6)]
    for rows, match in ((((1.0, 0.1),), "rising time"), (((0.0, 2.0),), "0..1")):
        with pytest.raises(SoftOddError, match=match):
            soft_odds.dimmer(cv, cv.comp, rows)


@pytest.mark.parametrize("draw", [soft_odds.brick, soft_odds.bowling_ball, soft_odds.coin_bag])
def test_a_thing_to_put_in_a_washer_is_drawn_where_it_is_asked_and_refuses_a_bad_scale(draw):
    cv = canvas()
    draw(cv, cv.comp, 540, 900, id="thing")
    assert groups(cv)["thing"].get("x") in ("540", "540.0")
    with pytest.raises(SoftOddError, match="positive scale"):
        draw(cv, cv.comp, 540, 900, scale=0)


def test_a_burger_lies_on_the_grate_until_it_is_turned():
    cv = canvas()
    soft_odds.grill(cv, cv.comp, 500, 1500, end=END, flip=4.0, id="g")
    assert keys(groups(cv)["g-burger-2"], "y")[:2] == [(0.0, -314.0), (4.0 - soft_odds.FLIP_LIFT, -314.0)]
    with pytest.raises(SoftOddError, match="turned from"):
        soft_odds.grill(cv, cv.comp, 500, 1500, end=END, flip=soft_odds.FLIP_LIFT / 2)

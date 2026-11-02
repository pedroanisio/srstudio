"""The Stick holiday props: each draws what it says, has no face, and refuses what it cannot draw."""

import json
import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Group, Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, registry, stick, stick_holiday
from srstudio.stick_holiday import BULB_COLOURS, HAT, PUMPKIN, RING, RING_DIM, TREE_H, WORKTOP_BODY, WORKTOP_TOP

PARTS = (
    "stick-holiday-tree",
    "stick-tree-star",
    "stick-light-string",
    "stick-step-stool",
    "stick-pumpkin",
    "stick-smart-speaker",
    "stick-worktop",
)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def paints(cv: Canvas) -> set[str]:
    """Every colour the drawing fills a shape with."""
    return {n.get("fill", "").lower() for n in tree(cv).iter() if n.get("fill")}


def spans(cv: Canvas, node: Group) -> list[tuple[float, float]]:
    """When ``node`` shows: its opacity keys, read back as (on, off) pairs."""
    root = tree(cv)
    target = next(n for n in root.iter() if n.get("id") == node.id)
    keys = [
        (float(k.get("time")), float(k.get("value")))
        for animate in target.findall("animate")
        if animate.get("property") == "opacity"
        for k in animate.findall("key")
    ]
    on, out = None, []
    for time, value in keys:
        if value > 0 and on is None:
            on = time
        elif value == 0 and on is not None:
            out.append((on, time))
            on = None
    return out


def test_the_tree_stands_on_its_foot_and_can_go_without_its_star():
    cv = canvas()
    with_star = stick_holiday.tree(cv, cv.comp, 500, 1700)
    without = stick_holiday.tree(cv, cv.comp, 500, 1700, star=False, scale=1.5)
    assert (float(with_star.x), float(with_star.y)) == (500, 1700)
    assert float(without.scaleX) == 1.5
    assert stick_holiday.tree_top(500, 1700) == (500, 1700 - TREE_H)
    assert stick_holiday.tree_top(500, 1700, scale=0.5) == (500, 1700 - TREE_H * 0.5)
    assert len(list(with_star.elements())) == len(list(without.elements())) + 1


@pytest.mark.parametrize("scale", [0, -1, float("nan"), True])
def test_a_tree_or_a_star_needs_a_positive_scale(scale):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_holiday.tree(cv, cv.comp, 0, 0, scale=scale)
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_holiday.tree_star(cv, cv.comp, 0, 0, scale=scale)


def test_a_star_is_five_pointed_about_its_middle():
    cv = canvas()
    star = stick_holiday.tree_star(cv, cv.comp, 200, 300, scale=2)
    assert (float(star.x), float(star.y), float(star.scaleX)) == (200, 300, 2)
    path = next(n.get("path") for n in tree(cv).iter() if n.get("path"))
    assert path.count("L") == 9 and path.endswith("Z")


def test_the_lights_sag_between_their_ends_with_one_bulb_each_and_stay_dark_until_they_blink_on():
    cv = canvas()
    points = stick_holiday.light_points(100, 200, 500, 200, 5, sag=40)
    assert points[0] == pytest.approx((100, 200)) and points[-1] == pytest.approx((500, 200))
    assert points[2] == pytest.approx((300, 240))
    assert [p[1] for p in points] == pytest.approx([200, 230, 240, 230, 200])
    g = stick_holiday.light_string(cv, cv.comp, 100, 200, 500, 200, 3.0, bulbs=5, sag=40, on=1.0)
    lit = next(n for n in g.elements() if n.id == stick_holiday.lit_group(g).id)
    assert spans(cv, lit) == [(1.0, 1.08), (1.16, 3.0)]
    assert paints(cv) >= {c.lower() for c in BULB_COLOURS}


def test_lights_with_no_moment_to_come_on_burn_from_the_first_frame():
    cv = canvas()
    g = stick_holiday.light_string(cv, cv.comp, 100, 200, 500, 200, 3.0)
    assert spans(cv, stick_holiday.lit_group(g)) == [(0.0, 3.0)]


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(bulbs=1), "bulbs"),
        (dict(bulbs=2.5), "bulbs"),
        (dict(sag=-1), "sag"),
        (dict(sag=float("inf")), "sag"),
        (dict(on=-0.1), "come on"),
        (dict(on=3.0), "come on"),
    ],
)
def test_lights_refuse_what_they_cannot_draw(kw, match):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match=match):
        stick_holiday.light_string(cv, cv.comp, 100, 200, 500, 200, 3.0, **kw)


def test_lights_need_some_seconds_and_finite_ends():
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="seconds"):
        stick_holiday.light_string(cv, cv.comp, 100, 200, 500, 200, 0.0)
    with pytest.raises(stick.StickDataError, match="ends"):
        stick_holiday.light_string(cv, cv.comp, float("nan"), 200, 500, 200, 1.0)


def test_a_stool_stands_on_its_foot_and_says_how_high_its_top_step_is():
    cv = canvas()
    two = stick_holiday.step_stool(cv, cv.comp, 400, 1700)
    assert (float(two.x), float(two.y)) == (400, 1700)
    assert stick_holiday.stool_top(steps=2) == 2 * stick_holiday.STEP_RISE
    assert stick_holiday.stool_top(steps=3, scale=2) == 6 * stick_holiday.STEP_RISE


@pytest.mark.parametrize(
    ("kw", "match"), [(dict(steps=0), "steps"), (dict(steps=4), "steps"), (dict(scale=0), "scale")]
)
def test_a_stool_refuses_what_it_cannot_draw(kw, match):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match=match):
        stick_holiday.step_stool(cv, cv.comp, 0, 0, **kw)
    with pytest.raises(stick.StickDataError, match=match):
        stick_holiday.stool_top(**kw)


def test_the_pumpkin_is_plain_with_a_hat_or_without_and_has_no_face():
    cv = canvas()
    stick_holiday.pumpkin(cv, cv.comp, 200, 1000)
    hatted = paints(cv)
    assert PUMPKIN.lower() in hatted and HAT.lower() in hatted
    bare = canvas()
    stick_holiday.pumpkin(bare, bare.comp, 200, 1000, hat=False)
    assert HAT.lower() not in paints(bare)
    # a carved face would be dark shapes on the pumpkin; the plain one only has its ribs and stem
    assert not [n for n in tree(bare).iter() if n.tag == "text" or n.get("shape") == "ellipse"]
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_holiday.pumpkin(cv, cv.comp, 0, 0, scale=-1)


def test_the_speaker_has_no_letters_and_lights_its_ring_only_for_its_spans():
    cv = canvas()
    g = stick_holiday.smart_speaker(cv, cv.comp, 300, 900, glow=((1.0, 2.5), (3.0, 3.5)))
    assert not [n for n in tree(cv).iter() if n.tag == "text"]
    assert RING.lower() in paints(cv) and RING_DIM.lower() in paints(cv)
    assert spans(cv, stick_holiday.ring_group(g)) == [(1.0, 2.5), (3.0, 3.5)]


def test_a_speaker_with_no_spans_stays_dim():
    cv = canvas()
    stick_holiday.smart_speaker(cv, cv.comp, 300, 900)
    assert RING.lower() not in paints(cv)


@pytest.mark.parametrize(
    ("glow", "match"),
    [
        (((2.0, 1.0),), "glow"),
        (((0.0, 1.0), (0.5, 2.0)), "glow"),
        (((float("nan"), 1.0),), "glow"),
        (((1.0,),), "glow"),
    ],
)
def test_a_speaker_refuses_a_glow_it_cannot_show(glow, match):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match=match):
        stick_holiday.smart_speaker(cv, cv.comp, 0, 0, glow=glow)


def test_a_speaker_needs_a_positive_scale():
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_holiday.smart_speaker(cv, cv.comp, 0, 0, scale=math.inf)


def test_the_worktop_runs_between_its_ends_and_down_to_the_frames_foot():
    cv = canvas()
    stick_holiday.worktop(cv, cv.comp, -20, 500, 1180)
    assert {WORKTOP_TOP.lower(), WORKTOP_BODY.lower()} <= paints(cv)
    rects = [n for n in tree(cv).iter() if n.get("shape") == "rect" and float(n.get("y", 0)) >= 1180]
    assert max(float(n.get("y")) + float(n.get("height")) for n in rects) >= 1920


@pytest.mark.parametrize(
    ("x0", "x1", "top"), [(500, 500, 1180), (500, 100, 1180), (0, 500, 1920), (0, 500, -1), (float("nan"), 500, 1180)]
)
def test_a_worktop_refuses_what_it_cannot_draw(x0, x1, top):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="worktop"):
        stick_holiday.worktop(cv, cv.comp, x0, x1, top)


@pytest.mark.parametrize("name", PARTS)
def test_every_prop_is_registered_with_a_contract_and_stays_in_the_stick_style(name):
    entry = registry.get("prop", name)
    assert entry.style == "stick"
    assert entry.contract is not None
    data = entry.describe()["contract"]
    assert json.loads(json.dumps(data, allow_nan=False)) == data
    assert not [n for n, p in data["arguments"]["properties"].items() if p.get("x-status") == "unknown"]


@pytest.mark.parametrize(
    ("build", "args"),
    [
        (stick_holiday.tree, (500, 1700)),
        (stick_holiday.tree_star, (500, 700)),
        (stick_holiday.step_stool, (500, 1700)),
        (stick_holiday.pumpkin, (500, 1100)),
        (stick_holiday.smart_speaker, (500, 1100)),
    ],
)
def test_every_placed_prop_draws_a_schema_valid_scene_the_same_way_twice(build, args):
    cv, again = canvas(), canvas()
    build(cv, cv.comp, *args)
    build(again, again.comp, *args)
    assert cv.scene.check(schema=True) == []
    assert cv.scene.to_bytes() == again.scene.to_bytes()

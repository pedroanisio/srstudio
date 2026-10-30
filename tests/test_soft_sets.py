"""Soft sets for a close shot, and what a reel in them holds: a phone that rides in the hands, canes, a time card."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import WARM, Canvas, Signature, blob, flat_counter, registry, soft_props, soft_sets
from srstudio.soft_props import SoftPropError, TimeState
from srstudio.soft_sets import SoftSetError
from support.soft_props import canvas


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def groups(cv: Canvas) -> dict:
    return {g.get("id"): g for g in tree(cv).iter("group")}


def signed() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=10.0, background=WARM.background)
    return Canvas(scene, WARM, font_asset="caption-font", namer=flat_counter("k"), signature=Signature())


def opacity_keys(group) -> list[tuple[float, float]]:
    animate = next(a for a in group.findall("animate") if a.get("property") == "opacity")
    return [(float(k.get("time")), float(k.get("value"))) for k in animate.iter("key")]


@pytest.mark.parametrize(
    ("kind", "name"),
    [
        ("location", "soft-park"),
        ("prop", "soft-bench"),
        ("prop", "soft-cane"),
        ("prop", "soft-phone"),
        ("graphic", "soft-time-card"),
    ],
)
def test_the_parts_are_registered_for_the_soft_style(kind, name):
    entry = registry.get(kind, name)
    assert entry.style == "soft"


def test_the_grade_is_a_group_of_its_own_carrying_every_finish_effect():
    cv = canvas()
    soft_sets.finish(cv, cv.comp)
    applied = groups(cv)["soft-finish"].get("effects")
    assert all(f"soft-{kind}" in applied for kind in soft_sets.FINISH)


def test_the_park_draws_each_tree_stage_only_in_its_span():
    cv = signed()
    soft_sets.park(cv, cv.comp, growth=((0.0, 0), (2.0, 1), (4.0, 3)))
    found = groups(cv)
    assert opacity_keys(found["soft-park-tree-0"])[:2] == [(0.0, 1.0), (2.0, 0.0)]
    assert (2.0, 1.0) in opacity_keys(found["soft-park-tree-1"])
    assert "soft-park-tree-2" not in found


def test_the_park_carries_both_signature_marks_in_front_of_the_cast():
    cv = signed()
    order = []
    soft_sets.park(cv, cv.comp, cast=lambda g: order.append(cv.group(g, "the-cast")))
    ids = [g.get("id") for g in tree(cv).iter("group")]
    assert ids.index("the-cast") < ids.index("sig-cactus") and "sig-code" in ids


def test_the_bench_shows_only_while_seated():
    cv = signed()
    soft_sets.park(cv, cv.comp)
    assert "soft-bench" not in groups(cv)
    cv = signed()
    soft_sets.park(cv, cv.comp, seated=[(5.0, 9.0)])
    found = groups(cv)
    assert "soft-bench" in found and (5.0, 1.0) in opacity_keys(found["soft-park-benched"])


@pytest.mark.parametrize(
    "growth", [(), ((1.0, 0),), ((0.0, 0), (0.0, 1)), ((0.0, 0), (2.0, 99)), ((0.0, 0), (float("inf"), 1))]
)
def test_a_growth_that_cannot_be_drawn_is_refused(growth):
    cv = signed()
    with pytest.raises(SoftSetError, match="growth"):
        soft_sets.park(cv, cv.comp, growth=growth)


def test_a_held_prop_rides_between_the_hands_on_every_drawing():
    cues = blob.settle(
        [blob.cue(0, "clasp", (100, 500), scale=2.0), blob.cue(1.0, "sit", (300, 500), scale=2.0, ease=0.4)], 15
    )
    cv = canvas()
    blob.held(cv, cv.comp, cues, end=2.0, scale=2.0, id="hands")
    frames = blob.drawings(cues, end=2.0)
    found = groups(cv)["hands"]
    xs = [float(k.get("value")) for a in found.findall("animate") if a.get("property") == "x" for k in a.iter("key")]
    assert len(xs) == len(frames)
    last = frames[-1].pose.limbs
    assert xs[-1] == pytest.approx(2.0 * (last["arm_l"].p3[0] + last["arm_r"].p3[0]) / 2, abs=1e-2)


def test_a_held_prop_refuses_a_bad_scale():
    cv = canvas()
    with pytest.raises(blob.BlobError, match="scale"):
        blob.held(cv, cv.comp, [blob.cue(0, "stand")], end=1.0, scale=0, id="hands")


def test_speaking_gives_a_character_the_sung_mouth_only_on_its_own_lines():
    cues = blob.speaking(
        [blob.cue(0, "stand", mouth="smile"), blob.cue(1, "stand", mouth="flat"), blob.cue(3, "stand", mouth="o")],
        [(1.2, 2.0)],
        4.0,
    )
    assert [c.mouth for c in cues] == ["smile", "sing", "o"]


def test_speaking_keeps_the_later_of_two_cues_at_one_time():
    cues = blob.speaking([blob.cue(0, "stand", eyes="open"), blob.cue(0, "stand", eyes="wide")], [], 1.0)
    assert [c.eyes for c in cues] == ["wide"]


def test_a_phone_shows_its_back_unless_it_is_given_a_screen():
    cv = canvas()
    drawn = []
    soft_props.phone(cv, cv.comp, id="back")
    soft_props.phone(cv, cv.comp, screen=lambda g: drawn.append(g), id="front")
    assert len(drawn) == 1
    found = groups(cv)
    assert len(list(found["back"].iter("shape"))) > len(list(found["front"].iter("shape")))


def test_a_month_view_stamps_every_week_only_when_asked():
    plain, stamped = canvas(), canvas()
    soft_props.month_view(plain, plain.comp, "MARCH", "2080")
    soft_props.month_view(stamped, stamped.comp, "MARCH", "2080", stamp="AWAY")
    assert [x.get("text") for x in tree(plain).iter("text")] == ["MARCH", "2080"]
    assert [x.get("text") for x in tree(stamped).iter("text")] == ["MARCH", "2080", "AWAY"]


def test_a_time_card_shows_one_reading_at_a_time():
    cv = canvas()
    soft_props.time_card(cv, cv.comp, [TimeState("2028", 1.0, 2.0), TimeState("2031", 2.0, 3.0)], (380, 450, 320, 118))
    found = groups(cv)
    assert [x.get("text") for x in tree(cv).iter("text")] == ["2028", "2031"]
    assert opacity_keys(found["soft-time-card-1"]) == [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)]


@pytest.mark.parametrize(
    ("states", "box", "why"),
    [
        ((), (0, 0, 10, 10), "at least one"),
        ((TimeState("1", 0.0, 1.0),), (0, 0, 0, 10), "positive size"),
        ((TimeState("1", 2.0, 1.0),), (0, 0, 10, 10), "in order"),
        ((TimeState("1", 0.0, 2.0), TimeState("2", 1.0, 3.0)), (0, 0, 10, 10), "in order"),
        ((TimeState("much too long", 0.0, 2.0),), (0, 0, 10, 10), "characters"),
    ],
)
def test_a_time_card_that_cannot_be_read_is_refused(states, box, why):
    cv = canvas()
    with pytest.raises(SoftPropError, match=why):
        soft_props.time_card(cv, cv.comp, states, box)


@pytest.mark.parametrize(
    "call",
    [
        lambda cv: soft_props.phone(cv, cv.comp, scale=0),
        lambda cv: soft_props.bench(cv, cv.comp, width=0),
        lambda cv: soft_props.cane(cv, cv.comp, 0, 0, height=0),
    ],
)
def test_a_prop_refuses_a_size_it_cannot_draw(call):
    with pytest.raises(SoftPropError):
        call(canvas())

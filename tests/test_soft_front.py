"""Soft front room: a room a sofa can leave, a mug, and a card of stars that takes one hard jab."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import SOFT, Canvas, blob, registry, soft_bedtime, soft_front
from srstudio.soft_front import SoftFrontError
from srstudio.soft_props import SoftPropError
from srstudio.soft_sets import Shot
from support.soft_props import canvas


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def groups(cv: Canvas) -> dict:
    return {g.get("id"): g for g in tree(cv).iter("group")}


def test_the_module_is_a_part_of_the_soft_style():
    assert "soft_front" in SOFT.parts
    entries = {e.name: e for e in registry.entries()}
    assert entries["soft-front-room"].kind == "location"
    assert entries["soft-mug"].kind == "prop"
    assert entries["soft-star-card"].kind == "graphic"
    assert {e.style for n, e in entries.items() if n in ("soft-front-room", "soft-mug", "soft-star-card")} == {"soft"}


def test_the_room_draws_its_cast_in_front_of_the_wall_and_what_is_in_the_hall_behind_it():
    cv = canvas()
    soft_front.front_room(cv, cv.comp, hall=lambda g: cv.group(g, "in-hall"), cast=lambda g: cv.group(g, "on-rug"))
    ids = [g.get("id") for g in tree(cv).iter("group")]
    assert ids.index("in-hall") < ids.index("soft-front-room-wall") < ids.index("on-rug")


def test_the_sofa_in_the_hall_is_there_only_while_it_is_told_to_be():
    cv = canvas()
    soft_front.front_room(cv, cv.comp, wedged=[(0.0, 4.0)])
    assert "soft-front-room-sofa" in groups(cv)
    bare = canvas()
    soft_front.front_room(bare, bare.comp)
    assert "soft-front-room-sofa" not in groups(bare)


def test_a_shot_cuts_in_on_the_room_and_leaves_the_marks_where_they_are():
    cv = canvas()
    soft_front.front_room(cv, cv.comp, shots=[Shot(0.0), Shot(1.0, 1.6, 300.0, 1100.0)])
    g = groups(cv)
    assert any(a.tag.endswith("animate") and a.get("property") == "scaleX" for a in g["soft-front-room-room"])
    assert not any(a.tag.endswith("animate") for a in g["soft-front-room-front"])


def test_a_room_refuses_shots_out_of_order():
    cv = canvas()
    with pytest.raises(ValueError, match="rising"):
        soft_front.front_room(cv, cv.comp, shots=[Shot(2.0), Shot(1.0)])


@pytest.mark.parametrize("spans", [[(3.0, 1.0)], [(-1.0, 2.0)], [(float("nan"), 2.0)]])
def test_a_wedged_sofa_needs_real_spans(spans):
    cv = canvas()
    with pytest.raises(SoftFrontError, match="wedged"):
        soft_front.front_room(cv, cv.comp, wedged=spans)


def test_a_mug_sits_at_a_finite_place():
    cv = canvas()
    soft_front.mug(cv, cv.comp, 100, 200, scale=0.5)
    assert groups(cv)["soft-mug"].get("x") is not None
    with pytest.raises(SoftFrontError, match="mug"):
        soft_front.mug(cv, cv.comp, float("inf"), 0)
    with pytest.raises(SoftFrontError, match="mug"):
        soft_front.mug(cv, cv.comp, 0, 0, scale=0)


def test_a_star_card_is_empty_until_the_jab_and_jumps_with_it():
    cv = canvas()
    soft_front.star_card(cv, cv.comp, 540, 960, tap=2.0, stars=1)
    g = groups(cv)
    lit = [k for k in g if k.startswith("soft-star-card-lit")]
    assert lit == ["soft-star-card-lit-1"]
    animated = g["soft-star-card"]
    assert any(a.tag.endswith("animate") and a.get("property") == "y" for a in animated)


def test_a_star_card_that_is_never_jabbed_stays_empty_and_still():
    cv = canvas()
    soft_front.star_card(cv, cv.comp, 540, 960)
    g = groups(cv)
    assert not [k for k in g if k.startswith("soft-star-card-lit")]
    assert not any(a.tag.endswith("animate") for a in g["soft-star-card"])


@pytest.mark.parametrize("stars", [0, 6, 1.5, True])
def test_a_star_card_refuses_a_rating_it_does_not_have(stars):
    cv = canvas()
    with pytest.raises(SoftFrontError, match="stars"):
        soft_front.star_card(cv, cv.comp, 540, 960, tap=1.0, stars=stars)


@pytest.mark.parametrize("tap", [-1.0, float("nan")])
def test_a_star_card_refuses_a_jab_off_the_clock(tap):
    cv = canvas()
    with pytest.raises(SoftFrontError, match="jab"):
        soft_front.star_card(cv, cv.comp, 540, 960, tap=tap)


def test_a_star_card_has_no_words_on_it():
    cv = canvas()
    soft_front.star_card(cv, cv.comp, 540, 960, tap=1.0)
    assert not [n for n in tree(cv).iter() if n.tag.endswith("text")]


def test_a_lamp_can_come_on_late_and_a_lamp_that_is_not_told_draws_as_it_did():
    plain, late = canvas(), canvas()
    soft_bedtime.bedside_lamp(plain, plain.comp)
    soft_bedtime.bedside_lamp(late, late.comp, on=3.0, off=5.0)
    default = groups(plain)["soft-bedside-lamp-lit"]
    assert ET.tostring(default) != ET.tostring(groups(late)["soft-bedside-lamp-lit"])
    same = canvas()
    soft_bedtime.bedside_lamp(same, same.comp, on=0.0)
    assert ET.tostring(default) == ET.tostring(groups(same)["soft-bedside-lamp-lit"])
    with pytest.raises(SoftPropError, match="come on before"):
        soft_bedtime.bedside_lamp(canvas(), canvas().comp, on=5.0, off=3.0)


def test_sitting_on_the_floor_keeps_the_seated_top_and_lays_the_legs_along_the_ground():
    sit, floor = blob.POSES["sit"], blob.POSES["floor"]
    assert floor.head == sit.head and floor.limbs["torso"] == sit.limbs["torso"]
    assert floor.limbs["arm_l"] == sit.limbs["arm_l"]
    assert sit.limbs["leg_l"].p3[1] > 40  # a shin goes down to a floor below the seat
    assert floor.limbs["leg_l"].p3[1] < 0 and floor.limbs["leg_l"].p3[0] < sit.limbs["leg_l"].p3[0]

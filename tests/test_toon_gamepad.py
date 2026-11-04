"""A controller held in both paws (ADR 0230): the holds as typed data, the pair of paws (one drawing, mirrored for the
frame's right arm), thumbs that point in toward each other, and a grip that draws wherever a pose does."""

import math
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, anatomy_parts, flat_counter, toon, toon_cast, toon_friends, toon_gamepad, toon_head
from srstudio.anatomy import Arm, Facing, Side
from srstudio.head_motion import HeadPlan
from srstudio.toon import Pose, ToonDataError
from srstudio.toon_cast import CENTRE
from srstudio.toon_gamepad import GRIP, GRIPS, HOLDS, Hold

PLAYERS = pytest.mark.parametrize("critter", [toon_friends.LEO_CRITTER, toon_friends.SAM_CRITTER], ids=("leo", "sam"))


def stage(seconds: float = 4.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=seconds, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("g"))


def points(shape) -> list[tuple[float, float]]:
    return list(zip(shape[0::2], shape[1::2], strict=True))


def same_points(a, b, within: float = 0.05) -> bool:
    def near(p, among):
        return min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in among) <= within

    return len(a) == len(b) and all(near(p, b) for p in a) and all(near(q, a) for q in b)


def bounds(layers) -> tuple[float, float, float, float]:
    every = [point for shape, _ in layers for point in points(shape)]
    xs, ys = [x for x, _ in every], [y for _, y in every]
    return min(xs), max(xs), min(ys), max(ys)


# -- the holds ---------------------------------------------------------------------------------------------------------
def test_the_grips_are_the_four_holds_in_order():
    assert GRIPS == ("pad", "pad-press", "pad-lap", "pad-up")
    assert tuple(HOLDS) == GRIPS


def test_no_grip_shares_a_name_with_a_shared_arm_kind():
    assert not set(GRIPS) & set(toon.ARMS)


@pytest.mark.parametrize("thumbs", [("stick",), ("stick", "stick", "stick"), ("stick", "nose"), ("", "rest")])
def test_a_hold_with_a_thumb_nowhere_it_can_lie_is_refused(thumbs):
    with pytest.raises(ToonDataError, match="each thumb"):
        Hold((CENTRE, 776.0), (104.0, 764.0), thumbs)


def test_the_lap_hold_sits_lower_and_the_lifted_one_higher_than_play():
    play, lap, up = HOLDS["pad"].at[1], HOLDS["pad-lap"].at[1], HOLDS["pad-up"].at[1]
    assert up < play < lap


def test_every_hold_is_centred_on_the_body():
    assert all(hold.at[0] == CENTRE for hold in HOLDS.values())


# -- the pair of paws --------------------------------------------------------------------------------------------------
def test_the_grip_is_the_frame_s_left_paw_seen_palm_on():
    assert (GRIP.side, GRIP.facing) == (Side.LEFT, Facing.PALM)
    assert anatomy_parts.CHARACTERS["toon-leo"].drawing == GRIP
    assert anatomy_parts.CHARACTERS["toon-sam"].drawing == GRIP


def test_the_right_arm_s_paw_is_the_grip_reflected_and_the_left_s_is_not():
    assert not GRIP.mirrored(Arm(Side.LEFT).hand(Facing.PALM))
    assert GRIP.mirrored(Arm(Side.RIGHT).hand(Facing.PALM))


@pytest.mark.parametrize("name", ["pad", "pad-lap", "pad-up"])
def test_on_a_hold_with_the_thumbs_alike_the_right_paw_is_the_left_one_reflected(name):
    look = toon_friends.LEO_CRITTER.look()
    hold = HOLDS[name]
    left = toon_gamepad.grip_layers(look, hold, Arm(Side.LEFT))
    right = toon_gamepad.grip_layers(look, hold, Arm(Side.RIGHT))
    assert [colour for _, colour in left] == [colour for _, colour in right]
    pressed, *rest = zip(left, right, strict=True)  # the paw's pressed ink band, then fill, fingers and thumb
    for (a, _), (b, _) in rest:  # the same outline, though a reflected stroke runs round it the other way
        assert same_points([(2 * CENTRE - x, y) for x, y in points(a)], points(b))
    (a, _), (b, _) = pressed  # the band's pressure is the hand's, not the side's: it breathes within its own weight
    al, ar, at, ab = bounds([(a, "ink")])
    bl, br, bt, bb = bounds([(b, "ink")])
    assert (bl, br, bt, bb) == pytest.approx((2 * CENTRE - ar, 2 * CENTRE - al, at, ab), abs=toon_cast.INK)


@pytest.mark.parametrize("name", GRIPS)
@pytest.mark.parametrize("side", [Side.LEFT, Side.RIGHT])
def test_each_thumb_points_in_toward_the_middle_from_its_grip(name, side):
    hold = HOLDS[name]
    grip_x = hold.at[0] + side.value * 50.0
    tip_x, tip_y = toon_gamepad.thumb_tip(hold, side)
    assert abs(tip_x - CENTRE) < abs(grip_x - CENTRE)
    assert (tip_x - CENTRE) * side.value > 0  # each thumb stays on its own half
    assert tip_y < hold.at[1]  # over the top edge, not under the controller


def test_a_pressing_thumb_moves_off_its_stick_and_the_other_stays():
    play, press = HOLDS["pad"], HOLDS["pad-press"]
    assert toon_gamepad.thumb_tip(press, Side.LEFT) == toon_gamepad.thumb_tip(play, Side.LEFT)
    assert toon_gamepad.thumb_tip(press, Side.RIGHT) != toon_gamepad.thumb_tip(play, Side.RIGHT)


# -- the controller ----------------------------------------------------------------------------------------------------
def test_the_controller_is_inked_and_in_its_own_colours_only():
    colours = {colour for _, colour in toon_gamepad.pad_layers((CENTRE, 776.0), "#c9ced6")}
    assert colours == {"ink", "#c9ced6", toon_gamepad.PAD_SHADE, toon_gamepad.PAD_BUMPER, toon_gamepad.PAD_CAP}


def test_the_controller_spans_less_than_the_shoulders():
    left, right, _, _ = bounds(toon_gamepad.pad_layers((CENTRE, 776.0)))
    shoulders = toon_cast.SHOULDERS
    assert shoulders[0][0] < left and right < shoulders[1][0]


# -- a player's gestures -----------------------------------------------------------------------------------------------
@PLAYERS
def test_a_shared_arm_kind_is_left_to_the_shared_drawing(critter):
    assert all(critter.gesture(arms) is None for arms in toon.ARMS)


@PLAYERS
def test_an_arm_kind_that_is_neither_shared_nor_a_grip_is_refused_by_name(critter):
    with pytest.raises(ToonDataError, match="no gesture 'juggle'"):
        critter.gesture("juggle")


@PLAYERS
@pytest.mark.parametrize("name", GRIPS)
def test_a_grip_draws_both_sleeves_the_controller_and_both_paws_under_the_face(critter, name):
    under, over = critter.gesture(name)
    assert over == []
    colours = [colour for _, colour in under]
    fur = critter.look().paw
    assert critter.sleeve in colours and critter.pad in colours and fur in colours
    sleeves = max(i for i, c in enumerate(colours) if c == critter.sleeve)
    assert sleeves < colours.index(critter.pad) < max(i for i, c in enumerate(colours) if c == fur)


@PLAYERS
def test_a_player_has_no_eye_of_its_own_to_shut(critter):
    assert not any(critter.shut(eyes) for eyes in toon.EYES)


def test_a_player_with_no_sleeve_wears_its_coat():
    bare = replace(toon_friends.LEO_CRITTER, sleeve="", sleeve_shade="")
    under, _ = bare.gesture("pad")
    assert bare.look().coat in [colour for _, colour in under]


# -- through the drawings ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", GRIPS)
def test_a_grip_draws_through_the_head_rig(name):
    cv = stage()
    toon_head.figure(cv, cv.comp, toon_friends.LEO_RIG, [Pose(0.0, "half", "flat", name)], 4.0, HeadPlan.still())
    assert b"<group" in cv.scene.to_bytes(layout="pretty")


def test_a_grip_records_a_hand_on_each_arm():
    cv = stage()
    toon_head.figure(cv, cv.comp, toon_friends.SAM_RIG, [Pose(0.0, "half", "flat", "pad")], 4.0, HeadPlan.still())
    sides = sorted(hand.side.value for hand in cv.limbs.values() if hand.owner == "sam")
    assert sides == [-1, 1]


def test_the_shared_flat_figure_still_holds_to_the_shared_arm_kinds():
    with pytest.raises(ToonDataError, match="no expression"):
        toon_cast.figure_layers(toon_friends.LEO, "half", "flat", "pad")

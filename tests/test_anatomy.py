"""The shared contract of a hand (ADR 0147): the rule, read from the arm, and every way of breaking it."""

import pytest

from srstudio import anatomy
from srstudio.anatomy import Arm, Drawing, Facing, Fingers, HandError, Side, Thumb, Thumbless, View, pair

LEFT, RIGHT = Side.LEFT, Side.RIGHT
SIDES = (LEFT, RIGHT)


@pytest.mark.parametrize("side", SIDES)
def test_palms_to_camera_both_thumbs_point_inward(side):
    assert Arm(side).hand(Facing.PALM).thumb is Thumb.IN


@pytest.mark.parametrize("side", SIDES)
def test_backs_to_camera_both_thumbs_point_outward(side):
    assert Arm(side).hand(Facing.BACK).thumb is Thumb.OUT


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize(("facing", "front"), [(Facing.PALM, Thumb.IN), (Facing.BACK, Thumb.OUT)])
def test_a_pov_arm_inverts(side, facing, front):
    seen = Arm(side, View.POV).hand(facing).thumb
    assert seen is not front


@pytest.mark.parametrize("side", SIDES)
def test_a_hanging_hand_shows_its_back_with_the_thumb_in_by_geometry(side):
    assert Arm(side).hand(Facing.BACK, Fingers.DOWN).thumb is Thumb.IN


def test_the_thumb_is_on_the_frame_where_the_arm_and_the_facing_put_it():
    assert Arm(RIGHT).hand(Facing.PALM).thumb_x == -1
    assert Arm(LEFT).hand(Facing.PALM).thumb_x == 1
    assert Arm(LEFT).hand(Facing.BACK).thumb_x == -1
    assert Arm(RIGHT).hand(Facing.BACK, Fingers.DOWN).thumb_x == -1


def test_the_right_hand_is_the_mirror_of_the_left_on_every_view():
    for view in View:
        for facing in Facing:
            assert Arm(LEFT, view).hand(facing).thumb_x == -Arm(RIGHT, view).hand(facing).thumb_x


@pytest.mark.parametrize("facing", Facing)
def test_a_drawing_is_mirrored_on_exactly_one_arm_of_a_pair(facing):
    drawing = Drawing("open", LEFT, facing)
    assert drawing.mirrored(Arm(LEFT).hand(facing)) is False
    assert drawing.mirrored(Arm(RIGHT).hand(facing)) is True


def test_the_back_of_a_hand_is_the_mirror_of_its_palm():
    drawing = Drawing("open", LEFT, Facing.PALM)
    assert drawing.mirrored(Arm(LEFT).hand(Facing.BACK)) is True
    assert drawing.mirrored(Arm(RIGHT).hand(Facing.BACK)) is False


def test_turning_a_drawing_fingers_down_never_mirrors_it():
    drawing = Drawing("open", LEFT, Facing.PALM)
    assert drawing.mirrored(Arm(LEFT).hand(Facing.PALM, Fingers.DOWN)) is False


def test_a_pov_arm_takes_the_other_drawing():
    drawing = Drawing("open", LEFT, Facing.PALM)
    assert drawing.mirrored(Arm(LEFT, View.POV).hand(Facing.PALM)) is True


def test_a_hand_on_the_other_arm_is_a_build_error():
    hand = Arm(LEFT).hand(Facing.PALM)
    assert hand.on(Arm(LEFT)) is hand
    with pytest.raises(HandError, match="the left arm's hand was placed on the right arm"):
        hand.on(Arm(RIGHT))


def test_a_hand_in_another_view_of_its_arm_is_a_build_error():
    with pytest.raises(HandError, match="another view"):
        Arm(LEFT).hand(Facing.PALM).on(Arm(LEFT, View.POV))


def test_a_pair_is_one_hand_of_each_arm_in_order():
    a, b = Arm(LEFT).hand(Facing.PALM), Arm(RIGHT).thumbless("folded under the arm")
    assert pair(a, b) == (a, b)
    with pytest.raises(HandError, match="left arm's hand, then the right"):
        pair(b, a)
    with pytest.raises(HandError, match="left arm's hand, then the right"):
        pair(a, Arm(LEFT).hand(Facing.BACK))


@pytest.mark.parametrize("why", ["", "   ", None, 3])
def test_a_hand_with_no_thumb_says_why(why):
    with pytest.raises(HandError, match="says why"):
        Arm(LEFT).thumbless(why)


def test_a_hand_with_no_thumb_has_no_thumb_side_and_still_keeps_to_its_arm():
    paw = Arm(RIGHT).thumbless("a ball at the end of a sleeve")
    assert paw.thumb is None and paw.thumb_x is None
    assert paw.on(Arm(RIGHT)) is paw
    with pytest.raises(HandError, match="placed on the left arm"):
        paw.on(Arm(LEFT))


def test_a_drawing_with_no_thumb_is_never_mirrored_by_the_contract():
    drawing = Drawing("open", LEFT, Facing.PALM)
    with pytest.raises(HandError, match="no thumb"):
        drawing.mirrored(Arm(RIGHT).thumbless("a mitten"))


@pytest.mark.parametrize(
    "build",
    [
        lambda: Arm("left"),
        lambda: Arm(LEFT, "front"),
        lambda: Arm(LEFT).hand("palm"),
        lambda: Arm(LEFT).hand(Facing.PALM, "up"),
        lambda: anatomy.Hand(None, Facing.PALM),
        lambda: anatomy.Hand(LEFT, Facing.PALM),
        lambda: Thumbless("left", "a mitten"),
        lambda: Drawing("", LEFT, Facing.PALM),
        lambda: Drawing("open", 1, Facing.PALM),
        lambda: Drawing("open", LEFT, "palm"),
    ],
)
def test_untyped_hands_are_refused(build):
    with pytest.raises(HandError):
        build()


@pytest.mark.parametrize(("sign", "side"), [(-1, LEFT), (1, RIGHT), (-1.0, LEFT), (1.0, RIGHT)])
def test_a_side_is_read_from_a_style_s_own_sign(sign, side):
    assert Side.of(sign) is side
    assert side.other is not side and side.other.other is side


@pytest.mark.parametrize("sign", [0, 2, -0.5, "left", None, True])
def test_any_other_sign_is_refused(sign):
    with pytest.raises(HandError):
        Side.of(sign)

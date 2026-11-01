"""stick.reaching: a hand sent to a point on a prop, an arm that keeps its length, and each refusal."""

import math
from dataclasses import replace

import pytest

from srstudio import stick
from srstudio.stick import ARM, RigPose, StickDataError, reaching

STAND = stick.STANDING["stand"]


def shoulder(pose: RigPose) -> tuple[float, float]:
    return pose.neck[0] - 4, pose.neck[1] + 34


def lengths(pose: RigPose, i: int) -> tuple[float, float]:
    return math.dist(shoulder(pose), pose.elbows[i]), math.dist(pose.elbows[i], pose.hands[i])


def test_the_hand_lands_on_the_point_and_the_arm_keeps_its_length():
    pose = reaching(STAND, (760.0, 1000.0))
    assert pose.hands[1] == (760.0, 1000.0)
    assert lengths(pose, 1) == pytest.approx((ARM, ARM))


def test_far_moves_the_far_arm_and_leaves_the_near_one():
    pose = reaching(STAND, (400.0, 1000.0), far=True)
    assert pose.hands[0] == (400.0, 1000.0)
    assert lengths(pose, 0) == pytest.approx((ARM, ARM))
    assert (pose.elbows[1], pose.hands[1]) == (STAND.elbows[1], STAND.hands[1])


def test_only_the_arm_changes():
    pose = reaching(STAND, (760.0, 1000.0))
    assert replace(pose, elbows=STAND.elbows, hands=STAND.hands) == STAND


def test_bend_picks_the_side_the_elbow_goes():
    down, up = reaching(STAND, (760.0, 900.0), bend=1), reaching(STAND, (760.0, 900.0), bend=-1)
    assert down.elbows[1][1] > 900.0 > up.elbows[1][1]


def test_a_longer_arm_is_a_choice():
    pose = reaching(STAND, (880.0, 900.0), arm=190.0)
    assert lengths(pose, 1) == pytest.approx((190.0, 190.0))


def test_a_point_out_of_reach_is_refused():
    with pytest.raises(StickDataError, match="out of reach"):
        reaching(STAND, (1200.0, 900.0))


@pytest.mark.parametrize(
    ("hand", "kw", "message"),
    [
        ((float("nan"), 900.0), {}, "finite"),
        ((700.0, 900.0), {"bend": 0}, "bends"),
        ((700.0, 900.0), {"arm": 0.0}, "arm"),
    ],
)
def test_a_bad_request_is_refused(hand, kw, message):
    with pytest.raises(StickDataError, match=message):
        reaching(STAND, hand, **kw)

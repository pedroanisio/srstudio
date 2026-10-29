"""Two-arm recipes preserve explicit depth, limb clearance and one shared prop's anchors."""

from dataclasses import replace

import pytest

from srstudio.limbs import HUMAN, ArmProfile, Frame, LimbError, Vec3
from srstudio.limbs.integration import legacy_action
from srstudio.limbs.motion import Action, Motion, TransformTrack
from srstudio.limbs.props import Anchor, Coordination, Prop, capsule_distance, crossed_arms, grip_prop


def profiles():
    return ArmProfile(shoulder=Vec3(0.58, 0, 0)), ArmProfile(shoulder=Vec3(-0.58, 0, 0), side="left")


def test_crossed_arms_reach_across_the_body_with_an_explicit_foreground_arm():
    right, left = profiles()
    pair = crossed_arms(right, left, duration=3, front="right")
    pose = pair.sample(1.5)
    assert pose.right.arm.wrist.x < 0 < pose.left.arm.wrist.x
    assert pose.right.arm.wrist.z > pose.left.arm.wrist.z + 0.3
    assert legacy_action("toon", "crossed", start=0, duration=3).name == "crossed"
    samples = {i: pair.sample(i / 24) for i in range(73)}
    for i in reversed(range(73)):
        assert pair.sample(i / 24) == samples[i]
        assert not samples[i].diagnostics
    reverse = crossed_arms(right, left, duration=3, front="left").sample(1.5)
    assert reverse.left.arm.wrist.z > reverse.right.arm.wrist.z
    with pytest.raises(LimbError):
        crossed_arms(right, left, front="neither")


def test_capsule_distance_handles_crossing_parallel_and_degenerate_segments():
    assert capsule_distance(Vec3(-1, 0, 0), Vec3(1, 0, 0), Vec3(0, -1, 0), Vec3(0, 1, 0)) == pytest.approx(0)
    assert capsule_distance(Vec3(), Vec3(2, 0, 0), Vec3(0, 1, 0), Vec3(2, 1, 0)) == pytest.approx(1)
    assert capsule_distance(Vec3(), Vec3(), Vec3(1, 0, 0), Vec3(2, 0, 0)) == pytest.approx(1)
    assert capsule_distance(Vec3(), Vec3(), Vec3(0, 2, 0), Vec3(0, 2, 0)) == pytest.approx(2)


def test_coordination_reports_inter_arm_penetration_and_strict_mode_rejects_it():
    right = Motion(ArmProfile(), HUMAN)
    left = Motion(ArmProfile(side="left"), HUMAN)
    pair = Coordination(right, left)
    assert any(d.code == "collision" for d in pair.sample(0).diagnostics)
    with pytest.raises(LimbError, match="arm"):
        replace(pair, strict_clearance=True).sample(0)


def test_two_hand_grip_uses_distinct_prop_anchors_and_rejects_an_ambiguous_grip():
    right_profile, left_profile = profiles()
    right, left = (Motion(p, HUMAN, (Action("grasp", duration=2),)) for p in (right_profile, left_profile))
    prop = Prop(
        "tray",
        TransformTrack.constant(Frame()),
        (Anchor("right", right.sample(1).hand.frame), Anchor("left", left.sample(1).hand.frame)),
    )
    pair = grip_prop(right, left, prop, right_anchor="right", left_anchor="left", start=0.8, end=1.3)
    for time in (1.3, 0.8, 1):
        sample = pair.sample(time)
        assert sample.right.hand.frame.origin.distance(prop.frame("right", time).origin) < 1e-8
        assert sample.left.hand.frame.origin.distance(prop.frame("left", time).origin) < 1e-8
    with pytest.raises(LimbError, match="distinct"):
        grip_prop(right, left, prop, right_anchor="right", left_anchor="right", start=0.8, end=1.3)


@pytest.mark.parametrize(
    "a,b,c,d",
    [
        (Vec3(), Vec3(1, 0, 0), Vec3(0.5, 1, 0), Vec3(0.5, 2, 0)),
        (Vec3(), Vec3(1, 0, 0), Vec3(0.5, -2, 0), Vec3(0.5, -1, 0)),
        (Vec3(), Vec3(1, 0, 0), Vec3(2, -1, 0), Vec3(2, 1, 0)),
        (Vec3(1, 0, 0), Vec3(2, 0, 0), Vec3(), Vec3()),
    ],
)
def test_segment_distance_is_symmetric_under_endpoints_and_argument_order(a, b, c, d):
    value = capsule_distance(a, b, c, d)
    assert value == pytest.approx(1)
    assert capsule_distance(b, a, c, d) == pytest.approx(value)
    assert capsule_distance(c, d, a, b) == pytest.approx(value)


def test_crossed_recipe_uses_torso_span_when_arm_proportions_change():
    right = ArmProfile(shoulder=Vec3(0.8, 0, 0), forearm=0.7)
    left = ArmProfile(shoulder=Vec3(-0.8, 0, 0), forearm=0.7, side="left")
    pose = crossed_arms(right, left).sample(1.5)
    assert pose.right.arm.wrist.x < 0 < pose.left.arm.wrist.x

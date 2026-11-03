"""Wrist orientation recovery preserves authored winding and both Euler representations."""

import math

import pytest

from srstudio.limbs import HUMAN, ArmProfile, HandControl, Quaternion, Vec3, hand_pose
from srstudio.limbs.motion import Action, Motion


@pytest.mark.parametrize(
    'twist', [math.pi, -math.pi, math.pi + 0.2, -math.pi - 0.2, math.tau, -math.tau, 5 * math.tau + 0.1]
)
@pytest.mark.parametrize('flex,deviation', [(0, 0), (0.7, -0.4), (2, 0.2), (math.pi / 2, 0.3), (-math.pi / 2, -0.3)])
def test_solved_orientation_retains_authored_winding_at_pi_and_whole_turns(twist, flex, deviation):
    profile = ArmProfile(twist_limit=(-40, 40), flex_limit=(-3, 3), deviation_limit=(-1, 1))
    motion = Motion(profile, HUMAN)
    control = HandControl(forearm_twist=twist, wrist_flex=flex, wrist_deviation=deviation)
    base = motion.sample(0)
    expected = hand_pose(HUMAN, control, base.arm.frame)
    _, hand, restored = motion._pose(0, base.arm.wrist, control, base.arm.elbow, expected.frame.rotation)
    assert restored.forearm_twist == pytest.approx(twist, abs=1e-8)
    assert restored.wrist_flex == pytest.approx(flex, abs=1e-8)
    assert restored.wrist_deviation == pytest.approx(deviation, abs=1e-8)
    assert hand.normal.distance(expected.normal) < 1e-8


def test_authored_full_turn_gesture_is_random_access_and_does_not_take_a_shortcut():
    motion = Motion(
        ArmProfile(twist_limit=(-math.tau, math.tau)),
        HUMAN,
        (Action('point', duration=2, control=HandControl(forearm_twist=math.tau)),),
    )
    times = [0.6, 0.4, 0.8, 0.6]
    samples = [motion.sample(t) for t in times]
    assert samples[0] == samples[-1]
    assert 0 < samples[1].control.forearm_twist < samples[0].control.forearm_twist < math.tau
    assert samples[2].control.forearm_twist == pytest.approx(math.tau)


def test_pi_representation_respects_a_one_sided_twist_limit():
    motion = Motion(ArmProfile(twist_limit=(0, math.pi)), HUMAN)
    base = motion.sample(0)
    control = HandControl(forearm_twist=math.pi)
    orientation = Quaternion.axis_angle(Vec3(0, 1, 0), -math.pi)
    _, _, restored = motion._pose(0, base.arm.wrist, control, base.arm.elbow, orientation, True)
    assert restored.forearm_twist == pytest.approx(math.pi)


def test_large_finite_winding_reference_does_not_overflow_candidate_selection():
    motion = Motion(ArmProfile(twist_limit=(-40, 40)), HUMAN)
    base = motion.sample(0)
    reference = HandControl(forearm_twist=1e200)
    _, hand, control = motion._pose(0, base.arm.wrist, reference, base.arm.elbow, Quaternion(), True)
    assert -40 <= control.forearm_twist <= 40
    assert hand.normal.distance(base.arm.frame.rotation.rotate(Vec3(0, 0, 1))) < 1e-8


def test_rotation_on_the_principal_branch_keeps_its_decomposition_bit_for_bit():
    # No turn is needed here, so recovery must return the principal angles themselves: rewriting -0.0 as 0.0
    # describes the same rotation but changes every saved and hashed sample that carries it.
    motion = Motion(ArmProfile(), HUMAN)
    base = motion.sample(0)
    rotation = Quaternion.axis_angle(Vec3(0, 1, 0), 0.3)
    x, y, z = (rotation.rotate(v) for v in (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)))
    principal = (math.atan2(z.x, z.z), math.asin(-z.y), math.atan2(x.y, y.y))
    _, _, restored = motion._pose(0, base.arm.wrist, HandControl(), base.arm.elbow, rotation, True)
    actual = (restored.forearm_twist, restored.wrist_flex, restored.wrist_deviation)
    assert actual == principal
    assert [math.copysign(1, a) for a in actual] == [math.copysign(1, p) for p in principal]

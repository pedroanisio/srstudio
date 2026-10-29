"""Spatial limb contracts: lengths, handedness, joint limits and projection are independent of drawing styles."""

import math
from dataclasses import replace

import pytest

from srstudio.limbs.constraints import forward, hand_pose, reach
from srstudio.limbs.math3d import Frame, Quaternion, Vec3
from srstudio.limbs.model import GRIPPER, HUMAN, MITTEN, PAW, THREE_FINGER, ArmProfile, HandControl, LimbError
from srstudio.limbs.projection import Affine, Camera


def test_rotation_and_frame_roundtrip():
    q = Quaternion.axis_angle(Vec3(0, 0, 1), math.pi / 2)
    assert q.rotate(Vec3(1, 0, 0)).distance(Vec3(0, 1, 0)) < 1e-12
    f = Frame(Vec3(1, 2, 3), q)
    p = Vec3(2, 4, 6)
    assert f.inverse_point(f.point(p)).distance(p) < 1e-12
    assert q.slerp(-q, 0.5).rotate(p).distance(q.rotate(p)) < 1e-12


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, "x"])
def test_coordinates_reject_nonfinite_and_nonnumeric_values(bad):
    with pytest.raises(LimbError):
        Vec3(bad, 0, 0)


@pytest.mark.parametrize("target", [Vec3(1, 1, 0), Vec3(-0.4, 1.1, 1), Vec3(0.01, 0, 0), Vec3(0, 1.999, 0)])
def test_spatial_ik_preserves_bone_lengths_and_reaches_target(target):
    profile = ArmProfile(upper=1, forearm=1, elbow_limit=(0, math.pi))
    pose = reach(profile, target, pole=Vec3(1, 0, 0))
    assert pose.shoulder.distance(pose.elbow) == pytest.approx(1)
    assert pose.elbow.distance(pose.wrist) == pytest.approx(1)
    assert pose.wrist.distance(target) < 1e-8
    assert pose.residual < 1e-8


def test_unreachable_target_raises_a_diagnostic_unless_clamping_is_explicit():
    p = ArmProfile(upper=1, forearm=1)
    with pytest.raises(LimbError, match="reach") as error:
        reach(p, Vec3(3, 0, 0))
    assert error.value.code == "unreachable"
    pose = reach(p, Vec3(3, 0, 0), policy="clamp")
    assert pose.wrist.x == pytest.approx(2)
    assert pose.residual == pytest.approx(1)
    assert pose.diagnostics[0].code == "unreachable"


def test_folded_and_collinear_targets_have_deterministic_solutions():
    p = ArmProfile(upper=1, forearm=1, elbow_limit=(0, math.pi))
    a = reach(p, Vec3(0, 0, 0), pole=Vec3(1, 0, 0))
    assert a.wrist.distance(Vec3(0, 0, 0)) < 1e-8
    assert a.elbow.distance(a.shoulder) == pytest.approx(1)
    assert reach(p, Vec3(0, 0, 0), pole=Vec3(1, 0, 0)) == a
    b = reach(p, Vec3(0, 1, 0), pole=Vec3(0, 2, 0))
    assert b.wrist.y == pytest.approx(1)


def test_elbow_limits_are_enforced_and_forward_kinematics_roundtrips():
    p = ArmProfile(upper=1, forearm=1, elbow_limit=(0, math.pi / 2))
    with pytest.raises(LimbError) as error:
        reach(p, Vec3(0, 0.1, 0))
    assert error.value.code == "joint-limit"
    pose = forward(p, shoulder_rotation=Quaternion.axis_angle(Vec3(0, 0, 1), 0.4), elbow=0.7)
    solved = reach(p, pose.wrist, pole=pose.elbow)
    assert solved.elbow.distance(pose.elbow) < 1e-8


def test_mirroring_preserves_anatomy_and_moves_the_elbow_to_the_opposite_side():
    p = ArmProfile(upper=1, forearm=0.8)
    a = reach(p, Vec3(0.5, 1, -0.3), pole=Vec3(1, 0, 0))
    b = reach(replace(p, side="left"), Vec3(-0.5, 1, -0.3), pole=Vec3(-1, 0, 0))
    assert b.elbow.distance(a.elbow.mirror()) < 1e-8
    assert b.wrist.distance(a.wrist.mirror()) < 1e-8


@pytest.mark.parametrize("profile,count", [(HUMAN, 5), (THREE_FINGER, 3), (MITTEN, 2), (PAW, 4), (GRIPPER, 2)])
def test_hand_topologies_preserve_each_phalanx_length(profile, count):
    control = HandControl(curl=0.7, spread=0.3, cup=0.2, opposition=0.8)
    pose = hand_pose(profile, control, Frame())
    assert len(pose.digits) == count
    for digit, anatomy in zip(pose.digits, profile.digits, strict=True):
        assert len(digit.points) == len(anatomy.lengths) + 1
        assert [a.distance(b) for a, b in zip(digit.points, digit.points[1:], strict=False)] == pytest.approx(
            anatomy.lengths
        )


def test_finger_overrides_and_thumb_opposition_are_independent_and_mirrorable():
    a = hand_pose(HUMAN, HandControl(curl=0.7, curls=(("index", 0.0),)), Frame())
    b = hand_pose(HUMAN, HandControl(curl=0.7), Frame())
    assert a.digit("index") != b.digit("index")
    assert a.digit("ring") == b.digit("ring")
    left = hand_pose(HUMAN, HandControl(curl=0.7, curls=(("index", 0.0),)), Frame(), side="left")
    for ra, rb in zip(a.digits, left.digits, strict=True):
        assert all(x.mirror().distance(y) < 1e-9 for x, y in zip(ra.points, rb.points, strict=True))


def test_positive_curl_bends_fingers_toward_the_palm_surface_not_the_back_of_the_hand():
    hand = hand_pose(HUMAN, HandControl(curl=0.5), Frame())
    finger = hand.digit("middle")
    assert (finger.points[1] - finger.points[0]).dot(hand.normal) > 0
    a = hand_pose(HUMAN, HandControl(curl=0.5, opposition=0), Frame()).digit("thumb")
    b = hand_pose(HUMAN, HandControl(curl=0.5, opposition=1), Frame()).digit("thumb")
    assert b.points[-1].x < a.points[-1].x


@pytest.mark.parametrize("changes", [{"upper": 0}, {"forearm": -1}, {"side": "other"}, {"elbow_limit": (2, 1)}])
def test_bad_profiles_are_rejected(changes):
    with pytest.raises(LimbError):
        ArmProfile(**changes)


@pytest.mark.parametrize(
    "changes", [{"curl": -0.1}, {"cup": 2}, {"curls": (("index", 2),)}, {"wrist_flex": float("nan")}]
)
def test_bad_controls_are_rejected(changes):
    with pytest.raises(LimbError):
        HandControl(**changes)


def test_perspective_foreshortening_uses_depth_and_parent_transform_exactly_once():
    camera = Camera(projection="perspective", distance=10, focal=10, scale=100, origin=(200, 300))
    assert camera.project(Vec3(1, 0, 0)).xy == pytest.approx((300, 300))
    assert camera.project(Vec3(1, 0, 5)).xy == pytest.approx((400, 300))
    parent = Affine(a=0, b=2, c=-2, d=0, e=100, f=200)
    local = camera.project(Vec3(1, 0, 5), parent=parent)
    assert parent.point(local.xy) == pytest.approx((400, 300))
    with pytest.raises(LimbError, match="near"):
        camera.project(Vec3(0, 0, 10))
    with pytest.raises(LimbError, match="singular"):
        Affine(a=0, d=0).inverse()


def test_camera_and_hand_frame_rotation_are_spatial():
    camera = Camera(scale=100)
    front = camera.project(Vec3(1, 0, 0)).xy
    turned = camera.project(Vec3(1, 0, 0), frame=Frame(rotation=Quaternion.axis_angle(Vec3(0, 1, 0), math.pi / 2)))
    assert front[0] == 100 and abs(turned.xy[0]) < 1e-10


def test_reach_frames_do_not_roll_when_a_foreshortened_arm_crosses_a_reference_axis_threshold():
    profile = ArmProfile(upper=1, forearm=1)
    before = reach(profile, Vec3(0, 0, 1.8999), pole=Vec3(0, 1, 0))
    after = reach(profile, Vec3(0, 0, 1.9001), pole=Vec3(0, 1, 0))
    a = before.frame.rotation.rotate(Vec3(1, 0, 0))
    b = after.frame.rotation.rotate(Vec3(1, 0, 0))
    assert a.dot(b) > 0.999

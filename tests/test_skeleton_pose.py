"""SkeletonPose: canonical rotations on a profile, forward kinematics, projection, blending and additive layers."""

import random

import pytest

from srstudio import skeleton as sk
from srstudio.limbs import Affine, Camera
from srstudio.limbs.math3d import Frame, Quaternion, Vec3
from srstudio.skeleton._rotation import angle_of

REAL = sk.preset("realistic")
TOON = sk.preset("cartoon")
STICK = sk.preset("stick")


def close(a: Vec3, b: Vec3, tolerance: float = 1e-9) -> bool:
    return a.distance(b) < tolerance


def random_values(profile, rng, share=0.6):
    values = {}
    for key in profile.controls:
        if key.split(".")[1] in ("right", "up", "forward"):
            continue
        low, high = profile.limits_of(key)
        values[key] = rng.uniform(low * share, high * share)
    return values


def test_a_pose_keeps_its_values_sorted_and_drops_zeros():
    pose = sk.pose(REAL, {"neck.nod_down_up": 0.1, "hips.front_back": 0.2, "jaw.close": 0.0})
    assert pose.values == (("hips.front_back", 0.2), ("neck.nod_down_up", 0.1))
    assert pose.value("neck.nod_down_up") == 0.1 and pose.value("jaw.close") == 0.0
    assert pose.as_dict() == {"hips.front_back": 0.2, "neck.nod_down_up": 0.1}
    assert sk.SkeletonPose(pose.root, tuple(reversed(pose.values))) == pose


def test_the_default_root_stands_on_the_ground():
    assert sk.pose(REAL).root == REAL.standing_root()
    assert REAL.standing_root().origin.y == pytest.approx(-REAL.pelvis_height)
    world = sk.world(REAL, sk.pose(REAL))
    assert world["left_foot"].origin.y == pytest.approx(-REAL.length("ankle"))


def test_a_pose_refuses_every_control_out_of_limit_with_its_value():
    low, high = REAL.limits_of("head.turn_left_right")
    with pytest.raises(sk.JointLimitError) as caught:
        sk.pose(REAL, {"head.turn_left_right": high + 1, "jaw.close": 2.0, "neck.nod_down_up": 0.0})
    found = caught.value.violations
    assert [v.key for v in found] == ["head.turn_left_right", "jaw.close"]
    assert found[0].value == high + 1 and (found[0].low, found[0].high) == (low, high)
    report = caught.value.to_dict()
    assert report["code"] == "skeleton.limit" and report["actual"][0][0] == "head.turn_left_right"


def test_clamping_is_opt_in():
    _, high = REAL.limits_of("head.turn_left_right")
    pose = sk.pose(REAL, {"head.turn_left_right": high + 1, "jaw.close": 0.0}, clamp=True)
    assert pose.value("head.turn_left_right") == high


def test_a_profile_narrower_than_the_canon_decides_the_limit():
    narrow = sk.SkeletonProfile("n", REAL.proportions, limits=(("jaw.close", (-0.1, 0.0)),))
    with pytest.raises(sk.JointLimitError):
        sk.pose(narrow, {"jaw.close": -0.2})
    assert sk.pose(REAL, {"jaw.close": -0.2}).value("jaw.close") == -0.2


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ({"tail.wag": 0.1}, "skeleton.unknown"),
        ({"jaw.close": -0.1}, "skeleton.absent"),
        ({"head.turn_left_right": "a"}, "skeleton.schema"),
        ({"head.turn_left_right": True}, "skeleton.schema"),
        ({"head.turn_left_right": float("nan")}, "skeleton.schema"),
    ],
)
def test_a_bad_control_is_a_typed_error(values, code):
    with pytest.raises(sk.SkeletonError) as caught:
        sk.pose(STICK, values)
    assert caught.value.to_dict()["code"] == code


@pytest.mark.parametrize(
    "build",
    [
        lambda: sk.SkeletonPose("root"),
        lambda: sk.SkeletonPose(Frame(Vec3(2000, 0, 0))),
        lambda: sk.SkeletonPose(Frame(), [("jaw.close", 0.1)]),
        lambda: sk.SkeletonPose(Frame(), (("jaw.close",),)),
        lambda: sk.SkeletonPose(Frame(), (("jaw.close", 0.1), ("jaw.close", 0.2))),
        lambda: sk.SkeletonPose(Frame(), (("tail.wag", 0.1),)),
        lambda: sk.SkeletonPose(Frame(), ((1, 0.1),)),
        lambda: sk.SkeletonPose(Frame(), (("jaw.close", "x"),)),
    ],
)
def test_a_malformed_pose_record_is_refused(build):
    with pytest.raises(sk.SkeletonError):
        build()


def test_value_of_an_unknown_key_is_typed():
    with pytest.raises(sk.SkeletonError):
        sk.pose(REAL).value("tail.wag")


def test_world_holds_only_the_joints_the_character_has():
    assert len(sk.world(REAL, sk.pose(REAL))) == 55
    held = sk.world(STICK, sk.pose(STICK))
    assert set(held) == {joint.name for joint in STICK.joints}
    assert "jaw" not in held


def test_the_t_pose_matches_the_offsets():
    world = sk.world(REAL, sk.pose(REAL, root=Frame()))
    assert close(world["hips"].origin, Vec3())
    assert close(world["right_lower_leg"].origin, REAL.offset("right_upper_leg") + REAL.offset("right_lower_leg"))
    assert world["left_hand"].origin.x < -0.5 < 0.5 < world["right_hand"].origin.x


def test_the_root_frame_carries_the_whole_figure():
    turn = Quaternion.axis_angle(Vec3(0, 1, 0), 0.7)
    root = Frame(Vec3(1, -2, 3), turn)
    moved = sk.world(REAL, sk.pose(REAL, {"neck.nod_down_up": 0.2}, root=root))
    still = sk.world(REAL, sk.pose(REAL, {"neck.nod_down_up": 0.2}, root=Frame()))
    for name, frame in still.items():
        assert close(moved[name].origin, root.point(frame.origin))
        assert angle_of(moved[name].rotation.inverse() * (turn * frame.rotation)) < 1e-9


def test_the_hips_channels_apply_inside_the_root():
    world = sk.world(REAL, sk.pose(REAL, {"hips.up": 0.1, "hips.right": 0.2, "hips.forward": -0.3}, root=Frame()))
    assert close(world["hips"].origin, Vec3(0.2, -0.1, -0.3))


@pytest.mark.parametrize(
    ("key", "value", "joint", "axis", "sign"),
    [
        ("neck.nod_down_up", -0.4, "head", "z", 1),  # negative nods the head forward
        ("left_upper_leg.front_back", -1.0, "left_lower_leg", "z", 1),  # negative lifts the knee forward
        ("right_upper_leg.front_back", -1.0, "right_lower_leg", "z", 1),
        ("right_lower_leg.stretch", -1.0, "right_foot", "z", -1),  # a knee bends backward
        ("left_lower_leg.stretch", -1.0, "left_foot", "z", -1),
        ("right_lower_arm.stretch", -1.0, "right_hand", "z", 1),  # an elbow bends forward
        ("left_lower_arm.stretch", -1.0, "left_hand", "z", 1),
        ("right_upper_arm.down_up", -1.0, "right_lower_arm", "y", 1),  # negative lowers the arm, y points down
        ("left_upper_arm.down_up", -1.0, "left_lower_arm", "y", 1),
        ("right_upper_arm.front_back", -1.0, "right_lower_arm", "z", 1),
        ("left_upper_arm.front_back", -1.0, "left_lower_arm", "z", 1),
    ],
)
def test_a_control_moves_the_body_the_way_its_name_says(key, value, joint, axis, sign):
    rest = sk.world(REAL, sk.pose(REAL, root=Frame()))[joint].origin
    moved = sk.world(REAL, sk.pose(REAL, {key: value}, root=Frame()))[joint].origin
    assert (getattr(moved, axis) - getattr(rest, axis)) * sign > 0.01


def test_bones_keep_their_lengths_in_any_pose():
    rng = random.Random(3)
    for profile in (REAL, TOON, STICK):
        for _ in range(10):
            world = sk.world(profile, sk.pose(profile, random_values(profile, rng)))
            for joint in profile.joints[1:]:
                length = world[joint.parent].origin.distance(world[joint.name].origin)
                assert length == pytest.approx(profile.offset(joint.name).length, abs=1e-9)


def test_tips_follow_their_bones():
    pose = sk.pose(STICK, {"left_middle_proximal.stretched": -0.4})
    world, tips = sk.world(STICK, pose), sk.tips(STICK, pose)
    assert set(tips) >= {"head", "left_middle_intermediate", "right_thumb_intermediate"}
    assert "left_toes" not in tips
    frame = world["left_middle_intermediate"]
    assert close(tips["left_middle_intermediate"], frame.point(STICK.tip("left_middle_intermediate")))


def test_projection_goes_through_the_limbs_camera():
    pose = sk.pose(REAL, root=Frame(Vec3(0, -1, 0)))
    camera = Camera(origin=(540, 1600), scale=700)
    shown = sk.project(REAL, pose, camera)
    assert shown["hips"].xy == pytest.approx((540, 1600 - 700))
    assert shown["head.tip"].xy[1] < shown["head"].xy[1]
    assert "jaw" in shown and "spine.tip" not in shown
    parent = Affine(e=100)
    moved = sk.project(REAL, pose, camera, parent=parent)
    assert moved["hips"].xy == pytest.approx((440, 900))


def test_perspective_projection_refuses_a_point_behind_the_camera():
    pose = sk.pose(REAL, root=Frame(Vec3(0, -1, 20)))
    with pytest.raises(sk.SkeletonError) as caught:
        sk.project(REAL, pose, Camera(projection="perspective", distance=5))
    assert caught.value.to_dict()["code"] == "skeleton.mismatch"


def test_world_rechecks_the_pose_against_this_profile():
    wide = sk.pose(REAL, {"jaw.close": -0.3})
    with pytest.raises(sk.SkeletonError) as caught:
        sk.world(STICK, wide)
    assert caught.value.to_dict()["code"] == "skeleton.absent"
    narrow = sk.SkeletonProfile("n", REAL.proportions, limits=(("jaw.close", (-0.1, 0.0)),))
    with pytest.raises(sk.JointLimitError):
        sk.world(narrow, wide)


def test_add_layers_deltas_onto_a_base():
    base = sk.rest_pose(REAL)
    layered = sk.add(REAL, base, {"neck.nod_down_up": 0.1, "left_upper_arm.down_up": 0.05})
    assert layered.value("neck.nod_down_up") == 0.1
    assert layered.value("left_upper_arm.down_up") == pytest.approx(base.value("left_upper_arm.down_up") + 0.05)
    assert layered.root == base.root


def test_add_refuses_a_step_past_the_limit_unless_clamped():
    _, high = REAL.limits_of("jaw.close")
    base = sk.pose(REAL, {"jaw.close": high})
    with pytest.raises(sk.JointLimitError):
        sk.add(REAL, base, {"jaw.close": 0.5})
    assert sk.add(REAL, base, {"jaw.close": 0.5}, clamp=True).value("jaw.close") == high


def test_rest_pose_reads_the_profile():
    pose = sk.rest_pose(TOON)
    assert pose.as_dict() == dict(TOON.rest)
    root = Frame(Vec3(1, 0, 0))
    assert sk.rest_pose(TOON, root=root).root == root


def test_blend_ends_are_the_poses_themselves():
    rng = random.Random(5)
    a = sk.pose(REAL, random_values(REAL, rng))
    b = sk.pose(REAL, random_values(REAL, rng), root=Frame(Vec3(1, -1, 0)))
    assert sk.blend(REAL, a, b, 0) == a
    assert sk.blend(REAL, a, b, 1) == b


def test_blend_of_a_one_control_joint_is_linear():
    a = sk.pose(REAL, {"right_lower_leg.stretch": -1.0, "jaw.close": -0.1})
    b = sk.pose(REAL, {"right_lower_leg.stretch": -0.4, "jaw.close": -0.3})
    mid = sk.blend(REAL, a, b, 0.5)
    assert mid.value("right_lower_leg.stretch") == pytest.approx(-0.7)
    assert mid.value("jaw.close") == pytest.approx(-0.2)


def test_blend_slerps_a_full_joint_rather_than_its_angles():
    a = sk.pose(REAL, {"right_upper_arm.down_up": -1.2})
    b = sk.pose(REAL, {"right_upper_arm.front_back": -1.2})
    mid = sk.blend(REAL, a, b, 0.5)
    q = {
        key: mid.value(key)
        for key in ("right_upper_arm.down_up", "right_upper_arm.front_back", "right_upper_arm.twist_in_out")
    }
    assert q["right_upper_arm.twist_in_out"] != pytest.approx(0, abs=1e-3)
    mid_world = sk.world(REAL, mid)["right_upper_arm"].rotation
    a_world = sk.world(REAL, a)["right_upper_arm"].rotation
    b_world = sk.world(REAL, b)["right_upper_arm"].rotation
    assert angle_of(mid_world.inverse() * a_world.slerp(b_world, 0.5)) < 1e-9


def test_blend_moves_the_root_and_translations_on_a_straight_line():
    a = sk.pose(REAL, {"hips.up": 0.1}, root=Frame(Vec3(0, -1, 0)))
    b = sk.pose(REAL, {"hips.up": 0.3}, root=Frame(Vec3(2, -1, 0), Quaternion.axis_angle(Vec3(0, 1, 0), 1.0)))
    mid = sk.blend(REAL, a, b, 0.25)
    assert mid.value("hips.up") == pytest.approx(0.15)
    assert mid.root.origin == Vec3(0.5, -1, 0)
    assert angle_of(mid.root.rotation.inverse() * Quaternion.axis_angle(Vec3(0, 1, 0), 0.25)) < 1e-9


def test_a_blend_stays_on_the_nearest_branch_past_a_right_angle():
    a = sk.pose(REAL, {"right_upper_arm.front_back": -2.2})
    b = sk.pose(REAL, {"right_upper_arm.front_back": -2.0})
    assert sk.blend(REAL, a, b, 0.5).value("right_upper_arm.front_back") == pytest.approx(-2.1)


def test_a_two_control_joint_keeps_what_it_can_hold():
    a = sk.pose(REAL, {"left_shoulder.down_up": 0.4})
    b = sk.pose(REAL, {"left_shoulder.front_back": 0.25})
    mid = sk.blend(REAL, a, b, 0.5)
    assert mid.value("left_shoulder.down_up") == pytest.approx(0.2, abs=0.01)
    assert mid.value("left_shoulder.front_back") == pytest.approx(0.125, abs=0.01)


def test_blend_refuses_an_amount_outside_the_unit_and_a_result_past_a_limit():
    a, b = sk.pose(REAL), sk.pose(REAL, {"jaw.close": -0.1})
    for amount in (-0.1, 1.1, float("nan"), True):
        with pytest.raises(sk.SkeletonSchemaError):
            sk.blend(REAL, a, b, amount)
    narrow = sk.SkeletonProfile(
        "n",
        REAL.proportions,
        limits=(
            ("head.nod_down_up", (-0.3, 0.3)),
            ("head.tilt_left_right", (-0.01, 0.01)),
            ("head.turn_left_right", (-0.6, 0.6)),
        ),
    )
    c, d = sk.pose(narrow, {"head.nod_down_up": 0.3}), sk.pose(narrow, {"head.turn_left_right": 0.6})
    with pytest.raises(sk.JointLimitError):
        sk.blend(narrow, c, d, 0.5)
    assert abs(sk.blend(narrow, c, d, 0.5, clamp=True).value("head.tilt_left_right")) <= 0.01


def test_a_pose_is_a_hashable_immutable_value():
    pose = sk.pose(REAL, {"head.turn_left_right": 0.2})
    assert hash(pose) == hash(sk.pose(REAL, {"head.turn_left_right": 0.2}))
    assert "head.turn_left_right" in repr(pose)
    with pytest.raises(AttributeError):
        pose.root = Frame()


@pytest.mark.parametrize(
    "call", [lambda: sk.pose(REAL, [("head.turn_left_right", 0.1)]), lambda: sk.add(REAL, sk.pose(REAL), [])]
)
def test_values_and_deltas_are_mappings(call):
    with pytest.raises(sk.SkeletonSchemaError):
        call()

"""The bridges: a SkeletonPose feeds what body and limbs adapters already draw, and comes back where that is defined."""

import math
import random
from pathlib import Path

import pytest

from srstudio import body, limbs
from srstudio import skeleton as sk
from srstudio.limbs.geometry import project_pose
from srstudio.limbs.math3d import Frame, Quaternion, Vec3
from srstudio.limbs.model import HandControl
from srstudio.limbs.motion import Sample
from srstudio.skeleton._rotation import angle_of

REAL = sk.preset("realistic")
TOON = sk.preset("cartoon")
STICK = sk.preset("stick")
SIDES = ("left", "right")
FLOOR = Frame()


def close(a: Vec3, b: Vec3, tolerance: float = 1e-6) -> bool:
    return a.distance(b) < tolerance


def turned(a: Quaternion, b: Quaternion, tolerance: float = 1e-6) -> bool:
    return angle_of(a.inverse() * b) < tolerance


def same_pose(a: sk.SkeletonPose, b: sk.SkeletonPose, tolerance: float = 1e-6) -> bool:
    keys = {*a.as_dict(), *b.as_dict()}
    return close(a.root.origin, b.root.origin, tolerance) and all(
        abs(a.value(key) - b.value(key)) < tolerance for key in keys
    )


def crouch(profile, drop=0.08):
    """Both feet flat under the hips, knees bent by lowering the root through the legs."""
    thigh, shin = profile.length("thigh"), profile.length("shin")
    reach = thigh + shin - drop
    knee = math.acos((reach**2 - thigh**2 - shin**2) / (2 * thigh * shin))
    hip = math.atan2(shin * math.sin(knee), thigh + shin * math.cos(knee))
    values = {}
    for side in SIDES:
        values[f"{side}_upper_leg.front_back"] = -hip
        values[f"{side}_lower_leg.stretch"] = -knee
        values[f"{side}_foot.up_down"] = hip - knee
    return sk.pose(profile, values, root=Frame(Vec3(0, -profile.pelvis_height + drop, 0)))


def test_a_body_pose_stands_on_the_ground():
    pose = crouch(REAL)
    shown = sk.to_body_pose(REAL, pose)
    world = sk.world(REAL, pose)
    assert [leg.side for leg in shown.legs] == ["left", "right"]
    for leg in shown.legs:
        assert close(leg.hip, world[f"{leg.side}_upper_leg"].origin)
        assert close(leg.knee, world[f"{leg.side}_lower_leg"].origin)
        assert close(leg.ankle, world[f"{leg.side}_foot"].origin)
        assert leg.sole.origin.y == pytest.approx(0, abs=1e-9)
        assert leg.planted
        assert leg.knee_angle > 0.1
    assert close(shown.shoulders[0].origin, world["left_upper_arm"].origin)
    assert close(shown.shoulders[1].origin, world["right_upper_arm"].origin)
    assert shown.support_margin > 0
    assert len(shown.support_polygon) >= 4


def test_the_body_root_sits_between_the_legs():
    pose = crouch(REAL)
    shown = sk.to_body_pose(REAL, pose, time=1.5)
    assert shown.time == 1.5
    width = sk.body_profile(REAL).hip_width
    for leg, sign in zip(shown.legs, (-1, 1), strict=True):
        assert close(leg.hip, shown.root.point(Vec3(sign * width / 2, 0, 0)))
    assert close(shown.torso.origin, shown.root.origin)


def test_a_compiled_body_plan_comes_through_the_skeleton_unchanged():
    profile = sk.body_profile(REAL)
    height = REAL.pelvis_height - profile.ankle_height * 0 - 0.04
    score = body.BodyScore(
        duration=2,
        roots=(
            body.BodyKey(0, Frame(Vec3(0, -height + REAL.offset("right_upper_leg").y, 0))),
            body.BodyKey(
                2,
                Frame(Vec3(0.02, -height + REAL.offset("right_upper_leg").y, 0.02)),
                Quaternion.axis_angle(Vec3(1, 0, 0), 0.2),
            ),
        ),
        stance=(
            body.FootAnchor("left", Frame(Vec3(-profile.hip_width / 2, 0, 0))),
            body.FootAnchor("right", Frame(Vec3(profile.hip_width / 2, 0, 0))),
        ),
        profile=profile,
    )
    plan = body.compile_body(score)
    for time in (0.0, 0.7, 2.0):
        sampled = plan.sample(time)
        through = sk.from_body_pose(REAL, sampled)
        again = sk.to_body_pose(REAL, through, time=time)
        assert close(again.root.origin, sampled.root.origin)
        assert turned(again.root.rotation, sampled.root.rotation)
        assert turned(again.torso.rotation, sampled.torso.rotation)
        for ours, theirs in zip(again.legs, sampled.legs, strict=True):
            assert close(ours.hip, theirs.hip)
            assert close(ours.knee, theirs.knee)
            assert close(ours.ankle, theirs.ankle)
            assert close(ours.sole.origin, theirs.sole.origin)
            assert turned(ours.sole.rotation, theirs.sole.rotation)
            assert ours.knee_angle == pytest.approx(theirs.knee_angle, abs=1e-6)
            assert ours.foot_yaw == pytest.approx(theirs.foot_yaw, abs=1e-6)


def test_a_body_pose_round_trips_to_the_same_skeleton_pose():
    pose = crouch(REAL)
    back = sk.from_body_pose(REAL, sk.to_body_pose(REAL, pose), base=pose)
    assert same_pose(back, pose)


def test_from_body_pose_keeps_the_rest_of_the_base():
    pose = crouch(REAL)
    base = sk.pose(REAL, {"head.turn_left_right": 0.3, "left_lower_arm.stretch": -1.0, "hips.up": 0.1})
    back = sk.from_body_pose(REAL, sk.to_body_pose(REAL, pose), base=base)
    assert back.value("head.turn_left_right") == 0.3
    assert back.value("left_lower_arm.stretch") == -1.0
    assert back.value("hips.up") == 0.0  # the body root carries the hips


def test_a_lean_is_shared_along_the_spine_and_comes_back():
    values = {"spine.front_back": -0.1, "chest.front_back": -0.05, "upper_chest.left_right": 0.02}
    pose = sk.pose(REAL, {**crouch(REAL).as_dict(), **values}, root=crouch(REAL).root)
    shown = sk.to_body_pose(REAL, pose)
    world = sk.world(REAL, sk.from_body_pose(REAL, shown))
    assert turned(world["upper_chest"].rotation, shown.torso.rotation)


def test_a_slightly_straight_knee_past_zero_stays_on_its_side():
    pose = sk.pose(REAL, {"right_lower_leg.stretch": 0.03})
    shown = sk.to_body_pose(REAL, pose, planted=("left",))
    back = sk.from_body_pose(REAL, shown, base=pose)
    assert back.value("right_lower_leg.stretch") == pytest.approx(0.03, abs=1e-6)
    assert back.value("right_upper_leg.twist_in_out") == pytest.approx(0, abs=1e-6)


def test_a_straight_leg_takes_no_twist():
    pose = sk.pose(REAL)
    back = sk.from_body_pose(REAL, sk.to_body_pose(REAL, pose))
    assert same_pose(back, pose)


def test_a_straight_leg_in_line_with_the_hips_cannot_say_which_way_it_bends():
    shown = sk.to_body_pose(REAL, sk.pose(REAL))
    width = REAL.length("thigh") + REAL.length("shin")
    left, right = shown.legs
    knee = Vec3(left.hip.x - REAL.length("thigh"), left.hip.y, left.hip.z)
    ankle = Vec3(left.hip.x - width, left.hip.y, left.hip.z)
    sole = Frame(ankle + Vec3(0, REAL.length("ankle"), 0))
    bent = body.LegPose("left", left.hip, knee, ankle, sole, True, 0.0, 0.0, 0.0, 0.0)
    broken = body.BodyPose(0.0, shown.root, shown.torso, shown.shoulders, (bent, right), Vec3(), (), 0.0)
    with pytest.raises(sk.SkeletonBridgeError) as caught:
        sk.from_body_pose(REAL, broken)
    assert caught.value.to_dict()["code"] == "skeleton.ill-posed"


def test_a_raised_foot_leaves_one_planted():
    pose = sk.pose(REAL, {"right_upper_leg.front_back": -0.5, "right_lower_leg.stretch": -0.5})
    shown = sk.to_body_pose(REAL, pose)
    assert [leg.planted for leg in shown.legs] == [True, False]


def test_no_foot_down_has_no_body_pose():
    pose = sk.pose(REAL, root=Frame(Vec3(0, -3, 0)))
    with pytest.raises(sk.SkeletonBridgeError) as caught:
        sk.to_body_pose(REAL, pose)
    assert caught.value.to_dict()["code"] == "skeleton.support"
    assert sk.world(REAL, pose)  # flight is a pose; it only has no support record


@pytest.mark.parametrize("planted", [("left", "right"), ("middle",), ()])
def test_a_named_foot_must_really_be_planted(planted):
    pose = sk.pose(REAL, {"right_upper_leg.front_back": -0.5, "right_lower_leg.stretch": -0.5})
    with pytest.raises(sk.SkeletonBridgeError) as caught:
        sk.to_body_pose(REAL, pose, planted=planted)
    assert caught.value.to_dict()["code"] == "skeleton.support"


def test_a_character_with_no_legs_has_no_body_pose():
    legless = sk.SkeletonProfile("x", REAL.proportions, omit=("left_upper_leg",))
    with pytest.raises(sk.SkeletonBridgeError) as caught:
        sk.to_body_pose(legless, sk.pose(legless))
    assert caught.value.to_dict()["code"] == "skeleton.absent"
    with pytest.raises(sk.SkeletonBridgeError):
        sk.from_body_pose(legless, sk.to_body_pose(REAL, sk.pose(REAL)))


@pytest.mark.parametrize("name", ["hip", "thigh", "shin", "sole", "torso", "side"])
def test_a_body_pose_of_another_figure_is_a_mismatch(name):
    shown = sk.to_body_pose(REAL, crouch(REAL))
    left, right = shown.legs
    edits = {
        "hip": ({"hip": left.hip + Vec3(0.1, 0, 0)}, {}),
        "thigh": ({"knee": left.knee + Vec3(0, 0.1, 0)}, {}),
        "shin": ({"ankle": left.ankle + Vec3(0, 0.1, 0)}, {}),
        "sole": ({"sole": Frame(left.sole.origin + Vec3(0, 0.1, 0), left.sole.rotation)}, {}),
    }
    if name == "torso":
        broken = body.BodyPose(
            0.0,
            shown.root,
            Frame(shown.root.origin + Vec3(0.1, 0, 0), shown.torso.rotation),
            shown.shoulders,
            shown.legs,
            Vec3(),
            (),
            0.0,
        )
    elif name == "side":
        broken = body.BodyPose(0.0, shown.root, shown.torso, shown.shoulders, (right, left), Vec3(), (), 0.0)
    else:
        fields = {f: getattr(left, f) for f in left.__dataclass_fields__} | edits[name][0]
        broken = body.BodyPose(
            0.0, shown.root, shown.torso, shown.shoulders, (body.LegPose(**fields), right), Vec3(), (), 0.0
        )
    with pytest.raises(sk.SkeletonBridgeError) as caught:
        sk.from_body_pose(REAL, broken)
    assert caught.value.to_dict()["code"] == "skeleton.mismatch"


def test_from_body_pose_refuses_what_is_not_a_body_pose():
    with pytest.raises(sk.SkeletonBridgeError):
        sk.from_body_pose(REAL, object())


def test_a_body_profile_carries_the_lengths_body_needs():
    profile = sk.body_profile(TOON)
    assert isinstance(profile, body.BodyProfile)
    assert profile.thigh == TOON.length("thigh") and profile.shin == TOON.length("shin")
    assert profile.ankle_height == TOON.length("ankle")
    assert profile.hip_width == pytest.approx(2 * abs(TOON.offset("left_upper_leg").x))
    shown = sk.to_body_pose(TOON, crouch(TOON, 0.03))
    assert close(
        shown.torso.point(Vec3(0, -profile.torso_height, 0)),
        (shown.shoulders[0].origin + shown.shoulders[1].origin) / 2,
        1e-6,
    )
    assert sk.body_profile(STICK).toe > 0  # a character with no toes joint still has a foot to stand on


def test_an_arm_pose_reads_the_joints_it_names():
    pose = sk.pose(REAL, {"right_upper_arm.down_up": -0.6, "right_lower_arm.stretch": -1.2})
    arm = sk.to_arm_pose(REAL, pose, "right")
    world = sk.world(REAL, pose)
    assert close(arm.shoulder, world["right_upper_arm"].origin)
    assert close(arm.elbow, world["right_lower_arm"].origin)
    assert close(arm.wrist, world["right_hand"].origin)
    assert arm.elbow_angle == pytest.approx(1.2)
    assert arm.frame.origin == arm.wrist


@pytest.mark.parametrize("side", SIDES)
def test_an_arm_matches_what_limbs_solves_for_the_same_points(side):
    pose = sk.pose(REAL, {f"{side}_upper_arm.down_up": -0.9, f"{side}_lower_arm.stretch": -1.1})
    arm = sk.to_arm_pose(REAL, pose, side)
    solved = limbs.reach(sk.arm_profile(REAL, pose, side), arm.wrist, pole=arm.elbow)
    assert close(solved.elbow, arm.elbow)
    assert solved.elbow_angle == pytest.approx(arm.elbow_angle)
    assert turned(solved.frame.rotation, arm.frame.rotation)


@pytest.mark.parametrize("side", SIDES)
def test_an_arm_round_trips(side):
    rng = random.Random(9)
    for _ in range(25):
        values = {}
        for name in ("down_up", "front_back", "twist_in_out"):
            low, high = REAL.limits_of(f"{side}_upper_arm.{name}")
            values[f"{side}_upper_arm.{name}"] = rng.uniform(low * 0.5, high * 0.5)
        values[f"{side}_lower_arm.stretch"] = rng.uniform(-2.5, -0.1)
        values[f"{side}_lower_arm.twist_in_out"] = rng.uniform(-1, 1)
        values[f"{side}_shoulder.down_up"] = rng.uniform(-0.2, 0.4)
        values["chest.front_back"] = rng.uniform(-0.3, 0.1)
        pose = sk.pose(REAL, values)
        base = sk.pose(REAL, {k: v for k, v in values.items() if "upper_arm" not in k and "stretch" not in k})
        back = sk.from_arm_pose(REAL, base, side, sk.to_arm_pose(REAL, pose, side))
        assert same_pose(back, pose, 1e-5)


def test_a_straight_arm_round_trips():
    pose = sk.pose(REAL, {"left_upper_arm.down_up": -0.7})
    assert same_pose(sk.from_arm_pose(REAL, sk.pose(REAL), "left", sk.to_arm_pose(REAL, pose, "left")), pose)


def test_an_arm_solved_by_limbs_lands_on_the_skeleton():
    base = sk.pose(REAL)
    profile = sk.arm_profile(REAL, base, "right")
    world = sk.world(REAL, base)
    target = world["right_upper_arm"].origin + Vec3(0.3, 0.2, 0.25)
    pole = world["right_upper_arm"].origin + Vec3(0.2, 0, -0.3)
    solved = limbs.reach(profile, target, pole=pole)
    landed = sk.from_arm_pose(REAL, base, "right", solved)
    assert close(sk.world(REAL, landed)["right_hand"].origin, solved.wrist)
    assert close(sk.world(REAL, landed)["right_lower_arm"].origin, solved.elbow)


@pytest.mark.parametrize("side", SIDES)
def test_an_arm_profile_carries_the_canonical_range_in_limbs_controls(side):
    profile = sk.arm_profile(REAL, sk.pose(REAL), side)
    sign = 1 if side == "right" else -1
    assert (
        profile.side == side and profile.upper == REAL.length("upper_arm") and profile.forearm == REAL.length("forearm")
    )
    assert profile.elbow_limit == pytest.approx((0, -REAL.limits_of(f"{side}_lower_arm.stretch")[0]))
    low, high = REAL.limits_of(f"{side}_lower_arm.twist_in_out")
    assert profile.twist_limit == pytest.approx(sorted((math.pi + sign * low, math.pi + sign * high)))
    low, high = REAL.limits_of(f"{side}_hand.down_up")
    assert profile.flex_limit == pytest.approx((-high, -low))
    low, high = REAL.limits_of(f"{side}_hand.in_out")
    assert profile.deviation_limit == pytest.approx(sorted((sign * low, sign * high)))


@pytest.mark.parametrize("side", SIDES)
def test_limbs_draws_the_skeletons_hand_on_its_own_arm_frame(side):
    rng = random.Random(4)
    limits = sk.arm_profile(REAL, sk.pose(REAL), side)
    for _ in range(20):
        values = {
            f"{side}_upper_arm.down_up": rng.uniform(-1, 0.5),
            f"{side}_upper_arm.twist_in_out": rng.uniform(-1, 1),
            f"{side}_lower_arm.stretch": rng.uniform(-2, 0),
            f"{side}_lower_arm.twist_in_out": rng.uniform(-1.4, 1.5),
            f"{side}_hand.down_up": rng.uniform(-1.3, 1.2),
            f"{side}_hand.in_out": rng.uniform(-0.3, 0.7),
        }
        pose = sk.pose(REAL, values)
        control = sk.wrist_control(REAL, pose, side)
        drawn = limbs.hand_pose(sk.hand_profile(REAL, side), control, sk.to_arm_pose(REAL, pose, side).frame, side=side)
        ours = sk.to_hand_pose(REAL, pose, side)
        assert close(drawn.frame.origin, ours.frame.origin)
        assert turned(drawn.frame.rotation, ours.frame.rotation)
        assert close(drawn.normal, ours.normal)
        for name, value in (("forearm_twist", control.forearm_twist), ("wrist_flex", control.wrist_flex)):
            low, high = getattr(limits, {"forearm_twist": "twist_limit", "wrist_flex": "flex_limit"}[name])
            assert low - 1e-9 <= value <= high + 1e-9
        assert limits.deviation_limit[0] - 1e-9 <= control.wrist_deviation <= limits.deviation_limit[1] + 1e-9


def test_a_wrist_control_needs_a_hand():
    handless = sk.SkeletonProfile("x", REAL.proportions, omit=("left_hand",), hands=("none", "human"))
    with pytest.raises(sk.SkeletonBridgeError) as caught:
        sk.wrist_control(handless, sk.pose(handless), "left")
    assert caught.value.to_dict()["code"] == "skeleton.absent"
    handless = sk.SkeletonProfile("x", REAL.proportions, omit=("left_hand",), hands=("none", "human"))
    assert sk.arm_profile(handless, sk.pose(handless), "left").flex_limit == limbs.ArmProfile().flex_limit


def test_an_arm_that_the_character_lacks_is_refused():
    armless = sk.SkeletonProfile("x", REAL.proportions, omit=("left_upper_arm",), hands=("none", "human"))
    for call in (
        lambda: sk.to_arm_pose(armless, sk.pose(armless), "left"),
        lambda: sk.arm_profile(armless, sk.pose(armless), "left"),
        lambda: sk.from_arm_pose(armless, sk.pose(armless), "left", sk.to_arm_pose(REAL, sk.pose(REAL), "left")),
    ):
        with pytest.raises(sk.SkeletonBridgeError) as caught:
            call()
        assert caught.value.to_dict()["code"] == "skeleton.absent"
    with pytest.raises(sk.SkeletonError):
        sk.to_arm_pose(REAL, sk.pose(REAL), "middle")


@pytest.mark.parametrize("name", ["shoulder", "upper", "forearm", "frame", "hinge", "type"])
def test_an_arm_of_another_figure_is_a_mismatch(name):
    pose = sk.pose(REAL, {"right_lower_arm.stretch": -1.0})
    arm = sk.to_arm_pose(REAL, pose, "right")
    kinds = {
        "shoulder": limbs.ArmPose(arm.shoulder + Vec3(0.1, 0, 0), arm.elbow, arm.wrist, arm.frame, arm.elbow_angle),
        "upper": limbs.ArmPose(arm.shoulder, arm.elbow + Vec3(0.1, 0, 0), arm.wrist, arm.frame, arm.elbow_angle),
        "forearm": limbs.ArmPose(arm.shoulder, arm.elbow, arm.wrist + Vec3(0.1, 0, 0), arm.frame, arm.elbow_angle),
        "frame": limbs.ArmPose(
            arm.shoulder,
            arm.elbow,
            arm.wrist,
            Frame(arm.wrist, Quaternion.axis_angle(Vec3(1, 0, 0), 1.0)),
            arm.elbow_angle,
        ),
        "hinge": limbs.ArmPose(
            arm.shoulder,
            arm.elbow,
            arm.wrist,
            Frame(arm.wrist, arm.frame.rotation * Quaternion.axis_angle(Vec3(0, 1, 0), 0.7)),
            arm.elbow_angle,
        ),
        "type": object(),
    }
    with pytest.raises(sk.SkeletonBridgeError) as caught:
        sk.from_arm_pose(REAL, sk.pose(REAL), "right", kinds[name])
    assert caught.value.to_dict()["code"] == "skeleton.mismatch"


def test_an_arm_the_limits_cannot_hold_is_refused_by_name():
    arm = sk.to_arm_pose(REAL, sk.pose(REAL, {"right_lower_arm.stretch": -1.0}), "right")
    narrow = sk.SkeletonProfile("x", REAL.proportions, limits=(("right_lower_arm.stretch", (-0.5, 0.0)),))
    with pytest.raises(sk.JointLimitError) as caught:
        sk.from_arm_pose(narrow, sk.pose(narrow), "right", arm)
    assert caught.value.violations[0].key == "right_lower_arm.stretch"


@pytest.mark.parametrize("kind", ["human", "three-finger", "mitten", "paw", "gripper"])
@pytest.mark.parametrize("side", SIDES)
def test_a_hand_profile_mirrors_its_limbs_kind(kind, side):
    profile = sk.SkeletonProfile("x", REAL.proportions, hands=(kind, kind))
    made = sk.hand_profile(profile, side)
    assert isinstance(made, limbs.HandProfile)
    assert made.name == kind
    assert [d.name for d in made.digits] == [d.name for d in limbs.HANDS[kind].digits]
    for digit, (_, joints) in zip(made.digits, profile.digits(side), strict=True):
        assert len(digit.lengths) == len(joints) == len(digit.max_flex)
    assert made.palm_width > 0 and made.palm_length > 0


def test_a_hand_profile_sets_the_thumb_across_from_the_little_finger():
    made = sk.hand_profile(REAL, "right")
    digits = {d.name: d for d in made.digits}
    assert digits["thumb"].thumb and not digits["index"].thumb
    assert digits["thumb"].base.x > 0 > digits["little"].base.x
    assert digits["thumb"].splay != 0 and digits["middle"].splay == pytest.approx(0)


@pytest.mark.parametrize("side", SIDES)
def test_a_hand_pose_reads_the_finger_joints(side):
    pose = sk.pose(REAL, {f"{side}_index_proximal.stretched": -0.8, f"{side}_index_proximal.spread": 0.1})
    hand = sk.to_hand_pose(REAL, pose, side)
    world, tips = sk.world(REAL, pose), sk.tips(REAL, pose)
    index = hand.digit("index")
    assert len(index.points) == 4
    assert close(index.points[0], world[f"{side}_index_proximal"].origin)
    assert close(index.points[3], tips[f"{side}_index_distal"])
    assert close(hand.frame.origin, world[f"{side}_hand"].origin)


@pytest.mark.parametrize("side", SIDES)
def test_the_hand_frame_follows_limbs_conventions(side):
    hand = sk.to_hand_pose(REAL, sk.pose(REAL), side)
    along = hand.frame.rotation.rotate(Vec3(0, 1, 0))
    assert close(along, Vec3(1 if side == "right" else -1, 0, 0))
    assert close(hand.normal, Vec3(0, 1, 0))  # the T-stance's palms face down
    thumb = hand.digit("thumb").points[0] - hand.frame.origin
    assert thumb.z > 0  # both thumbs lead, which is what limbs' mirrored x means on the left
    assert len(hand.palm) == 4


def test_a_mitten_keeps_the_limbs_topology():
    hand = sk.to_hand_pose(STICK, sk.rest_pose(STICK), "left")
    assert [d.name for d in hand.digits] == ["thumb", "fingers"]
    assert all(len(d.points) == 3 for d in hand.digits)


def test_a_hand_with_no_digits_is_refused():
    none = sk.SkeletonProfile("x", REAL.proportions, hands=("none", "human"))
    for call in (
        lambda: sk.hand_profile(none, "left"),
        lambda: sk.to_hand_pose(none, sk.pose(none), "left"),
        lambda: sk.from_hand_pose(none, sk.pose(none), "left", sk.to_hand_pose(REAL, sk.pose(REAL), "left")),
    ):
        with pytest.raises(sk.SkeletonBridgeError) as caught:
            call()
        assert caught.value.to_dict()["code"] == "skeleton.absent"


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("name", ["realistic", "cartoon", "stick"])
def test_a_hand_round_trips(side, name):
    profile = sk.preset(name)
    rng = random.Random(21)
    for _ in range(10):
        values = {
            f"{side}_lower_arm.stretch": rng.uniform(-2, -0.2),
            f"{side}_lower_arm.twist_in_out": rng.uniform(-1, 1),
            f"{side}_hand.down_up": rng.uniform(-1, 1),
            f"{side}_hand.in_out": rng.uniform(-0.3, 0.7),
        }
        for _, joints in profile.digits(side):
            for bone in joints:
                low, high = profile.limits_of(f"{bone}.stretched")
                values[f"{bone}.stretched"] = rng.uniform(low * 0.9, high * 0.9)
                if bone.endswith("proximal"):
                    low, high = profile.limits_of(f"{bone}.spread")
                    values[f"{bone}.spread"] = rng.uniform(low * 0.9, high * 0.9)
        pose = sk.pose(profile, values)
        base = sk.pose(profile, {f"{side}_lower_arm.stretch": values[f"{side}_lower_arm.stretch"]})
        back = sk.from_hand_pose(profile, base, side, sk.to_hand_pose(profile, pose, side))
        assert same_pose(back, pose, 1e-5)


def test_a_skeleton_arm_and_hand_draw_through_the_limbs_projection():
    pose = sk.pose(REAL, {"right_lower_arm.stretch": -1.0})
    arm, hand = sk.to_arm_pose(REAL, pose, "right"), sk.to_hand_pose(REAL, pose, "right")
    sample = Sample(0.0, arm, hand, sk.wrist_control(REAL, pose, "right"), "hold", "hold")
    drawn = project_pose(sample, limbs.Camera(origin=(540, 900), scale=700), width=0.05)
    assert {"upper", "forearm", "palm", "digit:thumb", "digit:little"} <= {part.name for part in drawn.parts}
    assert drawn.palm_view == "back" or drawn.palm_view == "side"


@pytest.mark.parametrize("name", ["origin", "names", "count", "root", "length", "plane", "type", "kinked"])
def test_a_hand_of_another_figure_is_a_mismatch(name):
    pose = sk.pose(REAL)
    hand = sk.to_hand_pose(REAL, pose, "right")
    thumb, *rest = hand.digits
    middle = rest[1]
    bent = (middle.points[0], middle.points[1], middle.points[2] + Vec3(0, 0.02, 0), middle.points[3])
    kinds = {
        "origin": limbs.HandPose(
            Frame(hand.frame.origin + Vec3(0.1, 0, 0), hand.frame.rotation), hand.palm, hand.digits, hand.normal
        ),
        "names": limbs.HandPose(hand.frame, hand.palm, hand.digits[1:], hand.normal),
        "count": limbs.HandPose(hand.frame, hand.palm, (type(thumb)("thumb", thumb.points[:-1]), *rest), hand.normal),
        "root": limbs.HandPose(
            hand.frame,
            hand.palm,
            (type(thumb)("thumb", tuple(p + Vec3(0, 0.1, 0) for p in thumb.points)), *rest),
            hand.normal,
        ),
        "length": limbs.HandPose(
            hand.frame,
            hand.palm,
            (type(thumb)("thumb", (*thumb.points[:-1], thumb.points[-1] + Vec3(0.2, 0, 0))), *rest),
            hand.normal,
        ),
        "plane": limbs.HandPose(
            hand.frame,
            hand.palm,
            (
                thumb,
                rest[0],
                type(thumb)("middle", (*middle.points[:-1], middle.points[-1] + Vec3(0, 0, 0.005))),
                *rest[2:],
            ),
            hand.normal,
        ),
        "kinked": limbs.HandPose(
            hand.frame, hand.palm, (thumb, rest[0], type(thumb)("middle", bent), *rest[2:]), hand.normal
        ),
        "type": object(),
    }
    with pytest.raises(sk.SkeletonBridgeError) as caught:
        sk.from_hand_pose(REAL, pose, "right", kinds[name])
    assert caught.value.to_dict()["code"] == "skeleton.mismatch"


def test_a_limbs_built_hand_with_this_geometry_lands_on_the_skeleton():
    made = sk.hand_profile(REAL, "right")
    pose = sk.pose(REAL)
    frame = sk.to_hand_pose(REAL, pose, "right").frame
    limbs_hand = limbs.hand_pose(made, HandControl(curl=0.0), frame, side="right")
    assert [d.name for d in limbs_hand.digits] == [d.name for d in made.digits]


def test_a_character_without_a_spine_takes_no_torso_turn():
    legs = sk.SkeletonProfile("legs", REAL.proportions, omit=("spine",), hands=("none", "none"))
    still = sk.to_body_pose(legs, crouch(legs))
    assert same_pose(sk.from_body_pose(legs, still), crouch(legs))
    leaning = sk.to_body_pose(
        REAL, sk.pose(REAL, {**crouch(REAL).as_dict(), "spine.front_back": -0.2}, root=crouch(REAL).root)
    )
    with pytest.raises(sk.SkeletonBridgeError) as caught:
        sk.from_body_pose(legs, leaning)
    assert caught.value.to_dict()["code"] == "skeleton.absent"


def test_bridges_refuse_what_is_not_their_input():
    with pytest.raises(sk.SkeletonSchemaError):
        sk.to_body_pose(REAL, crouch(REAL), time=math.nan)
    with pytest.raises(sk.SkeletonSchemaError):
        sk.to_body_pose(REAL, {"hips.up": 0.0})
    with pytest.raises(sk.SkeletonSchemaError):
        sk.from_body_pose(REAL, sk.to_body_pose(REAL, crouch(REAL)), base={"hips.up": 0.0})


@pytest.mark.parametrize("marker", ["skeleton-recipe", "skeleton-profile"])
def test_the_documented_recipes_execute(marker):
    text = (Path(__file__).parents[1] / "docs/authoring-skeleton.md").read_text()
    code = text.split(f"<!-- {marker}:start -->")[1].split("```python\n")[1].split("```")[0]
    namespace = {"sk": sk}
    exec(compile(code, marker, "exec"), namespace)

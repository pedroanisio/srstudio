"""Bridges from a skeleton pose to the records body and limbs adapters already draw, and back (ADR 0185).

``to_body_pose`` gives ``body.BodyPose`` (root, torso, legs, support); ``to_arm_pose`` and ``to_hand_pose`` give
``limbs.ArmPose`` and ``limbs.HandPose`` for one side. Each ``from_*`` reads such a record back into controls, keeping
everything else from a base pose, and refuses a record whose geometry is not this character's.

Conventions, all fixed by those modules rather than by the skeleton:

* body's root sits at hip-joint height between the hips with the hips' channels at zero, and its torso is the upper
  chest's turn at that origin. Back from body, a torso turn is shared along spine, chest and upper chest in
  proportion to each joint's canonical range, and the knee's own twist is left at zero; the foot carries it.
* limbs' arm frame follows its forearm with +x across the elbow's hinge, mirrored on the left. limbs' hand frame
  has +y toward the fingers, +z out of the palm and +x toward the thumb on the right, mirrored on the left; on the
  skeleton's hand that is (+z, +x, +y) on the right and (-z, -x, +y) on the left. At zero forearm twist limbs'
  palm faces away from where the skeleton's does, so :func:`wrist_control` and :func:`arm_profile` carry that half
  turn in the forearm twist.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from .. import checks
from ..body import BodyPose, BodyProfile, LegPose, support_footprint, support_hull, support_margin
from ..limbs.math3d import Frame, Quaternion, Vec3
from ..limbs.model import HUMAN, ArmPose, ArmProfile, DigitPose, DigitProfile, HandControl, HandPose, HandProfile
from ._errors import SkeletonBridgeError, SkeletonError, SkeletonSchemaError
from ._joints import BY_NAME, JOINT_TABLE, JOINTS, Joint
from ._pose import SkeletonPose, _checked, _solved, pose
from ._profile import FINGERS, HAND_KINDS, SkeletonProfile
from ._rotation import decompose, turn

TOLERANCE = 1e-6  # metres or radians a record may differ from this character's geometry and still be its own
SIDES = ("left", "right")
LEG = ("upper_leg", "lower_leg", "foot")
SPINE = ("spine", "chest", "upper_chest")
DOWN = Vec3(0, 1, 0)
X, Y, Z = Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)
# limbs' hand frame on the skeleton's hand, as the columns of a turn in the hand's own frame.
HAND_FRAME = {"right": Quaternion.axes(Z, X, Y), "left": Quaternion.axes(-Z, -X, Y)}
_TOE_TIP = BY_NAME["right_toes"].tip
assert _TOE_TIP is not None  # the table ends the toes; body's foot length is read from it
_TOE_REACH = _TOE_TIP.z


def _fail(message: str, code: str, path: str, actual: object = None, expected: object = None) -> SkeletonBridgeError:
    return SkeletonBridgeError(message, code=code, path=path, actual=actual, expected=expected)


def _sign(side: object) -> int:
    if side not in SIDES:
        raise SkeletonError(
            "a side is left or right", code="skeleton.unknown", path="side", actual=side, expected=SIDES
        )
    return 1 if side == "right" else -1


def _need(profile: SkeletonProfile, names: Sequence[str], path: str) -> None:
    missing = [name for name in names if not profile.has(name)]
    if missing:
        raise _fail(f"profile {profile.name!r} has no {', '.join(missing)}", "skeleton.absent", path, missing)


def _frames(profile: SkeletonProfile, pose_: SkeletonPose) -> dict[str, Frame]:
    if not isinstance(pose_, SkeletonPose):
        raise SkeletonSchemaError("expected a SkeletonPose", path="pose", actual=type(pose_).__name__)
    return _solved(profile, dict(_checked(profile, pose_.as_dict(), False)), pose_.root)


def _xyz(v: Vec3) -> list[float]:
    return [v.x, v.y, v.z]


def _at(found: Vec3, expected: Vec3, path: str) -> None:
    if found.distance(expected) > TOLERANCE:
        raise _fail("not where this character puts it", "skeleton.mismatch", path, _xyz(found), _xyz(expected))


def _long(span: Vec3, length: float, path: str) -> None:
    if abs(span.length - length) > TOLERANCE:
        raise _fail("a bone of another length", "skeleton.mismatch", path, span.length, length)


def _angle(a: Vec3, b: Vec3) -> float:
    return math.acos(max(-1.0, min(1.0, a.unit().dot(b.unit()))))


def _carry(source: tuple[Vec3, Vec3], target: tuple[Vec3, Vec3]) -> Quaternion:
    """The turn taking two perpendicular unit directions onto two others."""
    (a, b), (c, d) = source, target
    return Quaternion.axes(c, d, c.cross(d)) * Quaternion.axes(a, b, a.cross(b)).inverse()


def _solve(joint: Joint, local: Quaternion, values: dict[str, float], profile: SkeletonProfile) -> None:
    """Read a joint's turn on its parent into its controls, nearest the values already there."""
    keys = joint.controls
    angles, _ = decompose(
        joint.rest.inverse() * local,
        [dof.axis for dof in joint.dofs],
        [values.get(key, 0.0) for key in keys],
        [profile.limits_of(key) for key in keys],
    )
    values.update(zip(keys, angles, strict=True))


def _end(profile: SkeletonProfile, name: str) -> Vec3:
    """Where a finger bone ends in its own frame: its tip, or where the next canonical bone starts."""
    joint = BY_NAME[name]
    if joint.tip is not None:
        return joint.tip * profile._scale(joint)
    return profile._offset(next(j for j in JOINTS if j.parent == name))


# ---- body -------------------------------------------------------------------------------------------------------


def _drop(profile: SkeletonProfile) -> Vec3:
    """From the hips to body's root: down to the hip joints' height, on the midline."""
    hip = profile._offset(BY_NAME["right_upper_leg"])
    return Vec3(0, hip.y, hip.z)


def _torso_height(profile: SkeletonProfile) -> float:
    rise = sum(profile._offset(BY_NAME[name]).y for name in (*SPINE, "right_shoulder", "right_upper_arm"))
    return _drop(profile).y - rise


def body_profile(profile: SkeletonProfile) -> BodyProfile:
    """body's anatomy for this character: hip width, thigh, shin, ankle height and foot from its bones, and the torso
    from the hip joints to the shoulders. The sole's width and heel are the table's, from srlocations' foot solid,
    scaled with the foot. body's joint envelopes, stride and speed stay body's defaults. A character too small or large
    for body's 0.01..2 metre bounds raises body's own BodyError."""
    width = 2 * abs(profile._offset(BY_NAME["right_upper_leg"]).x)
    toes, foot = BY_NAME["right_toes"], profile._scale(BY_NAME["right_foot"])
    toe = profile._offset(toes).z + _TOE_REACH * profile._scale(toes)
    foot_width, heel = JOINT_TABLE.sole_width * foot, JOINT_TABLE.sole_heel * foot
    return BodyProfile(
        hip_width=width,
        thigh=profile._offset(BY_NAME["right_lower_leg"]).length,
        shin=profile._offset(BY_NAME["right_foot"]).length,
        ankle_height=profile.length("ankle"),
        foot_width=foot_width,
        heel=heel,
        toe=toe,
        torso_height=_torso_height(profile),
        support_margin=min(BodyProfile.support_margin, min(foot_width / 2, heel, toe) / 2),
    )


def _grounded(sole: Frame) -> Frame:
    """A planted sole on y=0 with its yaw alone: flat here is within TOLERANCE, and body's support takes exact soles."""
    ahead = sole.rotation.rotate(Z)
    return Frame(Vec3(sole.origin.x, 0.0, sole.origin.z), turn(Y, math.atan2(ahead.x, ahead.z)))


def _legs(profile: SkeletonProfile) -> None:
    _need(profile, [f"{side}_{part}" for side in SIDES for part in LEG], "legs")


def to_body_pose(
    profile: SkeletonProfile, pose: SkeletonPose, *, time: float = 0.0, planted: Sequence[str] | None = None
) -> BodyPose:
    """body's record of this pose at ``time``. A foot is planted when its sole lies flat on y=0; ``planted`` names
    the planted feet instead, each of which must be flat on y=0. With no foot planted there is no support and so no
    BodyPose. The shoulders are the upper arms' joints on the torso's turn, as body places its own."""
    _legs(profile)
    if not checks.number(time):
        raise SkeletonSchemaError("time is a finite number of seconds", path="time", actual=time)
    frames = _frames(profile, pose)
    shape = body_profile(profile)
    root = frames["hips"].compose(Frame(_drop(profile)))
    torso = Frame(root.origin, frames["upper_chest"].rotation)
    shoulders = tuple(Frame(frames[f"{side}_upper_arm"].origin, torso.rotation) for side in SIDES)
    soles = {}
    for side in SIDES:
        foot = frames[f"{side}_foot"]
        soles[side] = Frame(foot.point(Vec3(0, shape.ankle_height, 0)), foot.rotation)
    flat = {
        side: abs(sole.origin.y) <= TOLERANCE and _angle(sole.rotation.rotate(DOWN), DOWN) <= TOLERANCE
        for side, sole in soles.items()
    }
    if planted is None:
        chosen = tuple(side for side in SIDES if flat[side])
    elif isinstance(planted, (tuple, list)) and all(side in SIDES and flat[side] for side in planted):
        chosen = tuple(planted)
    else:
        raise _fail(
            "a named foot is not flat on y=0", "skeleton.support", "planted", planted, [s for s in SIDES if flat[s]]
        )
    if not chosen:
        raise _fail("no foot is flat on y=0, so nothing supports the body", "skeleton.support", "planted", (), SIDES)
    legs = []
    com = torso.point(Vec3(0, -0.45 * shape.torso_height, 0)) * 0.6
    support: list[tuple[float, float]] = []
    for side in SIDES:
        hip, knee, ankle = (frames[f"{side}_{part}"].origin for part in LEG)
        sole = soles[side]
        legs.append(
            LegPose(
                side,
                hip,
                knee,
                ankle,
                sole,
                side in chosen,
                _angle(knee - hip, ankle - knee),
                _angle(knee - hip, root.rotation.rotate(DOWN)),
                _angle(ankle - knee, sole.rotation.rotate(DOWN)),
                (root.rotation.inverse() * sole.rotation).rotation_vector.length,
            )
        )
        com += (hip + knee) * 0.06 + (knee + ankle) * 0.03 + sole.origin * 0.02
        if side in chosen:
            support.extend((p.x, p.z) for p in support_footprint(_grounded(sole), shape))
    polygon = support_hull(support)
    margin = support_margin(polygon, com)
    return BodyPose(float(time), root, torso, (shoulders[0], shoulders[1]), (legs[0], legs[1]), com, polygon, margin)


def from_body_pose(profile: SkeletonProfile, body: BodyPose, *, base: SkeletonPose | None = None) -> SkeletonPose:
    """The skeleton pose a BodyPose shows: root, spine and legs read from it, everything else from ``base``.

    The hips' own channels are zero, since body's root carries them. A straight leg cannot show which way its knee
    faces, so its hinge is taken across the hips; a straight leg lying along that line has no answer. The shoulders
    are not read: they follow from the spine and ``base``'s arms."""
    if not isinstance(body, BodyPose):
        raise _fail("expected a body.BodyPose", "skeleton.mismatch", "body", type(body).__name__)
    _legs(profile)
    if base is None:
        base = SkeletonPose()
    elif not isinstance(base, SkeletonPose):
        raise SkeletonSchemaError("expected a SkeletonPose", path="base", actual=type(base).__name__)
    if tuple(getattr(leg, "side", None) for leg in body.legs) != SIDES:
        raise _fail(
            "legs are the left then the right",
            "skeleton.mismatch",
            "body.legs",
            [getattr(leg, "side", None) for leg in body.legs],
            SIDES,
        )
    _at(body.torso.origin, body.root.origin, "body.torso.origin")
    root = body.root.compose(Frame(-_drop(profile)))
    values = {key: value for key, value in base.as_dict().items() if not key.startswith("hips.")}
    spine = [BY_NAME[name] for name in SPINE if profile.has(name)]
    lean = (body.root.rotation.inverse() * body.torso.rotation).rotation_vector
    if not spine and lean.length > TOLERANCE:
        raise _fail("a torso turn on a character with no spine", "skeleton.absent", "body.torso", lean.length, 0.0)
    ranges = [sum(dof.high - dof.low for dof in joint.dofs) for joint in spine]
    for joint, share in zip(spine, ranges, strict=True):
        _solve(joint, Quaternion.from_rotation_vector(lean * (share / sum(ranges))), values, profile)
    ankle = profile.length("ankle")
    for leg in body.legs:
        upper, lower, foot = (BY_NAME[f"{leg.side}_{part}"] for part in LEG)
        path = f"body.legs.{leg.side}"
        _at(leg.hip, root.point(profile._offset(upper)), path + ".hip")
        _long(leg.knee - leg.hip, profile._offset(lower).length, path + ".knee")
        _long(leg.ankle - leg.knee, profile._offset(foot).length, path + ".ankle")
        _at(leg.ankle, leg.sole.point(Vec3(0, -ankle, 0)), path + ".sole")
        thigh, shin = (leg.knee - leg.hip).unit(), (leg.ankle - leg.knee).unit()
        stretch = lower.dof("stretch")
        across = root.rotation.rotate(upper.rest.rotate(lower.rest.rotate(stretch.axis)))
        bend = thigh.cross(shin)
        if bend.length > 1e-9:
            hinge = bend.unit() if bend.dot(across) >= 0 else -bend.unit()
        else:
            square = across - thigh * thigh.dot(across)
            if square.length < TOLERANCE:
                raise _fail(
                    "a straight leg along the hips shows no knee direction", "skeleton.ill-posed", path, _xyz(thigh)
                )
            hinge = square.unit()
        knee = math.atan2(bend.dot(hinge), thigh.dot(shin))
        carried = _carry((profile._offset(lower).unit(), stretch.axis), (thigh, hinge))
        _solve(upper, root.rotation.inverse() * carried, values, profile)
        values[f"{lower.name}.stretch"] = knee
        values[f"{lower.name}.twist_in_out"] = 0.0
        shank = carried * lower.rest * turn(stretch.axis, knee)
        _solve(foot, shank.inverse() * leg.sole.rotation, values, profile)
    return pose(profile, values, root=root)


# ---- limbs: arm -------------------------------------------------------------------------------------------------


def _arm(profile: SkeletonProfile, side: object) -> tuple[Joint, Joint, Joint, int]:
    sign = _sign(side)
    _need(profile, [f"{side}_upper_arm", f"{side}_lower_arm"], f"arms.{side}")
    upper, lower, hand = (BY_NAME[f"{side}_{part}"] for part in ("upper_arm", "lower_arm", "hand"))
    return upper, lower, hand, sign


def _hinge(frames: dict[str, Frame], upper: Joint, lower: Joint) -> Vec3:
    return frames[upper.name].rotation.rotate(lower.rest.rotate(lower.dof("stretch").axis))


def _wrist(wrist: Vec3, forearm: Vec3, hinge: Vec3, sign: int) -> Frame:
    """limbs' one wrist convention: +y along the forearm, +x = hinge x y, mirrored on the left."""
    y = forearm.unit()
    x = hinge.cross(y).unit() * sign
    return Frame(wrist, Quaternion.axes(x, y, x.cross(y)))


def to_arm_pose(profile: SkeletonProfile, pose: SkeletonPose, side: str) -> ArmPose:
    """limbs' record of one arm: shoulder, elbow and wrist joints and limbs' wrist frame across the elbow's hinge."""
    upper, lower, hand, sign = _arm(profile, side)
    frames = _frames(profile, pose)
    shoulder, elbow, wrist = (frames[joint.name].origin for joint in (upper, lower, hand))
    frame = _wrist(wrist, wrist - elbow, _hinge(frames, upper, lower), sign)
    return ArmPose(shoulder, elbow, wrist, frame, _angle(elbow - shoulder, wrist - elbow))


def _shifted(limits: tuple[float, float], sign: int, shift: float = 0.0) -> tuple[float, float]:
    """``shift + sign * value`` over a range, kept ordered."""
    low, high = shift + sign * limits[0], shift + sign * limits[1]
    return (min(low, high), max(low, high))


def arm_profile(profile: SkeletonProfile, pose: SkeletonPose, side: str) -> ArmProfile:
    """limbs' arm for this character, with its shoulder where ``pose`` puts it and its limits in limbs' controls:
    elbow flexion is minus the stretch; wrist flex is minus the hand's down-up; deviation is the hand's in-out on
    the right and minus it on the left; forearm twist is half a turn plus the canonical twist on the right and half
    a turn minus it on the left. A character with no hand keeps limbs' default wrist limits."""
    upper, lower, hand, sign = _arm(profile, side)
    frames = _frames(profile, pose)
    stretch = profile.limits_of(f"{lower.name}.stretch")
    flex, deviation = ArmProfile.flex_limit, ArmProfile.deviation_limit
    if profile.has(hand.name):
        flex = _shifted(profile.limits_of(f"{hand.name}.down_up"), -1)
        deviation = _shifted(profile.limits_of(f"{hand.name}.in_out"), sign)
    length = profile._offset(lower).length
    return ArmProfile(
        shoulder=frames[upper.name].origin,
        upper=length,
        forearm=profile._offset(hand).length,
        width=length * ArmProfile.width / ArmProfile.upper,
        side=side,
        elbow_limit=(max(0.0, -stretch[1]), min(math.pi, -stretch[0])),
        twist_limit=_shifted(profile.limits_of(f"{lower.name}.twist_in_out"), sign, math.pi),
        flex_limit=flex,
        deviation_limit=deviation,
    )


def from_arm_pose(profile: SkeletonProfile, base: SkeletonPose, side: str, arm: ArmPose) -> SkeletonPose:
    """``base`` with one upper arm and elbow stretch read from a limbs ArmPose, such as ``limbs.reach`` returns for
    :func:`arm_profile`. The shoulder must be where ``base`` puts it. The hinge comes from the wrist frame, so a
    straight arm keeps its twist; forearm twist and the hand stay as in ``base``."""
    upper, lower, hand, sign = _arm(profile, side)
    if not isinstance(arm, ArmPose):
        raise _fail("expected a limbs.ArmPose", "skeleton.mismatch", "arm", type(arm).__name__)
    frames = _frames(profile, base)
    _at(arm.shoulder, frames[upper.name].origin, "arm.shoulder")
    _long(arm.elbow - arm.shoulder, profile._offset(lower).length, "arm.elbow")
    _long(arm.wrist - arm.elbow, profile._offset(hand).length, "arm.wrist")
    _at(arm.frame.origin, arm.wrist, "arm.frame.origin")
    bone, forearm = (arm.elbow - arm.shoulder).unit(), (arm.wrist - arm.elbow).unit()
    along = arm.frame.rotation.rotate(Y)
    _at(along, forearm, "arm.frame.rotation")
    hinge = along.cross(arm.frame.rotation.rotate(X) * sign)
    if abs(hinge.dot(bone)) > TOLERANCE:
        raise _fail(
            "the wrist frame's hinge does not cross the upper arm",
            "skeleton.mismatch",
            "arm.frame",
            hinge.dot(bone),
            0.0,
        )
    stretch = lower.dof("stretch")
    elbow = math.atan2(bone.cross(forearm).dot(hinge), bone.dot(forearm))
    carried = _carry((profile._offset(lower).unit(), lower.rest.rotate(stretch.axis)), (bone, hinge))
    values = base.as_dict()
    _solve(upper, frames[f"{side}_shoulder"].rotation.inverse() * carried, values, profile)
    values[f"{lower.name}.stretch"] = elbow
    return pose(profile, values, root=base.root)


# ---- limbs: hand ------------------------------------------------------------------------------------------------


def _limbs(v: Vec3, sign: int) -> Vec3:
    """A vector in the skeleton's hand frame, in limbs' hand coordinates before limbs mirrors x on the left."""
    return Vec3(v.z, sign * v.x, v.y)


def _kind(profile: SkeletonProfile, side: str) -> str:
    _sign(side)
    kind = profile.hand(side)
    if kind == "none":
        raise _fail(
            f"profile {profile.name!r} has no digits on the {side} hand", "skeleton.absent", f"hands.{side}", kind
        )
    return kind


def hand_profile(profile: SkeletonProfile, side: str) -> HandProfile:
    """limbs' hand for this character's hand kind on ``side``, with limbs' digit names and the skeleton's bones: each
    digit's base, phalanx lengths and rest splay, and maximum flexion from its stretch limits. The palm spans the
    knuckles of the four fingers and reaches them from the wrist; its thickness keeps limbs' human proportion."""
    kind = _kind(profile, side)
    sign = _sign(side)
    digits = []
    for (name, bones), (_, finger, _) in zip(profile.digits(side), HAND_KINDS[kind], strict=True):
        first = BY_NAME[bones[0]]
        heading = _limbs(first.rest.rotate(_end(profile, bones[0])), sign).unit()
        digits.append(
            DigitProfile(
                name,
                _limbs(profile._offset(first), sign),
                tuple(_end(profile, bone).length for bone in bones),
                math.atan2(-heading.x, heading.y),
                finger == "thumb",
                tuple(max(0.0, -profile.limits_of(f"{bone}.stretched")[0]) for bone in bones),
            )
        )
    knuckles = [_limbs(profile._offset(BY_NAME[f"{side}_{finger}_proximal"]), sign) for finger in FINGERS[1:]]
    width = max(k.x for k in knuckles) - min(k.x for k in knuckles)
    return HandProfile(
        kind,
        width,
        sum(k.y for k in knuckles) / len(knuckles),
        tuple(digits),
        width * HUMAN.thickness / HUMAN.palm_width,
    )


def to_hand_pose(profile: SkeletonProfile, pose: SkeletonPose, side: str) -> HandPose:
    """limbs' record of one hand: its frame, palm corners as limbs places them, each digit's joints and tip."""
    made = hand_profile(profile, side)
    sign = _sign(side)
    frames = _frames(profile, pose)
    hand = frames[f"{side}_hand"]
    frame = Frame(hand.origin, hand.rotation * HAND_FRAME[side])
    digits = tuple(
        DigitPose(name, (*(frames[bone].origin for bone in bones), frames[bones[-1]].point(_end(profile, bones[-1]))))
        for name, bones in profile.digits(side)
    )
    w, h = made.palm_width / 2, made.palm_length
    corners = (Vec3(-w * 0.65, 0, 0), Vec3(w * 0.65, 0, 0), Vec3(w, h, 0), Vec3(-w, h, 0))
    palm = tuple(frame.point(Vec3(c.x * sign, c.y, c.z)) for c in corners)
    return HandPose(frame, palm, digits, frame.rotation.rotate(Z))


def wrist_control(profile: SkeletonProfile, pose: SkeletonPose, side: str) -> HandControl:
    """The wrist of limbs' HandControl that turns limbs' arm frame (from :func:`to_arm_pose`) into this hand's frame
    (from :func:`to_hand_pose`), inside :func:`arm_profile`'s limits. Fingers are left straight: draw them from
    :func:`to_hand_pose`, since limbs' controls cannot spread one finger or bend one backwards."""
    _, _, hand, _ = _arm(profile, side)
    _need(profile, [hand.name], f"hands.{side}")
    arm = to_arm_pose(profile, pose, side)
    frames = _frames(profile, pose)
    relative = arm.frame.rotation.inverse() * frames[hand.name].rotation * HAND_FRAME[side]
    limits = arm_profile(profile, pose, side)
    (twist, flex, deviation), _ = decompose(
        relative, [Y, X, Z], [math.pi, 0.0, 0.0], [limits.twist_limit, limits.flex_limit, limits.deviation_limit]
    )
    return HandControl(curl=0.0, wrist_flex=flex, wrist_deviation=deviation, forearm_twist=twist)


def _bone(joint: Joint, frame: Quaternion, span: Vec3, end: Vec3) -> list[float]:
    """The controls that turn ``end`` (a bone at rest, in its frame) onto ``span`` (in the world): one hinge, or a
    hinge then a spread across it."""
    v = frame.inverse().rotate(span).unit()
    b = end.unit()
    axes = [dof.axis for dof in joint.dofs]
    first = axes[0]
    side = first.cross(b)
    bend = math.atan2(v.dot(side), v.dot(b))
    if len(axes) == 1:
        return [bend]
    across = axes[1].cross(b).dot(first)
    spread = math.atan2(across * v.dot(first), math.hypot(v.dot(b), v.dot(side)))
    return [bend, spread]


def from_hand_pose(profile: SkeletonProfile, base: SkeletonPose, side: str, hand: HandPose) -> SkeletonPose:
    """``base`` with one forearm twist, wrist and fingers read from a limbs HandPose made for this character, such
    as :func:`to_hand_pose` returns. The wrist must be where ``base`` puts it; the elbow and upper arm stay as in
    ``base``."""
    _kind(profile, side)
    if not isinstance(hand, HandPose):
        raise _fail("expected a limbs.HandPose", "skeleton.mismatch", "hand", type(hand).__name__)
    upper, lower, joint = (BY_NAME[f"{side}_{part}"] for part in ("upper_arm", "lower_arm", "hand"))
    frames = _frames(profile, base)
    _at(hand.frame.origin, frames[joint.name].origin, "hand.frame.origin")
    digits = profile.digits(side)
    names = [digit.name for digit in hand.digits]
    if names != [name for name, _ in digits]:
        raise _fail("digits of another hand", "skeleton.mismatch", "hand.digits", names, [name for name, _ in digits])
    values = base.as_dict()
    stretch = f"{lower.name}.stretch"
    elbow = frames[upper.name].rotation * lower.rest * turn(lower.dof("stretch").axis, values.get(stretch, 0.0))
    turned = hand.frame.rotation * HAND_FRAME[side].inverse()
    keys = (f"{lower.name}.twist_in_out", *joint.controls)
    axes = [lower.dof("twist_in_out").axis, *(dof.axis for dof in joint.dofs)]
    angles, _ = decompose(
        elbow.inverse() * turned, axes, [values.get(key, 0.0) for key in keys], [profile.limits_of(key) for key in keys]
    )
    values.update(zip(keys, angles, strict=True))
    palm = Frame(hand.frame.origin, turned)
    for (name, bones), digit in zip(digits, hand.digits, strict=True):
        path = f"hand.digits.{name}"
        if len(digit.points) != len(bones) + 1:
            raise _fail("a digit of another length", "skeleton.mismatch", path, len(digit.points), len(bones) + 1)
        parent = palm
        for i, bone in enumerate(bones):
            canon = BY_NAME[bone]
            start = parent.point(profile._offset(canon))
            _at(digit.points[i], start, f"{path}[{i}]")
            end = _end(profile, bone)
            span = digit.points[i + 1] - digit.points[i]
            _long(span, end.length, f"{path}[{i + 1}]")
            rest = parent.rotation * canon.rest
            found = _bone(canon, rest, span, end)
            values.update(zip(canon.controls, found, strict=True))
            moved = rest
            for dof, angle in zip(canon.dofs, found, strict=True):
                moved = moved * turn(dof.axis, angle)
            parent = Frame(start, moved)
            _at(parent.point(end), digit.points[i + 1], f"{path}[{i + 1}]")
    return pose(profile, values, root=base.root)

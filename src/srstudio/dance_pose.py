"""A dance frame on one character's skeleton (ADR 0186): the step from style-free moves to a pose any style can draw.

:func:`dance.sample` gives the root's translation in head radii and ``"joint.dof"`` deltas in radians.
:func:`dance_pose` adds them onto a :class:`skeleton.SkeletonPose` of a :class:`skeleton.SkeletonProfile`: the root
becomes the hips' ``right``, ``up`` and ``forward`` translations, in metres of that character's head radius, so a
big-headed cartoon bobs more than a realistic figure by the same share; each joint delta adds onto the base pose.

A delta on a joint the character lacks (a finger of a mitten hand, a joint ``omit`` removed) is dropped and named in
:attr:`DancePose.dropped`, never applied elsewhere. A target outside the canonical skeleton is refused, and a value
past a joint's limit is refused unless ``clamp`` asks for it to be clamped, as :func:`skeleton.add` does.

A frame's ``planted`` feet stay on the floor (ADR 0212). The root's translation is measured from standing: at a
root of zero, the lowest planted foot is where that foot stands in the base pose. So when a dance bends the legs, the
body is carried straight up or down by what the bend lifted or sank that foot, and the root's own travel rides on top,
as a bob or a hop. How far the bend lifts depends on this character's legs, so it is read here and never written into
a move, whose root is in head radii. A ``seat`` is held up by what it sits on and is not carried.

A frame's foot holds keep each planted foot where it was set down (ADR 0219). The legs are solved, inside this
character's limits, so the foot stays where and as it landed while the hips travel and the leg patterns swing; a leg
that cannot reach leaves its foot as near as its limits allow. A foot in the air carries the correction it had when it
was lifted and lets it go by the time it is next set down, so it neither jumps off the floor nor lands anywhere but
where the dance puts it. A frame without holds, as one built by hand, is posed as it is.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.optimize import least_squares

from . import skeleton as sk
from ._dance_sample import DanceFrame, FootHold

HIPS = ("hips.right", "hips.up", "hips.forward")  # the root's translations, in dance.ROOT's order
LEGS = {"left_foot": ("left_upper_leg", "left_lower_leg", "left_foot"),
        "right_foot": ("right_upper_leg", "right_lower_leg", "right_foot")}
TURN_RADII = 0.5  # a radian of a foot's turn weighs as much as half a head radius of its place
STAY = 0.02  # how hard each solved control is pulled back to the danced value, so the solve changes the least it can
MAX_EVALUATIONS = 200  # a bound on each leg's solve, owned here and never by the data
REACH = 0.98  # the share of a leg's length a planted foot is kept within, so the knee never locks straight


@dataclass(frozen=True)
class DancePose:
    """A frame danced on a character: the pose, and the canonical controls the character has no joint for."""

    pose: sk.SkeletonPose
    dropped: frozenset[str]


def dance_pose(
    profile: sk.SkeletonProfile, frame: DanceFrame, *, base: sk.SkeletonPose | None = None, clamp: bool = False
) -> DancePose:
    """``frame`` danced from ``base`` (the character's rest pose by default) on ``profile``."""
    start = base if base is not None else sk.rest_pose(profile)
    pose, dropped = _posed(profile, start, frame, clamp)
    if frame.support != "feet" or not frame.holds:
        return DancePose(pose, dropped)
    return DancePose(_reached(profile, start, frame, pose, clamp), dropped)


def _posed(
    profile: sk.SkeletonProfile, start: sk.SkeletonPose, frame: DanceFrame, clamp: bool
) -> tuple[sk.SkeletonPose, frozenset[str]]:
    """``frame`` added onto ``start`` and grounded, before any foot is held."""
    radius = profile.proportions.head_radius_m
    delta: dict[str, float] = {key: radius * value for key, value in zip(HIPS, frame.root, strict=True)}
    dropped = set()
    for key, value in _joints(frame.joints).items():
        if key not in sk.CONTROLS:
            raise sk.SkeletonSchemaError(
                "a dance moves a control the canonical skeleton does not have", path=f"joints.{key}", actual=key
            )
        if key in profile.controls:
            delta[key] = delta.get(key, 0.0) + value
        else:
            dropped.add(key)
    pose = sk.add(profile, start, delta, clamp=clamp)
    bent = sk.add(profile, start, {k: v for k, v in delta.items() if k not in HIPS}, clamp=clamp)
    return _grounded(profile, start, bent, pose, frame), frozenset(dropped)


def _foot(profile: sk.SkeletonProfile, start: sk.SkeletonPose, frame: DanceFrame, foot: str, clamp: bool) -> sk.Frame:
    """Where ``frame`` puts ``foot`` before any hold. A hold's frame recurs for every picture of its contact, so the
    answer is kept, keyed by everything that decides it."""
    joints = tuple(sorted(frame.joints.items()))
    return _foot_kept(profile, start, frame.root, joints, frame.planted, frame.support, foot, clamp)


@lru_cache(maxsize=512)
def _foot_kept(
    profile: sk.SkeletonProfile,
    start: sk.SkeletonPose,
    root: tuple[float, float, float],
    joints: tuple[tuple[str, float], ...],
    planted: frozenset[str],
    support: str,
    foot: str,
    clamp: bool,
) -> sk.Frame:
    frame = DanceFrame(0.0, root, dict(joints), None, planted, support, None)
    return sk.world(profile, _posed(profile, start, frame, clamp)[0])[foot]


@lru_cache(maxsize=64)
def _standing(profile: sk.SkeletonProfile, start: sk.SkeletonPose) -> Mapping[str, sk.Frame]:
    return sk.world(profile, start)


def _target(profile: sk.SkeletonProfile, start: sk.SkeletonPose, hold: FootHold, now: sk.Frame, foot: str,
            clamp: bool) -> sk.Frame:
    """Where ``hold`` keeps ``foot``: where it landed while planted; in the air, where the dance puts it now moved by
    ``weight`` of the correction the foot carried when it was lifted."""
    landed = _foot(profile, start, hold.landed, foot, clamp)
    if hold.lifted is None:
        return landed
    lifted = _foot(profile, start, hold.lifted, foot, clamp)
    moved = (landed.origin - lifted.origin) * hold.weight
    turn = sk.Quaternion.slerp(sk.Quaternion(), landed.rotation * lifted.rotation.inverse(), hold.weight)
    return sk.Frame(now.origin + moved, turn * now.rotation)


def _reached(
    profile: sk.SkeletonProfile, start: sk.SkeletonPose, frame: DanceFrame, pose: sk.SkeletonPose, clamp: bool
) -> sk.SkeletonPose:
    """``pose`` with each held foot's leg solved to put that foot where its hold keeps it. Where a planted foot was set
    down farther from the hip than the leg reaches, the body first comes down until it reaches, and no further."""
    world = sk.world(profile, pose)
    targets = {}
    for foot, hold in sorted(frame.holds.items()):
        chain = LEGS.get(foot)
        if chain is not None and all(j in world for j in chain):
            targets[foot] = (chain, hold, _target(profile, start, hold, world[foot], foot, clamp))
    drop = max((_short(profile, world, chain, target) for chain, hold, target in targets.values()
                if hold.lifted is None), default=0.0)
    root = pose.root
    if drop > 0.0:
        root = sk.Frame(root.origin + sk.Vec3(0.0, drop, 0.0), root.rotation)
        world = sk.world(profile, sk.SkeletonPose(root, pose.values))
    values = pose.as_dict()
    for chain, _, target in targets.values():
        values.update(_leg(profile, world[sk.joint(chain[0]).parent], chain, values, target))
    return sk.pose(profile, values, root=root, clamp=clamp)


def _short(profile: sk.SkeletonProfile, world: Mapping[str, sk.Frame], chain: tuple[str, ...], target: sk.Frame) -> float:
    """How far the hip must come down (along +y, the skeleton's down) for the leg of ``chain`` to reach ``target``
    with the knee kept just short of straight; zero when it already reaches."""
    reach = REACH * sum(profile.offset(name).length for name in chain[1:])
    hip, goal = world[chain[0]].origin, target.origin
    across = math.hypot(goal.x - hip.x, goal.z - hip.z)
    height = goal.y - math.sqrt(max(reach * reach - across * across, 0.0))  # the highest a hip that reaches stands
    return max(height - hip.y, 0.0)


def _matrix(q: sk.Quaternion) -> np.ndarray:
    w, x, y, z = q.w, q.x, q.y, q.z
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def _about(axis: sk.Vec3, angle: float) -> np.ndarray:
    """The turn by ``angle`` about a unit ``axis`` (Rodrigues), as :func:`skeleton.compose` turns one control."""
    x, y, z = axis.x, axis.y, axis.z
    s, c = math.sin(angle), math.cos(angle)
    t = 1 - c
    return np.array([
        [c + t * x * x, t * x * y - s * z, t * x * z + s * y],
        [t * x * y + s * z, c + t * y * y, t * y * z - s * x],
        [t * x * z - s * y, t * y * z + s * x, c + t * z * z],
    ])


def _turned(m: np.ndarray) -> np.ndarray:
    """The rotation vector of the turn ``m``."""
    cos = min(1.0, max(-1.0, (np.trace(m) - 1) / 2))
    angle = math.acos(cos)
    skew = np.array([m[2, 1] - m[1, 2], m[0, 2] - m[2, 0], m[1, 0] - m[0, 1]])
    if angle < 1e-9:
        return skew / 2
    if math.pi - angle < 1e-6:  # half a turn: the axis is read from the symmetric part
        axis = np.sqrt(np.maximum(np.diag(m) - cos, 0) / (1 - cos))
        return axis * angle
    return skew * (angle / (2 * math.sin(angle)))


def _leg(
    profile: sk.SkeletonProfile, hips: sk.Frame, chain: tuple[str, ...], values: Mapping[str, float], target: sk.Frame
) -> dict[str, float]:
    """The leg controls that bring the end of ``chain`` nearest ``target``, inside this character's limits."""
    links = []  # per joint: offset, rest turn, and its rotate controls as (axis, control) in order
    for name in chain:
        joint = sk.joint(name)
        offset = profile.offset(name)
        turns = [(d.axis, f"{name}.{d.name}") for d in joint.dofs if d.kind == "rotate"]
        links.append((np.array([offset.x, offset.y, offset.z]), _matrix(joint.rest), turns))
    controls = [c for _, _, turns in links for _, c in turns if c in profile.controls]
    limits = [profile.limits_of(c) for c in controls]
    free = [i for i, (low, high) in enumerate(limits) if high > low]
    if not free:
        return {}
    x0 = np.array([min(max(values.get(controls[i], 0.0), limits[i][0]), limits[i][1]) for i in free])
    radius = profile.proportions.head_radius_m
    base_at = np.array([hips.origin.x, hips.origin.y, hips.origin.z])
    base_turn = _matrix(hips.rotation)
    goal_at = np.array([target.origin.x, target.origin.y, target.origin.z])
    goal_turn = _matrix(target.rotation)
    slot = {controls[i]: n for n, i in enumerate(free)}

    def end(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        at, turn = base_at, base_turn
        for offset, rest, turns in links:
            local = rest
            for axis, control in turns:
                angle = float(x[slot[control]]) if control in slot else values.get(control, 0.0)
                local = local @ _about(axis, angle)
            at = at + turn @ offset
            turn = turn @ local
        return at, turn

    def misses(x: np.ndarray) -> np.ndarray:
        at, turn = end(x)
        return np.concatenate(((at - goal_at) / radius, _turned(goal_turn @ turn.T) * TURN_RADII, STAY * (x - x0)))

    low = np.array([limits[i][0] for i in free])
    high = np.array([limits[i][1] for i in free])
    found = least_squares(misses, x0, bounds=(low, high), method="trf", max_nfev=MAX_EVALUATIONS)
    best = found.x if found.cost <= 0.5 * float(np.sum(misses(x0) ** 2)) else x0
    if not np.all(np.isfinite(best)):
        return {}
    return {controls[i]: float(v) for i, v in zip(free, best, strict=True)}


def _grounded(
    profile: sk.SkeletonProfile, start: sk.SkeletonPose, bent: sk.SkeletonPose, pose: sk.SkeletonPose, frame: DanceFrame
) -> sk.SkeletonPose:
    """``pose`` carried along the vertical by what the joints alone (``bent``) moved the lowest of ``frame``'s
    planted feet from where ``start`` has it, so that at a root of zero that foot stands on the floor."""
    if frame.support == "seat" or not frame.planted:
        return pose
    at, floor = sk.world(profile, bent), _standing(profile, start)
    lifts = [floor[foot].origin.y - at[foot].origin.y for foot in sorted(frame.planted) if foot in at]
    if not lifts or min(lifts) == 0.0:
        return pose
    root = pose.root
    return sk.SkeletonPose(sk.Frame(root.origin + sk.Vec3(0.0, min(lifts), 0.0), root.rotation), pose.values)


def _joints(joints: Mapping[str, float]) -> Mapping[str, float]:
    if not isinstance(joints, Mapping):
        raise sk.SkeletonSchemaError("a frame's joints are a mapping", path="joints", actual=type(joints).__name__)
    return joints

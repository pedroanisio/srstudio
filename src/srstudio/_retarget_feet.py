"""Feet that stand still in the clip stand still on the character (ADR 0188).

Retargeting by rotations keeps every bone's direction, so on a character of other proportions the hips travel the
clip's path scaled by pelvis height while the legs are another length: a foot the clip holds still drifts. Here a
foot is planted where the clip's foot joint is near the ground and slow (``PLANT_HEIGHT_M``, ``PLANT_SPEED_M_S``);
while planted, the character's foot joint is held at one point, the mean of where it would have been, and the leg is
solved to reach it: the knee bends to the distance, the thigh swings on the shortest arc onto the line, and the foot
keeps the turn in the world the clip gives it. In the ``BLEND_S`` either side of a plant the hold eases in and out, so
a foot never jumps. Everything else in the pose is untouched.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from . import motion_bridge as mb
from . import skeleton as sk
from ._retarget_errors import RetargetInputError
from ._retarget_pose import ANKLE_SHARE, Tally, clip_scale
from .limbs.math3d import Frame, Quaternion, Vec3

# A planted foot in srlocations' walk sits 2 mm under its rest height (the take stands with soft knees) and moves less
# than a millimetre a second (the record's six-decimal rounding); the lowest foot in flight is 15 mm up, and a foot
# that low is moving at 0.3 m/s or more. 10 mm and 0.1 m/s sit between the two with room either side.
PLANT_HEIGHT_M = 0.01  # how far over its standing height the clip's foot joint may be and still be planted
PLANT_SPEED_M_S = 0.1  # how fast it may move, the faster of the steps into and out of the frame
MAX_PLANT_HEIGHT_M, MAX_PLANT_SPEED_M_S = 0.5, 5.0
BLEND_S = 0.1  # seconds over which a hold eases in before a plant and out after it: three frames at 30 fps
SIDES = ("left", "right")
LEG = ("upper_leg", "lower_leg", "foot")
REACH = 1e-9  # metres: a target this close to the hip gives the thigh no direction to swing


@dataclass(frozen=True)
class Plant:
    """A span of clip frames, ``first`` to ``last`` inclusive, in which one foot stands still."""

    side: str
    first: int
    last: int
    start_s: float
    end_s: float


@dataclass(frozen=True)
class FootLock:
    """Where the character's foot joint is held through one plant, in world metres, and the farthest the solved leg
    left it from there in a sample of the plant (0 when the leg reached it every time)."""

    side: str
    start_s: float
    end_s: float
    target: Vec3
    worst_miss_m: float


def _threshold(value: object, path: str, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= high:
        raise RetargetInputError("a threshold above 0", path=path, actual=value, expected=[0, high])
    return float(value)


def plants(
    clip: mb.MotionClip, *, height_m: float = PLANT_HEIGHT_M, speed_m_s: float = PLANT_SPEED_M_S
) -> tuple[Plant, ...]:
    """Every span in which a foot of the clip is planted, ordered by start and then side."""
    height = _threshold(height_m, "height_m", MAX_PLANT_HEIGHT_M)
    speed = _threshold(speed_m_s, "speed_m_s", MAX_PLANT_SPEED_M_S)
    places = [clip.positions(i) for i in range(clip.frame_count)]
    standing = ANKLE_SHARE * sk.JOINT_TABLE.reference_height_m * clip_scale(clip)
    found = []
    for side in SIDES:
        foot = f"{side}_foot"
        down = []
        for i, place in enumerate(places):
            near = [places[j][foot] for j in (i - 1, i + 1) if 0 <= j < len(places)]
            moving = max((math.dist(place[foot], other) * clip.fps for other in near), default=0.0)
            down.append(-place[foot][1] - standing <= height and moving <= speed)
        i = 0
        while i < len(down):
            if not down[i]:
                i += 1
                continue
            first = i
            while i + 1 < len(down) and down[i + 1]:
                i += 1
            found.append(Plant(side, first, i, clip.frames[first].time_s, clip.frames[i].time_s))
            i += 1
    return tuple(sorted(found, key=lambda p: (p.first, SIDES.index(p.side))))


def check_plants(found: object, clip: mb.MotionClip) -> tuple[Plant, ...]:
    if not isinstance(found, (tuple, list)) or any(not isinstance(p, Plant) for p in found):
        raise RetargetInputError("plants are a sequence of Plant", path="plants", actual=type(found).__name__)
    for p in found:
        if p.side not in SIDES or not 0 <= p.first <= p.last < clip.frame_count:
            raise RetargetInputError(
                "a plant of a foot on frames the clip has", path="plants", actual=[p.side, p.first, p.last]
            )
    return tuple(found)


def has_leg(profile: sk.SkeletonProfile, side: str) -> bool:
    return all(profile.has(f"{side}_{part}") for part in LEG)


def _smooth(u: float) -> float:
    return u * u * (3 - 2 * u)


@dataclass(frozen=True)
class _Hold:
    plant: Plant
    target: Vec3
    ease_in: Vec3  # from where the foot would be at the plant's first frame to the target
    ease_out: Vec3  # likewise at its last frame


class LockPlan:
    """The holds of one clip on one profile, which give a foot's goal at any time on the clip's clock."""

    def __init__(self, holds: tuple[_Hold, ...]) -> None:
        self._holds = holds

    @classmethod
    def build(cls, profile: sk.SkeletonProfile, poses: Sequence[sk.SkeletonPose], found: Sequence[Plant]) -> LockPlan:
        """Each plant's target is the mean of where the unlocked foot stands over it."""
        holds = []
        for plant in found:
            if not has_leg(profile, plant.side):
                continue
            foot = f"{plant.side}_foot"
            spots = [sk.world(profile, poses[i])[foot].origin for i in range(plant.first, plant.last + 1)]
            total = Vec3()
            for spot in spots:
                total = total + spot
            target = total * (1 / len(spots))
            holds.append(_Hold(plant, target, target - spots[0], target - spots[-1]))
        return cls(tuple(holds))

    @property
    def holds(self) -> tuple[tuple[Plant, Vec3], ...]:
        return tuple((hold.plant, hold.target) for hold in self._holds)

    def goal(self, side: str, time_s: float, free: Vec3) -> tuple[Vec3, bool] | None:
        """Where the foot joint should be at ``time_s`` given where it would be unlocked (``free``), and whether the
        foot is planted then; None when no hold reaches this time."""
        best: tuple[float, Vec3] | None = None
        for hold in self._holds:
            plant = hold.plant
            if plant.side != side:
                continue
            if plant.start_s <= time_s <= plant.end_s:
                return hold.target, True
            gap = plant.start_s - time_s if time_s < plant.start_s else time_s - plant.end_s
            if gap < BLEND_S and (best is None or gap < best[0]):
                shift = hold.ease_in if time_s < plant.start_s else hold.ease_out
                best = (gap, free + shift * _smooth(1 - gap / BLEND_S))
        return None if best is None else (best[1], False)


def _arc(a: Vec3, b: Vec3, spare: Vec3) -> Quaternion:
    """The shortest turn taking direction ``a`` onto ``b``; half a turn about ``spare`` when they are opposite."""
    a, b = a.unit(), b.unit()
    axis = a.cross(b)
    if axis.length < 1e-12:
        return Quaternion() if a.dot(b) > 0 else Quaternion.axis_angle(spare, math.pi)
    return Quaternion.axis_angle(axis, math.atan2(axis.length, a.dot(b)))


def _read(
    profile: sk.SkeletonProfile,
    joint: sk.Joint,
    local: Quaternion,
    values: dict[str, float],
    tally: Tally,
    time_s: float,
) -> Quaternion:
    """Read ``local`` (a joint's turn on its parent) into its controls; give back the turn they hold."""
    keys = joint.controls
    limits = [profile.limits_of(key) for key in keys]
    angles, _ = sk.decompose(
        joint.rest.inverse() * local, [dof.axis for dof in joint.dofs], [values.get(k, 0.0) for k in keys], limits
    )
    held = joint.rest
    for key, dof, angle, bounds in zip(keys, joint.dofs, angles, limits, strict=True):
        values[key] = tally.hold(key, angle, bounds, time_s)
        held = held * Quaternion.axis_angle(dof.axis, values[key])
    return held


def reach(
    profile: sk.SkeletonProfile,
    values: Mapping[str, float],
    root: Frame,
    side: str,
    target: Vec3,
    tally: Tally,
    time_s: float,
    *,
    turn: Quaternion | None = None,
) -> dict[str, float]:
    """``values`` with one leg solved so its foot joint reaches ``target`` and the foot keeps its turn in the world,
    or takes ``turn`` (a world turn) when one is given, as a foot laid flat on the floor does. The knee's twist is
    kept; a target out of reach leaves the leg straight toward it, short by the miss."""
    upper, lower, foot = (sk.joint(f"{side}_{part}") for part in LEG)
    frames = sk.world(profile, sk.pose(profile, values, root=root))
    hip = frames[upper.name].origin
    thigh, shin = profile.offset(lower.name), profile.offset(foot.name)
    span = target - hip
    if span.length < REACH:
        return dict(values)
    out = dict(values)
    cosine = (span.length**2 - thigh.length**2 - shin.length**2) / (2 * thigh.length * shin.length)
    stretch = lower.dof("stretch")
    low, high = profile.limits_of(f"{lower.name}.stretch")
    bend = min(high, max(low, -math.acos(max(-1.0, min(1.0, cosine)))))  # a knee folds on negative stretch
    out[f"{lower.name}.stretch"] = bend
    twist = lower.dof("twist_in_out")
    knee = lower.rest * Quaternion.axis_angle(stretch.axis, bend)
    knee = knee * Quaternion.axis_angle(twist.axis, out.get(f"{lower.name}.twist_in_out", 0.0))
    upper_world = frames[upper.name].rotation
    reached = upper_world.rotate(thigh) + (upper_world * knee).rotate(shin)
    swung = _arc(reached, span, upper_world.rotate(stretch.axis)) * upper_world
    held = _read(profile, upper, frames["hips"].rotation.inverse() * swung, out, tally, time_s)
    shank = frames["hips"].rotation * held * knee
    kept = frames[foot.name].rotation if turn is None else turn
    _read(profile, foot, shank.inverse() * kept, out, tally, time_s)
    return out


def lock(
    profile: sk.SkeletonProfile, plan: LockPlan, values: Mapping[str, float], root: Frame, time_s: float, tally: Tally
) -> tuple[dict[str, float], dict[str, float]]:
    """``values`` with each foot that has a goal at ``time_s`` solved onto it, and how far each planted foot missed."""
    out = dict(values)
    misses: dict[str, float] = {}
    goals = {}
    for side in SIDES:
        if not has_leg(profile, side):
            continue
        free = sk.world(profile, sk.pose(profile, out, root=root))[f"{side}_foot"].origin
        goal = plan.goal(side, time_s, free)
        if goal is not None:
            out = reach(profile, out, root, side, goal[0], tally, time_s)
            goals[side] = goal
    if goals:
        frames = sk.world(profile, sk.pose(profile, out, root=root))
        for side, (point, planted) in goals.items():
            if planted:
                misses[side] = frames[f"{side}_foot"].origin.distance(point)
    return out, misses


def foot_slip(profile: sk.SkeletonProfile, poses: Sequence[sk.SkeletonPose], found: Sequence[Plant]) -> float:
    """The farthest a foot joint of ``profile`` moves, in metres, from where it stands at the first frame of a plant,
    over every plant its leg has. ``poses`` are one per clip frame."""
    worst = 0.0
    for plant in found:
        if not isinstance(plant, Plant) or not 0 <= plant.first <= plant.last < len(poses):
            raise RetargetInputError(
                "a plant on frames the poses hold", path="plants", actual=repr(plant)[:120], expected=len(poses)
            )
        if not has_leg(profile, plant.side):
            continue
        foot = f"{plant.side}_foot"
        start = sk.world(profile, poses[plant.first])[foot].origin
        for i in range(plant.first + 1, plant.last + 1):
            worst = max(worst, sk.world(profile, poses[i])[foot].origin.distance(start))
    return worst

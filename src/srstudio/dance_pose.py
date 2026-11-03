"""A dance frame on one character's skeleton (ADR 0186): the step from style-free moves to a pose any style can draw.

:func:`dance.sample` gives the root's translation in head radii and ``"joint.dof"`` deltas in radians.
:func:`dance_pose` adds them onto a :class:`skeleton.SkeletonPose` of a :class:`skeleton.SkeletonProfile`: the root
becomes the hips' ``right``, ``up`` and ``forward`` translations, in metres of that character's head radius, so a
big-headed cartoon bobs more than a realistic figure by the same share; each joint delta adds onto the base pose.

A frame's ``floor`` (ADR 0194) moves and turns the base's root: ``right``, ``forward`` and ``up`` in hip heights of this
character along the base's own axes, ``turn`` about the vertical, so a phrase's steps scale with the legs that take
them. The root's head radii then ride on the turned body.

A delta on a joint the character lacks (a finger of a mitten hand, a joint ``omit`` removed) is dropped and named in
:attr:`DancePose.dropped`, never applied elsewhere. A target outside the canonical skeleton is refused, and a value
past a joint's limit is refused unless ``clamp`` asks for it to be clamped, as :func:`skeleton.add` does.

:func:`body_series` reads the swing a dance shows on a character, the head's travel and roll and the neck's lean,
frame by frame, for :func:`dance.measure_swing` (ADR 0201).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from . import skeleton as sk
from ._dance_model import DanceError
from ._dance_phrase import Floor
from ._dance_sample import MAX_FRAMES, DanceFrame

HIPS = ("hips.right", "hips.up", "hips.forward")  # the root's translations, in dance.ROOT's order


@dataclass(frozen=True)
class DancePose:
    """A frame danced on a character: the pose, and the canonical controls the character has no joint for."""

    pose: sk.SkeletonPose
    dropped: frozenset[str]


def dance_pose(
    profile: sk.SkeletonProfile, frame: DanceFrame, *, base: sk.SkeletonPose | None = None, clamp: bool = False
) -> DancePose:
    """``frame`` danced from ``base`` (the character's rest pose by default) on ``profile``."""
    start = on_floor(profile, base if base is not None else sk.rest_pose(profile), frame.floor)
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
    return DancePose(sk.add(profile, start, delta, clamp=clamp), frozenset(dropped))


UP_AXIS = sk.Vec3(0.0, 1.0, 0.0)  # y points down, so a turn about +y takes forward toward the right


def on_floor(profile: sk.SkeletonProfile, base: sk.SkeletonPose, floor: Floor) -> sk.SkeletonPose:
    """``base`` carried by ``floor``: its root moved in hip heights along its own axes and turned about the
    vertical; its controls unchanged."""
    if not isinstance(floor, Floor):
        raise sk.SkeletonSchemaError("a frame's floor is a dance.Floor", path="floor", actual=type(floor).__name__)
    if floor == Floor():
        return base
    height = profile.pelvis_height
    step = sk.Vec3(floor.right * height, -floor.up * height, floor.forward * height)
    root = base.root
    turned = sk.Frame(
        root.origin + root.rotation.rotate(step), root.rotation * sk.Quaternion.axis_angle(UP_AXIS, floor.turn)
    )
    return sk.SkeletonPose(turned, base.values)


def _joints(joints: Mapping[str, float]) -> Mapping[str, float]:
    if not isinstance(joints, Mapping):
        raise sk.SkeletonSchemaError("a frame's joints are a mapping", path="joints", actual=type(joints).__name__)
    return joints


@dataclass(frozen=True)
class BodySeries:
    """A dance as the picture of a character facing the camera shows it, one value per frame: the head's centre
    ``across`` (toward the character's right) and ``up`` from the rest pose's hips, in that character's head radii;
    the head's ``roll``, joint to crown, and the neck's ``lean``, neck to head joint, in radians from straight up,
    positive toward the character's right."""

    across: tuple[float, ...]
    up: tuple[float, ...]
    roll: tuple[float, ...]
    lean: tuple[float, ...]


def _side(a: sk.Vec3, b: sk.Vec3) -> float:
    """The angle from straight up of the line from ``a`` to ``b`` in the picture's plane (y is down)."""
    return math.atan2(b.x - a.x, a.y - b.y)


def body_series(
    profile: sk.SkeletonProfile,
    frames: Iterable[DanceFrame],
    *,
    base: sk.SkeletonPose | None = None,
    clamp: bool = False,
) -> BodySeries:
    """``frames`` danced on ``profile`` through :func:`dance_pose`, read as a :class:`BodySeries`; at most
    ``MAX_FRAMES`` frames are read. The head's centre is half way from its joint to its crown."""
    start = base if base is not None else sk.rest_pose(profile)
    radius = profile.proportions.head_radius_m
    hips = sk.world(profile, start)["hips"].origin
    rows: list[tuple[float, float, float, float]] = []
    for n, frame in enumerate(frames):
        if n >= MAX_FRAMES:
            raise DanceError(f"a body series reads at most {MAX_FRAMES} frames", path="frames")
        if not isinstance(frame, DanceFrame):
            raise DanceError(f"frames are dance.DanceFrame, not {type(frame).__name__}", path=f"frames[{n}]")
        pose = dance_pose(profile, frame, base=start, clamp=clamp).pose
        joints, crown = sk.world(profile, pose), sk.tips(profile, pose)["head"]
        head = joints["head"].origin
        centre_x, centre_y = (head.x + crown.x) / 2, (head.y + crown.y) / 2
        rows.append(
            (
                (centre_x - hips.x) / radius,
                (hips.y - centre_y) / radius,
                _side(head, crown),
                _side(joints["neck"].origin, head),
            )
        )
    if not rows:
        raise DanceError("a body series reads at least one frame", path="frames")
    across, up, roll, lean = (tuple(column) for column in zip(*rows, strict=True))
    return BodySeries(across, up, roll, lean)

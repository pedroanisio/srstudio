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
a move, whose root is in head radii. A planted foot may still slide along the floor, and the higher of two planted
feet may leave it. A ``seat`` is held up by what it sits on and is not carried.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from . import skeleton as sk
from ._dance_sample import DanceFrame

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
    start = base if base is not None else sk.rest_pose(profile)
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
    return DancePose(_grounded(profile, start, bent, pose, frame), frozenset(dropped))


def _grounded(
    profile: sk.SkeletonProfile, start: sk.SkeletonPose, bent: sk.SkeletonPose, pose: sk.SkeletonPose, frame: DanceFrame
) -> sk.SkeletonPose:
    """``pose`` carried along the vertical by what the joints alone (``bent``) moved the lowest of ``frame``'s
    planted feet from where ``start`` has it, so that at a root of zero that foot stands on the floor."""
    if frame.support == "seat" or not frame.planted:
        return pose
    at, floor = sk.world(profile, bent), sk.world(profile, start)
    lifts = [floor[foot].origin.y - at[foot].origin.y for foot in sorted(frame.planted) if foot in at]
    if not lifts or min(lifts) == 0.0:
        return pose
    root = pose.root
    return sk.SkeletonPose(sk.Frame(root.origin + sk.Vec3(0.0, min(lifts), 0.0), root.rotation), pose.values)


def _joints(joints: Mapping[str, float]) -> Mapping[str, float]:
    if not isinstance(joints, Mapping):
        raise sk.SkeletonSchemaError("a frame's joints are a mapping", path="joints", actual=type(joints).__name__)
    return joints

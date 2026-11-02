"""A dance frame on one character's skeleton (ADR 0186): the step from style-free moves to a pose any style can draw.

:func:`dance.sample` gives the root's translation in head radii and ``"joint.dof"`` deltas in radians.
:func:`dance_pose` adds them onto a :class:`skeleton.SkeletonPose` of a :class:`skeleton.SkeletonProfile`: the root
becomes the hips' ``right``, ``up`` and ``forward`` translations, in metres of that character's head radius, so a
big-headed cartoon bobs more than a realistic figure by the same share; each joint delta adds onto the base pose.

A delta on a joint the character lacks (a finger of a mitten hand, a joint ``omit`` removed) is dropped and named in
:attr:`DancePose.dropped`, never applied elsewhere. A target outside the canonical skeleton is refused, and a value
past a joint's limit is refused unless ``clamp`` asks for it to be clamped, as :func:`skeleton.add` does.
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
    return DancePose(sk.add(profile, start, delta, clamp=clamp), frozenset(dropped))


def _joints(joints: Mapping[str, float]) -> Mapping[str, float]:
    if not isinstance(joints, Mapping):
        raise sk.SkeletonSchemaError("a frame's joints are a mapping", path="joints", actual=type(joints).__name__)
    return joints

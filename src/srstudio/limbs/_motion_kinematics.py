"""Elbow-pole winding and final constrained arm/hand solve.

Derived winding caches remain bounded and owned by each public Motion instance.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import replace
from typing import TYPE_CHECKING

from ._motion_interpolation import smooth
from .constraints import hand_pose, reach
from .errors import LimbError
from .math3d import Quaternion, Vec3, bounded
from .model import ArmPose, HandControl, HandPose

if TYPE_CHECKING:
    from .motion import Action, Motion


def pole_geometry(motion: Motion, action: Action, time: float, goal: Vec3) -> tuple[Vec3, Vec3, float]:
    root = motion.root.sample(time)
    shoulder = root.point(motion.arm.shoulder)
    default = root.point(motion.arm.shoulder + Vec3(1 if motion.arm.side == 'right' else -1, 0, 0))
    delta = goal - shoulder
    direction = delta.unit() if delta.length > 1e-12 else Vec3(0, 1, 0)

    def bend(pole: Vec3) -> Vec3:
        toward = pole - shoulder
        projected = toward - direction * toward.dot(direction)
        if projected.length < 1e-10:
            axis = Vec3(1, 0, 0) if abs(direction.x) < 0.9 else Vec3(0, 0, 1)
            projected = axis - direction * axis.dot(direction)
        return projected.unit()

    assert action.pole is not None
    a, b = bend(default), bend(action.pole)
    return direction, a, math.atan2(direction.dot(a.cross(b)), a.dot(b))


def pole_path(motion: Motion, action: Action, start: float, end: float) -> tuple[tuple[float, ...], tuple[float, ...]]:
    key = (id(action), start, end)
    if key in motion._pole_paths:
        return motion._pole_paths[key]
    knots = {start, end, action.stroke_at}
    knots.update(k.time for k in motion.root.keys)
    for contact in motion.contacts:
        if action.start < contact.start < contact.end < action.end:
            knots.update((contact.start, contact.end))
            knots.update(k.time for k in contact.target.keys)
    ordered = sorted(t for t in knots if start <= t <= end)
    if (len(ordered) - 1) * 32 + 1 > 100000:
        raise LimbError('pole winding exceeds its 100000-sample preparation budget', code='budget')
    times = [ordered[0]]
    for a, b in zip(ordered, ordered[1:], strict=False):
        for i in range(1, 33):
            t = b if i == 32 else a + (b - a) * i / 32
            if t > times[-1]:
                times.append(t)
    angles: list[float] = []
    for t in times:
        goal = motion._contact_position(action, t, motion._request(t)[0])
        raw = motion._pole_geometry(action, t, goal)[2]
        previous = angles[-1] if angles else raw
        angles.append(previous + math.atan2(math.sin(raw - previous), math.cos(raw - previous)))
    result = (tuple(times), tuple(angles))
    if len(motion._pole_paths) >= 2:
        motion._pole_paths.clear()
    motion._pole_paths[key] = result
    return result


def pole(motion: Motion, action: Action | None, time: float, goal: Vec3) -> Vec3:
    root = motion.root.sample(time)
    shoulder = root.point(motion.arm.shoulder)
    default = root.point(motion.arm.shoulder + Vec3(1 if motion.arm.side == 'right' else -1, 0, 0))
    if action is None or action.pole is None:
        return default
    u = (time - action.start) / action.duration
    arrival = action.preparation or action.stroke
    recovery = action.preparation + action.stroke + action.hold
    weight = smooth(u / arrival) * (1 - smooth((u - recovery) / (1 - recovery)))
    if weight == 0:
        return default
    if weight == 1:
        return action.pole
    start, end = (
        (action.start, action.start + arrival * action.duration)
        if u < arrival
        else (action.start + recovery * action.duration, action.end)
    )
    times, angles = motion._pole_path(action, start, end)
    reference = angles[max(0, bisect_right(times, time) - 1)]
    direction, bend, angle = motion._pole_geometry(action, time, goal)
    angle += 2 * math.pi * round((reference - angle) / (2 * math.pi))
    return shoulder + Quaternion.axis_angle(direction, angle * weight).rotate(bend)


def pose(
    motion: Motion,
    time: float,
    goal: Vec3,
    control: HandControl,
    pole: Vec3,
    orientation: Quaternion | None = None,
    local_orientation: bool = False,
) -> tuple[ArmPose, HandPose, HandControl]:
    profile = replace(motion.arm, shoulder=motion.root.sample(time).point(motion.arm.shoulder))
    arm = reach(profile, goal, pole=pole, policy=motion.reach_policy)
    if orientation is not None:
        relative = orientation if local_orientation else arm.frame.rotation.inverse() * orientation
        x, y, z = (relative.rotate(v) for v in (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)))
        control = replace(
            control,
            wrist_flex=math.asin(max(-1, min(1, -z.y))),
            wrist_deviation=math.atan2(x.y, y.y),
            forearm_twist=math.atan2(z.x, z.z),
        )
    for name, limit in (
        ("wrist_flex", profile.flex_limit),
        ("wrist_deviation", profile.deviation_limit),
        ("forearm_twist", profile.twist_limit),
    ):
        bounded(getattr(control, name), *limit, name)
    hand = hand_pose(motion.hand, control, arm.frame, side=profile.side)
    return arm, hand, control

"""Pure two-leg solving and authored static-support validation; no physics history."""

from __future__ import annotations

import math
from bisect import bisect_right

from ._body_types import DOWN, BodyPose, BodyScore, LegPose, fail
from .limbs.constraints import reach
from .limbs.errors import LimbError
from .limbs.math3d import Frame, Vec3
from .limbs.model import ArmProfile
from .limbs.motion import smooth


def hull(points):
    """Counterclockwise convex support footprint in the ground x/z plane."""

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    points = sorted(set(points))
    sides = []
    for order in (points, list(reversed(points))):
        side = []
        for point in order:
            while len(side) >= 2 and cross(side[-2], side[-1], point) <= 0:
                side.pop()
            side.append(point)
        sides.extend(side[:-1])
    return tuple(sides)


def margin(polygon, point: Vec3) -> float:
    return min(
        ((b[0] - a[0]) * (point.z - a[1]) - (b[1] - a[1]) * (point.x - a[0])) / math.hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True)
    )


def footprint(sole, profile):
    return tuple(
        sole.point(Vec3(x, 0, z))
        for x, z in (
            (-profile.foot_width / 2, -profile.heel),
            (profile.foot_width / 2, -profile.heel),
            (profile.foot_width / 2, profile.toe),
            (-profile.foot_width / 2, profile.toe),
        )
    )


def sample(score: BodyScore, time: float) -> BodyPose:
    keys = score.roots
    i = max(0, bisect_right([k.time for k in keys], time) - 1)
    a, b = keys[i], keys[min(i + 1, len(keys) - 1)]
    u = smooth((time - a.time) / (b.time - a.time)) if b.time > a.time else 0
    root = Frame(a.root.origin.lerp(b.root.origin, u), a.root.rotation.slerp(b.root.rotation, u))
    torso = Frame(root.origin, root.rotation * a.torso.slerp(b.torso, u))
    profile = score.profile
    torso_angle = math.acos(max(-1, min(1, torso.rotation.rotate(DOWN).dot(DOWN))))
    if torso_angle > profile.torso_limit + 1e-9:
        raise fail(f'sample[{time}].torso', torso_angle, f'tilt <= {profile.torso_limit} radians', 'body.joint')
    legs = []
    support: list[tuple[float, float]] = []
    com = torso.point(Vec3(0, -0.45 * profile.torso_height, 0)) * 0.6
    for foot in sorted(score.stance, key=lambda f: f.side):
        sole, planted = foot.frame, True
        for step in score.steps:
            if step.side != foot.side or time < step.start:
                continue
            if time >= step.end:
                sole = step.target
                continue
            u = (time - step.start) / (step.end - step.start)
            weight = smooth(u)
            lift = 64 * u**3 * (1 - u) ** 3 * step.clearance
            sole = Frame(
                sole.origin.lerp(step.target.origin, weight) - Vec3(0, lift, 0),
                sole.rotation.slerp(step.target.rotation, weight),
            )
            planted = False
            break
        hip = root.point(Vec3((-1 if foot.side == 'left' else 1) * profile.hip_width / 2, 0, 0))
        ankle = sole.point(Vec3(0, -profile.ankle_height, 0))
        try:
            solved = reach(
                ArmProfile(
                    shoulder=hip,
                    upper=profile.thigh,
                    forearm=profile.shin,
                    side=foot.side,
                    elbow_limit=profile.knee_limits,
                ),
                ankle,
                pole=hip + root.rotation.rotate(Vec3(0, 0, 1)),
            )
        except LimbError as exc:
            raise fail(
                f'sample[{time}].legs.{foot.side}',
                exc.residual,
                'a reachable ankle inside the knee-flexion envelope',
                'body.joint',
            ) from exc
        hip_angle = math.acos(max(-1, min(1, (solved.elbow - hip).unit().dot(root.rotation.rotate(DOWN)))))
        ankle_angle = math.acos(max(-1, min(1, (ankle - solved.elbow).unit().dot(sole.rotation.rotate(DOWN)))))
        relative = root.rotation.inverse() * sole.rotation
        foot_yaw = relative.rotation_vector.length
        if (
            hip_angle > profile.hip_limit + 1e-9
            or ankle_angle > profile.ankle_limit + 1e-9
            or foot_yaw > profile.foot_yaw_limit + 1e-9
        ):
            raise fail(
                f'sample[{time}].legs.{foot.side}',
                (hip_angle, ankle_angle, foot_yaw),
                {'hip_cone': profile.hip_limit, 'ankle_cone': profile.ankle_limit, 'foot_yaw': profile.foot_yaw_limit},
                'body.joint',
            )
        legs.append(
            LegPose(
                foot.side, hip, solved.elbow, ankle, sole, planted, solved.elbow_angle, hip_angle, ankle_angle, foot_yaw
            )
        )
        com += (hip + solved.elbow) * 0.06 + (solved.elbow + ankle) * 0.03 + sole.origin * 0.02
        if planted:
            support.extend((p.x, p.z) for p in footprint(sole, profile))
    if not support:
        raise fail(f'sample[{time}].support', (), 'at least one planted foot', 'body.support')
    polygon = hull(support)
    distance = margin(polygon, com)
    if distance < profile.support_margin - 1e-9:
        raise fail(
            f'sample[{time}].support',
            {'margin': distance, 'center': (com.x, com.z)},
            f'mass projection at least {profile.support_margin}m inside the support polygon',
            'body.support',
        )
    shoulders = tuple(
        Frame(torso.point(Vec3(x, -profile.torso_height, 0)), torso.rotation)
        for x in (-profile.hip_width * 0.75, profile.hip_width * 0.75)
    )
    return BodyPose(time, root, torso, (shoulders[0], shoulders[1]), (legs[0], legs[1]), com, polygon, distance)

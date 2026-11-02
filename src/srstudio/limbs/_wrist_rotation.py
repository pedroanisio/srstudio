"""Recover Y-X-Z wrist controls near an authored reference without discarding whole turns."""

import math
from dataclasses import replace

from .math3d import Quaternion, Vec3
from .model import ArmProfile, HandControl


def _near(angle: float, reference: float, limits: tuple[float, float]) -> float:
    turn = round((reference - angle) / math.tau)
    low = math.ceil((limits[0] - angle - 1e-10) / math.tau)
    high = math.floor((limits[1] - angle + 1e-10) / math.tau)
    if low <= high:
        turn = max(low, min(high, turn))
    result = angle + turn * math.tau
    # Only absorb floating-point noise at the boundary, never a physically different rotation.
    if limits[0] - 1e-10 <= result <= limits[1] + 1e-10:
        result = max(limits[0], min(limits[1], result))
    return result


def controls(rotation: Quaternion, reference: HandControl, profile: ArmProfile) -> HandControl:
    x, y, z = (rotation.rotate(v) for v in (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)))
    cosine = math.hypot(z.x, z.z)
    flex = math.atan2(-z.y, cosine)
    deviation = reference.wrist_deviation if cosine < 1e-10 else math.atan2(x.y, y.y)
    if cosine < 1e-10:
        # At gimbal lock the outer axes coincide. Keep the authored deviation and solve the remaining twist.
        remaining = rotation * Quaternion.axis_angle(Vec3(0, 0, 1), -deviation)
        column = remaining.rotate(Vec3(1, 0, 0))
        twist = math.atan2(-column.z, column.x)
    else:
        twist = math.atan2(z.x, z.z)
    bounds = (profile.twist_limit, profile.flex_limit, profile.deviation_limit)
    refs = (reference.forearm_twist, reference.wrist_flex, reference.wrist_deviation)
    candidates = []
    for raw in ((twist, flex, deviation), (twist + math.pi, math.pi - flex, deviation + math.pi)):
        angles = tuple(_near(a, r, b) for a, r, b in zip(raw, refs, bounds, strict=True))
        outside = math.hypot(*(max(lo - a, 0, a - hi) for a, (lo, hi) in zip(angles, bounds, strict=True)))
        distance = math.hypot(*(a - r for a, r in zip(angles, refs, strict=True)))
        candidates.append((outside, distance, angles))
    twist, flex, deviation = min(candidates)[2]
    return replace(reference, forearm_twist=twist, wrist_flex=flex, wrist_deviation=deviation)

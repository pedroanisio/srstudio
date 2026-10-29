"""Analytic two-segment spatial IK, explicit reach policy, FK and articulated hand construction."""

from __future__ import annotations

import math

from .errors import Diagnostic, LimbError
from .math3d import Frame, Quaternion, Vec3, along, bounded
from .model import ArmPose, ArmProfile, DigitPose, HandControl, HandPose, HandProfile

_IDENTITY = Quaternion()


def reach(profile: ArmProfile, target: Vec3, *, pole: Vec3 | None = None, policy: str = "strict") -> ArmPose:
    if policy not in ("strict", "clamp"):
        raise LimbError(f"unknown reach policy {policy!r}")
    delta = target - profile.shoulder
    distance = delta.length
    a, b = profile.upper, profile.forearm
    lo_angle, hi_angle = profile.elbow_limit
    # Elbow flexion is zero when straight and pi when fully folded.
    low = math.sqrt(max(0, a * a + b * b + 2 * a * b * math.cos(hi_angle)))
    high = math.sqrt(max(0, a * a + b * b + 2 * a * b * math.cos(lo_angle)))
    limit = min(high, max(low, distance))
    residual = abs(distance - limit)
    diagnostics: tuple[Diagnostic, ...] = ()
    if residual > 1e-8:
        physical = abs(a - b) - 1e-8 <= distance <= a + b + 1e-8
        code = "joint-limit" if physical else "unreachable"
        message = f"target reach {distance:g} is outside {low:g}..{high:g} for this arm"
        if policy == "strict":
            raise LimbError(message, code=code, residual=residual)
        diagnostics = (Diagnostic(code, message, residual),)
    direction = delta.unit() if distance > 1e-12 else Vec3(0, 1, 0)
    toward = (
        pole if pole is not None else profile.shoulder + Vec3(1 if profile.side == "right" else -1, 0, 0)
    ) - profile.shoulder
    bend = toward - direction * toward.dot(direction)
    if bend.length < 1e-10:
        axis = Vec3(1, 0, 0) if abs(direction.x) < 0.9 else Vec3(0, 0, 1)
        bend = axis - direction * axis.dot(direction)
    bend = bend.unit()
    if limit < 1e-10:
        elbow = profile.shoulder + bend * a
    else:
        adjacent = (a * a - b * b + limit * limit) / (2 * limit)
        height = math.sqrt(max(0, a * a - adjacent * adjacent))
        elbow = profile.shoulder + direction * adjacent + bend * height
    wrist = profile.shoulder + direction * limit
    angle = math.acos(max(-1, min(1, (limit * limit - a * a - b * b) / (2 * a * b))))
    across = bend * (1 if profile.side == "right" else -1)
    return ArmPose(
        profile.shoulder, elbow, wrist, along(wrist, wrist - elbow, across=across), angle, residual, diagnostics
    )


def forward(profile: ArmProfile, *, shoulder_rotation: Quaternion = _IDENTITY, elbow: float = 0) -> ArmPose:
    bounded(elbow, *profile.elbow_limit, "elbow")
    joint = profile.shoulder + shoulder_rotation.rotate(Vec3(0, profile.upper, 0))
    q = shoulder_rotation * Quaternion.axis_angle(Vec3(0, 0, 1), -elbow)
    wrist = joint + q.rotate(Vec3(0, profile.forearm, 0))
    return ArmPose(profile.shoulder, joint, wrist, along(wrist, wrist - joint), elbow)


def hand_pose(profile: HandProfile, control: HandControl, frame: Frame, *, side: str = "right") -> HandPose:
    if side not in ("left", "right"):
        raise LimbError("hand side must be left or right")
    names = {d.name for d in profile.digits}
    if not (set(dict(control.curls)) | set(dict(control.joints))) <= names:
        raise LimbError("finger overrides name a digit absent from the hand profile")
    mirror = -1 if side == "left" else 1
    wrist = (
        Quaternion.axis_angle(Vec3(0, 1, 0), control.forearm_twist)
        * Quaternion.axis_angle(Vec3(1, 0, 0), control.wrist_flex)
        * Quaternion.axis_angle(Vec3(0, 0, 1), control.wrist_deviation)
    )
    local = Frame(frame.origin, frame.rotation * wrist)

    def point(v: Vec3) -> Vec3:
        return local.point(Vec3(v.x * mirror, v.y, v.z))

    w, h = profile.palm_width / 2, profile.palm_length
    palm = tuple(
        point(v)
        for v in (
            Vec3(-w * 0.65, 0, 0),
            Vec3(w * 0.65, 0, 0),
            Vec3(w, h, control.cup * w),
            Vec3(-w, h, control.cup * w),
        )
    )
    digits = []
    for digit in profile.digits:
        curl = dict(control.curls).get(digit.name, control.curl)
        maximum = digit.max_flex or tuple(1.3 if i < 2 else 0.9 for i in range(len(digit.lengths)))
        angles = dict(control.joints).get(digit.name, tuple(curl * a for a in maximum))
        if len(angles) != len(digit.lengths) or any(a > b for a, b in zip(angles, maximum, strict=True)):
            raise LimbError(f"joint overrides exceed limits or topology of {digit.name}", code="joint-limit")
        base = digit.base + Vec3(0, 0, control.cup * abs(digit.base.x))
        points = [point(base)]
        yaw = digit.splay * (1 + control.spread) + (control.opposition * 1.1 if digit.thumb else 0)
        q = Quaternion.axis_angle(Vec3(0, 0, 1), yaw)
        if digit.thumb:
            q = q * Quaternion.axis_angle(Vec3(0, 1, 0), -control.opposition * 1.4)
        cursor = base
        for length, angle in zip(digit.lengths, angles, strict=True):
            q = q * Quaternion.axis_angle(Vec3(1, 0, 0), angle)
            cursor = cursor + q.rotate(Vec3(0, length, 0))
            points.append(point(cursor))
        digits.append(DigitPose(digit.name, tuple(points)))
    return HandPose(local, palm, tuple(digits), local.rotation.rotate(Vec3(0, 0, 1)))

"""Turns about the canonical axes: composing a joint's controls and reading a rotation back into them.

Every canonical rotation axis is one of +/-x, +/-y, +/-z (the table refuses any other), so reading a rotation back
into a joint's controls is a Tait-Bryan decomposition in the joint's own order. Of the two solutions the one nearest
a reference is kept (the blend's straight line, or the pose being edited), each angle wrapped by a full turn where
that brings it inside its limits. A joint with fewer than three controls reports the turn it cannot hold as a
residual, in radians, rather than dropping it unseen.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..limbs.math3d import Quaternion, Vec3

Matrix = list[list[float]]
TAU = 2 * math.pi
GIMBAL = 1e-8  # the cosine of the middle angle below which the outer two angles share one degree of freedom


def turn(axis: Vec3, angle: float) -> Quaternion:
    return Quaternion.axis_angle(axis, angle) if angle else Quaternion()


def compose(axes: Sequence[Vec3], angles: Sequence[float]) -> Quaternion:
    """The product of the turns, the first outermost."""
    result = Quaternion()
    for axis, angle in zip(axes, angles, strict=True):
        result = result * turn(axis, angle)
    return result


def angle_of(q: Quaternion) -> float:
    """How far a rotation turns, in 0..pi."""
    return 2 * math.atan2(math.hypot(q.x, q.y, q.z), abs(q.w))


def _matrix(q: Quaternion) -> Matrix:
    w, x, y, z = q.w, q.x, q.y, q.z
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ]


def _index(axis: Vec3) -> tuple[int, float]:
    parts = (axis.x, axis.y, axis.z)
    i = max(range(3), key=lambda k: abs(parts[k]))
    return i, math.copysign(1.0, parts[i])


def _near(angle: float, reference: float, limits: tuple[float, float] | None) -> float:
    """``angle`` moved by whole turns to lie nearest ``reference``, preferring a turn inside ``limits``."""
    options = [angle + TAU * k for k in range(-2, 3)]
    if limits is not None:
        inside = [a for a in options if limits[0] - 1e-9 <= a <= limits[1] + 1e-9]
        options = inside or options
    return min(options, key=lambda a: abs(a - reference))


def _tait_bryan(m: Matrix, i: int, j: int, k: int, hint: float) -> list[tuple[float, float, float]]:
    """Both (a, b, c) with m = R_i(a) R_j(b) R_k(c) about the positive basis axes; ``hint`` is c at a gimbal lock."""
    e = 1.0 if (j - i) % 3 == 1 else -1.0
    cb = math.hypot(m[i][i], m[i][j])
    b = math.atan2(e * m[i][k], cb)  # atan2, because asin loses half the digits next to a right angle
    if cb < GIMBAL:
        # The outer axes align: keep c at the hint and read a from m R_k(-c), which is R_i(a) R_j(b).
        n = _times(m, _basis(k, -hint))
        a = math.atan2(e * n[k][j], n[j][j])
        return [(a, b, hint)]
    a = math.atan2(-e * m[j][k], m[k][k])
    c = math.atan2(-e * m[i][j], m[i][i])
    return [(a, b, c), (a + math.pi, math.pi - b, c + math.pi)]


def _basis(axis: int, angle: float) -> Matrix:
    c, s = math.cos(angle), math.sin(angle)
    if axis == 0:
        return [[1, 0, 0], [0, c, -s], [0, s, c]]
    if axis == 1:
        return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def _times(a: Matrix, b: Matrix) -> Matrix:
    return [[sum(a[r][n] * b[n][c] for n in range(3)) for c in range(3)] for r in range(3)]


def decompose(
    q: Quaternion, axes: Sequence[Vec3], reference: Sequence[float], limits: Sequence[tuple[float, float]] | None = None
) -> tuple[tuple[float, ...], float]:
    """Angles about ``axes`` (one to three distinct canonical axes, the first outermost) whose product is ``q``, nearest
    ``reference``, and the residual turn in radians that those axes cannot hold."""
    n = len(axes)
    bounds = list(limits) if limits is not None else [None] * n
    if n == 1:
        axis = axes[0]
        twist = 2 * math.atan2(q.x * axis.x + q.y * axis.y + q.z * axis.z, q.w)
        angle = _near(twist, reference[0], bounds[0])
        return (angle,), angle_of(turn(axis, angle).inverse() * q)
    full = list(axes)
    for spare in (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)):
        if len(full) < 3 and all(_index(spare)[0] != _index(a)[0] for a in full):
            full.append(spare)
    (i, si), (j, sj), (k, sk) = (_index(a) for a in full)
    hint = reference[2] * sk if n == 3 else 0.0
    choices = []
    for a, b, c in _tait_bryan(_matrix(q), i, j, k, hint):
        signed = (a * si, b * sj, c * sk)
        angles = tuple(_near(v, reference[m], bounds[m]) for m, v in enumerate(signed[:n]))
        residual = angle_of(compose(axes, angles).inverse() * q)
        distance = sum((x - y) ** 2 for x, y in zip(angles, reference, strict=True))
        choices.append((round(residual, 9), distance, angles, residual))
    _, _, angles, residual = min(choices, key=lambda row: row[:2])
    return angles, residual

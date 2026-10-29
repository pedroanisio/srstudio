"""View-dependent artist contours in wrist-anchored, camera-facing canonical units.

Keys use the camera-space palm-normal Z component (-1 back, 0 edge, +1 palm). Vertices correspond
by index across keys. Contours affect only drawing; bone lengths, contact points and motion remain intact.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .errors import LimbError
from .math3d import Vec3, bounded, number

if TYPE_CHECKING:
    from .geometry import Point, ProjectedPose
    from .motion import Sample
    from .projection import Affine, Camera


def _area(points: tuple[tuple[float, float], ...]) -> float:
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, (*points[1:], points[0]), strict=True))


@dataclass(frozen=True)
class ContourKey:
    view: float
    vertices: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        bounded(self.view, -1, 1, "corrective view")
        if not 3 <= len(self.vertices) <= 1024:
            raise LimbError("corrective contours need 3..1024 vertices")
        for point in self.vertices:
            if len(point) != 2:
                raise LimbError("corrective vertices need x and y")
            for value in point:
                number(value, "corrective vertex")
        area = _area(self.vertices)
        if abs(area) < 1e-10:
            raise LimbError("corrective contour must have nonzero signed area")


@dataclass(frozen=True)
class ContourCorrection:
    part: str
    keys: tuple[ContourKey, ...]
    strength: float = 1
    mirror: bool = False

    def __post_init__(self) -> None:
        if not self.part or not 1 <= len(self.keys) <= 128:
            raise LimbError("corrective needs a part and 1..128 view keys")
        if any(a.view >= b.view for a, b in zip(self.keys, self.keys[1:], strict=False)):
            raise LimbError("corrective view keys must be strictly increasing")
        if len({len(key.vertices) for key in self.keys}) != 1:
            raise LimbError("corrective keys must have corresponding vertex counts")
        if any(_area(key.vertices) * _area(self.keys[0].vertices) <= 0 for key in self.keys):
            raise LimbError("corrective keys must preserve contour winding")
        bounded(self.strength, 0, 1, "corrective strength")
        if not isinstance(self.mirror, bool):
            raise LimbError("corrective mirror must be boolean")

    def points(self, view: float) -> tuple[tuple[float, float], ...]:
        bounded(view, -1, 1, "corrective sample view")
        if view <= self.keys[0].view:
            return self.keys[0].vertices
        for a, b in zip(self.keys, self.keys[1:], strict=False):
            if view <= b.view:
                u = (view - a.view) / (b.view - a.view)
                return tuple(
                    (x + (xx - x) * u, y + (yy - y) * u)
                    for (x, y), (xx, yy) in zip(a.vertices, b.vertices, strict=True)
                )
        return self.keys[-1].vertices


def _resample(points: tuple[Point, ...], count: int) -> tuple[Point, ...]:
    lengths = [math.dist(a, b) for a, b in zip(points, (*points[1:], points[0]), strict=True)]
    perimeter = sum(lengths)
    if perimeter < 1e-12:
        raise LimbError("cannot blend a zero-length contour")
    result = []
    for i in range(count):
        distance = i * perimeter / count
        for j, length in enumerate(lengths):
            if distance <= length and length > 0:
                a, b = points[j], points[(j + 1) % len(points)]
                u = distance / length
                result.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
                break
            distance -= length
    return tuple(result)


def apply_correctives(
    pose: ProjectedPose, sample: Sample, camera: Camera, parent: Affine, corrections: tuple[ContourCorrection, ...]
) -> ProjectedPose:
    names = [c.part for c in corrections]
    if len(names) != len(set(names)) or not set(names) <= {p.name for p in pose.parts}:
        raise LimbError("corrective part must resolve uniquely in the projected hand")
    wrist = camera.project(sample.hand.frame.origin)
    along = camera.project(sample.hand.frame.point(Vec3(0, 1, 0))).xy
    dx, dy = along[0] - wrist.xy[0], along[1] - wrist.xy[1]
    length = math.hypot(dx, dy)
    # At a fully end-on wrist the longitudinal axis is undefined. A fixed camera axis keeps the drawing finite.
    ux, uy = (dx / length, dy / length) if length > 1e-7 else (0.0, 1.0)
    view = camera.view.rotation.inverse().rotate(sample.hand.normal).z
    lookup = {c.part: c for c in corrections}
    parts = []
    for part in pose.parts:
        correction = lookup.get(part.name)
        if correction is None or correction.strength == 0:
            parts.append(part)
            continue
        vertices = correction.points(max(-1, min(1, view)))
        projected = []
        for x, y in vertices:
            x *= -1 if correction.mirror else 1
            projected.append(
                parent.inverse().point(
                    (wrist.xy[0] + (uy * x + ux * y) * wrist.scale, wrist.xy[1] + (-ux * x + uy * y) * wrist.scale)
                )
            )
        if correction.strength < 1:
            original = _resample(part.polygon, len(projected))
            u = correction.strength
            projected = [
                (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u) for a, b in zip(original, projected, strict=True)
            ]
        parts.append(replace(part, polygon=tuple(projected), authored=True))
    return replace(pose, parts=tuple(parts))

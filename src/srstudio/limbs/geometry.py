"""Projected limb silhouettes. Perspective is applied once before conversion into the drawing parent's space."""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import unary_union
from shapely.errors import GEOSException
from shapely.geometry import MultiPoint, Polygon
from shapely.geometry import Point as ShapelyPoint

from .correctives import ContourCorrection, apply_correctives
from .errors import LimbError
from .math3d import Vec3, number
from .motion import Sample
from .projection import Affine, Camera

Point = tuple[float, float]
_PARENT = Affine()


@dataclass(frozen=True)
class Part:
    name: str
    polygon: tuple[Point, ...]
    centerline: tuple[Point, ...]
    depth: float
    width: float
    role: str
    authored: bool = False
    holes: tuple[tuple[Point, ...], ...] = ()


@dataclass(frozen=True)
class ProjectedPose:
    parts: tuple[Part, ...]
    shoulder: Point
    elbow: Point
    wrist: Point
    fingertips: tuple[tuple[str, Point], ...]
    palm_view: str
    time: float

    def select(self, names: set[str]) -> ProjectedPose:
        from dataclasses import replace

        return replace(self, parts=tuple(p for p in self.parts if p.name in names))


def _hull(points: list[Point]) -> tuple[Point, ...]:
    points = sorted(set(points))
    if len(points) < 3:
        raise LimbError("projected surface has fewer than three distinct vertices", code="projection")

    def cross(a: Point, b: Point, c: Point) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    low: list[Point] = []
    high: list[Point] = []
    for p in points:
        while len(low) >= 2 and cross(low[-2], low[-1], p) <= 0:
            low.pop()
        low.append(p)
    for p in reversed(points):
        while len(high) >= 2 and cross(high[-2], high[-1], p) <= 0:
            high.pop()
        high.append(p)
    return tuple(low[:-1] + high[:-1])


def ribbon(points: tuple[Point, ...], widths: tuple[float, ...]) -> tuple[Point, ...]:
    """A tapered, round-ended silhouette with bounded miters; an end-on segment becomes a disc."""
    if len(points) < 2 or len(widths) != len(points):
        raise LimbError("ribbon needs matching points and widths")
    if max(math.dist(points[0], p) for p in points) < 1e-7:
        x, y = points[0]
        radius = max(widths) / 2
        return tuple(
            (x + radius * math.cos(i * math.tau / 16), y + radius * math.sin(i * math.tau / 16)) for i in range(16)
        )
    directions = []
    for i in range(len(points)):
        a, b = points[max(0, i - 1)], points[min(len(points) - 1, i + 1)]
        if math.dist(a, b) < 1e-9:
            a, b = points[0], points[-1]
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        directions.append(angle)
    left = [
        (p[0] - math.sin(a) * w / 2, p[1] + math.cos(a) * w / 2)
        for p, a, w in zip(points, directions, widths, strict=True)
    ]
    right = [
        (p[0] + math.sin(a) * w / 2, p[1] - math.cos(a) * w / 2)
        for p, a, w in zip(points, directions, widths, strict=True)
    ]
    start, end = points[0], points[-1]
    cap_end = [
        (
            end[0] + widths[-1] / 2 * math.cos(directions[-1] + math.pi / 2 - i * math.pi / 8),
            end[1] + widths[-1] / 2 * math.sin(directions[-1] + math.pi / 2 - i * math.pi / 8),
        )
        for i in range(1, 8)
    ]
    cap_start = [
        (
            start[0] + widths[0] / 2 * math.cos(directions[0] - math.pi / 2 - i * math.pi / 8),
            start[1] + widths[0] / 2 * math.sin(directions[0] - math.pi / 2 - i * math.pi / 8),
        )
        for i in range(1, 8)
    ]
    return tuple(left + cap_end + list(reversed(right)) + cap_start)


@dataclass(frozen=True)
class Contour:
    exterior: tuple[Point, ...]
    holes: tuple[tuple[Point, ...], ...] = ()


def tube(points: tuple[Point, ...], widths: tuple[float, ...]) -> Contour:
    """Union tapered, round-ended phalanges into a simple contour, preserving genuine enclosed holes."""
    if not 2 <= len(points) <= 64 or len(widths) != len(points):
        raise LimbError("a finger tube needs 2..64 matching points and widths", code="geometry")
    for point, width in zip(points, widths, strict=True):
        if len(point) != 2 or number(width, "finger width") <= 0:
            raise LimbError("finger points need x/y and positive widths", code="geometry")
        for value in point:
            number(value, "finger coordinate")
    try:
        discs = [ShapelyPoint(p).buffer(w / 2, quad_segs=8) for p, w in zip(points, widths, strict=True)]
        segments = [
            MultiPoint((*a.exterior.coords, *b.exterior.coords)).convex_hull
            for a, b in zip(discs, discs[1:], strict=False)
        ]
        merged = unary_union(segments).normalize()
    except GEOSException as exc:
        raise LimbError(f"finger contour union failed: {exc}", code="geometry") from exc
    if not isinstance(merged, Polygon) or merged.is_empty or not merged.is_valid:
        raise LimbError("finger contour union did not produce one valid surface", code="geometry")
    exterior = tuple((float(p[0]), float(p[1])) for p in merged.exterior.coords)[:-1]
    holes = tuple(tuple((float(p[0]), float(p[1])) for p in ring.coords)[:-1] for ring in merged.interiors)
    return Contour(exterior, holes)


def project_pose(
    sample: Sample,
    camera: Camera,
    *,
    width: float,
    parent: Affine = _PARENT,
    thickness: float = 0.09,
    correctives: tuple[ContourCorrection, ...] = (),
) -> ProjectedPose:
    if number(width, "limb width") <= 0 or number(thickness, "hand thickness") <= 0:
        raise LimbError("limb width and hand thickness must be positive")
    inverse = parent.inverse()
    parts = []

    def strip(name: str, world: tuple[Vec3, ...], widths: tuple[float, ...], role: str) -> None:
        projected = tuple(camera.project(p) for p in world)
        points = tuple(p.xy for p in projected)
        sizes = tuple(w * p.scale for w, p in zip(widths, projected, strict=True))
        contour = tube(points, sizes) if name.startswith("digit:") else Contour(ribbon(points, sizes))
        polygon = tuple(inverse.point(p) for p in contour.exterior)
        centerline = tuple(inverse.point(p) for p in points)
        parts.append(
            Part(
                name,
                polygon,
                centerline,
                sum(p.depth for p in projected) / len(projected),
                sum(sizes) / len(sizes),
                role,
                holes=tuple(tuple(inverse.point(p) for p in ring) for ring in contour.holes),
            )
        )

    arm, hand = sample.arm, sample.hand
    strip("upper", (arm.shoulder, arm.elbow), (width * 1.2, width), "sleeve")
    strip("forearm", (arm.elbow, arm.wrist), (width, width * 0.72), "sleeve")
    for digit in hand.digits:
        n = len(digit.points)
        sizes = tuple(width * (0.4 - i / (n - 1) * 0.1) for i in range(n))
        strip(f"digit:{digit.name}", digit.points, sizes, "skin")
    palm = [camera.project(p + hand.normal * sign * thickness / 2) for p in hand.palm for sign in (-1, 1)]
    polygon = tuple(inverse.point(p) for p in _hull([p.xy for p in palm]))
    center = (sum(p[0] for p in polygon) / len(polygon), sum(p[1] for p in polygon) / len(polygon))
    parts.append(Part("palm", polygon, (center,), sum(p.depth for p in palm) / len(palm), width * camera.scale, "skin"))
    normal = camera.view.rotation.inverse().rotate(hand.normal)
    view = "palm" if normal.z > 0.2 else "back" if normal.z < -0.2 else "side"
    parts.sort(key=lambda p: (p.depth, p.name))
    # Palm and finger bases share an overlap rather than exposing gaps at the knuckles.
    pose = ProjectedPose(
        tuple(parts),
        inverse.point(camera.project(arm.shoulder).xy),
        inverse.point(camera.project(arm.elbow).xy),
        inverse.point(camera.project(arm.wrist).xy),
        tuple((d.name, inverse.point(camera.project(d.points[-1]).xy)) for d in hand.digits),
        view,
        sample.time,
    )
    return apply_correctives(pose, sample, camera, parent, correctives) if correctives else pose


def path(points: tuple[Point, ...], holes: tuple[tuple[Point, ...], ...] = ()) -> str:
    if len(points) < 3:
        raise LimbError("a limb contour needs at least three points")
    return " ".join("M" + " L".join(f"{x:.5f} {y:.5f}" for x, y in ring) + " Z" for ring in (points, *holes))

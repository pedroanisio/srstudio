"""A hand-inked brush for drawn characters: filled shapes with the line's weight built into the shape.

The traced Toon cat gets its look from the reference's brush: an ink band whose width breathes along the stroke,
round, slightly tapered ends, and fills laid over the band so its inner edge stays organic. A character drawn in
code gets the same look here, with no stroke attribute anywhere: every line is a closed filled shape.

Everything is geometry in the caller's units (the Toon parts use reference pixels), and every function returns a
*shape*: a flat tuple ``(x0, y0, c1x, c1y, c2x, c2y, x1, y1, ...)`` of one closed cubic path, the format of
``srstudio.toon`` shapes, drawn by :func:`srstudio.toon.shape_d`.

* :func:`spline` samples a Catmull-Rom curve through control points, open or closed;
* :func:`stroke` is a line drawn with the brush: a band around an open spline whose width swells and tapers
  (:class:`Pressure`), ends rounded;
* :func:`outline` is a smooth closed shape through points (a fill), and :func:`rim` the ink band drawn under it, the
  same shape pushed out by the line's weight;
* :func:`ellipse`, :func:`shift`, :func:`rotate` and :func:`flip` are the small tools around them.

Inputs are checked: a stroke needs two points, an outline three, a weight and a radius are positive, every
coordinate is finite (:class:`BrushError`).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .errors import SrstudioError

__all__ = [
    "BrushError",
    "Point",
    "Shape",
    "Pressure",
    "EVEN",
    "TAPERED",
    "spline",
    "stroke",
    "outline",
    "rim",
    "ellipse",
    "shift",
    "rotate",
    "flip",
    "bounds",
]

Point = tuple[float, float]
Shape = tuple[float, ...]
KAPPA = 0.5523  # a quarter circle as one cubic


class BrushError(SrstudioError, ValueError):
    """A measure the brush refuses."""


@dataclass(frozen=True)
class Pressure:
    """How the brush's width changes along a stroke, as factors of its weight: ``start`` and ``end`` at the tips,
    ``swell`` added at the middle, and a ``wobble`` of ``waves`` periods that breathes the width like a hand."""

    start: float = 0.55
    end: float = 0.45
    swell: float = 0.15
    wobble: float = 0.12
    waves: float = 2.5

    def at(self, s: float) -> float:
        """The width factor ``s`` of the way along the stroke, in 0..1."""
        base = self.start + (self.end - self.start) * s + self.swell * math.sin(math.pi * s)
        return max(0.15, base + self.wobble * math.sin(2 * math.pi * self.waves * s + 0.7))


EVEN = Pressure(1.0, 1.0, 0.0, 0.08, 2.0)  # an even line with a breath in it
TAPERED = Pressure()  # the default: thick in the middle, round tapered ends


def _points(points: Sequence[Point], least: int, where: str) -> list[Point]:
    if len(points) < least:
        raise BrushError(f"{where}: needs at least {least} points, got {len(points)}")
    out = []
    for p in points:
        if len(p) != 2 or not all(isinstance(v, int | float) and math.isfinite(v) for v in p):
            raise BrushError(f"{where}: {p!r} is not a finite point")
        out.append((float(p[0]), float(p[1])))
    return out


def _positive(value: float, name: str) -> float:
    if not (isinstance(value, int | float) and math.isfinite(value) and value > 0):
        raise BrushError(f"{name} must be a positive number, got {value!r}")
    return float(value)


def spline(points: Sequence[Point], closed: bool = False, steps: int = 8) -> list[Point]:
    """Points along the Catmull-Rom curve through ``points`` (``steps`` per segment); an open curve starts and
    ends on its first and last control point, a closed one returns to its first without repeating it."""
    pts = _points(points, 2, "spline")
    n = len(pts)

    def at(i: int) -> Point:
        return pts[i % n] if closed else pts[max(0, min(n - 1, i))]

    out: list[Point] = []
    segments = n if closed else n - 1
    for i in range(segments):
        p0, p1, p2, p3 = at(i - 1), at(i), at(i + 1), at(i + 2)
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            w0, w1, w2, w3 = -t + 2 * t2 - t3, 2 - 5 * t2 + 3 * t3, t + 4 * t2 - 3 * t3, -t2 + t3
            out.append(
                (
                    0.5 * (w0 * p0[0] + w1 * p1[0] + w2 * p2[0] + w3 * p3[0]),
                    0.5 * (w0 * p0[1] + w1 * p1[1] + w2 * p2[1] + w3 * p3[1]),
                )
            )
    if not closed:
        out.append(pts[-1])
    return out


def _cubic(poly: Sequence[Point], corner_deg: float = 100.0) -> Shape:
    """A closed polygon as a smooth cubic shape: Catmull-Rom tangents, vertices sharper than ``corner_deg`` kept
    as corners."""
    n = len(poly)

    def at(i: int) -> Point:
        return poly[i % n]

    corners = []
    for i in range(n):
        ax, ay = at(i - 1)[0] - at(i)[0], at(i - 1)[1] - at(i)[1]
        bx, by = at(i + 1)[0] - at(i)[0], at(i + 1)[1] - at(i)[1]
        cosang = (ax * bx + ay * by) / (math.hypot(ax, ay) * math.hypot(bx, by) + 1e-9)
        corners.append(math.degrees(math.acos(max(-1.0, min(1.0, cosang)))) < corner_deg)
    flat = [round(poly[0][0], 2), round(poly[0][1], 2)]
    for i in range(n):
        p0, p1, p2, p3 = at(i - 1), at(i), at(i + 1), at(i + 2)
        c1 = p1 if corners[i] else (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = p2 if corners[(i + 1) % n] else (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        flat += [round(v, 2) for v in (*c1, *c2, *p2)]
    return tuple(flat)


def _normals(path: Sequence[Point]) -> list[Point]:
    out = []
    n = len(path)
    for i in range(n):
        a, b = path[max(0, i - 1)], path[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1.0
        out.append((-dy / length, dx / length))
    return out


def _dedupe(path: Sequence[Point]) -> list[Point]:
    out: list[Point] = []
    for p in path:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 0.05:
            out.append(p)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= 0.05:
        out.pop()
    return out


def stroke(points: Sequence[Point], weight: float, pressure: Pressure = TAPERED, steps: int = 8) -> Shape:
    """A brush line through ``points``: a filled band ``weight`` wide at full pressure, its width following
    ``pressure`` along the way, with round ends."""
    weight = _positive(weight, "weight")
    path = _dedupe(spline(_points(points, 2, "stroke"), False, steps))
    if len(path) < 2:
        raise BrushError("stroke: the points are all in one place")
    lengths = [0.0]
    for a, b in zip(path, path[1:], strict=False):
        lengths.append(lengths[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = lengths[-1]
    normals = _normals(path)
    left, right = [], []
    for p, nrm, s in zip(path, normals, lengths, strict=True):
        half = weight * pressure.at(s / total) / 2
        left.append((p[0] + nrm[0] * half, p[1] + nrm[1] * half))
        right.append((p[0] - nrm[0] * half, p[1] - nrm[1] * half))

    def cap(centre: Point, nrm: Point, half: float, forward: Point) -> list[Point]:
        # a half circle from the left edge round the tip to the right edge
        out = []
        for k in range(1, 4):
            ang = math.pi * k / 4
            c, s_ = math.cos(ang), math.sin(ang)
            out.append(
                (centre[0] + (nrm[0] * c + forward[0] * s_) * half, centre[1] + (nrm[1] * c + forward[1] * s_) * half)
            )
        return out

    def unit(a: Point, b: Point) -> Point:
        dx, dy = a[0] - b[0], a[1] - b[1]
        length = math.hypot(dx, dy) or 1.0
        return dx / length, dy / length

    tip = cap(path[-1], normals[-1], weight * pressure.at(1.0) / 2, unit(path[-1], path[-2]))
    tail = cap(path[0], (-normals[0][0], -normals[0][1]), weight * pressure.at(0.0) / 2, unit(path[0], path[1]))
    poly = left + tip + right[::-1] + tail
    return _cubic(_dedupe(poly), 60.0)


def outline(points: Sequence[Point], steps: int = 6) -> Shape:
    """A smooth closed shape through ``points``: a fill."""
    return _cubic(_dedupe(spline(_points(points, 3, "outline"), True, steps)), 100.0)


def rim(points: Sequence[Point], weight: float, pressure: Pressure = EVEN, steps: int = 6) -> Shape:
    """The ink band under an :func:`outline` of the same points: the shape pushed out by ``weight`` (breathing
    with ``pressure`` around it), drawn first so the fill over it leaves a line of that weight showing."""
    weight = _positive(weight, "weight")
    path = _dedupe(spline(_points(points, 3, "rim"), True, steps))
    n = len(path)
    # outward normals of a closed path, whichever way it winds
    area = sum(path[i][0] * path[(i + 1) % n][1] - path[(i + 1) % n][0] * path[i][1] for i in range(n))
    sign = -1.0 if area > 0 else 1.0
    poly = []
    for i, p in enumerate(path):
        a, b = path[i - 1], path[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = sign * -dy / length, sign * dx / length
        push = weight * pressure.at(i / n)
        poly.append((p[0] + nx * push, p[1] + ny * push))
    return _cubic(poly, 100.0)


def ellipse(cx: float, cy: float, rx: float, ry: float, tilt: float = 0.0) -> Shape:
    """A closed ellipse of four cubic arcs, ``tilt`` degrees clockwise."""
    rx, ry = _positive(rx, "rx"), _positive(ry, "ry")
    pts = [(rx, 0.0), (0.0, ry), (-rx, 0.0), (0.0, -ry)]
    ctrl = [
        ((rx, KAPPA * ry), (KAPPA * rx, ry)),
        ((-KAPPA * rx, ry), (-rx, KAPPA * ry)),
        ((-rx, -KAPPA * ry), (-KAPPA * rx, -ry)),
        ((KAPPA * rx, -ry), (rx, -KAPPA * ry)),
    ]
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))

    def place(p: Point) -> list[float]:
        return [round(cx + p[0] * c - p[1] * s, 2), round(cy + p[0] * s + p[1] * c, 2)]

    flat = place(pts[0])
    for i in range(4):
        (c1, c2), p = ctrl[i], pts[(i + 1) % 4]
        flat += place(c1) + place(c2) + place(p)
    return tuple(flat)


def shift(shape: Shape, dx: float, dy: float) -> Shape:
    return tuple(round(v + (dx if i % 2 == 0 else dy), 2) for i, v in enumerate(shape))


def rotate(shape: Shape, cx: float, cy: float, degrees: float) -> Shape:
    """The shape turned ``degrees`` clockwise (y down) about ``(cx, cy)``."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    out = []
    for i in range(0, len(shape), 2):
        x, y = shape[i] - cx, shape[i + 1] - cy
        out += [round(cx + x * c - y * s, 2), round(cy + x * s + y * c, 2)]
    return tuple(out)


def flip(shape: Shape, cx: float) -> Shape:
    """The shape mirrored about the vertical line ``x = cx``."""
    return tuple(round(2 * cx - v, 2) if i % 2 == 0 else v for i, v in enumerate(shape))


def bounds(shape: Shape) -> tuple[float, float, float, float]:
    """``(min x, min y, max x, max y)`` of the shape's points and handles."""
    xs, ys = shape[0::2], shape[1::2]
    return min(xs), min(ys), max(xs), max(ys)

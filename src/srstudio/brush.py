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
* :func:`inked` is a rim pressed like a hand (:class:`Hand`): heavier where the outline turns away from the light,
  lighter at sharp tips, unevenly along the way; :func:`wobble` gives a contour a hand's small, uneven deviations;
* :func:`broken` is that band in pieces, the brush lifted in a few seeded places and nicked in others, and
  :func:`lump` an uneven one-off blob where a perfect :func:`ellipse` would look digital;
* :func:`ellipse`, :func:`shift`, :func:`rotate` and :func:`flip` are the small tools around them.

Inputs are checked: a stroke needs two points, an outline three, a weight and a radius are positive, every
coordinate is finite (:class:`BrushError`).
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from . import checks
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
    "Hand",
    "HAND",
    "inked",
    "facing",
    "crescent",
    "wobble",
    "broken",
    "lump",
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


def _grain(s: float, phase: float = 0.0) -> float:
    """An uneven but repeatable wave in -1..1, periodic over ``s`` in 0..1: a hand's pressure or drift."""
    return (
        math.sin(2 * math.pi * 7 * s + 0.3 + phase)
        + 0.6 * math.sin(2 * math.pi * 13 * s + 1.9 + 2.3 * phase)
        + 0.35 * math.sin(2 * math.pi * 29 * s + 4.1 + 3.7 * phase)
    ) / 1.95


def _grit(s: float) -> float:
    """A fine, rough wave in -1..1, periodic over ``s`` in 0..1: the paper's tooth catching the brush."""
    return (
        math.sin(2 * math.pi * 61 * s + 0.9)
        + 0.7 * math.sin(2 * math.pi * 97 * s + 2.6)
        + 0.5 * math.sin(2 * math.pi * 151 * s + 5.2)
    ) / 2.2


@dataclass(frozen=True)
class Hand:
    """How a hand presses an ink line round a shape, as factors of its weight: ``light`` where the outline faces
    the light and ``heavy`` where it turns away, the weight falling ``toward`` that direction (down and to the back
    by default); a convex turn of a right angle or more thins the line by ``tips`` (a tip, where the brush lifts),
    ``grain`` makes the pressure uneven along the way, and ``ragged`` adds the fine grit of a dry brush on paper."""

    light: float = 0.45
    heavy: float = 1.35
    toward: Point = (0.35, 0.94)
    tips: float = 0.65
    grain: float = 0.18
    ragged: float = 0.0

    def at(self, normal: Point, turn: float, s: float, seed: float = 0.0) -> float:
        """The width factor where the outward ``normal`` points, the outline turning ``turn`` radians there
        (positive convex), ``s`` of the way round; ``seed`` shifts the grain, so two shapes do not share it."""
        tx, ty = self.toward
        facing = (normal[0] * tx + normal[1] * ty) / math.hypot(tx, ty)
        base = self.light + (self.heavy - self.light) * (facing + 1) / 2
        tip = 1.0 - self.tips * min(1.0, max(0.0, turn) / (math.pi / 2))
        if self.ragged:
            return max(0.08, base * tip * (1 + self.grain * _grain(s, seed) + self.ragged * _grit(s)))
        return max(0.08, base * tip * (1 + self.grain * _grain(s, seed)))


HAND = Hand()


def _points(points: Sequence[Point], least: int, where: str) -> list[Point]:
    if len(points) < least:
        raise BrushError(f"{where}: needs at least {least} points, got {len(points)}")
    out = []
    for p in points:
        if len(p) != 2 or not all(checks.number(v) for v in p):
            raise BrushError(f"{where}: {p!r} is not a finite point")
        out.append((float(p[0]), float(p[1])))
    return out


def _positive(value: float, name: str) -> float:
    if not (checks.number(value) and value > 0):
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


def _ring(points: Sequence[Point], steps: int, where: str) -> tuple[list[Point], list[Point], float]:
    """The closed spline through ``points``: its samples, their outward normals and +1 when it winds clockwise on
    screen (y down), -1 otherwise."""
    path = _dedupe(spline(_points(points, 3, where), True, steps))
    n = len(path)
    area = sum(path[i][0] * path[(i + 1) % n][1] - path[(i + 1) % n][0] * path[i][1] for i in range(n))
    sign = -1.0 if area > 0 else 1.0
    normals = []
    for i in range(n):
        a, b = path[i - 1], path[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1.0
        normals.append((sign * -dy / length, sign * dx / length))
    return path, normals, 1.0 if area > 0 else -1.0


def facing(points: Sequence[Point], steps: int = 6) -> list[tuple[Point, Point]]:
    """Every sample of the closed spline through ``points`` with its outward normal, whichever way it winds."""
    path, normals, _ = _ring(points, steps, "facing")
    return list(zip(path, normals, strict=True))


def _pressed(
    points: Sequence[Point], weight: float, hand: Hand, steps: int, where: str, seed: float = 0.0
) -> list[tuple[Point, Point, float]]:
    """Every sample of the closed spline through ``points``, with its outward normal and the push ``hand`` gives
    it."""
    weight = _positive(weight, "weight")
    _positive(hand.light, "light")
    _positive(hand.heavy, "heavy")
    if not (all(checks.number(v) for v in hand.toward) and math.hypot(*hand.toward) > 0):
        raise BrushError(f"toward must be a direction, got {hand.toward!r}")
    path, normals, convex = _ring(points, steps, where)
    n = len(path)
    reach = max(1, steps)  # the turn is measured over about one control segment either side
    out = []
    for i, (p, (nx, ny)) in enumerate(zip(path, normals, strict=True)):
        back, ahead = path[(i - reach) % n], path[(i + reach) % n]
        ux, uy = p[0] - back[0], p[1] - back[1]
        vx, vy = ahead[0] - p[0], ahead[1] - p[1]
        turn = convex * math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        out.append((p, (nx, ny), weight * hand.at((nx, ny), turn, i / n, seed)))
    return out


def inked(points: Sequence[Point], weight: float, hand: Hand = HAND, steps: int = 6, seed: float = 0.0) -> Shape:
    """The ink band under an :func:`outline` of the same points, pressed by ``hand``: pushed out by ``weight`` times
    :meth:`Hand.at` at every point, so the line swells where the shape turns from the light and thins to almost
    nothing at its tips, like a traced line. ``seed`` gives a shape a grain of its own."""
    pressed = _pressed(points, weight, hand, steps, "inked", seed)
    return _cubic([(p[0] + nx * push, p[1] + ny * push) for p, (nx, ny), push in pressed], 100.0)


def broken(
    points: Sequence[Point],
    weight: float,
    hand: Hand = HAND,
    steps: int = 6,
    breaks: int = 4,
    gap: float | None = None,
    seed: int = 0,
) -> list[Shape]:
    """The :func:`inked` band in ``breaks`` pieces: the brush lifts in as many seeded places round the contour,
    each gap about ``gap`` long (the line's weight by default, varied per gap), the band tapering into it, and a
    nick bitten from the band's edge in each piece. A piece's inner edge sits a little inside the contour, under
    the fill drawn over it, so only the ink outside shows. The same ``seed`` breaks the same places every build."""
    if isinstance(breaks, bool) or not isinstance(breaks, int) or breaks < 1:
        raise BrushError(f"breaks must be a whole number of at least 1, got {breaks!r}")
    gap = weight if gap is None else gap
    gap = _positive(gap, "gap")
    pressed = _pressed(points, weight, hand, steps, "broken")
    n = len(pressed)
    along = [0.0]
    for (a, _, _), (b, _, _) in zip(pressed, pressed[1:] + pressed[:1], strict=True):
        along.append(along[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = along.pop()
    if breaks * gap > total / 2:
        raise BrushError(f"broken: the gaps would take half the contour ({breaks} x {gap} of {total:.1f})")
    rng = random.Random(seed)
    start = rng.random() * total
    gaps = []  # (where the gap opens, where it closes), along the contour from ``start``
    for k in range(breaks):
        centre = (k + 0.5 + rng.uniform(-0.3, 0.3)) * total / breaks
        half = gap * rng.uniform(0.6, 1.4) / 2
        gaps.append((centre - half, centre + half))
    opens = [g[0] for g in gaps[1:]] + [gaps[0][0] + total]
    nicks = [gaps[k][1] + rng.uniform(0.3, 0.7) * (opens[k] - gaps[k][1]) for k in range(breaks)]
    taper = 1.5 * weight
    inset = 0.25 * weight
    pieces = []
    for k in range(breaks):
        lo, hi = gaps[k][1], opens[k]
        outer, inner = [], []
        ahead = (((along[i] - start) % total, i) for i in range(n))
        for pos, i in sorted((pos + (total if pos < lo else 0.0), i) for pos, i in ahead):
            if pos > hi:
                break
            p, (nx, ny), push = pressed[i]
            t = min(1.0, min(pos - lo, hi - pos) / taper)
            bite = 1.0 - 0.4 * math.exp(-(((pos - nicks[k]) / (0.6 * weight)) ** 2))
            push *= t * t * (3 - 2 * t) * bite
            outer.append((p[0] + nx * push, p[1] + ny * push))
            inner.append((p[0] - nx * inset, p[1] - ny * inset))
        if len(outer) < 2:
            raise BrushError(f"broken: piece {k + 1} of {breaks} is too short to draw; use fewer breaks or more steps")
        pieces.append(_cubic(_dedupe(outer + inner[::-1]), 100.0))
    return pieces


def wobble(
    points: Sequence[Point],
    amount: float,
    closed: bool = True,
    steps: int = 4,
    seed: float = 0,
    weights: Sequence[float] | None = None,
) -> list[Point]:
    """Points along the spline through ``points`` (``steps`` per segment, as :func:`spline`), each moved across
    the curve by at most ``amount``: the small uneven drift of a hand following a contour. The drift repeats for a
    ``seed``, so a build draws the same line every time. ``weights``, a share in 0..1 per sample, calm it where a
    line must stay smooth (at ``steps=1`` the samples are the points themselves)."""
    if not (checks.number(amount) and amount >= 0):
        raise BrushError(f"amount must be a non-negative number, got {amount!r}")
    path = spline(_points(points, 2, "wobble"), closed, steps)
    n = len(path)
    if weights is not None and (len(weights) != n or not all(checks.number(w) and 0 <= w <= 1 for w in weights)):
        raise BrushError(f"wobble weights are one share in 0..1 per sample ({n}), got {weights!r}")
    out = []
    for i, p in enumerate(path):
        if closed:
            a, b = path[i - 1], path[(i + 1) % n]
        else:
            a, b = path[max(0, i - 1)], path[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1.0
        drift = amount * _grain(i / n if closed else i / max(1, n - 1), 1.618 * seed) * (weights[i] if weights else 1.0)
        out.append((p[0] - dy / length * drift, p[1] + dx / length * drift))
    return out


def crescent(outer: Sequence[Point], depth: float, inside: Point, peak: float = 0.6) -> tuple[Point, ...]:
    """A shade that runs inside an outline along ``outer``: it starts and ends on the outline and swells to ``depth``
    toward ``inside``, deepest ``peak`` of the way along, so it turns the form instead of striping it."""
    path = spline(outer, steps=3)
    along = [0.0]
    for a, b in zip(path, path[1:], strict=False):
        along.append(along[-1] + math.dist(a, b))
    bend = math.log(0.5) / math.log(peak)
    inner = []
    for i, p in enumerate(path):
        a, b = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        nx, ny = -dy / math.hypot(dx, dy), dx / math.hypot(dx, dy)
        if nx * (inside[0] - p[0]) + ny * (inside[1] - p[1]) < 0:
            nx, ny = -nx, -ny
        d = depth * math.sin(math.pi * (along[i] / along[-1]) ** bend)
        inner.append((p[0] + nx * d, p[1] + ny * d))
    return tuple(path) + tuple(inner[-2:0:-1])


def lump(
    cx: float, cy: float, rx: float, ry: float, amount: float, seed: int = 0, tilt: float = 0.0, points: int = 7
) -> Shape:
    """A one-off blob about ``rx`` by ``ry`` round ``(cx, cy)``, turned ``tilt`` degrees clockwise: a smooth closed
    shape through ``points`` points, each pushed in or out by up to ``amount`` of the radius and slid a little
    round, so no two seeds draw the same blob and none is a perfect :func:`ellipse`."""
    rx, ry = _positive(rx, "rx"), _positive(ry, "ry")
    if not (checks.number(amount) and 0 <= amount <= 0.5):
        raise BrushError(f"amount must be a number from 0 to 0.5, got {amount!r}")
    if isinstance(points, bool) or not isinstance(points, int) or points < 5:
        raise BrushError(f"points must be a whole number of at least 5, got {points!r}")
    rng = random.Random(seed)
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    pts = []
    for k in range(points):
        ang = 2 * math.pi * (k + rng.uniform(-0.25, 0.25)) / points
        r = 1 + amount * rng.uniform(-1.0, 1.0)
        x, y = rx * r * math.cos(ang), ry * r * math.sin(ang)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return outline(pts)


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

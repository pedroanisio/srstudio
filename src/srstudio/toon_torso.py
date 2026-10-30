"""A Toon torso: one smooth contour from the neck over the shoulders down the flanks, and arms drawn inside it
(ADR 0049).

The traced cat reads as one continuous silhouette: its head runs into its shoulders and body in a single outline,
the shoulders are a broad gentle curve and the arms are lines inside the body. A brush-drawn character gets the same
from a :class:`Torso` built from a few numbers under its own head contour:

* :attr:`Torso.contour` is the whole closed outline: down each side from where the head meets the neck, out to the
  shoulder at the given slope and on down the flank to the base, every turn an arc of a fixed least radius, so the
  line leaves the head without a corner and turns no sharper than a gentle curve;
* :meth:`Torso.weights` lets :func:`srstudio.brush.wobble` move the head's edge like a hand while the shoulders and
  flanks stay calm;
* :meth:`Torso.arm_path` and :meth:`Torso.limb` draw an arm from the shared arms of a pose
  (:func:`srstudio.toon_cast._arms`): its top moved below the shoulder line and well inside the body, its elbow
  pulled in when it would poke out, the paw left where the pose puts it; the stroke tapers into the body like a
  crease and is widest at the forearm, one form with the body along the flank: :func:`arm_lines` inks its edges only
  where they leave the body or lie well over it. The inked fox draws its arms with the same :func:`arm_lines`.

Any :class:`srstudio.toon_cast.Drawing` can use it: build a torso from the head, the shoulder half-width and slope,
the flank half-width and the arm's width, take the look's silhouette from :attr:`Torso.contour` (drifted by hand
with :meth:`Torso.weights`), and draw its ``limb`` with :meth:`Torso.limb` and a paw of its own. Everything is in
reference pixels. :mod:`srstudio.toon_critters` draws the sloth, the goat and the hamster this way.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property

from . import brush, checks
from .brush import Point
from .toon import ToonDataError
from .toon_cast import CENTRE, INK, Layer

__all__ = ["Torso", "TAPER", "UNDER", "ARM_LINE", "SEAM", "SPACING", "BULGE", "CURVE_IN", "arm_lines", "depth_in"]

TAPER = brush.Pressure(0.3, 1.0, 0.12, 0.04, 1.5)  # an arm: a thin crease into the body, the full width at the paw
UNDER = brush.Pressure(0.35, 0.3, 0.75, 0.06, 1.2)  # the shade under a forearm: pressed in the middle
ARM_LINE = brush.Pressure(0.3, 0.75, 0.45, 0.12, 1.6)  # an arm's ink: lifted at both ends of every run
SEAM = 0.55  # arm widths: an arm's edge this close inside the body, running along it, merges with the body
SPACING = 10.0  # reference pixels between the contour points down a side
INSET = 0.5  # how far inside the outline an arm's top sits, in arm widths: its thin start well clear of the edge
ELBOW = 0.55  # how far inside the outline an elbow is pulled, in arm widths
WRIST = 0.8  # how far inside the outline the rest of an arm is kept beside the shoulders, in arm widths
PAW = 0.85  # how far inside the outline a paw is kept beside the shoulders, in arm widths
SAG = 0.25  # how far an arm reaching out past its flank sags under the straight line, in arm widths
DROP = 0.8  # how far below an arm's top its elbow sits at least, in arm widths: an upper arm, not a hook
BULGE = 54.0  # the least radius where the outline bulges out (a shoulder): 8.5 degrees of turn every 8 px
CURVE_IN = 48.0  # the least radius where it curves in (under the jaw): 9.5 degrees every 8 px, never a notch
MOVES = 60  # how many 2 px steps an elbow may be pulled in before an arm is refused


def _resample(path: Sequence[Point], step: float) -> list[Point]:
    """Points ``step`` apart along a polyline, from just after its first point to exactly its last."""
    out: list[Point] = []
    carried = 0.0
    for a, b in zip(path, path[1:], strict=False):
        length = math.dist(a, b)
        at = step - carried
        while at < length:
            t = at / length
            out.append((round(a[0] + (b[0] - a[0]) * t, 2), round(a[1] + (b[1] - a[1]) * t, 2)))
            at += step
        carried = length - (at - step)
    if out and math.dist(out[-1], path[-1]) < step * 0.5:
        out.pop()  # no sliver before the end
    return [*out, (round(path[-1][0], 2), round(path[-1][1], 2))]


def _arc(at: Point, heading: float, turn: float, radius: float) -> tuple[list[Point], Point]:
    """Points every 2 degrees along a circular arc of ``radius`` from ``at`` heading ``heading`` (radians, y down)
    that turns by ``turn`` (positive: clockwise on screen), and where it ends."""
    if abs(turn) < 1e-9:
        return [], at
    sign = 1.0 if turn > 0 else -1.0
    centre = (at[0] - math.sin(heading) * sign * radius, at[1] + math.cos(heading) * sign * radius)
    a0 = math.atan2(at[1] - centre[1], at[0] - centre[0])
    steps = max(2, math.ceil(abs(math.degrees(turn)) / 2))
    out = [
        (centre[0] + radius * math.cos(a0 + turn * k / steps), centre[1] + radius * math.sin(a0 + turn * k / steps))
        for k in range(1, steps + 1)
    ]
    return out, out[-1]


def _distance(point: Point, path: Sequence[Point]) -> float:
    """How far ``point`` is from a polyline."""
    best = math.inf
    for a, b in zip(path, path[1:], strict=False):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / (dx * dx + dy * dy or 1.0)))
        best = min(best, math.dist(point, (a[0] + dx * t, a[1] + dy * t)))
    return best


def _towards(heading: float, goal: float) -> float:
    """The signed turn, in (-pi, pi], from one heading to another."""
    return math.atan2(math.sin(goal - heading), math.cos(goal - heading))


def _unit(dx: float, dy: float) -> Point:
    length = math.hypot(dx, dy) or 1.0
    return dx / length, dy / length


def depth_in(outline: Sequence[Point], p: Point) -> tuple[float, Point]:
    """How far inside the closed ``outline`` a point is (negative outside) and the direction of the nearest edge."""
    near, along, hit = math.inf, (1.0, 0.0), False
    for a, b in zip(outline, (*outline[1:], outline[0]), strict=True):
        (ax, ay), (bx, by) = a, b
        if (ay > p[1]) != (by > p[1]) and p[0] < ax + (p[1] - ay) * (bx - ax) / (by - ay):
            hit = not hit
        length = math.dist(a, b) or 1.0
        t = max(0.0, min(1.0, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / length**2))
        d = math.dist(p, (ax + t * (bx - ax), ay + t * (by - ay)))
        if d < near:
            near, along = d, ((bx - ax) / length, (by - ay) / length)
    return (near if hit else -near), along


def arm_lines(
    points: Sequence[Point],
    w: float,
    outline: Sequence[Point],
    taper: brush.Pressure,
    weight: float,
    line: brush.Pressure = ARM_LINE,
) -> list[brush.Shape]:
    """The ink of an arm drawn ``w`` wide with ``taper`` over a body with ``outline``: along each edge where it lies
    outside the body (its contour), deep inside it (the overlap line) or crosses the body's edge; never where it runs
    within :data:`SEAM` widths inside the body along the flank, where the arm and the body are one form."""
    path = [p for k, p in enumerate(brush.spline(points, False, 8)) if k == 0 or p != points[0]]
    lengths = [0.0]
    for a, b in zip(path, path[1:], strict=False):
        lengths.append(lengths[-1] + math.dist(a, b))
    out: list[brush.Shape] = []
    for side in (1.0, -1.0):
        run: list[Point] = []
        for i, (p, s) in enumerate(zip(path, lengths, strict=True)):
            a, b = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            length = math.hypot(tx, ty) or 1.0
            tx, ty = tx / length, ty / length
            half = side * w * taper.at(s / lengths[-1]) / 2
            edge = (p[0] - ty * half, p[1] + tx * half)
            depth, (ax, ay) = depth_in(outline, edge)
            if depth < 0.0 or depth > SEAM * w or abs(tx * ax + ty * ay) < 0.6:
                run.append(edge)
                continue
            if len(run) >= 4:
                out.append(brush.stroke(run, weight, line, steps=1))
            run = []
        if len(run) >= 4:
            out.append(brush.stroke(run, weight, line, steps=1))
    return out


@dataclass(frozen=True)
class Torso:
    """A body under ``head``: the head's contour from where it meets the neck on the left, over the crown, to where
    it meets the neck on the right. From each join the outline curves from the head's own heading into ``slope``
    degrees below level, runs out until the shoulder (from ``centre``) is ``shoulder`` wide, and curves down into a
    flank that lands ``flank`` wide at the ``base``; a shoulder narrower than its curves allow comes out as wide as
    they make it. ``arm`` is the arm's width at the forearm; the paw at its end is the character's own drawing."""

    head: tuple[Point, ...]
    shoulder: float
    slope: float
    flank: float
    arm: float
    base: float = 830.0
    centre: float = CENTRE

    def __post_init__(self) -> None:
        if len(self.head) < 3 or any(len(p) != 2 or not all(checks.number(v) for v in p) for p in self.head):
            raise ToonDataError(f"a torso's head is at least 3 finite points, got {self.head!r}")
        for name in ("shoulder", "flank", "arm", "base", "centre"):
            value = getattr(self, name)
            if not (checks.number(value) and (value > 0 or name == "centre")):
                raise ToonDataError(f"a torso's {name} is a positive number, got {value!r}")
        if not (checks.number(self.slope) and 0 <= self.slope < 90):
            raise ToonDataError(f"a torso's slope is 0 to under 90 degrees, got {self.slope!r}")
        _ = self._sides  # the shoulders placed and checked now, not at the first drawing

    # -- the contour ---------------------------------------------------------------------------------------------------
    def _radius(self, turn: float, side: int) -> float:
        return BULGE if turn * side > 0 else CURVE_IN  # out over a shoulder, in under a jaw

    @cached_property
    def _sides(self) -> dict[int, tuple[list[Point], Point]]:
        """Each side as a turtle draws it from the neck join: an arc from the head's own heading into the slope, the
        slope run out until the shoulder reaches its half-width, an arc down into the flank, and the flank straight
        to the base, leaning so its foot lands on the flank half-width. Every arc has the least radius of its kind,
        so nothing turns sharper than :data:`BULGE` or :data:`CURVE_IN` allow. With the side, the shoulder: where
        the slope starts to curve down into the flank."""
        out = {}
        for side in (-1, 1):
            join, before = (self.head[0], self.head[1]) if side < 0 else (self.head[-1], self.head[-2])
            start = math.atan2(join[1] - before[1], join[0] - before[0])
            slope = math.radians(self.slope) if side > 0 else math.pi - math.radians(self.slope)
            turn_in = _towards(start, slope)
            neck, knee = _arc(join, start, turn_in, self._radius(turn_in, side))
            fall = math.pi / 2  # straight down at first; leaned to land on the flank below
            for _ in range(4):
                turn_out = _towards(slope, fall)
                bend, end = _arc((0.0, 0.0), slope, turn_out, self._radius(turn_out, side))
                run = (self.centre + side * self.shoulder - knee[0] - end[0]) / math.cos(slope)
                run = max(0.0, run)  # arcs already wider than the shoulder: it is as wide as they make it
                corner = (knee[0] + run * math.cos(slope), knee[1] + run * math.sin(slope))
                edge = (corner[0] + end[0], corner[1] + end[1])
                if edge[1] >= self.base - self.arm:
                    raise ToonDataError(
                        f"a torso's shoulders reach {edge[1]:.0f}, under an arm's width above its base ({self.base}): "
                        "a lower slope, a narrower shoulder or a lower base gives it room"
                    )
                fall = math.atan2(self.base - edge[1], self.centre + side * self.flank - edge[0])
            arc = [(corner[0] + x, corner[1] + y) for x, y in bend]
            path = [join, *neck, corner, *arc, (self.centre + side * self.flank, self.base)]
            out[side] = (_resample(path, SPACING), (round(corner[0], 2), round(corner[1], 2)))
        return out

    @property
    def shoulders(self) -> tuple[Point, Point]:
        """The left and right shoulders: where each slope starts to curve down into the flank, the top of the
        shoulder line."""
        return self._sides[-1][1], self._sides[1][1]

    def _side(self, side: int) -> list[Point]:
        """One side from the neck join (excluded) down to the base."""
        return self._sides[side][0]

    @cached_property
    def contour(self) -> tuple[Point, ...]:
        """The closed outline: up the left side from the base, the head, down the right side, along the base."""
        left = self._side(-1)[::-1]
        right = self._side(1)
        bottom = [
            (round(self.centre + self.flank * 0.5, 2), self.base + 2.0),
            (round(self.centre - self.flank * 0.5, 2), self.base + 2.0),
        ]
        return tuple([*left, *self.head, *right, *bottom])

    def under(self, top: Sequence[Point]) -> tuple[Point, ...]:
        """The closed outline of the body alone: :attr:`contour` with ``top``, a line from one neck join to the other,
        where the head was, for a head drawn separately behind it (:mod:`srstudio.toon_head`)."""
        if len(top) < 3 or any(len(p) != 2 or not all(checks.number(v) for v in p) for p in top):
            raise ToonDataError(f"a body's top is at least 3 finite points, got {top!r}")
        whole = self.contour
        before = len(self._side(-1))
        return tuple([*whole[:before], *top, *whole[before + len(self.head) :]])

    def weights(self, calm: float, top: int | None = None) -> tuple[float, ...]:
        """How much of a hand's drift each contour point takes: all of it on the head, or on a body's ``top`` of that
        many points (:meth:`under`), ``calm`` (0..1) on the torso and on the two neck joins, so the line leaves the
        head as gently as the arcs below them run."""
        if not (checks.number(calm) and 0 <= calm <= 1):
            raise ToonDataError(f"calm is a share of the drift, 0 to 1, got {calm!r}")
        before = len(self._side(-1))
        count = len(self.head) if top is None else top
        total = len(self.contour) - len(self.head) + count
        head = range(before + 1, before + count - 1)
        return tuple(1.0 if i in head else float(calm) for i in range(total))

    def edge(self, y: float, side: int) -> float:
        """The outline's x at height ``y`` on the left (``side`` -1) or right (+1), between the neck and the base."""
        if side not in (-1, 1):
            raise ToonDataError(f"a side is -1 (left) or 1 (right), got {side!r}")
        neck = self.head[0] if side < 0 else self.head[-1]
        run = [neck, *self._side(side)]
        if not (checks.number(y) and run[0][1] <= y <= run[-1][1]):
            raise ToonDataError(f"the torso's edge runs from {run[0][1]} to {run[-1][1]}, not to {y!r}")
        for (ax, ay), (bx, by) in zip(run, run[1:], strict=False):
            if ay <= y <= by:
                return ax if by == ay else ax + (bx - ax) * (y - ay) / (by - ay)
        return run[-1][0]  # pragma: no cover - the range check above keeps y on the run

    # -- the arms ------------------------------------------------------------------------------------------------------
    def keep(self, point: Point, margin: float) -> Point:
        """``point`` moved in toward the middle of the chest, 2 px at a time, until it is ``margin`` inside the
        outline, when it lies beside the shoulders (between the neck join and half an arm below the shoulder line,
        where its width still reaches them); anywhere else as it is: a paw reaching past the flank below the
        shoulders, or up on the face, stays where the pose puts it."""
        x, y = float(point[0]), float(point[1])
        side = -1 if x < self.centre else 1
        join = self.head[0] if side < 0 else self.head[-1]
        if not join[1] <= y <= self._level + self.arm * 0.5 or self._reaches((x, y), side):
            return x, y
        run = [join, *self._side(side)]
        ux, uy = _unit(self.centre - x, self._level + self.arm * 2 - y)
        for _ in range(MOVES):
            if side * (self.edge(y, side) - x) > 0 and _distance((x, y), run) >= margin:
                break
            x, y = x + ux * 2.0, y + uy * 2.0
        return round(x, 2), round(y, 2)

    @property
    def _level(self) -> float:
        return max(y for _, y in self.shoulders)

    def arm_path(self, points: Sequence[Point]) -> list[Point]:
        """A pose's arm (shoulder, elbow, ..., wrist) redrawn inside the body: the top moved under the shoulder line
        and :data:`INSET` arm widths inside the outline, the elbow at least :data:`DROP` widths below it and pulled
        :data:`ELBOW` widths inside when it would poke out, and further in, 2 px at a time, until the arm is clear of
        the outline above the shoulders. The later points stay where the pose puts them, so the paw still reaches
        the desk, the keyboard or the face, unless they lie beside the shoulders (:meth:`keep`). A paw raised to the
        face crosses in front of the neck: only its upper arm has to clear the outline."""
        if len(points) < 2:
            raise ToonDataError(f"an arm runs from the shoulder through at least one more point, got {points!r}")
        side = -1 if points[0][0] < self.centre else 1
        _, sy = self.shoulders[0 if side < 0 else 1]
        top_y = sy + self.arm * 0.5
        top = (round(self.edge(top_y, side) - side * self.arm * INSET, 2), round(top_y, 2))
        out = [top, *(self.keep(p, self.arm * WRIST) for p in points[1:])]
        if len(points) == 2:
            return out
        if self._reaches(out[2], side):
            (tx, ty), (wx, wy) = top, out[2]
            out[1] = (round((tx + wx) / 2, 2), round((ty + wy) / 2 + self.arm * SAG, 2))
            return out
        y = max(out[1][1], top_y + self.arm * DROP)
        limit = self.edge(min(y, self.base), side) - side * self.arm * ELBOW
        x = min(out[1][0], limit) if side > 0 else max(out[1][0], limit)
        for _ in range(MOVES):
            out[1] = (round(x, 2), round(y, 2))
            if self._clear(out, side):
                return out
            x -= side * 2.0
        raise ToonDataError(f"an arm through {points!r} cannot stay inside the body above the shoulders")

    def _reaches(self, point: Point, side: int) -> bool:
        """Whether ``point``, level with the body, lies more than an arm's width out past it on its own ``side``."""
        join = self.head[0] if side < 0 else self.head[-1]
        return point[1] >= join[1] and side * (point[0] - self.edge(min(point[1], self.base), side)) > self.arm

    def _clear(self, path: Sequence[Point], side: int) -> bool:
        """Whether an arm along ``path`` keeps its inked width inside the outline wherever it is above the shoulders
        and below the neck join: all of it, or only the upper arm when the paw is raised past the neck join."""
        join = (self.head[0] if side < 0 else self.head[-1])[1]
        steps = 8
        line = brush.spline(path, False, steps)
        lengths = [0.0]
        for a, b in zip(line, line[1:], strict=False):
            lengths.append(lengths[-1] + math.dist(a, b))
        reach = steps + 1 if path[-1][1] < join else len(line)
        for (x, y), along in list(zip(line, lengths, strict=True))[:reach]:
            if join <= y <= self._level:
                half = (self.arm + 2 * INK) * TAPER.at(along / lengths[-1]) / 2 + 2.0
                if side * (self.edge(y, side) - x) < half:
                    return False
        return True

    def limb(self, points: Sequence[Point], paw: Point, coat: str, shade: str) -> tuple[list[Layer], Point, Point]:
        """An arm's layers, where its paw goes and the way it points: the coat tapering into the body (:data:`TAPER`),
        the shade along the forearm's underside, and the ink of :func:`arm_lines`. The paw is the caller's to draw, at
        ``paw`` kept inside the body beside the shoulders (:meth:`keep`)."""
        path = self.arm_path(points)
        w = self.arm
        under = [(x + 0.4, y + w * 0.26) for x, y in (path[1:] if len(path) > 2 else path)]
        layers: list[Layer] = [(brush.stroke(path, w, TAPER), coat), (brush.stroke(under, w * 0.4, UNDER), shade)]
        layers += [(line, "ink") for line in arm_lines(path, w, self.contour, TAPER, INK * 1.1)]
        ax, ay = path[-2]
        at = self.keep(paw, self.arm * PAW)
        return layers, at, _unit(at[0] - ax, at[1] - ay)

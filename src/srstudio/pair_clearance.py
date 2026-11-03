"""No two figures on screen touch, unless the choreography says they do.

Two dancers side by side each dance a pose that is fine alone, and still meet: a wide stance opens both figures'
facing feet into the same few pixels, an arm swings through the other's arm. No still of either figure shows it, and
a box test cannot tell a near miss from a touch: two wide stances overlap their boxes long before their feet meet.
This check reads the drawn skeleton of each figure on each frame, one :class:`FigureBones` per figure per frame on
screen, in frame px, from the pose that frame actually shows, and for every pair of figures on the same frame
measures:

- the **bone distance**: the smallest distance between any bone of one and any bone of the other, centre line to
  centre line, less both strokes' half widths; a head is a disc of its radius and its outline's half width. At 0 or
  below the drawings touch;
- the **box gap**: the separation of the two figures' drawn boxes along whichever axis separates them more, negative
  when the boxes overlap. It is reported, never judged: a box gap below 0 is not a touch.

Every frame where a pair's bones meet is a :class:`PairFinding`, unless a :class:`DeclaredContact` names that pair and
covers that frame: a hand-hold or a lift is choreography, and only an explicit typed list declares it. No declaration
means no contact is allowed. The run is clean only with no finding.

A standing gate on every multi-character dance (arc4d3, Slack 1793669089.710129), with contact shadows and steps.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields
from itertools import combinations
from typing import Any

from .errors import SrstudioError

__all__ = [
    "ClearanceReport",
    "DeclaredContact",
    "FigureBones",
    "PairClearance",
    "PairClearanceError",
    "PairFinding",
    "check",
    "contacts",
    "parse",
    "rig_bones",
]

Point = tuple[float, float]
Segment = tuple[Point, Point]
TOUCH = 0.0  # px: bones this close, strokes included, are drawn touching
TIE = 1e-9


class PairClearanceError(SrstudioError, ValueError):
    """Records or a contact declaration that are not what the check reads."""


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise PairClearanceError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def _whole(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PairClearanceError(f"{name} must be a whole number from 0, got {value!r}")
    return value


def _name(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise PairClearanceError(f"{name} must be a name, got {value!r}")
    return value


def _point(value: object, name: str) -> Point:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise PairClearanceError(f"{name} must be a point (x, y), got {value!r}")
    return (_number(value[0], f"{name} x"), _number(value[1], f"{name} y"))


@dataclass(frozen=True)
class FigureBones:
    """One figure on one frame as drawn, in frame px: ``bones`` its strokes as segments, ``head`` its head disc
    ``(x, y, radius)`` or ``None`` for a figure with none, ``half_width`` half its stroke's width (0 for hairlines)."""

    figure: str
    frame: int
    bones: tuple[Segment, ...]
    head: tuple[float, float, float] | None
    half_width: float = 0.0

    def __post_init__(self) -> None:
        _name(self.figure, "figure")
        _whole(self.frame, "frame")
        if not isinstance(self.bones, (list, tuple)) or not self.bones:
            raise PairClearanceError(
                f"{self.figure} frame {self.frame}: bones must be a list of segments, got {self.bones!r}"
            )
        segs = []
        for k, seg in enumerate(self.bones):
            if not isinstance(seg, (list, tuple)) or len(seg) != 2:
                raise PairClearanceError(f"bone {k} must be two points, got {seg!r}")
            segs.append((_point(seg[0], f"bone {k} start"), _point(seg[1], f"bone {k} end")))
        object.__setattr__(self, "bones", tuple(segs))
        if self.head is not None:
            if not isinstance(self.head, (list, tuple)) or len(self.head) != 3:
                raise PairClearanceError(f"head must be (x, y, radius), got {self.head!r}")
            x, y, r = (_number(v, "head") for v in self.head)
            if r <= 0:
                raise PairClearanceError(f"a head's radius must be above 0, got {r!r}")
            object.__setattr__(self, "head", (x, y, r))
        if _number(self.half_width, "half_width") < 0:
            raise PairClearanceError(f"half_width must not be negative, got {self.half_width!r}")
        object.__setattr__(self, "half_width", float(self.half_width))


@dataclass(frozen=True)
class DeclaredContact:
    """The choreography's contact: figures ``pair`` (two names, sorted) may touch on frames ``first`` to ``last``."""

    pair: tuple[str, str]
    first: int
    last: int

    def __post_init__(self) -> None:
        if not isinstance(self.pair, tuple) or len(self.pair) != 2:
            raise PairClearanceError(f"a contact names two figures, got {self.pair!r}")
        a, b = (_name(v, "a contact's figure") for v in self.pair)
        if not a < b:
            raise PairClearanceError(f"a contact's figures must be two different names, sorted, got {self.pair!r}")
        if _whole(self.first, "first") > _whole(self.last, "last"):
            raise PairClearanceError(f"a contact's first frame {self.first} is after its last {self.last}")


@dataclass(frozen=True)
class PairFinding:
    """``pair`` touch on ``frame``: ``distance`` the bone distance, at or below 0."""

    pair: tuple[str, str]
    frame: int
    distance: float


@dataclass(frozen=True)
class PairClearance:
    """One pair over the run: ``frames`` they share, ``nearest`` and ``box_gap`` the smallest bone distance and box
    gap with their frames, ``declared`` the touching frames a declaration allowed."""

    pair: tuple[str, str]
    frames: int
    nearest: tuple[float, int]
    box_gap: tuple[float, int]
    findings: tuple[PairFinding, ...]
    declared: int


@dataclass(frozen=True)
class ClearanceReport:
    pairs: tuple[PairClearance, ...]

    @property
    def clean(self) -> bool:
        return all(not p.findings for p in self.pairs)


def parse(rows: Iterable[object]) -> tuple[FigureBones, ...]:
    """Records from plain mappings, as a build writes them: a missing or an unknown field raises."""
    names = {f.name for f in fields(FigureBones)}
    out = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise PairClearanceError(f"a record must be a mapping, got {row!r}")
        extra, missing = set(row) - names, names - set(row)
        if extra or missing:
            raise PairClearanceError(f"record fields: missing {sorted(missing)}, unknown {sorted(map(str, extra))}")
        fixed: dict[str, Any] = dict(row)
        out.append(FigureBones(**fixed))
    return tuple(out)


def contacts(rows: Iterable[object]) -> tuple[DeclaredContact, ...]:
    """A choreography's declared contacts from plain mappings ``{"figures": [a, b], "first": f, "last": l}``: a
    missing or unknown field, a figure with itself, a window backwards, or two windows of one pair that overlap
    raise."""
    out: list[DeclaredContact] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise PairClearanceError(f"a contact must be a mapping, got {row!r}")
        if set(row) != {"figures", "first", "last"}:
            raise PairClearanceError(f"a contact is figures, first and last, got fields {sorted(map(str, row))}")
        figures = row["figures"]
        if not isinstance(figures, (list, tuple)) or len(figures) != 2:
            raise PairClearanceError(f"a contact names two figures, got {figures!r}")
        a, b = (_name(v, "a contact's figure") for v in figures)
        if a == b:
            raise PairClearanceError(f"a contact names {a!r} with itself")
        out.append(DeclaredContact((min(a, b), max(a, b)), row["first"], row["last"]))
    by_pair: dict[tuple[str, str], list[DeclaredContact]] = {}
    for d in out:
        by_pair.setdefault(d.pair, []).append(d)
    for pair, windows in by_pair.items():
        windows.sort(key=lambda d: d.first)
        for x, y in zip(windows, windows[1:], strict=False):
            if y.first <= x.last:
                raise PairClearanceError(f"contacts for {pair} overlap: {x.first}-{x.last} and {y.first}-{y.last}")
    return tuple(out)


def rig_bones(pose: Any) -> tuple[tuple[Segment, ...], Point]:
    """The strokes a :mod:`srstudio.stick` rig draws for ``pose``, in the pose's own px, and its head's centre: the
    spine, each leg's thigh, shin and foot (ankle to :func:`srstudio.stick.foot_end`), each arm's upper arm and
    forearm. The caller maps them to frame px and gives the head its radius."""
    from . import stick

    p = lambda q: (float(q[0]), float(q[1]))  # noqa: E731
    segs: list[Segment] = [(p(pose.neck), p(pose.hip))]
    for k in (0, 1):
        segs += [
            (p(pose.hip), p(pose.knees[k])),
            (p(pose.knees[k]), p(pose.feet[k])),
            (p(pose.feet[k]), p(stick.foot_end(pose, k))),
        ]
    for k in (0, 1):
        segs += [(p(pose.neck), p(pose.elbows[k])), (p(pose.elbows[k]), p(pose.hands[k]))]
    return tuple(segs), p(pose.head)


def _cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _point_segment(q: Point, s: Segment) -> float:
    (ax, ay), (bx, by) = s
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    u = 0.0 if length == 0 else max(0.0, min(1.0, ((q[0] - ax) * dx + (q[1] - ay) * dy) / length))
    return math.hypot(q[0] - (ax + u * dx), q[1] - (ay + u * dy))


def _segments(s: Segment, t: Segment) -> float:
    """The exact distance between two segments: 0 when they cross, else the nearest endpoint to the other."""
    d1, d2 = _cross(t[0], t[1], s[0]), _cross(t[0], t[1], s[1])
    d3, d4 = _cross(s[0], s[1], t[0]), _cross(s[0], s[1], t[1])
    if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
        return 0.0
    return min(_point_segment(s[0], t), _point_segment(s[1], t), _point_segment(t[0], s), _point_segment(t[1], s))


def _distance(a: FigureBones, b: FigureBones) -> float:
    reach = a.half_width + b.half_width
    best = min(_segments(s, t) for s in a.bones for t in b.bones) - reach
    if a.head is not None:
        best = min(best, min(_point_segment(a.head[:2], t) for t in b.bones) - a.head[2] - reach)
    if b.head is not None:
        best = min(best, min(_point_segment(b.head[:2], s) for s in a.bones) - b.head[2] - reach)
    if a.head is not None and b.head is not None:
        best = min(best, math.dist(a.head[:2], b.head[:2]) - a.head[2] - b.head[2] - reach)
    return best


def _box(f: FigureBones) -> tuple[float, float, float, float]:
    xs = [q[0] for s in f.bones for q in s]
    ys = [q[1] for s in f.bones for q in s]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    if f.head is not None:
        hx, hy, r = f.head
        x0, y0, x1, y1 = min(x0, hx - r), min(y0, hy - r), max(x1, hx + r), max(y1, hy + r)
    h = f.half_width
    return x0 - h, y0 - h, x1 + h, y1 + h


def _box_gap(a: FigureBones, b: FigureBones) -> float:
    p, q = _box(a), _box(b)
    return max(q[0] - p[2], p[0] - q[2], q[1] - p[3], p[1] - q[3])


def check(figures: Iterable[FigureBones], declared: Sequence[DeclaredContact] = ()) -> ClearanceReport:
    """Measure every pair of figures on every frame they share, and find each frame their bones meet that no
    declaration allows, whatever order the records come in."""
    frames: dict[int, dict[str, FigureBones]] = {}
    for record in figures:
        on = frames.setdefault(record.frame, {})
        if record.figure in on:
            raise PairClearanceError(f"{record.figure} is on frame {record.frame} twice")
        on[record.figure] = record
    if not frames:
        raise PairClearanceError("no figures to check")
    for d in declared:
        if not isinstance(d, DeclaredContact):
            raise PairClearanceError(f"a declared contact must be a DeclaredContact, got {d!r}")
    measured: dict[tuple[str, str], list[tuple[int, float, float]]] = {}
    for frame in sorted(frames):
        on = frames[frame]
        for a, b in combinations(sorted(on), 2):
            measured.setdefault((a, b), []).append((frame, _distance(on[a], on[b]), _box_gap(on[a], on[b])))
    for d in declared:
        if d.pair not in measured:
            raise PairClearanceError(f"a contact is declared for {d.pair}, never on screen together")
    out = []
    for pair in sorted(measured):
        rows = measured[pair]
        windows = [(d.first, d.last) for d in declared if d.pair == pair]
        touching = [(f, dist) for f, dist, _ in rows if dist <= TOUCH + TIE]
        allowed = [(f, dist) for f, dist in touching if any(lo <= f <= hi for lo, hi in windows)]
        findings = tuple(PairFinding(pair, f, dist) for f, dist in touching if (f, dist) not in allowed)
        nearest = min(((dist, f) for f, dist, _ in rows), key=lambda x: (x[0], x[1]))
        gap = min(((g, f) for f, _, g in rows), key=lambda x: (x[0], x[1]))
        out.append(PairClearance(pair, len(rows), nearest, gap, findings, len(allowed)))
    return ClearanceReport(tuple(out))

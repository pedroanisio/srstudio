"""A Cutout figure on its marks: a hard cut to a place between shots, or a walk there with a stride's bob and sway.

The Cutout rigs have no legs that step, so a walk is the paper puppet's: the figure slides along the floor and rises
between footfalls. ``rows`` are ``(time, x)``: two rows at one time are a cut, two rows with the same ``x`` are a stand
and two with different ``x`` are a walk. :func:`footfalls` gives the time each foot lands, for a reel's foley. Every
refusal is a :class:`CutoutWalkError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .errors import SrstudioError

__all__ = ["CUT", "CutoutWalkError", "bob", "footfalls", "track", "walk"]

CUT = 1 / 240  # how long before its frame a cut's old place ends: under any frame, so the slide is never drawn
STRIDE = 0.28  # seconds a stride takes
LIFT = 12.0  # how far a stride rises, in the parent's units
SWAY = 1.5  # degrees either way, a stride each
FASTEST = 2000.0  # units a second no walk reaches: past it, it is a cut

Row = tuple[float, float]


class CutoutWalkError(SrstudioError, ValueError):
    """Marks that cannot be walked, or a stride that cannot be taken."""


def _check(rows: Sequence[Row], stride: float) -> None:
    if not (checks.number(stride) and stride > 0):
        raise CutoutWalkError(f"a stride takes a positive time, got {stride!r}")
    if len(rows) < 2:
        raise CutoutWalkError(f"a figure's marks take at least two rows, got {len(rows)}")
    for t, x in rows:
        if not (checks.number(t) and checks.number(x)):
            raise CutoutWalkError(f"a mark's time and place are numbers, got {t!r}, {x!r}")
    if rows[0][0] < 0:
        raise CutoutWalkError(f"a figure's marks start at 0 or later: {rows[0][0]} is before the reel")
    for (a, xa), (b, xb) in zip(rows, rows[1:], strict=False):
        if b < a:
            raise CutoutWalkError(f"a figure's marks run forward, {a} to {b} runs backwards")
        if b > a and abs(xb - xa) / (b - a) > FASTEST:
            raise CutoutWalkError(f"{xa} to {xb} in {b - a} s is too fast to walk: two rows at one time are a cut")


def _walks(rows: Sequence[Row]) -> list[tuple[float, float]]:
    return [(a, b) for (a, xa), (b, xb) in zip(rows, rows[1:], strict=False) if b > a and xa != xb]


def _strides(start: float, end: float, stride: float) -> tuple[int, float]:
    """How many strides fill ``start`` to ``end``, nearest to ``stride``, and how long each takes."""
    count = max(1, round((end - start) / stride))
    return count, (end - start) / count


def footfalls(rows: Sequence[Row], *, stride: float = STRIDE) -> tuple[float, ...]:
    """When each foot lands, the last on the mark: nothing for a stand or a cut."""
    _check(rows, stride)
    out: list[float] = []
    for start, end in _walks(rows):
        count, each = _strides(start, end, stride)
        out += [start + k * each for k in range(1, count + 1)]
    return tuple(out)


def track(rows: Sequence[Row]) -> list[Row]:
    """The ``x`` keys of ``rows``, a cut's old place ending just under a frame before its new one starts."""
    _check(rows, STRIDE)
    out: list[Row] = []
    for i, (t, x) in enumerate(rows):
        if i and t == rows[i - 1][0]:
            out[-1] = (t - CUT, rows[i - 1][1])
        out.append((t, x))
    return out


def bob(rows: Sequence[Row], y: float, *, stride: float = STRIDE, lift: float = LIFT) -> list[Row]:
    """The ``y`` keys: on the floor at each footfall, up by ``lift`` halfway between them, and still while it stands."""
    _check(rows, stride)
    keys: list[Row] = [(rows[0][0], y)]
    for start, end in _walks(rows):
        count, each = _strides(start, end, stride)
        keys.append((start, y))
        for k in range(count):
            keys += [(start + (k + 0.5) * each, y - lift), (start + (k + 1) * each, y)]
    keys.append((rows[-1][0], y))
    return [row for i, row in enumerate(keys) if i == 0 or row[0] > keys[i - 1][0]]


def _sway(rows: Sequence[Row], stride: float, sway: float) -> list[Row]:
    keys: list[Row] = [(rows[0][0], 0.0)]
    for start, end in _walks(rows):
        count, each = _strides(start, end, stride)
        keys.append((start, 0.0))
        keys += [(start + (k + 0.5) * each, sway if k % 2 else -sway) for k in range(count)]
        keys.append((end, 0.0))
    return [row for i, row in enumerate(keys) if i == 0 or row[0] > keys[i - 1][0]]


def walk(
    cv: Canvas, node, rows: Sequence[Row], y: float, *, stride: float = STRIDE, lift: float = LIFT, sway: float = SWAY
) -> tuple[float, ...]:
    """Keys ``node``, a performed figure, along ``rows`` with its feet on ``y``, and gives back its footfalls."""
    falls = footfalls(rows, stride=stride)
    cv.keys(node, "x", track(rows), hold=False)
    cv.keys(node, "y", bob(rows, y, stride=stride, lift=lift), hold=False)
    if falls and sway:
        cv.keys(node, "rotation", _sway(rows, stride, sway), hold=False)
    return falls

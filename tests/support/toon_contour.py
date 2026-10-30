"""How smoothly a Toon outline runs (ADR 0049): the outer contour of a closed shape split into its left and right
sides over a band of heights, resampled at an even spacing, and the angle the line turns at every step."""

from __future__ import annotations

import math

from srstudio import toon_cast
from support.toon_thumbnail import _inside, _polygon

STEP = 8.0  # reference pixels between the samples the turning angle is measured over


def resample(path: list[tuple[float, float]], step: float = STEP) -> list[tuple[float, float]]:
    """Points every ``step`` along an open polyline, from its first point."""
    out = [path[0]]
    carried = 0.0
    for a, b in zip(path, path[1:], strict=False):
        length = math.dist(a, b)
        at = step - carried
        while at <= length:
            t = at / length
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            at += step
        carried = length - (at - step)
    return out


def turns(path: list[tuple[float, float]]) -> list[float]:
    """The signed angle, in degrees, the polyline turns at each inner point (positive clockwise on screen)."""
    out = []
    for a, b, c in zip(path, path[1:], path[2:], strict=False):
        ux, uy = b[0] - a[0], b[1] - a[1]
        vx, vy = c[0] - b[0], c[1] - b[1]
        out.append(math.degrees(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)))
    return out


def sides(shape, top: float, bottom: float) -> dict[str, list[tuple[float, float]]]:
    """The outline of a closed cubic ``shape`` between the heights ``top`` and ``bottom``, as its left and right
    runs (left and right of the figure's centre), each from top to bottom."""
    poly = _polygon(shape)
    low = max(range(len(poly)), key=lambda i: poly[i][1])
    poly = poly[low:] + poly[:low]  # start at the bottom, so no side wraps round the start
    runs: dict[str, list[tuple[float, float]]] = {"left": [], "right": []}
    for x, y in poly:
        if top <= y <= bottom:
            runs["left" if x < toon_cast.CENTRE else "right"].append((x, y))
    return {side: run[::-1] if run and run[0][1] > run[-1][1] else run for side, run in runs.items()}


def bends(shape, top: float, bottom: float) -> dict[str, list[float]]:
    """The turns, in degrees per :data:`STEP` px, down each side of the outline between ``top`` and ``bottom``:
    positive where the outline bulges out (a shoulder), negative where it curves in (a neck, a notch)."""
    runs = sides(shape, top, bottom)
    return {"left": [-t for t in turns(resample(runs["left"]))], "right": turns(resample(runs["right"]))}


def sharpest(shape, top: float, bottom: float) -> tuple[float, float]:
    """The sharpest outward and the sharpest inward turn, in degrees per :data:`STEP` px, of the outline's sides
    between ``top`` and ``bottom`` (0 when it never turns that way)."""
    every = [t for run in bends(shape, top, bottom).values() for t in run]
    return max([0.0, *every]), max([0.0, *(-t for t in every)])


def inside(shape, x: float, y: float) -> bool:
    """Whether ``(x, y)`` lies inside the closed cubic ``shape``."""
    return _inside(_polygon(shape), x, y)


def points(shape) -> list[tuple[float, float]]:
    """A closed cubic shape sampled into its outline."""
    return _polygon(shape)

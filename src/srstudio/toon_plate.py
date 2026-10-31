"""Flat spot-colour plates for the Toon style: a mid-century poster drawn as code, in the shapes the brush cast is made
of (:data:`srstudio.toon_cast.Layer`), so a plate goes through :class:`srstudio.canvas.Canvas` and into a digest like
every other part.

:func:`shape` turns an absolute SVG-style path (``M L Q C Z``, nothing else) into a closed cubic
:data:`srstudio.brush.Shape`; :class:`Frame` places what a plate was drawn in into the frame of the part that uses it
(a point is scaled, turned, then moved, and frames nest); :func:`clip` and :func:`inside` stand in for a clip path,
which a flat shape does not have: the outline is convex and the result is an ordinary polygon. :func:`ell`, :func:`box`,
:func:`rule`, :func:`hoop`, :func:`burst` and :func:`atom` are a plate's small vocabulary.

Coordinates come in as they were drawn and go out as Toon reference pixels. The colours are literal, so a plate keeps
its print palette on any canvas palette. Bad input is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

from . import brush, checks
from .brush import Point, Shape
from .toon import ToonDataError

__all__ = [
    "CORAL",
    "CREAM",
    "GOLD",
    "HILLS",
    "IDENTITY",
    "MINT",
    "MUTED",
    "NAVY",
    "NIGHT",
    "PALE",
    "PAPER",
    "SOLID",
    "TEAL",
    "Frame",
    "Plate",
    "atom",
    "box",
    "burst",
    "clip",
    "curve",
    "ell",
    "hoop",
    "inside",
    "points",
    "polygon",
    "rule",
    "shape",
]

PAPER = "#F3E5C4"
NAVY = "#173D46"
TEAL = "#398E95"
MINT = "#A7C9B8"
CORAL = "#D9623D"
GOLD = "#D5A244"
CREAM = "#FAF0D4"
PALE = "#DED7B4"
MUTED = "#5B7773"
NIGHT = "#285A63"
HILLS = "#326D73"

Plate = list[tuple[Shape, str]]  # a run of (shape, colour) layers, reference pixels

SOLID = brush.Pressure(1.0, 1.0, 0.0, 0.0, 2.0)  # a ruled line: the same weight end to end, with round ends
_TOKEN = re.compile(r"[A-Za-z]|-?\d+(?:\.\d+)?")
_ARITY = {"M": 2, "L": 2, "Q": 4, "C": 6}
_ARC = 0.5522847498  # a circle's cubic handle
_CURVE_STEPS = 10  # points per curved segment when a path is walked as a polyline


@dataclass(frozen=True)
class Frame:
    """Where a plate goes: its point ``(x, y)`` lands at ``(self.x + scale * x', self.y + scale * y')``, ``x', y'``
    being the point turned ``rotate`` degrees clockwise (y down) about the plate's origin."""

    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    rotate: float = 0.0

    def __post_init__(self) -> None:
        if not (checks.number(self.scale) and self.scale > 0.0):
            raise ToonDataError(f"a frame's scale is a positive number, got {self.scale!r}")
        if not (checks.number(self.x) and checks.number(self.y) and checks.number(self.rotate)):
            raise ToonDataError(f"a frame's place and turn are finite numbers, got {self!r}")

    def point(self, x: float, y: float) -> Point:
        a = math.radians(self.rotate)
        c, s = math.cos(a), math.sin(a)
        return (self.x + self.scale * (x * c - y * s), self.y + self.scale * (x * s + y * c))

    def then(self, inner: Frame) -> Frame:
        """The frame that places a plate first by ``inner``, then by this one."""
        x, y = self.point(inner.x, inner.y)
        return Frame(x, y, self.scale * inner.scale, self.rotate + inner.rotate)


IDENTITY = Frame()


def curve(d: str) -> list[tuple[str, tuple[float, ...]]]:
    """The commands of an absolute path, checked: one ``M`` first, then ``L``, ``Q``, ``C``, and an optional ``Z``."""
    tokens = _TOKEN.findall(d)
    if "".join(tokens) != "".join(d.split()):
        raise ToonDataError(f"a path holds commands and numbers only, got {d!r}")
    out: list[tuple[str, tuple[float, ...]]] = []
    i = 0
    while i < len(tokens):
        command = tokens[i]
        i += 1
        if command == "Z":
            if i != len(tokens):
                raise ToonDataError(f"Z ends a path, got {d!r}")
            break
        if command not in _ARITY:
            raise ToonDataError(f"this parser reads absolute M, L, Q, C and Z, got {command!r} in {d!r}")
        n = _ARITY[command]
        chunk = tokens[i : i + n]
        if len(chunk) != n:
            raise ToonDataError(f"{command} takes {n} numbers, got {chunk!r} in {d!r}")
        try:
            numbers = tuple(float(t) for t in chunk)
        except ValueError:
            raise ToonDataError(f"{command} takes numbers, got {chunk!r} in {d!r}") from None
        i += n
        out.append((command, numbers))
    if not out or out[0][0] != "M" or any(c == "M" for c, _ in out[1:]):
        raise ToonDataError(f"a path is one M and what follows it, got {d!r}")
    return out


def _segments(d: str, frame: Frame) -> tuple[Point, list[tuple[Point, Point, Point]]]:
    """A path as its start and cubic segments, placed."""
    commands = curve(d)
    start = frame.point(*commands[0][1])
    here = start
    out: list[tuple[Point, Point, Point]] = []
    for command, n in commands[1:]:
        if command == "L":
            end = frame.point(*n)
            out.append((_toward(here, end, 1 / 3), _toward(here, end, 2 / 3), end))
        elif command == "Q":
            q, end = frame.point(*n[:2]), frame.point(*n[2:])
            out.append((_toward(here, q, 2 / 3), _toward(end, q, 2 / 3), end))
        else:
            out.append((frame.point(*n[:2]), frame.point(*n[2:4]), frame.point(*n[4:])))
        here = out[-1][2]
    return start, out


def _toward(a: Point, b: Point, t: float) -> Point:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _flatten(start: Point, segments: Sequence[tuple[Point, Point, Point]]) -> Shape:
    values = [*start]
    for c1, c2, end in segments:
        values += [*c1, *c2, *end]
    return tuple(round(v, 2) for v in values)


def shape(d: str, frame: Frame = IDENTITY) -> Shape:
    """A closed brush shape from a path; an open one closes back to its start with a straight line."""
    start, segments = _segments(d, frame)
    here = segments[-1][2] if segments else start
    if math.dist(here, start) > 0.01:
        segments = [*segments, (_toward(here, start, 1 / 3), _toward(here, start, 2 / 3), start)]
    return _flatten(start, segments)


def points(d: str, frame: Frame = IDENTITY, steps: int = _CURVE_STEPS) -> tuple[Point, ...]:
    """A path walked as a polyline: a line's end, or ``steps`` points along a curve."""
    start, segments = _segments(d, frame)
    commands = curve(d)[1:]
    out = [start]
    here = start
    for (command, _), (c1, c2, end) in zip(commands, segments, strict=False):
        if command == "L":
            out.append(end)
        else:
            for k in range(1, steps + 1):
                t = k / steps
                u = 1 - t
                out.append(
                    (
                        u**3 * here[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * end[0],
                        u**3 * here[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * end[1],
                    )
                )
        here = end
    return tuple(out)


def polygon(corners: Sequence[Point]) -> Shape:
    """A closed brush shape with straight sides."""
    if len(corners) < 3:
        raise ToonDataError(f"a polygon has three corners or more, got {len(corners)}")
    here = corners[0]
    segments = []
    for end in (*corners[1:], corners[0]):
        segments.append((_toward(here, end, 1 / 3), _toward(here, end, 2 / 3), end))
        here = end
    return _flatten(corners[0], segments)


def _winding(outline: Sequence[Point]) -> float:
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, (*outline[1:], outline[0]), strict=True))


def _side(a: Point, b: Point, p: Point, sign: float) -> float:
    return sign * ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]))


def clip(subject: Sequence[Point], outline: Sequence[Point]) -> tuple[Point, ...]:
    """What of the polygon ``subject`` lies inside the convex polygon ``outline`` (Sutherland-Hodgman)."""
    sign = 1.0 if _winding(outline) > 0 else -1.0
    out = list(subject)
    for a, b in zip(outline, (*outline[1:], outline[0]), strict=True):
        if not out:
            break
        kept: list[Point] = []
        for p, q in zip(out, (*out[1:], out[0]), strict=True):
            dp, dq = _side(a, b, p, sign), _side(a, b, q, sign)
            if dp >= 0.0:
                kept.append(p)
            if (dp < 0.0) != (dq < 0.0):
                kept.append(_toward(p, q, dp / (dp - dq)))
        out = kept
    return tuple(out)


def inside(line: Sequence[Point], outline: Sequence[Point]) -> tuple[Point, ...]:
    """The points of a polyline that lie inside the convex polygon ``outline``."""
    sign = 1.0 if _winding(outline) > 0 else -1.0
    edges = list(zip(outline, (*outline[1:], outline[0]), strict=True))
    return tuple(p for p in line if all(_side(a, b, p, sign) >= 0.0 for a, b in edges))


def ell(cx: float, cy: float, rx: float, ry: float, frame: Frame = IDENTITY, tilt: float = 0.0) -> Shape:
    """An ellipse, turned ``tilt`` degrees clockwise about its centre, placed."""
    x, y = frame.point(cx, cy)
    return brush.ellipse(x, y, rx * frame.scale, ry * frame.scale, frame.rotate + tilt)


def box(x: float, y: float, w: float, h: float, frame: Frame = IDENTITY, radius: float = 0.0) -> Shape:
    """A rectangle with its corners rounded by ``radius``, placed."""
    r = min(radius, w / 2, h / 2)
    x1, y1 = x + w, y + h
    if r <= 0.0:
        return polygon([frame.point(*p) for p in ((x, y), (x1, y), (x1, y1), (x, y1))])
    k = r * (1 - _ARC)
    return shape(
        f"M {x + r} {y} L {x1 - r} {y} C {x1 - k} {y} {x1} {y + k} {x1} {y + r} L {x1} {y1 - r} "
        f"C {x1} {y1 - k} {x1 - k} {y1} {x1 - r} {y1} L {x + r} {y1} C {x + k} {y1} {x} {y1 - k} {x} {y1 - r} "
        f"L {x} {y + r} C {x} {y + k} {x + k} {y} {x + r} {y} Z",
        frame,
    )


def rule(d: str, weight: float, frame: Frame = IDENTITY) -> Shape:
    """A ruled line along a path, ``weight`` as drawn."""
    line = points(d, frame)
    return brush.stroke(line, weight * frame.scale, SOLID, steps=1)


def hoop(
    cx: float, cy: float, rx: float, ry: float, weight: float, frame: Frame = IDENTITY, tilt: float = 0.0
) -> Shape:
    """An ellipse's line and no fill, ``weight`` as drawn."""
    a = math.radians(tilt)
    c, s = math.cos(a), math.sin(a)
    line = []
    for k in range(51):  # past the start, so the ends lap
        t = 2 * math.pi * k / 48
        ex, ey = rx * math.cos(t), ry * math.sin(t)
        line.append(frame.point(cx + ex * c - ey * s, cy + ex * s + ey * c))
    return brush.stroke(line, weight * frame.scale, SOLID, steps=1)


def burst(x: float, y: float, r: float, colour: str, arms: int = 8, frame: Frame = IDENTITY) -> Plate:
    """A star of ``arms`` needle points."""
    corners = []
    for i in range(arms * 2):
        a = math.pi * i / arms - math.pi / 2
        radius = r if i % 2 == 0 else r * 0.13
        corners.append(frame.point(x + math.cos(a) * radius, y + math.sin(a) * radius))
    return [(polygon(corners), colour)]


def atom(x: float, y: float, size: float, colour: str, frame: Frame = IDENTITY) -> Plate:
    """The mid-century atom: three orbits, a coral nucleus, a gold electron."""
    f = frame.then(Frame(x, y, size))
    out: Plate = [(hoop(0.0, 0.0, 43.0, 15.0, 1.9, f, tilt), colour) for tilt in (0.0, 60.0, -60.0)]
    return out + [(ell(0.0, 0.0, 6.0, 6.0, f), CORAL), (ell(39.0, 6.0, 5.0, 5.0, f), GOLD)]

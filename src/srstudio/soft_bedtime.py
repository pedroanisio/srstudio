"""Soft, a bedtime: a wall clock, a picture book that slides, a lamp, an open case, a handshake, a quilt pulled up.

Each prop is drawn at ``x``, ``y`` in its parent's pixels and keyed on the episode's clock. Drawn inside a room they go
dark with it. Every refusal is a :class:`SoftPropError`.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from . import checks
from .blob import BO_FILL
from .canvas import Canvas
from .registry import register
from .soft_props import SoftPropError

__all__ = [
    "BookSlide",
    "SoftPropError",
    "bedside_lamp",
    "clock_hands",
    "handshake",
    "open_briefcase",
    "picture_book",
    "quilt_pull",
    "wall_clock",
]

WIDTH, HEIGHT = 1080, 1920
LATER = 1e6  # a gate that never closes
_TIME = re.compile(r"^(\d{1,2}):(\d{2})$")
LEATHER, LEATHER_LIGHT, BRASS, PAPER = "#8A5A36", "#9C6A42", "#E9C766", "#FBF6E9"
SHADE, SHADE_OFF, BULB = "#FFD98A", "#B8A98E", "#FFF3CF"
QUILT, QUILT_LINE = "#D8836B", "#B9654F"
PIP_FILL, CUFF = "#FFFFFF", "#F4F0EA"


class BookSlide(NamedTuple):
    """From ``time``, over ``seconds``, the book moves by (``dx``, ``dy``) and ends turned ``turn`` degrees."""

    time: float
    seconds: float
    dx: float
    dy: float
    turn: float = 0.0


def _check_place(x, y, scale, what: str) -> None:
    if not (checks.number(x) and checks.number(y) and checks.number(scale) and scale > 0):
        raise SoftPropError(f"{what} sits at a finite place with a positive scale, got {x!r}, {y!r}, {scale!r}")


def _check_time(value, what: str) -> None:
    if not checks.number(value) or value < 0:
        raise SoftPropError(f"{what} is a time on the clock, got {value!r}")


def clock_hands(time: str) -> tuple[float, float]:
    """The hour and minute hands of ``time`` ("H:MM"), in degrees clockwise from twelve."""
    found = _TIME.match(time) if isinstance(time, str) else None
    if found is None or int(found[1]) > 23 or int(found[2]) > 59:
        raise SoftPropError(f"a clock reads H:MM, got {time!r}")
    hours, minutes = int(found[1]) % 12, int(found[2])
    return hours * 30.0 + minutes * 0.5, minutes * 6.0


@register("prop", "soft-wall-clock", summary="A round wall clock with no numbers, reading the time it is given")
def wall_clock(
    cv: Canvas, parent, x=540, y=600, *, time: str = "8:30", scale: float = 1.0, id: str = "soft-wall-clock"
):
    """A face 200 px across at ``scale`` 1, its middle at (``x``, ``y``)."""
    _check_place(x, y, scale, "a wall clock")
    hour, minute = clock_hands(time)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -100, -100, 200, 200, PAPER, ink, 8)
    for turn in range(0, 360, 30):
        cv.line(cv.group(g, f"{id}-tick-{turn}", rotation=turn), 0, -86, 0, -74, ink, 6)
    cv.line(cv.group(g, f"{id}-hour", rotation=hour), 0, 8, 0, -50, ink, 12)
    cv.line(cv.group(g, f"{id}-minute", rotation=minute), 0, 10, 0, -74, ink, 8)
    cv.ellipse(g, -9, -9, 18, 18, ink)
    return g


@register("prop", "soft-picture-book", summary="A picture book held open, its cover to us, that can slide away")
def picture_book(
    cv: Canvas,
    parent,
    x=540,
    y=1400,
    *,
    slide: BookSlide | None = None,
    scale: float = 1.0,
    id: str = "soft-picture-book",
):
    """A book 300 px wide at ``scale`` 1, the middle of its spine at (``x``, ``y``). ``slide`` lets go of it."""
    _check_place(x, y, scale, "a picture book")
    if slide is not None:
        _check_time(slide.time, "a book's slide")
        fine = checks.number(slide.seconds) and slide.seconds > 0
        if not (fine and all(checks.number(v) for v in (slide.dx, slide.dy, slide.turn))):
            raise SoftPropError(f"a slide takes time and goes somewhere finite, got {slide!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -150, -105, 300, 210, "#3E8E6A", ink, 6, radius=10)
    cv.line(g, 0, -105, 0, 105, ink, 6)
    cv.ellipse(g, 44, -66, 72, 72, "#B98A5E", ink, 5)  # the little bear, on the front cover
    cv.ellipse(g, 40, -76, 28, 28, "#B98A5E", ink, 5)
    cv.ellipse(g, 92, -76, 28, 28, "#B98A5E", ink, 5)
    cv.ellipse(g, 74, -38, 12, 10, ink)
    cv.rect(g, 36, 28, 88, 12, BRASS, radius=6)
    cv.rect(g, 52, 50, 56, 12, BRASS, radius=6)
    if slide is not None:
        done = slide.time + slide.seconds
        cv.keys(g, "x", [(0.0, x), (slide.time, x), (done, x + slide.dx)], hold=False)
        cv.keys(g, "y", [(0.0, y), (slide.time, y), (done, y + slide.dy)], hold=False)
        cv.keys(g, "rotation", [(0.0, 0.0), (slide.time, 0.0), (done, slide.turn)], hold=False)
    return g


@register("prop", "soft-bedside-lamp", summary="A small bedside lamp, lit until it clicks off")
def bedside_lamp(
    cv: Canvas, parent, x=980, y=1662, *, off: float = LATER, scale: float = 1.0, id: str = "soft-bedside-lamp"
):
    """A lamp 300 px tall at ``scale`` 1, its base on (``x``, ``y``), lit until ``off``."""
    _check_place(x, y, scale, "a bedside lamp")
    _check_time(off, "a lamp's click")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -56, -16, 112, 16, "#6B4A30", ink, 5, radius=6)
    cv.rect(g, -12, -140, 24, 126, "#8A5A36", ink, 5, radius=6)
    unlit = cv.group(g, f"{id}-unlit")
    cv.path(unlit, "M -62 -300 L 62 -300 L 104 -136 L -104 -136 Z", SHADE_OFF, ink, 6)
    lit = cv.group(g, f"{id}-lit")
    cv.gate(lit, [(0.0, off)])
    cv.ellipse(lit, -44, -210, 88, 88, BULB)
    cv.path(lit, "M -62 -300 L 62 -300 L 104 -136 L -104 -136 Z", SHADE, ink, 6)
    return g


@register("prop", "soft-open-briefcase", summary="A briefcase open on a quilt, a contract inside, that can shut")
def open_briefcase(
    cv: Canvas, parent, x=600, y=1640, *, shut: float = LATER, scale: float = 1.0, id: str = "soft-open-briefcase"
):
    """A case 240 px wide at ``scale`` 1, the middle of its hinge at (``x``, ``y``), open until ``shut``."""
    _check_place(x, y, scale, "a briefcase")
    _check_time(shut, "a case's shutting")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    opened = cv.group(g, f"{id}-open")
    cv.gate(opened, [(0.0, shut)])
    cv.rect(opened, -120, -150, 240, 150, LEATHER, ink, 5, radius=14)
    cv.rect(opened, -104, -136, 208, 122, "#C9A77E", ink, 3, radius=8)
    cv.rect(opened, -70, -126, 112, 106, PAPER, ink, 3)  # the terms, pinned in the lid
    cv.line(opened, -56, -102, 26, -102, ink, 5)
    cv.line(opened, -56, -78, 26, -78, ink, 5)
    cv.line(opened, -56, -44, -6, -44, "#2F5D8C", 5)
    cv.rect(opened, -124, 0, 248, 76, LEATHER_LIGHT, ink, 5, radius=12)
    for cx in (-66, 66):
        cv.rect(opened, cx - 14, 0, 28, 22, BRASS, ink, 4, radius=6)
    closed = cv.group(g, f"{id}-shut")
    cv.gate(closed, [(shut, LATER)])
    cv.rect(closed, -124, -76, 248, 152, LEATHER, ink, 5, radius=14)
    cv.rect(closed, -124, -76, 248, 56, LEATHER_LIGHT, ink, 4, radius=14)
    for cx in (-66, 66):
        cv.rect(closed, cx - 14, -36, 28, 30, BRASS, ink, 4, radius=6)
    return g


def _arm(cv: Canvas, g, x1, y1, x2, y2, fill: str, width: float, *, grip_x: float) -> None:
    ink = cv.ink
    cv.line(g, x1, y1, x2, y2, ink, width + 12)
    cv.line(g, x1, y1, x2, y2, fill, width)
    radius = width * 0.72
    cv.ellipse(g, grip_x - radius, y2 - radius, 2 * radius, 2 * radius, fill, ink, 6)


@register("prop", "soft-handshake", summary="A close shot of a deal: a small hand and a big one, shaking on it")
def handshake(cv: Canvas, parent, start: float = 1.0, end: float = 2.0, *, pumps: int = 2, id: str = "soft-handshake"):
    """The whole frame from ``start`` to ``end``: a quilt, Bo's arm from the right, Pip's from the left, shaking."""
    _check_time(start, "a handshake's start")
    if not (checks.number(end) and end > start):
        raise SoftPropError(f"a handshake ends after it starts, got {start!r} to {end!r}")
    if not (isinstance(pumps, int) and pumps > 0):
        raise SoftPropError(f"a handshake pumps at least once, got {pumps!r}")
    ink = cv.ink
    g = cv.group(parent, id)
    cv.gate(g, [(start, end)])
    cv.rect(g, 0, 0, WIDTH, HEIGHT, QUILT)
    cv.path(g, "M 90 420 Q 260 380 420 430 M 620 330 Q 800 300 960 350", stroke=QUILT_LINE, sw=10)
    cv.path(g, "M 60 1500 Q 300 1460 480 1520 M 640 1600 Q 820 1560 1020 1620", stroke=QUILT_LINE, sw=10)
    grip = cv.group(g, f"{id}-grip", y=0)
    _arm(cv, grip, 1240, 1240, 640, 900, BO_FILL, 230, grip_x=640)
    cv.line(grip, 960, 950, 1100, 1330, "#5F7FA0", 90)  # Bo's pajama cuff
    _arm(cv, grip, -120, 1140, 450, 930, PIP_FILL, 130, grip_x=450)
    cv.line(grip, 130, 955, 190, 1160, CUFF, 96)
    cv.line(grip, 96, 960, 156, 1170, ink, 10)  # a shirt cuff: he came dressed for this
    for k in range(3):
        cv.line(grip, 470 + 44 * k, 870 + 12 * k, 500 + 44 * k, 960 + 12 * k, ink, 9)  # Pip's fingers, on Bo's hand
    step = (end - start) / (2 * pumps + 1)
    beats = [start + step * (k + 1) for k in range(2 * pumps)]
    cv.keys(grip, "y", [(start, 0.0), *((t, 60.0 if k % 2 == 0 else 0.0) for k, t in enumerate(beats))], hold=False)
    return g


@register("prop", "soft-quilt-pull", summary="The top of a quilt, drawn up over whoever is asleep under it")
def quilt_pull(
    cv: Canvas,
    parent,
    x=200,
    y=1540,
    to: float = 1350,
    at: float = 1.0,
    seconds: float = 0.5,
    *,
    width: float = 640,
    id: str = "soft-quilt-pull",
):
    """A quilt ``width`` px across, its top at ``y`` until ``at``, up at ``to`` ``seconds`` later."""
    _check_place(x, y, 1, "a quilt")
    if not (checks.number(to) and to < y):
        raise SoftPropError(f"a quilt is pulled up, from {y!r} to {to!r}")
    _check_time(at, "a quilt's pull")
    if not (checks.number(seconds) and seconds > 0 and checks.number(width) and width > 0):
        raise SoftPropError(f"a quilt takes time and has a width, got {seconds!r} and {width!r}")
    g = cv.group(parent, id, x=x, y=y)
    top = f"M 0 40 Q {width * 0.4} -20 {width} 60"  # its bottom and its far side melt into the quilt under it
    cv.path(g, f"{top} L {width} 800 L 0 800 Z", QUILT, "#00000000", 0)
    cv.path(g, top, stroke=QUILT_LINE, sw=7)
    cv.path(g, top, stroke="#F4E3D3", sw=20)
    cv.keys(g, "y", [(0.0, y), (at, y), (at + seconds, to)], hold=False)
    return g

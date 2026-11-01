"""Cutout, what a phone tells your family: a phone on a table, a map chip with a dot, and a dinner to stop eating.

The map is an invented chip: pale blocks, two roads and a blue dot, copying no real app, and it letters nothing, so it
can never repeat a caption. Its stops are a place setting, a pharmacy's cross and a house under a moon. The notice is
the only lettering, given by the reel. Every refusal is a :class:`CutoutLocateError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = [
    "CutoutLocateError",
    "dinner_plate",
    "held_phone",
    "location_chip",
    "notice_phone",
    "table_fork",
    "table_phone",
]

BLUE = "#2F7DE1"
BODY = "#22262C"
MAP = "#E7EDE2"
ROAD = "#FFFFFF"
BLOCK = "#CFDCC8"
KINDS = ("table", "cross", "moon")
NOTICE_LINE = 15  # the most characters on a line of the notice
NOTICE_LINES = 2
RATTLE = 0.04  # seconds between a ringing phone's shakes


class CutoutLocateError(SrstudioError, ValueError):
    """A prop asked for with arguments it cannot be drawn from."""


def _scale(scale) -> None:
    checks.positive(scale, CutoutLocateError, f"scale must be a positive number, got {scale!r}")


def _spans(values, what: str) -> list[tuple[float, float]]:
    return checks.spans(values, CutoutLocateError, lambda s: f"{what} is a rising span from 0, got {s!r}")


def _map(cv: Canvas, g, x, y, w, h, *, radius: float = 18) -> None:
    """The invented map, inside the box: pale ground, blocks and two roads, clipped by being drawn inside it."""
    cv.rect(g, x, y, w, h, MAP, cv.ink, 3, radius=radius)
    for bx, by, bw, bh in (
        (0.08, 0.1, 0.3, 0.3),
        (0.56, 0.08, 0.36, 0.26),
        (0.1, 0.62, 0.26, 0.28),
        (0.6, 0.58, 0.3, 0.32),
    ):
        cv.rect(g, x + bx * w, y + by * h, bw * w, bh * h, BLOCK, radius=8)
    cv.rect(g, x + 0.44 * w, y + 3, 0.09 * w, h - 6, ROAD)
    cv.rect(g, x + 3, y + 0.46 * h, w - 6, 0.09 * h, ROAD)


def _dot(cv: Canvas, g, x, y, start: float, end: float, *, size: float = 26) -> None:
    pulse = cv.group(g, cv.uid("dot-pulse"), x=x, y=y)
    keys = []
    at = start
    while at < end:
        keys += [(at, 0.8), (at + 0.5, 1.3)]
        at += 0.6
    cv.keys(pulse, "scaleX", keys, hold=False)
    cv.keys(pulse, "scaleY", keys, hold=False)
    cv.ellipse(pulse, -size, -size, 2 * size, 2 * size, BLUE, opacity=0.25)
    cv.ellipse(g, x - size / 2, y - size / 2, size, size, BLUE, "#FFFFFF", 4)


def _glyph(cv: Canvas, g, kind: str, x, y) -> None:
    ink = cv.ink
    if kind == "table":
        cv.ellipse(g, x - 40, y - 40, 80, 80, "#FFFFFF", ink, 4)
        cv.ellipse(g, x - 22, y - 22, 44, 44, "#F0E6D6", ink, 2.5)
        cv.line(g, x - 56, y - 30, x - 56, y + 34, ink, 5)
        cv.line(g, x + 56, y - 30, x + 56, y + 34, ink, 5)
    elif kind == "cross":
        cv.rect(g, x - 44, y - 44, 88, 88, "#FFFFFF", ink, 4, radius=12)
        cv.rect(g, x - 11, y - 32, 22, 64, "#2FB56A")
        cv.rect(g, x - 32, y - 11, 64, 22, "#2FB56A")
    else:
        cv.path(g, f"M{x - 54} {y + 44} L{x - 54} {y - 6} L{x} {y - 50} L{x + 54} {y - 6} L{x + 54} {y + 44}Z",
                "#E9C48E", ink, 4)  # fmt: skip
        cv.rect(g, x - 15, y + 8, 30, 36, "#7A4B35", ink, 3)
        cv.path(g, f"M{x + 92} {y - 80} A32 32 0 1 0 {x + 124} {y - 22} A26 26 0 0 1 {x + 92} {y - 80}Z",
                "#F2D86B", ink, 3)  # fmt: skip


@register("prop", "table-phone", style="cutout", summary="A phone lying on a table that rings, lights and talks")
def table_phone(
    cv: Canvas,
    parent,
    x=540,
    y=1220,
    *,
    rings: Sequence[tuple[float, float]] = (),
    speaker: Sequence[tuple[float, float]] = (),
    lit: Sequence[tuple[float, float]] = (),
    scale: float = 1.0,
    id: str = "table-phone",
):
    """Flat on the table, 170 by 56 at scale 1, centred on (``x``, ``y``). ``rings`` shakes it, ``lit`` lights its
    screen and ``speaker`` shows sound coming off it; each is a list of (start, end) spans."""
    _scale(scale)
    rings = _spans(rings, "a ring")
    speaker = _spans(speaker, "a speaker span")
    lit = _spans(lit, "a lit span")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    body = cv.group(g, f"{id}-body")
    if rings:
        keys = [(0.0, 0.0)]
        for a, b in rings:
            at, sign = a, 1
            while at < b:
                keys.append((at, 3.0 * sign))
                at += RATTLE
                sign = -sign
            keys.append((b, 0.0))
        cv.keys(body, "x", keys, hold=False)
    cv.path(body, "M-72 -28 L64 -28 L84 28 L-86 28Z", BODY, ink, 3.5)
    cv.path(body, "M-64 -21 L58 -21 L72 21 L-74 21Z", "#39424C")
    if lit:
        on = cv.group(body, f"{id}-lit")
        cv.gate(on, lit)
        cv.path(on, "M-64 -21 L58 -21 L72 21 L-74 21Z", "#BFE3F2")
    if speaker:
        arcs = cv.group(g, f"{id}-speaker")
        cv.gate(arcs, speaker)
        for k, r in enumerate((26.0, 48.0, 70.0)):
            arc = cv.group(arcs, f"{id}-arc-{k}")
            on, at = [], speaker[0][0]
            for a, b in speaker:
                at = a
                while at < b:
                    on.append((at + 0.12 * k, min(at + 0.12 * k + 0.3, b)))
                    at += 0.56
            cv.gate(arc, [s for s in on if s[0] < s[1]])
            cv.path(arc, f"M{-r} {-40 - r / 2} Q0 {-60 - r} {r} {-40 - r / 2}", stroke="#FFFFFF", sw=6)
    return g


@register("prop", "location-chip", style="cutout", summary="An invented map chip: a blue dot at each place it caught")
def location_chip(
    cv: Canvas,
    parent,
    x=540,
    y=400,
    stops: Sequence[tuple[float, float, str]] = ((0.0, 1.0, "table"),),
    *,
    scale: float = 1.0,
    id: str = "location-chip",
):
    """Centred on (``x``, ``y``), 440 by 300 at scale 1. Each stop is (start, end, kind), in order, and pops the map
    in with the dot on a :data:`KINDS` glyph."""
    _scale(scale)
    if not stops:
        raise CutoutLocateError("a location chip needs at least one stop")
    for stop in stops:
        if not (isinstance(stop, tuple | list) and len(stop) == 3) or stop[2] not in KINDS:
            raise CutoutLocateError(f"a stop is (start, end, one of {', '.join(KINDS)}), got {stop!r}")
    spans = checks.spans(
        [(a, b) for a, b, _ in stops],
        CutoutLocateError,
        lambda s: f"a stop is a rising span from 0, got {s!r}",
        ordered=lambda s: f"stops run in order without overlapping, got {s!r}",
    )
    g = cv.group(parent, id, x=x, y=y)
    for i, ((a, b), (_, _, kind)) in enumerate(zip(spans, stops, strict=True)):
        stop = cv.group(g, f"{id}-stop-{i}")
        cv.gate(stop, [(a, b)])
        cv.pop_in(stop, a, rest=scale, from_=scale * 0.8, over=scale * 1.04)
        _map(cv, stop, -220, -150, 440, 300)
        _glyph(cv, stop, kind, 70, 0)
        _dot(cv, stop, -30, 50, a, b)
    return g


@register("prop", "notice-phone", style="cutout", summary="A phone held up, a map on it and a notice chip landing")
def notice_phone(
    cv: Canvas,
    parent,
    x=330,
    y=1000,
    lines: Sequence[str] = ("A NOTICE",),
    *,
    at: float = 0.0,
    scale: float = 1.0,
    id: str = "notice-phone",
):
    """Upright, 300 by 580 at scale 1, centred on (``x``, ``y``). The chip with ``lines`` lands on it at ``at``."""
    _scale(scale)
    checks.non_negative(at, CutoutLocateError, f"a time is a number of at least 0, got {at!r}")
    if not 1 <= len(lines) <= NOTICE_LINES:
        raise CutoutLocateError(f"a notice is 1 to {NOTICE_LINES} lines, got {len(lines)}")
    for line in lines:
        if not isinstance(line, str) or not line.strip() or len(line) > NOTICE_LINE:
            raise CutoutLocateError(f"a notice's line is 1 to {NOTICE_LINE} characters, got {line!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -150, -290, 300, 580, BODY, ink, 5, radius=38)
    _map(cv, g, -134, -272, 268, 544, radius=26)
    _dot(cv, g, -40, 110, 0.0, at + 6.0)
    chip = cv.group(g, f"{id}-chip", x=0, y=-120)
    cv.keys(chip, "opacity", [(0, 0.0), (at, 1.0)])
    pop = cv.group(chip, f"{id}-chip-pop")
    cv.pop_in(pop, at, from_=0.7, over=1.06)
    height = 44 + 46 * len(lines)
    cv.rect(pop, -142, -height / 2, 284, height, "#FFFFFF", ink, 4, radius=20)
    for i, line in enumerate(lines):
        top = -height / 2 + 22 + 46 * i
        cv.text(pop, f"{id}-line-{i}", line, -134, top, 268, 44, 31, "#1F2B4A")
    return g


@register("prop", "dinner-plate", style="cutout", summary="A dinner plate seen across a table, half eaten")
def dinner_plate(cv: Canvas, parent, x=300, y=1220, *, scale: float = 1.0, id: str = "dinner-plate"):
    """Centred on (``x``, ``y``), 230 wide at scale 1."""
    _scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -115, -36, 230, 72, "#FBF6EA", ink, 4)
    cv.ellipse(g, -78, -22, 156, 44, "#EFE5D2", "#CFC3AC", 2)
    cv.path(g, "M-52 4 Q-30 -22 2 -14 Q34 -20 48 2 Q10 16 -52 4Z", "#D9A441", ink, 3)
    cv.ellipse(g, -12, -14, 26, 15, "#B5462F", ink, 2.5)
    return g


@register("prop", "table-fork", style="cutout", summary="A fork, held at its grip")
def table_fork(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, rotation: float = 0, id: str = "table-fork"):
    """The grip is on (``x``, ``y``) and the tines point up, ``rotation`` degrees round; 170 long at scale 1."""
    _scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=rotation)
    cv.path(g, "M-5 40 L-4 -80 L4 -80 L5 40 Q0 48 -5 40Z", "#C9CFD3", ink, 3)
    cv.path(g, "M-20 -130 L-20 -92 Q-20 -76 0 -74 Q20 -76 20 -92 L20 -130 L13 -130 L13 -100 L3.5 -100 L3.5 -130 L-3.5 "
               "-130 L-3.5 -100 L-13 -100 L-13 -130Z", "#DDE2E5", ink, 3)  # fmt: skip
    return g


@register("prop", "held-phone", style="cutout", summary="A phone held up by its edge, seen from the back")
def held_phone(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, id: str = "held-phone"):
    """Centred on (``x``, ``y``), 90 by 176 at scale 1, its back to the camera."""
    _scale(scale)
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -45, -88, 90, 176, BODY, cv.ink, 4, radius=14)
    cv.ellipse(g, -30, -74, 22, 22, "#39424C", "#5C6673", 2)
    return g

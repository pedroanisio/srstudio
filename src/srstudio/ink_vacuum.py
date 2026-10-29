"""The Ink robot vacuum: a talking disc on the floor and the map it keeps of the home, drawn in the style's pen
stroke (:mod:`srstudio.ink`).

The vacuum is seen from above at three quarters: a white top, a grey side band with the bumper, the laser turret,
the button and its ring of lights, and a small display. While it speaks its ring chases and voice marks flicker, as
the router's LEDs and marks do; it can sit still, roll off through the take or roll in and brake. The floor map is
the vacuum's app: the home as rooms in outline, each named, the route traced dot by dot and, at a moment of the
take, one room renamed. Every time is seconds into the take. The vacuum's side band carries the signature code
(ADR 0001).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import look, signature
from .canvas import Canvas
from .errors import SrstudioError
from .ink import ellipse, group, path
from .registry import register
from .timeline import Take

__all__ = ["Room", "VacuumError", "PLAN", "RING_LEDS", "TRACE_DOTS", "vacuum", "vacuum_shot", "floor_map"]

STATES = ("still", "roll", "stop")
RING_LEDS = 6
DISPLAY_MAX = 5  # characters on the vacuum's display
LABEL_MAX = 12  # characters in a room's name on the map
TRACE_DOTS = 24
ROLL = 700  # how far it rolls off through a take, its own units
BRAKE = 500  # how far before its mark it rolls in from
TOP = "#FDFDFD"
BAND = "#E6E6E6"


class VacuumError(SrstudioError, ValueError):
    """A state, a display, a room, a relabel or a trace the vacuum or its map cannot show."""


@dataclass(frozen=True)
class Room:
    """A room on the map: its ``label`` and its outline (frame pixels: top-left, width, height)."""

    label: str
    x: float
    y: float
    w: float
    h: float


PLAN = (
    Room("LIVING", 170, 300, 400, 330),
    Room("KITCHEN", 570, 300, 340, 330),
    Room("BEDROOM", 170, 630, 330, 340),
    Room("BATH", 500, 630, 200, 200),
    Room("CLOSET", 700, 630, 210, 200),
    Room("HALL", 500, 830, 410, 140),
)
ROUTE = (
    (260, 560),
    (260, 380),
    (480, 380),
    (480, 560),
    (620, 560),
    (620, 380),
    (860, 380),
    (860, 560),
    (560, 600),
    (560, 900),
    (230, 900),
    (230, 690),
    (430, 690),
)  # fmt: skip  around the labels


def _text(cv: Canvas, parent, value: str, x, y, w, h, size, color: str) -> None:
    """``value`` on one line in the box, its size in whole pixels."""
    look.text(cv, parent, value, x, y, round(w), round(h), size, color, asset="txt", layer="label")


def _ring_keys(i: int, duration: float) -> list[tuple[float, float]]:
    """Light ``i`` of the ring while the vacuum speaks: on, then a chase around the ring until the take ends."""
    period, step = 0.42, 0.07
    keys, t, lit = [(0.0, 1.0)], step * i + 0.08, False
    while t < duration:
        keys.append((round(t, 3), 1.0 if lit else 0.2))
        lit, t = not lit, t + period / 2
    return keys


@register(
    "character",
    "talking-vacuum",
    summary="A robot vacuum that talks: its ring of lights chases and voice marks flicker when it speaks; it sits "
    "still, rolls off or rolls in and brakes, with a word on its display",
    style="ink",
)
def vacuum(
    cv: Canvas,
    parent,
    take: Take,
    x,
    y,
    scale=1,
    *,
    speaker: str = "vacuum",
    state: str = "still",
    display: str | None = None,
):
    """The vacuum centred on ``x, y`` (the middle of its top); ``state`` is ``still``, ``roll`` (it rolls off to the
    right through the take) or ``stop`` (it rolls in from the left and brakes on its mark); ``display`` is a word of
    1 to :data:`DISPLAY_MAX` characters on its top."""
    if state not in STATES:
        raise VacuumError(f"state must be one of {STATES}, got {state!r}")
    if display is not None and not (0 < len(display.strip()) and len(display) <= DISPLAY_MAX):
        raise VacuumError(f"the display shows 1 to {DISPLAY_MAX} characters, got {display!r}")
    g = group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    if state == "roll":
        cv.keys(g, "x", [(0.0, x), (take.duration, x + ROLL * scale)], kind="cubic-in")
    elif state == "stop":
        end = min(0.7, take.duration)
        cv.keys(g, "x", [(0.0, x - BRAKE * scale), (end * 0.75, x + 14 * scale), (end, x)], kind="cubic-out")
    ellipse(cv, g, -215, 30, 430, 70, cv.shade, sw=0, opacity=0.35)  # the shadow on the floor
    path(cv, g, "M -200 0 L -200 46 A 200 70 0 0 0 200 46 L 200 0 Z", BAND, sw=2.6)
    path(cv, g, "M -196 26 A 200 70 0 0 0 196 26", sw=1.5)  # the bumper's seam
    ellipse(cv, g, -200, -70, 400, 140, TOP, sw=2.8)
    ellipse(cv, g, -150, -50, 300, 100, TOP, stroke=cv.shade, sw=1.4)
    # the laser turret, behind the button
    path(cv, g, "M 40 -52 L 40 -70 A 46 16 0 0 1 132 -70 L 132 -52 A 46 16 0 0 1 40 -52 Z", BAND, sw=2)
    ellipse(cv, g, 40, -86, 92, 32, TOP, sw=2)
    # the button and its ring
    ellipse(cv, g, -76, -22, 72, 28, TOP, sw=2.2)
    talking = take.actor == speaker
    for i in range(RING_LEDS):
        a = 2 * math.pi * i / RING_LEDS
        led = ellipse(cv, g, -40 + 52 * math.cos(a) - 5, -8 + 20 * math.sin(a) - 4, 10, 8, cv.ink, sw=0)
        if talking:
            cv.keys(led, "opacity", _ring_keys(i, take.duration))
    if display is not None:
        path(cv, g, "M -170 -6 L -100 -16 L -96 12 L -166 22 Z", cv.ink, sw=1.6)
        _text(cv, g, display, -172, -14, 80, 34, 26, cv.white)
    signature.code(cv, g, -20, 50, 9, angle=0)
    if talking:
        marks = group(cv, g, x=170, y=-140)
        path(cv, marks, "M 0 0 L 8 -24 M 19 8 L 40 -9 M 27 25 L 55 21", sw=2.6)
        fade = [(0, 0), (0.06, 0.9), (0.24, 0.3), (0.4, 0.8), (0.58, 0.25), (0.72, 0.65), (0.85, 0)]
        cv.keys(marks, "opacity", fade, hold=False)
    return g


@register(
    "location",
    "ink-vacuum-shot",
    summary="The robot vacuum on the floor by the wall's baseboard, normal or close",
    style="ink",
)
def vacuum_shot(cv: Canvas, parent, take: Take, *, close: bool = False, **vacuum_kw):
    """The floor and the baseboard, the vacuum on them; ``vacuum_kw`` (``state``, ``display``) go to
    :func:`vacuum`."""
    wall = 520 if close else 600
    path(cv, parent, f"M 0 {wall + 34} L 1080 {wall + 34} L 1080 1080 L 0 1080 Z", "#F7F7F7", sw=0)
    path(cv, parent, f"M 0 {wall} L 1080 {wall} M 0 {wall + 34} L 1080 {wall + 34}", sw=2.2)
    for k in range(4):  # the floorboards' seams run toward the viewer
        y0 = wall + 120 + k * 110
        path(cv, parent, f"M 0 {y0} L 1080 {y0 + 30}", stroke=cv.shade, sw=1.2)
    # the outlet on the wall and the vacuum's dock against the baseboard, its cable plugged in
    ox, dx = (930, 150) if close else (870, 210)  # the dock at the left, clear of the voice marks
    path(cv, parent, f"M {ox} {wall - 150} l 60 0 l 0 84 l -60 0 Z", cv.white, sw=2.2)
    path(cv, parent, f"M {ox + 22} {wall - 126} l 0 14 M {ox + 38} {wall - 126} l 0 14", sw=2.4)
    path(cv, parent, f"M {ox + 30} {wall - 66} Q {ox + 20} {wall + 10} {dx + 40} {wall + 4}", sw=2)
    path(cv, parent, f"M {dx - 50} {wall + 30} L {dx - 50} {wall - 70} Q {dx} {wall - 96} {dx + 50} {wall - 70} "
                     f"L {dx + 50} {wall + 30} Z", cv.white, sw=2.4)  # fmt: skip
    path(
        cv,
        parent,
        f"M {dx - 16} {wall - 30} L {dx} {wall - 46} L {dx + 16} {wall - 30} L {dx + 16} {wall - 12} "
        f"L {dx - 16} {wall - 12} Z",
        sw=1.8,
    )  # fmt: skip  a house: its home
    sc, vy = (2.3, 790) if close else (1.55, 830)
    return vacuum(cv, parent, take, 540, vy, sc, **vacuum_kw)


def _check_rooms(rooms: Sequence[Room]) -> list[Room]:
    if not rooms:
        raise VacuumError("the map needs at least one room")
    seen: set[str] = set()
    for room in rooms:
        if not (0 < len(room.label.strip()) and len(room.label) <= LABEL_MAX):
            raise VacuumError(f"a room's label is 1 to {LABEL_MAX} characters, got {room.label!r}")
        if room.label in seen:
            raise VacuumError(f"the room {room.label!r} is on the map twice")
        seen.add(room.label)
    return list(rooms)


@register(
    "graphic",
    "ink-floor-map",
    summary="The vacuum's map of the home: rooms in outline with their names, the route traced dot by dot, one "
    "room renamed at its moment",
    style="ink",
)
def floor_map(
    cv: Canvas,
    parent,
    take: Take,
    *,
    rooms: Sequence[Room] = PLAN,
    trace: tuple[float, float] | None = None,
    relabel: tuple[str, str, float] | None = None,
):
    """The map on the app's screen: every room of ``rooms`` outlined and named; with ``trace=(start, end)`` the
    vacuum's route appears dot by dot over that span; with ``relabel=(room, new label, at)`` that room's name is
    swapped for the new one at ``at`` and the room is shaded."""
    plan = _check_rooms(rooms)
    if trace is not None and not (0 <= trace[0] < trace[1] <= take.duration):
        raise VacuumError(f"the trace runs within the take, 0 <= start < end <= {take.duration}, got {trace!r}")
    swap = None
    if relabel is not None:
        name, new, at = relabel
        swap = next((r for r in plan if r.label == name), None)
        if swap is None:
            raise VacuumError(f"there is no room {name!r} on the map")
        if not (0 < len(new.strip()) and len(new) <= LABEL_MAX):
            raise VacuumError(f"a room's label is 1 to {LABEL_MAX} characters, got {new!r}")
        if not 0 <= at <= take.duration:
            raise VacuumError(f"the relabel falls within the take (0..{take.duration}), got {at}")
    g = group(cv, parent)
    path(cv, g, "M 150 280 L 930 280 L 930 990 L 150 990 Z", cv.white, sw=3)  # the app's map panel
    for room in plan:
        path(cv, g, f"M {room.x} {room.y} l {room.w} 0 l 0 {room.h} l {-room.w} 0 Z", cv.white, sw=3.2)
        label = group(cv, g)
        _text(cv, label, room.label, room.x, room.y + room.h / 2 - 30, room.w, 60, 40, cv.ink)
        if swap is room and relabel is not None:
            at = relabel[2]
            cv.keys(label, "opacity", [(0.0, 1.0), (at, 0.0)])
            fill = group(cv, g)
            path(cv, fill, f"M {room.x} {room.y} l {room.w} 0 l 0 {room.h} l {-room.w} 0 Z", cv.shade, sw=3.2)
            _text(cv, fill, relabel[1], room.x, room.y + room.h / 2 - 30, room.w, 60, 40, cv.white)
            cv.keys(fill, "opacity", [(0.0, 0.0), (at, 1.0)])
    if trace is not None:
        points = _along(ROUTE, TRACE_DOTS)
        a, b = trace
        for k, (px, py) in enumerate(points):
            dot = ellipse(cv, g, px - 7, py - 7, 14, 14, cv.ink, sw=0)
            cv.keys(dot, "opacity", [(0.0, 0.0), (round(a + (b - a) * k / (TRACE_DOTS - 1), 3), 1.0)])
    return g


def _along(route: Sequence[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    """``n`` points evenly spaced along the polyline ``route``, from its first point to its last."""
    legs = [math.dist(p, q) for p, q in zip(route, route[1:], strict=False)]
    total = sum(legs)
    out = []
    for k in range(n):
        s, i = total * k / (n - 1), 0
        while i < len(legs) - 1 and s > legs[i]:
            s -= legs[i]
            i += 1
        (x0, y0), (x1, y1) = route[i], route[i + 1]
        f = min(1.0, s / legs[i])
        out.append((round(x0 + (x1 - x0) * f, 2), round(y0 + (y1 - y0) * f, 2)))
    return out

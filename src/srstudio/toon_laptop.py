"""An open laptop in Toon with its screen turned to the viewer, the view :func:`srstudio.toon.desk` never gives: that
one shows the lid's back. The screen is any four-cornered :class:`Quad`, so one laptop can stand three-quarter on a
table beside a character and fill the frame as an insert, and the page on it is gray bars and one button, no real site
and no word. :class:`Note` rows land on it at their seconds, each scrawled so nothing reads, until the page is gone.
Every measure is a reference screen pixel (:func:`srstudio.toon.fx`/``fy``), every key on the composition clock. Bad
input is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy

__all__ = ["NOTE", "SCREEN", "Note", "Quad", "open_laptop"]

Point = tuple[float, float]
LID, KEYS, KEY_ROW = "#3a3840", "#55525a", "#45424a"
SCREEN, BAR, BAR_SOFT, BUTTON = "#f2f4f7", "#b8bfca", "#d6dbe2", "#6d7f92"
NOTE, NOTE_FOLD, SCRAWL = "#ffe27a", "#f0c94f", "#9c7a22"
NOTE_W, NOTE_H = 0.4, 0.52  # of the screen
BEZEL = 0.035  # of the screen, around it
SLAP = 0.1  # seconds a note takes to land
PEEL_LIFT = 26.0  # reference pixels a peeled note comes off the screen
PEEL_TURN = -14.0  # degrees it turns as it comes
PEEL_MOVE = 0.16  # seconds to lift, and to go back
ROWS = (  # the page: u, v, width in screen fractions, height in screen fractions, colour
    (0.06, 0.06, 0.52, 0.08, BAR),
    (0.06, 0.2, 0.86, 0.04, BAR_SOFT),
    (0.06, 0.28, 0.8, 0.04, BAR_SOFT),
    (0.06, 0.36, 0.88, 0.04, BAR_SOFT),
    (0.06, 0.48, 0.34, 0.06, BAR),
    (0.06, 0.58, 0.84, 0.04, BAR_SOFT),
    (0.06, 0.66, 0.78, 0.04, BAR_SOFT),
    (0.06, 0.74, 0.5, 0.04, BAR_SOFT),
)
PAGE_BUTTON = (0.68, 0.76, 0.26, 0.14)


@dataclass(frozen=True)
class Quad:
    """A screen's four corners, clockwise from its top left, in reference pixels."""

    top_left: Point
    top_right: Point
    bottom_right: Point
    bottom_left: Point

    def at(self, u: float, v: float) -> Point:
        """The point ``u`` across and ``v`` down the screen, each from 0 to 1."""
        (ax, ay), (bx, by) = self.top_left, self.top_right
        (cx, cy), (dx, dy) = self.bottom_right, self.bottom_left
        top = (ax + (bx - ax) * u, ay + (by - ay) * u)
        foot = (dx + (cx - dx) * u, dy + (cy - dy) * u)
        return (top[0] + (foot[0] - top[0]) * v, top[1] + (foot[1] - top[1]) * v)


@dataclass(frozen=True)
class Note:
    """A note centred ``u`` across and ``v`` down the screen, landing at second ``on``, tipped ``tilt`` degrees; with
    ``peel`` it lifts off at the first second and is back by the second."""

    u: float
    v: float
    on: float
    tilt: float = 0.0
    peel: tuple[float, float] | None = None


THREE_QUARTER = Quad((372.0, 548.0), (566.0, 520.0), (572.0, 770.0), (372.0, 760.0))


def _check_quad(quad: Quad) -> None:
    corners = (quad.top_left, quad.top_right, quad.bottom_right, quad.bottom_left)
    if not all(checks.number(x) and checks.number(y) for x, y in corners):
        raise ToonDataError(f"a screen's corners are numbers, got {corners!r}")
    if quad.top_left[0] >= quad.top_right[0] or quad.bottom_left[0] >= quad.bottom_right[0]:
        raise ToonDataError(f"a screen's left corners stand left of its right ones, got {corners!r}")
    if quad.top_left[1] >= quad.bottom_left[1] or quad.top_right[1] >= quad.bottom_right[1]:
        raise ToonDataError(f"a screen's top corners stand above its bottom ones, got {corners!r}")


def _check_notes(notes: Sequence[Note]) -> None:
    last = None
    for n in notes:
        if not (checks.number(n.u) and checks.number(n.v) and 0 <= n.u <= 1 and 0 <= n.v <= 1):
            raise ToonDataError(f"a note sits on the screen, 0 to 1 each way, got {n!r}")
        if not (checks.number(n.on) and n.on >= 0 and checks.number(n.tilt)):
            raise ToonDataError(f"a note lands on a second from 0 at a tilt in degrees, got {n!r}")
        if n.peel is not None:
            a, b = n.peel
            if not (checks.number(a) and checks.number(b) and n.on < a and a + 2 * PEEL_MOVE <= b):
                raise ToonDataError(f"a note peels after it lands, for {2 * PEEL_MOVE} s at least, got {n!r}")
        if last is not None and n.on < last:
            raise ToonDataError(f"notes land in order: {n.on} came after {last}")
        last = n.on


def _poly(cv: Canvas, g, points: Sequence[Point], fill: str | None, stroke: str, weight: float) -> None:
    d = "M " + " L ".join(f"{fx(x)} {fy(y)}" for x, y in points) + " Z"
    cv.path(g, d, fill, stroke, weight)


def _bar(cv: Canvas, g, quad: Quad, u: float, v: float, w: float, h: float, colour: str) -> None:
    corners = [quad.at(u, v), quad.at(u + w, v), quad.at(u + w, v + h), quad.at(u, v + h)]
    _poly(cv, g, corners, colour, cv.clear, 0)


def _note(cv: Canvas, parent, quad: Quad, n: Note) -> None:
    cx, cy = quad.at(n.u, n.v)
    x, y = fx(cx), fy(cy)
    g = cv.group(parent, cv.uid("g"), start=n.on, anchorX=x, anchorY=y, x=x, y=y)
    for prop in ("scaleX", "scaleY"):
        cv.keys(g, prop, [(n.on, 1.22), (n.on + SLAP, 1.0)], hold=False, local=False)
    if n.peel is not None:
        a, b = n.peel
        keys = [(a, 0.0), (a + PEEL_MOVE, 1.0), (b - PEEL_MOVE, 1.0), (b, 0.0)]
        cv.keys(g, "rotation", [(t, n.tilt + k * PEEL_TURN) for t, k in keys], hold=False, local=False)
        cv.keys(g, "y", [(t, round(y - k * fh(PEEL_LIFT), 2)) for t, k in keys], hold=False, local=False)
    elif n.tilt:
        g.rotation = n.tilt
    half_w, half_h = NOTE_W / 2, NOTE_H / 2
    u0, u1, v0, v1 = n.u - half_w, n.u + half_w, n.v - half_h, n.v + half_h
    _poly(cv, g, [quad.at(u0, v0), quad.at(u1, v0), quad.at(u1, v1), quad.at(u0, v1)], NOTE, cv.ink, FINE_W)
    _poly(cv, g, [quad.at(u1 - 0.09, v1), quad.at(u1, v1 - 0.11), quad.at(u1, v1)], NOTE_FOLD, cv.ink, FINE_W * 0.5)
    for row in range(3):  # a scrawl, not writing: a wave that spells nothing
        v = v0 + NOTE_H * (0.26 + 0.24 * row)
        span = NOTE_W * (0.74 - 0.14 * row)
        wave = [quad.at(u0 + 0.04 + span * k / 10, v + 0.018 * math.sin(k * 1.9 + row)) for k in range(11)]
        d = "M " + " L ".join(f"{fx(px)} {fy(py)}" for px, py in wave)
        cv.path(g, d, None, SCRAWL, FINE_W * 0.7)


@register(
    "prop",
    "toon-open-laptop",
    summary="An open laptop with its screen to the viewer, a page of gray bars, and notes that land on it one by one",
    style="toon",
)
def open_laptop(
    cv: Canvas,
    parent,
    notes: Sequence[Note] = (),
    *,
    quad: Quad = THREE_QUARTER,
    foot: float = 34.0,
    shift: float = -46.0,
) -> object:
    """The laptop on ``quad``, its keyboard ``foot`` pixels deep and leaning ``shift`` pixels sideways from the hinge,
    and ``notes`` over the page. Returns its group."""
    _check_quad(quad)
    _check_notes(notes)
    if not (checks.number(foot) and foot > 0 and checks.number(shift)):
        raise ToonDataError(f"a keyboard's depth is over 0 and its lean a number, got {foot!r}, {shift!r}")
    g = cv.group(parent, cv.uid("g"))
    hinge_l, hinge_r = quad.at(-BEZEL, 1 + BEZEL), quad.at(1 + BEZEL, 1 + BEZEL)
    near_l, near_r = (hinge_l[0] + shift, hinge_l[1] + foot), (hinge_r[0] + shift, hinge_r[1] + foot)
    _poly(cv, g, [hinge_l, hinge_r, near_r, near_l], KEYS, cv.ink, INK_W * 0.7)
    for row in (0.3, 0.62):
        a = (hinge_l[0] + shift * row + 12, hinge_l[1] + foot * row)
        b = (hinge_r[0] + shift * row - 12, hinge_r[1] + foot * row)
        cv.path(g, f"M {fx(a[0])} {fy(a[1])} L {fx(b[0])} {fy(b[1])}", None, KEY_ROW, FINE_W)
    _poly(
        cv,
        g,
        [
            quad.at(-BEZEL, -BEZEL),
            quad.at(1 + BEZEL, -BEZEL),
            quad.at(1 + BEZEL, 1 + BEZEL),
            quad.at(-BEZEL, 1 + BEZEL),
        ],
        LID,
        cv.ink,
        INK_W * 0.8,
    )
    _poly(cv, g, [quad.at(0, 0), quad.at(1, 0), quad.at(1, 1), quad.at(0, 1)], SCREEN, cv.clear, 0)
    for u, v, w, h, colour in ROWS:
        _bar(cv, g, quad, u, v, w, h, colour)
    _bar(cv, g, quad, *PAGE_BUTTON, BUTTON)
    for n in notes:
        _note(cv, g, quad, n)
    return g

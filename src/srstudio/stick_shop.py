"""The Stick style's shop: a supermarket's self-checkout, the kiosk that talks, and what passes over it.

:func:`checkout` is the back layer: the store's wall of stocked shelves under strip lights, a hanging
``SELF-CHECKOUT`` sign, the tiled floor and the bagging shelf left of the kiosk (an item rests on it at
:data:`BAG_SPOT`). :func:`kiosk` stands right of the shelf: the pedestal with its card reader and receipt slot, the
scanner bed with its red line, and the screen, whose :class:`Screen` schedule holds each message until the next, in
a tone (:data:`TONES`), with an employee's face for an award; its lamp flashes red at each ``alarm``. Figures stand
from :data:`srstudio.stick.STANDING`: the shopper at :data:`SHOPPER_AT`, left of the shelf, and a clerk mirrored at
:data:`CLERK_AT`, right of the kiosk; :func:`hand` finds the near hand that carries an :func:`avocado`.
:func:`name_badge` pins a name and a title on an apron (``stick.Look(apron=)``). Everything is in frame pixels of
the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial

from . import look, signature
from .canvas import Canvas
from .registry import register
from .stick import (
    CLOSED_MOUTHS,
    Face,
    Gradient,
    Look,
    Point,
    RigPose,
    StickDataError,
    _features,
    _gate,
    _group,
    _head,
    box,
    check_look,
    oval,
    paint,
    shape,
)

__all__ = [
    "BAG_SPOT",
    "CLERK_AT",
    "SCREEN_CHARS",
    "SCREEN_CENTRE",
    "SHOPPER_AT",
    "TONES",
    "Screen",
    "avocado",
    "checkout",
    "hand",
    "kiosk",
    "name_badge",
]

WALL_TOP, WALL_LOW, CEILING, BASEBOARD = "#ece6d8", "#d8cfbd", "#d2cab9", "#8c8576"
FLOOR, FLOOR_LINE, SHELF, SHELF_EDGE = "#cdc4b1", "#b5ab96", "#c9ced6", "#8e959f"
STEEL, STEEL_DARK, BODY, PANEL, BEZEL = "#c9ced6", "#9aa2ad", "#eceff3", "#3a3f48", "#2b2f36"
SIGN, LAMP_OFF, LAMP_ON, LASER = "#2f7d57", "#cfd4da", "#ff3b30", "#ff4d4d"
SHELF_FRONT, BADGE_INK = "#3f454e", "#0f2e1f"  # dark enough for their lettering to pass the 4.5:1 contrast check
STOCK = ("#e5484d", "#f5a524", "#2f6fdb", "#3ccf6e", "#8e6bd8", "#f0e2c0", "#e8743b", "#5bb5c9")
TONES = {"idle": "#1f5bc0", "error": "#c7333a", "help": "#a14f00", "award": "#8a6510"}  # headers: white reads on all
TONE_BODY = {"idle": "#ffffff", "error": "#ffe9e7", "help": "#fff5e0", "award": "#fff8e1"}
BRAND = "Freshly"  # the store's invented name, on the screen's header

SHELF_TOP, SHELF_X = 1078, (360, 600)  # the bagging shelf's top and its ends
BAG_SPOT = (480.0, float(SHELF_TOP))  # where an item rests on the shelf: its base's centre
DISPLAY = (603, 658, 274, 264)  # x, y, w, h of the kiosk's display, inside the bezel
SCREEN_CENTRE = (DISPLAY[0] + DISPLAY[2] / 2, DISPLAY[1] + DISPLAY[3] / 2)
SCREEN_CHARS = 60  # the longest message the display letters
SHOPPER_AT = (-220.0, 0.0)  # a STANDING pose here stands left of the shelf, facing the kiosk
CLERK_AT = (1520.0, 0.0)  # with flip=True a STANDING pose here stands right of the kiosk, facing it
LAMP = (873, 572)  # the alarm lamp's centre, on the bezel's corner
BADGE_W = 210  # a name badge's width: its title at 18 px fits
BLINK = 0.25  # the lamp's on and off beats; an alarm blinks three times


@dataclass(frozen=True)
class Screen:
    """From ``start`` (seconds) until the next screen, the kiosk shows ``text`` in ``tone``; an ``award`` may
    show the face of ``face`` above the text."""

    start: float
    text: str
    tone: str = "idle"
    face: Look | None = None


_label = partial(look.text, weight=700, lines=1, line_height="1.1", overflow="ellipsis")


def hand(pose: RigPose, *, at: Point = SHOPPER_AT, flip: bool = False) -> Point:
    """Where ``pose``'s near hand is once the figure stands at ``at`` (mirrored with ``flip``, as
    :func:`srstudio.stick.rig` places it): the point an item it carries is drawn at."""
    x, y = pose.hands[1]
    return (at[0] - x if flip else at[0] + x, at[1] + y)


@register("location", "stick-checkout", tags=("shop", "supermarket", "self-checkout"))
def checkout(cv: Canvas, parent) -> None:
    """A supermarket's self-checkout: stocked shelves along the back wall under strip lights, the hanging
    ``SELF-CHECKOUT`` sign, a tiled floor in perspective and the bagging shelf with its rack, left of where
    :func:`kiosk` stands."""
    cv.require_font("the checkout's sign is set in it")
    s = cv
    box(s, parent, 0, 0, s.width, 1480, paint(s, Gradient("shop-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0, 1480)))
    box(s, parent, 0, 0, s.width, 120, CEILING)
    for x in (60, 430, 800):  # strip lights and the glow under them
        box(s, parent, x, 44, 220, 26, "#fffbe8", 3, r=8)
        shape(s, parent, f"M {x - 30} 70 L {x + 250} 70 L {x + 330} 420 L {x - 110} 420 Z", "#fffbe8", opacity=0.12)
    # the hanging sign
    for x in (380, 700):
        shape(s, parent, f"M {x} 120 L {x} 150", sw=4, stroke=s.ink)
    box(s, parent, 320, 150, 440, 96, SIGN, 5, r=18)
    _label(s, parent, "SELF-CHECKOUT", 330, 150, 420, 96, 48, "#ffffff")
    # the back wall's shelving: uprights, boards and stock, every box placed by its index
    box(s, parent, 0, 560, s.width, 900, "#bfb6a3", 3)
    for i, board in enumerate((700, 860, 1020, 1180, 1340)):
        x = 14
        j = 0
        while x < s.width - 30:
            w = 40 + (j * 17 + i * 11) % 34
            h = 70 + (j * 23 + i * 7) % 56
            box(s, parent, x, board - h, w, h, STOCK[(j * 3 + i * 5) % len(STOCK)], 3, r=4)
            box(s, parent, x + 8, board - h + 14, w - 16, 10, "#ffffff", opacity=0.55)
            x += w + 8
            j += 1
        box(s, parent, 0, board, s.width, 22, SHELF, 3)
        box(s, parent, 0, board + 22, s.width, 8, SHELF_EDGE)
    for x in (0, 528, 1056):
        box(s, parent, x, 560, 24, 900, "#9e9686", 3)
    box(s, parent, 0, 1460, s.width, 26, BASEBOARD)
    # the floor: tiles in perspective toward the wall
    box(s, parent, 0, 1480, s.width, 440, FLOOR)
    for y in (1530, 1600, 1690, 1800):
        shape(s, parent, f"M 0 {y} L {s.width} {y}", sw=3, stroke=FLOOR_LINE)
    for x in range(-600, 1700, 180):
        shape(s, parent, f"M {540 + (x - 540) * 0.35:.0f} 1480 L {x} 1920", sw=3, stroke=FLOOR_LINE)
    shape(s, parent, "M 120 1560 L 980 1560 L 1080 1760 L 0 1760 Z", "#ffffff", opacity=0.12)  # the lights' sheen
    # the bagging shelf: legs, its rack, the top and the front with its label
    left, right = SHELF_X
    for x in (left + 16, right - 36):
        box(s, parent, x, SHELF_TOP + 60, 20, 1700 - SHELF_TOP - 60, STEEL_DARK, 3)
    for x in (left + 8, right - 20):
        box(s, parent, x, SHELF_TOP - 150, 12, 150, STEEL, 3)
    box(s, parent, left + 8, SHELF_TOP - 158, right - left - 16, 14, STEEL, 3, r=6)
    box(s, parent, left, SHELF_TOP, right - left, 22, SHELF, 4)
    box(s, parent, left, SHELF_TOP + 22, right - left, 44, SHELF_FRONT, 4)
    _label(s, parent, "BAGGING AREA", left, SHELF_TOP + 22, right - left, 44, 24, "#ffffff")
    shape(s, parent, f"M {left + 10} 1716 L {right + 10} 1716", sw=18, stroke="#000000", opacity=0.12)
    signature.cactus(s, parent, 990, 1180, scale=0.4)  # on the shelf among the stock (ADR 0001)
    signature.code(s, parent, 40, 1880, 9, color="#a99f8b")  # on the floor's near edge


def _check_screens(screens: Sequence[Screen], end: float, alarm: Sequence[float]) -> None:
    if not (math.isfinite(end) and end > 0):
        raise StickDataError(f"the kiosk needs a positive shot length, got {end!r}")
    if not screens or screens[0].start != 0:
        raise StickDataError("the kiosk's schedule starts with a screen at 0")
    for a, b in zip(screens, screens[1:], strict=False):
        if not b.start > a.start:
            raise StickDataError(f"screens must be in time order: {a.start} then {b.start}")
    if screens[-1].start >= end:
        raise StickDataError(f"a screen at {screens[-1].start} s starts at or after the end ({end} s)")
    for sc in screens:
        if not sc.text.strip() or len(sc.text) > SCREEN_CHARS:
            raise StickDataError(f"a screen's text has 1 to {SCREEN_CHARS} characters, got {sc.text!r}")
        if sc.tone not in TONES:
            raise StickDataError(f"unknown tone {sc.tone!r}; known: {', '.join(TONES)}")
        if sc.face is not None:
            check_look(sc.face)
    if any(not (math.isfinite(t) and 0 <= t < end) for t in alarm) or list(alarm) != sorted(set(alarm)):
        raise StickDataError(f"alarm times must be in the shot (0..{end}), in order, got {list(alarm)!r}")


def _display(cv: Canvas, parent, sc: Screen) -> None:
    x, y, w, h = DISPLAY
    box(cv, parent, x, y, w, h, TONE_BODY[sc.tone], r=10)
    box(cv, parent, x, y, w, 56, TONES[sc.tone], r=10)
    box(cv, parent, x, y + 40, w, 16, TONES[sc.tone])  # square off the header's lower corners
    _label(cv, parent, BRAND, x, y, w, 56, 28, "#ffffff")
    top = y + 64
    if sc.face is not None:
        head = _group(cv, parent, x=x + w / 2, y=y + 112, scaleX=0.42, scaleY=0.42)
        _head(cv, head, sc.face)
        face = Face("happy", "raised", "smile", (0.0, 0.0))
        _features(cv, _group(cv, head), face, sc.face)
        shape(cv, _group(cv, head, y=44), CLOSED_MOUTHS["smile"], sw=5, stroke=cv.ink)
        top = y + 160
    if sc.tone == "error":
        shape(cv, parent, f"M {x + w / 2} {top + 4} L {x + w / 2 + 22} {top + 42} L {x + w / 2 - 22} {top + 42} Z",
              TONES["error"])  # fmt: skip
        shape(cv, parent, f"M {x + w / 2} {top + 16} L {x + w / 2} {top + 30}", sw=5, stroke="#ffffff")
        oval(cv, parent, x + w / 2 - 3, top + 34, 6, 6, "#ffffff")
        top += 48
    _label(cv, parent, sc.text, x + 14, top, w - 28, y + h - top - 8, 30, cv.ink, lines=4)


@register("prop", "stick-kiosk", tags=("shop", "self-checkout", "screen", "font"))
def kiosk(cv: Canvas, parent, screens: Sequence[Screen], end: float, *, alarm: Sequence[float] = ()):
    """The self-checkout kiosk right of the bagging shelf: a pedestal with a card reader and a receipt slot, the
    scanner bed with its red line, and the screen on its neck showing each of ``screens`` from its start until the
    next (seconds on the parent's clock, to ``end``). Its lamp flashes red three times from each time in
    ``alarm``. :func:`_check_screens` refuses a schedule the screen cannot show."""
    cv.require_font("the kiosk's screen is set in it")
    _check_screens(screens, end, alarm)
    s = cv
    g = _group(s, parent)
    box(s, g, 610, 1100, 240, 600, BODY, 4, r=22)
    box(s, g, 610, 1100, 34, 600, "#dde1e7", r=16)
    box(s, g, 640, 1180, 180, 140, PANEL, 4, r=14)  # the card reader and its little screen
    box(s, g, 668, 1200, 124, 54, "#6fa8c9", 2, r=6)
    for i in range(3):
        for j in range(3):
            box(s, g, 668 + j * 44, 1266 + i * 16, 34, 10, "#5a606b", r=3)
    box(s, g, 650, 1360, 160, 16, PANEL, r=8)  # the receipt slot
    box(s, g, 596, 1690, 268, 26, "#4a4f58", 3, r=10)
    shape(s, g, "M 596 1040 L 864 1040 L 850 1100 L 610 1100 Z", PANEL, 4)  # the scanner bed
    box(s, g, 632, 1050, 196, 30, "#5a6b78", 2, r=6)
    shape(s, g, "M 646 1065 L 814 1065", sw=3, stroke=LASER)
    box(s, g, 718, 930, 26, 112, "#8e949c", 3)  # the screen's neck
    box(s, g, 585, 640, 310, 300, BEZEL, 5, r=22)
    shape(s, g, f"M {LAMP[0]} {LAMP[1] + 16} L {LAMP[0]} 642", sw=8, stroke=s.ink)
    oval(s, g, LAMP[0] - 22, LAMP[1] - 18, 44, 36, LAMP_OFF, stroke=s.ink, sw=4)
    for i, sc in enumerate(screens):
        until = screens[i + 1].start if i + 1 < len(screens) else end
        d = _group(s, g)
        _display(s, d, sc)
        _gate(s, d, sc.start, until, end)
    for t in alarm:
        lit = _group(s, g)
        oval(s, lit, LAMP[0] - 60, LAMP[1] - 56, 120, 112, LAMP_ON, opacity=0.25)
        oval(s, lit, LAMP[0] - 22, LAMP[1] - 18, 44, 36, LAMP_ON, stroke=s.ink, sw=4)
        s.gate(lit, [(min(t + k * 2 * BLINK, end), min(t + (k * 2 + 1) * BLINK, end)) for k in range(3)])
    return g


@register("prop", "stick-avocado", tags=("shop", "food", "item"))
def avocado(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0):
    """An avocado standing on (``x``, ``y``): a pear-shaped dark green skin, a highlight and a stalk, about 90 px
    tall at ``scale`` 1."""
    if not (math.isfinite(scale) and scale > 0):
        raise StickDataError(f"scale must be a positive number, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    shape(cv, g, "M 0 -88 Q 20 -88 22 -60 Q 24 -44 36 -30 Q 44 -14 30 -3 Q 16 4 0 4 Q -16 4 -30 -3 "
          "Q -44 -14 -36 -30 Q -24 -44 -22 -60 Q -20 -88 0 -88 Z", "#3f6b2a", 5, stroke=cv.ink)  # fmt: skip
    shape(cv, g, "M -10 -70 Q -16 -50 -24 -36", sw=5, stroke="#7fa65a")
    shape(cv, g, "M 0 -88 L 4 -100", sw=5, stroke="#6b4a2b")
    return g


@register("prop", "stick-name-badge", tags=("shop", "uniform", "badge", "font"))
def name_badge(cv: Canvas, parent, x: float, y: float, name: str, title: str):
    """A name badge with its top left at (``x``, ``y``): ``name`` large over ``title`` small, white on the
    store's green, for the chest of an apron."""
    cv.require_font("the name badge is set in it")
    if not name.strip() or not title.strip():
        raise StickDataError(f"a name badge needs a name and a title, got {name!r}, {title!r}")
    g = _group(cv, parent, x=x, y=y)
    box(cv, g, 0, 0, BADGE_W, 84, "#ffffff", 4, r=10)
    box(cv, g, 0, 0, BADGE_W, 14, SIGN, r=6)
    _label(cv, g, name, 6, 14, BADGE_W - 12, 36, 30, cv.ink)
    _label(cv, g, title, 6, 50, BADGE_W - 12, 28, 18, BADGE_INK)
    return g

"""The Stick style's gym: the front desk before dawn, and the counter with its sign.

:func:`gym` is the back layer: the wall in the gym's colours with the brand and a ``NO EXCUSES`` poster, a tall
window over the city at the left whose night sky turns to dawn at ``sunrise`` (the sun climbs over :data:`DAWN`
seconds), a dumbbell rack and a treadmill on the right, and rubber floor mats. :func:`counter` is the front layer,
drawn after the staff so it hides their legs: the desk's slab and front, a card reader, and a tent sign on top whose
``sign`` may carry an asterisk and its ``fine`` print, small enough to need a close-up (:data:`SIGN_CENTRE`).
Figures stand from :data:`srstudio.stick.STANDING`: the member at :data:`MEMBER_AT`, left of the desk, and the
staff mirrored at :data:`STAFF_AT`, behind it. Everything is in frame pixels of the 1080 × 1920 Stick frame and
nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

import math
from functools import partial

from . import look, signature
from .canvas import Canvas
from .registry import register
from .stick import Gradient, StickDataError, _group, box, oval, paint, shape

__all__ = [
    "BRAND",
    "COUNTER_TOP",
    "COUNTER_X",
    "DAWN",
    "FINE_CHARS",
    "MEMBER_AT",
    "SIGN_CENTRE",
    "SIGN_CHARS",
    "STAFF_AT",
    "counter",
    "gym",
]

BRAND = "Ironclad Fitness"  # the gym's invented name, on the wall
WALL_TOP, WALL_LOW, CEILING, TRIM = "#2e3440", "#3b4252", "#242933", "#e85d3f"
MAT, MAT_LINE, STEEL, STEEL_DARK, RUBBER = "#30343c", "#454b55", "#c9ced6", "#8e959f", "#1d2026"
NIGHT = ((0, "#0d1b3d"), (1, "#27406e"))
DAY = ((0, "#7fb6f0"), (0.7, "#ffc98a"), (1, "#ff9a5c"))
SUN, CITY, CITY_LIT = "#ffd36b", "#141a2a", "#ffe08a"
DESK, DESK_FRONT, DESK_EDGE, SIGN_BG = "#e85d3f", "#c94a30", "#f2f2f2", "#ffffff"
LETTER = "#a8361c"  # the brand orange darkened for lettering: 4.5:1 or better on the poster and the sign

WINDOW = (60, 300, 440, 720)  # x, y, w, h of the glass, inside its frame
COUNTER_X = (600, 1080)  # the desk's ends
COUNTER_TOP = 1160  # the desk's top: a STANDING figure behind it shows from the waist up
SIGN = (615, 1000, 340, 160)  # x, y, w, h of the tent sign standing on the desk
SIGN_CENTRE = (SIGN[0] + SIGN[2] / 2, SIGN[1] + SIGN[3] / 2)
SIGN_CHARS, FINE_CHARS = 18, 60  # the longest sign and fine print the card letters
MEMBER_AT = (-220.0, 0.0)  # a STANDING pose here stands left of the desk, facing it
STAFF_AT = (1520.0, 0.0)  # with flip=True a STANDING pose here stands behind the desk, facing the member
DAWN = 1.5  # seconds the sky takes to turn and the sun to climb


_label = partial(look.text, weight=700, lines=1, line_height="1.1", overflow="ellipsis")


def _sky(cv: Canvas, parent, stops, gid: str) -> None:
    x, y, w, h = WINDOW
    box(cv, parent, x, y, w, h, paint(cv, Gradient(gid, stops, 0, 0, 0, h)))


def _city(cv: Canvas, parent, lit: bool) -> None:
    """The skyline in the window's lower third; its windows are lit at night."""
    x, y, w, h = WINDOW
    base = y + h
    for i, (bx, bw, bh) in enumerate(((0, 80, 210), (86, 60, 300), (152, 96, 180), (254, 70, 260), (330, 110, 200))):
        box(cv, parent, x + bx, base - bh, bw, bh, CITY)
        if lit:
            for j in range(4):
                if (i + j) % 3:
                    box(cv, parent, x + bx + 14 + (j % 2) * 26, base - bh + 24 + j * 40, 14, 18, CITY_LIT)


@register("location", "stick-gym", tags=("gym", "fitness", "front-desk", "window", "dawn", "font"))
def gym(cv: Canvas, parent, end: float, *, sunrise: float | None = None) -> None:
    """The gym's front desk area before dawn: the wall, the brand, the poster, the window with the city (night, or
    dawn from ``sunrise`` seconds on the parent's clock, turning over :data:`DAWN`; 0 draws it already day), the
    rack and the treadmill, the mats."""
    cv.require_font("the gym's sign is set in it")
    if sunrise is not None and not (math.isfinite(sunrise) and 0 <= sunrise < end):
        raise StickDataError(f"sunrise is a second in the shot (0..{end}), got {sunrise!r}")
    s = cv
    box(s, parent, 0, 0, s.width, 1480, paint(s, Gradient("gym-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0, 1480)))
    box(s, parent, 0, 0, s.width, 110, CEILING)
    for x in (120, 480, 840):  # the ceiling's spots
        oval(s, parent, x, 96, 120, 28, "#fff4d6")
    box(s, parent, 0, 236, s.width, 14, TRIM)
    _label(s, parent, BRAND.upper(), 560, 130, 500, 90, 54, "#ffffff")
    # the window: frame, sky, city, mullions
    x, y, w, h = WINDOW
    box(s, parent, x - 16, y - 16, w + 32, h + 32, "#1b1f27", 4, r=6)
    if sunrise == 0:
        _sky(s, parent, DAY, "gym-day")
        oval(s, parent, x + 270, y + 330, 110, 110, SUN)
        _city(s, parent, lit=False)
    else:
        _sky(s, parent, NIGHT, "gym-night")
        oval(s, parent, x + 320, y + 80, 40, 40, "#f0f0e0")  # the moon
        _city(s, parent, lit=True)
        if sunrise is not None:
            dawn = _group(s, parent)
            _sky(s, dawn, DAY, "gym-day")
            sun = _group(s, dawn)
            oval(s, sun, x + 270, y + 330, 110, 110, SUN)
            s.keys(sun, "y", [(0.0, 260.0), (sunrise, 260.0), (sunrise + DAWN, 0.0)], hold=False)
            _city(s, dawn, lit=False)
            s.keys(dawn, "opacity", [(0.0, 0.0), (sunrise, 0.0), (sunrise + DAWN, 1.0)], hold=False)
    box(s, parent, x + w / 2 - 6, y, 12, h, "#1b1f27")
    box(s, parent, x, y + h / 2 - 6, w, 12, "#1b1f27")
    # the poster on the right wall
    box(s, parent, 640, 330, 360, 220, "#f4f1ea", 4, r=6)
    _label(s, parent, "NO EXCUSES", 650, 360, 340, 80, 52, LETTER)
    shape(s, parent, "M 700 470 L 940 470", sw=6, stroke="#2e3440")
    shape(s, parent, "M 740 500 L 900 500", sw=6, stroke="#2e3440")
    # the dumbbell rack and the treadmill, behind the desk
    box(s, parent, 600, 880, 460, 24, STEEL_DARK, 3)
    for i in range(6):
        cx = 630 + i * 74
        box(s, parent, cx, 846, 18, 34, RUBBER, 2, r=4)
        box(s, parent, cx + 18, 858, 24, 10, STEEL)
        box(s, parent, cx + 42, 846, 18, 34, RUBBER, 2, r=4)
    for lx in (620, 1030):
        box(s, parent, lx, 904, 14, 256, STEEL_DARK)
    shape(s, parent, "M 640 1150 L 1060 1150 L 1040 1110 L 680 1110 Z", RUBBER, 3, stroke="#000000")
    shape(s, parent, "M 1000 1110 L 1040 960 L 1000 940", sw=10, stroke=STEEL_DARK)
    box(s, parent, 0, 1460, s.width, 26, TRIM)
    # the floor: rubber mats in rows
    box(s, parent, 0, 1480, s.width, 440, MAT)
    for yy in (1560, 1660, 1780):
        shape(s, parent, f"M 0 {yy} L {s.width} {yy}", sw=3, stroke=MAT_LINE)
    for xx in range(-400, 1600, 240):
        shape(s, parent, f"M {540 + (xx - 540) * 0.4:.0f} 1480 L {xx} 1920", sw=3, stroke=MAT_LINE)
    signature.code(s, parent, 40, 1880, 9, color="#6b7280")  # on the mats' near edge (ADR 0001)


@register("prop", "stick-gym-counter", tags=("gym", "front-desk", "sign", "fine-print", "font"))
def counter(cv: Canvas, parent, *, sign: str, fine: str = ""):
    """The front desk, drawn over the staff: the slab, the front with its stripe, a card reader, and the tent sign
    on top lettered ``sign`` (1 to :data:`SIGN_CHARS` characters) over its ``fine`` print (up to
    :data:`FINE_CHARS`, set small: it reads in a close-up on :data:`SIGN_CENTRE`)."""
    cv.require_font("the counter's sign is set in it")
    if not sign.strip() or len(sign) > SIGN_CHARS:
        raise StickDataError(f"the sign has 1 to {SIGN_CHARS} characters, got {sign!r}")
    if len(fine) > FINE_CHARS:
        raise StickDataError(f"the fine print has at most {FINE_CHARS} characters, got {len(fine)}")
    s = cv
    g = _group(s, parent)
    left, right = COUNTER_X
    box(s, g, left, COUNTER_TOP + 30, right - left, 1700 - COUNTER_TOP - 30, DESK_FRONT, 4)
    box(s, g, left, COUNTER_TOP + 220, right - left, 40, "#ffffff", opacity=0.25)
    box(s, g, left - 20, COUNTER_TOP, right - left + 40, 34, DESK_EDGE, 4, r=6)
    shape(s, g, f"M {left - 10} 1716 L {right} 1716", sw=18, stroke="#000000", opacity=0.18)
    box(s, g, 960, COUNTER_TOP - 60, 90, 60, "#3a3f48", 3, r=8)  # the card reader
    box(s, g, 974, COUNTER_TOP - 50, 62, 22, "#6fa8c9", r=4)
    x, y, w, h = SIGN
    shape(s, g, f"M {x + 20} {y + h} L {x + w / 2} {y - 6} L {x + w - 20} {y + h} Z", "#d8d8d8", 3, stroke=s.ink)
    box(s, g, x, y, w, h, SIGN_BG, 4, r=8)
    if fine:
        _label(s, g, sign, x + 8, y + 10, w - 16, 70, 30, LETTER)
        _label(s, g, fine, x + 10, y + 82, w - 20, 66, 14, "#14171d", weight=600, lines=3)
    else:
        _label(s, g, sign, x + 8, y + 10, w - 16, h - 20, 30, LETTER)
    signature.cactus(s, g, 990, COUNTER_TOP - 60, scale=0.3)  # on the desk beside the sign (ADR 0001)
    return g

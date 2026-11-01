"""Version 2 of the news parts: the studio, the desk, Vera and Gus and the graphics of News Compiler (ADR 0060).

The same two people at the same desk, on the same calls as :mod:`srstudio.news_kit`, which keeps version 1 and every
type, number and check they share. A new reel of the show calls this module. Each part is registered as ``name@2``.

* **The set has planes.** The room behind the wall, the monitor wall out of focus, the anchors and the desk sharp, a
  floor under the desk, and a studio camera cropped by the frame's foot. The key light is the cast's: upper left.
* **The anchors are inked** the way the approved Toon cast is (:mod:`srstudio.toon_critters`): a pressed contour that
  swells away from the light, a shade tone on the far side, open inner strokes. They have necks, jointed sleeves and
  hands with fingers. Their forearms lie over the desk (``over`` in :func:`perform`), each on a contact shadow.
* **The graphics are one system.** One corner, one shadow, one chip height in the top row, and a flush bottom stack:
  banner, lower-third, ticker. The desk carries no word, so the Reels safe zone holds nothing a viewer needs.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any

from . import brush, head_motion, look, news_arms, news_head, news_kit, parts, toon, toon_head
from .brush import Point
from .canvas import Canvas
from .head_motion import Channel, HeadPlan
from .news_head import GUS_MOTION, GUS_MOTION_3, VERA_MOTION, VERA_MOTION_3, AnchorRig
from .news_kit import (
    BUG_H,
    BUG_Y,
    BUTTER,
    CAPTION_LEADING,
    CAPTION_PAD,
    CAPTION_SIZE,
    CAPTION_TOP,
    CARD_RISE,
    CARD_Y,
    CHIN_Y,
    CREAM,
    GUS_FACE,
    MINT,
    MINT_DARK,
    PLUM,
    PLUM_DEEP,
    ROSE,
    SHOW,
    SLIDE,
    SWEEP,
    SWEEP_LIGHT,
    TANGERINE,
    TANGERINE_DARK,
    TEXT_LEFT,
    TEXT_RIGHT,
    TEXT_WIDE,
    TICKER_SPEED,
    VERA_FACE,
    Act,
    Bubble,
    Face,
    Jaw,
    Measure,
    NewsKitError,
    Pose,
    Source,
    Spans,
    Track,
    _fit,
    _head_keys,
    _mouth,
    _slide,
    _span,
    _spans,
    _text,
    _wrap,
    check_copy,
    eye_track,
    mouth_track,
    sign,
)
from .registry import register
from .toon_critters import FUR, LIGHT_FROM, LINE, drifted, pressed, shade

__all__ = [
    "BANNER_H",
    "BANNER_Y",
    "CHIN_TIP",
    "COLLAR_Y",
    "FAR_BLUR",
    "FRAMING",
    "LOWER_H",
    "LOWER_Y",
    "MUG_SIZE",
    "MUG_X",
    "MUG_Y",
    "NEAR_BLUR",
    "NECK_Y",
    "Pin",
    "TICKER_H",
    "TICKER_Y",
    "TWO_SHOT",
    "banner",
    "bug",
    "missing_card",
    "captions",
    "desk",
    "gus",
    "live_door",
    "lower_third",
    "money_app",
    "oven_clock",
    "parody_tag",
    "perform",
    "phone_insert",
    "route_insert",
    "sign",
    "source_card",
    "stage",
    "studio",
    "ticker",
    "vera",
]

INK, FINE = 8.0, 5.0  # a contour and an inner stroke, as the pressed hand takes them
SLEEVE_INK, CUFF = 6.0, 12.0  # a sleeve's line, and how much cuff shows past it
PHONE_RISE, PHONE_HELD = 60.0, -66.0  # how far below his hands Gus's phone starts as they bring it up
FAR_BLUR, NEAR_BLUR = 4.0, 6.0  # px on the monitor wall and on the camera in the foreground
DESK_Y, LIP_Y, FRONT_Y, FLOOR_Y = 1082.0, 1134.0, 1150.0, 1730.0  # the top's back edge, its lip, the front, its foot
NECK_Y, COLLAR_Y, CHIN_TIP = (
    -200.0,
    -166.0,
    -20.0,
)  # the head's pivot, the jacket's closure, the chin's lowest point on the head
TWO_SHOT = {"vera": 262.0, "gus": 742.0}  # they fill the desk, so they sit left of the middle and leave the right edge
MUG_X, MUG_Y, MUG_SIZE = 1052.0, 1118.0, 0.82  # the one stretch of desk no sleeve reaches, in any shot or pose
FRAMING = {"vera": (540.0, 1.22), "gus": (560.0, 1.14)}  # (x, scale) of each close-up: the head clears a two-line cue
BANNER_Y, BANNER_H = 1146.0, 76.0  # under the desk's top, so the hands on it stay in the picture
LOWER_Y, LOWER_H = 1222.0, 130.0
TICKER_Y, TICKER_H = 1352.0, 64.0
CHIP = 10.0  # one corner for everything over the picture
CREDIT_GAP = 14.0  # between chips on the top row
SHADOW = "#160a3066"
PHONE_X, PHONE_Y, PHONE_W, PHONE_H = 190.0, 508.0, 700.0, 786.0  # the handset over the dimmed room
MAP_TOP = 108.0  # the screen under the phone's header
MAP_H = PHONE_H - MAP_TOP
TEAR = "#a8e0ff"
DROP = (6.0, 8.0)
LIT, LIGHTER = "#ffffff30", "#ffffff18"


# -- ink ---------------------------------------------------------------------------------------------------------------
def flat(cv: Canvas, parent, shape: brush.Shape, fill: str):
    """A brushed shape in this module's own units. :func:`srstudio.toon.flat` reads reference-screen pixels; the news
    parts are drawn in frame pixels on a bust at the desk, so nothing here goes through that scale."""
    points = [f"{value:.2f}" for value in shape]
    cubics = " ".join("C " + " ".join(points[i : i + 6]) for i in range(2, len(points), 6))
    return cv.path(parent, f"M {points[0]} {points[1]} {cubics} Z", fill, cv.clear, 0)


def _form(
    cv: Canvas,
    parent,
    points: Sequence[Point],
    fill: str,
    tone: str | None = None,
    seed: float = 0.0,
    weight: float = INK,
    depth: float = 20.0,
    amount: float = 0.6,
) -> tuple[Point, ...]:
    """A closed shape the way the cast is drawn: a pressed ink band, the fill, the shade away from the light."""
    contour = drifted(points, amount, seed)
    flat(cv, parent, pressed(contour, weight, seed=seed), PLUM_DEEP)
    flat(cv, parent, brush.outline(contour, steps=3), fill)
    if tone:
        for shape, colour in shade(contour, depth, tone):
            flat(cv, parent, shape, colour)
    return contour


def _line(
    cv: Canvas, parent, points: Sequence[Point], colour: str = PLUM_DEEP, weight: float = FINE, press=LINE
) -> None:
    """An open inner stroke, pressed in the middle and lifted at its ends."""
    flat(cv, parent, brush.stroke(points, weight, press, steps=4), colour)


def _oval(cv: Canvas, parent, x: float, y: float, rx: float, ry: float, fill: str) -> None:
    flat(cv, parent, brush.ellipse(x, y, rx, ry), fill)


def _inked_oval(cv: Canvas, parent, x: float, y: float, rx: float, ry: float, fill: str, weight: float = 4.0) -> None:
    _oval(cv, parent, x, y, rx + weight, ry + weight, PLUM_DEEP)
    _oval(cv, parent, x, y, rx, ry, fill)


def _limb(s: Point, e: Point, w: Point, top: float, bend: float, wrist: float) -> tuple[Point, ...]:
    """The contour of a sleeve from shoulder ``s`` through elbow ``e`` to wrist ``w``: two straight lengths that meet
    at a corner, wide at the top and narrow at the cuff, so it bends like an arm and not a hose."""

    def unit(a: Point, b: Point) -> Point:
        d = math.dist(a, b) or 1.0
        return (b[0] - a[0]) / d, (b[1] - a[1]) / d

    (ux, uy), (vx, vy) = unit(s, e), unit(e, w)
    n1, n2 = (-uy, ux), (-vy, vx)
    turn = ux * vy - uy * vx
    outer = -1.0 if turn > 0 else 1.0
    jx, jy = n1[0] + n2[0], n1[1] + n2[1]
    size = math.hypot(jx, jy) or 1.0
    jx, jy = jx / size, jy / size

    def side(sign_: float, reach: float) -> list[Point]:
        mid1 = ((s[0] + e[0]) / 2, (s[1] + e[1]) / 2)
        mid2 = ((e[0] + w[0]) / 2, (e[1] + w[1]) / 2)
        half = (top + bend) / 4
        low = (bend + wrist) / 4
        return [
            (s[0] + n1[0] * sign_ * top / 2, s[1] + n1[1] * sign_ * top / 2),
            (mid1[0] + n1[0] * sign_ * half, mid1[1] + n1[1] * sign_ * half),
            (e[0] + jx * sign_ * reach, e[1] + jy * sign_ * reach),
            (mid2[0] + n2[0] * sign_ * low, mid2[1] + n2[1] * sign_ * low),
            (w[0] + n2[0] * sign_ * wrist / 2, w[1] + n2[1] * sign_ * wrist / 2),
        ]

    far = side(outer, bend * 0.56)
    near = side(-outer, bend * 0.3)
    cap = (s[0] - ux * top * 0.26, s[1] - uy * top * 0.26)
    return (cap, *far, *reversed(near))


FINGERS_UP: tuple[Point, ...] = (  # the open hand, wrist at the origin, fingers up
    (-20, 8),
    (-25, -14),
    (-48, -24),
    (-60, -44),
    (-48, -50),
    (-28, -36),
    (-29, -62),
    (-33, -92),
    (-20, -98),
    (-12, -68),
    (-9, -104),
    (5, -106),
    (9, -70),
    (17, -98),
    (30, -94),
    (26, -62),
    (39, -82),
    (50, -74),
    (36, -38),
    (30, -14),
    (20, 8),
)
FIST: tuple[Point, ...] = (
    (-22, 6),
    (-34, -14),
    (-38, -42),
    (-26, -60),
    (-6, -66),
    (14, -64),
    (32, -56),
    (40, -36),
    (34, -12),
    (22, 6),
)
RESTING: tuple[Point, ...] = (  # a hand lying on the desk: the back of it, four fingers toward the viewer's side
    (-22, 6),
    (-32, -18),
    (-34, -44),
    (-32, -66),
    (-20, -72),
    (-13, -52),
    (-9, -78),
    (4, -80),
    (9, -54),
    (15, -74),
    (28, -70),
    (30, -46),
    (36, -24),
    (22, 6),
)
POINTING: tuple[Point, ...] = (  # a level point: three fingers curled under, the thumb on top, read from the side
    (-22, 6),
    (-38, -12),
    (-40, -40),
    (-28, -58),
    (-10, -62),
    (-8, -94),
    (-6, -122),
    (8, -124),
    (14, -96),
    (16, -64),
    (30, -58),
    (50, -74),
    (62, -62),
    (44, -32),
    (34, -12),
    (22, 6),
)
HANDS: dict[str, tuple[Point, ...]] = {"open": FINGERS_UP, "fist": FIST, "rest": RESTING, "point": POINTING}


def _hand(
    cv: Canvas, parent, kind: str, at: Point, turn: float, skin: str, tone: str, size: float = 1.0, seed: float = 0.0
) -> None:
    """A hand with its wrist at ``at``, fingers ``turn`` degrees clockwise of up, in the same ink as the sleeve."""
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1], rotation=turn, scaleX=size, scaleY=size)
    _form(cv, g, HANDS[kind], skin, tone, seed, INK * 0.72, depth=11.0, amount=0.3)
    if kind == "fist":
        for x in (-16, 2, 20):
            _line(cv, g, ((x, -58), (x + 1, -40)), PLUM_DEEP, 3.6)
        _form(cv, g, ((-30, -22), (-8, -32), (14, -30), (22, -20), (6, -14), (-22, -10)), skin, None, seed + 1, 5.0)
    elif kind == "rest":
        _line(cv, g, ((-14, -30), (-14, -48)), tone, 3.2)
        _line(cv, g, ((8, -32), (9, -50)), tone, 3.2)
    elif kind == "open":
        _line(cv, g, ((-16, -24), (6, -14), (22, -26)), tone, 3.6)
    elif kind == "point":
        for y in (-46, -30, -14):
            _line(cv, g, ((-34, y), (-12, y - 3)), PLUM_DEEP, 3.6)


def _heading(a: Point, b: Point) -> float:
    return math.degrees(math.atan2(b[0] - a[0], a[1] - b[1]))


def _arm(
    cv: Canvas,
    parent,
    s: Point,
    e: Point,
    w: Point,
    sleeve: str,
    tone: str,
    cuff: str,
    hand: str,
    skin: str,
    shadow: str,
    seed: float,
    size: float = 1.0,
    turn: float | None = None,
) -> None:
    """A sleeve in two lengths, its shirt cuff, and the hand that belongs to it."""
    way = _heading(e, w)
    g = cv.group(parent, cv.uid("g"), x=w[0], y=w[1], rotation=way)
    _form(cv, g, ((-25, -7), (25, -7), (26, 7), (-26, 7)), cuff, None, seed + 2, 5.0, amount=0.2)
    _hand(cv, parent, hand, w, way if turn is None else turn, skin, shadow, size, seed + 3)
    contour = _limb(s, e, w, 78.0, 62.0, 46.0)
    _form(cv, parent, contour, sleeve, tone, seed, depth=16.0, amount=0.4)


# -- the set -----------------------------------------------------------------------------------------------------------
SCREEN_W, SCREEN_H, SCREEN_GAP = 322.0, 232.0, 16.0
SCREEN_X, SCREEN_Y = 41.0, 132.0
SCREENS = (
    ("#39c6e8", "#2563c9"),
    ("#ff9e4a", "#e8407a"),
    ("#46e3b7", "#1590a8"),
    ("#ff6f9c", "#9a36c0"),
    ("#56b4ff", "#4b3fd0"),
    ("#ffc24a", "#f0612e"),
    ("#55e0c8", "#2a78c8"),
    ("#ff8fb8", "#c2379c"),
    ("#6fa8ff", "#5a3bd6"),
)
LAMPS = (90.0, 270.0, 450.0, 630.0, 810.0, 990.0)


def _screen_at(i: int) -> Point:
    return SCREEN_X + (i % 3) * (SCREEN_W + SCREEN_GAP), SCREEN_Y + (i // 3) * (SCREEN_H + SCREEN_GAP)


def _bars(cv: Canvas, g, x: float, y: float) -> None:
    for k, h in enumerate((70, 110, 88, 150, 126, 176)):
        cv.rect(g, x + 34 + k * 44, y + SCREEN_H - 24 - h, 30, h, "#ffffff58", radius=4.0)


def _curve(cv: Canvas, g, x: float, y: float) -> None:
    w, foot = SCREEN_W, y + SCREEN_H
    for dy, paint in ((0.0, "#ffffff30"), (46.0, "#ffffff24")):
        cv.path(
            g,
            f"M {x} {foot} L {x} {foot - 70 - dy} C {x + w * 0.3} {foot - 170 - dy}, {x + w * 0.6} {foot - 40 - dy}, "
            f"{x + w} {foot - 130 - dy} L {x + w} {foot} Z",
            paint,
            cv.clear,
            0,
        )


def _rings(cv: Canvas, g, x: float, y: float) -> None:
    cx, cy = x + SCREEN_W / 2, y + SCREEN_H / 2
    for r in (92.0, 62.0, 32.0):
        cv.ellipse(g, cx - r, cy - r, 2 * r, 2 * r, cv.clear, "#ffffff70", 6.0)
    cv.path(g, f"M {cx} {cy} L {cx + 92} {cy - 40} A 100 100 0 0 1 {cx + 94} {cy + 22} Z", "#ffffff60", cv.clear, 0)


def _skyline(cv: Canvas, g, x: float, y: float) -> None:
    foot = y + SCREEN_H
    for k, (w, h) in enumerate(((40, 70), (54, 128), (34, 96), (60, 160), (44, 84), (52, 122))):
        left = x + 14 + sum((40, 54, 34, 60, 44, 52)[:k])
        cv.rect(g, left, foot - h, w - 4, h, "#ffffff3c")
    _oval(cv, g, x + 260, y + 58, 26, 26, "#ffffff90")


def _chevrons(cv: Canvas, g, x: float, y: float) -> None:
    mid = y + SCREEN_H / 2
    for k in range(3):
        left = x + 50 + k * 84
        cv.path(
            g,
            f"M {left} {mid - 76} L {left + 42} {mid - 76} L {left + 92} {mid} L {left + 42} {mid + 76} L {left} "
            f"{mid + 76} L {left + 50} {mid} Z",
            "#ffffff5c",
            cv.clear,
            0,
        )


def _dots(cv: Canvas, g, x: float, y: float) -> None:
    for row in range(5):
        for col in range(9):
            size = 6.0 + ((row * 3 + col * 5) % 7)
            _oval(cv, g, x + 34 + col * 32, y + 44 + row * 36, size, size, "#ffffff4c")


def _wave(cv: Canvas, g, x: float, y: float) -> None:
    mid = y + SCREEN_H / 2
    for k in range(22):
        h = 12.0 + 74.0 * abs(math.sin(k * 0.73)) * (0.5 + 0.5 * math.cos(k * 0.21))
        cv.rect(g, x + 22 + k * 13, mid - h, 8, 2 * h, "#ffffff60", radius=4.0)


PICTURES = (_bars, _curve, _rings, _skyline, _chevrons, _bars, _dots, _curve, _wave)


def _monitors(cv: Canvas, frame) -> None:
    wide = 3 * SCREEN_W + 2 * SCREEN_GAP + 28
    tall = 3 * SCREEN_H + 2 * SCREEN_GAP + 28
    cv.rect(frame, SCREEN_X - 14, SCREEN_Y - 14, wide, tall, "#120828", radius=12.0)
    cv.rect(frame, SCREEN_X - 14, SCREEN_Y - 14, wide, 4, "#ffffff40")
    for i, (top, foot) in enumerate(SCREENS):
        x, y = _screen_at(i)
        paint = cv.grad(f"news2-screen-{i}", [(0, top), (1, foot)], (0, 0, 0.6, 1))
        cv.rect(frame, x - 4, y - 4, SCREEN_W + 8, SCREEN_H + 8, "#3a2a5e", radius=8.0)
        cv.rect(frame, x, y, SCREEN_W, SCREEN_H, paint, radius=4.0)
        PICTURES[i](cv, frame, x, y)
        cv.path(
            frame,
            f"M {x} {y} L {x + 150} {y} L {x + 40} {y + SCREEN_H} L {x} {y + SCREEN_H} Z",
            "#ffffff14",
            cv.clear,
            0,
        )
    for row, (rise, fade) in enumerate(SWEEP):
        lit = cv.group(frame, cv.uid("g"), opacity=0.0)
        for i in range(row * 3, row * 3 + 3):
            x, y = _screen_at(i)
            cv.rect(lit, x, y, SCREEN_W, SCREEN_H, "#ffffff", radius=4.0)
        cv.keys(
            lit,
            "opacity",
            [(rise, 0.0), ((rise + fade) / 2, SWEEP_LIGHT), (fade, 0.0)],
            kind="sine-in-out",
            local=False,
        )


def _rig(cv: Canvas, frame) -> None:
    """The lighting truss that fills the room's head: two rails, cans on them, and the light they drop."""
    cv.rect(frame, 0, 18, cv.width, 12, "#0e0620")
    cv.rect(frame, 0, 76, cv.width, 8, "#0e0620")
    for k in range(13):
        x = k * 90.0
        cv.path(frame, f"M {x} 24 L {x + 45} 80 L {x + 90} 24", cv.clear, "#0e0620", 5.0)
    for i, x in enumerate(LAMPS):
        beam = cv.grad(f"news2-beam-{i}", [(0, "#ffe9c858"), (1, "#ffe9c800")], (0, 0, 0, 1))
        cv.path(frame, f"M {x - 18} 100 L {x + 18} 100 L {x + 92} 470 L {x - 92} 470 Z", beam, cv.clear, 0)
        cv.rect(frame, x - 24, 62, 48, 38, "#1a0e36", radius=6.0)
        _oval(cv, frame, x, 104, 22, 9, "#fff6e4")


@register(
    "location", "news-set@2", summary="The studio with planes: a lit room, a monitor wall with pictures, a truss above"
)
def studio(cv: Canvas, parent, end: float = 10.0) -> None:
    """The far plane out of focus: a truss in the room's head, nine bezelled screens with a picture on each, the light
    passing down them row by row, and a panelled wall under them. A veil falls on the wall behind the anchors so a face
    never competes with a screen, and the screens' own light spills on the wall. It carries no word."""
    wall = cv.grad("news2-wall", [(0, "#1a0b3c"), (0.55, "#35186c"), (1, "#54288c")], (0, 0, 0, 1))
    cv.rect(parent, 0, 0, cv.width, DESK_Y + 60, wall)
    far = look.depth(cv, parent, "news-far", FAR_BLUR)
    frame = cv.group(far, cv.uid("g"))
    _rig(cv, frame)
    foot = SCREEN_Y + 3 * SCREEN_H + 2 * SCREEN_GAP + 14
    for x in (0.0, cv.width - 18.0):
        cv.rect(frame, x, 110, 18, foot - 110, "#2c1460")
        cv.rect(frame, x + 7, 130, 4, foot - 150, "#ffd9a860")
    _monitors(cv, frame)
    panel = cv.grad("news2-panel", [(0, "#3a1b76"), (1, "#26105a")], (0, 0, 0, 1))
    cv.rect(frame, 0, foot, cv.width, DESK_Y + 60 - foot, panel)
    for k in range(9):
        cv.rect(frame, 20 + k * 120.0, foot + 28, 104, 200, "#ffffff0c", radius=6.0)
    cv.rect(frame, 0, foot + 8, cv.width, 5, "#ffb56a80")
    cv.rect(parent, 0, 0, cv.width, DESK_Y + 60, "#1a0b3c70")  # the room's level: screens are lit, not the key
    look.fade(cv, parent, "news2-veil", "#160a30c8", DESK_Y, 500.0, cv.width)
    look.pool(cv, parent, "news2-key", "#ffd9a830", -340, 120, 1100, 1000)


def _mug(cv: Canvas, parent, x: float, y: float, size: float) -> None:
    """A mug with its foot at ``(x, y)``, its handle away from the anchors and past the frame's edge."""
    g = cv.group(parent, cv.uid("news-mug"), x=x, y=y, scaleX=size, scaleY=size)
    look.pool(cv, g, "news2-mug-shadow", "#160a3099", -66, -6, 132, 30)
    _form(cv, g, ((26, -50), (62, -46), (60, -18), (28, -16)), cv.clear, None, 7.0, 6.0)
    _form(
        cv,
        g,
        ((-40, -74), (40, -74), (37, -6), (22, 6), (-22, 6), (-37, -6)),
        CREAM,
        "#d9c6b0",
        5.0,
        6.5,
        depth=14.0,
        amount=0.2,
    )
    _oval(cv, g, 0, -74, 38, 9, "#4a2413")
    cv.rect(g, -37, -50, 74, 12, TANGERINE)


def _notepad(cv: Canvas, parent, x: float, y: float) -> None:
    look.pool(cv, parent, "news2-pad-shadow", "#160a3088", x - 92, y + 2, 190, 34)
    _form(
        cv, parent, ((x - 62, y - 18), (x + 52, y - 18), (x + 76, y + 18), (x - 76, y + 18)), "#efe6ff", None, 3.0, 5.5
    )
    for k in (-6.0, 4.0):
        _line(cv, parent, ((x - 44, y + k), (x + 42, y + k)), "#9b8cc4", 3.0)


def _camera(cv: Canvas, g) -> None:
    """A studio camera between us and the desk, cropped by the frame's foot, out of focus: the nearest plane."""
    near = look.depth(cv, g, "news-near", NEAR_BLUR)
    body = cv.grad("news2-camera", [(0, "#35255a"), (1, "#0a0516")], (0, 0, 0, 1))
    cv.path(near, "M -70 1990 L -40 1820 L 150 1820 L 190 1990 Z", "#0a0516", cv.clear, 0)
    cv.rect(near, -80, 1650, 300, 196, body, radius=26.0)
    cv.rect(near, 200, 1682, 96, 124, "#0e0620", radius=16.0)
    cv.rect(near, 288, 1696, 22, 96, "#3a2a5e", radius=8.0)
    cv.rect(near, -80, 1650, 300, 8, "#8a6fc0", radius=4.0)
    _oval(cv, near, 176, 1686, 9, 9, TANGERINE)


@register("prop", "news-desk@2", summary="The anchor desk: a polished top with a lip, a lit front, a floor under it")
def desk(cv: Canvas, parent) -> None:
    """A top with a back edge, a sheen and a lit lip; a front of ribbed panels that curves away, a light box with the
    show's chevrons and no word; a kick plate, then a glossy floor with the desk's shadow and light on it. The frame's
    foot is room, not lettering, so a Reels button covers nothing."""
    g = cv.group(parent, cv.uid("g"))
    look.fade(cv, g, "news2-behind", "#160a3090", DESK_Y, DESK_Y - 90.0, cv.width)
    floor = cv.grad("news2-floor", [(0, "#22104a"), (1, "#0c0520")], (0, 0, 0, 1))
    cv.rect(g, -40, FLOOR_Y - 90, cv.width + 80, cv.height - FLOOR_Y + 130, floor)
    look.pool(cv, g, "news2-floor-glow", "#3fe0b520", 60, FLOOR_Y + 6, 960, 110)
    shadow = cv.group(g, f"news-contact-floor-{cv.uid('c')}")
    cv.path(
        shadow,
        f"M -40 {FLOOR_Y - 30} Q 540 {FLOOR_Y + 100} {cv.width + 40} {FLOOR_Y - 30} L {cv.width + 40} {FLOOR_Y - 10} "
        f"Q 540 {FLOOR_Y + 150} -40 {FLOOR_Y - 10} Z",
        "#07021499",
        cv.clear,
        0,
    )
    _desk_front(cv, g)
    top = cv.grad("news2-top", [(0, "#8d6bc4"), (0.55, "#c9a8ea"), (1, "#f6e6ff")], (0, 0, 0, 1))
    cv.rect(g, -40, DESK_Y, cv.width + 80, LIP_Y - DESK_Y, top)
    cv.rect(g, -40, DESK_Y, cv.width + 80, 5, PLUM_DEEP)
    for left, w in ((120.0, 170.0), (640.0, 240.0)):  # the room's lamps in the polish
        cv.path(
            g,
            f"M {left} {DESK_Y + 8} L {left + w} {DESK_Y + 8} "
            f"L {left + w - 40} {LIP_Y - 6} L {left - 40} {LIP_Y - 6} Z",
            "#ffffff2c",
            cv.clear,
            0,
        )
    lip = cv.grad("news2-lip", [(0, "#fff4ff"), (0.35, "#b48fdc"), (1, "#54288c")], (0, 0, 0, 1))
    cv.rect(g, -40, LIP_Y, cv.width + 80, FRONT_Y - LIP_Y, lip)
    cv.rect(g, -40, FRONT_Y, cv.width + 80, 6, PLUM_DEEP)
    _notepad(cv, g, 96.0, DESK_Y + 28.0)
    _mug(cv, g, MUG_X, MUG_Y, MUG_SIZE)
    _camera(cv, g)


def _desk_front(cv: Canvas, g) -> None:
    """The desk's front: panels that narrow toward the frame's edges, as a curved front does, a recessed band with a
    row of the show's chevrons, and a kick plate with a mint light along it."""
    front = cv.grad("news2-front", [(0, "#2e1566"), (0.5, "#4a2288"), (1, "#26105a")], (0, 0, 0, 1))
    cv.path(
        g,
        f"M -40 {FRONT_Y} L {cv.width + 40} {FRONT_Y} L {cv.width + 40} {FLOOR_Y - 60} "
        f"Q 540 {FLOOR_Y + 60} -40 {FLOOR_Y - 60} Z",
        front,
        cv.clear,
        0,
    )
    edges = [540.0 + 640.0 * math.sin(math.radians(a)) for a in range(-72, 73, 24)]
    for i, (left, right) in enumerate(zip(edges, edges[1:], strict=False)):
        if i % 2:
            cv.path(
                g,
                f"M {left} {FRONT_Y} L {right} {FRONT_Y} L {right} {_foot(right - 540.0)} "
                f"L {left} {_foot(left - 540.0)} Z",
                "#ffffff0c",
                cv.clear,
                0,
            )
    for x in edges:
        cv.rect(g, x - 3, FRONT_Y, 6, _foot(x - 540.0) - FRONT_Y, "#160a3090")
        cv.rect(g, x + 3, FRONT_Y, 2, _foot(x - 540.0) - FRONT_Y, "#ffffff20")
    band = cv.grad("news2-band", [(0, "#160a30"), (1, "#22104a")], (0, 0, 0, 1))
    cv.rect(g, 96, 1500, 888, 92, band, radius=CHIP)
    cv.rect(g, 96, 1500, 888, 3, TANGERINE)
    for k in range(-5, 6):
        left = 540.0 + k * 74.0 - 24.0
        paint = TANGERINE if abs(k) < 2 else (TANGERINE_DARK if abs(k) < 4 else "#7a3f1e")
        cv.path(
            g,
            f"M {left} 1522 L {left + 20} 1522 L {left + 46} 1546 L {left + 20} 1570 L {left} 1570 "
            f"L {left + 26} 1546 Z",
            paint,
            cv.clear,
            0,
        )
    kick = cv.grad("news2-kick", [(0, "#160a30"), (1, "#0c0520")], (0, 0, 0, 1))
    cv.path(
        g,
        f"M -40 {FLOOR_Y - 74} Q 540 {FLOOR_Y + 46} {cv.width + 40} {FLOOR_Y - 74} L {cv.width + 40} "
        f"{FLOOR_Y - 56} Q 540 {FLOOR_Y + 64} -40 {FLOOR_Y - 56} Z",
        kick,
        cv.clear,
        0,
    )
    cv.path(g, f"M -40 {FLOOR_Y - 78} Q 540 {FLOOR_Y + 42} {cv.width + 40} {FLOOR_Y - 78}", cv.clear, MINT, 4.0)


def _foot(dx: float) -> float:
    """Where the front meets its kick plate, ``dx`` from the middle of the frame."""
    return FLOOR_Y - 18.0 - dx**2 / 4900.0


# -- the anchors -------------------------------------------------------------------------------------------------------
VERA_SKIN, VERA_TONE, VERA_DEEP = "#9a6240", "#75462b", "#5b3420"
GUS_SKIN, GUS_TONE, GUS_DEEP = "#ffd5ae", "#e2a67c", "#b97a50"
VERA_INKED = replace(VERA_FACE, skin=VERA_SKIN)
GUS_INKED = replace(GUS_FACE, skin=GUS_SKIN)
# Version 4: every mouth between the nose and the chin, with the face at the end of its drop on the rig. The shout has
# less height there than it had, so it takes width: it is the widest mouth on the face.
VERA_REDRAWN = replace(VERA_INKED, jaws=(Jaw("gape", -80.0, 78.0, 37.0), Jaw("grin", -78.0, 62.0, 33.0)))
GUS_REDRAWN = replace(
    GUS_INKED, jaws=(Jaw("gape", -84.0, 104.0, 39.0), Jaw("open", -75.0, 88.0, 31.0), Jaw("round", -69.5, 88.0, 23.5))
)


def inked(who: str, number: int = 2) -> Face:
    """The face of version ``number`` of ``who``: every version before 4 draws the same one."""
    if who == "vera":
        return VERA_REDRAWN if number >= 4 else VERA_INKED
    return GUS_REDRAWN if number >= 4 else GUS_INKED


def _tear(cv: Canvas, parent, x: float, y: float, r: float) -> None:
    """A tear running down the cheek from a shut eye, and the next one on its way."""
    drop = ((x - r * 0.3, y + r * 0.7), (x, y), (x + r * 0.3, y + r * 0.7), (x, y + r * 1.2))
    _form(cv, parent, drop, TEAR, "#3b83c9", 90.0, 3.0, 3.5, 0.1)
    low = tuple((px, py + r * 1.5) for px, py in drop)
    _form(cv, parent, low, TEAR, "#3b83c9", 90.0, 3.0, 3.5, 0.1)


def _eye(cv: Canvas, parent, face: Face, side: float, state: str) -> None:
    x, y, r = side * face.eye_x, face.eye_y, face.eye_r
    if state in ("shut", "weep"):
        _line(cv, parent, ((x - r, y + 1), (x, y + 10), (x + r, y + 1)), PLUM_DEEP, 7.0)
        if state == "weep":
            _tear(cv, parent, x, y + 14, r)
        return
    wide = 1.28 if state == "wide" else 1.0
    tall = {"wide": 1.45, "squint": 0.55, "down": 0.7}.get(state, 1.0)
    _inked_oval(cv, parent, x, y, r * wide, r * 1.08 * tall, "#ffffff", 3.4)
    _oval(cv, parent, x, y + r * 0.8 * tall, r * wide * 0.7, r * 0.14, "#e6e3f0")
    dx = {"side": face.toward * r * 0.42, "over": 0.0}.get(state, 0.0)
    dy = {"down": r * 0.34, "over": -r * 0.3}.get(state, 0.0)
    size = r * (0.48 if state == "wide" else 0.62)
    _oval(cv, parent, x + dx, y + dy, size, size, face.iris)
    _oval(cv, parent, x + dx, y + dy, size * 0.55, size * 0.55, PLUM_DEEP)
    _oval(cv, parent, x + dx - size * 0.32, y + dy - size * 0.36, size * 0.28, size * 0.28, "#ffffff")
    _oval(cv, parent, x + dx + size * 0.3, y + dy + size * 0.3, size * 0.13, size * 0.13, "#ffffff")
    if state != "wide":  # a level lid: nobody at this desk is surprised until they are
        top = y - r * 1.25
        cv.path(
            parent,
            f"M {x - r - 5} {y - r * 0.62} L {x + r + 5} {y - r * 0.62} L {x + r + 3} {top} L {x - r - 3} {top} Z",
            face.skin,
            cv.clear,
            0,
        )
        _line(cv, parent, ((x - r - 6, y - r * 0.56), (x, y - r * 0.66), (x + r + 6, y - r * 0.56)), PLUM_DEEP, 8.0)
    else:
        _line(cv, parent, ((x - r * 1.2, y - r), (x, y - r * 1.62), (x + r * 1.2, y - r)), PLUM_DEEP, 6.0)


def _brow(cv: Canvas, parent, face: Face, side: float, state: str) -> None:
    x, y, r = side * face.eye_x, face.eye_y, face.eye_r
    lift = {"wide": 26.0, "over": 16.0, "squint": -10.0, "down": -2.0, "shut": -4.0}.get(state, 0.0)
    if face.glasses and side > 0:  # hers: the right brow lives a little higher than the news deserves
        lift += 8.0
    tilt = 10.0 if state == "squint" else (-6.0 if state == "wide" else 0.0)
    top = y - r * 1.5 - lift
    _line(
        cv,
        parent,
        ((x - side * r * 1.15, top + 5), (x, top - 7), (x + side * r * 1.25, top + 7 + tilt)),
        face.brow,
        face.brow_w * 1.5,
    )


def _specs(cv: Canvas, parent, face: Face, drop: float) -> None:
    """Her half-moon glasses; she looks over them, and only then does anyone at the desk worry."""
    y = face.eye_y + drop
    for side in (-1.0, 1.0):
        x = side * face.eye_x
        cv.path(
            parent,
            f"M {x - 34} {y - 6} L {x + 34} {y - 6} Q {x + 34} {y + 26} {x} {y + 28} "
            f"Q {x - 34} {y + 26} {x - 34} {y - 6} Z",
            "#ffffff0e",
            PLUM_DEEP,
            5.0,
        )
        cv.path(
            parent,
            f"M {x - 28} {y + 8} L {x - 18} {y - 2} L {x - 14} {y - 2} L {x - 24} {y + 10} Z",
            "#ffffff70",
            cv.clear,
            0,
        )
    _line(cv, parent, ((-14, y - 3), (0, y - 11), (14, y - 3)), PLUM_DEEP, 5.5)
    for side in (-1.0, 1.0):
        _line(cv, parent, ((side * 82, y - 6), (side * 112, y - 14)), PLUM_DEEP, 4.5)


def _eyes(cv: Canvas, head, face: Face, track: Track, start: float, end: float) -> None:
    for state, spans in _spans(track, start, end).items():
        g = cv.group(head, cv.uid("g"), opacity=0.0)
        cv.gate(g, spans)
        for side in (-1.0, 1.0):
            _eye(cv, g, face, side, state)
            _brow(cv, g, face, side, state)
        if face.glasses:
            _specs(cv, g, face, 26.0 if state == "over" else 0.0)


def _mouths(cv: Canvas, head, face: Face, track: Track, start: float, end: float) -> None:
    for state, spans in _spans(track, start, end).items():
        g = cv.group(head, cv.uid("g"), opacity=0.0)
        cv.gate(g, spans)
        jaw = next((j for j in face.jaws if j.state == state), None)
        drawn = replace(face, mouth_y=jaw.y, mouth_w=jaw.wide) if jaw else face
        y, w = drawn.mouth_y, drawn.mouth_w
        if state in ("flat", "closed"):
            _line(cv, g, ((-w * 0.52, y + 1), (0, y - 1), (w * 0.52, y + 1)), face.lip, 9.0)
        elif state == "smirk":
            _line(cv, g, ((-w * 0.5, y + 4), (w * 0.1, y + 6), (w * 0.58, y - 13)), face.lip, 9.0)
        elif state == "frown":
            _line(cv, g, ((-w * 0.58, y + 12), (0, y - 4), (w * 0.58, y + 12)), face.lip, 9.0)
        elif state == "teeth":  # a word, not a smile: a mouth a little open, teeth along the top of it
            cv.path(
                g,
                f"M {-w * 0.42} {y - 8} Q 0 {y - 13} {w * 0.42} {y - 8} Q {w * 0.46} {y + 14} 0 {y + 18} "
                f"Q {-w * 0.46} {y + 14} {-w * 0.42} {y - 8} Z",
                "#4a1420",
                PLUM_DEEP,
                5.0,
            )
            cv.path(
                g,
                f"M {-w * 0.34} {y - 8} Q 0 {y - 12} {w * 0.34} {y - 8} L {w * 0.28} {y + 2} L {-w * 0.28} {y + 2} Z",
                "#ffffff",
                cv.clear,
                0,
            )
        else:
            _mouth(cv, g, drawn, state, jaw.tall if jaw else None)


TEAL, TEAL_TONE, TEAL_LAPEL = "#16857f", "#0d5a5e", "#1fa79c"
SILVER, SILVER_TONE, SILVER_LINE = "#dcdae8", "#a5a1c2", "#6f6b92"
ORANGE, ORANGE_TONE, ORANGE_LAPEL = "#ffa548", "#dd6f12", "#ffb96c"
HAIR, HAIR_TONE, HAIR_SHINE = "#4a2413", "#2f1409", "#8a5230"


Motion = tuple[AnchorRig, HeadPlan] | None  # a head on its rig and what it does in this shot; None, the drawing at rest


def _slides(cv: Canvas, head, motion: Motion):
    """Where what slides across the head goes: the head itself when it does not move, else a group of its own."""
    if motion is None:
        return head
    rig, plan = motion
    face = cv.group(head, cv.uid("head-face"))
    toon_head._animate(cv, face, "x", plan.face_x)
    toon_head._animate(cv, face, "y", plan.nod, rig.face_slide)
    return face


def _neck(cv: Canvas, g, skin: str, tone: str, deep: str, wide: float) -> None:
    _form(
        cv,
        g,
        ((-wide, -262), (-wide, -196), (-wide - 12, -150), (wide + 12, -150), (wide, -196), (wide, -262)),
        skin,
        tone,
        3.0,
        INK * 0.8,
        depth=16.0,
        amount=0.3,
    )
    cv.path(  # the chin's shadow
        g,
        f"M {-wide + 4} -214 Q 0 -160 {wide - 4} -214 L {wide - 4} -196 Q 0 -146 {-wide + 4} -196 Z",
        deep + "90",
        cv.clear,
        0,
    )


VERA_TORSO: tuple[Point, ...] = (
    (-216, 60),
    (-214, -20),
    (-204, -84),
    (-168, -130),
    (-112, -150),
    (-62, -158),
    (-44, -166),
    (0, -120),
    (44, -166),
    (62, -158),
    (112, -150),
    (168, -130),
    (204, -84),
    (214, -20),
    (216, 60),
)


def _vera_body(cv: Canvas, g, number: int = 2) -> None:
    _neck(cv, g, VERA_SKIN, VERA_TONE, VERA_DEEP, 42.0)
    torso = news_arms.TORSOS["vera"] if number >= 5 else VERA_TORSO
    _form(cv, g, torso, TEAL, TEAL_TONE, 11.0, depth=30.0, amount=0.3)
    _form(
        cv, g, ((-46, -164), (0, -74), (46, -164), (24, -150), (0, -132), (-24, -150)), CREAM, "#e3d3bc", 12.0, 5.5, 8.0
    )
    _form(
        cv,
        g,
        ((-46, -166), (-68, -152), (-98, -112), (-58, -92), (-34, -96), (-12, -40), (0, -44), (-18, -110)),
        TEAL_LAPEL,
        None,
        13.0,
        6.0,
    )
    _form(
        cv,
        g,
        ((46, -166), (68, -152), (98, -112), (58, -92), (34, -96), (12, -40), (0, -44), (18, -110)),
        TEAL_LAPEL,
        TEAL,
        14.0,
        6.0,
        depth=10.0,
    )
    _inked_oval(cv, g, -106, -86, 13, 13, TANGERINE, 3.5)
    _oval(cv, g, -110, -91, 4, 4, "#ffd9a8")
    _line(cv, g, ((0, -44), (2, 30)), PLUM_DEEP, 5.0)


def _sheaf(cv: Canvas, g) -> None:
    """The news under Vera's hands."""
    look.pool(cv, g, "news2-sheaf-shadow", "#160a3099", -130, 10, 260, 34)
    _form(cv, g, ((-96, -18), (96, -18), (116, 28), (-116, 28)), "#efe7f5", None, 21.0, 5.5, amount=0.2)
    _form(cv, g, ((-92, -26), (92, -26), (110, 20), (-110, 20)), CREAM, None, 22.0, 5.5, amount=0.2)
    for k in (-10.0, -1.0, 8.0):
        _line(cv, g, ((-62 - k * 0.3, k), (58 + k * 0.3, k)), "#c7bcd6", 3.4)


VERA_ARM: tuple[Point, Point, Point] = (
    (174.0, -96.0),
    (222.0, 4.0),
    (92.0, 14.0),
)  # shoulder, elbow, wrist, on the right


def _vera_arms(cv: Canvas, parent, spans: Mapping[str, Spans]) -> None:
    for when in spans.values():  # her hands stay where they are: it is the news that moves
        g = cv.group(parent, cv.uid("g"), opacity=0.0)
        cv.gate(g, when)
        _sheaf(cv, g)
        for side, seed in ((-1.0, 31.0), (1.0, 37.0)):
            _arm(
                cv,
                g,
                (side * VERA_ARM[0][0], VERA_ARM[0][1]),
                (side * VERA_ARM[1][0], VERA_ARM[1][1]),
                (side * VERA_ARM[2][0], VERA_ARM[2][1]),
                TEAL,
                TEAL_TONE,
                CREAM,
                "rest",
                VERA_SKIN,
                VERA_TONE,
                seed,
                0.92,
                side * -98.0,
            )


VERA_BACK: tuple[Point, ...] = (
    (-58, -324),
    (12, -334),
    (84, -318),
    (142, -268),
    (172, -196),
    (176, -128),
    (160, -74),
    (122, -52),
    (98, -74),
    (0, -90),
    (-98, -74),
    (-126, -48),
    (-164, -70),
    (-180, -128),
    (-172, -204),
    (-130, -278),
)
VERA_HEAD: tuple[Point, ...] = (
    (-110, -178),
    (-106, -118),
    (-80, -68),
    (-38, -40),
    (0, -33),
    (38, -40),
    (80, -68),
    (106, -118),
    (110, -178),
    (98, -236),
    (52, -270),
    (0, -278),
    (-52, -270),
    (-98, -236),
)


def _vera_head(
    cv: Canvas, g, eyes: Track, mouth: Track, start: float, end: float, motion: Motion = None, face: Face = VERA_INKED
) -> None:
    _form(cv, g, VERA_BACK, SILVER_TONE, "#7f7ba1", 41.0, depth=26.0)
    _form(cv, g, VERA_HEAD, VERA_SKIN, VERA_TONE, 43.0, depth=30.0, amount=0.4)
    under = _slides(cv, g, motion)
    cv.path(under, "M -92 -116 Q -74 -98 -50 -106 Q -74 -128 -92 -116 Z", "#b3603c50", cv.clear, 0)
    cv.path(under, "M 92 -116 Q 74 -98 50 -106 Q 74 -128 92 -116 Z", "#b3603c50", cv.clear, 0)
    _line(cv, under, ((-5, -152), (-15, -118), (-3, -104), (15, -108)), VERA_DEEP, 6.0)
    _line(cv, under, ((-60, -98), (-52, -82)), VERA_TONE, 3.6)
    _line(cv, under, ((60, -98), (52, -82)), VERA_TONE, 3.6)
    left = (
        (36, -306),
        (-30, -312),
        (-98, -288),
        (-140, -226),
        (-146, -150),
        (-130, -112),
        (-114, -148),
        (-106, -196),
        (-72, -228),
        (-22, -244),
        (34, -256),
    )
    _form(cv, g, left, SILVER, SILVER_TONE, 44.0, depth=18.0)
    right = (
        (34, -306),
        (92, -298),
        (138, -250),
        (150, -170),
        (136, -112),
        (116, -142),
        (110, -194),
        (88, -234),
        (52, -256),
        (34, -258),
    )
    _form(cv, g, right, SILVER, SILVER_TONE, 45.0, depth=18.0)
    for line in (
        ((-108, -214), (-68, -262), (-14, -286), (26, -288)),
        ((-84, -214), (-50, -244), (-6, -262), (24, -270)),
        ((-130, -176), (-124, -230), (-94, -268)),
        ((62, -282), (104, -256), (126, -206)),
        ((70, -262), (100, -226), (112, -196)),
        ((142, -136), (160, -186), (150, -240)),
        ((-160, -112), (-168, -176), (-150, -240)),
    ):
        _line(cv, g, line, SILVER_LINE, 4.6)
    cv.path(g, "M -100 -248 Q -54 -290 8 -296 Q -46 -270 -84 -226 Z", "#ffffff66", cv.clear, 0)
    over = _slides(cv, g, motion)
    _eyes(cv, over, face, eyes, start, end)
    _mouths(cv, over, face, mouth, start, end)


GUS_TORSO: tuple[Point, ...] = (
    (-228, 60),
    (-226, -20),
    (-212, -90),
    (-172, -134),
    (-116, -152),
    (-66, -158),
    (-48, -168),
    (-4, -110),
    (52, -166),
    (68, -156),
    (122, -148),
    (178, -128),
    (214, -80),
    (226, -20),
    (228, 60),
)


def _gus_body(cv: Canvas, g, number: int = 2) -> None:
    _neck(cv, g, GUS_SKIN, GUS_TONE, GUS_DEEP, 48.0)
    torso = news_arms.TORSOS["gus"] if number >= 5 else GUS_TORSO
    _form(cv, g, torso, ORANGE, ORANGE_TONE, 51.0, depth=32.0, amount=0.5)
    _form(
        cv,
        g,
        ((-52, -166), (-4, -70), (54, -164), (24, -150), (-4, -140), (-28, -150)),
        MINT,
        MINT_DARK,
        52.0,
        5.5,
        8.0,
    )
    _form(cv, g, ((-16, -150), (24, -146), (20, -122), (-8, -126)), ROSE, "#d43b70", 53.0, 5.5, 6.0, 0.3)
    _form(cv, g, ((-8, -130), (20, -126), (42, -48), (10, -26), (-20, -46)), ROSE, "#d43b70", 54.0, 5.5, 12.0, 0.3)
    _form(
        cv,
        g,
        ((-52, -168), (-76, -152), (-104, -116), (-62, -96), (-40, -100), (-14, -40), (-2, -44), (-22, -116)),
        ORANGE_LAPEL,
        None,
        55.0,
        6.0,
    )
    _form(
        cv,
        g,
        ((54, -166), (74, -150), (100, -120), (58, -98), (38, -102), (6, -40), (-4, -42), (22, -116)),
        ORANGE_LAPEL,
        ORANGE,
        56.0,
        6.0,
        depth=10.0,
    )
    if number < 5:  # from version 5 the sleeves lie where these two creases sat, and they read as marks on his chest
        _line(cv, g, ((-170, -66), (-152, -52), (-138, -62)), "#b4520c", 5.0)  # a jacket that has been sat on
        _line(cv, g, ((160, -52), (148, -44), (134, -54)), "#b4520c", 5.0)


def _phone(cv: Canvas, parent, x: float, y: float) -> None:
    """The back of his phone, which is what the rest of us see of it, in a case he chose."""
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    _form(cv, g, ((-46, -84), (46, -84), (48, 76), (-48, 76)), PLUM, "#160a30", 71.0, 7.0, 10.0, 0.1)
    cv.rect(g, -36, -74, 36, 48, "#160a30", radius=9.0)
    _oval(cv, g, -18, -62, 9, 9, "#6f8fd0")
    _oval(cv, g, -18, -38, 9, 9, "#6f8fd0")
    _oval(cv, g, -20, -64, 3, 3, "#ffffff")
    cv.path(g, "M 18 -70 L 34 -70 L 8 66 L -8 66 Z", "#ffffff14", cv.clear, 0)


GUS_ARMS: dict[str, tuple[tuple[Point, Point, Point, str, float | None], ...]] = {  # shoulder, elbow, wrist, hand, turn
    "up": (((-180, -96), (-272, -74), (-246, -232), "open", -8.0), ((180, -96), (272, -74), (246, -232), "open", 8.0)),
    "chest": (((-180, -96), (-232, 6), (-104, 14), "rest", 98.0), ((180, -96), (226, -14), (70, -56), "fist", -52.0)),
    "point": (((-180, -96), (-170, -2), (-272, -52), "point", -80.0), ((180, -96), (232, 6), (104, 14), "rest", -98.0)),
    "phone": (((-180, -96), (-222, -2), (-66, -22), "fist", 84.0), ((180, -96), (222, -2), (66, -22), "fist", -84.0)),
    "rest": (((-180, -96), (-232, 6), (-104, 14), "rest", 98.0), ((180, -96), (232, 6), (104, 14), "rest", -98.0)),
}


def _gus_arms(cv: Canvas, parent, spans: Mapping[str, Spans]) -> None:
    for state, when in spans.items():
        g = cv.group(parent, cv.uid("g"), opacity=0.0)
        cv.gate(g, when)
        if state == "phone":
            _phone(cv, g, 0.0, -82.0)
        for i, (s, e, w, hand, turn) in enumerate(GUS_ARMS[state]):
            size = 1.12 if state in ("up", "point") else 0.98
            _arm(cv, g, s, e, w, "#f2811a", ORANGE_TONE, CREAM, hand, GUS_SKIN, GUS_TONE, 61.0 + i * 3, size, turn)


_DRESS = {"vera": (TEAL, TEAL_TONE, VERA_SKIN, VERA_TONE), "gus": (ORANGE, ORANGE_TONE, GUS_SKIN, GUS_TONE)}


def _bones(cv: Canvas, parent, build: news_arms.Build, side: float, keys: Mapping[str, news_arms.Keys]):
    """The two lengths of an arm as nested groups, each turning on its joint: one such pair per layer of the arm."""
    upper = cv.group(parent, cv.uid("arm"), x=build.shoulder[0] * side, y=build.shoulder[1], anchorX=0.0, anchorY=0.0)
    cv.keys(upper, "rotation", keys["upper"], hold=False, kind="sine-in-out", local=False)
    fore = cv.group(upper, cv.uid("forearm"), x=0.0, y=-build.upper, anchorX=0.0, anchorY=0.0)
    cv.keys(fore, "rotation", keys["bend"], hold=False, kind="sine-in-out", local=False)
    return upper, fore


def _strip(cv: Canvas, parent, near: float, far: float, length: float, edge: float, tone: str, spans: Spans) -> None:
    """The shade along the ``edge`` of a length of sleeve, while ``spans`` last."""
    g = cv.group(parent, cv.uid("g"), opacity=0.0, scaleX=edge)
    cv.gate(g, spans)
    flat(cv, g, brush.outline(news_arms.shade_strip(near, far, length), steps=3), tone)


def _arm_on_rig(
    cv: Canvas,
    parent,
    who: str,
    side: float,
    acts: Sequence[tuple[float, Pose]],
    spans: Mapping[str, Spans],
    seed: float,
) -> None:
    """One arm of version 5: the hand under the sleeve, then all the sleeve's ink, then all its fill, so that a line
    runs around the whole arm with none at the elbow, where the two lengths are one sleeve, or at the shoulder."""
    build = news_arms.BUILDS[who]
    sleeve, tone, skin, shadow = _DRESS[who]
    keys = news_arms.keys_of(who, side, acts)
    holds = {state: hold for state, hold in news_arms.holds(who, side).items() if state in spans}
    _, fore = _bones(cv, parent, build, side, keys)
    wrist = cv.group(fore, cv.uid("wrist"), x=0.0, y=-build.fore - CUFF, anchorX=0.0, anchorY=0.0)
    cv.keys(wrist, "rotation", keys["palm"], hold=False, kind="sine-in-out", local=False)
    for hand in sorted({hold.hand for hold in holds.values()}):
        g = cv.group(wrist, cv.uid("g"), opacity=0.0)
        cv.gate(g, [span for state, hold in holds.items() if hold.hand == hand for span in spans[state]])
        _hand(cv, g, hand, (0.0, 0.0), 0.0, skin, shadow, build.hand, seed + 3)
    end = -build.fore
    _form(
        cv,
        fore,
        ((-24, end - CUFF), (24, end - CUFF), (25, end + 6), (-25, end + 6)),
        CREAM,
        None,
        seed + 2,
        5.0,
        amount=0.2,
    )
    upper, fore = _bones(cv, parent, build, side, keys)
    flat(cv, upper, brush.outline(news_arms.sleeve(build, SLEEVE_INK, -side), steps=3), PLUM_DEEP)
    flat(cv, fore, brush.outline(news_arms.forearm(build, SLEEVE_INK), steps=3), PLUM_DEEP)
    upper, _ = _bones(cv, parent, build, side, keys)
    _, fore = _bones(cv, parent, build, side, keys)  # its own chain, so that the forearm lies on the upper arm's shade
    for bone, drawn, near, far, length, turn in (
        (upper, news_arms.sleeve(build), build.root, build.elbow, build.upper, lambda h: h.upper),
        (fore, news_arms.forearm(build), build.elbow, build.wrist, build.fore, lambda h: h.upper + h.bend),
    ):
        flat(cv, bone, brush.outline(drawn, steps=3), sleeve)
        for edge in (-1.0, 1.0):
            when = [
                span
                for state, hold in holds.items()
                if news_arms.sheds(turn(hold), edge, LIGHT_FROM)
                for span in spans[state]
            ]
            if when:
                _strip(cv, bone, near, far, length, edge, tone, when)


def _arms_on_rig(cv: Canvas, parent, who: str, acts: Sequence[tuple[float, Pose]], spans: Mapping[str, Spans]) -> None:
    """Both arms of version 5, over what they hold: Vera's sheaf and Gus's phone, which rises with his hands."""
    if who == "vera":
        g = cv.group(parent, cv.uid("g"), opacity=0.0)
        cv.gate(g, [span for when in spans.values() for span in when])
        _sheaf(cv, g)
    elif "phone" in spans:
        g = cv.group(parent, cv.uid("g"), opacity=0.0)
        cv.gate(g, spans["phone"])
        rise = cv.group(g, cv.uid("g"))
        keys: list[tuple[float, float]] = [(0.0, PHONE_RISE)]
        for a, b in spans["phone"]:
            keys += [(a, PHONE_RISE), (a + news_arms.EASE, 0.0), (b - news_arms.EASE, 0.0), (b, PHONE_RISE)]
        cv.keys(rise, "y", keys, hold=False, kind="sine-in-out", local=False)
        _phone(cv, rise, 0.0, PHONE_HELD)
    for i, side in enumerate((-1.0, 1.0)):
        _arm_on_rig(cv, parent, who, side, acts, spans, (31.0 if who == "vera" else 61.0) + i * 6)


def skeleton(who: str, number: int, state: str) -> tuple[tuple[Point, Point, Point], ...]:
    """Shoulder, elbow and wrist of both arms of version ``number`` holding ``state``, frame left first."""
    if number >= 5:
        build = news_arms.BUILDS[who]
        pair = news_arms.REACHES[who][state]
        return tuple(
            ((build.shoulder[0] * side, build.shoulder[1]), news_arms.elbow_of(build, side, reach), reach.wrist)
            for side, reach in zip((-1.0, 1.0), pair, strict=True)
        )
    if who == "gus":
        return tuple((s, e, w) for s, e, w, _, _ in GUS_ARMS[state])
    (s, e, w) = VERA_ARM
    return tuple(((side * s[0], s[1]), (side * e[0], e[1]), (side * w[0], w[1])) for side in (-1.0, 1.0))


CURLS: tuple[tuple[float, float, float], ...] = (  # the fringe: x, y, radius
    (-92, -262, 34),
    (-48, -286, 38),
    (4, -294, 40),
    (56, -286, 36),
    (98, -258, 30),
)


GUS_CLOUD: tuple[Point, ...] = (
    (-146, -128),
    (-172, -160),
    (-160, -204),
    (-180, -246),
    (-146, -286),
    (-126, -322),
    (-74, -330),
    (-40, -352),
    (14, -344),
    (58, -354),
    (100, -328),
    (146, -316),
    (160, -280),
    (182, -240),
    (164, -200),
    (176, -160),
    (146, -128),
    (0, -160),
)
GUS_HEAD: tuple[Point, ...] = (
    (-120, -178),
    (-114, -116),
    (-84, -60),
    (-38, -40),
    (2, -32),
    (44, -40),
    (86, -62),
    (114, -116),
    (120, -178),
    (106, -240),
    (58, -278),
    (0, -284),
    (-58, -278),
    (-106, -240),
)


def _gus_head(
    cv: Canvas, g, eyes: Track, mouth: Track, start: float, end: float, motion: Motion = None, face: Face = GUS_INKED
) -> None:
    _form(cv, g, GUS_CLOUD, HAIR, HAIR_TONE, 81.0, depth=26.0, amount=1.0)
    for side, x in ((-1.0, -122.0), (1.0, 122.0)):
        _form(
            cv,
            g,
            ((x + side * 18, -176), (x + side * 32, -146), (x + side * 22, -104), (x, -98), (x - side * 8, -140)),
            GUS_SKIN,
            GUS_TONE,
            82.0 + side,
            6.5,
            8.0,
        )
        _line(cv, g, ((x + side * 18, -156), (x + side * 8, -130), (x + side * 12, -116)), GUS_DEEP, 3.8)
    _form(cv, g, GUS_HEAD, GUS_SKIN, GUS_TONE, 85.0, depth=26.0, amount=0.5)
    under = _slides(cv, g, motion)
    cv.path(under, "M -100 -112 Q -76 -88 -50 -102 Q -76 -128 -100 -112 Z", "#f0805a40", cv.clear, 0)
    cv.path(under, "M 100 -112 Q 76 -88 50 -102 Q 76 -128 100 -112 Z", "#f0805a40", cv.clear, 0)
    for x, y, r in (
        (-68, -122, 4.6),
        (-84, -112, 3.8),
        (-58, -106, 4.0),
        (-74, -102, 3.2),
        (68, -122, 4.4),
        (84, -112, 4.0),
        (58, -106, 3.8),
        (76, -100, 3.2),
        (-12, -130, 3.0),
        (14, -132, 3.0),
    ):
        _oval(cv, under, x, y, r, r, "#c9875a")
    _line(cv, under, ((-10, -156), (-26, -118), (-10, -98), (24, -106)), GUS_DEEP, 6.5)
    for cx, cy, cr in CURLS:
        _inked_oval(cv, g, cx, cy, cr, cr * 0.9, HAIR, 6.0)
        _oval(cv, g, cx + cr * 0.3, cy + cr * 0.4, cr * 0.62, cr * 0.42, HAIR_TONE)
        _line(
            cv,
            g,
            (
                (cx - cr * 0.5, cy - cr * 0.1),
                (cx - cr * 0.1, cy - cr * 0.6),
                (cx + cr * 0.5, cy - cr * 0.2),
                (cx + cr * 0.1, cy + cr * 0.2),
            ),
            HAIR_SHINE,
            5.0,
            FUR,
        )
    for x, y in ((-140, -240), (-108, -306), (-40, -326), (40, -330), (112, -304), (150, -236)):
        _line(cv, g, ((x - 14, y + 8), (x, y - 12), (x + 16, y - 2), (x + 4, y + 10)), HAIR_SHINE, 5.0, FUR)
    over = _slides(cv, g, motion)
    _eyes(cv, over, face, eyes, start, end)
    _mouths(cv, over, face, mouth, start, end)


def perform(
    cv: Canvas,
    parent,
    who: str,
    x: float,
    acts: Sequence[tuple[float, Pose]],
    start: float,
    end: float,
    mouths: Track = (),
    id: str | None = None,
    scale: float = 1.0,
    over=None,
    motion: Motion = None,
    looks: Sequence[tuple[float, float]] = (),
    number: int = 2,
):
    """``who`` at the desk from ``start`` to ``end``, centred on frame ``x``: ``acts`` is the :class:`Pose` from each
    second on and ``mouths`` the take's visemes. The arms and hands go in ``over``, the plane in front of the desk,
    when there is one, so a forearm lies across the desk's top and a head stays behind its edge. ``motion`` puts the
    head on its rig (:func:`_on_rig`) and ``looks`` is when its eyes go to the other anchor with it. ``number`` is the
    version drawn."""
    _span(start, end, "an anchor")
    if who not in ("vera", "gus"):
        raise NewsKitError(f"the desk seats vera and gus, not {who!r}")
    if not acts or acts[0][0] > start:
        raise NewsKitError(f"an anchor needs a pose from {start} s, got {acts[:1]!r}")
    size = scale if scale else 1.0
    g = cv.group(parent, id or cv.uid("anchor"), x=x, y=DESK_Y, scaleX=size, scaleY=size)
    hands = g if over is None else cv.group(over, cv.uid("hands"), x=x, y=DESK_Y, scaleX=size, scaleY=size)
    arms = _spans([(at, pose.arms) for at, pose in acts], start, end)
    eyes = eye_track(side_eyes(acts, looks, end), end, 4.3 if who == "vera" else 2.4, 1.7 if who == "vera" else 0.9)
    mouth = mouth_track(acts, mouths, end)
    if motion is not None:
        _on_rig(cv, g, hands, who, acts, arms, eyes, mouth, start, end, motion, inked(who, number), number)
        return g
    neck = dict(x=0.0, y=NECK_Y, anchorX=0.0, anchorY=CHIN_Y)  # the head turns on the neck, over the collar
    if who == "vera":
        _vera_body(cv, g, number)
        head = cv.group(g, cv.uid("g"), **neck)
        _vera_head(cv, head, eyes, mouth, start, end, None, inked(who, number))
    else:
        _gus_body(cv, g, number)
        head = cv.group(g, cv.uid("g"), **neck)
        _gus_head(cv, head, eyes, mouth, start, end, None, inked(who, number))
    _arms_of(cv, hands, who, acts, arms, number)
    cv.keys(head, "rotation", _head_keys(acts), hold=False, kind="sine-in-out", local=False)
    return g


def _arms_of(
    cv: Canvas, hands, who: str, acts: Sequence[tuple[float, Pose]], arms: Mapping[str, Spans], number: int
) -> None:
    """The arms of version ``number``: from version 5 on their rig, before it a drawing for each pose."""
    if number >= 5:
        _arms_on_rig(cv, hands, who, acts, arms)
    else:
        (_vera_arms if who == "vera" else _gus_arms)(cv, hands, arms)


def side_eyes(
    acts: Sequence[tuple[float, Pose]], looks: Sequence[tuple[float, float]], end: float
) -> Sequence[tuple[float, Pose]]:
    """``acts`` with level eyes on the other anchor through ``looks``: any other eyes are the beat's, and stay."""
    if not looks:
        return acts
    times = sorted({*(at for at, _ in acts), *(t for span in looks for t in span if acts[0][0] < t < end)})
    rows = []
    for t in times:
        pose = next(p for at, p in reversed(acts) if at <= t)
        looking = any(on <= t < off for on, off in looks)
        rows.append((t, replace(pose, eyes="side") if looking and pose.eyes == "level" else pose))
    return rows


def _on_rig(
    cv: Canvas,
    g,
    hands,
    who: str,
    acts: Sequence[tuple[float, Pose]],
    arms: Mapping[str, Spans],
    eyes: Track,
    mouth: Track,
    start: float,
    end: float,
    motion: tuple[AnchorRig, HeadPlan],
    face: Face,
    number: int = 2,
) -> None:
    """An anchor whose head moves. The nesting is :mod:`srstudio.toon_head`'s, one kind of motion a group, outermost
    first: over the body, which does not move, the beat's tilt, the plan's turn and nod, with all the hair and the
    ears, and the face that slides over those."""
    rig, plan = motion
    pivot = dict(x=0.0, y=CHIN_Y, anchorX=0.0, anchorY=CHIN_Y)  # a group that turns on the point the head sits on
    (_vera_body if who == "vera" else _gus_body)(cv, g, number)
    tilt = cv.group(g, cv.uid("head-tilt"), x=0.0, y=NECK_Y, anchorX=0.0, anchorY=CHIN_Y)
    cv.keys(tilt, "rotation", _head_keys(acts), hold=False, kind="sine-in-out", local=False)
    turn = cv.group(tilt, cv.uid("head-turn"), **pivot)
    toon_head._animate(cv, turn, "rotation", plan.turn)
    nod = cv.group(turn, cv.uid("head-nod"), **pivot)
    toon_head._animate(cv, nod, "rotation", plan.roll)
    toon_head._animate(cv, nod, "y", plan.nod, 1.0, CHIN_Y)
    (_vera_head if who == "vera" else _gus_head)(cv, nod, eyes, mouth, start, end, motion, face)
    _arms_of(cv, hands, who, acts, arms, number)


def _rig_of(body: tuple[float, float], skin: tuple[Point, ...], hair: tuple[Point, ...], wide: float, **move) -> dict:
    x, y = body
    return dict(
        neck=(x, y),
        head=tuple((px, py + y - CHIN_Y) for px, py in skin),
        cover=((-wide, _NECK_TOP), (0.0, _NECK_TOP), (wide, _NECK_TOP)),
        skin=skin,
        outline=hair,
        **move,
    )


_NECK_TOP = -262.0
VERA_RIG = AnchorRig(
    who="vera",
    style=VERA_MOTION,
    toward=VERA_FACE.toward,
    lag=0.15,
    back=0.45,
    **_rig_of((0.0, NECK_Y), VERA_HEAD, VERA_BACK, 42.0),
)
GUS_RIG = AnchorRig(
    who="gus",
    style=GUS_MOTION,
    toward=GUS_FACE.toward,
    lag=0.4,
    back=0.3,
    **_rig_of((0.0, NECK_Y), GUS_HEAD, GUS_CLOUD, 48.0),
)
VERA_RIG_3 = replace(VERA_RIG, style=VERA_MOTION_3, face_slide=0.6)
GUS_RIG_3 = replace(GUS_RIG, style=GUS_MOTION_3, face_slide=0.2)  # his nod is big: the face stays by the skull on it
RIGS: Mapping[str, AnchorRig] = MappingProxyType(
    {
        "news-vera@2": VERA_RIG,
        "news-gus@2": GUS_RIG,
        "news-vera@3": VERA_RIG_3,
        "news-gus@3": GUS_RIG_3,
        "news-vera@4": VERA_RIG_3,
        "news-gus@4": GUS_RIG_3,
        "news-vera@5": VERA_RIG_3,
        "news-gus@5": GUS_RIG_3,
    }
)


def mouths_shown(seconds: float, number: int) -> Track:
    """The mouths a specimen of version ``number`` draws: from version 4, whose mouths are its change, every one."""
    states = news_kit.EXPRESSIONS if number >= 4 else ("closed", "open")
    return tuple((seconds * n / len(states), state) for n, state in enumerate(states))


def rig_specimen(cv: Canvas, who: str, seconds: float, number: int = 2) -> None:
    """Every eye, arm and mouth state of ``who`` on the rig of version ``number``, the head at each corner of what it
    can reach, and the face at the end of its slide: what the rig's digest holds."""
    rig = RIGS[f"news-{who}@{number}"]
    count = len(news_kit.ARMS)
    acts = tuple(
        (seconds * n / count, Pose(eyes, "talk", arms))
        for n, (eyes, arms) in enumerate(zip(news_kit.EYES, news_kit.ARMS, strict=False))
    )
    slide = head_motion.limit(rig.style, "face_x")
    plan = replace(toon_head.reach(rig), face_x=Channel(((0.0, -slide), (seconds, slide))))
    perform(
        cv, cv.comp, who, 540.0, acts, 0.0, seconds, mouths_shown(seconds, number), motion=(rig, plan), number=number
    )


@register(
    "character", "news-vera@2", summary="Vera Stillman, inked: a silver bob with a parting, half-moon glasses, a neck"
)
def vera(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Vera at the desk in one pose."""
    return perform(cv, parent, "vera", x, ((start, pose or Pose()),), start, end, mouths)


@register("character", "news-gus@2", summary="Gus Bellows, inked: curls, a pulled tie, sleeves with elbows, real hands")
def gus(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Gus at the desk in one pose."""
    return perform(cv, parent, "gus", x, ((start, pose or Pose()),), start, end, mouths)


@register("character", "news-vera@3", summary="Vera on the rig whose face stays on her skin: the same drawing as @2")
def vera_3(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Vera at the desk in one pose."""
    return perform(cv, parent, "vera", x, ((start, pose or Pose()),), start, end, mouths)


@register("character", "news-gus@3", summary="Gus on the rig whose face stays on his skin: the same drawing as @2")
def gus_3(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Gus at the desk in one pose."""
    return perform(cv, parent, "gus", x, ((start, pose or Pose()),), start, end, mouths)


@register("character", "news-vera@4", summary="Vera with the shout inside her chin, the rig of @3")
def vera_4(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Vera at the desk in one pose."""
    return perform(cv, parent, "vera", x, ((start, pose or Pose()),), start, end, mouths, number=4)


@register("character", "news-gus@4", summary="Gus with the shout inside his chin and his mouths clear of his nose")
def gus_4(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Gus at the desk in one pose."""
    return perform(cv, parent, "gus", x, ((start, pose or Pose()),), start, end, mouths, number=4)


@register("character", "news-vera@5", summary="Vera with a sloped shoulder that her sleeve grows out of")
def vera_5(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Vera at the desk in one pose."""
    return perform(cv, parent, "vera", x, ((start, pose or Pose()),), start, end, mouths, number=5)


@register("character", "news-gus@5", summary="Gus with arms of one length that travel between their poses")
def gus_5(
    cv: Canvas,
    parent,
    pose: Pose | None = None,
    x: float = 540.0,
    start: float = 0.0,
    end: float = 2.0,
    mouths: Track = (),
):
    """Gus at the desk in one pose."""
    return perform(cv, parent, "gus", x, ((start, pose or Pose()),), start, end, mouths, number=5)


def _phone_down(cv: Canvas, parent, x: float, spans: Spans) -> None:
    """Gus's phone lying face down on the desk's top, in the desk's perspective, on its own shadow."""
    g = cv.group(parent, cv.uid("g"), opacity=0.0)
    cv.gate(g, spans)
    y = DESK_Y + 8.0
    cv.path(
        g, f"M {x - 92} {y + 42} L {x - 58} {y + 6} L {x + 66} {y + 6} L {x + 96} {y + 42} Z", "#160a3080", cv.clear, 0
    )
    _form(
        cv,
        g,
        ((x - 56, y - 2), (x + 56, y - 2), (x + 80, y + 36), (x - 80, y + 36)),
        PLUM,
        "#160a30",
        75.0,
        6.5,
        8.0,
        0.1,
    )
    _oval(cv, g, x - 34, y + 12, 11, 6, "#6f8fd0")
    cv.path(
        g, f"M {x + 2} {y + 2} L {x + 22} {y + 2} L {x + 18} {y + 32} L {x - 8} {y + 32} Z", "#ffffff14", cv.clear, 0
    )


def _seat(cv: Canvas, front, who: str, x: float, scale: float) -> None:
    """What an anchor puts on the desk's top: their colour in its polish and their shadow."""
    wide = 520.0 * scale
    left = x - wide / 2
    tint = {"vera": "#16857f44", "gus": "#ff8a1f44"}[who]
    look.pool(cv, front, f"news2-polish-{who}", tint, left, DESK_Y + 6, wide, 50)
    shadow = cv.group(front, f"news-contact-{who}-{cv.uid('c')}")
    look.pool(cv, shadow, "news2-contact", "#160a30b0", left + 20, DESK_Y + 26 * min(scale, 1.2), wide - 40, 40)


def stage(
    acts: Sequence[Act], end_scan: float = 30.0, heads: bool = True, version: int | None = None
) -> Callable[[Any], None]:
    """The dress of every shot: the room, then both anchors in the two-shot (``desk``), one close (``vera``, ``gus``)
    or nobody (``phone``, which :func:`phone_insert` fills), each with their forearms over the desk. ``acts`` runs
    parallel to the sketch's beats. Their heads move on the takes (:mod:`srstudio.news_head`), on a rig whose record
    must be approved; ``heads=False`` draws them still. ``version`` is the rig: by default each anchor's latest approved
    version, and a reel delivered on an older one names it, so a rebuild draws what went out."""

    def dress(shot: Any) -> None:
        if len(acts) != len(shot.beats):
            raise NewsKitError(f"{len(acts)} acts for {len(shot.beats)} beats")
        cv, app = shot.cv, shot.app
        studio(cv, shot.back, end_scan)
        holds = news_head.holds_of(acts, shot.beats) if any(act.holds for act in acts) else ()
        seats = {
            "desk": tuple((who, x, 1.0) for who, x in TWO_SHOT.items()),
            "vera": (("vera", *FRAMING["vera"]),),
            "gus": (("gus", *FRAMING["gus"]),),
        }.get(app.who, ())
        for who, x, scale in seats:
            rows = [(b.start, getattr(act, who)) for b, act in zip(shot.beats, acts, strict=True)]
            held = [row for row in rows if row[0] <= app.start][-1:]
            during = [
                (max(at, app.start), pose) for at, pose in [*held, *(r for r in rows if app.start < r[0] < app.end)]
            ]
            look.pool(cv, shot.back, "news2-behind-anchor", "#0c052070", x - 330 * scale, 420, 660 * scale, 760)
            _seat(cv, shot.front, who, x, scale)
            motion: Motion = None
            looks: list[tuple[float, float]] = []
            number = parts.latest(f"news-{who}").number if version is None else version
            if heads:
                rig = RIGS[f"news-{who}@{number}"]
                if not news_head.approved(who, number):
                    raise NewsKitError(
                        f"news-{who}@{number}'s head rig is not approved: stage with heads=False until it is"
                    )
                said = shot.said()
                motion = (rig, news_head.plan_of(who, rig, said, holds, shot.end).during(app.start, app.end))
                looks = [(on, off) for on, off, _ in news_head.facing(who, rig, said, holds, shot.end)]
            perform(
                cv,
                shot.back,
                who,
                x,
                during,
                app.start,
                app.end,
                shot.mouths.get(who, ()),
                scale=scale,
                over=shot.front,
                motion=motion,
                looks=looks,
                number=number,
            )
            if who == "gus":
                down = _spans([(at, pose.arms) for at, pose in during], app.start, app.end).get("rest")
                if down:
                    _phone_down(cv, shot.front, x, down)

    return dress


# -- the graphics ------------------------------------------------------------------------------------------------------
def _card(cv: Canvas, parent, x: float, y: float, w: float, h: float, fill: str, radius: float = CHIP) -> None:
    """A panel of the show: its one corner on its one shadow."""
    cv.rect(parent, x + DROP[0], y + DROP[1], w, h, SHADOW, radius=radius)
    cv.rect(parent, x, y, w, h, fill, radius=radius)


def _chip(cv: Canvas, parent, x: float, w: float, fill: str, stroke: str | None = None) -> None:
    """A chip of the top row: every one the same height on the same line."""
    cv.rect(parent, x + DROP[0], BUG_Y + DROP[1], w, BUG_H, SHADOW, radius=CHIP)
    cv.rect(parent, x, BUG_Y, w, BUG_H, fill, stroke, 3.0 if stroke else 0.0, radius=CHIP)


@register("graphic", "news-bug@2", summary="The show's name in the corner, on the top row's chip")
def bug(cv: Canvas, parent, start: float, end: float, measure: Measure, id: str = "news-bug") -> None:
    """The show's name in a tangerine chip, top left."""
    _span(start, end, "the bug")
    g = cv.group(parent, id, start=start, end=end)
    wide = measure(SHOW, 40.0) + 36.0
    _chip(cv, g, TEXT_LEFT, wide, TANGERINE)
    _text(cv, g, SHOW, TEXT_LEFT, BUG_Y, wide, BUG_H, 40, PLUM_DEEP, "center")


def _tag_wide(measure: Measure) -> float:
    return measure("PARODY", 40.0) + 44.0


@register("graphic", "news-parody-tag@2", summary="The PARODY tag on the top row's chip, on a whole fictional reel")
def parody_tag(cv: Canvas, parent, start: float, end: float, measure: Measure, id: str = "news-parody-tag") -> None:
    """PARODY in butter on plum, top right, opposite the show's name."""
    _span(start, end, "the PARODY tag")
    g = cv.group(parent, id, start=start, end=end)
    wide = _tag_wide(measure)
    x = TEXT_RIGHT - wide
    _chip(cv, g, x, wide, PLUM_DEEP, BUTTER)
    _text(cv, g, "PARODY", x, BUG_Y, wide, BUG_H, 40, BUTTER, "center")


MISSING_X, MISSING_Y, MISSING_W, MISSING_H = 794.0, 486.0, 236.0, 296.0  # beside the close-up's head, under the top row
MISSING_HEAD = 66.0
MISSING_SIZE = 36.0
LID_FILL, LID_RIM = "#8fd4dc", "#5fb3c0"
LID = ((-78, -34), (-62, -48), (62, -48), (78, -34), (78, 34), (62, 48), (-62, 48), (-78, 34))


@register("graphic", "news-missing-card", summary="A missing-person flyer for an object: its picture and its name")
def missing_card(
    cv: Canvas, parent, label: str, start: float, end: float, measure: Measure, id: str = "news-missing-card"
) -> None:
    """A flyer beside a close-up's head: MISSING, a storage lid, and ``label`` under it; it refuses a label too wide."""
    _span(start, end, "the missing card")
    if not label.strip() or measure(label, MISSING_SIZE) > MISSING_W - 24.0:
        raise NewsKitError(f"the missing card's label {label!r} must be some words that fit")
    g = cv.group(parent, id, start=start, end=end)
    x, y = MISSING_X, MISSING_Y
    cv.rect(g, x + DROP[0], y + DROP[1], MISSING_W, MISSING_H, SHADOW, radius=CHIP)
    cv.rect(g, x, y, MISSING_W, MISSING_H, CREAM, PLUM_DEEP, 4.0, radius=CHIP)
    cv.rect(g, x, y, MISSING_W, MISSING_HEAD, PLUM_DEEP, radius=CHIP)
    _text(cv, g, "MISSING", x, y + 6.0, MISSING_W, MISSING_HEAD - 12.0, 46, BUTTER, "center")
    lid = cv.group(g, f"{id}-lid", x=x + MISSING_W / 2, y=y + 150.0)
    _form(cv, lid, LID, LID_RIM, None, 3.0, 5.0, depth=0.0, amount=0.2)
    _form(cv, lid, tuple((a * 0.8, b * 0.72) for a, b in LID), LID_FILL, None, 5.0, 2.5, depth=0.0, amount=0.2)
    _form(cv, lid, ((64, -56), (98, -66), (104, -48), (76, -38)), LID_RIM, None, 7.0, 4.0, depth=0.0, amount=0.2)
    _text(cv, g, label, x, y + MISSING_H - 62.0, MISSING_W, 48.0, MISSING_SIZE, PLUM_DEEP, "center")


DOOR_WALL = "#7f6a9e"
DOOR_FILL, DOOR_SHADE = "#c98a55", "#a56c3f"
DOOR_TOP, DOOR_FOOT = 84.0, 226.0  # the picture's band inside the card, down from its top
DOOR_LEFT, DOOR_RIGHT = -58.0, 58.0  # the door frame, either side of the card's centre


def _polygon(cv: Canvas, parent, points: Sequence[Point], fill: str, weight: float) -> None:
    """A straight-edged shape: a door keeps its corners, which :func:`_form`'s brushed contour would round off."""
    d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in points) + " Z"
    cv.path(parent, d, fill, PLUM_DEEP, weight)


def _door(cv: Canvas, parent, right: float) -> None:
    """A door hung on the frame's left and swung to ``right``, its free edge foreshortened, two panels and a knob."""
    t, f = DOOR_TOP, DOOR_FOOT
    lean = (DOOR_RIGHT - right) * 0.16

    def at(u: float, v: float) -> Point:  # across the door and down it, each 0..1
        return DOOR_LEFT + u * (right - DOOR_LEFT), t + v * (f - t) + (0.5 - v) * 2.0 * u * lean

    _polygon(cv, parent, (at(0, 0), at(1, 0), at(1, 1), at(0, 1)), DOOR_FILL, 3.5)
    for top, foot in ((0.1, 0.44), (0.54, 0.9)):
        _polygon(cv, parent, (at(0.2, top), at(0.8, top), at(0.8, foot), at(0.2, foot)), DOOR_SHADE, 2.0)
    knob = at(0.9, 0.5)
    _inked_oval(cv, parent, knob[0], knob[1], 5.5, 5.5, BUTTER, 2.5)


@register("graphic", "news-live-door", summary="A live shot of a door nothing happens at, which can slam shut")
def live_door(
    cv: Canvas,
    parent,
    label: str,
    start: float,
    end: float,
    measure: Measure,
    shut: float | None = None,
    id: str = "news-live-door",
) -> None:
    """A live inset beside a close-up's head: LIVE, a door ajar on a lit room, and ``label`` under it. With ``shut``,
    the door is closed from that instant and the light gone; it refuses a label too wide or an instant off its span."""
    _span(start, end, "the live door")
    if not label.strip() or measure(label, MISSING_SIZE) > MISSING_W - 24.0:
        raise NewsKitError(f"the live door's label {label!r} must be some words that fit")
    if shut is not None and not start < shut < end:
        raise NewsKitError(f"the live door shuts inside {start}..{end}, not at {shut}")
    g = cv.group(parent, id, start=start, end=end)
    x, y = MISSING_X, MISSING_Y
    cv.rect(g, x + DROP[0], y + DROP[1], MISSING_W, MISSING_H, SHADOW, radius=CHIP)
    cv.rect(g, x, y, MISSING_W, MISSING_H, CREAM, PLUM_DEEP, 4.0, radius=CHIP)
    cv.rect(g, x, y, MISSING_W, MISSING_HEAD, PLUM_DEEP, radius=CHIP)
    _text(cv, g, "LIVE", x, y + 6.0, MISSING_W, MISSING_HEAD - 12.0, 46, BUTTER, "center")
    cv.rect(g, x + 12.0, y + MISSING_HEAD + 8.0, MISSING_W - 24.0, DOOR_FOOT - MISSING_HEAD - 8.0, DOOR_WALL)
    centre = x + MISSING_W / 2
    room = cv.group(g, f"{id}-room", x=centre, y=y)
    frame = (DOOR_LEFT - 8.0, DOOR_TOP - 8.0, DOOR_RIGHT - DOOR_LEFT + 16.0, DOOR_FOOT - DOOR_TOP + 8.0)
    cv.rect(room, *frame, PLUM_DEEP)
    ajar = cv.group(room, f"{id}-ajar", start=start, end=end if shut is None else shut)
    cv.rect(ajar, DOOR_LEFT, DOOR_TOP, DOOR_RIGHT - DOOR_LEFT, DOOR_FOOT - DOOR_TOP, BUTTER)
    _door(cv, ajar, DOOR_RIGHT - 34.0)
    if shut is not None:
        _door(cv, cv.group(room, f"{id}-shut", start=shut, end=end), DOOR_RIGHT)
    _text(cv, g, label, x, y + MISSING_H - 62.0, MISSING_W, 48.0, MISSING_SIZE, PLUM_DEEP, "center")


@register(
    "graphic", "news-source-card@2", summary="A real story's source: a card with the headline, then a top-row chip"
)
def source_card(
    cv: Canvas,
    parent,
    source: Source,
    start: float,
    small: float,
    end: float,
    measure: Measure,
    id: str = "news-source-card",
    beside_tag: bool = False,
) -> None:
    """The card rises over the desk at ``start``, large enough to read the headline; at ``small`` it goes and the
    outlet and date stand on the top row until ``end``, at its right, or with ``beside_tag`` just left of the PARODY
    tag, which keeps the corner. The headline is the outlet's, word for word."""
    _span(start, small, "a source card")
    _span(small, end, "a source card's corner")
    x, wide, pad = TEXT_LEFT - 30.0, TEXT_WIDE + 60.0, 34.0
    lines, size = _fit(measure, source.headline, 60.0, 42.0, wide - 2 * pad, 3)
    tall = 2 * pad + 62.0 + 14.0 + math.ceil(len(lines) * size * 1.12) + 2
    g = cv.group(parent, id, start=start, end=small)
    box = cv.group(g, f"{id}-box", y=0.0)
    _card(cv, box, x, CARD_Y, wide, tall, CREAM)
    tag = measure(source.outlet, 46.0) + 40.0
    cv.rect(box, x + pad, CARD_Y + pad, tag, 62.0, MINT, radius=CHIP)
    _text(cv, box, source.outlet, x + pad, CARD_Y + pad, tag, 62.0, 46, PLUM_DEEP, "center")
    _text(cv, box, source.date, x + pad + tag + 20, CARD_Y + pad, wide - 2 * pad - tag - 20, 62.0, 42, PLUM)
    _text(
        cv,
        box,
        "\n".join(lines),
        x + pad,
        CARD_Y + pad + 76.0,
        wide - 2 * pad,
        math.ceil(len(lines) * size * 1.12) + 2,
        size,
        PLUM_DEEP,
    )
    cv.keys(box, "y", [(start, CARD_RISE), (start + SLIDE, 0.0)], kind="cubic-out", local=False)
    corner = cv.group(parent, f"{id}-small", start=small, end=end)
    label = f"{source.outlet}, {source.date}"
    w = measure(label, 34.0) + 32.0
    right = TEXT_RIGHT - _tag_wide(measure) - CREDIT_GAP if beside_tag else TEXT_RIGHT
    if beside_tag and right - w < TEXT_LEFT + measure(SHOW, 40.0) + 36.0 + CREDIT_GAP:
        raise NewsKitError(f"{label!r} does not fit on the top row between the show's name and the PARODY tag")
    _chip(cv, corner, right - w, w, CREAM)
    _text(cv, corner, label, right - w, BUG_Y, w, BUG_H, 34, PLUM_DEEP, "center")


@register("graphic", "news-lower-third@2", summary="The lower-third: a mint kicker over one line, flush on the ticker")
def lower_third(
    cv: Canvas,
    parent,
    kicker: str,
    headline: str,
    start: float,
    end: float,
    measure: Measure,
    id: str | None = None,
    y: float = LOWER_Y,
    slide: bool = True,
) -> None:
    """A kicker over one line of story, sliding in at ``start``: readable with the sound off."""
    _span(start, end, "a lower-third")
    lines, size = _fit(measure, check_copy(headline), 60.0, 38.0, TEXT_WIDE, 1)
    g = cv.group(parent, id or cv.uid("news-lower"), start=start, end=end, x=0.0)
    band = cv.grad("news2-lower", [(0, PLUM), (1, PLUM_DEEP)], (0, 0, 0, 1))
    cv.rect(g, -20, y, cv.width + 40, LOWER_H, band)
    words = cv.group(g, cv.uid("g"), start=start + SLIDE if slide else start, end=end)  # on arrival, never off frame
    wide = measure(check_copy(kicker), 34.0) + 28.0
    cv.rect(words, TEXT_LEFT, y + 12, wide, 42.0, MINT, radius=CHIP)
    _text(cv, words, kicker, TEXT_LEFT, y + 12, wide, 42.0, 34, PLUM_DEEP, "center")
    _text(cv, words, lines[0], TEXT_LEFT, y + 56.0, TEXT_WIDE, 68.0, size, CREAM)
    _slide(cv, g, start, moves=slide)


@register(
    "graphic", "news-banner@2", summary="The BREAKING banner, slimmer, flush on the lower-third, chevrons running"
)
def banner(
    cv: Canvas, parent, start: float, end: float, measure: Measure, id: str = "news-banner", slide: bool = True
) -> None:
    """BREAKING across the frame at the desk's edge, in from the left at ``start``, with chevrons running under it."""
    _span(start, end, "the banner")
    g = cv.group(parent, id, start=start, end=end, x=0.0)
    cv.rect(g, -20, BANNER_Y, cv.width + 40, BANNER_H, TANGERINE)
    run = cv.group(g, f"{id}-run", x=0.0, start=start + SLIDE if slide else start, end=end)  # the bar arrives first
    gap = 120.0
    for i in range(40):
        left = i * gap
        cv.path(
            run,
            f"M {left} {BANNER_Y} L {left + 44} {BANNER_Y} L {left + 80} {BANNER_Y + BANNER_H / 2} L {left + 44} "
            f"{BANNER_Y + BANNER_H} L {left} {BANNER_Y + BANNER_H} L {left + 36} {BANNER_Y + BANNER_H / 2} Z",
            TANGERINE_DARK,
            cv.clear,
            0,
        )
    span = end - start
    shift = gap * round(span * 2.0)
    cv.keys(run, "x", [(start, 0.0), (end, -min(shift, gap * 26))], hold=False, local=False)
    wide = measure("BREAKING", 54.0) + 52.0
    chip = cv.group(g, f"{id}-word", start=start + SLIDE if slide else start, end=end)
    cv.rect(chip, TEXT_LEFT, BANNER_Y + 7, wide, BANNER_H - 14, PLUM_DEEP, radius=CHIP)
    _text(cv, chip, "BREAKING", TEXT_LEFT, BANNER_Y + 7, wide, BANNER_H - 14, 54, BUTTER, "center")
    _slide(cv, g, start, moves=slide)


@register("graphic", "news-ticker@2", summary="The ticker, flush under the lower-third, its tab cut to a chevron")
def ticker(
    cv: Canvas, parent, items: Sequence[str], start: float, end: float, measure: Measure, id: str = "news-ticker"
) -> None:
    """``items`` running right to left from ``start`` to ``end`` at the kit's speed, repeated as often as the time
    asks, so it never runs out."""
    _span(start, end, "the ticker")
    if not items or not all(isinstance(item, str) and item.strip() for item in items):
        raise NewsKitError("a ticker needs at least one item of words")
    size = 40.0
    one = "   /   ".join(check_copy(item) for item in items) + "   /   "
    needed = cv.width + TICKER_SPEED * (end - start)
    many = one * max(1, math.ceil(needed / measure(one, size)))
    g = cv.group(parent, id, start=start, end=end)
    cv.rect(g, -20, TICKER_Y + 6, cv.width + 40, TICKER_H, SHADOW)
    cv.rect(g, -20, TICKER_Y, cv.width + 40, TICKER_H, CREAM)
    run = cv.group(g, f"{id}-run", x=cv.width)
    wide = math.ceil(measure(many, size)) + 40
    _text(cv, run, many, 0, TICKER_Y, wide, TICKER_H, size, PLUM_DEEP)
    cv.keys(run, "x", [(start, 170.0), (end, 170.0 - TICKER_SPEED * (end - start))], hold=False, local=False)
    edge = 150.0
    cv.path(
        g,
        f"M -20 {TICKER_Y} L {edge} {TICKER_Y} L {edge + 24} {TICKER_Y + TICKER_H / 2} L {edge} {TICKER_Y + TICKER_H} "
        f"L -20 {TICKER_Y + TICKER_H} Z",
        TANGERINE,
        cv.clear,
        0,
    )
    _text(cv, g, "NEWS", 20, TICKER_Y, 130, TICKER_H, 40, PLUM_DEEP, "center")


@register("graphic", "news-captions@2", summary="The show's dialogue captions on the show's panel, a colour per anchor")
def captions(
    cv: Canvas,
    parent,
    lines: Sequence[toon.Line],
    measure: Measure,
    tints: Mapping[str, str] | None = None,
    id: str = "news-captions",
):
    """One panel per cue over the faces, in the fill ``tints`` gives its speaker: a cue that needs a third line stops
    the build. Returns the group that holds them, which a build keeps off the cover."""
    cv.require_font("the show letters its captions in its font", NewsKitError)
    track = cv.group(parent, id)
    for line in lines:
        wrapped = _wrap(measure, line.text, CAPTION_SIZE, TEXT_WIDE - 2 * CAPTION_PAD, 2)
        if not wrapped:
            raise NewsKitError(f"a caption takes two lines at most: {line.text!r}")
        fill = (tints or {}).get(line.speaker, CREAM)
        g = cv.group(track, cv.uid("g"), start=line.start, end=line.end)
        wide = max(measure(row, CAPTION_SIZE) for row in wrapped) + 2 * CAPTION_PAD + 12
        high = len(wrapped) * CAPTION_SIZE * CAPTION_LEADING + CAPTION_PAD
        x = round((TEXT_LEFT + TEXT_RIGHT) / 2 - wide / 2, 2)
        _card(cv, g, x, CAPTION_TOP, wide, high, fill)
        cv.text(
            g,
            cv.uid("caption"),
            "\n".join(wrapped),
            x,
            CAPTION_TOP,
            round(wide),
            round(high),
            CAPTION_SIZE,
            color=PLUM_DEEP,
            wrap="none",
        )
    return track


def _handset(cv: Canvas, g, title: str) -> None:
    """The phone over the dimmed room: case, buttons, screen and a header carrying ``title``."""
    x, y, wide, tall = PHONE_X, PHONE_Y, PHONE_W, PHONE_H
    cv.rect(g, 0, 0, cv.width, TICKER_Y, "#160a3088")
    case = cv.grad("news2-case", [(0, "#4b3a78"), (1, "#1a0e36")], (0, 0, 1, 1))
    cv.rect(g, x - 12, y - 8, wide + 48, tall + 48, SHADOW, radius=60.0)
    cv.rect(g, x - 20, y - 20, wide + 40, tall + 40, case, PLUM_DEEP, 5.0, radius=60.0)
    cv.rect(g, x - 26, y + 150, 8, 96, "#2a1d44", radius=4.0)
    cv.rect(g, x + wide + 18, y + 120, 8, 150, "#2a1d44", radius=4.0)
    cv.rect(g, x, y, wide, tall, "#f7f1ff", radius=42.0)
    head = cv.grad("news2-chat", [(0, MINT), (1, "#2cc9a3")], (0, 0, 0, 1))
    cv.rect(g, x, y, wide, 108.0, head, radius=42.0)
    cv.rect(g, x, y + 60.0, wide, 48.0, head)
    cv.rect(g, x + wide / 2 - 70, y + 10, 140, 26, PLUM_DEEP, radius=13.0)
    _oval(cv, g, x + 58, y + 62, 28, 28, PLUM)
    _oval(cv, g, x + 58, y + 54, 10, 10, MINT)
    _oval(cv, g, x + 58, y + 76, 16, 10, MINT)
    _text(cv, g, title, x + 96, y + 34, wide - 192, 66.0, 48, PLUM_DEEP, "center")


@register(
    "graphic", "news-phone@2", summary="Gus's phone, a real handset: bezel, buttons, a status row, tailed bubbles"
)
def phone_insert(
    cv: Canvas,
    parent,
    chat: str,
    bubbles: Sequence[Bubble],
    start: float,
    end: float,
    measure: Measure,
    id: str = "news-phone",
) -> None:
    """A phone over the room from ``start`` to ``end``, the room dimmed behind it down to the ticker, the chat's name
    at its head and ``bubbles`` stacked from the top, each from its second on."""
    _span(start, end, "the phone")
    if not bubbles:
        raise NewsKitError("the phone needs a message to show")
    x, y, wide = PHONE_X, PHONE_Y, PHONE_W
    g = cv.group(parent, id, start=start, end=end)
    _handset(cv, g, chat)
    top, size, row = y + 124.0, 46.0, 104.0
    for i, bubble in enumerate(bubbles):
        at = max(bubble.at, start)
        if at >= end:
            raise NewsKitError(f"message {bubble.text!r} arrives after the phone has gone")
        check_copy(bubble.text)
        words = f"{bubble.clock}  {bubble.text}"
        w = measure(words, size) + 44.0
        if w > wide - 40.0:
            raise NewsKitError(f"message {bubble.text!r} is too wide for the phone")
        left = x + wide - w - 22.0 if bubble.out else x + 22.0
        box = cv.group(g, f"{id}-{i}", start=at, end=end)
        fill = MINT if bubble.out else BUTTER
        foot = top + i * row + row - 16.0
        tip = left + w + 12.0 if bubble.out else left - 12.0
        root = left + w - 26.0 if bubble.out else left + 26.0
        cv.path(box, f"M {root} {foot - 34} L {tip} {foot} L {root} {foot - 4} Z", fill, cv.clear, 0)
        cv.rect(box, left, top + i * row, w, row - 16.0, fill, radius=24.0)
        _text(cv, box, words, left, top + i * row, w, row - 16.0, size, PLUM_DEEP, "center")


@dataclass(frozen=True)
class Pin:
    """A labelled place on the route's map, in pixels of the phone's screen under its header."""

    x: float
    y: float
    label: str
    fill: str
    below: bool = False  # the label under the pin, when the route needs the room over it


def _inside(x: float, y: float) -> bool:
    return 0.0 <= x <= PHONE_W and 0.0 <= y <= MAP_H


def _sea(cv: Canvas, g, x: float, y: float) -> None:
    """The map under the route: sea, a coast top right and the swell's marks."""
    r, foot = 42.0, y + MAP_H
    sea = (
        f"M {x} {y} L {x + PHONE_W} {y} L {x + PHONE_W} {foot - r} Q {x + PHONE_W} {foot} {x + PHONE_W - r} {foot} "
        f"L {x + r} {foot} Q {x} {foot} {x} {foot - r} Z"
    )
    cv.path(g, sea, "#7cc6e0", "#00000000", 0.0)
    land = (
        (PHONE_W, 0.0),
        (PHONE_W, 330.0),
        (640.0, 300.0),
        (600.0, 220.0),
        (500.0, 190.0),
        (450.0, 90.0),
        (380.0, 60.0),
        (360.0, 0.0),
    )
    coast = " L ".join(f"{x + px} {y + py}" for px, py in land)
    cv.path(g, f"M {coast} Z", "#bfe6a8", "#3f7d5a", 5.0)
    for px, py in ((90, 120), (220, 240), (70, 360), (330, 330), (480, 560), (250, 520)):
        cv.path(g, f"M {x + px} {y + py} q 18 -12 36 0 t 36 0", None, "#ffffff66", 4.0)


def _marker(cv: Canvas, m, kind: str) -> None:
    """What moves along the route, on its own origin: a seabird from above, or a person's dot."""
    if kind == "bird":
        wings = "M -46 10 Q -22 -22 0 -6 Q 22 -22 46 10 Q 20 -2 0 12 Q -20 -2 -46 10 Z"
        cv.path(m, wings, "#ffffff", PLUM_DEEP, 5.0)
        cv.path(m, "M -6 -6 Q 0 -18 6 -6 L 0 16 Z", PLUM_DEEP, PLUM_DEEP, 2.0)
    else:
        _inked_oval(cv, m, 0.0, 0.0, 22.0, 22.0, TANGERINE, 5.0)


@register("graphic", "news-route", summary="A route on Gus's phone: a sea, a coast, a track that draws itself, pins")
def route_insert(
    cv: Canvas,
    parent,
    title: str,
    track: Sequence[Point],
    pins: Sequence[Pin],
    start: float,
    end: float,
    measure: Measure,
    direct: tuple[Point, Point] | None = None,
    marker: str = "bird",
    draw: float | None = None,
    id: str = "news-route",
) -> None:
    """A map on the phone from ``start`` to ``end``: ``track`` draws itself over ``draw`` seconds with ``marker`` at its
    head, ``direct`` is the dashed line it should have taken, and ``pins`` stay up throughout. Points are pixels of the
    screen under its header, so a track that leaves the screen stops the build, as a word the show keeps off it does."""
    _span(start, end, "the route")
    check_copy(title)
    if len(track) < 2:
        raise NewsKitError("a route needs a start and somewhere it went")
    if marker not in ("bird", "dot"):
        raise NewsKitError(f"a route's marker is 'bird' or 'dot', got {marker!r}")
    seconds = min(2.4, end - start) if draw is None else draw
    if not 0.0 < seconds <= end - start:
        raise NewsKitError(f"a route draws itself in {seconds} s, in a phone that is up for {end - start} s")
    size = 34.0
    for pin in pins:
        check_copy(pin.label)
        if not _inside(pin.x, pin.y):
            raise NewsKitError(f"pin {pin.label!r} is off the map")
        if measure(pin.label, size) + 36.0 > PHONE_W:
            raise NewsKitError(f"pin {pin.label!r} is too wide for the phone")
    if not all(_inside(px, py) for px, py in track):
        raise NewsKitError("a route that leaves the map cannot be shown")
    g = cv.group(parent, id, start=start, end=end)
    _handset(cv, g, title)
    x, y = PHONE_X, PHONE_Y + MAP_TOP
    _sea(cv, g, x, y)
    if direct is not None:
        (ax, ay), (bx, by) = direct
        line = cv.group(g, f"{id}-direct")
        steps = max(int(math.hypot(bx - ax, by - ay) / 34.0), 1)
        for i in range(steps):
            f, h = i / steps, (i + 0.55) / steps
            cv.path(
                line,
                f"M {x + ax + (bx - ax) * f} {y + ay + (by - ay) * f} "
                f"L {x + ax + (bx - ax) * h} {y + ay + (by - ay) * h}",
                None,
                CREAM,
                7.0,
            )
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(track, track[1:], strict=False)]
    whole = sum(lengths)
    if whole <= 0.0:
        raise NewsKitError("a route has to go somewhere")
    times, at = [start], start
    for piece in lengths:
        at += seconds * piece / whole
        times.append(at)
    for i, (a, b) in enumerate(zip(track, track[1:], strict=False)):
        leg = cv.group(g, f"{id}-leg-{i}", start=round(times[i], 3), end=end)
        cv.path(leg, f"M {x + a[0]} {y + a[1]} L {x + b[0]} {y + b[1]}", None, TANGERINE, 10.0)
    for pin in pins:
        wide = measure(pin.label, size) + 36.0
        left = min(max(x + pin.x - wide / 2, x + 8.0), x + PHONE_W - wide - 8.0)
        top = y + pin.y + 16.0 if pin.below or pin.y < 74.0 else y + pin.y - 72.0
        _inked_oval(cv, g, x + pin.x, y + pin.y, 13.0, 13.0, pin.fill, 4.0)
        cv.rect(g, left, top, wide, 56.0, pin.fill, PLUM_DEEP, 4.0, radius=CHIP)
        _text(cv, g, pin.label, left, top, wide, 56.0, size, PLUM_DEEP, "center")
    head = cv.group(g, f"{id}-marker", x=x + track[0][0], y=y + track[0][1])
    _marker(cv, head, marker)
    cv.keys(head, "x", [(round(t, 3), x + p[0]) for t, p in zip(times, track, strict=True)], hold=False, local=False)
    cv.keys(head, "y", [(round(t, 3), y + p[1]) for t, p in zip(times, track, strict=True)], hold=False, local=False)


APP_LABEL_Y, APP_AMOUNT_Y, APP_BUTTON_Y = 40.0, 110.0, 310.0  # down from the screen's top, under the header
APP_BUTTON_W, APP_BUTTON_H = 560.0, 132.0
APP_NOTE_Y, APP_NOTE_H, APP_NOTES = 468.0, 84.0, 2  # the notes under the button, and how many fit before the foot
APP_AMOUNT_SIZE, APP_WORD_SIZE, APP_NOTE_SIZE = 150.0, 64.0, 44.0
APP_DEAD = "#b7afc4"  # a button that no longer does anything
APP_TAP, APP_TAP_R = 0.28, 40.0  # seconds a tap's ring stays, and its size


def _button(cv: Canvas, g, word: str, fill: str, ink: str) -> None:
    """The app's one button, across the middle of the screen."""
    x, y = PHONE_X + (PHONE_W - APP_BUTTON_W) / 2, PHONE_Y + MAP_TOP + APP_BUTTON_Y
    cv.rect(g, x, y, APP_BUTTON_W, APP_BUTTON_H, fill, PLUM_DEEP, 5.0, radius=CHIP)
    _text(cv, g, word, x, y, APP_BUTTON_W, APP_BUTTON_H, APP_WORD_SIZE, ink, "center")


@register(
    "graphic", "news-money-app", summary="An unbranded money app on Gus's phone, whose button stops working on cue"
)
def money_app(
    cv: Canvas,
    parent,
    title: str,
    amount: str,
    action: str,
    refused: str,
    start: float,
    end: float,
    measure: Measure,
    taps: Sequence[float] = (),
    refused_at: float | None = None,
    notes: Sequence[tuple[float, str]] = (),
    id: str = "news-money-app",
) -> None:
    """A balance on the phone from ``start`` to ``end``: ``amount`` under the app's ``title``, and a button that reads
    ``action`` until ``refused_at`` and ``refused`` from then on. ``taps`` are the seconds a finger lands on it, beside
    the word so the word stays read, and each of ``notes`` (its second, its words) stays once it arrives. It refuses
    copy the show keeps off the screen, words too wide for the phone, and any instant off its span. It copies no real
    app: a mint header and one button."""
    _span(start, end, "the app")
    for word, size, room in (
        (amount, APP_AMOUNT_SIZE, PHONE_W - 60.0),
        (action, APP_WORD_SIZE, APP_BUTTON_W - 40.0),
        (refused, APP_WORD_SIZE, APP_BUTTON_W - 40.0),
    ):
        check_copy(word)
        if not word.strip() or measure(word, size) > room:
            raise NewsKitError(f"the app's {word!r} must be some words that fit")
    beside = APP_BUTTON_W / 2 - measure(action, APP_WORD_SIZE) / 2  # the button left on either side of the word
    if taps and beside < 2 * (APP_TAP_R + 4.0):
        raise NewsKitError(f"a tap needs room beside {action!r} on the button")
    check_copy(title)
    blocked = end if refused_at is None else refused_at
    if not start <= blocked <= end or (refused_at is not None and blocked >= end):
        raise NewsKitError(f"the app's button stops inside {start}..{end}, not at {refused_at}")
    if not all(start <= at < end for at in taps):
        raise NewsKitError(f"a tap lands inside {start}..{end}, got {tuple(taps)}")
    if len(notes) > APP_NOTES:
        raise NewsKitError(f"the screen holds {APP_NOTES} notes, got {len(notes)}")
    for at, note in notes:
        check_copy(note)
        if not start <= at < end:
            raise NewsKitError(f"note {note!r} arrives after the app has gone")
        if not note.strip() or measure(note, APP_NOTE_SIZE) > PHONE_W - 80.0:
            raise NewsKitError(f"note {note!r} must be some words that fit")
    g = cv.group(parent, id, start=start, end=end)
    _handset(cv, g, title)
    x, y = PHONE_X, PHONE_Y + MAP_TOP
    _text(cv, g, "BALANCE", x, y + APP_LABEL_Y, PHONE_W, 56.0, 46, PLUM, "center")
    _text(cv, g, amount, x, y + APP_AMOUNT_Y, PHONE_W, 170.0, APP_AMOUNT_SIZE, PLUM_DEEP, "center")
    if blocked > start:
        _button(cv, cv.group(g, f"{id}-live", start=start, end=blocked), action, MINT, PLUM_DEEP)
    if refused_at is not None:
        _button(cv, cv.group(g, f"{id}-refused", start=blocked, end=end), refused, APP_DEAD, PLUM_DEEP)
    for i, at in enumerate(taps):
        ring = cv.group(g, f"{id}-tap-{i}", start=at, end=min(at + APP_TAP, end))
        at_x = x + PHONE_W / 2 + APP_BUTTON_W / 2 - beside / 2
        _inked_oval(cv, ring, at_x, y + APP_BUTTON_Y + APP_BUTTON_H / 2, APP_TAP_R, APP_TAP_R, BUTTER)
    for i, (at, note) in enumerate(notes):
        row = cv.group(g, f"{id}-note-{i}", start=at, end=end)
        top = y + APP_NOTE_Y + i * (APP_NOTE_H + 12.0)
        cv.rect(row, x + 30.0, top, PHONE_W - 60.0, APP_NOTE_H, BUTTER, PLUM_DEEP, 4.0, radius=CHIP)
        _text(cv, row, note, x + 30.0, top, PHONE_W - 60.0, APP_NOTE_H, APP_NOTE_SIZE, PLUM_DEEP, "center")


OVEN_STRIP, OVEN_DOOR_Y, OVEN_FOOT = 270.0, 296.0, 786.0  # the stove's control strip and door, under the phone's window
OVEN_DIGIT_W, OVEN_DIGIT_H, OVEN_STROKE, OVEN_GAP = 80.0, 150.0, 16.0, 14.0
OVEN_LIT, OVEN_DARK = "#ffb347", "#2a1830"  # the display: a segment on, and one off that still shows faintly
OVEN_TAG_SIZE, OVEN_LABEL_SIZE = 76.0, 46.0
OVEN_SEGMENTS = {  # the seven segments, clockwise from the top bar with g across the middle
    "0": "abcdef",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
}
_OVEN_TIME = re.compile(r"(?:[1-9]|1[0-2]):[0-5]\d")


def _oven_digit(cv: Canvas, g, x: float, y: float, digit: str) -> None:
    """One seven-segment digit at ``x``, ``y``: every bar drawn, the ones the digit does not use left dark."""
    w, h, t = OVEN_DIGIT_W, OVEN_DIGIT_H, OVEN_STROKE
    mid = y + (h - t) / 2
    half = (h - t) / 2
    bars = {
        "a": (x + t, y, w - 2 * t, t),
        "b": (x + w - t, y + t / 2, t, half),
        "c": (x + w - t, mid + t / 2, t, half),
        "d": (x + t, y + h - t, w - 2 * t, t),
        "e": (x, mid + t / 2, t, half),
        "f": (x, y + t / 2, t, half),
        "g": (x + t, mid, w - 2 * t, t),
    }
    for name, box in bars.items():
        cv.rect(g, *box, OVEN_LIT if name in OVEN_SEGMENTS[digit] else OVEN_DARK, radius=4.0)


def _oven_tag(cv: Canvas, g, word: str, fill: str) -> None:
    """The tag hung in the door's window."""
    x, y = PHONE_X + 90.0, PHONE_Y + OVEN_DOOR_Y + 216.0
    cv.rect(g, x, y, PHONE_W - 180.0, 160.0, fill, PLUM_DEEP, 5.0, radius=CHIP)
    _text(cv, g, word, x, y, PHONE_W - 180.0, 160.0, OVEN_TAG_SIZE, PLUM_DEEP, "center")


@register("graphic", "news-oven-clock", summary="An unbranded stove whose clock never changes while the tag on it does")
def oven_clock(
    cv: Canvas,
    parent,
    label: str,
    time: str,
    wrong: str,
    right: str,
    start: float,
    end: float,
    measure: Measure,
    right_at: float | None = None,
    id: str = "news-oven-clock",
) -> None:
    """A stove over the dimmed room from ``start`` to ``end``: ``time`` on its seven-segment clock, ``label`` in its
    door and a tag reading ``wrong`` until ``right_at`` and ``right`` from then on. The digits stay as they are through
    the turn, and that is the joke: the clock was never touched. It refuses a time that is no clock's, copy the show
    keeps off the screen, words too wide for the door, and an instant off its span. It copies no real stove."""
    _span(start, end, "the oven")
    if not _OVEN_TIME.fullmatch(time):
        raise NewsKitError(f"the oven's clock reads h:mm, not {time!r}")
    for word, size, room in (
        (label, OVEN_LABEL_SIZE, PHONE_W - 160.0),
        (wrong, OVEN_TAG_SIZE, PHONE_W - 220.0),
        (right, OVEN_TAG_SIZE, PHONE_W - 220.0),
    ):
        check_copy(word)
        if not word.strip() or measure(word, size) > room:
            raise NewsKitError(f"the oven's {word!r} must be some words that fit")
    if right_at is not None and not start < right_at < end:
        raise NewsKitError(f"the oven's tag turns inside {start}..{end}, not at {right_at}")
    g = cv.group(parent, id, start=start, end=end)
    x, y, wide = PHONE_X, PHONE_Y, PHONE_W
    cv.rect(g, 0, 0, cv.width, TICKER_Y, "#160a3088")
    steel = cv.grad("news2-stove", [(0, "#efe9f6"), (1, "#b7afc4")], (0, 0, 0, 1))
    cv.rect(g, x - 12, y - 8, wide + 48, OVEN_FOOT + 48, SHADOW, radius=2 * CHIP)
    cv.rect(g, x - 20, y - 20, wide + 40, OVEN_FOOT + 40, steel, PLUM_DEEP, 5.0, radius=2 * CHIP)
    cv.rect(g, x, y, wide, OVEN_STRIP, PLUM_DEEP, radius=CHIP)
    for knob in (x + 70.0, x + wide - 70.0):
        _inked_oval(cv, g, knob, y + OVEN_STRIP / 2, 40.0, 40.0, CREAM)
        cv.rect(g, knob - 4.0, y + OVEN_STRIP / 2 - 36.0, 8.0, 30.0, PLUM_DEEP, radius=4.0)
    cv.rect(g, x + wide / 2 - 220.0, y + 30.0, 440.0, OVEN_STRIP - 60.0, "#0e0620", radius=CHIP)
    numerals = time.replace(":", "")
    colon = time.index(":")
    room = 2 * OVEN_GAP + OVEN_STROKE  # what the colon takes between the hours and the minutes
    left = x + wide / 2 - (len(numerals) * (OVEN_DIGIT_W + OVEN_GAP) - OVEN_GAP + room) / 2
    top = y + (OVEN_STRIP - OVEN_DIGIT_H) / 2
    digits = cv.group(g, f"{id}-digits")
    for i, digit in enumerate(numerals):
        _oven_digit(cv, digits, left + i * (OVEN_DIGIT_W + OVEN_GAP) + (room if i >= colon else 0.0), top, digit)
    dots = left + colon * (OVEN_DIGIT_W + OVEN_GAP)
    for dot in (0.3, 0.6):
        cv.rect(digits, dots, top + dot * OVEN_DIGIT_H, OVEN_STROKE, OVEN_STROKE, OVEN_LIT, radius=4.0)
    cv.rect(g, x, y + OVEN_DOOR_Y, wide, OVEN_FOOT - OVEN_DOOR_Y, "#cfc7db", PLUM_DEEP, 5.0, radius=CHIP)
    cv.rect(g, x + 60.0, y + OVEN_DOOR_Y + 24.0, wide - 120.0, 30.0, CREAM, PLUM_DEEP, 4.0, radius=15.0)
    cv.rect(g, x + 60.0, y + OVEN_DOOR_Y + 78.0, wide - 120.0, 392.0, PLUM, PLUM_DEEP, 5.0, radius=CHIP)
    _text(cv, g, label, x, y + OVEN_DOOR_Y + 124.0, wide, 60.0, OVEN_LABEL_SIZE, CREAM, "center")
    turned = end if right_at is None else right_at
    _oven_tag(cv, cv.group(g, f"{id}-wrong", start=start, end=turned), wrong, TANGERINE)
    if right_at is not None:
        _oven_tag(cv, cv.group(g, f"{id}-right", start=right_at, end=end), right, MINT)

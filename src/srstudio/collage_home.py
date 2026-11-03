"""Collage home and table props: a wall TV whose screen a reel fills, a builder's hat, a hole in the wall, a pay
envelope, cereal, menus, plates and the small things a long stay leaves behind.

Paper like the cast (ADR 0026): hand-cut edges, an ink line and a drop shadow, drawn from :mod:`srstudio.collage`. They
hold no timing of their own; a caller keys the group each returns on the project clock, so a recording that re-times
the beats moves them with it. No prop carries a brand, and none carries a figure anyone could read as personal data.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import NamedTuple

from . import checks, collage_sets
from ._collage_home_contracts import contract
from .canvas import Canvas
from .collage import CAPTION_BOTTOM, INK, Point, _cut, _paper, _smooth, draw_shapes
from .errors import SrstudioError
from .registry import register
from .toon_props import clock_angles

__all__ = [
    "DISHES",
    "HomeError",
    "Screen",
    "WallClock",
    "cereal_bowl",
    "chair_back",
    "dead_plant",
    "desk_lamp",
    "hard_hat",
    "headset",
    "hook_box",
    "hook_card",
    "kayak",
    "land",
    "menu_card",
    "napkin",
    "order_pad",
    "pay_envelope",
    "pen",
    "plate",
    "school_desk",
    "snowy_window",
    "spoon",
    "staircase",
    "tissue_box",
    "toothbrush_mug",
    "wall_clock",
    "wall_hole",
    "wall_tv",
]

ENVELOPE = "#d9b382"  # manila
STAMP = "#c1121f"
HAT = "#ffca3a"
DISHES = ("steak", "salad", "sauce", "empty")
PLASTER = "#efe6d4"  # what a broken wall shows round its hole
STUD = "#b08355"
VOID = "#2a2024"
LAND_FROM = -240.0  # how far above its rest a prop starts
LAND_DROP = 0.16  # seconds to the table
LAND_BOUNCE = 0.24  # the top of its one small bounce
LAND_RISE = 12.0
LAND_SETTLE = 0.34  # at rest
FRAME_W = 1080.0
HOOK_TOP = CAPTION_BOTTOM + 14.0  # the room under the caption pill
HOOK_H = 104.0
HOOK_SIZE = 56.0
HOOK_PAD = 40.0  # either side of the words
HOOK_MARGIN = 40.0  # from the frame's edge and from the shelf


class HomeError(SrstudioError, ValueError):
    """A prop asked for something it cannot draw."""


class Screen(NamedTuple):
    """A TV: its whole ``group``, and ``image``, a group clipped to the screen with its origin at the screen's top-left,
    ``w`` by ``h``, that a reel fills."""

    group: object
    image: object
    w: float
    h: float


class WallClock(NamedTuple):
    """A clock: its ``group`` and where its hands point, degrees clockwise from twelve."""

    group: object
    hour: float
    minute: float


def _size(value: float, what: str) -> float:
    if not (checks.number(value) and value > 0):
        raise HomeError(f"{what} must be positive, got {value!r}")
    return float(value)


def _box(w: float, h: float) -> list[Point]:
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def _dome(w: float, h: float, n: int = 12) -> list[Point]:
    """The top half of an ellipse, left to right, its flat side on y 0."""
    return [(-w / 2 * math.cos(math.pi * i / n), -h * math.sin(math.pi * i / n)) for i in range(n + 1)]


def land(cv: Canvas, node, *, at: float, y: float) -> None:
    """``node`` (a group drawn where it comes to rest, ``y`` its resting ``y``) is unseen until ``at`` on the project
    clock, then drops in from above, lands and settles with one small bounce: one-at-a-time arrivals, placed by the
    caller on the beats, so a recording's timing moves them."""
    if not (checks.number(at) and at >= 0):
        raise HomeError(f"a prop lands on a second, >= 0, got {at!r}")
    above = y + LAND_FROM
    keys = [(at, above), (at + LAND_DROP, y), (at + LAND_BOUNCE, y - LAND_RISE), (at + LAND_SETTLE, y)]
    if at > 0:
        keys.insert(0, (0.0, above))
    cv.keys(node, "y", keys, kind="cubic-in", local=False)
    cv.keys(node, "opacity", [(0.0, 0.0), (at, 1.0)] if at > 0 else [(0.0, 1.0)], local=False)


def _lettered(cv: Canvas, g, text: str, x: float, y: float, w: float, h: float, size: float, color: str) -> None:
    cv.text(g, cv.uid("home"), text, x, y, round(w), round(h), round(size), color=color)


def hook_box(text: str, room: str, measure: Callable[..., float]) -> tuple[float, float, float, float]:
    """Where a hook card goes on the set ``room`` (x0, y0, x1, y1): under the caption pill, centred in the width the
    wider side of the shelf leaves, so the signature, the show's bug and a two-row caption all stay clear whatever the
    set. Raises :class:`HomeError` for no words, or words too wide for that room."""
    if not text.strip():
        raise HomeError("a hook card that says nothing is not a hook")
    shelf = collage_sets.signature_box(room)
    left, right = max(
        ((HOOK_MARGIN, shelf[0] - HOOK_MARGIN), (shelf[2] + HOOK_MARGIN, FRAME_W - HOOK_MARGIN)),
        key=lambda side: side[1] - side[0],
    )
    width = math.ceil(measure(text, size=HOOK_SIZE) + 2 * HOOK_PAD)
    if width > right - left:
        raise HomeError(f"{text!r} is too wide for the {right - left:g} px beside the shelf of {room}: {width:g} px")
    x0 = float((left + right - width) // 2)
    return x0, HOOK_TOP, x0 + width, HOOK_TOP + HOOK_H


def hook_card(
    cv: Canvas, parent, text: str, room: str, measure: Callable[..., float], *, start: float, seconds: float
) -> object:
    """The one short on-screen line of a reel, up for ``seconds`` from ``start`` on the project clock, placed by
    :func:`hook_box`; a card that spans a cut is drawn in each shot it shows in."""
    _size(seconds, "a hook card's seconds")
    x0, y0, x1, y1 = hook_box(text, room, measure)
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(start, start + seconds)])
    collage_sets.sign(cv, g, text, round(x0), round(y0), round(x1 - x0), round(y1 - y0), size=round(HOOK_SIZE))
    return g


@register(
    "prop",
    "collage-wall-tv",
    summary="A flat paper TV on the wall with an empty screen a reel fills",
    contract=contract('collage-wall-tv'),
)
def wall_tv(cv: Canvas, parent, x: float, y: float, w: float) -> Screen:
    """A TV ``w`` wide with its top-left at ``x, y``; draw into :attr:`Screen.image`, clipped to the screen."""
    h = _size(w, "a TV's width") * 0.62
    rim = 22.0
    g = cv.group(parent, cv.uid("g"))
    draw_shapes(cv, g, _paper(_cut(f"wall-tv-{x}-{y}", [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], 2), "#23202b"))
    sw, sh = w - 2 * rim, h - 2 * rim
    cv.rect(g, x + rim, y + rim, sw, sh, "#0f0d14")
    image = cv.group(g, cv.uid("tv-image"), x=x + rim, y=y + rim)
    image.add_mask(type="rect", x=0, y=0, width=sw, height=sh)
    return Screen(g, image, sw, sh)


@register(
    "prop",
    "collage-hard-hat",
    summary="A yellow builder's hard hat with a ridge and a short brim",
    contract=contract('collage-hard-hat'),
)
def hard_hat(cv: Canvas, parent, x: float, y: float, w: float = 420.0, tilt: float = 0.0) -> object:
    """A hat ``w`` across its brim, the brim's centre at ``x, y``, for a head or a table."""
    k = round(_size(w, "a hat's width") / 420.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut("hat-dome", _dome(370, 190), 1), HAT))
    draw_shapes(cv, g, _paper(_cut("hat-ridge", [(-34, -196), (34, -196), (46, -8), (-46, -8)], 1), "#ffdd6e", False))
    draw_shapes(cv, g, _paper(_cut("hat-brim", [(-210, -10), (210, -10), (220, 22), (-220, 22)], 1), "#e8a916"))
    return g


@register(
    "prop",
    "collage-kayak",
    summary="A red paper kayak with its cockpit and a paddle across it",
    contract=contract('collage-kayak'),
)
def kayak(cv: Canvas, parent, x: float, y: float, w: float = 560.0, tilt: float = 0.0) -> object:
    """A kayak ``w`` long, centred on ``x, y``."""
    k = round(_size(w, "a kayak's length") / 560.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k, rotation=tilt)
    hull = [(-280, -6), (-150, -44), (150, -44), (280, -6), (150, 40), (-150, 40)]
    draw_shapes(cv, g, _paper(_cut("kayak-hull", hull, 2), "#e63946"))
    cv.ellipse(g, -96, -32, 192, 44, "#23202b", INK, 4)
    paddle = cv.group(g, cv.uid("g"), y=-70, rotation=-16.0)
    cv.rect(paddle, -250, -6, 500, 12, "#3a3a44", INK, 2)
    for dx in (-274, 274):
        cv.ellipse(paddle, dx - 30, -44, 60, 88, "#ffca3a", INK, 3)
    return g


@register(
    "prop",
    "collage-school-desk",
    summary="A child's school desk on two legs, seen from the front",
    contract=contract('collage-school-desk'),
)
def school_desk(cv: Canvas, parent, x: float, y: float, w: float = 240.0) -> object:
    """A desk ``w`` wide, its feet centred on ``x, y``."""
    k = round(_size(w, "a desk's width") / 240.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    for dx in (-92, 92):
        draw_shapes(
            cv,
            g,
            _paper(
                _cut(f"desk-leg-{dx}", [(dx - 8, -150), (dx + 8, -150), (dx + 8, 0), (dx - 8, 0)], 1), "#6d6875", False
            ),
        )
    draw_shapes(cv, g, _paper(_cut("desk-top", [(-120, -176), (120, -176), (120, -146), (-120, -146)], 1), "#dda15e"))
    return g


@register(
    "prop",
    "collage-staircase",
    summary="A short flight of paper stairs rising to the right, with a handrail",
    contract=contract('collage-staircase'),
)
def staircase(cv: Canvas, parent, x: float, y: float, w: float, h: float, steps: int = 6) -> object:
    """A flight ``w`` by ``h`` with its foot's left corner at ``x, y``, rising to the right in ``steps`` steps."""
    _size(w, "a staircase's width")
    _size(h, "a staircase's height")
    if not (isinstance(steps, int) and steps >= 2):
        raise HomeError(f"a staircase has at least 2 steps, got {steps!r}")
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    run, rise = w / steps, h / steps
    points: list[Point] = [(0.0, 0.0)]
    for i in range(steps):
        points += [(i * run, -(i + 1) * rise), ((i + 1) * run, -(i + 1) * rise)]
    points.append((w, 0.0))
    draw_shapes(cv, g, _paper(_cut(f"stairs-{steps}", points, 1), "#a98467"))
    cv.line(g, run * 0.4, -rise * 3.4, w - run * 0.4, -h - rise * 2.4, "#6b4f3a", 12)
    return g


@register(
    "prop",
    "collage-pay-envelope",
    summary="A sealed manila pay envelope with a stamp across it, nothing else",
    contract=contract('collage-pay-envelope'),
)
def pay_envelope(
    cv: Canvas, parent, x: float, y: float, w: float = 560.0, stamp: str = "CONFIDENTIAL", size: float = 60.0
) -> object:
    """A sealed envelope ``w`` wide, centred on ``x, y``, its ``stamp`` across it. It shows no figure, whatever the
    reel: the point of it is that nobody can read what is inside."""
    h = _size(w, "an envelope's width") * 0.62
    _size(size, "a stamp's type size")
    if any(c.isdigit() for c in stamp):
        raise HomeError(f"a sealed envelope shows no figure, got {stamp!r}")
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    draw_shapes(cv, g, _paper(_cut("envelope", _box(w, h), 2), ENVELOPE))
    flap = [(-w / 2, -h / 2), (w / 2, -h / 2), (0.0, -h * 0.02)]
    draw_shapes(cv, g, _paper(_cut("envelope-flap", flap, 1), "#c99e6b", False))
    cv.ellipse(g, -30, -h * 0.02 - 30, 60, 60, STAMP, INK, 4)
    if stamp:
        band = cv.group(g, cv.uid("g"), y=h * 0.26, rotation=-5.0)
        cv.rect(band, -w * 0.46, -size * 0.72, w * 0.92, size * 1.44, "#fffaf0", STAMP, 7, radius=8)
        _lettered(cv, band, stamp, -w * 0.46, -size * 0.72, w * 0.92, size * 1.44, size, STAMP)
    return g


@register(
    "prop",
    "collage-headset",
    summary="A call-centre headset: a band over the head, one earcup, a boom mic",
    contract=contract('collage-headset'),
)
def headset(cv: Canvas, parent, cx: float, cy: float, rx: float = 220.0, ry: float = 205.0) -> object:
    """A headset on a head centred on ``cx, cy`` with radii ``rx`` and ``ry``, as :data:`srstudio.collage.HEAD_Y`."""
    _size(rx, "a head's width")
    _size(ry, "a head's height")
    g = cv.group(parent, cv.uid("g"), x=cx, y=cy)
    band = [(-rx * math.cos(math.pi * i / 12), -ry * 1.04 * math.sin(math.pi * i / 12)) for i in range(13)]
    cv.path(g, _smooth(band, closed=False), stroke="#23202b", sw=22)
    cv.ellipse(g, rx - 34, -44, 74, 110, "#23202b", INK, 4)
    cv.path(g, f"M{rx + 2:g} 60 Q{rx - 30:g} {ry * 0.92:g} {rx * 0.34:g} {ry * 0.86:g}", stroke="#23202b", sw=11)
    cv.ellipse(g, rx * 0.34 - 20, ry * 0.86 - 14, 40, 28, "#3a3a44", INK, 3)
    return g


@register(
    "prop",
    "collage-desk-lamp",
    summary="One bare lamp on a stalk with its pool of light",
    contract=contract('collage-desk-lamp'),
)
def desk_lamp(cv: Canvas, parent, x: float, y: float, h: float = 300.0) -> object:
    """A lamp ``h`` tall, its base centred on ``x, y``."""
    k = round(_size(h, "a lamp's height") / 300.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    glow = cv.rgrad("collage-lamp-glow", [(0, "#fff3b0d0"), (1, "#fff3b000")])
    cv.ellipse(g, -230, -500, 460, 460, glow)
    draw_shapes(cv, g, _paper(_cut("lamp-base", [(-70, -18), (70, -18), (80, 0), (-80, 0)], 1), "#3a3a44"))
    cv.line(g, 0, -18, 0, -240, "#3a3a44", 12)
    draw_shapes(cv, g, _paper(_cut("lamp-shade", [(-50, -300), (50, -300), (92, -230), (-92, -230)], 2), "#6d6875"))
    cv.ellipse(g, -24, -244, 48, 34, "#fff3b0")
    return g


@register(
    "prop",
    "collage-dead-plant",
    summary="A dead plant in a pot: brown stalks, one leaf left hanging",
    contract=contract('collage-dead-plant'),
)
def dead_plant(cv: Canvas, parent, x: float, y: float, h: float = 300.0) -> object:
    """A pot and its dead plant ``h`` tall, the pot's foot centred on ``x, y``."""
    k = round(_size(h, "a plant's height") / 300.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    for d in ("M0 -120 Q-10 -220 -90 -250", "M0 -120 Q14 -230 70 -290", "M0 -120 Q30 -180 110 -170"):
        cv.path(g, d, stroke="#6b4f3a", sw=9)
    draw_shapes(cv, g, _paper(_cut("plant-leaf", [(108, -170), (138, -150), (120, -104), (98, -140)], 1), "#a98467"))
    draw_shapes(cv, g, _paper(_cut("plant-pot", [(-80, -120), (80, -120), (58, 0), (-58, 0)], 2), "#bc6c25"))
    return g


@register(
    "prop",
    "collage-cereal-bowl",
    summary="A bowl of cereal, seen from the side, with the milk showing",
    contract=contract('collage-cereal-bowl'),
)
def cereal_bowl(cv: Canvas, parent, x: float, y: float, w: float = 300.0) -> object:
    """A bowl ``w`` wide, its foot centred on ``x, y``."""
    k = round(_size(w, "a bowl's width") / 300.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    cv.ellipse(g, -140, -158, 280, 56, "#fffaf0", INK, 4)
    for dx, dy in ((-80, -138), (-30, -146), (24, -136), (76, -142)):
        cv.ellipse(g, dx - 15, dy - 9, 30, 18, "#e9a23b", INK, 2)
    bowl = [(-150, -130), (150, -130), (96, -6), (-96, -6)]
    draw_shapes(cv, g, _paper(_cut("bowl", bowl, 2), "#457b9d"))
    return g


@register("prop", "collage-spoon", summary="A paper spoon, its bowl at the top", contract=contract('collage-spoon'))
def spoon(cv: Canvas, parent, x: float, y: float, length: float = 300.0, tilt: float = 0.0) -> object:
    """A spoon ``length`` long, the end of its handle at ``x, y``, turned ``tilt`` degrees about that end."""
    k = round(_size(length, "a spoon's length") / 300.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut("spoon-stem", [(-9, 0), (9, 0), (7, -220), (-7, -220)], 1), "#ced4da", False))
    cv.ellipse(g, -34, -300, 68, 92, "#ced4da", INK, 4)
    return g


@register("prop", "collage-pen", summary="A ballpoint pen, its tip at the bottom", contract=contract('collage-pen'))
def pen(cv: Canvas, parent, x: float, y: float, length: float = 240.0, tilt: float = 0.0, colour: str = "#1d3557"):
    """A pen ``length`` long with its tip at ``x, y``, turned ``tilt`` degrees about the tip."""
    k = round(_size(length, "a pen's length") / 240.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut("pen-body", [(-13, -40), (13, -40), (13, -240), (-13, -240)], 1), colour))
    draw_shapes(cv, g, _paper(_cut("pen-tip", [(-13, -40), (13, -40), (0, 0)], 0), "#ced4da", False))
    return g


@register(
    "prop",
    "collage-menu-card",
    summary="A tall folded restaurant menu held closed, no brand",
    contract=contract('collage-menu-card'),
)
def menu_card(cv: Canvas, parent, x: float, y: float, w: float = 300.0, h: float = 420.0, tilt: float = 0.0) -> object:
    """A menu ``w`` by ``h``, centred on ``x, y``, its cover lettered MENU."""
    _size(w, "a menu's width")
    _size(h, "a menu's height")
    g = cv.group(parent, cv.uid("g"), x=x, y=y, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut(f"menu-{w}-{h}", _box(w, h), 2), "#6a040f"))
    cv.rect(g, -w / 2 + 16, -h / 2 + 16, w - 32, h - 32, cv.clear, "#ffca3a", 4, radius=6)
    _lettered(cv, g, "MENU", -w / 2, -56, w, 112, min(w / 4.2, 74), "#ffca3a")
    return g


@register(
    "prop",
    "collage-order-pad",
    summary="A waiter's spiral order pad, a blank page and a short scrawl",
    contract=contract('collage-order-pad'),
)
def order_pad(cv: Canvas, parent, x: float, y: float, w: float = 240.0, tilt: float = 0.0, *, lines: int = 3) -> object:
    """A pad ``w`` wide, centred on ``x, y``, with ``lines`` of unreadable scrawl on its page."""
    h = _size(w, "a pad's width") * 1.32
    if not (isinstance(lines, int) and lines >= 0):
        raise HomeError(f"a pad's lines are a whole number, got {lines!r}")
    g = cv.group(parent, cv.uid("g"), x=x, y=y, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut("order-pad", _box(w, h), 2), "#fffdf0"))
    for i in range(7):
        cx = -w / 2 + (i + 1) * w / 8
        cv.ellipse(g, cx - 7, -h / 2 - 8, 14, 22, "#adb5bd", INK, 2)
    for i in range(lines):
        y0 = -h / 2 + (i + 1) * h / (lines + 2)
        points = [(-w * 0.36 + j * w * 0.09, y0 + (9 if j % 2 else -9)) for j in range(9)]
        cv.path(g, _smooth(points, closed=False), stroke="#1d3557", sw=5)
    return g


def _steak(cv: Canvas, g) -> None:
    meat = [(-110, -30), (-30, -56), (90, -40), (116, 16), (24, 46), (-96, 34)]
    draw_shapes(cv, g, _paper(_cut("steak", meat, 3), "#6f3b22"))
    for dx in (-60, 0, 60):
        cv.line(g, dx - 20, 22, dx + 34, -30, "#3a1d10", 8)


def _salad(cv: Canvas, g) -> None:
    for dx, dy, colour in ((-70, -6, "#588157"), (0, -30, "#a3b18a"), (70, -4, "#3a5a40"), (-20, 20, "#8ac926")):
        cv.ellipse(g, dx - 56, dy - 34, 112, 68, colour, INK, 3)
    cv.ellipse(g, 12, -6, 34, 34, "#e63946", INK, 3)


def _sauce(cv: Canvas, g) -> None:
    cv.ellipse(g, -66, -40, 132, 80, "#fffaf0", INK, 4)
    cv.ellipse(g, -48, -28, 96, 56, "#8a4b1f")


DISH_DRAW = {"steak": _steak, "salad": _salad, "sauce": _sauce, "empty": lambda cv, g: None}


@register(
    "prop",
    "collage-plate",
    summary="A plate seen from a little above, with a steak, a salad or sauce on it",
    contract=contract('collage-plate'),
)
def plate(cv: Canvas, parent, x: float, y: float, w: float = 400.0, dish: str = "empty") -> object:
    """A plate ``w`` wide, centred on ``x, y``, with ``dish`` (one of :data:`DISHES`) on it."""
    k = round(_size(w, "a plate's width") / 400.0, 4)
    if dish not in DISHES:
        raise HomeError(f"no dish {dish!r}; one of {DISHES}")
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    cv.ellipse(g, -200, -104, 400, 208, "#fffaf0", INK, 5)
    cv.ellipse(g, -150, -76, 300, 152, "#f1ece0")
    DISH_DRAW[dish](cv, g)
    return g


@register(
    "prop",
    "collage-chair-back",
    summary="The tall wooden back of a dining chair, seen from the front",
    contract=contract('collage-chair-back'),
)
def chair_back(cv: Canvas, parent, x: float, y: float, w: float = 460.0, h: float = 760.0) -> object:
    """A chair back ``w`` by ``h``, its top centred on ``x, y``."""
    _size(w, "a chair's width")
    _size(h, "a chair's height")
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    draw_shapes(
        cv,
        g,
        _paper(
            _cut(
                f"chair-{w}-{h}", [(-w / 2, 40), (-w * 0.3, 0), (w * 0.3, 0), (w / 2, 40), (w / 2, h), (-w / 2, h)], 3
            ),
            "#6b4f3a",
        ),
    )
    draw_shapes(
        cv,
        g,
        _paper(
            _cut(f"chair-in-{w}-{h}", [(-w * 0.36, 70), (w * 0.36, 70), (w * 0.36, h), (-w * 0.36, h)], 2),
            "#a98467",
            False,
        ),
    )
    return g


@register(
    "prop",
    "collage-wall-hole",
    summary="A rough hole knocked through a wall: torn plaster, bare studs, dark",
    contract=contract('collage-wall-hole'),
)
def wall_hole(cv: Canvas, parent, x: float, y: float, w: float = 300.0, h: float = 340.0) -> object:
    """A hole ``w`` by ``h``, centred on ``x, y``: the torn edge, the void behind it and two studs."""
    _size(w, "a hole's width")
    _size(h, "a hole's height")
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    edge = [(-0.5, -0.3), (-0.3, -0.5), (0.06, -0.42), (0.34, -0.52), (0.5, -0.2), (0.44, 0.12), (0.52, 0.42),
            (0.2, 0.5), (-0.1, 0.42), (-0.38, 0.52), (-0.52, 0.16)]  # fmt: skip
    torn = [(a * w * 1.12, b * h * 1.12) for a, b in edge]
    hole = [(a * w * 0.9, b * h * 0.9) for a, b in edge]
    draw_shapes(cv, g, _paper(_cut("hole-plaster", torn, 6), PLASTER))
    draw_shapes(cv, g, _paper(_cut("hole-void", hole, 6), VOID, False))
    for dx in (-w * 0.2, w * 0.2):
        cv.rect(g, dx - 20, -h * 0.42, 40, h * 0.84, STUD, INK, 3)
    return g


@register(
    "prop",
    "collage-snowy-window",
    summary="A window pane full of winter: pale sky, a white sill, falling snow",
    contract=contract('collage-snowy-window'),
)
def snowy_window(cv: Canvas, parent, x: float, y: float, w: float, h: float, *, flakes: Sequence[Point] = ()) -> object:
    """A pane ``w`` by ``h`` with its top-left at ``x, y``, laid over a set's window; ``flakes`` are fractions of it."""
    _size(w, "a window's width")
    _size(h, "a window's height")
    g = cv.group(parent, cv.uid("g"))
    sky = cv.grad("collage-snow-sky", [(0, "#c9d6e3"), (1, "#eef3f7")], (0, 0, 0, 1))
    cv.rect(g, x, y, w, h, sky, "#5a4632", 12)
    drift = [(x, y + h), (x, y + h * 0.82), (x + w * 0.4, y + h * 0.72), (x + w, y + h * 0.8), (x + w, y + h)]
    draw_shapes(cv, g, _paper(_cut("snow-drift", drift, 2), "#ffffff", False))
    cv.line(g, x + w / 2, y, x + w / 2, y + h, "#5a4632", 9)
    for fx, fy in flakes or ((0.2, 0.2), (0.7, 0.14), (0.42, 0.42), (0.84, 0.5), (0.14, 0.6), (0.6, 0.64)):
        cv.ellipse(g, x + fx * w - 8, y + fy * h - 8, 16, 16, "#ffffff")
    return g


@register(
    "prop",
    "collage-tissue-box",
    summary="A box of tissues with one standing up out of its slot",
    contract=contract('collage-tissue-box'),
)
def tissue_box(cv: Canvas, parent, x: float, y: float, w: float = 280.0) -> object:
    """A box ``w`` wide, its foot centred on ``x, y``."""
    k = round(_size(w, "a box's width") / 280.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    tissue = [(-46, -128), (-30, -214), (8, -186), (38, -232), (52, -128)]
    draw_shapes(cv, g, _paper(_cut("tissue", tissue, 2), "#ffffff"))
    draw_shapes(cv, g, _paper(_cut("tissue-box", [(-140, -130), (140, -130), (140, 0), (-140, 0)], 2), "#a2d2ff"))
    cv.ellipse(g, -80, -128, 160, 26, "#3a5a78", INK, 3)
    return g


@register(
    "prop",
    "collage-wall-clock",
    summary="A round wall clock whose hands point at the time it is given",
    contract=contract('collage-wall-clock'),
)
def wall_clock(cv: Canvas, parent, x: float, y: float, r: float = 90.0, time: str = "9:00") -> WallClock:
    """A clock of radius ``r`` centred on ``x, y``, showing ``time`` as ``"9:50"``."""
    _size(r, "a clock's radius")
    try:
        hour, minute = clock_angles(time)
    except ValueError as refused:
        raise HomeError(f"a wall clock tells a time like 9:50, got {time!r}") from refused
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    cv.ellipse(g, -r, -r, 2 * r, 2 * r, "#fffaf0", INK, 7)
    for i in range(12):
        tick = cv.group(g, cv.uid("g"), rotation=float(i * 30))
        cv.rect(tick, -3, -r * 0.9, 6, r * 0.14, INK)
    for angle, length, width in ((hour, 0.52, 13), (minute, 0.78, 8)):
        hand = cv.group(g, cv.uid("g"), rotation=angle)
        cv.rect(hand, -width / 2, -r * length, width, r * length, INK)
    cv.ellipse(g, -9, -9, 18, 18, "#c1121f", INK, 2)
    return WallClock(g, hour, minute)


@register(
    "prop",
    "collage-toothbrush-mug",
    summary="A mug with one toothbrush standing in it",
    contract=contract('collage-toothbrush-mug'),
)
def toothbrush_mug(cv: Canvas, parent, x: float, y: float, h: float = 150.0, colour: str = "#e63946") -> object:
    """A mug ``h`` tall with a toothbrush in it, the foot centred on ``x, y``."""
    k = round(_size(h, "a mug's height") / 150.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    brush = cv.group(g, cv.uid("g"), rotation=9.0)
    cv.rect(brush, -8, -270, 16, 210, colour, INK, 3)
    cv.rect(brush, -8, -300, 16, 44, "#fffaf0", INK, 3)
    draw_shapes(cv, g, _paper(_cut("mug", [(-74, -150), (74, -150), (66, 0), (-66, 0)], 2), "#fffaf0"))
    cv.path(g, "M74 -112 Q124 -92 70 -38", stroke=INK, sw=8)
    return g


@register(
    "prop",
    "collage-napkin",
    summary="A white napkin tucked in at the collar, a triangle on the chest",
    contract=contract('collage-napkin'),
)
def napkin(cv: Canvas, parent, x: float, y: float, w: float = 320.0) -> object:
    """A napkin ``w`` wide, its tucked edge centred on ``x, y``."""
    k = round(_size(w, "a napkin's width") / 320.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    draw_shapes(cv, g, _paper(_cut("napkin", [(-160, 0), (160, 0), (0, 300)], 2), "#fffaf0"))
    cv.line(g, -60, 34, 0, 200, "#d8d2c4", 4)
    return g

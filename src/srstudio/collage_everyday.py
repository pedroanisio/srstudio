"""Collage everyday props: paper food, a phone with message bubbles, a clock, chip bags and what comes out of them,
bills that bite, confetti that can turn back, and the bed and table fronts the seated busts sink into.

The props are paper like the cast (ADR 0026): hand-cut edges, an ink line and a drop shadow, drawn in the style's own
vocabulary from :mod:`srstudio.collage`. They hold no timing of their own but what a caller gives them on the project
clock, so a recording that re-times the beats moves them with it. Lettering is kept to words large enough to read on
a phone, and an invented product carries no brand.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence

from . import checks, collage
from .canvas import Canvas
from .collage import (
    CX,
    HALF_WIDTH,
    INK,
    LOOKS,
    SHOULDER_Y,
    Look,
    Point,
    _cut,
    _hand,
    _paper,
    _ring,
    _sleeve,
    _smooth,
    draw_shapes,
)
from .errors import SrstudioError
from .registry import register

__all__ = [
    "BED_TOP",
    "CHIPS",
    "DEAD_SCREEN",
    "EverydayError",
    "FLIP",
    "FOODS",
    "LASAGNA_LAYERS",
    "LOW_BATTERY",
    "TABLE_TOP",
    "alarm_clock",
    "arm",
    "battery_insert",
    "bill",
    "bubble",
    "cereal_box",
    "certificate",
    "chew",
    "chip",
    "chip_bag",
    "confetti",
    "duvet",
    "flip_card",
    "food",
    "gust",
    "lasagna",
    "magnifying_glass",
    "phone",
    "router",
    "salt_shaker",
    "snapshot",
    "tablecloth",
    "thumb",
]

BED_TOP = 1610.0  # the duvet's top edge: what is below it is hidden
TABLE_TOP = 1600.0  # the tablecloth's top edge
BEZEL = 26.0  # the phone's frame round its screen
CONFETTI = ("#e63946", "#ffca3a", "#8ac926", "#1982c4", "#ff7ab6", "#fffaf0")
CHEW = 0.24  # seconds of one chew, open and shut
FOREVER = 86400.0  # the end of a span that runs on: past any reel
LASAGNA_LAYERS = (  # top of each layer and its colour, drawn from the crust down
    (-112.0, "#d9913a"),
    (-72.0, "#fffaf0"),
    (-46.0, "#c1121f"),
    (-18.0, "#f2c14e"),
    (8.0, "#c1121f"),
)
FLIP = 0.2  # the seconds a flip card takes to turn
CARD_PAD = 30.0  # a flip card's margin round its type
CARD_GLYPH = 0.62  # a capital's width as a share of the type size
CARD_LEADING = 1.2  # a row's height as a share of the type size
CARD_FILLS = ("#fffaf0", "#ffe9a8")  # its sides, in turn: a card turned over shows it has
LOW_BATTERY = "#ff5a64"  # the battery's colour at LOW_LEVEL percent or under
LOW_LEVEL = 20
DEAD_SCREEN = "#0b0a10"  # a phone that has died
LIGHTS = {"off": "#3a3a44", "green": "#3ddc6e", "amber": "#ffb703", "red": "#ef3340"}  # a router's status light


class EverydayError(SrstudioError, ValueError):
    """A prop asked for something it cannot draw."""


def _size(value: float, what: str) -> float:
    if not (checks.number(value) and value > 0):
        raise EverydayError(f"{what} must be positive, got {value!r}")
    return float(value)


def _box(w: float, h: float) -> list[Point]:
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def _letter(cv: Canvas, g, name: str, text: str, x: float, y: float, w: float, h: float, size: float, **kw) -> None:
    """Text in a box of whole pixels, as the engine's text assets take it."""
    cv.text(g, cv.uid(name), text, x, y, round(w), round(h), round(size), **kw)


# -- food -------------------------------------------------------------------------------------------------------------
def _taco(cv: Canvas, g) -> None:
    for i in range(7):
        x = -84 + i * 28
        draw_shapes(
            cv, g, [(_smooth(_ring(f"lettuce-{i}", x, -24 - 10 * (i % 2), 26, 22, 10)), "#8ac926", INK, 4.0, 1.0)]
        )
    for x, colour in ((-44, "#e63946"), (6, "#ffca3a"), (52, "#e63946")):
        cv.ellipse(g, x - 15, -44, 30, 30, colour, INK, 3)
    shell = [(100 * math.cos(a), 26 - 96 * math.sin(a) * 0.9) for a in (math.pi * i / 16 for i in range(17))]
    draw_shapes(cv, g, _paper(_cut("taco", [(x, y + 62) for x, y in shell], 2), "#f2c14e"))
    for x in (-56, 0, 54):
        cv.ellipse(g, x - 6, 30, 12, 12, "#c98a1b")


def _sushi(cv: Canvas, g) -> None:
    draw_shapes(cv, g, _paper(_cut("sushi-rice", [(-104, 8), (104, 8), (112, 74), (-112, 74)], 3), "#fffaf0"))
    draw_shapes(cv, g, _paper(_cut("sushi-fish", [(-116, -44), (116, -44), (108, 14), (-108, 14)], 3), "#f4845f"))
    for x in (-60, 0, 60):
        cv.line(g, x - 18, -36, x + 16, 8, "#ffc9b0", 7)
    draw_shapes(
        cv, g, _paper(_cut("sushi-nori", [(-30, -52), (30, -52), (36, 80), (-36, 80)], 2), "#1f3a2d", shadow=False)
    )


def _soup(cv: Canvas, g) -> None:
    for x in (-40, 10, 56):
        cv.path(g, f"M{x} -44 C{x - 26} -74 {x + 26} -92 {x} -122", stroke="#fffaf0", sw=9)
    draw_shapes(cv, g, _paper(_ring("soup-rim", 0, -18, 116, 34, 24, 0.0), "#f4a261"))
    bowl = [(-114, -14), (-84, 62), (-34, 88), (34, 88), (84, 62), (114, -14)]
    draw_shapes(cv, g, _paper(_cut("soup-bowl", bowl, 2), "#3c7a89"))


def _pizza(cv: Canvas, g) -> None:
    draw_shapes(cv, g, _paper(_cut("pizza", [(-104, -74), (104, -74), (0, 112)], 3), "#ffca3a"))
    draw_shapes(cv, g, _paper(_cut("pizza-crust", [(-116, -100), (116, -100), (108, -66), (-108, -66)], 3), "#d9913a"))
    for x, y in ((-44, -36), (36, -30), (0, 26)):
        cv.ellipse(g, x - 21, y - 21, 42, 42, "#c1121f", INK, 3)


FOODS: dict[str, Callable[[Canvas, object], None]] = {"taco": _taco, "sushi": _sushi, "soup": _soup, "pizza": _pizza}


@register(
    "prop", "collage-food", summary="A paper cut-out of a dish: a taco, sushi, a bowl of soup or a slice of pizza"
)
def food(cv: Canvas, parent, kind: str, x: float, y: float, size: float = 240.0, tilt: float = 0.0) -> object:
    """The dish ``kind`` (:data:`FOODS`), about ``size`` wide, centred on ``x, y``, turned ``tilt`` degrees."""
    if kind not in FOODS:
        raise EverydayError(f"no food {kind!r}; one of {sorted(FOODS)}")
    k = round(_size(size, "a food's size") / 240.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, rotation=tilt, scaleX=k, scaleY=k)
    FOODS[kind](cv, g)
    return g


@register(
    "prop", "collage-lasagna", summary="A paper lasagna in its dish: layers of pasta, sauce and cheese, seen side on"
)
def lasagna(cv: Canvas, parent, x: float = 540.0, y: float = 1400.0, w: float = 520.0, tilt: float = 0.0) -> object:
    """A whole lasagna ``w`` wide, centred on ``x, y``, turned ``tilt`` degrees: drawn large, its layers read at a
    glance as the one thing it can be."""
    k = round(_size(w, "a lasagna's width") / 520.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, rotation=tilt, scaleX=k, scaleY=k)
    for i, (top, colour) in enumerate(LASAGNA_LAYERS):
        ripple = [(-236 + 59 * n, top + (5 if n % 2 else -5)) for n in range(9)]
        slab = [*ripple, (236, 70), (-236, 70)]
        draw_shapes(cv, g, _paper(_cut(f"lasagna-layer-{i}", slab, 2), colour, shadow=False))
    for n, (spot_x, spot_y) in enumerate(((-168, -96), (-62, -104), (34, -90), (142, -100))):
        cv.ellipse(g, spot_x - 26, spot_y - 9, 52 + 8 * (n % 2), 16, "#a4551f")
    dish = [(-260, 26), (260, 26), (226, 112), (-226, 112)]
    draw_shapes(cv, g, _paper(_cut("lasagna-dish", dish, 2), "#c8553d"))
    cv.rect(g, -274, 16, 548, 24, "#e07a5f", INK, 4, radius=10)
    return g


# -- a flip card ------------------------------------------------------------------------------------------------------
def _wrapped(text: str, per_line: int) -> list[str]:
    """``text`` greedily broken into rows of at most ``per_line`` characters."""
    rows: list[str] = []
    for word in text.split():
        if rows and len(rows[-1]) + 1 + len(word) <= per_line:
            rows[-1] += " " + word
        else:
            rows.append(word)
    return rows


def _check_fits(text: str, w: float, h: float, size: float) -> None:
    """Refuse a side too long to read at its size: the card exists to be read, and a clipped word cannot be."""
    per_line = int((w - 2 * CARD_PAD) / (size * CARD_GLYPH))
    rows = _wrapped(text, per_line)
    if not rows or max(len(row) for row in rows) > per_line or len(rows) * size * CARD_LEADING > h - CARD_PAD:
        raise EverydayError(f"{text!r} does not fit a {w} by {h} card at {size} px")


@register("prop", "collage-flip-card", summary="A big paper card held up to be read, which flips to its other side")
def flip_card(
    cv: Canvas,
    parent,
    sides: Sequence[tuple[float, str]] = ((0.0, "NO THANKS"),),
    x: float = 540.0,
    y: float = 1500.0,
    w: float = 760.0,
    h: float = 420.0,
    *,
    size: float = 84.0,
    tilt: float = 0.0,
) -> object:
    """A card ``w`` by ``h`` centred on ``x, y``, showing each of ``sides`` (``(from, text)``, project seconds) in
    turn, in type that is measured against the card: it turns edge-on over :data:`FLIP` seconds at each change, so the
    change reads as the card being turned, and refuses a side it could not show whole."""
    if not sides:
        raise EverydayError("a flip card needs at least one side")
    times = [at for at, _ in sides]
    if times != sorted(set(times)):
        raise EverydayError(f"a flip card's sides run forward in time, got {times}")
    _size(w, "a card's width"), _size(h, "a card's height"), _size(size, "a card's type size")
    g = cv.group(parent, cv.uid("g"), x=x, y=y, rotation=tilt)
    for i, (at, text) in enumerate(sides):
        _check_fits(text, w, h, size)
        side = cv.group(g, cv.uid("g"))
        cv.gate(side, [(at, times[i + 1] if i + 1 < len(sides) else FOREVER)])
        draw_shapes(cv, side, _paper(_cut(f"flip-card-{i}", _box(w, h), 3), CARD_FILLS[i % len(CARD_FILLS)]))
        cv.rect(side, -w / 2 + 16, -h / 2 + 16, w - 32, h - 32, "#ffffff00", "#c1121f", 6, radius=10)
        _letter(cv, side, "flip-card", text, -w / 2 + CARD_PAD, -h / 2, w - 2 * CARD_PAD, h, size, color=INK)
    if len(sides) > 1:
        turns = [(times[0], 1.0)]
        for at in times[1:]:
            turns += [(at - FLIP / 2, 1.0), (at, 0.0), (at + FLIP / 2, 1.0)]
        cv.keys(g, "scaleX", turns, hold=False, local=False)
    return g


@register("prop", "collage-magnifying-glass", summary="A paper magnifying glass: a ring, a tinted lens and a handle")
def magnifying_glass(
    cv: Canvas, parent, x: float = 540.0, y: float = 1100.0, size: float = 420.0, tilt: float = -30.0
) -> object:
    """A glass whose lens is ``size`` across, centred on ``x, y``, its handle running away at ``tilt`` degrees: the
    lens is see-through, so what is drawn under it shows; returns the group, which a caller keys to move."""
    k = round(_size(size, "a lens's size") / 420.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut("glass-handle", [(-34, 200), (34, 200), (44, 520), (-44, 520)], 2), "#6b4226"))
    cv.ellipse(g, -210, -210, 420, 420, "#cfe8ff40", "#2b2d42", 26)
    cv.ellipse(g, -180, -180, 360, 360, "#ffffff00", "#ffffff99", 6)
    cv.path(g, "M-120 -96 Q-82 -148 -22 -152", stroke="#ffffffcc", sw=16)
    return g


# -- a router ---------------------------------------------------------------------------------------------------------
def _light_spans(light: Sequence[tuple[float, str]]) -> list[tuple[str, float, float | None]]:
    """``(state, from, to)`` of each stretch of ``light``; the last runs on (``to`` None)."""
    if not light or light[0][0] != 0:
        raise EverydayError(f"a router's light is known from second 0, got {light!r}")
    times = [at for at, _ in light]
    if not all(checks.number(t) for t in times) or times != sorted(set(times)):
        raise EverydayError(f"a router's light changes in rising seconds, got {times!r}")
    unknown = sorted({state for _, state in light} - set(LIGHTS))
    if unknown:
        raise EverydayError(f"no router light {unknown}; one of {sorted(LIGHTS)}")
    ends: list[float | None] = [*times[1:], None]
    return [(state, at, stop) for (at, state), stop in zip(light, ends, strict=True)]


@register(
    "prop",
    "collage-router",
    summary="A paper home router with two aerials, one big status light keyed on cue, and a cord that can be pulled",
)
def router(
    cv: Canvas,
    parent,
    x: float = 540.0,
    y: float = 1400.0,
    w: float = 320.0,
    *,
    light: Sequence[tuple[float, str]] = ((0.0, "green"),),
    unplugged: float | None = None,
) -> object:
    """A router ``w`` wide centred on ``x, y``, its cord running right to a wall socket. ``light`` is ``(project second,
    state)`` from 0, a state one of :data:`LIGHTS`, big enough to read on a phone. From ``unplugged`` the plug hangs
    out of the socket; the light is the caller's to change."""
    spans = _light_spans(light)
    width = _size(w, "a router's width")
    if unplugged is not None and not (checks.number(unplugged) and unplugged >= 0):
        raise EverydayError(f"a router is unplugged from second 0 on, got {unplugged!r}")
    k = round(width / 320.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    for dx, lean in ((-104, -9), (104, 9)):
        cv.line(g, dx, -46, dx + lean, -190, INK, 11)
    socket = (232.0, 8.0)
    cv.rect(g, socket[0] - 36, socket[1] - 46, 72, 92, "#fffaf0", INK, 4, radius=8)
    for side in (-12, 12):
        cv.rect(g, socket[0] + side - 3, socket[1] - 14, 6, 26, INK)
    draw_shapes(cv, g, _paper(_cut("router-case", [(-160, -56), (160, -56), (160, 56), (-160, 56)], 2), "#2f3e5b"))
    cv.rect(g, -128, 30, 180, 6, "#5c6f94")
    cv.rect(g, -128, 14, 180, 6, "#5c6f94")
    for state, at, stop in spans:
        lamp = cv.group(g, cv.uid("g"))
        cv.gate(lamp, [(at, FOREVER if stop is None else stop)])
        if state != "off":
            cv.ellipse(lamp, 54, -70, 140, 140, LIGHTS[state], opacity=0.35)
        cv.ellipse(lamp, 84, -40, 80, 80, LIGHTS[state], INK, 5)
    plugged = cv.group(g, cv.uid("g"))
    cv.line(plugged, 160, 40, socket[0] - 20, 40, INK, 8)
    cv.line(plugged, socket[0] - 20, 40, socket[0], 8, INK, 8)
    cv.rect(plugged, socket[0] - 18, socket[1] - 20, 36, 40, "#23202b", radius=6)
    if unplugged is not None:
        cv.gate(plugged, [(0.0, unplugged)])
        hanging = cv.group(g, cv.uid("g"))
        cv.gate(hanging, [(unplugged, FOREVER)])
        cv.line(hanging, 160, 40, 190, 120, INK, 8)
        cv.rect(hanging, 172, 118, 36, 40, "#23202b", radius=6)
    return g


# -- a phone ----------------------------------------------------------------------------------------------------------
@register("prop", "collage-phone", summary="A big paper phone, its screen a group the caller writes on")
def phone(cv: Canvas, parent, x: float, y: float, w: float, h: float, screen: str = "#fffaf0", tilt: float = 0.0):
    """A phone ``w`` by ``h`` with its top-left at ``x, y``, turned ``tilt`` degrees about its centre; returns the
    screen's group, its origin at the screen's top-left, :data:`BEZEL` inside the frame."""
    _size(w - 2 * BEZEL, "a phone's screen width")
    _size(h - 2 * BEZEL, "a phone's screen height")
    g = cv.group(parent, cv.uid("g"), x=x + w / 2, y=y + h / 2, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut(f"phone-{w}-{h}", _box(w, h), 2), "#23202b"))
    cv.rect(g, -w / 2 + BEZEL, -h / 2 + BEZEL, w - 2 * BEZEL, h - 2 * BEZEL, screen, radius=14)
    cv.ellipse(g, -9, -h / 2 + 7, 13, 13, "#4a4752")
    return cv.group(g, cv.uid("g"), x=-w / 2 + BEZEL, y=-h / 2 + BEZEL)


@register(
    "prop",
    "collage-battery-insert",
    summary="A phone filling the frame with its battery and percentage on it, red when low, then a dead black screen",
)
def battery_insert(
    cv: Canvas,
    parent,
    x: float = 190.0,
    y: float = 420.0,
    w: float = 700.0,
    h: float = 1200.0,
    *,
    levels: Sequence[tuple[float, int]] = ((0.0, 1),),
    dead: float | None = None,
) -> object:
    """A phone ``w`` by ``h`` with its top-left at ``x, y``, the battery on its screen at each of ``levels`` (``(from,
    percent)``, project seconds from 0); from ``dead`` the screen is black. Returns the screen's group."""
    if not levels or levels[0][0] != 0:
        raise EverydayError(f"a battery's level is known from second 0, got {levels!r}")
    times = [at for at, _ in levels]
    if not all(checks.number(t) for t in times) or times != sorted(set(times)):
        raise EverydayError(f"a battery's level changes in rising seconds, got {times!r}")
    if not all(0 <= percent <= 100 for _, percent in levels):
        raise EverydayError(f"a battery runs from 0 to 100 percent, got {levels!r}")
    if dead is not None and not (checks.number(dead) and dead >= 0):
        raise EverydayError(f"a battery dies from second 0 on, got {dead!r}")
    screen = phone(cv, parent, x, y, w, h, screen="#17151f")
    across, down = w - 2 * BEZEL, h - 2 * BEZEL
    case_w, case_h = across * 0.68, across * 0.3
    left, top = (across - case_w) / 2, down * 0.3
    ends: list[float] = [*times[1:], FOREVER]
    for (at, percent), stop in zip(levels, ends, strict=True):
        level = cv.group(screen, cv.uid("g"))
        cv.gate(level, [(at, stop)])
        colour = LOW_BATTERY if percent <= LOW_LEVEL else "#3ddc6e"
        cv.rect(level, left, top, case_w, case_h, "#ffffff00", "#fffaf0", 12, radius=26)
        cv.rect(level, left + case_w, top + case_h * 0.3, 26, case_h * 0.4, "#fffaf0", radius=8)
        fill = max(case_w - 40, 1.0) * max(percent, 2) / 100
        cv.rect(level, left + 20, top + 20, fill, case_h - 40, colour, radius=10)
        _letter(cv, level, "battery", f"{percent}%", 0, top + case_h + 40, across, 260, 200, color=colour)
    if dead is not None:
        black = cv.group(screen, cv.uid("g"))
        cv.gate(black, [(dead, FOREVER)])
        cv.rect(black, 0, 0, across, down, DEAD_SCREEN, radius=14)
    return screen


@register("prop", "collage-bubble", summary="A paper message bubble with its tail, grey for theirs and green for mine")
def bubble(
    cv: Canvas, parent, text: str, x: float, y: float, w: float, h: float, *, size: float, mine: bool = False
) -> object:
    """A message ``w`` by ``h`` with its top-left at ``x, y``: on the left in grey, or ``mine``, on the right in green;
    ``text`` wraps inside it, left-aligned."""
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    fill = "#c9f2c7" if mine else "#ece9f1"
    tail = [(w - 46, h - 6), (w + 4, h + 26), (w - 16, h - 6)] if mine else [(46, h - 6), (-4, h + 26), (16, h - 6)]
    draw_shapes(cv, g, [(collage._poly(tail), fill, INK, collage.EDGE, 1.0)])
    cv.rect(g, 0, 0, w, h, fill, INK, collage.EDGE, radius=30)
    _letter(cv, g, "bubble", text, 26, 0, w - 52, h, size, color=INK, align="start")
    return g


@register("prop", "collage-thumb", summary="A paper thumbs-up, the size of a message, drawn rather than typed")
def thumb(cv: Canvas, parent, x: float, y: float, size: float = 170.0) -> object:
    """A thumbs-up ``size`` tall, centred on ``x, y``."""
    k = round(_size(size, "a thumb's size") / 170.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    fist = [(-52, -14), (74, -14), (82, 76), (-52, 84)]
    digit = [(-34, -14), (-32, -70), (-14, -92), (14, -84), (16, -14)]
    draw_shapes(cv, g, _paper(_cut("thumb-digit", digit, 2), "#f2c14e"))
    draw_shapes(cv, g, _paper(_cut("thumb-fist", fist, 2), "#f2c14e"))
    for y0 in (14, 40, 64):
        cv.line(g, 18, y0, 76, y0, INK, 4)
    return g


# -- a clock ----------------------------------------------------------------------------------------------------------
@register("prop", "collage-alarm-clock", summary="A paper bedside clock with lit red digits")
def alarm_clock(cv: Canvas, parent, x: float, y: float, w: float, text: str) -> object:
    """A clock ``w`` wide with its top-left at ``x, y``, its digits showing ``text``."""
    h = _size(w, "a clock's width") * 0.5
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    draw_shapes(cv, g, _paper(_cut("alarm-clock", [(0, 0), (w, 0), (w, h), (0, h)], 3), "#2b2d42"))
    cv.rect(g, 22, 22, w - 44, h - 44, "#160c10", radius=10)
    _letter(cv, g, "clock", text, 22, 22, w - 44, h - 44, round(h * 0.56), color="#ff4d4d")
    return g


# -- in bed, at table -------------------------------------------------------------------------------------------------
@register("prop", "collage-cereal-box", summary="A paper cereal box with a bowl on its front and no brand")
def cereal_box(cv: Canvas, parent, x: float, y: float, w: float, h: float, tilt: float = 0.0) -> object:
    """A box ``w`` by ``h`` with its top-left at ``x, y``, turned ``tilt`` degrees about its centre."""
    _size(w, "a box's width")
    _size(h, "a box's height")
    g = cv.group(parent, cv.uid("g"), x=x + w / 2, y=y + h / 2, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut("cereal-box", _box(w, h), 3), "#ffca3a"))
    cv.rect(g, -w / 2 + 12, -h * 0.34, w - 24, h * 0.16, "#e63946")
    cv.ellipse(g, -w * 0.34, h * 0.02, w * 0.68, h * 0.26, "#fffaf0", INK, 4)
    for dx, dy in ((-0.14, 0.05), (0.02, 0.03), (0.14, 0.07), (-0.04, 0.09)):
        cv.ellipse(g, w * dx - 13, h * dy, 26, 22, "#d9913a", INK, 2)
    return g


@register("prop", "collage-duvet", summary="The front of a duvet, its folds in paper: the seated busts sink into it")
def duvet(cv: Canvas, parent, top: float = BED_TOP, colour: str = "#51629e") -> object:
    """A duvet across the frame from ``top`` down: in a shot's ``front``, it hides where the busts end."""
    g = cv.group(parent, cv.uid("g"))
    wave = [(x, top + 14 * math.sin(x / 130)) for x in range(-60, 1200, 60)]
    draw_shapes(cv, g, _paper(wave + [(1200, 1990), (-60, 1990)], colour))
    for x0, x1, y in ((90, 420, 1730), (560, 980, 1700), (300, 760, 1820)):
        cv.path(g, f"M{x0} {y} Q{(x0 + x1) / 2} {y + 34} {x1} {y}", stroke="#39477a", sw=7)
    return g


@register(
    "prop", "collage-tablecloth", summary="The near edge of a laid table: a paper cloth the seated busts sink into"
)
def tablecloth(cv: Canvas, parent, top: float = TABLE_TOP, colour: str = "#f4ecd8") -> object:
    """A table across the frame from ``top`` down, in a shot's ``front``."""
    g = cv.group(parent, cv.uid("g"))
    draw_shapes(cv, g, _paper([(-60, top), (1140, top), (1140, 1990), (-60, 1990)], colour))
    for x in range(40, 1080, 200):
        cv.line(g, x, top + 8, x, 1920, "#e3d6b8", 8)
    return g


@register("prop", "collage-salt-shaker", summary="A paper salt shaker with a dotted steel cap")
def salt_shaker(cv: Canvas, parent, x: float, y: float, size: float = 140.0) -> object:
    """A shaker ``size`` tall, its base centred on ``x, y``."""
    k = round(_size(size, "a shaker's size") / 140.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=k, scaleY=k)
    draw_shapes(cv, g, _paper(_cut("salt-body", [(-34, -96), (34, -96), (50, 0), (-50, 0)], 2), "#fffaf0"))
    cap = [(-34, -96), (-30, -128), (-12, -140), (12, -140), (30, -128), (34, -96)]
    draw_shapes(cv, g, _paper(_cut("salt-cap", cap, 1), "#adb5bd", shadow=False))
    for dx in (-12, 0, 12):
        cv.ellipse(g, dx - 3, -124, 7, 7, INK)
    return g


# -- chips ------------------------------------------------------------------------------------------------------------
@register("prop", "collage-chip-bag", summary="A puffed paper chip bag with crimped ends and a label, no brand")
def chip_bag(
    cv: Canvas, parent, x: float, y: float, w: float, h: float, label: str, colour: str = "#e63946", *, size: float = 80
) -> object:
    """A bag ``w`` by ``h`` centred on ``x, y`` with ``label`` across it; returns the group, which a caller may key:
    its origin is the bag's centre, so scaling it down lets the air out."""
    _size(w, "a bag's width")
    _size(h, "a bag's height")
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    teeth = 12
    top = [(-w / 2 + w * i / teeth, -h / 2 + (0 if i % 2 else 18)) for i in range(teeth + 1)]
    bottom = [(w / 2 - w * i / teeth, h / 2 - (0 if i % 2 else 18)) for i in range(teeth + 1)]
    bulge = [(w / 2 + 26 * math.sin(math.pi * i / 6), -h / 2 + h * i / 6) for i in range(1, 6)]
    back = [(-x_, y_) for x_, y_ in reversed(bulge)]
    draw_shapes(cv, g, _paper(_cut(f"bag-{label}", top + bulge + bottom + back, 1.5), colour))
    cv.rect(g, -w / 2 + 4, -h / 2 + 26, w - 8, 9, "#00000030")
    cv.rect(g, -w / 2 + 4, h / 2 - 34, w - 8, 9, "#00000030")
    shine = cv.grad("collage-bag-shine", [(0, "#ffffff00"), (0.5, "#ffffff66"), (1, "#ffffff00")], (0, 0, 1, 0))
    cv.rect(g, -w * 0.36, -h * 0.4, w * 0.24, h * 0.8, shine)
    panel = [(-w * 0.42, -h * 0.2), (w * 0.42, -h * 0.2), (w * 0.42, h * 0.2), (-w * 0.42, h * 0.2)]
    draw_shapes(cv, g, _paper(_cut(f"bag-label-{label}", panel, 2), "#fffaf0", shadow=False))
    _letter(cv, g, "bag", label, -w * 0.4, -h * 0.2, w * 0.8, h * 0.4, size, color=INK)
    return g


def _whole(cv: Canvas, g) -> None:
    draw_shapes(cv, g, _paper(_ring("chip-whole", 0, 0, 104, 88, 14, 0.09), "#f2c14e"))
    for x0, x1, y in ((-62, 44, -30), (-70, 62, 6), (-44, 50, 40)):
        cv.path(g, f"M{x0} {y} Q{(x0 + x1) / 2} {y + 16} {x1} {y}", stroke="#c98a1b", sw=6)


def _half(cv: Canvas, g) -> None:
    edge = [(-98, -30), (-60, -74), (-6, -86), (6, -40), (-14, 2), (12, 44), (-8, 82), (-68, 62), (-100, 18)]
    draw_shapes(cv, g, _paper(_cut("chip-half", edge, 2), "#f2c14e"))
    cv.path(g, "M-70 -24 Q-40 -8 -18 -26", stroke="#c98a1b", sw=6)
    cv.path(g, "M-74 26 Q-46 40 -22 24", stroke="#c98a1b", sw=6)


def _crumb(cv: Canvas, g) -> None:
    draw_shapes(cv, g, _paper(_ring("chip-crumb", 0, 0, 30, 24, 8, 0.2), "#f2c14e"))


CHIPS: dict[str, Callable[[Canvas, object], None]] = {"whole": _whole, "half": _half, "crumb": _crumb}


@register("prop", "collage-chip", summary="A paper potato chip: whole, broken in half, or the last crumb")
def chip(cv: Canvas, parent, x: float, y: float, part: str = "whole", size: float = 210.0, tilt: float = 0.0) -> object:
    """The chip ``part`` (:data:`CHIPS`) centred on ``x, y``, scaled by ``size`` (a whole chip's width)."""
    if part not in CHIPS:
        raise EverydayError(f"no chip part {part!r}; one of {sorted(CHIPS)}")
    k = round(_size(size, "a chip's size") / 210.0, 4)
    g = cv.group(parent, cv.uid("g"), x=x, y=y, rotation=tilt, scaleX=k, scaleY=k)
    CHIPS[part](cv, g)
    return g


@register("prop", "collage-certificate", summary="A paper certificate with a double border and a red seal")
def certificate(
    cv: Canvas, parent, text: str, x: float, y: float, w: float, h: float, *, size: float, tilt: float = 0.0
):
    """A certificate ``w`` by ``h`` with its top-left at ``x, y``, turned ``tilt`` degrees, saying ``text``."""
    _size(w, "a certificate's width")
    _size(h, "a certificate's height")
    g = cv.group(parent, cv.uid("g"), x=x + w / 2, y=y + h / 2, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut("certificate", _box(w, h), 3), "#fffaf0"))
    cv.rect(g, -w / 2 + 14, -h / 2 + 14, w - 28, h - 28, "#00000000", "#b08d2e", 5)
    _letter(cv, g, "certificate", text, -w / 2 + 34, -h / 2 + 20, w - 68, h - 84, size, color=INK)
    seal = _ring("certificate-seal", w / 2 - 62, h / 2 - 60, 40, 40, 16, 0.12)
    draw_shapes(cv, g, _paper(seal, "#c1121f", shadow=False))
    return g


@register("prop", "collage-snapshot", summary="A snapshot of a chip: a white-bordered print on a dark ground")
def snapshot(cv: Canvas, parent, x: float, y: float, w: float, tilt: float = 0.0) -> object:
    """A print ``w`` wide with its top-left at ``x, y``, turned ``tilt`` degrees, of one whole chip."""
    h = _size(w, "a print's width") * 1.16
    g = cv.group(parent, cv.uid("g"), x=x + w / 2, y=y + h / 2, rotation=tilt)
    draw_shapes(cv, g, _paper(_cut("snapshot", _box(w, h), 2), "#fffdf7"))
    cv.rect(g, -w / 2 + 20, -h / 2 + 20, w - 40, w - 40, "#2b2d42")
    chip(cv, g, 0, -h / 2 + w / 2, size=w * 0.62)
    return g


@register("prop", "collage-gust", summary="Paper-white lines of rushing air, streaming from a point towards another")
def gust(cv: Canvas, parent, frm: Point, to: Point, start: float, end: float, *, lines: int = 5) -> object:
    """``lines`` strokes streaming from ``frm`` to ``to`` over and over from ``start`` to ``end``, project seconds."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise EverydayError(f"a gust runs forward, got {start!r} to {end!r}")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    (x0, y0), (x1, y1) = frm, to
    angle = math.atan2(y1 - y0, x1 - x0)
    nx, ny = -math.sin(angle), math.cos(angle)
    for i in range(lines):
        off = (i - (lines - 1) / 2) * 46
        stroke = cv.group(g, cv.uid("g"))
        cv.line(stroke, 0, 0, 120 * math.cos(angle), 120 * math.sin(angle), "#fffaf0", 9)
        pass_time = 0.42
        t, xs, ys, os = start + i * 0.07, [], [], []
        while t < end:
            b = min(t + pass_time, end)
            xs += [(t, round(x0 + nx * off, 1)), (b - 0.001, round(x1 + nx * off, 1))]
            ys += [(t, round(y0 + ny * off, 1)), (b - 0.001, round(y1 + ny * off, 1))]
            os += [(t, 0.9), (b - 0.001, 0.0)]
            t = b
        if xs:
            cv.keys(stroke, "x", xs, hold=False, local=False)
            cv.keys(stroke, "y", ys, hold=False, local=False)
            cv.keys(stroke, "opacity", os, hold=False, local=False)
    return g


# -- payday -----------------------------------------------------------------------------------------------------------
@register("prop", "collage-bill", summary="A paper bill with a jagged mouth that walks in and takes its bite")
def bill(
    cv: Canvas,
    parent,
    text: str,
    x: float,
    y: float,
    w: float = 330.0,
    h: float = 220.0,
    *,
    size: float = 52,
    legs: bool = True,
) -> object:
    """A bill ``w`` by ``h`` centred on ``x, y``, saying ``text``; returns the group, which a caller keys to walk.
    Without ``legs`` it is paper that falls or lands, with no feet to stand on."""
    _size(w, "a bill's width")
    _size(h, "a bill's height")
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    draw_shapes(cv, g, _paper(_cut(f"bill-{text}", _box(w, h), 3), "#fffaf0"))
    teeth = 9
    jaw = [(-w / 2 + w * i / teeth, -h / 2 + (0 if i % 2 else 34)) for i in range(teeth + 1)]
    draw_shapes(cv, g, [(collage._poly(jaw + [(w / 2, -h / 2 - 6), (-w / 2, -h / 2 - 6)]), "#c1121f", INK, 4.0, 1.0)])
    _letter(cv, g, "bill", text, -w / 2 + 16, -h / 2 + 36, w - 32, h - 44, size, color=INK)
    for dx in (-w * 0.2, w * 0.2) if legs else ():
        cv.line(g, dx, h / 2, dx, h / 2 + 34, INK, 10)
        cv.line(g, dx, h / 2 + 34, dx + 30, h / 2 + 34, INK, 10)
    return g


def _piece_y(y0: float, speed: float, start: float, end: float, turn: float | None) -> list[tuple[float, float]]:
    if turn is None or turn >= end:
        return [(start, y0), (end, round(y0 + speed * (end - start), 1))]
    at_turn = y0 + speed * (turn - start)
    return [(start, y0), (turn, round(at_turn, 1)), (end, round(at_turn - 1.6 * speed * (end - turn), 1))]


@register("prop", "collage-confetti", summary="Paper confetti in mid-fall, which can turn and fall back upwards")
def confetti(
    cv: Canvas, parent, start: float, end: float, *, turn: float | None = None, count: int = 34, key: str = "confetti"
) -> object:
    """``count`` paper bits falling across the frame from ``start`` to ``end``, project seconds, already in the air on
    the first frame; from ``turn`` every bit goes back up, a little faster."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise EverydayError(f"confetti falls forward in time, got {start!r} to {end!r}")
    if turn is not None and not (checks.number(turn) and start <= turn):
        raise EverydayError(f"confetti turns after it starts, got {turn!r}")
    rng = random.Random(key)
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    for i in range(count):
        colour = CONFETTI[i % len(CONFETTI)]
        x, speed = rng.uniform(30, 1050), rng.uniform(70, 150)
        y0 = rng.uniform(-400, 1500)
        w, h = rng.uniform(26, 40), rng.uniform(14, 24)
        bit = cv.group(g, cv.uid("g"), x=round(x, 1), y=round(y0, 1), rotation=round(rng.uniform(0, 180), 1))
        cv.rect(bit, -w / 2, -h / 2, w, h, colour, INK, 2)
        cv.keys(bit, "y", _piece_y(round(y0, 1), speed, start, end, turn), hold=False, local=False)
        spin = rng.uniform(120, 300) * rng.choice((-1, 1))
        cv.keys(bit, "rotation", [(start, 0), (end, round(spin * (end - start), 1))], hold=False, local=False)
    return g


def shoulder(who: str | Look) -> Point:
    """Where ``who``'s screen-left arm starts in a single, for an arm drawn by the scene over the ``free`` pose."""
    look = LOOKS[who] if isinstance(who, str) else who
    return (CX - HALF_WIDTH[look.build] + 46, SHOULDER_Y[look.build] + 50)


@register("prop", "collage-arm", summary="A character's arm on its own, sleeve and hand, for reaching past the pose")
def arm(
    cv: Canvas, parent, who: str | Look, frm: Point, to: Point, *, width: float = 72.0, hand: bool = True
) -> object:
    """``who``'s arm from ``frm`` (off the frame, usually) to its hand at ``to``; returns the group, which a caller
    keys to bring it in. ``hand=False`` is an upper arm, which ends in the elbow the forearm starts from."""
    look = LOOKS[who] if isinstance(who, str) else who
    g = cv.group(parent, cv.uid("g"))
    draw_shapes(cv, g, _sleeve(look, "reach", frm, to, width) + (_hand(look, "reach-hand", *to, r=38) if hand else []))
    return g


def chew(track: Sequence[tuple[float, str]], start: float, end: float) -> list[tuple[float, str]]:
    """The viseme ``track`` with a chewing mouth from ``start`` to ``end``, project seconds: open and shut every half
    :data:`CHEW`, shut at the end, and whatever the track held outside that span kept."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise EverydayError(f"chewing runs forward, got {start!r} to {end!r}")
    out = [(t, v) for t, v in track if t < start or t > end]
    n = int((end - start) / (CHEW / 2))
    out += [(round(start + i * CHEW / 2, 6), "open" if i % 2 == 0 else "closed") for i in range(n)]
    out.append((round(start + n * CHEW / 2, 6), "closed"))
    return sorted(out)

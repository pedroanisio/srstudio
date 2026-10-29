"""Toon sets and props, second round: an office kitchen and a home office at night, and the props that live in
them: a coffee machine that brews, a desk lamp that can be switched off, a plant that sways and a wall calendar
whose pages tear off.

They are drawn more finely than the first sets (:mod:`srstudio.toon`, :mod:`srstudio.toon_props`). The objects are
inked with the brush (:mod:`srstudio.brush`), so their outlines swell and taper like the characters'. Surfaces carry
light: a highlight on glass, steel and glaze, a soft shadow under each object, glows drawn as radial gradients.
Small things move: stars twinkle, string lights pulse, lit windows go out, leaves sway, the coffee drips.

Every measure is a reference screen pixel (:func:`srstudio.toon.fx`/``fy``), like the rest of the style. Every
animation is keyed on the composition clock. Looping motion runs from 0 to ``end`` (project seconds) and is left out
when ``end`` is 0, so a still frame of a set is the same with or without it.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

from . import brush
from .brush import Point, Shape
from .canvas import Canvas
from .registry import register
from .toon import CHAIR_D, FINE_W, INK_W, ToonDataError, _d, _path, fh, fx, fy, shape_d

__all__ = [
    "kitchen",
    "home",
    "coffee_machine",
    "desk_lamp",
    "plant",
    "calendar",
    "call_centre",
    "WAITING_MAX",
    "cycle_keys",
    "parse_pages",
    "NOTE_MAX",
    "note_insert",
]

INK = 5.5  # the brush's weight for an object's outline, reference pixels (as the characters')
FINE = 3.0
SHADOW = "#1b1430"  # soft shadows, at low opacity
GLINT = "#ffffff"
NOTE_MAX = 14  # the longest note the fridge door takes, in characters

# the office kitchen
KITCHEN_WALL = (("0", "#fff6e0"), ("0.55", "#fbe6bf"), ("1", "#f4d6a6"))
CABINET = "#7cc6b4"
CABINET_PANEL = "#a3dccd"
HANDLE = "#eef3f4"
TILE = "#eaf4f6"
GROUT = "#bfd3d9"
COUNTER = "#dc9d63"
COUNTER_EDGE = "#b97b47"
LOWER = "#68b3a1"
FRIDGE = ("#ffffff", "#e9eff5", "#d3dde7")
FRIDGE_HANDLE = "#a3afbb"
KITCHEN_CHAIR = "#f2a65a"
KITCHEN_CHAIR_LIGHT = "#f7c28a"
MAGNETS = ("#ef6f6c", "#f2c14e", "#5fa8e8")
NOTE = "#fff3a3"
NOTE_INK = "#1e293b"
CABINET_TOP, CABINET_BOTTOM = 150, 300
COUNTER_Y = 500  # the counter's top: props stand on it above the laptop lid (which starts at 523)
FRIDGE_X, FRIDGE_TOP = 474, 160

# the home office at night
HOME_WALL = (("0", "#575696"), ("0.6", "#7a76b6"), ("1", "#968fc6"))
NIGHT = (("0", "#121a3b"), ("0.65", "#2c2961"), ("1", "#57397a"))
WINDOW_FRAME = "#efe3d2"
MOON = "#fff2c2"
CRATER = "#efdea6"
STAR = "#fff8dc"
SKYLINE = "#1d1b3c"
LIT = "#ffd36b"
CURTAIN = "#e8706e"
CURTAIN_FOLD = "#c85656"
ROD = "#b88a5a"
SHELF = "#c48a5a"
BOOKS = ("#f2c14e", "#5fb3a3", "#ef6f6c", "#7aa5e8", "#f4a3c0", "#9b8ce0")
HOME_CHAIR = "#2f6f73"
HOME_CHAIR_LIGHT = "#3f8d90"
BULBS = ("#ffd36b", "#ff8fab", "#8be0c8", "#9fc2ff")
SHELF_Y = 190  # the shelf board's top, above the caption pill (which sits at about 253-303)
STARS = ((400, 330), (445, 410), (520, 312), (565, 388), (612, 340), (418, 470), (590, 470), (640, 300), (500, 520))
TWINKLE = 2.4  # seconds per twinkle
WINDOW_BLINK = 7.0  # seconds a lit window in the skyline stays on before it goes out and comes back

# the props
MACHINE = "#3a3f47"
MACHINE_LIGHT = "#59606b"
GLASS = "#cfe8f0"
COFFEE = "#5b3a24"
LED_ON, LED_OFF = "#ff3b30", "#6b2f2f"
DRIP = 0.6  # seconds per drop while brewing
LAMP = "#2fa3a0"
LAMP_DARK = "#227a78"
LAMP_INSIDE = "#fff6d5"
LIGHT = "#ffe9a6"
POT = "#d9774e"
POT_RIM = "#e98f64"
SOIL = "#4a3426"
LEAF = ("#3fa36b", "#2f8a57", "#4cb57a")
STEM = "#2f7a4e"
VEIN = "#7fd19f"
SWAY = 3.2  # seconds per sway of the leaves
SWAY_DEGREES = 2.5
CAL_PAPER = "#ffffff"
CAL_HEADER = "#b42318"
CAL_W, CAL_H = 100, 116
FLIP = 0.35  # seconds a torn page takes to fall
PAGE = re.compile(r"^[A-Z]{3} [0-9]{1,2}$")

# the call centre
CENTRE_WALL = (("0", "#eef2f8"), ("0.6", "#dbe3ee"), ("1", "#c7d2e1"))
PARTITION = "#5d7ea8"
PARTITION_FLECK = "#7d9cc4"
PARTITION_CAP = "#c9d1dc"
CENTRE_CHAIR = "#3b4a63"
CENTRE_CHAIR_LIGHT = "#56688a"
BOARD = "#1f2430"
BOARD_FRAME = "#9aa3b2"
LED = "#ff4d3d"
LED_DIM = "#5a2a28"
POSTER = "#fff7e8"
POSTER_BAND = "#f2a65a"
POSTER_INK = "#2b2f3a"
WAITING_MAX = 9999  # the most calls the board can count
BLINK = 1.0  # seconds per blink of the board's lamp

Spans = Sequence[tuple[float, float]]


# -- drawing helpers ------------------------------------------------------------------------------------------------
def _fill(cv: Canvas, g, shape: Shape, fill: str, opacity: float | None = None):
    """A brushed shape filled flat, no stroke; ``opacity`` for light and shadow."""
    kw = {} if opacity is None else {"opacity": opacity}
    return cv.path(g, shape_d(shape), fill=fill, stroke=cv.clear, sw=0, **kw)


def _inked(cv: Canvas, g, points: Sequence[Point], fill: str, weight: float = INK, steps: int = 3) -> None:
    """An object's body: an ink rim the brush draws round ``points``, then the fill inside it."""
    _fill(cv, g, brush.rim(points, weight, brush.EVEN, steps=steps), cv.ink)
    _fill(cv, g, brush.outline(points, steps=steps), fill)


def _line(cv: Canvas, g, points: Sequence[Point], weight: float = FINE, colour: str | None = None, opacity=None):
    """A tapered brush line."""
    _fill(cv, g, brush.stroke(points, weight), cv.ink if colour is None else colour, opacity)


def _glow(cv: Canvas, g, name: str, cx: float, cy: float, r: float, colour: str):
    """A soft round glow of ``colour`` fading to nothing at ``r``."""
    paint = cv.rgrad(name, ((0, colour + "cc"), (0.45, colour + "55"), (1, colour + "00")))
    return cv.ellipse(g, fx(cx - r), fy(cy - r), fh(2 * r), fh(2 * r), paint)


def _shadow(cv: Canvas, g, cx: float, y: float, w: float, h: float = 8.0, opacity: float = 0.18) -> None:
    cv.ellipse(g, fx(cx - w / 2), fy(y - h / 2), fh(w), fh(h), SHADOW, opacity=opacity)


def _check_end(end: float) -> float:
    if isinstance(end, bool) or not isinstance(end, int | float) or not (math.isfinite(end) and end >= 0):
        raise ToonDataError(f"end is a number of seconds >= 0, got {end!r}")
    return float(end)


def _check_spans(spans: Spans, what: str) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for span in spans:
        if not (isinstance(span, tuple | list) and len(span) == 2):
            raise ToonDataError(f"{what} spans are (start, end) pairs, got {span!r}")
        a, b = span
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a < b):
            raise ToonDataError(f"{what} spans need 0 <= start < end, got {span!r}")
        if out and a < out[-1][1]:
            raise ToonDataError(f"{what} spans must be in order and must not overlap")
        out.append((float(a), float(b)))
    return out


def cycle_keys(
    pattern: Sequence[tuple[float, float]], period: float, start: float, end: float, phase: float = 0.0
) -> list[tuple[float, float]]:
    """Keys that repeat ``pattern`` (``(offset, value)`` within one ``period``, offsets in ``[0, period)``) from
    ``start`` to ``end``, shifted by ``phase`` seconds; the value at ``start`` and at ``end`` is keyed too."""
    if not (math.isfinite(period) and period > 0):
        raise ToonDataError(f"a cycle needs a period over 0 s, got {period!r}")
    if not pattern or any(not 0 <= o < period for o, _ in pattern):
        raise ToonDataError("a cycle's offsets lie in [0, period)")
    if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
        raise ToonDataError(f"a cycle runs from a start to a later end, got {start!r}..{end!r}")

    def value_at(t: float) -> float:
        local = (t - start - phase) % period
        before = [v for o, v in pattern if o <= local + 1e-9]
        return before[-1] if before else pattern[-1][1]

    keys = {round(start, 6): value_at(start)}
    k = math.floor((start - start - phase) / period)
    while True:
        base = start + phase + k * period
        if base >= end:
            break
        for o, v in pattern:
            t = base + o
            if start < t < end:
                keys[round(t, 6)] = v
        k += 1
    keys[round(end, 6)] = value_at(end)
    return sorted(keys.items())


# -- the office kitchen ---------------------------------------------------------------------------------------------
def _tiles(cv: Canvas, g, x0: float, y0: float, x1: float, y1: float) -> None:
    """Subway tiles: the grout as one path of lines, a glint on each tile as one path of small bars."""
    cv.rect(g, fx(x0), fy(y0), fh(x1 - x0), fh(y1 - y0), TILE, cv.clear, 0, radius=0)
    w, h = 52.0, 25.0
    grout, glints = [], []
    row = 0
    y = y0
    while y < y1 - 1:
        grout.append(_d("M", (x0, y), "L", (x1, y)))
        offset = 0.0 if row % 2 == 0 else w / 2
        x = x0 - offset
        while x < x1:
            if x > x0:
                grout.append(_d("M", (x, y), "L", (x, min(y + h, y1))))
            gx = max(x, x0) + 5
            if gx + 14 < min(x + w, x1) and y + 9 < y1:
                glints.append(_d("M", (gx, y + 5), "L", (gx + 14, y + 5), "L", (gx + 14, y + 8), "L", (gx, y + 8), "Z"))
            x += w
        y += h
        row += 1
    cv.path(g, " ".join(grout), fill=cv.clear, stroke=GROUT, sw=2.0)
    cv.path(g, " ".join(glints), fill=GLINT, stroke=cv.clear, sw=0, opacity=0.7)


def _door(cv: Canvas, g, x0: float, y0: float, x1: float, y1: float, colour: str, panel: str, knob_x: float) -> None:
    cv.rect(g, fx(x0), fy(y0), fh(x1 - x0), fh(y1 - y0), colour, cv.ink, INK_W * 0.8, radius=fh(6))
    cv.rect(g, fx(x0 + 12), fy(y0 + 12), fh(x1 - x0 - 24), fh(y1 - y0 - 24), panel, cv.ink, FINE_W * 0.6, radius=fh(4))
    cv.rect(g, fx(x0 + 18), fy(y0 + 16), fh(x1 - x0 - 36), fh(5), GLINT, cv.clear, 0, radius=fh(2), opacity=0.45)
    cv.rect(g, fx(knob_x - 4), fy((y0 + y1) / 2 - 16), fh(8), fh(32), HANDLE, cv.ink, FINE_W * 0.5, radius=fh(4))


@register(
    "location",
    "toon-kitchen",
    summary="The office kitchen: tiled backsplash, mint cabinets, a counter for props and a tall fridge with a note",
)
def kitchen(cv: Canvas, parent, note: str = "") -> None:
    """The office kitchen behind the character: a warm wall, mint upper and lower cabinets, a white subway-tile
    backsplash with a glint on every tile, a wooden counter at :data:`COUNTER_Y` that props stand on, and a tall
    fridge at the right with magnets and, when ``note`` is given (1 to :data:`NOTE_MAX` characters), a note stuck
    to its door. The signature marks are the desk's (:func:`srstudio.toon.desk`)."""
    if note and (len(note) > NOTE_MAX or not note.strip()):
        raise ToonDataError(f"the fridge note is 1 to {NOTE_MAX} characters")
    g = cv.group(parent, cv.uid("g"))
    wall = cv.grad("toon-kitchen-wall", [(float(o), c) for o, c in KITCHEN_WALL], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, wall)
    # the upper cabinets, their shadow on the tiles, the backsplash, the counter and the lower cabinets
    _tiles(cv, g, -10, CABINET_BOTTOM, FRIDGE_X, COUNTER_Y)
    cv.rect(g, fx(-10), fy(CABINET_BOTTOM), fh(FRIDGE_X + 10), fh(16), SHADOW, cv.clear, 0, radius=0, opacity=0.12)
    for x0, x1, knob in ((-20, 150, 136), (150, 320, 164), (320, FRIDGE_X - 4, 334)):
        _door(cv, g, x0, CABINET_TOP, x1, CABINET_BOTTOM, CABINET, CABINET_PANEL, knob)
    cv.rect(g, fx(-10), fy(CABINET_TOP - 12), fh(FRIDGE_X + 6), fh(14), CABINET, cv.ink, INK_W * 0.8, radius=0)
    for x0, x1, knob in ((-20, 210, 196), (210, FRIDGE_X - 4, 224)):
        _door(cv, g, x0, COUNTER_Y + 30, x1, 900, LOWER, CABINET, knob)
    cv.rect(g, fx(-10), fy(COUNTER_Y), fh(FRIDGE_X + 6), fh(20), COUNTER, cv.ink, INK_W * 0.8, radius=fh(4))
    cv.rect(g, fx(-10), fy(COUNTER_Y + 20), fh(FRIDGE_X + 6), fh(12), COUNTER_EDGE, cv.ink, FINE_W * 0.6, radius=0)
    cv.rect(g, fx(0), fy(COUNTER_Y + 4), fh(FRIDGE_X - 10), fh(4), GLINT, cv.clear, 0, radius=fh(2), opacity=0.35)
    _fridge(cv, g, note)
    # the chair back: wood, with a lighter rail
    _path(cv, g, CHAIR_D, KITCHEN_CHAIR)
    _line(cv, g, [(40, 600), (150, 584), (270, 596)], 10.0, KITCHEN_CHAIR_LIGHT)


def _fridge(cv: Canvas, g, note: str) -> None:
    x0, x1, top, bottom = FRIDGE_X, 680, FRIDGE_TOP, 900
    side = cv.grad("toon-fridge", [(0.0, FRIDGE[0]), (0.55, FRIDGE[1]), (1.0, FRIDGE[2])], (0, 0, 1, 0))
    cv.rect(g, fx(x0 - 10), fy(top + 10), fh(14), fh(bottom - top), SHADOW, cv.clear, 0, radius=fh(10), opacity=0.14)
    cv.rect(g, fx(x0), fy(top), fh(x1 - x0), fh(bottom - top), side, cv.ink, INK_W, radius=fh(22))
    seam = top + 200
    _path(cv, g, _d("M", (x0, seam), "L", (x1, seam)), None, FINE_W)
    for y0, y1 in ((top + 70, top + 170), (seam + 40, seam + 230)):
        cv.rect(g, fx(x0 + 14), fy(y0), fh(12), fh(y1 - y0), FRIDGE_HANDLE, cv.ink, FINE_W * 0.6, radius=fh(6))
    for x in (x0 + 72, x0 + 88):  # the steel's glint
        _line(cv, g, [(x, top + 30), (x + 2, top + 150)], 5.0, GLINT, 0.9)
    for i, (mx, my) in enumerate(((x0 + 60, seam + 30), (x0 + 96, seam + 52), (x0 + 50, seam + 200))):
        cv.ellipse(g, fx(mx - 9), fy(my - 9), fh(18), fh(18), MAGNETS[i], cv.ink, FINE_W * 0.6)
        cv.ellipse(g, fx(mx - 4), fy(my - 6), fh(5), fh(4), GLINT, opacity=0.8)
    if note:
        n = cv.group(g, cv.uid("g"), anchorX=fx(x0 + 75), anchorY=fy(seam + 110), x=fx(x0 + 75), y=fy(seam + 110))
        n.rotation = 4
        cv.rect(n, fx(x0 + 34), fy(seam + 72), fh(86), fh(80), NOTE, cv.ink, FINE_W * 0.6, radius=fh(2))
        cv.ellipse(n, fx(x0 + 70), fy(seam + 64), fh(14), fh(14), MAGNETS[0], cv.ink, FINE_W * 0.5)
        cv.text(n, cv.uid("fridge-note"), note, fx(x0 + 36), fy(seam + 82), int(fh(82)), int(fh(66)), 24,
                color=NOTE_INK, wrap="word")  # fmt: skip


INSERT_NOTE = 760  # the note's side in the insert, frame pixels
INSERT_TEXT = 128  # the insert's lettering, frame pixels: legible on a phone
INSERT_PUSH = 1.04  # the slow push through the insert


@register(
    "prop",
    "toon-note-insert",
    summary="A full-frame close-up of the fridge note: the evidence cut in, legible on a phone",
    style="toon",
)
def note_insert(cv: Canvas, parent, text: str, start: float, end: float) -> None:
    """A full-frame insert of a note on the fridge door from ``start`` to ``end`` (project seconds): the steel with
    its glint and handle, two magnets and the note, tipped and lettered at :data:`INSERT_TEXT` pixels, under a slow
    push. Cut it in over a shot (into the props in front) when the note itself is the joke; the note on the fridge
    in the wide shot is too small to read on a phone. ``text`` is 1 to :data:`NOTE_MAX` characters."""
    if not text.strip() or len(text) > NOTE_MAX:
        raise ToonDataError(f"the insert's note is 1 to {NOTE_MAX} characters")
    if not 0 <= start < end:
        raise ToonDataError(f"the insert starts before it ends, from 0: {start}..{end}")
    w, h = cv.width, cv.height
    g = cv.group(parent, cv.uid("g"), start=start, end=end, anchorX=w / 2, anchorY=h / 2, x=w / 2, y=h / 2)
    steel = cv.grad("toon-note-insert-steel", [(0.0, FRIDGE[0]), (0.6, FRIDGE[1]), (1.0, FRIDGE[2])], (0, 0, 1, 1))
    cv.rect(g, 0, 0, w, h, steel, cv.clear, 0, radius=0)
    cv.rect(g, 70, -20, 54, h * 0.62, FRIDGE_HANDLE, cv.ink, INK_W * 1.6, radius=27)
    for x in (230, 270):  # the steel's glint
        cv.rect(g, x, 120, 12, 520, GLINT, cv.clear, 0, radius=6, opacity=0.9)
    x0, y0 = (w - INSERT_NOTE) / 2 + 30, (h - INSERT_NOTE) / 2
    n = cv.group(g, cv.uid("g"), anchorX=w / 2, anchorY=h / 2, x=w / 2, y=h / 2)
    n.rotation = 4
    cv.rect(n, x0 + 18, y0 + 26, INSERT_NOTE, INSERT_NOTE, SHADOW, cv.clear, 0, radius=8, opacity=0.18)
    cv.rect(n, x0, y0, INSERT_NOTE, INSERT_NOTE, NOTE, cv.ink, INK_W * 1.6, radius=8)
    cv.text(n, cv.uid("insert-note"), text, x0 + 50, y0 + 150, INSERT_NOTE - 100, INSERT_NOTE - 260, INSERT_TEXT,
            color=NOTE_INK, wrap="word")  # fmt: skip
    for i, (mx, my, r) in enumerate(((w / 2 + 20, y0 - 10, 46), (w - 150, 260, 38))):
        cv.ellipse(n if i == 0 else g, mx - r, my - r, 2 * r, 2 * r, MAGNETS[i], cv.ink, INK_W * 1.2)
        cv.ellipse(n if i == 0 else g, mx - r * 0.45, my - r * 0.6, r * 0.5, r * 0.4, GLINT, opacity=0.8)
    cv.keys(g, "scaleX", [(start, 1.0), (end, INSERT_PUSH)], hold=False)
    cv.keys(g, "scaleY", [(start, 1.0), (end, INSERT_PUSH)], hold=False)


# -- the home office at night ---------------------------------------------------------------------------------------
def _star(cx: float, cy: float, r: float) -> list[Point]:
    """A four-point twinkle."""
    k = r * 0.28
    return [(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r), (cx - k, cy + k),
            (cx - r, cy), (cx - k, cy - k)]  # fmt: skip


def _skyline(cv: Canvas, g, end: float) -> None:
    roofs = [(360, 530), (392, 530), (392, 490), (440, 490), (440, 512), (470, 512), (470, 462), (512, 462),
             (512, 500), (548, 500), (548, 480), (590, 480), (590, 450), (622, 450), (622, 505),
             (680, 505)]  # fmt: skip
    d = _d("M", (360, 696), *[c for p in roofs for c in ("L", p)], "L", (680, 696), "Z")
    _path(cv, g, d, SKYLINE, 0)
    windows = [(400, 502), (416, 502), (452, 522), (482, 476), (482, 494), (496, 476), (522, 512), (560, 494),
               (600, 464), (600, 482), (634, 518), (650, 518), (560, 520)]  # fmt: skip
    for i, (x, y) in enumerate(windows):
        w = cv.rect(g, fx(x), fy(y), fh(8), fh(10), LIT, cv.clear, 0, radius=fh(1))
        if end and i % 4 == 1:  # every fourth window goes out for a while and comes back
            off = WINDOW_BLINK * (0.35 + 0.15 * (i % 3))
            cv.keys(w, "opacity", cycle_keys([(0.0, 1), (off, 0)], WINDOW_BLINK + i * 0.7, 0.0, end, phase=i * 1.3))


def _curtain(cv: Canvas, g) -> None:
    """A gathered curtain: straight under the rod, flaring a little, with a scalloped hem and deep folds."""
    hem = [(400, 712), (386, 724), (372, 712), (358, 724), (344, 712), (330, 724), (318, 712)]
    d = _d("M", (322, 254), "L", (394, 254), "Q", (392, 480), (400, 712),
           *[c for a, b in zip(hem, hem[1:], strict=False) for c in ("Q", ((a[0] + b[0]) / 2, b[1] + 8), b)],
           "Q", (316, 480), (322, 254), "Z")  # fmt: skip
    _path(cv, g, d, CURTAIN, INK_W)
    for x in (344, 358, 372, 386):
        _line(cv, g, [(x - 2, 262), (x, 480), (x, 708)], 5.0, CURTAIN_FOLD)
    _line(cv, g, [(330, 266), (328, 480), (330, 690)], 4.0, GLINT, 0.4)
    _path(cv, g, _d("M", (318, 262), "L", (398, 262)), None, FINE_W)


def _string_lights(cv: Canvas, g, end: float) -> None:
    hooks = [(330, 248), (465, 268), (600, 248)]
    wire = []
    for (ax, ay), (bx, by) in zip(hooks, hooks[1:], strict=False):
        for k in range(9):
            s = k / 8
            wire.append((ax + (bx - ax) * s, ay + (by - ay) * s + 22 * math.sin(math.pi * s)))
    _line(cv, g, wire, 2.6)
    groups = [cv.group(g, cv.uid("g")), cv.group(g, cv.uid("g"))]
    for i, (x, y) in enumerate(wire[1::2]):
        col = BULBS[i % len(BULBS)]
        bulb = groups[i % 2]
        _glow(cv, bulb, f"toon-bulb-{i % len(BULBS)}", x, y + 9, 20, col)
        _inked(cv, bulb, [(x - 5, y + 2), (x + 5, y + 2), (x + 6, y + 14), (x, y + 19), (x - 6, y + 14)], col, 2.4, 4)
        cv.ellipse(bulb, fx(x - 3), fy(y + 6), fh(3), fh(5), GLINT, opacity=0.8)
    if end:
        for k, bulb in enumerate(groups):
            cv.keys(bulb, "opacity", cycle_keys([(0.0, 1.0), (1.1, 0.55)], 2.2, 0.0, end, phase=k * 1.1), hold=False)


def _book(cv: Canvas, g, corners: Sequence[Point], colour: str) -> None:
    """A book's spine: crisp corners in ink, a band near the top and a glint down its edge."""
    _path(cv, g, _d("M", corners[0], *[c for p in corners[1:] for c in ("L", p)], "Z"), colour, FINE_W)
    (bl, br, tr, tl) = corners

    def at(a: Point, b: Point, s: float) -> Point:
        return (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)

    band = [at(bl, tl, 0.78), at(br, tr, 0.78), at(br, tr, 0.86), at(bl, tl, 0.86)]
    _path(cv, g, _d("M", band[0], "L", band[1], "L", band[2], "L", band[3], "Z"), SHADOW, 0).opacity = 0.25
    _line(cv, g, [at(bl, tl, 0.08), at(bl, tl, 0.7)], 2.4, GLINT, 0.5)


def _shelf(cv: Canvas, g) -> None:
    """A wall shelf above the character: six books standing, the last one leaning on them."""
    x = 24.0
    sizes = ((22, 70), (18, 60), (26, 78), (20, 64), (24, 72))
    for i, (w, h) in enumerate(sizes):
        _book(cv, g, [(x, SHELF_Y), (x + w, SHELF_Y), (x + w, SHELF_Y - h), (x, SHELF_Y - h)], BOOKS[i])
        x += w + 1
    lean = math.radians(18)
    w, h = 20, 66
    base = x + h * math.sin(lean) + 2
    ux, uy = -math.sin(lean), -math.cos(lean)  # up the spine; it rests on its corner and its top on the last book
    bl, br = (base, SHELF_Y), (base + w * math.cos(lean), SHELF_Y - w * math.sin(lean))
    _book(cv, g, [bl, br, (br[0] + ux * h, br[1] + uy * h), (bl[0] + ux * h, bl[1] + uy * h)], BOOKS[5])
    cv.rect(g, fx(0), fy(SHELF_Y), fh(300), fh(12), SHELF, cv.ink, FINE_W, radius=fh(3))
    cv.rect(g, fx(0), fy(SHELF_Y + 12), fh(300), fh(8), SHADOW, cv.clear, 0, radius=0, opacity=0.18)


@register(
    "location",
    "toon-home",
    summary="A home office at night: a moonlit window over the city, string lights, a curtain and a bookshelf",
)
def home(cv: Canvas, parent, end: float = 0.0) -> None:
    """The character's room at night: a dusk-violet wall; the window at the right with the night sky, a cratered
    moon in its glow, stars that twinkle, the city skyline whose windows go out now and then, string lights along
    the curtain rod that pulse; a red curtain; a bookshelf above the character. The stars, lights and windows move
    from 0 to ``end`` (none when ``end`` is 0). The signature marks are the desk's (:func:`srstudio.toon.desk`)."""
    end = _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    wall = cv.grad("toon-home-wall", [(float(o), c) for o, c in HOME_WALL], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, wall)
    cv.rect(g, fx(333), fy(262), fh(330), fh(471), WINDOW_FRAME, cv.ink, INK_W, radius=0)
    sky = cv.grad("toon-night", [(float(o), c) for o, c in NIGHT], (0, 0, 0, 1))
    cv.rect(g, fx(372), fy(296), fh(300), fh(400), sky, cv.ink, FINE_W, radius=0)
    _glow(cv, g, "toon-moon-glow", 520, 380, 90, MOON)
    cv.ellipse(g, fx(490), fy(350), fh(60), fh(60), MOON, cv.ink, FINE_W * 0.6)
    for cx, cy, r in ((508, 368, 7), (530, 392, 5), (512, 395, 4)):
        cv.ellipse(g, fx(cx - r), fy(cy - r), fh(2 * r), fh(2 * r), CRATER)
    for i, (sx, sy) in enumerate(STARS):
        s = cv.group(g, cv.uid("g"))
        _fill(cv, s, brush.outline(_star(sx, sy, 7 if i % 3 else 10), steps=2), STAR)
        if end:
            pattern = [(0.0, 1.0), (TWINKLE / 2, 0.3)]
            cv.keys(s, "opacity", cycle_keys(pattern, TWINKLE, 0.0, end, phase=i * 0.37), hold=False)
    _skyline(cv, g, end)
    cv.rect(g, fx(372), fy(296), fh(300), fh(14), SHADOW, cv.clear, 0, radius=0, opacity=0.25)  # under the lintel
    _path(cv, g, _d("M", (320, 252), "L", (620, 252)), ROD, INK_W)
    _curtain(cv, g)
    _string_lights(cv, g, end)
    _shelf(cv, g)
    _path(cv, g, CHAIR_D, HOME_CHAIR)
    _line(cv, g, [(60, 598), (160, 578), (260, 590)], 12.0, HOME_CHAIR_LIGHT)
    _line(cv, g, [(150, 556), (152, 700)], 9.0, CURTAIN, 0.9)  # the gaming chair's stripe


# -- props ------------------------------------------------------------------------------------------------------------
@register(
    "prop",
    "toon-coffee-machine",
    summary="A drip coffee machine on the kitchen counter: while it brews its light blinks, coffee drips, steam rises",
)
def coffee_machine(cv: Canvas, parent, brewing: Spans = (), at: tuple[float, float] = (418, COUNTER_Y)) -> None:
    """A coffee machine standing on ``at`` (its centre and base, reference pixels; the kitchen counter by default):
    a charcoal body with a steel glint, a glass carafe half full, a light that is dark until it brews. In each
    ``brewing`` span the light blinks, drops fall into the carafe and steam rises from it."""
    spans = _check_spans(brewing, "brewing")
    x, y = at
    g = cv.group(parent, cv.uid("g"))
    _shadow(cv, g, x, y, 112)
    _inked(cv, g, [(x + 18, y - 104), (x + 50, y - 104), (x + 50, y - 10), (x + 18, y - 10)], MACHINE)
    _inked(cv, g, [(x - 50, y - 146), (x + 50, y - 146), (x + 50, y - 100), (x - 50, y - 100)], MACHINE, steps=4)
    _inked(cv, g, [(x - 54, y - 16), (x + 54, y - 16), (x + 54, y), (x - 54, y)], MACHINE_LIGHT)
    _line(cv, g, [(x - 40, y - 138), (x + 30, y - 138)], 4.0, GLINT, 0.45)
    _line(cv, g, [(x + 42, y - 96), (x + 42, y - 22)], 4.0, MACHINE_LIGHT)
    _inked(cv, g, [(x - 24, y - 100), (x - 6, y - 100), (x - 10, y - 90), (x - 20, y - 90)], MACHINE_LIGHT, FINE)
    # the carafe: glass, the coffee in it, the handle, a glint
    pot = [(x - 44, y - 68), (x + 10, y - 68), (x + 14, y - 40), (x + 8, y - 18), (x - 42, y - 18), (x - 48, y - 40)]
    _fill(cv, g, brush.rim(pot, FINE, brush.EVEN, steps=5), cv.ink)
    _fill(cv, g, brush.outline(pot, steps=5), GLASS, 0.75)
    _fill(
        cv, g, brush.outline([(x - 46, y - 44), (x + 12, y - 44), (x + 8, y - 20), (x - 42, y - 20)], steps=4), COFFEE
    )
    _line(cv, g, [(x + 14, y - 60), (x + 28, y - 52), (x + 26, y - 30), (x + 12, y - 28)], 4.5)
    _line(cv, g, [(x - 36, y - 62), (x - 38, y - 30)], 3.5, GLINT, 0.8)
    _inked(cv, g, [(x - 46, y - 74), (x + 12, y - 74), (x + 12, y - 66), (x - 46, y - 66)], cv.ink, FINE)
    # the light: dark, and a bright one that blinks while it brews
    lx, ly = x + 30, y - 123
    cv.ellipse(g, fx(lx - 6), fy(ly - 6), fh(12), fh(12), LED_OFF, cv.ink, FINE_W * 0.4)
    if not spans:
        return
    on = cv.group(g, cv.uid("g"))
    _glow(cv, on, "toon-led-glow", lx, ly, 18, LED_ON)
    cv.ellipse(on, fx(lx - 6), fy(ly - 6), fh(12), fh(12), LED_ON, cv.ink, FINE_W * 0.4)
    blink: dict[float, float] = {0.0: 0}
    drip: dict[float, float] = {0.0: 0}
    fall: dict[float, float] = {0.0: 0.0}
    for a, b in spans:
        for t, v in cycle_keys([(0.0, 1), (0.5, 0)], 1.0, a, b):
            blink[t] = v
        blink[round(b, 6)] = 0
        k = a
        while k + 0.05 < b:
            drip[round(k, 6)] = 1
            drip[round(min(k + DRIP * 0.8, b), 6)] = 0
            fall[round(k, 6)] = 0.0
            fall[round(min(k + DRIP * 0.8, b), 6)] = fh(52)
            fall[round(min(k + DRIP * 0.8, b) + 0.001, 6)] = 0.0
            k += DRIP
    cv.keys(on, "opacity", sorted(blink.items()))
    drop = cv.group(g, cv.uid("g"))
    cv.ellipse(drop, fx(x - 18), fy(y - 92), fh(6), fh(9), COFFEE)
    cv.keys(drop, "opacity", sorted(drip.items()))
    cv.keys(drop, "y", sorted(fall.items()), hold=False)
    steam = cv.group(g, cv.uid("g"), anchorX=fx(x - 16), anchorY=fy(y - 76), x=fx(x - 16), y=fy(y - 76))
    for dx in (-12, 2):
        sx = x - 16 + dx
        _line(cv, steam, [(sx, y - 78), (sx - 6, y - 90), (sx + 5, y - 102), (sx, y - 116)], 4.0, GLINT, 0.85)
    cv.gate(steam, spans)
    sway = []
    for a, b in spans:
        sway += cycle_keys([(0.0, -4.0), (0.6, 4.0)], 1.2, a, b)
    cv.keys(steam, "rotation", sway, hold=False)


@register(
    "prop",
    "toon-desk-lamp",
    summary="An angled desk lamp at the desk's right that pools warm light over the laptop, and can go dark",
)
def desk_lamp(cv: Canvas, parent, lit: Spans | None = None, at: tuple[float, float] = (610, 838)) -> None:
    """A teal angled lamp whose base stands on the desk at ``at`` (by default at the right edge, clear of the
    signature cactus on the desk) and whose head hangs over the laptop. Its light,
    a pool of warm glow and a soft cone, shows in the ``lit`` spans; ``None`` keeps it on throughout and ``()``
    leaves it off."""
    spans = None if lit is None else _check_spans(lit, "lit")
    x, y = at
    g = cv.group(parent, cv.uid("g"))
    light = cv.group(g, cv.uid("g"))
    head = (x - 62, y - 330)  # the shade's mouth
    cone = [(head[0] - 22, head[1] + 10), (head[0] + 26, head[1] + 4), (head[0] + 70, y - 40), (head[0] - 150, y - 40)]
    paint = cv.grad("toon-lamp-cone", [(0.0, LIGHT + "aa"), (1.0, LIGHT + "00")], (0, 0, 0, 1))
    _fill(cv, light, brush.outline(cone, steps=2), paint)
    _glow(cv, light, "toon-lamp-pool", head[0] - 30, y - 60, 120, LIGHT)
    _glow(cv, light, "toon-lamp-bulb", head[0] + 2, head[1] + 6, 40, LIGHT)
    if spans is not None:
        cv.gate(light, spans)
    _shadow(cv, g, x, y, 90, 10)
    _inked(cv, g, [(x - 40, y - 18), (x + 40, y - 18), (x + 44, y), (x - 44, y)], LAMP, steps=4)
    elbow = (x + 26, y - 190)
    for a, b in (((x, y - 16), elbow), (elbow, (head[0] + 36, head[1] - 34))):
        _line(cv, g, [a, b], 11.0)
        _line(cv, g, [a, b], 5.0, LAMP_DARK)
    for cx, cy in ((x, y - 16), elbow):
        cv.ellipse(g, fx(cx - 8), fy(cy - 8), fh(16), fh(16), LAMP, cv.ink, FINE_W * 0.6)
    shade = [(head[0] + 50, head[1] - 46), (head[0] + 26, head[1] - 52), (head[0] - 26, head[1] + 4),
             (head[0] + 4, head[1] + 18), (head[0] + 30, head[1] + 4)]  # fmt: skip
    _inked(cv, g, shade, LAMP, steps=4)
    _fill(cv, g, brush.ellipse(head[0] + 2, head[1] + 10, 26, 9, tilt=-30), LAMP_INSIDE)
    _line(cv, g, [(head[0] + 36, head[1] - 40), (head[0] + 4, head[1] - 10)], 3.5, GLINT, 0.6)


def _leaf(base: Point, angle: float, length: float, width: float) -> list[Point]:
    """A pointed leaf from ``base`` toward ``angle`` degrees (0 up, clockwise)."""
    a = math.radians(angle)
    ux, uy = math.sin(a), -math.cos(a)
    nx, ny = -uy, ux
    left, right = [], []
    for k in range(1, 6):
        s = k / 6
        half = width * math.sin(math.pi * s) ** 0.8
        px, py = base[0] + ux * length * s, base[1] + uy * length * s
        left.append((px + nx * half, py + ny * half))
        right.append((px - nx * half, py - ny * half))
    tip = (base[0] + ux * length, base[1] + uy * length)
    return [base, *left, tip, *reversed(right)]


@register("prop", "toon-plant", summary="A potted plant with glossy leaves that sway, for a desk, a counter or a shelf")
def plant(cv: Canvas, parent, at: tuple[float, float] = (380, 838), scale: float = 0.8, end: float = 0.0) -> None:
    """A terracotta pot standing on ``at`` (its centre and base; by default the desk's left end, the mug's place)
    with five leaves on stems, each with a vein and a
    gloss, ``scale`` times the default size. The leaves sway gently from 0 to ``end`` (still when ``end`` is 0)."""
    if not (isinstance(scale, int | float) and math.isfinite(scale) and 0.3 <= scale <= 3):
        raise ToonDataError(f"a plant's scale is 0.3 to 3, got {scale!r}")
    end = _check_end(end)
    x, y = at

    def p(dx: float, dy: float) -> Point:
        return (x + dx * scale, y + dy * scale)

    g = cv.group(parent, cv.uid("g"))
    _shadow(cv, g, x, y, 70 * scale)
    top = p(0, -54)
    leaves = cv.group(g, cv.uid("g"), anchorX=fx(top[0]), anchorY=fy(top[1]), x=fx(top[0]), y=fy(top[1]))
    for i, (angle, length, width, dx) in enumerate(
        ((-58, 70, 20, -6), (58, 66, 19, 6), (-22, 92, 24, -3), (22, 86, 23, 3), (0, 104, 26, 0))
    ):
        base = p(dx, -50 - 20)
        stem_end = (base[0] + math.sin(math.radians(angle)) * 18 * scale, base[1] - 18 * scale)
        _line(cv, leaves, [p(dx * 0.4, -52), base, stem_end], 4.5 * scale, STEM)
        shape = _leaf(stem_end, angle, length * scale, width * scale)
        _fill(cv, leaves, brush.rim(shape, FINE, brush.EVEN, steps=4), cv.ink)
        _fill(cv, leaves, brush.outline(shape, steps=4), LEAF[i % len(LEAF)])
        a = math.radians(angle)
        tip = (stem_end[0] + math.sin(a) * length * scale * 0.85, stem_end[1] - math.cos(a) * length * scale * 0.85)
        _line(cv, leaves, [stem_end, tip], 2.6 * scale, VEIN, 0.9)
        gloss = (stem_end[0] + math.sin(a) * length * scale * 0.35 - 5 * scale, stem_end[1] - math.cos(a) * length
                 * scale * 0.35)  # fmt: skip
        cv.ellipse(leaves, fx(gloss[0] - 3 * scale), fy(gloss[1] - 6 * scale), fh(6 * scale), fh(12 * scale), GLINT,
                   opacity=0.5)  # fmt: skip
    if end:
        sway = [(0.0, -SWAY_DEGREES), (SWAY / 2, SWAY_DEGREES)]
        cv.keys(leaves, "rotation", cycle_keys(sway, SWAY, 0.0, end), kind="sine-in-out")
    pot = [p(-30, -54), p(30, -54), p(22, 0), p(-22, 0)]
    _inked(cv, g, pot, POT, INK * min(1.0, scale), 2)
    _inked(cv, g, [p(-34, -62), p(34, -62), p(34, -48), p(-34, -48)], POT_RIM, FINE, 2)
    _fill(cv, g, brush.ellipse(x, y - 61 * scale, 28 * scale, 4 * scale), SOIL)
    _line(cv, g, [p(-20, -40), p(-16, -8)], 4.0 * scale, GLINT, 0.4)


def parse_pages(pages: Sequence[tuple[float, str]]) -> list[tuple[float, str, str]]:
    """``(project second, "OCT 14")`` pages in rising time, the first from 0: ``(second, month, day)``."""
    out: list[tuple[float, str, str]] = []
    for item in pages:
        if not (isinstance(item, tuple | list) and len(item) == 2):
            raise ToonDataError(f"a calendar page is (second, 'MON 14'), got {item!r}")
        t, text = item
        if isinstance(t, bool) or not isinstance(t, int | float) or not (math.isfinite(t) and t >= 0):
            raise ToonDataError(f"a calendar page's second is a number >= 0, got {t!r}")
        if not isinstance(text, str) or not PAGE.match(text) or not 1 <= int(text.split()[1]) <= 31:
            raise ToonDataError(f"a calendar page reads like 'OCT 14', got {text!r}")
        if out and t <= out[-1][0]:
            raise ToonDataError("calendar pages need rising seconds")
        month, day = text.split()
        out.append((float(t), month, day))
    if not out or out[0][0] != 0:
        raise ToonDataError("a calendar needs a page from 0 s")
    return out


@register(
    "prop", "toon-calendar", summary="A tear-off wall calendar whose page rips and falls at each new date", style="toon"
)
def calendar(cv: Canvas, parent, pages: Sequence[tuple[float, str]], at: tuple[float, float] = (105, 390)) -> None:
    """A tear-off calendar hung on a nail at ``at`` (its centre), in the clock's place by default: a red header
    with the month, the day large below it, two rings and a shadow on the wall. ``pages`` are ``(project second,
    "OCT 14")`` (:func:`parse_pages`); at each later one the page above tears off, tips and falls away."""
    parsed = parse_pages(pages)
    cx, cy = at
    x0, y0 = cx - CAL_W / 2, cy - CAL_H / 2
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x0 + 6), fy(y0 + 8), fh(CAL_W), fh(CAL_H), SHADOW, cv.clear, 0, radius=fh(4), opacity=0.2)
    cv.rect(g, fx(x0 - 4), fy(y0 - 4), fh(CAL_W + 8), fh(CAL_H + 8), "#d8d2c8", cv.ink, FINE_W * 0.7, radius=fh(4))
    # the pages: the last at the bottom of the pad, each earlier one drawn over it and torn off at the next date
    for i in range(len(parsed) - 1, -1, -1):
        t, month, day = parsed[i]
        page = cv.group(g, cv.uid("g"), anchorX=fx(x0 + 8), anchorY=fy(y0 + 20), x=fx(x0 + 8), y=fy(y0 + 20))
        cv.rect(page, fx(x0), fy(y0), fh(CAL_W), fh(CAL_H), CAL_PAPER, cv.ink, FINE_W * 0.7, radius=fh(3))
        cv.rect(page, fx(x0), fy(y0), fh(CAL_W), fh(30), CAL_HEADER, cv.ink, FINE_W * 0.7, radius=fh(3))
        cv.text(page, cv.uid("cal-month"), month, fx(x0), fy(y0 + 1), int(fh(CAL_W)), int(fh(28)), 30)
        cv.text(page, cv.uid("cal-day"), day, fx(x0), fy(y0 + 34), int(fh(CAL_W)), int(fh(78)), 92, color=cv.ink)
        if i + 1 < len(parsed):
            torn = parsed[i + 1][0]
            cv.keys(page, "rotation", [(0, 0), (torn, 0), (torn + FLIP, 38)], hold=False)
            cv.keys(page, "y", [(0, fy(y0 + 20)), (torn, fy(y0 + 20)), (torn + FLIP, fy(y0 + 20) + fh(150))],
                    hold=False)  # fmt: skip
            cv.keys(page, "opacity", [(0, 1), (torn, 1), (torn + FLIP, 0)], hold=False)
    for rx in (cx - 26, cx + 26):
        cv.ellipse(g, fx(rx - 5), fy(y0 - 10), fh(10), fh(18), "#9aa0a8", cv.ink, FINE_W * 0.5)
    cv.ellipse(g, fx(cx - 4), fy(y0 - 26), fh(8), fh(8), cv.ink)
    _line(cv, g, [(cx - 26, y0 - 6), (cx, y0 - 22), (cx + 26, y0 - 6)], 2.4)


@register(
    "location",
    "toon-call-centre",
    summary="A call-centre cubicle: a fabric partition, a YOUR CALL MATTERS poster and a CALLS WAITING board",
)
def call_centre(cv: Canvas, parent, waiting: Sequence[tuple[float, int]] = ((0.0, 12),), end: float = 0.0) -> None:
    """The character's cubicle on a pale office wall: a flecked blue fabric partition with an aluminium cap behind
    the character, a cheerful poster above it that reads YOUR CALL MATTERS, and, where the other sets have their
    window, a dark LED board of the CALLS WAITING with a red lamp. ``waiting`` is ``(project second, count)`` from
    0, in time order, each count 0 to :data:`WAITING_MAX`; the board shows one count at a time. The lamp blinks
    from 0 to ``end`` (still when ``end`` is 0)."""
    counts = _check_waiting(waiting)
    end = _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    wall = cv.grad("toon-centre-wall", [(float(o), c) for o, c in CENTRE_WALL], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, wall)
    # the poster: a band of colour, two lines of type
    cv.rect(g, fx(42), fy(370), fh(250), fh(70), SHADOW, cv.clear, 0, radius=fh(4), opacity=0.16)
    cv.rect(g, fx(36), fy(364), fh(250), fh(70), POSTER, cv.ink, FINE_W, radius=fh(4))
    cv.rect(g, fx(36), fy(364), fh(250), fh(14), POSTER_BAND, cv.ink, FINE_W, radius=fh(4))
    cv.text(g, cv.uid("centre-poster"), "YOUR CALL\nMATTERS", fx(36), fy(380), int(fh(250)), int(fh(52)), 40,
            color=POSTER_INK)  # fmt: skip
    # the board, in the window's place: a frame, the dark face, the label, the lamp and the count
    cv.rect(g, fx(348), fy(362), fh(250), fh(150), BOARD_FRAME, cv.ink, INK_W, radius=fh(6))
    cv.rect(g, fx(362), fy(374), fh(240), fh(126), BOARD, cv.ink, FINE_W, radius=fh(4))
    cv.text(g, cv.uid("centre-label"), "CALLS WAITING", fx(380), fy(382), int(fh(200)), int(fh(30)), 30, color=LED,
            align="start")  # fmt: skip
    cv.ellipse(g, fx(566), fy(386), fh(18), fh(18), LED_DIM, cv.ink, FINE_W * 0.5)
    lamp = cv.group(g, cv.uid("g"))
    _glow(cv, lamp, "toon-centre-lamp", 575, 395, 22, LED)
    cv.ellipse(lamp, fx(566), fy(386), fh(18), fh(18), LED, cv.ink, FINE_W * 0.5)
    if end:
        cv.keys(lamp, "opacity", cycle_keys([(0.0, 1.0), (BLINK / 2, 0.15)], BLINK, 0.0, end), hold=False)
    for i, (at, count) in enumerate(counts):
        digits = cv.group(g, cv.uid("g"))
        cv.text(digits, cv.uid("centre-count"), str(count), fx(380), fy(410), int(fh(204)), int(fh(86)), 110,
                color=LED, align="start")  # fmt: skip
        keys = [(0.0, 1.0 if at == 0 else 0.0)] + ([(at, 1.0)] if at > 0 else [])
        if i + 1 < len(counts):
            keys.append((counts[i + 1][0], 0.0))
        cv.keys(digits, "opacity", keys)
    # the partition behind the character, its cap and a scatter of flecks in the weave, then the chair
    cv.rect(g, fx(-10), fy(600), fh(612), fh(210), PARTITION, cv.ink, FINE_W, radius=0)
    for k in range(40):
        x, y = 8 + (k * 53) % 590, 616 + (k * 37) % 180
        cv.ellipse(g, fx(x), fy(y), fh(4), fh(3), PARTITION_FLECK, opacity=0.8)
    cv.rect(g, fx(-10), fy(588), fh(612), fh(16), PARTITION_CAP, cv.ink, FINE_W, radius=fh(4))
    _path(cv, g, CHAIR_D, CENTRE_CHAIR)
    _line(cv, g, [(60, 598), (160, 578), (260, 590)], 12.0, CENTRE_CHAIR_LIGHT)


def _check_waiting(waiting: Sequence[tuple[float, int]]) -> list[tuple[float, int]]:
    out: list[tuple[float, int]] = []
    for item in waiting:
        if not (isinstance(item, tuple | list) and len(item) == 2):
            raise ToonDataError(f"the board takes (second, count) pairs, got {item!r}")
        at, count = item
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= WAITING_MAX:
            raise ToonDataError(f"a count of calls waiting is a whole number 0 to {WAITING_MAX}, got {count!r}")
        if isinstance(at, bool) or not isinstance(at, int | float) or not math.isfinite(at):
            raise ToonDataError(f"the board's counts change in order, from 0: got {at!r}")
        if not out and at != 0:
            raise ToonDataError(f"the board shows a count from 0, its first is at {at}")
        if out and at <= out[-1][0]:
            raise ToonDataError(f"the board's counts change in order, from 0: {at} after {out[-1][0]}")
        out.append((float(at), count))
    if not out:
        raise ToonDataError("the board needs at least one count")
    return out

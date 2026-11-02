"""Toon homeware: the kitchen and bathroom things a domestic sketch turns on.

A dishwasher that fills as somebody loads it and its top rack seen close, rolling out; a baby monitor, its unit and
its receiver with level bars; a swing door between a kitchen and a dining room; a tray of flagged cupcakes; a shampoo
bottle that gives up one bubble; a pile of soup tubs that grows; a streaming service's profile screen and device list;
a scribble that stands where a caption would for words nobody caught; a garden power tool that drowns a voice.

Geometry uses reference screen pixels (:func:`srstudio.toon.fx`/``fy``); typography uses frame pixels.
Animation keys follow Canvas.local_time (composition by default); visibility uses the parent timeline.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import _toon_domestic_contracts as dc
from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy
from .toon_sets import _inked, _line

__all__ = [
    "baby_monitor",
    "blower",
    "cupcakes",
    "device_list",
    "dishwasher",
    "monitor_receiver",
    "lasagna",
    "mower",
    "profile_list",
    "rack",
    "scribble",
    "shampoo",
    "soup_tubs",
    "swing_door",
    "toast",
]

Point = tuple[float, float]
Spans = Sequence[tuple[float, float]]

STEEL, STEEL_DARK, STEEL_LIGHT = "#c4ccd6", "#8d97a5", "#e4e9ef"
WIRE = "#6b7686"
MUG, MUG_SHADE = "#f7f1e5", "#dccfb8"
PLATE, PLATE_RIM = "#ffffff", "#c9d6e2"
GLASS = "#cfe9f2"
PLASTIC, PLASTIC_SHADE = "#f8f8f4", "#d6d6cc"
LED = "#42d67a"
DOOR, DOOR_SHADE = "#b98a5e", "#8e6541"
ROOM = "#4f3a2a"
ROOM_GLOW = "#ffd98a"
TRAY = "#9aa4b1"
CAKE, CASE, CASE_LINE = "#f4d9a6", "#f39bb4", "#d96f90"
FROSTING = ("#fff3f7", "#ffe08a", "#b9e4ff")
FLAG = "#e2364b"
TUB, TUB_LID, SOUP = "#f4f7f9", "#e8574f", "#f0b45a"
BOTTLE, BOTTLE_SHADE, BOTTLE_LABEL = "#57b6c9", "#3b8fa2", "#fff6dc"
BUBBLE = "#e6f7ff"
PAGE_BG, TILE_INK = "#14161f", "#ffffff"
DARK_SCREEN = (PAGE_BG, "#232634", TILE_INK, "#b9c0d0", LED)  # page, row, ink, soft ink, the doing
AVATARS = ("#b4432f", "#2a6aaa", "#8a6710", "#2f7550", "#7443b0")
LIGHT_SCREEN = ("#e6edf4", "#ffffff", "#20242e", "#566074", "#17703f")  # page, row, ink, soft ink, the doing
PROFILE_TOP, PROFILE_ROW, PROFILE_ROOM = 322.0, 88.0, 450.0  # reference units: under the caption, over the ledge
SCRAWL_BG, SCRAWL_INK = "#fff1cf", "#1f2933"
MOWER, MOWER_DARK = "#d9483b", "#9c2f26"
BLOWER, BLOWER_DARK = "#f28c28", "#b85f12"
RUBBER = "#2b2d35"
MAX_LOADED = 12
MAX_TUBS = 6
NAME_MAX = 12


def _point(at: object, what: str) -> Point:
    if not (isinstance(at, tuple) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"{what} is an (x, y), got {at!r}")
    return at


def _scale(scale: object) -> float:
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a scale is over 0, got {scale!r}")
    return float(scale)


def _rising(times: Sequence[float], what: str) -> list[float]:
    out = [float(t) for t in times]
    if any(not checks.number(t) or t < 0 for t in out) or any(b <= a for a, b in zip(out, out[1:], strict=False)):
        raise ToonDataError(f"{what} rise from 0, got {list(times)}")
    return out


def _spans(spans: Spans, what: str) -> list[tuple[float, float]]:
    out = []
    last = 0.0
    for span in spans:
        if not (isinstance(span, tuple) and len(span) == 2 and all(checks.number(v) for v in span)):
            raise ToonDataError(f"{what} are (start, end) pairs, got {span!r}")
        a, b = span
        if a < last or b <= a:
            raise ToonDataError(f"{what} rise and do not overlap, got {list(spans)}")
        out.append((float(a), float(b)))
        last = b
    return out


def _mug(cv: Canvas, parent, x: float, y: float, s: float, tilt: float = 0.0):
    """A mug upside down on a rack, its base at ``(x, y)`` reference, tilted ``tilt`` degrees; returns its group."""
    px, py = fx(x), fy(y)
    g = cv.group(parent, cv.uid("g"), rotation=tilt, x=px, y=py, anchorX=px, anchorY=py)
    cv.rect(g, fx(x - 30 * s), fy(y - 66 * s), fh(60 * s), fh(66 * s), MUG, cv.ink, FINE_W, radius=fh(7 * s))
    cv.rect(g, fx(x + 8 * s), fy(y - 60 * s), fh(12 * s), fh(54 * s), MUG_SHADE, radius=fh(4 * s))
    cv.ellipse(g, fx(x + 22 * s), fy(y - 52 * s), fh(26 * s), fh(34 * s), cv.clear, cv.ink, FINE_W)
    return g


@register(
    "prop",
    "toon-dishwasher",
    contract=dc.contract('toon-dishwasher'),
    summary="An open dishwasher that fills, dish by dish, on cue",
)
def dishwasher(
    cv: Canvas, parent, at: Point = (448.0, 838.0), scale: float = 1.0, loads: Sequence[float] = (), end: float = 0.0
) -> None:
    """An open dishwasher standing on reference ``at``, its door down: one dish appears in its racks at each of
    ``loads`` (seconds, rising) and stays until ``end``."""
    x, y = _point(at, "a dishwasher's place")
    s = _scale(scale)
    times = _rising(loads, "a dishwasher's loads")
    if len(times) > MAX_LOADED:
        raise ToonDataError(f"a dishwasher takes {MAX_LOADED} dishes, got {len(times)}")
    if times and end <= times[-1]:
        raise ToonDataError(f"a dishwasher's last dish lands before its end, got {end}")
    g = cv.group(parent, cv.uid("g"))
    w, h = 250 * s, 320 * s
    left, top = x - w / 2, y - h
    cv.rect(g, fx(left), fy(top), fh(w), fh(h), STEEL_DARK, cv.ink, INK_W, radius=fh(6))
    cv.rect(g, fx(left + 14 * s), fy(top + 14 * s), fh(w - 28 * s), fh(h - 60 * s), "#55606e", cv.ink, FINE_W)
    for row in (top + 118 * s, top + 232 * s):
        cv.rect(g, fx(left + 14 * s), fy(row), fh(w - 28 * s), fh(7 * s), WIRE)
    _inked(cv, g, [(left - 22 * s, y), (left + w + 22 * s, y), (left + w, y - 46 * s), (left, y - 46 * s)], STEEL_LIGHT)
    for i, t in enumerate(times):
        row, col = i // 6, i % 6
        dish = cv.group(g, cv.uid("g"), start=t, end=end)
        dx = left + 40 * s + col * 34 * s
        floor = top + (118 if row == 0 else 232) * s
        if i % 2:
            cv.rect(
                dish, fx(dx - 5 * s), fy(floor - 76 * s), fh(12 * s), fh(76 * s), PLATE, cv.ink, FINE_W, radius=fh(5)
            )
        else:
            cv.rect(
                dish, fx(dx - 15 * s), fy(floor - 46 * s), fh(30 * s), fh(46 * s), MUG, cv.ink, FINE_W, radius=fh(5)
            )


@register(
    "prop",
    "toon-rack",
    contract=dc.contract('toon-rack'),
    summary="A dishwasher's top rack seen close: perfect rows of mugs, rolling out on cue",
)
def rack(
    cv: Canvas,
    parent,
    roll: tuple[float, float] = (0.0, 1.0),
    tilt: tuple[float, float] | None = None,
    rows: int = 3,
    start: float = 0.0,
    end: float = 2.0,
):
    """The top rack filling the frame, rows of mugs all at one slant, rolling in from below over ``roll`` (seconds);
    ``tilt`` is the span over which the front row's middle mug is tipped back and forward by a finger."""
    if not (isinstance(rows, int) and 1 <= rows <= 4):
        raise ToonDataError(f"a rack has 1 to 4 rows, got {rows!r}")
    if not (start <= roll[0] < roll[1] <= end):
        raise ToonDataError(f"a rack rolls inside its time on screen, got {roll} of {start}..{end}")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    cv.rect(g, fx(-10), fy(0), fh(612), fh(1000), "#3f4955")
    moved = cv.group(g, cv.uid("g"), x=0, y=0)
    cv.keys(moved, "y", [(roll[0], fh(420)), (roll[1], 0.0)], kind="sine-in-out")
    for i in range(7):
        cv.rect(moved, fx(30 + i * 90), fy(190), fh(6), fh(640), WIRE)
    middle = None
    for row in range(rows):
        y = 340 + row * 190
        cv.rect(moved, fx(10), fy(y + 6), fh(572), fh(9), WIRE)
        for col in range(5):
            mug = _mug(cv, moved, 82 + col * 108, y, 1.1, -14.0)
            if row == rows - 1 and col == 2:
                middle = mug
    if tilt is not None and middle is not None:
        a, b = tilt
        if not (roll[1] <= a < b <= end):
            raise ToonDataError(f"a mug is tipped after the rack has rolled, got {tilt}")
        cv.keys(middle, "rotation", [(a, -14.0), ((a + b) / 2, 8.0), (b, -14.0)], kind="sine-in-out")
    return g


@register(
    "prop",
    "toon-baby-monitor",
    contract=dc.contract('toon-baby-monitor'),
    summary="A small white baby monitor with an aerial and one green light",
)
def baby_monitor(cv: Canvas, parent, at: Point = (452.0, 500.0), scale: float = 1.0) -> None:
    """The nursery unit standing on reference ``at``, its green light on."""
    x, y = _point(at, "a baby monitor's place")
    s = _scale(scale)
    g = cv.group(parent, cv.uid("g"))
    _line(cv, g, [(x + 24 * s, y - 92 * s), (x + 34 * s, y - 136 * s)], 6.0 * s, cv.ink)
    cv.rect(g, fx(x - 36 * s), fy(y - 96 * s), fh(72 * s), fh(96 * s), PLASTIC, cv.ink, INK_W, radius=fh(14 * s))
    for i in range(3):
        cv.rect(g, fx(x - 20 * s), fy(y - 80 * s + i * 11 * s), fh(40 * s), fh(4 * s), PLASTIC_SHADE, radius=fh(2))
    cv.ellipse(g, fx(x - 8 * s), fy(y - 34 * s), fh(16 * s), fh(16 * s), LED, cv.ink, FINE_W / 2)


@register(
    "prop",
    "toon-monitor-receiver",
    contract=dc.contract('toon-monitor-receiver'),
    summary="A baby monitor's receiver, its green level bars jumping on cue",
)
def monitor_receiver(
    cv: Canvas, parent, at: Point = (440.0, 800.0), scale: float = 1.5, pulses: Sequence[float] = (), end: float = 0.0
) -> None:
    """The parents' half standing on reference ``at``; its five green bars jump at each of ``pulses`` (seconds)."""
    x, y = _point(at, "a receiver's place")
    s = _scale(scale)
    times = _rising(pulses, "a receiver's pulses")
    if times and end <= times[-1]:
        raise ToonDataError(f"a receiver's last pulse comes before its end, got {end}")
    g = cv.group(parent, cv.uid("g"))
    _line(cv, g, [(x + 42 * s, y - 118 * s), (x + 56 * s, y - 172 * s)], 6.0 * s, cv.ink)
    cv.rect(g, fx(x - 62 * s), fy(y - 124 * s), fh(124 * s), fh(124 * s), PLASTIC, cv.ink, INK_W, radius=fh(16 * s))
    cv.rect(g, fx(x - 48 * s), fy(y - 106 * s), fh(96 * s), fh(50 * s), "#1b2430", cv.ink, FINE_W, radius=fh(6))
    for i in range(5):
        bx = x - 40 * s + i * 17 * s
        cv.rect(g, fx(bx), fy(y - 66 * s), fh(11 * s), fh(4 * s), LED)
        tall = cv.rect(g, fx(bx), fy(y - 66 * s - (6 + 6 * i) * s), fh(11 * s), fh((6 + 6 * i) * s), LED, opacity=0.0)
        keys: list[tuple[float, float]] = [(0.0, 0.0)]
        for t in times:
            keys += [(t, 1.0), (t + 0.14, 0.0)]
        if len(keys) > 1:
            cv.keys(tall, "opacity", keys)
    for i in range(3):
        cv.rect(g, fx(x - 26 * s), fy(y - 44 * s + i * 11 * s), fh(52 * s), fh(4 * s), PLASTIC_SHADE, radius=fh(2))


@register(
    "prop",
    "toon-swing-door",
    contract=dc.contract('toon-swing-door'),
    summary="A swing door with a round window, shut or open on a lit dining room",
)
def swing_door(
    cv: Canvas,
    parent,
    opens: Spans = (),
    at: Point = (380.0, 150.0),
    size: Point = (200.0, 620.0),
    end: float = 0.0,
    *,
    legs: bool = False,
) -> None:
    """A door whose frame's top left is reference ``at``: shut, and for each of ``opens`` (seconds) swung back on a
    lit room with a guest's shadow crossing it, standing on the room's floor when ``legs``."""
    x, y = _point(at, "a door's place")
    w, h = size
    spans = _spans(opens, "a door's opens")
    if spans and end < spans[-1][1]:
        raise ToonDataError(f"a door stays on until its last close, got {end}")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x - 12), fy(y - 12), fh(w + 24), fh(h + 12), "#efe3d2", cv.ink, INK_W)
    gap = cv.group(g, cv.uid("g"))
    cv.rect(gap, fx(x), fy(y), fh(w), fh(h), ROOM)
    cv.rect(gap, fx(x), fy(y), fh(w), fh(h * 0.7), ROOM_GLOW)
    shut: list[tuple[float, float]] = [(0.0, 1.0)]
    for a, b in spans:
        shut += [(a, 0.0), (b, 1.0)]
    door = cv.group(g, cv.uid("g"))
    cv.rect(door, fx(x), fy(y), fh(w), fh(h), DOOR, cv.ink, FINE_W)
    cv.ellipse(door, fx(x + w / 2 - 52), fy(y + 70), fh(104), fh(104), GLASS, cv.ink, INK_W)
    cv.rect(door, fx(x + 14), fy(y + h * 0.62), fh(w - 28), fh(84), "#d3c6b0", DOOR_SHADE, FINE_W)
    if spans:
        cv.keys(door, "opacity", shut)
        ajar = cv.group(g, cv.uid("g"), opacity=0.0)
        cv.rect(ajar, fx(x + w - 32), fy(y), fh(32), fh(h), DOOR_SHADE, cv.ink, FINE_W)
        guest = cv.group(g, cv.uid("g"), opacity=0.0)
        cv.ellipse(guest, fx(x + 40), fy(y + 130), fh(80), fh(90), "#7a5a42")
        if legs:
            for leg in (x + 36, x + 92):
                cv.rect(guest, fx(leg), fy(y + 480), fh(32), fh(130), "#7a5a42")
                cv.rect(guest, fx(leg - 8), fy(y + 596), fh(48), fh(24), "#7a5a42", radius=fh(10))
        cv.rect(guest, fx(x + 22), fy(y + 216), fh(116), fh(300), "#7a5a42", radius=fh(30))
        seen = [(t, 1.0 - v) for t, v in shut]
        cv.keys(ajar, "opacity", seen)
        cv.keys(guest, "opacity", seen)


@register(
    "prop",
    "toon-cupcakes",
    contract=dc.contract('toon-cupcakes'),
    summary="Trays of cupcakes filling the frame, each with a tiny flag",
)
def cupcakes(cv: Canvas, parent, start: float = 0.0, end: float = 2.0, rows: int = 5, cols: int = 6) -> None:
    """A worktop of cupcakes, ``rows`` by ``cols``, each frosted, each with a tiny red flag, from ``start`` to
    ``end``."""
    if not (isinstance(rows, int) and isinstance(cols, int) and 1 <= rows <= 6 and 1 <= cols <= 6):
        raise ToonDataError(f"a tray is 1 to 6 by 1 to 6, got {rows!r} by {cols!r}")
    if end <= start:
        raise ToonDataError(f"cupcakes leave after they arrive, got {start}..{end}")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    cv.rect(g, fx(-10), fy(0), fh(612), fh(900), "#fbe6bf")
    cv.rect(g, fx(14), fy(226), fh(564), fh(630), TRAY, cv.ink, INK_W, radius=fh(14))
    pitch_x, pitch_y = 90.0, 104.0
    for row in range(rows):
        for col in range(cols):
            x, y = 72 + col * pitch_x, 318 + row * pitch_y
            _inked(cv, g, [(x - 34, y), (x + 34, y), (x + 24, y + 48), (x - 24, y + 48)], CASE, FINE_W, 1)
            for d in (-12, 0, 12):
                _line(cv, g, [(x + d, y + 4), (x + d * 0.7, y + 44)], FINE_W / 2, CASE_LINE)
            frosting = FROSTING[(row * 2 + col) % len(FROSTING)]
            cv.ellipse(g, fx(x - 40), fy(y - 42), fh(80), fh(54), frosting, cv.ink, FINE_W)
            _line(cv, g, [(x + 2, y - 30), (x + 2, y - 78)], FINE_W, cv.ink)
            _inked(cv, g, [(x + 2, y - 78), (x + 30, y - 68), (x + 2, y - 58)], FLAG, FINE_W / 2, 1)


@register(
    "prop",
    "toon-shampoo",
    contract=dc.contract('toon-shampoo'),
    summary="A squeezy shampoo bottle, held up or standing, that gives up one bubble",
)
def shampoo(cv: Canvas, parent, at: Point = (340.0, 700.0), scale: float = 1.0, bubble: float | None = None):
    """A shampoo bottle with its base at reference ``at``, one bubble rising from its cap at ``bubble`` (seconds);
    returns the group, whose keys move the whole bottle."""
    x, y = _point(at, "a bottle's place")
    s = _scale(scale)
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x - 16 * s), fy(y - 214 * s), fh(32 * s), fh(32 * s), BOTTLE_SHADE, cv.ink, FINE_W, radius=fh(5))
    cv.rect(g, fx(x - 46 * s), fy(y - 186 * s), fh(92 * s), fh(186 * s), BOTTLE, cv.ink, INK_W, radius=fh(26 * s))
    cv.rect(g, fx(x - 32 * s), fy(y - 134 * s), fh(64 * s), fh(82 * s), BOTTLE_LABEL, cv.ink, FINE_W / 2, radius=fh(6))
    _line(cv, g, [(x - 20 * s, y - 112 * s), (x + 20 * s, y - 112 * s)], FINE_W, BOTTLE_SHADE)
    _line(cv, g, [(x - 20 * s, y - 92 * s), (x + 12 * s, y - 92 * s)], FINE_W, BOTTLE_SHADE)
    if bubble is not None:
        if not (checks.number(bubble) and bubble >= 0):
            raise ToonDataError(f"a bubble comes at a time, got {bubble!r}")
        b = cv.group(g, cv.uid("g"), start=bubble, end=bubble + 0.9)
        cv.ellipse(b, fx(x - 15 * s), fy(y - 250 * s), fh(30 * s), fh(30 * s), BUBBLE, cv.ink, FINE_W / 2)
        cv.keys(b, "y", [(bubble, 0.0), (bubble + 0.9, -fh(80 * s))], hold=False)
    return g


@register(
    "prop",
    "toon-soup-tubs",
    contract=dc.contract('toon-soup-tubs'),
    summary="A pile of soup tubs with red lids that grows, stop by stop",
)
def soup_tubs(
    cv: Canvas, parent, counts: Sequence[tuple[float, int]], at: Point = (300.0, 838.0), end: float = 0.0
) -> None:
    """Tubs stacked on reference ``at``: each ``(second, count)`` of ``counts`` shows that many, to the next one, the
    last until ``end``."""
    x, y = _point(at, "a stack's place")
    times = _rising([c[0] for c in counts], "a stack's counts")
    if not counts or any(not (isinstance(c[1], int) and 1 <= c[1] <= MAX_TUBS) for c in counts):
        raise ToonDataError(f"a stack is 1 to {MAX_TUBS} tubs, got {list(counts)}")
    if end <= times[-1]:
        raise ToonDataError(f"a stack lasts past its last count, got {end}")
    g = cv.group(parent, cv.uid("g"))
    for n in range(max(c[1] for c in counts)):
        for arrives, leaves in _tub_spans(counts, n, end):
            tub = cv.group(g, cv.uid("g"), start=arrives, end=leaves)
            top = y - (n + 1) * 74
            cv.rect(tub, fx(x - 78), fy(top + 16), fh(156), fh(56), TUB, cv.ink, INK_W, radius=fh(10))
            cv.rect(tub, fx(x - 66), fy(top + 30), fh(132), fh(36), SOUP, radius=fh(8))
            cv.rect(tub, fx(x - 86), fy(top), fh(172), fh(20), TUB_LID, cv.ink, INK_W, radius=fh(6))


def _tub_spans(counts: Sequence[tuple[float, int]], level: int, end: float) -> list[tuple[float, float]]:
    """Merge consecutive cues keeping this tub visible, including disappearance and return."""
    spans = []
    start = None
    for time, count in counts:
        if count > level and start is None:
            start = float(time)
        elif count <= level and start is not None:
            spans.append((start, float(time)))
            start = None
    if start is not None:
        spans.append((start, end))
    return spans


def _fit(text: str, what: str) -> str:
    if not 1 <= len(text) <= NAME_MAX:
        raise ToonDataError(f"{what} is 1 to {NAME_MAX} characters, got {text!r}")
    return text


@register(
    "prop",
    "toon-profile-list",
    contract=dc.contract('toon-profile-list'),
    summary="A streaming service's Who's on the couch? list: round avatars, names",
)
def profile_list(
    cv: Canvas, parent, names: Sequence[str] = ("Mia", "Brock"), start: float = 0.0, end: float = 2.0
) -> None:
    """The frame filled by a pale profile screen: the question, under it a list of up to six rows, a round avatar with
    the name's initial beside each name. The rows start under the caption's place."""
    if not 1 <= len(names) <= 6:
        raise ToonDataError(f"a profile list shows 1 to 6 rows, got {len(names)}")
    if end <= start:
        raise ToonDataError(f"a screen leaves after it arrives, got {start}..{end}")
    page, _, ink, soft, _ = LIGHT_SCREEN
    pitch = min(PROFILE_ROW, PROFILE_ROOM / len(names))
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    cv.rect(g, fx(-10), fy(0), fh(612), fh(1000), page)
    cv.text(g, cv.uid("profiles-head"), "Who's on the couch?", fx(0), fy(130), int(fh(592)), int(fh(90)), 68,
            color=ink, wrap="none")  # fmt: skip
    for i, name in enumerate(names):
        y = PROFILE_TOP + i * pitch
        name = _fit(name, "a profile's name")
        cv.ellipse(g, fx(64), fy(y + 6), fh(64), fh(64), AVATARS[i % len(AVATARS)], cv.ink, FINE_W)
        cv.text(g, cv.uid("profile-initial"), name[0].upper(), fx(64), fy(y + 14), int(fh(64)), int(fh(48)), 44,
                color="#ffffff", wrap="none")  # fmt: skip
        cv.text(g, cv.uid("profile"), name, fx(150), fy(y + 14), int(fh(390)), int(fh(48)), 44, color=ink,
                align="start", wrap="none")  # fmt: skip
        cv.rect(g, fx(150), fy(y + 76), fh(390), fh(2), soft, cv.clear, 0, radius=0, opacity=0.5)


@register(
    "prop",
    "toon-device-list",
    contract=dc.contract('toon-device-list'),
    summary="A streaming account's device list: who is watching on what, right now",
)
def device_list(
    cv: Canvas, parent, rows: Sequence[tuple[str, str, str]] = (("Kyle", "Living Room TV", "Now watching"),),
    start: float = 0.0, end: float = 2.0, *, paints: tuple[str, str, str, str, str] = DARK_SCREEN,
) -> None:  # fmt: skip
    """The frame filled by a device list, a row per ``(name, device, doing)``, the doing in green. ``paints`` are the
    page, the row, the ink, the soft ink and the doing: :data:`LIGHT_SCREEN` goes with :func:`profile_list`."""
    if not 1 <= len(rows) <= 4:
        raise ToonDataError(f"a device list shows 1 to 4 rows, got {len(rows)}")
    if end <= start:
        raise ToonDataError(f"a screen leaves after it arrives, got {start}..{end}")
    page, row, ink, soft, doing_ink = paints
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    cv.rect(g, fx(-10), fy(0), fh(612), fh(1000), page)
    cv.text(g, cv.uid("devices-head"), "Your devices", fx(0), fy(190), int(fh(592)), int(fh(80)), 64, color=ink,
            wrap="none")  # fmt: skip
    for i, (name, device, doing) in enumerate(rows):
        y = 310 + i * 200
        cv.rect(g, fx(36), fy(y), fh(520), fh(172), row, radius=fh(14))
        name = _fit(name, "a device's owner")
        cv.text(g, cv.uid("device-name"), name, fx(56), fy(y + 12), int(fh(480)), int(fh(62)), 54, color=ink,
                align="start", wrap="none")  # fmt: skip
        cv.text(g, cv.uid("device"), device, fx(56), fy(y + 72), int(fh(480)), int(fh(44)), 38, color=soft,
                align="start", wrap="none")  # fmt: skip
        cv.text(g, cv.uid("doing"), doing, fx(56), fy(y + 116), int(fh(480)), int(fh(44)), 38, color=doing_ink,
                align="start", wrap="none")  # fmt: skip


@register(
    "prop",
    "toon-scribble",
    contract=dc.contract('toon-scribble'),
    summary="A caption pill with a scrawl in it, for words nobody could make out",
)
def scribble(
    cv: Canvas, parent, spans: Spans, at: Point = (296.0, 278.0), width: float = 420.0, colour: str = SCRAWL_BG
) -> None:
    """A pill centred on reference ``at`` for each of ``spans`` (seconds), holding a line of scrawl: words that were
    said and not heard. Its height and place follow a Toon caption, so it stands where the caption would."""
    x, y = _point(at, "a scribble's place")
    if not (checks.number(width) and 120 <= width <= 540):
        raise ToonDataError(f"a scribble is 120 to 540 wide, got {width!r}")
    for n, (a, b) in enumerate(_spans(spans, "a scribble's spans")):
        g = cv.group(parent, cv.uid("g"), start=a, end=b)
        left = x - width / 2
        cv.rect(g, fx(left), fy(y - 30), fh(width), fh(60), colour, radius=fh(14))
        points = [(left + 26 + i * (width - 52) / 18, y + (-13 if (i + n) % 2 else 13) * (1 - (i % 5) * 0.13))
                  for i in range(19)]  # fmt: skip
        _line(cv, g, points, 5.0, SCRAWL_INK)


@register(
    "prop",
    "toon-mower",
    contract=dc.contract('toon-mower'),
    summary="A red lawn mower's engine and handle, seen over a fence",
)
def mower(cv: Canvas, parent, at: Point = (70.0, 838.0), scale: float = 1.0, running: Spans = ()) -> None:
    """A mower on reference ``at``, its handle rising to the right; it shudders over each of ``running``."""
    x, y = _point(at, "a mower's place")
    s = _scale(scale)
    spans = _spans(running, "a mower's running")
    g = cv.group(parent, cv.uid("g"))
    _line(cv, g, [(x + 60 * s, y - 80 * s), (x + 240 * s, y - 240 * s)], 12.0 * s, cv.ink)
    _inked(cv, g, [(x - 66 * s, y), (x + 106 * s, y), (x + 90 * s, y - 76 * s), (x - 50 * s, y - 76 * s)], MOWER)
    cv.rect(g, fx(x - 22 * s), fy(y - 118 * s), fh(76 * s), fh(46 * s), MOWER_DARK, cv.ink, FINE_W, radius=fh(6))
    _shudder(cv, g, spans)


@register(
    "prop", "toon-blower", contract=dc.contract('toon-blower'), summary="An orange leaf blower held out, tube first"
)
def blower(cv: Canvas, parent, at: Point = (150.0, 760.0), scale: float = 1.0, running: Spans = ()) -> None:
    """A leaf blower with its grip at reference ``at``, the tube pointing right; it shudders over each of
    ``running``."""
    x, y = _point(at, "a blower's place")
    s = _scale(scale)
    spans = _spans(running, "a blower's running")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x + 90 * s), fy(y - 26 * s), fh(210 * s), fh(36 * s), BLOWER, cv.ink, INK_W, radius=fh(10 * s))
    cv.rect(g, fx(x - 40 * s), fy(y - 66 * s), fh(140 * s), fh(116 * s), BLOWER_DARK, cv.ink, INK_W, radius=fh(26 * s))
    cv.rect(g, fx(x - 10 * s), fy(y - 44 * s), fh(82 * s), fh(32 * s), RUBBER, radius=fh(10))
    _shudder(cv, g, spans)


def _shudder(cv: Canvas, g, spans: list[tuple[float, float]]) -> None:
    keys: list[tuple[float, float]] = [(0.0, 0.0)]
    for a, b in spans:
        for tick in range(math.ceil((b - a) * 12)):
            t = a + tick / 12
            keys.append((round(t, 3), -fh(3) if tick % 2 else fh(3)))
        keys.append((b, 0.0))
    if len(keys) > 1:
        cv.keys(g, "y", keys)


@register(
    "prop",
    "toon-lasagna",
    contract=dc.contract('toon-lasagna'),
    summary="A deep dish of lasagna carried in two oven gloves",
)
def lasagna(cv: Canvas, parent, at: Point = (185.0, 838.0), scale: float = 1.0) -> None:
    """The dish with its base at reference ``at``, an oven glove at each end."""
    x, y = _point(at, "a dish's place")
    s = _scale(scale)
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x - 160 * s), fy(y - 96 * s), fh(320 * s), fh(30 * s), "#e0612f", cv.ink, FINE_W, radius=fh(10))
    cv.rect(g, fx(x - 150 * s), fy(y - 74 * s), fh(300 * s), fh(22 * s), "#f6d67a")
    cv.rect(g, fx(x - 176 * s), fy(y - 56 * s), fh(352 * s), fh(56 * s), "#c9d6e2", cv.ink, INK_W, radius=fh(12))
    for side in (-1, 1):
        cv.rect(g, fx(x + side * 196 * s - 44 * s), fy(y - 84 * s), fh(88 * s), fh(76 * s), "#ef6f6c", cv.ink, FINE_W,
                radius=fh(26 * s))  # fmt: skip


@register(
    "prop",
    "toon-plate-of-toast",
    contract=dc.contract('toon-plate-of-toast'),
    summary="A plate of toast, two slices, on whatever it is put down on",
)
def toast(cv: Canvas, parent, at: Point = (300.0, 838.0), scale: float = 1.0) -> None:
    """The plate standing on reference ``at``, two slices leaning on each other."""
    x, y = _point(at, "a plate's place")
    s = _scale(scale)
    g = cv.group(parent, cv.uid("g"))
    for dx, lean in ((-30, -8.0), (24, 9.0)):
        px, py = fx(x + dx * s), fy(y - 10 * s)
        slice_ = cv.group(g, cv.uid("g"), rotation=lean, x=px, y=py, anchorX=px, anchorY=py)
        cv.rect(slice_, fx(x + (dx - 40) * s), fy(y - 92 * s), fh(80 * s), fh(82 * s), "#d99a4e", cv.ink, INK_W,
                radius=fh(16 * s))  # fmt: skip
        cv.rect(slice_, fx(x + (dx - 30) * s), fy(y - 82 * s), fh(60 * s), fh(62 * s), "#f6dfae", radius=fh(10 * s))
    cv.ellipse(g, fx(x - 104 * s), fy(y - 18 * s), fh(208 * s), fh(30 * s), PLATE, cv.ink, INK_W)

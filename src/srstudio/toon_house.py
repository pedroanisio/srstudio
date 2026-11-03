"""Toon rooms and props of the house: a hallway with a front door, what comes through it, and a surface for a shot
with no desk in it.

:func:`hallway` is a hall wall with a front door at the right, shut or open on the porch at night; :func:`horse`
stands in that doorway, a long face looking straight down the lens. :func:`ledge` takes the desk's place in front of
the character (``Staging(desk=toon_house.ledge)``, or drawn per shot from ``dress`` into ``shot.front``) with the
signature on it as the desk has it (ADR 0001), in one of :data:`LEDGES`. :func:`key_line` letters a reel's premise in
the band under the desk's top edge, so a viewer with the sound off has it from the first frame.

Geometry uses reference screen pixels (:func:`srstudio.toon.fx`/``fy``); typography uses frame pixels.
Animation keys use composition time; visibility bounds use the parent timeline.
Bad input is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from . import _toon_domestic_contracts as dc
from . import anatomy_ledger, checks, signature
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, _path, fh, fx, fy
from .toon_sets import _glow, _inked, _line, _shadow, cycle_keys

__all__ = [
    "BOW_TIE",
    "DOORS",
    "HORSE_BLINK",
    "KEY_LINE_MAX",
    "KEY_LINE_SIZE",
    "KEY_LINE_TOP",
    "LEDGES",
    "SHOWER_HEAD",
    "SOAK_STAGES",
    "WATER_PERIOD",
    "WATER_PHASES",
    "bathroom",
    "bedroom",
    "bow_tie",
    "day_card",
    "finger",
    "hallway",
    "horse",
    "key_line",
    "ledge",
    "quilt",
    "rope",
    "shower_water",
    "sink",
    "streaks",
    "suds",
    "tee",
    "thermostat",
    "towel",
    "vent",
    "water_dashes",
    "watering_can",
]

Point = tuple[float, float]

# the surface: (top, front, side panel, the code's shade)
LEDGES = {
    "oak": ("#c98f55", "#a56f3e", "#b57d48", "#7c5029"),
    "white": ("#f4f1ea", "#dcd7cc", "#e8e3d8", "#a59f92"),
    "steel": ("#c9d3dc", "#a4b0bc", "#b4bfca", "#73808e"),
    "dash": ("#4e5478", "#2a2d44", "#343854", "#a6acc6"),  # a car's dashboard
    "parlour": ("#fff6ee", "#f59ab5", "#ef86a5", "#8a2f4e"),  # an ice cream parlour's counter
}
LEDGE_TOP = 801  # as the desk's, so a character's arms rest where they do on it

KEY_LINE_TOP, KEY_LINE_H = 884, 62  # the band under the desk's top edge and the signature code
KEY_LINE_SIZE = 56
KEY_LINE_MAX = 34  # characters
KEY_LINE_BG, KEY_LINE_INK, KEY_LINE_PAD = "#1d1a2b", "#ffffff", 64.0
KEY_LINE_MARGIN = 40.0  # frame pixels left at each side

WALL = (("0", "#dfe7dc"), ("0.6", "#cfdccf"), ("1", "#bccbbd"))
WAINSCOT, WAINSCOT_LINE = "#f3efe6", "#cfc8b9"
DOORS = ("shut", "open", "none")
DOOR_BOX = (352.0, 214.0, 566.0, 800.0)  # x0, y0, x1, y1
DOOR_LEAF, DOOR_PANEL, DOOR_FRAME = "#3f6f73", "#4f868a", "#f3efe6"
BRASS = "#d9b25f"
NIGHT = (("0", "#141c3d"), ("0.7", "#22305a"), ("1", "#34406a"))
PORCH, PORCH_LIGHT = "#6b6f7e", "#ffd98a"
FRAMES = ((48, 200, 96, 118, "#9cc3d5"), (168, 232, 74, 92, "#e8b4a0"))  # the family pictures: x, y, w, h, colour

COAT, COAT_DARK, COAT_LIGHT = "#aeb2bc", "#7f8491", "#c8cbd2"
MANE = "#ece7dc"
BLAZE, MUZZLE = "#c8cbd2", "#858996"
HORSE_BLINK = 2.6  # seconds between blinks
STRAP = "#2c2a33"
SCALES = (0.5, 1.5)


def _rise(times: Sequence[float], what: str) -> None:
    last = None
    for t in times:
        if not (checks.number(t) and t >= 0):
            raise ToonDataError(f"{what}: a second is a number >= 0, got {t!r}")
        if last is not None and t <= last:
            raise ToonDataError(f"{what}: seconds rise, {t} came after {last}")
        last = t


@register(
    "prop",
    "toon-ledge",
    contract=dc.contract('toon-ledge'),
    summary="A plain surface in the desk's place, in oak, white or steel, signed as the desk is",
)
def ledge(cv: Canvas, parent, finish: str = "oak", inset: float = 0.0) -> None:
    """A surface with no laptop on it, in front of the character as the desk is, in one of :data:`LEDGES`, with the
    cactus on its top and the code on its front where the desk has them, ``inset`` pixels in from there for a shot
    that pushes in far enough to lose them."""
    if finish not in LEDGES:
        raise ToonDataError(f"a ledge is one of {sorted(LEDGES)}, got {finish!r}")
    if not (checks.number(inset) and inset >= 0):
        raise ToonDataError(f"a ledge's marks are inset by 0 or more, got {inset!r}")
    top, front, side, code = LEDGES[finish]
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(-10), fy(LEDGE_TOP + 47), fh(612), fh(300), front, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(LEDGE_TOP + 47), fh(106), fh(300), side, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(LEDGE_TOP), fh(612), fh(47), cv.ink, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(LEDGE_TOP + 12), fh(612), fh(31), top, cv.clear, 0, radius=0)
    signature.cactus(cv, g, fx(548 - inset), fy(838), 0.7)
    signature.code(cv, g, fx(580 - inset), fy(866), 14, color=code, opacity=0.9, align="end")


@register(
    "graphic",
    "toon-key-line",
    contract=dc.contract('toon-key-line'),
    summary="The reel's premise in one short line, white on a dark bar in the band under the desk's top edge",
)
def key_line(
    cv: Canvas, parent, text: str, start: float, end: float, *, measure: Callable[[str, float], float]
) -> None:
    """``text`` on a dark bar centred on the frame from ``start`` to ``end``, its width measured in the style's font
    by ``measure`` (``Shot.measure``). It sits below the signature code and above the frame's safe bottom."""
    if not text.strip() or len(text) > KEY_LINE_MAX:
        raise ToonDataError(f"a key line is 1 to {KEY_LINE_MAX} characters, got {text!r}")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a key line needs 0 <= start < end, got {start}..{end}")
    width = round(measure(text, KEY_LINE_SIZE) + KEY_LINE_PAD, 2)
    if width > cv.width - 2 * KEY_LINE_MARGIN:
        raise ToonDataError(f"the key line {text!r} is {width} px wide, over the frame's margins")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    x, top, height = round(cv.width / 2 - width / 2, 2), fy(KEY_LINE_TOP), fh(KEY_LINE_H)
    cv.rect(g, x, top, width, height, KEY_LINE_BG, cv.clear, 0, radius=round(height / 3, 2))
    cv.text(
        g, cv.uid("key-line"), text, x, top, int(width), int(height), KEY_LINE_SIZE, color=KEY_LINE_INK, wrap="none"
    )


def _porch(cv: Canvas, g, x0: float, y0: float, x1: float, y1: float) -> None:
    """The night outside an open door: the sky, the porch's boards and the lamp's light on them."""
    sky = cv.grad("toon-hallway-night", [(float(o), c) for o, c in NIGHT], (0, 0, 0, 1))
    cv.rect(g, fx(x0), fy(y0), fh(x1 - x0), fh(y1 - y0), sky, cv.clear, 0, radius=0)
    for sx, sy in ((x0 + 30, y0 + 40), (x0 + 120, y0 + 90), (x0 + 64, y0 + 150), (x1 - 34, y0 + 60)):
        cv.ellipse(g, fx(sx), fy(sy), fh(5), fh(5), "#fff6d8")
    _glow(cv, g, "toon-hallway-porch", (x0 + x1) / 2, y0 + 60, 170, PORCH_LIGHT)
    cv.rect(g, fx(x0), fy(y1 - 70), fh(x1 - x0), fh(70), PORCH, cv.clear, 0, radius=0)


@register(
    "location",
    "toon-hallway",
    contract=dc.contract('toon-hallway'),
    summary="A hall with a white dado, family pictures and a teal front door at the right, shut or open on the night",
)
def hallway(cv: Canvas, parent, door: str = "shut") -> None:
    """The hall wall in soft sage, its pictures at the left above the character, a dado rail, and the front door
    (:data:`DOOR_BOX`): ``"shut"``, ``"open"`` on the porch at night with the leaf folded back against the wall, or
    ``"none"``, plain wall where it would be."""
    if door not in DOORS:
        raise ToonDataError(f"a hallway's door is one of {DOORS}, got {door!r}")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, cv.grad("toon-hallway-wall", [(float(o), c) for o, c in WALL], (0, 0, 0, 1)))
    cv.rect(g, fx(-10), fy(640), fh(612), fh(240), WAINSCOT, cv.ink, FINE_W * 0.6, radius=0)
    for x in range(24, 340, 92):
        cv.rect(g, fx(x), fy(664), fh(74), fh(150), WAINSCOT, WAINSCOT_LINE, FINE_W * 0.6, radius=fh(3))
    for x, y, w, h, colour in FRAMES:
        cv.rect(g, fx(x + 6), fy(y + 7), fh(w), fh(h), "#1b1430", cv.clear, 0, radius=fh(3), opacity=0.16)
        cv.rect(g, fx(x), fy(y), fh(w), fh(h), "#7c5a3c", cv.ink, FINE_W * 0.8, radius=fh(3))
        cv.rect(g, fx(x + 10), fy(y + 10), fh(w - 20), fh(h - 20), colour, cv.ink, FINE_W * 0.4, radius=0)
        cv.ellipse(g, fx(x + w / 2 - 12), fy(y + h / 2 - 16), fh(24), fh(24), "#fff3df", cv.ink, FINE_W * 0.4)
    if door == "none":
        return
    x0, y0, x1, y1 = DOOR_BOX
    cv.rect(g, fx(x0 - 16), fy(y0 - 16), fh(x1 - x0 + 32), fh(y1 - y0 + 32), DOOR_FRAME, cv.ink, INK_W * 0.8, radius=0)
    if door == "shut":
        cv.rect(g, fx(x0), fy(y0), fh(x1 - x0), fh(y1 - y0), DOOR_LEAF, cv.ink, INK_W * 0.7, radius=0)
        for ty, th in ((y0 + 30, 220), (y0 + 280, 240)):
            cv.rect(g, fx(x0 + 28), fy(ty), fh(x1 - x0 - 56), fh(th), DOOR_PANEL, cv.ink, FINE_W * 0.5, radius=fh(4))
        cv.ellipse(g, fx(x0 + 22), fy(y0 + 268), fh(24), fh(24), BRASS, cv.ink, FINE_W * 0.6)
    else:
        _porch(cv, g, x0, y0, x1, y1)
        _path(cv, g, f"M {fx(x0)} {fy(y0)} L {fx(x0 + 34)} {fy(y0 + 34)} L {fx(x0 + 34)} {fy(y1 - 34)} "
              f"L {fx(x0)} {fy(y1)} Z", DOOR_LEAF, INK_W * 0.7)  # fmt: skip


def rope(cv: Canvas, parent, points: Sequence[Point], colour: str = "#c9a56b") -> None:
    """A lead rope through reference ``points``, from the hand that holds it to what is on the end of it."""
    _line(cv, parent, points, 7.0, cv.ink)
    _line(cv, parent, points, 4.0, colour)


def _flick(cv: Canvas, node, at: Sequence[float], up: float, down: float, end: float, hold: float = 0.12) -> None:
    """Hold keys on ``node``'s opacity: ``down`` from each of ``at`` for ``hold`` seconds, ``up`` otherwise."""
    keys: list[tuple[float, float]] = [(0.0, up)]
    for t in at:
        if t + hold < end:
            keys += [(round(t, 6), down), (round(t + hold, 6), up)]
    cv.keys(node, "opacity", keys, local=False)


@register(
    "prop",
    "toon-horse",
    contract=dc.contract('toon-horse'),
    summary="A horse's long face, front on, in a halter, its neck behind it: it blinks and looks straight at you",
)
def horse(
    cv: Canvas,
    parent,
    at: Point = (460, 470),
    scale: float = 1.0,
    start: float = 0.0,
    end: float = 0.0,
    blinks: Sequence[float] | None = None,
    id: str = "horse",
    neck: float = 640.0,
) -> None:
    """The head centred on reference ``at``, about 420 tall at ``scale`` 1 (within :data:`SCALES`), the neck running
    down behind it to ``neck`` below that point, shorter for a horse whose chest a car hides. Its lids drop at each
    of ``blinks`` (project seconds), every :data:`HORSE_BLINK` seconds from ``start`` to ``end`` when ``blinks`` is
    None. ``end`` 0 disables automatic blinks; explicit ``blinks`` still run. These times do not hide the horse."""
    if not (checks.number(scale) and SCALES[0] <= scale <= SCALES[1]):
        raise ToonDataError(f"a horse's scale is within {SCALES}, got {scale!r}")
    if not (isinstance(at, tuple | list) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"a horse stands at a reference point (x, y), got {at!r}")
    if not (checks.number(start) and checks.number(end) and start >= 0 and end >= 0):
        raise ToonDataError(f"a horse's clock needs start and end >= 0, got {start}, {end}")
    times = [start + 0.9 + k * HORSE_BLINK for k in range(int(max(end - start, 0) / HORSE_BLINK) + 1)]
    times = [t for t in times if t < end] if blinks is None else list(blinks)
    _rise(times, "a horse's blinks")
    x, y = at
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)

    def local(points: Sequence[Point]) -> list[Point]:  # the brush works in reference pixels of the frame
        return [(p[0], p[1] + 70) for p in points]

    _inked(cv, g, local([(-96, 40), (-132, 330), (-120, neck), (120, neck), (132, 330), (96, 40)]), COAT_DARK)
    for side in (-1, 1):
        ear = [(side * 44, -176), (side * 78, -262), (side * 94, -160)]
        _inked(cv, g, local(ear), COAT)
        _fill_ear = [(side * 58, -186), (side * 78, -236), (side * 84, -170)]
        _inked(cv, g, local(_fill_ear), "#d9a58a", weight=2.0)
    face = [(-92, -160), (-44, -196), (44, -196), (92, -160), (96, -60), (76, 50), (68, 150), (54, 212), (0, 230),
            (-54, 212), (-68, 150), (-76, 50), (-96, -60)]  # fmt: skip
    _inked(cv, g, local(face), COAT, weight=6.5, steps=6)
    _inked(cv, g, local([(-20, -130), (20, -130), (26, 20), (34, 118), (-34, 118), (-26, 20)]), BLAZE, weight=2.0)
    _inked(cv, g, local([(-66, 120), (66, 120), (56, 208), (0, 228), (-56, 208)]), MUZZLE, weight=3.0, steps=6)
    for side in (-1, 1):
        cv.ellipse(g, fh(side * 30 - 11), fh(162), fh(22), fh(30), "#1a120d")
    _line(cv, g, local([(-30, 206), (0, 214), (30, 206)]), 3.0)
    tuft = [(-46, -188), (-30, -246), (-8, -206), (8, -256), (22, -204), (46, -238), (44, -160), (0, -128), (-44, -160)]
    _inked(cv, g, local(tuft), MANE)
    for side in (-1, 1):  # the eyes, set wide, a heavy lid across each
        ex = side * 74
        cv.ellipse(g, fh(ex - 27), fh(-108), fh(54), fh(50), "#fffdf7", cv.ink, FINE_W)
        cv.ellipse(g, fh(ex - 15), fh(-96), fh(30), fh(32), "#20140d")
        cv.ellipse(g, fh(ex - 6), fh(-92), fh(9), fh(9), "#ffffff")
        cv.rect(g, fh(ex - 30), fh(-112), fh(60), fh(22), COAT, cv.clear, 0, radius=fh(10))
        _line(cv, g, local([(ex - 29, -89), (ex, -92), (ex + 29, -89)]), 4.0)
    lids = cv.group(g, f"{id}-lids", opacity=0.0)
    for side in (-1, 1):
        cv.ellipse(lids, fh(side * 74 - 29), fh(-112), fh(58), fh(56), COAT, cv.ink, FINE_W)
    if times:
        _flick(cv, lids, times, 0.0, 1.0, end or times[-1] + 1)
    # the halter: nose band, cheek straps and the ring the rope is clipped to
    _line(cv, g, local([(-72, 96), (0, 108), (72, 96)]), 9.0, STRAP)
    for side in (-1, 1):
        _line(cv, g, local([(side * 92, -62), (side * 76, 40), (side * 72, 96)]), 8.0, STRAP)
    cv.ellipse(g, fh(-12), fh(208 - 90), fh(24), fh(24), BRASS, cv.ink, FINE_W * 0.6)
    _shadow(cv, g, 0, 70 + 640, 240)


THERMOSTAT_SIZE = 76
THERMOSTAT_BODY, THERMOSTAT_DIAL, THERMOSTAT_INK = "#f6f2e8", "#dfe6e4", "#23303a"
READING = re.compile(r"\d{2}")
SLEEVE = "#4a6fa5"
NAIL = "#fff1e6"
GLIDE = 0.1  # seconds a finger takes between two places
VENT, VENT_SLAT = "#e9e6dc", "#8e918f"
BEDROOM_WALL = (("0", "#26305e"), ("0.7", "#1f2850"), ("1", "#181f42"))
HEADBOARD, PILLOW = "#5a3f33", "#e8e4f0"
MOON_SKY, MOON = "#0f1534", "#f4edc9"
QUILTS = {"plum": ("#7b4a78", "#94608f"), "teal": ("#2f7277", "#46898c")}
NIGHTSTAND, NIGHTSTAND_FRONT = "#6f4d38", "#5c3f2e"


def _point(at: object, what: str) -> tuple[float, float]:
    if not (isinstance(at, tuple | list) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"{what} is a reference point (x, y), got {at!r}")
    return float(at[0]), float(at[1])


@register(
    "prop",
    "toon-thermostat",
    contract=dc.contract('toon-thermostat'),
    summary="A wall thermostat whose two-digit reading changes on cue",
)
def thermostat(
    cv: Canvas,
    parent,
    readings: Sequence[tuple[float, str]],
    end: float = 0.0,
    at: Point = (450, 440),
    scale: float = 1.0,
    id: str = "thermostat",
) -> None:
    """The dial centred on reference ``at``, showing each ``(second, two digits)`` of ``readings`` until the next one,
    the last until ``end``. A still (``end`` 0) takes one reading at 0."""
    if not readings or any(not (isinstance(r, tuple | list) and len(r) == 2) for r in readings):
        raise ToonDataError(f"a thermostat needs (second, reading) pairs, got {readings!r}")
    times = [r[0] for r in readings]
    _rise(times, "a thermostat's readings")
    if times[0] != 0 or (not end and len(times) > 1) or (end and times[-1] >= end):
        raise ToonDataError(f"a thermostat's readings start at 0 and lie before its end, got {times} of {end}")
    if any(not (isinstance(r[1], str) and READING.fullmatch(r[1])) for r in readings):
        raise ToonDataError(f"a thermostat reads two digits, got {[r[1] for r in readings]}")
    if not (checks.number(scale) and SCALES[0] <= scale <= SCALES[1]):
        raise ToonDataError(f"a thermostat's scale is within {SCALES}, got {scale!r}")
    x, y = _point(at, "a thermostat's place")
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    half, dial = fh(90), fh(72)
    cv.rect(g, -half + fh(7), -half + fh(8), 2 * half, 2 * half, "#1b1430", cv.clear, 0, radius=fh(22), opacity=0.16)
    cv.rect(g, -half, -half, 2 * half, 2 * half, THERMOSTAT_BODY, cv.ink, INK_W * 0.8, radius=fh(22))
    cv.ellipse(g, -dial, -dial, 2 * dial, 2 * dial, THERMOSTAT_DIAL, cv.ink, FINE_W)
    box_w, box_h = int(fh(120)), int(fh(70))
    for i, (start, reading) in enumerate(readings):
        stop = readings[i + 1][0] if i + 1 < len(readings) else end
        shown = cv.group(g, cv.uid("g"), start=start, end=stop) if end else cv.group(g, cv.uid("g"))
        cv.text(shown, cv.uid("reading"), reading, -box_w / 2, -box_h / 2, box_w, box_h, THERMOSTAT_SIZE,
                color=THERMOSTAT_INK, wrap="none")  # fmt: skip


@register(
    "prop",
    "toon-finger",
    contract=dc.contract('toon-finger'),
    summary="A forearm and a pointing finger, its tip going where it is told",
)
def finger(
    cv: Canvas,
    parent,
    tip: Point = (345, 520),
    angle: float = 0.0,
    colour: str = "#d8b08c",
    sleeve: str = SLEEVE,
    moves: Sequence[tuple[float, float, float]] = (),
    start: float = 0.0,
    end: float = 0.0,
    id: str = "finger",
) -> None:
    """A finger whose tip is on reference ``tip``, pointing up turned ``angle`` degrees clockwise, its forearm running
    back out of frame. It shows from ``start`` to ``end`` (always, in a still), gliding to each ``(second, x, y)`` of
    ``moves``."""
    x, y = _point(tip, "a finger's tip")
    if not checks.number(angle):
        raise ToonDataError(f"a finger's angle is a number of degrees, got {angle!r}")
    if not (checks.number(start) and checks.number(end) and start >= 0 and end >= 0):
        raise ToonDataError(f"a finger's clock needs start and end >= 0, got {start}, {end}")
    _rise([m[0] for m in moves], "a finger's moves")
    if moves and not end:
        raise ToonDataError("a still finger cannot move")
    timed = {"start": start, "end": end} if end else {}
    g = cv.group(parent, id, x=fx(x), y=fy(y), rotation=angle, **timed)
    # the index is the hand's outer edge, the other fingers curled beside it and the thumb across them: a pointing
    # finger never rises from the middle of the hand
    cv.rect(g, -fh(8), fh(180), fh(92), fh(900), sleeve, cv.ink, INK_W * 0.8, radius=fh(14))
    cv.rect(g, -fh(24), fh(104), fh(126), fh(130), colour, cv.ink, INK_W * 0.8, radius=fh(34))
    for k in range(3):  # the three curled fingers, side on
        cv.rect(g, fh(22 + k * 20), fh(96 + k * 2), fh(28), fh(58), colour, cv.ink, INK_W * 0.6, radius=fh(13))
    cv.rect(g, -fh(21), 0, fh(42), fh(150), colour, cv.ink, INK_W * 0.8, radius=fh(20))
    cv.rect(g, -fh(19), fh(100), fh(38), fh(62), colour, cv.clear, 0, radius=0)
    cv.ellipse(g, fh(-4), fh(160), fh(92), fh(38), colour, cv.ink, INK_W * 0.8)  # the thumb, across the curled fingers
    cv.ellipse(g, -fh(11), fh(6), fh(22), fh(26), NAIL, cv.ink, FINE_W * 0.4)
    _line(cv, g, [(-14, 70 + 58), (14, 70 + 58)], 3.0)
    if moves:
        for axis, first, index, convert in (("x", x, 1, fx), ("y", y, 2, fy)):
            keys, here = [(0.0, convert(first))], convert(first)
            for move in moves:
                keys.append((move[0], here))
                here = convert(move[index])
                keys.append((move[0] + GLIDE, here))
            cv.keys(g, axis, keys, hold=False, local=False)


@register("prop", "toon-vent", contract=dc.contract('toon-vent'), summary="A wall vent with white slats")
def vent(cv: Canvas, parent, at: Point = (452, 470), width: float = 180.0) -> None:
    """A vent centred on reference ``at``, ``width`` wide (120 to 240) and a little over half as tall."""
    x, y = _point(at, "a vent's place")
    if not (checks.number(width) and 120 <= width <= 240):
        raise ToonDataError(f"a vent is 120 to 240 wide, got {width!r}")
    height = round(width * 0.58, 2)
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x - width / 2), fy(y - height / 2), fh(width), fh(height), VENT, cv.ink, INK_W * 0.7, radius=fh(6))
    for k in range(1, 6):
        ty = y - height / 2 + k * height / 6
        cv.rect(g, fx(x - width / 2 + 12), fy(ty - 3), fh(width - 24), fh(6), VENT_SLAT, cv.clear, 0, radius=fh(3))


@register(
    "location",
    "toon-bedroom",
    contract=dc.contract('toon-bedroom'),
    summary="A dark bedroom at night: a wooden headboard, a pillow, a moonlit window",
)
def bedroom(cv: Canvas, parent) -> None:
    """The wall at night, a window with the moon at the right above the pill's clearance, the headboard and the pillow
    behind the character. :func:`quilt` goes in front of the character."""
    g = cv.group(parent, cv.uid("g"))
    wall = cv.grad("toon-bedroom-wall", [(float(o), c) for o, c in BEDROOM_WALL], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, wall)
    cv.rect(g, fx(392), fy(330), fh(170), fh(220), MOON_SKY, cv.ink, INK_W * 0.8, radius=fh(4))
    cv.ellipse(g, fx(452), fy(372), fh(62), fh(62), MOON)
    _line(cv, g, [(477, 330), (477, 550)], 6.0)
    _line(cv, g, [(392, 440), (562, 440)], 6.0)
    cv.rect(g, fx(-20), fy(330), fh(390), fh(560), HEADBOARD, cv.ink, INK_W * 0.8, radius=fh(40))
    cv.ellipse(g, fx(-30), fy(470), fh(390), fh(330), PILLOW, cv.ink, INK_W * 0.7)


@register(
    "prop",
    "toon-quilt",
    contract=dc.contract('toon-quilt'),
    summary="A patched quilt in front of the character, a nightstand signed as the desk is",
)
def quilt(cv: Canvas, parent, pattern: str = "plum") -> None:
    """A quilt up to the character's chest in one of :data:`QUILTS`, with the nightstand holding the cactus and the
    code where the desk has them."""
    if pattern not in QUILTS:
        raise ToonDataError(f"a quilt is one of {sorted(QUILTS)}, got {pattern!r}")
    base, patch = QUILTS[pattern]
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(-20), fy(740), fh(540), fh(420), base, cv.ink, INK_W, radius=fh(30))
    for row, top in enumerate(range(770, 1100, 76)):
        for col, left in enumerate(range(0, 500, 92)):
            if (row + col) % 2 == 0:
                cv.rect(g, fx(left), fy(top), fh(78), fh(62), patch, cv.clear, 0, radius=fh(6))
    cv.rect(g, fx(506), fy(838), fh(110), fh(16), NIGHTSTAND, cv.ink, FINE_W, radius=fh(3))
    cv.rect(g, fx(516), fy(854), fh(100), fh(320), NIGHTSTAND_FRONT, cv.ink, FINE_W, radius=0)
    signature.cactus(cv, g, fx(548), fy(838), 0.7)
    signature.code(cv, g, fx(580), fy(866), 14, color="#b9a48f", opacity=0.9, align="end")


SOAK_STAGES = ("skin", "plant", "mail", "frog")  # what a pan grows, each staying once it has come
COUNTER_TOP, COUNTER_EDGE, CODE_SHADE = "#e6dfcf", "#cfc6b2", "#9a917f"
SINK_RIM, SINK_BOWL = "#c4ccd3", "#7f8a94"
PAN, PAN_RIM, PAN_HANDLE = "#2b2d33", "#454852", "#1f2026"
WATER, SCUM, SCUM_LINE = "#9fb3b0", "#b7a678", "#8f7f52"
LEAF, LEAF_DARK, STEM = "#5cae5a", "#3f8a48", "#3f7a3e"
MAILBOX, MAILBOX_FLAG, ENVELOPE = "#3d6fb0", "#d8413a", "#fbf7ec"
TINY_FROG, TINY_FROG_DARK = "#7cc35a", "#4f9440"
WAVE_PERIOD = 0.5  # seconds per wave of the tiny frog's arm
DAY_INK, DAY_HEAD, DAY_PAPER = "#23303a", "#b92f2a", "#fffdf7"
DAY_SIZE = 96
CAN, CAN_DARK, DROP = "#3f8f8f", "#2c6c6e", "#8fcbe8"
DROP_FALL, DROP_EVERY = 118.0, 0.36


@register(
    "prop",
    "toon-sink",
    contract=dc.contract('toon-sink'),
    summary="A counter seen from above with a sink, a pan left in it and what the pan grows",
)
def sink(
    cv: Canvas, parent, stages: Sequence[tuple[float, str]] = (), end: float = 0.0, id: str = "sink", inset: float = 0.0
) -> None:
    """In front of the character in the desk's place, signed as it is: a pale counter, a steel sink and a pan in dirty
    water. Each ``(second, stage)`` of ``stages``, in the order of :data:`SOAK_STAGES`, comes and stays until ``end``;
    in a still (``end`` 0) every stage named shows. The marks sit ``inset`` pixels in, as a :func:`ledge`'s do, for a
    shot that pushes in far enough to lose them."""
    if not (checks.number(inset) and inset >= 0):
        raise ToonDataError(f"a sink's marks are inset by 0 or more, got {inset!r}")
    names = [stage[1] for stage in stages]
    if any(n not in SOAK_STAGES for n in names) or names != [n for n in SOAK_STAGES if n in names]:
        raise ToonDataError(f"a pan's stages come in the order {SOAK_STAGES}, each once, got {names}")
    _rise([stage[0] for stage in stages], "a pan's stages")
    if end and stages and stages[-1][0] >= end:
        raise ToonDataError(f"a pan's stages lie before its end, got {stages[-1][0]} of {end}")
    g = cv.group(parent, id)
    cv.rect(g, fx(-10), fy(LEDGE_TOP), fh(612), fh(340), COUNTER_TOP, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(LEDGE_TOP), fh(612), fh(14), cv.ink, cv.clear, 0, radius=0)
    cv.ellipse(g, fx(28), fy(838), fh(476), fh(230), SINK_RIM, cv.ink, INK_W)
    cv.ellipse(g, fx(50), fy(852), fh(432), fh(198), SINK_BOWL, cv.ink, FINE_W)
    _line(cv, g, [(396, 968), (520, 1026)], 30.0, PAN_HANDLE)
    cv.ellipse(g, fx(112), fy(866), fh(296), fh(150), PAN, cv.ink, INK_W * 0.8)
    cv.ellipse(g, fx(128), fy(876), fh(264), fh(126), WATER, PAN_RIM, FINE_W)
    for i, (x0, x1, y) in enumerate(((176, 248, 912), (280, 356, 952), (196, 262, 972))):
        _line(cv, g, [(x0, y), ((x0 + x1) / 2, y + 5), (x1, y)], 3.0, PAN_RIM, 0.45 + 0.1 * i)
    signature.cactus(cv, g, fx(548 - inset), fy(838), 0.7)
    signature.code(cv, g, fx(580 - inset), fy(866), 14, color=CODE_SHADE, opacity=0.9, align="end")
    drawers = {"skin": _skin, "plant": _sprout, "mail": _mailbox, "frog": _tiny_frog}
    for start, name in stages:
        layer = cv.group(g, f"{id}-{name}", start=start, end=end) if end else cv.group(g, f"{id}-{name}")
        drawers[name](cv, layer, start, end)


def _skin(cv: Canvas, g, start: float, end: float) -> None:
    cv.ellipse(g, fx(130), fy(878), fh(260), fh(122), SCUM, opacity=0.92)
    for x0, y0, x1, y1 in ((168, 906, 262, 914), (272, 924, 362, 918), (178, 958, 280, 966), (232, 936, 328, 944)):
        _line(cv, g, [(x0, y0), ((x0 + x1) / 2, y0 + 7), (x1, y1)], 3.5, SCUM_LINE)


def _sprout(cv: Canvas, g, start: float, end: float) -> None:
    _line(cv, g, [(214, 948), (208, 896), (224, 846)], 8.0, STEM)
    for x, y, w, h, colour in ((150, 842, 66, 40, LEAF), (222, 806, 72, 44, LEAF), (172, 884, 44, 26, LEAF_DARK)):
        cv.ellipse(g, fx(x), fy(y), fh(w), fh(h), colour, cv.ink, FINE_W)


def _mailbox(cv: Canvas, g, start: float, end: float) -> None:
    cv.rect(g, fx(322), fy(868), fh(12), fh(92), "#8a6a4a", cv.ink, FINE_W, radius=fh(2))
    cv.rect(g, fx(280), fy(816), fh(98), fh(58), MAILBOX, cv.ink, INK_W * 0.6, radius=fh(24))
    cv.rect(g, fx(262), fy(830), fh(62), fh(32), ENVELOPE, cv.ink, FINE_W, radius=fh(2))
    _line(cv, g, [(262, 830), (293, 848), (324, 830)], 2.5)
    cv.rect(g, fx(372), fy(806), fh(8), fh(36), MAILBOX_FLAG, cv.ink, FINE_W * 0.6, radius=0)
    cv.rect(g, fx(372), fy(806), fh(26), fh(16), MAILBOX_FLAG, cv.ink, FINE_W * 0.6, radius=0)


def _tiny_frog(cv: Canvas, g, start: float, end: float) -> None:
    cx, cy = 270.0, 950.0
    cv.ellipse(g, fx(cx - 34), fy(cy - 18), fh(68), fh(46), TINY_FROG, cv.ink, INK_W * 0.6)
    for side in (-1, 1):
        cv.ellipse(g, fx(cx + side * 18 - 11), fy(cy - 32), fh(22), fh(22), "#fffdf7", cv.ink, FINE_W)
        cv.ellipse(g, fx(cx + side * 18 - 4), fy(cy - 26), fh(8), fh(10), "#20140d")
    _line(cv, g, [(cx - 14, cy + 6), (cx, cy + 12), (cx + 14, cy + 6)], 3.0)
    x, y = fx(cx + 30), fy(cy)
    arm = cv.group(g, cv.uid("g"), anchorX=x, anchorY=y, x=x, y=y)
    _line(cv, arm, [(cx + 30, cy), (cx + 46, cy - 24), (cx + 54, cy - 44)], 9.0, TINY_FROG_DARK)
    cv.ellipse(arm, fx(cx + 46), fy(cy - 56), fh(16), fh(16), TINY_FROG, cv.ink, FINE_W)
    if end:
        cv.keys(arm, "rotation", cycle_keys([(0.0, -18.0), (WAVE_PERIOD / 2, 18.0)], WAVE_PERIOD, start, end),
                hold=False, local=False)  # fmt: skip


@register(
    "prop",
    "toon-day-card",
    contract=dc.contract('toon-day-card'),
    summary="A tear-off card on the fridge counting days on cue",
)
def day_card(
    cv: Canvas,
    parent,
    days: Sequence[tuple[float, int]],
    end: float = 0.0,
    at: Point = (500, 470),
    id: str = "day-card",
) -> None:
    """A card centred on reference ``at`` headed DAY, showing each ``(second, day)`` of ``days`` (1 to 999) until the
    next, the last until ``end``. A still (``end`` 0) takes one day at 0."""
    if not days or any(not (isinstance(d, tuple | list) and len(d) == 2) for d in days):
        raise ToonDataError(f"a day card needs (second, day) pairs, got {days!r}")
    times = [d[0] for d in days]
    _rise(times, "a day card's days")
    if times[0] != 0 or (not end and len(times) > 1) or (end and times[-1] >= end):
        raise ToonDataError(f"a day card's days start at 0 and lie before its end, got {times} of {end}")
    if any(isinstance(d[1], bool) or not isinstance(d[1], int) or not 1 <= d[1] <= 999 for d in days):
        raise ToonDataError(f"a day is a whole number from 1 to 999, got {[d[1] for d in days]}")
    x, y = _point(at, "a day card's place")
    g = cv.group(parent, id, x=fx(x), y=fy(y))
    w, h, head = fh(150), fh(176), fh(52)
    cv.rect(g, -w / 2 + fh(6), -h / 2 + fh(7), w, h, "#1b1430", cv.clear, 0, radius=fh(8), opacity=0.18)
    cv.rect(g, -w / 2, -h / 2, w, h, DAY_PAPER, cv.ink, INK_W * 0.8, radius=fh(8))
    cv.rect(g, -w / 2, -h / 2, w, head, DAY_HEAD, cv.ink, INK_W * 0.8, radius=fh(8))
    cv.text(g, cv.uid("day-head"), "DAY", -w / 2, -h / 2, int(w), int(head), 52, color="#ffffff", wrap="none")
    for i, (start, day) in enumerate(days):
        stop = days[i + 1][0] if i + 1 < len(days) else end
        shown = cv.group(g, cv.uid("g"), start=start, end=stop) if end else cv.group(g, cv.uid("g"))
        cv.text(shown, cv.uid("day"), str(day), -w / 2, -h / 2 + head, int(w), int(h - head), DAY_SIZE, color=DAY_INK,
                wrap="none")  # fmt: skip


@register(
    "prop",
    "toon-watering-can",
    contract=dc.contract('toon-watering-can'),
    summary="A watering can in a dark glove, pouring",
)
def watering_can(
    cv: Canvas,
    parent,
    at: Point = (388, 690),
    start: float = 0.0,
    end: float = 0.0,
    pour: float = 0.0,
    id: str = "watering-can",
) -> None:
    """A can with its spout's rose near reference ``at``, tipped down and to the left, shown from ``start`` to ``end``
    (always, in a still), its drops falling from ``pour``."""
    anatomy_ledger.loose_hand(cv, "toon-watering-can")
    x, y = _point(at, "a watering can's place")
    if not (checks.number(start) and checks.number(end) and checks.number(pour) and min(start, end, pour) >= 0):
        raise ToonDataError(f"a watering can's clock needs times >= 0, got {start}, {end}, {pour}")
    if end and not start <= pour < end:
        raise ToonDataError(f"a watering can pours within its time, got {pour} of {start}..{end}")
    timed = {"start": start, "end": end} if end else {}
    outer = cv.group(parent, id, **timed)
    g = cv.group(outer, cv.uid("g"), x=fx(x), y=fy(y), rotation=-16)
    _line(cv, g, [(0, 70 + 2), (96, 70 + 46)], 20.0, CAN_DARK)
    cv.rect(g, fh(84), fh(10), fh(150), fh(120), CAN, cv.ink, INK_W * 0.8, radius=fh(14))
    cv.rect(g, -fh(14), -fh(18), fh(22), fh(44), CAN_DARK, cv.ink, FINE_W, radius=fh(4))
    cv.ellipse(g, fh(124), -fh(44), fh(84), fh(84), cv.clear, cv.ink, INK_W * 0.8)
    cv.ellipse(g, fh(190), fh(30), fh(62), fh(66), "#2e2a33", cv.ink, FINE_W)
    if not end:
        return
    for k in range(3):
        px = fx(x - 14 + k * 11)
        drop = cv.group(outer, cv.uid("g"), x=px, y=fy(y + 20), start=pour, end=end)
        cv.ellipse(drop, -fh(5), -fh(7), fh(10), fh(14), DROP, cv.ink, FINE_W * 0.3)
        fall = [(0.0, fy(y + 20)), (DROP_EVERY * 0.9, fy(y + 20 + DROP_FALL))]
        cv.keys(drop, "y", cycle_keys(fall, DROP_EVERY, pour, end, phase=k * 0.11), hold=False, local=False)


TEE_LOUD = "#b7e04a"
TEE_BODY = "M -30 0 L -78 16 L -66 140 L 66 140 L 78 16 L 30 0 C 22 24 -22 24 -30 0 Z"
TEE_COLLAR = "M -30 0 C -22 24 22 24 30 0"
TEE_HEART = "M 0 124 C -68 76 -54 34 -20 40 C -9 42 -2 49 0 58 C 2 49 9 42 20 40 C 54 34 68 76 0 124 Z"
TEE_MOUSTACHE = (
    "M 0 84 C -8 76 -18 78 -24 86 C -28 92 -34 88 -31 83 C -34 96 -14 98 0 90 "
    "C 14 98 34 96 31 83 C 34 88 28 92 24 86 C 18 78 8 76 0 84 Z"
)


@register(
    "prop",
    "toon-tee",
    contract=dc.contract('toon-tee'),
    summary="A loud T-shirt front with an invented portrait in a heart, between a figure's arms",
)
def tee(
    cv: Canvas,
    parent,
    at: object,
    scale: float = 1.0,
    colour: str = TEE_LOUD,
    start: float | None = None,
    end: float | None = None,
    id: str = "tee",
) -> None:
    """The front of a T-shirt whose collar's middle is on reference ``at``, drawn over a figure's chest. Its print is
    the same smug moustached potato in a pink heart on everyone: an invented face, with no word on it."""
    x, y = _point(at, "a tee's place")
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a tee's scale is over 0, got {scale!r}")
    if not (isinstance(colour, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", colour)):
        raise ToonDataError(f"a tee's colour is a #rrggbb colour, got {colour!r}")
    timing = {} if start is None else {"start": start, "end": end}
    outer = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale, **timing)
    g = cv.group(outer, cv.uid("g"), scaleX=fh(1), scaleY=fh(1))
    line = INK_W / fh(1)
    cv.path(g, TEE_BODY, colour, cv.ink, line)
    cv.path(g, TEE_COLLAR, cv.clear, cv.ink, line * 1.6)
    cv.path(g, TEE_HEART, "#ff4f8b", cv.ink, line * 0.7)
    cv.ellipse(g, -22, 42, 44, 56, "#d8b078", cv.ink, line * 0.6)
    cv.ellipse(g, -13, 62, 7, 7, cv.ink)
    cv.ellipse(g, 6, 62, 7, 7, cv.ink)
    cv.path(g, "M -5 76 C -2 80 2 80 5 76", cv.clear, cv.ink, line * 0.5)
    cv.path(g, TEE_MOUSTACHE, "#3a2a1a", cv.clear, 0)


BOW_TIE = "#1d1a26"


@register(
    "prop",
    "toon-bow-tie",
    contract=dc.contract('toon-bow-tie'),
    summary="A black bow tie under a figure's chin, which makes anyone a waiter",
)
def bow_tie(cv: Canvas, parent, at: object, scale: float = 1.0, id: str = "bow-tie") -> None:
    """A bow tie whose knot is on reference ``at``, in the figure's own coordinates so it scales with the figure."""
    x, y = _point(at, "a bow tie's place")
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a bow tie's scale is over 0, got {scale!r}")
    outer = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    g = cv.group(outer, cv.uid("g"), scaleX=fh(1), scaleY=fh(1))
    line = INK_W / fh(1)
    for side in (-1, 1):
        cv.path(
            g,
            f"M {side * 6} -6 C {side * 22} -14 {side * 40} -24 {side * 48} -22 "
            f"C {side * 54} -8 {side * 54} 8 {side * 48} 22 C {side * 40} 24 {side * 22} 14 {side * 6} 6 Z",
            BOW_TIE,
            cv.ink,
            line,
        )
        cv.path(g, f"M {side * 16} -5 L {side * 36} -11", cv.clear, "#4a4658", line * 0.7)
    cv.rect(g, -10, -11, 20, 22, "#34303f", cv.ink, line, radius=5.0)


# -- the bathroom ------------------------------------------------------------------------------------------------------
BATH_WALL = ((0, "#d7ecea"), (1, "#a8cfd0"))
BATH_GROUT = "#8fbcbf"
BATH_TILE = 74  # reference pixels between grout lines
CHROME, CHROME_DARK = "#d5dde3", "#8d9aa6"
BOTTLES = ((430, 92, 46, "#f28fa8"), (484, 74, 38, "#f5c04e"), (528, 104, 42, "#8fd0a0"))  # x, height, width, colour
SHELF_Y = 626
SHOWER_HEAD = (256.0, 190.0)  # the rose's middle: above the caption and over where a head stands
WATER_PERIOD, WATER_PHASES = 0.24, 3  # seconds a dash takes to fall one dash and a gap, in this many steps
WATER_DASH, WATER_GAP = 110.0, 70.0  # along the fall, in reference pixels
WATER_FROM, WATER_TO = 12.0, 830.0  # the fall begins this far under the rose and ends behind the ledge
WATER_SPREAD = 0.12  # how wide a column's first dash starts, as a share of how far out it ends
WATER_XS = tuple(range(-304, 817, 56))  # where each column lands at the fall's foot; the fan runs off the frame
WATER_COLOUR, WATER_W, WATER_OPACITY = "#4fa8d8", 6.0, 0.75
SUDS_PUFFS = ((-62, -6, 58), (-22, -34, 72), (28, -28, 66), (66, -2, 52), (-4, 10, 74), (34, 14, 46), (-40, 18, 44))
SUDS_LINE, SUDS_SHADE = "#9db8c4", "#dfeef4"
TOWEL_COLOUR, TOWEL_SHADE, TOWEL_LINE = "#f7efe2", "#e2d4bf", "#8a7a68"
TOWEL_DOME = "M -128 20 C -136 -52 -70 -96 0 -98 C 70 -96 136 -52 128 20 C 84 44 -84 44 -128 20 Z"
TOWEL_FOLDS = ("M -112 -14 C -60 -2 40 -46 112 -36", "M -74 -62 C -30 -52 30 -76 78 -72")
TOWEL_TAIL = "M 60 -86 C 92 -128 138 -124 150 -92 C 132 -86 112 -74 104 -52 Z"


@register(
    "location",
    "toon-bathroom",
    contract=dc.contract('toon-bathroom'),
    summary="A tiled shower wall with a chrome shower head and a shelf of bottles",
)
def bathroom(cv: Canvas, parent) -> None:
    """The wall of a shower, tile from edge to edge, the arm of the rose coming in from the right and three plain
    bottles on a shelf: :func:`shower_water` falls in front of the character from :data:`SHOWER_HEAD`, and a white
    :func:`ledge` is the rim of the bath."""
    g = cv.group(parent, cv.uid("g"))
    cv.rect(
        g, 0, 0, cv.width, cv.height, cv.grad("toon-bathroom-wall", [(float(o), c) for o, c in BATH_WALL], (0, 0, 0, 1))
    )
    for x in range(BATH_TILE // 2, 620, BATH_TILE):
        cv.rect(g, fx(x), 0, fh(2.5), cv.height, BATH_GROUT, opacity=0.8)
    for y in range(70 + BATH_TILE // 2, 1140, BATH_TILE):
        cv.rect(g, 0, fy(y), cv.width, fh(2.5), BATH_GROUT, opacity=0.8)
    rose_x, rose_y = SHOWER_HEAD
    _line(cv, g, [(620, rose_y - 34), (rose_x, rose_y - 34), (rose_x, rose_y - 12)], 12.0, CHROME_DARK)
    _line(cv, g, [(620, rose_y - 34), (rose_x, rose_y - 34), (rose_x, rose_y - 12)], 6.0, CHROME)
    cv.ellipse(g, fx(rose_x - 58), fy(rose_y - 16), fh(116), fh(32), CHROME, cv.ink, FINE_W)
    cv.rect(g, fx(404), fy(SHELF_Y), fh(186), fh(12), CHROME, cv.ink, FINE_W, radius=fh(4))
    for bx, h, w, colour in BOTTLES:
        cv.rect(g, fx(bx), fy(SHELF_Y - h), fh(w), fh(h), colour, cv.ink, FINE_W, radius=fh(10))
        cv.rect(g, fx(bx + w / 2 - 8), fy(SHELF_Y - h - 14), fh(16), fh(16), colour, cv.ink, FINE_W, radius=fh(3))


def streaks(clear: tuple[float, float] | None) -> tuple[float, ...]:
    """Where each column of water lands, without those in ``clear``, the span kept free so a face stays seen."""
    return tuple(float(x) for x in WATER_XS if clear is None or not clear[0] <= x <= clear[1])


def water_dashes(foot: float, phase: int, stop: float = WATER_TO) -> list[tuple[Point, Point]]:
    """The dashes of the column that lands at ``foot``, on one ``phase`` of the fall: a straight line out of the rose,
    never above it, so the water does not read as rain, and ending at reference y ``stop``."""
    rose_x, rose_y = SHOWER_HEAD
    top, length = rose_y + WATER_FROM, WATER_TO - rose_y - WATER_FROM
    period = WATER_DASH + WATER_GAP

    def along(y: float) -> Point:
        reach = WATER_SPREAD + (1 - WATER_SPREAD) * (y - top) / length
        return (round(rose_x + (foot - rose_x) * reach, 2), round(y, 2))

    dashes = []
    y = top + phase * period / WATER_PHASES + (foot * 7) % period / WATER_PHASES
    while y < stop:
        dashes.append((along(y), along(min(y + WATER_DASH, stop))))
        y += period
    return dashes


@register(
    "prop",
    "toon-shower-water",
    contract=dc.contract('toon-shower-water'),
    summary="Shower water falling in streaks while the tap is on, and only then",
)
def shower_water(
    cv: Canvas,
    parent,
    spans: Sequence[tuple[float, float]],
    clear: tuple[float, float] | None = None,
    stop: float | None = None,
    id: str = "water",
) -> None:
    """Water falling down the frame through each ``(start, end)`` in rising project seconds, gone at once between
    them, in a group ``{id}-{n}`` each. ``clear`` is the span of the fall's foot left dry, so nothing runs across a
    face; with ``stop`` the columns in it fall as far as that reference y and land on the head instead."""
    if not spans:
        raise ToonDataError("water needs at least one span")
    last = 0.0
    for span in spans:
        if not (len(span) == 2 and all(checks.number(v) for v in span) and last <= span[0] < span[1]):
            raise ToonDataError(f"water's spans are rising (start, end) seconds, got {spans!r}")
        last = span[1]
    if clear is not None and not (len(clear) == 2 and all(checks.number(v) for v in clear) and clear[0] < clear[1]):
        raise ToonDataError(f"water's clear span is (left, right), got {clear!r}")
    columns = [(foot, WATER_TO) for foot in streaks(clear)]
    if clear is not None and stop is not None:
        columns += [(float(foot), stop) for foot in WATER_XS if clear[0] <= foot <= clear[1]]
    for n, (start, end) in enumerate(spans):
        g = cv.group(parent, f"{id}-{n}", start=start, end=end)
        step = WATER_PERIOD / WATER_PHASES
        for phase in range(WATER_PHASES):
            shown = cv.group(g, cv.uid("g"), opacity=WATER_OPACITY)
            cycle = cycle_keys([(0.0, WATER_OPACITY), (step, 0.0)], WATER_PERIOD, start, end, phase=phase * step)
            cv.keys(shown, "opacity", cycle, local=False)
            for foot, last in columns:
                for a, b in water_dashes(foot, phase, last):
                    _line(cv, shown, [a, b], WATER_W, WATER_COLOUR)


def _worn(cv: Canvas, parent, at: object, scale: float, start, end, id: str, what: str):
    """The scaled group of something a head wears, in units of a reference pixel about ``at``."""
    x, y = _point(at, f"{what}'s place")
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"{what}'s scale is over 0, got {scale!r}")
    timing = {} if start is None else {"start": start, "end": end}
    outer = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale, **timing)
    return cv.group(outer, cv.uid("g"), scaleX=fh(1), scaleY=fh(1))


@register("prop", "toon-suds", contract=dc.contract('toon-suds'), summary="A heap of shampoo on someone's head")
def suds(
    cv: Canvas,
    parent,
    at: object,
    scale: float = 1.0,
    start: float | None = None,
    end: float | None = None,
    id: str = "suds",
) -> None:
    """A heap of foam with its middle on reference ``at``, drawn into the figure's group."""
    g = _worn(cv, parent, at, scale, start, end, id, "suds")
    line = FINE_W / fh(1)
    for x, y, r in SUDS_PUFFS:
        cv.ellipse(g, x - r / 2, y - r / 2, r, r, "#ffffff", SUDS_LINE, line)
    for x, y, r in SUDS_PUFFS[:3]:
        cv.ellipse(g, x - r / 6, y + r / 10, r / 3, r / 4, SUDS_SHADE)


@register("prop", "toon-towel", contract=dc.contract('toon-towel'), summary="A towel wrapped round someone's head")
def towel(
    cv: Canvas,
    parent,
    at: object,
    scale: float = 1.0,
    start: float | None = None,
    end: float | None = None,
    id: str = "towel",
) -> None:
    """A towel wound round a head, the middle of its lower edge on reference ``at``, drawn into the figure's group."""
    g = _worn(cv, parent, at, scale, start, end, id, "a towel")
    line = INK_W / fh(1)
    cv.path(g, TOWEL_TAIL, TOWEL_SHADE, cv.ink, line)
    cv.path(g, TOWEL_DOME, TOWEL_COLOUR, cv.ink, line)
    for fold in TOWEL_FOLDS:
        cv.path(g, fold, cv.clear, TOWEL_LINE, line * 0.5)

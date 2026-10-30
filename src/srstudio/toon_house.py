"""Toon rooms and props of the house: a hallway with a front door, what comes through it, and a surface for a shot
with no desk in it.

:func:`hallway` is a hall wall with a front door at the right, shut or open on the porch at night; :func:`horse`
stands in that doorway, a long face looking straight down the lens. :func:`ledge` takes the desk's place in front of
the character (``Staging(desk=toon_house.ledge)``, or drawn per shot from ``dress`` into ``shot.front``) with the
signature on it as the desk has it (ADR 0001), in one of :data:`LEDGES`. :func:`key_line` letters a reel's premise in
the band under the desk's top edge, so a viewer with the sound off has it from the first frame.

Every measure is a reference screen pixel (:func:`srstudio.toon.fx`/``fy``), like the rest of the style, and every
key is on the composition clock. Bad input is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from . import checks, signature
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, _path, fh, fx, fy
from .toon_sets import _glow, _inked, _line, _shadow

__all__ = [
    "DOORS",
    "HORSE_BLINK",
    "KEY_LINE_MAX",
    "KEY_LINE_SIZE",
    "KEY_LINE_TOP",
    "LEDGES",
    "bedroom",
    "finger",
    "hallway",
    "horse",
    "key_line",
    "ledge",
    "quilt",
    "rope",
    "thermostat",
    "vent",
]

Point = tuple[float, float]

# the surface: (top, front, side panel, the code's shade)
LEDGES = {
    "oak": ("#c98f55", "#a56f3e", "#b57d48", "#7c5029"),
    "white": ("#f4f1ea", "#dcd7cc", "#e8e3d8", "#a59f92"),
    "steel": ("#c9d3dc", "#a4b0bc", "#b4bfca", "#73808e"),
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
    "prop", "toon-ledge", summary="A plain surface in the desk's place, in oak, white or steel, signed as the desk is"
)
def ledge(cv: Canvas, parent, finish: str = "oak") -> None:
    """A surface with no laptop on it, in front of the character as the desk is, in one of :data:`LEDGES`, with the
    cactus on its top and the code on its front where the desk has them."""
    if finish not in LEDGES:
        raise ToonDataError(f"a ledge is one of {sorted(LEDGES)}, got {finish!r}")
    top, front, side, code = LEDGES[finish]
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(-10), fy(LEDGE_TOP + 47), fh(612), fh(300), front, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(LEDGE_TOP + 47), fh(106), fh(300), side, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(LEDGE_TOP), fh(612), fh(47), cv.ink, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(LEDGE_TOP + 12), fh(612), fh(31), top, cv.clear, 0, radius=0)
    signature.cactus(cv, g, fx(548), fy(838), 0.7)
    signature.code(cv, g, fx(580), fy(866), 14, color=code, opacity=0.9, align="end")


@register(
    "graphic",
    "toon-key-line",
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
) -> None:
    """The head centred on reference ``at``, about 420 tall at ``scale`` 1 (within :data:`SCALES`), the neck running
    down behind it. Its lids drop at each of ``blinks`` (project seconds), every :data:`HORSE_BLINK` seconds from
    ``start`` to ``end`` when ``blinks`` is None; a still (``end`` 0) never blinks."""
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

    _inked(cv, g, local([(-96, 40), (-132, 330), (-120, 640), (120, 640), (132, 330), (96, 40)]), COAT_DARK)
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


@register("prop", "toon-thermostat", summary="A wall thermostat whose two-digit reading changes on cue")
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


@register("prop", "toon-finger", summary="A forearm and a pointing finger, its tip going where it is told")
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
    cv.rect(g, -fh(46), fh(180), fh(92), fh(900), sleeve, cv.ink, INK_W * 0.8, radius=fh(14))
    cv.ellipse(g, -fh(92), fh(112), fh(62), fh(36), colour, cv.ink, INK_W * 0.8)  # the thumb, across the palm
    cv.rect(g, -fh(62), fh(104), fh(126), fh(130), colour, cv.ink, INK_W * 0.8, radius=fh(34))
    for k in range(3):  # the three curled fingers, side on
        cv.rect(g, fh(4 + k * 18), fh(96 - k * 2), fh(26), fh(58), colour, cv.ink, INK_W * 0.6, radius=fh(13))
    cv.rect(g, -fh(21), 0, fh(42), fh(150), colour, cv.ink, INK_W * 0.8, radius=fh(20))
    cv.rect(g, -fh(19), fh(100), fh(38), fh(62), colour, cv.clear, 0, radius=0)
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


@register("prop", "toon-vent", summary="A wall vent with white slats")
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


@register("location", "toon-bedroom", summary="A dark bedroom at night: a wooden headboard, a pillow, a moonlit window")
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


@register("prop", "toon-quilt", summary="A patched quilt in front of the character, a nightstand signed as the desk is")
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

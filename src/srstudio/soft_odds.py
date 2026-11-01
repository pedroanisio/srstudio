"""Soft odds and ends: the things a sketch hands to its cast, each drawn once so the next reel can pick it up.

A character in the Soft rig holds what :func:`srstudio.blob.held` puts between both hands; :func:`in_hand` is the same
ride for one hand, named by the side of the frame it is on, so a prop stays with that hand through a turn. The props
that do something keep it in the prop: tongs snap on cue, a grill's burgers char and its flames climb, smoke thickens.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import blob, checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = [
    "LOADS",
    "SoftOddError",
    "bottle",
    "book",
    "bowling_ball",
    "brick",
    "coin_bag",
    "dimmer",
    "dust",
    "grill",
    "home_fridge",
    "hush_finger",
    "in_hand",
    "notice",
    "pizza_box",
    "rumble",
    "smoke",
    "tongs",
    "tv",
    "washer",
    "yogurt",
]

METAL, METAL_LIGHT, METAL_DARK = blob.METAL, blob.METAL_LIGHT, blob.METAL_DARK
CHAR = "#2A211C"
SNAP = 0.07  # seconds tongs stay shut
FLIP_LIFT = 0.12  # seconds a turned burger takes to leave the grate
TONGS_OPEN = 7.0  # degrees either arm stands off the middle
FLAME_LEVELS = 4  # none, licks, flames, a fire
SMOKE_LEVELS = 4  # none, a thread, smoke, thick
SMOKE_RISE = 1.9  # seconds a puff takes to rise and go
SMOKE_PUFFS = (0, 2, 5, 9)  # puffs going at once at each level
DRUM_TURN = 1.6  # seconds a washer's drum takes to go round
TV_STEP = 0.4  # seconds a TV picture holds before it shifts
TV_FLICKER = (0.2, 0.75, 0.4, 1.0, 0.1, 0.6)  # how far the picture has shifted, step by step
DUST_SPECKS = 14
MAX_NOTICE = 24  # characters a notice holds at its size
RUMBLE_STEP = 0.07  # seconds a rumble holds one side
RUMBLE_SHAKE = 5.0  # px it shakes either way
FINGER_WIDTH, FINGER_LENGTH = 30, 62  # px; short, so that it stays a finger at any zoom


class SoftOddError(SrstudioError, ValueError):
    """A Soft prop asked for something it cannot draw."""


def _place(name: str, x: float, y: float, scale: float) -> None:
    if not (checks.number(x) and checks.number(y) and checks.number(scale) and scale > 0):
        raise SoftOddError(f"{name} stands at a finite place with a positive scale, got {x!r}, {y!r}, {scale!r}")


def _rows(name: str, rows: Sequence[tuple[float, int]], levels: int) -> None:
    """``(time, level)`` rows run from 0 in rising time, each level inside ``levels``."""
    times = [row[0] for row in rows]
    rising = all(b > a for a, b in zip(times, times[1:], strict=False))
    if not rows or times[0] != 0 or not all(checks.number(t) for t in times) or not rising:
        raise SoftOddError(f"{name} rows run from 0 in rising time, got {list(rows)!r}")
    if not all(isinstance(level, int) and 0 <= level < levels for _, level in rows):
        raise SoftOddError(f"{name} levels are 0..{levels - 1}, got {list(rows)!r}")


def _spans(rows: Sequence[tuple[float, int]], level: int, end: float) -> list[tuple[float, float]]:
    """The spans in which ``rows`` stand at ``level``, up to ``end``."""
    until = [*(row[0] for row in rows[1:]), end]
    return [(row[0], stop) for row, stop in zip(rows, until, strict=True) if row[1] == level]


def in_hand(
    cv: Canvas, parent, cues: Sequence[blob.Cue], side: str, *, end: float, scale: float = 1, fps: float = 15, id: str
):
    """A group that rides the hand on the ``side`` ("left" or "right") of the frame through ``cues``, drawing by
    drawing: :func:`srstudio.blob.held` for one hand. A flip changes which arm that is, not which side it is."""
    if side not in ("left", "right"):
        raise SoftOddError(f"a hand is on the left or the right of the frame, got {side!r}")
    checks.positive(scale, SoftOddError, f"a held prop's scale must be a positive number, got {scale!r}")
    frames = blob.drawings(cues, end=end, fps=fps)
    tips = [d.pose.limbs["arm_l" if (side == "left") != d.cue.flip else "arm_r"].p3 for d in frames]
    g = cv.group(parent, id)
    cv.keys(g, "x", [(d.time, round(scale * tip[0], 3)) for d, tip in zip(frames, tips, strict=True)])
    cv.keys(g, "y", [(d.time, round(scale * tip[1], 3)) for d, tip in zip(frames, tips, strict=True)])
    return g


def _tong_arm(cv: Canvas, g) -> None:
    cv.path(g, "M -7 0 L 7 0 L 12 -250 Q 22 -292 4 -318 L -14 -318 Q -8 -280 -8 -250 Z", METAL_LIGHT, cv.ink, 4)
    for k in range(3):  # the scallops that grip
        cv.line(g, -12, -300 + 12 * k, 12, -300 + 12 * k, METAL_DARK, 3)
    cv.rect(g, -10, -96, 20, 96, "#2E3238", cv.ink, 3, radius=6)  # the handle's sleeve


@register(
    "prop",
    "soft-tongs",
    summary="Long kitchen tongs held by the hinge: two metal arms with scalloped tips that snap shut on cue",
)
def tongs(
    cv: Canvas,
    parent,
    x: float = 0,
    y: float = 0,
    *,
    scale: float = 1,
    angle: float = 0,
    clicks: Sequence[float] = (),
    id: str = "soft-tongs",
):
    """Tongs 320 px long at ``scale`` 1, the hinge at (``x``, ``y``), the tips up at ``angle`` 0, open; they snap
    shut for :data:`SNAP` seconds from each of ``clicks``."""
    _place("tongs", x, y, scale)
    if not checks.number(angle):
        raise SoftOddError(f"tongs lie at a finite angle, got {angle!r}")
    if any(not checks.number(t) or t < 0 for t in clicks) or list(clicks) != sorted(clicks):
        raise SoftOddError(f"tongs click at rising times from 0, got {list(clicks)!r}")
    if any(b - a < 2 * SNAP for a, b in zip(clicks, clicks[1:], strict=False)):
        raise SoftOddError(f"tongs need {2 * SNAP:.2f} s between clicks, got {list(clicks)!r}")
    g = cv.group(parent, id, x=x, y=y, rotation=angle, scaleX=scale, scaleY=scale)
    for side, name in ((-1, "left"), (1, "right")):
        arm = cv.group(g, f"{id}-{name}", rotation=side * TONGS_OPEN, scaleX=-side)
        _tong_arm(cv, arm)
        keys: list[tuple[float, float]] = [(0.0, side * TONGS_OPEN)]
        for t in clicks:
            keys = [k for k in keys if k[0] < t]
            keys += [(t, side * 0.5), (t + SNAP, side * TONGS_OPEN)]
        if clicks:
            cv.keys(arm, "rotation", keys)
    return g


@register(
    "prop",
    "soft-grill",
    summary="A kettle grill on three legs with a side shelf and burgers on the grate: the burgers char and the flames "
    "climb on cue",
)
def grill(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    *,
    end: float,
    scale: float = 1,
    burgers: int = 3,
    char: float | None = None,
    flames: Sequence[tuple[float, int]] = ((0.0, 0),),
    flip: float | None = None,
    id: str = "soft-grill",
):
    """A grill 400 px high at ``scale`` 1 with its feet at (``x``, ``y``) and the shelf on its right. ``flames`` are
    (time, level) rows from 0 up to ``end``, level 0 to 3; the burgers go black at ``char``; the middle burger hops
    over at ``flip``."""
    _place("a grill", x, y, scale)
    checks.positive(end, SoftOddError, f"a grill's end must be a positive number of seconds, got {end!r}")
    _rows("flames", flames, FLAME_LEVELS)
    if not (isinstance(burgers, int) and 1 <= burgers <= 4):
        raise SoftOddError(f"a grill takes 1 to 4 burgers, got {burgers!r}")
    for name, value in (("char", char), ("flip", flip)):
        if value is not None and not (checks.number(value) and 0 <= value < end):
            raise SoftOddError(f"a grill's {name} is a time within {end}, got {value!r}")
    if flip is not None and flip <= FLIP_LIFT:
        raise SoftOddError(f"a burger is turned from {FLIP_LIFT} s on, got {flip!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    for x0, x1 in ((-120, -190), (120, 190), (0, 0)):
        cv.line(g, x0, -200, x1, 0, ink, 15)
        cv.line(g, x0, -200, x1, 0, METAL_DARK, 8)
    cv.rect(g, 190, -292, 200, 22, blob.WOOD_TOP, blob.WOOD_LINE, 4, radius=6)  # the shelf
    cv.line(g, 215, -270, 215, 0, ink, 12)
    cv.line(g, 215, -270, 215, 0, METAL_DARK, 6)
    cv.path(g, "M -210 -300 Q -200 -130 0 -130 Q 200 -130 210 -300 Z", "#2F333A", ink, 5)
    cv.path(g, "M -176 -270 Q -130 -180 -40 -158", None, "#59606A", 8)  # the shine on the bowl
    for level in range(1, FLAME_LEVELS):
        spans = _spans(flames, level, end)
        if not spans:
            continue
        lit = cv.group(g, f"{id}-flames-{level}")
        cv.gate(lit, spans)
        top = 70 + 90 * level
        for k, dx in enumerate((-140, -70, 0, 70, 140)):
            h = top * (1.0 if k % 2 else 0.78)
            lick = cv.group(lit, f"{id}-flame-{level}-{k + 1}", x=dx, y=-298)
            cv.path(lick, f"M -44 0 Q -52 {-h * 0.5:g} 0 {-h:g} Q 52 {-h * 0.5:g} 44 0 Z", "#F08A2E", ink, 3)
            cv.path(lick, f"M -22 0 Q -26 {-h * 0.3:g} 0 {-h * 0.55:g} Q 26 {-h * 0.3:g} 22 0 Z", "#F7CF4F")
            beats = int((spans[-1][1] - spans[0][0]) / 0.14) + 1
            steps = [(spans[0][0] + n * 0.14, 1.0 if (n + k) % 2 else 0.84) for n in range(beats)]
            cv.keys(lick, "scaleY", steps)
    cv.ellipse(g, -218, -318, 436, 44, "#454B54", ink, 5)
    for k in range(7):  # the grate
        cv.line(g, -150 + 50 * k, -314, -150 + 50 * k, -278, "#6E777D", 3)
    gap = 340 / burgers
    for k in range(burgers):
        at = -170 + gap * (k + 0.5)
        burger = cv.group(g, f"{id}-burger-{k + 1}", x=at, y=-314)
        if flip is not None and k == burgers // 2:
            lifted = flip - FLIP_LIFT  # it lies on the grate until it is turned
            cv.keys(burger, "y", [(0.0, -314.0), (lifted, -314.0), (flip, -372.0), (flip + 0.2, -314.0)], False)
            cv.keys(burger, "rotation", [(0.0, 0.0), (flip, 0.0), (flip + 0.2, 360.0)], False)
        cv.ellipse(burger, -48, -18, 96, 34, "#8A5A3A", ink, 4)
        if char is not None:
            black = cv.group(burger, f"{id}-burger-{k + 1}-char")
            cv.gate(black, [(char, end)])
            cv.ellipse(black, -48, -18, 96, 34, CHAR, ink, 4)
    return g


@register(
    "prop", "soft-smoke", summary="Grey puffs rising and fading from a point, from a thread to a thick column, on cue"
)
def smoke(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    rows: Sequence[tuple[float, int]] = ((0.0, 2),),
    *,
    end: float,
    scale: float = 1,
    id: str = "soft-smoke",
):
    """Smoke rising from (``x``, ``y``): ``rows`` are (time, level) from 0 up to ``end``, level 0 none to 3 thick. The
    same puffs every build; they lean a little to the right as they go."""
    _place("smoke", x, y, scale)
    checks.positive(end, SoftOddError, f"smoke's end must be a positive number of seconds, got {end!r}")
    _rows("smoke", rows, SMOKE_LEVELS)
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    for level in range(1, SMOKE_LEVELS):
        spans = _spans(rows, level, end)
        if not spans:
            continue
        stage = cv.group(g, f"{id}-level-{level}")
        cv.gate(stage, spans)
        first, last = spans[0][0], spans[-1][1]
        puffs = SMOKE_PUFFS[level]
        for k in range(puffs):
            offset = SMOKE_RISE * k / puffs
            sway = 30.0 * math.sin(k * 2.4)
            puff = cv.group(stage, f"{id}-puff-{level}-{k + 1}")
            starts = [first - SMOKE_RISE + offset + n * SMOKE_RISE for n in range(int((last - first) / SMOKE_RISE) + 3)]
            ys, xs, fades, sizes = [], [], [], []
            for s in starts:
                ys += [(s, 0.0), (s + SMOKE_RISE - 0.001, -560.0)]
                xs += [(s, sway), (s + SMOKE_RISE - 0.001, sway + 110.0)]
                fades += [(s, 0.0), (s + 0.25, 0.8), (s + SMOKE_RISE - 0.001, 0.0)]
                sizes += [(s, 0.5), (s + SMOKE_RISE - 0.001, 1.5 + 0.2 * level)]
            for prop, keys in (("y", ys), ("x", xs), ("opacity", fades), ("scaleX", sizes), ("scaleY", sizes)):
                cv.keys(puff, prop, [(max(t, 0.0), v) for t, v in keys if t >= 0], False)
            cv.ellipse(puff, -60, -60, 120, 120, "#D9D7D2")
    return g


@register(
    "prop",
    "soft-pizza-box",
    summary="A flat cardboard pizza box seen from a little above, with a red stamp on the lid and vents on its edge",
)
def pizza_box(cv: Canvas, parent, x: float, y: float, *, scale: float = 1, id: str = "soft-pizza-box"):
    """A pizza box 340 px wide at ``scale`` 1, centred on (``x``, ``y``)."""
    _place("a pizza box", x, y, scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M -170 -10 L -120 -74 L 120 -74 L 170 -10 Z", "#E3C08E", ink, 4)
    cv.rect(g, -170, -10, 340, 46, "#CFA870", ink, 4, radius=3)
    cv.ellipse(g, -48, -66, 96, 46, "#D9534F", ink, 3)
    cv.ellipse(g, -22, -54, 44, 22, "#F7E7C9")
    for dx in (-110, 110):
        cv.rect(g, dx - 18, 2, 36, 22, "#B8925C", radius=4)  # the vents
    cv.path(g, "M -40 26 L -40 6 L 40 6 L 40 26 Z", "#D9534F", ink, 3)  # the shop's band, no lettering: it travels
    return g


@register("prop", "soft-bottle", summary="A squeeze bottle with a nozzle and a blank label, red unless asked otherwise")
def bottle(
    cv: Canvas, parent, x: float, y: float, *, scale: float = 1, color: str = "#D9534F", id: str = "soft-bottle"
):
    """A squeeze bottle 230 px tall at ``scale`` 1, centred on (``x``, ``y``)."""
    _place("a bottle", x, y, scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M -9 -118 L 9 -118 L 16 -78 L -16 -78 Z", "#F4F0E6", ink, 4)
    cv.path(
        g,
        "M -44 -60 Q -44 -78 -26 -78 L 26 -78 Q 44 -78 44 -60 L 44 104 Q 44 116 32 116 L -32 116 Q -44 116 -44 104 Z",
        color,
        ink,
        4,
    )
    cv.rect(g, -30, -30, 60, 80, "#FBF7EE", ink, 3, radius=8)
    cv.path(g, "M -30 -66 L -30 -40", None, "#FFFFFF", 6)
    return g


@register(
    "prop",
    "soft-washer",
    summary="A front-loading washing machine with a round glass door, a drum that turns on cue and a light that dies; "
    "what has been put in rides round in the drum",
)
def washer(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    *,
    end: float,
    scale: float = 1,
    stop: float | None = None,
    open_at: Sequence[tuple[float, float]] = (),
    loads: Sequence[tuple[float, str]] = (),
    id: str = "soft-washer",
):
    """A washer 460 px wide and 560 high at ``scale`` 1, its feet at (``x``, ``y``). The drum turns from 0 until
    ``stop`` (to ``end`` when None) and its green light goes out with it; the door stands open through ``open_at``;
    ``loads`` are (time, kind) rows, each kind one of :data:`LOADS`, in the drum from that time."""
    _place("a washer", x, y, scale)
    checks.positive(end, SoftOddError, f"a washer's end must be a positive number of seconds, got {end!r}")
    last = end if stop is None else stop
    if not (checks.number(last) and 0 < last <= end):
        raise SoftOddError(f"a washer stops within {end}, got {stop!r}")
    for start, close in open_at:
        if not (checks.number(start) and checks.number(close) and 0 <= start < close <= end):
            raise SoftOddError(f"a washer's door opens within {end}, got {list(open_at)!r}")
    for time, kind in loads:
        if kind not in LOADS or not (checks.number(time) and 0 <= time < end):
            raise SoftOddError(f"a load is a time within {end} and one of {LOADS}, got {(time, kind)!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    for dx in (-190, 150):
        cv.rect(g, dx, -18, 40, 18, "#4A4F58", ink, 3, radius=4)
    cv.rect(g, -230, -560, 460, 546, "#F4F2EC", ink, 5, radius=26)
    cv.rect(g, -230, -560, 460, 92, "#E3E0D8", ink, 4, radius=24)
    cv.ellipse(g, -196, -544, 60, 60, "#FFFFFF", ink, 4)  # the dial
    cv.line(g, -166, -514, -166, -538, ink, 5)
    cv.rect(g, -110, -536, 150, 40, "#2B3038", ink, 3, radius=8)  # the display
    light = cv.group(g, f"{id}-light")
    cv.gate(light, [(0.0, last)])
    cv.ellipse(light, 90, -530, 28, 28, "#6BD08A", ink, 3)
    cv.rect(light, -96, -526, 40, 20, "#6BD08A", radius=4)
    cv.ellipse(g, 150, -530, 28, 28, "#C9C5BB", ink, 3)
    cv.ellipse(g, -176, -420, 352, 352, "#D5D2C9", ink, 5)  # the door's seat
    cv.ellipse(g, -142, -386, 284, 284, "#232833", ink, 4)  # the mouth of the drum
    drum = cv.group(g, f"{id}-drum", x=0, y=-244)
    if last > 0:
        cv.keys(drum, "rotation", [(0.0, 0.0), (last, 360.0 * last / DRUM_TURN)], False)
    for k in range(3):
        rib = cv.group(drum, f"{id}-rib-{k + 1}", rotation=120 * k)
        cv.rect(rib, -12, -142, 24, 44, "#6E777D", ink, 3, radius=6)
    cv.ellipse(drum, -80, 10, 118, 84, "#8FB3D0", ink, 3)  # the washing
    cv.ellipse(drum, -16, -92, 104, 74, "#E8A6A0", ink, 3)
    for k, (time, kind) in enumerate(loads):
        item = cv.group(drum, f"{id}-load-{k + 1}")
        cv.gate(item, [(time, end)])
        LOAD_SHAPES[kind](cv, item, k)
    glass = cv.group(g, f"{id}-door")
    cv.gate(glass, _closed(open_at, end))
    cv.ellipse(glass, -160, -404, 320, 320, "#BFD9E688", "#7C8791", 16)
    cv.path(glass, "M -98 -326 Q -70 -368 -28 -372", None, "#FFFFFF", 9)
    cv.rect(glass, 142, -270, 34, 58, "#C9C5BB", ink, 3, radius=8)  # the handle
    swung = cv.group(g, f"{id}-door-open")
    cv.gate(swung, open_at)
    cv.ellipse(swung, -296, -404, 96, 320, "#BFD9E6", "#7C8791", 12)
    return g


def _closed(open_at: Sequence[tuple[float, float]], end: float) -> list[tuple[float, float]]:
    """The spans of ``0..end`` outside the ``open_at`` spans."""
    out, at = [], 0.0
    for start, close in sorted(open_at):
        if start > at:
            out.append((at, start))
        at = close
    return [*out, (at, end)] if at < end else out


def _load_brick(cv: Canvas, g, k: int) -> None:
    turn = cv.group(g, f"load-turn-{k + 1}", x=60 - 30 * k, y=70 - 44 * k, rotation=20 + 70 * k)
    cv.rect(turn, -66, -30, 132, 60, "#B5533C", cv.ink, 4, radius=6)


def _load_ball(cv: Canvas, g, k: int) -> None:
    cv.ellipse(g, -48, -88, 112, 112, "#3C2A6B", cv.ink, 4)
    cv.ellipse(g, -2, -66, 16, 16, "#120B25")
    cv.ellipse(g, 22, -66, 16, 16, "#120B25")


def _load_coins(cv: Canvas, g, k: int) -> None:
    for n in range(9):
        cv.ellipse(g, -90 + 24 * n, 44 - 26 * (n % 3), 26, 26, "#E9B949", cv.ink, 3)


def _load_shovel(cv: Canvas, g, k: int) -> None:
    turn = cv.group(g, f"load-shovel-{k + 1}", rotation=-30)
    cv.rect(turn, -8, -128, 16, 170, "#A5713F", cv.ink, 3, radius=5)
    cv.path(turn, "M -42 34 L 42 34 L 30 96 L 0 124 L -30 96 Z", "#A9B3BA", cv.ink, 4)


LOAD_SHAPES = {"brick": _load_brick, "ball": _load_ball, "coins": _load_coins, "shovel": _load_shovel}
LOADS = tuple(LOAD_SHAPES)


@register("prop", "soft-brick", summary="A red house brick with two rows of holes on its face")
def brick(
    cv: Canvas, parent, x: float = 0, y: float = 0, *, scale: float = 1, angle: float = 0, id: str = "soft-brick"
):
    """A brick 180 x 84 px at ``scale`` 1, centred on (``x``, ``y``)."""
    _place("a brick", x, y, scale)
    g = cv.group(parent, id, x=x, y=y, rotation=angle, scaleX=scale, scaleY=scale)
    cv.rect(g, -90, -42, 180, 84, "#B5533C", cv.ink, 4, radius=6)
    cv.rect(g, -90, -42, 180, 20, "#C96A52", radius=6)
    for k in range(3):
        cv.ellipse(g, -56 + 44 * k, -6, 24, 24, "#8A3E2C", cv.ink, 3)
    return g


@register("prop", "soft-bowling-ball", summary="A dark purple bowling ball with its three finger holes and a shine")
def bowling_ball(cv: Canvas, parent, x: float = 0, y: float = 0, *, scale: float = 1, id: str = "soft-bowling-ball"):
    """A ball 190 px across at ``scale`` 1, centred on (``x``, ``y``)."""
    _place("a ball", x, y, scale)
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -95, -95, 190, 190, "#3C2A6B", cv.ink, 5)
    cv.path(g, "M -60 -30 Q -50 -62 -22 -70", None, "#7A63B5", 9)
    for dx, dy in ((14, -30), (46, -24), (30, 6)):
        cv.ellipse(g, dx, dy, 22, 24, "#120B25")
    return g


@register("prop", "soft-coin-bag", summary="A burlap sack tied at the neck with a dollar sign on it")
def coin_bag(cv: Canvas, parent, x: float = 0, y: float = 0, *, scale: float = 1, id: str = "soft-coin-bag"):
    """A sack 190 x 220 px at ``scale`` 1, centred on (``x``, ``y``)."""
    _place("a sack", x, y, scale)
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M -30 -74 Q -96 -30 -94 44 Q -92 110 0 110 Q 92 110 94 44 Q 96 -30 30 -74 Z", "#C9A66B", cv.ink, 5)
    cv.path(g, "M -30 -74 L -46 -108 L 46 -108 L 30 -74 Z", "#B8925C", cv.ink, 4)
    cv.rect(g, -36, -84, 72, 14, "#7A5A36", cv.ink, 3, radius=6)
    cv.path(g, "M 26 -10 Q 0 -30 -24 -12 Q -36 8 0 18 Q 36 28 24 50 Q 0 66 -26 46 M 0 -36 L 0 72", None, "#7A5A36", 9)
    return g


@register(
    "prop", "soft-tv", summary="A flat television on a low stand: its picture changes color until it goes dark on cue"
)
def tv(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    *,
    end: float,
    off: float | None = None,
    scale: float = 1,
    id: str = "soft-tv",
):
    """A set 420 px wide on a stand, its feet at (``x``, ``y``); the picture flickers until ``off`` (or the end)."""
    _place("a TV", x, y, scale)
    checks.positive(end, SoftOddError, f"a TV's end must be a positive number of seconds, got {end!r}")
    last = end if off is None else off
    if not (checks.number(last) and 0 < last <= end):
        raise SoftOddError(f"a TV goes off within {end}, got {off!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -170, -72, 340, 72, blob.WOOD_FRONT, blob.WOOD_LINE, 4, radius=8)
    cv.rect(g, -40, -96, 80, 24, "#2B2E36", ink, 3)
    cv.rect(g, -210, -340, 420, 250, "#23262C", ink, 5, radius=14)
    cv.rect(g, -194, -324, 388, 218, "#10131A", radius=6)
    lit = cv.group(g, f"{id}-picture")
    cv.gate(lit, [(0.0, last)])
    cv.rect(lit, -194, -324, 388, 218, "#7FB6DA", radius=6)
    glow = cv.group(lit, f"{id}-flicker")
    cv.rect(glow, -194, -220, 388, 114, "#8FBB7C", radius=6)
    cv.ellipse(glow, -60, -280, 120, 120, "#F4D06F")
    steps = int(last / TV_STEP) + 1
    cv.keys(glow, "opacity", [(n * TV_STEP, TV_FLICKER[n % len(TV_FLICKER)]) for n in range(steps)])
    return g


@register(
    "prop",
    "soft-home-fridge",
    summary="A front-on two-door kitchen fridge that stands anywhere, with a small green light that dies on cue",
)
def home_fridge(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    *,
    end: float,
    off: float | None = None,
    scale: float = 1,
    id: str = "soft-home-fridge",
):
    """A fridge 300 x 760 px at ``scale`` 1, its feet at (``x``, ``y``); its light is on until ``off``."""
    _place("a fridge", x, y, scale)
    checks.positive(end, SoftOddError, f"a fridge's end must be a positive number of seconds, got {end!r}")
    last = end if off is None else off
    if not (checks.number(last) and 0 < last <= end):
        raise SoftOddError(f"a fridge dies within {end}, got {off!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -150, -760, 300, 750, "#E6EEF0", ink, 5, radius=24)
    cv.line(g, -150, -520, 150, -520, ink, 4)
    cv.rect(g, -124, -610, 16, 64, "#9AA3A8", ink, 3, radius=6)
    cv.rect(g, -124, -490, 16, 90, "#9AA3A8", ink, 3, radius=6)
    cv.rect(g, 40, -440, 60, 46, "#F2A93B", ink, 3, radius=4)  # a magnet and its note
    light = cv.group(g, f"{id}-light")
    cv.gate(light, [(0.0, last)])
    cv.ellipse(light, 100, -730, 22, 22, "#6BD08A", ink, 3)
    return g


@register("prop", "soft-dust", summary="Specks of dust that fall from overhead on cue and thin out")
def dust(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    start: float = 0,
    *,
    end: float,
    width: float = 240,
    fall: float = 700,
    id: str = "soft-dust",
):
    """Specks falling from (``x``, ``y``) across ``width`` px, ``fall`` px down, from ``start`` until ``end``; the same
    every build."""
    _place("dust", x, y, 1.0)
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise SoftOddError(f"dust falls from a time before its end, got {start!r}, {end!r}")
    g = cv.group(parent, id, x=x, y=y)
    cv.gate(g, [(start, end)])
    for k in range(DUST_SPECKS):
        at = -width / 2 + width * ((k * 7) % DUST_SPECKS) / DUST_SPECKS
        begin = start + 0.09 * k
        speck = cv.group(g, f"{id}-{k + 1}", x=at)
        cv.keys(speck, "y", [(begin, 0.0), (begin + 0.9, fall)], False)
        cv.ellipse(speck, -6, -6, 12 + 3 * (k % 3), 12 + 3 * (k % 3), "#C9B8A0", "#8A7A64", 2)
    return g


@register(
    "graphic",
    "soft-dimmer",
    summary="A veil over the whole frame that deepens step by step: a room whose lights go out one at a time",
)
def dimmer(
    cv: Canvas,
    parent,
    rows: Sequence[tuple[float, float]] = ((0.0, 0.5),),
    *,
    color: str = "#0B1026",
    id: str = "soft-dimmer",
):
    """A full-frame veil: ``rows`` are (time, opacity) from 0, each opacity holding until the next."""
    times = [row[0] for row in rows]
    if not rows or times[0] != 0 or not all(b > a for a, b in zip(times, times[1:], strict=False)):
        raise SoftOddError(f"a dimmer's rows run from 0 in rising time, got {list(rows)!r}")
    if not all(checks.number(level) and 0 <= level <= 1 for _, level in rows):
        raise SoftOddError(f"a dimmer's levels are 0..1, got {list(rows)!r}")
    g = cv.group(parent, id)
    cv.rect(g, -100, -100, 1280, 2120, color)
    cv.keys(g, "opacity", list(rows))
    return g


@register("prop", "soft-notice", summary="A framed notice on a wall, a few big words: the rule of the room")
def notice(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    text: str = "QUIET PLEASE",
    *,
    scale: float = 1,
    shown: Sequence[tuple[float, float]] | None = None,
    size: float = 62,
    id: str = "soft-notice",
):
    """A notice 440 x 180 px at ``scale`` 1, centred on (``x``, ``y``), reading ``text`` at ``size``. ``shown`` gates it
    to spans: its words are a text layer, and a text layer stays in the safe area for as long as it shows."""
    _place("a notice", x, y, scale)
    if not text.strip() or len(text) > MAX_NOTICE:
        raise SoftOddError(f"a notice reads 1 to {MAX_NOTICE} characters, got {text!r}")
    if not (checks.number(size) and size > 0):
        raise SoftOddError(f"a notice's size must be a positive number, got {size!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    if shown is not None:
        cv.gate(g, list(shown))
    cv.rect(g, -220, -90, 440, 180, "#7A5A36", cv.ink, 5, radius=10)
    cv.rect(g, -204, -74, 408, 148, "#FBF6EA", cv.ink, 3, radius=6)
    cv.text(g, f"{id}-words", text, -200, -74, 400, 148, size, color=cv.ink)
    return g


@register("prop", "soft-book", summary="A closed hardback with a band on its cover, held up or lying in a pile")
def book(
    cv: Canvas,
    parent,
    x: float = 0,
    y: float = 0,
    *,
    scale: float = 1,
    angle: float = 0,
    color: str = "#4C7A9E",
    id: str = "soft-book",
):
    """A book 170 x 220 px at ``scale`` 1, centred on (``x``, ``y``), its spine on the left at ``angle`` 0."""
    _place("a book", x, y, scale)
    g = cv.group(parent, id, x=x, y=y, rotation=angle, scaleX=scale, scaleY=scale)
    cv.rect(g, -77, -106, 162, 212, "#F4EFE2", cv.ink, 3, radius=3)  # the pages
    cv.rect(g, -85, -110, 158, 220, color, cv.ink, 5, radius=6)
    cv.rect(g, -85, -110, 22, 220, "#00000030", radius=6)  # the spine
    cv.rect(g, -44, -66, 92, 26, "#F4EFE2", cv.ink, 3, radius=4)
    return g


@register("prop", "soft-yogurt", summary="A small plastic yogurt pot with a foil lid and a strawberry on its label")
def yogurt(cv: Canvas, parent, x: float = 0, y: float = 0, *, scale: float = 1, id: str = "soft-yogurt"):
    """A pot 130 px wide and 150 high at ``scale`` 1, its base on (``x``, ``y``)."""
    _place("a yogurt", x, y, scale)
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M -60 -130 L -44 -2 Q 0 8 44 -2 L 60 -130 Z", "#FBF6EA", cv.ink, 5)
    cv.path(g, "M -52 -76 L -48 -36 Q 0 -28 48 -36 L 52 -76 Q 0 -68 -52 -76 Z", "#E8A6A0", cv.ink, 3)
    cv.ellipse(g, -13, -70, 26, 28, "#D94A4A", cv.ink, 3)
    cv.rect(g, -68, -148, 136, 20, "#C9CFD6", cv.ink, 4, radius=8)
    return g


@register("prop", "soft-rumble", summary="Three curved lines either side of a belly, shaking while it talks")
def rumble(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    spans: Sequence[tuple[float, float]] = ((0.0, 1.0),),
    *,
    scale: float = 1,
    color: str = "#1A1714",
    id: str = "soft-rumble",
):
    """Lines 260 px apart at ``scale`` 1 around (``x``, ``y``), shaking through each of ``spans``, the same every
    build. The ``color`` ties a belly to the words it says."""
    _place("a rumble", x, y, scale)
    last = 0.0
    for start, stop in spans:
        if not (checks.number(start) and checks.number(stop) and last <= start < stop):
            raise SoftOddError(f"rumble spans run in order and apart, got {list(spans)!r}")
        last = stop
    if not spans:
        raise SoftOddError("a rumble needs at least one span")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.gate(g, list(spans))
    shake = cv.group(g, f"{id}-shake")
    rows = []
    for start, stop in spans:
        rows += [
            (round(start + RUMBLE_STEP * n, 3), RUMBLE_SHAKE * (-1 if n % 2 else 1))
            for n in range(int((stop - start) / RUMBLE_STEP) + 1)
        ]
    cv.keys(shake, "x", rows)
    for side in (-1, 1):
        for k in range(3):
            at = side * (130 + 26 * k)
            bow = side * 26
            cv.path(shake, f"M {at} {-44 + 8 * k} Q {at + bow} 0 {at} {44 - 8 * k}", None, color, 8)
    return g


@register(
    "prop",
    "soft-hush-finger",
    summary="A forearm that curls in from a raised hand and one short finger across the lips",
)
def hush_finger(
    cv: Canvas,
    parent,
    x: float = 0,
    y: float = 0,
    *,
    fill: str = blob.BO_FILL,
    reach: float = 150,
    scale: float = 1,
    id: str = "soft-hush-finger",
):
    """From a hand at (``x``, ``y``), the rig's raised hand in ``step``, an arm curls ``reach`` px across the face and a
    finger rises over the lips. A negative ``reach`` curls the other way."""
    _place("a finger", x, y, scale)
    if not (checks.number(reach) and reach != 0):
        raise SoftOddError(f"a finger's reach must be a number other than 0, got {reach!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    curl = f"M 0 0 Q {-reach * 0.5:g} 66 {-reach:g} 62 L {-reach:g} {62 - FINGER_LENGTH:g}"
    cv.path(g, curl, None, cv.ink, FINGER_WIDTH + 8)
    cv.path(g, curl, None, fill, FINGER_WIDTH)
    return g

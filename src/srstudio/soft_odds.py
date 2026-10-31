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

__all__ = ["SoftOddError", "bottle", "grill", "in_hand", "pizza_box", "smoke", "tongs"]

METAL, METAL_LIGHT, METAL_DARK = blob.METAL, blob.METAL_LIGHT, blob.METAL_DARK
CHAR = "#2A211C"
SNAP = 0.07  # seconds tongs stay shut
FLIP_LIFT = 0.12  # seconds a turned burger takes to leave the grate
TONGS_OPEN = 7.0  # degrees either arm stands off the middle
FLAME_LEVELS = 4  # none, licks, flames, a fire
SMOKE_LEVELS = 4  # none, a thread, smoke, thick
SMOKE_RISE = 1.9  # seconds a puff takes to rise and go
SMOKE_PUFFS = (0, 2, 5, 9)  # puffs going at once at each level


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

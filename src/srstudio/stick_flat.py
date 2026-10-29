"""The Stick style's flat: a studio for rent, with its kitchen toilet, its painted window and a bed in the wall.

:func:`studio` is the back layer, drawn wider than the frame (:data:`SET_W`) so a camera can turn from the kitchen
to the bed: the wall and the floorboards, the counter with its stove and pot, a toilet plumbed in beside the stove,
a window whose view is painted on (the paint runs over the frame and drips down the wall), and the cabinet the bed
folds out of. :func:`murphy_bed` is that bed: closed in the wall, folding down at ``drop_at`` through one mid frame
(:data:`FOLD`), and open on the floor, where a ``sleeper`` (a :class:`srstudio.stick.Look`) can lie under the
blanket, snore, and talk in his sleep. Figures stand from :data:`srstudio.stick.STANDING`: the viewer at
:data:`VIEWER_AT`, by the kitchen, and the agent mirrored at :data:`AGENT_AT`, between the kitchen and the bed.
Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import signature
from .canvas import Canvas
from .registry import register
from .stick import (
    Face,
    Gradient,
    Look,
    StickDataError,
    _features,
    _gate,
    _group,
    _head,
    box,
    check_look,
    oval,
    paint,
    shape,
)

__all__ = ["AGENT_AT", "BED_FOCUS", "FOLD", "SET_W", "VIEWER_AT", "WINDOW_FOCUS", "murphy_bed", "studio"]

WALL_TOP, WALL_LOW, SKIRTING = "#e3dccb", "#cfc5ae", "#8f846c"
FLOOR, BOARD, COUNTER, COUNTER_TOP = "#b48a5c", "#97703f", "#d7d2c6", "#7e8a91"
STEEL, BURNER, POT, PORCELAIN = "#4a4f57", "#2b2f36", "#c0453b", "#f7f5ef"
CABINET, CABINET_EDGE, RECESS = "#a8794c", "#7d5532", "#4b3624"
MATTRESS, BLANKET, BLANKET_FOLD, PILLOW = "#f3efe4", "#5876a8", "#45608f", "#ffffff"
SKY, HILL, HILL_FAR, SUN = "#8fc3ea", "#6fae5b", "#93c47d", "#ffd34d"
SET_W = 2100  # the set runs past the frame's right edge: the bed is a turn of the camera away
FLOOR_Y = 1480
WINDOW = (380, 360, 360, 420)  # x, y, w, h of the painted window
WINDOW_FOCUS = (WINDOW[0] + WINDOW[2] / 2, WINDOW[1] + WINDOW[3] / 2)
CAB = (1220, 640, 520, FLOOR_Y - 640)  # the bed's cabinet in the wall
BED_FOCUS = (CAB[0] + CAB[2] / 2, 1560)  # the sleeper's head on the open bed
VIEWER_AT = (-200.0, 0.0)  # a STANDING pose here stands at the stove, facing right
AGENT_AT = (1480.0, 0.0)  # with flip=True a STANDING pose here stands right of the toilet, facing the viewer
FOLD = 0.125  # the mid frame of the fold, three frames at 24 fps
NEAR_Y = 1730  # the open bed's foot, toward the camera


def _check_time(t: float, end: float, what: str) -> float:
    if not (isinstance(t, (int, float)) and math.isfinite(t) and 0 <= t < end):
        raise StickDataError(f"{what} must be in the shot (0..{end}), got {t!r}")
    return float(t)


@register("location", "stick-studio-flat", episodes=("the-viewing",), tags=("home", "flat", "rental", "kitchen"))
def studio(cv: Canvas, parent) -> None:
    """A studio flat for rent, :data:`SET_W` wide: the wall and its skirting over floorboards, the kitchen counter
    with a stove, a pot and a tap, a toilet plumbed in right beside the stove, a window whose sunny view is painted
    on (the blue runs over the frame and drips down the wall), and the cabinet the bed folds out of (draw
    :func:`murphy_bed` over it). A potted cactus sits on the counter and the code on the floor (ADR 0001)."""
    s = cv
    wall = paint(s, Gradient("flat-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0, FLOOR_Y))
    box(s, parent, 0, 0, SET_W, FLOOR_Y, wall)
    for x in range(60, SET_W, 120):  # a tired stripe in the wallpaper
        box(s, parent, x, 0, 34, FLOOR_Y, "#ffffff", opacity=0.10)
    box(s, parent, 0, FLOOR_Y - 26, SET_W, 26, SKIRTING)
    box(s, parent, 0, FLOOR_Y, SET_W, 2400 - FLOOR_Y, FLOOR)  # deep enough for a close shot of the bed
    for y in (1530, 1600, 1700, 1830):
        shape(s, parent, f"M 0 {y} L {SET_W} {y}", sw=3, stroke=BOARD)
    for i, x in enumerate(range(-400, SET_W + 400, 220)):
        y0 = (1530, 1600, 1700, 1830)[i % 4]
        shape(s, parent, f"M {x} {y0} L {x} {y0 + 70}", sw=3, stroke=BOARD)
    shape(s, parent, f"M 0 1560 L {SET_W} 1560 L {SET_W} 1640 L 0 1640 Z", "#ffffff", opacity=0.07)
    _window(s, parent)
    _kitchen(s, parent)
    _toilet(s, parent, 700)
    x, y, w, h = CAB  # the cabinet's frame; the bed itself is murphy_bed
    box(s, parent, x - 26, y - 26, w + 52, h + 26, CABINET_EDGE, 4, r=8)
    shape(s, parent, f"M {x - 60} {FLOOR_Y + 6} L {x + w + 60} {FLOOR_Y + 6}", sw=16, stroke="#000000", opacity=0.10)
    signature.cactus(s, parent, 330, 1150, scale=0.42)  # on the counter, by the wall
    signature.code(s, parent, 40, 1880, 9, color="#7a5a35")  # on the floor's near edge


def _window(s: Canvas, parent) -> None:
    x, y, w, h = WINDOW
    box(s, parent, x - 16, y - 16, w + 32, h + 32, "#ffffff", 4, r=6)
    box(s, parent, x, y, w, h, SKY)
    oval(s, parent, x + w - 120, y + 50, 76, 76, SUN)
    shape(s, parent, f"M {x} {y + 260} Q {x + 110} {y + 170} {x + 230} {y + 250} Q {x + 300} {y + 200} {x + w} "
                     f"{y + 230} L {x + w} {y + h} L {x} {y + h} Z", HILL_FAR)  # fmt: skip
    shape(s, parent, f"M {x} {y + 330} Q {x + 160} {y + 250} {x + w} {y + 320} L {x + w} {y + h} L {x} {y + h} Z",
          HILL)  # fmt: skip
    box(s, parent, x + 90, y + 250, 12, 60, "#6b4a2b")  # a tree, painted
    oval(s, parent, x + 62, y + 196, 68, 68, "#3f8a3a")
    # the paint runs over the frame onto the wall, and drips
    shape(s, parent, f"M {x + w - 40} {y - 16} Q {x + w + 30} {y - 30} {x + w + 46} {y + 40} Q {x + w + 50} {y + 90} "
                     f"{x + w + 16} {y + 120} L {x + w + 16} {y - 16} Z", SKY)  # fmt: skip
    shape(s, parent, f"M {x + w + 30} {y + 100} L {x + w + 30} {y + 190}", sw=10, stroke=SKY)
    oval(s, parent, x + w + 22, y + 184, 16, 22, SKY)
    shape(s, parent, f"M {x + w / 2} {y - 16} L {x + w / 2} {y + h + 16} M {x - 16} {y + h / 2} L {x + w + 16} "
                     f"{y + h / 2}", sw=12, stroke="#ffffff")  # fmt: skip
    box(s, parent, x - 30, y + h + 10, w + 60, 22, "#ffffff", 4, r=4)  # the sill


def _kitchen(s: Canvas, parent) -> None:
    top = 1180
    box(s, parent, 300, top, 360, FLOOR_Y - top, COUNTER, 4, r=6)
    box(s, parent, 290, top - 20, 380, 26, COUNTER_TOP, 4, r=6)
    for x in (320, 490):  # the cupboard doors and their knobs
        box(s, parent, x, top + 40, 150, 230, "#e6e1d6", 3, r=6)
        oval(s, parent, x + (130 if x == 320 else 10), top + 140, 12, 12, STEEL)
    box(s, parent, 380, top - 32, 220, 14, STEEL, r=4)  # the hob and its two burners
    for cx in (430, 550):
        oval(s, parent, cx - 40, top - 38, 80, 18, BURNER)
    shape(s, parent, f"M 400 {top - 40} L 400 {top - 120} Q 400 {top - 136} 416 {top - 136} L 484 {top - 136} "
                     f"Q 500 {top - 136} 500 {top - 120} L 500 {top - 40} Z", POT, 4, stroke=s.ink)  # fmt: skip
    box(s, parent, 386, top - 146, 128, 14, "#a3372f", 3, r=6)
    shape(s, parent, f"M 500 {top - 110} L 556 {top - 122}", sw=8, stroke=s.ink)
    shape(
        s,
        parent,
        f"M 630 {top - 20} L 630 {top - 96} Q 630 {top - 120} 606 {top - 120} L 590 {top - 120}",
        sw=8,
        stroke=STEEL,
    )  # the tap, fmt: skip


def _toilet(s: Canvas, parent, x: float) -> None:
    """A toilet with its cistern against the wall, its bowl's front on the floor at ``x``..``x + 170``."""
    box(s, parent, x + 20, 1140, 130, 150, PORCELAIN, 4, r=14)
    box(s, parent, x + 60, 1150, 50, 12, "#c9c4b8", r=4)  # the flush button
    box(s, parent, x, 1290, 170, 30, PORCELAIN, 4, r=12)  # the seat
    shape(s, parent, f"M {x + 10} 1320 L {x + 160} 1320 Q {x + 150} 1420 {x + 112} 1440 L {x + 120} {FLOOR_Y} "
                     f"L {x + 50} {FLOOR_Y} L {x + 58} 1440 Q {x + 20} 1420 {x + 10} 1320 Z", PORCELAIN, 4,
          stroke=s.ink)  # fmt: skip
    shape(s, parent, f"M {x + 32} 1336 Q {x + 85} 1372 {x + 138} 1336", sw=4, stroke="#c9c4b8")


def _closed(cv: Canvas, parent) -> None:
    x, y, w, h = CAB
    box(cv, parent, x, y, w, h, CABINET, 4, r=6)
    for i in range(3):
        box(cv, parent, x + 30, y + 40 + i * (h - 80) / 3, w - 60, (h - 80) / 3 - 20, "#b98a5b", 3, r=6)
    for hx in (x + w / 2 - 90, x + w / 2 + 60):
        box(cv, parent, hx, y + h - 120, 30, 70, STEEL, r=8)


def _folding(cv: Canvas, parent) -> None:
    """The bed halfway: the cabinet's face tipping toward the camera, wider and shorter."""
    x, y, w, _ = CAB
    _recess(cv, parent)
    shape(cv, parent, f"M {x} {FLOOR_Y} L {x + w} {FLOOR_Y} L {x + w + 70} {y + 360} L {x - 70} {y + 360} Z",
          CABINET, 4, stroke=cv.ink)  # fmt: skip


def _recess(cv: Canvas, parent) -> None:
    x, y, w, h = CAB
    box(cv, parent, x, y, w, h, RECESS, 4, r=6)
    box(cv, parent, x + w / 2 - 70, y + 90, 140, 180, "#e9dcc0", 3, r=4)  # a postcard Gary left in there
    shape(cv, parent, f"M {x + w / 2 - 50} {y + 230} Q {x + w / 2} {y + 150} {x + w / 2 + 50} {y + 230}", sw=6,
          stroke="#c0453b")  # fmt: skip


def _open(cv: Canvas, parent, sleeper: Look | None, talk: Sequence[tuple[float, float]], end: float) -> None:
    x, _, w, _ = CAB
    _recess(cv, parent)
    far, near = (x, x + w), (x - 140, x + w + 140)
    for lx in (near[0] + 30, near[1] - 60):  # the legs that swing out
        box(cv, parent, lx, NEAR_Y + 40, 30, 70, CABINET_EDGE, 3, r=4)
    base = f"M {near[0]} {NEAR_Y} L {near[1]} {NEAR_Y} L {near[1]} {NEAR_Y + 50} L {near[0]} {NEAR_Y + 50} Z"
    shape(cv, parent, base, CABINET, 4, stroke=cv.ink)
    top = f"M {far[0]} {FLOOR_Y} L {far[1]} {FLOOR_Y} L {near[1]} {NEAR_Y} L {near[0]} {NEAR_Y} Z"
    shape(cv, parent, top, MATTRESS, 4, stroke=cv.ink)
    cx = x + w / 2
    oval(cv, parent, cx - 160, FLOOR_Y - 4, 320, 84, PILLOW, stroke=cv.ink, sw=4)
    if sleeper is None:
        shape(cv, parent, f"M {far[0] + 30} {FLOOR_Y + 90} L {far[1] - 30} {FLOOR_Y + 90} L {near[1] - 40} "
                          f"{NEAR_Y - 10} L {near[0] + 40} {NEAR_Y - 10} Z", BLANKET, 4, stroke=cv.ink)  # fmt: skip
        return
    head = _group(cv, parent, x=cx, y=FLOOR_Y + 10, scaleX=0.8, scaleY=0.8)
    _head(cv, head, sleeper)
    _features(cv, _group(cv, head), Face("closed", "flat", "flat", (0.0, 0.0)), sleeper)
    quiet = _group(cv, head, y=44)
    shape(cv, quiet, "M -18 0 Q 0 8 18 0", sw=5, stroke=cv.ink)
    for start, stop in talk:  # an open mouth while he talks, the line otherwise
        said = _group(cv, head, y=44)
        oval(cv, said, -16, -10, 32, 26, "#3a2a2a", stroke=cv.ink, sw=4)
        _gate(cv, said, start, stop, end)
    if talk:
        cv.gate(quiet, [(a, b) for a, b in _between(talk, end)])
    # the blanket over him, up to the chin, with the bump of his knees
    shape(cv, parent, f"M {far[0] + 20} {FLOOR_Y + 80} Q {cx} {FLOOR_Y + 60} {far[1] - 20} {FLOOR_Y + 80} "
                      f"L {near[1] - 30} {NEAR_Y - 8} L {near[0] + 30} {NEAR_Y - 8} Z", BLANKET, 4,
          stroke=cv.ink)  # fmt: skip
    shape(cv, parent, f"M {cx - 120} {NEAR_Y - 90} Q {cx - 60} {NEAR_Y - 170} {cx} {NEAR_Y - 90} M {cx + 10} "
                      f"{NEAR_Y - 90} Q {cx + 70} {NEAR_Y - 170} {cx + 130} {NEAR_Y - 90}", sw=5,
          stroke=BLANKET_FOLD)  # fmt: skip
    shape(
        cv,
        parent,
        f"M {far[0] + 30} {FLOOR_Y + 112} Q {cx} {FLOOR_Y + 96} {far[1] - 30} {FLOOR_Y + 112}",
        sw=6,
        stroke="#ffffff",
    )  # the sheet's turned-down edge, fmt: skip
    zs = _group(cv, parent)
    for i, (zx, zy, zs_) in enumerate(((cx + 90, FLOOR_Y - 60, 1.0), (cx + 140, FLOOR_Y - 130, 1.4))):
        k = 22 * zs_
        shape(cv, zs, f"M {zx} {zy} L {zx + k} {zy} L {zx} {zy + k} L {zx + k} {zy + k}", sw=5 + i, stroke=cv.ink)
    if talk:
        cv.gate(zs, [(a, b) for a, b in _between(talk, end)])


def _between(talk: Sequence[tuple[float, float]], end: float) -> list[tuple[float, float]]:
    """The spans of the shot outside ``talk``."""
    out, at = [], 0.0
    for start, stop in talk:
        if start > at:
            out.append((at, start))
        at = stop
    if at < end:
        out.append((at, end))
    return out


@register("prop", "stick-murphy-bed", episodes=("the-viewing",), tags=("home", "flat", "bed", "reveal"))
def murphy_bed(
    cv: Canvas,
    parent,
    end: float,
    *,
    drop_at: float | None = None,
    sleeper: Look | None = None,
    talk: Sequence[tuple[float, float]] = (),
):
    """The bed in :func:`studio`'s cabinet over a shot of ``end`` seconds: closed in the wall, or, from
    ``drop_at``, folding down through one mid frame (:data:`FOLD`) and open on the floor (0: open the whole shot).
    Open, it holds ``sleeper`` under the blanket, snoring, and his mouth opens in each ``(start, stop)`` of
    ``talk``, which must fall while the bed is open."""
    if not (isinstance(end, (int, float)) and math.isfinite(end) and end > 0):
        raise StickDataError(f"the bed needs a positive shot length, got {end!r}")
    if drop_at is not None:
        drop_at = _check_time(drop_at, end, "drop_at")
    if sleeper is not None:
        check_look(sleeper)
    if talk and sleeper is None:
        raise StickDataError("only a sleeper can talk: pass sleeper= with talk=")
    opened = None if drop_at is None else drop_at + (FOLD if drop_at > 0 else 0.0)
    last = 0.0
    for start, stop in talk:
        if not (opened is not None and opened <= start < stop <= end and start >= last):
            raise StickDataError(f"talk spans run in order while the bed is open ({opened}..{end}), got {list(talk)!r}")
        last = stop
    g = _group(cv, parent)
    if drop_at is None:
        _closed(cv, g)
        return g
    assert opened is not None
    if drop_at > 0:
        up, mid = _group(cv, g), _group(cv, g)
        _closed(cv, up)
        _gate(cv, up, 0.0, drop_at, end)
        _folding(cv, mid)
        _gate(cv, mid, drop_at, min(opened, end), end)
    down = _group(cv, g)
    _open(cv, down, sleeper, talk, end)
    _gate(cv, down, min(round(opened, 3), end), end, end)
    return g

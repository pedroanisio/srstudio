"""The Saga's everyday rooms: a family's hut with a table and a Directorate returns desk, and what lands on them.

The mundane system wins in these two rooms, so they are drawn as plainly as the bridge is drawn grandly: a table, a
plate, a form; a counter, a printer, a coupon. Both have a front layer the cast stand behind (:data:`saga_sets.FRONTS`),
and a prop that moves does so on the shot's clock from a track of its own, so a reel can time it to a recorded line.
Importing this module adds its sets and props to :data:`saga_sets.SETS`, :data:`saga_sets.FRONTS` and
:data:`saga_sets.PROPS`, which is how a :class:`~srstudio.saga_reel.Stage` names them.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks, saga_sets
from ._saga_everyday_contracts import contract
from .canvas import Canvas
from .registry import register
from .saga import SagaError
from .saga_sets import FLOOR, INK_W, H, W, _check_end, _check_spans, _far, _marks, _pool, _stars, _text

__all__ = [
    "TABLE_BOTTOM",
    "TABLE_TOP",
    "DESK_TOP",
    "DESK_EDGE",
    "hut",
    "hut_table",
    "returns",
    "returns_desk",
    "plate",
    "cup",
    "teapot",
    "ration_bar",
    "wince",
    "tooth",
    "benefits",
    "form",
    "pen",
    "basket",
    "coupon",
    "dim",
    "bar_down",
    "hole_of",
]

TABLE_TOP = 1075  # the far edge of the hut's table
TABLE_FRONT = 1135  # where its top meets its front
TABLE_BOTTOM = FLOOR + 120  # where its front stops, far enough under the hem of whoever stands behind it
DESK_TOP = 1000  # the returns counter's top
DESK_EDGE = 640  # its left end, where a coupon runs out of counter
SHELF_Y = 540  # the hut's shelf, the height of the hologram's puck
HOLE = (45, 100)  # a basket's panel's hole from the basket's rim centre
RETURNS_LIT = ((633.5, 369.5, 237.0, 95.0), (670.0, 472.0, 164.0, 70.0))  # the sign and its number board, lit
Track = Sequence[tuple[float, ...]]


def _track(track: Track, width: int, what: str) -> None:
    """``track`` is rows of ``width`` finite numbers whose first, the second, rises from 0 or later."""
    if not track or any(len(row) != width or not all(map(checks.number, row)) for row in track):
        raise SagaError(f"{what}: a track is rows of {width} finite numbers, got {track}")
    times = [row[0] for row in track]
    if times[0] < 0 or times != sorted(set(times)):
        raise SagaError(f"{what}: a track's seconds must rise from 0 or later, got {times}")


def _key(cv: Canvas, node, prop: str, rows: Sequence[tuple[float, float]], kind: str = "sine-in-out") -> None:
    cv.keys(node, prop, [(t, round(v, 3)) for t, v in rows], kind=kind)


# -- the hut ----------------------------------------------------------------------------------------------------------
@register(
    "location",
    "saga-hut",
    summary="Inside the family's desert hut: warm plaster, a round window on two suns, a shelf of jars with the "
    "cactus on its end",
    contract=contract('saga-hut'),
)
def hut(cv: Canvas, parent, *, end: float) -> None:
    """The hut; the cast stands behind its table (:func:`hut_table`) on :data:`saga_sets.BEHIND`."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    far = _far(cv, g)
    cv.rect(far, 0, 0, W, H, cv.grad("saga-hut-wall", [(0, "#a06a42"), (0.6, "#6e4228"), (1, "#3a2214")], (0, 0, 0, 1)))
    cv.ellipse(far, 660, 320, 250, 250, "#3a2214", cv.ink, INK_W)
    cv.ellipse(far, 676, 336, 218, 218, cv.grad("saga-hut-sky", [(0, "#f2c26b"), (1, "#e2622e")], (0, 0, 0, 1)))
    for x, y, r in ((720, 396, 46), (806, 430, 28)):
        cv.ellipse(far, x, y, r, r, "#fff0c4")
    cv.path(far, "M676 480 Q760 440 894 474 L880 530 Q790 570 700 530 Z", "#a85a2e")
    cv.path(far, "M-20 150 Q540 40 1100 150", stroke="#3a2214", sw=18)
    cv.rect(g, 0, 1240, W, H - 1240, cv.grad("saga-hut-floor", [(0, "#4a2c1c"), (1, "#1c0f08")], (0, 0, 0, 1)))
    for y, gap in ((1450, 150), (1560, 210), (1700, 290)):
        cv.line(g, -20, y, W + 20, y, "#2a170c", 4)
        for x in range(-60 + y % 90, W, gap):
            cv.line(g, x, y, x - 20, y + gap // 2, "#2a170c", 3)
    _pool(cv, g, "hut", "#f2b84b", 1180, opacity=0.2)
    cv.rect(g, 84, SHELF_Y, 590, 22, "#5a3420", cv.ink, INK_W, radius=6)
    for x, y in ((130, 562), (620, 562)):
        cv.path(g, f"M{x} {y} L{x} {y + 34} L{x + 26} {y}", "#4a2c1c", cv.ink, 4)
    _marks(cv, g, (632, SHELF_Y), (186, SHELF_Y + 30), 0.5, "#f2d9a6")


@register(
    "location",
    "saga-hut-table",
    summary="The hut's kitchen table, drawn after the family who sit behind it: a scrubbed top and a plank front",
    contract=contract('saga-hut-table'),
)
def hut_table(cv: Canvas, parent, *, end: float) -> None:
    """The table, drawn after the cast behind it; what stands on it is a prop drawn after this."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, -20, TABLE_TOP, W + 40, TABLE_FRONT - TABLE_TOP, "#b5804c", cv.ink, INK_W)
    cv.rect(g, -20, TABLE_TOP + 6, W + 40, 8, "#ffffff", opacity=0.1)
    cv.rect(g, -20, TABLE_FRONT, W + 40, TABLE_BOTTOM - TABLE_FRONT, "#4e2d1a", cv.ink, INK_W)
    for x in range(100, W, 220):
        cv.line(g, x, TABLE_FRONT + 6, x, TABLE_BOTTOM - 6, "#3a2012", 5)


@register("prop", "saga-plate", summary="A plain plate, seen from the table's edge", contract=contract('saga-plate'))
def plate(cv: Canvas, parent, *, at: tuple[float, float], end: float, width: float = 180) -> None:
    _check_end(end)
    x, y = at
    g = cv.group(parent, cv.uid("g"))
    cv.ellipse(g, x - width / 2 + 6, y - 12, width, 40, "#000000", opacity=0.22)
    cv.ellipse(g, x - width / 2, y - 18, width, 36, "#e4dcc8", cv.ink, 4)
    cv.ellipse(g, x - width * 0.34, y - 11, width * 0.68, 22, "#cfc6ae", opacity=0.8)


@register(
    "prop",
    "saga-cup",
    summary="A clay cup with no handle, tea running into it, a little steam off it after",
    contract=contract('saga-cup'),
)
def cup(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    end: float,
    steam: float | None = None,
    pour: tuple[float, float] | None = None,
) -> None:
    """The cup on the table at ``at``; tea falls into it during ``pour``, and steam rises from second ``steam``."""
    _check_end(end)
    x, y = at
    g = cv.group(parent, cv.uid("g"))
    cv.path(g, f"M{x - 34} {y - 54} L{x + 34} {y - 54} L{x + 26} {y} L{x - 26} {y} Z", "#8a4a2c", cv.ink, 4)
    cv.ellipse(g, x - 34, y - 62, 68, 16, "#3a1a10", cv.ink, 4)
    if steam is not None:
        if not (checks.number(steam) and 0 <= steam < end):
            raise SagaError(f"a cup's steam starts inside the shot, got {steam}")
        rise = cv.path(g, f"M{x} {y - 70} q-14 -26 0 -50 q14 -26 0 -50", stroke="#fff4dc", sw=5)
        _key(cv, rise, "opacity", [(0.0, 0.0), (steam, 0.0), (min(steam + 0.4, end), 0.35)], "linear")
    if pour is not None:
        tea = cv.line(g, x, y - 112, x, y - 58, "#8a4a2c", 8)
        cv.gate(tea, _check_spans((pour,), end, "a pour"))


def teapot(cv: Canvas, hand, *, turn: float = 0.0) -> None:
    """A clay teapot held by its handle in a hand's group (:attr:`srstudio.saga.Arm.holds`), its spout along the
    pot's own +x, ``turn`` degrees on from the arm, so a reel can level it against the arm's swing."""
    g = cv.group(hand, cv.uid("g"), rotation=turn)
    cv.path(g, "M12 -30 Q-26 0 12 30", stroke=cv.ink, sw=16)
    cv.path(g, "M100 -10 L148 -34 L154 -20 L108 24 Z", "#8a4a2c", cv.ink, 4)
    cv.ellipse(g, 10, -46, 112, 92, "#8a4a2c", cv.ink, INK_W)
    cv.ellipse(g, 44, -58, 44, 16, "#6e3a22", cv.ink, 4)


def ration_bar(cv: Canvas, hand, *, until: float | None = None) -> None:
    """A foil ration bar in a hand, its top already bitten at; ``until`` it is put down."""
    g = cv.group(hand, cv.uid("g"))
    if until is not None:
        cv.gate(g, [(0.0, until)])
    cv.path(g, "M-20 -8 L20 -8 L20 74 Q8 62 2 76 Q-8 62 -20 72 Z", "#6e7a4a", cv.ink, 4)
    cv.rect(g, -20, -8, 40, 24, "#c9c2a8", cv.ink, 3)
    cv.line(g, -10, 34, 10, 34, "#4e5834", 4)


@register(
    "prop",
    "saga-ration-bar",
    summary="A foil ration bar put down on a plate, one end bitten at",
    contract=contract('saga-ration-bar'),
)
def bar_down(cv: Canvas, parent, *, at: tuple[float, float], end: float, since: float = 0.0) -> None:
    _check_end(end)
    x, y = at
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    if since:
        cv.gate(g, [(since, end)])
    cv.path(g, "M-46 -20 L38 -20 Q26 -8 40 -2 Q26 4 38 12 L-46 12 Z", "#6e7a4a", cv.ink, 4)
    cv.rect(g, -46, -20, 26, 32, "#c9c2a8", cv.ink, 3)


@register(
    "prop",
    "saga-wince",
    summary="Three red pain ticks at a jaw, shown in the spans it hurts",
    contract=contract('saga-wince'),
)
def wince(cv: Canvas, parent, *, at: tuple[float, float], end: float, spans: Sequence[tuple[float, float]]) -> None:
    _check_end(end)
    held = _check_spans(spans, end, "a wince")
    if not held:
        raise SagaError("a wince needs a span to hurt in")
    x, y = at
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, held)
    for dx, dy, ex, ey in ((0, -40, 26, -66), (12, 0, 46, 0), (0, 40, 26, 66)):
        cv.line(g, x + dx, y + dy, x + ex, y + ey, "#e0352b", 8)


@register(
    "prop",
    "saga-tooth",
    summary="One tooth that drops from a mouth to where it lands, with a small bounce",
    contract=contract('saga-tooth'),
)
def tooth(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    end: float,
    start: tuple[float, float] | None = None,
    falls: tuple[float, float] = (0.0, 0.0),
) -> None:
    """A tooth on ``at``; with ``start``, it appears there at ``falls[0]`` and lands at ``falls[1]``."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1])
    if start is not None:
        a, b = falls
        if not 0 <= a < b <= end:
            raise SagaError(f"a tooth falls inside the shot, got {falls} of {end}")
        cv.gate(g, [(a, end)])
        _key(cv, g, "x", [(a, start[0]), (b, at[0])], "linear")
        drop = [(a, start[1]), (b, at[1]), (b + 0.07, at[1] - 16), (b + 0.14, at[1])]
        cv.keys(g, "y", [(t, round(v, 3)) for t, v in drop if t <= end], hold=False)
    shape = "M-16 -22 Q0 -30 16 -22 Q22 -4 12 8 L9 22 L3 8 L-3 8 L-9 22 L-12 8 Q-22 -4 -16 -22 Z"
    cv.path(g, shape, "#fffdf2", cv.ink, 3)


@register(
    "prop",
    "saga-benefits",
    summary="A hologram on a shelf puck, kept like a graduation photo: the Directorate's benefits card",
    contract=contract('saga-benefits'),
)
def benefits(cv: Canvas, parent, *, at: tuple[float, float], end: float, since: float | None = None) -> None:
    """The puck on the shelf at ``at``; from ``since`` (a second of the shot, 0 already on) the card above it."""
    _check_end(end)
    x, y = at
    g = cv.group(parent, cv.uid("g"))
    cv.ellipse(g, x - 54, y - 18, 108, 24, "#2b3142", cv.ink, 4)
    if since is None:
        return
    if not (checks.number(since) and 0 <= since < end):
        raise SagaError(f"a hologram comes on inside the shot, got {since}")
    card = cv.group(g, cv.uid("g"))
    if since:
        _key(cv, card, "opacity", [(0.0, 0.0), (since, 0.0), (min(since + 0.14, end), 1.0)], "linear")
    cv.path(card, f"M{x - 34} {y - 14} L{x + 34} {y - 14} L{x + 180} {y - 66} L{x - 180} {y - 66} Z", "#f2b84b",
            opacity=0.16)  # fmt: skip
    box = (x - 214, y - 216, 428, 150)
    cv.rect(card, *box, saga_sets.HOLO_FILL, "#f2b84b", 5, radius=18)
    for yy in range(int(box[1]) + 10, int(box[1] + box[3]) - 6, 16):
        cv.rect(card, box[0] + 8, yy, box[2] - 16, 2, "#f2b84b", opacity=0.06)
    _text(cv, card, "DIRECTORATE BENEFITS", box[0] + 18, box[1] + 18, box[2] - 36, 44, 34, "#f2b84b", "center")
    _text(cv, card, "Dental. Vision. Pension.", box[0] + 18, box[1] + 76, box[2] - 36, 44, 34, "#fff4dc", "center")


@register(
    "prop",
    "saga-form",
    summary="A Directorate application, filled in and stamped, that slides over a table with a pen on top",
    contract=contract('saga-form'),
)
def form(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    end: float,
    slide: Track = (),
    since: float = 0.0,
    pen_until: float | None = None,
) -> None:
    """The form on ``at``; ``slide`` is rows of (second, x) along the table; the pen lies on it until ``pen_until``."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1])
    if since:
        cv.gate(g, [(since, end)])
    if slide:
        _track(slide, 2, "a form's slide")
        _key(cv, g, "x", [(t, x) for t, x in slide])
    cv.path(g, "M-120 22 L-86 -22 L120 -22 L104 22 Z", "#000000", opacity=0.2)
    cv.path(g, "M-124 16 L-90 -28 L116 -28 L100 16 Z", "#f4eedc", cv.ink, 4)
    for y, a, b in ((-18, -70, 60), (-8, -84, 74), (2, -94, 40)):
        cv.line(g, a, y, b, y, "#2b3142", 3)
    cv.ellipse(g, 54, -8, 30, 18, "#c9302c", opacity=0.85)
    drawn = cv.group(g, cv.uid("g"))
    if pen_until is not None:
        if not 0 < pen_until <= end:
            raise SagaError(f"a pen is taken inside the shot, got {pen_until} of {end}")
        cv.gate(drawn, [(0.0, pen_until)])
    cv.line(drawn, -60, 10, 66, -22, "#15161c", 9)
    cv.line(drawn, 58, -20, 70, -23, "#f2b84b", 5)


def pen(cv: Canvas, hand, *, since: float) -> None:
    """The pen in a hand's group, in the fingers from ``since``."""
    g = cv.group(hand, cv.uid("g"))
    cv.gate(g, [(since, 3600.0)])
    cv.line(g, 0, -40, 0, 70, "#15161c", 9)
    cv.line(g, 0, 64, 0, 78, "#f2b84b", 5)


# -- the returns desk -------------------------------------------------------------------------------------------------
@register(
    "location",
    "saga-returns",
    summary="A Directorate returns desk on the bridge: a window on the stars, a RETURNS sign and a number board",
    contract=contract('saga-returns'),
)
def returns(cv: Canvas, parent, *, end: float) -> None:
    """The returns bay; the cast stands on its deck at :data:`saga_sets.FLOOR`, the clerk behind its desk."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    far = _far(cv, g)
    cv.rect(far, 0, 0, W, H, cv.grad("saga-returns-wall", [(0, "#2f3850"), (1, "#161b28")], (0, 0, 0, 1)))
    cv.rect(far, 40, 240, 540, 296, "#060814", cv.ink, INK_W, radius=18)
    _stars(cv, far, 11, 26, (60, 256, 560, 520), end)
    for x in (220, 400):
        cv.path(far, f"M{x} 240 L{x - 14} 536", stroke="#2b3142", sw=18)
    cv.rect(g, 0, 960, W, FLOOR - 960, "#151a26")
    cv.rect(g, 40, 972, 1000, 12, "#5fd4ff", radius=6, opacity=0.5)
    cv.rect(g, 0, FLOOR, W, H - FLOOR, cv.grad("saga-returns-deck", [(0, "#232a3a"), (1, "#0b0d14")], (0, 0, 0, 1)))
    for i in range(7):
        cv.line(g, 540 + (i - 3) * 60, FLOOR, 540 + (i - 3) * 400, H, "#2f3850", 3)
    _pool(cv, g, "returns", "#5fd4ff", FLOOR - 60, opacity=0.2)
    cv.rect(g, 36, 536, 552, 18, "#2b3142", cv.ink, INK_W, radius=4)
    cv.rect(g, 636, 372, 232, 90, "#0f1a20", "#f2b84b", 5, radius=12)
    _text(cv, g, "RETURNS", 642, 392, 220, 54, 46, "#f2b84b", "center")
    cv.rect(g, 672, 474, 160, 66, "#0f1a20", cv.ink, 4, radius=10)
    _text(cv, g, "No. 1", 680, 484, 144, 46, 38, "#ff9d8f", "center")
    _marks(cv, g, (120, 536), (212, 566), 0.5, "#5fd4ff")


@register(
    "location",
    "saga-returns-desk",
    summary="The returns counter, drawn after the clerk behind it: a steel top, a coupon printer and a dark front",
    contract=contract('saga-returns-desk'),
)
def returns_desk(cv: Canvas, parent, *, end: float) -> None:
    """The counter from :data:`DESK_EDGE` to the frame's right, its top at :data:`DESK_TOP`."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, DESK_EDGE, DESK_TOP, W, 44, "#9aa3ad", cv.ink, INK_W)
    cv.rect(g, DESK_EDGE, DESK_TOP + 44, W, FLOOR + 56 - DESK_TOP - 44, "#232a3a", cv.ink, INK_W)
    cv.rect(g, DESK_EDGE + 8, DESK_TOP + 6, W, 8, "#ffffff", opacity=0.25)
    for x in (720, 880, 1040):
        cv.rect(g, x, DESK_TOP + 80, 120, 190, "#1b2030", cv.ink, 4, radius=10)
    cv.rect(g, 700, DESK_TOP - 42, 110, 46, "#2b3142", cv.ink, 4, radius=8)
    cv.rect(g, 708, DESK_TOP - 10, 94, 8, "#060814")


@register(
    "prop",
    "saga-basket",
    summary="A wire basket of battle-station wreckage, a bent panel hanging off its front with the hole in it",
    contract=contract('saga-basket'),
)
def basket(cv: Canvas, parent, *, at: tuple[float, float], end: float) -> None:
    """The basket's rim centred on ``at``; :func:`hole_of` says where the panel's hole lands."""
    _check_end(end)
    x, y = at
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    for points, colour in (
        ("M-74 6 L-54 -96 L-14 -60 L-20 6 Z", "#4a5163"),
        ("M-14 6 L6 -120 L52 -86 L44 6 Z", "#6b7486"),
        ("M30 6 L56 -74 L74 -40 L70 6 Z", "#3a3f52"),
    ):
        cv.path(g, points, colour, cv.ink, 4)
    cv.path(g, "M-88 0 L88 0 L74 150 L-74 150 Z", "#2b3142", cv.ink, INK_W)
    for k in range(-2, 3):
        cv.line(g, k * 32, 6, k * 28, 146, "#6b7486", 4)
    cv.line(g, -82, 60, 82, 60, "#6b7486", 4)
    px, py = HOLE
    cv.path(g, f"M{px - 66} {py - 56} L{px + 60} {py - 66} Q{px + 84} {py + 10} {px + 56} {py + 70} "
               f"L{px - 58} {py + 62} Q{px - 86} {py} {px - 66} {py - 56} Z", "#9aa3ad", cv.ink, INK_W)  # fmt: skip
    cv.ellipse(g, px - 40, py - 40, 80, 80, "#060814", "#ffb25a", 5)
    for dx, dy in ((-48, -44), (46, -50), (44, 48), (-46, 44)):
        cv.ellipse(g, px + dx - 4, py + dy - 4, 8, 8, "#4a5163")


def hole_of(at: tuple[float, float]) -> tuple[float, float]:
    """Where the hole of a basket at ``at`` lands on the frame."""
    return at[0] + HOLE[0], at[1] + HOLE[1]


@register(
    "prop",
    "saga-coupon",
    summary="A tiny printed coupon, on a track of its own, that can shrink to nothing",
    contract=contract('saga-coupon'),
)
def coupon(cv: Canvas, parent, *, at: tuple[float, float], end: float, track: Track) -> None:
    """A coupon at ``at`` moved by ``track``, rows of (second, x, y, scale), hidden before its first and at scale 0."""
    _check_end(end)
    _track(track, 4, "a coupon")
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1])
    gone = next((row[0] for row in track if row[3] <= 0), end)
    cv.gate(g, [(track[0][0], gone)])
    for prop, i in (("x", 1), ("y", 2), ("scaleX", 3), ("scaleY", 3)):
        cv.keys(g, prop, [(row[0], round(row[i], 3)) for row in track], hold=False)
    cv.rect(g, -34, -14, 68, 28, "#fff8e6", cv.ink, 3, radius=3)
    cv.line(g, -24, -4, 18, -4, "#2b3142", 3)
    cv.line(g, -24, 5, 4, 5, "#2b3142", 3)


def _hole(box: tuple[float, ...], radius: float = 12.0) -> str:
    """The rounded outline of a box a dim leaves lit."""
    if len(box) != 4 or not all(checks.number(v) for v in box):
        raise SagaError(f"a lit box is x, y, w, h, got {box}")
    x, y, w, h = box
    if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > W or y + h > H:
        raise SagaError(f"a lit box stays on the frame and has an area, got {box}")
    r = min(radius, w / 2, h / 2)
    return (
        f"M{x + r} {y} H{x + w - r} Q{x + w} {y} {x + w} {y + r} V{y + h - r} Q{x + w} {y + h} {x + w - r} {y + h} "
        f"H{x + r} Q{x} {y + h} {x} {y + h - r} V{y + r} Q{x} {y} {x + r} {y} Z"
    )


@register(
    "prop",
    "saga-dim",
    summary="The room darkening over whatever is drawn before it, and coming back",
    contract=contract('saga-dim'),
)
def dim(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    end: float,
    spans: Sequence[tuple[float, float]],
    depth: float = 0.5,
    fade: float = 0.3,
    spared: Sequence[tuple[float, ...]] = (),
) -> None:
    """Dark over the frame in ``spans``, ``fade`` seconds in and out, to ``depth``, except the (x, y, w, h) boxes of
    ``spared``, the lit things a dark room leaves readable; ``at`` is its unused centre."""
    _check_end(end)
    held = _check_spans(spans, end, "a dim")
    if not held or not 0 < depth <= 1:
        raise SagaError(f"a dim needs a span and a depth in 0..1, got {spans} and {depth}")
    keys: list[tuple[float, float]] = [(0.0, 0.0)]
    for a, b in held:
        keys += [(a, 0.0), (round(a + fade, 4), depth), (round(max(b - fade, a + fade), 4), depth), (b, 0.0)]
    d = f"M-200 -200 H{W + 200} V{H + 200} H-200 Z"
    for box in spared:
        d += " " + _hole(box)
    node = cv.path(parent, d, "#05060c", cv.clear, 0, fillRule="evenodd")
    cv.keys(node, "opacity", sorted(set(keys)), hold=False)


saga_sets.SETS.update(hut=hut, returns=returns)
saga_sets.FRONTS.update(hut=hut_table, returns=returns_desk)
saga_sets.BEHIND.update(hut=1340, returns=1300)
saga_sets.PROPS.update(
    {
        "plate": plate,
        "cup": cup,
        "ration-bar": bar_down,
        "wince": wince,
        "tooth": tooth,
        "benefits": benefits,
        "form": form,
        "basket": basket,
        "coupon": coupon,
        "dim": dim,
    }
)

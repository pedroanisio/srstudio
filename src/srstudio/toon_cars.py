"""Toon cars: a car's inside seen from the dashboard, what goes past its windows, and a pad that keeps count.

:func:`car_inside` is a car's body round one wide window with the road scrolling through it (``toon_world.road`` behind
the glass), and whatever :class:`Passing` says goes by between the two, right to left. :func:`seat` stands behind the
character, :func:`steering_wheel` in front of it, and the dashboard is ``toon_house.ledge(cv, front, "dash")``, which
carries the signature marks as a desk does. :func:`side_car`, :func:`school_bus` and :func:`banana` are drawn on their
own too, for a shot with no car round them; :func:`drive_past` moves a vehicle across the frame. :func:`tally_pad`
holds a count in fives, and each of its ``strokes`` is added at its time.

Every measure is a reference screen pixel (:func:`srstudio.toon.fx`/``fy``), like the rest of the style, and every key
is on the composition clock. Bad input is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

from . import checks, toon_world
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, REF_W, ToonDataError, _path, fh, fx, fy
from .toon_sets import _inked, _line, _shadow

__all__ = [
    "BODY",
    "GREY",
    "PAD_H",
    "PAD_W",
    "PAD_MOST",
    "Passing",
    "banana",
    "car_inside",
    "dash_vents",
    "drive_past",
    "pass_seconds",
    "school_bus",
    "seat",
    "side_car",
    "steering_wheel",
    "stroke_line",
    "tally_pad",
]

Point = tuple[float, float]

BODY = "#ffcf33"  # a car's paint, inside and out, unless a part is told otherwise
BODY_SHADE = "#e0ab1c"
GREY = "#9aa2ad"
GLASS = "#a9d6e6"
GLASS_DARK = "#6f9fb4"
TIRE = "#2b2b33"
HUB = "#c9ced6"
LAMP = "#fff3c4"
TRIM = "#3a3f5c"
TRIM_LIGHT = "#4e5478"
TRIM_DARK = "#2a2d44"
BUS_STRIPE = "#22242e"
BANANA = "#ffd84a"
BANANA_TIP = "#6b4a24"
PAPER = "#fbf7ec"
PAPER_LINE = "#c8d6e6"
RING = "#7b8294"
PENCIL = "#22242e"
_HEX = re.compile(r"#[0-9a-fA-F]{6}")

SPEED = 900.0  # reference pixels a second, what goes past
ROAD_Y, ROAD_SCALE = 770.0, 1.5  # the near lane through the glass: its ground, and how big it draws what goes past
HALF_LENGTH = {"car": 170.0, "bus": 290.0}
WINDOW = (34.0, 176.0, 524.0, 700.0)  # x, y, width, height of the glass, its foot under the dashboard
PILLAR = 96.0
CAR_OUTLINE = (
    "M -158,-24 L -158,-56 Q -156,-72 -128,-76 L -78,-84 Q -50,-128 -20,-130 L 36,-130 Q 62,-128 94,-84 L 138,-76 "
    "Q 160,-70 160,-50 L 160,-24 Z"
)
PAD_W, PAD_H = 216.0, 190.0
STROKE_GAP, GATE_GAP, ROW_GAP = 11.0, 21.0, 74.0  # between strokes, between fives, between rows
STROKE_H = 54.0
PAD_GATES, PAD_ROWS = 3, 2
PAD_MOST = 5 * PAD_GATES * PAD_ROWS
_WOBBLE = (0.0, 2.0, -1.5, 1.0)  # a hand does not rule its lines: the same wobble each time, so a redraw is the same


@dataclass(frozen=True)
class Passing:
    """One vehicle going by: ``at`` is when its middle crosses the frame's, ``kind`` a key of :data:`HALF_LENGTH`."""

    at: float
    kind: str = "car"
    colour: str = GREY


def _colour(colour: object, what: str) -> None:
    if not (isinstance(colour, str) and _HEX.fullmatch(colour)):
        raise ToonDataError(f"{what} is a #rrggbb colour, got {colour!r}")


def _check_passing(passing: Passing) -> None:
    if not (checks.number(passing.at) and passing.at >= 0):
        raise ToonDataError(f"a vehicle passes at 0 s or later, got {passing.at!r}")
    if passing.kind not in HALF_LENGTH:
        raise ToonDataError(f"a passing vehicle is one of {sorted(HALF_LENGTH)}, got {passing.kind!r}")
    _colour(passing.colour, "a passing vehicle's paint")


def _scaled(cv: Canvas, parent, at: Point, scale: float, id: str | None):
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a scale is over 0, got {scale!r}")
    x, y = fx(at[0]), fy(at[1])
    return cv.group(parent, id or cv.uid("g"), x=x, y=y, anchorX=x, anchorY=y, scaleX=scale, scaleY=scale)


def _traced(x: float, y: float, outline: str) -> str:
    """An outline's offsets from the ground point ``x``, ``y`` as a frame path: ``dx,dy`` pairs and path letters."""
    words = []
    for word in outline.split():
        if "," in word:
            dx, dy = word.split(",")
            words.append(f"{fx(x + float(dx)):.1f} {fy(y + float(dy)):.1f}")
        else:
            words.append(word)
    return " ".join(words)


def _wheel(cv: Canvas, g, x: float, y: float, r: float) -> None:
    cv.ellipse(g, fx(x - r), fy(y - r), fh(2 * r), fh(2 * r), TIRE, cv.ink, FINE_W)
    cv.ellipse(g, fx(x - r / 2), fy(y - r / 2), fh(r), fh(r), HUB, cv.ink, FINE_W / 2)


@register("prop", "toon-side-car", summary="A plain small car from the side, facing left, in any paint, with no badge")
def side_car(
    cv: Canvas,
    parent,
    at: Point = (296.0, 780.0),
    colour: str = BODY,
    scale: float = 1.0,
    id: str | None = None,
    wheels: tuple[str, ...] = ("front", "rear"),
) -> None:
    """The car with its wheels on the ground at ``at``, ``scale`` times its size about that point. ``wheels`` names
    the wheels it still has: :func:`loose_wheel` plays the one it lost."""
    _colour(colour, "a car's paint")
    if len(set(wheels)) != len(wheels) or not set(wheels) <= {"front", "rear"}:
        raise ToonDataError(f"a car's wheels are distinct among front and rear, got {wheels!r}")
    g = _scaled(cv, parent, at, scale, id)
    x, y = at
    _shadow(cv, g, x, y, 330, 16, 0.3)
    _path(cv, g, _traced(x, y, CAR_OUTLINE), colour, FINE_W)
    _inked(cv, g, [(x - 62, y - 84), (x - 32, y - 118), (x - 4, y - 118), (x - 4, y - 84)], GLASS, FINE_W / 2, 2)
    _inked(cv, g, [(x + 6, y - 84), (x + 6, y - 118), (x + 38, y - 118), (x + 74, y - 84)], GLASS, FINE_W / 2, 2)
    _line(cv, g, [(x + 1, y - 84), (x + 1, y - 28)], 4.0)
    cv.rect(g, fx(x - 34), fy(y - 70), fh(24), fh(7), TRIM, radius=fh(3))
    cv.ellipse(g, fx(x - 156), fy(y - 66), fh(26), fh(20), LAMP, cv.ink, FINE_W / 2)
    for name, wheel in (("front", x - 96), ("rear", x + 98)):
        if name in wheels:
            _wheel(cv, g, wheel, y - 28, 30)


@register(
    "prop",
    "toon-loose-wheel",
    summary="A car wheel that lets go of its axle at a set second and rolls away along the ground, turning as it goes",
)
def loose_wheel(
    cv: Canvas,
    parent,
    at: Point = (296.0, 780.0),
    start: float = 0.0,
    to: float = -80.0,
    seconds: float = 3.0,
    scale: float = 1.0,
    id: str | None = None,
) -> None:
    """A :func:`side_car`'s front wheel, for the car parked at ``at`` with ``wheels=("rear",)``: on its axle until
    ``start``, then rolling to reference ``to`` along the ground over ``seconds``, turning the distance it covers."""
    if not (checks.number(seconds) and seconds > 0):
        raise ToonDataError(f"a wheel rolls for over 0 seconds, got {seconds!r}")
    if not (checks.number(start) and start >= 0):
        raise ToonDataError(f"a wheel lets go from second 0, got {start!r}")
    x, y = at[0] - 96 * scale, at[1] - 28 * scale
    r = 30 * scale
    cx, cy = fx(x), fy(y)
    g = cv.group(parent, id or cv.uid("wheel"), x=cx, y=cy, anchorX=cx, anchorY=cy)
    _wheel(cv, g, x, y, r)
    _line(cv, g, [(x, y - r / 2), (x, y + r / 2)], 3.0)  # a spoke, or a turning wheel would look still
    travel = fx(to) - cx
    turned = math.degrees(travel / fh(r))
    keys = [(0.0, 0.0), (start, 0.0), (start + seconds, 1.0)]
    cv.keys(g, "x", [(t, round(cx + travel * k, 3)) for t, k in keys], hold=False, local=False)
    cv.keys(g, "rotation", [(t, round(turned * k, 3)) for t, k in keys], hold=False, local=False)


@register("prop", "toon-school-bus", summary="A long yellow bus from the side, facing left, stripes and no lettering")
def school_bus(cv: Canvas, parent, at: Point = (296.0, 780.0), scale: float = 1.0, id: str | None = None) -> None:
    """The bus with its wheels on the ground at ``at``, ``scale`` times its size about that point."""
    g = _scaled(cv, parent, at, scale, id)
    x, y = at
    _shadow(cv, g, x, y, 570, 18, 0.3)
    _inked(cv, g, [(x - 282, y - 26), (x - 282, y - 96), (x - 218, y - 112), (x - 218, y - 26)], BODY, FINE_W, 2)
    cv.rect(g, fx(x - 222), fy(y - 214), fh(500), fh(188), BODY, cv.ink, INK_W / 2, radius=fh(22))
    cv.rect(g, fx(x - 222), fy(y - 214), fh(500), fh(14), BODY_SHADE, cv.clear, 0, radius=fh(7))
    for k in range(7):
        cv.rect(g, fx(x - 204 + 66 * k), fy(y - 184), fh(54), fh(58), GLASS, cv.ink, FINE_W / 2, radius=fh(6))
    for top in (-112, -92):
        cv.rect(g, fx(x - 222), fy(y + top), fh(500), fh(9), BUS_STRIPE, cv.clear, 0, radius=0)
    cv.ellipse(g, fx(x - 278), fy(y - 86), fh(22), fh(20), LAMP, cv.ink, FINE_W / 2)
    for wheel in (x - 170, x + 186):
        _wheel(cv, g, wheel, y - 30, 36)


@register("prop", "toon-banana", summary="One banana on its side, ripe, a little bruised at the tips")
def banana(cv: Canvas, parent, at: Point = (296.0, 780.0), scale: float = 1.0, id: str | None = None) -> None:
    """The banana lying with its belly on the ground at ``at``, ``scale`` times its size about that point."""
    g = _scaled(cv, parent, at, scale, id)
    x, y = at
    _shadow(cv, g, x, y, 200, 12, 0.3)
    _inked(
        cv,
        g,
        [(x + dx, y + dy) for dx, dy in (
            (-104, -64), (-74, -20), (-20, -4), (44, -6), (96, -46), (108, -74), (86, -66),
            (34, -40), (-20, -38), (-82, -74),
        )],
        BANANA,
        FINE_W,
        4,
    )  # fmt: skip
    _line(cv, g, [(x - 72, y - 46), (x - 18, y - 22), (x + 42, y - 24), (x + 84, y - 54)], 4.0, BODY_SHADE)
    cv.rect(g, fx(x - 112), fy(y - 80), fh(22), fh(18), BANANA_TIP, cv.ink, FINE_W / 2, radius=fh(4))


def _half_span(passing: Passing, scale: float) -> float:
    return REF_W / 2 + HALF_LENGTH[passing.kind] * scale + 20.0


def pass_seconds(passing: Passing, scale: float = 1.0, speed: float = SPEED) -> float:
    """How long ``passing`` is on the frame, nose in to tail out."""
    return 2 * _half_span(passing, scale) / speed


def drive_past(
    cv: Canvas, parent, passing: Passing, y: float, scale: float = 1.0, speed: float = SPEED, id: str | None = None
) -> None:
    """``passing`` crossing the frame right to left with its wheels on reference height ``y``. One that was already
    on the frame at 0 s starts part of the way across."""
    _check_passing(passing)
    if not (checks.number(y) and checks.number(speed) and speed > 0):
        raise ToonDataError(f"a vehicle drives at a height, at a speed over 0, got {y!r}, {speed!r}")
    half = _half_span(passing, scale)
    start, end = max(0.0, passing.at - half / speed), passing.at + half / speed
    g = cv.group(parent, id or cv.uid("g"), start=start, end=end)
    cv.keys(g, "x", [(t, fh(speed * (passing.at - t))) for t in (start, end)], hold=False)
    middle = (REF_W / 2, y)
    if passing.kind == "bus":
        school_bus(cv, g, middle, scale)
    else:
        side_car(cv, g, middle, passing.colour, scale)


@register(
    "location",
    "toon-car-inside",
    summary="Inside a car from the dashboard: its paint round one wide window, the road going past through the glass",
)
def car_inside(
    cv: Canvas, parent, start: float = 0.0, end: float = 4.0, passing: Sequence[Passing] = (), body: str = BODY
) -> None:
    """The road scrolling from ``start`` to ``end``, each of ``passing`` going by behind the glass, and the body round
    it; a seat, a wheel and a dashboard go on top, in front of the character or behind."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a car's inside runs over 0 <= start < end, got {start!r}..{end!r}")
    _colour(body, "a car's paint")
    g = cv.group(parent, cv.uid("g"))
    toon_world.road(cv, g, start, end, cab=False)
    for vehicle in passing:
        drive_past(cv, g, vehicle, ROAD_Y, ROAD_SCALE)
    x, y, w, h = WINDOW
    cv.rect(g, 0, 0, cv.width, fy(y - PILLAR / 2), body)
    cv.rect(g, fx(x - PILLAR / 2), fy(y - PILLAR / 2), fh(w + PILLAR), fh(h + PILLAR), cv.clear, body, fh(PILLAR),
            radius=fh(46 + PILLAR / 2))  # fmt: skip
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), cv.clear, cv.ink, INK_W, radius=fh(46))
    cv.rect(g, 0, fy(y - 60), cv.width, fh(8), BODY_SHADE if body == BODY else cv.ink, opacity=0.8)
    cv.rect(g, fx(226), fy(y - 8), fh(140), fh(46), TRIM_DARK, cv.ink, FINE_W, radius=fh(12))  # the mirror
    cv.rect(g, fx(236), fy(y), fh(120), fh(30), GLASS_DARK, cv.clear, 0, radius=fh(7))


@register("prop", "toon-car-seat", summary="A car seat's back and headrest, behind whoever sits in it")
def seat(cv: Canvas, parent, x: float = 165.0, colour: str = TRIM) -> None:
    """The seat centred on reference ``x``, its foot under the dashboard."""
    if not checks.number(x):
        raise ToonDataError(f"a seat stands at a reference x, got {x!r}")
    _colour(colour, "a seat's cover")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x - 74), fy(300), fh(148), fh(130), colour, cv.ink, INK_W, radius=fh(34))
    cv.rect(g, fx(x - 150), fy(410), fh(300), fh(520), colour, cv.ink, INK_W, radius=fh(46))
    cv.rect(g, fx(x - 118), fy(440), fh(236), fh(490), TRIM_LIGHT, cv.clear, 0, radius=fh(30))


@register(
    "prop", "toon-dash-vents", summary="A dashboard's front: two air vents and a glovebox, for under its top edge"
)
def dash_vents(cv: Canvas, parent) -> None:
    """Drawn over a ledge's front, with no marks of its own: the ledge carries them."""
    g = cv.group(parent, cv.uid("g"))
    for x in (60.0, 214.0):
        cv.rect(g, fx(x), fy(884), fh(120), fh(62), TRIM_DARK, TRIM_LIGHT, FINE_W, radius=fh(14))
        for k in range(4):
            cv.rect(g, fx(x + 12), fy(896 + 11 * k), fh(96), fh(4), TRIM_LIGHT, cv.clear, 0, radius=0)
    cv.rect(g, fx(372), fy(892), fh(170), fh(92), TRIM, TRIM_LIGHT, FINE_W, radius=fh(12))
    cv.rect(g, fx(436), fy(916), fh(44), fh(12), TRIM_LIGHT, cv.clear, 0, radius=fh(6))


@register("prop", "toon-steering-wheel", summary="A plain round steering wheel, front on, three spokes and no badge")
def steering_wheel(cv: Canvas, parent, at: Point = (165.0, 850.0), radius: float = 122.0) -> None:
    """The wheel centred on ``at``; a dashboard drawn after it hides its foot."""
    if not (checks.number(radius) and radius > 0):
        raise ToonDataError(f"a wheel's radius is over 0, got {radius!r}")
    x, y = at
    g = cv.group(parent, cv.uid("g"))
    for dx, dy in ((-1.0, 0.0), (1.0, 0.0), (0.0, 1.0)):
        cv.path(g, f"M {fx(x):.1f} {fy(y):.1f} L {fx(x + dx * radius):.1f} {fy(y + dy * radius):.1f}",
                fill=cv.clear, stroke=TRIM_DARK, sw=fh(30))  # fmt: skip
    cv.ellipse(g, fx(x - radius), fy(y - radius), fh(2 * radius), fh(2 * radius), cv.clear, cv.ink, fh(34))
    cv.ellipse(g, fx(x - radius), fy(y - radius), fh(2 * radius), fh(2 * radius), cv.clear, TRIM_DARK, fh(26))
    cv.ellipse(g, fx(x - 38), fy(y - 30), fh(76), fh(60), TRIM, cv.ink, FINE_W)


def stroke_line(index: int) -> tuple[Point, Point]:
    """Where stroke ``index`` of a pad goes, from its foot to its top, as an offset from the pad's top-left corner.
    They run in fives, four up and the fifth across them, three fives to a row."""
    gate, stroke = index // 5, index % 5
    row, column = gate // PAD_GATES, gate % PAD_GATES
    left = 18.0 + column * (4 * STROKE_GAP + GATE_GAP)
    top = 38.0 + row * ROW_GAP
    if stroke == 4:
        return (left - 7.0, top + STROKE_H - 8.0), (left + 3 * STROKE_GAP + 7.0, top + 8.0)
    x = left + stroke * STROKE_GAP
    wobble = _WOBBLE[(gate + stroke) % len(_WOBBLE)]
    return (x - wobble, top + STROKE_H), (x + wobble, top)


@register(
    "prop", "toon-tally-pad", summary="A spiral pad on the dashboard that keeps a count in fives, stroke by stroke"
)
def tally_pad(
    cv: Canvas,
    parent,
    at: Point = (296.0, 800.0),
    count: int = 11,
    strokes: Sequence[float] = (),
    scale: float = 1.0,
    id: str = "tally-pad",
) -> None:
    """The pad with its top-left corner at ``at``, ``count`` strokes on it from the start and one more at each of
    ``strokes``, drawn ``scale`` times its size about that corner."""
    if not (isinstance(count, int) and 0 <= count):
        raise ToonDataError(f"a pad starts from a whole count, got {count!r}")
    if count + len(strokes) > PAD_MOST:
        raise ToonDataError(f"a page holds {PAD_MOST} strokes, got {count} and {len(strokes)} more")
    times = list(strokes)
    if not all(checks.number(t) and t >= 0 for t in times) or times != sorted(times):
        raise ToonDataError(f"a pad's strokes come at rising times from 0, got {times!r}")
    g = _scaled(cv, parent, at, scale, id)
    x, y = at
    cv.rect(g, fx(x), fy(y), fh(PAD_W), fh(PAD_H), PAPER, cv.ink, INK_W / 2, radius=fh(8))
    for k in range(9):
        cv.rect(g, fx(x + 14 + k * 23), fy(y - 10), fh(6), fh(26), RING, cv.ink, FINE_W / 3, radius=fh(3))
    for row in range(PAD_ROWS):
        rule = y + 38 + row * ROW_GAP + STROKE_H + 6
        cv.rect(g, fx(x + 8), fy(rule), fh(PAD_W - 16), fh(2), PAPER_LINE, cv.clear, 0, radius=0)
    marks = cv.group(g, f"{id}-marks")
    arrivals: list[float | None] = [None] * count
    for k, t in enumerate([*arrivals, *times]):
        timing = {} if t is None else {"start": t}
        stroke = cv.group(marks, f"{id}-stroke-{k}", **timing)
        foot, top = stroke_line(k)
        _line(cv, stroke, [(x + foot[0], y + foot[1]), (x + top[0], y + top[1])], 8.0, PENCIL)

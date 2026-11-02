"""An ice cream parlour for Toon: both sides of its counter, and what is handed across it.

:func:`parlour_front` is the customer's side, a shop window on the street with whatever :class:`~srstudio.toon_cars.
Passing` says going by; :func:`parlour_back` is the server's side, a wall of shelves under a picture board that has no
words on it. :func:`cone` draws a cone of one of :data:`FLAVOURS`, and :func:`toothpaste_cone` a cone nobody ordered.
:func:`held` is a forearm rising from behind a surface with a cone in its fist, in a shot that draws its ledge after
it, so an arm that sinks goes behind the counter. The counter itself is ``toon_house.ledge(cv, front, "parlour")``, and
:func:`case` the glass case set into it.

Nothing here carries a brand: the tube has no lettering. Every measure is a reference screen pixel
(:func:`srstudio.toon.fx`/``fy``). Traffic and held-arm keys use composition time; visibility uses parent time.
Bad input is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import _toon_social_contracts as tc
from . import checks, toon_cars
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy
from .toon_cars import Passing
from .toon_sets import _inked, _line

__all__ = ["FLAVOURS", "HELD", "case", "cone", "held", "parlour_back", "parlour_front", "toothpaste_cone"]

Point = tuple[float, float]

WALL = (("0", "#ffe9f0"), ("0.7", "#ffdbe6"), ("1", "#ffcfdd"))
TRIM, TRIM_DARK = "#8fe3c8", "#62c7a8"
SKY = (("0", "#8fd8f7"), ("0.7", "#c8eefc"), ("1", "#f0fbff"))
PAVEMENT, KERB, ROAD = "#efe6d6", "#d3c6b0", "#7b8290"
BUILDING, BUILDING_DARK, PANE = "#ffd9a0", "#f4b976", "#bfe7f4"
SHELF, SHELF_DARK = "#ffffff", "#e7d3da"
BOARD, BOARD_EDGE = "#fffaf0", "#f59ab5"
WAFER, WAFER_LINE = "#e9b66c", "#c08a42"
SCOOP = {"vanilla": "#fff3cf", "mint": "#a6f0cf"}
FLECK = "#5a3a2a"
PASTE, PASTE_BLUE, PASTE_RED = "#ffffff", "#54c6f2", "#ff6b6b"
TUBE, TUBE_BAND, CAP = "#f6f9fc", "#3f8fe0", "#2f6fc4"
FLAVOURS = tuple(SCOOP)
HELD = (*FLAVOURS, "toothpaste")
CASE_BACK, TUBS = "#d9f4f7", ("#fff3cf", "#a6f0cf", "#ff9db8", "#8a5a44", "#ffc978", "#b7a8ec")
ARM_W = 56.0  # a forearm's width
FIST = 34.0  # a fist's radius
ROAD_LINE = 700.0  # where a passing vehicle's wheels are, seen through the window
WINDOW = (46.0, 150.0, 500.0, 610.0)  # x, y, w, h
PASSING_SCALE = 0.7


def _colour(name: str, known: Sequence[str], what: str) -> None:
    if name not in known:
        raise ToonDataError(f"{what} is one of {list(known)}, got {name!r}")


def _point(at: object, what: str) -> Point:
    if not (isinstance(at, tuple) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"{what} is an (x, y), got {at!r}")
    return at


def _scale(scale: object) -> float:
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a scale is over 0, got {scale!r}")
    return float(scale)


def _wafer(cv: Canvas, g, x: float, y: float, s: float) -> None:
    """The wafer with its point at ``(x, y)``, cross-hatched inside its edges."""
    top = y - 150 * s

    def edge(side: float, t: float) -> Point:
        return x + side * 56 * s * (1 - t), top + 150 * s * t

    _inked(cv, g, [(x - 56 * s, top), (x + 56 * s, top), (x, y)], WAFER, steps=1)
    for t in (0.08, 0.3, 0.52):
        _line(cv, g, [edge(-1, t), edge(1, t + 0.36)], 3.0, WAFER_LINE)
        _line(cv, g, [edge(1, t), edge(-1, t + 0.36)], 3.0, WAFER_LINE)


@register(
    "prop",
    "toon-cone",
    contract=tc.contract('toon-cone'),
    summary="An ice cream cone with one big scoop on it, vanilla or mint with chips",
)
def cone(cv: Canvas, parent, at: Point = (296.0, 760.0), flavour: str = "vanilla", scale: float = 1.0):
    """A cone of ``flavour`` with its point at ``at``; returns the group, whose keys move the whole cone."""
    x, y = _point(at, "a cone's point")
    s = _scale(scale)
    _colour(flavour, FLAVOURS, "a cone's flavour")
    g = cv.group(parent, cv.uid("g"))
    top = y - 150 * s
    cv.ellipse(g, fx(x - 74 * s), fy(top - 112 * s), fh(148 * s), fh(138 * s), SCOOP[flavour], cv.ink, INK_W)
    cv.ellipse(g, fx(x - 46 * s), fy(top - 94 * s), fh(38 * s), fh(24 * s), "#ffffff", opacity=0.7)
    if flavour == "mint":
        for dx, dy in ((-34, -44), (8, -74), (38, -32), (-6, -22), (-44, -14), (30, -8)):
            cv.rect(g, fx(x + dx * s), fy(top + dy * s), fh(16 * s), fh(9 * s), FLECK, radius=fh(3))
    _wafer(cv, g, x, y, s)
    return g


@register(
    "prop",
    "toon-toothpaste-cone",
    contract=tc.contract('toon-toothpaste-cone'),
    summary="A cone with a swirl of striped toothpaste and the tube stuck in it",
)
def toothpaste_cone(cv: Canvas, parent, at: Point = (296.0, 760.0), scale: float = 1.0):
    """A cone with a striped toothpaste swirl where the scoop should be and the blank tube upended in its top, its
    point at ``at``; returns the group."""
    x, y = _point(at, "a cone's point")
    s = _scale(scale)
    g = cv.group(parent, cv.uid("g"))
    top = y - 150 * s
    px, py = fx(x), fy(top - 120 * s)
    tube = cv.group(g, cv.uid("g"), rotation=14.0, x=px, y=py, anchorX=px, anchorY=py)
    _inked(cv, tube, [(x - 30 * s, top - 150 * s), (x + 30 * s, top - 150 * s), (x + 46 * s, top - 262 * s),
                      (x - 46 * s, top - 262 * s)], TUBE, steps=1)  # fmt: skip
    cv.rect(tube, fx(x - 37 * s), fy(top - 226 * s), fh(74 * s), fh(30 * s), TUBE_BAND)
    cv.rect(tube, fx(x - 50 * s), fy(top - 276 * s), fh(100 * s), fh(18 * s), TUBE, cv.ink, FINE_W, radius=fh(3))
    cv.rect(tube, fx(x - 22 * s), fy(top - 158 * s), fh(44 * s), fh(30 * s), CAP, cv.ink, FINE_W, radius=fh(6))
    for wide, rise, tall in ((156, -44, 56), (118, -92, 52), (78, -134, 48)):
        left, up = x - wide / 2 * s, top + rise * s
        cv.rect(g, fx(left), fy(up), fh(wide * s), fh(tall * s), PASTE, cv.ink, INK_W, radius=fh(tall / 2 * s))
        cv.rect(g, fx(left + 8 * s), fy(up + 12 * s), fh((wide - 16) * s), fh(9 * s), PASTE_BLUE, radius=fh(4))
        cv.rect(g, fx(left + 8 * s), fy(up + tall * 0.58 * s), fh((wide - 16) * s), fh(9 * s), PASTE_RED, radius=fh(4))
    _wafer(cv, g, x, y, s)
    return g


@register(
    "prop",
    "toon-parlour-case",
    contract=tc.contract('toon-parlour-case'),
    summary="The glass case under a parlour counter, with six tubs of ice cream in it",
)
def case(cv: Canvas, parent, top: float = 892.0):
    """The counter front's glass case, its top edge at ``top``, drawn after the ledge; returns the group."""
    if not checks.number(top):
        raise ToonDataError(f"a case's top is a number, got {top!r}")
    g = cv.group(parent, cv.uid("g"))
    x, wide, high = 40.0, 520.0, 170.0
    cv.rect(g, fx(x), fy(top), fh(wide), fh(high), CASE_BACK, cv.ink, INK_W, radius=fh(10))
    step = (wide - 28) / len(TUBS)
    for k, colour in enumerate(TUBS):
        left = x + 14 + k * step
        cv.ellipse(g, fx(left + 6), fy(top + 40), fh(step - 12), fh(64), colour, cv.ink, FINE_W)
        cv.rect(g, fx(left + 2), fy(top + 74), fh(step - 4), fh(78), SHELF, cv.ink, FINE_W, radius=fh(5))
        cv.rect(g, fx(left + 2), fy(top + 96), fh(step - 4), fh(24), colour, cv.ink, FINE_W)
    cv.rect(g, fx(x + 30), fy(top + 12), fh(120), fh(10), "#ffffff", opacity=0.6, radius=fh(5))
    return g


def _flavoured(cv: Canvas, parent, kind: str, at: Point, scale: float):
    return toothpaste_cone(cv, parent, at, scale) if kind == "toothpaste" else cone(cv, parent, at, kind, scale)


def _forearm(root: Point, wrist: Point, s: float) -> list[Point]:
    """The outline of a forearm that bows a little from a round elbow at ``root``, narrowing to ``wrist``."""
    bx, by = root
    x, y = wrist
    long = math.hypot(x - bx, y - by)
    ux, uy = (x - bx) / long, (y - by) / long
    nx, ny = -uy, ux
    elbow, wrist_half = ARM_W * 0.62 * s, ARM_W * 0.4 * s

    def on(along: float, side: float) -> Point:
        return bx + ux * along + nx * side, by + uy * along + ny * side

    bow = long * 0.05
    near = [
        on(k * long, -(elbow + (wrist_half - elbow) * k) - bow * math.sin(k * math.pi)) for k in (0.0, 0.35, 0.7, 1.0)
    ]
    far = [on(k * long, elbow + (wrist_half - elbow) * k - bow * math.sin(k * math.pi)) for k in (1.0, 0.7, 0.35, 0.0)]
    cap = [on(-elbow * math.sin(a), -elbow * math.cos(a)) for a in (2.4, 1.6, 0.8)]
    return [*near, *far, *cap]


def held(
    cv: Canvas,
    parent,
    spans: Sequence[tuple[float, float, str]],
    root: Point,
    at: Point,
    coat: str,
    hand: str,
    start: float,
    end: float,
    scale: float = 1.0,
    swings: Sequence[tuple[float, float]] = (),
):
    """A forearm of ``coat`` from ``root``, where a resting paw is, up to a ``hand`` at ``at``, from ``start`` to
    ``end``, with the cone each ``(from, to, kind)`` of ``spans`` names on it. ``swings`` are ``(t, degrees)`` keys of
    the whole arm about ``root``, clockwise: a shot that draws its ledge after this hides an arm swung down behind it.
    Returns the arm's group."""
    bx, by = _point(root, "an arm's root")
    x, y = _point(at, "a fist")
    s = _scale(scale)
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"an arm is held over 0 <= start < end, got {start!r}..{end!r}")
    if math.hypot(x - bx, y - by) < ARM_W:
        raise ToonDataError(f"an arm is longer than it is wide, got {root!r} to {at!r}")
    g = cv.group(parent, cv.uid("g"), start=start, end=end, x=fx(bx), y=fy(by), anchorX=fx(bx), anchorY=fy(by))
    if swings:
        cv.keys(g, "rotation", sorted(swings), hold=False, kind="cubic-in-out", local=False)
    for a, b, kind in spans:
        _colour(kind, HELD, "what an arm holds")
        if not (checks.number(a) and checks.number(b) and a < b):
            raise ToonDataError(f"a cone is held over from < to, got {a!r}..{b!r}")
        _flavoured(cv, cv.group(g, cv.uid("g"), start=a, end=b), kind, (x, y + 14 * s), s)
    _inked(cv, g, _forearm((bx, by), (x, y), s), coat, steps=2)
    r = FIST * s
    cv.ellipse(g, fx(x - r), fy(y - r), fh(2 * r), fh(2 * r), hand, cv.ink, INK_W)
    for k in (-0.45, 0.05, 0.55):
        _line(cv, g, [(x + k * r - 8 * s, y - 0.1 * r), (x + k * r + 8 * s, y + 0.1 * r)], 3.0, "#ffffff", 0.5)
    return g


def _paint(cv: Canvas, name: str, stops) -> str:
    return cv.grad(name, [(float(o), c) for o, c in stops], (0, 0, 0, 1))


def _awning(cv: Canvas, g, y: float) -> None:
    """A scalloped pink and mint trim right across the frame, its top at ``y``."""
    cv.rect(g, 0, fy(y), cv.width, fh(46), TRIM)
    for k in range(9):
        left = k * 74.0 - 14.0
        colour = TRIM if k % 2 else "#f59ab5"
        cv.rect(g, fx(left), fy(y), fh(74), fh(46), colour)
        cv.ellipse(g, fx(left), fy(y + 22), fh(74), fh(50), colour)


@register(
    "location",
    "toon-parlour-front",
    contract=tc.contract('toon-parlour-front'),
    summary="An ice cream parlour from behind its counter: pink walls and a shop window on a street, traffic going by",
)
def parlour_front(
    cv: Canvas,
    parent,
    start: float = 0.0,
    end: float = 4.0,
    passing: Sequence[Passing] = (),
    scale: float = PASSING_SCALE,
) -> None:
    """The customer's side: the street, each of ``passing`` going by it, and the wall round the window."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a parlour's street runs over 0 <= start < end, got {start!r}..{end!r}")
    g = cv.group(parent, cv.uid("g"))
    x, y, w, h = WINDOW
    cv.rect(g, 0, 0, cv.width, cv.height, _paint(cv, "toon-parlour-sky", SKY))
    for left, up, wide in ((60, 300, 150), (230, 240, 170), (420, 320, 170)):
        cv.rect(g, fx(left), fy(up), fh(wide), fh(ROAD_LINE - up), BUILDING, cv.ink, FINE_W)
        cv.rect(g, fx(left), fy(up), fh(wide), fh(20), BUILDING_DARK)
        for row in range(3):
            for col in range(2):
                cv.rect(g, fx(left + 22 + col * 66), fy(up + 44 + row * 92), fh(44), fh(60), PANE, cv.ink, FINE_W * 0.5)
    cv.rect(g, 0, fy(ROAD_LINE - 90), cv.width, fh(70), ROAD)
    for vehicle in passing:
        toon_cars.drive_past(cv, g, vehicle, ROAD_LINE - 30.0, scale)
    cv.rect(g, 0, fy(ROAD_LINE - 24), cv.width, fh(16), KERB)
    cv.rect(g, 0, fy(ROAD_LINE - 8), cv.width, fh(400), PAVEMENT)
    # the wall, as four panels round the glass, so what passes shows through it
    wall = cv.group(g, cv.uid("g"))
    paint = WALL[0][1]
    cv.rect(wall, 0, 0, cv.width, fy(y), paint)
    cv.rect(wall, 0, fy(y), fx(x), cv.height, paint)
    cv.rect(wall, fx(x + w), fy(y), cv.width - fx(x + w), cv.height, paint)
    cv.rect(wall, 0, fy(y + h), cv.width, cv.height - fy(y + h), paint)
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), cv.clear, cv.ink, INK_W, radius=fh(10))
    cv.rect(g, fx(x + w / 2 - 6), fy(y), fh(12), fh(h), "#ffffff", cv.ink, FINE_W)
    _awning(cv, g, 86.0)


@register(
    "location",
    "toon-parlour-back",
    contract=tc.contract('toon-parlour-back'),
    summary="An ice cream parlour from the customer's side: shelves of cones under a picture board with no words on it",
)
def parlour_back(cv: Canvas, parent) -> None:
    """The server's side: the wall, the picture board and two shelves of cones and tubs."""
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, _paint(cv, "toon-parlour-wall", WALL))
    _awning(cv, g, 86.0)
    cv.rect(g, fx(70), fy(170), fh(452), fh(190), BOARD, BOARD_EDGE, fh(10), radius=fh(18))
    for k, kind in enumerate(("vanilla", "mint", "vanilla")):
        cone(cv, g, (146.0 + k * 150.0, 346.0), kind, 0.58)
    for up in (500.0, 660.0):
        cv.rect(g, fx(40), fy(up), fh(512), fh(16), SHELF, cv.ink, FINE_W)
        cv.rect(g, fx(40), fy(up + 16), fh(512), fh(8), SHELF_DARK)
        for k in range(5):
            left = 62.0 + k * 96.0
            colour = ("#ffd166", "#ff9ab8", "#8fe3c8", "#b9a7f2", "#ffb07a")[(k + int(up)) % 5]
            cv.rect(g, fx(left), fy(up - 66), fh(70), fh(66), colour, cv.ink, FINE_W, radius=fh(8))
            cv.rect(g, fx(left - 4), fy(up - 74), fh(78), fh(14), "#ffffff", cv.ink, FINE_W, radius=fh(4))

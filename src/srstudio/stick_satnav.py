"""The Stick style's road ahead and the phone that gives directions on it.

:func:`ahead` is the view from the driver's seat, with a surface of ``street``, ``gravel`` or ``grass`` running at the
camera, and shaking the frame as the ground gets worse; with ``fence`` it comes up to a wooden fence and stops there.
:func:`nav_insert` is the phone in its mount, filling the frame: an invented map, a route, and one instruction from
:data:`SCREENS`. :data:`POSES` adds to :data:`srstudio.stick_windshield.FRONT` a passenger pointing across the driver.
Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import checks, signature
from .canvas import Canvas
from .registry import register
from .stick import Gradient, RigPose, StickDataError, _group, _seat, box, oval, paint, shape
from .stick_windshield import FRONT

__all__ = ["POSES", "SCREENS", "SURFACES", "VANISH", "ahead", "nav_insert"]

HORIZON = 900
VANISH = (540.0, float(HORIZON))
SURFACES = ("street", "gravel", "grass")
GROW = 1.45  # each mark on the ground is this much nearer than the next: one growth is one mark passing
MARKS = range(-1, 8)  # from under the car out to the horizon
NEAR = 620.0  # how far below the horizon mark 0 sits
RATE = {"street": 3.0, "gravel": 2.4, "grass": 1.8}  # marks passing a second
SHAKE = {"street": 0.0, "gravel": 7.0, "grass": 13.0}  # pixels the frame jumps as the ground gets worse
SHAKE_RATE = 12  # jumps a second
EDGE = {"street": 520.0, "gravel": 400.0}  # half the surface's width at the bottom of the frame
FENCE_FROM, FENCE_AT = 0.3, 1.0  # the fence's size as it comes into sight and when the car stops at it
SKY_TOP, SKY_LOW, FAR_FIELD, FIELD, FIELD_LOW = "#83bde4", "#dcefee", "#a9c48f", "#93b277", "#7fa064"
STREET, LINE, GRAVEL, GRAVEL_LOW, STONE, TUFT, TUFT_DARK = (
    "#7f8489",
    "#f2efe6",
    "#c9b793",
    "#b49f78",
    "#8f7f62",
    "#6c9150",
    "#55763e",
)
RAIL, RAIL_DARK = "#a57f54", "#7c5c3a"
DASH_TOP, DASH_LOW, TRIM, PILLAR = "#4c5059", "#30333a", "#6a6f7a", "#3e424b"
SCREEN_W, SCREEN_H = 560, 890  # the phone's screen on the frame
SCREEN_X, SCREEN_Y = (1080 - SCREEN_W) // 2, 545
MAP_LAND, MAP_ROAD, MAP_WATER, ROUTE, CARD = "#ece8dc", "#fbfaf5", "#a9d0de", "#b5532f", "#e3b23c"
PIN, COUCH, COUCH_DARK = "#d6453c", "#b9743c", "#8e5427"
CARD_H, CARD_GAP = 330, 18  # the instruction's card over the foot of the map, for an icon and two lines of words
CARD_X, CARD_Y, CARD_W = SCREEN_X + CARD_GAP, SCREEN_Y + SCREEN_H - CARD_H - CARD_GAP, SCREEN_W - 2 * CARD_GAP
ROUTE_FROM = CARD_Y - 70  # where the route leaves the car, the location dot on it, clear of the card
SPIN_STEPS, SPIN_RATE = 8, 1.5  # the recalculating ring's drawn steps, and turns a second


@dataclass(frozen=True)
class Screen:
    """One instruction: ``words`` on the card, what the map shows (``route`` of ``straight``, ``lost`` or ``end``)
    and ``icon`` (``arrow``, ``spin``, ``flag``, ``fence``, ``couch``)."""

    words: str
    route: str
    icon: str


SCREENS = {
    "straight": Screen("CONTINUE STRAIGHT", "straight", "arrow"),
    "recalculating": Screen("RECALCULATING", "lost", "spin"),
    "apologize": Screen("IN 200 FT: APOLOGIZE", "lost", "flag"),
    "fence": Screen("AT THE FENCE", "lost", "fence"),
    "couch": Screen("ARRIVE: THE COUCH", "end", "couch"),
}

POSES: dict[str, RigPose] = {
    **FRONT,
    "point": _seat((548, 930), (542, 1037), (540, 1420), ((510, 1480), (570, 1480)), ((500, 1700), (580, 1700)),
                   ((470, 1232), (712, 1062)), ((500, 1330), (880, 972))),
}  # fmt: skip


def _check_end(end: float, what: str) -> None:
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"the {what} needs a positive shot length, got {end!r}")


def _depth(k: int) -> float:
    return NEAR * GROW**-k


def _dash(k: int) -> str:
    d, far = _depth(k), _depth(k) * 0.82
    x, y = VANISH
    return (f"M {x - 0.022 * d:.2f} {y + d:.2f} L {x + 0.022 * d:.2f} {y + d:.2f} "
            f"L {x + 0.018 * far:.2f} {y + far:.2f} L {x - 0.018 * far:.2f} {y + far:.2f} Z")  # fmt: skip


def _marks(cv: Canvas, parent, surface: str) -> None:
    """What passes on ``surface``, built so one growth by :data:`GROW` lands on the same drawing."""
    x, y = VANISH
    for k in MARKS:
        d = _depth(k)
        if surface == "street":
            shape(cv, parent, _dash(k), LINE)
        elif surface == "gravel":
            for side, lane in ((-1, 0.14), (1, 0.27), (-1, 0.4), (1, 0.06)):
                size = max(2.0, 0.03 * d)
                oval(cv, parent, x + side * lane * d - size, y + d * (0.84 + lane / 2), size * 2, size, STONE)
        else:
            for side, lane in ((-1, 0.24), (1, 0.12), (-1, 0.62), (1, 0.5), (1, 0.86), (-1, 0.95)):
                tx, ty, h = x + side * lane * d, y + d * (0.8 + lane / 4), max(4.0, 0.16 * d)
                d_blades = (f"M {tx - h / 2:.2f} {ty:.2f} L {tx - h / 3:.2f} {ty - h:.2f} L {tx:.2f} {ty:.2f} "
                            f"L {tx + h / 3:.2f} {ty - h * 1.2:.2f} L {tx + h / 2:.2f} {ty:.2f} Z")  # fmt: skip
                shape(cv, parent, d_blades, TUFT if k % 2 else TUFT_DARK)


def _run(cv: Canvas, node, until: float, rate: float) -> None:
    """Grow ``node`` about the vanishing point by :data:`GROW` once per mark, and snap back, until ``until``."""
    period = 1 / rate
    passes = math.ceil(until * rate)
    keys: list[tuple[float, float]] = []
    for i in range(passes):
        keys += [(i * period, 1.0), ((i + 1) * period - 0.001, GROW)]
    keys.append((passes * period, 1.0))
    cv.keys(node, "scaleX", keys, hold=False)
    cv.keys(node, "scaleY", keys, hold=False)


def _fence(cv: Canvas, parent) -> None:
    """A wooden post-and-rail fence across the field, about the vanishing point, its posts standing on the horizon at
    full size. Drawn at the size it stops at."""
    y = VANISH[1] + 190
    for rail in (y - 250, y - 120):
        shape(cv, parent, f"M -500 {rail} L 1580 {rail}", sw=44, stroke=cv.ink)
        shape(cv, parent, f"M -500 {rail} L 1580 {rail}", sw=31, stroke=RAIL)
    for px in range(-400, 1500, 300):
        box(cv, parent, px - 30, y - 330, 60, 340, RAIL_DARK, 5, r=6)


def _surface(cv: Canvas, parent, surface: str) -> None:
    x, y = VANISH
    if surface == "grass":
        return
    bottom = EDGE[surface]
    fill = STREET if surface == "street" else GRAVEL
    shape(cv, parent, f"M {x - 12} {y} L {x + 12} {y} L {x + bottom} 1920 L {x - bottom} 1920 Z", fill)
    if surface == "gravel":
        shape(cv, parent, f"M {x - 4} {y} L {x + 4} {y} L {x + 70} 1920 L {x - 70} 1920 Z", GRAVEL_LOW)


def _cabin(cv: Canvas, parent) -> None:
    """The edge of the car around the view: the roof, the pillars and the dash, with the marks on it."""
    shape(cv, parent, "M 0 0 L 1080 0 L 1080 96 Q 540 44 0 96 Z", PILLAR, 5)
    shape(cv, parent, "M 0 96 L 56 80 L 0 1500 Z", PILLAR, 5)
    shape(cv, parent, "M 1080 96 L 1024 80 L 1080 1500 Z", PILLAR, 5)
    top = paint(cv, Gradient("nav-dash", ((0, DASH_TOP), (1, DASH_LOW)), 0, 1480, 0, 1920))
    shape(cv, parent, "M 0 1540 Q 540 1440 1080 1540 L 1080 1920 L 0 1920 Z", top, 5)
    shape(cv, parent, "M 30 1552 Q 540 1456 1050 1552", sw=3, stroke=TRIM)
    signature.cactus(cv, parent, 170, 1500, scale=0.5)
    signature.code(cv, parent, 760, 1520, 13, color="#d7dae0")  # on the dash, above the captions


@register("location", "stick-rough-road", tags=("car", "road", "gravel", "grass", "field", "fence", "driver", "view"))
def ahead(cv: Canvas, parent, end: float, *, surface: str = "street", fence: float | None = None) -> None:
    """The road from the driver's seat, ``surface`` running at the camera and the frame shaking as it gets worse; with
    ``fence`` (seconds into the shot) a wooden fence comes up across the field and the car stops at it then."""
    _check_end(end, "road ahead")
    if surface not in SURFACES:
        raise StickDataError(f"unknown surface {surface!r}; known: {', '.join(SURFACES)}")
    if fence is not None and not (checks.number(fence) and 0 < fence <= end):
        raise StickDataError(f"the fence is reached inside the shot (0..{end}), got fence={fence!r}")
    stops = fence if fence is not None else end
    x, y = VANISH
    view = _group(cv, parent)
    jump = SHAKE[surface]
    if jump:
        steps = int(stops * SHAKE_RATE)
        keys = [(k / SHAKE_RATE, jump * ((-1) ** k) * (0.6 + 0.4 * ((k * 7) % 3) / 2)) for k in range(steps)]
        cv.keys(view, "y", [*keys, (stops, 0.0)])
    sky = paint(cv, Gradient("nav-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, 0, 0, HORIZON))
    box(cv, view, -40, -40, cv.width + 80, HORIZON + 40, sky)
    for cx, cy, w in ((230, 320, 260), (780, 240, 340)):
        oval(cv, view, cx - w / 2, cy - w / 8, w, w / 4, "#fbfdff", opacity=0.9)
    box(cv, view, -40, HORIZON, cv.width + 80, 18, FAR_FIELD)
    ground = paint(cv, Gradient("nav-field", ((0, FIELD), (1, FIELD_LOW)), 0, HORIZON, 0, 1920))
    box(cv, view, -40, HORIZON + 18, cv.width + 80, 1100, ground)
    _surface(cv, view, surface)
    passing = _group(cv, view, anchorX=x, anchorY=y, x=x, y=y)
    _marks(cv, passing, surface)
    _run(cv, passing, stops, RATE[surface])
    if fence is not None:
        coming = _group(cv, view, anchorX=x, anchorY=y, x=x, y=y, scaleX=FENCE_FROM, scaleY=FENCE_FROM)
        keys = [(0.0, FENCE_FROM), (fence, FENCE_AT)]
        cv.keys(coming, "scaleX", keys, kind="cubic-out")
        cv.keys(coming, "scaleY", keys, kind="cubic-out")
        _fence(cv, coming)
    _cabin(cv, parent)


def _map(cv: Canvas, parent, screen: Screen) -> None:
    """The invented map: its streets, a lake, and the route as far as this instruction goes."""
    x, y, w, h = SCREEN_X, SCREEN_Y, SCREEN_W, SCREEN_H
    box(cv, parent, x, y, w, h, MAP_LAND)
    oval(cv, parent, x + 340, y + 250, 300, 380, MAP_WATER)
    for k in range(6):
        ry = y + 50 + k * 150
        shape(cv, parent, f"M {x} {ry} L {x + w} {ry + 30}", sw=26, stroke=MAP_ROAD)
    for k in range(4):
        rx = x + 80 + k * 150
        shape(cv, parent, f"M {rx} {y} L {rx + 40} {y + h}", sw=26, stroke=MAP_ROAD)
    cx, base = x + w / 2, ROUTE_FROM
    if screen.route == "straight":
        shape(cv, parent, f"M {cx} {base} L {cx} {y + 70}", sw=30, stroke=ROUTE)
    elif screen.route == "lost":
        shape(cv, parent, f"M {cx - 170} {base} L {cx - 150} {y + 260}", sw=30, stroke=ROUTE)
        d = f"M {cx - 150} {y + 260} Q {cx - 40} {y + 210} {cx + 30} {y + 140}"
        shape(cv, parent, d, sw=12, stroke=PIN)
        cx, base = cx + 30, y + 140
    else:
        shape(cv, parent, f"M {cx} {base} Q {cx - 140} {y + 260} {cx} {y + 120}", sw=30, stroke=ROUTE)
    oval(cv, parent, cx - 30, base - 30, 60, 60, ROUTE, stroke=cv.ink, sw=6)


def _arrow(cv: Canvas, parent, x: float, y: float, _end: float) -> None:
    shape(cv, parent, f"M {x} {y - 70} L {x + 60} {y + 2} L {x + 24} {y + 2} L {x + 24} {y + 70} L {x - 24} {y + 70} "
          f"L {x - 24} {y + 2} L {x - 60} {y + 2} Z", cv.ink)  # fmt: skip


def _spin(cv: Canvas, parent, x: float, y: float, end: float) -> None:
    ring = _group(cv, parent, x=x, y=y)
    for k in range(SPIN_STEPS):
        a = 2 * math.pi * k / SPIN_STEPS
        oval(cv, ring, 52 * math.cos(a) - 12, 52 * math.sin(a) - 12, 24, 24, cv.ink, opacity=0.25 + 0.75 * k / 7)
    step = 1 / (SPIN_STEPS * SPIN_RATE)
    cv.keys(ring, "rotation", [(k * step, k * 360 / SPIN_STEPS) for k in range(int(end / step) + 1)])


def _flag(cv: Canvas, parent, x: float, y: float, _end: float) -> None:
    shape(cv, parent, f"M {x - 40} {y + 70} L {x - 40} {y - 70}", sw=12, stroke=cv.ink)
    shape(cv, parent, f"M {x - 40} {y - 70} L {x + 60} {y - 36} L {x - 40} {y} Z", PIN)


def _gate(cv: Canvas, parent, x: float, y: float, _end: float) -> None:
    for rail in (y - 24, y + 28):
        shape(cv, parent, f"M {x - 84} {rail} L {x + 84} {rail}", sw=14, stroke=cv.ink)
    for px in (x - 60, x, x + 60):
        shape(cv, parent, f"M {px} {y - 66} L {px} {y + 66}", sw=14, stroke=cv.ink)


def _sofa(cv: Canvas, parent, x: float, y: float, _end: float) -> None:
    box(cv, parent, x - 80, y - 60, 160, 80, COUCH, 5, r=18)
    box(cv, parent, x - 100, y - 10, 200, 60, COUCH_DARK, 5, r=16)
    for side in (-1, 1):
        oval(cv, parent, x + side * 98 - 28, y - 22, 56, 70, COUCH, stroke=cv.ink, sw=5)
    shape(cv, parent, f"M {x - 76} {y + 50} L {x - 76} {y + 68} M {x + 76} {y + 50} L {x + 76} {y + 68}", sw=10)


ICONS = {"arrow": _arrow, "spin": _spin, "flag": _flag, "fence": _gate, "couch": _sofa}


@register("prop", "stick-nav-insert", tags=("car", "phone", "map", "navigation", "directions", "font", "insert"))
def nav_insert(cv: Canvas, parent, end: float, *, screen: str = "straight", buzz: Sequence[float] = ()) -> None:
    """The phone in its mount, filling the frame against the dash and the road: an invented map and one instruction
    from :data:`SCREENS`, shaking a little at each time in ``buzz`` (seconds on the shot clock)."""
    _check_end(end, "phone")
    if screen not in SCREENS:
        raise StickDataError(f"unknown screen {screen!r}; known: {', '.join(SCREENS)}")
    cv.require_font("the phone's instruction is set in it")
    if not all(checks.number(t) and 0 <= t < end for t in buzz):
        raise StickDataError(f"a buzz happens inside the shot (0..{end}), got {tuple(buzz)!r}")
    shown = SCREENS[screen]
    sky = paint(cv, Gradient("nav-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, 0, 0, HORIZON))
    box(cv, parent, 0, 0, cv.width, 1000, sky)
    box(cv, parent, 0, 1000, cv.width, 920, FIELD_LOW)
    _cabin(cv, parent)
    shape(cv, parent, "M 540 1480 L 540 1530", sw=54, stroke=cv.ink)
    shape(cv, parent, "M 540 1480 L 540 1530", sw=36, stroke=TRIM)
    phone = _group(cv, parent)
    if buzz:
        keys: list[tuple[float, float]] = [(0.0, 0.0)]
        for t in buzz:
            keys += [(t, 0.0), (t + 0.04, 9.0), (t + 0.08, -9.0), (t + 0.12, 6.0), (t + 0.16, 0.0)]
        cv.keys(phone, "x", keys, kind="linear")
    box(cv, phone, SCREEN_X - 26, SCREEN_Y - 44, SCREEN_W + 52, SCREEN_H + 100, "#1f2228", 6, r=56)
    screen_area = _group(cv, phone)
    screen_area.add_mask(type="path", path=f"M {SCREEN_X} {SCREEN_Y} h {SCREEN_W} v {SCREEN_H} h {-SCREEN_W} Z")
    _map(cv, screen_area, shown)
    box(cv, screen_area, CARD_X, CARD_Y, CARD_W, CARD_H, CARD, 5, r=28)
    ICONS[shown.icon](cv, screen_area, 540.0, CARD_Y + 92, end)
    cv.text(screen_area, cv.uid("nav-words"), shown.words, CARD_X + 6, CARD_Y + 170, CARD_W - 12, 150, 60,
            cv.ink, weight=700)  # fmt: skip

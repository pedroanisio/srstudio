"""The Stick style's car from the front: a two-shot through the windshield, the couple in the front seats.

The camera sits on the hood, looking in. :func:`windshield` is the back layer: the sky above the roof, the
headliner, the rear window with the road receding behind the car (its centre line and its poles shrink toward the
horizon, ``speed`` of them a second), the rear seat and the two front seats. A figure posed from :data:`FRONT`
sits in each, placed with ``at``: the passenger at :data:`PASSENGER_AT` on the left, the driver at
:data:`DRIVER_AT` on the right. :func:`dashboard` is drawn over them: the wheel in front of the driver, the
dashboard that hides the laps, the phone in a mount between the seats (it buzzes, and is put face down on the
dashboard), the glare on the glass, the wipers, the pillars and the hood. :data:`COUPLE` holds the couple's looks
under the short names a release's tags use. Everything is in frame pixels of the 1080 × 1920 Stick frame; the
faces sit above the word captions (:data:`srstudio.stick.WORD_Y`).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import checks, signature
from .canvas import Canvas
from .registry import register
from .stick import PLAIN, Gradient, Look, RigPose, StickDataError, _group, _seat, box, oval, paint, shape
from .stick_car import (
    DASH,
    DASH_LIGHT,
    FIELD,
    ROAD,
    ROOF_LIGHT,
    ROOF_SHADE,
    SEAT,
    SEAT_DEEP,
    SEAT_LIGHT,
    SEAT_SHADE,
    SKY_LOW,
    SKY_TOP,
    WHEEL,
    WHEEL_LIGHT,
    _lift,
)
from .stick_car import DASH_TOP as DASH_TOP_PAINT

__all__ = [
    "COUPLE",
    "DASH_TOP",
    "DRIVER_AT",
    "FRONT",
    "NOOR",
    "PASSENGER_AT",
    "REAR_WINDOW",
    "RECEDE",
    "WHEEL_AT",
    "WHEEL_R",
    "dashboard",
    "windshield",
]

BODY, BODY_LIGHT, BODY_SHADE = "#c46a4a", "#d98a68", "#9e5238"  # the car's paint
FIELD_FAR = "#a9c48f"  # the far fields along the horizon
DASH_TOP = 1290  # the dashboard's top edge across the cabin: what is below it is hidden
GLASS = "M 74 584 L 1006 584 L 1080 1462 L 0 1462 Z"  # the windshield, its frame drawn over its edge
REAR_WINDOW = "M 150 712 Q 158 668 214 664 L 866 664 Q 922 668 930 712 L 958 902 L 122 902 Z"
HORIZON = 792  # where the road behind meets the sky in the rear window
VANISH = (540.0, HORIZON)
RECEDE = 1.6  # each dash of the centre line is this much nearer than the next: one shrink is one dash passing
DASHES = range(-3, 11)  # the dashes drawn, from the nearest (below the window) to the horizon
NEAR = 130.0  # how far below the horizon dash 0 ends
SEATS = (310.0, 770.0)  # the front seats' centre lines: the passenger's, the driver's
PASSENGER_AT, DRIVER_AT = (SEATS[0] - 540, 0.0), (SEATS[1] - 540, 0.0)  # where a FRONT pose (centred on 540) sits
WHEEL_AT, WHEEL_R = (770.0, 1270.0), (170.0, 150.0)  # the wheel's centre and radii, face-on in front of the driver
PHONE = (502.0, 1120.0, 76.0, 136.0)  # the mounted phone's back: x, y, w, h, between the seats
LYING = (468.0, DASH_TOP - 16.0, 144.0, 18.0)  # the phone face down on the dashboard

NOOR = Look(hair="bun", glasses=True)  # the passenger: a bun and glasses
COUPLE: dict[str, Look] = {"dev": PLAIN, "noor": NOOR}  # the couple of The Exit, by their short names

# Front-facing seated poses, centred on x 540: place them with ``at`` = PASSENGER_AT or DRIVER_AT. The laps run
# under the dashboard; "drive" holds the wheel at ten and two from the driver's seat, "cite" lifts the near hand off
# it to count a point, "reach" stretches the passenger's near hand to the phone between the seats.
FRONT: dict[str, RigPose] = {
    "sit": _seat((540, 930), (540, 1037), (540, 1420), ((510, 1480), (570, 1480)), ((500, 1700), (580, 1700)),
                 ((470, 1232), (610, 1232)), ((500, 1330), (580, 1330))),
    "drive": _seat((540, 930), (540, 1037), (540, 1420), ((510, 1480), (570, 1480)), ((500, 1700), (580, 1700)),
                   ((396, 1252), (684, 1252)), ((410, 1174), (670, 1174))),
    "cite": _seat((532, 926), (538, 1035), (540, 1420), ((510, 1480), (570, 1480)), ((500, 1700), (580, 1700)),
                  ((396, 1252), (690, 1150)), ((410, 1174), (640, 1004))),
    "crossed": _seat((548, 934), (542, 1040), (540, 1420), ((510, 1480), (570, 1480)), ((500, 1700), (580, 1700)),
                     ((450, 1192), (630, 1192)), ((610, 1150), (470, 1150))),
    "reach": _seat((562, 936), (552, 1042), (540, 1420), ((510, 1480), (570, 1480)), ((500, 1700), (580, 1700)),
                   ((470, 1232), (680, 1162)), ((500, 1330), (770, 1196))),
    "slump": _seat((540, 962), (540, 1066), (540, 1420), ((510, 1480), (570, 1480)), ((500, 1700), (580, 1700)),
                   ((470, 1256), (610, 1256)), ((500, 1336), (580, 1336))),
}  # fmt: skip

BUZZ_MARKS = 0.35  # how long the buzz marks show
SHAKE = (0.05, -7.0), (0.1, 7.0), (0.15, -5.0), (0.2, 5.0), (0.25, 0.0)  # a buzz: (seconds in, x offset)


def _check_end(end: float, what: str) -> None:
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"the {what} needs a positive shot length, got {end!r}")


def _dash(k: int) -> str:
    """The ``k``-th dash of the centre line behind the car, as seen in the rear window: a thin quad from ``d`` to
    ``0.8 d`` below the horizon, ``d`` shrinking by :data:`RECEDE` per dash, so the drawing is the same after one
    shrink about the vanishing point."""
    d = NEAR * RECEDE**-k
    far = 0.8 * d
    x, y = VANISH
    return (f"M {x - 0.05 * d:.2f} {y + d:.2f} L {x + 0.05 * d:.2f} {y + d:.2f} L {x + 0.04 * far:.2f} {y + far:.2f} "
            f"L {x - 0.04 * far:.2f} {y + far:.2f} Z")  # fmt: skip


def _pole(k: int, side: int) -> str:
    """A roadside pole beside the ``k``-th dash: its foot off the road's edge, as tall as it is far below the
    horizon, so it shrinks with the dashes."""
    d = NEAR * RECEDE**-k
    x, y = VANISH[0] + side * 1.45 * d, VANISH[1]
    return f"M {x:.2f} {y + d:.2f} L {x:.2f} {y - 0.55 * d:.2f} M {x - side * 0.12 * d:.2f} {y - 0.48 * d:.2f} L {x:.2f} {y - 0.48 * d:.2f}"  # noqa: E501


def _recede(cv: Canvas, node, end: float, speed: float) -> None:
    """Shrink ``node`` about the vanishing point by :data:`RECEDE` once per dash, ``speed`` dashes a second, and
    snap it back: the road behind runs away from the car without end."""
    if not speed:
        return
    period = 1 / speed
    keys: list[tuple[float, float]] = []
    for i in range(math.ceil(end * speed)):
        keys += [(i * period, 1.0), ((i + 1) * period - 0.001, 1 / RECEDE)]
    keys.append((math.ceil(end * speed) * period, 1.0))
    cv.keys(node, "scaleX", keys, hold=False)
    cv.keys(node, "scaleY", keys, hold=False)


def _road(cv: Canvas, parent, end: float, speed: float) -> None:
    """What the rear window shows: the sky, the fields, the road narrowing to the horizon, and its centre line and
    poles receding."""
    g = _group(cv, parent)
    g.add_mask(type="path", path=REAR_WINDOW)
    sky = paint(cv, Gradient("ws-rear-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, 660, 0, HORIZON))
    box(cv, g, 100, 640, 880, HORIZON - 640, sky)
    box(cv, g, 100, HORIZON, 880, 920 - HORIZON, FIELD)
    shape(cv, g, f"M 100 {HORIZON} L 980 {HORIZON} L 980 {HORIZON + 14} L 100 {HORIZON + 14} Z", FIELD_FAR)
    x, y = VANISH
    shape(cv, g, f"M {x - 3} {y} L {x + 3} {y} L {x + 300} 920 L {x - 300} 920 Z", ROAD, 3, stroke=cv.ink)
    lines = _group(cv, g, anchorX=x, anchorY=y, x=x, y=y)
    for k in DASHES:
        shape(cv, lines, _dash(k), "#f2efe6")
        for side in (-1, 1):
            shape(cv, lines, _pole(k, side), sw=max(1.0, 0.06 * NEAR * RECEDE**-k), stroke=cv.ink)
    _recede(cv, lines, end, speed)


def _seat_back(cv: Canvas, parent, cx: float) -> None:
    """A front seat seen from ahead: the headrest on its posts behind the head, the back between its bolsters."""
    for dx in (-34, 34):
        box(cv, parent, cx + dx - 7, 880, 14, 60, "#9aa3b0", 3)
    rest = paint(cv, Gradient("ws-headrest", ((0, SEAT_LIGHT), (1, SEAT)), 0, 790, 0, 900))
    box(cv, parent, cx - 82, 796, 164, 104, rest, 5, r=40)
    back = paint(cv, Gradient("ws-seat-back", ((0, SEAT_LIGHT), (0.3, SEAT), (1, SEAT_SHADE)), 0, 930, 0, 1460))
    shape(cv, parent, f"M {cx - 150} 1460 L {cx - 156} 1000 Q {cx - 150} 936 {cx - 90} 932 L {cx + 90} 932 "
          f"Q {cx + 150} 936 {cx + 156} 1000 L {cx + 150} 1460 Z", back, 5)  # fmt: skip
    for dx in (-96, 96):
        shape(cv, parent, f"M {cx + dx} 960 L {cx + dx * 1.04} 1440", sw=3, stroke=SEAT_DEEP)


@register("location", "stick-windshield", tags=("car", "interior", "front", "two-shot", "rear-window", "road"))
def windshield(cv: Canvas, parent, end: float, *, speed: float = 2.5) -> None:
    """The car from its hood, the back layer: the sky above the roof, the headliner with its mirror, the rear window
    with the road receding behind the car (``speed`` dashes of its centre line a second; 0 for a parked car), the
    rear seat and the two front seats at :data:`SEATS`. Pose a figure from :data:`FRONT` in each, then draw
    :func:`dashboard` over them."""
    _check_end(end, "windshield")
    if not (checks.number(speed) and speed >= 0):
        raise StickDataError(f"the road's speed must be a non-negative number of dashes a second, got {speed!r}")
    s = cv
    sky = paint(s, Gradient("ws-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, 0, 0, 600))
    box(s, parent, 0, 0, s.width, 600, sky)
    for kx, ky, w in ((210, 210, 260), (760, 140, 320), (980, 330, 180)):  # a few still clouds
        oval(s, parent, kx - w / 2, ky - w / 8, w, w / 4, "#fbfdff", opacity=0.9)
    # the cabin seen through the glass: the headliner, the side walls and the rear window
    box(s, parent, 0, 580, s.width, 900, "#8f8170")
    roof = paint(s, Gradient("ws-headliner", ((0, ROOF_LIGHT), (1, ROOF_SHADE)), 0, 584, 0, 720))
    box(s, parent, 0, 584, s.width, 136, roof)
    shape(s, parent, REAR_WINDOW, s.clear, 7, stroke=s.ink)
    _road(s, parent, end, speed)
    shape(s, parent, REAR_WINDOW, sw=7, stroke=s.ink)
    rear = paint(s, Gradient("ws-rear-seat", ((0, SEAT_LIGHT), (1, SEAT_SHADE)), 0, 896, 0, 1000))
    shape(s, parent, "M 104 1000 L 112 914 Q 120 896 160 896 L 920 896 Q 960 896 968 914 L 976 1000 Z", rear, 4)
    for cx in SEATS:
        _seat_back(s, _group(s, parent, effects=_lift(s)), cx)
    # the rear-view mirror on its stem, between the heads
    shape(s, parent, "M 540 584 L 540 636", sw=10, stroke=s.ink)
    box(s, parent, 456, 630, 168, 52, "#3e424b", 4, r=16)
    box(s, parent, 468, 640, 144, 32, "#9fb6c4", 2, r=10)


def _check_phone(end: float, buzz: Sequence[float], down: float | None) -> None:
    if any(not (checks.number(t) and 0 <= t < end) for t in buzz) or list(buzz) != sorted(buzz):
        raise StickDataError(f"buzz times must be in order within the shot (0..{end}), got {list(buzz)!r}")
    if down is None:
        return
    if not (checks.number(down) and 0 < down < end):
        raise StickDataError(f"the phone is put down within the shot (0..{end}), got down={down!r}")
    if any(t >= down for t in buzz):
        raise StickDataError(f"a phone face down from {down} s cannot buzz in its mount at {list(buzz)!r}")


def _phone(cv: Canvas, parent, buzz: Sequence[float], down: float | None) -> None:
    """The phone between the seats: its back to the camera in a mount on the dashboard, shaking with buzz marks at
    each time in ``buzz``; from ``down`` it is gone from the mount and lies face down on the dashboard."""
    x, y, w, h = PHONE
    mounted = _group(cv, parent)
    shape(cv, mounted, f"M {x + w / 2} {y + h} L {x + w / 2} {DASH_TOP + 6}", sw=18, stroke=cv.ink)
    shape(cv, mounted, f"M {x + w / 2} {y + h} L {x + w / 2} {DASH_TOP + 6}", sw=8, stroke=WHEEL_LIGHT)
    case = _group(cv, mounted, x=x, y=y)
    box(cv, case, 0, 0, w, h, "#2b2e35", 5, r=16)
    box(cv, case, 12, 12, 26, 26, "#1b1d22", 2, r=8)  # the camera
    oval(cv, case, 19, 19, 12, 12, "#4a5568")
    if buzz:
        keys = [(0.0, x)]
        for t in buzz:
            keys += [(t, x), *((t + dt, x + dx) for dt, dx in SHAKE)]
        cv.keys(case, "x", keys, kind="linear")
        for t in buzz:
            marks = _group(cv, parent)
            cv.gate(marks, [(t, t + BUZZ_MARKS)])
            for side, mx in ((-1, x - 16), (1, x + w + 16)):
                shape(cv, marks, f"M {mx} {y + 30} Q {mx + side * 16} {y + h / 2} {mx} {y + h - 30}", sw=6,
                      stroke=cv.ink)  # fmt: skip
    if down is None:
        return
    cv.keys(mounted, "opacity", [(0.0, 1.0), (down, 0.0)])
    lying = _group(cv, parent)
    lx, ly, lw, lh = LYING
    shape(cv, lying, f"M {lx + 10} {ly} L {lx + lw - 10} {ly} L {lx + lw} {ly + lh} L {lx} {ly + lh} Z", "#2b2e35",
          4, stroke=cv.ink)  # fmt: skip
    cv.keys(lying, "opacity", [(0.0, 0.0), (down, 1.0)])


def _wheel(cv: Canvas, parent) -> None:
    """The steering wheel face-on: the rim with a lit edge, three spokes and the hub; its bottom goes behind the
    dashboard."""
    (cx, cy), (rx, ry) = WHEEL_AT, WHEEL_R
    g = _group(cv, parent, effects=_lift(cv))
    for ex, ey in ((-rx, 6), (rx, 6), (0, ry)):
        shape(cv, g, f"M {cx} {cy} L {cx + ex} {cy + ey}", sw=26, stroke=cv.ink)
        shape(cv, g, f"M {cx} {cy} L {cx + ex} {cy + ey}", sw=16, stroke=WHEEL_LIGHT)
    oval(cv, g, cx - 46, cy - 40, 92, 80, WHEEL, stroke=cv.ink, sw=5)
    cv.ellipse(g, cx - rx, cy - ry, 2 * rx, 2 * ry, cv.clear, stroke=cv.ink, sw=34)
    cv.ellipse(g, cx - rx, cy - ry, 2 * rx, 2 * ry, cv.clear, stroke=WHEEL, sw=22)
    shape(cv, g, f"M {cx - rx * 0.72:.1f} {cy - ry * 0.7:.1f} Q {cx} {cy - ry * 1.06:.1f} {cx + rx * 0.72:.1f} "
          f"{cy - ry * 0.7:.1f}", sw=5, stroke="#7b8290")  # fmt: skip


@register("prop", "stick-windshield-dash", tags=("car", "front", "dashboard", "steering-wheel", "phone", "buzz"))
def dashboard(
    cv: Canvas,
    parent,
    end: float,
    *,
    buzz: Sequence[float] = (),
    down: float | None = None,
    code: tuple[float, float, float, str] = (70, 1840, 9, BODY_SHADE),
) -> None:
    """What is between the camera and the couple of :func:`windshield`: the wheel in front of the driver, the
    dashboard across the cabin (its top at :data:`DASH_TOP`), the phone in its mount between the seats, buzzing at
    each time in ``buzz`` and put face down on the dashboard at ``down`` (seconds on the shot clock), the glare on
    the glass, the wipers, the pillars, the roof's edge and the hood. ``code`` is the signature code's x, y, height and
    colour, on the hood; a reel whose captions darken its foot lifts it clear (ADR 0001)."""
    _check_end(end, "dashboard")
    _check_phone(end, buzz, down)
    s = cv
    _wheel(s, parent)
    dash = _group(s, parent, effects=_lift(s))
    top = paint(s, Gradient("ws-dash", ((0, DASH_TOP_PAINT), (0.3, DASH), (1, "#3c4049")), 0, DASH_TOP, 0, 1470))
    shape(s, dash, f"M 0 {DASH_TOP + 18} Q 540 {DASH_TOP - 22} 1080 {DASH_TOP + 18} L 1080 1470 L 0 1470 Z", top, 5)
    shape(s, dash, f"M 20 {DASH_TOP + 24} Q 540 {DASH_TOP - 12} 1060 {DASH_TOP + 24}", sw=3, stroke=DASH_LIGHT)
    for vx in (430, 610):  # the centre vents
        box(s, dash, vx - 50, 1340, 100, 44, "#33363d", 4, r=12)
        for vy in (1352, 1366):
            shape(s, dash, f"M {vx - 38} {vy} L {vx + 38} {vy}", sw=4, stroke="#575c67")
    box(s, dash, 120, 1360, 220, 70, DASH_TOP_PAINT, 4, r=14)  # the glovebox
    signature.cactus(s, parent, 196, DASH_TOP + 8, scale=0.3)  # on the dashboard, the passenger's side (ADR 0001)
    _phone(s, parent, buzz, down)
    glare = _group(s, parent, blend="screen", opacity=0.16)
    glare.add_mask(type="path", path=GLASS)
    for x0 in (120, 330):
        shape(s, glare, f"M {x0} 584 L {x0 + 120} 584 L {x0 - 260} 1462 L {x0 - 380} 1462 Z", "#ffffff")
    for x0 in (140, 600):  # the wipers at rest along the glass's foot
        shape(s, parent, f"M {x0} 1452 L {x0 + 360} 1424", sw=12, stroke=s.ink)
        shape(s, parent, f"M {x0} 1452 L {x0 + 360} 1424", sw=5, stroke="#4b4f58")
    paint_body = paint(s, Gradient("ws-body", ((0, BODY_LIGHT), (1, BODY_SHADE)), 0, 1462, 0, 1920))
    shape(s, parent, "M 0 1462 L 1080 1462 L 1080 1920 L 0 1920 Z", paint_body, 5)  # the hood
    shape(s, parent, "M 540 1480 L 540 1920", sw=3, stroke=BODY_SHADE)
    shape(s, parent, "M 60 1520 Q 540 1490 1020 1520", sw=4, stroke=BODY_LIGHT)
    shape(s, parent, "M 0 520 L 74 584 L 0 1462 Z", BODY, 5)  # the pillars and the roof's front edge
    shape(s, parent, "M 1080 520 L 1006 584 L 1080 1462 Z", BODY, 5)
    shape(s, parent, "M 0 600 L 0 520 Q 40 486 160 480 L 920 480 Q 1040 486 1080 520 L 1080 600 L 1006 584 "
          "L 74 584 Z", BODY, 5)  # fmt: skip
    shape(s, parent, "M 120 500 Q 540 486 960 500", sw=4, stroke=BODY_LIGHT)
    shape(s, parent, GLASS, s.clear, 7, stroke=s.ink)
    x, y, height, colour = code
    signature.code(s, parent, x, y, height, color=colour)  # on the hood

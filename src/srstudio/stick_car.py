"""The Stick style's car: an interior seen from the passenger door, the country passing in the window, the driving
poses for :func:`srstudio.stick.rig`, the passenger seat in the foreground and what lies on it.

The car faces right. :func:`car` is the back layer: the headliner, the windows with six parallax layers of
scenery scrolling left behind the glass (clouds, mountains, hills, a row of houses and small trees, roadside trees
with utility poles and their wires, a guardrail), the door, the driver's seat and the dashboard. A figure posed from
:data:`DRIVING` sits in that seat; :func:`cockpit` is drawn over it: the knee panel that hides the legs under the
dash, the steering column and the wheel in front of the hands, the seatbelt across the chest of every pose, and the
shadows of the passing trees sweeping over the cabin. :func:`ride` bobs a node on the suspension. :func:`seat` is the
passenger seat drawn over the driver's lap, for a shot of what is on it, and :func:`laptop` stands on its cushion;
:func:`phone` sits in a mount on the windshield (:data:`MOUNT`). Everything is in frame pixels of the 1080 × 1920
Stick frame, drawn in the style's ink; nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import partial

from . import checks, look, signature
from .canvas import Canvas
from .registry import register
from .stick import (
    Gradient,
    RigKey,
    RigPose,
    StickDataError,
    _gate,
    _group,
    _seat,
    _spans,
    box,
    check_keys,
    oval,
    paint,
    shape,
)

__all__ = ["CUSHION", "DRIVING", "MOUNT", "SEAT_TOP", "Scroll", "car", "cockpit", "laptop", "phone", "ride", "seat"]

ROOF_LIGHT, ROOF_SHADE = "#e0d5bf", "#bcae93"
DOOR, DOOR_LIGHT, DOOR_SHADE, TRIM, CHROME = "#8f8170", "#a4957f", "#776a5b", "#b3a48c", "#d9dde3"
SEAT, SEAT_SHADE, SEAT_LIGHT, SEAT_DEEP = "#5d7397", "#4b5f80", "#7a92b8", "#425473"
DASH, DASH_TOP, DASH_LIGHT, WHEEL, WHEEL_LIGHT = "#4d525d", "#666c79", "#7b8290", "#2f323a", "#5d6370"
BELT, BELT_EDGE, BELT_LIGHT, BUCKLE = "#7d8796", "#2b2f36", "#a3acb9", "#c7ccd4"
SKY_TOP, SKY_LOW, CLOUD = "#7fb8d8", "#d4eaf2", "#fbfdff"
MOUNTAIN, MOUNTAIN_LINE, HILL, HILL_LINE = "#b3c9d6", "#93abb9", "#a6c48f", "#6f8a5c"
FIELD, VERGE, ROAD = "#93b277", "#7fa064", "#8a8f96"
TRUNK, LEAF, LEAF_DARK, PINE = "#7b5a3c", "#6f9c58", "#5a854a", "#4f7a4a"
HOUSE, HOUSE_ROOF, POLE, RAIL = "#e8dcc4", "#b8574a", "#7a6450", "#c9ced6"
SIDE_WINDOW = "M 64 352 Q 70 300 128 296 L 812 282 Q 852 282 870 312 L 948 908 L 64 922 Z"
WINDSHIELD = "M 924 280 L 1080 214 L 1080 904 L 1000 906 Z"
GLASS = SIDE_WINDOW + " " + WINDSHIELD
HORIZON = 742  # where the hills meet the fields in the window
NEAR = 906  # the roadside: where the near trees and poles stand
SEAT_TOP = 905  # the top of the passenger seat's back; what is above it shows the driver
CUSHION = 1290  # the passenger cushion's top edge, where props stand: above the Stick word captions
MOUNT = (862, 540)  # the top left of the phone in its windshield mount, beside the driver's view
TREE_GAP = 250  # the roadside trees' average spacing, in px
POLE_EVERY = 3  # a utility pole after every third roadside tree
WHEEL_AT, WHEEL_R, WHEEL_TILT = (690, 1060), (40, 170), -22  # the rim: centre, half-axes, lean back toward the driver
BELT_ANCHOR = (40, 860)  # where the shoulder strap leaves the door pillar
LAYERS = (  # (name, fraction of the roadside speed): the parallax, far to near
    ("clouds", 0.03),
    ("mountains", 0.07),
    ("hills", 0.18),
    ("middle", 0.42),
    ("roadside", 1.0),
    ("rail", 1.35),
)


@dataclass(frozen=True)
class Scroll:
    """How fast the roadside passes (px/s; farther layers move at their :data:`LAYERS` fraction) and where the
    scenery starts (px), so consecutive shots need not show the same trees."""

    speed: float = 520.0
    offset: float = 0.0

    def check(self) -> None:
        if not (checks.number(self.speed) and self.speed >= 0 and checks.number(self.offset)):
            raise StickDataError(f"scroll speed must be non-negative and offset finite, got {self!r}")


# Poses for the driver's seat of :func:`car`: the hands hold the wheel's rim, which leans back toward the driver;
# the shins run under the knee panel of :func:`cockpit`.
DRIVING: dict[str, RigPose] = {
    "drive": _seat((372, 900), (352, 1008), (300, 1338), ((540, 1300), (566, 1290)), ((585, 1640), (612, 1650)),
                   ((482, 1124), (500, 1104)), ((616, 931), (634, 902))),
    "grip": _seat((392, 896), (368, 1004), (302, 1338), ((540, 1300), (566, 1290)), ((585, 1640), (612, 1650)),
                  ((494, 1090), (512, 1078)), ((619, 912), (643, 907))),
    "one-hand": _seat((360, 896), (348, 1006), (298, 1338), ((540, 1300), (566, 1290)), ((585, 1640), (612, 1650)),
                      ((420, 1210), (500, 1104)), ((520, 1290), (634, 902))),
    "turn": _seat((350, 894), (346, 1006), (298, 1338), ((540, 1300), (566, 1290)), ((585, 1640), (612, 1650)),
                  ((482, 1124), (440, 1170)), ((616, 931), (560, 1250))),
}  # fmt: skip


# -- the scenery ------------------------------------------------------------------------------------------------
def _crown(cx: float, cy: float, r: float, lobes: int = 7) -> str:
    """A scalloped tree crown: ``lobes`` bumps around a circle of radius ``r``."""
    pts = []
    for k in range(lobes + 1):
        a = -math.pi / 2 + 2 * math.pi * k / lobes
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    for k in range(lobes):
        m = -math.pi / 2 + 2 * math.pi * (k + 0.5) / lobes
        c = (cx + 1.32 * r * math.cos(m), cy + 1.32 * r * math.sin(m))
        d += f" Q {c[0]:.1f} {c[1]:.1f} {pts[k + 1][0]:.1f} {pts[k + 1][1]:.1f}"
    return d + " Z"


def _pine(cx: float, base: float, h: float) -> str:
    """A pine of height ``h`` standing at ``base``: three stacked tiers."""
    d, w = "", h * 0.42
    for tier in range(3):
        top, bottom = base - h + tier * h * 0.24, base - h * 0.62 + tier * h * 0.26
        half = w * (0.55 + 0.25 * tier)
        d += f"M {cx:.1f} {top:.1f} L {cx + half:.1f} {bottom:.1f} L {cx - half:.1f} {bottom:.1f} Z "
    return d


def _ridge(start: float, end: float, base: float, step: float, heights: Sequence[float]) -> str:
    """A soft ridge from ``start`` to ``end`` above ``base``: peaks every ``step`` px cycling ``heights``."""
    d = f"M {start:g} {base:g}"
    x, k = start, 0
    while x < end:
        h = heights[k % len(heights)]
        d += f" Q {x + step / 2:g} {base - h:g} {x + step:g} {base - h * 0.35:g}"
        x += step
        k += 1
    return d + f" L {x:g} 1000 L {start:g} 1000 Z"


def _span(cv: Canvas, travel: float, fraction: float, offset: float) -> tuple[float, float]:
    """The x range a layer must cover so the window is never empty while it moves ``travel × fraction``."""
    return -300 - (offset * fraction) % 600, cv.width + travel * fraction + 300


def _scroll(cv: Canvas, node, end: float, distance: float) -> None:
    if distance:
        cv.keys(node, "x", [(0, 0), (end, -distance)], kind="linear")


def _scenery(cv: Canvas, parent, end: float, scroll: Scroll, passing: Sequence[float], defocus: float) -> None:
    """The country behind the glass, far to near, each layer scrolling left at its share of the speed: the far
    layers out of focus under a haze, the near ones motion-blurred by the engine, an oncoming car at each time in
    ``passing``, and the glass's glare over it all, all of it ``defocus``-blurred when that is set."""
    g = _group(cv, parent)
    g.add_mask(type="path", path=GLASS)
    focus = (
        dict(effects=cv.effect(f"car-defocus-{defocus:g}", "blur", radius=defocus), **look.sheet(cv)) if defocus else {}
    )
    g, glass = _group(cv, g, **focus), g  # the country rides on the suspension inside the still window
    ride(cv, g, end, amplitude=3.0, phase=2.0)

    # a rect paints in its own coordinates (see stick.Gradient): the sky box starts at y 200
    sky = paint(cv, Gradient("car-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, 20, 0, HORIZON - 200))
    box(cv, g, 0, 200, cv.width, 760, sky)
    travel, off = scroll.speed * end, scroll.offset

    def layer(name: str):  # the next layer up, far ones out of focus, near ones motion-blurred, scrolling
        fraction = dict(LAYERS)[name]
        if fraction < 0.25:
            radius = round(4 - 10 * fraction)
            node = _group(cv, g, effects=cv.effect(f"car-far-{radius}", "blur", radius=radius), **look.sheet(cv))
        else:
            node = _group(cv, g, motionBlur="on", shutterAngle=270)
        _scroll(cv, node, end, travel * fraction)
        return node, *_span(cv, travel, fraction, off)

    clouds, lo, hi = layer("clouds")
    for k, x in enumerate(range(int(lo), int(hi), 420)):
        cy = 400 + 46 * (k % 3)
        d = _crown(x, cy, 34 + 8 * (k % 2), 6) + " " + _crown(x + 52, cy + 8, 26, 6)
        shape(cv, clouds, d, CLOUD, 2.5, stroke="#c8dce8")
    mountains, lo, hi = layer("mountains")
    shape(cv, mountains, _ridge(lo, hi, HORIZON - 20, 260, (150, 96, 190, 120)), MOUNTAIN, 2.5, stroke=MOUNTAIN_LINE)
    haze = paint(cv, Gradient("car-haze", ((0, "#eef6f800"), (0.75, "#eef6f8"), (1, "#eef6f800")), 0, 0, 0, 190))
    box(cv, g, 0, HORIZON - 150, cv.width, 190, haze, opacity=0.55)
    hills, lo, hi = layer("hills")
    shape(cv, hills, _ridge(lo, hi, HORIZON + 12, 330, (74, 52, 90)), HILL, 3, stroke=HILL_LINE)
    box(cv, g, 0, HORIZON, cv.width, 260, FIELD)
    for y in (HORIZON + 34, HORIZON + 80):  # furrows of the field, still: they lie along the road
        shape(cv, g, f"M 0 {y} L {cv.width} {y + 6}", sw=3, stroke=VERGE, opacity=0.6)
    _middle(cv, *layer("middle"))
    roadside, lo, hi = layer("roadside")
    _roadside(cv, roadside, lo, hi, off)
    box(cv, g, 0, NEAR - 4, cv.width, 30, VERGE)
    for at in passing:  # on the far lane, behind the rail
        _oncoming(cv, g, at, end)
    rail, lo, hi = layer("rail")
    for x in range(int(lo), int(hi), 96):
        box(cv, rail, x, NEAR - 34, 12, 42, "#8e949c", 2.5)
    shape(cv, rail, f"M {lo:g} {NEAR - 30} L {hi:g} {NEAR - 30} L {hi:g} {NEAR - 14} L {lo:g} {NEAR - 14} Z", RAIL, 3)
    # the glass: two faint diagonal reflections over everything outside
    glare = _group(cv, glass, opacity=0.22, blend="screen", effects=cv.effect("car-glare", "blur", radius=10))
    shape(cv, glare, "M 180 300 L 300 300 L 120 922 L 0 922 Z", "#ffffff")
    shape(cv, glare, "M 360 300 L 400 300 L 220 922 L 180 922 Z", "#ffffff")


ONCOMING = 2600.0  # px/s: an oncoming car's speed across the window, ours and its own together
ONCOMING_PAINT = "#c0483a"


def _oncoming(cv: Canvas, parent, at: float, end: float) -> None:
    """An oncoming car crossing the window right to left, centred on it at ``at`` seconds, motion-blurred."""
    width = 520
    car = _group(cv, parent, motionBlur="on", shutterAngle=300, x=cv.width, y=NEAR - 30)
    shape(cv, car, "M 0 0 L 0 -70 Q 4 -96 40 -100 L 120 -104 L 190 -168 Q 210 -184 250 -184 L 400 -184 "
          "Q 440 -184 460 -160 L 500 -104 Q 520 -100 520 -70 L 520 0 Z", ONCOMING_PAINT, 5)  # fmt: skip
    shape(cv, car, "M 140 -106 L 202 -162 Q 214 -172 240 -172 L 300 -172 L 300 -106 Z", "#a9cbe0", 3)
    shape(cv, car, "M 316 -106 L 316 -172 L 396 -172 Q 424 -172 438 -154 L 476 -106 Z", "#a9cbe0", 3)
    shape(cv, car, "M 8 -60 L 512 -60", sw=3, stroke="#8e3329")
    for x in (110, 410):
        oval(cv, car, x - 46, -46, 92, 92, "#26282d", stroke=cv.shade, sw=5)
        oval(cv, car, x - 20, -20, 40, 40, "#9aa0a8")
    distance = cv.width + width  # from just off the right edge to just off the left
    start = at - distance / ONCOMING / 2
    a, b = max(0.0, start), min(end, start + distance / ONCOMING)
    cv.keys(car, "x", [(t, round(cv.width - ONCOMING * (t - start), 2)) for t in (a, b)], kind="linear")
    _gate(cv, car, a, b, end)


def _middle(cv: Canvas, parent, lo: float, hi: float) -> None:
    """A row of small farmhouses and trees on the far side of the field, thinner-lined for the distance."""
    x, k = lo, 0
    while x < hi:
        base = HORIZON + 26
        if k % 4 == 1:
            box(cv, parent, x - 34, base - 52, 68, 52, HOUSE, 2.5)
            shape(cv, parent, f"M {x - 44} {base - 50} L {x} {base - 84} L {x + 44} {base - 50} Z", HOUSE_ROOF, 2.5)
            box(cv, parent, x - 10, base - 38, 18, 18, "#7aa6c4", 2)
        else:
            r = 20 + 6 * (k % 3)
            box(cv, parent, x - 4, base - 30, 8, 30, TRUNK, 2)
            shape(cv, parent, _crown(x, base - 30 - r, r, 6), LEAF if k % 2 else LEAF_DARK, 2.5, stroke=HILL_LINE)
        k += 1
        x += 120 + 40 * (k % 3)


def _roadside(cv: Canvas, parent, lo: float, hi: float, offset: float) -> None:
    """Round trees and pines at the roadside, a utility pole after every :data:`POLE_EVERY` trees, wires between."""
    x, k, poles = lo - (offset % TREE_GAP), 0, []
    while x < hi:
        h = 150 + 46 * ((k * 7) % 3)  # a fixed rhythm of heights, nothing random to seed
        if k % 3 == 2:
            box(cv, parent, x - 9, NEAR - 40, 18, 40, TRUNK, 3)
            shape(cv, parent, _pine(x, NEAR - 30, h + 40), PINE, 4)
        else:
            r = 58 + 12 * ((k * 5) % 3)
            box(cv, parent, x - 11, NEAR - h, 22, h, TRUNK, 3.5)
            shape(cv, parent, f"M {x - 6} {NEAR - h + 30} L {x - 34} {NEAR - h - 10}", sw=7, stroke=TRUNK)
            shape(cv, parent, _crown(x, NEAR - h - 0.9 * r, r), LEAF if k % 2 else LEAF_DARK, 4)
        if k % POLE_EVERY == 1:
            px = x + TREE_GAP / 2
            box(cv, parent, px - 8, NEAR - 360, 16, 360, POLE, 3)
            box(cv, parent, px - 46, NEAR - 340, 92, 12, POLE, 3)
            poles.append(px)
        k += 1
        x += TREE_GAP + 50 * ((k * 3) % 3) - 50
    for a, b in zip(poles, poles[1:], strict=False):
        for dx, y in ((-40, NEAR - 334), (40, NEAR - 334)):
            shape(cv, parent, f"M {a + dx:g} {y} Q {(a + b) / 2 + dx:g} {y + 46} {b + dx:g} {y}", sw=2.5,
                  stroke="#3d3f44")  # fmt: skip


def _lift(cv: Canvas) -> str:
    """The soft shadow a part of the cabin casts on what is behind it, the light coming from the windows."""
    return cv.effect("car-lift", "drop-shadow", radius=16, offsetX=-8, offsetY=12, intensity=0.38)


def _sunk(cv: Canvas) -> str:
    """The shadow inside a recess: a pocket, a handle's cup, a speaker's grille."""
    return cv.effect("car-sunk", "inner-shadow", radius=10, offsetX=0, offsetY=8, intensity=0.55)


# -- the cabin --------------------------------------------------------------------------------------------------
@register("location", "stick-car", tags=("car", "interior", "driving", "window", "scrolling", "parallax"))
def car(
    cv: Canvas, parent, end: float, *, scroll: Scroll | None = None, passing: Sequence[float] = (), defocus: float = 0.0
) -> None:
    """A car's interior from the passenger door: the headliner with its grab handle, visor and mirror; the side
    window and the windshield with the country passing left in six parallax layers (``scroll``, over ``end``
    seconds); the door with its trim, armrest, handle, pocket and speaker; the driver's seat; the dashboard. Draw a
    figure posed from :data:`DRIVING` next, then :func:`cockpit` over it. An oncoming car passes at each time
    in ``passing`` (seconds into the shot). ``defocus`` blurs the whole country by that radius, for a close-up
    focused on the driver: the lens that magnifies the face magnifies the passing trees' contrast too."""
    scroll = scroll or Scroll()
    scroll.check()
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"the car needs a positive shot length, got {end!r}")
    if any(not (checks.number(t) and 0 <= t <= end) for t in passing):
        raise StickDataError(f"a passing car must pass within the shot (0..{end}), got {tuple(passing)}")
    if not (checks.number(defocus) and defocus >= 0):
        raise StickDataError(f"defocus must be a non-negative radius, got {defocus!r}")
    s = cv
    box(s, parent, 0, 0, s.width, s.height, DOOR)
    _scenery(s, parent, end, scroll, passing, defocus)
    # the headliner, the pillars and the window frames with their rubber seals
    roof = paint(s, Gradient("car-roof", ((0, ROOF_SHADE), (1, ROOF_LIGHT)), 0, 0, 0, 320))
    shape(s, parent, "M 0 0 L 1080 0 L 1080 214 L 924 280 L 870 312 Q 852 282 812 282 L 128 296 Q 70 300 64 352 "
          "L 64 922 L 0 930 Z", roof, 4)  # fmt: skip
    shape(s, parent, "M 0 0 L 1080 0 L 1080 96 Q 560 150 0 136 Z", ROOF_SHADE)
    shape(s, parent, "M 0 136 Q 560 150 1080 96", sw=3, stroke="#a8997e")
    shape(s, parent, "M 0 320 L 64 352 L 64 922 L 0 930 Z", ROOF_SHADE, 4)  # the door pillar
    box(s, parent, 18, BELT_ANCHOR[1] - 24, 44, 48, "#5a5f69", 3, r=8)  # the belt's guide on the pillar
    shape(s, parent, "M 870 312 L 924 280 L 1000 906 L 948 908 Z", ROOF_SHADE, 4)  # the windshield pillar
    shape(s, parent, SIDE_WINDOW, s.clear, 7, stroke=s.ink)
    shape(s, parent, "M 76 360 Q 82 312 132 308 L 810 294 Q 846 294 860 320 L 934 896 L 76 910 Z", sw=4,
          stroke="#3a3c42", opacity=0.5)  # fmt: skip
    shape(s, parent, WINDSHIELD, s.clear, 7, stroke=s.ink)
    # the grab handle above the window, the folded visor and the rear-view mirror on the windshield
    shape(s, parent, "M 400 250 L 404 274 Q 470 290 536 274 L 540 250", sw=14, stroke=s.ink)
    shape(s, parent, "M 400 250 L 404 274 Q 470 290 536 274 L 540 250", sw=8, stroke=TRIM)
    visor = _group(s, parent, x=880, y=170, rotation=-14)
    box(s, visor, 0, 0, 190, 54, ROOF_LIGHT, 4, r=18)
    shape(s, visor, "M 14 27 L 176 27", sw=2, stroke=ROOF_SHADE)
    shape(s, parent, "M 1040 222 L 1030 300", sw=10, stroke=s.ink)
    box(s, parent, 960, 296, 120, 54, "#3e424b", 4, r=16)
    box(s, parent, 972, 306, 96, 30, "#9fb6c4", 2, r=10)
    # the door: sill trim, a fabric insert, the armrest, the handle, the pocket and the speaker
    shape(s, parent, "M 0 930 L 1080 904 L 1080 1920 L 0 1920 Z", DOOR, 4)
    shape(s, parent, "M 0 930 L 1080 904 L 1080 948 L 0 976 Z", TRIM, 3)
    shape(s, parent, "M 0 936 L 1080 910", sw=3, stroke="#d2c6b0")
    shape(s, parent, "M 0 1000 L 1080 974 L 1080 1170 L 0 1196 Z", DOOR_LIGHT, 3)
    for y in (1012, 1184):
        shape(s, parent, f"M 0 {y} L 1080 {y - 26}", sw=2.5, stroke=DOOR_SHADE, dash=[10, 9])
    arm = _group(s, parent, effects=_lift(s))
    shape(s, arm, "M 0 1200 L 1080 1174 L 1080 1236 Q 1080 1250 1066 1252 L 0 1280 Z", TRIM, 4)  # armrest
    shape(s, arm, "M 0 1206 L 1080 1180", sw=3, stroke="#cdbfa6")
    recess = _group(s, parent, effects=_sunk(s))
    box(s, recess, 700, 1070, 110, 46, DOOR_SHADE, 3, r=20)  # the handle's recess and the chrome pull
    shape(s, parent, "M 712 1093 Q 755 1080 798 1093", sw=9, stroke=CHROME)
    shape(s, recess, "M 0 1540 L 1080 1500 L 1080 1600 L 0 1640 Z", DOOR_SHADE, 3)  # the map pocket
    shape(s, parent, "M 0 1540 L 1080 1500", sw=3, stroke="#b5a68d")
    spk = _group(s, _group(s, parent, effects=_sunk(s)), x=110, y=1760)
    oval(s, spk, -76, -76, 152, 152, "#5e5446", stroke=s.ink, sw=4)
    for r in (56, 36, 16):
        s.ellipse(spk, -r, -r, 2 * r, 2 * r, s.clear, stroke="#463e33", sw=3)
    box(s, parent, 0, 1860, s.width, 60, "#3b3530")  # the carpet
    # the driver's seat: headrest on its posts, a pleated back between bolsters, the cushion, the rails
    chair = _group(s, parent, effects=_lift(s))
    for x in (232, 296):
        box(s, chair, x, 760, 14, 70, "#9aa3b0", 3)
    box(s, chair, 196, 676, 150, 100, SEAT, 5, r=34)
    shape(s, chair, "M 212 700 Q 270 688 330 700", sw=4, stroke=SEAT_LIGHT)
    shape(s, chair, "M 150 880 Q 146 800 208 794 L 300 790 Q 352 792 356 850 L 344 1330 L 168 1342 Z", SEAT, 5)
    shape(s, chair, "M 196 840 Q 250 828 316 836 L 306 1300 L 206 1306 Z", SEAT_SHADE, 3)
    for y in range(900, 1300, 64):
        shape(s, chair, f"M 200 {y} L 312 {y - 4}", sw=3, stroke=SEAT_DEEP)
    shape(s, chair, "M 172 900 Q 176 830 210 824 L 224 824 L 210 1320 L 180 1324 Z", SEAT_LIGHT)
    shape(s, chair, "M 160 1300 L 548 1286 Q 590 1290 586 1334 L 572 1412 L 170 1426 Z", SEAT, 5)
    shape(s, chair, "M 470 1296 Q 560 1290 580 1330 L 570 1400 L 470 1408 Z", SEAT_LIGHT)  # the front bolster
    shape(s, chair, "M 176 1396 L 566 1384 L 566 1412 L 170 1426 Z", SEAT_SHADE)
    box(s, chair, 180, 1426, 360, 46, "#3a3f4a", 3)  # the base, its rail and the lever
    box(s, chair, 150, 1472, 440, 14, "#8e949c", 3)
    shape(s, chair, "M 470 1440 Q 520 1440 540 1462", sw=8, stroke=s.ink)
    # the dashboard: its top under the windshield, the hood over the instruments, a vent in its side
    dash = _group(s, parent, effects=_lift(s))
    shape(s, dash, "M 1080 880 L 960 894 Q 830 920 764 984 Q 742 1008 748 1048 L 760 1180 L 1080 1180 Z", DASH, 5)
    shape(s, dash, "M 1080 880 L 960 894 Q 830 920 764 984 Q 790 972 860 958 Q 960 940 1080 930 Z", DASH_TOP, 3)
    shape(s, dash, "M 764 984 Q 772 932 836 924 Q 886 920 904 944", DASH, 5)  # the instrument hood
    shape(s, dash, "M 776 972 Q 790 942 836 938", sw=3, stroke=DASH_LIGHT)
    box(s, dash, 962, 1010, 104, 66, "#33363d", 4, r=14)
    for y in (1026, 1042, 1058):
        shape(s, dash, f"M 974 {y} L 1054 {y}", sw=4, stroke="#575c67")
    signature.cactus(s, parent, 1012, 902, scale=0.3)  # on the dashboard, under the windshield (ADR 0001)
    signature.code(s, parent, 70, 1820, 9, color="#a99a85")  # on the door, by the carpet


def _rim(cv: Canvas, parent) -> None:
    """The steering wheel, seen from its side: a thick rim with a highlight, the hub and its two spokes."""
    (cx, cy), (rx, ry) = WHEEL_AT, WHEEL_R
    rim = _group(cv, parent, x=cx, y=cy, rotation=WHEEL_TILT)
    for k in (-1, 1):
        shape(cv, rim, f"M 0 0 L {-8 * k} {k * (ry - 20)}", sw=22, stroke=cv.ink)
        shape(cv, rim, f"M 0 0 L {-8 * k} {k * (ry - 20)}", sw=12, stroke=WHEEL_LIGHT)
    oval(cv, rim, -26, -34, 52, 68, WHEEL, stroke=cv.ink, sw=5)
    cv.ellipse(rim, -rx, -ry, 2 * rx, 2 * ry, cv.clear, stroke=cv.ink, sw=34)
    cv.ellipse(rim, -rx, -ry, 2 * rx, 2 * ry, cv.clear, stroke=WHEEL, sw=22)
    shape(cv, rim, f"M {-rx * 0.7:.1f} {-ry * 0.72:.1f} Q {-rx * 1.02:.1f} 0 {-rx * 0.7:.1f} {ry * 0.72:.1f}", sw=5,
          stroke=WHEEL_LIGHT)  # fmt: skip


def _belt(cv: Canvas, parent, pose: RigPose) -> None:
    """The shoulder strap from its guide on the door pillar over the shoulder, across the chest to the buckle by
    the hip, and the lap strap back from the buckle: a grey webbing with a dark edge and a lit fold."""
    nx, ny = pose.neck
    hx, hy = pose.hip
    shoulder = (nx - 6, ny + 30)
    buckle = (hx + 64, hy - 30)
    strap = (f"M {BELT_ANCHOR[0]} {BELT_ANCHOR[1]} L {shoulder[0]:g} {shoulder[1]:g} "
             f"Q {nx + 74:g} {(ny + hy) / 2:g} {buckle[0]:g} {buckle[1]:g} L {hx - 46:g} {hy + 2:g}")  # fmt: skip
    shape(cv, parent, strap, sw=24, stroke=BELT_EDGE)
    shape(cv, parent, strap, sw=16, stroke=BELT)
    shape(cv, parent, f"M {shoulder[0]:g} {shoulder[1] + 4:g} Q {nx + 68:g} {(ny + hy) / 2:g} {buckle[0] - 4:g} "
          f"{buckle[1] - 8:g}", sw=3, stroke=BELT_LIGHT)  # fmt: skip
    box(cv, parent, buckle[0] - 16, buckle[1] - 14, 34, 28, BUCKLE, 3, r=6)
    box(cv, parent, buckle[0] - 6, buckle[1] - 5, 14, 10, "#8c929b", r=2)


@register("prop", "stick-cockpit", tags=("car", "steering-wheel", "seatbelt", "shadows", "sunlight", "vignette"))
def cockpit(
    cv: Canvas,
    parent,
    keys: Sequence[RigKey],
    end: float,
    *,
    poses: Mapping[str, RigPose] = DRIVING,
    scroll: Scroll | None = None,
) -> None:
    """What is in front of the driver of :func:`car`: the knee panel under the dashboard (the shins go under it),
    the column with its indicator stalk, the wheel in front of the hands, the seatbelt across the chest of each
    key's pose (``keys`` as given to :func:`srstudio.stick.rig`), the soft shadows of the roadside trees sweeping
    across the cabin at the ``scroll`` speed, the late sun through the windshield and a vignette."""
    scroll = scroll or Scroll()
    scroll.check()
    check_keys(keys, end, poses)
    s = cv
    for k, a, b in _spans(keys, end):
        belt = _group(s, parent, effects=_lift(s))
        _belt(s, belt, poses[k.pose])
        _gate(s, belt, a, b, end)
    knee = _group(s, parent, effects=_lift(s))
    lower = paint(s, Gradient("car-knee", ((0, DASH_TOP), (0.35, DASH), (1, "#3c4049")), 0, 1150, 0, 1860))
    shape(s, knee, "M 624 1150 Q 566 1196 556 1290 L 548 1860 L 1080 1860 L 1080 1180 L 760 1180 Z", lower, 5)
    shape(s, knee, "M 624 1150 Q 566 1196 556 1290 L 578 1290 Q 590 1210 636 1168 Z", DASH_LIGHT)
    shape(s, knee, "M 576 1420 L 1080 1400", sw=3, stroke="#3d4149")
    box(s, knee, 660, 1460, 90, 54, "#3d4149", 3, r=10)  # the hood release
    column = _group(s, parent, effects=_lift(s))
    shape(s, column, "M 700 1060 L 862 1176 L 900 1150 L 742 1032 Z", "#3a3e47", 5)  # the column's shroud
    shape(s, column, "M 740 1060 L 806 1012", sw=12, stroke=s.ink)
    shape(s, column, "M 740 1060 L 806 1012", sw=6, stroke="#5a606c")
    _rim(s, _group(s, parent, effects=_lift(s)))
    # the trees' shadows: soft bands multiplied over the cabin (not the glass), passing at the roadside speed
    shade = _group(s, parent, opacity=0.22, blend="multiply", effects=s.effect("car-shade", "blur", radius=36))
    shade.add_mask(type="path", path=GLASS, invert=True)
    band = TREE_GAP * 1.6
    travel = scroll.speed * end
    x = -band - (scroll.offset % band)
    while x < s.width + travel + band:
        shape(s, shade, f"M {x:g} 200 L {x + 170:g} 200 L {x + 60:g} 1920 L {x - 110:g} 1920 Z", "#3b4a66")
        x += band
    _scroll(s, shade, end, travel)
    # the sun, low through the windshield, and the darkened corners
    sun = s.rgrad("car-sun", ((0, "#ffe2a8"), (0.45, "#ffd28a66"), (1, "#ffd28a00")), (0.5, 0.5, 0.5))
    oval(s, _group(s, parent, blend="screen", opacity=0.55), 560, -60, 760, 1100, sun)
    edge = s.rgrad("car-vignette", ((0, "#00000000"), (0.62, "#00000000"), (1, "#1a140f")), (0.5, 0.48, 0.72))
    box(s, _group(s, parent, blend="multiply", opacity=0.45), 0, 0, s.width, s.height, edge)


@register("prop", "stick-ride", tags=("car", "motion", "suspension"))
def ride(cv: Canvas, node, end: float, *, amplitude: float = 2.5, phase: float = 0.0, step: float = 1 / 12) -> None:
    """Bobs ``node`` up and down by up to ``amplitude`` px, as the road shakes the car: two incommensurate waves
    sampled at ``step`` (12 fps cartoon timing), shifted by ``phase`` radians so two nodes need not bob together,
    the same every time."""
    numbers = (amplitude, phase, step, end)
    if not (all(checks.number(v) for v in numbers) and amplitude >= 0 and step > 0 and end > 0):
        raise StickDataError(f"ride needs amplitude >= 0, step > 0 and a positive end, got {amplitude}, {step}, {end}")
    if amplitude == 0:
        return
    base = float(node.y or 0)
    n = max(1, math.ceil(end / step))
    values = [
        (
            round(i * step, 4),
            round(base + amplitude * (0.6 * math.sin(i * 1.7 + phase) + 0.4 * math.sin(i * 0.63 + 1)), 2),
        )
        for i in range(n + 1)
    ]
    cv.keys(node, "y", values, kind="linear")


@register("prop", "stick-car-seat", tags=("car", "seat", "foreground"))
def seat(cv: Canvas, parent) -> None:
    """The passenger seat, close to the camera and over the driver's lap: its back at the left edge (top at
    :data:`SEAT_TOP`, clear of the driver's head) with a pleated panel between bolsters, its headrest, and a long
    cushion whose top edge is :data:`CUSHION`, for things to stand on, stitched along its pleats."""
    s = cv
    g = _group(s, parent, effects=_lift(s))
    for x in (30, 130):
        box(s, g, x, SEAT_TOP - 110, 18, 120, "#9aa3b0", 3)
        shape(s, g, f"M {x + 4} {SEAT_TOP - 100} L {x + 4} {SEAT_TOP}", sw=3, stroke="#c9d0d9")
    rest = paint(s, Gradient("car-headrest", ((0, SEAT_LIGHT), (1, SEAT)), 0, 0, 0, 130))
    box(s, g, -20, SEAT_TOP - 250, 220, 160, rest, 6, r=50)
    shape(s, g, f"M 10 {SEAT_TOP - 214} Q 90 {SEAT_TOP - 236} 170 {SEAT_TOP - 214}", sw=4, stroke="#a9bddb")
    back = paint(s, Gradient("car-seat-back", ((0, SEAT_LIGHT), (0.25, SEAT), (1, SEAT_SHADE)), 0, SEAT_TOP, 0, 1540))
    shape(s, g, f"M -60 {SEAT_TOP + 60} Q -50 {SEAT_TOP - 10} 20 {SEAT_TOP} L 196 {SEAT_TOP} "
          f"Q 252 {SEAT_TOP + 10} 248 {SEAT_TOP + 100} L 232 1520 L -60 1540 Z", back, 6)  # fmt: skip
    shape(s, g, f"M 70 {SEAT_TOP + 70} Q 130 {SEAT_TOP + 56} 200 {SEAT_TOP + 70} L 190 1480 L 60 1490 Z",
          SEAT_SHADE, 3)  # fmt: skip
    for y in range(SEAT_TOP + 140, 1480, 70):
        shape(s, g, f"M 66 {y} Q 130 {y + 8} 194 {y - 4}", sw=3, stroke=SEAT_DEEP)
    shape(s, g, f"M -10 {SEAT_TOP + 60} Q 0 {SEAT_TOP + 20} 40 {SEAT_TOP + 20} L 56 {SEAT_TOP + 20} "
          f"L 44 1500 L 0 1504 Z", SEAT_LIGHT)  # fmt: skip
    shape(s, g, f"M 62 {SEAT_TOP + 74} L 56 1486", sw=2.5, stroke="#a9bddb", dash=[8, 8])
    top = paint(s, Gradient("car-cushion", ((0, SEAT_LIGHT), (0.4, SEAT), (1, SEAT)), 0, CUSHION - 20, 0, 1540))
    shape(s, g, f"M 170 {CUSHION + 10} L 1000 {CUSHION - 20} Q 1092 {CUSHION - 20} 1092 {CUSHION + 70} "
          f"L 1092 1540 L 170 1580 Z", top, 6)  # fmt: skip
    for x0, x1 in ((420, 400), (640, 640), (860, 880)):  # the pleats run toward the camera
        shape(s, g, f"M {x0} {CUSHION + 4} L {x1} 1540", sw=4, stroke=SEAT_DEEP)
        shape(s, g, f"M {x0 + 8} {CUSHION + 8} L {x1 + 8} 1536", sw=2, stroke="#8aa1c4", dash=[8, 8])
    shape(s, g, f"M 190 {CUSHION + 22} L 1000 {CUSHION - 6} Q 1072 {CUSHION - 4} 1076 {CUSHION + 60}", sw=2.5,
          stroke="#a9bddb", dash=[10, 8])  # fmt: skip
    shape(s, g, "M 170 1520 L 1092 1480 L 1092 1560 Q 1092 1580 1070 1582 L 170 1610 Z", SEAT_SHADE, 4)  # roll
    shape(s, g, "M 170 1610 L 1070 1582 L 1092 1600 L 1092 1920 L 170 1920 Z", "#3c4252", 4)


SCREEN_W, SCREEN_H = 330, 220  # the laptop's screen, before ``scale``


BADGE, STAMP = "#a51d24", "#374151"  # the unread pill and the time stamp: 7:1 and more, for small antialiased text


@register("prop", "stick-laptop", tags=("laptop", "email", "font"))
def laptop(
    cv: Canvas, parent, x: float, y: float, *, title: str, rows: Sequence[str], badge: str = "", scale: float = 1.0
):
    """An open laptop standing on a surface at (``x``, ``y``: its base's left end), its screen toward the camera: a
    mail window with ``title``, up to four ``rows`` each ticked as sent, and an optional ``badge`` (a count in a red
    pill), all sized by ``scale``."""
    cv.require_font("the laptop's screen is set in it")
    if not title.strip() or not 1 <= len(rows) <= 4 or any(not r.strip() for r in rows):
        raise StickDataError(f"a laptop screen needs a title and 1 to 4 non-empty rows, got {title!r}, {rows!r}")
    if not (checks.number(scale) and scale > 0):
        raise StickDataError(f"scale must be a positive number, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    shape(cv, g, f"M -20 0 L {SCREEN_W + 60} 0 L {SCREEN_W + 20} 34 L -50 34 Z", "#6e737c", 5)
    box(cv, g, 0, -SCREEN_H - 30, SCREEN_W + 40, SCREEN_H + 30, "#5b5d69", 5, r=14)
    box(cv, g, 14, -SCREEN_H - 16, SCREEN_W + 12, SCREEN_H + 4, "#ffffff", 3, r=6)
    box(cv, g, 14, -SCREEN_H - 16, SCREEN_W + 12, 44, "#eef0f3", 0, r=6)
    _text(cv, g, title, 26, -SCREEN_H - 16, SCREEN_W - 70, 44, 26, cv.ink, weight=700)
    if badge:
        box(cv, g, SCREEN_W - 50, -SCREEN_H - 9, 70, 32, BADGE, r=16)
        _text(cv, g, badge, SCREEN_W - 50, -SCREEN_H - 9, 70, 32, 22, "#ffffff", weight=700, align="center")
    for i, row in enumerate(rows):
        top = -SCREEN_H + 34 + i * 42
        shape(cv, g, f"M 30 {top + 22} L 38 {top + 30} L 52 {top + 12}", sw=4, stroke="#3ccf6e")
        _text(cv, g, row, 62, top, SCREEN_W - 40, 42, 22, cv.ink, weight=400)
    return g


PHONE_W, PHONE_H = 204, 300


@register("prop", "stick-phone", tags=("phone", "mount", "notification", "buzz", "font"))
def phone(cv: Canvas, parent, *, sender: str, text: str, buzz: Sequence[float] = (), at: tuple[float, float] = MOUNT):
    """A phone standing in a windshield mount with its top left at ``at`` (the dashboard's mount, :data:`MOUNT`),
    showing one notification from ``sender``; it shakes, with buzz marks, for a moment at each time in ``buzz``
    (seconds on the parent's clock)."""
    cv.require_font("the phone's notification is set in it")
    if not sender.strip() or not text.strip():
        raise StickDataError("a phone notification needs a sender and a text")
    if any(not (checks.number(t) and t >= 0) for t in buzz) or list(buzz) != sorted(buzz):
        raise StickDataError(f"buzz times must be non-negative and in order, got {list(buzz)!r}")
    x, y = at
    shape(cv, parent, f"M {x + PHONE_W / 2} {y + PHONE_H} L {x + PHONE_W / 2 + 30} {y + PHONE_H + 70}", sw=26,
          stroke=cv.ink)  # fmt: skip
    shape(cv, parent, f"M {x + PHONE_W / 2} {y + PHONE_H} L {x + PHONE_W / 2 + 30} {y + PHONE_H + 70}", sw=14,
          stroke=WHEEL)  # fmt: skip
    g = _group(cv, parent, x=x, y=y)
    box(cv, g, 0, 0, PHONE_W, PHONE_H, "#2b2e35", 5, r=24)
    box(cv, g, 10, 14, PHONE_W - 20, PHONE_H - 28, "#3d5a80", 0, r=14)
    box(cv, g, 16, 40, PHONE_W - 32, 110, "#f4f5f7", 0, r=12)
    _text(cv, g, sender, 26, 44, PHONE_W - 52, 34, 24, cv.ink, weight=700)
    _text(cv, g, text, 26, 78, PHONE_W - 44, 32, 19, cv.ink, weight=400)
    _text(cv, g, "now", 26, 108, PHONE_W - 52, 30, 18, STAMP, weight=700)
    if buzz:
        keys = [(0.0, x)]
        for t in buzz:
            keys += [(t, x), (t + 0.05, x - 7), (t + 0.1, x + 7), (t + 0.15, x - 5), (t + 0.2, x + 5), (t + 0.25, x)]
        cv.keys(g, "x", keys, kind="linear")
        for t in buzz:
            marks = _group(cv, parent)
            cv.gate(marks, [(t, t + 0.35)])
            for side, mx in ((-1, x - 18), (1, x + PHONE_W + 18)):
                shape(cv, marks, f"M {mx} {y + 90} Q {mx + side * 18} {y + 145} {mx} {y + 200}", sw=6, stroke=cv.ink)
    return g


_text = partial(look.text, align="start", overflow="ellipsis")  # one line, cut with an ellipsis

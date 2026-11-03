"""The Stick style's front door: a hall seen from inside, the yard through the doorway, and what arrives in that yard.

:func:`hall` is the back layer: the wall with its coats and the shelf that holds the cactus, the doorway of
:mod:`srstudio.stick_door` with a front yard beyond it, a picket fence, the houses across the street out of focus, and
the path up to the step. Who stands outside is drawn in :func:`outside` and placed by
:func:`srstudio.stick_door.on_path`. :func:`front_door` goes over them: a panelled door hinged on the left jamb, shut
until ``opens``, then swinging in through :data:`SWING_STEPS` drawn frames and held back at :data:`DOOR_BACK`.

:func:`tow_truck` is a truck from behind, reversing down the path toward the door through ``path`` with its beacon
turning, and lowering its hook from ``drop``; with neither it stands where :data:`PARKED` left it, hook down.
:func:`clipboard` (:func:`srstudio.stick_table.clipboard`, re-exported) is what a man from an agency carries: edge on
while he reads it, flat to the viewer when he turns it round. :data:`POSES` are the visitor's and the householder's:
the visitor stands at :data:`VISITOR` and the householder, mirrored, at :data:`HOUSEHOLDER_AT`, at
:data:`HOUSEHOLDER_SCALE`. Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot
redraws the same.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks, signature
from .canvas import Canvas
from .look import sheet
from .registry import register
from .stick import STANDING, Gradient, RigPose, StickDataError, _group, _seat, box, oval, paint, shape
from .stick_door import DOORWAY, HANDLE_Y, MAX_DEPTH, SWING_STEP, SWING_STEPS, VANISH, on_path, through
from .stick_table import BOARD_LETTERS, clipboard

__all__ = [
    "BOARD_LETTERS",
    "DOOR_BACK",
    "HOOK_HANG",
    "HOOK_LOW",
    "HOUSEHOLDER_AT",
    "HOUSEHOLDER_SCALE",
    "PARKED",
    "POSES",
    "VISITOR",
    "VISITOR_LANE",
    "clipboard",
    "front_door",
    "hall",
    "outside",
    "truck_place",
    "tow_truck",
]

WALL_TOP, WALL_LOW, DADO, RAIL, FLOOR_TOP, FLOOR_LOW, BOARD_LINE = (
    "#b8c7b0",
    "#a3b59b",
    "#e6e0cf",
    "#c9c1ab",
    "#a07a55",
    "#7f5e41",
    "#6a4e37",
)
JAMB, JAMB_LIGHT, LEAF, LEAF_LIGHT, LEAF_DEEP, KNOB = "#ece6d6", "#fbf8ee", "#8f3f36", "#a84f44", "#73302a", "#e3b23c"
SKY_TOP, SKY_LOW, LAWN_FAR, LAWN_NEAR, PATH, PATH_EDGE = (
    "#86c2e6",
    "#e3f1ee",
    "#9cc173",
    "#7fa95a",
    "#d9d3c5",
    "#a9a397",
)
FENCE, FENCE_SHADE, HOUSE_A, HOUSE_B, ROOF, TREE = "#f4efe3", "#c9c2b2", "#d9b98f", "#c5cdd8", "#8a4b40", "#6f9a58"
COAT_A, COAT_B, PEG, SHELF = "#46607c", "#b9743c", "#4a3a2c", "#7a5a3e"
TRUCK, TRUCK_SHADE, TRUCK_DARK, STEEL, STEEL_DARK, TYRE, GLASS = (
    "#e0a830",
    "#b98420",
    "#2c2e33",
    "#8f97a1",
    "#5f666f",
    "#202226",
    "#3a4a58",
)
AMBER, TAIL, STRIPE = "#ffb22e", "#c8362b", "#f6efe0"

X, Y, W, H = DOORWAY
FLOOR_Y = Y + H
JAMB_WIDTH = 26.0
DOOR_BACK = X + 104.0  # the door's free edge once it stands open, swung in against the left jamb
KNOB_Y = HANDLE_Y
FENCE_Y = VANISH[1] + 18.0  # the foot of the pickets
SHELF_AT = (882.0, 1262.0, 170.0)  # x, y, width of the hall's small shelf
TRUCK_ASIDE = 130.0  # pixels right of the path's edge, per unit of depth: its hook comes down clear of the step
TRUCK_SIZE = 1.15  # of the truck's drawn size, per unit of depth along the path
PARKED = 0.62  # the depth the truck stops at
BOOM_TOP = -1180.0  # the boom's tip above the ground, in the truck's own pixels
HOOK_HANG = 90.0  # the cable's length with the hook up, in the truck's own pixels
HOOK_LOW = 330.0  # and with it down
LOWER = 0.8  # seconds the hook takes to come down
BEACON_RATE = 2.0  # turns of the beacon a second: below anything a flash check counts on so small a light
VISITOR, VISITOR_LANE = 0.98, -0.3  # the step: a visitor on it stands just outside the door, left of the path
HOUSEHOLDER_AT, HOUSEHOLDER_SCALE = (1322.0, 138.0), 0.86  # with flip=True, a pose here stands right of the doorway
_FEET = dict(hip=(540, 1190), knees=((525, 1445), (560, 1445)), feet=((512, 1700), (566, 1700)))
_FAR = dict(elbow=(510, 1040), hand=(502, 1195))


def _standing(head, neck, elbow, hand, *, far_elbow=None, far_hand=None) -> RigPose:
    return _seat(head, neck, _FEET["hip"], _FEET["knees"], _FEET["feet"],
                 (far_elbow or _FAR["elbow"], elbow), (far_hand or _FAR["hand"], hand))  # fmt: skip


# For the visitor: the clipboard up before his chest, read with the head down, turned round at arm's length. For the
# householder, mirrored: the near hand on the knob; and, after the hands-hips of STANDING, as small as she gets.
POSES: dict[str, RigPose] = {
    **STANDING,
    "board": _standing((540, 750), (540, 857), (606, 1010), (652, 948)),
    "read": _standing((552, 772), (544, 866), (606, 1016), (652, 948)),
    "offer": _standing((556, 752), (544, 858), (650, 1000), (790, 1090)),
    "knob": _standing((552, 754), (540, 857), (660, 950), (764, 920)),
    "small": _standing((528, 792), (534, 884), (592, 1040), (570, 1120), far_elbow=(486, 1040), far_hand=(528, 1124)),
}


def outside(cv: Canvas, parent):
    """A group masked to the opening inside the frame of the door: what stands in the yard is drawn in it."""
    g = _group(cv, parent)
    left, top, right = X + JAMB_WIDTH / 2, Y + JAMB_WIDTH / 2, X + W - JAMB_WIDTH / 2
    g.add_mask(type="path", path=f"M {left} {top} L {right} {top} L {right} {FLOOR_Y} L {left} {FLOOR_Y} Z")
    return g


def _check_end(end: float, what: str) -> None:
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"the {what} needs a positive shot length, got {end!r}")


def _yard(cv: Canvas, parent) -> None:
    """The sky, the houses over the road out of focus, the lawn, the fence with its gate open, and the path."""
    vx, vy = VANISH
    sky = paint(cv, Gradient("porch-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, Y, 0, vy))
    box(cv, parent, X - 10, Y - 10, W + 20, vy - Y + 40, sky)
    far = _group(cv, parent, effects=cv.effect("porch-far-blur", "blur", radius=4.0), **sheet(cv))
    for hx, hw, wall in ((X - 60, 300, HOUSE_A), (X + 300, 340, HOUSE_B)):
        top, peak, right = vy - 190, vy - 330, hx + hw
        shape(cv, far, f"M {hx} {vy} L {hx} {top} L {hx + hw / 2} {peak} L {right} {top} L {right} {vy} Z", wall, 3)
        shape(cv, far, f"M {hx - 30} {vy - 180} L {hx + hw / 2} {vy - 350} L {hx + hw + 30} {vy - 180} Z", ROOF, 3)
        box(cv, far, hx + hw * 0.3, vy - 150, hw * 0.4, 90, "#8fa9b5")
    oval(cv, far, X + 210, vy - 300, 170, 320, TREE)
    lawn = paint(cv, Gradient("porch-lawn", ((0, LAWN_FAR), (1, LAWN_NEAR)), 0, vy, 0, FLOOR_Y))
    box(cv, parent, X - 10, vy, W + 20, FLOOR_Y - vy + 10, lawn)
    shape(cv, parent, f"M {vx - 44} {FENCE_Y} L {vx + 44} {FENCE_Y} L {X + W - 110} {FLOOR_Y} L {X + 40} {FLOOR_Y} Z",
          PATH, 3, stroke=PATH_EDGE)  # fmt: skip
    for k in range(7):  # the slabs, closing up with distance
        d = 0.72**k
        yk = FENCE_Y + (FLOOR_Y - FENCE_Y) * d
        half = 44 + (W / 2 - 44) * d * 0.9
        shape(cv, parent, f"M {vx - half} {yk} L {vx + half} {yk}", sw=max(1.5, 3 * d), stroke=PATH_EDGE)
    for px in range(int(X) - 20, int(X + W) + 40, 44):
        if abs(px - vx) < 74:  # the gate stands open
            continue
        top, tip = FENCE_Y - 96, FENCE_Y - 116
        picket = f"M {px} {FENCE_Y} L {px} {top} L {px + 14} {tip} L {px + 28} {top} L {px + 28} {FENCE_Y} Z"
        shape(cv, parent, picket, FENCE, 3, stroke=FENCE_SHADE)
    for side in (X - 10, vx + 70):
        width = (vx - 70 - side) if side < vx else (X + W + 10 - side)
        box(cv, parent, side, FENCE_Y - 74, width, 11, FENCE)


@register("location", "stick-hall", tags=("home", "hall", "doorway", "front-door", "yard", "fence", "exterior"))
def hall(cv: Canvas, parent, end: float) -> None:
    """A house's front hall from inside, the doorway standing where :mod:`srstudio.stick_door` keeps it and a front yard
    beyond: wall and dado, two coats on their pegs, the shelf with the cactus, boards and a runner. Draw who is outside
    in :func:`outside` and :func:`front_door` over them."""
    _check_end(end, "hall")
    s = cv
    wall = paint(s, Gradient("porch-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0, FLOOR_Y))
    box(s, parent, 0, 0, s.width, FLOOR_Y, wall)
    box(s, parent, 0, 1150, s.width, FLOOR_Y - 1150, DADO)
    box(s, parent, 0, 1136, s.width, 18, RAIL, 3)
    box(s, parent, 0, FLOOR_Y - 26, s.width, 26, RAIL, 3)
    floor = paint(s, Gradient("porch-floor", ((0, FLOOR_TOP), (1, FLOOR_LOW)), 0, FLOOR_Y, 0, s.height))
    box(s, parent, 0, FLOOR_Y, s.width, s.height - FLOOR_Y, floor)
    for fy in (1560, 1650, 1780):
        shape(s, parent, f"M 0 {fy} L {s.width} {fy}", sw=3, stroke=BOARD_LINE)
    shape(s, parent, f"M {X + 60} {FLOOR_Y} L {X + W - 40} {FLOOR_Y} L 980 1920 L 60 1920 Z", "#7c4a42", 4, opacity=0.8)
    box(s, parent, 930, 560, 150, 18, PEG, 3, r=6)
    for px, coat in ((1000, COAT_B), (1078, COAT_A)):
        oval(s, parent, px - 8, 576, 16, 24, PEG)
        shape(s, parent, f"M {px - 16} 596 Q {px} 586 {px + 16} 596 L {px + 56} 880 L {px + 26} 900 L {px + 14} 1060 "
              f"L {px - 14} 1060 L {px - 26} 900 L {px - 56} 880 Z", coat, 4)  # fmt: skip
    outside = through(s, parent)
    _yard(s, outside)
    shape(s, parent, f"M {X} {FLOOR_Y} L {X} {Y} L {X + W} {Y} L {X + W} {FLOOR_Y}", sw=JAMB_WIDTH, stroke=JAMB)
    shape(s, parent, f"M {X + 13} {FLOOR_Y} L {X + 13} {Y + 13} L {X + W - 13} {Y + 13} L {X + W - 13} {FLOOR_Y}", sw=3,
          stroke=JAMB_LIGHT)  # fmt: skip
    shape(s, parent, f"M {X - 13} {FLOOR_Y} L {X - 13} {Y - 13} L {X + W + 13} {Y - 13} L {X + W + 13} {FLOOR_Y}", sw=3,
          stroke="#b5ae9c")  # fmt: skip
    sx, sy, sw = SHELF_AT
    signature.cactus(s, parent, sx + sw * 0.55, sy, scale=0.42)
    box(s, parent, sx, sy, sw, 16, SHELF, 3, r=4)
    signature.code(s, parent, sx + 4, sy - 16, 13, color="#4f4c3f")


def _leaf(cv: Canvas, parent, edge: float) -> None:
    """The door with its free edge at ``edge``, hinged on the left jamb: two panels and a brass knob, its height drawn
    larger as the free edge swings toward the camera."""
    swing = (X + W - edge) / W  # 0 shut, up to 1 flat against the hinge
    top, bottom = Y + 14 - 70 * swing, FLOOR_Y + 110 * swing
    hinge = X + 13
    shape(cv, parent, f"M {hinge} {Y + 13} L {edge} {top} L {edge} {bottom} L {hinge} {FLOOR_Y} Z", LEAF, 5)
    inset = 0.16 * (edge - hinge)

    def panel(a: float, b: float) -> None:
        def on(x: float, along: float) -> float:
            f = (x - hinge) / (edge - hinge)
            near, far = Y + 13 + along * H, top + along * (bottom - top)
            return near + (far - near) * f

        left, right = hinge + inset, edge - inset
        d = f"M {left} {on(left, a)} L {right} {on(right, a)} L {right} {on(right, b)} L {left} {on(left, b)} Z"
        shape(cv, parent, d, LEAF_DEEP, 3, stroke=LEAF_LIGHT)

    panel(0.08, 0.44)
    panel(0.54, 0.92)
    oval(cv, parent, edge - 42, KNOB_Y - 15, 30, 30, KNOB, stroke=cv.ink, sw=4)


@register("prop", "stick-front-door", tags=("home", "door", "front-door", "swing", "panelled"))
def front_door(cv: Canvas, parent, end: float, *, opens: float | None = None) -> None:
    """A panelled front door hinged on the left jamb of the doorway: standing open at :data:`DOOR_BACK`, or, given
    ``opens`` (seconds into the shot), shut until then and swinging in through :data:`SWING_STEPS` drawn frames."""
    _check_end(end, "front door")
    if opens is None:
        _leaf(cv, _group(cv, parent), DOOR_BACK)
        return
    if not (checks.number(opens) and 0 <= opens and opens + SWING_STEPS * SWING_STEP < end):
        raise StickDataError(f"the door opens inside the shot (0..{end}), got opens={opens!r}")
    shut = X + W - 13
    if opens:
        held = _group(cv, parent)
        cv.gate(held, [(0, opens)])
        _leaf(cv, held, shut)
    for step in range(SWING_STEPS):
        frame = _group(cv, parent)
        at = opens + step * SWING_STEP
        last = step == SWING_STEPS - 1
        cv.gate(frame, [(at, end if last else at + SWING_STEP)])
        _leaf(cv, frame, shut + (DOOR_BACK - shut) * (step + 1) / SWING_STEPS)


def truck_place(depth: float) -> tuple[float, float, float]:
    """``(x, y, scale)`` of the truck ``depth`` of the way down the path: the middle of its back axle on the ground."""
    if not (checks.number(depth) and 0 < depth <= MAX_DEPTH):
        raise StickDataError(f"a depth on the path is above 0 and up to {MAX_DEPTH}, got {depth!r}")
    x, y, scale = on_path(depth, 1.0)
    return round(x + 540 * scale + TRUCK_ASIDE * depth, 4), round(y + 1700 * scale, 4), round(depth * TRUCK_SIZE, 4)


def _cab(cv: Canvas, parent) -> None:
    """The cab behind the bed, its back window and the bar of lights on its roof."""
    box(cv, parent, -220, -600, 440, 280, TRUCK_SHADE, 6, r=30)
    box(cv, parent, -170, -560, 340, 130, GLASS, 5, r=14)
    box(cv, parent, -170, -636, 340, 38, TRUCK_DARK, 5, r=12)


def _boom(cv: Canvas, parent) -> None:
    """The A-frame up from the bed to the tip of the boom, and its pulley."""
    for x in (-150, 150):
        shape(cv, parent, f"M {x} -330 L 0 {BOOM_TOP}", sw=40, stroke=cv.ink)
        shape(cv, parent, f"M {x} -330 L 0 {BOOM_TOP}", sw=28, stroke=STEEL)
    shape(cv, parent, "M -90 -640 L 90 -640", sw=26, stroke=cv.ink)
    shape(cv, parent, "M -90 -640 L 90 -640", sw=15, stroke=STEEL_DARK)
    oval(cv, parent, -34, BOOM_TOP - 34, 68, 68, STEEL_DARK, stroke=cv.ink, sw=6)


def _bed(cv: Canvas, parent) -> None:
    """The back of the truck: tyres, the bed in hazard stripes, tail lights and the stinger."""
    for x in (-300, 190):
        box(cv, parent, x, -140, 110, 140, TYRE, 5, r=18)
    box(cv, parent, -320, -340, 640, 220, TRUCK, 6, r=12)
    for k in range(-3, 3):
        x = k * 104
        shape(cv, parent, f"M {x} -210 L {x + 52} -210 L {x + 96} -130 L {x + 44} -130 Z", TRUCK_DARK)
        shape(cv, parent, f"M {x + 52} -210 L {x + 104} -210 L {x + 148} -130 L {x + 96} -130 Z", STRIPE)
    for x in (-296, 216):
        box(cv, parent, x, -310, 80, 56, TAIL, 4, r=8)
    box(cv, parent, -130, -300, 260, 62, TRUCK_SHADE, 4, r=6)
    box(cv, parent, -340, -126, 680, 26, STEEL_DARK, 5, r=6)


def _beacon(cv: Canvas, parent, end: float) -> None:
    lit = _group(cv, parent)
    oval(cv, lit, -60, -668, 120, 56, AMBER, stroke=cv.ink, sw=5)
    step = 0.5 / BEACON_RATE
    count = int(end / step)
    if count:
        cv.keys(lit, "opacity", [(k * step, 1.0 if k % 2 == 0 else 0.4) for k in range(count + 1)])


def _hook(cv: Canvas, parent) -> None:
    """The hook, hanging from its origin."""
    shape(cv, parent, "M 0 0 L 0 34", sw=22, stroke=cv.ink)
    oval(cv, parent, -26, 26, 52, 52, STEEL_DARK, stroke=cv.ink, sw=7)
    d = "M 0 78 Q 66 92 56 160 Q 46 216 -8 212 Q -58 206 -66 158"
    shape(cv, parent, d, sw=38, stroke=cv.ink)
    shape(cv, parent, d, sw=23, stroke=STEEL)
    shape(cv, parent, "M -66 158 L -84 124 L -42 136 Z", STEEL, 6, stroke=cv.ink)


@register("prop", "stick-tow-truck", tags=("truck", "tow", "hook", "reversing", "vehicle", "beacon"))
def tow_truck(
    cv: Canvas, parent, end: float, *, path: Sequence[tuple[float, float]] | None = None, drop: float | None = None
):
    """A tow truck from behind, unbranded, its boom up and a hook on a cable, in the doorway's perspective: on the path
    at :data:`PARKED` with its hook down, or reversing through ``path`` (seconds, depth) and lowering the hook over
    :data:`LOWER` seconds from ``drop``. Returns its group."""
    _check_end(end, "tow truck")
    spots = list(path) if path else [(0.0, PARKED)]
    times = [t for t, _ in spots]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise StickDataError(f"a truck's path runs in time order, got {spots!r}")
    if not all(checks.number(t) and 0 <= t <= end for t in times):
        raise StickDataError(f"a truck's path runs inside the shot (0..{end}), got {spots!r}")
    if drop is not None and not (checks.number(drop) and 0 <= drop and drop + LOWER <= end):
        raise StickDataError(f"the hook comes down inside the shot (0..{end}), got drop={drop!r}")
    places = [(t, truck_place(d)) for t, d in spots]
    x, y, scale = places[0][1]
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    if len(places) > 1:
        for prop, i in (("x", 0), ("y", 1), ("scaleX", 2), ("scaleY", 2)):
            cv.keys(g, prop, [(t, p[i]) for t, p in places], kind="sine-in-out")
    shape(cv, g, "M -340 0 L 340 0 L 380 40 L -380 40 Z", "#3a4a2c", opacity=0.35)  # its shadow on the path
    _cab(cv, g)
    _beacon(cv, g, end)
    _boom(cv, g)
    _bed(cv, g)
    low = BOOM_TOP + HOOK_LOW
    high = BOOM_TOP + HOOK_HANG
    start = high if drop is not None else low
    cable = _group(cv, g, y=BOOM_TOP, scaleY=(start - BOOM_TOP) / 100)
    box(cv, cable, -5, 0, 10, 100, TRUCK_DARK)
    hook = _group(cv, g, y=start)
    if drop is not None:
        span = [(0.0, high), (drop, high), (drop + LOWER, low)]
        cv.keys(hook, "y", span, kind="linear")
        cv.keys(cable, "scaleY", [(t, round((v - BOOM_TOP) / 100, 4)) for t, v in span], kind="linear")
    _hook(cv, hook)
    return g

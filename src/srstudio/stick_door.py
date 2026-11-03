"""The Stick style's entrance: a lobby seen from inside, the street through its doorway, and a glass door held open.

:func:`entrance` is the back layer: the lobby wall with its clock and the sun that crosses it, the doorway
(:data:`DOORWAY`) with the street running away to :data:`VANISH`, and the floor. ``night`` keys how dark the street
and the lobby are, and a wall clock's hands run at ``clock`` turns a second. :func:`street` is what a long lens sees
of that street. :func:`door` is the glass door on its hinge at the doorway's right jamb: held open at
:data:`OPEN_EDGE`, and, from ``shut``, swinging closed in :data:`SWING_STEPS` drawn frames.

A figure outside walks the path: :func:`on_path` places it by depth, :func:`approach` keys it toward the door, and
:func:`jogger` is a :func:`srstudio.stick.rig` running on the spot, from :data:`JOG`. The holder stands in the lobby
at :data:`HOLDER_AT`, mirrored, posed from :data:`HOLD`; :func:`shaking` is his arm giving up, and :func:`snow_cap`
what settles on him. :func:`snow` falls over the street, and :func:`marathon` runs past its far end. Everything is
in frame pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import _stick_scene_contracts as sc
from . import checks, signature, stick_reel
from .canvas import Canvas
from .held_keys import held_key
from .look import sheet
from .registry import register
from .stick import Face, Gradient, Look, RigKey, RigPose, StickDataError, _group, _seat, box, oval, paint, rig, shape

__all__ = [
    "DOORWAY",
    "HOLD",
    "HOLDER_AT",
    "JOG",
    "MAX_DEPTH",
    "OPEN_EDGE",
    "SWING_STEPS",
    "VANISH",
    "approach",
    "door",
    "door_edge",
    "entrance",
    "jogger",
    "marathon",
    "on_path",
    "shaking",
    "snow",
    "snow_cap",
    "steps",
    "street",
    "through",
]

WALL_TOP, WALL_LOW, FLOOR, FLOOR_LINE = "#efe6d3", "#dacdb2", "#a9967a", "#8f7d63"
METAL, METAL_LIGHT, GLASS, SUN_PATCH = "#3b4048", "#6a717c", "#bfe0ea", "#fff0ba"
SKY_TOP, SKY_LOW, BUILDING, BUILDING_FAR, PAVEMENT, KERB = (
    "#7fb8d8",
    "#dcecef",
    "#b9a48d",
    "#cdbda6",
    "#c9c3b6",
    "#9c968a",
)
NIGHT, STAR, LAMP_GLOW, SNOW, SILHOUETTE = "#0d1b3d", "#fdf6d8", "#ffe2a0", "#f7fbff", "#141821"

DOORWAY = (110.0, 240.0, 580.0, 1260.0)  # x, y, w, h of the opening: its right jamb is the door's hinge
VANISH = (340.0, 930.0)  # where the street runs out
FLOOR_Y = DOORWAY[1] + DOORWAY[3]
HINGE = DOORWAY[0] + DOORWAY[2]
OPEN_EDGE = 545.0  # the free edge of the door while it is held
SWING_STEPS = 4  # frames drawn of the door swinging shut
SWING_STEP = 1 / 24  # how long each is up
HANDLE_Y = 930.0
CLOCK = (925.0, 330.0, 74.0)  # centre and radius of the lobby's clock
HOLDER_AT = (1380.0, 0.0)  # with flip=True a pose from HOLD stands here, right of the doorway, facing it
PATH_X, PATH_HALF = 345.0, 190.0  # the path's centre and half-width, at the door
MAX_DEPTH = 1.4  # a figure this far along has come through the doorway to the camera
SNOW_FLAKES = 26

_STAND = dict(neck=(540, 857), hip=(540, 1190), knees=((525, 1445), (560, 1445)), feet=((512, 1700), (566, 1700)))
_FAR_ARM = dict(elbow=(510, 1040), hand=(502, 1195))


def _holding(head: tuple[float, float], elbow: tuple[float, float], hand: tuple[float, float]) -> RigPose:
    return _seat(head, _STAND["neck"], _STAND["hip"], _STAND["knees"], _STAND["feet"],
                 (_FAR_ARM["elbow"], elbow), (_FAR_ARM["hand"], hand))  # fmt: skip


# Standing, the near arm out to the door's edge; mirrored at HOLDER_AT the hand lands on the handle. "hold-a" and
# "hold-b" are that arm shaking, "sag" its last moment and "drop" the arm given out.
HOLD: dict[str, RigPose] = {
    "hold": _holding((552, 754), (684, 906), (832, HANDLE_Y)),
    "hold-a": _holding((552, 754), (682, 900), (832, HANDLE_Y - 9)),
    "hold-b": _holding((552, 754), (686, 913), (832, HANDLE_Y + 9)),
    "sag": _holding((560, 770), (672, 972), (806, 1010)),
    "drop": _holding((546, 780), (606, 1050), (632, 1240)),
}


def _jog(head_y: float, knees, feet, hand: tuple[float, float]) -> RigPose:
    neck, hip = (540, head_y + 106), (540, head_y + 430)
    arms = ((452, head_y + 260), (640, head_y + 240)), ((430, head_y + 370), hand)
    return _seat((540, head_y), neck, hip, knees, feet, *arms)


# Running at the camera on the spot, the near hand up in the small wave that means sorry.
JOG: dict[str, RigPose] = {
    "jog-a": _jog(760, ((488, 1405), (598, 1330)), ((500, 1690), (592, 1520)), (706, 874)),
    "jog-b": _jog(742, ((482, 1312), (592, 1392)), ((488, 1502), (580, 1672)), (718, 830)),
}


def _check_end(end: float, what: str) -> None:
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"the {what} needs a positive shot length, got {end!r}")


def _check_night(night: Sequence[tuple[float, float]], end: float) -> None:
    if not night or night[0][0] != 0:
        raise StickDataError(f"the night's keys start at 0 s, got {list(night)!r}")
    times = [t for t, _ in night]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)) or times[-1] > end:
        raise StickDataError(f"the night's keys run in order inside the shot (0..{end}), got {list(night)!r}")
    if not all(checks.number(v) and 0 <= v <= 1 for _, v in night):
        raise StickDataError(f"the night's darkness is 0..1, got {list(night)!r}")


def _dark(cv: Canvas, node, night: Sequence[tuple[float, float]], *, scale: float = 1.0, light: bool = False) -> None:
    """Key ``node``'s opacity by the night: ``scale`` of the darkness, or of the daylight left when ``light``."""
    keys = [(t, round(scale * ((1 - v) if light else v), 4)) for t, v in night]
    if len(keys) == 1:
        node.opacity = keys[0][1]
    else:
        cv.keys(node, "opacity", keys, hold=False)


def through(cv: Canvas, parent):
    """A group masked to the doorway: what is drawn in it is seen through the opening."""
    x, y, w, h = DOORWAY
    g = _group(cv, parent)
    g.add_mask(type="path", path=f"M {x} {y} L {x + w} {y} L {x + w} {y + h} L {x} {y + h} Z")
    return g


def _outside(cv: Canvas, parent, night: Sequence[tuple[float, float]]) -> None:
    """The sky, the two rows of buildings to the vanishing point, the pavement and the path; lamps come on at dark."""
    vx, vy = VANISH
    x, y, w, h = DOORWAY
    sky = paint(cv, Gradient("door-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, y, 0, vy))
    box(cv, parent, x - 10, y - 10, w + 20, vy - y + 20, sky)
    far = _group(cv, parent, effects=cv.effect("door-far-blur", "blur", radius=3.0), **sheet(cv))
    for side, edge in ((-1, x - 60), (1, x + w + 60)):
        shape(cv, far, f"M {vx + side * 34} {vy + 6} L {vx + side * 34} {vy - 120} L {edge} {y - 80} "
                       f"L {edge} {vy + 140} Z", BUILDING_FAR, 3)  # fmt: skip
        for k in range(1, 5):  # windows, shrinking toward the street's end
            d = 0.8**k
            wx = vx + side * (380 * d)
            wy = vy - 420 * d
            shape(cv, far, f"M {wx} {wy} L {wx + side * 70 * d} {wy - 40 * d} L {wx + side * 70 * d} {wy + 130 * d} "
                           f"L {wx} {wy + 120 * d} Z", "#8fa9b5")  # fmt: skip
    ground = paint(cv, Gradient("door-ground", ((0, "#dcd6c9"), (1, PAVEMENT)), 0, vy, 0, FLOOR_Y))
    box(cv, parent, x - 10, vy, w + 20, FLOOR_Y - vy + 10, ground)
    shape(cv, parent, f"M {vx - 3} {vy} L {vx + 3} {vy} L {PATH_X + 230} {FLOOR_Y} L {PATH_X - 230} {FLOOR_Y} Z",
          "#e6e0d3", 3, stroke=KERB)  # fmt: skip
    for k in range(9):  # the slabs, closing up with distance
        d = 0.74**k
        yk = vy + (FLOOR_Y - vy) * d
        half = 230 * d
        shape(cv, parent, f"M {PATH_X - half} {yk} L {PATH_X + half} {yk}", sw=max(1.5, 3 * d), stroke=KERB)
    for side in (-1, 1):  # street lamps, one pair near and one far
        for d in (0.62, 0.34):
            lx, ly = vx + side * 330 * d, vy + 230 * d
            shape(cv, parent, f"M {lx} {ly} L {lx} {ly - 520 * d}", sw=max(3, 9 * d), stroke=METAL)
            glow = _group(cv, parent)
            oval(cv, glow, lx - 40 * d, ly - 560 * d, 80 * d, 80 * d, LAMP_GLOW)
            _dark(cv, glow, night)
    shade = _group(cv, parent)
    box(cv, shade, x - 10, y - 10, w + 20, h + 20, NIGHT)
    _dark(cv, shade, night, scale=0.82)
    stars = _group(cv, parent)
    for sx, sy in ((180, 300), (250, 420), (420, 330), (610, 390), (520, 520), (160, 560)):
        oval(cv, stars, sx, sy, 7, 7, STAR)
    _dark(cv, stars, night, scale=0.9)


def _clock(cv: Canvas, parent, end: float, turns: float) -> None:
    cx, cy, r = CLOCK
    oval(cv, parent, cx - r - 8, cy - r - 8, 2 * r + 16, 2 * r + 16, METAL)
    oval(cv, parent, cx - r, cy - r, 2 * r, 2 * r, "#fbf7ec")
    for k in range(12):
        a = math.radians(30 * k)
        shape(cv, parent, f"M {cx + (r - 14) * math.sin(a):.1f} {cy - (r - 14) * math.cos(a):.1f} "
                          f"L {cx + (r - 5) * math.sin(a):.1f} {cy - (r - 5) * math.cos(a):.1f}",
                          sw=4, stroke=METAL)  # fmt: skip
    for length, width, rate in ((r - 16, 6, 1.0), (r - 34, 9, 1 / 12)):
        hand = _group(cv, parent, x=cx, y=cy, anchorX=0, anchorY=0, rotation=40 if width == 9 else 300)
        shape(cv, hand, f"M 0 8 L 0 {-length}", sw=width, stroke=cv.ink)
        if turns:
            start = 40 if width == 9 else 300
            cv.keys(hand, "rotation", [(0, start), (end, start + 360 * turns * rate * end)], hold=False)
    oval(cv, parent, cx - 8, cy - 8, 16, 16, cv.ink)


@register(
    "location",
    "stick-entrance",
    contract=sc.contract('stick-entrance'),
    tags=("lobby", "doorway", "street", "glass-door", "night", "clock"),
)
def entrance(
    cv: Canvas, parent, end: float, *, night: Sequence[tuple[float, float]] = ((0.0, 0.0),), clock: float = 0.0
) -> None:
    """A building's lobby from inside: the wall with its clock (hands running ``clock`` turns of the long hand a
    second) and the patch of sun on it, the doorway and the street beyond, running away to :data:`VANISH`, and the
    floor. ``night`` keys the darkness (seconds, 0..1) over the street and the lobby. Draw :func:`door` over it."""
    _check_end(end, "entrance")
    _check_night(night, end)
    s = cv
    wall = paint(s, Gradient("door-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0, FLOOR_Y))
    box(s, parent, 0, 0, s.width, FLOOR_Y, wall)
    box(s, parent, 0, FLOOR_Y - 22, s.width, 22, "#8c7a5f")
    floor = paint(s, Gradient("door-floor", ((0, "#b7a386"), (1, FLOOR)), 0, FLOOR_Y, 0, s.height))
    box(s, parent, 0, FLOOR_Y, s.width, s.height - FLOOR_Y, floor)
    for fy in (1560, 1650, 1780):
        shape(s, parent, f"M 0 {fy} L {s.width} {fy}", sw=3, stroke=FLOOR_LINE)
    sun = _group(s, parent)
    shape(s, sun, "M 700 300 L 1080 200 L 1080 1090 L 700 1320 Z", SUN_PATCH, opacity=0.5)
    shape(s, sun, f"M 110 {FLOOR_Y} L 690 {FLOOR_Y} L 1080 1920 L 300 1920 Z", SUN_PATCH, opacity=0.28)
    _dark(s, sun, night, light=True)
    x, y, w, h = DOORWAY
    outside = through(s, parent)
    _outside(s, outside, night)
    _clock(s, parent, end, clock)
    gloom = _group(s, parent)
    box(s, gloom, x + w + 26, 0, s.width, FLOOR_Y, NIGHT)
    box(s, gloom, 0, 0, x - 26, FLOOR_Y, NIGHT)
    box(s, gloom, 0, 0, s.width, y - 26, NIGHT)
    box(s, gloom, 0, FLOOR_Y, s.width, s.height - FLOOR_Y, NIGHT)
    _dark(s, gloom, night, scale=0.34)
    shape(s, parent, f"M {x} {y + h} L {x} {y} L {x + w} {y} L {x + w} {y + h}", sw=26, stroke=METAL, strokeCap="butt")
    shape(s, parent, f"M {x + 13} {y + h} L {x + 13} {y + 13} L {x + w - 13} {y + 13} L {x + w - 13} {y + h}", sw=3,
          stroke=METAL_LIGHT)  # fmt: skip
    signature.cactus(s, parent, 975, 1205, scale=0.42)
    box(s, parent, 900, 1205, 150, 16, METAL, r=4)  # the ledge the cactus stands on
    signature.code(s, parent, 40, 1885, 9, color="#6d5f49")


@register(
    "location",
    "stick-street-lens",
    contract=sc.contract('stick-street-lens'),
    tags=("street", "long-lens", "path", "night"),
)
def street(cv: Canvas, parent, end: float, *, night: Sequence[tuple[float, float]] = ((0.0, 0.0),)) -> None:
    """What a long lens sees of :func:`entrance`'s street, filling the frame: the path, the pavement and the end of
    the street, soft behind a runner sharp in the middle of it. It carries both signature marks."""
    _check_end(end, "street")
    _check_night(night, end)
    s = cv
    sky = paint(s, Gradient("lens-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, 0, 0, 900))
    box(s, parent, 0, 0, s.width, 900, sky)
    far = _group(s, parent, effects=s.effect("lens-far-blur", "blur", radius=7.0), **sheet(s))
    shape(s, far, "M -40 900 L -40 180 L 420 620 L 420 900 Z", BUILDING_FAR, 4)
    shape(s, far, "M 1120 900 L 1120 180 L 660 620 L 660 900 Z", BUILDING, 4)
    for wx, wy, ww, wh in ((30, 420, 100, 170), (250, 610, 70, 120), (960, 420, 100, 170), (760, 610, 70, 120)):
        box(s, far, wx, wy, ww, wh, "#8fa9b5")
    ground = paint(s, Gradient("lens-ground", ((0, "#dcd6c9"), (1, PAVEMENT)), 0, 900, 0, s.height))
    box(s, parent, 0, 900, s.width, s.height - 900, ground)
    shape(s, parent, f"M 500 900 L 580 900 L 1040 {s.height} L 40 {s.height} Z", "#e6e0d3", 3, stroke=KERB)
    for ly in (960, 1060, 1210, 1440, 1780):
        half = 40 + (ly - 900) * 0.49
        shape(s, parent, f"M {540 - half} {ly} L {540 + half} {ly}", sw=3, stroke=KERB)
    shade = _group(s, parent)
    box(s, shade, 0, 0, s.width, s.height, NIGHT)
    _dark(s, shade, night, scale=0.7)
    signature.cactus(s, parent, 66, 1500, scale=0.42)  # someone's pot, at the kerb
    signature.code(s, parent, 40, 1885, 9, color="#6d5f49")


def door_edge(step: int) -> float:
    """Where the door's free edge is ``step`` frames into its swing, :data:`OPEN_EDGE` at 0, the jamb at the last."""
    open_angle = math.acos((HINGE - OPEN_EDGE) / DOORWAY[2])
    return HINGE - DOORWAY[2] * math.cos(open_angle * (1 - step / SWING_STEPS))


def _pane(cv: Canvas, parent, edge: float) -> None:
    """The door with its free edge at ``edge``: glass in a metal frame, a push bar, a shine across the glass."""
    x, y, w, h = DOORWAY
    swing = 1 - (HINGE - edge) / w  # 0 shut, toward 1 flat out from the wall
    top, bottom = y + 14 + 90 * swing, y + h - 150 * swing
    hinge_top, hinge_bottom = y + 13, y + h
    frame = f"M {HINGE - 13} {hinge_top} L {edge} {top} L {edge} {bottom} L {HINGE - 13} {hinge_bottom} Z"
    shape(cv, parent, frame, f"{GLASS}55", 22, stroke=METAL)
    cx, ch = (edge + HINGE) / 2, HANDLE_Y
    shine = abs(HINGE - edge) * 0.22
    shape(cv, parent, f"M {cx + shine * 0.5} {top + 60} L {cx + shine * 1.5} {top + 60} L {cx + shine} {bottom - 200} "
                      f"L {cx} {bottom - 200} Z", "#ffffff", opacity=0.2)  # fmt: skip
    shape(cv, parent, f"M {edge + 8} {ch} L {HINGE - 40} {ch - 4}", sw=13, stroke=METAL_LIGHT)
    shape(cv, parent, f"M {edge + 8} {ch} L {edge + 8} {ch + 6}", sw=20, stroke=METAL)


@register(
    "prop", "stick-glass-door", contract=sc.contract('stick-glass-door'), tags=("door", "glass", "swing", "lobby")
)
def door(cv: Canvas, parent, end: float, *, shut: float | None = None, closed: bool = False) -> None:
    """The glass door on its hinge at :data:`DOORWAY`'s right jamb: held open at :data:`OPEN_EDGE`, and, from
    ``shut`` (seconds into the shot), swinging closed through :data:`SWING_STEPS` drawn frames; ``closed`` draws it
    already shut."""
    _check_end(end, "door")
    if closed and shut is not None:
        raise StickDataError(f"a door already closed cannot shut at {shut!r}")
    if shut is None:
        _pane(cv, _group(cv, parent), door_edge(SWING_STEPS) if closed else OPEN_EDGE)
        return
    if not (checks.number(shut) and 0 < shut < end):
        raise StickDataError(f"the door can shut inside the shot (0..{end}), got shut={shut!r}")
    held = _group(cv, parent)
    cv.gate(held, [(0, shut)])
    _pane(cv, held, OPEN_EDGE)
    for step in range(1, SWING_STEPS):
        frame = _group(cv, parent)
        at = shut + (step - 1) * SWING_STEP
        cv.gate(frame, [(at, at + SWING_STEP)])
        _pane(cv, frame, door_edge(step))
    closed = _group(cv, parent)
    cv.gate(closed, [(shut + (SWING_STEPS - 1) * SWING_STEP, end)])
    _pane(cv, closed, door_edge(SWING_STEPS))


def on_path(depth: float, lane: float = 0.0) -> tuple[float, float, float]:
    """``(x, y, scale)`` that stands a pose centred on x 540 with feet at 1700 ``depth`` of the way down the path:
    0 at :data:`VANISH`, 1 at the door, up to :data:`MAX_DEPTH` through it toward the camera. ``lane`` is -1..1 across
    the path, from its left edge to its right."""
    if not (checks.number(depth) and 0 < depth <= MAX_DEPTH):
        raise StickDataError(f"a depth on the path is above 0 and up to {MAX_DEPTH}, got {depth!r}")
    if not (checks.number(lane) and -1 <= lane <= 1):
        raise StickDataError(f"a lane is -1..1 across the path, got {lane!r}")
    scale = depth * 0.78
    foot_y = VANISH[1] + depth * (FLOOR_Y - VANISH[1])
    foot_x = VANISH[0] + depth * (PATH_X - VANISH[0] + lane * PATH_HALF)
    return foot_x - 540 * scale, foot_y - 1700 * scale, scale


def approach(cv: Canvas, parent, keys: Sequence[tuple[float, float]], *, lane: float = 0.0):
    """A group walking down the path through ``keys`` (seconds, depth): draw a figure into it at the origin."""
    times = [t for t, _ in keys]
    if not keys or any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise StickDataError(f"an approach's keys run in time order, got {list(keys)!r}")
    places = [(t, on_path(d, lane)) for t, d in keys]
    x, y, scale = places[0][1]
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    if len(places) > 1:
        for prop, i in (("x", 0), ("y", 1), ("scaleX", 2), ("scaleY", 2)):
            cv.keys(g, prop, [(t, round(p[i], 4)) for t, p in places], hold=False)
    return g


def steps(end: float, rate: float = 6.0) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """The spans of a run's two strides, ``rate`` strides a second."""
    return stick_reel.turns(end, rate)


def jogger(cv: Canvas, parent, end: float, *, look: Look, face: Face, rate: float = 6.0, **rigged):
    """A figure running on the spot: the two strides of :data:`JOG` turn about, ``rigged`` going to each
    :func:`srstudio.stick.rig`. Returns its group."""
    g = _group(cv, parent)
    for pose, spans in zip(("jog-a", "jog-b"), steps(end, rate), strict=True):
        stride = _group(cv, g)
        cv.gate(stride, spans)
        rig(cv, stride, [RigKey(0, pose, face)], end, poses=JOG, look=look, **rigged)
    return g


def shaking(
    start: float, end: float, face: Face, *, rate: float = 12.0, fps: int = 30, published: bool = False
) -> list[RigKey]:
    """The holding arm trembling from ``start`` to ``end``: :data:`HOLD`'s two tired poses, ``rate`` swaps a second.

    The first pose holds from ``start``; each swap after it is keyed half a frame before the first frame of the
    ``fps`` reel that shows it (ADR 0216), and a swap that no frame shows is left out. ``published`` keeps the
    four-decimal swap times hold_the_door was published with, one swap in six of which lands after its frame at 12
    a second."""
    if not end > start:
        raise StickDataError(f"a shaking arm runs some time, got {start} to {end}")
    count = math.ceil((end - start) * rate)
    if published:
        return [RigKey(round(start + i / rate, 4), "hold-a" if i % 2 == 0 else "hold-b", face) for i in range(count)]
    keys = [RigKey(start, "hold-a", face)]
    for i in range(1, count):
        at = max(start, held_key(start + i / rate, fps))
        if at >= end:
            break
        if keys[-1].start >= at:
            keys.pop()
        keys.append(RigKey(at, "hold-a" if i % 2 == 0 else "hold-b", face))
    return keys


@register("prop", "stick-snow-cap", contract=sc.contract('stick-snow-cap'), tags=("snow", "winter", "weather"))
def snow_cap(cv: Canvas, parent, x: float, y: float, step: int, *, width: float = 150.0):
    """A heap of settled snow on what is at (``x``, ``y``, its base's centre), bigger with each ``step`` (1 to 3)."""
    if step not in (1, 2, 3):
        raise StickDataError(f"the snow has steps 1 to 3, got {step!r}")
    h, w = width * step * 0.17, width * (0.7 + 0.15 * step)
    d = (f"M {x - w / 2} {y} Q {x - w * 0.42} {y - h * 0.9} {x - w * 0.14} {y - h * 0.8} "
         f"Q {x} {y - h * 1.3} {x + w * 0.2} {y - h * 0.8} Q {x + w * 0.45} {y - h * 0.8} {x + w / 2} {y} Z"
         )  # fmt: skip
    return shape(cv, parent, d, SNOW, 4, stroke="#9fb4c6")


def snow(cv: Canvas, parent, end: float, *, x: float = 0.0, y: float = 0.0, w: float = 1080.0, h: float = 1560.0):
    """Snow falling over the box ``x, y, w, h`` for ``end`` seconds: each flake on its own fixed lane and period."""
    _check_end(end, "snow")
    g = _group(cv, parent)
    for k in range(SNOW_FLAKES):
        lane = x + w * ((k * 0.618) % 1)
        phase = (k * 0.37) % 1
        period = 2.0 + (k % 5) * 0.35
        size = 8 + (k % 3) * 4
        flake = _group(cv, g, x=lane, y=y)
        oval(cv, flake, 0, 0, size, size, SNOW)
        keys: list[tuple[float, float]] = []
        t, top = 0.0, y + h * phase
        while t < end:  # bounded: t grows by a positive span each pass
            span = period * (y + h - top) / h
            stop = min(t + span, end)
            keys += [(round(t, 4), top), (round(stop - 0.001, 4), top + (y + h - top) * (stop - t) / span)]
            t += span
            top = y
        cv.keys(flake, "y", keys, hold=False)
    return g


@register(
    "prop",
    "stick-marathon",
    contract=sc.contract('stick-marathon'),
    tags=("marathon", "crowd", "silhouette", "runners"),
)
def marathon(cv: Canvas, parent, end: float, *, count: int = 14, base: float = 952.0, size: float = 96.0):
    """Runners in silhouette crossing the street's far end from right to left, ``size`` px tall on the line ``base``,
    two strides turn about, all past inside ``end`` seconds."""
    if not (checks.number(end) and end > 0 and isinstance(count, int) and count > 0):
        raise StickDataError(f"a marathon needs a shot and runners, got end={end!r}, count={count!r}")
    a, b = stick_reel.turns(end, 8.0)
    pack = _group(cv, parent)
    span = count * size * 0.62
    cv.keys(pack, "x", [(0, DOORWAY[0] + DOORWAY[2] + 40), (end, DOORWAY[0] - 60 - span)], hold=False)
    for spans, reach in ((a, 1.0), (b, -1.0)):
        stride = _group(cv, pack)
        cv.gate(stride, spans)
        for k in range(count):
            cx = k * size * 0.62
            r = size * 0.13
            top = base - size
            d = (f"M {cx} {top + 2 * r} L {cx} {top + size * 0.58} "
                 f"M {cx - 0.3 * size * reach} {base} L {cx} {top + size * 0.58} L {cx + 0.3 * size * reach} {base} "
                 f"M {cx - 0.26 * size * reach} {top + size * 0.42} L {cx} {top + size * 0.26} "
                 f"L {cx + 0.26 * size * reach} {top + size * 0.46}")  # fmt: skip
            shape(cv, stride, d, sw=size * 0.075, stroke=SILHOUETTE)
            oval(cv, stride, cx - r, top, 2 * r, 2 * r, SILHOUETTE)
    return pack

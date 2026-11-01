"""The Stick style's interview: a small office, a desk seen from its long side, and what is kept in its bottom drawer.

:func:`room` is the back layer: the wall, the door between the two chairs, a window with the city out of focus, a plant,
the two chairs and the desk's top. Figures posed from :data:`POSES` sit in them, one at :data:`LEFT_AT` and one,
mirrored, at :data:`RIGHT_AT`. :func:`desk` goes over them, with its drawers to the camera and the marks on it: the
bottom drawer stays shut, or from ``opens`` slides out through :data:`DRAWER_STEPS` drawn frames to show a pillow, a
folded blanket and a stack of delivery menus. :func:`page` is a sheet lying on the desk, printed side up or face down,
and :func:`resume_insert` is one sheet filling the frame, one line ringed in red. Every word on it is generic and it
names nobody. Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the
same."""

from __future__ import annotations

from . import checks, signature
from .canvas import Canvas
from .look import sheet
from .registry import register
from .stick import Gradient, RigPose, StickDataError, _group, _seat, box, oval, paint, shape

__all__ = [
    "BOTTOM_DRAWER",
    "DRAWER_OUT",
    "DRAWER_STEP",
    "DRAWER_STEPS",
    "LEFT_AT",
    "POSES",
    "RIGHT_AT",
    "desk",
    "drawer_handle",
    "page",
    "resume_insert",
    "room",
]

WALL_TOP, WALL_LOW, SKIRT, FLOOR, FLOOR_LOW = "#d6d3c4", "#c3c0b0", "#8b8778", "#8d8a84", "#6f6c67"
DOOR, DOOR_DARK, FRAME, HANDLE = "#a67c52", "#8a6440", "#e9e4d6", "#e3b23c"
SKY_TOP, SKY_LOW, TOWER_A, TOWER_B, TOWER_C = "#a7cbe6", "#e9f1ee", "#8ea0b3", "#a9b3bf", "#7d8ea0"
LEAF, LEAF_DARK, POT, CHAIR, CHAIR_DARK = "#5f8f54", "#47703f", "#b56b4a", "#3c4450", "#2b313a"
TOP, TOP_EDGE, FRONT, FRONT_DARK, PULL = "#b58a5a", "#94703f", "#9d7648", "#7f5e39", "#d9c58f"
PAPER, PAPER_BACK, INK_GREY, RING = "#fbf8f0", "#ded8c9", "#a5a095", "#d03a30"
PILLOW, PILLOW_SHADE, BLANKET, BLANKET_DARK = "#f1eee6", "#cfcabb", "#6f8fb3", "#4f6d90"
MENU_A, MENU_B, MENU_C = "#d9503f", "#e8b53c", "#3f9a6b"
SKIRT_Y, FLOOR_Y = 1270, 1300
DESK_LEFT, DESK_RIGHT, TOP_BACK, TOP_FRONT, DESK_FOOT = 340, 790, 1052, 1132, 1572
BOTTOM_DRAWER = (500, 1432, 260, 128)  # x, y, width, height of the shut bottom drawer
DRAWER_STEPS = 5  # drawn frames of the drawer sliding out
DRAWER_STEP = 1 / 16  # seconds each
DRAWER_OUT = 76  # pixels the drawer's front drops as it comes toward the camera
DRAWER_GROW = 0.14  # and how much larger it gets
LEFT_AT, RIGHT_AT = (-70.0, -130.0), (1150.0, -130.0)  # the second figure with flip=True
CLASP = (610, 1140)  # a hand at the middle of the desk, for a figure at either place
LINE_LETTERS = 14  # the longest line the insert's ring goes round


def _sit(head, neck, far_elbow, near_elbow, far_hand, near_hand) -> RigPose:
    return _seat(head, neck, (300, 1338), ((505, 1352), (530, 1336)), ((492, 1690), (520, 1700)),
                 (far_elbow, near_elbow), (far_hand, near_hand))  # fmt: skip


# Hands on the desk; a finger on the middle of it; the near hand on a page by the near elbow; the far arm thrown out a
# little, to explain; both reaching over, then the handshake up and down.
POSES: dict[str, RigPose] = {
    "rest": _sit((372, 905), (352, 1012), (440, 1190), (470, 1200), (520, 1214), (560, 1220)),
    "finger": _sit((392, 912), (362, 1016), (440, 1190), (492, 1210), (520, 1214), (612, 1226)),
    "page": _sit((372, 905), (352, 1012), (440, 1190), (416, 1214), (520, 1214), (478, 1224)),
    "explain": _sit((364, 900), (350, 1010), (420, 1186), (470, 1130), (510, 1214), (560, 1060)),
    "reach": _sit((392, 908), (362, 1014), (440, 1190), (500, 1170), (520, 1214), (610, 1190)),
    "shake-up": _sit((392, 908), (362, 1014), (440, 1190), (500, 1140), (520, 1214), CLASP),
    "shake-down": _sit((392, 908), (362, 1014), (440, 1190), (500, 1180), (520, 1214), (610, 1190)),
    "down": _sit((404, 930), (374, 1034), (440, 1190), (490, 1220), (520, 1214), (540, 1330)),
}


def _check_end(end: float, what: str) -> None:
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"the {what} needs a positive shot length, got {end!r}")


def _city(cv: Canvas, parent, x: int, y: int, w: int, h: int) -> None:
    g = _group(cv, parent, effects=cv.effect("interview-far-blur", "blur", radius=4.0), **sheet(cv))
    sky = paint(cv, Gradient("interview-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, y, 0, y + h))
    box(cv, g, x - 12, y - 12, w + 24, h + 24, sky)
    for tx, top, tw, wall in ((x - 8, 180, 76, TOWER_A), (x + 60, 90, 62, TOWER_B), (x + 118, 230, 66, TOWER_C)):
        box(cv, g, tx, y + top, tw, h - top + 14, wall)


def _window(cv: Canvas, parent) -> None:
    x, y, w, h = 884, 440, 160, 360
    glass = _group(cv, parent)
    glass.add_mask(type="path", path=f"M {x} {y} h {w} v {h} h {-w} Z")
    _city(cv, glass, x, y, w, h)
    shape(cv, parent, f"M {x} {y} h {w} v {h} h {-w} Z", cv.clear, 12, stroke=FRAME)
    shape(cv, parent, f"M {x + w / 2} {y} L {x + w / 2} {y + h}", sw=8, stroke=FRAME)


def _door(cv: Canvas, parent) -> None:
    x, y, w = 462, 420, 176
    box(cv, parent, x, y, w, FLOOR_Y - y, DOOR, 4)
    box(cv, parent, x + 26, y + 40, w - 52, 240, DOOR_DARK, 3, r=6)
    box(cv, parent, x + 26, y + 330, w - 52, 300, DOOR_DARK, 3, r=6)
    oval(cv, parent, x + w - 38, 790, 24, 24, HANDLE, stroke=cv.ink, sw=4)
    shape(cv, parent, f"M {x} {FLOOR_Y} L {x} {y} L {x + w} {y} L {x + w} {FLOOR_Y}", sw=16, stroke=FRAME)


def _plant(cv: Canvas, parent) -> None:
    for tip, fill in (((40, 760), LEAF_DARK), ((100, 720), LEAF), ((160, 790), LEAF_DARK), ((70, 830), LEAF)):
        d = f"M 96 1120 Q {tip[0] - 30} {tip[1] + 160} {tip[0]} {tip[1]} Q {tip[0] + 60} {tip[1] + 180} 96 1120 Z"
        shape(cv, parent, d, fill, 3)
    shape(cv, parent, "M 44 1110 L 148 1110 L 134 1270 L 58 1270 Z", POT, 4)


def _chair(cv: Canvas, parent, x: float, side: int) -> None:
    """An office chair at ``x``, its back toward ``side``."""
    bx = x + side * 92
    box(cv, parent, min(bx, bx + side * 34), 880, 34, 330, CHAIR, 4, r=14)
    shape(cv, parent, f"M {bx} 1200 L {x + side * 40} 1250", sw=16, stroke=CHAIR_DARK)
    box(cv, parent, x - 104, 1212, 208, 42, CHAIR, 4, r=14)
    shape(cv, parent, f"M {x} 1254 L {x} 1500", sw=20, stroke=CHAIR_DARK)
    shape(cv, parent, f"M {x - 90} 1560 L {x} 1500 L {x + 90} 1560", sw=14, stroke=CHAIR_DARK)


@register("location", "stick-interview-room", tags=("office", "interview", "door", "window", "plant", "chairs"))
def room(cv: Canvas, parent, end: float) -> None:
    """The room behind the desk: the wall, the door between the chairs, a window with the city out of focus, a plant
    the two chairs at :data:`LEFT_AT` and :data:`RIGHT_AT`, and the top of the desk, for a :func:`page` and hands to lie
    on. Sit the figures, then draw :func:`desk` over their knees."""
    _check_end(end, "room")
    s = cv
    wall = paint(s, Gradient("interview-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0, SKIRT_Y))
    box(s, parent, 0, 0, s.width, SKIRT_Y, wall)
    box(s, parent, 0, SKIRT_Y, s.width, FLOOR_Y - SKIRT_Y, SKIRT)
    floor = paint(s, Gradient("interview-floor", ((0, FLOOR), (1, FLOOR_LOW)), 0, FLOOR_Y, 0, s.height))
    box(s, parent, 0, FLOOR_Y, s.width, s.height - FLOOR_Y, floor)
    _window(s, parent)
    _door(s, parent)
    _plant(s, parent)
    _chair(s, parent, 200, -1)
    _chair(s, parent, 880, 1)
    shape(s, parent, f"M {DESK_LEFT + 30} {TOP_BACK} L {DESK_RIGHT - 30} {TOP_BACK} L {DESK_RIGHT} {TOP_FRONT} "
          f"L {DESK_LEFT} {TOP_FRONT} Z", TOP, 4)  # fmt: skip


def _pillow(cv: Canvas, parent) -> None:
    shape(cv, parent, "M -124 0 Q -140 -120 -118 -150 Q -50 -176 8 -150 Q 26 -100 10 0 Z", PILLOW, 4)
    shape(cv, parent, "M -92 -128 Q -60 -96 -40 -40 M -30 -140 Q -44 -100 -70 -60", sw=4, stroke=PILLOW_SHADE)


def _blanket(cv: Canvas, parent) -> None:
    for k in range(4):
        box(cv, parent, 6, -108 + k * 27, 92, 27, BLANKET if k % 2 else BLANKET_DARK, 3, r=8)


def _menus(cv: Canvas, parent) -> None:
    for k, (name, fill) in enumerate((("WOK", MENU_C), ("THAI", MENU_B), ("PIZZA", MENU_A))):
        y = -130 + k * 34
        box(cv, parent, 40 + k * 6, y, 110, 66, fill, 3, r=4)
        cv.text(parent, cv.uid("menu"), name, 40 + k * 6, y + 2, 110, 34, 25, "#ffffff", weight=700)


def _drawer(cv: Canvas, parent, amount: float) -> None:
    """The bottom drawer, ``amount`` of the way out: at 0 flush with the desk; further out its front drops and grows
    toward the camera, with the dark of its inside above it and what it holds rising over the rim."""
    x, y, w, h = BOTTOM_DRAWER
    cx = x + w / 2
    grow = 1 + DRAWER_GROW * amount
    top = y + DRAWER_OUT * amount
    if amount:
        box(cv, parent, x, y, w, h, "#2b2118")
        shape(
            cv, parent, f"M {x} {y} L {cx - w * grow / 2} {top} L {cx + w * grow / 2} {top} L {x + w} {y} Z", FRONT_DARK
        )
        held = _group(cv, parent, x=cx, y=top + 4, scaleX=grow, scaleY=amount)
        _pillow(cv, held)
        _blanket(cv, held)
        _menus(cv, held)
    left, width, height = cx - w * grow / 2, w * grow, h * grow
    box(cv, parent, left, top, width, height, FRONT, 5, r=6)
    box(cv, parent, cx - 44 * grow, top + height / 2 - 8, 88 * grow, 16, PULL, 3, r=8)


def drawer_handle(amount: float) -> tuple[float, float]:
    """Where the bottom drawer's pull is, on the frame, ``amount`` of the way out."""
    if not (checks.number(amount) and 0 <= amount <= 1):
        raise StickDataError(f"a drawer is 0 to 1 of the way out, got {amount!r}")
    x, y, w, h = BOTTOM_DRAWER
    return x + w / 2, y + DRAWER_OUT * amount + h * (1 + DRAWER_GROW * amount) / 2


@register("prop", "stick-interview-desk", tags=("office", "interview", "desk", "drawer", "pillow", "menus", "font"))
def desk(cv: Canvas, parent, end: float, *, opens: float | None = None, is_open: bool = False) -> None:
    """The desk from its long side, drawers to the camera, the marks on it: the bottom drawer shut, ``is_open`` with a
    pillow, a blanket and a stack of delivery menus in it, or shut until ``opens`` and then sliding out."""
    _check_end(end, "desk")
    if opens is not None and (is_open or not (checks.number(opens) and opens >= 0)):
        raise StickDataError(f"a drawer opens once, at a time in the shot, got opens={opens!r}, is_open={is_open!r}")
    if opens is not None and opens + DRAWER_STEPS * DRAWER_STEP >= end:
        raise StickDataError(f"the drawer finishes opening inside the shot (0..{end}), got opens={opens!r}")
    if opens is not None or is_open:
        cv.require_font("the menus are set in it")
    s = cv
    box(s, parent, DESK_LEFT - 8, TOP_FRONT, DESK_RIGHT - DESK_LEFT + 16, 28, TOP_EDGE, 4, r=4)
    box(
        s, parent, DESK_LEFT + 6, TOP_FRONT + 28, DESK_RIGHT - DESK_LEFT - 12, DESK_FOOT - TOP_FRONT - 28, FRONT_DARK, 4
    )
    signature.cactus(s, parent, 476, TOP_BACK + 24, scale=0.3)
    signature.code(s, parent, 516, TOP_FRONT + 8, 9, color="#e4cfa8")
    x, _, w, _ = BOTTOM_DRAWER
    for y, h in ((1176, 112), (1304, 112)):
        box(s, parent, x, y, w, h, FRONT, 4, r=6)
        box(s, parent, x + w / 2 - 44, y + h / 2 - 8, 88, 16, PULL, 3, r=8)
    if opens is None:
        _drawer(s, _group(s, parent), 1.0 if is_open else 0.0)
        return
    if opens:
        shut = _group(s, parent)
        s.gate(shut, [(0, opens)])
        _drawer(s, shut, 0.0)
    for step in range(DRAWER_STEPS):
        frame = _group(s, parent)
        at = opens + step * DRAWER_STEP
        s.gate(frame, [(at, end if step == DRAWER_STEPS - 1 else at + DRAWER_STEP)])
        _drawer(s, frame, (step + 1) / DRAWER_STEPS)


@register("prop", "stick-desk-page", tags=("office", "paper", "resume", "page"))
def page(cv: Canvas, parent, x: float, y: float, *, face_down: bool = False, ringed: bool = False):
    """A sheet lying on the desk, ``x``, ``y`` its middle, seen low from the front: scrawled lines, or its blank back
    ``face_down``, and one line ringed in red."""
    if face_down and ringed:
        raise StickDataError("a page face down shows no ring")
    g = _group(cv, parent, x=x, y=y)
    shape(cv, g, "M -44 -26 L 44 -26 L 62 26 L -62 26 Z", PAPER_BACK if face_down else PAPER, 3)
    if not face_down:
        for k, half in enumerate((30, 44, 38, 46)):
            ly = -16 + k * 11
            shape(cv, g, f"M {-half} {ly} L {half} {ly}", sw=3, stroke=INK_GREY)
    if ringed:
        oval(cv, g, -40, -8, 80, 22, cv.clear, stroke=RING, sw=4)
    return g


@register("prop", "stick-resume-insert", tags=("office", "resume", "insert", "page", "ring", "font"))
def resume_insert(cv: Canvas, parent, end: float, *, line: str = "CONSULTING") -> None:
    """A resume filling the frame on the desk: a heading, grey lines where the details are, and ``line`` ringed in red
    by hand. It names nobody."""
    _check_end(end, "resume")
    cv.require_font("the resume's lines are set in it")
    if not line.strip() or len(line) > LINE_LETTERS:
        raise StickDataError(f"a ringed line is 1 to {LINE_LETTERS} letters, got {line!r}")
    s = cv
    top = paint(s, Gradient("interview-top", ((0, TOP), (1, TOP_EDGE)), 0, 0, 0, s.height))
    box(s, parent, 0, 0, s.width, s.height, top)
    shape(s, parent, "M 196 250 L 884 262 L 872 1500 L 182 1488 Z", PAPER, 5)
    x, w = 240, 600
    s.text(parent, s.uid("resume-head"), "RESUME", x, 300, w, 100, 76, s.ink, weight=700)
    box(s, parent, 340, 410, 400, 22, INK_GREY, r=8)
    s.text(parent, s.uid("resume-section"), "EXPERIENCE", x, 500, w, 60, 44, s.ink, weight=700)
    for k, half in enumerate((280, 240, 270)):
        box(s, parent, 540 - half, 590 + k * 46, half * 2, 18, INK_GREY, r=8)
    s.text(parent, s.uid("resume-line"), line, x, 800, w, 120, 84, s.ink, weight=700)
    d = "M 214 864 C 214 758 862 742 870 856 C 878 968 208 978 226 846"
    shape(s, parent, d, sw=11, stroke=RING)
    for k, half in enumerate((260, 280, 220, 250, 200)):
        box(s, parent, 540 - half, 1020 + k * 72, half * 2, 18, INK_GREY, r=8)
    signature.cactus(s, parent, 120, 1500, scale=0.3)
    signature.code(s, parent, 60, 1880, 9, color="#6e5230")

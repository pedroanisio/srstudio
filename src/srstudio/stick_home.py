"""The Stick style's kitchen: a table to run round, a fridge, a safe on the wall, and the phones it all turns on.

:func:`kitchen` is the back layer: the wall, the window, the calendar, the floor, the shut fridge at :data:`FRIDGE`
and the shut safe at :data:`SAFE`. :func:`table` is drawn apart so a figure can pass behind it and in front of it.
:func:`fridge_open` and :func:`safe_open` go over the shut ones for as long as they stand open. :func:`handset` is a
phone a hand can hold, :func:`key` the small key to the safe, and :func:`reply` the whole frame given over to one
message. Figures stand from :data:`POSES`, with :data:`LEFT_AT` and, mirrored, :data:`RIGHT_AT` facing each other
across the table. Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot
redraws the same.
"""

from __future__ import annotations

from . import checks, signature, stick_reel
from .canvas import Canvas
from .registry import register
from .stick import STANDING, Gradient, RigPose, StickDataError, _group, _seat, box, oval, paint, shape

__all__ = [
    "FRIDGE",
    "LEFT_AT",
    "PLAN",
    "POSES",
    "RIGHT_AT",
    "SAFE",
    "TABLE_TOP",
    "fridge_open",
    "from_above",
    "handset",
    "key",
    "kitchen",
    "plan",
    "reply",
    "safe_open",
    "table",
]

WALL_TOP, WALL_LOW, FLOOR, FLOOR_LINE = "#f6e3c5", "#ecd2a8", "#b6805a", "#9a6a48"
WHITE_GOODS, WHITE_SHADE, STEEL, STEEL_DARK = "#f4f5f2", "#cfd3d0", "#7c8590", "#4b525c"
WOOD, WOOD_DARK, SKY, CURTAIN = "#c88b4e", "#9a6636", "#bfe3f2", "#d9694c"
FRIDGE_GLOW, SHELF, BUBBLE_SENT, BUBBLE_GOT, SCREEN, SCREEN_INK = (
    "#fff8d8",
    "#d7e6ea",
    "#1a5fd0",
    "#e7e7ec",
    "#ffffff",
    "#15161a",
)

FLOOR_Y = 1400
FRIDGE = (800.0, 500.0, 250.0, 900.0)  # x, y, w, h
SAFE = (90.0, 380.0, 250.0, 250.0)  # x, y, w, h: above the heads, so nobody flickers past it
TABLE_TOP = 1240
PLAN = (340.0, 520.0, 400.0, 720.0)  # x, y, w, h of the table from above
SKIN = "#f3ead9"
TABLE_X = (190.0, 890.0)
LEFT_AT = (-140.0, 0.0)  # a pose here stands left of the table, facing right
RIGHT_AT = (1360.0, 0.0)  # with flip=True, a pose here stands right of the table, facing left

_STAND = STANDING["stand"]


def _arms(head, elbows, hands) -> RigPose:
    return _seat(head, _STAND.neck, _STAND.hip, _STAND.knees, _STAND.feet, elbows, hands)


# Standing poses for a kitchen argument; the near hand (a pose's second hand) is the one that holds a phone.
POSES: dict[str, RigPose] = {
    "stand": _STAND,
    "offer": _arms((548, 752), ((640, 990), (644, 960)), ((770, 950), (776, 910))),
    "plead": _arms((566, 764), ((640, 960), (640, 930)), ((770, 860), (784, 800))),
    "keep": _arms((524, 756), ((640, 960), (440, 930)), ((760, 900), (350, 780))),
    "raise": _arms((540, 750), ((470, 1020), (640, 950)), ((560, 980), (690, 800))),
    "type-a": _arms((552, 766), ((470, 1020), (640, 970)), ((600, 930), (690, 860))),
    "type-b": _arms((552, 766), ((470, 1020), (640, 970)), ((606, 948), (690, 860))),
    "push": _arms((556, 754), ((640, 1000), (650, 950)), ((770, 960), (800, 900))),
    "reach-up": _arms((552, 754), ((510, 1040), (680, 780)), ((502, 1195), (810, 610))),
    "swallow": _arms((526, 738), ((510, 1040), (640, 930)), ((502, 1195), (600, 838))),
    "cheer": _arms((540, 744), ((420, 800), (660, 800)), ((340, 610), (740, 610))),
    "pat-a": _arms((540, 760), ((440, 1040), (640, 1040)), ((444, 1190), (636, 1180))),
    "pat-b": _arms((540, 770), ((440, 1050), (640, 1050)), ((436, 1110), (644, 1100))),
    "perch": _seat(
        (540, 770),
        (540, 877),
        (540, 1215),
        ((470, 1280), (610, 1280)),
        ((480, 1530), (600, 1530)),
        ((440, 1040), (640, 1040)),
        ((466, 1200), (614, 1200)),
    ),
}


@register("location", "stick-kitchen", tags=("home", "kitchen", "domestic", "fridge"))
def kitchen(cv: Canvas, parent) -> None:
    """The kitchen, without its table: the window and its curtains, a calendar, a shut fridge, a shut safe."""
    s = _group(cv, parent)
    wall = paint(cv, Gradient("kitchen-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0, FLOOR_Y))
    box(cv, s, 0, 0, cv.width, FLOOR_Y, wall)
    box(cv, s, 0, FLOOR_Y, cv.width, cv.height - FLOOR_Y, FLOOR)
    for y in (1480, 1600, 1760):
        box(cv, s, 0, y, cv.width, 4, FLOOR_LINE)
    box(cv, s, 0, FLOOR_Y - 16, cv.width, 16, WHITE_SHADE)
    box(cv, s, 400, 170, 340, 340, SKY, 6, r=6)  # the window and its curtains
    box(cv, s, 566, 170, 8, 340, WHITE_GOODS)
    shape(cv, s, "M 380 160 L 480 160 Q 470 340 400 530 L 380 530 Z", CURTAIN)
    shape(cv, s, "M 760 160 L 660 160 Q 670 340 740 530 L 760 530 Z", CURTAIN)
    box(cv, s, 370, 516, 400, 18, WOOD_DARK)
    signature.cactus(cv, s, 700, 516, scale=0.42)
    _fridge(cv, s)
    _safe(cv, s)
    signature.code(cv, s, 40, 1885, 9, color="#6d5f49")


def _fridge(cv: Canvas, parent) -> None:
    x, y, w, h = FRIDGE
    box(cv, parent, x, y, w, h, WHITE_GOODS, 6, r=18)
    box(cv, parent, x, y + 290, w, 7, WHITE_SHADE)
    box(cv, parent, x + 22, y + 90, 16, 150, STEEL, r=8)
    box(cv, parent, x + 22, y + 340, 16, 220, STEEL, r=8)


def _safe(cv: Canvas, parent) -> None:
    x, y, w, h = SAFE
    box(cv, parent, x, y, w, h, STEEL, 6, r=10)
    box(cv, parent, x + 22, y + 22, w - 44, h - 44, STEEL_DARK, r=6)
    cx, cy = x + w / 2, y + h / 2
    oval(cv, parent, cx - 50, cy - 50, 100, 100, WHITE_SHADE)
    oval(cv, parent, cx - 30, cy - 30, 60, 60, STEEL)
    box(cv, parent, cx - 5, cy - 56, 10, 28, STEEL_DARK)


@register("prop", "stick-table", tags=("home", "kitchen", "table", "furniture"))
def table(cv: Canvas, parent) -> None:
    """The kitchen table, its top at :data:`TABLE_TOP`."""
    x0, x1 = TABLE_X
    g = _group(cv, parent)
    for x in (x0 + 34, x1 - 62):
        box(cv, g, x, TABLE_TOP + 30, 28, 420, WOOD_DARK, 5)
    box(cv, g, x0, TABLE_TOP, x1 - x0, 42, WOOD, 6, r=8)


@register("location", "stick-kitchen-plan", tags=("home", "kitchen", "overhead", "chase"))
def plan(cv: Canvas, parent) -> None:
    """The kitchen straight from above, for running round the table: the floor and the table top at :data:`PLAN`."""
    g = _group(cv, parent)
    box(cv, g, 0, 0, cv.width, cv.height, FLOOR)
    for board in range(90, 1080, 180):
        box(cv, g, board, 0, 4, cv.height, FLOOR_LINE)
    x, y, w, h = PLAN
    box(cv, g, x + 14, y + 18, w, h, "#00000044", r=12)
    box(cv, g, x, y, w, h, WOOD, 6, r=12)
    box(cv, g, x + 18, y + 18, w - 36, h - 36, WOOD_DARK, r=8, opacity=0.25)
    signature.cactus(cv, g, 540, 930, scale=0.42)
    signature.code(cv, g, 40, 1885, 9, color="#3d2c1c")


@register("prop", "stick-from-above", tags=("figure", "overhead", "chase"))
def from_above(cv: Canvas, parent, end: float, *, hair: str = "none", phone: str | None = None, rate: float = 6.0):
    """A figure seen from straight above and heading up the frame, centred on the origin: feet that step ``rate``
    times a second, shoulders, arms ahead, a head with a ``hair`` of ``none``, ``side-part`` or ``bun``, and a
    ``phone`` of that colour held out."""
    if hair not in ("none", "side-part", "bun"):
        raise StickDataError(f"from above, hair is none, side-part or bun, got {hair!r}")
    if not end > 0:
        raise StickDataError(f"a figure from above lasts some seconds, got {end!r}")
    g = _group(cv, parent)
    for side, spans in zip((-1, 1), stick_reel.turns(end, rate), strict=True):
        foot = _group(cv, g)
        cv.gate(foot, spans)
        oval(cv, foot, side * 34 - 16, -60, 32, 56, cv.ink)
    shape(cv, g, "M -66 0 L 66 0", sw=18, stroke=cv.ink)
    shape(cv, g, "M -60 0 L -40 -66 M 60 0 L 40 -66", sw=13, stroke=cv.ink)
    if phone is not None:
        box(cv, g, 22, -116, 36, 58, phone, 3, r=7)
    oval(cv, g, -48, -48, 96, 96, cv.ink)
    oval(cv, g, -41, -41, 82, 82, SKIN)
    if hair == "side-part":
        shape(cv, g, "M -40 8 A 41 41 0 0 1 40 8 Q 8 -12 -40 8 Z", cv.ink)
    elif hair == "bun":
        oval(cv, g, -17, -17, 34, 34, cv.ink)
    return g


@register("prop", "stick-fridge-open", tags=("home", "kitchen", "fridge"))
def fridge_open(cv: Canvas, parent):
    """The fridge at :data:`FRIDGE` standing open: the lit shelves, and the door swung toward the camera."""
    x, y, w, h = FRIDGE
    g = _group(cv, parent)
    box(cv, g, x, y, w, h, FRIDGE_GLOW, 6, r=10)
    for k in range(1, 4):
        box(cv, g, x + 12, y + k * h / 4, w - 24, 10, SHELF)
    box(cv, g, x + 60, y + h / 4 - 90, 60, 90, "#e7b23c", 3, r=6)  # a jar
    box(cv, g, x + 40, y + h / 2 - 70, 120, 70, "#7fae6a", 3, r=8)  # leftovers
    shape(cv, g, f"M {x} {y} L {x - 170} {y + 70} L {x - 170} {y + h + 60} L {x} {y + h} Z", WHITE_GOODS, 6,
          stroke=WHITE_SHADE)  # fmt: skip
    return g


@register("prop", "stick-safe-open", tags=("home", "safe", "valuables"))
def safe_open(cv: Canvas, parent):
    """The safe at :data:`SAFE` standing open: a dark box and its door swung back off the wall."""
    x, y, w, h = SAFE
    g = _group(cv, parent)
    box(cv, g, x, y, w, h, "#20242a", 6, r=10)
    box(cv, g, x + 14, y + h - 60, w - 28, 8, STEEL)
    shape(cv, g, f"M {x + w} {y} L {x + w + 120} {y - 34} L {x + w + 120} {y + h + 34} L {x + w} {y + h} Z", STEEL, 6,
          stroke=STEEL_DARK)  # fmt: skip
    return g


@register("prop", "stick-handset", tags=("phone", "hand", "prop"))
def handset(cv: Canvas, parent, x: float, y: float, *, colour: str = "#1f2430", lit: bool = False, scale: float = 1.0):
    """A phone a hand can hold, centred on (``x``, ``y``), in a case of ``colour``, its screen ``lit`` or dark."""
    if not (checks.number(scale) and scale > 0):
        raise StickDataError(f"a phone's scale is positive, got {scale!r}")
    w, h = 74 * scale, 138 * scale
    g = _group(cv, parent)
    box(cv, g, x - w / 2, y - h / 2, w, h, colour, 4, r=14 * scale)
    box(cv, g, x - w / 2 + 7 * scale, y - h / 2 + 8 * scale, w - 14 * scale, h - 20 * scale,
        "#dff0ff" if lit else "#39414f", r=6 * scale)  # fmt: skip
    return g


@register("prop", "stick-key", tags=("key", "safe", "small"))
def key(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0):
    """A small brass key, its bow at (``x``, ``y``)."""
    if not (checks.number(scale) and scale > 0):
        raise StickDataError(f"a key's scale is positive, got {scale!r}")
    brass = "#d9a826"
    g = _group(cv, parent)
    oval(cv, g, x - 16 * scale, y - 16 * scale, 32 * scale, 32 * scale, brass)
    oval(cv, g, x - 6 * scale, y - 6 * scale, 12 * scale, 12 * scale, "#00000000", stroke=cv.ink, sw=3)
    box(cv, g, x + 12 * scale, y - 4 * scale, 44 * scale, 8 * scale, brass)
    box(cv, g, x + 42 * scale, y + 2 * scale, 7 * scale, 10 * scale, brass)
    return g


@register("prop", "stick-reply-screen", tags=("phone", "chat", "reveal", "fullscreen"))
def reply(cv: Canvas, parent, *, name: str, sent: str, answer: str):
    """The whole frame as a chat with ``name``: the message ``sent``, and one big ``answer`` under it."""
    cv.require_font("the chat is set in it")
    if not (name.strip() and sent.strip() and answer.strip()):
        raise StickDataError("a chat needs a name, a sent message and an answer")
    g = _group(cv, parent)
    box(cv, g, 0, 0, cv.width, cv.height, SCREEN)
    box(cv, g, 0, 0, cv.width, 420, "#f2f2f6")
    oval(cv, g, 450, 130, 180, 180, "#b9bec9")
    cv.text(g, cv.uid("chat-name"), name, 240, 330, 600, 64, 48, SCREEN_INK)
    box(cv, g, 150, 560, 880, 150, BUBBLE_SENT, r=50)
    cv.text(g, cv.uid("chat-sent"), sent, 170, 602, 840, 70, 50, "#FFFFFF")
    box(cv, g, 50, 800, 950, 300, BUBBLE_GOT, r=80)
    cv.text(g, cv.uid("chat-answer"), answer, 70, 880, 910, 140, 124, SCREEN_INK)
    return g

"""The Stick style's road home: the street they never leave, the U-turn, and what they keep going back to check.

:func:`street` is the back layer of the house they live in, seen from the kerb: sky, lawn, a tree that grows, the
house with its door and its window. :func:`in_window` is a group masked to the window, and :func:`window_frame` goes
over it. :func:`side_car` is the loaded car from the side. :func:`road_plan` and :func:`top_car` are the road and the
car from straight above, for the U-turn, with a scar on the tarmac for every turn before it. :func:`stove_knob` and
:func:`door_lock` fill the frame with the thing they came back for, and :func:`road_ahead` and :func:`road_sign` are
the only sight of the airport they get. :func:`suitcases` go on the back seat. Everything is in frame pixels of the
1080 × 1920 Stick frame and nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

from . import _stick_transport_contracts as tc
from . import checks, signature
from .canvas import Canvas
from .registry import register
from .stick import Gradient, StickDataError, _group, box, oval, paint, shape

__all__ = [
    "HOUSE_WINDOW",
    "STREET_Y",
    "door_lock",
    "in_window",
    "road_ahead",
    "road_plan",
    "road_sign",
    "side_car",
    "stove_knob",
    "street",
    "suitcases",
    "top_car",
    "window_frame",
]

SKY_TOP, SKY_LOW, LAWN, LAWN_DARK, TARMAC, KERB, LINE = (
    "#86c2e6",
    "#e3f1ee",
    "#7fb35a",
    "#669645",
    "#5b5f66",
    "#b4b4ac",
    "#f2efe0",
)
WALL, ROOF, TRIM, DOOR, TRUNK, LEAF, GLASS_DARK = (
    "#e9c9a0",
    "#a0483a",
    "#fbf6ea",
    "#3f6f88",
    "#7a5536",
    "#4d8a3f",
    "#2d3a46",
)
BODY, BODY_DARK, TYRE, CASE_A, CASE_B, STEEL, ENAMEL = (
    "#c8493f",
    "#94322b",
    "#23262b",
    "#3f7f9c",
    "#d8a03c",
    "#7c8590",
    "#eef0ee",
)
SIGN_GREEN = "#14683f"

STREET_Y = 1420  # the kerb
HOUSE_WINDOW = (640.0, 720.0, 300.0, 300.0)  # x, y, w, h


@register(
    "location",
    "stick-home-street",
    contract=tc.contract('stick-home-street'),
    tags=("street", "house", "suburb", "lawn", "exterior"),
)
def street(cv: Canvas, parent, *, tree: float = 1.0) -> None:
    """The house from the kerb, its lawn and the road; ``tree`` scales the tree, which is how years show."""
    if not (checks.number(tree) and tree > 0):
        raise StickDataError(f"a tree's scale is positive, got {tree!r}")
    s = _group(cv, parent)
    box(cv, s, 0, 0, cv.width, 1000, paint(cv, Gradient("street-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, 0, 0, 1000)))
    box(cv, s, 0, 1000, cv.width, STREET_Y - 1000, LAWN)
    box(cv, s, 0, STREET_Y, cv.width, 26, KERB)
    box(cv, s, 0, STREET_Y + 26, cv.width, cv.height - STREET_Y, TARMAC)
    box(cv, s, 0, 1760, cv.width, 12, LINE)
    shape(cv, s, "M 470 520 L 1100 520 L 1100 1140 L 470 1140 Z", WALL)
    shape(cv, s, "M 420 540 L 800 250 L 1180 540 Z", ROOF, 5, stroke="#6e2f25")
    box(cv, s, 500, 800, 110, 340, DOOR, 5, r=4)
    oval(cv, s, 584, 960, 16, 16, "#e7c55a")
    box(cv, s, *HOUSE_WINDOW, GLASS_DARK, r=2)
    shape(cv, s, "M 520 1140 L 590 1140 L 360 1420 L 180 1420 Z", "#cdc6b5")
    trunk_h, crown = 360 * tree, 170 * tree
    base = 1240.0
    box(cv, s, 180 - 22 * tree, base - trunk_h, 44 * tree, trunk_h, TRUNK)
    oval(cv, s, 180 - crown, base - trunk_h - crown * 1.4, crown * 2, crown * 2.2, LEAF)
    oval(cv, s, 180 - crown * 0.5, base - trunk_h - crown * 1.2, crown * 0.8, crown * 0.8, LAWN_DARK, opacity=0.5)
    signature.cactus(cv, s, 640, 1176, scale=0.42)
    signature.code(cv, s, 40, 1885, 9, color="#d6d6d0")


def in_window(cv: Canvas, parent):
    """A group masked to :data:`HOUSE_WINDOW`: who is drawn in it stands inside the house."""
    x, y, w, h = HOUSE_WINDOW
    g = _group(cv, parent)
    g.add_mask(type="path", path=f"M {x} {y} L {x + w} {y} L {x + w} {y + h} L {x} {y + h} Z")
    return g


def window_frame(cv: Canvas, parent) -> None:
    """The frame and the bars of the window, over whoever is in it."""
    x, y, w, h = HOUSE_WINDOW
    g = _group(cv, parent)
    for bx, by, bw, bh in ((x - 12, y - 12, w + 24, 14), (x - 12, y + h - 2, w + 24, 14), (x - 12, y - 12, 14, h + 24),
                           (x + w - 2, y - 12, 14, h + 24), (x + w / 2 - 5, y, 10, h)):  # fmt: skip
        box(cv, g, bx, by, bw, bh, TRIM)


@register(
    "prop", "stick-side-car", contract=tc.contract('stick-side-car'), tags=("car", "exterior", "holiday", "luggage")
)
def side_car(cv: Canvas, parent):
    """The car from the side, nose to the right, wheels on the origin's line, with the holiday on its roof."""
    g = _group(cv, parent)
    box(cv, g, 110, -318, 190, 86, CASE_A, 5, r=10)
    box(cv, g, 310, -302, 130, 70, CASE_B, 5, r=10)
    box(cv, g, 90, -232, 400, 12, STEEL, r=4)
    shape(cv, g, "M 0 -60 L 0 -130 Q 8 -160 70 -164 L 130 -232 Q 140 -240 160 -240 L 440 -240 Q 464 -240 480 -222 "
                 "L 540 -164 Q 650 -158 680 -120 L 690 -60 Z", BODY, 6, stroke=BODY_DARK)  # fmt: skip
    shape(cv, g, "M 150 -164 L 186 -214 L 300 -214 L 300 -164 Z", GLASS_DARK)
    shape(cv, g, "M 324 -164 L 324 -214 L 440 -214 L 492 -164 Z", GLASS_DARK)
    for x in (130, 560):
        oval(cv, g, x - 62, -116, 124, 124, TYRE)
        oval(cv, g, x - 26, -80, 52, 52, STEEL)
    return g


@register("prop", "stick-suitcases", contract=tc.contract('stick-suitcases'), tags=("luggage", "holiday", "car"))
def suitcases(cv: Canvas, parent, x: float, y: float):
    """Two suitcases and a pillow stacked on the back seat, standing on (``x``, ``y``)."""
    g = _group(cv, parent)
    box(cv, g, x - 90, y - 130, 120, 130, CASE_A, 5, r=10)
    box(cv, g, x + 26, y - 100, 90, 100, CASE_B, 5, r=10)
    box(cv, g, x - 66, y - 176, 130, 46, "#f4efe4", 4, r=20)
    return g


@register("location", "stick-road-plan", contract=tc.contract('stick-road-plan'), tags=("road", "overhead", "u-turn"))
def road_plan(cv: Canvas, parent, *, scars: int = 0) -> None:
    """A road from straight above with ``scars`` skid marks already on it, one for each U-turn before this one."""
    if not (isinstance(scars, int) and 0 <= scars <= 8):
        raise StickDataError(f"a road carries 0 to 8 skid marks, got {scars!r}")
    s = _group(cv, parent)
    box(cv, s, 0, 0, cv.width, cv.height, LAWN)
    box(cv, s, 130, 0, 820, cv.height, TARMAC)
    box(cv, s, 112, 0, 18, cv.height, KERB)
    box(cv, s, 950, 0, 18, cv.height, KERB)
    for y in range(40, 1920, 200):
        box(cv, s, 530, y, 20, 110, LINE)
    for k in range(scars):
        d = 62 * k
        skid = (f"M {740 - d * 0.2} {1010 + d} Q {740 - d * 0.2} {560 + d} {540} {540 + d} "
                f"Q {340 + d * 0.2} {560 + d} {340 + d * 0.2} {1010 + d}")  # fmt: skip
        shape(cv, s, skid, None, 14, stroke="#26282c", opacity=0.55)
    signature.cactus(cv, s, 56, 1560, scale=0.42)
    signature.code(cv, s, 40, 1885, 9, color="#2d4a1e")


@register("prop", "stick-top-car", contract=tc.contract('stick-top-car'), tags=("car", "overhead", "u-turn"))
def top_car(cv: Canvas, parent):
    """The car from straight above, nose up the frame, centred on the origin, the holiday on its roof."""
    g = _group(cv, parent)
    box(cv, g, -92, -190, 184, 380, BODY, 6, r=46)
    box(cv, g, -74, -108, 148, 66, GLASS_DARK, r=14)
    box(cv, g, -74, 110, 148, 46, GLASS_DARK, r=12)
    box(cv, g, -56, -32, 66, 110, CASE_A, 4, r=8)
    box(cv, g, 14, -22, 44, 84, CASE_B, 4, r=8)
    return g


@register(
    "prop",
    "stick-stove-knob",
    contract=tc.contract('stick-stove-knob'),
    tags=("kitchen", "stove", "insert", "fullscreen"),
)
def stove_knob(cv: Canvas, parent):
    """The whole frame as the front of a stove: one great knob, turned to OFF."""
    cv.require_font("the knob's marks are set in it")
    g = _group(cv, parent)
    box(cv, g, 0, 0, cv.width, cv.height, ENAMEL)
    box(cv, g, 0, 1400, cv.width, 520, "#d7dad7")
    oval(cv, g, 240, 560, 600, 600, STEEL)
    oval(cv, g, 280, 600, 520, 520, "#2c3037")
    box(cv, g, 510, 590, 60, 250, "#f2efe0", r=20)
    cv.text(g, cv.uid("knob-off"), "OFF", 340, 370, 400, 150, 120, "#15161a")
    cv.text(g, cv.uid("knob-hi"), "HI", 830, 830, 200, 70, 56, "#3a3f47")
    return g


@register(
    "prop", "stick-door-lock", contract=tc.contract('stick-door-lock'), tags=("door", "lock", "insert", "fullscreen")
)
def door_lock(cv: Canvas, parent):
    """The whole frame as the front door: a deadbolt, thrown, and a word on it."""
    cv.require_font("the lock's mark is set in it")
    g = _group(cv, parent)
    box(cv, g, 0, 0, cv.width, cv.height, DOOR)
    box(cv, g, 90, 170, 900, 480, "#356078", r=10)
    box(cv, g, 90, 1190, 900, 480, "#356078", r=10)
    box(cv, g, 860, 0, 220, cv.height, "#d9c8a8", 6)
    box(cv, g, 360, 820, 360, 240, "#e7c55a", 6, r=24)
    box(cv, g, 690, 900, 230, 76, STEEL, 5, r=6)
    oval(cv, g, 470, 870, 140, 140, "#caa63e")
    box(cv, g, 526, 886, 28, 108, "#6e5a20", r=8)
    cv.text(g, cv.uid("lock-word"), "LOCKED", 240, 1120, 600, 110, 96, "#ffffff")
    return g


@register("location", "stick-road-ahead", contract=tc.contract('stick-road-ahead'), tags=("road", "pov", "highway"))
def road_ahead(cv: Canvas, parent) -> None:
    """The open road from the driver's seat."""
    s = _group(cv, parent)
    box(cv, s, 0, 0, cv.width, 1000, paint(cv, Gradient("ahead-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, 0, 0, 1000)))
    box(cv, s, 0, 1000, cv.width, 920, LAWN)
    shape(cv, s, "M 500 1000 L 580 1000 L 1080 1920 L 0 1920 Z", TARMAC)
    for a, b in ((1040, 1120), (1220, 1340), (1520, 1720)):
        h = (b - 1000) * 0.016
        shape(cv, s, f"M {540 - h} {a} L {540 + h} {a} L {540 + h * 1.4} {b} L {540 - h * 1.4} {b} Z", LINE)
    signature.cactus(cv, s, 90, 1480, scale=0.42)
    signature.code(cv, s, 40, 1885, 9, color="#2d4a1e")


@register("prop", "stick-road-sign", contract=tc.contract('stick-road-sign'), tags=("road", "sign", "motorway"))
def road_sign(cv: Canvas, parent, end: float, *, text: str):
    """A green motorway sign reading ``text``, coming up over the road for ``end`` seconds."""
    cv.require_font("the sign is set in it")
    if not text.strip():
        raise StickDataError("a road sign needs words")
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"a road sign lasts some seconds, got {end!r}")
    g = _group(cv, parent, x=540.0, y=930.0, scaleX=0.7, scaleY=0.7)
    for prop in ("scaleX", "scaleY"):
        cv.keys(g, prop, [(0, 0.7), (end, 1.15)], hold=False)
    for x in (-250, 230):
        box(cv, g, x, -120, 22, 520, "#6b7078")
    box(cv, g, -380, -340, 760, 300, SIGN_GREEN, 8, r=20)
    shape(cv, g, "M -300 -300 L 300 -300", None, 6, stroke="#ffffff")
    cv.text(g, cv.uid("sign-text"), text, -360, -260, 720, 150, 104, "#FFFFFF")
    return g

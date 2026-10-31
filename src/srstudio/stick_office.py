"""The Stick style's coffee corner: two coworkers, one window, and whatever the week does to them.

:func:`corner` is the back layer: the wall, the floor and the window between the two of them, with its city.
:func:`counter` goes in front of the figures, with the coffee machine on it. :func:`view` is a group masked to the
window, for what happens outside; :func:`meteor` is the only thing that does. What the weeks leave is drawn over a
figure from :data:`POSES`, at the point :func:`on_figure` finds: :func:`cast`, :func:`brace`, :func:`parrot` and
:func:`flames`, and in the end :func:`tombstone`. Figures stand with :data:`LEFT_AT` and, mirrored, :data:`RIGHT_AT`.
Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

from . import checks, signature, stick_reel
from .canvas import Canvas
from .registry import register
from .stick import STANDING, Gradient, RigPose, StickDataError, _group, _seat, box, oval, paint, shape

__all__ = [
    "COUNTER_TOP",
    "LEFT_AT",
    "POSES",
    "RIGHT_AT",
    "WINDOW",
    "brace",
    "cast",
    "corner",
    "counter",
    "flames",
    "meteor",
    "mug",
    "on_figure",
    "parrot",
    "tombstone",
    "view",
]

WALL_TOP, WALL_LOW, FLOOR, TRIM = "#dfe6e4", "#c6d1cf", "#8c8f94", "#7a8a8a"
SKY_TOP, SKY_LOW, TOWER, TOWER_FAR, LIT = "#8fc4e6", "#e6eef0", "#6f7d8c", "#a4afba", "#f6e7a8"
LAMINATE, LAMINATE_DARK, MACHINE, MACHINE_DARK, PLASTER, STONE, STONE_DARK = (
    "#e7dcc7",
    "#b9a988",
    "#3a3f47",
    "#23262b",
    "#fbfbf6",
    "#a9adb3",
    "#7d8288",
)
FIRE_OUT, FIRE_IN, ROCK, ROCK_DARK, GLOW = "#f2701d", "#ffd23c", "#5e4a3f", "#3d2f28", "#ff8a3c"

WINDOW = (330.0, 190.0, 420.0, 640.0)  # x, y, w, h of the glass
COUNTER_TOP = 1240
LEFT_AT = (-140.0, 0.0)  # a pose here stands left of the machine, facing right
RIGHT_AT = (1360.0, 0.0)  # with flip=True, a pose here stands right of it, facing left
LAND = (560.0, 720.0)  # where the meteor comes down, behind the towers

_STAND = STANDING["stand"]


def _arms(head, near_elbow, near_hand) -> RigPose:
    return _seat(head, _STAND.neck, _STAND.hip, _STAND.knees, _STAND.feet, (_STAND.elbows[0], near_elbow),
                 (_STAND.hands[0], near_hand))  # fmt: skip


# A figure with a mug; the near hand (a pose's second hand) holds it, and "sip" brings it to the mouth.
POSES: dict[str, RigPose] = {
    "stand": _STAND,
    "mug": _arms((540, 750), (610, 1070), (690, 960)),
    "sip": _arms((528, 738), (650, 960), (618, 852)),
}


def on_figure(pose: RigPose, *, at: tuple[float, float], flip: bool = False) -> dict[str, tuple[float, float]]:
    """Where a figure's parts land in the frame: ``head``, ``neck``, ``elbow`` and ``hand`` (the near arm's)."""

    def place(p) -> tuple[float, float]:
        return (at[0] - p[0] if flip else at[0] + p[0], at[1] + p[1])

    return {"head": place(pose.head), "neck": place(pose.neck), "elbow": place(pose.elbows[1]),
            "hand": place(pose.hands[1])}  # fmt: skip


@register("location", "stick-coffee-corner", tags=("office", "coffee", "work", "window"))
def corner(cv: Canvas, parent) -> None:
    """The office's coffee corner: the wall, the floor, and a tall window on the city between the two of them."""
    s = _group(cv, parent)
    wall = paint(cv, Gradient("corner-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0, 1400))
    box(cv, s, 0, 0, cv.width, 1400, wall)
    box(cv, s, 0, 1400, cv.width, cv.height - 1400, FLOOR)
    box(cv, s, 0, 1384, cv.width, 16, TRIM)
    x, y, w, h = WINDOW
    box(cv, s, x - 12, y - 12, w + 24, h + 24, TRIM, 4, r=6)
    city = view(cv, s)
    box(cv, city, x, y, w, h, paint(cv, Gradient("corner-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, y, 0, y + h)))
    for bx, by, bw in ((330, 560, 120), (440, 620, 110), (640, 540, 130)):
        box(cv, city, bx, by, bw, y + h - by, TOWER_FAR)
    for bx, by, bw in ((380, 640, 100), (600, 660, 120)):
        box(cv, city, bx, by, bw, y + h - by, TOWER)
        for wy in range(by + 24, int(y + h) - 20, 44):
            for wx in range(bx + 16, bx + bw - 24, 34):
                box(cv, city, wx, wy, 16, 22, LIT)
    box(cv, s, x + w / 2 - 5, y, 10, h, TRIM)
    signature.cactus(cv, s, 930, 720, scale=0.42)
    box(cv, s, 860, 720, 150, 14, TRIM, r=4)
    signature.code(cv, s, 40, 1885, 9, color="#4f5656")


def view(cv: Canvas, parent):
    """A group masked to :data:`WINDOW`: what is drawn in it is seen through the glass."""
    x, y, w, h = WINDOW
    g = _group(cv, parent)
    g.add_mask(type="path", path=f"M {x} {y} L {x + w} {y} L {x + w} {y + h} L {x} {y + h} Z")
    return g


@register("prop", "stick-coffee-counter", tags=("office", "coffee", "counter", "machine"))
def counter(cv: Canvas, parent):
    """The counter across the frame, in front of the figures, with the coffee machine on it."""
    g = _group(cv, parent)
    box(cv, g, 460, 1096, 160, 144, MACHINE, 5, r=14)
    box(cv, g, 482, 1112, 116, 44, "#9fd8b4", r=6)
    box(cv, g, 510, 1168, 60, 62, MACHINE_DARK, r=6)
    box(cv, g, 120, COUNTER_TOP, 840, 34, LAMINATE, 6, r=6)
    box(cv, g, 140, COUNTER_TOP + 34, 800, cv.height - COUNTER_TOP, LAMINATE_DARK, 5)
    return g


@register(
    "prop",
    "stick-mug",
    tags=("office", "coffee", "mug"),
    examples=('from srstudio import get\nmug = get("prop", "stick-mug")(ep.cv, ep.comp, 540, 960)',),
)
def mug(cv: Canvas, parent, x: float, y: float, *, colour: str = "#f4f1e8"):
    """A mug in a hand at (``x``, ``y``)."""
    g = _group(cv, parent)
    box(cv, g, x - 34, y - 40, 68, 80, colour, 5, r=10)
    shape(cv, g, f"M {x + 34} {y - 20} Q {x + 66} {y} {x + 34} {y + 20}", None, 8, stroke=cv.ink)
    return g


@register("prop", "stick-arm-cast", tags=("injury", "cast", "plaster"))
def cast(cv: Canvas, parent, elbow: tuple[float, float], hand: tuple[float, float]):
    """Plaster from ``elbow`` to ``hand``."""
    d = f"M {elbow[0]} {elbow[1]} L {hand[0]} {hand[1]}"
    g = _group(cv, parent)
    shape(cv, g, d, None, 46, stroke=cv.ink)
    shape(cv, g, d, None, 34, stroke=PLASTER)
    return g


@register("prop", "stick-neck-brace", tags=("injury", "neck", "brace"))
def brace(cv: Canvas, parent, x: float, y: float):
    """A foam collar under the chin of a head whose neck is at (``x``, ``y``)."""
    g = _group(cv, parent)
    box(cv, g, x - 66, y - 44, 132, 70, PLASTER, 5, r=26)
    box(cv, g, x - 58, y - 12, 116, 6, "#c9cbc4", r=3)
    return g


@register("prop", "stick-parrot", tags=("animal", "parrot", "bird"))
def parrot(cv: Canvas, parent, x: float, y: float, *, facing: int = -1):
    """A parrot standing at (``x``, ``y``), looking left (``facing=-1``) or right (``1``)."""
    if facing not in (-1, 1):
        raise StickDataError(f"a parrot faces -1 or 1, got {facing!r}")
    f = facing
    g = _group(cv, parent)
    shape(
        cv, g, f"M {x - f * 18} {y - 50} L {x - f * 74} {y + 30} L {x - f * 34} {y + 8} Z", "#d3392f", 4, stroke=cv.ink
    )
    oval(cv, g, x - 40, y - 96, 80, 96, "#3aa655")
    oval(cv, g, x + f * 6 - 26, y - 134, 52, 52, "#3aa655")
    oval(cv, g, x + f * 12 - 7, y - 120, 14, 14, "#ffffff")
    oval(cv, g, x + f * 15 - 4, y - 117, 8, 8, cv.ink)
    shape(
        cv, g, f"M {x + f * 28} {y - 118} Q {x + f * 58} {y - 110} {x + f * 32} {y - 92} Z", "#f0b429", 3, stroke=cv.ink
    )
    return g


def _flame(cv: Canvas, parent, x: float, y: float, h: float, lean: float) -> None:
    shape(cv, parent, f"M {x - 44} {y} Q {x - 60 + lean} {y - h * 0.5} {x + lean} {y - h} "
                      f"Q {x + 60 + lean} {y - h * 0.5} {x + 44} {y} Z", FIRE_OUT)  # fmt: skip
    shape(cv, parent, f"M {x - 22} {y} Q {x - 30 + lean} {y - h * 0.3} {x + lean * 0.6} {y - h * 0.6} "
                      f"Q {x + 30 + lean} {y - h * 0.3} {x + 22} {y} Z", FIRE_IN)  # fmt: skip


@register("prop", "stick-flames", tags=("fire", "flames", "slightly"))
def flames(cv: Canvas, parent, x: float, y: float, end: float, *, rate: float = 4.0):
    """A small fire standing on (``x``, ``y``) for ``end`` seconds, its two drawings turning ``rate`` times a second."""
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"flames last some seconds, got {end!r}")
    g = _group(cv, parent)
    for lean, spans in zip((-14, 14), stick_reel.turns(end, rate), strict=True):
        one = _group(cv, g)
        cv.gate(one, spans)
        _flame(cv, one, x, y, 120, lean)
    return g


@register("prop", "stick-tombstone", tags=("death", "grave", "stone"))
def tombstone(cv: Canvas, parent, x: float, *, words: str):
    """A headstone standing behind the counter at ``x``, cut with ``words``."""
    cv.require_font("the stone is cut in it")
    if not words.strip():
        raise StickDataError("a tombstone needs words")
    top, w = 740.0, 340.0
    g = _group(cv, parent)
    foot = COUNTER_TOP + 4
    stone = f"M {x - w / 2} {foot} L {x - w / 2} {top + 170} A {w / 2} {w / 2} 0 0 1 {x + w / 2} {top + 170} "
    shape(cv, g, stone + f"L {x + w / 2} {foot} Z", STONE, 6, stroke=STONE_DARK)
    cv.text(g, cv.uid("stone-rip"), "R.I.P.", x - 150, top + 120, 300, 60, 44, "#23262b")
    cv.text(g, cv.uid("stone-words"), words, x - 150, top + 210, 300, 96, 76, "#23262b")
    return g


@register("prop", "stick-meteor", tags=("meteor", "disaster", "sky"))
def meteor(cv: Canvas, parent, end: float, *, land: float):
    """A meteor coming down behind the towers, reaching :data:`LAND` ``land`` seconds in, then the glow it leaves.
    Draw it in :func:`view`; it is held to the window."""
    if not (checks.number(end) and checks.number(land) and 0 < land < end):
        raise StickDataError(f"a meteor lands inside its shot, got {land!r} of {end!r}")
    g = _group(cv, parent)
    x, y = LAND
    rock = _group(cv, g, x=x + 300, y=y - 620)
    cv.keys(rock, "x", [(0, x + 300), (land, x)], hold=False)
    cv.keys(rock, "y", [(0, y - 620), (land, y)], hold=False)
    cv.gate(rock, [(0, land)])
    shape(cv, rock, "M -20 -30 L 190 -240 L 50 -10 Z", FIRE_OUT, opacity=0.85)
    shape(cv, rock, "M -10 -20 L 110 -140 L 30 -6 Z", FIRE_IN)
    oval(cv, rock, -52, -52, 104, 104, ROCK)
    oval(cv, rock, -22, -24, 26, 26, ROCK_DARK)
    glow = _group(cv, g)
    cv.gate(glow, [(land, end)])
    oval(cv, glow, x - 240, y - 260, 480, 420, GLOW, opacity=0.8)
    oval(cv, glow, x - 130, y - 130, 260, 220, FIRE_IN, opacity=0.9)
    return g

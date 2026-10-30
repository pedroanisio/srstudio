"""Toon past the desk: the furniture, the outdoors and the small helpers a sketch needs when its cast leaves the office.

The desk is one stand-in among others: :data:`srstudio.toon_sketch.Staging.desk` can be :func:`no_desk`, and a shot's
``dress`` then draws what stands in front of the character, the signature (ADR 0001) on it. :func:`sofa` is a sofa
and side table that carry the character and the marks anywhere (a ground beside it says where); :func:`ledge` is a
plain counter top in the desk's place. The sets are :func:`yard`, :func:`road` and :func:`dump`.

:func:`placed` draws anything a second time at a scale, somewhere else in the frame: a far figure on a far sofa behind
the character who is talking. :func:`paw` slides an arm in from the frame's edge with something in its hand, the way
a sketch reaches into a shot its speaker is not in. :func:`gull` flies in and lands; :func:`snores` lets Zs rise.

Every measure is a reference screen pixel (:func:`srstudio.toon.fx`/``fy``), every key is on the composition clock.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from . import brush, checks, signature
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy
from .toon_rooms import LOUNGE_WALL, PILLOW, SOFA, SOFA_LIGHT, SOFA_SEAM, STRIPE
from .toon_sets import _fill, _glow, _inked, _line, _shadow

__all__ = [
    "GROUNDS",
    "GULL_FLIGHT",
    "HEAD_TOP",
    "LEAVE",
    "RoadLayers",
    "chopper",
    "dump",
    "gull",
    "hall_chair",
    "ledge",
    "lower_third",
    "mics",
    "missed_slip",
    "night_street",
    "no_desk",
    "paw",
    "placed",
    "porch",
    "press_room",
    "road",
    "snores",
    "stuck_note",
    "sofa",
    "sofa_back",
    "van",
    "wall",
    "yard",
]

Point = tuple[float, float]
HEAD_TOP = 438.0  # about where a Toon character's skull begins, reference pixels
SOFA_DARK, SOFA_DEEP = "#663d6a", "#4f2e53"
TABLE, TABLE_DARK, TABLE_LEG = "#d9a066", "#b67f4a", "#8a5c33"
SIGN_CODE = "#7a4f2c"
GROUNDS = ("rug", "bare", "lawn", "flatbed", "heap")
FLOOR, FLOOR_LINE, PATCH = "#8a5a3c", "#6f4630", "#a97c58"
RUG, RUG_BAND = "#b5413f", "#e6b450"
GRASS, GRASS_DARK, GRASS_LIGHT = "#79b857", "#5f9c45", "#9ad071"
STEEL, STEEL_DARK = "#59636e", "#3b434c"
ASPHALT, LANE = "#4a4d55", "#f1e7c6"
TYRE, HUB = "#23252b", "#b7bcc4"
TRASH, TRASH_DARK, TRASH_LIGHT = "#55535d", "#3d3b45", "#6f6d78"
LEDGE_TOP, LEDGE_FRONT, LEDGE_EDGE, LEDGE_CODE = "#c98a58", "#a96f43", "#bb7d4c", "#7a4f2c"
SKY_DAY = (("0", "#8fd0f2"), ("0.7", "#d3eefb"), ("1", "#f3fbff"))
SKY_DUSK = (("0", "#8a6f8f"), ("0.55", "#e39a7a"), ("1", "#f7cf97"))
CLOUD = "#ffffff"
SIDING, SIDING_LINE, TRIM = "#f2d7a9", "#dcbd8b", "#fff6e6"
FENCE, FENCE_SHADE = "#fbf6ec", "#d9d2c3"
HEDGE, HEDGE_DARK = "#4f9a5b", "#3c7e4a"
CASHBOX = "#3f7d6e"
SIGN_BOARD, SIGN_INK = "#fff3c9", "#b42318"
TABLETOP, TABLE_METAL = "#e9e4d8", "#8c919a"
HILL_FAR, HILL_NEAR, TREE, TREE_DARK, POST = "#9dc7c9", "#7fb58c", "#4f9a5b", "#3c7e4a", "#8a6a4a"
CAB, CAB_DARK, CAB_GLASS = "#d9534f", "#b03c39", "#bfe3ef"
BAG, BAG_DARK, BAG_LIGHT = "#2f3038", "#1f2026", "#50525c"
TIRE, CRATE, CRATE_DARK = "#26272d", "#b98a55", "#94683a"
TV_DEAD, TV_FACE_DEAD, CRACK = "#15161c", "#262a33", "#c8d6e6"
GULL_WHITE, GULL_GREY, GULL_BEAK, GULL_LEG = "#fbfbf8", "#a9b2bd", "#f0b429", "#e98a3c"
REMOTE, REMOTE_KEY = "#23252b", "#e2483d"
SNORE_INK = "#ffffff"
HELD = ("remote", "note", "keys", "torch", "")
KEY_METAL, KEY_BRASS, TORCH, TORCH_GLOW = "#c3cad3", "#e0b13e", "#3b3f4a", "#ffe680"
KEY_SWING, KEY_PERIOD = 14.0, 0.5  # degrees each way, seconds a swing
SNORE_RISE = 90.0  # how far a Z rises, reference pixels
SNORE_EVERY = 0.7  # seconds between Zs


def no_desk(cv: Canvas, parent) -> None:
    """Nothing in the desk's place: the shot's ``dress`` draws what stands in front of the character, signed."""


def placed(cv: Canvas, parent, at: Point, scale: float, draw: Callable[[object], object], pivot: Point = (185, 812)):
    """Draw ``draw(group)`` with its reference point ``pivot`` at ``at``, ``scale`` times its size."""
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"placed: scale must be positive, got {scale!r}")
    g = cv.group(parent, cv.uid("g"), scaleX=scale, scaleY=scale)
    g.anchorX, g.anchorY = fx(pivot[0]), fy(pivot[1])
    g.x, g.y = fx(at[0]), fy(at[1])
    draw(g)
    return g


# -- what stands in front of the character -----------------------------------------------------------------------------
@register("prop", "toon-sofa-back", summary="The sofa's back behind a character, for a sofa that is not in the lounge")
def sofa_back(cv: Canvas, parent) -> None:
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(-20), fy(560), fh(400), fh(250), SOFA, cv.ink, INK_W, radius=fh(30))
    _line(cv, g, [(10, 578), (180, 570), (350, 578)], 10.0, SOFA_LIGHT)
    for x in (120, 250):
        _line(cv, g, [(x, 590), (x + 2, 700), (x, 800)], FINE_W / 2, SOFA_SEAM)
    _inked(cv, g, [(298, 548), (370, 540), (378, 612), (304, 620)], PILLOW)


def _rug(cv: Canvas, g) -> None:
    cv.rect(g, fx(-10), fy(900), fh(612), fh(240), FLOOR, cv.clear, 0, radius=0)
    for y in (940, 1000, 1070):
        cv.rect(g, fx(-10), fy(y), fh(612), fh(3), FLOOR_LINE, cv.clear, 0, radius=0)
    cv.ellipse(g, fx(40), fy(960), fh(540), fh(210), RUG, cv.ink, FINE_W)
    cv.ellipse(g, fx(80), fy(980), fh(460), fh(170), cv.clear, RUG_BAND, 7.0)


def _bare(cv: Canvas, g) -> None:
    cv.rect(g, fx(-10), fy(900), fh(612), fh(240), FLOOR, cv.clear, 0, radius=0)
    cv.ellipse(g, fx(40), fy(960), fh(540), fh(210), PATCH, opacity=0.55)
    for y in (940, 1000, 1070):
        cv.rect(g, fx(-10), fy(y), fh(612), fh(3), FLOOR_LINE, cv.clear, 0, radius=0)


def _lawn(cv: Canvas, g) -> None:
    cv.rect(g, fx(-10), fy(880), fh(612), fh(260), GRASS, cv.clear, 0, radius=0)
    for i, (x, y) in enumerate(((40, 1030), (150, 1085), (300, 1040), (420, 1095), (530, 1035), (90, 960))):
        tuft = [(x - 12, y), (x - 4, y - 18), (x + 2, y), (x + 8, y - 16), (x + 14, y)]
        _line(cv, g, tuft, 4.0, GRASS_DARK if i % 2 else GRASS_LIGHT)


def _flatbed(cv: Canvas, g) -> None:
    cv.rect(g, fx(-10), fy(1070), fh(612), fh(70), ASPHALT, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(985), fh(612), fh(44), STEEL, cv.ink, FINE_W, radius=0)
    cv.rect(g, fx(-10), fy(1016), fh(612), fh(16), STEEL_DARK, cv.clear, 0, radius=0)
    for x in (120, 470):  # the wheels
        cv.ellipse(g, fx(x - 62), fy(990), fh(124), fh(124), TYRE, cv.ink, FINE_W)
        cv.ellipse(g, fx(x - 28), fy(1024), fh(56), fh(56), HUB, cv.ink, FINE_W / 2)


def _heap(cv: Canvas, g) -> None:
    cv.rect(g, fx(-10), fy(900), fh(612), fh(240), TRASH, cv.clear, 0, radius=0)
    for x, y, w, h in ((10, 1000, 170, 90), (220, 1040, 190, 80), (430, 990, 170, 100)):
        outline = [(x, y + h), (x + w * 0.2, y + 10), (x + w * 0.55, y), (x + w, y + h * 0.7), (x + w * 0.9, y + h)]
        _inked(cv, g, outline, BAG, FINE_W, 4)
        _line(cv, g, [(x + w * 0.35, y + 22), (x + w * 0.55, y + 38)], 5.0, BAG_LIGHT)


_GROUND = {"rug": _rug, "bare": _bare, "lawn": _lawn, "flatbed": _flatbed, "heap": _heap}


@register(
    "prop",
    "toon-sofa",
    summary="A sofa's seat with a side table that carries the signature, on a rug, a bare floor, a lawn, a truck's "
    "flatbed or a heap of bags",
)
def sofa(cv: Canvas, parent, ground: str = "rug", signed: bool = True) -> None:
    """The seat in front of the character, its arm, its feet and the side table on ``ground`` (:data:`GROUNDS`). The
    cactus stands on the side table and the code is on its apron: wherever the sofa goes, the marks go; a far sofa
    drawn with :func:`placed` is not ``signed``."""
    if ground not in _GROUND:
        raise ToonDataError(f"a sofa stands on one of {GROUNDS}, not {ground!r}")
    g = cv.group(parent, cv.uid("g"))
    _GROUND[ground](cv, g)
    for x in (24, 340):  # the feet
        cv.rect(g, fx(x), fy(960), fh(26), fh(32), SOFA_DEEP, cv.ink, FINE_W, radius=fh(4))
    _shadow(cv, g, 190, 992, 440, 16, 0.3)
    cv.rect(g, fx(-30), fy(866), fh(420), fh(104), SOFA_DARK, cv.ink, INK_W, radius=fh(10))
    cv.rect(g, fx(-30), fy(790), fh(400), fh(84), SOFA, cv.ink, INK_W, radius=fh(24))
    _line(cv, g, [(0, 806), (180, 800), (350, 806)], 8.0, SOFA_LIGHT)
    _line(cv, g, [(182, 796), (184, 868)], FINE_W / 2, SOFA_SEAM)
    cv.rect(g, fx(344), fy(690), fh(84), fh(282), SOFA, cv.ink, INK_W, radius=fh(34))
    _line(cv, g, [(362, 712), (384, 704), (408, 712)], 8.0, SOFA_LIGHT)
    # the side table, with the marks: the same place as on the desk (toon_everyday.SIGNATURE_BOX)
    for x in (466, 570):
        cv.rect(g, fx(x), fy(880), fh(12), fh(106), TABLE_LEG, cv.ink, FINE_W / 2, radius=0)
    _shadow(cv, g, 524, 988, 150, 10, 0.3)
    cv.rect(g, fx(452), fy(848), fh(146), fh(40), TABLE_DARK, cv.ink, FINE_W, radius=0)
    cv.rect(g, fx(446), fy(832), fh(158), fh(20), TABLE, cv.ink, FINE_W, radius=fh(4))
    if signed:
        signature.cactus(cv, g, fx(536), fy(832), 0.7)
        signature.code(cv, g, fx(572), fy(866), 14, color=SIGN_CODE, opacity=0.9, align="end")


@register("prop", "toon-worktop", summary="A plain counter top in the desk's place, no laptop, signed as the desk is")
def ledge(cv: Canvas, parent, top: str = LEDGE_TOP, front: str = LEDGE_FRONT, code: str = LEDGE_CODE) -> None:
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(-10), fy(848), fh(612), fh(300), front, cv.clear, 0, radius=0)
    for x, w in ((-30, 200), (190, 200), (410, 200)):  # its doors, so the band is furniture and not a wall
        cv.rect(g, fx(x), fy(886), fh(w), fh(212), front, code, FINE_W / 2, radius=fh(6))
        cv.ellipse(g, fx(x + w - 34), fy(980), fh(14), fh(14), top, code, FINE_W / 3)
    cv.rect(g, fx(-10), fy(801), fh(612), fh(47), cv.ink, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(813), fh(612), fh(31), top, cv.clear, 0, radius=0)
    signature.cactus(cv, g, fx(548), fy(838), 0.7)
    signature.code(cv, g, fx(580), fy(866), 14, color=code, opacity=0.9, align="end")


@register(
    "location", "toon-far-wall", summary="The lounge's teal wall and floor, seen from the TV: room for a far sofa"
)
def wall(cv: Canvas, parent) -> None:
    g = cv.group(parent, cv.uid("g"))
    paint = cv.grad("toon-lounge-wall", [(float(o), c) for o, c in LOUNGE_WALL], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, paint)
    for x in range(24, 592, 48):
        cv.rect(g, fx(x), 0, fh(6), cv.height, STRIPE, opacity=0.3)
    cv.rect(g, fx(-10), fy(820), fh(612), fh(330), FLOOR, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(812), fh(612), fh(10), TRIM, cv.ink, FINE_W / 2, radius=0)


# -- the outdoors --------------------------------------------------------------------------------------------------
def _sky(cv: Canvas, g, name: str, stops) -> None:
    paint = cv.grad(name, [(float(o), c) for o, c in stops], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, paint)


def _cloud(cv: Canvas, g, x: float, y: float, s: float = 1.0) -> None:
    for dx, dy, r in ((0, 0, 34), (38, -14, 42), (82, 0, 32)):
        cv.ellipse(g, fx(x + dx * s - r * s), fy(y + dy * s - r * s), fh(2 * r * s), fh(2 * r * s), CLOUD, opacity=0.92)


def _sign(cv: Canvas, g, text: str, x: float, y: float, w: float, h: float, size: int) -> None:
    _shadow(cv, g, x + w / 2, y + h + 150, 40, 6, 0.25)
    cv.rect(g, fx(x + w / 2 - 7), fy(y + h - 2), fh(14), fh(150), POST, cv.ink, FINE_W, radius=0)
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), SIGN_BOARD, cv.ink, INK_W, radius=fh(6))
    cv.text(g, cv.uid("sign"), text, fx(x + 8), fy(y + 6), int(fh(w - 16)), int(fh(h - 12)), size, color=SIGN_INK)


@register(
    "location",
    "toon-yard",
    summary="A front yard on a bright day: a house, a picket fence, a YARD SALE sign and a folding table holding "
    "the room's own TV",
)
def yard(cv: Canvas, parent, sign: str | None = "YARD SALE", table: bool = True) -> None:
    """The sky, a clapboard house at the left, the fence and hedge, the lawn, the sign at the right unless ``sign`` is
    None and, unless a far sofa stands there, the ``table`` with what has been sold from the house on it."""
    g = cv.group(parent, cv.uid("g"))
    _sky(cv, g, "toon-yard-sky", SKY_DAY)
    _cloud(cv, g, 420, 190)
    _cloud(cv, g, 250, 130, 0.7)
    cv.rect(g, fx(-10), fy(250), fh(330), fh(420), SIDING, cv.ink, INK_W, radius=0)
    for y in range(280, 660, 34):
        cv.rect(g, fx(-10), fy(y), fh(326), fh(4), SIDING_LINE, cv.clear, 0, radius=0)
    _inked(cv, g, [(-20, 262), (160, 150), (346, 262)], "#b45f4e")
    cv.rect(g, fx(-10), fy(600), fh(612), fh(310), GRASS, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(560), fh(612), fh(52), HEDGE, cv.clear, 0, radius=fh(20))
    for x in range(330, 600, 34):
        _inked(cv, g, [(x, 640), (x, 574), (x + 12, 556), (x + 24, 574), (x + 24, 640)], FENCE, FINE_W, 2)
    cv.rect(g, fx(322), fy(590), fh(280), fh(12), FENCE_SHADE, cv.ink, FINE_W / 2, radius=0)
    # the table with the TV on it, and the sign on its post behind it
    if sign is not None:
        _sign(cv, g, sign, 382, 372, 198, 104, 66)
    if not table:
        return
    _shadow(cv, g, 485, 792, 230, 12, 0.25)
    for x in (398, 566):
        _line(cv, g, [(x, 722), (x + (10 if x < 480 else -10), 792)], 6.0, TABLE_METAL)
    cv.rect(g, fx(420), fy(622), fh(130), fh(86), TV_DEAD, cv.ink, INK_W, radius=fh(6))
    cv.rect(g, fx(430), fy(632), fh(110), fh(66), TV_FACE_DEAD, radius=fh(3))
    cv.rect(g, fx(376), fy(706), fh(218), fh(18), TABLETOP, cv.ink, FINE_W, radius=fh(3))


class RoadLayers:
    """How fast :func:`road`'s planes pass, in reference pixels per second, far to near (hand-drawn parallax)."""

    HILLS = 40.0
    TREES = 220.0
    POSTS = 900.0


def _drift(cv: Canvas, g, speed: float, start: float, end: float) -> None:
    cv.keys(g, "x", [(start, 0.0), (end, -fh(speed * (end - start)))], hold=False)


@register(
    "location",
    "toon-road",
    summary="A highway seen from the moving truck: sky, hills, trees and fence posts passing at their own speeds, "
    "the truck's cab beside the load",
)
def road(cv: Canvas, parent, start: float = 0.0, end: float = 4.0, cab: bool = True) -> None:
    """The planes scroll from ``start`` to ``end``, each drawn far enough for its speed, the cab at the right."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a road scrolls over 0 <= start < end, got {start!r}..{end!r}")
    span = end - start
    g = cv.group(parent, cv.uid("g"))
    _sky(cv, g, "toon-road-sky", SKY_DAY)
    _cloud(cv, g, 120, 190, 0.8)
    _cloud(cv, g, 430, 150)
    hills = cv.group(g, cv.uid("g"))
    for i in range(int(RoadLayers.HILLS * span / 260) + 3):
        x = -100 + 260 * i
        _fill_hill(cv, hills, x, 640, 320, 170, HILL_FAR)
    _drift(cv, hills, RoadLayers.HILLS, start, end)
    trees = cv.group(g, cv.uid("g"))
    cv.rect(trees, fx(-10), fy(640), fh(612 + RoadLayers.TREES * span + 40), fh(90), HILL_NEAR, cv.clear, 0, radius=0)
    for i in range(int(RoadLayers.TREES * span / 120) + 7):
        x = -40 + 120 * i + (i % 3) * 16
        cv.rect(trees, fx(x + 18), fy(600), fh(12), fh(60), POST, cv.clear, 0, radius=0)
        cv.ellipse(
            trees, fx(x - 8), fy(520 + (i % 2) * 18), fh(64), fh(96), TREE if i % 2 else TREE_DARK, cv.ink, FINE_W
        )
    _drift(cv, trees, RoadLayers.TREES, start, end)
    cv.rect(g, fx(-10), fy(720), fh(612), fh(330), ASPHALT, cv.clear, 0, radius=0)
    posts = cv.group(g, cv.uid("g"))
    for i in range(int(RoadLayers.POSTS * span / 170) + 7):
        x = -20 + 170 * i
        cv.rect(posts, fx(x), fy(640), fh(14), fh(96), FENCE, cv.ink, FINE_W, radius=0)
    cv.rect(posts, fx(-30), fy(660), fh(612 + RoadLayers.POSTS * span + 60), fh(12), FENCE_SHADE, cv.ink, FINE_W / 2,
            radius=0)  # fmt: skip
    _drift(cv, posts, RoadLayers.POSTS, start, end)
    if cab:
        _cab(cv, g)


def _cab(cv: Canvas, g) -> None:
    """The truck's cab, square as a truck's, its nose past the frame's edge."""
    cv.rect(g, fx(452), fy(420), fh(16), fh(150), STEEL_DARK, cv.ink, FINE_W, radius=0)  # the exhaust stack
    cv.rect(g, fx(474), fy(530), fh(170), fh(440), CAB, cv.ink, INK_W, radius=fh(8))
    cv.rect(g, fx(498), fy(556), fh(146), fh(120), CAB_GLASS, cv.ink, FINE_W, radius=fh(4))
    cv.rect(g, fx(474), fy(720), fh(170), fh(14), CAB_DARK, cv.clear, 0, radius=0)
    cv.rect(g, fx(498), fy(690), fh(4), fh(250), CAB_DARK, cv.clear, 0, radius=0)
    cv.rect(g, fx(520), fy(748), fh(46), fh(12), HUB, cv.ink, FINE_W / 2, radius=fh(3))


def _fill_hill(cv: Canvas, g, x: float, y: float, w: float, h: float, colour: str) -> None:
    d = f"M {fx(x):.1f} {fy(y):.1f} Q {fx(x + w / 2):.1f} {fy(y - 2 * h):.1f} {fx(x + w):.1f} {fy(y):.1f} Z"
    cv.path(g, d, fill=colour, stroke=cv.clear, sw=0)


def _mound(cv: Canvas, g, points: Sequence[Point], colour: str) -> None:
    _inked(cv, g, points, colour, FINE_W, 4)


@register(
    "location",
    "toon-dump",
    summary="A landfill at dusk: heaps of bags, a tyre, a crate and, at the right, a dead TV with a cracked screen",
)
def dump(cv: Canvas, parent) -> None:
    """A dusk sky, the far heap, gulls far off; on the mound at the right, where a lounge's TV hangs, the dead TV."""
    g = cv.group(parent, cv.uid("g"))
    _sky(cv, g, "toon-dump-sky", SKY_DUSK)
    _glow(cv, g, "toon-dump-sun", 330, 470, 210, "#fff0b8")
    for x, y in ((90, 250), (150, 320), (500, 215)):
        _line(cv, g, [(x - 18, y - 6), (x - 8, y - 12), (x, y), (x + 8, y - 12), (x + 18, y - 6)], 4.0, "#4a3b52")
    _mound(cv, g, [(-30, 760), (60, 520), (200, 470), (330, 540), (420, 500), (620, 640), (620, 780)], TRASH_DARK)
    for x, y in ((70, 590), (180, 520), (300, 590), (440, 560), (530, 640)):
        _inked(cv, g, [(x - 34, y + 30), (x - 14, y - 12), (x + 22, y - 16), (x + 40, y + 28)], BAG, FINE_W, 4)
        _line(cv, g, [(x - 8, y), (x + 8, y + 12)], 4.0, BAG_LIGHT)
    # the near mound under the TV, the crate and the tyre
    _mound(cv, g, [(360, 900), (392, 520), (580, 470), (640, 480), (640, 900)], TRASH)
    cv.rect(g, fx(528), fy(610), fh(84), fh(70), CRATE, cv.ink, FINE_W, radius=0)
    for y in (630, 652):
        cv.rect(g, fx(528), fy(y), fh(84), fh(5), CRATE_DARK, cv.clear, 0, radius=0)
    cv.ellipse(g, fx(420), fy(640), fh(86), fh(86), TIRE, cv.ink, FINE_W)
    cv.ellipse(g, fx(446), fy(666), fh(34), fh(34), TRASH)
    # the TV, where it hung in the lounge
    _shadow(cv, g, 485, 474, 210, 10, 0.35)
    cv.rect(g, fx(380), fy(330), fh(210), fh(138), TV_DEAD, cv.ink, INK_W, radius=fh(8))
    cv.rect(g, fx(392), fy(342), fh(186), fh(114), TV_FACE_DEAD, radius=fh(3))
    for crack in (
        ((470, 390), (430, 348)),
        ((470, 390), (548, 352)),
        ((470, 390), (410, 444)),
        ((470, 390), (520, 450)),
    ):
        _line(cv, g, list(crack), 3.5, CRACK)


# -- what moves in a shot ---------------------------------------------------------------
GULL_FLIGHT = 0.5  # seconds it flies in


def _gull_body(cv: Canvas, g, flap: float | None) -> None:
    """A gull in profile, facing left, its feet at the group's origin; ``flap`` lifts the wing (None: folded)."""

    def at(points: Sequence[Point]) -> list[Point]:
        return [(x + 200, y + 200) for x, y in points]

    for dx in (-8, 8):
        _line(cv, g, at([(dx, -22), (dx, 0)]), 4.0, GULL_LEG)
    _inked(cv, g, at([(-58, -52), (-30, -22), (24, -18), (72, -36), (20, -58), (-20, -66)]), GULL_WHITE, FINE_W, 3)
    _inked(cv, g, at([(-78, -98), (-58, -112), (-34, -102), (-20, -62), (-54, -56)]), GULL_WHITE, FINE_W, 3)
    _inked(cv, g, at([(-76, -98), (-104, -90), (-76, -88)]), GULL_BEAK, FINE_W / 2, 1)
    cv.ellipse(g, fx(200 - 62), fy(200 - 106), fh(9), fh(9), cv.ink)
    wing = (
        [(-8, -50), (46, -30), (84, -22), (20, -60)]
        if flap is None
        else [(-8, -52), (30, -46 - flap), (70, -70 - flap), (24, -66)]
    )
    _inked(cv, g, at(wing), GULL_GREY, FINE_W, 3)


@register("prop", "toon-gull", summary="A seagull that flies in from the frame's top right and lands, then stands")
def gull(cv: Canvas, parent, at: Point = (165.0, HEAD_TOP), land: float = 0.5, end: float = 4.0) -> None:
    """The gull lands on ``at`` (where its feet stand) at ``land`` seconds and stays to ``end``."""
    if not (checks.number(land) and checks.number(end) and GULL_FLIGHT <= land < end):
        raise ToonDataError(f"a gull needs {GULL_FLIGHT} s to fly in before it lands: {land!r}, {end!r}")
    x, y = fx(at[0] - 200), fy(at[1] - 200) - fy(0)
    flying = cv.group(parent, cv.uid("g"), start=land - GULL_FLIGHT, end=land)
    cv.keys(flying, "x", [(land - GULL_FLIGHT, x + fh(420)), (land, x)], hold=False)
    cv.keys(flying, "y", [(land - GULL_FLIGHT, y - fh(330)), (land, y)], hold=False)
    _gull_body(cv, flying, 34.0)
    standing = cv.group(parent, cv.uid("g"), start=land, end=end, x=x, y=y)
    _gull_body(cv, standing, None)


@register("prop", "toon-paw", summary="An arm in the colour of a character's coat that slides in holding something")
def paw(
    cv: Canvas,
    parent,
    spans: Sequence[tuple[float, float]] = ((0.0, 2.0),),
    coat: str = "#e8e4ec",
    side: float = 1.0,
    y: float = 640.0,
    reach: float = 300.0,
    holding: str = "remote",
    presses: Sequence[float] = (),
    slide: float = 0.16,
) -> None:
    """For each ``(start, end)`` the arm comes in from the right edge (``side`` 1) at height ``y``, ``reach`` pixels
    into the frame over ``slide`` seconds, holds, and leaves, with what it is ``holding`` in its hand, jabbing forward
    at each of ``presses``."""
    if holding not in HELD:
        raise ToonDataError(f"a paw holds one of {HELD}, not {holding!r}")
    if side not in (1.0, -1.0):
        raise ToonDataError(f"a paw comes in from the right (1) or the left (-1), not {side!r}")
    for start, end in spans:
        if not (checks.number(start) and checks.number(end) and 0 <= start and start + 2 * slide <= end):
            raise ToonDataError(f"a paw needs {2 * slide} s for each span, got {start!r}..{end!r}")
        outer = cv.group(parent, cv.uid("g"), start=start, end=end)
        off = fh(side * reach)
        cv.keys(outer, "x", [(start, off), (start + slide, 0.0), (end - slide, 0.0), (end, off)], hold=False)
        g = cv.group(outer, cv.uid("g"))
        jabs = [t for t in presses if start <= t < end]
        if jabs:
            cv.keys(g, "x", [(0.0, 0.0), *((k, v) for t in jabs for k, v in ((t, -fh(16)), (t + 0.1, 0.0)))])
        edge = 620.0 if side > 0 else -30.0
        tip = edge - side * reach
        arm = [(edge + side * 40, y + 40), (edge - side * reach * 0.5, y + 16), (tip + side * 26, y)]
        _fill(cv, g, _stroke(arm, 62.0), cv.ink)
        _fill(cv, g, _stroke(arm, 50.0), coat)
        cv.ellipse(g, fx(tip - 16), fy(y - 34), fh(68), fh(68), coat, cv.ink, FINE_W * 1.4)
        if holding == "remote":
            cv.rect(g, fx(tip - 84), fy(y - 18), fh(120), fh(36), REMOTE, cv.ink, FINE_W, radius=fh(8))
            cv.ellipse(g, fx(tip - 76), fy(y - 7), fh(14), fh(14), REMOTE_KEY)
        elif holding == "note":
            cv.rect(
                g, fx(tip - 76 if side > 0 else tip + 20), fy(y - 44), fh(88), fh(88), SLIP, cv.ink, FINE_W, radius=0
            )
        elif holding == "keys":
            _keys(cv, g, tip - 4, y + 22, start, end)
        elif holding == "torch":
            _torch(cv, g, tip, y)


def _keys(cv: Canvas, g, x: float, y: float, start: float, end: float) -> None:
    """A ring of keys hanging from ``(x, y)``, swinging from the first frame of its span."""
    swing = cv.group(g, cv.uid("g"), x=fx(x), y=fy(y), anchorX=fx(x), anchorY=fy(y))
    keys: list[tuple[float, float]] = []
    t = start
    while t < end:
        keys += [(round(t, 3), -KEY_SWING), (round(t + KEY_PERIOD / 2, 3), KEY_SWING)]
        t += KEY_PERIOD
    cv.keys(swing, "rotation", keys, hold=False)
    cv.ellipse(swing, fx(x - 22), fy(y), fh(44), fh(44), cv.clear, KEY_METAL, fh(7))
    for dx, length, colour in ((-16, 72, KEY_METAL), (6, 88, KEY_BRASS), (20, 60, KEY_METAL)):
        cv.rect(swing, fx(x + dx - 6), fy(y + 40), fh(12), fh(length), colour, cv.ink, FINE_W * 0.6, radius=fh(4))
        cv.ellipse(swing, fx(x + dx - 13), fy(y + 30), fh(26), fh(26), colour, cv.ink, FINE_W * 0.6)


def _torch(cv: Canvas, g, x: float, y: float) -> None:
    """A flashlight aimed at the viewer: a barrel in the hand and the lens's glare."""
    _glow(cv, g, cv.uid("toon-torch-glare"), x - 70, y, 110, TORCH_GLOW)
    cv.rect(g, fx(x - 70), fy(y - 22), fh(96), fh(44), TORCH, cv.ink, FINE_W, radius=fh(8))
    cv.ellipse(g, fx(x - 92), fy(y - 34), fh(44), fh(68), "#fff7c8", cv.ink, FINE_W)


def _stroke(points: Sequence[Point], width: float):

    return brush.stroke(points, width, brush.EVEN)


@register("prop", "toon-snores", summary="Zs that rise and fade from a sleeper's mouth")
def snores(
    cv: Canvas, parent, spans: Sequence[tuple[float, float]] = ((0.0, 2.0),), at: Point = (300.0, 520.0)
) -> None:
    """A Z every :data:`SNORE_EVERY` seconds through each span, rising :data:`SNORE_RISE` pixels from ``at``."""
    for a, b in spans:
        t = a
        while t < b:
            stop = min(t + 1.2, b)
            z = cv.group(parent, cv.uid("g"), start=t, end=stop)
            x, y = at[0], at[1]
            size = 34.0
            d = (f"M {fx(x):.1f} {fy(y):.1f} L {fx(x + size):.1f} {fy(y):.1f} L {fx(x):.1f} {fy(y + size):.1f} "
                 f"L {fx(x + size):.1f} {fy(y + size):.1f}")  # fmt: skip
            cv.path(z, d, fill=None, stroke=cv.ink, sw=fh(11))
            cv.path(z, d, fill=None, stroke=SNORE_INK, sw=fh(5))
            cv.keys(z, "y", [(t, 0.0), (stop, -fh(SNORE_RISE))], hold=False)
            cv.keys(z, "x", [(t, 0.0), (stop, fh(26))], hold=False)
            cv.keys(z, "opacity", [(t, 0.0), (t + 0.15, 1.0), (stop - 0.25, 1.0), (stop, 0.0)], hold=False)
            t += SNORE_EVERY


# -- the night a mother calls it in ---------------------------------------------------------------------------------
STREET_SKY = (("0", "#0f1630"), ("0.6", "#232c55"), ("1", "#3b3a63"))
STREET_HOUSE, STREET_WINDOW, STREET_KERB, STREET_ROAD = "#1c2342", "#f7cf67", "#3a3f5c", "#2a2e45"
FIGURE, FIGURE_LIGHT = "#10142a", "#ffe680"
CROWD: tuple[Point, ...] = ((30, 700), (338, 716), (392, 690), (446, 716), (500, 690), (554, 716), (368, 660))
READ, WALK = 0.85, 0.3  # seconds a figure reads its phone, then takes to walk out of the street
LEAVE = READ + WALK
BACKDROP, BACKDROP_LIGHT, STAGE = "#27407a", "#35549a", "#1e2c52"
FLAG_RED, FLAG_PALE = "#c8473f", "#eef1f7"
LIVE_RED, THIRD_BG, THIRD_TEXT = "#d92c2c", "#fbfbf8", "#17203a"
FLASH = 0.09  # seconds a press camera's flash lasts
THIRD_TOP, THIRD_H = 906.0, 76.0  # on the lectern's front, under its top and over its code
ROTOR, HULL, BEAM = "#0d1020", "#171b33", "#fff3b0"


@register(
    "location", "toon-night-street", summary="A night street of dark houses; a crowd holds its lights and walks away"
)
def night_street(cv: Canvas, parent, leave: Sequence[float] = (), end: float = 4.0, said: str = "home") -> None:
    """Houses against the night and the street's crowd, each figure with its light; the figures named by ``leave``
    (seconds, left to right, as many as it lists) get ``said`` on their phones and walk out."""
    if len(leave) > len(CROWD):
        raise ToonDataError(f"the street holds {len(CROWD)} figures, {len(leave)} cannot leave")
    if any(not (checks.number(t) and 0 <= t and t + LEAVE <= end) for t in leave):
        raise ToonDataError(f"a figure needs {LEAVE} s to leave before {end!r}: {leave!r}")
    g = cv.group(parent, cv.uid("g"))
    _sky(cv, g, "toon-street-sky", STREET_SKY)
    for hx, hy, w, h in ((-20, 470, 220, 250), (215, 420, 190, 300), (420, 480, 210, 240)):
        cv.rect(g, fx(hx), fy(hy), fh(w), fh(h), STREET_HOUSE, cv.ink, FINE_W, radius=0)
        for wx in (hx + 40, hx + 120):
            cv.rect(g, fx(wx), fy(hy + 60), fh(44), fh(56), STREET_WINDOW, cv.ink, FINE_W / 2, radius=0, opacity=0.8)
    cv.rect(g, fx(-10), fy(716), fh(612), fh(30), STREET_KERB, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(746), fh(612), fh(400), STREET_ROAD, cv.clear, 0, radius=0)
    for i, (x, y) in enumerate(CROWD):
        gone = leave[i] if i < len(leave) else None
        figure = cv.group(g, cv.uid("g"), end=None if gone is None else gone + LEAVE)
        cv.ellipse(figure, fx(x - 19), fy(y - 96), fh(38), fh(38), FIGURE, cv.ink, FINE_W / 2)
        cv.rect(figure, fx(x - 25), fy(y - 60), fh(50), fh(90), FIGURE, cv.ink, FINE_W / 2, radius=fh(16))
        cv.ellipse(figure, fx(x + 12), fy(y - 44), fh(22), fh(22), FIGURE_LIGHT)
        if gone is not None:
            way = -fh(620) if x < 296 else fh(620)
            cv.keys(figure, "x", [(gone + READ, 0.0), (gone + LEAVE, way)], hold=False)
            lit = cv.group(figure, cv.uid("g"), start=gone, end=gone + READ)
            left, top = min(max(x - 44, 4), 500), y - 152 - (i % 3) * 52
            cv.rect(lit, fx(left), fy(top), fh(88), fh(44), "#ffffff", cv.ink, FINE_W / 2, radius=fh(14))
            cv.text(
                lit,
                cv.uid("ping"),
                said,
                fx(left),
                fy(top + 2),
                int(fh(88)),
                int(fh(40)),
                40,
                color="#000000",
                wrap="none",
            )


@register("location", "toon-press-room", summary="A press conference: curtain, flags, stage, flashes, a LIVE bug")
def press_room(cv: Canvas, parent, flashes: Sequence[float] = (), live: bool = True) -> None:
    """A briefing room's curtain with two plain flags and, at each of ``flashes``, a press camera firing."""
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, BACKDROP)
    for x in range(12, 600, 62):
        cv.rect(g, fx(x), 0, fh(22), cv.height, BACKDROP_LIGHT, opacity=0.5)
    for x in (28, 512):
        cv.rect(g, fx(x), fy(350), fh(8), fh(470), POST, cv.ink, FINE_W / 2, radius=0)
        cv.rect(g, fx(x + 8), fy(362), fh(62), fh(150), FLAG_RED, cv.ink, FINE_W, radius=0)
        cv.rect(g, fx(x + 8), fy(412), fh(62), fh(50), FLAG_PALE, cv.ink, FINE_W / 2, radius=0)
    cv.rect(g, fx(-10), fy(800), fh(612), fh(340), STAGE, cv.clear, 0, radius=0)
    if live:
        cv.rect(g, fx(452), fy(116), fh(112), fh(42), LIVE_RED, cv.ink, FINE_W / 2, radius=fh(6))
        cv.text(g, cv.uid("live"), "LIVE", fx(452), fy(118), int(fh(112)), int(fh(38)), 44, color=cv.white)
    for i, t in enumerate(flashes):
        x = 60 + (i * 197) % 470
        y = 560 + (i * 83) % 200
        pop = cv.group(g, cv.uid("g"), start=t, end=t + FLASH)
        cv.ellipse(pop, fx(x - 70), fy(y - 70), fh(140), fh(140), "#ffffff", opacity=0.85)


@register("prop", "toon-mics", summary="A bunch of microphones on the lectern, aimed at whoever stands behind it")
def mics(cv: Canvas, parent, x: float = 185.0, top: float = 730.0) -> None:
    g = cv.group(parent, cv.uid("g"))
    for dx, colour in ((-70, "#3a3f4b"), (-24, "#c8473f"), (24, "#2f6bb0"), (70, "#3a3f4b")):
        _line(cv, g, [(x + dx * 1.2, 812), (x + dx, top + 34)], 7.0, "#23252b")
        cv.rect(g, fx(x + dx - 16), fy(top), fh(32), fh(50), colour, cv.ink, FINE_W, radius=fh(12))


@register(
    "graphic", "toon-lower-third", summary="A news strap on the lectern's front, its text changing at given times"
)
def lower_third(
    cv: Canvas, parent, spans: Sequence[tuple[float, float, str]], measure: Callable[..., float], size: int = 40
) -> None:
    """Each ``(start, end, text)`` is one strap across the frame."""
    for start, end, text in spans:
        if not text.strip() or measure(text, size) > cv.width * 0.86:
            raise ToonDataError(f"a lower third holds one short line that fits the frame, not {text!r}")
        g = cv.group(parent, cv.uid("g"), start=start, end=end)
        cv.rect(g, fx(-10), fy(THIRD_TOP), fh(612), fh(THIRD_H), THIRD_BG, cv.ink, FINE_W, radius=0)
        cv.rect(g, fx(-10), fy(THIRD_TOP), fh(26), fh(THIRD_H), LIVE_RED, cv.clear, 0, radius=0)
        cv.text(g, cv.uid("strap"), text, fx(26), fy(THIRD_TOP + 6), int(fh(556)), int(fh(THIRD_H - 12)), size,
                color=THIRD_TEXT, wrap="none")  # fmt: skip


@register("prop", "toon-chopper", summary="A helicopter in the window with a searchlight that sweeps the room")
def chopper(cv: Canvas, parent, start: float = 0.0, end: float = 3.0, sky: Point = (480.0, 400.0), over=None) -> None:
    """From ``start`` it flies in to hover at ``sky``, rotor flickering; a pale patch sweeps the frame until ``end``,
    in ``over`` (a group in front of the character) when there is one."""
    if not (checks.number(start) and checks.number(end) and 0 <= start and start + 1.0 <= end):
        raise ToonDataError(f"a helicopter needs a second from {start!r} to {end!r}")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    craft = cv.group(g, cv.uid("g"))
    cv.keys(craft, "x", [(start, fh(320)), (start + 0.6, 0.0)], hold=False)
    x, y = sky
    cv.ellipse(craft, fx(x - 52), fy(y - 22), fh(104), fh(50), HULL, cv.ink, FINE_W)
    cv.rect(craft, fx(x + 44), fy(y - 8), fh(84), fh(12), HULL, cv.ink, FINE_W / 2, radius=0)
    cv.rect(craft, fx(x - 8), fy(y - 38), fh(16), fh(18), ROTOR, cv.clear, 0, radius=0)
    blade = cv.group(craft, cv.uid("g"), x=fx(x), y=fy(y - 40), anchorX=fx(x), anchorY=fy(y - 40))
    t, keys = start, []
    while t < end:
        keys += [(round(t, 3), 1.0), (round(t + 0.05, 3), 0.25)]
        t += 0.1
    cv.keys(blade, "scaleX", keys)
    cv.rect(blade, fx(x - 110), fy(y - 44), fh(220), fh(7), ROTOR, cv.clear, 0, radius=fh(3))
    sweep = cv.group(cv.group(over if over is not None else parent, cv.uid("g"), start=start, end=end), cv.uid("g"))
    t, keys, side = start, [], 0
    while t < end:
        keys.append((round(t, 3), fh(-40 if side else 300)))
        t += 0.8
        side = 1 - side
    cv.keys(sweep, "x", keys, hold=False)
    _glow(cv, sweep, cv.uid("toon-chopper-beam"), 150, 620, 300, BEAM)


# -- a parcel that never comes --------------------------------------------------------------------------------------
CHAIR, CHAIR_DARK = "#c0793f", "#8e5729"
PORCH_DOOR, PORCH_TRIM, MAT = "#3f7d6e", "#fff6e6", "#8a6a4a"
VAN, VAN_DARK, VAN_GLASS = "#f4f4f0", "#c9cbc6", "#3a4a58"
SLIP, SLIP_EDGE, SLIP_HEAD, SLIP_INK = "#fff3a3", "#d9b84a", "#b42318", "#1a1a1a"
SLIP_FLOOR, SLIP_BOARD, SLIP_BACK = "#a9774a", "#8a5c33", "#1c1420"
SLIP_SLIDE = 0.7


@register("prop", "toon-hall-chair", summary="A plain wooden chair back behind whoever sits on it")
def hall_chair(cv: Canvas, parent) -> None:
    g = cv.group(parent, cv.uid("g"))
    for x in (20, 322):
        cv.rect(g, fx(x), fy(400), fh(28), fh(420), CHAIR, cv.ink, FINE_W, radius=fh(6))
    for y in (420, 500):
        cv.rect(g, fx(20), fy(y), fh(330), fh(44), CHAIR, cv.ink, FINE_W, radius=fh(6))
        _line(cv, g, [(36, y + 34), (334, y + 34)], 5.0, CHAIR_DARK)


@register("location", "toon-porch", summary="A clapboard wall and a front door from outside, a mat at its foot")
def porch(cv: Canvas, parent) -> None:
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, SIDING)
    for y in range(90, 800, 40):
        cv.rect(g, fx(-10), fy(y), fh(612), fh(5), SIDING_LINE, cv.clear, 0, radius=0)
    cv.rect(g, fx(338), fy(250), fh(262), fh(552), PORCH_TRIM, cv.ink, INK_W, radius=0)
    cv.rect(g, fx(362), fy(274), fh(240), fh(528), PORCH_DOOR, cv.ink, FINE_W, radius=0)
    cv.rect(g, fx(396), fy(320), fh(170), fh(180), PORCH_DOOR, HEDGE_DARK, FINE_W, radius=0)
    cv.ellipse(g, fx(376), fy(540), fh(22), fh(22), "#c9a23c", cv.ink, FINE_W / 2)
    cv.rect(g, fx(350), fy(780), fh(250), fh(24), MAT, cv.ink, FINE_W / 2, radius=fh(4))


@register("prop", "toon-van", summary="A plain white van driving away down the street, getting smaller")
def van(cv: Canvas, parent, start: float = 0.0, end: float = 2.0, at: Point = (440.0, 660.0)) -> None:
    """The van's back from ``start``, leaving past the frame's right as it shrinks until ``end``."""
    if not (checks.number(start) and checks.number(end) and 0 <= start and start + 0.3 <= end):
        raise ToonDataError(f"a van drives off over 0.3 s at least, got {start!r}..{end!r}")
    cx, cy = fx(at[0]), fy(at[1])
    g = cv.group(parent, cv.uid("g"), start=start, end=end, x=cx, y=cy, anchorX=cx, anchorY=cy)
    for prop in ("scaleX", "scaleY"):
        cv.keys(g, prop, [(start, 1.0), (end, 0.25)], hold=False)
    cv.keys(g, "x", [(start, cx), (end, cx + fh(90))], hold=False)
    x, y = at
    for wheel in (x - 62, x + 38):
        cv.rect(g, fx(wheel), fy(y + 44), fh(26), fh(38), TIRE, cv.ink, FINE_W / 2, radius=fh(6))
    cv.rect(g, fx(x - 84), fy(y - 92), fh(168), fh(144), VAN, cv.ink, INK_W, radius=fh(14))
    cv.rect(g, fx(x - 66), fy(y - 74), fh(58), fh(56), VAN_GLASS, cv.ink, FINE_W, radius=fh(4))
    cv.rect(g, fx(x + 8), fy(y - 74), fh(58), fh(56), VAN_GLASS, cv.ink, FINE_W, radius=fh(4))
    cv.rect(g, fx(x - 84), fy(y + 26), fh(168), fh(26), VAN_DARK, cv.ink, FINE_W, radius=fh(4))


@register("prop", "toon-missed-slip", summary="A delivery slip sliding out from under a door until it fills the frame")
def missed_slip(cv: Canvas, parent, text: str = "Sorry we missed you.", start: float = 0.0, end: float = 1.6) -> None:
    """From ``start`` to ``end`` the foot of a door and the floor, the slip coming out of the gap at the viewer until
    it can be read: draw it before the ledge that signs the shot."""
    if not text.strip() or len(text) > 40:
        raise ToonDataError(f"a slip holds 1 to 40 characters, got {text!r}")
    if not (checks.number(start) and checks.number(end) and 0 <= start and start + SLIP_SLIDE < end):
        raise ToonDataError(f"a slip needs {SLIP_SLIDE} s to arrive, got {start!r}..{end!r}")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    cv.rect(g, 0, 0, cv.width, cv.height, SLIP_FLOOR)
    for y in range(280, 800, 110):
        cv.rect(g, fx(-10), fy(y), fh(612), fh(5), SLIP_BOARD, cv.clear, 0, radius=0)
    cx, cy = fx(296), fy(500)
    slip = cv.group(g, cv.uid("g"), x=cx, y=cy, anchorX=cx, anchorY=cy)
    for prop in ("scaleX", "scaleY"):
        cv.keys(slip, prop, [(start, 0.2), (start + SLIP_SLIDE, 1.0)], hold=False)
    cv.keys(slip, "y", [(start, cy - fh(330)), (start + SLIP_SLIDE, cy)], hold=False)
    cv.rect(slip, fx(46), fy(280), fh(500), fh(440), SLIP, SLIP_EDGE, INK_W, radius=fh(10))
    words = cv.group(slip, cv.uid("g"), start=start + SLIP_SLIDE)  # blank while the door's edge is over it
    cv.text(words, cv.uid("slip"), text, fx(76), fy(330), int(fh(440)), int(fh(340)), 118, color=SLIP_HEAD, wrap="word")
    cv.rect(g, fx(-10), 0, fh(612), fy(190), PORCH_DOOR, cv.ink, INK_W, radius=0)
    cv.rect(g, fx(-10), fy(186), fh(612), fh(16), SLIP_BACK, cv.clear, 0, radius=0)


@register("prop", "toon-stuck-note", summary="A yellow note with words on it, on someone's forehead or in their lap")
def stuck_note(
    cv: Canvas,
    parent,
    text: str = "Sorry we missed you.",
    start: float = 0.0,
    stuck: float | None = None,
    at: Point = (185.0, 500.0),
    reach: float = 350.0,
) -> None:
    """Shown from ``start`` and left there, tipped a little. With ``stuck`` it comes in from ``reach`` pixels to the
    right and arrives at that second, blank until it does, so it can ride a :func:`paw`."""
    if not text.strip() or len(text) > 40:
        raise ToonDataError(f"a note holds 1 to 40 characters, got {text!r}")
    if not (checks.number(start) and start >= 0) or (
        stuck is not None and not (checks.number(stuck) and stuck > start)
    ):
        raise ToonDataError(f"a note goes on at a second, got {start!r}, {stuck!r}")
    x, y = at
    outer = cv.group(parent, cv.uid("g"), start=start)
    if stuck is not None:
        cv.keys(outer, "x", [(start, fh(reach)), (stuck, 0.0)], hold=False)
    g = cv.group(outer, cv.uid("g"), x=fx(x), y=fy(y), anchorX=fx(x), anchorY=fy(y), rotation=-5)
    cv.rect(g, fx(x - 92), fy(y - 66), fh(184), fh(132), SLIP, cv.ink, INK_W, radius=fh(6))
    words = cv.group(g, cv.uid("g"), start=start if stuck is None else stuck)
    cv.text(
        words, cv.uid("note"), text, fx(x - 82), fy(y - 58), int(fh(164)), int(fh(116)), 54, color=SLIP_INK, wrap="word"
    )

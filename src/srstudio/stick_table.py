"""The Stick style's table for two: two people sat at the ends of it, and what lands on it.

:func:`seats` draws a wooden chair each side with its shadow, :func:`table` the kitchen table narrowed to stand between
them, its top at :data:`TOP`, and it goes over the figures, so their knees run under it. Figures posed from
:data:`POSES` sit at :data:`LEFT_AT` and, mirrored, at :data:`RIGHT_AT`; ``"up"`` stands the same figure beside its
chair. :func:`clipboard` is held by a hand, edge on as its reader sees it or turned flat to the viewer, and
:func:`board_in_hand` puts it and the :func:`pen` in a posed figure's hands;
:func:`wall_brackets` are two brackets on a wall with nothing on them yet, :func:`folded_bedding` a pillow on a folded
duvet, which can slide along a table. Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is
random, so a shot redraws the same.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from . import checks, stick_home
from .canvas import Canvas
from .registry import register
from .stick import RigKey, RigPose, StickDataError, _group, _seat, box, forearm, held, oval, shape

__all__ = [
    "BOARD_LETTERS",
    "BRACKET_DROP",
    "EDGE_SPAN",
    "HAND_CLEAR",
    "LEFT_AT",
    "ON_PAGE",
    "PEN_SPAN",
    "PEN_WIDTH",
    "POSES",
    "RIGHT_AT",
    "SHUT",
    "TABLE_X",
    "TOP",
    "board_in_hand",
    "clipboard",
    "folded_bedding",
    "pen",
    "seats",
    "table",
    "wall_brackets",
]

BOARD, BOARD_EDGE, PAGE, RULE, CLIP, TAIL = "#a9794a", "#7c5532", "#fbf8f0", "#b9b4a8", "#70777f", "#c8362b"
PILLOW, PILLOW_SHADE, DUVET, DUVET_DARK = "#f1eee6", "#cfcabb", "#6f8fb3", "#4f6d90"
BRACKET, PENCIL, SHADOW = "#7c8590", "#8f7f66", "#3a2a1c"
BOARD_LETTERS = 16  # the longest heading the turned clipboard takes
EDGE_SPAN = (-8.0, 46.0)  # where the edge-on clipboard runs across, about the hand that holds it
PEN_SPAN = (-14.0, 64.0)  # where the pen runs across, about the hand that holds it
PEN_WIDTH = 10  # the pen's stroke
HAND_CLEAR = 10.0  # the least gap from the board to the pen hand, which the rig draws under the board
SHUT = ("guard", "up")  # the poses that hold the clipboard edge on
ON_PAGE = ("board", "read", "write-a", "write-b", "click")  # the poses with the pen hand over the board's face
BRACKET_DROP = 96  # how far a wall bracket hangs below its top
TOP = 1090.0  # the table's top, in frame pixels
TABLE_X = (281.0, 799.0)  # where it runs, left to right
FLOOR = 1560.0  # where the feet and the chairs stand
LEFT_AT, RIGHT_AT = (-70.0, -130.0), (1150.0, -130.0)  # the second figure with flip=True
CHAIRS = (196.0, 884.0)  # the chairs' middles
RISE = 190.0  # how much taller than the stick-chair these stand, to a seat under the hips
_HIP, _KNEES, _FEET = (300, 1338), ((505, 1352), (530, 1336)), ((492, 1690), (520, 1700))


def _sit(head, neck, far_elbow, near_elbow, far_hand, near_hand) -> RigPose:
    return _seat(head, neck, _HIP, _KNEES, _FEET, (far_elbow, near_elbow), (far_hand, near_hand))


_REST = ((440, 1190), (470, 1200), (520, 1214), (560, 1220))
_BOARD = ((440, 1140), (450, 1170), (494, 1120), (525, 1200))  # the pen near the page, the board on the table


# Hands on the table; half out of the chair; a hand at the collar; up straight; looking back over the shoulder; leaning
# in; sunk; a hand out on the table. With a clipboard: read, the pen on the page in two frames, clicked, thrown out to
# point, the board pulled in to the chest with the pen laid along it from the hand; and stood up, the board under the
# near arm. Through ON_PAGE the far hand is on the board's face, where board_in_hand draws its forearm over the board.
POSES: dict[str, RigPose] = {
    "rest": _sit((372, 905), (352, 1012), *_REST),
    "landing": _seat((346, 846), (330, 954), (292, 1262), ((500, 1300), (526, 1290)), _FEET,
                     ((430, 1120), (460, 1130)), ((520, 1210), (556, 1210))),
    "tug-a": _sit((372, 903), (352, 1010), (440, 1190), (470, 1120), (520, 1214), (398, 1046)),
    "tug-b": _sit((378, 897), (354, 1006), (440, 1190), (476, 1104), (520, 1214), (416, 1030)),
    "straight": _sit((362, 890), (348, 1000), (440, 1186), (470, 1196), (520, 1214), (560, 1216)),
    "back": _sit((350, 905), (346, 1012), *_REST),
    "lean": _sit((438, 925), (392, 1026), (480, 1190), (510, 1196), (560, 1214), (600, 1214)),
    "sunk": _sit((388, 940), (360, 1044), (440, 1200), (470, 1206), (520, 1216), (556, 1218)),
    "hand-out": _sit((376, 912), (354, 1016), (440, 1190), (500, 1204), (520, 1214), (620, 1216)),
    "board": _sit((372, 905), (352, 1012), *_BOARD),
    "read": _sit((386, 920), (358, 1020), *_BOARD),
    "write-a": _sit((390, 924), (360, 1024), (434, 1100), (450, 1170), (500, 1056), (525, 1200)),
    "write-b": _sit((390, 924), (360, 1024), (438, 1110), (450, 1170), (510, 1078), (525, 1200)),
    "click": _sit((372, 905), (352, 1012), (440, 1110), (450, 1170), (486, 1040), (525, 1200)),
    "point": _sit((384, 900), (358, 1008), (480, 958), (450, 1170), (566, 900), (525, 1200)),
    "guard": _sit((360, 906), (346, 1012), (356, 1130), (404, 1176), (398, 1044), (428, 1168)),
    "up": _seat((404, 640), (404, 747), (404, 1075), ((386, 1330), (424, 1330)), ((372, 1690), (430, 1700)),
                ((340, 900), (470, 900)), ((352, 1060), (470, 1030))),
}  # fmt: skip


@register("prop", "stick-clipboard", tags=("clipboard", "form", "official", "collections", "font"))
def clipboard(cv: Canvas, parent, *, turned: bool = False, quarter: bool = False, heading: str = "SIGN HERE"):
    """A clipboard about its origin, the hand that holds it: edge on, as its reader sees the page and no one else does;
    ``quarter``, angled so the viewer sees a page of notes and cannot read them; or ``turned`` flat to the viewer:
    ``heading``, ruled lines, a row of four boxes and a line to sign on."""
    if turned and quarter:
        raise StickDataError("a clipboard is turned or at a quarter, not both")
    if quarter:
        g = _group(cv, parent)
        shape(cv, g, "M -52 -216 L 52 -240 L 52 18 L -52 46 Z", BOARD, 5, stroke=cv.ink)
        shape(cv, g, "M -40 -198 L 40 -216 L 40 4 L -40 28 Z", PAGE, 3, stroke=BOARD_EDGE)
        for ry in (-160, -124, -88, -52, -16):
            shape(cv, g, f"M -28 {ry} q 14 -8 26 -6 q 12 -8 28 -8", sw=5, stroke=RULE)
        box(cv, g, -18, -250, 36, 30, CLIP, 4, r=4)
        return g
    if not turned:
        g = _group(cv, parent)
        shape(cv, g, "M -8 -210 L 34 -226 L 34 16 L -8 40 Z", BOARD, 5, stroke=cv.ink)
        shape(cv, g, "M 34 -226 L 46 -220 L 46 14 L 34 16 Z", BOARD_EDGE, 3, stroke=cv.ink)
        box(cv, g, 2, -240, 26, 30, CLIP, 4, r=4)
        return g
    cv.require_font("the clipboard's page is set in it")
    if not heading.strip() or len(heading) > BOARD_LETTERS:
        raise StickDataError(f"a clipboard's heading is 1 to {BOARD_LETTERS} letters, got {heading!r}")
    g = _group(cv, parent)
    box(cv, g, -150, -320, 300, 380, BOARD, 6, r=16)
    box(cv, g, -126, -286, 252, 326, PAGE, 3, r=4)
    box(cv, g, -44, -340, 88, 42, CLIP, 5, r=8)
    cv.text(g, cv.uid("clipboard-heading"), heading, -120, -274, 240, 74, 46, cv.ink, weight=700)
    for ry in (-186, -160, -134):
        shape(cv, g, f"M -104 {ry} L 104 {ry}", sw=5, stroke=RULE)
    for k in range(4):
        box(cv, g, -104 + k * 56, -112, 40, 40, PAGE, 4)
    shape(cv, g, "M -104 -2 L 104 -2", sw=5, stroke=cv.ink)
    shape(cv, g, "M -104 -32 L -84 -12 M -84 -32 L -104 -12", sw=6, stroke=TAIL)
    return g


def pen(cv: Canvas, parent):
    """A red pen about its origin, the hand that holds it, running out by :data:`PEN_SPAN`."""
    return shape(cv, parent, f"M {PEN_SPAN[0]:g} 6 L {PEN_SPAN[1]:g} -14", sw=PEN_WIDTH, stroke=TAIL)


def board_in_hand(
    cv: Canvas,
    parent,
    keys: Sequence[RigKey],
    end: float,
    *,
    tilt: Mapping[str, float] | None = None,
    poses: Mapping[str, RigPose] = POSES,
    at: tuple[float, float] = (0.0, 0.0),
    scale: float = 1.0,
    flip: bool = False,
) -> None:
    """The clipboard in the near hand and the pen in the far one, drawn over a figure :func:`~srstudio.stick.rig` has
    already posed with the same ``keys``, ``poses``, ``at``, ``scale`` and ``flip``. The board is at a quarter, or edge
    on through :data:`SHUT`; ``tilt`` turns the pen by pose, in degrees, and a pose it leaves out holds it level. The
    rig is under the board, so through :data:`ON_PAGE` the far forearm comes over its face to the pen."""
    tilt = tilt or {}
    hand = held(cv, parent, keys, end, poses=poses, at=at, scale=scale, flip=flip)
    spans = [(k.start, keys[i + 1].start if i + 1 < len(keys) else end) for i, k in enumerate(keys)]
    shut = [span for span, k in zip(spans, keys, strict=True) if k.pose in SHUT]
    edge, page = cv.group(hand, cv.uid("board-edge")), cv.group(hand, cv.uid("board-page"))
    cv.gate(edge, shut or [(0, 0.0)])
    cv.gate(page, [span for span, k in zip(spans, keys, strict=True) if k.pose not in SHUT] or [(0, 0.0)])
    clipboard(cv, edge)
    clipboard(cv, page, quarter=True)
    forearm(cv, parent, keys, end, over=ON_PAGE, poses=poses, far=True, at=at, scale=scale, flip=flip)
    held_pen = cv.group(
        held(cv, parent, keys, end, poses=poses, far=True, at=at, scale=scale, flip=flip), cv.uid("pen")
    )
    if len({tilt.get(k.pose, 0.0) for k in keys}) > 1:
        cv.keys(held_pen, "rotation", [(k.start, tilt.get(k.pose, 0.0)) for k in keys])
    else:
        held_pen.rotation = tilt.get(keys[0].pose, 0.0)
    pen(cv, held_pen)


def table(cv: Canvas, parent) -> None:
    """The kitchen table (``stick-table``) over :data:`TABLE_X`, its top at :data:`TOP`, on the floor the chairs use."""
    stick_home.table(cv, parent, span=TABLE_X, top=TOP, legs=FLOOR - 20.0 - TOP - 30.0)


def seats(cv: Canvas, parent) -> None:
    """A chair each side of the table, each with its back away from it, and their shadows on the floor."""
    for x in CHAIRS:
        oval(cv, parent, x - 150, FLOOR - 22, 300, 44, SHADOW, opacity=0.28)
    stick_home.chair(cv, parent, CHAIRS[0], FLOOR, rise=RISE, flip=True)
    stick_home.chair(cv, parent, CHAIRS[1], FLOOR, rise=RISE)


@register("prop", "stick-wall-brackets", tags=("shelf", "home", "diy", "unfinished", "wall"))
def wall_brackets(cv: Canvas, parent, x: float, y: float, *, span: float = 190.0, scale: float = 1.0):
    """Two steel shelf brackets on a wall with nothing on them, the first's top at ``x, y`` and the other ``span`` to
    its right, a pencilled level line running between them: a shelf that has been about to go up for some time."""
    if not (checks.number(span) and span > 0):
        raise StickDataError(f"the brackets' span is positive, got {span!r}")
    if not (checks.number(scale) and scale > 0):
        raise StickDataError(f"a bracket's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    shape(cv, g, f"M -46 -2 L {span + 74} -2", sw=3, stroke=PENCIL)
    for dx in (0.0, span):
        path = (
            f"M {dx} 0 L {dx + 74} 0 L {dx + 74} 16 L {dx + 20} 16 Q {dx + 14} 62 {dx + 14} {BRACKET_DROP} "
            f"L {dx} {BRACKET_DROP} Z"
        )
        shape(cv, g, path, BRACKET, 4, stroke=cv.ink)
    return g


def _check_slide(slide: Sequence[tuple[float, float]]) -> None:
    times = [key[0] for key in slide]
    if len(slide) == 1 or any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise StickDataError(f"a slide runs through at least two rising (second, x) keys, got {slide!r}")


@register("prop", "stick-folded-bedding", tags=("home", "bed", "sofa", "pillow", "duvet", "reveal"))
def folded_bedding(
    cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0, slide: Sequence[tuple[float, float]] = ()
):
    """A pillow on a folded duvet, the stack's foot centred on ``x, y``. ``slide`` keys its ``x`` (second on the shot
    clock, px), easing out into its stop: a stack that comes along a table and stops where it is meant to."""
    if not (checks.number(scale) and scale > 0):
        raise StickDataError(f"the bedding's scale is positive, got {scale!r}")
    _check_slide(slide)
    g = _group(cv, parent, x=slide[0][1] if slide else x, y=y, scaleX=scale, scaleY=scale)
    if slide:
        cv.keys(g, "x", list(slide), kind="cubic-out")
    box(cv, g, -120, -44, 240, 44, DUVET, 4, r=14)
    box(cv, g, -116, -86, 232, 44, DUVET_DARK, 4, r=14)
    shape(cv, g, "M -92 -86 Q -112 -148 -40 -146 L 60 -146 Q 118 -146 96 -86 Z", PILLOW, 4, stroke=cv.ink)
    shape(cv, g, "M -60 -104 Q 0 -94 62 -106", sw=4, stroke=PILLOW_SHADE)
    return g

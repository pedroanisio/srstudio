"""The Stick style's classroom on parent-teacher night: the room, the tiny chair, the teacher's desk and the essay.

:func:`classroom` is the back layer: a primary-school wall with an alphabet strip, a chalkboard lettered ``board``,
the class's drawings pinned up, a clock and a linoleum floor. :func:`tiny_chair` is a child's plastic chair at the
left, drawn before the parent who perches on it in a :data:`PERCHED` pose (hip on the low seat, knees above it).
:func:`teacher_desk` is the front layer at the right, drawn after the teacher so it hides her legs; she stands
mirrored at :data:`TEACHER_AT` in a :data:`TEACHER_POSES` pose, and in a :data:`READING` pose :func:`held` is where
the page in her hands goes. :func:`essay` is the page itself: a ruled sheet with its title and author, the lines
read so far (``shown``), a highlighter sweeping the line being read (``mark``), a grade and a margin note, and the
child's crayon drawing of his dad. Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is
random, so a shot redraws the same.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import partial

from . import look, signature
from .canvas import Canvas
from .registry import register
from .stick import STANDING, Gradient, RigPose, StickDataError, _group, _seat, box, oval, paint, shape

__all__ = [
    "BOARD_CHARS",
    "DESK_TOP",
    "DESK_X",
    "ESSAY_LINES",
    "FLOOR_FEET",
    "LINE_CHARS",
    "NOTE_CHARS",
    "PERCHED",
    "READING",
    "SEAT_Y",
    "SHEET",
    "SWEEP",
    "TEACHER_AT",
    "TEACHER_POSES",
    "classroom",
    "essay",
    "held",
    "teacher_desk",
    "tiny_chair",
]

WALL_TOP, WALL_LOW, SKIRTING, FLOOR, TILE = "#f6e7b8", "#ecd89a", "#9a7b4f", "#c9d3c4", "#b3bfae"
BOARD_GREEN, BOARD_FRAME, CHALK = "#2f5d4a", "#8a5a33", "#f2f2ea"
CHAIR, CHAIR_DARK, DESK, DESK_FRONT, DESK_EDGE = "#f2994a", "#c9732c", "#b98a58", "#9c6f41", "#d9b383"
PAPER, RULE, MARGIN, PENCIL, RED, HIGHLIGHT = "#fffdf6", "#a9c6e8", "#e58c8c", "#2f3a66", "#c0392b", "#ffe24d"
CRAYON = ("#e74c3c", "#2e86de", "#27ae60", "#f39c12")
FLOOR_Y = 1480
FLOOR_FEET = 1700  # where a STANDING or PERCHED figure's feet are
SEAT_Y = 1500  # the top of the tiny chair's seat: half a grown-up's hip height
BOARD = (120, 300, 840, 330)  # x, y, w, h of the chalkboard inside its frame
BOARD_CHARS = 22
DESK_X = (600, 1080)  # the teacher's desk, from its left end to past the frame
DESK_TOP = 1190  # a STANDING teacher behind it shows from the waist up
TEACHER_AT = (1420.0, 0.0)  # with flip=True a STANDING pose here stands behind the desk, facing the parent
SHEET = (90, 300, 900, 1180)  # x, y, w, h of the essay page at full size
ESSAY_LINES, LINE_CHARS, NOTE_CHARS = 6, 48, 24
LINE_TOP, LINE_STEP, LINE_W = 470, 132, 720  # the lines' slots on the page
SWEEP = 0.4  # seconds the highlighter takes across a line

# The parent on the tiny chair, facing right: the hip on the seat, the knees up above it, the feet on the floor.
PERCHED: dict[str, RigPose] = {
    "perch": _seat((296, 1060), (290, 1167), (300, 1500), ((495, 1410), (510, 1420)), ((505, 1700), (530, 1700)),
                   ((400, 1310), (420, 1320)), ((488, 1400), (508, 1408))),
    "perch-lean": _seat((360, 1086), (340, 1190), (302, 1500), ((495, 1410), (510, 1420)), ((505, 1700), (530, 1700)),
                        ((430, 1320), (450, 1326)), ((488, 1400), (508, 1408))),
    "perch-shrug": _seat((300, 1066), (290, 1170), (300, 1500), ((495, 1410), (510, 1420)), ((505, 1700), (530, 1700)),
                         ((196, 1258), (392, 1258)), ((160, 1160), (430, 1160))),
    "perch-point": _seat((304, 1062), (292, 1168), (300, 1500), ((495, 1410), (510, 1420)), ((505, 1700), (530, 1700)),
                         ((400, 1310), (420, 1236)), ((488, 1400), (548, 1140))),
    "perch-face": _seat((290, 1072), (288, 1176), (300, 1500), ((495, 1410), (510, 1420)), ((505, 1700), (530, 1700)),
                        ((400, 1310), (420, 1262)), ((488, 1400), (366, 1122))),
}  # fmt: skip

# The teacher holding the page at her chest, or lowered; in the pose's own frame, facing right before the flip.
READING: dict[str, RigPose] = {
    "read": _seat((548, 756), (540, 857), (540, 1190), ((525, 1445), (560, 1445)), ((512, 1700), (566, 1700)),
                  ((566, 1084), (600, 1090)), ((640, 1006), (668, 1000))),
    "lower": _seat((536, 750), (540, 857), (540, 1190), ((525, 1445), (560, 1445)), ((512, 1700), (566, 1700)),
                   ((524, 1060), (560, 1070)), ((610, 1150), (636, 1144))),
}  # fmt: skip
TEACHER_POSES: dict[str, RigPose] = {**STANDING, **READING}


def held(pose: str) -> tuple[float, float]:
    """Where the page is, in frame pixels, in the hands of the teacher at :data:`TEACHER_AT` in a :data:`READING`
    pose: midway between her hands."""
    if pose not in READING:
        raise StickDataError(f"the teacher holds the page in a reading pose ({', '.join(READING)}), got {pose!r}")
    hands = READING[pose].hands
    return TEACHER_AT[0] - (hands[0][0] + hands[1][0]) / 2, (hands[0][1] + hands[1][1]) / 2


_label = partial(look.text, weight=700, lines=1, line_height="1.15", overflow="ellipsis")


@register("location", "stick-classroom", tags=("school", "classroom", "parent-teacher", "chalkboard", "font"))
def classroom(cv: Canvas, parent, *, board: str = "PARENT-TEACHER NIGHT") -> None:
    """A primary-school classroom: the wall and its alphabet strip, the chalkboard lettered ``board`` (1 to
    :data:`BOARD_CHARS` characters, in chalk), the class's crayon drawings pinned up, the clock and the linoleum
    floor. The code sits on the floor's near edge (ADR 0001)."""
    cv.require_font("the chalkboard is set in it")
    if not board.strip() or len(board) > BOARD_CHARS:
        raise StickDataError(f"the board has 1 to {BOARD_CHARS} characters, got {board!r}")
    s = cv
    box(s, parent, 0, 0, s.width, FLOOR_Y, paint(s, Gradient("class-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0,
                                                             FLOOR_Y)))  # fmt: skip
    for i, letters in enumerate(("Aa", "Bb", "Cc", "Dd", "Ee", "Ff")):  # the alphabet strip
        x = 40 + i * 146
        box(s, parent, x, 150, 130, 110, "#ffffff", 3, r=10)
        _label(s, parent, letters, x, 150, 130, 110, 64, CRAYON[i % len(CRAYON)])
    x, y, w, h = BOARD
    box(s, parent, x - 22, y - 22, w + 44, h + 44, BOARD_FRAME, 4, r=8)
    box(s, parent, x, y, w, h, BOARD_GREEN)
    for sx, sy, ex in ((160, 560, 420), (520, 590, 900)):  # old chalk, half rubbed out
        shape(s, parent, f"M {sx} {sy} Q {(sx + ex) / 2} {sy - 24} {ex} {sy}", sw=8, stroke=CHALK, opacity=0.18)
    _label(s, parent, board, x + 20, y + 40, w - 40, 140, 66, CHALK)
    shape(s, parent, f"M {x + 220} {y + 200} L {x + w - 220} {y + 200}", sw=6, stroke=CHALK, opacity=0.8)
    box(s, parent, x - 22, y + h + 22, w + 44, 20, BOARD_FRAME, 3)  # the chalk tray
    box(s, parent, x + 60, y + h + 12, 40, 12, CHALK)
    # the class's drawings: a house, a sun, a cat, each on its sheet
    for i, (px, tilt) in enumerate(((40, -4), (270, 3), (500, -2))):
        g = _group(s, parent, x=px + 110, y=820, rotation=tilt)
        box(s, g, -110, -90, 220, 180, "#ffffff", 3)
        oval(s, g, -8, -100, 16, 16, RED)  # the pin
        c = CRAYON[i]
        if i == 0:
            shape(s, g, "M -60 60 L -60 -5 L 0 -55 L 60 -5 L 60 60 Z", sw=6, stroke=c)
            box(s, g, -14, 20, 28, 40, c)
        elif i == 1:
            oval(s, g, -40, -40, 80, 80, CRAYON[3])
            for k in range(8):
                a = k * math.pi / 4
                shape(s, g, f"M {55 * math.cos(a):.0f} {55 * math.sin(a):.0f} L {75 * math.cos(a):.0f} "
                            f"{75 * math.sin(a):.0f}", sw=6, stroke=CRAYON[3])  # fmt: skip
        else:
            oval(s, g, -50, -20, 100, 70, c, sw=4, stroke=s.ink)
            shape(s, g, "M -40 -10 L -30 -45 L -15 -18 M 40 -10 L 30 -45 L 15 -18", sw=6, stroke=s.ink)
    # the clock
    oval(s, parent, 920, 140, 130, 130, "#ffffff", sw=6, stroke=s.ink)  # top right, clear of the teacher's head
    shape(s, parent, "M 985 205 L 985 165 M 985 205 L 1015 220", sw=7, stroke=s.ink)
    box(s, parent, 0, FLOOR_Y - 26, s.width, 26, SKIRTING)
    box(s, parent, 0, FLOOR_Y, s.width, 1920 - FLOOR_Y, FLOOR)
    for yy in (1540, 1620, 1730, 1860):
        shape(s, parent, f"M 0 {yy} L {s.width} {yy}", sw=3, stroke=TILE)
    for xx in range(-400, 1600, 200):
        shape(s, parent, f"M {540 + (xx - 540) * 0.4:.0f} {FLOOR_Y} L {xx} 1920", sw=3, stroke=TILE)
    signature.code(s, parent, 40, 1880, 9, color="#7a8577")


@register("prop", "stick-tiny-chair", tags=("school", "chair", "child-size"))
def tiny_chair(cv: Canvas, parent):
    """A child's plastic chair at the left, its seat at :data:`SEAT_Y`: draw it before the grown-up perched on it."""
    s = cv
    g = _group(s, parent)
    shape(s, g, f"M 186 1300 L 214 1300 L 226 {SEAT_Y} L 198 {SEAT_Y} Z", CHAIR, 4, stroke=s.ink)  # the back
    box(s, g, 176, 1290, 60, 70, CHAIR, 4, r=12)
    for x0, x1 in ((214, 206), (398, 410)):  # the legs splay to the floor
        shape(s, g, f"M {x0} {SEAT_Y + 20} L {x1} {FLOOR_FEET}", sw=14, stroke=CHAIR_DARK)
    box(s, g, 196, SEAT_Y, 230, 26, CHAIR, 4, r=8)
    return g


@register("prop", "stick-teacher-desk", tags=("school", "desk", "apple", "front-layer"))
def teacher_desk(cv: Canvas, parent):
    """The teacher's desk at the right, from :data:`DESK_X` at :data:`DESK_TOP`: drawn after the teacher, it hides her
    legs. On it, a stack of marked papers, an apple and the cactus (ADR 0001)."""
    s = cv
    g = _group(s, parent)
    left, right = DESK_X
    box(s, g, left, DESK_TOP + 30, right - left, 1700 - DESK_TOP - 30, DESK_FRONT, 4)
    for yy in (DESK_TOP + 160, DESK_TOP + 330):
        shape(s, g, f"M {left + 30} {yy} L {right} {yy}", sw=4, stroke=s.ink, opacity=0.35)
    box(s, g, left - 20, DESK_TOP, right - left + 40, 34, DESK_EDGE, 4, r=6)
    shape(s, g, f"M {left - 10} 1716 L {right} 1716", sw=18, stroke="#000000", opacity=0.18)
    for i in range(3):  # the marked papers
        box(s, g, 900 + i * 4, DESK_TOP - 18 - i * 10, 150, 14, PAPER, 2)
    oval(s, g, 680, DESK_TOP - 70, 74, 70, RED, sw=4, stroke=s.ink)
    shape(s, g, f"M 717 {DESK_TOP - 70} L 722 {DESK_TOP - 92}", sw=6, stroke="#6b4a2b")
    shape(s, g, f"M 722 {DESK_TOP - 86} Q 744 {DESK_TOP - 100} 752 {DESK_TOP - 82}", "#3f8f3f", 3, stroke=s.ink)
    signature.cactus(s, g, 830, DESK_TOP - 60, scale=0.3)
    return g


def _check_essay(lines, title, shown, mark, mark_at, grade, note, note_at) -> None:
    if not 1 <= len(lines) <= ESSAY_LINES:
        raise StickDataError(f"an essay has 1 to {ESSAY_LINES} lines, got {len(lines)}")
    for k, line in enumerate(lines):
        if not line.strip() or len(line) > LINE_CHARS:
            raise StickDataError(f"line {k} has 1 to {LINE_CHARS} characters, got {line!r}")
    if not title.strip():
        raise StickDataError("an essay needs a title")
    if not (isinstance(shown, int) and 0 <= shown <= len(lines)):
        raise StickDataError(f"shown is how many lines are up, 0 to {len(lines)}, got {shown!r}")
    if mark is not None and not (isinstance(mark, int) and 0 <= mark < shown):
        raise StickDataError(f"mark is a line already shown (0 to {shown - 1}), got {mark!r}")
    for value, what in ((mark_at, "mark_at"), (note_at, "note_at")):
        if not (isinstance(value, (int, float)) and math.isfinite(value) and value >= 0):
            raise StickDataError(f"{what} is a second on the shot clock, got {value!r}")
    if grade is not None and not 1 <= len(grade.strip()) <= 3:
        raise StickDataError(f"a grade has 1 to 3 characters, got {grade!r}")
    if note is not None and not 1 <= len(note.strip()) <= NOTE_CHARS:
        raise StickDataError(f"a note has 1 to {NOTE_CHARS} characters, got {note!r}")


def _drawing(cv: Canvas, parent) -> None:
    """The child's crayon drawing: Dad in a tie and nothing below it, at his laptop, asleep."""
    s = cv
    g = _group(s, parent, x=800, y=1390)
    c, tie, desk, z = CRAYON[1], CRAYON[0], CRAYON[3], CRAYON[2]
    oval(s, g, -88, -96, 56, 56, "#ffffff", sw=5, stroke=c)  # the head
    shape(s, g, "M -60 -40 L -60 30 M -60 30 L -86 90 M -60 30 L -34 90 M -60 -20 L -10 0 M -60 -20 L -100 10",
          sw=5, stroke=c)  # fmt: skip
    shape(s, g, "M -66 -36 L -54 -36 L -52 10 L -60 22 L -68 10 Z", tie, 2, stroke=tie)
    box(s, g, -10, 0, 120, 10, desk)  # the laptop on its desk
    shape(s, g, "M 20 0 L 40 -60 L 110 -60 L 92 0", sw=5, stroke=desk)
    for k, (zx, zy, zs) in enumerate(((-20, -110, 22), (6, -140, 28), (38, -176, 34))):
        _label(s, g, "z", zx, zy, 40, 40, zs + k * 4, z)


@register("graphic", "stick-essay", tags=("school", "essay", "page", "highlighter", "grade", "font"))
def essay(
    cv: Canvas,
    parent,
    lines: Sequence[str],
    *,
    title: str,
    by: str,
    shown: int,
    mark: int | None = None,
    mark_at: float = 0.0,
    grade: str | None = None,
    note: str | None = None,
    note_at: float = 0.0,
    at: tuple[float, float] | None = None,
    scale: float = 1.0,
):
    """A child's essay on ruled paper (:data:`SHEET`, centred on ``at`` and sized by ``scale``): the ``title`` and
    who it is ``by``, the first ``shown`` of its ``lines`` (up to :data:`ESSAY_LINES`, each up to
    :data:`LINE_CHARS` characters, two rows at most), a highlighter sweeping line ``mark`` over :data:`SWEEP`
    seconds from ``mark_at``, a ``grade`` circled in red, a margin ``note`` that appears at ``note_at``, and the
    crayon drawing of Dad. Lines not yet read are not drawn, so the page never runs ahead of the reading."""
    cv.require_font("the essay is set in it")
    _check_essay(lines, title, shown, mark, mark_at, grade, note, note_at)
    s = cv
    x, y, w, h = SHEET
    cx, cy = at if at is not None else (x + w / 2, y + h / 2)
    g = _group(s, parent, anchorX=x + w / 2, anchorY=y + h / 2, x=cx, y=cy, scaleX=scale, scaleY=scale)
    box(s, g, x + 14, y + 18, w, h, "#000000", opacity=0.18)  # its shadow
    box(s, g, x, y, w, h, PAPER, 4)
    for ry in range(y + 160, y + h - 20, 65):
        shape(s, g, f"M {x} {ry} L {x + w} {ry}", sw=3, stroke=RULE)
    shape(s, g, f"M {x + 120} {y} L {x + 120} {y + h}", sw=4, stroke=MARGIN)
    for hy in (y + 140, y + h / 2, y + h - 140):
        oval(s, g, x + 30, hy - 20, 40, 40, "#d9d2c4", sw=3, stroke=s.ink)
    _label(s, g, title, x + 140, y + 30, w - 340, 80, 54, PENCIL, align="start")
    _label(s, g, by, x + 140, y + 104, w - 300, 44, 30, PENCIL, weight=600, align="start")
    for k in range(shown):
        top = LINE_TOP + k * LINE_STEP
        if k == mark:
            band = _group(s, g, x=x + 140, y=top)
            box(s, band, 0, 6, LINE_W + 20, LINE_STEP - 18, HIGHLIGHT, opacity=0.6)
            s.keys(band, "scaleX", [(0.0, 0.0), (mark_at, 0.0), (mark_at + SWEEP, 1.0)], hold=False)
        _label(s, g, lines[k], x + 150, top, LINE_W, LINE_STEP - 8, 50, PENCIL, weight=600, lines=2, align="start")
    if grade is not None:
        oval(s, g, x + w - 160, y + 30, 130, 130, PAPER, sw=7, stroke=RED)
        _label(s, g, grade, x + w - 160, y + 30, 130, 130, 84, RED, weight=800)
    if note is not None:
        n = _group(s, g)
        _label(s, n, note, x + 150, y + h - 190, 440, 120, 50, RED, lines=2, align="start")
        if note_at > 0:
            s.keys(n, "opacity", [(0.0, 0.0), (note_at, 0.0), (note_at + 0.01, 1.0)], hold=False)
    _drawing(s, g)
    return g

"""The Stick style at the airport: the boarding gate and the cabin row a passenger ends up in.

:func:`gate` is the back layer of the gate: the terminal wall, a window on the apron with a parked airliner, the
row of gate seats under it, the boarding sign (the gate and the group being called, ``now``) and the carpet. The
passenger stands at the left in a :data:`srstudio.stick.STANDING` pose, his :func:`carry_on` beside him with its
group tag; the agent stands mirrored at :data:`AGENT_AT`, and :func:`podium` is drawn after her so it hides her
legs. :func:`cabin` is the back layer of a row seen from the aisle: overhead bins labelled with the row and its
seats, three seat backs at :data:`SEATS` and the floor; the passengers sit in :data:`SQUEEZED` poses, one per seat
(``at=(seat - 540, 0)``), and :func:`armrests` is the front layer between the seats. Everything is in frame pixels
of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

from functools import partial

from . import look, signature
from .canvas import Canvas
from .registry import register
from .stick import Gradient, RigPose, StickDataError, _group, _seat, box, oval, paint, shape

__all__ = [
    "AGENT_AT",
    "ARMRESTS",
    "ARMREST_W",
    "FLOOR_FEET",
    "NOW_CHARS",
    "PODIUM_TOP",
    "PODIUM_X",
    "SEATS",
    "SEAT_STEP",
    "SQUEEZED",
    "TAG_CHARS",
    "TAG_SPAN",
    "armrests",
    "cabin",
    "carry_on",
    "gate",
    "podium",
]

WALL_TOP, WALL_LOW, SKIRTING, CARPET, CARPET_DOT = "#e3e8eb", "#c9d2d8", "#6f7b86", "#4f6275", "#5d7287"
SKY_TOP, SKY_LOW, APRON, FRAME = "#8ec3e6", "#cfe7f5", "#9aa3a8", "#56616b"
FUSELAGE, STRIPE, ENGINE, PORT = "#fbfbf8", "#2a9d8f", "#d7dcdf", "#33414d"
SIGN, SIGN_TEXT, SIGN_LIGHT = "#1d2733", "#ffb400", "#fff4d6"
SEAT_BLUE, SEAT_DARK, PODIUM_FRONT, PODIUM_EDGE = "#2f4a6d", "#22374f", "#2d3e50", "#c9d2d8"
CASE, CASE_DARK, TAG = "#c0453b", "#8f2f28", "#fff4d6"
CABIN_TOP, CABIN_LOW, BIN, BIN_EDGE, AISLE = "#efe9dc", "#ddd3bf", "#f6f2e8", "#b9ae98", "#5b4f6b"
FLOOR_Y = 1480  # the wall meets the carpet
FLOOR_FEET = 1700  # where a STANDING figure's feet are
WINDOW = (40, 300, 480, 880)  # x, y, w, h of the window on the apron
SIGN_BOX = (540, 290, 400, 250)  # x, y, w, h of the boarding sign, clear of the standing heads
GATE_CHARS, NOW_CHARS, TAG_CHARS, ROW_CHARS = 4, 12, 8, 3
TAG_SPAN = (40, 200)  # the luggage tag's left and right edges, from the carry-on's middle
PODIUM_X = (640, 1080)  # the podium, from its left end to past the frame
PODIUM_TOP = 1150  # a STANDING agent behind it shows from the waist up
AGENT_AT = (1420.0, 0.0)  # with flip=True a STANDING pose here stands behind the podium, facing the passenger
SEATS = (240, 540, 840)  # the seats' centres, window to aisle
SEAT_STEP = 300
ARMRESTS = (390, 690)  # between the seats
ARMREST_W = 40
ARMREST_TOP = 1220
SEAT_TOP, CUSHION = 640, 1270


_label = partial(look.text, weight=700)  # one line, no cut


def _plane(cv: Canvas, parent) -> None:
    """A parked airliner on the apron, side on, its nose to the right, inside the window."""
    s = cv
    g = _group(s, parent)
    shape(s, g, "M 120 830 L 92 700 L 140 700 L 220 830 Z", FUSELAGE, 4, stroke=s.ink)  # the tail fin
    shape(s, g, "M 104 712 L 132 712 L 168 770 L 116 770 Z", STRIPE)
    shape(
        s,
        g,
        "M 96 830 Q 90 790 140 790 L 440 790 Q 500 792 512 840 Q 500 890 440 892 L 140 892 Q 92 890 96 860 Z",
        FUSELAGE,
        4,
        stroke=s.ink,
    )  # fmt: skip  the fuselage
    shape(s, g, "M 120 858 L 506 858 L 504 870 L 124 870 Z", STRIPE)
    for k in range(9):  # the cabin windows
        oval(s, g, 170 + k * 30, 818, 14, 18, PORT)
    shape(s, g, "M 260 880 L 360 880 L 300 930 L 230 930 Z", FUSELAGE, 4, stroke=s.ink)  # the wing
    box(s, g, 270, 925, 70, 34, ENGINE, 4, r=16)
    shape(s, g, "M 200 892 L 200 1000 M 440 892 L 440 1000", sw=6, stroke=s.ink)  # the gear
    for x in (186, 228, 426):
        oval(s, g, x, 990, 30, 30, s.ink)


@register("location", "stick-gate", tags=("airport", "gate", "boarding", "travel", "font"))
def gate(cv: Canvas, parent, *, gate: str = "B9", now: str = "GROUP 1") -> None:
    """The boarding gate: the terminal wall, the window on the apron with a parked airliner, the gate seats under it,
    the boarding sign with ``gate`` (1 to :data:`GATE_CHARS` characters) and the group called ``now`` (1 to
    :data:`NOW_CHARS`), and the carpet. The code sits on the carpet's near edge and the cactus by the window
    (ADR 0001)."""
    cv.require_font("the boarding sign is set in it")
    if not gate.strip() or len(gate) > GATE_CHARS:
        raise StickDataError(f"the gate has 1 to {GATE_CHARS} characters, got {gate!r}")
    if not now.strip() or len(now) > NOW_CHARS:
        raise StickDataError(f"the sign calls 1 to {NOW_CHARS} characters, got {now!r}")
    s = cv
    wall = paint(s, Gradient("gate-wall", ((0, WALL_TOP), (1, WALL_LOW)), 0, 0, 0, FLOOR_Y))
    box(s, parent, 0, 0, s.width, FLOOR_Y, wall)
    x, y, w, h = WINDOW
    box(s, parent, x - 16, y - 16, w + 32, h + 32, FRAME, r=10)
    box(s, parent, x, y, w, h, paint(s, Gradient("gate-sky", ((0, SKY_TOP), (1, SKY_LOW)), 0, y, 0, y + h)))
    box(s, parent, x, y + h - 170, w, 170, APRON)
    shape(s, parent, f"M {x} {y + h - 90} L {x + w} {y + h - 90}", sw=6, stroke="#f3e9b5", opacity=0.8)
    _plane(s, parent)
    for mx in (x + w / 3, x + 2 * w / 3):  # the mullions
        box(s, parent, mx - 7, y, 14, h, FRAME)
    # the boarding sign, hung from the ceiling on two rods
    sx, sy, sw_, sh = SIGN_BOX
    for rx in (sx + 60, sx + sw_ - 60):
        box(s, parent, rx - 4, 0, 8, sy, FRAME)
    box(s, parent, sx, sy, sw_, sh, SIGN, r=14)
    box(s, parent, sx + 20, sy + 20, 120, 110, SIGN_LIGHT, r=10)
    _label(s, parent, gate, sx + 20, sy + 20, 120, 110, 72, SIGN)
    _label(s, parent, "NOW BOARDING", sx + 150, sy + 30, sw_ - 170, 90, 38, SIGN_TEXT, align="start")
    _label(s, parent, now, sx + 20, sy + 140, sw_ - 40, 96, 72, SIGN_TEXT)
    # the gate seats under the window: a row joined on one beam
    box(s, parent, 30, 1420, 560, 16, SEAT_DARK)
    for k in range(4):
        cx = 40 + k * 140
        box(s, parent, cx, 1250, 120, 150, SEAT_BLUE, 4, r=16)
        box(s, parent, cx - 4, 1380, 128, 34, SEAT_DARK, r=10)
    box(s, parent, 0, FLOOR_Y - 26, s.width, 26, SKIRTING)
    box(s, parent, 0, FLOOR_Y, s.width, 1920 - FLOOR_Y, CARPET)
    for row in range(5):  # the carpet's dots, sparser toward the wall
        yy = FLOOR_Y + 50 + row * row * 18 + row * 40
        for col in range(12):
            oval(s, parent, 20 + col * 92 + (row % 2) * 46, yy, 14, 8, CARPET_DOT)
    signature.cactus(s, parent, 610, FLOOR_Y, scale=0.42)
    signature.code(s, parent, 40, 1880, 9, color="#8a99a8")


@register("prop", "stick-gate-podium", tags=("airport", "gate", "counter", "front-layer", "font"))
def podium(cv: Canvas, parent, *, gate: str = "B9", plate: bool = True):
    """The gate podium at the right, from :data:`PODIUM_X` at :data:`PODIUM_TOP`: drawn after the agent, it hides
    her legs. A screen on top and the gate lettered on its front plate, or the plate blank with ``plate=False``
    (a close-up whose caption band would sit over the lettering)."""
    if plate:
        cv.require_font("the gate plate is set in it")
    if not gate.strip() or len(gate) > GATE_CHARS:
        raise StickDataError(f"the gate has 1 to {GATE_CHARS} characters, got {gate!r}")
    s = cv
    g = _group(s, parent)
    left, right = PODIUM_X
    box(s, g, left, PODIUM_TOP + 30, right - left, FLOOR_FEET - PODIUM_TOP - 30, PODIUM_FRONT, 4)
    box(s, g, left - 0, PODIUM_TOP, right - left, 34, PODIUM_EDGE, 4, r=6)
    box(s, g, 940, PODIUM_TOP - 110, 120, 100, SIGN, 4, r=8)  # the agent's screen, turned to her
    box(s, g, 720, PODIUM_TOP + 120, 200, 100, SIGN_LIGHT, r=12)
    if plate:
        _label(s, g, gate, 720, PODIUM_TOP + 120, 200, 100, 64, SIGN)
    box(s, g, left, FLOOR_FEET + 6, right - left, 18, "#000000", opacity=0.18)
    return g


@register("prop", "stick-carry-on", tags=("airport", "luggage", "suitcase", "tag", "font"))
def carry_on(cv: Canvas, parent, x, y, *, tag: str | None = "GROUP 4"):
    """A wheeled carry-on standing on ``x, y`` (the floor under its middle), its handle up and a luggage tag
    lettered ``tag`` (1 to :data:`TAG_CHARS` characters; ``None``: left blank) hanging from the grip."""
    if tag is not None:
        cv.require_font("the luggage tag is set in it")
    if tag is not None and (not tag.strip() or len(tag) > TAG_CHARS):
        raise StickDataError(f"the tag has 1 to {TAG_CHARS} characters, got {tag!r}")
    s = cv
    g = _group(s, parent)
    for hx in (x - 34, x + 34):  # the handle's rods
        box(s, g, hx - 5, y - 440, 10, 200, "#7d868e")
    box(s, g, x - 46, y - 452, 92, 22, s.ink, r=10)  # the grip
    box(s, g, x - 70, y - 260, 140, 236, CASE, 5, r=18)
    for gx in (x - 30, x, x + 30):
        shape(s, g, f"M {gx} {y - 244} L {gx} {y - 40}", sw=4, stroke=CASE_DARK)
    for wx in (x - 56, x + 32):
        oval(s, g, wx, y - 26, 24, 24, s.ink)
    shape(s, g, f"M {x + 30} {y - 440} Q {x + 60} {y - 420} {x + 74} {y - 380}", sw=4, stroke=s.ink)
    tag_x, tag_w = x + TAG_SPAN[0], TAG_SPAN[1] - TAG_SPAN[0]
    box(s, g, tag_x, y - 384, tag_w, 64, TAG, 4, r=10)
    if tag is not None:
        _label(s, g, tag, tag_x, y - 384, tag_w, 64, 34, s.ink)
    return g


@register("location", "stick-cabin", tags=("airport", "plane", "cabin", "middle-seat", "travel", "font"))
def cabin(cv: Canvas, parent, *, row: str = "38", seats: str = "DEF") -> None:
    """A row of the cabin seen from the aisle: the overhead bins with the ``row`` number (1 to :data:`ROW_CHARS`
    characters) and a letter over each of the three seats (``seats``, three letters), the seat backs at
    :data:`SEATS` with their headrest covers, the cushions and the floor. The code sits on the floor (ADR 0001)."""
    cv.require_font("the row label is set in it")
    if not row.strip() or len(row) > ROW_CHARS:
        raise StickDataError(f"the row has 1 to {ROW_CHARS} characters, got {row!r}")
    if len(seats) != len(SEATS) or not all(c.strip() for c in seats):
        raise StickDataError(f"the row has {len(SEATS)} seats, one letter each, got {seats!r}")
    s = cv
    box(s, parent, 0, 0, s.width, 1920, paint(s, Gradient("cabin-wall", ((0, CABIN_TOP), (1, CABIN_LOW)), 0, 0, 0,
                                                                    1400)))  # fmt: skip
    box(s, parent, 0, 140, s.width, 380, BIN, 4, r=0)  # the overhead bins
    for bx in (360, 720):
        shape(s, parent, f"M {bx} 160 L {bx} 500", sw=4, stroke=BIN_EDGE)
    box(s, parent, 0, 500, s.width, 40, BIN_EDGE)
    box(s, parent, 90, 300, 150, 110, SIGN, r=12)
    _label(s, parent, row, 90, 300, 150, 110, 72, SIGN_LIGHT)
    for cx, letter in zip(SEATS, seats, strict=True):
        box(s, parent, cx - 40, 420, 80, 70, SIGN_LIGHT, 3, r=10)
        _label(s, parent, letter, cx - 40, 420, 80, 70, 52, SIGN)
        box(s, parent, cx - 140, SEAT_TOP, 280, CUSHION - SEAT_TOP, SEAT_BLUE, 5, r=40)
        box(s, parent, cx - 100, SEAT_TOP + 24, 200, 120, "#f4f1ea", r=18)  # the headrest cover
    box(s, parent, 0, CUSHION, s.width, 90, SEAT_DARK, 4)
    box(s, parent, 0, CUSHION + 90, s.width, 1920 - CUSHION - 90, AISLE)
    signature.code(s, parent, 40, 1880, 9, color="#8a7f99")


@register("prop", "stick-armrests", tags=("airport", "plane", "cabin", "front-layer"))
def armrests(cv: Canvas, parent):
    """The two armrests between the three seats, at :data:`ARMRESTS`: drawn after the passengers, so an elbow on
    one rests on it."""
    s = cv
    g = _group(s, parent)
    for x in ARMRESTS:
        box(s, g, x - ARMREST_W / 2, ARMREST_TOP, ARMREST_W, CUSHION + 60 - ARMREST_TOP, SEAT_DARK, 4, r=12)
        box(s, g, x - ARMREST_W / 2 - 6, ARMREST_TOP - 10, ARMREST_W + 12, 26, "#3a3f47", r=10)
    return g


# Seated in a row, facing the viewer, centred on x 540: place them with ``at=(seat - 540, 0)``. ``tucked`` keeps
# both elbows in, clear of the armrests; ``spread`` rests them on the armrests either side.
SQUEEZED: dict[str, RigPose] = {
    "tucked": _seat((540, 880), (540, 985), (540, 1290), ((505, 1330), (575, 1330)), ((500, 1640), (580, 1640)),
                    ((488, 1130), (592, 1130)), ((522, 1262), (558, 1262))),
    "tucked-up": _seat((540, 872), (540, 978), (540, 1290), ((505, 1330), (575, 1330)), ((500, 1640), (580, 1640)),
                       ((488, 1130), (596, 1110)), ((522, 1262), (566, 990))),
    "spread": _seat((540, 870), (540, 975), (540, 1290), ((470, 1330), (610, 1330)), ((440, 1640), (640, 1640)),
                    ((390, 1205), (690, 1205)), ((396, 1262), (684, 1262))),
}  # fmt: skip

"""The Stick style at the airport: the boarding gate and the cabin row a passenger ends up in.

:func:`gate` is the back layer of the gate: the terminal wall, a window on the apron with a parked airliner, the
row of gate seats under it, the boarding sign (the gate and the group being called, ``now``) and the carpet. The
passenger stands at the left in a :data:`srstudio.stick.STANDING` pose, his :func:`carry_on` beside him with its
group tag; the agent stands mirrored at :data:`AGENT_AT`, and :func:`podium` is drawn after her so it hides her
legs. :func:`bag_scale` weighs a bag on the floor and shows the weight on a readout big enough for a phone, and
:func:`coat_ball` is everything a passenger owns, worn. :func:`palm` stands at the other end of the flight.
:func:`cabin` is the back layer of a row seen from the aisle: overhead bins labelled with the row and its
seats, three seat backs at :data:`SEATS` and the floor; the passengers sit in :data:`SQUEEZED` poses, one per seat
(``at=(seat - 540, 0)``), and :func:`armrests` is the front layer between the seats. Everything is in frame pixels
of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

from functools import partial

from . import _stick_transport_contracts as tc
from . import checks, look, signature
from .canvas import Canvas
from .registry import register
from .stick import Gradient, RigPose, StickDataError, _group, _seat, box, oval, paint, shape

__all__ = [
    "AGENT_AT",
    "ARMRESTS",
    "ARMREST_W",
    "BOARDING_SIZE",
    "FLOOR_FEET",
    "NOW_CHARS",
    "PODIUM_TOP",
    "PODIUM_X",
    "READOUT",
    "READOUT_CHARS",
    "READOUT_SIZE",
    "SEATS",
    "SEAT_STEP",
    "SQUEEZED",
    "TAG_CHARS",
    "TAG_SPAN",
    "armrests",
    "bag_scale",
    "cabin",
    "carry_on",
    "coat_ball",
    "gate",
    "now_size",
    "palm",
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
APPROVED_BOARDING_SIZE = 38  # the first line stick-gate version 1 was approved with
BOARDING_SIZE = 25  # the size that fits the room beside the gate letters even in a wide bold: a new reel asks for it
GATE_CHARS, NOW_CHARS, TAG_CHARS, ROW_CHARS = 4, 12, 8, 3
TAG_SPAN = (40, 200)  # the luggage tag's left and right edges, from the carry-on's middle
PODIUM_X = (640, 1080)  # the podium, from its left end to past the frame
CACTUS_AT = (610, FLOOR_Y)  # by the window, where the pot stands on the carpet
PODIUM_TOP = 1150  # a STANDING agent behind it shows from the waist up
AGENT_AT = (1420.0, 0.0)  # with flip=True a STANDING pose here stands behind the podium, facing the passenger
SEATS = (240, 540, 840)  # the seats' centres, window to aisle
SEAT_STEP = 300
ARMRESTS = (390, 690)  # between the seats
ARMREST_W = 40
ARMREST_TOP = 1220
SEAT_TOP, CUSHION = 640, 1270
READOUT = (672, 1215, 376, 170)  # x, y, w, h of the scale's readout, on the podium's front above the caption band
READOUT_CHARS, READOUT_SIZE = 5, 124  # a weight a viewer reads on a phone, across the frame from the bag
LED, LED_BACK, PLATTER, PLATTER_DARK = "#ff3b30", "#16080a", "#b7c0c7", "#7d868e"
COATS = ("#3f5c7a", "#6b4f3a", "#4d6a4f", "#7a3f52")  # the outermost coat first
SCARVES = ("#d9a441", "#c0453b", "#2a9d8f")
HATS = ("#55607a", "#a8743a", "#3a3f47", "#9c4a4a")
SHOE, POCKET, BARK, FROND = "#8a5a33", "#2c4258", "#8a6a48", "#2f8a5b"
HEAD_TOP = 184  # from a STANDING chin to the top of the head
MAX_LAYERS, MAX_HATS, MAX_SCARVES = 4, 4, 3


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


def now_size(now: str) -> float:
    """The letter size of the sign's second line: ten characters fill it, and a longer call shrinks to stay inside."""
    return 72 if len(now) <= 10 else 72 * 8 / len(now)


@register(
    "location", "stick-gate", contract=tc.contract('stick-gate'), tags=("airport", "gate", "boarding", "travel", "font")
)
def gate(
    cv: Canvas,
    parent,
    *,
    gate: str = "B9",
    now: str = "GROUP 1",
    boarding_size: float = APPROVED_BOARDING_SIZE,
    cactus_at: tuple[float, float] = CACTUS_AT,
    sign: bool = True,
) -> None:
    """The boarding gate: the terminal wall, the window on the apron with a parked airliner, the gate seats under it,
    the boarding sign with ``gate`` (1 to :data:`GATE_CHARS` characters) and the group called ``now`` (1 to
    :data:`NOW_CHARS`), and the carpet. The code sits on the carpet's near edge and the cactus by the window
    (ADR 0001). ``boarding_size`` letters the sign's first line; the default is the drawing that was approved, and
    a reel whose font runs wide passes :data:`BOARDING_SIZE`. ``cactus_at`` is where the cactus's pot stands; the
    default is the approved drawing, and a reel that stands something in front of it moves it. ``sign=False`` leaves
    the sign's face to :func:`boarding_sign`, for a reel that washes the room and keeps the sign out of the wash."""
    cv.require_font("the boarding sign is set in it")
    if not (isinstance(cactus_at, tuple) and len(cactus_at) == 2 and all(checks.number(value) for value in cactus_at)):
        raise StickDataError(f"the cactus stands at an x and a y, got {cactus_at!r}")
    if not (checks.number(boarding_size) and boarding_size > 0):
        raise StickDataError(f"the sign's first line has a size above 0, got {boarding_size!r}")
    _check_sign(gate, now)
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
    sx, sy, sw_, _ = SIGN_BOX
    for rx in (sx + 60, sx + sw_ - 60):
        box(s, parent, rx - 4, 0, 8, sy, FRAME)
    if sign:
        boarding_sign(s, parent, gate=gate, now=now, boarding_size=boarding_size)
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
    signature.cactus(s, parent, *cactus_at, scale=0.42)
    signature.code(s, parent, 40, 1880, 9, color="#8a99a8")


@register(
    "prop",
    "stick-gate-podium",
    contract=tc.contract('stick-gate-podium'),
    tags=("airport", "gate", "counter", "front-layer", "font"),
)
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


@register(
    "prop",
    "stick-carry-on",
    contract=tc.contract('stick-carry-on'),
    tags=("airport", "luggage", "suitcase", "tag", "font"),
)
def carry_on(cv: Canvas, parent, x, y, *, tag: str | None = "GROUP 4", hanging: bool = False):
    """A wheeled carry-on standing on ``x, y`` (the floor under its middle), its handle up and a luggage tag
    lettered ``tag`` (1 to :data:`TAG_CHARS` characters; ``None``: left blank) hanging from the grip; ``hanging``
    drops a blank tag straight down from its string, close to the handle, instead of the wide tag beside it."""
    if hanging and tag is not None:
        raise StickDataError("a hanging tag is blank")
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
    if hanging:
        shape(s, g, f"M {x + 30} {y - 440} Q {x + 58} {y - 430} {x + 62} {y - 396}", sw=4, stroke=s.ink)
        box(s, g, x + 42, y - 396, 40, 86, TAG, 4, r=8)
        return g
    shape(s, g, f"M {x + 30} {y - 440} Q {x + 60} {y - 420} {x + 74} {y - 380}", sw=4, stroke=s.ink)
    tag_x, tag_w = x + TAG_SPAN[0], TAG_SPAN[1] - TAG_SPAN[0]
    box(s, g, tag_x, y - 384, tag_w, 64, TAG, 4, r=10)
    if tag is not None:
        _label(s, g, tag, tag_x, y - 384, tag_w, 64, 34, s.ink)
    return g


@register(
    "prop",
    "stick-bag-scale",
    contract=tc.contract('stick-bag-scale'),
    tags=("airport", "scale", "luggage", "readout", "weight", "font"),
)
def bag_scale(cv: Canvas, parent, x, y, readings, end, *, readout: tuple[float, float, float, float] = READOUT):
    """A bag scale: its platter set in the floor under ``x, y`` and its red readout at ``readout``, on the podium's
    front by default. ``readings`` are ``(start, weight)`` in rising order, the first from the shot's start; each
    shows until the next and the last until ``end``. A weight has 1 to :data:`READOUT_CHARS` characters, lit at
    :data:`READOUT_SIZE` so it reads at phone size, and a weight of ``None`` leaves the readout dark. Draw it after the
    podium and before the bag."""
    cv.require_font("the readout is set in it")
    readings = tuple(readings)
    if not readings:
        raise StickDataError("a scale shows at least one reading")
    starts = [start for start, _ in readings]
    if starts[0] != 0 or any(b <= a for a, b in zip(starts, starts[1:], strict=False)) or starts[-1] >= end:
        raise StickDataError(f"readings start at 0 and rise before the end, got {starts} to {end}")
    for _, weight in readings:
        if weight is not None and (not weight.strip() or len(weight) > READOUT_CHARS):
            raise StickDataError(f"a reading has 1 to {READOUT_CHARS} characters, got {weight!r}")
    s = cv
    g = _group(s, parent)
    box(s, g, x - 170, y - 22, 340, 44, PLATTER_DARK, 4, r=8)
    box(s, g, x - 150, y - 34, 300, 22, PLATTER, 4, r=8)
    rx, ry, rw, rh = readout
    box(s, g, rx, ry, rw, rh, LED_BACK, 5, r=16)
    for (start, weight), until in zip(readings, [*starts[1:], end], strict=True):
        if weight is None:
            continue
        lit = _group(s, g)
        _label(s, lit, weight, rx, ry, rw, rh, READOUT_SIZE, LED)
        s.gate(lit, [(start, until)])
    return g


def _check_sign(gate: str, now: str) -> None:
    if not gate.strip() or len(gate) > GATE_CHARS:
        raise StickDataError(f"the gate has 1 to {GATE_CHARS} characters, got {gate!r}")
    if not now.strip() or len(now) > NOW_CHARS:
        raise StickDataError(f"the sign calls 1 to {NOW_CHARS} characters, got {now!r}")


def boarding_sign(
    cv: Canvas, parent, *, gate: str = "B9", now: str = "GROUP 1", boarding_size: float = APPROVED_BOARDING_SIZE
) -> None:
    """The face of the gate's boarding sign at :data:`SIGN_BOX`: ``gate`` on its light tile, the first line in
    ``boarding_size``, the group called ``now`` under them."""
    _check_sign(gate, now)
    s = cv
    sx, sy, sw_, sh = SIGN_BOX
    box(s, parent, sx, sy, sw_, sh, SIGN, r=14)
    box(s, parent, sx + 20, sy + 20, 120, 110, SIGN_LIGHT, r=10)
    _label(s, parent, gate, sx + 20, sy + 20, 120, 110, 72, SIGN)
    _label(s, parent, "NOW BOARDING", sx + 150, sy + 30, sw_ - 170, 90, boarding_size, SIGN_TEXT, align="start")
    _label(s, parent, now, sx + 20, sy + 140, sw_ - 40, 96, now_size(now), SIGN_TEXT)


@register(
    "prop",
    "stick-coat-ball",
    contract=tc.contract('stick-coat-ball'),
    tags=("airport", "clothes", "coats", "scarf", "hat", "front-layer"),
)
def coat_ball(cv: Canvas, parent, x, chin, radius, *, layers=3, hats=0, scarves=0, trousers=False, shoes=False):
    """Everything a passenger owns, worn: a ball of ``radius`` hanging from the chin at ``x, chin``, drawn after a
    STANDING figure so only the head shows. ``layers`` of coat (1 to :data:`MAX_LAYERS`) show as hems around it, a
    sleeve stands out at each side, ``scarves`` wind under the chin, ``hats`` pile on the head, ``trousers`` swell
    the legs to the floor and ``shoes`` stick out of the pockets."""
    if radius < 100:
        raise StickDataError(f"a ball under a chin has a radius of at least 100, got {radius}")
    if not 1 <= layers <= MAX_LAYERS:
        raise StickDataError(f"a ball wears 1 to {MAX_LAYERS} coats, got {layers}")
    if not 0 <= hats <= MAX_HATS or not 0 <= scarves <= MAX_SCARVES:
        raise StickDataError(f"at most {MAX_HATS} hats and {MAX_SCARVES} scarves, got {hats} and {scarves}")
    s = cv
    g = _group(s, parent)
    cy = chin + radius - 8
    if trousers:
        for lx in (x - 110, x + 12):
            box(s, g, lx, cy, 98, FLOOR_FEET - cy - 8, "#3a4152", 4, r=30)
    for side in (-1, 1):  # the sleeves, too full to bend
        sx = x + side * (radius - 10)
        oval(s, g, sx - 34 + side * 28, cy - 40, 68, 118, COATS[0])
        box(s, g, sx - 22 + side * 42, cy + 58, 44, 34, "#e9c7a4", 4, r=14)
    oval(s, g, x - radius, cy - radius, radius * 2, radius * 2, COATS[0])
    shape(s, g, f"M {x} {cy - radius} L {x} {cy + radius}", sw=5, stroke=s.ink)
    for i in range(layers - 1):  # the hem of each coat under the one over it
        r = radius * (0.97 - 0.05 * i)
        drop = cy + r * (0.62 + 0.09 * i)
        side = r * (1 - (0.62 + 0.09 * i) ** 2) ** 0.5
        shape(s, g, f"M {x - side} {drop} Q {x} {drop + r * 0.34} {x + side} {drop}", sw=14, stroke=COATS[i + 1])
    for by in range(int(chin + radius * 0.5), int(cy + radius * 0.7), int(radius * 0.4)):  # the buttons, straining
        oval(s, g, x - 13, by, 26, 26, "#e8dcc2")
    if shoes:
        for side in (-1, 1):
            sx = x + side * radius * 0.62
            box(s, g, sx - 62, cy + radius * 0.16, 124, 66, POCKET, 4, r=10)
            shape(s, g, _shoe(sx, cy + radius * 0.16, side), SHOE, 4, stroke=s.ink)
    for i in range(scarves):
        y = chin + 6 + 30 * i
        wide = min(radius * 0.72, 160 + 26 * i)
        box(s, g, x - wide, y - 20, wide * 2, 44, SCARVES[i], 4, r=20)
    for i in range(hats):  # bottom hat first, each sitting on the one before
        y = chin - HEAD_TOP - 46 * i
        box(s, g, x - 118 + 8 * i, y + 8, 236 - 16 * i, 18, HATS[i], 4, r=8)
        box(s, g, x - 74 + 6 * i, y - 34, 148 - 12 * i, 46, HATS[i], 4, r=10)
    return g


def _shoe(x, y, side) -> str:
    """A shoe heel-down in a pocket at ``x, y``, its toe out to ``side``."""
    heel, ankle, toe = x - side * 30, x + side * 20, x + side * 70
    return f"M {heel} {y + 12} L {heel} {y - 70} L {ankle} {y - 70} Q {toe} {y - 30} {toe} {y + 12} Z"


@register(
    "prop", "stick-palm", contract=tc.contract('stick-palm'), tags=("palm", "tree", "tropics", "arrivals", "holiday")
)
def palm(cv: Canvas, parent, x, y, *, height=560):
    """A palm standing on ``x, y``: a bent trunk ``height`` tall and seven fronds. Nothing about it is cold."""
    if height < 120:
        raise StickDataError(f"a palm is at least 120 tall, got {height}")
    s = cv
    g = _group(s, parent)
    top = y - height
    lean = height * 0.16
    shape(s, g, f"M {x} {y} Q {x - lean} {y - height * 0.5} {x + lean * 0.4} {top}", sw=34, stroke=BARK)
    for i in range(1, 7):
        ty = y - height * i / 7
        tx = x - lean * 0.9 * (1 - abs(i / 7 - 0.5) * 2) + lean * 0.3 * i / 7
        shape(s, g, f"M {tx - 20} {ty} L {tx + 20} {ty}", sw=5, stroke="#6c5238")
    cx = x + lean * 0.4
    for dx, dy in ((-230, 30), (-170, -120), (-40, -180), (90, -170), (210, -90), (240, 40), (-120, 120)):
        ex, ey = cx + dx * height / 560, top + dy * height / 560
        mx, my = (cx + ex) / 2, min(top, ey) - 60 * height / 560
        shape(s, g, f"M {cx} {top} Q {mx} {my} {ex} {ey} Q {mx} {my + 56} {cx} {top} Z", FROND, 4, stroke=s.ink)
    return g


@register(
    "location",
    "stick-cabin",
    contract=tc.contract('stick-cabin'),
    tags=("airport", "plane", "cabin", "middle-seat", "travel", "font"),
)
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


@register(
    "prop", "stick-armrests", contract=tc.contract('stick-armrests'), tags=("airport", "plane", "cabin", "front-layer")
)
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

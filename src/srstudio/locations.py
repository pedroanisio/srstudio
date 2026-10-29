"""Locations: complete sets with named slots where the cast is placed.

Each builder draws the set in z-order and calls the slot callbacks at the right depth,
so a character sits behind the desk and in front of the chair without the episode
knowing the stacking. Slots receive the set's group and return nothing.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from . import props, signature
from .canvas import Canvas
from .registry import register

Slot = Callable[[object], None] | None


def _call(slot: Slot, g):
    if slot:
        slot(g)


def _office_room(cv: Canvas, g, p, plant_id="office-plant"):
    """Wall, art and plant of the interviewer's office (the back of the wide shot)."""
    cv.rect(g, 0, 0, 1080, 1920, p["wall"])
    cv.rect(g, 1018, 0, 62, 1165, "#879399", opacity=0.33)
    cv.line(g, 1020, 0, 1020, 1156, "#444F53", 3)
    cv.line(g, 1026, 0, 1026, 1156, "#E4E8E5", 3, opacity=0.65)
    props.office_art(cv, g)
    props.plant(cv, g, id=plant_id)


def _office_room_symbol(cv: Canvas) -> str:
    return cv.symbol("office-room", lambda s: _office_room(cv, s, props.office_paints(cv)))


def _office_desk_front_symbol(cv: Canvas) -> str:
    return cv.symbol("office-desk-front", lambda s: _office_desk_front(cv, s, props.office_paints(cv)))


def _office_desk_front(cv: Canvas, g, p):
    """The interviewer's desk with its papers and laptop, in front of whoever sits behind it."""
    cv.path(g, "M0 1217 L1080 1137 L1080 1533 L0 1588Z", p["desk"], cv.ink, 4)
    props.woodgrain(cv, g, 1200, 355)
    cv.path(g, "M0 1590 L1080 1537 L1080 1920 L0 1920Z", p["desk_front"], cv.ink, 4)
    signature.code(cv, props.papers(cv, g, 467, 1197, 0.88, -3), 20, 10, 11, color="#5C625D")
    signature.cactus(cv, g, 780, 1200, 0.55)  # between the papers and the laptop, the far corner of the desk
    props.laptop(cv, g)


@register(
    "location",
    "office-wide",
    summary="Office, wide shot: wall art, plant, desk, laptop, the candidate's back",
    episodes=("01", "02", "03", "04", "06"),
)
def office_wide(cv: Canvas, parent, at_desk: Slot = None, id="wide-office-angle", shots=None, instanced=False):
    """``instanced`` places the room and the desk as shared symbols (drawn once per document).

    The engine draws an instance into an offscreen at its symbol's frame size and scales that texture, so
    a camera push-in on an instanced angle softens its edges: keep the inline drawing for angles that zoom."""
    p = props.office_paints(cv)
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)  # the gate precedes the drawing, as in the shipped scenes
    if instanced:
        cv.instance(g, f"{id}-room", _office_room_symbol(cv))
    else:
        _office_room(cv, g, p)
    props.chair(cv, g)
    _call(at_desk, g)
    if instanced:
        cv.instance(g, f"{id}-desk-front", _office_desk_front_symbol(cv))
    else:
        _office_desk_front(cv, g, p)
    props.candidate_back(cv, g)
    return g


@register(
    "location",
    "office-desk",
    summary="Office, wide shot without the foreground candidate: whoever sits behind "
    "the desk; chair=False leaves the chair to the slot (to spin it)",
    episodes=("06",),
)
def office_desk(
    cv: Canvas,
    parent,
    behind_desk: Slot = None,
    chair: bool = True,
    id="desk-office-angle",
    shots=None,
    instanced=False,
):
    """``instanced`` places the room and the desk as shared symbols; inline, the plant takes an id of its own.

    As for :func:`office_wide`, keep the inline drawing for an angle the camera zooms into."""
    p = props.office_paints(cv)
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    if instanced:
        cv.instance(g, f"{id}-room", _office_room_symbol(cv))
    else:
        _office_room(cv, g, p, plant_id=f"{id}-plant")
    if chair:
        props.chair(cv, g)
    _call(behind_desk, g)
    if instanced:
        cv.instance(g, f"{id}-desk-front", _office_desk_front_symbol(cv))
    else:
        _office_desk_front(cv, g, p)
    return g


@register(
    "location",
    "office-reverse",
    summary="Office, reverse angle on the candidate: warm wall, gray chair, glass of water",
    episodes=("01", "02", "03", "04", "06"),
)
def office_reverse(cv: Canvas, parent, in_chair: Slot = None, id="candidate-reverse-angle", shots=None):
    p = props.office_paints(cv)
    ink = cv.ink
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)  # the gate precedes the drawing, as in the shipped scenes
    cv.rect(g, 0, 0, 1080, 1920, p["warm_wall"])
    cv.rect(g, 0, 0, 14, 1410, "#818074", ink, 3)
    cv.line(g, 20, 0, 20, 1402, "#ECE0C9", 3)
    for y in [8, 342]:
        cv.path(g, f"M1069 {y + 12} L1086 {y} L1086 {y + 38} L1071 {y + 43}Z", "#A49176", ink, 3)
    props.chair(cv, g, "gray")
    _call(in_chair, g)
    cv.rect(g, 0, 1399, 1080, 433, p["desk"], ink, 4)
    props.woodgrain(cv, g, 1418, 390, 12)
    cv.rect(g, 0, 1833, 1080, 20, "#B09171", ink, 3)
    cv.rect(g, 0, 1856, 1080, 64, p["desk_front"])
    signature.code(cv, props.papers(cv, g, 649, 1482, 1.23, 6), 20, 10, 11, color="#5C625D")
    signature.cactus(cv, g, 120, 1440, 0.9)
    props.water_glass(cv, g)
    return g


@register(
    "location",
    "cafe",
    summary="Café interior: tiles, shelf, menu, masked window, pendants, espresso machine, counter",
    episodes=("05",),
)
def cafe(
    cv: Canvas,
    parent,
    behind_counter: Slot = None,
    at_counter: Slot = None,
    on_counter: Slot = None,
    id="location-cafe",
    shots=None,
):
    p = props.cafe_paints(cv)
    ink = cv.ink
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)  # the gate precedes the drawing, as in the shipped scenes
    cv.rect(g, -1200, -1700, 3500, 3600, p["cream"])
    cv.rect(g, -1200, 1320, 3500, 1500, "#D4B390")
    for xx in range(-900, 2200, 180):
        cv.line(g, xx, 1320, xx + 230, 2200, "#BC9B7C", 2, opacity=0.55)
    cv.rect(g, -500, 865, 2200, 390, "#E4DBC4")
    for yy in range(865, 1256, 65):
        cv.line(g, -500, yy, 1700, yy, "#C9C6AC", 2)
    for xx in range(-500, 1701, 110):
        cv.line(g, xx, 865, xx, 1255, "#C9C6AC", 2)
    cv.rect(g, -500, 1012, 2200, 22, "#946642", ink, 3)
    props.menu_board(cv, g)
    signature.code(cv, g, 445, 708, 11, color="#C49B68", opacity=0.9, align="end")
    props.cafe_window(cv, g)
    for xx in [300, 850]:
        props.pendant_light(cv, g, xx)
    for i in range(3):
        props.bean_jar(cv, g, 85 + i * 93)
    signature.cactus(cv, g, 430, 1012, 0.6)  # on the shelf, after the jars
    _call(behind_counter, g)
    props.espresso_machine(cv, g)
    cv.rect(g, -600, 1240, 2300, 78, p["wood"], ink, 5)
    cv.rect(g, -600, 1317, 2300, 350, "#A5704E", ink, 5)
    for xx in range(-500, 1600, 110):
        cv.line(g, xx, 1320, xx, 1668, "#8C5C40", 2, opacity=0.65)
    cv.rect(g, -600, 1327, 2300, 18, "#D3A571", opacity=0.5)
    props.pastry_stand(cv, g)
    _call(on_counter, g)
    _call(at_counter, g)
    return g


@register(
    "location", "park", summary="Park: buildings, lawn, path, swaying tree, shrubs, sign, bench", episodes=("05",)
)
def park(cv: Canvas, parent, on_bench: Slot = None, beside_bench: Slot = None, id="location-park", shots=None):
    p = props.cafe_paints(cv)
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)  # the gate precedes the drawing, as in the shipped scenes
    cv.rect(g, 0, 0, 1080, 1920, p["sky"])
    for xx, yy, ww, hh in [(0, 380, 130, 320), (160, 445, 160, 255), (780, 398, 170, 302), (963, 350, 170, 350)]:
        props.building(cv, g, xx, yy, ww, hh)
    cv.path(g, "M0 722 Q420 600 1080 724 L1080 1390 L0 1390Z", p["grass"], cv.clear, 0)
    cv.rect(g, 0, 1420, 1080, 500, "#D7D0B8")
    cv.path(g, "M0 1415 L1080 1415 L1080 1480 L0 1493Z", "#C1BEA6", cv.clear, 0)
    for yy in [1530, 1710, 1880]:
        cv.line(g, 0, yy, 1080, yy, "#B8BAA6", 3)
    for xx in [120, 440, 765, 1070]:
        cv.line(g, xx, 1475, xx - 110, 1920, "#BEC0AC", 2)
    props.tree(cv, g)
    for xx in [18, 73, 210, 865, 940, 1010]:
        props.shrub(cv, g, xx)
    props.park_sign(cv, g)
    signature.code(cv, g, 1030, 624, 9, color="#F0E7CF", opacity=0.85, align="end")
    props.bench(cv, g)
    signature.cactus(cv, g, 905, 1300, 0.75)  # on the grass beside the bench
    _call(on_bench, g)
    _call(beside_bench, g)
    return g


# -- polished rooms (ADR 0011) ------------------------------------------------------------------------------------

CONFERENCE_SEAT = (540, 735, 1.45)  # x, y, scale of an office actor in the conference chair, as ``perform`` takes
CONFERENCE_BOARD = (620, 300, 420, 420)  # x, y, width, height of the whiteboard
CONFERENCE_TABLE_Y = 1130  # the table's far edge: everything of the seated actor below it is hidden
RECEPTION_CLERK = (600, 790, 1.3)  # an office actor behind the counter
RECEPTION_VISITOR = (250, 1080, 1.5)  # a standing café actor in front of it
COUNTER_Y = 1060  # the counter's top
COUNTER_FLOOR = 1440  # where the counter meets the floor


@register(
    "location",
    "conference-room",
    summary="Conference room: blinds with light shafts, a whiteboard with a chart and sticky notes, a high-back "
    "chair, a walnut table with a speakerphone, notes and a mug",
)
def conference_room(
    cv: Canvas,
    parent,
    behind_table: Slot = None,
    on_table: Slot = None,
    id="location-conference-room",
    shots=None,
    rising: bool | None = True,
    on_wall: Slot = None,
):
    """``behind_table`` seats an office actor at :data:`CONFERENCE_SEAT`; ``rising`` turns the board's trend, and
    ``None`` leaves the wall bare for ``on_wall``, which draws over the wall and behind the light and the chair."""
    ink = cv.ink
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    wall = cv.grad("conference-wall", [(0, "#C3CED2"), (0.5, "#E6EBE9"), (1, "#CCD5D7")], (0, 0, 1, 0.15))
    carpet = cv.grad("conference-carpet", [(0, "#56636A"), (1, "#3F4A50")], (0, 0, 0, 1))
    cv.rect(g, 0, 0, 1080, 1260, wall)
    cv.rect(g, 0, 1260, 1080, 660, carpet)
    cv.rect(g, 0, 1236, 1080, 24, "#F2F2EE", ink, 3)  # the baseboard
    cv.rect(g, 0, 0, 1080, 118, "#EEF1EF")
    cv.line(g, 0, 118, 1080, 118, ink, 3)
    cv.rect(g, 250, 44, 580, 28, "#FFFDF4", ink, 3, radius=14)  # a linear ceiling light
    props.blinds_window(cv, g, 40, 210, 330, 880, id=f"{id}-window")
    if rising is not None:
        props.whiteboard(cv, g, *CONFERENCE_BOARD, rising=rising, id=f"{id}-whiteboard")
    _call(on_wall, g)
    light = cv.group(g, f"{id}-light")
    cv.path(light, "M56 762 L356 762 L820 1236 L520 1236Z", "#FFE7B0", cv.clear, 0, opacity=0.34)
    cv.path(light, "M56 762 L356 762 L1000 1460 L700 1460Z", "#FFE7B0", cv.clear, 0, opacity=0.14)
    cv.rect(light, 250, 72, 580, 90, props.GLOW, opacity=0.18)
    chair = cv.group(g, f"{id}-chair")
    mesh = cv.grad("chair-mesh", [(0, "#4A4F52"), (0.5, "#2F3437"), (1, "#3D4245")], (0, 0, 1, 0))
    cv.path(chair, "M378 1150 L372 700 Q376 618 460 610 L620 610 Q704 618 708 700 L702 1150Z", mesh, ink, 5)
    cv.path(chair, "M402 1140 L398 712 Q402 640 466 636 L614 636 Q678 640 682 712 L678 1140Z", cv.clear, "#5D6366", 2)
    cv.path(chair, "M396 660 Q420 628 470 626", stroke="#8D9497", sw=4, opacity=0.7)
    _call(behind_table, g)
    table = cv.group(g, f"{id}-table")
    top = cv.grad("walnut-top", [(0, "#6E4A31"), (0.45, "#946740"), (1, "#5F3F2A")], (0, 0, 0.3, 1))
    cv.rect(table, -10, CONFERENCE_TABLE_Y, 1100, 590, top, ink, 4)
    for k, yy in enumerate((1190, 1290, 1420, 1580)):
        cv.path(
            table, f"M0 {yy} Q300 {yy - 14 + 6 * k} 560 {yy + 4} T1080 {yy - 6}", stroke="#4E3322", sw=2.5, opacity=0.4
        )
    cv.path(table, "M90 1134 L330 1134 L560 1716 L320 1716Z", "#FFFFFF", cv.clear, 0, opacity=0.13)  # the window
    cv.rect(table, 0, 1762, 1080, 158, "#262D31", opacity=0.45)  # the table's shadow on the carpet
    for xx in (90, 930):
        cv.rect(table, xx, 1740, 60, 200, "#3E2819", ink, 4)  # the legs
        cv.rect(table, xx + 8, 1760, 10, 160, "#6B4A33", opacity=0.7)
    cv.rect(table, -10, 1716, 1100, 46, "#4A3020", ink, 4)
    cv.rect(table, -10, 1716, 1100, 8, "#B48660", opacity=0.6)
    signature.code(cv, props.papers(cv, table, 70, 1290, 0.82, -7), 20, 10, 11, color="#5C625D")
    cv.path(table, "M300 1330 L392 1268", stroke="#1F2B4A", sw=9)  # a pen across the notes
    cv.path(table, "M300 1330 L312 1322", stroke="#C9A24E", sw=9)
    props.speakerphone(cv, table, 560, 1330, id=f"{id}-speakerphone")
    mug = cv.group(table, f"{id}-mug", x=850, y=1250)
    cv.ellipse(mug, -54, 92, 120, 22, "#2B1C12", opacity=0.25)
    cv.path(mug, "M44 22 Q86 24 82 56 Q78 82 42 80", stroke=ink, sw=12)
    cv.path(mug, "M44 22 Q86 24 82 56 Q78 82 42 80", stroke="#F4F1EA", sw=6)
    cv.path(
        mug,
        "M-48 0 L48 0 L44 92 Q0 104 -44 92Z",
        cv.grad("mug", [(0, "#FFFFFF"), (1, "#DCD8CF")], (0, 0, 1, 0)),
        ink,
        4,
    )
    cv.ellipse(mug, -48, -10, 96, 22, "#5A3824", ink, 3.5)
    cv.ellipse(mug, -36, -6, 40, 9, "#8C5E3E", opacity=0.6)
    for k, dx in enumerate((-18, 10)):
        steam = cv.path(mug, f"M{dx} -24 q-14 -26 0 -50 t0 -50", stroke="#FFFFFF", sw=5, opacity=0.5)
        cv.expression(steam, "opacity", f".35+.2*Math.sin(time*2.2+{k * 1.7})")
    signature.cactus(cv, table, 1000, 1236, 0.55)
    _call(on_table, table)
    return g


@register(
    "location",
    "reception",
    summary="Reception: a lit walnut slat wall with a backlit logo, opal globe pendants, a plant, a stone-topped "
    "fluted counter with a monitor and flowers, and a polished floor that reflects them",
)
def reception(
    cv: Canvas,
    parent,
    behind_desk: Slot = None,
    on_desk: Slot = None,
    at_desk: Slot = None,
    id="location-reception",
    shots=None,
):
    """``behind_desk`` at :data:`RECEPTION_CLERK`, ``at_desk`` at :data:`RECEPTION_VISITOR`."""
    ink = cv.ink
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    wall = cv.grad("reception-wall", [(0, "#EDE5D8"), (1, "#D8CCBB")], (0, 0, 0, 1))
    floor = cv.grad("reception-floor", [(0, "#BFB4A3"), (0.3, "#DDD5C8"), (1, "#EAE4DA")], (0, 0, 0, 1))
    cv.rect(g, 0, 0, 1080, COUNTER_FLOOR, wall)
    cv.rect(g, 0, 0, 1080, 112, "#F4F0E9")
    cv.line(g, 0, 112, 1080, 112, ink, 3)
    for xx in (120, 960):
        cv.ellipse(g, xx - 26, 100, 52, 14, "#FFF6DE", ink, 2.5)  # recessed downlights
    cv.rect(g, 0, COUNTER_FLOOR, 1080, 480, floor)
    for k, yy in enumerate((1478, 1540, 1626, 1744, 1900)):
        cv.line(g, 0, yy, 1080, yy, "#B0A694", 2, opacity=0.6 - 0.06 * k)
    for xx in range(-1200, 2400, 240):
        cv.line(g, 540 + (xx - 540) * 0.18, COUNTER_FLOOR, xx, 1920, "#B0A694", 2, opacity=0.45)
    light = cv.group(g, f"{id}-light")
    props.slat_wall(cv, g, 160, 160, 760, 920, light=light, id=f"{id}-slat-wall")
    logo = cv.group(g, f"{id}-logo")
    cv.ellipse(logo, 430, 330, 220, 220, "#2A1F18", ink, 5)
    cv.ellipse(logo, 458, 358, 164, 164, cv.clear, "#FFE6B0", 12)
    cv.path(logo, "M540 382 Q600 440 540 518 Q480 440 540 382Z", "#FFE6B0", cv.clear, 0)
    cv.path(logo, "M540 400 L540 500", stroke="#2A1F18", sw=4)
    props.glow(cv, light, 540, 440, 230, peak=0.3)
    plant = cv.group(g, f"{id}-plant")
    leaf = cv.grad("reception-leaf", [(0, "#4F7A45"), (0.5, "#7FA45F"), (1, "#A9C27F")], (0, 0, 1, 1))
    for d in (
        "M92 1260 Q40 1000 -20 860 Q60 900 104 1250Z",
        "M98 1260 Q90 900 150 700 Q170 900 116 1260Z",
        "M106 1262 Q200 1020 250 900 Q236 1080 122 1266Z",
        "M96 1262 Q10 1100 -30 1060 Q70 1080 110 1262Z",
    ):
        cv.path(plant, d, leaf, ink, 3)
    cv.path(plant, "M108 1250 Q132 960 150 760", stroke="#C9DA9F", sw=3, opacity=0.7)
    planter = cv.grad("planter", [(0, "#F4F0E8"), (0.6, "#D9D2C4"), (1, "#BDB4A4")], (0, 0, 1, 0))
    cv.path(plant, "M26 1250 L190 1250 L176 1440 L40 1440Z", planter, ink, 4)
    for xx in (290, 790):
        props.globe_pendant(cv, g, xx, 300, light=light, id=f"{id}-pendant-{xx}")
        cv.ellipse(light, xx - 90, 1470, 180, 34, props.GLOW, opacity=0.3)  # its reflection on the floor
    _call(behind_desk, g)
    props.reception_counter(cv, g, 230, 1010, COUNTER_Y, COUNTER_FLOOR, id=f"{id}-counter")
    shine = cv.grad("floor-reflection", [(0, "#8C7F6E80"), (1, "#8C7F6E00")], (0, 0, 0, 1))
    cv.rect(g, 246, COUNTER_FLOOR + 2, 780, 120, shine, opacity=0.5)  # the counter mirrored in the floor
    desk = cv.group(g, f"{id}-desk")
    cv.path(desk, "M790 1060 L776 1040 L864 1040 L850 1060Z", "#3A3F42", ink, 3)
    cv.rect(desk, 812, 990, 16, 52, "#4A5054", ink, 2.5)
    cv.rect(desk, 730, 880, 180, 118, "#33383B", ink, 4, radius=10)  # the monitor, seen from behind
    cv.ellipse(desk, 806, 928, 28, 22, "#4A5054", ink, 2)
    cv.path(desk, "M742 892 L800 892", stroke="#7B8387", sw=3, opacity=0.7)
    vase = cv.grad("vase", [(0, "#BFE1DC"), (0.5, "#8CC3BC"), (1, "#5E9C95")], (0, 0, 1, 0))
    for (fx, fy), col in (((296, 930), "#F2A3A0"), ((326, 912), "#F7D27A"), ((352, 936), "#F2A3A0")):
        cv.path(desk, f"M324 1040 Q{(fx + 324) / 2} {fy + 60} {fx} {fy}", stroke="#5E8A4E", sw=3.5)
        for a in range(5):
            ang = a * 2 * math.pi / 5
            cv.ellipse(desk, fx + 9 * math.cos(ang) - 8, fy + 9 * math.sin(ang) - 8, 16, 16, col, ink, 1.5)
        cv.ellipse(desk, fx - 5, fy - 5, 10, 10, "#E8A94B", ink, 1.5)
    cv.path(desk, "M300 1060 L298 1004 Q324 990 350 1004 L348 1060Z", vase, ink, 3)
    cv.ellipse(desk, 304, 996, 42, 14, "#D7EEEA", ink, 2.5)
    signature.cactus(cv, desk, 450, COUNTER_Y + 6, 0.5)
    signature.code(cv, g, 990, COUNTER_FLOOR - 64, 10, color="#9E9483", align="end")
    _call(on_desk, desk)
    _call(at_desk, g)
    return g

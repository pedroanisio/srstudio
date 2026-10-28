"""Locations: complete sets with named slots where the cast is placed.

Each builder draws the set in z-order and calls the slot callbacks at the right depth,
so a character sits behind the desk and in front of the chair without the episode
knowing the stacking. Slots receive the set's group and return nothing.
"""

from __future__ import annotations

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

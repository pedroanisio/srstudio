"""Locations: complete sets with named slots where the cast is placed.

Each builder draws the set in z-order and calls the slot callbacks at the right depth,
so a character sits behind the desk and in front of the chair without the episode
knowing the stacking. Slots receive the set's group and return nothing.

The office, café and park sets take a ``cactus`` slot (ADR 0039): it replaces the set's own signature cactus at the
same depth and must draw exactly one (:func:`srstudio.signature.home_cactus`), so the cactus can perform without a
second one in the shot. Without it the set is drawn as before, byte for byte.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from . import checks, look, props, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

Slot = Callable[[object], None] | None


class LocationError(SrstudioError, ValueError):
    """A location was given an option it cannot draw."""


def _call(slot: Slot, g):
    if slot is not None:
        slot(g)


def _check_slots(**slots: object) -> None:
    """Validate presence without executing callbacks or allocating drawing resources."""
    for name, slot in slots.items():
        if slot is not None and not callable(slot):
            raise LocationError(
                f'{name} must be a drawing callback or None',
                code='location.slot',
                path=name,
                actual=slot,
                expected='a callable accepting the supplied Group, or None',
                remedy='Pass a callback receiving the drawing group; use None to omit this slot.',
            )


def _check_depth(depth) -> None:
    if depth is not None and not (checks.number(depth) and depth > 0):
        raise LocationError(
            'depth is a far-plane blur radius in px above 0',
            code='location.depth',
            path='depth',
            actual=depth,
            expected='a finite positive blur radius in pixels, or None',
            remedy='Pass a positive pixel radius; use None to disable depth blur.',
        )


def _far(cv: Canvas, g, depth: float | None, overscan: bool = False):
    """Where a set draws its far plane: ``g`` itself, or with ``depth`` a group in it blurred by that radius
    (:func:`srstudio.look.depth`), which ``overscan`` passes on. The cast, the props and the signature marks are drawn
    outside it."""
    if depth is None:
        return g
    return look.depth(cv, g, f"cutout-depth-{depth:g}", depth, overscan=overscan)


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


def _refuse_instanced_hand_off(instanced: bool, cactus: Slot):
    if instanced and cactus is not None:
        raise signature.SignatureError(
            "an instanced office draws its desk once for every angle; hand its cactus "
            "over on the inline drawing (instanced=False)"
        )


def _office_desk_front(cv: Canvas, g, p, cactus: Slot = None):
    """The interviewer's desk with its papers and laptop, in front of whoever sits behind it."""
    cv.path(g, "M0 1217 L1080 1137 L1080 1533 L0 1588Z", p["desk"], cv.ink, 4)
    props.woodgrain(cv, g, 1200, 355)
    cv.path(g, "M0 1590 L1080 1537 L1080 1920 L0 1920Z", p["desk_front"], cv.ink, 4)
    signature.code(cv, props.papers(cv, g, 467, 1197, 0.88, -3), 20, 10, 11, color="#5C625D")
    signature.home_cactus(cv, g, 780, 1200, 0.55, slot=cactus)  # between the papers and the laptop, far corner
    props.laptop(cv, g)


@register(
    "location",
    "office-wide",
    summary="Office, wide shot: wall art, plant, desk, laptop, the candidate's back",
    examples=(
        'from srstudio import cast, get\n'
        'location = ep.setup(\n'
        '    get("location", "office-wide"), [(0, ep.t.duration)],\n'
        '    at_desk=lambda group: ep.perform(cast.Manager(ep.cv), group, 560, 724, 1.45),\n'
        ')',
    ),
)
def office_wide(
    cv: Canvas,
    parent,
    at_desk: Slot = None,
    id="wide-office-angle",
    shots=None,
    instanced=False,
    cactus: Slot = None,
    *,
    depth: float | None = None,
):
    """``instanced`` places the room and the desk as shared symbols (drawn once per document).

    The engine draws an instance into an offscreen at its symbol's frame size and scales that texture, so
    a camera push-in on an instanced angle softens its edges: keep the inline drawing for angles that zoom.
    ``cactus`` draws the desk's cactus instead of the set (ADR 0039); it needs the inline drawing. ``depth`` blurs
    the room behind the desk (wall, art, plant) by that many px; the desk, the cast and the marks stay sharp."""
    _check_slots(at_desk=at_desk, cactus=cactus)
    _refuse_instanced_hand_off(instanced, cactus)
    _check_depth(depth)
    if instanced and depth is not None:
        raise LocationError("an instanced office shares its room with every angle; blur its depth inline")
    p = props.office_paints(cv)
    g = cv.group(parent, id)
    if shots is not None:
        cv.gate(g, shots)  # the gate precedes the drawing, as in the shipped scenes
    if instanced:
        cv.instance(g, f"{id}-room", _office_room_symbol(cv))
    else:
        _office_room(cv, _far(cv, g, depth, overscan=True), p)
    props.chair(cv, g)
    _call(at_desk, g)
    if instanced:
        cv.instance(g, f"{id}-desk-front", _office_desk_front_symbol(cv))
    else:
        _office_desk_front(cv, g, p, cactus)
    props.candidate_back(cv, g)
    return g


@register(
    "location",
    "office-desk",
    summary="Office, wide shot without the foreground candidate: whoever sits behind "
    "the desk; chair=False leaves the chair to the slot (to spin it)",
)
def office_desk(
    cv: Canvas,
    parent,
    behind_desk: Slot = None,
    chair: bool = True,
    id="desk-office-angle",
    shots=None,
    instanced=False,
    cactus: Slot = None,
):
    """``instanced`` places the room and the desk as shared symbols; inline, the plant takes an id of its own.

    As for :func:`office_wide`, keep the inline drawing for an angle the camera zooms into. ``cactus`` draws the
    desk's cactus instead of the set, after ``behind_desk`` and before the desk's front (ADR 0039)."""
    _check_slots(behind_desk=behind_desk, cactus=cactus)
    _refuse_instanced_hand_off(instanced, cactus)
    p = props.office_paints(cv)
    g = cv.group(parent, id)
    if shots is not None:
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
        _office_desk_front(cv, g, p, cactus)
    return g


@register(
    "location",
    "office-reverse",
    summary="Office, reverse angle on the candidate: warm wall, gray chair, glass of water",
)
def office_reverse(
    cv: Canvas,
    parent,
    in_chair: Slot = None,
    id="candidate-reverse-angle",
    shots=None,
    cactus: Slot = None,
    *,
    depth: float | None = None,
    chair: bool = True,
):
    """``depth`` blurs the wall behind the chair by that many px; the chair, the cast, the desk and the marks stay
    sharp. ``chair=False`` leaves the chair to the slot (to sink it)."""
    _check_slots(in_chair=in_chair, cactus=cactus)
    _check_depth(depth)
    p = props.office_paints(cv)
    ink = cv.ink
    g = cv.group(parent, id)
    if shots is not None:
        cv.gate(g, shots)  # the gate precedes the drawing, as in the shipped scenes
    far = _far(cv, g, depth, overscan=True)
    cv.rect(far, 0, 0, 1080, 1920, p["warm_wall"])
    cv.rect(far, 0, 0, 14, 1410, "#818074", ink, 3)
    cv.line(far, 20, 0, 20, 1402, "#ECE0C9", 3)
    for y in [8, 342]:
        cv.path(far, f"M1069 {y + 12} L1086 {y} L1086 {y + 38} L1071 {y + 43}Z", "#A49176", ink, 3)
    if chair:
        props.chair(cv, g, "gray")
    _call(in_chair, g)
    cv.rect(g, 0, 1399, 1080, 433, p["desk"], ink, 4)
    props.woodgrain(cv, g, 1418, 390, 12)
    cv.rect(g, 0, 1833, 1080, 20, "#B09171", ink, 3)
    cv.rect(g, 0, 1856, 1080, 64, p["desk_front"])
    signature.code(cv, props.papers(cv, g, 649, 1482, 1.23, 6), 20, 10, 11, color="#5C625D")
    signature.home_cactus(cv, g, 120, 1440, 0.9, slot=cactus)
    props.water_glass(cv, g)
    return g


FINISH: dict[str, dict[str, float | str]] = {  # the opt-in Cutout grade: warm corners and a soft lift on the lamps
    "vignette": dict(amount=0.24, radius=0.95, softness=0.8, color="#3b2a1e"),
    "bloom": dict(threshold=0.9, radius=18, intensity=0.18),
}


def finish(cv: Canvas, parent, id: str = "cutout-finish"):
    """A group in ``parent`` graded by :data:`FINISH`, for an episode to draw its sets into (camera moves stay
    inside it, so the grade holds still on the frame). Opt-in: a set drawn without it is unchanged. No grain, so a
    still opening stays still; no blur, so the signature marks stay sharp."""
    g = cv.group(parent, id)
    return cv.apply(g, *(cv.effect(f"cutout-{kind}", kind, **attrs) for kind, attrs in FINISH.items()))


MENU_CHARS = 14  # the most characters a line of the café's menu board holds at its size


@register(
    "location",
    "cafe",
    summary="Café interior: tiles, shelf, menu, masked window, pendants, espresso machine, counter",
    examples=(
        'from srstudio import cast, get\n'
        'location = ep.setup(\n'
        '    get("location", "cafe"), [(0, ep.t.duration)],\n'
        '    at_counter=lambda group: ep.perform(cast.Customer(ep.cv), group, 270, 1035, 1.53),\n'
        ')',
    ),
)
def cafe(
    cv: Canvas,
    parent,
    behind_counter: Slot = None,
    at_counter: Slot = None,
    on_counter: Slot = None,
    id="location-cafe",
    shots=None,
    cactus: Slot = None,
    *,
    menu: tuple[str, str, str] | None = None,
    code_on_shelf: bool = False,
):
    """``menu`` letters the board's three lines under its title (the two prices and the footer, each 1 to
    :data:`MENU_CHARS` characters) with an episode's own; ``None`` draws the shipped board, byte for byte.
    ``code_on_shelf`` moves the signature code from the board's corner to the shelf's edge, for a reel with someone
    standing in front of the board."""
    _check_slots(behind_counter=behind_counter, at_counter=at_counter, on_counter=on_counter, cactus=cactus)
    if menu is not None and not (
        isinstance(menu, tuple)
        and len(menu) == 3
        and all(isinstance(line, str) and 0 < len(line.strip()) and len(line) <= MENU_CHARS for line in menu)
    ):
        raise LocationError(f"menu is a tuple of three lines of 1 to {MENU_CHARS} characters, got {menu!r}")
    p = props.cafe_paints(cv)
    ink = cv.ink
    g = cv.group(parent, id)
    if shots is not None:
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
    if menu is None:
        props.menu_board(cv, g)
    else:
        coffee, pastry, footer = menu
        props.menu_board(
            cv,
            g,
            items=(
                ("menu-title", "CAFÉ", 343, 90, 67, "#F3DCA4"),
                ("menu-coffee", coffee, 458, 67, 34, "#F5EBD5"),
                ("menu-pastry", pastry, 534, 67, 34, "#F5EBD5"),
                ("menu-wifi", footer, 634, 61, 31, "#A9CBB8"),
            ),
        )
    if code_on_shelf:
        signature.code(cv, g, 555, 1017, 12, color="#F3DCA4", align="end")
    else:
        signature.code(cv, g, 445, 708, 11, color="#C49B68", opacity=0.9, align="end")
    props.cafe_window(cv, g)
    for xx in [300, 850]:
        props.pendant_light(cv, g, xx)
    for i in range(3):
        props.bean_jar(cv, g, 85 + i * 93)
    signature.home_cactus(cv, g, 430, 1012, 0.6, slot=cactus)  # on the shelf, after the jars
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


PARK_SEAT_Y = 1262  # where a seated actor's torso meets the bench, under the backrest and above the seat's edge


def park_seat_y(bottom: float, scale: float) -> float:
    """The ``y`` that seats an actor whose torso ends at ``bottom`` (rig units) on the park bench at ``scale``."""
    return PARK_SEAT_Y - bottom * scale


@register("location", "park", summary="Park: buildings, lawn, path, swaying tree, shrubs, sign, bench")
def park(
    cv: Canvas,
    parent,
    on_bench: Slot = None,
    beside_bench: Slot = None,
    id="location-park",
    shots=None,
    cactus: Slot = None,
    *,
    sign_lettering: bool = True,
):
    """``sign_lettering=False`` keeps the sign's post, board and signature code but leaves its lettering out: the
    safe-area audit (SA01) measures a text layer even off frame, so a framing that crops the sign away must not draw
    it. The default draws the set as before, byte for byte."""
    _check_slots(on_bench=on_bench, beside_bench=beside_bench, cactus=cactus)
    if not isinstance(sign_lettering, bool):
        raise LocationError(f"sign_lettering is True or False, got {sign_lettering!r}")
    p = props.cafe_paints(cv)
    g = cv.group(parent, id)
    if shots is not None:
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
    if sign_lettering:
        props.park_sign(cv, g)
    else:
        props.park_sign(cv, g, text=None)
    signature.code(cv, g, 1030, 624, 9, color="#F0E7CF", opacity=0.85, align="end")
    props.bench(cv, g)
    signature.home_cactus(cv, g, 905, 1300, 0.75, slot=cactus)  # on the grass beside the bench
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
RECEPTION_CODE = (990, COUNTER_FLOOR - 64)  # the code on the counter's face, by its top right corner


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
    speaker_talk: Sequence[tuple[float, float]] = (),
):
    """``behind_table`` seats an office actor at :data:`CONFERENCE_SEAT`; ``rising`` turns the board's trend, and
    ``None`` leaves the wall bare for ``on_wall``, which draws over the wall and behind the light and the chair.
    ``speaker_talk`` lights the speakerphone in the spans a caller speaks (:func:`props.speakerphone`)."""
    _check_slots(behind_table=behind_table, on_table=on_table, on_wall=on_wall)
    ink = cv.ink
    g = cv.group(parent, id)
    if shots is not None:
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
    props.speakerphone(cv, table, 560, 1330, id=f"{id}-speakerphone", talk=speaker_talk)
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
    cactus: Slot = None,
    code_at: tuple[float, float] | None = None,
):
    """``behind_desk`` at :data:`RECEPTION_CLERK`, ``at_desk`` at :data:`RECEPTION_VISITOR`; ``cactus`` takes over the
    counter's cactus (:func:`srstudio.signature.home_cactus`) for a reel that puts something in front of it, and
    ``code_at`` moves the code (its top right, default :data:`RECEPTION_CODE`) for a reel whose framing leaves it
    out."""
    _check_slots(behind_desk=behind_desk, on_desk=on_desk, at_desk=at_desk, cactus=cactus)
    ink = cv.ink
    g = cv.group(parent, id)
    if shots is not None:
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
    signature.home_cactus(cv, desk, 450, COUNTER_Y + 6, 0.5, slot=cactus)
    code_x, code_y = code_at or RECEPTION_CODE
    signature.code(cv, g, code_x, code_y, 10, color="#9E9483", align="end")
    _call(on_desk, desk)
    _call(at_desk, g)
    return g


ELEVATOR_FLOOR = 1760  # where a standing rider's soles meet the cab floor
ELEVATOR_BACK = (150, 230, 930, 1500)  # the back wall: left x, top y, right x, the floor line
DOOR_X, DOOR_TOP, DOOR_W = 340, 560, 200  # the doors' left edge, top, and each panel's width (they meet at x 540)
DOOR_SLIDE = 0.45  # seconds a door takes to slide open or shut
FLOOR_MAX, BUTTONS = 99, 12  # the display's two digits; the panel's buttons, floors 1 to 12
SEGMENTS = {  # seven-segment digits: a top, b top right, c bottom right, d bottom, e bottom left, f top left, g middle
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg",
}  # fmt: skip
_SEG = {  # x, y, w, h of each segment in a 34 × 60 cell
    "a": (4, 0, 26, 6), "b": (28, 4, 6, 24), "c": (28, 32, 6, 24), "d": (4, 54, 26, 6),
    "e": (0, 32, 6, 24), "f": (0, 4, 6, 24), "g": (4, 27, 26, 6),
}  # fmt: skip
LED, LED_OFF = "#FF5A3C", "#3A1E1A"


def elevator_stand_y(bottom: float, scale: float) -> float:
    """The ``y`` that stands an office actor with ``legs="standing"`` (torso ``bottom``) on the cab floor."""
    from .cast import OfficeActor

    return ELEVATOR_FLOOR - (bottom + OfficeActor.STANDING_LEGS) * scale


def _check_floors(floors) -> None:
    if not floors or floors[0][0] != 0:
        raise LocationError("the floor display needs (second, floor) pairs starting at 0")
    for (a, _), (b, _) in zip(floors, floors[1:], strict=False):
        if not b > a:
            raise LocationError(f"floor changes must be in time order: {a} then {b}")
    for _, n in floors:
        if not (isinstance(n, int) and 1 <= n <= FLOOR_MAX):
            raise LocationError(f"a floor is a whole number 1 to {FLOOR_MAX}, got {n!r}")


def _check_doors(doors) -> None:
    last = -math.inf
    for a, b in doors:
        if not (0 <= a < b) or a < last:
            raise LocationError(f"doors open and shut in order, each span after the last one shut: {(a, b)!r}")
        last = b + DOOR_SLIDE


def _digit(cv: Canvas, parent, ch: str, x, y, id: str):
    g = cv.group(parent, id, x=x, y=y)
    for seg in SEGMENTS[ch]:
        sx, sy, sw, sh = _SEG[seg]
        cv.rect(g, sx, sy, sw, sh, LED, radius=2)
    return g


@register(
    "location",
    "elevator",
    summary="Elevator cab: brushed steel walls, sliding doors onto a hallway, a seven-segment floor display, a "
    "button panel with the rider's floor lit, a ceiling light and handrails",
)
def elevator(
    cv: Canvas,
    parent,
    riders: Slot = None,
    on_floor: Slot = None,
    id="location-elevator",
    shots=None,
    floors: Sequence[tuple[float, int]] = ((0.0, 1),),
    doors: Sequence[tuple[float, float]] = (),
    lit: int | None = None,
    going: str = "up",
    depth: float | None = None,
    hallway: Slot = None,
):
    """A cab seen from inside, the doors on the back wall: ``riders`` stand in front of them facing the camera
    (office actors with ``legs="standing"`` at :func:`elevator_stand_y`), and ``on_floor`` draws in front of the
    riders (a pigeon walking in). ``floors`` is ``(second, floor)`` from 0: the display shows each floor until the
    next; ``doors`` are ``(open, shut)`` spans, each door sliding :data:`DOOR_W` behind the wall over
    :data:`DOOR_SLIDE` seconds onto the hallway; ``lit`` lights a floor's button (1 to :data:`BUTTONS`); ``going``
    points the display's arrow ``"up"`` (the default) or ``"down"``; ``depth`` blurs the hallway seen through the
    doorway by that many px (its cactus, the cab and the riders stay sharp); ``hallway`` draws in the hallway, in
    focus, behind the doors (someone waiting there, seen while they are open)."""
    _check_slots(riders=riders, on_floor=on_floor, hallway=hallway)
    _check_depth(depth)
    _check_floors(floors)
    _check_doors(doors)
    if lit is not None and not (isinstance(lit, int) and 1 <= lit <= BUTTONS):
        raise LocationError(f"lit is a button, 1 to {BUTTONS}, got {lit!r}")
    if going not in ("up", "down"):
        raise LocationError(f"going is \"up\" or \"down\", got {going!r}")
    ink = cv.ink
    left, top, right, base = ELEVATOR_BACK
    g = cv.group(parent, id)
    if shots is not None:
        cv.gate(g, shots)
    steel = cv.grad("elevator-steel", [(0, "#AEB6BA"), (0.5, "#D5DADB"), (1, "#A3ABAF")], (0, 0, 1, 0))
    side = cv.grad("elevator-side", [(0, "#8E979C"), (1, "#B9C0C2")], (0, 0, 1, 0))
    cv.path(g, f"M0 0 L1080 0 L{right} {top} L{left} {top}Z", "#E7E9E6", ink, 3)  # the ceiling
    cv.path(g, f"M0 0 L{left} {top} L{left} {base} L0 1720Z", side, ink, 3)
    cv.path(g, f"M1080 0 L{right} {top} L{right} {base} L1080 1720Z", side, ink, 3)
    floor = cv.grad("elevator-floor", [(0, "#5C5550"), (1, "#3E3935")], (0, 0, 0, 1))
    cv.path(
        g, f"M{left} {base} L{right} {base} L1080 1720 L1080 2600 L0 2600 L0 1720Z", floor, ink, 3
    )  # deep: close-ups
    for k in range(1, 5):  # the floor's diamond plate seams, in perspective
        xb, xf = left + (right - left) * k / 5, 1080 * k / 5
        cv.line(g, xb, base, xf, 1920, "#2E2A27", 2, opacity=0.5)
    # the hallway through the doorway
    hall = _far(cv, g, depth)
    cv.rect(hall, DOOR_X, DOOR_TOP, 2 * DOOR_W, base - DOOR_TOP, "#EADFC8")
    cv.rect(hall, DOOR_X, base - 120, 2 * DOOR_W, 120, "#8C7A63")
    cv.rect(hall, DOOR_X + 60, DOOR_TOP + 120, 120, 150, "#F7F1E3", ink, 3)  # a print on the hallway wall
    cv.path(hall, f"M{DOOR_X + 72} {DOOR_TOP + 250} L{DOOR_X + 110} {DOOR_TOP + 180} L{DOOR_X + 168} {DOOR_TOP + 250}Z",
            "#9DB7A5", ink, 2)  # fmt: skip
    signature.cactus(cv, g, DOOR_X + 300, base - 120, 0.5)  # on the hallway floor, seen when the doors open
    _call(hallway, g)
    # the doors, then the wall around them, so an open door slides behind it
    leaves = cv.group(g, f"{id}-doors")
    for name, x0, sign in (("left", DOOR_X, -1), ("right", DOOR_X + DOOR_W, 1)):
        leaf = cv.group(leaves, f"{id}-door-{name}")
        cv.rect(leaf, x0, DOOR_TOP, DOOR_W, base - DOOR_TOP, steel, ink, 3)
        cv.line(leaf, x0 + DOOR_W / 2, DOOR_TOP + 30, x0 + DOOR_W / 2, base - 30, "#FFFFFF", 4, opacity=0.35)
        if doors:
            keys = [(0.0, 0.0)]
            for a, b in doors:
                keys += [(a, 0.0), (a + DOOR_SLIDE, sign * DOOR_W), (b, sign * DOOR_W), (b + DOOR_SLIDE, 0.0)]
            cv.keys(leaf, "x", keys, hold=False)
    cv.rect(g, left, top, DOOR_X - left, base - top, steel, ink, 3)
    cv.rect(g, DOOR_X + 2 * DOOR_W, top, right - DOOR_X - 2 * DOOR_W, base - top, steel, ink, 3)
    cv.rect(g, DOOR_X, top, 2 * DOOR_W, DOOR_TOP - top, steel, ink, 3)
    cv.rect(g, DOOR_X - 6, DOOR_TOP - 6, 2 * DOOR_W + 12, base - DOOR_TOP + 6, cv.clear, ink, 6)  # the frame
    for x0, x1 in ((left, DOOR_X - 20), (DOOR_X + 2 * DOOR_W + 20, right)):  # the handrails
        cv.rect(g, x0 + 10, 1150, x1 - x0 - 20, 16, "#C9CFD1", ink, 3, radius=8)
    # the floor display above the doors
    cv.rect(g, 470, 410, 140, 100, "#141414", ink, 4, radius=10)
    cv.path(g, "M490 470 L506 440 L522 470Z" if going == "up" else "M490 440 L506 470 L522 440Z", LED)
    for x in (540, 576):  # the unlit segments behind the digits
        dim = cv.group(g, f"{id}-led-off-{x}", x=x, y=430)
        for sx, sy, sw, sh in _SEG.values():
            cv.rect(dim, sx, sy, sw, sh, LED_OFF, radius=2)
    for n in sorted({n for _, n in floors}):
        shown = cv.group(g, f"{id}-floor-{n}")
        text = str(n)
        for k, ch in enumerate(text):
            _digit(cv, shown, ch, 576 - 36 * (len(text) - 1 - k), 430, f"{id}-floor-{n}-digit-{k}")
        cv.keys(shown, "opacity", [(t, 1 if m == n else 0) for t, m in floors])
    # the button panel on the right wall
    panel = cv.group(g, f"{id}-panel")
    cv.path(panel, "M968 760 L1040 740 L1040 1170 L968 1150Z", "#C4CACC", ink, 3)
    for k in range(BUTTONS):
        row, col = divmod(k, 2)
        bx, by = 980 + col * 30, 1096 - row * 62 + col * 4
        on = lit == k + 1
        cv.ellipse(panel, bx, by, 22, 26, "#FFD27A" if on else "#E9ECEC", ink, 2)
    signature.code(cv, panel, 972, 1186, 8, color="#5D6366")
    light = cv.group(g, f"{id}-light")
    cv.rect(g, 330, 70, 420, 70, "#FFFBEE", ink, 3, radius=10)  # the ceiling light
    cv.path(light, f"M330 140 L750 140 L{right - 40} {base} L{left + 40} {base}Z", props.GLOW, cv.clear, 0,
            opacity=0.16)  # fmt: skip
    cv.ellipse(light, 300, 1560, 480, 70, props.GLOW, opacity=0.22)  # its pool on the floor
    _call(riders, g)
    _call(on_floor, g)
    return g

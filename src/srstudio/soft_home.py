"""Soft at home: a sofa in a room with a window, two flats cut in two, and a restaurant's door at dusk.

The rooms of :mod:`srstudio.soft_sets` are built for a close shot of one place. These are for the reels that happen on a
sofa. :func:`den` is a room whose time of day is part of the set: ``day`` rows raise its blind and take the night off
everything in it, and a set's foreground stays out of the dark so the signature marks are seen in either. :func:`flats`
is two homes side by side with one wall between them, for two people who are not in the same room. :func:`doorway` runs
its pavement far below the frame, so a reel can tilt down to what its cast is standing in. The props are what a sofa
collects: a television with no face, a bag of chips, a blanket, a scarf for going out, and slippers for not going out.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import NamedTuple

from . import checks, look, signature
from ._soft_home_contracts import contract
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .soft_sets import FAR_BLUR, FLICKER, FLICKER_STEP, INK_LINE, NIGHT, OVER, Shot, _framed, _framing

__all__ = [
    "BLUE_HOUSE",
    "GREEN_HOUSE",
    "MAX_DIGIT",
    "MAX_HOOK",
    "Room",
    "SoftHomeError",
    "blanket",
    "chip",
    "chip_bag",
    "den",
    "doorway",
    "flats",
    "hook_card",
    "scarf",
    "slippers",
    "television",
]

WIDTH, HEIGHT = 1080, 1920
Slot = Callable[[object], object] | None
Rows = Sequence[tuple[float, float]]

MAX_HOOK = 16  # characters a hook card holds at its size
MAX_DIGIT = 1  # a television counts one digit at a time
BLIND_UP = 0.08  # of the window a raised blind still covers
TILT = 0.6  # seconds a tilt takes unless told otherwise
TV_BARS = (-104.0, -52.0, 0.0, 52.0, 104.0)  # the voice bars across the screen, from its middle
TV_PULSE = 0.09  # seconds a voice bar holds a height
TV_HEIGHTS = (0.5, 1.0, 0.7, 0.35, 0.85, 0.6, 1.0, 0.45)  # how tall each bar stands, in turn
BLUE_GLOW = "#2C4FB0"


class SoftHomeError(SrstudioError, ValueError):
    """A Soft home was asked for something it cannot draw."""


class Room(NamedTuple):
    """A home's colours: its wall and floor, each from top to bottom, and its sofa's line, top and front."""

    wall: tuple[str, str]
    floor: tuple[str, str]
    sofa: tuple[str, str, str]


GREEN_HOUSE = Room(("#F1E2C6", "#E6D2AE"), ("#C79A6B", "#B3855A"), ("#2E4A41", "#8FB3A5", "#769C8E"))
BLUE_HOUSE = Room(("#E3E6DA", "#D3D8CB"), ("#B99C7E", "#A3866A"), ("#4A2E34", "#D8836B", "#BF6B55"))


def _rows(name: str, rows: Rows) -> None:
    times = [t for t, _ in rows]
    fine = rows and times[0] == 0 and all(checks.number(t) and checks.number(v) for t, v in rows)
    if not fine or any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise SoftHomeError(f"{name} are (time, level) rows from 0 in rising time, got {list(rows)!r}")
    if not all(0 <= v <= 1 for _, v in rows):
        raise SoftHomeError(f"{name} levels run 0 to 1, got {list(rows)!r}")


def _sofa(cv: Canvas, g, x: float, y: float, w: float, h: float, room: Room) -> None:
    """A sofa straight on, its back's top at ``y``, ``w`` wide and ``h`` from the back's top to the floor."""
    line, top, front = room.sofa
    cv.rect(g, x + 0.06 * w, y + h - 16, 34, 34, line, radius=6)
    cv.rect(g, x + 0.94 * w - 34, y + h - 16, 34, 34, line, radius=6)
    cv.rect(g, x + 0.05 * w, y, 0.9 * w, 0.72 * h, top, line, INK_LINE, radius=46)
    cv.line(g, x + w / 2, y + 26, x + w / 2, y + 0.6 * h, line, 3)
    cv.rect(g, x + 0.02 * w, y + 0.6 * h, 0.96 * w, 0.4 * h, front, line, INK_LINE, radius=30)
    cv.rect(g, x + 0.02 * w, y + 0.6 * h, 0.96 * w, 0.14 * h, top, line, INK_LINE, radius=26)
    for side in (x - 0.03 * w, x + 0.91 * w):
        cv.rect(g, side, y + 0.34 * h, 0.12 * w, 0.66 * h, front, line, INK_LINE, radius=34)


def _window(cv: Canvas, room, g, rows: Rows, id: str) -> None:
    """The window of a den: a blurred morning, and a blind that ``rows`` raise."""
    x, y, w, h = 610.0, 470.0, 400.0, 590.0
    sky = cv.grad(f"{id}-sky", [(0.0, "#BFDDEE"), (1.0, "#F9E7C4")], (0, 0, 0, 1))
    cv.rect(g, x, y, w, h, sky)
    far = look.depth(cv, g, f"{id}-far", FAR_BLUR)
    cv.ellipse(far, x + 30, y + 390, 240, 190, "#A5C79E")
    cv.ellipse(far, x + 150, y + 350, 230, 230, "#9CC096")
    cv.rect(g, x - 22, y - 22, w + 44, 22, "#FFFFFF", cv.ink, INK_LINE)
    cv.rect(g, x - 22, y + h, w + 44, 22, "#FFFFFF", cv.ink, INK_LINE)
    cv.rect(g, x - 22, y, 22, h, "#FFFFFF", cv.ink, INK_LINE)
    cv.rect(g, x + w, y, 22, h, "#FFFFFF", cv.ink, INK_LINE)
    blind = cv.group(g, f"{id}-blind", x=x, y=y)
    cv.keys(blind, "scaleY", [(t, round(1 - (1 - BLIND_UP) * v, 3)) for t, v in rows], False, kind="sine-in-out")
    cv.rect(blind, 0, 0, w, h, "#EDE4D3", cv.ink, INK_LINE)
    for k in range(1, 13):
        cv.line(blind, 0, k * h / 13, w, k * h / 13, "#CFC2AB", 4)
    cv.line(room, x + w - 6, y, x + w - 6, y + h, "#8A6242", 5)  # the cord


@register(
    "location",
    "soft-den",
    summary="A living room straight on at any hour: a sofa under a window whose blind and daylight are keyed, night "
    "pooled in a screen's blue, and the signature cactus on a side table out of the dark",
    contract=contract('soft-den'),
)
def den(
    cv: Canvas,
    parent,
    *,
    end: float,
    day: Rows = ((0.0, 1.0),),
    still: float = 0.0,
    pool: tuple[float, float] = (470.0, 1120.0),
    shots: Sequence[Shot] = (Shot(0.0),),
    behind: Slot = None,
    cast: Slot = None,
    lit: Slot = None,
    room_colors: Room = GREEN_HOUSE,
    id: str = "soft-den",
):
    """The room: ``day`` rows are (time, level), 0 night with the blind down and 1 morning with it up, and it moves
    between rows. Night pools blue on ``pool`` and flickers from ``still`` seconds on. ``behind`` draws behind the
    sofa, ``cast`` on it, ``lit`` over the dark (a screen makes its own light), and ``shots`` cut in on everything but
    the side table, which holds the signature marks."""
    _rows("day rows", day)
    if not (checks.number(end) and end > 0 and checks.number(still) and 0 <= still < end):
        raise SoftHomeError(f"a den runs to a positive end with its stillness inside it, got {end!r}, {still!r}")
    framing = _framing(shots)
    g = cv.group(parent, id)
    room = _framed(cv, g, f"{id}-room", framing)
    wall = cv.grad(f"{id}-wall", [(0.0, room_colors.wall[0]), (1.0, room_colors.wall[1])], (0, 0, 0, 1))
    cv.rect(room, -OVER, -OVER, WIDTH + 2 * OVER, 1500 + OVER, wall)
    floor = cv.grad(f"{id}-floor", [(0.0, room_colors.floor[0]), (1.0, room_colors.floor[1])], (0, 0, 0, 1))
    cv.rect(room, -OVER, 1500, WIDTH + 2 * OVER, 420 + OVER, floor)
    cv.rect(room, -OVER, 1484, WIDTH + 2 * OVER, 22, "#FFFFFF", cv.ink, INK_LINE)
    pane = cv.group(room, f"{id}-window")
    _window(cv, room, pane, day, id)
    if behind is not None:
        behind(room)
    _sofa(cv, room, 420.0, 1120.0, 680.0, 530.0, room_colors)
    if cast is not None:
        cast(room)
    dark = cv.group(room, f"{id}-night")
    cv.keys(dark, "opacity", [(t, round(1 - v, 3)) for t, v in day], False, kind="sine-in-out")
    flicker = cv.group(dark, f"{id}-flicker")
    x, y = pool
    blue = [(0.0, "#1E3A9C80"), (0.16, "#172E86B4"), (0.32, "#0F1C5CEC"), (0.6, NIGHT)]
    cv.rect(flicker, x - 2000, y - 2000, 4000, 4000, cv.rgrad(f"{id}-pool", blue))
    beats = int(max(end - still, 0.0) / FLICKER_STEP) + 1
    cv.keys(flicker, "opacity", [(0.0, 1.0), *((still + n * FLICKER_STEP, FLICKER[n % 8]) for n in range(beats))])
    if lit is not None:
        lit(room)
    front = cv.group(g, f"{id}-front")
    cv.rect(front, 846, 1752, 260, 190, "#B67B4E", cv.ink, INK_LINE, radius=14)
    cv.rect(front, 830, 1736, 290, 36, "#C98C5C", cv.ink, INK_LINE, radius=12)
    signature.cactus(cv, front, 968, 1744, 0.72)
    signature.code(cv, front, 880, 1800, 15, color="#F3DFCF")
    return g


def _flat(cv: Canvas, g, x: float, room: Room, door_x: float, sofa_x: float, id: str) -> None:
    """One half of :func:`flats`: a wall, a floor, a door on the outer side and a sofa against the middle."""
    w = WIDTH / 2
    wall = cv.grad(f"{id}-wall", [(0.0, room.wall[0]), (1.0, room.wall[1])], (0, 0, 0, 1))
    cv.rect(g, x, -OVER, w, 1440 + OVER, wall)
    floor = cv.grad(f"{id}-floor", [(0.0, room.floor[0]), (1.0, room.floor[1])], (0, 0, 0, 1))
    cv.rect(g, x, 1440, w, 480 + OVER, floor)
    cv.rect(g, x, 1428, w, 16, "#FFFFFF", cv.ink, 3)
    cv.rect(g, door_x, 760, 150, 672, "#FFFFFF", cv.ink, INK_LINE)
    cv.rect(g, door_x + 14, 774, 122, 658, "#C98C5C", cv.ink, INK_LINE)
    cv.ellipse(g, door_x + (104 if door_x < WIDTH / 2 else 22), 1110, 24, 24, "#E9C766", cv.ink, 3)
    _sofa(cv, g, sofa_x, 1040.0, 340.0, 384.0, room)


@register(
    "location",
    "soft-flats",
    summary="Two homes cut in two: side by side with one wall between them, a sofa and a door in each, for a pair who "
    "are not in the same room; a shot cuts in on either",
    contract=contract('soft-flats'),
)
def flats(
    cv: Canvas,
    parent,
    *,
    shots: Sequence[Shot] = (Shot(0.0),),
    left: Room = GREEN_HOUSE,
    right: Room = BLUE_HOUSE,
    cast: Slot = None,
    id: str = "soft-flats",
):
    """The two homes, the wall at x 540. ``cast`` sits on the sofas, and ``shots`` cut in on everything but the
    planter that holds the signature marks: ``Shot(t, 2, 270, 960)`` is the left home alone."""
    framing = _framing(shots)
    g = cv.group(parent, id)
    room = _framed(cv, g, f"{id}-room", framing)
    _flat(cv, room, 0.0, left, 12.0, 176.0, f"{id}-left")
    _flat(cv, room, WIDTH / 2, right, 918.0, 564.0, f"{id}-right")
    cv.rect(room, 534, -OVER, 12, HEIGHT + 2 * OVER, cv.ink)
    if cast is not None:
        cast(room)
    front = cv.group(g, f"{id}-front")
    cv.rect(front, 846, 1752, 260, 190, "#B67B4E", cv.ink, INK_LINE, radius=14)
    cv.rect(front, 830, 1736, 290, 36, "#C98C5C", cv.ink, INK_LINE, radius=12)
    signature.cactus(cv, front, 968, 1744, 0.72)
    signature.code(cv, front, 880, 1800, 15, color="#F3DFCF")
    return g


@register(
    "location",
    "soft-restaurant",
    summary="A restaurant's door at dusk, straight on: lit glass, a plain striped awning and a pavement that runs far "
    "below the frame, so a tilt finds what the cast is standing in",
    contract=contract('soft-restaurant'),
)
def doorway(
    cv: Canvas,
    parent,
    *,
    tilt: float | None = None,
    back: float | None = None,
    drop: float = 640.0,
    seconds: float = TILT,
    cast: Slot = None,
    id: str = "soft-restaurant",
):
    """The door, and from ``tilt`` the camera tilts down ``drop`` px over ``seconds``, and from ``back`` up again. The
    world runs to y 2640, and the marks stand in it on a shelf above the cast: a tilt carries them off the top."""
    if tilt is not None and not (checks.number(tilt) and tilt >= 0):
        raise SoftHomeError(f"a tilt starts at a second >= 0, got {tilt!r}")
    if not (checks.number(drop) and 0 < drop <= 720 and checks.number(seconds) and seconds > 0):
        raise SoftHomeError(f"a tilt drops up to 720 px over positive seconds, got {drop!r}, {seconds!r}")
    if back is not None and (tilt is None or not (checks.number(back) and back >= tilt + seconds)):
        raise SoftHomeError(f"a tilt comes back after it has gone down, got tilt {tilt!r}, back {back!r}")
    g = cv.group(parent, id)
    world = cv.group(g, f"{id}-world")
    if tilt is not None:
        rows = [(0.0, 0.0), (tilt, 0.0), (tilt + seconds, -drop)]
        if back is not None:
            rows += [(back, -drop), (back + seconds, 0.0)]
        cv.keys(world, "y", rows, False, kind="sine-in-out")
    dusk = cv.grad(f"{id}-dusk", [(0.0, "#39406E"), (0.6, "#8A5F86"), (1.0, "#E9A27A")], (0, 0, 0, 1))
    cv.rect(world, -OVER, -OVER, WIDTH + 2 * OVER, 1200 + OVER, dusk)
    far = look.depth(cv, world, f"{id}-far", FAR_BLUR)
    for x, h, w in ((-40, 420, 240), (900, 500, 260)):
        cv.rect(far, x, 1200 - h, w, h, "#3A3550")
    cv.rect(world, 120, 420, 840, 1160, "#A65F47", cv.ink, INK_LINE)  # the restaurant's front
    for k in range(9):
        cv.line(world, 120, 520 + k * 118, 960, 520 + k * 118, "#8C4E3A", 4)
    cv.rect(world, 390, 760, 300, 820, "#FFE3A8", cv.ink, INK_LINE)
    cv.rect(world, 412, 782, 256, 360, "#FFF2CF", cv.ink, INK_LINE, radius=6)
    cv.ellipse(world, 634, 1190, 26, 26, "#E9C766", cv.ink, 3)
    for k in range(6):
        fill = "#C8473E" if k % 2 else "#F7EFE2"
        cv.path(world, f"M {120 + k * 140} 470 h 140 l 0 110 q -70 46 -140 0 Z", fill, cv.ink, INK_LINE)
    cv.rect(world, -OVER, 1580, WIDTH + 2 * OVER, 1060 + OVER, "#8C8F97")
    cv.rect(world, -OVER, 1568, WIDTH + 2 * OVER, 22, "#6E7178", cv.ink, INK_LINE)
    for k in range(6):
        cv.line(world, -OVER, 1720 + k * 190, WIDTH + OVER, 1720 + k * 190, "#7A7D85", 5)
    if cast is not None:
        cast(world)
    cv.rect(world, 736, 760, 200, 58, "#7B5236", cv.ink, INK_LINE, radius=8)  # a shelf above the cast's heads
    signature.cactus(cv, world, 838, 764, 0.62)
    signature.code(cv, world, 760, 772, 15, color="#F3DFCF")
    return g


@register(
    "prop",
    "soft-television",
    summary="A television on a low cabinet with no face: a blue screen, voice bars that move while it talks and a "
    "countdown of one digit at a time",
    contract=contract('soft-television'),
)
def television(
    cv: Canvas,
    parent,
    *,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
    still: float = 0.0,
    talks: Sequence[tuple[float, float]] = (),
    counts: Sequence[tuple[str, float, float]] = (),
    id: str = "soft-television",
):
    """A television 360 wide, its screen's middle on (``x``, ``y``). ``talks`` are its spans of speech, ``counts`` are
    (digit, start, end) on the screen, and the screen's light changes from ``still`` seconds on."""
    if not (checks.number(scale) and scale > 0 and checks.number(still) and still >= 0):
        raise SoftHomeError(f"a television's scale and stillness are numbers, got {scale!r}, {still!r}")
    if any(not (checks.number(a) and checks.number(b) and a < b) for a, b in talks):
        raise SoftHomeError(f"a television's talk spans start before they end, got {list(talks)!r}")
    for digit, a, b in counts:
        if len(digit) != MAX_DIGIT or not digit.isdigit() or not (checks.number(a) and checks.number(b) and a < b):
            raise SoftHomeError(f"a television counts one digit over a span, got {digit!r}, {a!r}, {b!r}")
    if any(a < d and c < b for a, b in talks for _, c, d in counts):
        raise SoftHomeError("a television's voice and its count share one screen, one at a time")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -170, 136, 340, 190, "#7B5236", cv.ink, INK_LINE, radius=12)  # the cabinet, running out of the frame
    cv.rect(g, -36, 112, 72, 30, "#23262C", cv.ink, INK_LINE)
    cv.rect(g, -180, -124, 360, 240, "#23262C", cv.ink, INK_LINE, radius=18)
    glass = cv.grad(f"{id}-glass", [(0.0, "#5F86E6"), (1.0, "#2F52B4")], (0, 0, 0, 1))
    cv.rect(g, -164, -108, 328, 208, glass, radius=10)
    bars = cv.group(g, f"{id}-voice")
    if talks:
        cv.gate(bars, list(talks))
    last = max((b for _, b in talks), default=0.0)
    steps = int(last / TV_PULSE) + 1
    for k, bx in enumerate(TV_BARS):
        bar = cv.group(bars, f"{id}-bar-{k + 1}", x=bx, y=0)
        rows = [(n * TV_PULSE, TV_HEIGHTS[(n + 3 * k) % len(TV_HEIGHTS)]) for n in range(steps)]
        cv.keys(bar, "scaleY", [(0.0, 0.6), *rows[1:]] if talks else [(0.0, 0.2)])
        cv.rect(bar, -15, -66, 30, 132, "#FFFFFF", radius=15, opacity=0.9)
    for k, (digit, a, b) in enumerate(counts):
        shown = cv.group(g, f"{id}-count-{k + 1}")
        cv.gate(shown, [(a, b)])
        cv.text(shown, f"{id}-count-{k + 1}-text", digit, -100, -108, 200, 208, 170, color="#FFFFFF")
    return g


@register(
    "prop",
    "soft-chip-bag",
    summary="An open foil bag of chips with no brand on it, leaning where it was left",
    contract=contract('soft-chip-bag'),
)
def chip_bag(cv: Canvas, parent, x: float, y: float, *, scale: float = 1, id: str = "soft-chip-bag"):
    """A bag 170 wide, its foot's middle on (``x``, ``y``)."""
    if not (checks.number(scale) and scale > 0):
        raise SoftHomeError(f"a chip bag's scale must be a positive number, got {scale!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=-7)
    teeth = "M -82 -220 l 16 -14 l 16 14 l 16 -14 l 16 14 l 16 -14 l 16 14 l 16 -14 l 16 14 l 16 -14 l 16 14"
    cv.path(g, f"{teeth} Q 98 -100 78 -6 Q 0 14 -78 -6 Q -98 -100 -82 -220 Z", "#E8A93B", cv.ink, INK_LINE)
    cv.path(g, "M -70 -150 Q 0 -128 72 -150 L 74 -86 Q 0 -66 -72 -86 Z", "#C8473E")
    cv.ellipse(g, -46, -56, 92, 34, "#F3D08A", opacity=0.8)
    return g


@register("prop", "soft-chip", summary="One chip, held up as evidence", contract=contract('soft-chip'))
def chip(cv: Canvas, parent, x: float = 0, y: float = 0, *, scale: float = 1, id: str = "soft-chip"):
    """A chip 70 wide, centred on (``x``, ``y``)."""
    if not (checks.number(scale) and scale > 0):
        raise SoftHomeError(f"a chip's scale must be a positive number, got {scale!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=8)
    cv.path(g, "M -35 18 Q -30 -30 2 -34 Q 34 -24 36 16 Q 0 32 -35 18 Z", "#EDC25E", cv.ink, INK_LINE)
    cv.ellipse(g, -8, -8, 12, 7, "#C9963A")
    cv.ellipse(g, 12, 6, 10, 6, "#C9963A")
    return g


@register(
    "prop",
    "soft-blanket",
    summary="A checked blanket around the shoulders, for a person who is not going out",
    contract=contract('soft-blanket'),
)
def blanket(
    cv: Canvas,
    parent,
    x: float = 0,
    y: float = 0,
    *,
    scale: float = 1,
    color: str = "#6C8FB5",
    id: str = "soft-blanket",
):
    """A blanket worn under a head centred on (``x``, ``y``): ``scale`` is the wearer's, it falls 330 below the head."""
    if not (checks.number(scale) and scale > 0):
        raise SoftHomeError(f"a blanket's scale must be a positive number, got {scale!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    shape = "M -128 66 Q -220 170 -176 356 Q 0 404 176 356 Q 220 170 128 66 Q 0 142 -128 66 Z"
    cv.path(g, shape, color, cv.ink, 2 * INK_LINE / scale)
    for dx in (-110, -40, 40, 110):
        cv.line(g, dx, 110 + abs(dx) * 0.1, dx * 1.18, 370, "#FFFFFF", 6, opacity=0.35)
    for dy in (190, 280):
        cv.line(g, -178, dy, 178, dy, "#FFFFFF", 6, opacity=0.35)
    cv.path(g, "M -4 112 L -50 366 M 4 112 L 50 366", stroke=cv.ink, sw=INK_LINE / scale)
    return g


@register(
    "prop",
    "soft-scarf",
    summary="A wound scarf with one end hanging, for a person who has gone out after all",
    contract=contract('soft-scarf'),
)
def scarf(
    cv: Canvas, parent, x: float = 0, y: float = 0, *, scale: float = 1, color: str = "#C8473E", id: str = "soft-scarf"
):
    """A scarf under a head centred on (``x``, ``y``): ``scale`` is the wearer's."""
    if not (checks.number(scale) and scale > 0):
        raise SoftHomeError(f"a scarf's scale must be a positive number, got {scale!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    o = 2 * INK_LINE / scale
    cv.path(g, "M 40 110 L 30 268 L 96 268 L 100 104 Z", color, cv.ink, o)
    cv.path(g, "M -116 72 Q 0 138 116 72 Q 130 110 108 138 Q 0 192 -108 138 Q -130 110 -116 72 Z", color, cv.ink, o)
    cv.path(g, "M -104 106 Q 0 156 104 106", stroke=cv.ink, sw=o / 2)
    return g


@register(
    "prop",
    "soft-slippers",
    summary="A pair of fluffy house slippers on the ground, worn to a restaurant",
    contract=contract('soft-slippers'),
)
def slippers(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    *,
    scale: float = 1,
    apart: float = 100.0,
    color: str = "#E79BB0",
    id: str = "soft-slippers",
):
    """One pair, its feet ``apart`` in the wearer's rig units, either side of (``x``, ``y``) on the ground. ``scale`` is
    the wearer's, so a pair lands on a blob's feet."""
    if not (checks.number(scale) and scale > 0 and checks.number(apart) and apart > 0):
        raise SoftHomeError(f"a pair of slippers needs a positive scale and gap, got {scale!r}, {apart!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    o = 2 * INK_LINE / scale
    for side in (-1, 1):
        cx = side * apart / 2
        cv.ellipse(g, cx - 58, -44, 116, 56, "#F7EFE2", cv.ink, o)
        cv.path(g, f"M {cx - 54} -22 Q {cx} -80 {cx + 54} -22 Q {cx} 2 {cx - 54} -22 Z", color, cv.ink, o)
        for k in (-30, -6, 20):
            cv.ellipse(g, cx + k - 11, -62, 24, 22, "#FFFFFF", cv.ink, o / 2)
    return g


@register(
    "graphic",
    "soft-hook-card",
    summary="A white card with a dark outline and a few words on it, shown for a span: a hook a time card cannot hold",
    contract=contract('soft-hook-card'),
)
def hook_card(
    cv: Canvas,
    parent,
    text: str,
    box: tuple[float, float, float, float],
    *,
    start: float = 0.0,
    end: float,
    size: float = 56,
    id: str = "soft-hook-card",
):
    """A card in ``box`` (x, y, width, height) reading ``text`` from ``start`` until ``end``."""
    if not text.strip() or len(text) > MAX_HOOK:
        raise SoftHomeError(f"a hook card reads 1 to {MAX_HOOK} characters, got {text!r}")
    if len(box) != 4 or not all(checks.number(v) for v in box) or box[2] <= 0 or box[3] <= 0:
        raise SoftHomeError(f"a hook card's box is (x, y, width, height) with a positive size, got {box!r}")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise SoftHomeError(f"a hook card shows over a span, got {start!r} to {end!r}")
    x, y, w, h = box
    g = cv.group(parent, id)
    cv.gate(g, [(start, end)])
    cv.rect(g, x, y, w, h, cv.white, cv.ink, 6, radius=min(h / 2, 28))
    cv.text(g, f"{id}-text", text, x, y, w, h, size, color=cv.ink)
    return g

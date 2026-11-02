"""Collage things for tables and corners: a desk phone and its handset, a CV with a blank back, a gravy boat with forks
taped round it, forks, a bank card, a wallet with an empty slot, a shop counter and its till, a receipt, a tiny cup, a
wine glass, a stool, a towel, the corner of a boxing ring, and one eyelid that gives its owner away.

Paper like the rest of the style (ADR 0026): hand-cut edges, an ink line and a drop shadow. A prop holds no timing but
what a caller gives it on the project clock, so a recording that re-times the beats moves it too, and each returns its
group for the caller to key. Lettering is kept to words large enough to read on a phone.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import camera, checks
from ._collage_thing_contracts import contract
from .canvas import Canvas
from .collage import INK, LOOKS, _blob, _cut, _eye_centres, _paper, _smooth, draw_shapes
from .errors import SrstudioError
from .registry import register

__all__ = [
    "CARD_RATIO",
    "PHONE_RATIO",
    "ThingError",
    "bank_card",
    "counter",
    "desk_phone",
    "fork",
    "gravy_boat",
    "handset",
    "receipt",
    "resume",
    "ring_corner",
    "stool",
    "till",
    "tiny_cup",
    "towel",
    "twitch",
    "wallet",
    "wine_glass",
]

PHONE_RATIO = 0.62  # a desk phone's height over its width
CARD_RATIO = 0.63  # a bank card's height over its width
TWITCH = 0.09  # seconds an eyelid stays down in a twitch
TURN = 0.3  # seconds a sheet takes to turn over
FOREVER = 1e6  # a second past the end of any reel
MAX_FORKS = 5  # more than this is a hedge, not a press conference
ROPES = ("#e63946", "#fffaf0", "#1d3557")  # a ring's three ropes, top to bottom
PHONE_BODY, PHONE_EDGE = "#2f3140", "#4a4d60"
STEEL, STEEL_DARK = "#d9dee4", "#9aa3ad"
TAPE = "#c9c2ad"
GRAVY_BOAT = "#f6efe0"


class ThingError(SrstudioError, ValueError):
    """A prop asked for at a size, a count or a time it cannot draw."""


def _size(value: float, what: str) -> float:
    if not (checks.number(value) and value > 0):
        raise ThingError(f"{what} must be positive, got {value!r}")
    return float(value)


def _box(x: float, y: float, w: float, h: float) -> list[tuple[float, float]]:
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def _sheet(cv: Canvas, g, key: str, points: Sequence[tuple[float, float]], fill: str, amount: float = 3.0) -> None:
    draw_shapes(cv, g, _paper(_cut(key, list(points), amount), fill))


def _word(cv: Canvas, g, text: str, x: float, y: float, w: float, h: float, size: float, color: str = INK) -> None:
    """Text in a box of whole pixels, as the engine's text assets take it."""
    cv.text(g, cv.uid("thing"), text, x, y, round(w), round(h), round(size), color=color)


# -- the phone --------------------------------------------------------------------------------------------------------
def _handset_shapes(cv: Canvas, g, length: float) -> None:
    """A handset lying along x, centred on the origin: a bar and two rounded ends."""
    h = length * 0.15
    _sheet(cv, g, "handset-bar", _box(-length / 2, -h / 2, length, h), PHONE_BODY, 2.0)
    for side in (-1, 1):
        draw_shapes(cv, g, [_blob(f"handset-{side}", side * length * 0.42, h * 0.45, length * 0.13, length * 0.1,
                                  PHONE_BODY, n=12, amount=0.02)])  # fmt: skip


@register(
    "prop",
    "collage-handset",
    summary="A desk phone's handset on its own, for a hand or an ear",
    contract=contract('collage-handset'),
)
def handset(cv: Canvas, parent, x: float, y: float, length: float = 340.0, tilt: float = 0.0) -> object:
    """A handset ``length`` long centred on ``x, y``, turned ``tilt`` degrees; returns the group."""
    _size(length, "a handset's length")
    g = cv.group(parent, cv.uid("handset"), x=x, y=y, rotation=tilt)
    _handset_shapes(cv, g, length)
    return g


@register(
    "prop",
    "collage-desk-phone",
    summary="A paper desk phone: keypad, a lit display, the handset on its cradle",
    contract=contract('collage-desk-phone'),
)
def desk_phone(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    w: float = 340.0,
    display: str = "",
    *,
    off_hook: bool = False,
    size: float = 0.0,
) -> object:
    """A desk phone ``w`` wide standing with its foot's centre on ``x, y``, its display saying ``display`` at ``size``
    (empty, a dark screen), with no handset on its cradle when ``off_hook``; returns the group."""
    _size(w, "a desk phone's width")
    if display:
        _size(size, "the display's lettering")
    g = cv.group(parent, cv.uid("desk-phone"), x=x, y=y)
    h = w * PHONE_RATIO
    top = -h * 0.8
    _sheet(cv, g, f"desk-phone-{w}", [(-w / 2, 0), (w / 2, 0), (w * 0.4, top), (-w * 0.4, top)], PHONE_BODY)
    sw, sh = w * 0.72, h * 0.24
    sy = top + h * 0.12
    cv.rect(g, -sw / 2, sy, sw, sh, "#c8f4d4" if display else "#23202b", INK, 3, radius=8)
    if display:
        _word(cv, g, display, -sw / 2 + 6, sy, sw - 12, sh, size)
    pad = w * 0.075
    for row in range(3):
        for col in range(4):
            cv.rect(g, (col - 2) * pad * 1.5 + pad * 0.25, top + h * 0.42 + row * pad * 1.1, pad, pad * 0.8, PHONE_EDGE,
                    radius=4)  # fmt: skip
    if not off_hook:
        rest = cv.group(g, cv.uid("g"), x=0, y=top - h * 0.1)
        _handset_shapes(cv, rest, w * 0.86)
    return g


# -- paper ------------------------------------------------------------------------------------------------------------
@register(
    "prop",
    "collage-resume",
    summary="A CV on one sheet of paper, turning over to show a blank back",
    contract=contract('collage-resume'),
)
def resume(
    cv: Canvas, parent, x: float, y: float, w: float = 300.0, *, tilt: float = 0.0, turn: float | None = None
) -> object:
    """A sheet ``w`` wide centred on ``x, y`` headed CV, turned ``tilt`` degrees; it turns over at project second
    ``turn``, its back blank. Returns the group."""
    _size(w, "a CV's width")
    if turn is not None and not (checks.number(turn) and turn >= 0):
        raise ThingError(f"a sheet turns over at a project second, got {turn!r}")
    h = w * 1.3
    g = cv.group(parent, cv.uid("resume"), x=x, y=y, rotation=tilt)
    front = cv.group(g, cv.uid("g"))
    _sheet(cv, front, f"resume-{w}", _box(-w / 2, -h / 2, w, h), "#fffaf0")
    tall, wide, top = h * 0.16, w * 0.13, -h / 2 + h * 0.08  # the heading drawn, so a shot of any length can hold it
    heavy = max(8.0, w * 0.04)
    cv.path(front, f"M {-w * 0.03} {top} q {-wide * 1.5} {tall / 2} 0 {tall}", fill=cv.clear, stroke=INK, sw=heavy)
    cv.path(front, f"M {w * 0.03} {top} L {w * 0.03 + wide / 2} {top + tall} L {w * 0.03 + wide} {top}", fill=cv.clear,
            stroke=INK, sw=heavy)  # fmt: skip
    for i in range(5):
        length = w * (0.74 - 0.08 * (i % 3))
        ly = -h / 2 + h * (0.4 + 0.11 * i)
        cv.path(
            front, f"M {-length / 2} {ly} L {length / 2} {ly}", fill=cv.clear, stroke="#6b6b76", sw=max(4, w * 0.02)
        )
    if turn is None:
        return g
    mid = round(turn + TURN / 2, 6)
    cv.gate(front, [(0.0, mid)], local=False)
    back = cv.group(g, cv.uid("g"))
    cv.gate(back, [(mid, FOREVER)], local=False)
    _sheet(cv, back, f"resume-back-{w}", _box(-w / 2, -h / 2, w, h), "#fffaf0")
    cv.keys(g, "scaleX", [(turn, 1.0), (mid, camera.EDGE_ON), (round(turn + TURN, 6), 1.0)], hold=False, local=False)
    return g


# -- a table ----------------------------------------------------------------------------------------------------------
@register(
    "prop", "collage-fork", summary="A paper fork, standing on its handle's end", contract=contract('collage-fork')
)
def fork(cv: Canvas, parent, x: float, y: float, length: float = 300.0, tilt: float = 0.0) -> object:
    """A fork ``length`` long with its handle's end on ``x, y`` and its tines up, turned ``tilt`` degrees about that
    end; returns the group."""
    _size(length, "a fork's length")
    g = cv.group(parent, cv.uid("fork"), x=x, y=y, rotation=tilt)
    _fork_shapes(cv, g, length)
    return g


def _fork_shapes(cv: Canvas, g, length: float) -> None:
    w = length * 0.2
    head = -length * 0.68
    stem = length * 0.045
    _sheet(cv, g, "fork-stem", _box(-stem, head, 2 * stem, -head), STEEL, 1.0)
    points = [(-w / 2, head - length * 0.1), (w / 2, head - length * 0.1), (w * 0.3, head + length * 0.06),
              (-w * 0.3, head + length * 0.06)]  # fmt: skip
    _sheet(cv, g, "fork-head", points, STEEL, 1.0)
    for i in (-1, 0, 1):
        tine = i * w * 0.36
        cv.line(g, tine, head - length * 0.09, tine, -length, INK, max(10.0, length * 0.042))
        cv.line(g, tine, head - length * 0.09, tine, -length, STEEL, max(6.0, length * 0.026))


@register(
    "prop",
    "collage-gravy-boat",
    summary="A gravy boat with forks taped round it, pointing like microphones",
    contract=contract('collage-gravy-boat'),
)
def gravy_boat(
    cv: Canvas, parent, x: float, y: float, size: float = 360.0, *, forks: int = 3, tilt: float = 0.0
) -> object:
    """A gravy boat ``size`` long standing with its foot's centre on ``x, y``, ``forks`` forks taped round it with
    their tines up and fanned, turned ``tilt`` degrees; returns the group, which a caller keys to slide."""
    _size(size, "a gravy boat's length")
    if not (type(forks) is int and 0 <= forks <= MAX_FORKS):
        raise ThingError(f"a gravy boat takes 0 to {MAX_FORKS} forks, got {forks!r}")
    g = cv.group(parent, cv.uid("gravy-boat"), x=x, y=y, rotation=tilt)
    h = size * 0.42
    rim = -h
    for i in range(forks):
        spread = (i - (forks - 1) / 2) * 14.0
        stand = cv.group(g, cv.uid("g"), x=spread * size * 0.012, y=rim * 0.55, rotation=spread)
        _fork_shapes(cv, stand, size * 0.95)
    _sheet(cv, g, "boat-saucer", [(-size * 0.5, -size * 0.04), (size * 0.5, -size * 0.04), (size * 0.42, 0),
                                  (-size * 0.42, 0)], "#e8dcc6", 1.5)  # fmt: skip
    body = [(-size * 0.5, rim * 1.1), (-size * 0.2, rim), (size * 0.34, rim), (size * 0.28, rim * 0.34),
            (size * 0.12, -size * 0.04), (-size * 0.16, -size * 0.04), (-size * 0.3, rim * 0.34)]  # fmt: skip
    draw_shapes(cv, g, _paper(_cut(f"boat-{size}", body, 2), GRAVY_BOAT))
    handle = [(size * 0.33, rim * 0.92), (size * 0.5, rim * 0.86), (size * 0.5, rim * 0.5), (size * 0.29, rim * 0.44)]
    cv.path(g, _smooth(handle, closed=False), fill=cv.clear, stroke=INK, sw=size * 0.04)
    if forks:
        _sheet(cv, g, "boat-tape", _box(-size * 0.28, rim * 0.74, size * 0.56, size * 0.11), TAPE, 2.0)
    return g


@register(
    "prop", "collage-tiny-cup", summary="A very small cup on a very small saucer", contract=contract('collage-tiny-cup')
)
def tiny_cup(cv: Canvas, parent, x: float, y: float, size: float = 110.0) -> object:
    """An espresso cup ``size`` wide with its saucer's centre on ``x, y``; returns the group."""
    _size(size, "a cup's width")
    g = cv.group(parent, cv.uid("tiny-cup"), x=x, y=y)
    bowl = [(-size / 2, -size * 0.72), (size / 2, -size * 0.72), (size * 0.34, 0), (-size * 0.34, 0)]
    _sheet(cv, g, "cup-body", bowl, "#fffaf0", 1.0)
    cv.path(g, f"M {size * 0.46} {-size * 0.58} q {size * 0.3} {size * 0.1} {-size * 0.08} {size * 0.36}",
            fill=cv.clear, stroke=INK, sw=max(4.0, size * 0.05))  # fmt: skip
    _sheet(cv, g, "cup-saucer", _box(-size * 0.68, 0, size * 1.36, size * 0.1), "#e8dcc6", 1.0)
    return g


@register(
    "prop",
    "collage-wine-glass",
    summary="A paper wine glass with a little red left in it",
    contract=contract('collage-wine-glass'),
)
def wine_glass(cv: Canvas, parent, x: float, y: float, height: float = 300.0) -> object:
    """A wine glass ``height`` tall standing on ``x, y``; returns the group."""
    _size(height, "a glass's height")
    g = cv.group(parent, cv.uid("wine-glass"), x=x, y=y)
    w = height * 0.46
    cv.line(g, 0, -height * 0.5, 0, 0, INK, max(8.0, height * 0.035))
    cv.line(g, 0, -height * 0.5, 0, 0, "#e6eef2", max(4.0, height * 0.018))
    _sheet(cv, g, "glass-foot", _box(-height * 0.2, -height * 0.03, height * 0.4, height * 0.03), "#e6eef2", 1.0)
    bowl = [
        (-w / 2, -height),
        (w / 2, -height),
        (w * 0.42, -height * 0.62),
        (0, -height * 0.48),
        (-w * 0.42, -height * 0.62),
    ]
    cv.path(g, _smooth(bowl), fill="#e6eef2", stroke=INK, sw=5.0, opacity=0.9)
    wine = [(-w * 0.45, -height * 0.74), (w * 0.45, -height * 0.74), (w * 0.38, -height * 0.6), (0, -height * 0.5),
            (-w * 0.38, -height * 0.6)]  # fmt: skip
    cv.path(g, _smooth(wine), fill="#7a1e35")
    return g


# -- paying -----------------------------------------------------------------------------------------------------------
@register(
    "prop",
    "collage-bank-card",
    summary="A bank card with a stripe, a chip and a name in capitals",
    contract=contract('collage-bank-card'),
)
def bank_card(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    w: float = 330.0,
    name: str = "",
    *,
    colour: str = "#1d3557",
    tilt: float = 0.0,
) -> object:
    """A card ``w`` wide centred on ``x, y``, its holder's ``name`` large enough to read, turned ``tilt`` degrees;
    returns the group, which a caller keys to fly."""
    _size(w, "a card's width")
    h = w * CARD_RATIO
    g = cv.group(parent, cv.uid("bank-card"), x=x, y=y, rotation=tilt)
    _sheet(cv, g, f"card-{w}", _box(-w / 2, -h / 2, w, h), colour, 2.0)
    cv.rect(g, -w / 2 + 2, -h * 0.28, w - 4, h * 0.16, "#14141c")
    cv.rect(g, -w * 0.4, -h * 0.05, w * 0.18, h * 0.2, "#e9c46a", INK, 2, radius=4)
    if name:
        _word(cv, g, name, -w * 0.44, h * 0.18, w * 0.88, h * 0.28, w * 0.16, "#fffaf0")
    return g


@register(
    "prop",
    "collage-receipt",
    summary="A till receipt, whole or torn across its foot",
    contract=contract('collage-receipt'),
)
def receipt(
    cv: Canvas, parent, x: float, y: float, w: float = 260.0, h: float = 420.0, *, torn: bool = False, tilt: float = 0.0
) -> object:
    """A slip ``w`` by ``h`` centred on ``x, y``, printed in grey bars, its foot ripped across when ``torn``, turned
    ``tilt`` degrees; returns the group, which a caller keys to slam, tear or fly."""
    _size(w, "a receipt's width")
    _size(h, "a receipt's length")
    g = cv.group(parent, cv.uid("receipt"), x=x, y=y, rotation=tilt)
    teeth = 7
    foot = [(w / 2 - i * w / teeth, h / 2 - (h * 0.05 if torn and i % 2 else 0.0)) for i in range(teeth + 1)]
    _sheet(cv, g, f"receipt-{w}-{h}-{torn}", [(-w / 2, -h / 2), (w / 2, -h / 2), *foot], "#fffaf0", 2.0)
    for i in range(6):
        cv.rect(g, -w * 0.38, -h * 0.4 + i * h * 0.12, w * (0.76 if i in (0, 5) else 0.5), h * 0.04, "#8d99ae")
    return g


@register(
    "prop",
    "collage-wallet",
    summary="An open wallet: its card slots, one of them empty",
    contract=contract('collage-wallet'),
)
def wallet(
    cv: Canvas, parent, x: float, y: float, w: float = 640.0, *, cards: Sequence[str] = ("#e63946", "#2a9d8f")
) -> object:
    """An open wallet ``w`` wide centred on ``x, y``: a card of each colour of ``cards`` in the top slots, and the
    slot under them empty; returns the group."""
    _size(w, "a wallet's width")
    if len(cards) > 2:
        raise ThingError(f"a wallet shows at most two cards above its empty slot, got {len(cards)}")
    h = w * 0.62
    g = cv.group(parent, cv.uid("wallet"), x=x, y=y)
    _sheet(cv, g, f"wallet-{w}", _box(-w / 2, -h / 2, w, h), "#6b4226")
    cv.line(g, 0, -h / 2 + 8, 0, h / 2 - 8, "#4a2c17", 8)
    slot_w, slot_h = w * 0.4, h * 0.2
    for i, colour in enumerate([*cards, *[None] * (3 - len(cards))]):
        sy = -h / 2 + h * 0.08 + i * h * 0.29
        cv.rect(g, w * 0.05, sy, slot_w, slot_h, colour or "#2a1a0e", INK, 3, radius=6)
        cv.rect(g, w * 0.04, sy + slot_h * 0.72, slot_w + w * 0.02, slot_h * 0.5, "#7d4f2e", INK, 3, radius=4)
    return g


@register(
    "prop",
    "collage-counter",
    summary="The front of a restaurant's counter, with a slab along its top",
    contract=contract('collage-counter'),
)
def counter(
    cv: Canvas, parent, top: float = 1500.0, colour: str = "#7a4a2b", slab: str = "#e9edc9", seam: str = "#5f3a21"
) -> object:
    """A counter or a desk across the frame from ``top`` down, in a shot's ``front``; returns the group."""
    _size(top, "a counter's top")
    g = cv.group(parent, cv.uid("counter"))
    draw_shapes(cv, g, _paper(_box(-60, top + 34, 1200, 1990 - top), colour))
    for x in range(0, 1080, 180):
        cv.line(g, x, top + 44, x, 1920, seam, 6)
    draw_shapes(cv, g, _paper(_box(-60, top, 1200, 44), slab))
    return g


@register("prop", "collage-till", summary="A paper till with a lit readout", contract=contract('collage-till'))
def till(cv: Canvas, parent, x: float, y: float, w: float = 320.0, text: str = "", *, size: float = 0.0) -> object:
    """A till ``w`` wide standing with its foot's centre on ``x, y``, its readout saying ``text`` at ``size``; returns
    the group."""
    _size(w, "a till's width")
    if text:
        _size(size, "the readout's lettering")
    g = cv.group(parent, cv.uid("till"), x=x, y=y)
    h = w * 0.8
    _sheet(cv, g, f"till-{w}", [(-w / 2, 0), (w / 2, 0), (w * 0.42, -h), (-w * 0.42, -h)], "#8d99ae")
    cv.rect(g, -w * 0.36, -h * 0.92, w * 0.72, h * 0.3, "#c8f4d4", INK, 3, radius=6)
    if text:
        _word(cv, g, text, -w * 0.34, -h * 0.92, w * 0.68, h * 0.3, size)
    for row in range(2):
        for col in range(4):
            cv.rect(g, -w * 0.32 + col * w * 0.165, -h * 0.54 + row * h * 0.16, w * 0.12, h * 0.11, "#fffaf0", INK, 2,
                    radius=3)  # fmt: skip
    return g


# -- a corner ---------------------------------------------------------------------------------------------------------
@register(
    "prop", "collage-stool", summary="A corner stool: a round seat on three legs", contract=contract('collage-stool')
)
def stool(cv: Canvas, parent, x: float, y: float, w: float = 300.0) -> object:
    """A stool ``w`` wide, its seat's top centre on ``x, y``; returns the group."""
    _size(w, "a stool's width")
    g = cv.group(parent, cv.uid("stool"), x=x, y=y)
    for dx, foot in ((-0.38, -0.5), (0.0, 0.0), (0.38, 0.5)):
        cv.line(g, dx * w, w * 0.1, foot * w, w * 1.1, INK, w * 0.08)
        cv.line(g, dx * w, w * 0.1, foot * w, w * 1.1, "#a47148", w * 0.05)
    draw_shapes(cv, g, [_blob(f"stool-{w}", 0, w * 0.06, w / 2, w * 0.1, "#bc4749", n=18, amount=0.01)])
    return g


@register(
    "prop",
    "collage-towel",
    summary="A striped towel with a fringe, for a shoulder or a corner",
    contract=contract('collage-towel'),
)
def towel(cv: Canvas, parent, x: float, y: float, w: float = 260.0, h: float = 460.0, *, tilt: float = 0.0) -> object:
    """A towel ``w`` by ``h`` hanging from its top centre on ``x, y``, turned ``tilt`` degrees about it; returns the
    group, which a caller keys to swing."""
    _size(w, "a towel's width")
    _size(h, "a towel's length")
    g = cv.group(parent, cv.uid("towel"), x=x, y=y, rotation=tilt)
    _sheet(cv, g, f"towel-{w}-{h}", _box(-w / 2, 0, w, h), "#fffaf0", 4.0)
    for frac in (0.68, 0.78):
        cv.rect(g, -w / 2 + 3, h * frac, w - 6, h * 0.05, "#457b9d")
    for i in range(9):
        fx = -w / 2 + (i + 0.5) * w / 9
        cv.line(g, fx, h, fx, h + 22, "#e8dcc6", 5)
    return g


@register(
    "prop",
    "collage-ring-corner",
    summary="A boxing ring's padded corner post and its three ropes",
    contract=contract('collage-ring-corner'),
)
def ring_corner(
    cv: Canvas, parent, x: float = 960.0, y: float = 900.0, h: float = 720.0, *, reach: float = 1100.0
) -> object:
    """A post ``h`` tall with its top on ``x, y``, three ropes running ``reach`` px to the left of it; drawn behind the
    cast. Returns the group."""
    _size(h, "a corner post's height")
    _size(reach, "the ropes' reach")
    g = cv.group(parent, cv.uid("ring-corner"))
    for i, colour in enumerate(ROPES):
        ry = y + h * (0.1 + 0.3 * i)
        cv.line(g, x, ry, x - reach, ry + 60, INK, 26)
        cv.line(g, x, ry, x - reach, ry + 60, colour, 18)
    _sheet(cv, g, "corner-post", _box(x - 46, y, 92, h), "#2b2d42")
    for i, colour in enumerate(ROPES):
        cv.rect(g, x - 60, y + h * (0.05 + 0.3 * i), 120, h * 0.12, colour, INK, 4, radius=14)
    return g


# -- one eye ----------------------------------------------------------------------------------------------------------
@register(
    "prop",
    "collage-eye-twitch",
    summary="One eyelid of a Collage character, twitching over a held smile",
    contract=contract('collage-eye-twitch', cast=tuple(LOOKS)),
)
def twitch(cv: Canvas, parent, who: str, times: Sequence[float], *, side: int = 1) -> object:
    """``who``'s eye on ``side`` (-1 its left on screen, 1 its right) shut for :data:`TWITCH` at each project second
    of ``times``, in that figure's coordinates, over a held face; returns the group. Overlapping or touching
    closures keep the eye shut until the last cue ends."""
    if who not in LOOKS:
        raise ThingError(f"{who!r} is not in the Collage cast")
    if side not in (-1, 1):
        raise ThingError(f"side is -1 or 1, got {side!r}")
    seconds = checks.rising(times, ThingError, lambda i, t: f"twitch {i} at {t!r} runs backward", end=FOREVER)
    if not seconds:
        raise ThingError("an eye twitches at least once")
    look = LOOKS[who]
    ex, ey = _eye_centres(look)[0 if side < 0 else 1]
    g = cv.group(parent, cv.uid("twitch"))
    draw_shapes(cv, g, [_blob(f"{who}-twitch{side}", ex, ey, 57, 75, look.skin, n=14, amount=0.01, edge=0)])
    cv.line(g, ex - 44, ey + 8, ex + 44, ey + 8, INK, 7)
    states: list[tuple[float, float]] = [(0.0, 0.0)]
    for t in seconds:
        start, end = round(t, 6), round(t + TWITCH, 6)
        if len(states) > 1 and start <= states[-1][0]:
            states[-1] = (end, 0.0)
        else:
            states += [(start, 1.0), (end, 0.0)]
    cv.keys(g, "opacity", states, local=False)
    return g

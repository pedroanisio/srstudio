"""Toon dinner: a restaurant booth, a laid table that stands in for the desk, the dishes on it and a card reader.

The Toon shots put every character behind the office desk (:func:`srstudio.toon.desk`). A dinner needs a table
instead: :func:`table` is a drop-in replacement, a white tablecloth over the same footprint that carries the signature
as the desk does, so the sets in this module leave it out. :func:`restaurant` is the backdrop: a terracotta wall over
a dark wood wainscot, a framed seascape, a wall sconce, a chalk SPECIALS board where the other sets have their window,
and a red leather booth behind the character. :func:`dishes` lays the table, each dish at its own x and, if asked,
arriving at a time; :func:`card_reader` is a handheld payment terminal whose screen changes on cue (TAP CARD,
DECLINED, APPROVED).

Every measure is a reference screen pixel (:func:`srstudio.toon.fx`/``fy``), like the rest of the style.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import _toon_social_contracts as tc
from . import checks, signature
from .canvas import Canvas
from .registry import register
from .toon import CHAIR_D, FINE_W, INK_W, REF_W, ToonDataError, _path, fh, fx, fy
from .toon_sets import SHADOW, _glow

__all__ = [
    "DISHES",
    "SPECIAL_MAX",
    "SCREEN_MAX",
    "TABLE_Y",
    "TONES",
    "card_reader",
    "dishes",
    "mint",
    "restaurant",
    "table",
]

WALL = (("0", "#8c4a3f"), ("0.6", "#a85d4c"), ("1", "#c27a5e"))
WAINSCOT, WAINSCOT_PANEL, RAIL = "#5a3426", "#6b3f2e", "#7d4b36"
LEATHER, LEATHER_LIGHT = "#b8323a", "#d0474d"
CHALK_BOARD, CHALK, CHALK_ACCENT = "#22302a", "#f4f1e8", "#f2c14e"
WOOD = "#9a6a43"
SCONCE, SCONCE_LIGHT = "#d6b25e", "#ffd88a"
CLOTH, CLOTH_FRONT, CLOTH_FOLD, CLOTH_STRIPE, CLOTH_CODE = "#fbf8f2", "#f1ebe1", "#ddd3c3", "#c8414a", "#c9bfae"
TABLE_Y = 826  # where a dish stands on the cloth, reference pixels
SPECIAL_MAX = 12  # characters of the special's name on the board
PRICE_LINE = 8  # characters per line of the price, two lines at most
SCREEN_MAX = 10  # characters on the card reader's screen
DISH_SCALE = 1.5  # dishes are drawn larger than life, to read beside the characters
READER_SCALE = 0.75  # the reader stands below the specials board
TONES = {"idle": ("#d9ecf2", "#1e293b"), "bad": ("#ffd6d2", "#b42318"), "good": ("#d6f5dd", "#1f7a3a")}


# -- the restaurant --------------------------------------------------------------------------------------------------
@register(
    "location",
    "toon-restaurant",
    contract=tc.contract('toon-restaurant'),
    summary="A bistro booth: a terracotta wall, a dark wainscot, a framed seascape, a sconce, a chalk SPECIALS "
    "board and a red leather banquette behind the character",
)
def restaurant(
    cv: Canvas, parent, special: tuple[str, str] = ("LOBSTER", "MARKET\nPRICE"), lettering: bool = True
) -> None:
    """The backdrop of a dinner shot; ``special`` is the board's dish (1 to :data:`SPECIAL_MAX` characters) and its
    price (one or two lines of up to :data:`PRICE_LINE`). ``lettering=False`` leaves the board's words out, for a shot
    in which something stands in front of them: the engine measures a text layer even when it is covered."""
    dish, price = special
    lines = price.split("\n")
    if not dish.strip() or len(dish) > SPECIAL_MAX or not price.strip() or len(lines) > 2:
        raise ToonDataError(f"the special is a dish of 1 to {SPECIAL_MAX} characters and a price, got {special!r}")
    if any(len(line) > PRICE_LINE for line in lines):
        raise ToonDataError(f"the special's price takes lines of up to {PRICE_LINE} characters, got {price!r}")
    ink = cv.ink
    g = cv.group(parent, cv.uid("g"))
    wall = cv.grad("toon-restaurant-wall", [(float(o), c) for o, c in WALL], (0, 0, 0, 1))
    cv.rect(g, 0, 0, cv.width, cv.height, wall)
    # a framed seascape where the other sets hang their clock
    cv.rect(g, fx(44), fy(338), fh(130), fh(100), SHADOW, cv.clear, 0, radius=fh(3), opacity=0.2)
    cv.rect(g, fx(36), fy(330), fh(130), fh(100), WOOD, ink, FINE_W, radius=fh(3))
    cv.rect(g, fx(48), fy(342), fh(106), fh(76), "#bfe3ef", ink, FINE_W * 0.6, radius=0)
    cv.rect(g, fx(48), fy(384), fh(106), fh(34), "#3e8fb0")
    cv.ellipse(g, fx(116), fy(356), fh(20), fh(20), "#ffd36b")
    _path(cv, g, f"M {fx(60)} {fy(392)} q {fh(10)} {-fh(6)} {fh(20)} 0 M {fx(96)} {fy(404)} q {fh(10)} "
          f"{-fh(6)} {fh(20)} 0", None, FINE_W * 0.5, "#e7f4f8")  # fmt: skip
    # the sconce and its light on the wall
    _glow(cv, g, "toon-restaurant-sconce", 560, 470, 70, SCONCE_LIGHT)
    _path(cv, g, f"M {fx(548)} {fy(490)} L {fx(572)} {fy(490)} L {fx(580)} {fy(462)} L {fx(540)} {fy(462)} Z",
          SCONCE, FINE_W * 0.7)  # fmt: skip
    cv.rect(g, fx(556), fy(490), fh(8), fh(18), RAIL, ink, FINE_W * 0.5)
    # the specials board, in the window's place
    cv.rect(g, fx(388), fy(488), fh(196), fh(176), SHADOW, cv.clear, 0, radius=fh(4), opacity=0.25)
    cv.rect(g, fx(380), fy(480), fh(196), fh(176), WOOD, ink, INK_W * 0.8, radius=fh(4))
    cv.rect(g, fx(390), fy(490), fh(176), fh(156), CHALK_BOARD, ink, FINE_W * 0.6, radius=fh(2))
    if lettering:
        cv.text(g, cv.uid("special-title"), "SPECIALS", fx(390), fy(494), int(fh(176)), int(fh(32)), 34,
                color=CHALK_ACCENT)  # fmt: skip
    _path(cv, g, f"M {fx(420)} {fy(528)} L {fx(536)} {fy(528)}", None, FINE_W * 0.5, CHALK)
    if lettering:
        cv.text(g, cv.uid("special-dish"), dish, fx(390), fy(534), int(fh(176)), int(fh(44)), 40, color=CHALK)
        cv.text(g, cv.uid("special-price"), price, fx(390), fy(578), int(fh(176)), int(fh(62)), 32, color=CHALK)
    # the wainscot, its rail and panels
    cv.rect(g, fx(-10), fy(640), fh(612), fh(220), WAINSCOT, ink, FINE_W, radius=0)
    for x in range(10, 592, 118):
        cv.rect(g, fx(x), fy(664), fh(96), fh(120), WAINSCOT_PANEL, ink, FINE_W * 0.4, radius=fh(3))
    cv.rect(g, fx(-10), fy(630), fh(612), fh(16), RAIL, ink, FINE_W * 0.8, radius=fh(3))
    # the banquette behind the character: the chair's outline in red leather, piped and buttoned
    _path(cv, g, CHAIR_D, LEATHER)
    _path(cv, g, f"M {fx(10)} {fy(600)} C {fx(80)} {fy(578)} {fx(220)} {fy(574)} {fx(306)} {fy(604)}", None, 9.0,
          LEATHER_LIGHT)  # fmt: skip
    for x, y in ((60, 640), (160, 628), (260, 640), (110, 700), (210, 700), (60, 760), (160, 760), (260, 760)):
        cv.ellipse(g, fx(x - 4), fy(y - 4), fh(8), fh(8), "#7e1f26")


# -- the table -------------------------------------------------------------------------------------------------------
@register(
    "prop",
    "toon-table",
    contract=tc.contract('toon-table'),
    summary="A dinner table under a white tablecloth with red stripes at the hem, in the desk's place, signed as the "
    "desk is",
)
def table(cv: Canvas, parent) -> None:
    """The desk's replacement in a dinner shot (``Staging(desk=table)``): the cloth's top where dishes stand
    (:data:`TABLE_Y`), its front falling in folds, two red stripes at the hem, and the signature on it."""
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(-10), fy(842), fh(612), fh(306), CLOTH_FRONT, cv.clear, 0, radius=0)
    for x in range(40, 592, 74):
        _path(cv, g, f"M {fx(x)} {fy(852)} Q {fx(x + 8)} {fy(960)} {fx(x - 4)} {fy(1140)}", None, 5.0, CLOTH_FOLD)
    for y in (1078, 1094):
        cv.rect(g, fx(-10), fy(y), fh(612), fh(7), CLOTH_STRIPE, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(792), fh(612), fh(52), cv.ink, cv.clear, 0, radius=0)  # the edge lines, as the desk's
    cv.rect(g, fx(-10), fy(798), fh(612), fh(40), CLOTH, cv.clear, 0, radius=0)
    signature.cactus(cv, g, fx(548), fy(832), 0.7)
    signature.code(cv, g, fx(580), fy(866), 14, color=CLOTH_CODE, opacity=0.9, align="end")


# -- the dishes ------------------------------------------------------------------------------------------------------
def _salad(cv: Canvas, g) -> None:
    _local(cv, g, "M -46 -30 Q -42 6 0 6 Q 42 6 46 -30 Z", "#f4efe6")
    for dx, dy, w, colour in ((-30, -44, 34, "#4cb57a"), (-6, -50, 36, "#3fa36b"), (16, -44, 34, "#6cc48a"),
                              (-18, -38, 30, "#2f8a57"), (10, -36, 28, "#4cb57a")):  # fmt: skip
        cv.ellipse(g, fh(dx - w / 2), fh(dy), fh(w), fh(18), colour, cv.ink, FINE_W * 0.4)
    cv.ellipse(g, fh(20), fh(-48), fh(14), fh(14), "#e8574a", cv.ink, FINE_W * 0.4)
    _local(cv, g, "M -46 -30 L 46 -30", None, FINE_W * 0.8)


def _glass(cv: Canvas, g, wine: bool) -> None:
    if wine:
        _local(cv, g, "M -21 -84 Q -22 -58 0 -56 Q 22 -58 21 -84 Z", "#7a1e2c", 0)
    _local(cv, g, "M -22 -108 Q -26 -60 0 -56 Q 26 -60 22 -108", None, FINE_W * 0.7)
    _local(cv, g, "M 0 -56 L 0 -6 M -18 -2 Q 0 -10 18 -2", None, FINE_W * 0.7)
    _local(cv, g, "M -12 -100 Q -14 -80 -8 -68", None, FINE_W * 0.5, "#ffffff")
    if not wine:
        cv.ellipse(g, fh(-4), fh(-62), fh(8), fh(5), "#7a1e2c")  # the last drop


def _water(cv: Canvas, g) -> None:
    _local(cv, g, "M -16 -62 L 16 -62 L 13 0 L -13 0 Z", "#bfe3ef", 0)
    _local(cv, g, "M -18 -90 L 18 -90 L 14 0 L -14 0 Z", None, FINE_W * 0.7)
    _local(cv, g, "M -10 -82 L -8 -12", None, FINE_W * 0.5, "#ffffff")


def _plate(cv: Canvas, g) -> None:
    cv.ellipse(g, fh(-64), fh(-14), fh(128), fh(24), "#ffffff", cv.ink, FINE_W * 0.7)
    cv.ellipse(g, fh(-44), fh(-9), fh(88), fh(13), "#ece7de")


def _lobster(cv: Canvas, g) -> None:
    _plate(cv, g)
    red = "#d9432f"
    for side in (-1, 1):
        _local(cv, g, f"M {side * 24} -24 Q {side * 44} -40 {side * 46} -58", None, FINE_W * 0.9, red)
        cv.ellipse(g, fh(side * 50 - 14), fh(-78), fh(28), fh(24), red, cv.ink, FINE_W * 0.5)
    cv.ellipse(g, fh(-38), fh(-38), fh(76), fh(30), red, cv.ink, FINE_W * 0.6)
    for dx in (-12, 2, 16):
        _local(cv, g, f"M {dx} -36 L {dx + 4} -12", None, FINE_W * 0.4)
    for dx in (-8, 8):
        cv.ellipse(g, fh(dx - 3), fh(-44), fh(6), fh(6), cv.ink)


def _carcass(cv: Canvas, g, x: float, y: float, side: int) -> None:
    """One emptied lobster lying on its side: the carapace, four tail segments narrowing away from it, the fan."""
    red, dark = "#d9432f", "#a8301f"
    cv.ellipse(g, fh(x - 22), fh(y - 12), fh(44), fh(24), red, cv.ink, FINE_W * 0.5)
    cv.ellipse(g, fh(x - 12), fh(y - 8), fh(16), fh(6), "#ef7a5f")  # the shine
    tip = x + side * 22
    for k, w in enumerate((18, 16, 13, 10)):
        cx = tip + side * (8 + 12 * k)
        cv.ellipse(g, fh(cx - 7), fh(y - w / 2), fh(14), fh(w), red, cv.ink, FINE_W * 0.4)
    fan = tip + side * 62
    for dy in (-8, 0, 8):
        cv.ellipse(g, fh(fan - 7 + side * 4), fh(y + dy - 4), fh(14), fh(8), dark, cv.ink, FINE_W * 0.3)


def _shells(cv: Canvas, g) -> None:
    _plate(cv, g)
    for x, y, side in ((-30, -14, 1), (8, -20, -1), (-12, -36, 1)):
        _carcass(cv, g, x, y, side)
    for x, y, side in ((44, -38, 1), (-50, -30, -1)):  # two claws, cracked open
        _local(cv, g, f"M {x} {y} Q {x + side * 18} {y - 16} {x + side * 30} {y - 4} L {x + side * 16} {y - 2} "
               f"Q {x + side * 24} {y + 8} {x + side * 12} {y + 10} Q {x + side * 2} {y + 8} {x} {y} Z", "#d9432f",
               FINE_W * 0.5)  # fmt: skip


def _wine(cv: Canvas, g) -> None:
    _local(cv, g, "M -16 0 L -16 -88 Q -16 -108 -6 -116 L -6 -150 L 6 -150 L 6 -116 Q 16 -108 16 -88 L 16 0 Z",
           "#2f5d3a", FINE_W * 0.8)  # fmt: skip
    cv.rect(g, fh(-14), fh(-72), fh(28), fh(30), "#f4ead2", cv.ink, FINE_W * 0.4)
    cv.rect(g, fh(-7), fh(-154), fh(14), fh(16), "#8e1b2a", cv.ink, FINE_W * 0.4)
    _local(cv, g, "M -10 -100 L -10 -20", None, FINE_W * 0.5, "#5f8f6a")


def _check(cv: Canvas, g) -> None:
    _local(cv, g, "M -30 -10 L 22 -12 L 24 -30 L -28 -28 Z", "#ffffff", FINE_W * 0.5)
    _local(cv, g, "M -54 -4 L 44 -10 L 56 2 L -42 8 Z", "#1d1d22", FINE_W * 0.6)
    _local(cv, g, "M -40 0 L 40 -5", None, FINE_W * 0.4, "#c9a227")


DISHES = {
    "salad": _salad,
    "water": _water,
    "lobster": _lobster,
    "shells": _shells,
    "wine": _wine,
    "glass": lambda cv, g: _glass(cv, g, True),
    "empty": lambda cv, g: _glass(cv, g, False),
    "check": _check,
}


def _local(cv: Canvas, g, d: str, fill: str | None, sw: float = FINE_W * 0.7, stroke: str | None = None) -> None:
    """A path given in reference units about a dish's base point, scaled to the frame."""
    out = []
    for token in d.split():
        try:
            out.append(f"{fh(float(token)):g}")
        except ValueError:
            out.append(token)
    cv.path(g, " ".join(out), fill, (cv.ink if stroke is None else stroke) if sw else cv.clear, sw)


@register(
    "prop",
    "toon-dishes",
    contract=tc.contract('toon-dishes'),
    summary="Dishes for the dinner table: a side salad, a water glass, a lobster, a plate of empty shells, a wine "
    "bottle, a full and an empty wine glass and the check in its folder; each can arrive on cue",
)
def dishes(cv: Canvas, parent, items: Sequence[tuple], id: str = "dish") -> None:
    """``items`` are ``(kind, x)`` or ``(kind, x, at)``: a :data:`DISHES` kind standing on the cloth at reference
    ``x`` (inside the frame), shown from 0 or from ``at`` seconds, drawn in order (later ones in front); each is the
    group ``{id}-{kind}`` (a second of a kind ``{id}-{kind}-2``), so shots that lay the same table take their own
    ``id``."""
    seen: dict[str, int] = {}
    for item in items:
        if not (isinstance(item, tuple | list) and len(item) in (2, 3) and item[0] in DISHES):
            raise ToonDataError(f"a dish is (kind, x[, at]) with a kind of {sorted(DISHES)}, got {item!r}")
        kind, x = item[0], item[1]
        if isinstance(x, bool) or not isinstance(x, int | float) or not 0 <= x <= REF_W:
            raise ToonDataError(f"a dish stands inside the frame, x 0 to {REF_W}, got {x!r}")
        at = item[2] if len(item) == 3 else 0.0
        if not (checks.number(at) and at >= 0):
            raise ToonDataError(f"a dish arrives at a time >= 0, got {at!r}")
        seen[kind] = seen.get(kind, 0) + 1
        name = f"{id}-{kind}" if seen[kind] == 1 else f"{id}-{kind}-{seen[kind]}"
        g = cv.group(parent, name, x=fx(x), y=fy(TABLE_Y), scaleX=DISH_SCALE, scaleY=DISH_SCALE)
        if at:
            cv.keys(g, "opacity", [(0, 0), (at, 1)])
        cv.ellipse(g, fh(-50), fh(-6), fh(100), fh(12), SHADOW, opacity=0.14)
        DISHES[kind](cv, g)


# -- the mint --------------------------------------------------------------------------------------------------------
MINT_STRIPES = ((-0.92, -0.58), (-0.2, 0.2), (0.58, 0.92))  # each stripe's edges, as shares of the sweet's half-width


@register(
    "prop",
    "toon-mint",
    contract=tc.contract('toon-mint'),
    summary="A small saucer with one striped mint in a twisted wrapper, set down on cue, or the empty wrapper",
)
def mint(
    cv: Canvas,
    parent,
    at: tuple[float, float] = (300, TABLE_Y),
    scale: float = 1.0,
    start: float = 0.0,
    eaten: bool = False,
    id: str = "mint",
) -> None:
    """The saucer stands at reference ``at``, ``scale`` times its size, shown from ``start`` seconds; ``eaten`` leaves
    only the wrapper on it. What a restaurant hands over with the bill."""
    x, y = at
    if not (checks.number(x) and checks.number(y) and checks.number(scale) and scale > 0):
        raise ToonDataError(f"a mint stands at a reference point at a scale over 0, got {at!r}, {scale!r}")
    if not (checks.number(start) and start >= 0):
        raise ToonDataError(f"a mint arrives at a time >= 0, got {start!r}")
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    if start:
        cv.keys(g, "opacity", [(0, 0), (start, 1)])
    cv.ellipse(g, fh(-74), fh(-4), fh(148), fh(18), SHADOW, opacity=0.18)
    cv.ellipse(g, fh(-68), fh(-22), fh(136), fh(34), "#fbf8f2", cv.ink, INK_W * 0.8)
    cv.ellipse(g, fh(-42), fh(-14), fh(84), fh(18), CLOTH_FOLD, cv.ink, FINE_W * 0.4)
    wrapper = "#f4f1e8" if eaten else "#ffffff"
    for side in (-1, 1):  # the wrapper's twists
        tip = 62 if not eaten else 40
        _local(cv, g, f"M {side * 22} -22 L {side * tip} -36 L {side * (tip - 4)} -8 Z", wrapper, FINE_W * 0.7)
    if eaten:
        _local(cv, g, "M -26 -8 Q -8 -30 0 -14 Q 10 -32 26 -8 Q 0 2 -26 -8 Z", wrapper, FINE_W * 0.7)
        return
    cv.ellipse(g, fh(-28), fh(-52), fh(56), fh(50), "#fff7f2", cv.ink, INK_W * 0.8)
    for left, right in MINT_STRIPES:  # each runs pole to pole round it, as a boiled sweet's do
        _local(cv, g, f"M 0 -52 Q {left * 56} -27 0 -2 Q {right * 56} -27 0 -52 Z", CLOTH_STRIPE, 0)
    cv.ellipse(g, fh(-28), fh(-52), fh(56), fh(50), cv.clear, cv.ink, INK_W * 0.8)
    cv.ellipse(g, fh(-14), fh(-44), fh(16), fh(9), "#ffffff", opacity=0.8)


# -- the card reader -------------------------------------------------------------------------------------------------
@register(
    "prop",
    "toon-card-reader",
    contract=tc.contract('toon-card-reader'),
    summary="A handheld card reader standing on the table whose screen changes on cue: TAP CARD, DECLINED, APPROVED",
)
def card_reader(
    cv: Canvas,
    parent,
    states: Sequence[tuple[float, str, str]],
    at: tuple[float, float] = (470, TABLE_Y),
    id: str = "card-reader",
) -> None:
    """The reader with its base at reference ``at``; ``states`` are ``(project second, text, tone)`` from 0 in rising
    time, the text 1 to :data:`SCREEN_MAX` characters and the tone one of :data:`TONES`; one screen shows at a
    time."""
    if not states:
        raise ToonDataError("a card reader needs at least one screen")
    for k, state in enumerate(states):
        if not (isinstance(state, tuple | list) and len(state) == 3):
            raise ToonDataError(f"a card reader screen is (second, text, tone), got {state!r}")
        t, text, tone = state
        if not checks.number(t):
            raise ToonDataError(f"a card reader screen's second is a number, got {t!r}")
        if k == 0 and t != 0:
            raise ToonDataError(f"a card reader shows a screen from 0, its first is at {t}")
        if k and not t > states[k - 1][0]:
            raise ToonDataError(f"card reader screens need rising seconds: {t} after {states[k - 1][0]}")
        if not text.strip() or len(text) > SCREEN_MAX:
            raise ToonDataError(f"a card reader screen reads 1 to {SCREEN_MAX} characters, got {text!r}")
        if tone not in TONES:
            raise ToonDataError(f"a card reader tone is one of {sorted(TONES)}, got {tone!r}")
    x, y = at
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=READER_SCALE, scaleY=READER_SCALE)
    cv.ellipse(g, fh(-56), fh(-6), fh(112), fh(12), SHADOW, opacity=0.16)
    cv.rect(g, fh(-50), fh(-176), fh(100), fh(176), "#3a3f47", cv.ink, INK_W * 0.7, radius=fh(14))
    cv.rect(g, fh(-40), fh(-188), fh(80), fh(20), "#59606b", cv.ink, FINE_W * 0.6, radius=fh(6))  # the receipt slot
    cv.rect(g, fh(-28), fh(-206), fh(56), fh(22), "#ffffff", cv.ink, FINE_W * 0.4, radius=fh(2))  # its paper
    for row in range(3):
        for col in range(3):
            cv.ellipse(g, fh(-30 + col * 22), fh(-78 + row * 22), fh(16), fh(14), "#59606b", cv.ink, FINE_W * 0.3)
    for k, (t, text, tone) in enumerate(states):
        bg, fg = TONES[tone]
        screen = cv.group(g, f"{id}-screen-{k}")
        keys = [(0.0, 1.0 if t == 0 else 0.0)] + ([(t, 1.0)] if t > 0 else [])
        if k + 1 < len(states):
            keys.append((states[k + 1][0], 0.0))
        cv.keys(screen, "opacity", keys)
        cv.rect(screen, fh(-40), fh(-162), fh(80), fh(66), bg, cv.ink, FINE_W * 0.5, radius=fh(6))
        cv.text(screen, cv.uid("reader-text"), text, fh(-40), fh(-160), int(fh(80)), int(fh(62)), 30, color=fg)

"""Collage, a phone on the largest text size there is: a page of one to three words, each word on a row of its own, as
big as the screen lets it be, so that a text can be read across a table.

An invented interface, in no real app's look: no avatar, no keyboard, no number, no address, no read mark and no name
but the words a caller gives it, which are refused if they carry a digit. Paper like the rest of the style (ADR 0026).
It holds no timing but what a caller gives it on the project clock, so a recording that re-times the beats moves its
pages too. A refusal is a :class:`BigTypeError`, raised before anything is drawn.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import checks, ink_meter
from ._collage_context_contracts import PARENT_GROUP, PROJECT_CLOCK
from ._collage_thing_contracts import ANGLE, COPY, FONT, LOCAL, PARENT, drawing
from .canvas import Canvas
from .collage import INK
from .collage_everyday import BEZEL, CARD_GLYPH, CARD_LEADING, _letter, phone
from .contracts import ParameterContract as P
from .errors import SrstudioError
from .registry import register

__all__ = ["BEZEL", "CARD_GLYPH", "CARD_LEADING", "SCREEN", "BigTypeError", "big_type"]

SCREEN = "#fffaf0"
MAX_WORDS = 3
FILL = 0.9  # of the screen's width, for the widest word: a capital's width is an estimate, and a page must not wrap
FOREVER = 86400.0  # the end of the last page: past any reel


class BigTypeError(SrstudioError, ValueError):
    """Pages a big-type phone cannot show, or a phone too small to show them."""


def _size_for(words: Sequence[str], across: float, down: float) -> float:
    """The largest whole-pixel type at which the longest of ``words`` fits ``across`` and all of them fit ``down``."""
    wide = FILL * across / (max(len(word) for word in words) * CARD_GLYPH)
    return math.floor(min(wide, down / (len(words) * CARD_LEADING)))


def _check(w: float, h: float, pages: Sequence[tuple[float, str]]) -> list[tuple[float, float, list[str], float]]:
    """Each page's span, words and type size. Refuses what it could not show whole, before anything is drawn."""
    if not all(checks.number(v) for v in (w, h)) or w <= 2 * BEZEL or h <= 2 * BEZEL:
        raise BigTypeError(f"a phone needs room for a screen inside its {BEZEL} px frame, got {w} by {h}")
    if not pages:
        raise BigTypeError("a big-type phone needs at least one page")
    times = [at for at, _ in pages]
    if not all(checks.number(t) for t in times) or times != sorted(set(times)):
        raise BigTypeError(f"pages change in rising seconds, got {times!r}")
    if times[0] != 0:
        raise BigTypeError(f"a phone shows a page from second 0, got {times[0]!r}")
    across, down = w - 2 * BEZEL, h - 2 * BEZEL
    out = []
    for (at, text), stop in zip(pages, [*times[1:], FOREVER], strict=True):
        words = text.split()
        if not 1 <= len(words) <= MAX_WORDS:
            raise BigTypeError(f"a page is 1 to {MAX_WORDS} words, got {text!r}")
        if text != text.upper():
            raise BigTypeError(f"{text!r}: the style's font has capitals only")
        if any(c.isdigit() for c in text):
            raise BigTypeError(f"{text!r}: a page has no numbers, so nothing personal can arrive on one")
        size = _size_for(words, across, down)
        if size < ink_meter.LEGIBLE_PX:
            raise BigTypeError(f"{text!r} on a {w} by {h} phone is under the legibility floor {ink_meter.LEGIBLE_PX}")
        out.append((at, stop, words, size))
    return out


@register(
    "prop",
    "collage-big-type",
    summary="A phone on the largest text size: a few words filling the screen, a page at a time, read across a table",
    contract=drawing(
        ("x", PARENT),
        ("y", PARENT),
        ("w", LOCAL),
        ("h", LOCAL),
        ("pages", P(items=P(prefix_items=(P(unit="seconds", timebase="composition", minimum=0), COPY)))),
        ("tilt", ANGLE),
        returns=PARENT_GROUP,
        constraints=(
            FONT,
            PROJECT_CLOCK,
            "x/y is the phone top-left before center rotation. Returns an untranslated wrapper containing the whole "
            "phone. pages is nonempty, starts at second 0 and rises; each page is 1 to 3 capital words with no digit, "
            "one word a row, sized to the screen from the estimated width of a capital, above the 21.6-pixel "
            "legibility floor. A page shows until the next, the last for as long as the reel runs. "
            "No messages are retrieved or sent.",
        ),
    ),
)
def big_type(
    cv: Canvas, parent, x: float, y: float, w: float, h: float, *, pages: Sequence[tuple[float, str]], tilt: float = 0.0
) -> object:
    """A phone ``w`` by ``h`` with its top-left at ``x, y``, turned ``tilt`` degrees about its centre, its screen filled
    by each of ``pages`` (``(from, words)``, project seconds, the first from 0). Returns the group."""
    laid = _check(w, h, pages)
    across, down = w - 2 * BEZEL, h - 2 * BEZEL
    g = cv.group(parent, cv.uid("g"))
    screen = phone(cv, g, x, y, w, h, screen=SCREEN, tilt=tilt)
    for at, stop, words, size in laid:
        page = cv.group(screen, cv.uid("g"))
        cv.gate(page, [(at, stop)])
        row = size * CARD_LEADING
        top = (down - row * len(words)) / 2
        for i, word in enumerate(words):
            _letter(cv, page, "big-type", word, 0, top + i * row, across, row, size, color=INK)
    return g

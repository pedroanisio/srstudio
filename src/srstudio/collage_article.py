"""A phone open on an invented article, for a Collage insert: one big headline, a picture box with no face in it and
grey bars for the text.

It copies no real site, app or paper: the page has no masthead, byline, date or address to fill in, and the only words
on it are the ones a caller passes. A headline is measured against the page and refused when it would be clipped or
fall under the engine's legibility floor, since the insert exists to be read on a phone. Paper like the rest of the
style (ADR 0026); it holds no timing, and returns its group for the caller to key.
"""

from __future__ import annotations

from . import checks, collage_everyday, ink_meter
from .canvas import Canvas
from .collage import INK, _cut, _paper, draw_shapes
from .collage_everyday import BEZEL, CARD_GLYPH, CARD_LEADING, phone
from .errors import SrstudioError
from .registry import register

__all__ = ["ArticleError", "article"]

PAGE = "#fffaf0"
PAD = 30.0  # the page's margin round what is on it
STRIP = 84.0  # the sender's strip across the top of the page
SENDER_SIZE = 44.0
PICTURE = 0.3  # of the page's height, the picture box
BARS = 4  # lines of grey text under the headline
BAR_H, BAR_GAP = 18.0, 20.0
SKY, HILL, GREY = "#b9c4d0", "#8d99ae", "#c9c4b8"


class ArticleError(SrstudioError, ValueError):
    """An article asked for at a size it cannot draw, or with a headline it could not show whole."""


def _rows(headline: str, per_line: int) -> list[str]:
    rows: list[str] = []
    for word in headline.split():
        if rows and len(rows[-1]) + 1 + len(word) <= per_line:
            rows[-1] += " " + word
        else:
            rows.append(word)
    return rows


def _check(headline: str, w: float, room: float, size: float) -> None:
    if not headline.strip():
        raise ArticleError("an article needs a headline")
    if headline != headline.upper():
        raise ArticleError(f"{headline!r}: the style's font has capitals only")
    if not (checks.number(size) and size >= ink_meter.LEGIBLE_PX):
        raise ArticleError(f"a headline at {size!r} px is under the legibility floor of {ink_meter.LEGIBLE_PX}")
    per_line = int(w / (size * CARD_GLYPH))
    rows = _rows(headline, per_line)
    if max(len(row) for row in rows) > per_line or len(rows) * size * CARD_LEADING > room:
        raise ArticleError(f"{headline!r} does not fit a page {w} wide at {size} px")


@register("prop", "collage-article", summary="A phone open on an invented article: a headline, no masthead, no faces")
def article(
    cv: Canvas, parent, x: float, y: float, w: float, h: float, headline: str, *, size: float = 66.0, sender: str = ""
) -> object:
    """A phone ``w`` by ``h`` with its top-left at ``x, y``, open on ``headline`` at ``size``, with ``sender`` in a
    strip above it when given; returns the group."""
    if not (checks.number(w) and w > 2 * (BEZEL + PAD) and checks.number(h) and h > 2 * (BEZEL + PAD)):
        raise ArticleError(f"a page of {w!r} by {h!r} has no room for anything")
    page_w, page_h = w - 2 * BEZEL, h - 2 * BEZEL
    top = STRIP if sender else 0.0
    picture = page_h * PICTURE
    room = page_h - top - picture - 2 * PAD - BARS * (BAR_H + BAR_GAP)
    wide = page_w - 2 * PAD
    _check(headline, wide, room, size)
    g = cv.group(parent, cv.uid("g"))
    page = phone(cv, g, x, y, w, h, screen=PAGE)
    if sender:
        cv.rect(page, 0, 0, page_w, STRIP, HILL, radius=14)
        collage_everyday._letter(cv, page, "article", sender, PAD, 0, wide, STRIP, SENDER_SIZE, color=INK)
    tall = len(_rows(headline, int(wide / (size * CARD_GLYPH)))) * size * CARD_LEADING
    collage_everyday._letter(cv, page, "article", headline, PAD, top + PAD / 2, wide, tall, size, color=INK)
    picture_y = top + PAD / 2 + tall + PAD / 2
    box = [(PAD, picture_y), (PAD + wide, picture_y), (PAD + wide, picture_y + picture), (PAD, picture_y + picture)]
    draw_shapes(cv, page, _paper(_cut(f"article-{w}-{h}", box, 2), SKY, shadow=False))
    hill = [
        (PAD, picture_y + picture),
        (PAD + wide * 0.4, picture_y + picture * 0.45),
        (PAD + wide, picture_y + picture),
    ]
    draw_shapes(cv, page, _paper(hill, HILL, shadow=False))
    bars = picture_y + picture + PAD / 2
    for i in range(BARS):
        cv.rect(page, PAD, bars + i * (BAR_H + BAR_GAP), wide * (0.72 if i == BARS - 1 else 1.0), BAR_H, GREY, radius=6)
    return g

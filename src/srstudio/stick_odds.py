"""The Stick style's odds and ends: things one reel needed and the next will want.

:func:`poster` is a wall poster with a line of lettering, big enough to cover what is on the wall behind it;
:func:`headset` goes on a standing figure's head. Everything is in frame pixels of the 1080 × 1920 Stick frame and
nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

from .canvas import Canvas
from .registry import register
from .stick import HEAD_R, StickDataError, _group, box, oval, shape

__all__ = ["headset", "poster"]

PAPER, LETTER = "#f4f1ea", "#a8361c"
HEADSET, PAD = "#1f2430", "#3b4252"


@register("prop", "stick-poster", tags=("wall", "poster", "sign", "font"))
def poster(cv: Canvas, parent, x: float, y: float, w: float, h: float, text: str, *, size: float = 92):
    """A paper poster at ``x, y`` of ``w`` by ``h`` with ``text`` in the caption font, balanced over up to 4 lines."""
    cv.require_font("the poster is lettered in it")
    if not text.strip():
        raise StickDataError("a poster needs lettering")
    if w <= 0 or h <= 0:
        raise StickDataError(f"a poster has a size, got {w} by {h}")
    g = _group(cv, parent)
    box(cv, g, x, y, w, h, PAPER, 5, r=8)
    pad = 30
    name = cv.uid("text")
    cv.assets.add_text(id=name, text=text, width=w - 2 * pad, height=h - 2 * pad, size=size, fontAsset=cv.font_asset,
                       weight=700, color=LETTER, align="center", verticalAlign="middle", wrap="balance",
                       lineHeight="1.08", maxLines=4)  # fmt: skip
    g.add_layer(id=cv.uid("layer"), asset=name, x=x + pad, y=y + pad)
    return g


@register("prop", "stick-headset", tags=("headset", "front-desk", "phone", "work"))
def headset(cv: Canvas, parent, x: float, y: float, *, flip: bool = False, scale: float = 1.0):
    """A headset on the head centred at ``x, y``: the band, the ear pad and the mic at the mouth, on the side the
    figure faces (``flip``: left). Draw it after the figure."""
    if scale <= 0:
        raise StickDataError(f"a headset's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=-scale if flip else scale, scaleY=scale)
    r = HEAD_R + 6
    shape(cv, g, f"M {-r} -6 A {r} {r} 0 0 1 {r} -6", sw=11, stroke=HEADSET)
    oval(cv, g, -r - 16, -36, 34, 74, PAD)
    shape(cv, g, f"M {-r} 34 Q -74 78 22 62", sw=7, stroke=HEADSET)
    oval(cv, g, 14, 52, 24, 20, HEADSET)
    return g

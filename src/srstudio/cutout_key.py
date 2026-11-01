"""The one short line a Cutout reel opens on: the premise on a dark bar, read with the sound off.

It sits on the frame, above the camera, so a move never carries it, and it is measured in the reel's own font, so the
bar is as wide as its words. The bar never reaches the show's bug (:data:`srstudio.show.BUG_BOX`), and it comes off
before the line it would repeat: :class:`CutoutKeyError` refuses what cannot be drawn.
"""

from __future__ import annotations

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .fonts import text_width
from .show import BUG_BOX

__all__ = ["BG", "CutoutKeyError", "HEIGHT", "INK", "MAX_CHARS", "PAD", "SIZE", "TOP", "key_line"]

TOP = 350  # under the top 14 % Meta keeps clear and under the bug, above the faces of the usual two-shot
HEIGHT = 92
SIZE = 54
PAD = 64  # the bar past its words, both sides together
MAX_CHARS = 24
MARGIN = 60
BG, INK = "#1E2C3C", "#FFFFFF"


class CutoutKeyError(SrstudioError, ValueError):
    """A key line that does not fit its bar, or a span it cannot show in."""


def key_line(
    cv: Canvas, parent, text: str, start: float, end: float, *, font: bytes, top: float = TOP, id: str = "key-line"
):
    """``text`` on a dark bar centred on the frame from ``start`` to ``end``, with ``font`` the reel's caption face.
    Returns the group, for :meth:`srstudio.episode.Episode.hide_on_cover`."""
    if not text.strip() or len(text) > MAX_CHARS:
        raise CutoutKeyError(f"a key line is 1 to {MAX_CHARS} characters, got {text!r}")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise CutoutKeyError(f"a key line needs 0 <= start < end, got {start}..{end}")
    width = round(text_width(font, text, SIZE) + PAD, 2)
    if width > cv.width - 2 * MARGIN:
        raise CutoutKeyError(f"the key line {text!r} is {width} px wide, over the frame's margins")
    x = round(cv.width / 2 - width / 2, 2)
    if x + width > BUG_BOX[0] and top < BUG_BOX[3] and top + HEIGHT > BUG_BOX[1]:
        raise CutoutKeyError(f"the key line {text!r} reaches the show's bug")
    g = cv.group(parent, id, start=start, end=end)
    cv.rect(g, x, top, width, HEIGHT, BG, cv.clear, 0, radius=round(HEIGHT / 3, 2))
    cv.text(g, f"{id}-text", text, x, top, int(width), HEIGHT, SIZE, color=INK, wrap="none")
    return g

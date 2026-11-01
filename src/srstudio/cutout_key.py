"""The one short line a Cutout reel opens on: the premise on a dark bar, read with the sound off.

It sits on the frame, above the camera, so a move never carries it, and it is measured in the reel's own font, so the
bar is as wide as its words. The bar never reaches the show's bug (:data:`srstudio.show.BUG_BOX`), and it comes off
before the line it would repeat: :class:`CutoutKeyError` refuses what cannot be drawn.

:func:`camera` cuts one set between framings, and refuses a framing that would show where the set stops being painted.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .fonts import text_width
from .show import BUG_BOX

__all__ = ["BG", "CUT", "CutoutKeyError", "HEIGHT", "INK", "MAX_CHARS", "PAD", "SIZE", "TOP", "camera", "key_line"]

TOP = 350  # under the top 14 % Meta keeps clear and under the bug, above the faces of the usual two-shot
HEIGHT = 92
SIZE = 54
PAD = 64  # the bar past its words, both sides together
MAX_CHARS = 24
MARGIN = 60
CUT = 1 / 120  # how far before its time a hard cut's outgoing frame ends
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


def camera(
    cv: Canvas,
    group,
    moves: Sequence[tuple[float, tuple[float, float, float]]],
    *,
    box: tuple[float, float, float, float] | None = None,
) -> None:
    """Key ``group``, a whole set, on ``moves``: (time, (scale, x, y)). The camera moves between two frames at different
    times; two frames at one time are a hard cut. ``box`` (left, top, right, bottom) is how far the set is painted, in
    its own units, by default the frame. Every framing stays inside it, so no cut or push ever shows a set's edge."""
    if not moves:
        raise CutoutKeyError("a camera needs at least one frame")
    left, top, right, bottom = box if box is not None else (0.0, 0.0, float(cv.width), float(cv.height))
    last = None
    for at, (scale, x, y) in moves:
        if not (checks.number(at) and at >= 0 and (last is None or at >= last)):
            raise CutoutKeyError(f"frames run in time order from zero or later, got {at!r} after {last!r}")
        last = at
        if not (checks.number(scale) and scale > 0 and checks.number(x) and checks.number(y)):
            raise CutoutKeyError(f"a frame is a positive scale and a position, got {(scale, x, y)!r}")
        seen = (-x / scale, -y / scale, (cv.width - x) / scale, (cv.height - y) / scale)
        if seen[0] < left or seen[1] < top or seen[2] > right or seen[3] > bottom:
            raise CutoutKeyError(f"the frame at {at} sees {seen!r}, past the set's edge {(left, top, right, bottom)!r}")
    if len(moves) > 1 and moves[0][0] == moves[1][0] == 0:
        raise CutoutKeyError("a cut at the first instant has nothing to cut from")
    timed = [(at - CUT if i + 1 < len(moves) and moves[i + 1][0] == at else at, f) for i, (at, f) in enumerate(moves)]
    for i, prop in enumerate(("scaleX", "x", "y")):
        cv.keys(group, prop, [(at, frame[i]) for at, frame in timed], hold=False)
    cv.keys(group, "scaleY", [(at, frame[0]) for at, frame in timed], hold=False)

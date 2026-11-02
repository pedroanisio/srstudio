"""The fixed corner of an Okayville reel: the show bug, drawn on the frame from the first to the last (ADR 0074).

The bug is the approved OK-eye mark and the reel's number on a small chip in the right gutter, outside the safe area, so
no text the safe-area check holds can reach it. A build of a numbered release (:func:`stamping`, set by
``srstudio build``) draws it as the last child of the composition, above the camera: a camera move, a shake or a crash
zoom moves the picture under it and leaves it where it is. It is a drawing, with the K as an outline, so it needs no
font and looks the same on every style. It adds no seconds and hides on the cover, which says the number on its own
band.

What refuses a reel that lost it is :mod:`srstudio.show_gate`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from ._remaining_part_contracts import contract
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .signature import ADVANCE, GLYPHS
from .thumbnail import INK

__all__ = ["BUG_BOX", "BUG_ID", "ShowError", "active", "bug", "bug_id", "stamping"]

BUG_ID = "show-bug"
BUG_BOX = (
    926.0,
    270.0,
    1044.0,
    332.0,
)  # the right gutter, under the top 14 % Meta keeps clear, over a caption at y 334
HASH = "M3.5 0 L1.5 16 M8.5 0 L6.5 16 M0 5.5 L10 5.5 M0 10.5 L10 10.5"  # a glyph of the signature's set, for this mark
_CHIP = INK.ink
_RADIUS, _PAD = 12.0, 8.0
_STROKE = 2.5  # of the glyph box
_MARK_TOP, _MARK_HEIGHT = 4.0, 28.0  # below the chip's top; the mark's height
_DIGIT_TOP, _DIGIT_HEIGHT = 35.0, 21.0  # below the chip's top; the height of a digit
# The approved OK-eye, in the avatar's own pixels: its tall yellow O, the white eye with pupil and highlight under a
# flat lid, and Anton's K as an outline, so the chip still needs no font.
# The eye and the pupil stop at the lid (y 420) instead of going under it, which at this size would leave a white halo,
# and the K stands 20 px further off than on the avatar, so the two letters stay apart at a 28 px height.
_YELLOW, _WHITE, _PUPIL = "#FFD23F", "#FFFFFF", "#111111"
_O_RING = (219.0, 202.0, 300.0, 472.0)  # x, y, width, height
_O_EYE = "M 283.5 420 A 86 172 0 1 0 454.5 420 Z"
_O_PUPIL = "M 365.3 420 A 52 52 0 1 0 420.7 420 Z"
_O_SHINE = (363.0, 440.0, 28.0, 28.0)
_K = (
    "M 576.0 675.0 L 576.0 193.8 L 671.2 193.8 L 671.2 386.5 L 716.0 193.8 L 812.8 193.8 L 758.9 414.1 "
    "L 824.0 675.0 L 724.2 675.0 L 671.7 442.0 L 671.7 675.0 Z"
)
_MARK_BOX = (219.0, 193.8, 824.0, 675.0)  # left, top, right, bottom of the O and the K
_active: ContextVar[int | None] = ContextVar("show_number", default=None)


class ShowError(SrstudioError, ValueError):
    """A show number that is not a whole number from 1."""


def bug_id(number: int) -> str:
    """The id of the bug of reel ``number``. The gate reads the number here, so a scene built for another reel fails."""
    return f"{BUG_ID}-{number}"


def active() -> int | None:
    """The number of the reel this build draws, or None for a build of anything else."""
    return _active.get()


@contextmanager
def stamping(number: int | None) -> Iterator[None]:
    """Inside the block, every episode that finishes carries the bug of reel ``number``; None changes nothing."""
    token = _active.set(number)
    try:
        yield
    finally:
        _active.reset(token)


def _mark(cv: Canvas, parent, id: str, centre: float, top: float) -> None:
    """The OK-eye, :data:`_MARK_HEIGHT` tall, centred on ``centre`` with its top at ``top``."""
    left, high, right, low = _MARK_BOX
    scale = _MARK_HEIGHT / (low - high)
    g = cv.group(parent, id, x=centre - (right - left) * scale / 2 - left * scale, y=top - high * scale,
                 scaleX=scale, scaleY=scale)  # fmt: skip
    cv.ellipse(g, *_O_RING, _YELLOW)
    cv.path(g, _O_EYE, fill=_WHITE, stroke=cv.clear, sw=0)
    cv.path(g, _O_PUPIL, fill=_PUPIL, stroke=cv.clear, sw=0)
    cv.ellipse(g, *_O_SHINE, _WHITE)
    cv.path(g, _K, fill=_YELLOW, stroke=cv.clear, sw=0)


def _glyphs(cv: Canvas, parent, id: str, text: str, x: float, y: float, scale: float, colour: str) -> None:
    for i, ch in enumerate(text):
        g = cv.group(parent, f"{id}-{i}", x=x + i * ADVANCE * scale, y=y, scaleX=scale, scaleY=scale)
        cv.path(g, HASH if ch == "#" else GLYPHS[ch], stroke=colour, sw=_STROKE)


@register(
    "graphic",
    BUG_ID,
    summary="The show's fixed corner: the OK-eye mark and the reel's number",
    style="",
    contract=contract('show-bug'),
)
def bug(cv: Canvas, parent, number: int):
    """The bug of reel ``number`` on ``parent``, every point of it inside :data:`BUG_BOX`; returns its group."""
    if type(number) is not int or number < 1:
        raise ShowError(f"a show number is a whole number from 1, got {number!r}")
    left, top, right, bottom = BUG_BOX
    width = right - left
    g = cv.group(parent, bug_id(number))
    cv.rect(g, left, top, width, bottom - top, _CHIP, radius=_RADIUS)
    _mark(cv, g, f"{bug_id(number)}-mark", left + width / 2, top + _MARK_TOP)
    label = f"#{number}"
    scale = min(_DIGIT_HEIGHT / 16, (width - 2 * _PAD) / ((len(label) - 1) * ADVANCE + 10))
    wide = ((len(label) - 1) * ADVANCE + 10) * scale
    y = top + _DIGIT_TOP + (_DIGIT_HEIGHT - 16 * scale) / 2
    _glyphs(cv, g, f"{bug_id(number)}-n", label, left + (width - wide) / 2, y, scale, INK.white)
    return g

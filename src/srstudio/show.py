"""The fixed corner of an Okayville reel: the show bug, drawn on the frame from the first to the last (ADR 0074).

The bug is the OK-eye mark and the reel's number on a small chip in the right gutter, outside the safe area, so no text
the safe-area check holds can reach it. A build of a numbered release (:func:`stamping`, set by ``srstudio build``)
draws it as the last child of the composition, above the camera: a camera move, a shake or a crash zoom moves the
picture under it and leaves it where it is. It is a stroked drawing, like the signature code, so it needs no font and
looks the same on every style. It adds no seconds and hides on the cover, which says the number on its own band.

What refuses a reel that lost it is :mod:`srstudio.show_gate`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .signature import ADVANCE, GLYPHS
from .thumbnail import INK, Thumbnail

__all__ = ["BUG_BOX", "BUG_ID", "ShowError", "active", "bug", "bug_id", "stamping"]

BUG_ID = "show-bug"
BUG_BOX = (926.0, 232.0, 1044.0, 298.0)  # the right gutter, level with News's bug and over a hook card's top edge
HASH = "M3.5 0 L1.5 16 M8.5 0 L6.5 16 M0 5.5 L10 5.5 M0 10.5 L10 10.5"  # a glyph of the signature's set, for this mark
_CHIP = INK.ink
_MARK = Thumbnail.accent
_RADIUS, _PAD = 12.0, 8.0
_EYE = 11.5  # the eye's radius: it is the O of OK, under a lid drawn flat, because everything here is okay
_RING = 3.5
_LID = 3.5  # px above the eye's centre where the lid stops
_PUPIL = 4.5
_K_SCALE, _K_GAP = 1.5, 9.0
_STROKE = 2.5  # of the glyph box
_MARK_TOP = 7.0  # below the chip's top
_DIGIT_TOP, _DIGIT_HEIGHT = 37.0, 23.0  # below the chip's top; the height of a digit
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


def _eye(cv: Canvas, parent, cx: float, cy: float) -> None:
    """The OK-eye's O: a ring, a flat lid across its top and the pupil looking out from under it."""
    r = _EYE
    cv.ellipse(parent, cx - r, cy - r, 2 * r, 2 * r, cv.clear, stroke=_MARK, sw=_RING)
    half = (r**2 - _LID**2) ** 0.5
    lid = f"M{cx - half:g} {cy - _LID:g} A{r:g} {r:g} 0 0 1 {cx + half:g} {cy - _LID:g} Z"
    cv.path(parent, lid, fill=_MARK, stroke=_MARK, sw=1.5)
    cv.ellipse(parent, cx - _PUPIL, cy + 2.0 - _PUPIL, 2 * _PUPIL, 2 * _PUPIL, _MARK)


def _glyphs(cv: Canvas, parent, id: str, text: str, x: float, y: float, scale: float, colour: str) -> None:
    for i, ch in enumerate(text):
        g = cv.group(parent, f"{id}-{i}", x=x + i * ADVANCE * scale, y=y, scaleX=scale, scaleY=scale)
        cv.path(g, HASH if ch == "#" else GLYPHS[ch], stroke=colour, sw=_STROKE)


@register("graphic", BUG_ID, summary="The show's fixed corner: the OK-eye mark and the reel's number", style="")
def bug(cv: Canvas, parent, number: int):
    """The bug of reel ``number`` on ``parent``, every point of it inside :data:`BUG_BOX`; returns its group."""
    if type(number) is not int or number < 1:
        raise ShowError(f"a show number is a whole number from 1, got {number!r}")
    left, top, right, bottom = BUG_BOX
    width = right - left
    g = cv.group(parent, bug_id(number))
    cv.rect(g, left, top, width, bottom - top, _CHIP, radius=_RADIUS)
    k_wide = 10 * _K_SCALE
    mark = 2 * _EYE + _K_GAP + k_wide
    x = left + (width - mark) / 2
    cy = top + _MARK_TOP + _EYE
    _eye(cv, g, x + _EYE, cy)
    _glyphs(cv, g, f"{bug_id(number)}-k", "K", x + 2 * _EYE + _K_GAP, cy - 8 * _K_SCALE, _K_SCALE, _MARK)
    label = f"#{number}"
    scale = min(_DIGIT_HEIGHT / 16, (width - 2 * _PAD) / ((len(label) - 1) * ADVANCE + 10))
    wide = ((len(label) - 1) * ADVANCE + 10) * scale
    y = top + _DIGIT_TOP + (_DIGIT_HEIGHT - 16 * scale) / 2
    _glyphs(cv, g, f"{bug_id(number)}-n", label, left + (width - wide) / 2, y, scale, INK.white)
    return g

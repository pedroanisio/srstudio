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

import math
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from . import fonts
from ._remaining_part_contracts import contract
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .signature import ADVANCE, GLYPHS
from .thumbnail import INK

if TYPE_CHECKING:
    from .layout import SafeArea
    from .social import InstagramPost

__all__ = [
    "NewReelPolicy",
    "NewReelPolicyError",
    "TITLE_ID",
    "TITLE_HOLD",
    "title_card",
    "BUG_BOX",
    "BUG_ID",
    "CLEAR",
    "ShowError",
    "active",
    "bug",
    "bug_id",
    "clear_of_bug",
    "stamping",
    "widest_clear",
]

BUG_ID = "show-bug"
BUG_BOX = (
    926.0,
    270.0,
    1044.0,
    332.0,
)  # the right gutter, under the top 14 % Meta keeps clear, over a caption at y 334
CLEAR = 12.0  # frame pixels a caption or a text pill keeps between itself and the bug's box, on one side at least
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


def clear_of_bug(box: tuple[float, float, float, float]) -> bool:
    """Whether ``box`` (left, top, right, bottom, frame pixels) keeps :data:`CLEAR` pixels off :data:`BUG_BOX` on at
    least one side: a pill that meets the bug's corner diagonally is as crowded as one under its edge."""
    left, top, right, bottom = box
    bug_left, bug_top, bug_right, bug_bottom = BUG_BOX
    return (
        right <= bug_left - CLEAR or left >= bug_right + CLEAR or bottom <= bug_top - CLEAR or top >= bug_bottom + CLEAR
    )


def widest_clear(top: float, bottom: float, centre: float) -> float:
    """The widest box centred on ``centre`` from ``top`` to ``bottom`` that is :func:`clear_of_bug`: infinite when
    those rows already clear it, else what keeps its right edge :data:`CLEAR` left of the bug."""
    if bottom <= BUG_BOX[1] - CLEAR or top >= BUG_BOX[3] + CLEAR:
        return math.inf
    return 2 * (BUG_BOX[0] - CLEAR - centre)


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


TITLE_ID = "new-reel-title"
TITLE_HOLD = 2.5  # seconds the opening title stays before the picture is clear (ADR 0253)


class NewReelPolicyError(ShowError):
    """A new reel cannot satisfy its explicit authoring policy (ADR 0253)."""


@dataclass(frozen=True)
class NewReelPolicy:
    """Opt-in contract for a new Okayville reel, never inferred from a published reel's cover.

    Series use ``situation_title`` (also set on EpisodeSpec); one-offs use the caption's first line.
    Voice names identify the synthetic voices actually used by the author.
    """

    voices: tuple[str, ...]
    situation_title: str | None = None

    def __post_init__(self) -> None:
        from .social import disclosure

        disclosure(self.voices)
        object.__setattr__(self, "voices", tuple(self.voices))
        if self.situation_title is not None:
            _title_line(self.situation_title)

    def expected_title(self, post: InstagramPost) -> str:
        from .thumbnail import ShowCover

        cover = post.thumbnail
        if isinstance(cover, ShowCover) and cover.series:
            if self.situation_title is None:
                raise NewReelPolicyError("a series needs a one-line situation title")
            return self.situation_title
        return _title_line(post.text().splitlines()[0])


def _title_line(line: str) -> str:
    if not isinstance(line, str) or not line.strip() or line != line.strip() or "\n" in line or "\r" in line:
        raise NewReelPolicyError("a situation title must be a nonempty single line without edge whitespace")
    return line


def title_card(
    cv: Canvas, parent, line: str, *, font: Path, safe_area: SafeArea, min_size: float, hold: float = TITLE_HOLD
):
    """Draw an opaque opening title at the safe area's top for ``hold`` seconds; refuse lines under the floor.

    Call on the composition after drawing the scene, so frame zero carries the title above the camera.
    """
    line = _title_line(line)
    if not math.isfinite(min_size) or min_size <= 0:
        raise NewReelPolicyError("title legibility floor must be finite and positive")
    area = safe_area.region(cv.width, cv.height)
    pad = 16.0
    room = math.floor(area.x1 - area.x0 - 2 * pad)
    data = Path(font).read_bytes()
    width_at_one = fonts.text_width(data, line, 1)
    size = min(64.0, room / max(width_at_one, 1))
    height = size * 1.5 + 2 * pad
    if size < min_size or height > area.y1 - area.y0:
        raise NewReelPolicyError("title does not fit the safe area at the legibility floor; shorten it")
    group = cv.group(parent, TITLE_ID + "-panel")
    cv.rect(group, area.x0, area.y0, area.x1 - area.x0, height, "#111111", radius=12)
    cv.text(group, TITLE_ID, line, area.x0 + pad, area.y0 + pad, room, math.ceil(size * 1.5), size, "#FFFFFF")
    if not math.isfinite(hold) or hold <= 0:
        raise NewReelPolicyError("the title hold must be finite and positive")
    cv.gate(group, [(0.0, hold)])  # an opening line, not a band over the whole reel
    return group

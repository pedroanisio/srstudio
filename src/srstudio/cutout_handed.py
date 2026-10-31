"""Cutout, what changes hands: a CV folder across a desk.

Each prop is drawn at ``x``, ``y`` in its parent's pixels and keyed on the episode's clock. Light comes from the top
left, as in every Cutout set, so each contact shadow falls down and to the right. Every refusal is a
:class:`CutoutHandedError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks, look
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = ["CutoutHandedError", "cv_folder"]

MANILA = "#E2C07A"
MANILA_DARK = "#C49F58"
PAGE = "#FBFAF2"
SHADOW = "#2A2018CC"


class CutoutHandedError(SrstudioError, ValueError):
    """A prop asked for with arguments it cannot be drawn from."""


def _check_scale(scale) -> None:
    checks.positive(scale, CutoutHandedError, f"scale must be a positive number, got {scale!r}")


def _check_spans(spans, name: str) -> None:
    checks.spans(
        spans, CutoutHandedError, lambda s: f"{name} are rising spans, got {s!r}", ordered=f"{name} run in order"
    )


@register("prop", "cv-folder", style="cutout", summary="A manila CV folder on a desk: shut, or open on a page, on cue")
def cv_folder(
    cv: Canvas,
    parent,
    x=540,
    y=1200,
    *,
    open_spans: Sequence[tuple[float, float]] = (),
    label: str = "CV",
    scale: float = 1.0,
    id: str = "cv-folder",
):
    """The folder's centre is (``x``, ``y``), 460 wide shut and 760 open. ``open_spans`` are when it lies open, in
    rising order; it is shut the rest of the time. ``label`` (1 to 8 characters) is on its cover."""
    cv.require_font("a folder's label is set in it", CutoutHandedError)
    _check_scale(scale)
    _check_spans(open_spans, "open spans")
    if not isinstance(label, str) or not 0 < len(label.strip()) <= 8:
        raise CutoutHandedError(f"a folder's label has 1 to 8 characters, got {label!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=-1.5)
    shut = cv.group(g, f"{id}-shut")
    look.pool(cv, shut, f"{id}-shut-contact", SHADOW, -226, 112, 480, 66, opacity=0.5)
    cv.path(shut, "M-230 -130 L-230 -168 Q-228 -176 -216 -176 L-70 -176 Q-58 -176 -54 -160 L-46 -130Z",
            MANILA_DARK, ink, 4)  # fmt: skip
    cv.rect(shut, -230, -134, 460, 280, MANILA, ink, 4, radius=8)
    cv.rect(shut, -210, -116, 170, 8, "#F4E3B4", radius=4, opacity=0.8)
    cv.rect(shut, -110, -56, 220, 110, PAGE, ink, 3, radius=6)
    cv.text(shut, f"{id}-label", label, -110, -56, 220, 110, 64, ink)
    wide = cv.group(g, f"{id}-open")
    cv.gate(wide, list(open_spans))
    look.pool(cv, wide, f"{id}-open-contact", SHADOW, -376, 112, 780, 66, opacity=0.5)
    cv.rect(wide, -380, -146, 380, 292, MANILA, ink, 4, radius=8)
    cv.rect(wide, 0, -146, 380, 292, MANILA, ink, 4, radius=8)
    cv.rect(wide, 24, -130, 330, 262, PAGE, ink, 3)
    cv.rect(wide, 48, -110, 76, 90, "#B9C9D2", ink, 3)
    cv.rect(wide, 142, -106, 180, 16, ink)
    for k in range(3):
        cv.line(wide, 142, -72 + k * 24, 330, -72 + k * 24, "#8C8C8C", 7)
    for k in range(4):
        cv.line(wide, 48, 8 + k * 30, 330 if k % 3 != 2 else 230, 8 + k * 30, "#8C8C8C", 7)
    cv.gate(shut, _gaps(open_spans))
    return g


def _gaps(spans: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """The time outside ``spans``, from 0, for a state shown when the other is not."""
    out, last = [], 0.0
    for a, b in spans:
        if a > last:
            out.append((last, a))
        last = b
    out.append((last, 3600.0))
    return out

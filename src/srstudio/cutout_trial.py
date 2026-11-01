"""What a trial shift hands out: a spare apron held by its neck loop, and a small tag that says what you are.

The apron is the café's own green and carries no name; the tag is a blank plastic pin with one short word. Neither
copies a real uniform. Both take ``x``, ``y`` and ``scale``, in the units of whatever holds them. Every refusal is a
:class:`CutoutTrialError`.
"""

from __future__ import annotations

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = ["CutoutTrialError", "GREEN", "TAG", "apron_spare", "trial_tag"]

GREEN = "#366761"  # the café's aprons
GREEN_DARK = "#2C5853"
TAG = (112, 46)  # a tag's width and height, about its centre
TAG_FACE = "#F3E3BE"
TAG_INK = "#233A37"
MAX_LABEL = 6


class CutoutTrialError(SrstudioError, ValueError):
    """An apron or a tag that cannot be drawn as asked."""


def _place(what: str, x: float, y: float, scale: float) -> None:
    if not (checks.number(x) and checks.number(y)):
        raise CutoutTrialError(f"{what}'s place must be numbers, got {x!r}, {y!r}")
    if not (checks.number(scale) and scale > 0):
        raise CutoutTrialError(f"{what}'s scale must be a positive number, got {scale!r}")


@register("prop", "apron-spare", style="cutout", summary="A spare green apron, held up by its neck loop, ties hanging")
def apron_spare(cv: Canvas, parent, x: float = 540, y: float = 800, *, scale: float = 1.0, id: str = "apron-spare"):
    """The neck loop's top is (``x``, ``y``) and the apron hangs 330 below it, as from a hook or a hand."""
    _place("an apron", x, y, scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M-26 74 Q-30 12 0 0 Q30 12 26 74", stroke=GREEN_DARK, sw=9)
    cv.path(g, "M-44 70 L44 70 L50 150 Q78 154 92 170 L82 330 L-82 330 L-92 170 Q-78 154 -50 150Z", GREEN, ink, 4)
    cv.rect(g, -46, 214, 92, 58, GREEN_DARK, ink, 2.5, radius=8)
    cv.path(g, "M-92 172 Q-122 214 -110 262 M92 172 Q122 214 110 262", stroke=GREEN_DARK, sw=7)
    return g


@register("prop", "trial-tag", style="cutout", summary="A small pinned tag with one short word: TRIAL")
def trial_tag(
    cv: Canvas,
    parent,
    x: float = 540,
    y: float = 800,
    *,
    scale: float = 1.0,
    label: str = "TRIAL",
    id: str = "trial-tag",
):
    """The tag's centre is (``x``, ``y``). ``label`` is 1 to :data:`MAX_LABEL` characters."""
    cv.require_font("a tag's label is set in it", CutoutTrialError)
    _place("a tag", x, y, scale)
    if not isinstance(label, str) or not 0 < len(label.strip()) <= MAX_LABEL:
        raise CutoutTrialError(f"a tag's label has 1 to {MAX_LABEL} characters, got {label!r}")
    w, h = TAG
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=-2)
    cv.rect(g, -w / 2, -h / 2, w, h, TAG_FACE, cv.ink, 3, radius=6)
    cv.text(g, f"{id}-label", label, -w / 2, -h / 2, w, h, 30, TAG_INK)
    return g

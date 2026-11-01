"""Cutout, what a town does with your news: a takeaway cup lettered for you, a page in crayon, a cake knife and a slice.

The cup's lettering is given by the reel and read in an insert, so it sits large on a plain sleeve with no brand. The
crayon page letters nothing, so it reads at any size. Every refusal is a :class:`CutoutLeakError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import _cutout_contracts, checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = ["CUP_LINE", "CUP_LINES", "CutoutLeakError", "cake_knife", "cake_slice", "crayon_page", "lettered_cup"]

CUP_LINE = 12  # the most characters on a line of the cup
CUP_LINES = 3
CUP_TOP, CUP_RISE = -170, 62  # the first line's top, and each line's below it
CRAYON = ("#D23A2E", "#2F6FB5", "#3E9B4F", "#E0A31E")
PAPER = "#FBF6E6"
MARKER = "#2B2F36"


class CutoutLeakError(SrstudioError, ValueError):
    """A prop asked for with arguments it cannot be drawn from."""


def _scale(scale) -> None:
    checks.positive(scale, CutoutLeakError, f"scale must be a positive number, got {scale!r}")


@register(
    "prop",
    "lettered-cup",
    style="cutout",
    summary="A big takeaway cup with a message in marker on it, no brand",
    contract=_cutout_contracts.contract('lettered-cup'),
)
def lettered_cup(
    cv: Canvas, parent, x=540, y=800, *, lines: Sequence[str] = ("HELLO",), scale: float = 1.0, id: str = "lettered-cup"
):
    """The middle of the cup is on (``x``, ``y``), 340 wide and 500 tall at scale 1, for an insert. ``lines`` are 1 to
    :data:`CUP_LINES`, each 1 to :data:`CUP_LINE` characters, set in the reel's font."""
    _scale(scale)
    if isinstance(lines, str) or not 1 <= len(lines) <= CUP_LINES:
        raise CutoutLeakError(f"a cup is lettered with 1 to {CUP_LINES} lines, got {lines!r}")
    for line in lines:
        if not isinstance(line, str) or not line.strip() or len(line) > CUP_LINE:
            raise CutoutLeakError(f"a line on a cup is 1 to {CUP_LINE} characters, got {line!r}")
    cv.require_font("a cup is lettered in it", CutoutLeakError)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M-160 -196 L160 -196 L120 250 Q0 276 -120 250Z", cv.white, ink, 6)
    cv.path(g, "M-136 80 L136 80 L124 200 Q0 226 -124 200Z", "#B27F51", cv.clear, 0)
    cv.ellipse(g, -176, -236, 352, 70, "#3E4947", ink, 6)
    cv.rect(g, -172, -214, 344, 38, "#4B5550", ink, 5, radius=10)
    for n, line in enumerate(lines):
        cv.text(g, f"{id}-line-{n}", line, -142, CUP_TOP + n * CUP_RISE, 284, 60, 46, MARKER)
    return g


@register(
    "prop",
    "crayon-page",
    style="cutout",
    summary="A sheet in a child's crayon, scribble only, no lettering",
    contract=_cutout_contracts.contract('crayon-page'),
)
def crayon_page(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, rotation: float = 0, id: str = "crayon-page"):
    """The middle of the sheet is on (``x``, ``y``), 220 by 300 at scale 1, ``rotation`` degrees round."""
    _scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=rotation)
    cv.rect(g, -110, -150, 220, 300, PAPER, ink, 4)
    cv.path(g, "M-70 -96 q24 -40 48 0 t48 0 t48 -6", stroke=CRAYON[0], sw=12)
    for k, yy in enumerate((-30, 24, 78, 122)):
        wobble = 12 if k % 2 else -10
        cv.path(g, f"M-78 {yy} Q-30 {yy + wobble} 8 {yy} T{74 - 16 * k} {yy + 3}", stroke=CRAYON[(k + 1) % 4], sw=9)
    return g


@register(
    "prop",
    "cake-knife",
    style="cutout",
    summary="A broad cake knife, held at its handle",
    contract=_cutout_contracts.contract('cake-knife'),
)
def cake_knife(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, rotation: float = 0, id: str = "cake-knife"):
    """The grip is on (``x``, ``y``) and the blade points down, ``rotation`` degrees round; 220 long at scale 1."""
    _scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=rotation)
    cv.rect(g, -13, -60, 26, 84, "#3A2A20", ink, 3.5, radius=8)
    cv.path(g, "M-16 24 L18 24 L14 160 Q-2 176 -16 150Z", "#DDE2E5", ink, 3.5)
    return g


@register(
    "prop",
    "cake-slice",
    style="cutout",
    summary="A slice of sheet cake on a paper plate",
    contract=_cutout_contracts.contract('cake-slice'),
)
def cake_slice(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, id: str = "cake-slice"):
    """The plate's middle is on (``x``, ``y``), 240 wide at scale 1."""
    _scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -120, -30, 240, 66, "#FBF6EA", ink, 4)
    cv.ellipse(g, -84, -18, 168, 42, "#EFE5D2", "#CFC3AC", 2)
    cv.path(g, "M-66 2 L-66 -70 L58 -70 L58 2 Q-4 16 -66 2Z", "#E8C38E", ink, 3.5)
    cv.path(g, "M-66 -46 L-66 -74 L58 -74 L58 -46 Q40 -30 26 -46 Q6 -28 -14 -46 Q-34 -30 -66 -46Z", "#FBF3E4", ink, 3)
    cv.ellipse(g, -8, -76, 20, 14, "#C8352B", ink, 2.5)
    return g

"""Cutout odds and ends: small things a physical gag turns on, at a table, in a store, or at a desk.

Each part stands alone, draws in its own group, and takes its beats as times, so a reel keys the picture on its lines.
Every refusal is a :class:`CutoutOddsError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = ["CutoutOddsError", "bistro_table", "eaten_sandwich", "paper_napkin"]

BREAD = "#F2E2BE"


class CutoutOddsError(SrstudioError, ValueError):
    """A prop asked for with arguments it cannot be drawn from."""


def _check_scale(scale) -> None:
    checks.positive(scale, CutoutOddsError, f"scale must be a positive number, got {scale!r}")


def _rising(times: Sequence[float], what: str) -> None:
    if not all(checks.number(t) and t >= 0 for t in times) or any(
        b <= a for a, b in zip(times, times[1:], strict=False)
    ):
        raise CutoutOddsError(f"{what} are rising times, got {list(times)!r}")


def _layers(cv: Canvas, g, right: float, scallop: bool) -> None:
    """A long sandwich from x -90 to ``right``; ``scallop`` bites its right end."""
    ink = cv.ink
    end = f"Q{right + 22:g} 0 {right:g} 40"
    if scallop:
        end = (
            f"Q{right + 16:g} -30 {right - 4:g} -14 Q{right + 18:g} 2 {right - 4:g} 16 Q{right + 14:g} 32 {right:g} 40"
        )
    cv.path(g, f"M-78 40 Q-96 0 -78 -40 L{right:g} -40 {end} Z", BREAD, ink, 3.5)
    edge = max(right - 8, -60)
    frill = f"M-90 8 Q-72 -4 -54 8 Q-36 -4 -18 8 Q0 -4 18 8 Q36 -4 {edge:g} 8 L{edge:g} 18 L-90 18Z"
    cv.path(g, frill, "#7FA45F", ink, 2.5)
    cv.rect(g, -86, -12, right + 80, 11, "#C9573F", ink, 2.5, radius=4)


@register(
    "prop", "eaten-sandwich", style="cutout", summary="A long sandwich in hand that loses a mouthful at every bite"
)
def eaten_sandwich(
    cv: Canvas, parent, x=540, y=900, *, bites: Sequence[float] = (), scale: float = 1.0, id: str = "eaten-sandwich"
):
    """Centred on (``x``, ``y``), 190 wide whole. Each time in ``bites`` takes a mouthful off its right end."""
    _check_scale(scale)
    _rising(bites, "bites")
    if len(bites) > 3:
        raise CutoutOddsError(f"a sandwich lasts three bites, got {len(bites)}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    edges = [0.0, *bites]
    for n, begin in enumerate(edges):
        stage = cv.group(g, f"{id}-stage-{n}")
        if bites:
            cv.gate(stage, [(begin, edges[n + 1] if n + 1 < len(edges) else 1e6)])
        _layers(cv, stage, 92 - 46 * n, n > 0)
    return g


@register("prop", "paper-napkin", style="cutout", summary="A folded white paper napkin, one corner lifting")
def paper_napkin(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, id: str = "paper-napkin"):
    """Lying centred on (``x``, ``y``), 150 wide."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M-75 -24 L58 -30 L75 24 L-62 30Z", "#FBF8F0", ink, 3)
    cv.path(g, "M30 -29 L58 -30 L66 -6Z", "#E4DED0", ink, 2.5)
    cv.path(g, "M-50 8 L38 4 M-44 18 L20 15", stroke="#D6CFBF", sw=2.5)
    return g


@register("prop", "bistro-table", style="cutout", summary="A small round bistro table on one leg, seen side on")
def bistro_table(cv: Canvas, parent, x=540, y=1100, *, width: float = 300, id: str = "bistro-table"):
    """The middle of its top is (``x``, ``y``); its foot stands ``width`` * 0.9 below."""
    checks.positive(width, CutoutOddsError, f"width must be positive, got {width!r}")
    ink = cv.ink
    half, foot = width / 2, width * 0.9
    g = cv.group(parent, id, x=x, y=y)
    cv.rect(g, -width * 0.03, 8, width * 0.06, foot - 8, "#4A4C4A", ink, 3)
    cv.path(g, f"M{-half * 0.5:g} {foot:g} Q0 {foot - 24:g} {half * 0.5:g} {foot:g}Z", "#4A4C4A", ink, 3)
    cv.ellipse(g, -half, -14, width, 32, "#D9C7A6", ink, 4)
    return g

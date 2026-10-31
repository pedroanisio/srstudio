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

__all__ = ["CutoutOddsError", "bistro_table", "earbud", "eaten_sandwich", "paper_napkin", "store_box", "tin_of_peas"]

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


@register("prop", "earbud", style="cutout", summary="A white wireless earbud with its short stem")
def earbud(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, flip: bool = False, id: str = "earbud"):
    """The bud's middle is on (``x``, ``y``), the stem hanging 50 below it; ``flip`` turns it for the other ear."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=-scale if flip else scale, scaleY=scale)
    cv.rect(g, -2, 2, 13, 48, "#FBFBF8", ink, 2.5, radius=6)
    cv.ellipse(g, -14, -14, 30, 28, "#FBFBF8", ink, 2.5)
    cv.path(g, "M-8 -6 Q-12 0 -8 6", stroke="#B8BBC0", sw=2.5)
    return g


@register("prop", "tin-of-peas", style="cutout", summary="A tin of peas with a green label and a pod on it")
def tin_of_peas(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, id: str = "tin-of-peas"):
    """Centred on (``x``, ``y``), 80 wide and 104 tall."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M-40 -42 L-40 42 Q0 62 40 42 L40 -42Z", "#C9CCD1", ink, 3.5)
    cv.path(g, "M-40 -28 L-40 34 Q0 54 40 34 L40 -28 Q0 -8 -40 -28Z", "#3F8A4B", ink, 2.5)
    cv.ellipse(g, -40, -56, 80, 28, "#DFE2E6", ink, 3.5)
    cv.ellipse(g, -30, -50, 60, 16, "#C9CCD1", "#A9ADB3", 2)
    cv.path(g, "M-27 20 Q0 -22 28 6 Q4 38 -27 20Z", "#BFE08F", ink, 2.5)
    for dx, dy in ((-14, 10), (0, 3), (14, 0)):
        cv.ellipse(g, dx - 7, dy - 7, 14, 14, "#6FB350", ink, 1.5)
    return g


@register("prop", "store-box", style="cutout", summary="A plain supermarket box of crackers, no brand")
def store_box(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, id: str = "store-box"):
    """Centred on (``x``, ``y``), 130 wide and 180 tall."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -65, -90, 130, 180, "#E08A3C", ink, 4)
    cv.path(g, "M-65 -44 L65 -44 L65 16 L-65 16Z", "#F7EBD2", ink, 3)
    cv.ellipse(g, -26, -38, 52, 48, "#E9C37C", ink, 2.5)
    for dx in (-10, 2, 12):
        cv.ellipse(g, dx - 2, -18, 4, 4, ink)
    cv.rect(g, -40, 38, 80, 12, "#B96A25", radius=4)
    return g

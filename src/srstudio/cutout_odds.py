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

__all__ = [
    "CutoutOddsError",
    "bistro_table",
    "chair_lever",
    "coin_purse",
    "earbud",
    "eaten_sandwich",
    "gas_lift",
    "gas_lift_keys",
    "glasses_glint",
    "lane_sign",
    "paper_napkin",
    "small_coin",
    "store_box",
    "tin_of_peas",
]

BREAD = "#F2E2BE"
LIFT_PAST = 0.06  # how far past its depth a gas lift goes, of the drop
LIFT_SETTLE = 0.3  # how long it takes to come back up, of the drop
LIFT_SETTLE_MOST = 0.12  # and no longer than this, in seconds, however long the drop


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


@register("prop", "coin-purse", style="cutout", summary="A clasp coin purse that opens on the coins inside it")
def coin_purse(
    cv: Canvas, parent, x=540, y=900, *, opens: Sequence[tuple[float, float]] = (), scale: float = 1.0, id="coin-purse"
):
    """Centred on (``x``, ``y``), 110 wide. It is shut but for the ``(start, end)`` spans of ``opens``."""
    _check_scale(scale)
    _rising([t for span in opens for t in span], "opens")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M-46 -22 Q-66 44 -30 50 L30 50 Q66 44 46 -22Z", "#7B3F5E", ink, 3.5)
    cv.path(g, "M-30 8 Q0 22 30 8 M-34 28 Q0 42 34 28", stroke="#9C5E7E", sw=2.5)
    shut = cv.group(g, f"{id}-shut")
    agape = cv.group(g, f"{id}-open")
    if opens:
        cv.gate(agape, opens)
        edges = [0.0, *(t for span in opens for t in span), 1e6]
        cv.gate(shut, [(a, b) for a, b in zip(edges[::2], edges[1::2], strict=True) if b > a])
    else:
        cv.gate(agape, [(1e6, 1e6 + 1)])
    cv.path(shut, "M-46 -22 Q0 -34 46 -22", stroke="#D3A73A", sw=6)
    cv.ellipse(shut, -14, -44, 13, 13, "#E6C25A", ink, 2)
    cv.ellipse(shut, 1, -44, 13, 13, "#E6C25A", ink, 2)
    cv.ellipse(agape, -46, -42, 92, 40, "#2A1A24", ink, 3)
    for dx in (-22, 2, 20):
        cv.ellipse(agape, dx - 9, -34, 18, 18, "#E6C25A", ink, 2)
    cv.path(agape, "M-46 -22 Q0 -4 46 -22", stroke="#D3A73A", sw=6)
    return g


@register("prop", "small-coin", style="cutout", summary="One small coin")
def small_coin(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, id: str = "small-coin"):
    """Centred on (``x``, ``y``), 44 wide."""
    _check_scale(scale)
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -22, -22, 44, 44, "#E6C25A", cv.ink, 3)
    cv.ellipse(g, -14, -14, 28, 28, cv.clear, "#B98F2E", 2)
    return g


@register("prop", "lane-sign", style="cutout", summary="A checkout lane's lit number, hung from the ceiling")
def lane_sign(
    cv: Canvas,
    parent,
    x=540,
    y=200,
    *,
    numbers: Sequence[tuple[float, str]] = ((0.0, "4"),),
    scale: float = 1.0,
    id: str = "lane-sign",
):
    """The sign's middle is (``x``, ``y``), 120 wide; ``numbers`` are ``(from time, number)``, the first from 0."""
    _check_scale(scale)
    if not numbers or numbers[0][0] != 0 or not all(isinstance(n, str) and n for _, n in numbers):
        raise CutoutOddsError(f"numbers run from time 0 and are non-empty strings, got {list(numbers)!r}")
    times = [t for t, _ in numbers]
    _rising(times, "numbers")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M-40 -60 L-40 -500 M40 -60 L40 -500", stroke="#6F747B", sw=6)
    cv.rect(g, -60, -60, 120, 120, "#23262A", ink, 4, radius=12)
    cv.rect(g, -50, -50, 100, 100, "#2F7A5F", radius=6)
    for n, ((begin, number), end) in enumerate(zip(numbers, [*times[1:], 1e6], strict=True)):
        lit = cv.group(g, f"{id}-number-{n}")
        cv.gate(lit, [(begin, end)])
        cv.text(lit, f"{id}-text-{n}", number, -50, -46, 100, 90, 70, "#FFFFFF")
    return g


@register("prop", "glasses-glint", style="cutout", summary="The light catching a pair of round glasses, once")
def glasses_glint(
    cv: Canvas,
    parent,
    lenses: Sequence[tuple[float, float]] = ((-34, -18), (36, -18)),
    *,
    at: float = 0.5,
    seconds: float = 0.5,
    scale: float = 1.0,
    id: str = "glasses-glint",
):
    """White over each lens at ``lenses``, and a star on the last, up to full at ``at`` and gone ``seconds`` later."""
    _check_scale(scale)
    if not lenses:
        raise CutoutOddsError("a glint needs at least one lens")
    checks.positive(seconds, CutoutOddsError, f"seconds must be positive, got {seconds!r}")
    _rising([at], "at")
    g = cv.group(parent, id, scaleX=scale, scaleY=scale)
    cv.gate(g, [(max(at - 0.08, 0.0), at + seconds)])
    for lens_x, lens_y in lenses:
        cv.ellipse(g, lens_x - 22, lens_y - 20, 44, 40, "#FFFFFF", opacity=0.9)
    star_x, star_y = lenses[-1]
    star = cv.group(g, f"{id}-star", x=star_x + 16, y=star_y - 14)
    size = [(at - 0.08, 0.3), (at, 1.2), (at + seconds, 0.2)]
    cv.keys(star, "scaleX", size, hold=False)
    cv.keys(star, "scaleY", size, hold=False)
    cv.path(star, "M0 -42 Q4 -4 42 0 Q4 4 0 42 Q-4 4 -42 0 Q-4 -4 0 -42Z", "#FFFFFF", cv.ink, 2)
    return g


def gas_lift_keys(drops: Sequence[tuple[float, float, float]], y: float = 0.0) -> list[tuple[float, float]]:
    """The y keys of something that sinks on a gas lift, from ``y``: each drop is ``(start, seconds, depth)``.

    It lets go slowly, falls, goes a little too far and settles at the depth, so a stack of small drops reads as one
    chair letting go again and again. Drops run in order and do not overlap. Every refusal is a
    :class:`CutoutOddsError`.
    """
    if not drops:
        raise CutoutOddsError("a gas lift needs at least one drop")
    keys = [(0.0, float(y))]
    at, level = 0.0, float(y)
    for n, drop in enumerate(drops):
        if len(drop) != 3 or not all(checks.number(v) for v in drop):
            raise CutoutOddsError(f"drop {n} is (start, seconds, depth), got {drop!r}")
        start, seconds, depth = drop
        if start < at:
            raise CutoutOddsError(f"drop {n} starts after the last one ends, got {drop!r}")
        if seconds <= 0 or depth <= 0:
            raise CutoutOddsError(f"drop {n} has a positive length and depth, got {drop!r}")
        settle = min(seconds * LIFT_SETTLE, LIFT_SETTLE_MOST)
        if start > keys[-1][0]:
            keys.append((start, level))
        keys += [
            (start + seconds * 0.25, level + depth * 0.1),
            (start + seconds, level + depth * (1 + LIFT_PAST)),
            (start + seconds + settle, level + depth),
        ]
        at, level = start + seconds + settle, level + depth
    return keys


def gas_lift(cv: Canvas, group, drops: Sequence[tuple[float, float, float]], y: float = 0.0) -> float:
    """Keys ``group``'s y through :func:`gas_lift_keys` and returns where it comes to rest."""
    keys = gas_lift_keys(drops, y)
    cv.keys(group, "y", keys, hold=False)
    return keys[-1][1]


@register("prop", "chair-lever", style="cutout", summary="An office chair's height lever, which tips on each pull")
def chair_lever(
    cv: Canvas, parent, x=540, y=900, *, pulls: Sequence[float] = (), scale: float = 1.0, id: str = "chair-lever"
):
    """The pivot is on (``x``, ``y``), the knob 80 out to the right. Each of ``pulls`` tips it down and lets it back."""
    _check_scale(scale)
    _rising(pulls, "pulls")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    arm = cv.group(g, f"{id}-arm", rotation=-8)
    if pulls:
        tips = [(0.0, -8.0)]
        for at in pulls:
            tips += [(at, -8.0), (at + 0.08, 24.0), (at + 0.3, 24.0), (at + 0.42, -8.0)]
        cv.keys(arm, "rotation", tips, hold=False)
    cv.rect(arm, 0, -5, 74, 10, "#3B3D40", cv.ink, 2.5, radius=4)
    cv.ellipse(arm, 62, -14, 28, 28, "#23262A", cv.ink, 2.5)
    cv.ellipse(g, -10, -10, 20, 20, "#6F747B", cv.ink, 2.5)
    return g

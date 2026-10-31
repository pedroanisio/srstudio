"""Collage odds and ends: paper props the everyday reels need, each a thing one sketch asks of a room.

Every prop is one paper cut-out on a place in screen pixels; its cue times are project seconds, and a bad cue is a
:class:`CollageOddsError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks, collage_sets
from .canvas import Canvas
from .collage import INK
from .errors import SrstudioError
from .registry import register

__all__ = [
    "BLUR",
    "CollageOddsError",
    "cake_slice",
    "doctor_scale",
    "eye_chart",
    "lens_frame",
    "sensor_tap",
    "spinach",
    "water_jug",
    "wine_glass",
]

Point = tuple[float, float]
BLUR = "#b9b2a4"
EDGE = 4.0
STEEL = "#aab1b8"
GLASS = "#dcecf2"
WINE = "#6b1f3a"
CAKE = "#f0c987"
ICING = "#fff3e0"
PLATE = "#fffaf0"


class CollageOddsError(SrstudioError, ValueError):
    """A prop was asked for something it cannot draw."""


def _rising(cues: Sequence[float], what: str) -> tuple[float, ...]:
    times = tuple(cues)
    if not all(checks.number(t) and t >= 0 for t in times) or list(times) != sorted(set(times)):
        raise CollageOddsError(f"{what} are rising seconds, got {cues!r}")
    return times


@register("prop", "collage-cake-slice", summary="A slice of cake on a plate that halves on every cue", style="collage")
def cake_slice(cv: Canvas, parent, x: float, y: float, cuts: Sequence[float] = (), size: float = 300.0):
    """A plate centred on ``x, y`` with a slice of ``size`` on it, half as big after every second of ``cuts``."""
    times = _rising(cuts, "a slice's cuts")
    if not (checks.number(size) and size > 0):
        raise CollageOddsError(f"a slice has a size, got {size!r}")
    g = cv.group(parent, cv.uid("g"))
    cv.ellipse(g, x - size * 0.9, y - size * 0.16, size * 1.8, size * 0.5, PLATE, INK, EDGE)
    piece = cv.group(g, cv.uid("g"), anchorX=x, anchorY=y + size * 0.08, x=x, y=y + size * 0.08)
    if times:
        keys = [(0.0, 1.0)] + [(t, 0.5 ** (k + 1)) for k, t in enumerate(times)]
        cv.keys(piece, "scaleX", keys, local=False)
        cv.keys(piece, "scaleY", keys, local=False)
    cv.rect(piece, x - size / 2, y - size * 0.34, size, size * 0.42, CAKE, INK, EDGE, radius=size * 0.03)
    cv.rect(piece, x - size / 2, y - size * 0.34, size, size * 0.12, ICING, INK, EDGE, radius=size * 0.04)
    return g


@register("prop", "collage-eye-chart", summary="An eye chart whose rows snap sharp one at a time", style="collage")
def eye_chart(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    rows: Sequence[str],
    sharp: Sequence[float],
    end: float = 4.0,
    blur_at: float | None = None,
):
    """A lit chart at ``x, y`` of ``rows``, smaller going down, each a blurred bar until its second of ``sharp``, then
    lettered; all of them melt back to bars from ``blur_at``."""
    times = _rising(sharp, "a chart's rows")
    if len(times) != len(rows) or not rows:
        raise CollageOddsError(f"a chart has one cue per row, got {len(rows)} rows and {len(times)} cues")
    last = end if blur_at is None else blur_at
    g = cv.group(parent, cv.uid("g"))
    width = 620.0
    cv.rect(g, x, y, width, 150.0 + 110.0 * len(rows), "#fffef4", INK, EDGE, radius=10.0)
    for k, (text, at) in enumerate(zip(rows, times, strict=True)):
        top = y + 50.0 + k * 110.0
        bar = width - 90.0 - k * 60.0
        blurred = cv.group(g, cv.uid("g"))
        cv.gate(blurred, [(0.0, at), *([(blur_at, end)] if blur_at is not None else [])])
        cv.rect(blurred, x + (width - bar) / 2, top + 20.0, bar, 42.0, BLUR, opacity=0.8, radius=20.0)
        if last > at:
            lit = cv.group(g, cv.uid("g"), start=at, end=last)
            collage_sets.sign(cv, lit, text, x + 20.0, top, int(width - 40), 84, size=52 - k * 6)
    return g


@register("prop", "collage-lens-frame", summary="A clinic lens frame held in front of a face", style="collage")
def lens_frame(cv: Canvas, parent, x: float, y: float, spread: float = 150.0):
    """Two lenses in a steel frame centred on ``x, y``, ``spread`` apart, with a dial between them."""
    if not (checks.number(spread) and spread > 0):
        raise CollageOddsError(f"a lens frame has a spread, got {spread!r}")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, x - spread - 150, y - 44, 2 * spread + 300, 88, STEEL, INK, EDGE, radius=30.0)
    for side in (-1, 1):
        cv.ellipse(g, x + side * spread / 2 - 86 + side * 60, y - 86, 172, 172, STEEL, INK, EDGE)
        cv.ellipse(g, x + side * spread / 2 - 56 + side * 60, y - 56, 112, 112, GLASS, INK, EDGE, opacity=0.65)
    cv.ellipse(g, x - 26, y - 26, 52, 52, "#5c6670", INK, EDGE)
    return g


@register("prop", "collage-sensor-tap", summary="A chrome sensor tap over a basin, running on cue", style="collage")
def sensor_tap(cv: Canvas, parent, x: float, y: float, runs: Sequence[tuple[float, float]] = ()):
    """A basin with its rim at ``y``, a tap at ``x``, water falling through each ``(start, end)`` of ``runs``."""
    if not all(checks.number(a) and checks.number(b) and 0 <= a < b for a, b in runs):
        raise CollageOddsError(f"a tap runs forward in time, got {runs!r}")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, x - 210, y, 420, 170, "#f4f6f4", INK, EDGE, radius=26.0)
    cv.rect(g, x - 16, y - 120, 32, 124, STEEL, INK, EDGE, radius=8.0)
    cv.rect(g, x - 16, y - 136, 110, 34, STEEL, INK, EDGE, radius=14.0)
    cv.ellipse(g, x - 9, y - 96, 18, 18, "#d93a3a", INK, 2.0)
    if runs:
        water = cv.group(g, cv.uid("g"))
        cv.gate(water, list(runs))
        cv.rect(water, x + 70, y - 104, 16, 110, "#8ccdf0", opacity=0.9, radius=6.0)
    return g

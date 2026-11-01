"""Light from outside going past: a streetlight over a moving car, a station through a train window, a lighthouse.

:func:`bands` draws a soft band that crosses the whole frame once at each given second, screened over what is under it,
so it brightens faces and leaves the dark alone. It reads only the canvas's size, so it works in any style; put it above
the figures it should cross and under what it should not (captions, a dashboard). Every band lives on the project clock
for its crossing and no longer, so a band can be placed on a held beat, the moment a pause needs something to happen.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from . import checks
from .canvas import Canvas, CanvasError

__all__ = ["CROSSING", "OPACITY", "STREETLIGHT", "bands", "shade"]

STREETLIGHT = "#ffc878"  # sodium, warm against a night shade
CROSSING = 0.8  # seconds, frame edge to frame edge
OPACITY = 0.42
WIDTH = 0.55  # of the frame's width
TILT = 12.0  # degrees: the band leans, as a light through a window does
OVERSCAN = 1.5  # of the frame's height, so a tilted band has no end in frame
_HEX = re.compile(r"#[0-9a-fA-F]{6}")


def shade(cv: Canvas, parent, colour: str, opacity: float):
    """The dark the bands cross: ``colour`` multiplied over all that is under it, at ``opacity``."""
    _checked((), CROSSING, opacity, WIDTH, colour)
    g = cv.group(parent, cv.uid("passing-shade"), blend="multiply", opacity=opacity)
    cv.rect(g, 0, 0, cv.width, cv.height, colour, cv.clear, 0, radius=0)
    return g


def _checked(at: Sequence[float], crossing: float, opacity: float, width: float, colour: str) -> None:
    if not (checks.number(crossing) and crossing > 0):
        raise CanvasError(f"a band crosses in over 0 seconds, got {crossing!r}")
    if not (checks.number(opacity) and 0 < opacity <= 1):
        raise CanvasError(f"a band's opacity is over 0 and at most 1, got {opacity!r}")
    if not (checks.number(width) and width > 0):
        raise CanvasError(f"a band's width is over 0, got {width!r}")
    if not (isinstance(colour, str) and _HEX.fullmatch(colour)):
        raise CanvasError(f"a band's colour is #rrggbb, got {colour!r}")
    if any(not (checks.number(t) and t >= 0) for t in at):
        raise CanvasError(f"a band passes at seconds >= 0, got {list(at)!r}")
    if any(b - a < crossing for a, b in zip(at, at[1:], strict=False)):
        raise CanvasError(f"bands pass in order, each after the last has crossed in {crossing} s: {list(at)!r}")


def bands(
    cv: Canvas,
    parent,
    at: Sequence[float],
    *,
    crossing: float = CROSSING,
    colour: str = STREETLIGHT,
    opacity: float = OPACITY,
    width: float = WIDTH,
    tilt: float = TILT,
    leftward: bool = False,
) -> None:
    """One band across the frame at each second of ``at``, taking ``crossing`` seconds, left to right unless
    ``leftward``; ``width`` is a fraction of the frame."""
    _checked(at, crossing, opacity, width, colour)
    wide = round(cv.width * width, 2)
    tall = round(cv.height * OVERSCAN, 2)
    paint = cv.grad(f"passing-light-{colour[1:]}", [(0.0, "#000000"), (0.5, colour), (1.0, "#000000")], (0, 0, 1, 0))
    away = wide + cv.height * 0.3  # past either edge, whatever the lean
    ends = (-away, cv.width + away)
    first, last = reversed(ends) if leftward else ends
    for t in at:
        g = cv.group(parent, cv.uid("passing-light"), start=t, end=round(t + crossing, 6), blend="screen",
                     opacity=opacity, y=round(cv.height / 2, 2), rotation=tilt)  # fmt: skip
        cv.keys(g, "x", [(t, round(first, 2)), (t + crossing, round(last, 2))], hold=False, local=False)
        cv.rect(g, round(-wide / 2, 2), round(-tall / 2, 2), wide, tall, paint)

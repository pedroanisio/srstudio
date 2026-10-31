"""The Stick style's family car trip: the rear-view mirror that fills the frame, the swim ring and the indicator.

:func:`rear_view` is the whole frame as a driver's mirror: its glass is masked, so a figure drawn large into it shows
only what the mirror catches, and it is drawn the same at noon as at 2 a.m., so a reel can cut from its last shot back
to its first. :func:`swim_ring` is an inflated ring, squashed flat when ``rx`` and ``ry`` differ, for a car packed for
the beach. :func:`blinker` is the amber arrow of the indicator, lit at each time it clicks. Everything is in frame
pixels of the 1080 × 1920 Stick frame.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from . import checks
from .canvas import Canvas
from .registry import register
from .stick import COLOUR, Gradient, StickDataError, _group, box, paint, shape

__all__ = ["CLICK_SHOWS", "MIRROR", "blinker", "rear_view", "swim_ring"]

HEADLINER = ("#4a4f59", "#2b2e35")
HOUSING, HOUSING_EDGE = "#22252b", "#3e424b"
SILVER = ("#aebcc8", "#7f8e9c")  # the same by day and by night
MIRROR = (40.0, 640.0, 1000.0, 460.0)  # the glass: x, y, w, h
_RADIUS = 110
RING_WHITE = "#f7f3e8"
AMBER, AMBER_DARK = "#ffb22e", "#7a5213"
CLICK_SHOWS = 0.26  # seconds the arrow stays lit after a click


def _rounded(x: float, y: float, w: float, h: float, r: float) -> str:
    return (f"M {x + r} {y} L {x + w - r} {y} Q {x + w} {y} {x + w} {y + r} L {x + w} {y + h - r} "
            f"Q {x + w} {y + h} {x + w - r} {y + h} L {x + r} {y + h} Q {x} {y + h} {x} {y + h - r} L {x} {y + r} "
            f"Q {x} {y} {x + r} {y} Z")  # fmt: skip


@register("prop", "stick-rear-view", tags=("car", "mirror", "insert", "fullscreen", "eyes"))
def rear_view(cv: Canvas, parent, figure: Callable[[object], object] | None = None):
    """The whole frame as a rear-view mirror on its stem. ``figure`` is called with the masked glass and draws into
    it; returns the glass."""
    if figure is not None and not callable(figure):
        raise StickDataError(f"a mirror's figure is a function that draws into the glass, got {figure!r}")
    x, y, w, h = MIRROR
    back = paint(cv, Gradient("mirror-headliner", ((0, HEADLINER[0]), (1, HEADLINER[1])), 0, 0, 0, cv.height))
    box(cv, parent, 0, 0, cv.width, cv.height, back)
    box(cv, parent, 500, 0, 80, y, HOUSING, 5)
    box(cv, parent, x - 30, y - 30, w + 60, h + 60, HOUSING, 6, r=_RADIUS + 26)
    shape(cv, parent, _rounded(x - 16, y - 16, w + 32, h + 32, _RADIUS + 12), sw=5, stroke=HOUSING_EDGE)
    glass = _group(cv, parent)
    outline = _rounded(x, y, w, h, _RADIUS)
    glass.add_mask(type="path", path=outline)
    silver = paint(cv, Gradient("mirror-glass", ((0, SILVER[0]), (1, SILVER[1])), 0, y, 0, y + h))
    box(cv, glass, x, y, w, h, silver)
    if figure is not None:
        figure(glass)
    shape(cv, parent, f"M {x + 60} {y + 90} L {x + 190} {y + 40}", sw=12, stroke="#ffffff", opacity=0.35)
    return glass


def _arc(rx: float, ry: float, start: float, stop: float) -> str:
    x0, y0 = rx * math.cos(start), ry * math.sin(start)
    x1, y1 = rx * math.cos(stop), ry * math.sin(stop)
    return f"M {x0:.2f} {y0:.2f} A {rx} {ry} 0 0 1 {x1:.2f} {y1:.2f}"


@register("prop", "stick-swim-ring", tags=("beach", "inflatable", "holiday", "car"))
def swim_ring(cv: Canvas, parent, x: float, y: float, *, rx: float = 120.0, ry: float = 120.0, band: str = "#d9483b"):
    """An inflated ring in ``band`` and white centred on (``x``, ``y``), ``ry`` under ``rx`` when it is squashed; its
    tube is as thick as a third of the smaller radius, so a ring too small to draw is refused."""
    if not all(checks.number(v) for v in (x, y, rx, ry)) or min(rx, ry) < 30:
        raise StickDataError(f"a ring sits somewhere with radii of at least 30, got {(x, y, rx, ry)!r}")
    if max(rx, ry) > 3 * min(rx, ry):
        raise StickDataError(f"a ring squashes to a third at most, got radii {rx} and {ry}")
    if not COLOUR.match(band):
        raise StickDataError(f"a ring's band must be a #rrggbb colour, got {band!r}")
    tube = min(rx, ry) * 2 / 3
    g = _group(cv, parent, x=x, y=y)
    cv.ellipse(g, -rx, -ry, 2 * rx, 2 * ry, cv.clear, stroke=cv.ink, sw=tube + 12)
    cv.ellipse(g, -rx, -ry, 2 * rx, 2 * ry, cv.clear, stroke=RING_WHITE, sw=tube)
    for k in range(4):
        start = k * math.pi / 2 + 0.2
        shape(cv, g, _arc(rx, ry, start, start + math.pi / 4 + 0.2), sw=tube - 14, stroke=band)
    shape(cv, g, _arc(rx + tube * 0.2, ry + tube * 0.2, math.pi * 1.1, math.pi * 1.45), sw=7, stroke="#ffffff")
    return g


@register("prop", "stick-blinker", tags=("car", "indicator", "amber", "dashboard"))
def blinker(cv: Canvas, parent, x: float, y: float, end: float, clicks: Sequence[float] = (), *, scale: float = 1.0):
    """The indicator's left arrow centred on (``x``, ``y``): dark, and lit for :data:`CLICK_SHOWS` from each time in
    ``clicks``."""
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"a blinker needs a positive shot length, got {end!r}")
    if not all(checks.number(v) for v in (x, y, scale)) or scale <= 0:
        raise StickDataError(f"a blinker sits somewhere at a positive scale, got {(x, y, scale)!r}")
    times = checks.rising(
        clicks, StickDataError, lambda i, t: f"click {i} must follow the last, within the shot, got {t!r}", end=end
    )
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    arrow = "M -70 0 L -14 -52 L -14 -24 L 66 -24 L 66 24 L -14 24 L -14 52 Z"
    shape(cv, g, arrow, AMBER_DARK, 5, stroke=cv.ink)
    lit = _group(cv, g)
    shape(cv, lit, arrow, AMBER, 5, stroke=cv.ink)
    cv.gate(lit, [(t, min(t + CLICK_SHOWS, end)) for t in times])
    return g

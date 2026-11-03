"""What a Toon character puts on to go somewhere: a necktie, held up or worn, and a company lanyard over it.

Both are drawn into a shot's ``front`` at reference coordinates, so they read on any character of the cast, and neither
letters anything: the card on a lanyard carries a scrawl, a word at that size being a texture on a phone. Bad input is
a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from ._toon_story_contracts import contract
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, _d, _path, fh, fx, fy
from .toon_sets import _line

__all__ = ["CARD", "SILK", "STRAP", "SWING", "SWING_PERIOD", "lanyard", "necktie"]

Point = tuple[float, float]
SILK, STRIPE = "#b23a48", "#f0c869"
STRAP, CARD, CARD_BAND = "#2f6fb7", "#fbfaf4", "#2f6fb7"
SWING, SWING_PERIOD = 7.0, 0.9  # degrees either way and the seconds of one swing, for a tie held up by its knot


def _point(at: object, what: str) -> Point:
    if not (isinstance(at, tuple) and len(at) == 2 and checks.number(at[0]) and checks.number(at[1])):
        raise ToonDataError(f"{what} is a reference point (x, y), got {at!r}")
    return float(at[0]), float(at[1])


def _scale(scale: object) -> float:
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a scale is over 0, got {scale!r}")
    return float(scale)


def _swing_keys(start: float, end: float) -> list[tuple[float, float]]:
    keys, t, side = [], start, 1.0
    while t < end:
        keys.append((round(t, 3), side * SWING))
        t, side = t + SWING_PERIOD / 2, -side
    return keys + [(round(end, 3), side * SWING)]


@register(
    "prop",
    "toon-necktie",
    summary="A striped necktie, held up by its knot and swinging, or worn",
    style="toon",
    contract=contract('toon-necktie'),
)
def necktie(
    cv: Canvas,
    parent,
    at: Point = (300.0, 560.0),
    scale: float = 1.0,
    length: float = 200.0,
    swinging: tuple[float, float] | None = None,
    start: float | None = None,
    end: float | None = None,
) -> object:
    """A tie hanging from its knot at reference ``at``, ``length`` long at ``scale`` 1, from ``start`` to ``end`` (the
    parent's stretch by default); over ``swinging`` it sways about the knot. Returns its group."""
    x, y = _point(at, "a tie's knot")
    s = _scale(scale)
    if not (checks.number(length) and length >= 60):
        raise ToonDataError(f"a tie is at least 60 long, got {length!r}")
    timed = {k: v for k, v in (("start", start), ("end", end)) if v is not None}
    g = cv.group(parent, cv.uid("g"), x=fx(x), y=fy(y), anchorX=fx(x), anchorY=fy(y), **timed)
    if swinging is not None:
        a, b = swinging
        if not (checks.number(a) and checks.number(b) and 0 <= a < b):
            raise ToonDataError(f"a tie swings over 0 <= start < end, got {swinging!r}")
        cv.keys(g, "rotation", _swing_keys(a, b), hold=False, kind="sine-in-out", local=False)
    w, n, long = 26.0 * s, 13.0 * s, length * s
    knot = 26.0 * s
    blade = _d(
        "M", (x - n, y + knot), "L", (x + n, y + knot), "L", (x + w, y + long - 30 * s), "L", (x, y + long),
        "L", (x - w, y + long - 30 * s), "Z",
    )  # fmt: skip
    _path(cv, g, blade, SILK, INK_W * 0.8)
    for k in (0.3, 0.52, 0.74):
        yy = y + long * k
        half = n + (w - n) * k
        _line(cv, g, [(x - half + 5 * s, yy + 11 * s), (x + half - 5 * s, yy - 11 * s)], 7.0 * s, STRIPE)
    tip = _d(
        "M", (x - 16 * s, y), "L", (x + 16 * s, y), "L", (x + n, y + knot), "L", (x - n, y + knot), "Z",
    )  # fmt: skip
    _path(cv, g, tip, SILK, INK_W * 0.8)
    return g


@register(
    "prop",
    "toon-lanyard",
    summary="A company lanyard with a white card, unlettered, worn over a chest",
    style="toon",
    contract=contract('toon-lanyard'),
)
def lanyard(
    cv: Canvas,
    parent,
    at: Point = (300.0, 760.0),
    scale: float = 1.0,
    neck: Sequence[Point] = ((250.0, 600.0), (350.0, 600.0)),
    start: float | None = None,
    end: float | None = None,
) -> object:
    """Two straps from the two ``neck`` points, either side of the throat, down to a card hanging at reference ``at``.
    Returns its group."""
    x, y = _point(at, "a lanyard's card")
    s = _scale(scale)
    if len(neck) != 2:
        raise ToonDataError(f"a lanyard hangs from two points, got {neck!r}")
    left, right = _point(neck[0], "a strap's end"), _point(neck[1], "a strap's end")
    timed = {k: v for k, v in (("start", start), ("end", end)) if v is not None}
    g = cv.group(parent, cv.uid("g"), **timed)
    for top in (left, right):
        _line(cv, g, [top, ((top[0] + x) / 2, (top[1] + y) / 2 + 6 * s), (x, y)], 13.0 * s, cv.ink)
        _line(cv, g, [top, ((top[0] + x) / 2, (top[1] + y) / 2 + 6 * s), (x, y)], 8.0 * s, STRAP)
    w, h = 76.0 * s, 104.0 * s
    cv.rect(g, fx(x - w / 2), fy(y), fh(w), fh(h), CARD, cv.ink, INK_W * 0.7, radius=fh(6 * s))
    cv.rect(
        g, fx(x - w / 2 + 5 * s), fy(y + 6 * s), fh(w - 10 * s), fh(24 * s), CARD_BAND, cv.clear, 0, radius=fh(3 * s)
    )
    cv.ellipse(g, fx(x - 17 * s), fy(y + 36 * s), fh(34 * s), fh(34 * s), "#d7dde6", cv.ink, FINE_W * 0.5)
    for k in (76.0, 88.0):
        _line(cv, g, [(x - 26 * s, y + k * s), (x + 26 * s, y + (k - 1) * s)], 4.0 * s, "#8a93a3")
    return g

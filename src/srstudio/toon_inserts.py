"""Small Toon parts for what a reel shows and nobody says: drops going into an eye, a voice note's progress, a list of
Wi-Fi networks, a receptionist's glass, a gull that looks at you, a garden gnome, a box of noodles and rain.

Each refuses what it cannot draw, and nothing is drawn before its time. What must be read is lettered at
phone size (:data:`READ_SIZE` frame pixels at least)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, ToonDataError, fh, fx, fy
from .toon_sets import _inked, _line

Point = tuple[float, float]
Measure = Callable[[str, float], float]
READ_SIZE = 44  # frame pixels: under this a word on a phone is a texture

__all__ = ["READ_SIZE", "eye_drops", "reception_glass"]


def _second(value: object, what: str) -> float:
    if not (checks.number(value) and value >= 0):  # type: ignore[operator]
        raise ToonDataError(f"{what} is a second from 0, got {value!r}")
    return float(value)  # type: ignore[arg-type]


COUNTER = 801.0  # the reference height of the counter top, the desk's edge
GAP = 64.0  # the gap under the glass for the paperwork
DROP_FALL = 0.22  # seconds a drop takes to reach the eye
BOTTLE, CAP, DROP = "#e8f4fb", "#3f7fbf", "#8fd0f5"


@register(
    "prop",
    "toon-eye-drops",
    summary="A bottle of eye drops that comes in over a face and lets drops fall",
    style="toon",
)
def eye_drops(
    cv: Canvas,
    parent,
    eye: Point = (176.0, 500.0),
    start: float = 0.0,
    squeezes: Sequence[float] = (0.6, 1.1),
    leave: float = 1.8,
    scale: float = 1.0,
    id: str | None = None,
) -> None:
    """The bottle tipped over the reference point ``eye`` from ``start`` to ``leave``, one drop falling at each of
    ``squeezes``, and landing on ``eye``."""
    first = _second(start, "the bottle's arrival")
    times = [_second(t, "a squeeze") for t in squeezes]
    if not times or times != sorted(times) or times[0] <= first or leave <= times[-1] + DROP_FALL:
        raise ToonDataError(f"drops fall between {start!r} and {leave!r}, in order, got {squeezes!r}")
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a scale is over 0, got {scale!r}")
    x, y = eye
    tip = y - 150 * scale
    g = cv.group(parent, id or cv.uid("eye-drops"), start=first, end=leave)
    w = 34 * scale
    body = [
        (x - w, tip - 92 * scale),
        (x + w, tip - 92 * scale),
        (x + w, tip - 26 * scale),
        (x + 8 * scale, tip),
        (x - 8 * scale, tip),
        (x - w, tip - 26 * scale),
    ]
    _inked(cv, g, body, BOTTLE, FINE_W, 2)
    cv.rect(g, fx(x - w), fy(tip - 120 * scale), fh(2 * w), fh(30 * scale), CAP, cv.ink, FINE_W, radius=fh(6))
    for at in times:
        drop = cv.group(g, cv.uid("drop"), start=at, end=at + DROP_FALL)
        cv.ellipse(drop, fx(x - 7 * scale), fy(tip), fh(14 * scale), fh(20 * scale), DROP, cv.ink, FINE_W / 2)
        cv.keys(drop, "y", [(at, 0.0), (at + DROP_FALL, fh(y - tip))], hold=False, local=False)


GLASS, GLASS_EDGE, TRAY = "#d7eef2", "#8fb0b6", "#e7e2d6"


@register(
    "prop",
    "toon-reception-glass",
    summary="A receptionist's sliding glass over a counter, with a speaking hole and a gap for the paperwork",
    style="toon",
)
def reception_glass(cv: Canvas, parent, left: float = -10.0, right: float = 602.0, top: float = 300.0) -> None:
    """The pane from reference ``left`` to ``right``, ``top`` down to the counter: whoever sits behind it is behind it
    for the whole shot. It is drawn over them, so it goes in the shot's ``front``."""
    if not (checks.number(left) and checks.number(right) and checks.number(top) and left < right and top < COUNTER):
        raise ToonDataError(f"a pane spans left to right above the counter, got {left!r}, {right!r}, {top!r}")
    g = cv.group(parent, cv.uid("reception-glass"))
    cv.rect(
        g,
        fx(left),
        fy(top),
        fh(right - left),
        fh(COUNTER - GAP - top),
        GLASS,
        GLASS_EDGE,
        FINE_W,
        radius=0,
        opacity=0.28,
    )
    for x in (left + (right - left) * 0.2, left + (right - left) * 0.62):  # two glints, so the pane reads as glass
        _line(cv, g, [(x, top + 40), (x + 70, top + 150)], 6.0, "#ffffff", 0.55)
    cv.rect(g, fx(left), fy(COUNTER - GAP), fh(right - left), fh(10), GLASS_EDGE, cv.ink, FINE_W / 2, radius=0)
    mid = (left + right) / 2
    cv.ellipse(g, fx(mid - 38), fy(top + 190), fh(76), fh(76), "#ffffff", GLASS_EDGE, FINE_W, opacity=0.5)
    for dx, dy in ((-16, 0), (16, 0), (0, -16), (0, 16), (0, 0)):
        cv.ellipse(g, fx(mid + dx - 4), fy(top + 228 + dy - 4), fh(8), fh(8), GLASS_EDGE)

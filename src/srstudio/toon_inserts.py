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
from .toon_sets import _inked

Point = tuple[float, float]
Measure = Callable[[str, float], float]
READ_SIZE = 44  # frame pixels: under this a word on a phone is a texture

__all__ = ["READ_SIZE", "eye_drops"]


def _second(value: object, what: str) -> float:
    if not (checks.number(value) and value >= 0):  # type: ignore[operator]
        raise ToonDataError(f"{what} is a second from 0, got {value!r}")
    return float(value)  # type: ignore[arg-type]


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

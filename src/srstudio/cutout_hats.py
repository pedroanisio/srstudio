"""Cutout hats that stack: each one lands on the last, and the pile leans, sways and comes down together.

A stack is a chain of seats, each carried by the seat under it, so a small turn at every seat adds up to a column that
bends the higher it goes. A hat lands with a short drop and a squash at its given time. A stack is meant to be hung on
a head (``who.head``), which carries it through the head's own nods. ``hats`` may run well past the top of the frame.
Every refusal is a :class:`CutoutHatsError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = ["CutoutHatsError", "HATS", "STACK", "hat_stack", "stack_height", "tiny_hat"]

HEIGHT = {
    "trilby": 44,
    "boater": 36,
    "visor": 20,
    "beanie": 60,
    "headset": 26,
    "hard-hat": 66,
    "chef": 190,
}  # the next sits into the crown
HATS = tuple(HEIGHT)
STACK = (("trilby", 0.0), ("boater", 0.0), ("beanie", 0.0))
DROP = 0.14  # seconds from the air to the landing
LEAN = (-1.0, 1.4, -0.8, 1.0, -1.2, 0.9, -0.7)  # how each hat sits on the one under it, in degrees
TOPPLE = 0.55  # seconds from the push to out of the frame


class CutoutHatsError(SrstudioError, ValueError):
    """A hat or a stack asked for with arguments it cannot be drawn from."""


def stack_height(kinds: Sequence[str]) -> int:
    """How tall ``kinds`` stand on one another at scale 1."""
    return sum(HEIGHT[kind] for kind in kinds)


def _trilby(cv: Canvas, g) -> None:
    cv.path(g, "M-70 -12 Q-74 -74 -38 -80 Q0 -66 38 -80 Q74 -74 70 -12Z", "#5B5148", cv.ink, 3.5)
    cv.rect(g, -71, -32, 142, 20, "#2A2622", cv.ink, 2)
    cv.path(g, "M-112 -6 Q0 -22 112 -6 Q0 12 -112 -6Z", "#6C6156", cv.ink, 3.5)


def _boater(cv: Canvas, g) -> None:
    cv.path(g, "M-74 -8 L-70 -58 Q0 -66 70 -58 L74 -8Z", "#E8D08E", cv.ink, 3.5)
    cv.rect(g, -73, -30, 146, 22, "#C8352B", cv.ink, 2)
    cv.path(g, "M-118 -4 Q0 -18 118 -4 Q0 12 -118 -4Z", "#EAD596", cv.ink, 3.5)


def _visor(cv: Canvas, g) -> None:
    cv.path(g, "M-78 -34 Q0 -22 78 -34 L80 -6 Q0 6 -80 -6Z", "#2E7D52", cv.ink, 3)
    cv.path(g, "M-74 -8 Q0 4 74 -8 L92 26 Q0 44 -92 26Z", "#3FA66E", cv.ink, 3, opacity=0.8)


def _beanie(cv: Canvas, g) -> None:
    cv.path(g, "M-72 -8 Q-80 -88 0 -90 Q80 -88 72 -8Z", "#D98A2B", cv.ink, 3.5)
    for x in (-44, -15, 15, 44):
        cv.line(g, x, -14, x * 0.74, -82, "#B86F1C", 3)
    cv.rect(g, -78, -30, 156, 30, "#C07820", cv.ink, 3, radius=8)
    cv.ellipse(g, -24, -116, 48, 44, "#F1E4C8", cv.ink, 3)


def _headset(cv: Canvas, g) -> None:
    cv.path(g, "M-74 -8 Q-76 -54 0 -56 Q76 -54 74 -8", stroke=cv.ink, sw=9)
    cv.path(g, "M-74 -8 Q-76 -54 0 -56 Q76 -54 74 -8", stroke="#4A525C", sw=5)
    cv.rect(g, -92, -26, 30, 44, "#2F353D", cv.ink, 3, radius=9)
    cv.rect(g, 62, -26, 30, 44, "#2F353D", cv.ink, 3, radius=9)
    cv.path(g, "M-78 18 Q-70 40 -30 38", stroke=cv.ink, sw=5)
    cv.ellipse(g, -36, 31, 16, 14, "#2F353D", cv.ink, 2)


def _hard_hat(cv: Canvas, g) -> None:
    cv.path(g, "M-76 -10 Q-76 -92 0 -92 Q76 -92 76 -10Z", "#F0C233", cv.ink, 3.5)
    cv.path(g, "M-14 -91 Q-14 -60 -18 -10 L18 -10 Q14 -60 14 -91Z", "#DDAE22", cv.ink, 2.5)
    cv.path(g, "M-104 -12 L104 -12 Q110 2 100 4 L-100 4 Q-110 2 -104 -12Z", "#F0C233", cv.ink, 3.5)


def _chef(cv: Canvas, g) -> None:
    cv.path(g, "M-60 -10 L-68 -116 Q-104 -160 -56 -176 Q-30 -204 4 -184 Q44 -206 66 -172 Q104 -152 68 -114 L60 -10Z",
            "#FFFFFF", cv.ink, 3.5)  # fmt: skip
    cv.line(g, -26, -112, -24, -40, "#CFCFC8", 3)
    cv.line(g, 26, -112, 24, -40, "#CFCFC8", 3)
    cv.rect(g, -62, -32, 124, 26, "#F2F0E8", cv.ink, 3)


DRAW = {
    "trilby": _trilby,
    "boater": _boater,
    "visor": _visor,
    "beanie": _beanie,
    "headset": _headset,
    "hard-hat": _hard_hat,
    "chef": _chef,
}


def _check_stack(hats, scale, topple) -> None:
    checks.positive(scale, CutoutHatsError, f"scale must be a positive number, got {scale!r}")
    if not hats:
        raise CutoutHatsError("a stack needs at least one hat")
    unknown = [h[0] for h in hats if h[0] not in HEIGHT]
    if unknown:
        raise CutoutHatsError(f"no hat is drawn for {unknown}; known: {', '.join(HATS)}")
    times = [h[1] for h in hats]
    if not all(checks.number(t) and t >= 0 for t in times):
        raise CutoutHatsError(f"a hat lands at a finite time, got {times!r}")
    if any(b < a for a, b in zip(times, times[1:], strict=False)):
        raise CutoutHatsError(f"a stack grows from the bottom, so its hats land in order, got {times!r}")
    if topple is not None:
        if len(topple) != 2 or not checks.number(topple[0]) or topple[1] not in (1, -1):
            raise CutoutHatsError(f"a topple is (time, side), side +1 or -1, got {topple!r}")
        if topple[0] < times[-1]:
            raise CutoutHatsError(f"a stack falls after its last hat, got {topple[0]!r} and {times[-1]!r}")


@register(
    "prop",
    "hat-stack",
    style="cutout",
    summary="A column of hats, each landing on the last with a squash, that sways and topples as one",
)
def hat_stack(
    cv: Canvas,
    parent,
    x=540,
    y=800,
    hats: Sequence[tuple[str, float]] = STACK,
    *,
    scale: float = 1.0,
    sway: Sequence[tuple[float, float]] = (),
    topple: tuple[float, int] | None = None,
    id: str = "hat-stack",
):
    """The first hat's brim sits on (``x``, ``y``). ``hats`` are (kind, landing time), from the bottom; ``sway`` is
    rotation keys every seat takes, so they add up towards the top. ``topple`` is (time, side): the column swings over
    that way and drops out of the frame, and is gone :data:`TOPPLE` later."""
    _check_stack(hats, scale, topple)
    root = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    if topple is not None:
        at, side = topple
        cv.gate(root, [(0.0, at + TOPPLE)])
        cv.keys(root, "rotation", [(at, 0.0), (at + TOPPLE, 118.0 * side)], hold=False, kind="sine-in")
        cv.keys(root, "y", [(at, y), (at + TOPPLE, y + 520.0)], hold=False, kind="sine-in")
    seat = root
    for n, (kind, at) in enumerate(hats):
        tilted = cv.group(seat, f"{id}-seat-{n}", rotation=LEAN[n % len(LEAN)])
        if sway:
            lean = LEAN[n % len(LEAN)]
            cv.keys(tilted, "rotation", [(t, lean + value) for t, value in sway], hold=False, kind="sine-in-out")
        landing = cv.group(tilted, f"{id}-{n}-{kind}")
        if at >= DROP:
            cv.keys(landing, "opacity", [(0.0, 0), (at - DROP, 1)])
            cv.keys(landing, "y", [(at - DROP, -240.0), (at, 0.0)], hold=False, kind="sine-in")
            cv.keys(landing, "scaleY", [(at, 0.86), (at + 0.1, 1.04), (at + 0.18, 1.0)], hold=False)
        DRAW[kind](cv, landing)
        seat = cv.group(tilted, f"{id}-on-{n}", y=-HEIGHT[kind])
    return root


@register("prop", "tiny-hat", style="cutout", summary="A very small round hat, the size of a walnut on a grown head")
def tiny_hat(cv: Canvas, parent, x=540, y=800, *, scale: float = 1.0, id: str = "tiny-hat"):
    """The brim's middle sits on (``x``, ``y``), 58 wide and 30 tall at scale 1."""
    checks.positive(scale, CutoutHatsError, f"scale must be a positive number, got {scale!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M-17 -4 Q-19 -30 0 -30 Q19 -30 17 -4Z", "#2E3138", cv.ink, 2.5)
    cv.rect(g, -18, -11, 36, 7, "#C8352B", cv.ink, 1.5)
    cv.path(g, "M-29 -3 Q0 -10 29 -3 Q0 5 -29 -3Z", "#2E3138", cv.ink, 2.5)
    return g

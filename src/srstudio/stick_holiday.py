"""The Stick style's holidays: what a kitchen fills up with when one person has decided the season has started.

:func:`tree` is a small potted fir and :func:`tree_star` the star for its tip, drawn apart so a hand can hold it;
:func:`light_string` is a string of bulbs that can blink on at a moment; :func:`step_stool` is what somebody stands on
to reach; :func:`pumpkin` is a plain pumpkin with no carved face, in a plain red bobble hat or without one; and
:func:`smart_speaker` is an invented speaker with a band of light, its shape no real product's, with no letters on it.
:func:`worktop` is a plain kitchen worktop to stand them on, drawn in front of the figures. Nothing here draws a face.
Everything is in frame pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same. Every
refusal is a :class:`~srstudio.stick.StickDataError`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from . import checks
from ._stick_contract_base import END, PIXEL, SCALE, draw, placed
from .canvas import Canvas
from .contracts import ParameterContract as P
from .registry import register
from .stick import StickDataError, _group, box, oval, shape

__all__ = [
    "BULB_COLOURS",
    "HAT",
    "PUMPKIN",
    "RING",
    "RING_DIM",
    "STEP_RISE",
    "TREE_H",
    "WORKTOP_BODY",
    "WORKTOP_TOP",
    "light_points",
    "light_string",
    "lit_group",
    "pumpkin",
    "ring_group",
    "smart_speaker",
    "step_stool",
    "stool_top",
    "tree",
    "tree_star",
    "tree_top",
    "worktop",
]

NEEDLE, NEEDLE_DARK, BARK, POT, POT_DARK = "#3f7d4e", "#2e6240", "#6b4a2f", "#b5573d", "#8d3f2a"
STAR, STAR_EDGE = "#f4c542", "#b98a1e"
TREE_H = 900.0  # the pot's foot to the tree's tip, the star's middle, at scale 1
_TIERS = ((-170.0, -560.0, 190.0), (-400.0, -740.0, 155.0), (-600.0, -TREE_H, 115.0))  # base, tip, half width
_BAUBLES = (
    (-100.0, -240.0, "#d0453b"),
    (80.0, -290.0, "#f4c542"),
    (-60.0, -460.0, "#e8e2d4"),
    (65.0, -510.0, "#d0453b"),
    (-38.0, -660.0, "#f4c542"),
    (26.0, -740.0, "#e8e2d4"),
)
BULB_COLOURS = ("#ff5a4f", "#ffc93c", "#58d68d", "#5ab4ff")
WIRE, DARK_BULB = "#2f3438", "#7a7468"
BLINK_ON, BLINK_OFF = 0.08, 0.16  # after ``on``: lit this long, then dark until this far in, then it holds
BULB_R, GLOW_R, GLOW_OPACITY = 11.0, 24.0, 0.32
WOOD, WOOD_DARK = "#c88b4e", "#9a6636"
STEP_RISE, STEP_W, TREAD = 80.0, 230.0, 18.0  # one tread up to the next, its width and thickness, at scale 1
MAX_STEPS = 3
PUMPKIN, PUMPKIN_DARK, STEM = "#e8852c", "#c96a1c", "#6f7a3a"
HAT, HAT_CUFF, BOBBLE = "#c8362b", "#a32a22", "#f6f1e6"
_LOBES = ((-48.0, 54.0), (48.0, 54.0), (-20.0, 46.0), (20.0, 46.0))  # the pumpkin's ribs: x of the middle, half width
BODY, SLOT = "#3d4a52", "#222a2f"
RING, RING_DIM = "#ff7a5c", "#6d4a45"  # coral: no real speaker's ring
WORKTOP_TOP, WORKTOP_EDGE, WORKTOP_BODY, WORKTOP_LINE = "#e9e3d6", "#cfc7b6", "#7f9a8a", "#62796b"
SLAB, DOOR_W, OVERHANG = 34.0, 170.0, 14.0  # the slab's thickness, a cupboard door's width, the slab past the doors


def _scale(scale: float, what: str) -> float:
    return checks.positive(scale, StickDataError, f"a {what}'s scale is positive, got {scale!r}")


def _placed(cv: Canvas, parent, x: float, y: float, scale: float):
    return _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)


def tree_top(x: float, y: float, *, scale: float = 1.0) -> tuple[float, float]:
    """Where the tip of a :func:`tree` with its foot at ``x, y`` is: the star's middle."""
    return x, y - TREE_H * _scale(scale, "tree")


@register(
    "prop",
    "stick-tree-star",
    contract=placed(
        ("scale", SCALE),
        local=True,
        constraints=("x/y is the star's middle: draw it at tree_top, or at a held group's origin.",),
    ),
    tags=("christmas", "star", "holiday", "tree"),
)
def tree_star(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0):
    """A plain five-pointed star, its middle at ``x, y``."""
    g = _placed(cv, parent, x, y, _scale(scale, "star"))
    points = []
    for i in range(10):
        reach = 62.0 if i % 2 == 0 else 26.0
        angle = math.radians(-90 + i * 36)
        points.append((round(reach * math.cos(angle), 2), round(reach * math.sin(angle), 2)))
    (hx, hy), *rest = points
    shape(cv, g, f"M {hx} {hy} " + " ".join(f"L {a} {b}" for a, b in rest) + " Z", STAR, 5, stroke=STAR_EDGE)
    return g


@register(
    "prop",
    "stick-holiday-tree",
    contract=placed(
        ("scale", SCALE),
        (
            "star",
            P(type=bool, description="Draws the star on the tip; False leaves it bare, for a star held in a hand."),
        ),
        local=True,
        constraints=("x/y is the pot's foot; tree_top gives the tip, TREE_H above it at scale 1.",),
    ),
    tags=("christmas", "tree", "holiday", "home"),
)
def tree(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0, star: bool = True):
    """A small potted fir, its pot's foot at ``x, y``: three tiers and a few plain baubles. ``star=False`` leaves the
    tip bare, for a star still in somebody's hand."""
    g = _placed(cv, parent, x, y, _scale(scale, "tree"))
    limbs = _group(cv, g)
    box(cv, limbs, -18, -200, 36, 90, BARK)
    for base, tip, half in _TIERS:
        shape(cv, limbs, f"M {-half} {base} Q 0 {base + 34} {half} {base} L 0 {tip} Z", NEEDLE, 6, stroke=NEEDLE_DARK)
    for bx, by, colour in _BAUBLES:
        oval(cv, limbs, bx - 15, by - 15, 30, 30, colour)
    shape(cv, g, "M -92 -116 L 92 -116 L 70 0 L -70 0 Z", POT, 6, stroke=cv.ink)
    cv.rect(g, -104, -134, 208, 28, POT_DARK, stroke=cv.ink, sw=6, radius=6)
    if star:
        tree_star(cv, g, 0, -TREE_H)
    return g


def light_points(x0: float, y0: float, x1: float, y1: float, bulbs: int, *, sag: float) -> list[tuple[float, float]]:
    """Where ``bulbs`` bulbs hang on a wire from ``x0, y0`` to ``x1, y1`` that sags ``sag`` at its middle."""
    return [
        (x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + sag * 4 * u * (1 - u))
        for u in (i / (bulbs - 1) for i in range(bulbs))
    ]


def lit_group(string):
    """The group of a :func:`light_string` that holds its lit bulbs: the one a scene's gate is read from."""
    return list(string.elements())[-1]


@register(
    "prop",
    "stick-light-string",
    contract=draw(
        ("x0", PIXEL),
        ("y0", PIXEL),
        ("x1", PIXEL),
        ("y1", PIXEL),
        ("end", END),
        ("bulbs", P(type=int, description="At least two bulbs, spaced evenly along the wire.")),
        ("sag", P(unit="frame pixels", description="How far the wire hangs below its ends at its middle.")),
        (
            "on",
            P(unit="seconds", timebase="canvas", minimum=0, description="When it blinks on; None burns throughout."),
        ),
        constraints=("The bulbs burn in the same four plain colours in order; it stutters once as it comes on.",),
    ),
    tags=("christmas", "lights", "holiday", "home", "window"),
)
def light_string(
    cv: Canvas,
    parent,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    end: float,
    *,
    bulbs: int = 9,
    sag: float = 36.0,
    on: float | None = None,
):
    """A wire of bulbs from ``x0, y0`` to ``x1, y1``, dark until ``on`` seconds, when it stutters once and burns to
    ``end``; with no ``on`` it burns from the first frame."""
    if not all(checks.number(v) for v in (x0, y0, x1, y1)):
        raise StickDataError(f"a string of lights has finite ends, got {(x0, y0, x1, y1)!r}")
    checks.positive(end, StickDataError, f"a string of lights lasts some seconds, got {end!r}")
    if not (isinstance(bulbs, int) and not isinstance(bulbs, bool) and bulbs >= 2):
        raise StickDataError(f"a string of lights has at least 2 bulbs, got {bulbs!r}")
    checks.non_negative(sag, StickDataError, f"a string of lights sags 0 or more, got {sag!r}")
    if on is not None:
        checks.second(on, StickDataError, f"lights come on inside 0..{end}, got {on!r}", end=end - BLINK_OFF)
    g = _group(cv, parent)
    points = light_points(x0, y0, x1, y1, bulbs, sag=sag)
    middle = ((x0 + x1) / 2, (y0 + y1) / 2 + 2 * sag)
    shape(cv, g, f"M {x0} {y0} Q {middle[0]} {middle[1]} {x1} {y1}", sw=4, stroke=WIRE)
    for x, y in points:
        oval(cv, g, x - BULB_R, y, 2 * BULB_R, 2 * BULB_R, DARK_BULB)
    lit = _group(cv, g)
    for i, (x, y) in enumerate(points):
        colour = BULB_COLOURS[i % len(BULB_COLOURS)]
        oval(cv, lit, x - GLOW_R, y + BULB_R - GLOW_R, 2 * GLOW_R, 2 * GLOW_R, colour, opacity=GLOW_OPACITY)
        oval(cv, lit, x - BULB_R, y, 2 * BULB_R, 2 * BULB_R, colour)
    cv.gate(lit, [(0.0, end)] if on is None else [(on, on + BLINK_ON), (on + BLINK_OFF, end)])
    return g


def _steps(steps: int) -> int:
    if not (isinstance(steps, int) and not isinstance(steps, bool) and 1 <= steps <= MAX_STEPS):
        raise StickDataError(f"a step stool has 1 to {MAX_STEPS} steps, got {steps!r}")
    return steps


def stool_top(*, steps: int = 2, scale: float = 1.0) -> float:
    """How high above its foot a :func:`step_stool`'s top tread stands."""
    return _steps(steps) * STEP_RISE * _scale(scale, "stool")


@register(
    "prop",
    "stick-step-stool",
    contract=placed(
        ("steps", P(type=int, description="One to three treads.")),
        ("scale", SCALE),
        local=True,
        constraints=("x/y is the middle of its foot; stool_top gives the top tread's height above it.",),
    ),
    tags=("stool", "steps", "home", "kitchen"),
)
def step_stool(cv: Canvas, parent, x: float, y: float, *, steps: int = 2, scale: float = 1.0):
    """A plain wooden step stool, its foot's middle at ``x, y``: a figure stands on its top tread, :func:`stool_top`
    above the foot."""
    high = stool_top(steps=steps, scale=1.0)
    g = _placed(cv, parent, x, y, _scale(scale, "stool"))
    half = STEP_W / 2
    for leg in (-1, 1):
        shape(cv, g, f"M {leg * half} 0 L {leg * (half - 34)} {-high}", sw=14, stroke=WOOD_DARK)
    for i in range(1, steps + 1):
        narrower = 12.0 * (steps - i)
        top = -i * STEP_RISE
        cv.rect(g, -half + 10 + narrower, top, STEP_W - 20 - 2 * narrower, TREAD, WOOD, stroke=cv.ink, sw=4, radius=4)
    return g


@register(
    "prop",
    "stick-pumpkin",
    contract=placed(
        ("scale", SCALE),
        ("hat", P(type=bool, description="A plain red bobble hat, cuff and white bobble; False leaves it bare.")),
        local=True,
        constraints=("x/y is the middle of its foot. It has ribs and a stem and no face, carved or painted.",),
    ),
    tags=("halloween", "pumpkin", "holiday", "food", "hat"),
)
def pumpkin(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0, hat: bool = True):
    """A plain orange pumpkin sitting on ``x, y``: ribs and a stem and no face, in a plain red bobble hat unless
    ``hat=False``."""
    g = _placed(cv, parent, x, y, _scale(scale, "pumpkin"))
    high = 128.0
    shape(
        cv, g, f"M 0 0 C -130 12 -130 {-high - 8} 0 {-high} C 130 {-high - 8} 130 12 0 0 Z", PUMPKIN, 6, stroke=cv.ink
    )
    for rib, half in _LOBES:
        shape(cv, g, f"M {rib} -2 Q {rib + (half if rib > 0 else -half) * 0.8} {-high / 2} {rib} {-high + 2}", sw=4,
              stroke=PUMPKIN_DARK)  # fmt: skip
    if hat:
        _hat(cv, g, high)
    else:
        shape(cv, g, f"M -9 {-high + 4} L -5 {-high - 32} L 13 {-high - 36} L 11 {-high + 4} Z", STEM, 5, stroke=cv.ink)
    return g


def _hat(cv: Canvas, parent, high: float) -> None:
    """A knitted hat pulled down on the pumpkin: a dome, a ribbed cuff and one white bobble, no fur and no point."""
    cuff = -high - 8
    shape(
        cv, parent, f"M -66 {cuff} Q -62 {cuff - 92} 0 {cuff - 94} Q 62 {cuff - 92} 66 {cuff} Z", HAT, 6, stroke=cv.ink
    )
    cv.rect(parent, -74, cuff - 12, 148, 34, HAT_CUFF, stroke=cv.ink, sw=6, radius=10)
    for rib in (-48, -24, 0, 24, 48):
        shape(cv, parent, f"M {rib} {cuff - 8} L {rib} {cuff + 18}", sw=3, stroke=HAT)
    cv.ellipse(parent, -26, cuff - 142, 52, 52, BOBBLE, stroke=cv.ink, sw=5)


def ring_group(speaker):
    """The group of a :func:`smart_speaker` that holds its lit ring: the one a scene's gate is read from."""
    return list(speaker.elements())[-1]


@register(
    "prop",
    "stick-smart-speaker",
    contract=placed(
        ("scale", SCALE),
        (
            "glow",
            P(
                unit="seconds",
                timebase="canvas",
                description="Rising (start, end) spans when the ring is lit; between them it stays dim.",
            ),
        ),
        local=True,
        constraints=("x/y is the middle of its foot. No letters, logo or wake word: it is called only Speaker.",),
    ),
    tags=("speaker", "device", "home", "invented", "voice"),
)
def smart_speaker(
    cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0, glow: Sequence[tuple[float, float]] = ()
):
    """An invented smart speaker, its foot's middle at ``x, y``: a squat chamfered block, five slots of grille and a
    band of coral light round its top, dim except through the ``glow`` spans. It answers to no real product's shape."""
    scale = _scale(scale, "speaker")
    spans = checks.spans(
        glow,
        StickDataError,
        lambda span: f"a speaker's glow spans a start before its end, got {span!r}",
        shape=lambda span: f"a speaker's glow span is a (start, end) pair, got {span!r}",
        ordered=lambda span: f"a speaker's glow spans do not overlap, got {span!r}",
    )
    g = _placed(cv, parent, x, y, scale)
    shape(
        cv, g, "M -96 -16 L -96 -102 L -62 -140 L 62 -140 L 96 -102 L 96 -16 L 78 0 L -78 0 Z", BODY, 6, stroke=cv.ink
    )
    for i in range(5):
        box(cv, g, -58, -84 + i * 15, 116, 6, SLOT, r=3)
    band = "M -62 -132 L 62 -132 L 84 -106 L -84 -106 Z"
    shape(cv, g, band, RING_DIM)
    lit = _group(cv, g)
    if spans:
        shape(cv, lit, "M -74 -146 L 74 -146 L 106 -98 L -106 -98 Z", RING, opacity=GLOW_OPACITY)
        shape(cv, lit, band, RING)
        cv.gate(lit, spans)
    return g


@register(
    "prop",
    "stick-worktop",
    contract=draw(
        ("x0", PIXEL),
        ("x1", PIXEL),
        ("top", PIXEL),
        constraints=(
            "Drawn over the figures, it hides what stands behind it from the slab down, to the frame's foot.",
        ),
    ),
    tags=("kitchen", "counter", "home", "front-layer"),
)
def worktop(cv: Canvas, parent, x0: float, x1: float, top: float):
    """A plain kitchen worktop from ``x0`` to ``x1``, its slab's top at ``top``, with cupboard doors under it down past
    the frame's foot. Draw it after the figures it stands in front of, and stand what is on it after it."""
    if not all(checks.number(v) for v in (x0, x1, top)) or x1 <= x0 or not 0 <= top < cv.height:
        raise StickDataError(f"a worktop runs from x0 to a later x1 with its top in the frame, got {(x0, x1, top)!r}")
    g = _group(cv, parent)
    body = top + SLAB
    box(cv, g, x0, body, x1 - x0 - OVERHANG, cv.height - body + 8, WORKTOP_BODY)
    n = max(1, round((x1 - x0 - OVERHANG) / DOOR_W))
    door = (x1 - x0 - OVERHANG) / n
    for i in range(n):
        cv.rect(
            g, x0 + i * door + 12, body + 34, door - 24, cv.height, WORKTOP_BODY, stroke=WORKTOP_LINE, sw=6, radius=6
        )
        box(cv, g, x0 + (i + 0.5) * door - 30, body + 16, 60, 8, WORKTOP_LINE, r=4)
    cv.rect(g, x0, top, x1 - x0, SLAB, WORKTOP_TOP, stroke=cv.ink, sw=6, radius=4)
    box(cv, g, x0, top + SLAB - 10, x1 - x0, 10, WORKTOP_EDGE)
    return g

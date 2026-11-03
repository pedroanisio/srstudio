"""Cutout at a big-box store: the aisle, what goes in the cart, and the dark at home afterwards.

The aisle follows :mod:`srstudio.locations`: it draws in z-order, calls its slots at the right depth, gates its root
group before drawing, and places both signature marks. Its shelves are a blurred far plane, so they can slide past
without taking the cast with them.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from . import _counter_store_contracts as family_contracts
from . import checks, locations, look, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

Slot = locations.Slot

__all__ = [
    "CutoutStoreError",
    "checkout_lane",
    "dark_eyes",
    "hand_basket",
    "kayak",
    "life_ring",
    "light_switch",
    "long_receipt",
    "paddle",
    "shelf_goods",
    "shopping_cart",
    "step_ladder",
    "store_aisle",
    "table_lamp",
    "taper_candles",
]

SHADOW = "#2A2018"
CHROME = "#B9C2C8"


class CutoutStoreError(SrstudioError, ValueError):
    """A prop or a set asked for with arguments it cannot be drawn from."""


def _check_scale(scale) -> None:
    checks.positive(scale, CutoutStoreError, f"scale must be a positive number, got {scale!r}")


@register(
    "prop",
    "hand-basket",
    style="cutout",
    summary="A very small red wire shopping basket, with a handle",
    contract=family_contracts.contract('hand-basket'),
)
def hand_basket(cv: Canvas, parent, x=540, y=1300, *, scale: float = 1.0, id: str = "hand-basket"):
    """The foot's middle stands on (``x``, ``y``), 240 wide at scale 1."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M-110 -130 Q0 -290 110 -130", stroke="#C8352B", sw=10)
    cv.path(g, "M-120 -130 L-96 0 L96 0 L120 -130Z", "#D8473B", ink, 4.5)
    for k in range(-2, 3):
        cv.line(g, k * 40, -126, k * 34, -6, "#8E2A22", 4)
    for yy in (-94, -56, -20):
        cv.line(g, -112, yy, 112, yy, "#8E2A22", 4)
    return g


@register(
    "prop",
    "shopping-cart",
    style="cutout",
    summary="A store cart seen from the front, chrome wire on small wheels; goods stand inside it",
    contract=family_contracts.contract('shopping-cart'),
    slots=('contents',),
)
def shopping_cart(
    cv: Canvas, parent, x=540, y=1500, *, contents: Slot = None, scale: float = 1.0, id: str = "shopping-cart"
):
    """The wheels stand on (``x``, ``y``), 620 wide at scale 1. ``contents`` draws inside, in the cart's own
    coordinates, with the front wire over it; its floor is at y -170."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    look.pool(cv, g, f"{id}-contact", SHADOW + "CC", -320, -30, 660, 60, opacity=0.5)
    cv.path(g, "M-310 -540 L-310 -590 L310 -590 L310 -540", stroke=CHROME, sw=12)  # the handle, beyond the goods
    locations._call(contents, g)
    cv.path(g, "M-300 -520 L-250 -170 L250 -170 L300 -520Z", "#FFFFFF", CHROME, 6, opacity=0.12)
    for k in range(-5, 6):
        cv.line(g, k * 56, -520, k * 46, -170, CHROME, 5)
    for yy in (-470, -400, -330, -250):
        half = 300 - (yy + 520) * 0.143
        cv.line(g, -half, yy, half, yy, CHROME, 5)
    cv.path(g, "M-300 -520 L-250 -170 L250 -170 L300 -520Z", stroke=ink, sw=4)
    cv.path(g, "M-250 -170 L-230 -40 M250 -170 L230 -40", stroke="#6F747B", sw=9)
    for wx in (-230, 230):
        cv.ellipse(g, wx - 34, -60, 68, 68, "#23262A", ink, 4)
    return g


@register(
    "prop",
    "table-lamp",
    style="cutout",
    summary="A table lamp with a pleated shade",
    contract=family_contracts.contract('table-lamp'),
)
def table_lamp(cv: Canvas, parent, x=540, y=1300, *, scale: float = 1.0, id: str = "table-lamp"):
    """Its foot's middle stands on (``x``, ``y``), 300 tall at scale 1."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -50, -16, 100, 16, "#6E5236", ink, 3.5)
    cv.rect(g, -9, -170, 18, 156, "#8E6340", ink, 3)
    cv.path(g, "M-54 -300 L54 -300 L96 -160 L-96 -160Z", "#F0C655", ink, 4)
    for k in range(-3, 4):
        cv.line(g, k * 14, -296, k * 26, -164, "#D3A73A", 3)
    return g


@register(
    "prop",
    "taper-candles",
    style="cutout",
    summary="Three tall candles bound together with string",
    contract=family_contracts.contract('taper-candles'),
)
def taper_candles(cv: Canvas, parent, x=540, y=1300, *, scale: float = 1.0, id: str = "taper-candles"):
    """Their foot's middle stands on (``x``, ``y``), 260 tall at scale 1."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    for k, tall in zip((-30, 0, 30), (240, 260, 225), strict=True):
        cv.rect(g, k - 13, -tall, 26, tall, "#F4EFE0", ink, 3)
        cv.line(g, k, -tall, k, -tall - 16, ink, 3)
    cv.rect(g, -48, -96, 96, 16, "#C8352B", ink, 2.5)
    return g


@register(
    "prop",
    "step-ladder",
    style="cutout",
    summary="An aluminium step ladder, folded, with four treads",
    contract=family_contracts.contract('step-ladder'),
)
def step_ladder(cv: Canvas, parent, x=540, y=1300, *, height: float = 760, scale: float = 1.0, id: str = "step-ladder"):
    """Its foot's middle stands on (``x``, ``y``), ``height`` tall."""
    _check_scale(scale)
    checks.positive(height, CutoutStoreError, f"height must be positive, got {height!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -80, -height, 20, height, CHROME, ink, 3.5)
    cv.rect(g, 60, -height, 20, height, CHROME, ink, 3.5)
    for k in range(1, 5):
        cv.rect(g, -66, -k * height / 5 - 10, 132, 20, "#D7DDE1", ink, 3)
    return g


@register(
    "prop",
    "kayak",
    style="cutout",
    summary="A long yellow sit-in kayak seen from the side, with its cockpit open",
    contract=family_contracts.contract('kayak'),
    slots=('rider',),
)
def kayak(
    cv: Canvas,
    parent,
    x=540,
    y=900,
    *,
    length: float = 1500,
    beam: float = 96,
    rider: Slot = None,
    rotation: float = 0,
    scale: float = 1.0,
    id: str = "kayak",
):
    """The cockpit's middle is (``x``, ``y``); the hull runs ``length`` from tip to tip and ``beam`` sets how deep it
    is. ``rider`` draws in the kayak's own coordinates, between the cockpit and the hull's near side."""
    _check_scale(scale)
    for name, value in (("length", length), ("beam", beam)):
        checks.positive(value, CutoutStoreError, f"{name} must be positive, got {value!r}")
    ink = cv.ink
    half = length / 2
    g = cv.group(parent, id, x=x, y=y, rotation=rotation, scaleX=scale, scaleY=scale)
    hull = cv.grad(f"{id}-hull", [(0, "#FAD65A"), (1, "#D99A1E")], (0, 0, 0, 1))
    cv.path(g, f"M{-half:.0f} 0 Q0 {-beam:.0f} {half:.0f} 0 Q0 {beam * 1.15:.0f} {-half:.0f} 0Z", hull, ink, 5)
    cv.ellipse(g, -130, -beam * 0.62, 260, beam * 0.62, "#2F3438", ink, 4)
    locations._call(rider, g)
    cv.path(g, f"M{-half:.0f} 0 Q0 {beam * 0.1:.0f} {half:.0f} 0 Q0 {beam * 1.15:.0f} {-half:.0f} 0Z", hull, ink, 5)
    cv.path(g, f"M{-half + 40:.0f} 4 Q0 {beam * 0.3:.0f} {half - 40:.0f} 4", stroke="#B97D14", sw=4)
    return g


@register(
    "prop",
    "paddle",
    style="cutout",
    summary="A double-bladed kayak paddle on a long black shaft",
    contract=family_contracts.contract('paddle'),
)
def paddle(
    cv: Canvas,
    parent,
    x=540,
    y=900,
    *,
    length: float = 1000,
    rotation: float = 0,
    scale: float = 1.0,
    id: str = "paddle",
):
    """The shaft's middle is (``x``, ``y``); it runs ``length`` from blade tip to blade tip."""
    _check_scale(scale)
    checks.positive(length, CutoutStoreError, f"length must be positive, got {length!r}")
    ink = cv.ink
    half = length / 2
    g = cv.group(parent, id, x=x, y=y, rotation=rotation, scaleX=scale, scaleY=scale)
    cv.rect(g, -8, -half + 90, 16, length - 180, "#23262A", ink, 3)
    for sign in (-1, 1):
        tip = sign * half
        neck = sign * (half - 170)
        d = f"M-12 {neck:.0f} Q-44 {tip * 0.92:.0f} -28 {tip:.0f} L28 {tip:.0f} Q44 {tip * 0.92:.0f} 12 {neck:.0f}Z"
        cv.path(g, d, "#E8622B", ink, 4)
    return g


@register(
    "prop",
    "life-ring",
    style="cutout",
    summary="A red and white life ring",
    contract=family_contracts.contract('life-ring'),
)
def life_ring(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, id: str = "life-ring"):
    """Its middle is (``x``, ``y``), 300 across at scale 1."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -150, -150, 300, 300, "#F7F5EC", ink, 5)
    for rotation in (45, 135, 225, 315):
        band = cv.group(g, f"{id}-band-{rotation}", rotation=rotation)
        cv.path(band, "M-46 -146 L46 -146 L34 -74 L-34 -74Z", "#D8352B", ink, 3.5)
    cv.ellipse(g, -72, -72, 144, 144, cv.clear, ink, 5)
    return g


@register(
    "prop",
    "dark-eyes",
    style="cutout",
    summary="A pair of eyes in total darkness, white with small pupils, blinking on cue",
    contract=family_contracts.contract('dark-eyes'),
)
def dark_eyes(
    cv: Canvas,
    parent,
    x=540,
    y=860,
    *,
    blinks: Sequence[tuple[float, float]] = (),
    glances: Sequence[tuple[float, float]] = ((0.0, 0.0),),
    scale: float = 1.0,
    id: str = "dark-eyes",
):
    """The point between the eyes is (``x``, ``y``); each of ``blinks`` closes them for that span, and ``glances``
    key the pupils' sideways shift ``(time, x)``."""
    _check_scale(scale)
    checks.spans(
        blinks, CutoutStoreError, lambda s: f"a blink is a rising span, got {s!r}", ordered="blinks run in order"
    )
    if not glances:
        raise CutoutStoreError("the eyes need at least one glance key")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    open_ = cv.group(g, f"{id}-open")
    start = 0.0
    spans = []
    for a, b in blinks:
        spans.append((start, a))
        start = b
    spans.append((start, 3600.0))
    cv.gate(open_, spans)
    for ex in (-92, 92):
        cv.ellipse(open_, ex - 58, -46, 116, 92, "#F7F5EC")
    pupils = cv.group(open_, f"{id}-pupils")
    cv.keys(pupils, "x", list(glances), hold=False)
    for ex in (-92, 92):
        cv.ellipse(pupils, ex - 16, -18, 32, 36, "#15161A")
    return g


@register(
    "prop",
    "shelf-goods",
    style="cutout",
    summary="Store shelves in a long run, packed with coloured boxes, sliding past on cue",
    contract=family_contracts.contract('shelf-goods'),
)
def shelf_goods(
    cv: Canvas,
    parent,
    y=200,
    *,
    width: float = 6000,
    drift: Sequence[tuple[float, float]] = ((0.0, 0.0),),
    seed: int = 17,
    id: str = "shelf-goods",
):
    """Four shelves from ``y`` down, ``width`` long, the run's x keyed by ``drift`` ``(time, x)``."""
    checks.positive(width, CutoutStoreError, f"width must be positive, got {width!r}")
    if not drift:
        raise CutoutStoreError("a run of shelves needs at least one drift key")
    rng = random.Random(seed)
    g = cv.group(parent, id)
    cv.keys(g, "x", list(drift), hold=False)
    for row in range(4):
        yy = y + 260 * row
        at = -200.0
        while at < width:
            w = rng.uniform(70, 150)
            tall = rng.uniform(120, 210)
            cv.rect(
                g,
                at,
                yy + 220 - tall,
                w,
                tall,
                rng.choice(("#D9694F", "#3F7F8C", "#F0C655", "#6F9A5A", "#ECE4D2", "#7A5C99")),
            )
            at += w + 10
        cv.rect(g, -200, yy + 220, width + 400, 24, "#8FA6A8")
    return g


@register(
    "location",
    "store-aisle",
    style="cutout",
    summary="A big-box store aisle: long shelves out of focus sliding past, a pale floor, strip lights",
    contract=family_contracts.contract('store-aisle'),
)
def store_aisle(
    cv: Canvas,
    parent,
    in_aisle: Slot = None,
    front: Slot = None,
    id: str = "location-store-aisle",
    shots=None,
    *,
    drift: Sequence[tuple[float, float]] = ((0.0, 0.0),),
    depth: float = 8.0,
):
    """``in_aisle`` draws whoever walks it, ``front`` what is nearest the lens. ``drift`` keys the shelves' x."""
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    cv.rect(g, -10, -10, 1100, 1940, "#E7E3D6")
    far = look.depth(cv, g, f"aisle-depth-{depth:g}", depth)
    cv.rect(far, -300, -300, 1680, 2400, cv.grad("aisle-back", [(0, "#F2EEE2"), (1, "#D5D1C2")], (0, 0, 0, 1)))
    shelf_goods(cv, far, 170, drift=drift, id=f"{id}-goods")
    cv.rect(g, -300, 1240, 1680, 900, cv.grad("aisle-floor", [(0, "#DAD6C8"), (1, "#B7B3A5")], (0, 0, 0, 1)))
    for k in range(4):
        cv.path(g, f"M{k * 300 - 120} 1240 L{k * 420 - 300} 1920", stroke="#A9A597", sw=2.5, opacity=0.5)
    signature.code(cv, g, 1000, 1262, 10, color="#7A7668", align="end")
    signature.cactus(cv, g, 96, 1300, 0.5)
    locations._call(in_aisle, g)
    locations._call(front, g)
    return g


@register(
    "prop",
    "light-switch",
    style="cutout",
    summary="A wall light switch on a white plate, whose rocker flips on cue",
    contract=family_contracts.contract('light-switch'),
)
def light_switch(
    cv: Canvas, parent, x=160, y=860, *, flips: Sequence[float] = (), scale: float = 1.0, id: str = "light-switch"
):
    """The plate's middle is (``x``, ``y``); the rocker starts down and changes over at each of ``flips``."""
    _check_scale(scale)
    if not all(checks.number(t) and t >= 0 for t in flips) or list(flips) != sorted(set(flips)):
        raise CutoutStoreError(f"flips are rising times, got {flips!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -70, -110, 140, 220, "#F4EFE0", ink, 4, radius=10)
    cv.rect(g, -30, -56, 60, 112, "#D5CFBE", ink, 3)
    rocker = cv.group(g, f"{id}-rocker", y=18.0)
    keys = [(0.0, 18.0)]
    down = True
    for t in flips:
        keys.append((t, 18.0 if down else -18.0))
        down = not down
        keys.append((t + 0.04, 18.0 if down else -18.0))
    cv.keys(rocker, "y", sorted(set(keys)), hold=False)
    cv.rect(rocker, -24, -30, 48, 60, "#FFFDF4", ink, 3)
    return g


@register(
    "prop",
    "long-receipt",
    style="cutout",
    summary="A till receipt printing out and running on down the frame, lines of items on it",
    contract=family_contracts.contract('long-receipt'),
)
def long_receipt(
    cv: Canvas,
    parent,
    x=540,
    y=1200,
    *,
    length: float = 700,
    printing: tuple[float, float] = (0.0, 1.0),
    id: str = "long-receipt",
):
    """It hangs from its top edge's middle at (``x``, ``y``), growing to ``length`` over the span ``printing``."""
    checks.positive(length, CutoutStoreError, f"length must be positive, got {length!r}")
    checks.spans([printing], CutoutStoreError, lambda s: f"a receipt prints over a rising span, got {s!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y)
    cv.keys(g, "scaleY", [(0.0, 0.0), (printing[0], 0.0), (printing[1], 1.0)], hold=False)
    cv.rect(g, -100, 0, 200, length, "#FFFDF4", ink, 3)
    rng = random.Random(23)
    at = 24.0
    while at < length - 16:
        cv.rect(g, -82, at, rng.uniform(60, 110), 8, "#8B8B85")
        cv.rect(g, 44, at, 38, 8, "#8B8B85")
        at += 26
    return g


@register(
    "prop",
    "checkout-lane",
    style="cutout",
    summary="A supermarket checkout counter across the foot of the frame, its black belt running",
    contract=family_contracts.contract('checkout-lane'),
)
def checkout_lane(cv: Canvas, parent, y=1130, *, running: tuple[float, float] = (0.0, 1.0), id: str = "checkout-lane"):
    """The counter's far edge is at ``y``; the belt's marks run for the span ``running``."""
    checks.spans([running], CutoutStoreError, lambda s: f"the belt runs for a rising span, got {s!r}")
    ink = cv.ink
    g = cv.group(parent, id)
    cv.rect(g, -300, y, 1680, 1200, cv.grad(f"{id}-steel", [(0, "#D7DDE1"), (1, "#9EA6AC")], (0, 0, 0, 1)), ink, 4)
    cv.rect(g, -300, y + 26, 1680, 130, "#23262A", ink, 4)
    marks = cv.group(g, f"{id}-marks")
    cv.keys(marks, "x", [(running[0], 0.0), (running[1], -(running[1] - running[0]) * 700.0)], hold=False)
    for k in range(60):
        cv.line(marks, -200 + k * 120, y + 30, -200 + k * 120, y + 152, "#3A3F45", 6)
    return g

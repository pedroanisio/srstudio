"""Cutout at the barber's: the mirror, the cape, and what the tools on the shelf are not supposed to be.

The set follows :mod:`srstudio.locations`: it draws in z-order, calls its slots at the right depth, gates its root
group before drawing, and places both signature marks. Its far plane is its own blurred group, so the cast, the
props and the marks stay sharp.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from . import _cutout_contracts, checks, locations, look, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

Slot = locations.Slot

__all__ = ["BARBER_MIRROR", "CutoutShopError", "barber_cape", "barbershop", "hair_fall", "hedge_trimmer", "lawnmower"]

BARBER_MIRROR = (100, 110, 880, 1150)  # x, y, width, height of the mirror's glass
SHADOW = "#2A2018"
CHROME = "#B9C2C8"
HAIR_GREY = "#C8CBD1"


class CutoutShopError(SrstudioError, ValueError):
    """A prop or a set asked for with arguments it cannot be drawn from."""


def _check_scale(scale) -> None:
    checks.positive(scale, CutoutShopError, f"scale must be a positive number, got {scale!r}")


@register(
    "prop",
    "barber-cape",
    style="cutout",
    summary="A pinstriped barber's cape, tied at the neck and falling wide over whoever sits under it",
    contract=_cutout_contracts.contract('barber-cape'),
)
def barber_cape(
    cv: Canvas,
    parent,
    x=540,
    y=900,
    *,
    width: float = 780,
    height: float = 460,
    spread: bool = False,
    id: str = "barber-cape",
):
    """Its collar's middle is (``x``, ``y``); it falls ``height`` below that and spreads to ``width``. A ``spread`` cape
    is the cloth flung open, a sheet with no collar, its top edge's middle at (``x``, ``y``)."""
    for name, value in (("width", width), ("height", height)):
        checks.positive(value, CutoutShopError, f"{name} must be positive, got {value!r}")
    ink = cv.ink
    half = width / 2
    g = cv.group(parent, id, x=x, y=y)
    if spread:
        cv.rect(g, -half, 0, width, height, "#2C3E50", ink, 5)
        for k in range(1, 12):
            cv.line(g, -half + k * width / 12, 6, -half + k * width / 12, height - 6, "#51667A", 3)
        return g
    d = f"M-46 0 Q{-half * 0.7:.1f} 40 {-half:.1f} {height:.1f} L{half:.1f} {height:.1f} Q{half * 0.7:.1f} 40 46 0Z"
    cv.path(g, d, "#2C3E50", ink, 5)
    for k in range(-3, 4):
        cv.line(g, k * 12, 16, k * width / 7, height - 4, "#51667A", 3)
    cv.rect(g, -58, -14, 116, 28, "#F4EFE0", ink, 4, radius=12)
    return g


@register(
    "prop",
    "hedge-trimmer",
    style="cutout",
    summary="A petrol hedge trimmer: a long toothed bar and a red motor body",
    contract=_cutout_contracts.contract('hedge-trimmer'),
)
def hedge_trimmer(
    cv: Canvas, parent, x=540, y=900, *, rotation: float = 0, scale: float = 1.0, id: str = "hedge-trimmer"
):
    """The motor's middle is (``x``, ``y``), the bar running 420 to the right at scale 1."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, rotation=rotation, scaleX=scale, scaleY=scale)
    cv.rect(g, 50, -14, 420, 28, CHROME, ink, 3.5)
    for k in range(12):
        cv.path(g, f"M{62 + k * 34} -14 l12 -18 l12 18 M{62 + k * 34} 14 l12 18 l12 -18", "#8E959C", ink, 2.5)
    cv.rect(g, -90, -46, 150, 92, "#C8352B", ink, 4, radius=18)
    cv.path(g, "M-70 -46 Q-70 -92 -10 -92 Q40 -92 40 -46", stroke=ink, sw=10)
    return g


@register(
    "prop",
    "lawnmower",
    style="cutout",
    summary="A push lawnmower from the side, green, with its handle up",
    contract=_cutout_contracts.contract('lawnmower'),
)
def lawnmower(cv: Canvas, parent, x=240, y=1200, *, scale: float = 1.0, facing: float = 1, id: str = "lawnmower"):
    """The wheels stand on (``x``, ``y``); its handle rises to the right, or to the left at ``facing`` -1."""
    if facing not in (1, -1):
        raise CutoutShopError(f"facing is 1 or -1, got {facing!r}")
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale * facing, scaleY=scale)
    cv.path(g, "M120 -60 L290 -330 L340 -330", stroke=ink, sw=11)
    cv.path(g, "M-150 -30 L-140 -120 Q-40 -170 100 -130 L150 -30Z", "#3C9A58", ink, 4.5)
    cv.rect(g, -60, -196, 90, 62, "#2F3438", ink, 4, radius=10)
    for wx, r in ((-100, 44), (110, 44)):
        cv.ellipse(g, wx - r, -2 * r, 2 * r, 2 * r, "#23262A", ink, 4)
        cv.ellipse(g, wx - 15, -r - 15, 30, 30, CHROME, ink, 3)
    return g


@register(
    "prop",
    "hair-fall",
    style="cutout",
    summary="Sheets of cut hair falling past the lens, out of focus, one sheet after another",
    contract=_cutout_contracts.contract('hair-fall'),
)
def hair_fall(
    cv: Canvas,
    parent,
    *,
    falls: Sequence[tuple[float, float]] = ((0.0, 0.6),),
    colour: str = HAIR_GREY,
    seed: int = 5,
    id: str = "hair-fall",
):
    """Each of ``falls`` is ``(start, seconds)``: a sheet crosses the frame from top to bottom in that time."""
    if not falls or any(not checks.number(a) or not checks.number(b) or b <= 0 for a, b in falls):
        raise CutoutShopError(f"a fall is a start and a positive length, got {falls!r}")
    rng = random.Random(seed)
    g = cv.group(parent, id)
    soft = look.depth(cv, g, f"{id}-depth", 5.0)
    for k, (start, seconds) in enumerate(falls):
        sheet = cv.group(soft, f"{id}-sheet-{k + 1}", x=rng.uniform(40, 700))
        cv.gate(sheet, [(start, start + seconds)])
        cv.keys(sheet, "y", [(0.0, -760.0), (start, -760.0), (start + seconds, 2000.0)], hold=False)
        w = rng.uniform(320, 520)
        for strand in range(26):
            at = rng.uniform(0, w)
            top = rng.uniform(0, 160)
            long = rng.uniform(420, 720)
            bend = rng.uniform(-70, 70)
            d = f"M{at:.0f} {top:.0f} Q{at + bend:.0f} {top + long / 2:.0f} {at - bend * 0.4:.0f} {top + long:.0f}"
            cv.path(sheet, d, stroke=colour if strand % 3 else "#9EA2A9", sw=rng.uniform(9, 20))
    return g


@register(
    "location",
    "barbershop",
    style="cutout",
    summary="A barber's seen through its mirror: a wide framed glass, the room reflected in it, and a counter of "
    "tools at the foot of the frame",
    contract=_cutout_contracts.contract('barbershop'),
    slots=('in_mirror', 'on_counter'),
)
def barbershop(
    cv: Canvas,
    parent,
    in_mirror: Slot = None,
    on_counter: Slot = None,
    id: str = "location-barbershop",
    shots=None,
    *,
    price: str = "TRIM $22",
    depth: float = 7.0,
):
    """``in_mirror`` draws the reflected people inside :data:`BARBER_MIRROR`, over the room reflected behind them, and
    must stay inside it: the callback is not clipped or mirrored automatically. ``on_counter`` draws on the shelf
    below the glass. ``price`` is the card stuck to the glass, drawn only when there is one."""
    if price:
        cv.require_font("the price card is set in it")
    ink = cv.ink
    x, y, w, h = BARBER_MIRROR
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    cv.rect(g, -10, -10, 1100, 1940, cv.grad("barber-wall", [(0, "#E9D7BC"), (1, "#CFB997")], (0, 0, 0, 1)))
    for k in range(-1, 14):  # the tiled wall around the glass
        cv.line(g, k * 90, 0, k * 90, 1920, "#BFA985", 2, opacity=0.5)
    glass = cv.group(g, f"{id}-glass")
    far = look.depth(cv, glass, f"barber-depth-{depth:g}", depth)
    cv.rect(far, x - 24, y - 24, w + 48, h + 48, cv.grad("barber-room", [(0, "#4F8A87"), (1, "#2E5F60")], (0, 0, 1, 1)))
    for k in range(4):
        cv.rect(far, x + 60 + k * 210, y + 80, 150, 210, "#F4EFE0", "#3B3126", 5)
    cv.rect(far, x - 24, y + h - 150, w + 48, 174, "#C7BCA4")
    locations._call(in_mirror, glass)
    cv.path(g, f"M{x + 30} {y + 20} L{x + 200} {y + 20} L{x + 30} {y + 420}Z", "#FFFFFF", opacity=0.14)
    cv.rect(g, x - 20, y - 20, w + 40, h + 40, cv.clear, "#7D5C3F", 40, radius=10)
    cv.rect(g, x - 42, y - 42, w + 84, h + 84, cv.clear, ink, 4, radius=16)
    if price:
        card = cv.group(g, f"{id}-price", x=x + w - 170, y=y + 60, rotation=3)
        cv.rect(card, -130, -56, 260, 112, "#FFFDF4", ink, 4)
        cv.text(card, f"{id}-price-text", price, -120, -38, 240, 76, 54, "#C8352B")
    top = cv.grad("barber-shelf", [(0, "#F4EFE0"), (1, "#C9C2B0")], (0, 0, 0, 1))
    cv.rect(g, -300, y + h + 24, 1680, 800, top, ink, 4)
    cv.rect(g, -300, y + h + 96, 1680, 60, "#7D5C3F", ink, 4)
    signature.code(cv, g, 1000, y + h + 50, 10, color="#5C625D", align="end")
    signature.cactus(cv, g, 110, y + h + 90, 0.55)
    locations._call(on_counter, g)
    return g

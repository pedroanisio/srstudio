"""The Stick style's odds and ends: things one reel needed and the next will want.

:func:`poster` is a wall poster with a line of lettering, big enough to cover what is on the wall behind it;
:func:`headset` goes on a standing figure's head. :func:`xray` fills the frame with a scanner's screen: what is in the
bag, in glowing false colour (:data:`XRAY_ITEMS`), under a moving scan line. :func:`plate` and :func:`spoon` are dinner,
:func:`robe` dresses a figure in a robe or a coat key by key, :func:`scan_belt` is the belt the bag goes through,
:func:`foil_parcel` what is in the bag and :func:`foil_note` the note on it, filling the frame. Everything is in frame
pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from . import checks
from .canvas import Canvas
from .registry import register
from .stick import HEAD_R, Gradient, RigKey, RigPose, StickDataError, _gate, _group, box, oval, paint, shape

__all__ = [
    "BELT_TOP",
    "NOTE_BOX",
    "XRAY_ITEMS",
    "foil_note",
    "foil_parcel",
    "headset",
    "plate",
    "poster",
    "robe",
    "scan_belt",
    "spoon",
    "xray",
]

PAPER, LETTER = "#f4f1ea", "#a8361c"
HEADSET, PAD = "#1f2430", "#3b4252"
SCREEN, GRID, ORGANIC, METAL, BONE, SCAN = "#07131f", "#10283a", "#ff9a3c", "#39a0ff", "#ffeccc", "#7dffb2"
CHINA, RIM, HEAPS = "#fbf8f0", "#c9c2b2", ("#c08a4a", "#7fa04e", "#e0b64f", "#b5573d")
STEEL, STEEL_DARK = "#aab2bb", "#5c646e"
FOIL, FOIL_LIGHT, FOIL_DARK = "#c6ccd2", "#eef1f4", "#8d959e"
NOTE, NOTE_INK = "#fff8dc", "#23252b"
BELT, BELT_LIGHT, TUNNEL, TUNNEL_DARK, FLAP = "#2a2e35", "#4a505a", "#c9d2d8", "#8f9aa5", "#3b4048"
FACETS = (  # the creases of crumpled foil: triangles in fractions of its box
    (0.08, 0.1, 0.34, 0.03, 0.22, 0.26), (0.34, 0.03, 0.62, 0.14, 0.42, 0.28), (0.62, 0.14, 0.92, 0.06, 0.8, 0.3),
    (0.05, 0.34, 0.26, 0.3, 0.14, 0.52), (0.42, 0.34, 0.66, 0.3, 0.58, 0.5), (0.72, 0.36, 0.95, 0.42, 0.8, 0.56),
    (0.04, 0.62, 0.3, 0.56, 0.2, 0.74), (0.34, 0.58, 0.56, 0.54, 0.46, 0.72), (0.62, 0.6, 0.9, 0.62, 0.72, 0.76),
    (0.06, 0.82, 0.3, 0.78, 0.18, 0.96), (0.4, 0.8, 0.66, 0.84, 0.5, 0.97), (0.7, 0.82, 0.96, 0.8, 0.86, 0.96),
)  # fmt: skip
ROBE_COLOUR, ROBE_EDGE = "#7f9fc4", "#5d7ea6"
GLOW = 16.0  # px of blur on the copy of a scanned object that makes it glow
BELT_TOP = 1200  # the belt's top: what stands on it has its feet here
BELT_X = (300.0, 1080.0)
TUNNEL_BOX = (340.0, 790.0, 290.0, 410.0)  # x, y, w, h of the scanner the belt runs through
NOTE_BOX = (110, 420, 860, 860)  # x, y, w, h of the note on the foil
XRAY_ITEMS: dict[str, tuple[tuple[str, str, str], ...]] = {  # paths around the origin: (path, fill, stroke)
    "chicken": (
        ("M -210 40 Q -230 -120 -40 -140 Q 150 -150 190 -30 Q 215 60 90 110 Q -120 170 -210 40 Z", ORGANIC, ORGANIC),
        ("M 150 40 Q 250 90 280 170 Q 300 215 262 214 Q 225 210 215 180 Q 170 130 90 100 Z", ORGANIC, ORGANIC),
        ("M -150 -30 Q -40 -110 120 -70 M -150 30 Q -30 -30 130 0 M -120 90 Q 0 40 110 60", "", BONE),
        ("M 130 60 L 240 170", "", BONE),
    ),
    "lasagna": (
        ("M -230 -80 L 230 -80 L 230 90 L -230 90 Z", ORGANIC, METAL),
        ("M -214 -40 Q -160 -60 -105 -40 T 0 -40 T 105 -40 T 214 -40", "", BONE),
        ("M -214 10 Q -160 -10 -105 10 T 0 10 T 105 10 T 214 10", "", BONE),
        ("M -214 55 Q -160 35 -105 55 T 0 55 T 105 55 T 214 55", "", BONE),
    ),
    "rolling-pin": (
        ("M -160 -38 L 160 -38 Q 176 -38 176 0 Q 176 38 160 38 L -160 38 Q -176 38 -176 0 Q -176 -38 -160 -38 Z", METAL,
         METAL),
        ("M -176 -12 L -270 -12 L -270 12 L -176 12 Z M 176 -12 L 270 -12 L 270 12 L 176 12 Z", METAL, METAL),
        ("M -280 0 L 280 0", "", BONE),
    ),
}  # fmt: skip


@register("prop", "stick-poster", tags=("wall", "poster", "sign", "font"))
def poster(cv: Canvas, parent, x: float, y: float, w: float, h: float, text: str, *, size: float = 92):
    """A paper poster at ``x, y`` of ``w`` by ``h`` with ``text`` in the caption font, balanced over up to 4 lines."""
    cv.require_font("the poster is lettered in it")
    if not text.strip():
        raise StickDataError("a poster needs lettering")
    if w <= 0 or h <= 0:
        raise StickDataError(f"a poster has a size, got {w} by {h}")
    g = _group(cv, parent)
    box(cv, g, x, y, w, h, PAPER, 5, r=8)
    pad = 30
    name = cv.uid("text")
    cv.assets.add_text(id=name, text=text, width=w - 2 * pad, height=h - 2 * pad, size=size, fontAsset=cv.font_asset,
                       weight=700, color=LETTER, align="center", verticalAlign="middle", wrap="balance",
                       lineHeight="1.08", maxLines=4)  # fmt: skip
    g.add_layer(id=cv.uid("layer"), asset=name, x=x + pad, y=y + pad)
    return g


@register("prop", "stick-headset", tags=("headset", "front-desk", "phone", "work"))
def headset(cv: Canvas, parent, x: float, y: float, *, flip: bool = False, scale: float = 1.0):
    """A headset on the head centred at ``x, y``: the band, the ear pad and the mic at the mouth, on the side the
    figure faces (``flip``: left). Draw it after the figure."""
    if scale <= 0:
        raise StickDataError(f"a headset's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=-scale if flip else scale, scaleY=scale)
    r = HEAD_R + 6
    shape(cv, g, f"M {-r} -6 A {r} {r} 0 0 1 {r} -6", sw=11, stroke=HEADSET)
    oval(cv, g, -r - 16, -36, 34, 74, PAD)
    shape(cv, g, f"M {-r} 34 Q -74 78 22 62", sw=7, stroke=HEADSET)
    oval(cv, g, 14, 52, 24, 20, HEADSET)
    return g


def _scanned(cv: Canvas, parent, name: str, x: float, y: float, scale: float) -> None:
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    for path, fill, stroke in XRAY_ITEMS[name]:
        shape(cv, g, path, f"{fill}55" if fill else None, 7, stroke=stroke)


@register("prop", "stick-xray", tags=("airport", "security", "scanner", "insert", "fullscreen", "effect"))
def xray(cv: Canvas, parent, end: float, items: Sequence[tuple[str, float, float, float]]):
    """A scanner's screen filling the frame: ``items`` (a name from :data:`XRAY_ITEMS`, x, y, scale) in false colour,
    each over a blurred copy of itself so that it glows, and a scan line that crosses the screen once in ``end``."""
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"a scan lasts some seconds, got {end!r}")
    if not items:
        raise StickDataError("a scan shows at least one thing")
    for name, *_ in items:
        if name not in XRAY_ITEMS:
            raise StickDataError(f"unknown scanned item {name!r}; known: {', '.join(XRAY_ITEMS)}")
    g = _group(cv, parent)
    box(cv, g, 0, 0, cv.width, cv.height, SCREEN)
    for at in range(120, cv.width, 120):
        shape(cv, g, f"M {at} 0 L {at} {cv.height}", sw=2, stroke=GRID)
    for at in range(120, cv.height, 120):
        shape(cv, g, f"M 0 {at} L {cv.width} {at}", sw=2, stroke=GRID)
    glow = _group(cv, g, effects=cv.effect("xray-glow", "blur", radius=GLOW))
    for name, x, y, scale in items:
        _scanned(cv, glow, name, x, y, scale)
    for name, x, y, scale in items:
        _scanned(cv, g, name, x, y, scale)
    line = box(cv, g, 0, 0, cv.width, 8, SCAN, opacity=0.7)
    cv.keys(line, "y", [(0.0, 0.0), (end, float(cv.height))], kind="linear")
    return g


@register("prop", "stick-plate", tags=("home", "food", "dinner", "plate"))
def plate(cv: Canvas, parent, x: float, y: float, *, heap: int = 2, scale: float = 1.0):
    """A dinner plate seen from the side, standing on ``x, y``, under ``heap`` (0 to 3) tiers of food."""
    if heap not in range(4):
        raise StickDataError(f"a heap has 0 to 3 tiers, got {heap!r}")
    if scale <= 0:
        raise StickDataError(f"a plate's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    for tier in range(heap):
        wide, tall, lift = 170 - 40 * tier, 96, 8 + 70 * tier
        shape(cv, g, f"M {-wide} {-lift} Q 0 {-lift - 2 * tall} {wide} {-lift} Z", HEAPS[tier], 5, stroke=cv.ink)
        oval(cv, g, -wide * 0.5, -lift - 44, 46, 34, HEAPS[(tier + 1) % len(HEAPS)])
        oval(cv, g, wide * 0.2, -lift - 62, 38, 30, HEAPS[(tier + 2) % len(HEAPS)])
    shape(cv, g, "M -200 -14 Q -190 8 -130 12 L 130 12 Q 190 8 200 -14 Z", CHINA, 5, stroke=cv.ink)
    shape(cv, g, "M -200 -14 L 200 -14", sw=7, stroke=RIM)
    return g


@register("prop", "stick-spoon", tags=("home", "food", "kitchen", "spoon"))
def spoon(cv: Canvas, parent, grip: tuple[float, float], bowl: tuple[float, float], *, full: bool = False):
    """A big serving spoon from the hand at ``grip`` to its bowl at ``bowl``, with a helping in it if ``full``."""
    g = _group(cv, parent)
    shape(cv, g, f"M {grip[0]} {grip[1]} L {bowl[0]} {bowl[1]}", sw=13, stroke=STEEL_DARK)
    oval(cv, g, bowl[0] - 56, bowl[1] - 32, 112, 64, STEEL)
    if full:
        oval(cv, g, bowl[0] - 44, bowl[1] - 42, 88, 54, HEAPS[0])
    return g


def _robed(cv: Canvas, parent, pose: RigPose, colour: str, belt: str) -> None:
    (nx, ny), (hx, hy) = pose.neck, pose.hip
    shoulder = (nx - 4, ny + 34)
    for i, width in ((0, 44), (1, 48)):
        elbow, hand = pose.elbows[i], pose.hands[i]
        cuff = (elbow[0] + (hand[0] - elbow[0]) * 0.75, elbow[1] + (hand[1] - elbow[1]) * 0.75)
        sleeve = f"M {shoulder[0]} {shoulder[1]} L {elbow[0]} {elbow[1]} L {cuff[0]:.1f} {cuff[1]:.1f}"
        shape(cv, parent, sleeve, sw=width + 10, stroke=cv.ink)
        shape(cv, parent, sleeve, sw=width, stroke=colour)
    hem = hy + 250
    shape(cv, parent, f"M {nx - 62} {ny + 14} L {nx + 62} {ny + 14} L {hx + 112} {hem} L {hx - 112} {hem} Z", colour, 6,
          stroke=cv.ink)  # fmt: skip
    shape(cv, parent, f"M {nx - 40} {ny + 12} L {hx + 6} {hy - 130} L {nx + 40} {ny + 12}", sw=6, stroke=belt)
    shape(cv, parent, f"M {hx - 86} {hy - 10} L {hx + 86} {hy - 10}", sw=14, stroke=belt)


@register("prop", "stick-robe", tags=("clothes", "robe", "coat", "home"))
def robe(cv: Canvas, parent, keys: Sequence[RigKey], end: float, poses: Mapping[str, RigPose], *,
         at: tuple[float, float] = (0, 0), scale: float = 1.0, flip: bool = False, colour: str = ROBE_COLOUR,
         belt: str = ROBE_EDGE):  # fmt: skip
    """A robe or a long coat over a figure: draw it after :func:`srstudio.stick.rig` with the same ``keys``, ``end``,
    ``poses``, ``at``, ``scale`` and ``flip``, and it holds each pose as the figure does. The head stays clear of it."""
    if scale <= 0:
        raise StickDataError(f"a robe's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=at[0], y=at[1], scaleX=-scale if flip else scale, scaleY=scale)
    for i, key in enumerate(keys):
        one = _group(cv, g)
        _robed(cv, one, poses[key.pose], colour, belt)
        _gate(cv, one, key.start, keys[i + 1].start if i + 1 < len(keys) else end, end)
    return g


@register("prop", "stick-scan-belt", tags=("airport", "security", "scanner", "belt"))
def scan_belt(cv: Canvas, parent):
    """The security belt across the frame from the left of its scanner to the right edge, its top at
    :data:`BELT_TOP`: drawn over the officer behind it, so it hides his legs. The scanner's hood is at the left."""
    g = _group(cv, parent)
    x0, x1 = BELT_X
    box(cv, g, x0, BELT_TOP, x1 - x0, 40, BELT)
    for x in range(int(x0) + 20, int(x1), 60):
        oval(cv, g, x, BELT_TOP + 8, 24, 24, BELT_LIGHT)
    box(cv, g, x0, BELT_TOP + 40, x1 - x0, 500, STEEL_DARK, 4)
    tx, ty, tw, th = TUNNEL_BOX
    box(cv, g, tx, ty, tw, th, TUNNEL, 6, r=26)
    box(cv, g, tx + 26, ty + 100, tw - 52, th - 100, TUNNEL_DARK)
    for k in range(6):
        box(cv, g, tx + 30 + k * 40, ty + 104, 30, 210, FLAP)
    return g


def _crumple(cv: Canvas, parent, x: float, y: float, w: float, h: float) -> None:
    box(cv, parent, x, y, w, h, FOIL, 6, r=min(w, h) * 0.18)
    for k, (ax, ay, bx, by, cx, cy) in enumerate(FACETS):
        corners = " L ".join(f"{x + w * u:.1f} {y + h * v:.1f}" for u, v in ((ax, ay), (bx, by), (cx, cy)))
        shape(cv, parent, f"M {corners} Z", FOIL_LIGHT if k % 2 else FOIL_DARK, opacity=0.7)


@register("prop", "stick-foil-parcel", tags=("food", "foil", "leftovers", "parcel"))
def foil_parcel(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0):
    """A crumpled foil parcel of leftovers centred on ``x, y``."""
    if scale <= 0:
        raise StickDataError(f"a parcel's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    _crumple(cv, g, -90, -60, 180, 120)
    return g


@register("prop", "stick-foil-note", tags=("food", "foil", "note", "insert", "fullscreen", "font"))
def foil_note(cv: Canvas, parent, text: str, *, size: float = 104):
    """The frame given over to a sheet of foil and the note taped to it, lettered ``text``, up to five lines."""
    cv.require_font("the note is lettered in it")
    if not text.strip():
        raise StickDataError("a note needs words")
    g = _group(cv, parent)
    box(cv, g, 0, 0, cv.width, cv.height, paint(cv, Gradient("foil", ((0, FOIL_LIGHT), (1, FOIL_DARK)), 0, 0, 0, 1920)))
    _crumple(cv, g, -60, -60, cv.width + 120, cv.height + 120)
    x, y, w, h = NOTE_BOX
    box(cv, g, x + 10, y + 12, w, h, FOIL_DARK)
    box(cv, g, x, y, w, h, NOTE, 5)
    box(cv, g, x + w / 2 - 110, y - 34, 220, 66, FOIL_LIGHT, opacity=0.75)
    pad = 60
    name = cv.uid("text")
    cv.assets.add_text(id=name, text=text, width=w - 2 * pad, height=h - 2 * pad, size=size, fontAsset=cv.font_asset,
                       weight=700, color=NOTE_INK, align="center", verticalAlign="middle", wrap="balance",
                       lineHeight="1.14", maxLines=5)  # fmt: skip
    g.add_layer(id=cv.uid("layer"), asset=name, x=x + pad, y=y + pad)
    return g

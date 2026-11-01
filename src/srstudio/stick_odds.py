"""The Stick style's odds and ends: things one reel needed and the next will want.

:func:`poster` is a wall poster with a line of lettering, big enough to cover what is on the wall behind it;
:func:`headset` goes on a standing figure's head. :func:`xray` fills the frame with a scanner's screen: what is in the
bag, in glowing false colour (:data:`XRAY_ITEMS`), under a moving scan line. :func:`plate` and :func:`spoon` are dinner,
:func:`robe` dresses a figure in a robe or a coat key by key, :func:`scan_belt` is the belt the bag goes through,
:func:`foil_parcel` what is in the bag and :func:`foil_note` the note on it, filling the frame. Everything is in frame
pixels of the 1080 × 1920 Stick frame and nothing is random, so a shot redraws the same. :func:`aisle` looks down a
plane's aisle in one-point perspective and :func:`queue` stands a line of people in it who can all turn round at once;
:func:`book` and :func:`duffel` are what a passenger carries. :func:`wheelie_bin`, :func:`trash_truck`, :func:`slipper`
and :func:`sparks` are trash day. :func:`planks`, :func:`wardrobe`, :func:`drill`, :func:`screws` and
:func:`manual_page` are flat-pack furniture, from the pile to the manual's last page (:data:`MANUAL_DRAWINGS`);
:func:`caller` is a phone ringing with a name on it. :func:`double_take` is not a drawing: it is the keys of a look, a
look away and a snap back, for any figure in any shot. :func:`carton` is a plain delivery box and :func:`receipt` a long
till receipt on a hand, which can unroll to the floor.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from . import checks, signature
from .canvas import Canvas
from .registry import register
from .stick import HEAD_R, Face, Gradient, RigKey, RigPose, StickDataError, _gate, _group, box, oval, paint, shape

__all__ = [
    "BELT_TOP",
    "MANUAL_DRAWINGS",
    "NOTE_BOX",
    "WARDROBE_STAGES",
    "XRAY_ITEMS",
    "aisle",
    "book",
    "caller",
    "carton",
    "double_take",
    "drill",
    "duffel",
    "foil_note",
    "foil_parcel",
    "headset",
    "manual_page",
    "planks",
    "plate",
    "poster",
    "queue",
    "receipt",
    "robe",
    "scan_belt",
    "screws",
    "slipper",
    "sparks",
    "spoon",
    "trash_truck",
    "wardrobe",
    "wheelie_bin",
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
COVER, PAGES, DUFFEL, DUFFEL_DARK = "#8a3f5a", "#fbf8f0", "#55704f", "#3f5439"
HULL, HULL_LOW, CARPET, BIN_DOOR, SEAT, SEAT_LIGHT = "#efe9dc", "#d8cdb8", "#5b4f6b", "#f6f2e8", "#2f4a6d", "#3f5f88"
SKIN, HAIRS, COATS = (
    "#f0e9df",
    ("#23252b", "#6b4a2f", "#a9a39a", "#c98f3f"),
    ("#7f9fc4", "#c0453b", "#6b5a48", "#55704f"),
)
TROUSERS = "#34343e"
HORIZON = 620  # the aisle's vanishing point on the frame's height
AISLE_ROWS = 12
RECEDE = 0.24  # how fast the rows shrink: each is 1 / (1 + RECEDE * depth) the near one
BIN_BODY, BIN_LID, TRUCK_BODY, TRUCK_DARK, CAB, TYRE = "#3f6b52", "#2f5240", "#6f8f5a", "#3b4a35", "#f0ece2", "#23252b"
GLASS, PLUSH, SPARK, SPARK_CORE = "#bcd8e6", "#c98fa2", "#ffb400", "#fff4c2"
OAK, OAK_DARK, OAK_LIGHT, CHIPBOARD, CARDBOARD = "#c79a62", "#94693a", "#dcb782", "#e8dcc3", "#c8a877"
TOOL, TOOL_DARK, MANUAL_PAPER, RING_GREEN, RING_RED = "#d9622b", "#3a3f47", "#fbfaf5", "#39a85b", "#d0453b"
WARDROBE_STAGES = ("half", "done")
WARDROBE_W, WARDROBE_H = 410.0, 860.0
MANUAL_DRAWINGS = ("smiling", "argument", "crossed", "sofa", "suitcase", "hug", "bun")
TRUCK_LENGTH, CAB_WINDOW = 1000.0, (830.0, -400.0, 130.0, 130.0)  # x, y, w, h from the truck's rear wheel on the road
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


CARTON, CARTON_TOP, CARTON_SIDE, CARTON_TAPE = "#c49a66", "#d9b583", "#a67f50", "#e5cfa6"
TILL_PAPER, TILL_RULE = "#fbf8f0", "#b9b4a8"
TILL_ROW = 34  # px between a receipt's scrawled rows
FLOOR_SHADOW = "#3a2a1c"


@register("prop", "stick-box", tags=("box", "parcel", "delivery", "home"))
def carton(
    cv: Canvas, parent, x: float, y: float, *, w: float = 190, h: float = 150, flip: bool = False, scale: float = 1.0
):
    """A plain delivery carton standing on the floor at ``x, y``, the middle of its foot: a taped front, a top and a
    shaded side, with a contact shadow. It carries no lettering and no logo. ``flip`` puts the side on the left."""
    if not (w > 0 and h > 0):
        raise StickDataError(f"a carton's size is positive, got {w!r} by {h!r}")
    if scale <= 0:
        raise StickDataError(f"a carton's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=-scale if flip else scale, scaleY=scale)
    deep = 0.16 * w
    oval(cv, g, -w * 0.6, -12, w * 1.3, 26, FLOOR_SHADOW, opacity=0.28)
    shape(cv, g, f"M {w / 2} {-h} L {w / 2 + deep} {-h - deep * 0.6} L {w / 2 + deep} {-deep * 0.6} L {w / 2} 0 Z",
          CARTON_SIDE, 5, stroke=cv.ink)  # fmt: skip
    top = -h - deep * 0.6
    shape(cv, g, f"M {-w / 2} {-h} L {-w / 2 + deep} {top} L {w / 2 + deep} {top} L {w / 2} {-h} Z", CARTON_TOP, 5,
          stroke=cv.ink)  # fmt: skip
    cv.rect(g, -w / 2, -h, w, h, CARTON, stroke=cv.ink, sw=5, radius=0)
    box(cv, g, -w * 0.07, -h, w * 0.14, h * 0.34, CARTON_TAPE)
    shape(cv, g, f"M {-w * 0.07 + deep * 0.5} {-h - deep * 0.3} L {w * 0.07 + deep * 0.5} {-h - deep * 0.3} "
          f"L {w * 0.07} {-h} L {-w * 0.07} {-h} Z", CARTON_TAPE)  # fmt: skip
    return g


@register("prop", "stick-receipt", tags=("receipt", "paper", "money", "shop"))
def receipt(
    cv: Canvas, parent, x: float, y: float, length: float, *, w: float = 74, unroll: tuple[float, float] | None = None
):
    """A long till receipt hanging from ``x, y``, the middle of its top edge, ``length`` px down to a curl. Its rows are
    scrawled, so no figure reads. ``unroll`` is the span of seconds it runs out from nothing, about its top."""
    if not length > 0:
        raise StickDataError(f"a receipt's length is positive, got {length!r}")
    if not w > 0:
        raise StickDataError(f"a receipt's width is positive, got {w!r}")
    if unroll is not None and not 0 <= unroll[0] < unroll[1]:
        raise StickDataError(f"a receipt unrolls over a rising span of seconds, got {unroll!r}")
    g = _group(cv, parent, x=x, y=y, anchorX=0, anchorY=0)
    cv.rect(g, -w / 2, 0, w, length, TILL_PAPER, stroke=cv.ink, sw=4, radius=0)
    for k in range(1, int((length - TILL_ROW) // TILL_ROW)):
        row = k * TILL_ROW
        reach = w * (0.28 if k % 3 else 0.12)
        shape(cv, g, f"M {-w * 0.34} {row} L {reach} {row}", sw=4, stroke=TILL_RULE)
        shape(cv, g, f"M {w * 0.22} {row} L {w * 0.36} {row}", sw=4, stroke=TILL_RULE)
    left, right, foot = -w / 2, w / 2, length
    curl = f"M {left} {foot} Q 0 {foot + 26} {right} {foot} Q {w * 0.2} {foot - 16} {left} {foot} Z"
    shape(cv, g, curl, TILL_RULE, 4, stroke=cv.ink)
    if unroll is not None:
        cv.keys(g, "scaleY", [(unroll[0], 0.02), (unroll[1], 1.0)], kind="sine-out")
    return g


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


def _depth(row: int) -> float:
    return 1 / (1 + RECEDE * row)


def _sx(side: int, out: float, depth: float) -> float:
    return 540 + side * out * depth


@register("location", "stick-aisle", tags=("airport", "plane", "cabin", "aisle", "perspective", "travel"))
def aisle(cv: Canvas, parent):
    """A plane's aisle from the back of the cabin in one-point perspective: the hull, the bins on both sides and the
    seat rows shrinking toward the bulkhead at :data:`HORIZON`. Stand people in it with :func:`queue`. The code sits on
    the floor and the cactus on the nearest seat (ADR 0001)."""
    g = _group(cv, parent)
    box(cv, g, 0, 0, cv.width, cv.height, HULL)
    far = _depth(AISLE_ROWS)
    fl, fr = _sx(-1, 300, far), _sx(1, 300, far)
    box(cv, g, fl, HORIZON - 420 * far, fr - fl, 1300 * far, HULL_LOW, 4)
    floor = HORIZON + 1300
    shape(cv, g, f"M {_sx(-1, 300, 1)} {floor} L {fl} {HORIZON + 880 * far} L {fr} {HORIZON + 880 * far} "
                 f"L {_sx(1, 300, 1)} {floor} Z", CARPET)  # fmt: skip
    for side in (-1, 1):
        edge, near = _sx(side, 300, far), _sx(side, 620, 1)
        shape(cv, g, f"M {near} 0 L {edge} {HORIZON - 420 * far} L {edge} {HORIZON - 190 * far} "
                     f"L {_sx(side, 340, 1)} {HORIZON - 190} L {near} {HORIZON - 190} Z",
              BIN_DOOR, 4, stroke="#b9ae98")  # fmt: skip
    for row in range(AISLE_ROWS, -1, -1):
        depth = _depth(row)
        for side in (-1, 1):
            inner, outer = sorted((_sx(side, 240, depth), _sx(side, 760, depth)))
            top, base = HORIZON + 180 * depth, HORIZON + 1300 * depth
            box(cv, g, inner, top, outer - inner, base - top, SEAT, 3, r=40 * depth)
            box(cv, g, inner + 26 * depth, top + 24 * depth, outer - inner - 52 * depth, 150 * depth, SEAT_LIGHT)
            x = _sx(side, 300, depth)
            shape(cv, g, f"M {x} {HORIZON - 190 * depth} L {_sx(side, 620, depth)} {HORIZON - 190 * depth}", sw=4,
                  stroke="#b9ae98")  # fmt: skip
    signature.cactus(cv, g, 90, 1640, scale=0.5)
    signature.code(cv, g, 40, 1880, 9, color="#8a7f99")
    return g


def _passenger(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    depth: float,
    hair: str,
    coat: str,
    turn: float,
    end: float,
    *,
    legs: bool = False,
):
    r = 120 * depth
    wide, base, top = 190 * depth, y + 420 * depth, y + 100 * depth
    if legs:
        for side in (-1, 1):
            leg = x + side * wide * 0.5
            box(cv, parent, leg - 44 * depth, base - 20 * depth, 88 * depth, 210 * depth, TROUSERS, 4)
            box(cv, parent, leg - 54 * depth, base + 170 * depth, 108 * depth, 40 * depth, cv.ink, r=14 * depth)
    shape(cv, parent, f"M {x - wide} {base} Q {x - wide + 10 * depth} {top} {x} {top} "
                      f"Q {x + wide - 10 * depth} {top} {x + wide} {base} Z", coat, 4, stroke=cv.ink)  # fmt: skip
    oval(cv, parent, x - r, y - r, 2 * r, 2 * r, SKIN, sw=4)
    back = _group(cv, parent)
    shape(cv, back, f"M {x - r} {y} A {r} {r} 0 0 1 {x + r} {y} Q {x} {y + r * 1.3} {x - r} {y} Z", hair)
    _gate(cv, back, 0, turn, end)
    face = _group(cv, parent)
    for eye in (-0.36, 0.36):
        oval(cv, face, x + eye * r - r * 0.13, y - r * 0.2, r * 0.26, r * 0.26, cv.ink)
    shape(cv, face, f"M {x - r * 0.26} {y + r * 0.46} L {x + r * 0.26} {y + r * 0.46}", sw=4 * max(depth, 0.5),
          stroke=cv.ink)  # fmt: skip
    _gate(cv, face, turn, end, end)


@register("prop", "stick-queue", tags=("airport", "plane", "cabin", "crowd", "people"))
def queue(cv: Canvas, parent, end: float, *, turn: float, rows: int = AISLE_ROWS, legs: bool = False):
    """A line of ``rows`` pairs of people down :func:`aisle`, backs to the viewer, who all turn to face them at
    ``turn`` seconds, with ``legs`` under their coats for a shot that shows the floor. Fixed hair and coats, so a shot
    redraws the same."""
    if rows not in range(1, AISLE_ROWS + 1):
        raise StickDataError(f"the aisle holds 1 to {AISLE_ROWS} rows, got {rows!r}")
    if not 0 <= turn <= end:
        raise StickDataError(f"they turn inside the shot of {end} s, got {turn!r}")
    g = _group(cv, parent)
    for row in range(rows, 0, -1):
        depth = _depth(row)
        for side in (-1, 1):
            n = 2 * row + (side > 0)
            x = 540 + side * (112 - 14 * (row % 3)) * depth
            y = HORIZON + (760 + 50 * (n % 3)) * depth
            hair, coat = HAIRS[n % len(HAIRS)], COATS[(n // 2) % len(COATS)]
            _passenger(cv, g, x, y, depth, hair, coat, turn, end, legs=legs)
    return g


@register("prop", "stick-book", tags=("book", "reading", "hand-prop"))
def book(cv: Canvas, parent, x: float, y: float, *, shut: bool = False, scale: float = 1.0, colour: str = COVER):
    """A paperback centred on ``x, y``, seen from its ``colour`` cover: open and held up to read, or ``shut``."""
    if scale <= 0:
        raise StickDataError(f"a book's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    if shut:
        box(cv, g, -44, -62, 88, 124, colour, 5, r=6)
        return g
    box(cv, g, -92, -66, 184, 8, PAGES, 3)
    shape(cv, g, "M 0 -62 L -96 -72 L -96 62 L 0 66 Z", colour, 5, stroke=cv.ink)
    shape(cv, g, "M 0 -62 L 96 -72 L 96 62 L 0 66 Z", colour, 5, stroke=cv.ink)
    return g


@register("prop", "stick-duffel", tags=("bag", "travel", "hand-prop"))
def duffel(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0, colour: str = DUFFEL):
    """A soft duffel bag centred on ``x, y``, its strap up, in ``colour``."""
    if scale <= 0:
        raise StickDataError(f"a bag's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    shape(cv, g, "M -60 -40 Q 0 -150 60 -40", sw=8, stroke=cv.ink)
    box(cv, g, -120, -56, 240, 112, colour, 5, r=46)
    shape(cv, g, "M -92 -14 L 92 -14", sw=6, stroke=DUFFEL_DARK)
    return g


def double_take(at: float, pose: str, first: Face, away: Face, second: Face, *, step: float = 0.45) -> list[RigKey]:
    """A double take from ``at`` seconds, holding ``pose``: ``first`` for ``step`` seconds, ``away`` for as long, then
    ``second``, the one that lands. Extend a figure's keys with it; it is timing, so it works in any shot."""
    if not (checks.number(step) and step > 0):
        raise StickDataError(f"a double take's step is positive, got {step!r}")
    if at < 0:
        raise StickDataError(f"a double take starts in the shot, got {at!r}")
    return [RigKey(at, pose, first), RigKey(at + step, pose, away), RigKey(at + 2 * step, pose, second)]


@register("prop", "stick-wheelie-bin", tags=("trash", "street", "bin", "home"))
def wheelie_bin(cv: Canvas, parent, x: float, y: float, *, wheels: int = 2, lean: float = 0.0, scale: float = 1.0):
    """A wheeled trash bin standing on ``x, y``, its handle at the top right, tipped ``lean`` degrees onto its wheels.
    ``wheels`` is how many it still has: with none it stands on its corner."""
    if wheels not in (0, 1, 2):
        raise StickDataError(f"a bin has 0 to 2 wheels, got {wheels!r}")
    if scale <= 0:
        raise StickDataError(f"a bin's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale, rotation=lean)
    shape(cv, g, "M -92 -300 L 92 -300 L 76 -24 L -76 -24 Z", BIN_BODY, 5, stroke=cv.ink)
    box(cv, g, -108, -326, 216, 30, BIN_LID, 5, r=8)
    box(cv, g, 92, -330, 40, 16, cv.ink, r=6)
    for k in range(wheels):
        oval(cv, g, 40 - k * 120, -44, 58, 58, TYRE)
    return g


@register("prop", "stick-trash-truck", tags=("trash", "street", "truck", "vehicle"))
def trash_truck(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0):
    """A trash truck heading right, its rear on ``x`` and its wheels on the road at ``y``: the hopper, the body and the
    cab, :data:`TRUCK_LENGTH` long. The cab's window is :data:`CAB_WINDOW`, so a driver can be drawn in it."""
    if scale <= 0:
        raise StickDataError(f"a truck's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    box(cv, g, 0, -420, 300, 340, TRUCK_DARK, 5, r=10)
    box(cv, g, 34, -380, 200, 200, "#14181c", r=8)
    box(cv, g, 260, -540, 520, 460, TRUCK_BODY, 5, r=14)
    for rib in range(340, 780, 110):
        shape(cv, g, f"M {rib} -520 L {rib} -100", sw=6, stroke=TRUCK_DARK)
    nose = TRUCK_LENGTH
    shape(cv, g, f"M 780 -440 L 930 -440 Q {nose} -420 {nose} -300 L {nose} -80 L 780 -80 Z", CAB, 5,
          stroke=cv.ink)  # fmt: skip
    cx, cy, cw, ch = CAB_WINDOW
    box(cv, g, cx, cy, cw, ch, GLASS, 5, r=10)
    box(cv, g, -20, -90, TRUCK_LENGTH + 40, 30, cv.ink, r=8)
    for wheel in (150, 620, 870):
        oval(cv, g, wheel - 78, -128, 156, 156, TYRE)
        oval(cv, g, wheel - 30, -80, 60, 60, STEEL)
    return g


@register("prop", "stick-slipper", tags=("clothes", "home", "slipper", "shoe"))
def slipper(cv: Canvas, parent, x: float, y: float, *, scale: float = 1.0):
    """One bedroom slipper centred on ``x, y``, toe to the right; key the group to throw it."""
    if scale <= 0:
        raise StickDataError(f"a slipper's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    shape(cv, g, "M -70 22 Q -74 -12 -30 -10 L 26 -28 Q 76 -24 78 22 Z", PLUSH, 5, stroke=cv.ink)
    shape(cv, g, "M -78 26 L 84 26", sw=9, stroke=cv.ink)
    return g


@register("prop", "stick-sparks", tags=("effect", "sparks", "scrape", "metal"))
def sparks(cv: Canvas, parent, x: float, y: float, end: float, *, rate: float = 12.0, scale: float = 1.0):
    """A spray of sparks thrown back from ``x, y``, redrawn ``rate`` times a second for ``end`` seconds: two sprays turn
    about, so it flickers the same on every render."""
    if not (checks.number(end) and end > 0):
        raise StickDataError(f"sparks last some seconds, got {end!r}")
    if not (checks.number(rate) and rate > 0):
        raise StickDataError(f"sparks flicker a positive rate, got {rate!r}")
    if scale <= 0:
        raise StickDataError(f"sparks' scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    sprays = (((-120, -40), (-70, -90), (-160, -14), (-30, -60)), ((-90, -70), (-150, -36), (-44, -96), (-110, -10)))
    step = 1 / rate
    for which, spray in enumerate(sprays):
        one = _group(cv, g)
        for dx, dy in spray:
            shape(cv, one, f"M 0 0 L {dx} {dy}", sw=6, stroke=SPARK)
            shape(cv, one, f"M {dx * 0.4} {dy * 0.4} L {dx * 0.8} {dy * 0.8}", sw=3, stroke=SPARK_CORE)
        spans = [(k * step, min((k + 1) * step, end)) for k in range(which, int(end / step) + 1, 2) if k * step < end]
        cv.gate(one, spans)
    return g


@register("prop", "stick-planks", tags=("furniture", "flat-pack", "home", "planks"))
def planks(cv: Canvas, parent, x: float, floor: float, *, scale: float = 1.0):
    """What a flat-pack is before it is anything: panels leaning on the wall and the flat box they came in, its left
    edge at ``x`` and its foot on ``floor``."""
    if scale <= 0:
        raise StickDataError(f"a pile's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=floor, scaleX=scale, scaleY=scale)
    for lean, height, colour in ((150, 830, OAK_DARK), (210, 880, OAK), (270, 760, OAK_LIGHT), (320, 690, CHIPBOARD)):
        shape(cv, g, f"M {lean} 0 L {lean + 34} {-height} L {lean + 96} {-height + 6} L {lean + 62} 0 Z", colour, 5,
              stroke=cv.ink)  # fmt: skip
    box(cv, g, 10, -110, 400, 110, CARDBOARD, 5, r=4)
    shape(cv, g, "M 10 -110 L -36 -176 L 214 -176 L 214 -110", CARDBOARD, 5, stroke=cv.ink)
    shape(cv, g, "M 30 -56 L 390 -56", sw=9, stroke=OAK_DARK)
    for i, dx in enumerate((-90, -40, 8)):  # a few loose boards on the floor
        box(cv, g, dx, 18 + i * 26, 250 - i * 40, 22, OAK if i % 2 else OAK_LIGHT, 4, r=4)
    return g


@register("prop", "stick-wardrobe", tags=("furniture", "flat-pack", "home", "wardrobe", "stages", "font"))
def wardrobe(cv: Canvas, parent, x: float, floor: float, stage: str = "done", *, scale: float = 1.0):
    """A flat-pack wardrobe with its left edge at ``x`` and its foot on ``floor``: ``"half"`` up, with no top and its
    right door hung backwards, raw side out with the hinges showing and the label meant for the inside, or ``"done"``,
    two doors shut and standing."""
    if stage not in WARDROBE_STAGES:
        raise StickDataError(f"a wardrobe's stage is one of {WARDROBE_STAGES}, got {stage!r}")
    if scale <= 0:
        raise StickDataError(f"a wardrobe's scale is positive, got {scale!r}")
    w, h = WARDROBE_W, WARDROBE_H
    half = w / 2
    g = _group(cv, parent, x=x, y=floor, scaleX=scale, scaleY=scale)
    box(cv, g, 0, -h, w, h, OAK_DARK, 5, r=4)
    box(cv, g, 14, -h + 16, w - 28, h - 30, CHIPBOARD)
    if stage == "done":
        box(cv, g, -8, -h - 16, w + 16, 26, OAK, 5, r=4)
    _door(cv, g, 14, -h + 16, half - 16, h - 44)
    if stage == "done":
        _door(cv, g, half + 2, -h + 16, half - 16, h - 44, handle=-1)
        box(cv, g, 0, -32, w, 32, OAK_DARK, 4)
        return g
    box(cv, g, half + 2, -h + 16, half - 16, h - 44, CHIPBOARD, 5, r=4)
    for dy in (70, h - 150):  # the hinges, on the side nobody is meant to see
        oval(cv, g, half + 16, -h + 16 + dy, 54, 54, STEEL, sw=4, stroke=cv.ink)
        box(cv, g, half + 44, -h + 34 + dy, 50, 18, STEEL_DARK, 3, r=4)
    for dy in (260, 300, 340, 380):
        oval(cv, g, w - 60, -h + dy, 16, 16, OAK_DARK)
    cv.require_font("the wardrobe's label is lettered in it")
    label = _group(cv, g, x=half + 12, y=-h / 2 + 30)
    box(cv, label, 0, 0, 160, 110, "#ffffff", 4, r=4)
    name = cv.uid("text")
    cv.assets.add_text(id=name, text="THIS SIDE IN", width=144, height=96, size=38, fontAsset=cv.font_asset, weight=700,
                       color=LETTER, align="center", verticalAlign="middle", wrap="balance", lineHeight="1.05",
                       maxLines=2)  # fmt: skip
    label.add_layer(id=cv.uid("layer"), asset=name, x=8, y=6)
    box(cv, g, 0, -32, w, 32, OAK_DARK, 4)
    return g


def _door(cv: Canvas, parent, x: float, y: float, w: float, h: float, handle: int = 1) -> None:
    box(cv, parent, x, y, w, h, OAK, 5, r=4)
    box(cv, parent, x + 26, y + 30, w - 52, h - 60, OAK_LIGHT, 3, r=4)
    box(cv, parent, x + (w - 26 if handle > 0 else 12), y + h / 2 - 50, 14, 100, STEEL_DARK, r=6)


@register("prop", "stick-drill", tags=("tool", "drill", "hand-prop", "home"))
def drill(cv: Canvas, parent, x: float, y: float, *, flip: bool = False, scale: float = 1.0):
    """A cordless drill with its grip at ``x, y``, the bit pointing right (``flip``: left)."""
    if scale <= 0:
        raise StickDataError(f"a drill's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=-scale if flip else scale, scaleY=scale)
    box(cv, g, -26, -10, 54, 104, TOOL_DARK, 5, r=10)
    box(cv, g, -40, 88, 82, 34, TOOL, 5, r=6)
    box(cv, g, -44, -62, 148, 62, TOOL, 5, r=14)
    box(cv, g, 104, -48, 34, 34, TOOL_DARK, 4, r=4)
    box(cv, g, 138, -36, 62, 10, STEEL, 3, r=2)
    return g


@register("prop", "stick-screws", tags=("tool", "screws", "small", "flat-pack"))
def screws(cv: Canvas, parent, x: float, y: float, *, count: int = 4, scale: float = 1.0):
    """``count`` loose screws in a row, the first centred on ``x, y``: small enough to matter."""
    if count < 1:
        raise StickDataError(f"there is at least one screw, got {count!r}")
    if scale <= 0:
        raise StickDataError(f"a screw's scale is positive, got {scale!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    for i in range(count):
        dx = i * 44
        tilt = (-8, 6, -4, 10)[i % 4]
        oval(cv, g, dx - 16, -30, 32, 16, STEEL, sw=3, stroke=cv.ink)
        shape(cv, g, f"M {dx} -14 L {dx + tilt} 26", sw=9, stroke=STEEL_DARK)
        shape(cv, g, f"M {dx - 7} -2 L {dx + 8} 4 M {dx - 7} 10 L {dx + 8} 16", sw=3, stroke=cv.ink)
    return g


def _pictogram(cv: Canvas, parent, x: float, foot: float, *, mouth: str = "smile", arms: str = "down",
               bun: bool = False, scale: float = 1.0):  # fmt: skip
    """One of a manual's little people: a round head on a blank round body, feet on ``foot``."""
    g = _group(cv, parent, x=x, y=foot, scaleX=scale, scaleY=scale)
    for dx in (-30, 30):
        box(cv, g, dx - 20, -150, 40, 150, MANUAL_PAPER, 6, r=20)
    _bust(cv, g, -300, mouth=mouth, arms=arms, bun=bun)
    return g


def _bust(cv: Canvas, g, top: float, *, mouth: str, arms: str, bun: bool) -> None:
    """A pictogram from the hips up, the top of its body at ``top``."""
    box(cv, g, -66, top, 132, 180, MANUAL_PAPER, 6, r=60)
    arm_paths = {
        "down": ((-60, 26, -94, 150), (60, 26, 94, 150)),
        "crossed": ((-60, 40, 46, 92), (60, 40, -46, 92)),
        "right": ((-60, 26, -94, 150), (60, 30, 170, 40)),
        "left": ((60, 26, 94, 150), (-60, 30, -170, 40)),
        "lap": ((-60, 30, -30, 130), (60, 30, 30, 130)),
    }
    for x0, y0, x1, y1 in arm_paths[arms]:
        shape(cv, g, f"M {x0} {top + y0} L {x1} {top + y1}", sw=30, stroke=cv.ink)
        shape(cv, g, f"M {x0} {top + y0} L {x1} {top + y1}", sw=18, stroke=MANUAL_PAPER)
    if bun:
        oval(cv, g, -34, top - 196, 68, 68, cv.ink)
    oval(cv, g, -74, top - 150, 148, 148, MANUAL_PAPER, sw=6, stroke=cv.ink)
    for dx in (-28, 28):
        oval(cv, g, dx - 8, top - 92, 16, 16, cv.ink)
    curve = {"smile": 30, "flat": 0, "frown": -24}[mouth]
    shape(cv, g, f"M -32 {top - 50} Q 0 {top - 50 + curve} 32 {top - 50}", sw=7, stroke=cv.ink)


def _sofa(cv: Canvas, parent, x: float, foot: float, *, fine: bool = False, sitter: str = "flat", bun: bool = False,
          scale: float = 1.0):  # fmt: skip
    """A sofa with someone on it, seen from the front: a plain one, or a ``fine`` new one with cushions and a lamp."""
    g = _group(cv, parent, x=x, y=foot, scaleX=scale, scaleY=scale)
    w = 720 if fine else 560
    box(cv, g, -w / 2, -340, w, 260, MANUAL_PAPER, 6, r=40)
    sitting = _group(cv, g, y=90.0, scaleX=1.45, scaleY=1.45) if fine else g
    _bust(cv, sitting, -360, mouth=sitter, arms="lap", bun=bun)
    box(cv, g, -w / 2, -170, w, 130, MANUAL_PAPER, 6, r=26)
    for side in (-1, 1):
        box(cv, g, side * w / 2 - 50, -240, 100, 200, MANUAL_PAPER, 6, r=40)
        box(cv, g, side * (w / 2 - 70) - 12, -44, 24, 44, cv.ink)
    if fine:
        for side in (-1, 1):
            box(cv, g, side * 214 - 60, -270, 120, 110, "#ffd34d", 6, r=26)
        shape(cv, g, "M 460 0 L 460 -470", sw=10, stroke=cv.ink)
        shape(cv, g, "M 400 -440 L 520 -440 L 490 -540 L 430 -540 Z", "#ffd34d", 6, stroke=cv.ink)
        shape(cv, g, "M 420 0 L 500 0", sw=10, stroke=cv.ink)


def _suitcase(cv: Canvas, parent, x: float, foot: float) -> None:
    g = _group(cv, parent, x=x, y=foot)
    shape(
        cv, g, "M -90 -440 L -90 -530 Q -90 -560 -60 -560 L 60 -560 Q 90 -560 90 -530 L 90 -440", sw=20, stroke=cv.ink
    )
    box(cv, g, -280, -440, 560, 400, MANUAL_PAPER, 7, r=30)
    for dx in (-150, 150):
        shape(cv, g, f"M {dx} -440 L {dx} -40", sw=14, stroke=cv.ink)
    for dx in (-210, 210):
        oval(cv, g, dx - 26, -44, 52, 52, MANUAL_PAPER, sw=7, stroke=cv.ink)


def _speech(cv: Canvas, parent, text: str) -> None:
    """The speech bubble across the top of a page's drawing, its tail down to the left-hand figure's mouth."""
    x, y, w, h = 120, 470, 840, 300
    shape(cv, parent, f"M 300 {y + h - 6} L 300 {y + h + 150} L 410 {y + h - 6}", MANUAL_PAPER, 6, stroke=cv.ink)
    box(cv, parent, x, y, w, h, MANUAL_PAPER, 6, r=70)
    box(cv, parent, 306, y + h - 12, 100, 18, MANUAL_PAPER)
    name = cv.uid("text")
    cv.assets.add_text(id=name, text=text, width=w - 80, height=h - 40, size=86, fontAsset=cv.font_asset, weight=700,
                       color=NOTE_INK, align="center", verticalAlign="middle", wrap="balance", lineHeight="1.1",
                       maxLines=3)  # fmt: skip
    parent.add_layer(id=cv.uid("layer"), asset=name, x=x + 40, y=y + 20)


@register("prop", "stick-manual-page", tags=("insert", "fullscreen", "flat-pack", "manual", "font"))
def manual_page(cv: Canvas, parent, step: int, drawing: str, *, bubble: str = ""):
    """The frame given over to one page of an assembly manual: the step's number and one of :data:`MANUAL_DRAWINGS`
    in its wordless little people. Only ``"argument"`` has words, its ``bubble``, and it must have them."""
    cv.require_font("the manual's step numbers are set in it")
    if drawing not in MANUAL_DRAWINGS:
        raise StickDataError(f"a manual page draws one of {MANUAL_DRAWINGS}, got {drawing!r}")
    if step < 1:
        raise StickDataError(f"a manual's steps start at 1, got {step!r}")
    if (drawing == "argument") != bool(bubble.strip()):
        raise StickDataError("a speech bubble belongs on the argument page, and only there")
    g = _group(cv, parent)
    box(cv, g, 0, 0, cv.width, cv.height, MANUAL_PAPER)
    box(cv, g, 0, 0, 44, cv.height, "#000000", opacity=0.07)
    box(cv, g, 84, 250, 912, 1240, "#00000000", 5, r=8)
    name = cv.uid("text")
    cv.assets.add_text(id=name, text=str(step), width=320, height=190, size=170, fontAsset=cv.font_asset, weight=700,
                       color=NOTE_INK, align="start", verticalAlign="middle", maxLines=1)  # fmt: skip
    g.add_layer(id=cv.uid("layer"), asset=name, x=124, y=272)
    foot = 1400.0
    if drawing == "smiling":
        _pictogram(cv, g, 330, foot, scale=1.45)
        _pictogram(cv, g, 750, foot, scale=1.45)
    elif drawing == "argument":
        _speech(cv, g, bubble)
        _pictogram(cv, g, 330, foot, mouth="frown", arms="right", scale=1.0)
        _pictogram(cv, g, 750, foot, mouth="frown", arms="left", scale=1.0)
    elif drawing == "crossed":
        _pictogram(cv, g, 540, foot, mouth="flat", arms="crossed", scale=1.6)
    elif drawing == "sofa":
        _sofa(cv, g, 540, foot, sitter="frown", scale=1.35)
    elif drawing == "suitcase":
        _suitcase(cv, g, 540, foot - 120)
    elif drawing == "hug":
        _pictogram(cv, g, 420, foot - 110, arms="right", scale=1.25)
        _pictogram(cv, g, 650, foot - 110, arms="left", scale=1.25)
        screws(cv, g, 460, foot - 30, scale=1.3)
    else:
        _sofa(cv, g, 470, foot, fine=True, sitter="smile", bun=True, scale=1.0)
    return g


@register("prop", "stick-caller", tags=("phone", "ringing", "hand-prop", "font"))
def caller(cv: Canvas, parent, x: float, y: float, name: str, *, ring: Sequence[float] = (), scale: float = 1.0):
    """A phone centred on ``x, y`` ringing with ``name`` across its screen, the answer and decline buttons under it;
    it shakes for a moment at each time in ``ring`` (seconds on the parent's clock)."""
    cv.require_font("the caller's name is set in it")
    if not name.strip():
        raise StickDataError("a ringing phone says who is calling")
    if scale <= 0:
        raise StickDataError(f"a phone's scale is positive, got {scale!r}")
    if any(not (checks.number(t) and t >= 0) for t in ring) or list(ring) != sorted(ring):
        raise StickDataError(f"ring times must be non-negative and in order, got {list(ring)!r}")
    g = _group(cv, parent, x=x, y=y, scaleX=scale, scaleY=scale)
    box(cv, g, -100, -190, 200, 380, "#1f2430", 5, r=26)
    box(cv, g, -86, -170, 172, 340, "#dff0ff", 0, r=14)
    text = cv.uid("text")
    cv.assets.add_text(id=text, text=name, width=160, height=70, size=54, fontAsset=cv.font_asset, weight=700,
                       color=NOTE_INK, align="center", verticalAlign="middle", maxLines=1)  # fmt: skip
    g.add_layer(id=cv.uid("layer"), asset=text, x=-80, y=-120)
    oval(cv, g, -66, 74, 56, 56, RING_RED)
    oval(cv, g, 10, 74, 56, 56, RING_GREEN)
    if ring:
        keys = [(0.0, x)]
        for t in ring:
            keys += [(t, x), (t + 0.05, x - 9), (t + 0.1, x + 9), (t + 0.15, x - 7), (t + 0.2, x + 7), (t + 0.25, x)]
        cv.keys(g, "x", keys, kind="linear")
    return g

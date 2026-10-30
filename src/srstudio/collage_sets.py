"""Collage sets and props: painted rooms behind the paper cast, and the paper signs, charts and the TV that carry
the gags (ADR 0026).

Each set paints the whole 1080x1920 frame in soft gradients (the "painted backdrop" half of the mixed media) and
puts a few flat objects on it; the signature cactus and code (ADR 0001) sit on a shelf or sill above
:data:`srstudio.collage.FIGURE_BOX` and below the caption pill, so neither the character nor a caption covers them.
The props are paper too: :func:`sign` (a card with words), :func:`chart` (bars on paper) and :func:`tv` (a screen
playing *BOWLHEADS*, the invented toilet show, with a tiny Flush in it).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from . import checks, signature
from .canvas import Canvas
from .collage import INK, LOOKS, CollageError, Point, _cut, _paper, _ring, draw_shapes, figure_shapes
from .registry import register

__all__ = [
    "CACTUS_HEIGHT",
    "SETS",
    "SHELVES",
    "signature_box",
    "boardroom",
    "classroom",
    "living_room",
    "cafe",
    "newsroom",
    "therapy",
    "stage",
    "bathroom",
    "sign",
    "chart",
    "tv",
    "call_buttons",
    "marks_box",
    "zoom_pivot",
]

CACTUS_HEIGHT = 152.0  # signature.cactus at scale 1
SILL_Y = 735.0  # where the cactus stands: above the figure, below the caption pill
CACTUS_SCALE = 0.95
CODE_HEIGHT = 16


def _wall(cv: Canvas, g, name: str, top: str, bottom: str) -> None:
    cv.rect(g, 0, 0, cv.width, cv.height, cv.grad(f"collage-{name}-wall", [(0, top), (1, bottom)], (0, 0, 0, 1)))


DEPTH_BLUR = 3.0  # the painted backdrop is a touch out of focus, the paper cast and the signature are sharp
OVERSCAN = 1.04  # the backdrop drawn a little larger than the frame, so its blur never pulls the frame's edge in


def _backdrop(cv: Canvas, g) -> object:
    """The group a set paints into: scaled up about the frame's centre and blurred, for depth."""
    cx, cy = cv.width / 2, cv.height / 2
    back = cv.group(g, cv.uid("g"), x=cx, y=cy, anchorX=cx, anchorY=cy, scaleX=OVERSCAN, scaleY=OVERSCAN)
    cv.apply(back, cv.effect("collage-depth", "blur", radius=DEPTH_BLUR))
    return back


def _finish(cv: Canvas, back) -> None:
    """A soft light from above and a painted vignette over a set's backdrop (the engine's vignette effect blacks out
    the frame on scene-render 0.8, so it is painted)."""
    light = cv.rgrad("collage-light", [(0, "#fff6e04d"), (1, "#fff6e000")], (0.5, 0.42, 0.5))
    cv.rect(back, 0, 0, cv.width, cv.height, light)
    shade = cv.rgrad("collage-vignette", [(0, "#2b183800"), (0.62, "#2b183800"), (1, "#2b183870")], (0.5, 0.5, 0.75))
    cv.rect(back, 0, 0, cv.width, cv.height, shade)


# each set's shelf: its left edge and width; the cactus stands near the left end, the code sits at the right
SHELVES: dict[str, tuple[float, float]] = {
    "boardroom": (720.0, 300.0),
    "classroom": (40.0, 330.0),
    "living-room": (60.0, 320.0),
    "cafe": (720.0, 320.0),
    "newsroom": (40.0, 330.0),
    "therapy": (380.0, 300.0),
    "stage": (690.0, 320.0),
    "bathroom": (730.0, 290.0),
}
SHELF_DEPTH = 26.0


def signature_box(name: str) -> tuple[float, float, float, float]:
    """Where a set's shelf, cactus and code are (x0, y0, x1, y1): a prop or a figure must leave it clear."""
    if name not in SHELVES:
        raise CollageError(f"no set {name!r}; one of {sorted(SHELVES)}")
    x, width = SHELVES[name]
    return x, SILL_Y - CACTUS_HEIGHT * CACTUS_SCALE, x + width, SILL_Y + SHELF_DEPTH


CACTUS_X = 70.0  # the cactus stands this far into its shelf
CACTUS_HALF = 44.0  # signature.cactus reaches this far either side at scale 1, its shadow included
CODE_INSET = 12.0  # the code ends this far before the shelf's right end
ZOOM_MARGIN = 12.0  # frame pixels a zoomed signature keeps from the frame's edge


def marks_box(name: str) -> tuple[float, float, float, float]:
    """Where a set's two marks are (x0, y0, x1, y1): from the cactus's left to the code's end, from the cactus's
    top to the shelf's front; the bare ends of the shelf are outside it."""
    x, width = SHELVES[name] if name in SHELVES else (0.0, 0.0)
    _, y0, _, y1 = signature_box(name)
    return x + CACTUS_X - CACTUS_HALF * CACTUS_SCALE, y0, x + width - CODE_INSET, y1


def zoom_pivot(name: str, face: Point, scale: float, width: float = 1080.0, height: float = 1920.0) -> Point:
    """Where a zoom by ``scale`` onto ``face`` pivots on set ``name`` so that both signature marks, cactus and code
    (:func:`marks_box`), stay at least :data:`ZOOM_MARGIN` inside the frame: the face itself when it already does,
    otherwise the point nearest to it that does. :class:`CollageError` when no pivot can keep them in frame at that
    scale."""
    if not (checks.number(scale) and scale > 1):
        raise CollageError(f"a zoom scales up: got {scale!r}")
    x0, y0, x1, y1 = marks_box(name)
    k = scale - 1
    pivot = []
    for v, lo_edge, hi_edge, size in ((face[0], x0, x1, width), (face[1], y0, y1, height)):
        lo = (hi_edge * scale - size + ZOOM_MARGIN) / k  # the far side of the box stays in
        hi = (lo_edge * scale - ZOOM_MARGIN) / k  # the near side of the box stays in
        if lo > hi:
            raise CollageError(f"{name}: no zoom by {scale} keeps its signature in frame")
        pivot.append(min(max(v, lo), hi))
    return pivot[0], pivot[1]


def _shelf(cv: Canvas, g, name: str, colour: str) -> None:
    """A paper shelf under the signature, with the cactus on it and the code on its edge."""
    x, width = SHELVES[name]
    draw_shapes(
        cv,
        g,
        _paper(
            _cut(
                f"shelf-{x}",
                [(x, SILL_Y), (x + width, SILL_Y), (x + width, SILL_Y + SHELF_DEPTH), (x, SILL_Y + SHELF_DEPTH)],
                2,
            ),
            colour,
        ),
    )
    signature.cactus(cv, g, x + CACTUS_X, SILL_Y, CACTUS_SCALE)
    signature.code(cv, g, x + width - CODE_INSET, SILL_Y + 5, CODE_HEIGHT, color="#fffaf0", opacity=0.85, align="end")


def _frame(cv: Canvas, g, key: str, x: float, y: float, w: float, h: float, fill: str, border: str = "#6b4f3a") -> None:
    box = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    draw_shapes(cv, g, _paper(_cut(f"{key}-frame", box, 3), border))
    cv.rect(g, x + 16, y + 16, w - 32, h - 32, fill, INK, 4)  # the picture: a colour or a painted gradient


@register(
    "location",
    "collage-boardroom",
    summary="A glass-walled boardroom: city at dusk, a mission poster, a shelf with the signature cactus",
)
def boardroom(cv: Canvas, parent) -> object:
    g = cv.group(parent, cv.uid("g"))
    back = _backdrop(cv, g)
    _wall(cv, back, "boardroom", "#2b3a55", "#8d99ae")
    sky = cv.grad("collage-boardroom-sky", [(0, "#f6bd60"), (0.6, "#f28482"), (1, "#84a59d")], (0, 0, 0, 1))
    cv.rect(back, 60, 470, 960, 1150, sky)
    for i, (w, h) in enumerate(((90, 420), (120, 560), (70, 330), (140, 700), (100, 480), (80, 380), (130, 610))):
        x = 70 + i * 135
        cv.rect(back, x, 1620 - h, w, h, "#3d405b", opacity=0.85)
        for row in range(int(h // 70)):
            cv.rect(back, x + 18, 1620 - h + 24 + row * 70, w - 36, 16, "#f2cc8f", opacity=0.5)
    for x in (60, 380, 700, 1020):
        cv.rect(back, x - 6, 460, 12, 1170, "#1b263b")
    cv.rect(
        back, 0, 1610, cv.width, 310, cv.grad("collage-boardroom-table", [(0, "#6f4e37"), (1, "#3b2a1e")], (0, 0, 0, 1))
    )
    _finish(cv, back)
    _shelf(cv, g, "boardroom", "#1b263b")
    return g


@register(
    "location",
    "collage-classroom",
    summary="A classroom: chalkboard with scribbles, a colour strip, a clock and the cactus on the sill",
)
def classroom(cv: Canvas, parent) -> object:
    g = cv.group(parent, cv.uid("g"))
    back = _backdrop(cv, g)
    _wall(cv, back, "classroom", "#e9f5db", "#b5c99a")
    cv.rect(back, 0, 480, cv.width, 34, "#ffffff", opacity=0.6)
    for i, colour in enumerate(("#e63946", "#f4a261", "#e9c46a", "#2a9d8f", "#457b9d", "#9b5de5") * 2):
        cv.rect(back, 20 + i * 88, 488, 70, 18, colour)
    board = [(70, 800), (1010, 800), (1010, 1500), (70, 1500)]
    draw_shapes(cv, back, _paper(_cut("chalkboard", board, 3), "#2d4739"))
    for i, (x, y) in enumerate(((140, 880), (620, 900), (160, 1320), (700, 1340))):
        cv.path(
            back,
            f"M{x} {y} L{x + 120} {y + 30} L{x + 220} {y - 10} L{x + 300} {y + 20}",
            stroke="#f1faee",
            sw=6,
            opacity=0.7,
        )
        cv.path(back, f"M{x} {y + 60} L{x + 260} {y + 60}", stroke="#f1faee", sw=5, opacity=0.5 + 0.1 * (i % 2))
    clock = _ring("classroom-clock", 900, 620, 70, 70, n=24, amount=0.0)
    draw_shapes(cv, back, _paper(clock, "#ffffff"))
    cv.line(back, 900, 620, 900, 572, INK, 7)
    cv.line(back, 900, 620, 934, 640, INK, 7)
    cv.rect(
        back, 0, 1500, cv.width, 420, cv.grad("collage-classroom-floor", [(0, "#d4a373"), (1, "#a47148")], (0, 0, 0, 1))
    )
    _finish(cv, back)
    _shelf(cv, g, "classroom", "#8a5a44")
    return g


@register(
    "location",
    "collage-living-room",
    summary="A living room: striped wallpaper, a window with curtains, a "
    "framed sunset, a floor lamp, the cactus on a shelf",
)
def living_room(cv: Canvas, parent) -> object:
    g = cv.group(parent, cv.uid("g"))
    back = _backdrop(cv, g)
    _wall(cv, back, "living", "#ffe5d9", "#ffcad4")
    for x in range(0, 1080, 90):
        cv.rect(back, x, 0, 34, 1920, "#f4acb7", opacity=0.35)
    cv.rect(back, 620, 820, 360, 520, cv.grad("collage-living-window", [(0, "#a2d2ff"), (1, "#cdb4db")], (0, 0, 0, 1)))
    for x in (590, 900):
        draw_shapes(
            cv,
            back,
            _paper(_cut(f"curtain-{x}", [(x, 800), (x + 110, 800), (x + 90, 1380), (x + 10, 1380)], 5), "#9d4edd"),
        )
    _frame(
        cv,
        back,
        "sunset",
        110,
        840,
        300,
        220,
        cv.grad("collage-living-sunset", [(0, "#ffb703"), (1, "#fb8500")], (0, 0, 0, 1)),
    )
    cv.rect(
        back, 0, 1560, cv.width, 360, cv.grad("collage-living-sofa", [(0, "#588157"), (1, "#3a5a40")], (0, 0, 0, 1))
    )
    _finish(cv, back)
    _shelf(cv, g, "living-room", "#7f5539")
    return g


@register(
    "location",
    "collage-cafe",
    summary="A café: painted brick, a chalk menu, two glowing pendant lamps, the cactus on the counter shelf",
)
def cafe(cv: Canvas, parent) -> object:
    g = cv.group(parent, cv.uid("g"))
    back = _backdrop(cv, g)
    _wall(cv, back, "cafe", "#bc6c25", "#7f4f24")
    for row in range(26):
        offset = 0 if row % 2 else 60
        for col in range(-1, 10):
            cv.rect(back, offset + col * 120, row * 74, 110, 64, "#dda15e", radius=4, opacity=0.25)
    for x in (230, 850):
        cv.line(back, x, 0, x, 520, INK, 4)
        glow = cv.rgrad("collage-cafe-glow", [(0, "#fff3b0"), (1, "#fff3b000")])
        cv.ellipse(back, x - 160, 440, 320, 320, glow, opacity=0.8)
        draw_shapes(
            cv,
            back,
            _paper(_cut(f"lamp-{x}", [(x - 60, 520), (x + 60, 520), (x + 40, 470), (x - 40, 470)], 2), "#283618"),
        )
    menu = [(330, 790), (750, 790), (750, 1250), (330, 1250)]
    draw_shapes(cv, back, _paper(_cut("menu", menu, 3), "#2b2d42"))
    for i in range(6):
        cv.path(
            back, f"M{370} {850 + i * 64} L{560 + (i % 3) * 40} {850 + i * 64}", stroke="#f8f9fa", sw=7, opacity=0.75
        )
        cv.path(back, f"M{660} {850 + i * 64} L{710} {850 + i * 64}", stroke="#f8f9fa", sw=7, opacity=0.75)
    cv.rect(back, 0, 1580, cv.width, 340, cv.grad("collage-cafe-table", [(0, "#e9edc9"), (1, "#ccd5ae")], (0, 0, 0, 1)))
    _finish(cv, back)
    _shelf(cv, g, "cafe", "#283618")
    return g


@register(
    "location",
    "collage-newsroom",
    summary="A TV newsroom: blue gradient, a spinning-globe graphic, light streaks, the cactus on the anchor's shelf",
)
def newsroom(cv: Canvas, parent) -> object:
    g = cv.group(parent, cv.uid("g"))
    back = _backdrop(cv, g)
    _wall(cv, back, "news", "#03045e", "#0077b6")
    for i in range(7):
        cv.path(back, f"M{-100 + i * 200} 1920 L{300 + i * 160} 0", stroke="#90e0ef", sw=26, opacity=0.08)
    globe = cv.rgrad("collage-news-globe", [(0, "#48cae4"), (1, "#023e8a")], (0.4, 0.35, 0.7))
    cv.ellipse(back, 640, 760, 380, 380, globe, "#caf0f8", 4)
    for k in (0.3, 0.65, 1.0):
        cv.ellipse(back, 830 - 190 * k, 760, 380 * k, 380, "#00000000", "#caf0f8", 3, opacity=0.6)
    for dy in (95, 190, 285):
        cv.line(back, 660, 760 + dy, 1000, 760 + dy, "#caf0f8", 3, opacity=0.6)
    cv.rect(back, 0, 1600, cv.width, 320, cv.grad("collage-news-desk", [(0, "#0096c7"), (1, "#023047")], (0, 0, 0, 1)))
    cv.rect(back, 0, 1596, cv.width, 10, "#ffb703")
    _finish(cv, back)
    _shelf(cv, g, "newsroom", "#023047")
    return g


@register(
    "location",
    "collage-therapy",
    summary="A therapist's office: bookshelf, framed diploma, window blinds, a "
    "rubber plant and the cactus on the books",
)
def therapy(cv: Canvas, parent) -> object:
    g = cv.group(parent, cv.uid("g"))
    back = _backdrop(cv, g)
    _wall(cv, back, "therapy", "#f5ebe0", "#d6ccc2")
    for i in range(9):
        cv.rect(back, 660, 800 + i * 40, 340, 22, "#e3d5ca", opacity=0.9)
    cv.rect(back, 650, 790, 360, 380, "#00000000", "#a68a64", 10)
    _frame(cv, back, "diploma", 120, 860, 300, 220, "#fefae0")
    for i in range(4):
        cv.line(back, 170, 920 + i * 34, 370, 920 + i * 34, "#bc6c25", 4, opacity=0.6)
    colours = ("#9a031e", "#5f0f40", "#0f4c5c", "#e36414", "#fb8b24", "#606c38", "#283618", "#bc6c25")
    for i, colour in enumerate(colours):
        h = 110 + (i * 37) % 60
        cv.rect(back, 52 + i * 40, SILL_Y - h, 34, h, colour, radius=3)
    cv.rect(
        back, 0, 1560, cv.width, 360, cv.grad("collage-therapy-chair", [(0, "#a98467"), (1, "#6c584c")], (0, 0, 0, 1))
    )
    _finish(cv, back)
    _shelf(cv, g, "therapy", "#6c584c")
    return g


@register(
    "location",
    "collage-stage",
    summary="The BOWLHEADS stage: a candy sky, a rainbow, sparkles, a tiled floor and the cactus on a floating shelf",
)
def stage(cv: Canvas, parent) -> object:
    g = cv.group(parent, cv.uid("g"))
    back = _backdrop(cv, g)
    _wall(cv, back, "stage", "#ff99c8", "#a9def9")
    for i, colour in enumerate(("#ff595e", "#ffca3a", "#8ac926", "#1982c4", "#6a4c93")):
        r = 620 - i * 46
        cv.ellipse(back, 540 - r, 1300 - r, 2 * r, 2 * r, "#00000000", colour, 40, opacity=0.8)
    for i, (x, y) in enumerate(((150, 560), (930, 600), (260, 1060), (860, 1120), (520, 520))):
        star = _ring(f"spark-{i}", x, y, 34, 34, n=8, amount=0.0)
        spikes = [
            (px, py) if k % 2 == 0 else (x + (px - x) * 0.35, y + (py - y) * 0.35) for k, (px, py) in enumerate(star)
        ]
        draw_shapes(cv, back, _paper(spikes, "#fffaf0", shadow=False))
    for row in range(5):
        for col in range(10):
            fill = "#ffffff" if (row + col) % 2 else "#b8c0ff"
            cv.rect(back, col * 108, 1560 + row * 72, 108, 72, fill, opacity=0.9)
    _finish(cv, back)
    _shelf(cv, g, "stage", "#6a4c93")
    return g


@register(
    "location",
    "collage-bathroom",
    summary="A family bathroom: two-tone tiles, a mirror with a sheen, a striped shower curtain, a towel on its rail "
    "and the cactus on the shelf above the sink",
)
def bathroom(cv: Canvas, parent) -> object:
    g = cv.group(parent, cv.uid("g"))
    back = _backdrop(cv, g)
    _wall(cv, back, "bathroom", "#e6f4f1", "#bfe1dc")
    for row in range(12):
        for col in range(10):
            fill = "#d3ece8" if (row + col) % 2 else "#c3e3de"
            cv.rect(back, col * 108 + 3, 1060 + row * 42 + 3, 102, 36, fill, radius=4, opacity=0.9)
    cv.rect(back, 0, 1050, cv.width, 14, "#7fb7ad")
    cv.rect(back, 0, 380, 300, 1180, "#8ecae6")
    for i in range(6):
        cv.rect(back, 18 + i * 50, 380, 22, 1180, "#ffffff", opacity=0.55)
        cv.ellipse(back, 14 + i * 50, 360, 30, 30, "#00000000", "#adb5bd", 6)
    cv.rect(back, -20, 352, 340, 12, "#adb5bd", radius=6)
    _frame(cv, back, "mirror", 420, 520, 360, 440, "#dff3ff")
    cv.path(back, "M470 560 L560 560 L460 680 Z", "#ffffff", opacity=0.6)
    cv.path(back, "M600 560 L640 560 L470 760 L460 720 Z", "#ffffff", opacity=0.35)
    cv.rect(back, 830, 980, 200, 14, "#adb5bd", radius=7)
    cv.rect(back, 860, 994, 140, 260, "#ffafcc", radius=10)
    cv.rect(back, 860, 1180, 140, 20, "#ff8fab")
    cv.rect(
        back, 0, 1560, cv.width, 360, cv.grad("collage-bathroom-floor", [(0, "#b8c0ff"), (1, "#7d83c4")], (0, 0, 0, 1))
    )
    cv.ellipse(back, 340, 1690, 400, 120, "#ffd6e0", opacity=0.85)
    _finish(cv, back)
    _shelf(cv, g, "bathroom", "#7fb7ad")
    return g


SETS: dict[str, Callable[[Canvas, object], object]] = {
    "boardroom": boardroom,
    "classroom": classroom,
    "living-room": living_room,
    "cafe": cafe,
    "newsroom": newsroom,
    "therapy": therapy,
    "stage": stage,
    "bathroom": bathroom,
}


# -- props ------------------------------------------------------------------------------------------------------------
@register("prop", "collage-sign", summary="A paper card with words on it, tilted, with a drop shadow")
def sign(
    cv: Canvas,
    parent,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    size: float,
    fill: str = "#fffaf0",
    color: str = INK,
    tilt: float = 0.0,
) -> object:
    """A card ``w`` by ``h`` with its top-left at ``x, y``, turned ``tilt`` degrees about its centre."""
    g = cv.group(parent, cv.uid("g"), x=x + w / 2, y=y + h / 2, rotation=tilt)
    card = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    draw_shapes(cv, g, _paper(_cut(f"sign-{text}", card, 3), fill))
    cv.text(g, cv.uid("sign"), text, -w / 2 + 12, -h / 2, w - 24, h, size, color=color)
    return g


@register("prop", "collage-chart", summary="A paper bar chart: bars rising to the given fractions")
def chart(
    cv: Canvas, parent, x: float, y: float, w: float, h: float, values: Sequence[float], colour: str = "#e94f37"
) -> object:
    """Bars of ``values`` (fractions of the height, each in (0, 1]) on a paper card at ``x, y``."""
    if not values or any(not (0 < v <= 1) for v in values):
        raise CollageError(f"a chart needs values in (0, 1], got {tuple(values)}")
    g = cv.group(parent, cv.uid("g"))
    draw_shapes(cv, g, _paper(_cut(f"chart-{x}-{y}", [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], 3), "#fffaf0"))
    left, bottom, inner_w, inner_h = x + 30, y + h - 26, w - 60, h - 60
    cv.line(g, left, y + 24, left, bottom, INK, 5)
    cv.line(g, left, bottom, x + w - 24, bottom, INK, 5)
    step = inner_w / len(values)
    for i, v in enumerate(values):
        top = bottom - v * inner_h
        bar = [
            (left + 14 + i * step, top),
            (left + i * step + step - 6, top),
            (left + i * step + step - 6, bottom),
            (left + 14 + i * step, bottom),
        ]
        draw_shapes(cv, g, _paper(_cut(f"bar-{x}-{i}", bar, 2), colour, shadow=False))
    return g


@register("prop", "collage-tv", summary="A paper TV playing BOWLHEADS: a tiny glossy Flush in the screen")
def tv(cv: Canvas, parent, x: float, y: float, w: float) -> object:
    """A TV ``w`` wide at ``x, y`` (top-left), its screen showing Flush from :mod:`srstudio.collage`."""
    h = w * 0.66
    g = cv.group(parent, cv.uid("g"))
    draw_shapes(cv, g, _paper(_cut(f"tv-{x}-{y}", [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], 3), "#2b2d42"))
    sx, sy, sw, sh = x + 18, y + 18, w - 36, h - 36
    cv.rect(g, sx, sy, sw, sh, cv.grad("collage-tv-screen", [(0, "#ffd6ff"), (1, "#bbd0ff")], (0, 0, 0, 1)))
    scale = (sh - 10) / 1160
    show = cv.group(
        g,
        cv.uid("g"),
        x=round(sx + sw / 2 - 540 * scale, 2),
        y=round(sy + sh - 1920 * scale, 2),
        scaleX=round(scale, 4),
        scaleY=round(scale, 4),
    )
    under, mouth, over = figure_shapes(LOOKS["flush"], "wide", "grin", "down")
    draw_shapes(cv, show, under + mouth + over)
    draw_shapes(
        cv,
        g,
        _paper(
            [
                (x + w / 2 - 40, y + h),
                (x + w / 2 + 40, y + h),
                (x + w / 2 + 60, y + h + 40),
                (x + w / 2 - 60, y + h + 40),
            ],
            "#2b2d42",
        ),
    )
    return g


HANG_UP = "#e63946"  # the red of the button that ends a call
CALL_GREY = "#5c5f66"
CALL_Y = 1560.0  # the buttons' centre line: over the figure's chest, above the reel's bottom bar
CALL_R = 58.0
CALL_STEP = 190.0
CALL_BOX = (540.0 - CALL_STEP - CALL_R, CALL_Y - CALL_R, 540.0 + CALL_STEP + CALL_R, CALL_Y + CALL_R)


@register(
    "prop",
    "collage-call-buttons",
    summary="A video call's buttons over the picture: mute and camera in grey, the red hang-up between them",
)
def call_buttons(cv: Canvas, parent) -> object:
    """Three paper buttons across :data:`CALL_BOX`: what turns a shot into the other side of a video call. No
    lettering, so nothing on them is measured by the safe-area check."""
    g = cv.group(parent, cv.uid("g"))
    for i, (dx, fill) in enumerate(((-CALL_STEP, CALL_GREY), (0.0, HANG_UP), (CALL_STEP, CALL_GREY))):
        cx = 540.0 + dx
        draw_shapes(cv, g, _paper(_ring(f"call-{i}", cx, CALL_Y, CALL_R, CALL_R), fill))
    mx, my = 540.0 - CALL_STEP, CALL_Y
    # the microphone: a capsule on a stand
    draw_shapes(cv, g, [(_capsule(mx - 13, my - 34, 26, 44), "#fffaf0", None, 0.0, 1.0)])
    cv.line(g, mx, my + 14, mx, my + 30, "#fffaf0", 6)
    cv.line(g, mx - 16, my + 30, mx + 16, my + 30, "#fffaf0", 6)
    # the handset, lying down: the hang-up
    draw_shapes(cv, g, [(_capsule(540.0 - 36, CALL_Y - 9, 72, 22), "#fffaf0", None, 0.0, 1.0)])
    # the camera: a body and its lens
    cx = 540.0 + CALL_STEP
    draw_shapes(cv, g, [(_capsule(cx - 32, CALL_Y - 20, 46, 40, r=8), "#fffaf0", None, 0.0, 1.0)])
    draw_shapes(
        cv,
        g,
        [
            (
                _poly_closed(
                    [(cx + 16, CALL_Y - 4), (cx + 34, CALL_Y - 16), (cx + 34, CALL_Y + 16), (cx + 16, CALL_Y + 4)]
                ),
                "#fffaf0",
                None,
                0.0,
                1.0,
            )
        ],
    )
    return g


def _poly_closed(points: Sequence[Point]) -> str:
    return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in points) + " Z"


def _capsule(x: float, y: float, w: float, h: float, r: float | None = None) -> str:
    """A rounded rectangle as path data, its corner radius ``r`` (half the short side by default)."""
    r = min(w, h) / 2 if r is None else r
    return (
        f"M {x + r:.1f} {y:.1f} H {x + w - r:.1f} A {r:.1f} {r:.1f} 0 0 1 {x + w:.1f} {y + r:.1f} "
        f"V {y + h - r:.1f} A {r:.1f} {r:.1f} 0 0 1 {x + w - r:.1f} {y + h:.1f} H {x + r:.1f} "
        f"A {r:.1f} {r:.1f} 0 0 1 {x:.1f} {y + h - r:.1f} V {y + r:.1f} A {r:.1f} {r:.1f} 0 0 1 {x + r:.1f} {y:.1f} Z"
    )

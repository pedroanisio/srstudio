"""The Gloss style's sets and props: the Plaza, the Activity Room and the Waiting Room, the Joy Points board every
gag is shown on, the exit door (painted on, or nested), the queue ticket, the hook card and the Plaza Notice that
buttons each reel (ADR 0030).

Every location fills the 1080 × 1920 frame, draws both signature marks (ADR 0001) and takes its events on the
shot's clock: the Waiting Room's display shows ``serving`` numbers, a door opens at each second of ``opens``.
Lettering that belongs to the scenery (a display's label, a sign, a room name) is drawn in strokes
(:func:`srstudio.gloss.letters`) and numbers as seven-segment shapes, so the sets need no font and a camera move
never carries a text layer out of the safe area. Words on the board, the hook and the notice are text, measured
with :func:`wrap`, which refuses a text that does not fit its box, so no lettering spills.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import camera, gloss, look, signature
from .canvas import Canvas
from .gloss import GlossError, Talk
from .registry import register

__all__ = [
    "Card",
    "TONES",
    "FLOOR",
    "HOST_Y",
    "SAFE",
    "BOARD_BOX",
    "wrap",
    "plaza",
    "activity",
    "waiting",
    "board",
    "door",
    "ticket",
    "hook",
    "notice",
    "SETS",
    "PROPS",
    "finish",
    "GRADE",
]

W, H = 1080, 1920
FLOOR = 1270  # where the dolls stand: feet just above the caption band
CAPTION_SHADE = 1230  # where the floor starts to darken toward the caption band
POP_OPEN = 0.16  # seconds the first card takes to pop open; its words show from then on
HOST_Y = 560  # where Sunny floats by default
SAFE = (80, 220, 920, 1420)  # the vertical safe region (layout.VERTICAL) every text layer stays inside
INK_W = 6.0
PAPER = "#fff8ee"  # the board's and the notice's opaque ground
TEXT = "#2a1f3d"
TONES = {"info": "#22479a", "ok": "#14603a", "alert": "#a3192f", "plum": "#6b2fa8"}  # 7:1 on PAPER: the encode
# measures antialiased glyphs, which read about a quarter lower than the colour
BOARD_PAD = 22
BOARD_MIN = 150
BADGE_W = 190  # the points badge on a scored card
BOARD_BOX = (90, 232, 820, FLOOR - gloss.HEIGHT - 20 - 232)  # x, y, w, most height: it ends above a standing head
DOORS_MAX = 3
Spans = Sequence[tuple[float, float]]


@dataclass(frozen=True)
class Card:
    """What the board shows from ``start`` (seconds on the shot's clock) until the next card: a small ``label``
    over a title and an optional body, and, on a scored card, the ``points`` won or lost in a badge. The tone
    follows the points (gain ok, loss alert) unless one is named. A ``carried`` card is the one the shot before
    ended on: it is on from the cut (``start`` 0) and does not pop again."""

    start: float
    title: str
    body: str = ""
    label: str = ""
    points: int | None = None
    tone: str = ""
    carried: bool = False

    @property
    def colour(self) -> str:
        if self.tone:
            return TONES[self.tone]
        if self.points is None or self.points == 0:
            return TONES["info"]
        return TONES["ok" if self.points > 0 else "alert"]

    @property
    def heading(self) -> str:
        return self.label or ("JOY POINTS" if self.points is not None else "")


# -- text and numbers -------------------------------------------------------------------------------------------------
def wrap(font: bytes, text: str, size: float, width: float, max_lines: int) -> list[str]:
    """:func:`srstudio.look.wrap`, refusing with :class:`GlossError`."""
    try:
        return look.wrap(font, text, size, width, max_lines)
    except look.FitError as e:
        raise GlossError(str(e)) from None


# segments a..g of a seven-segment digit: a top, b top right, c bottom right, d bottom, e bottom left, f top left,
# g middle
_SEGMENTS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
}


def digits_width(text: str, h: float) -> float:
    """How wide :func:`digits` draws ``text`` at height ``h``."""
    return len(text) * h * 0.62 - h * 0.1


def digits(cv: Canvas, parent, text: str, x: float, y: float, h: float, colour: str, *, ghost: str | None = None):
    """``text`` (digits only) as seven-segment numerals ``h`` tall, top-left at ``x``, ``y``; unlit segments in
    ``ghost`` when given, as an LED display shows them."""
    if not text or any(c not in _SEGMENTS for c in text):
        raise GlossError(f"a seven-segment number is digits only, got {text!r}")
    t, w = h * 0.12, h * 0.52
    half = h / 2
    rects = {
        "a": (t * 0.6, 0, w - 1.2 * t, t),
        "b": (w - t, t * 0.6, t, half - 1.2 * t),
        "c": (w - t, half + t * 0.6, t, half - 1.2 * t),
        "d": (t * 0.6, h - t, w - 1.2 * t, t),
        "e": (0, half + t * 0.6, t, half - 1.2 * t),
        "f": (0, t * 0.6, t, half - 1.2 * t),
        "g": (t * 0.6, half - t / 2, w - 1.2 * t, t),
    }
    g = cv.group(parent, cv.uid("g"))
    for i, c in enumerate(text):
        x0 = x + i * h * 0.62
        for seg, (sx, sy, sw, sh) in rects.items():
            lit = seg in _SEGMENTS[c]
            if lit or ghost:
                cv.rect(g, round(x0 + sx, 2), round(y + sy, 2), round(sw, 2), round(sh, 2), colour if lit else ghost,
                        radius=round(t / 2, 2))  # fmt: skip
    return g


def _check_end(end: float) -> None:
    if not (math.isfinite(end) and end > 0):
        raise GlossError(f"a set is drawn for more than 0 s, got {end}")


def _rising(seconds: Sequence[float], end: float, what: str) -> None:
    last = -1.0
    for t in seconds:
        if not (math.isfinite(t) and last < t < end):
            raise GlossError(f"{what} at {t} must rise inside the shot (0..{end})")
        last = t


def _marks(cv: Canvas, g, cactus_at: tuple[float, float], code_at: tuple[float, float], colour=None) -> None:
    signature.cactus(cv, g, cactus_at[0], cactus_at[1], 0.5)
    signature.code(cv, g, code_at[0], code_at[1], 14, color=colour)


# -- the world's finish -----------------------------------------------------------------------------------------------
HAZE = "#ffe6f1"  # the warm horizon haze every far plane fades into
DEPTH_BLUR = 2.5  # px of blur on a set's far plane; the cast and the floor stay sharp
LINE = "#5b3f8c"  # scenery outline: lighter and thinner than the cast's ink, so the guests read first
LINE_W = 4.0
GRADE: dict[str, dict[str, Any]] = {  # over every shot: lights bloom, corners fall off into plum, a fine grain
    "bloom": dict(threshold=0.86, radius=26, intensity=0.32),
    "vignette": dict(amount=0.32, radius=0.92, softness=0.75, color="#3a1f5c"),
    "film-grain": dict(amount=0.025, size=1.1, seed=1028),
}


def finish(cv: Canvas, node) -> None:
    """The style's grade over a shot (:data:`GRADE`)."""
    look.grade(cv, node, "gloss", GRADE)


def _caption_shade(cv: Canvas, g) -> None:
    """The floor darkens toward the frame's foot under the cast, so the white captions read over the pale tiles."""
    paint = cv.grad("gloss-caption-shade", [(0, "#3a1f5c00"), (0.15, "#3a1f5c80"), (1, "#3a1f5cb3")], (0, 0, 0, 1))
    cv.rect(g, 0, CAPTION_SHADE, W, H - CAPTION_SHADE, paint)


def _card_shadow(cv: Canvas) -> str:
    """The soft plum shadow that lifts a card off the shot."""
    return cv.effect("gloss-card-shadow", "drop-shadow", radius=26, offsetX=6, offsetY=16, intensity=0.3,
                     color="#3a1f5c")  # fmt: skip


def _sparkles(cv: Canvas, g, points: Sequence[tuple[float, float, float]], end: float) -> None:
    """Four-pointed twinkles at ``(x, y, size)``, each pulsing on its own phase."""
    for i, (x, y, s) in enumerate(points):
        star = cv.group(g, cv.uid("g"), x=x, y=y)
        camera.anchor(star, x, y, place=True)
        cv.path(star, f"M{x:g} {y - s:g} Q{x:g} {y:g} {x + s:g} {y:g} Q{x:g} {y:g} {x:g} {y + s:g} "
                f"Q{x:g} {y:g} {x - s:g} {y:g} Q{x:g} {y:g} {x:g} {y - s:g} Z", "#ffffff", opacity=0.9)  # fmt: skip
        period, t, keys = 1.3 + 0.27 * i, 0.31 * i, [(0.0, 0.6)]
        while t < end:
            keys += [(round(t, 4), 0.6), (round(t + period / 2, 4), 1.15)]
            t += period
        cv.keys(star, "scaleX", keys, kind="sine-in-out")
        cv.keys(star, "scaleY", keys, kind="sine-in-out")


def _floor(cv: Canvas, g, top: float, base: str, tile: str, *, vp: float = 560, step: float = 26) -> None:
    """A glossy checkerboard floor in one-point perspective from the horizon ``top`` to the frame's foot: hazy
    far off, the sky's light lying on it in a soft streak, shading toward the viewer."""
    cv.rect(g, 0, top, W, H - top, base)
    rows = [top]
    while rows[-1] < H:
        rows.append(rows[-1] + step * 1.3 ** (len(rows) - 1))
    for i, (y0, y1) in enumerate(zip(rows, rows[1:], strict=False)):
        y1 = min(y1, H + 200)
        for j in range(-9, 9):
            if (i + j) % 2:
                continue
            k0, k1 = (y0 - vp) / (H - vp), (y1 - vp) / (H - vp)
            xs = [540 + (j + d) * 220 * k for k, d in ((k0, 0), (k0, 1), (k1, 1), (k1, 0))]
            ys = (y0, y0, y1, y1)
            cv.path(g, "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in zip(xs, ys, strict=True)) + " Z", tile,
                    stroke=cv.clear, sw=0)  # fmt: skip
    streak = cv.group(g, cv.uid("g"), opacity=0.5)  # the sky's light lying on the gloss
    cv.ellipse(streak, 140, top + 70, 800, 120, "#ffffff")
    cv.apply(streak, cv.effect("gloss-floor-sheen", "blur", radius=40))
    look.fade(cv, g, f"gloss-horizon-{HAZE[1:]}", HAZE, top, top + 260, W)
    look.fade(cv, g, "gloss-foot-shade", "#3a1f5c66", H, 1380, W)
    cv.rect(g, 0, top - 2, W, 4, "#ffffff", opacity=0.8)


def _block(cv: Canvas, g, x: float, y: float, s: float, colour: str, end: float, phase: float) -> None:
    """A floating toy cube (three lit faces) centred on ``x``, ``y``, ``s`` wide, bobbing."""
    b = cv.group(g, cv.uid("g"))
    top = f"M{x:g} {y - s * 0.5:g} L{x + s * 0.5:g} {y - s * 0.25:g} L{x:g} {y:g} L{x - s * 0.5:g} {y - s * 0.25:g} Z"
    left = f"M{x - s * 0.5:g} {y - s * 0.25:g} L{x:g} {y:g} L{x:g} {y + s * 0.5:g} L{x - s * 0.5:g} {y + s * 0.25:g} Z"
    right = f"M{x + s * 0.5:g} {y - s * 0.25:g} L{x:g} {y:g} L{x:g} {y + s * 0.5:g} L{x + s * 0.5:g} {y + s * 0.25:g} Z"
    cv.path(b, left, gloss.mix(colour, "#fff6e8", 0.1), LINE, LINE_W)
    cv.path(b, right, gloss.mix(colour, "#4a2470", 0.25), LINE, LINE_W)
    cv.path(b, top, gloss.mix(colour, "#fff6e8", 0.45), LINE, LINE_W)
    cv.path(b, f"M{x - s * 0.36:g} {y - s * 0.22:g} L{x - s * 0.06:g} {y - s * 0.37:g}", stroke="#ffffff",
            sw=max(3, s * 0.06), opacity=0.9)  # fmt: skip
    steps = max(2, math.ceil(end / 1.4) + 1)
    cv.keys(b, "y", [(round(phase + i * 1.4, 4) if i else 0, (0, -16)[i % 2]) for i in range(steps)],
            kind="sine-in-out")  # fmt: skip


def _bunting(cv: Canvas, g, y: float, sag: float, end: float) -> None:
    """A string of pennants across the top of the frame, swaying."""
    line = cv.group(g, cv.uid("g"))
    camera.anchor(line, 540, y - 40, place=True)
    cv.path(line, f"M-20 {y:g} Q540 {y + 2 * sag:g} 1100 {y:g}", stroke=LINE, sw=3)
    colours = ("#ff7fb6", "#ffd45e", "#7fd6c9", "#b59cff")
    for i in range(13):
        t = (i + 0.5) / 13
        x = -20 + 1120 * t
        yy = y + 2 * sag * 2 * t * (1 - t)
        flag = f"M{x - 30:g} {yy:g} L{x + 30:g} {yy:g} L{x:g} {yy + 62:g} Z"
        c = colours[i % 4]
        cv.path(line, flag, gloss.mix(c, "#fff6e8", 0.15), LINE, 3)
        cv.path(line, f"M{x - 18:g} {yy + 6:g} L{x - 4:g} {yy + 36:g}", stroke="#ffffff", sw=4, opacity=0.6)
    keys, t = [(0.0, -1.2)], 0.0
    while t < end:
        keys += [(round(t, 4), -1.2), (round(t + 1.7, 4), 1.2)]
        t += 3.4
    cv.keys(line, "rotation", keys, kind="sine-in-out")


# -- locations --------------------------------------------------------------------------------------------------------
@register(
    "location",
    "gloss-plaza",
    summary="The Plaza: a glossy pink checkerboard to a hazy horizon under a periwinkle-to-peach sky dome with "
    "its seams just showing, toy monuments on the skyline, bunting, floating blocks and twinkles; optionally a "
    "YOU ARE HERE sign pointing every way",
)
def plaza(cv: Canvas, parent, *, end: float, sign: bool = False) -> None:
    """The Plaza for ``end`` seconds; with ``sign`` a YOU ARE HERE signpost stands on the left."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    sky = [(0, "#7c68e6"), (0.42, "#b39af3"), (0.78, "#f5c4e6"), (1, "#ffe1d6")]
    cv.rect(g, 0, 0, W, 960, cv.grad("gloss-plaza-dome", sky, (0, 0, 0, 1)))
    look.pool(cv, g, "gloss-plaza-sun", "#fff4e0", -260, 560, 1600, 640, opacity=0.9)
    seams = cv.group(g, cv.uid("g"), opacity=0.13)  # the sky is a dome, and its panels show if you look
    for k in range(1, 6):
        cv.path(seams, f"M-40 {120 * k + 40:g} Q540 {120 * k - 60:g} 1120 {120 * k + 40:g}", stroke="#ffffff", sw=3)
    for x in (-300, 0, 270, 540, 810, 1080, 1380):
        cv.path(seams, f"M540 -400 Q{(540 + x) / 2:g} 300 {x:g} 900", stroke="#ffffff", sw=3)
    for i, (x, y, s) in enumerate(((170, 330, 1.0), (790, 250, 0.8), (1000, 450, 0.6))):
        cloud = cv.group(g, cv.uid("g"))
        for dx, dy, r in ((-60, 10, 50), (0, -12, 72), (70, 8, 54)):
            cv.ellipse(cloud, x + dx * s - r * s, y + dy * s - r * s, 2 * r * s, 2 * r * s,
                       cv.rgrad("gloss-cloud", [(0, "#ffffff"), (0.7, "#ffffff"), (1, "#f1e2fb")],
                                (0.4, 0.3, 0.75)))  # fmt: skip
        cv.ellipse(cloud, x - 120 * s, y + 30 * s, 240 * s, 34 * s, "#d9c6f5", opacity=0.6)
        cv.keys(cloud, "x", [(0, 0), (end, (-1) ** i * 30)], hold=False)
    _sparkles(cv, g, ((120, 560, 16), (960, 170, 20), (420, 210, 12), (700, 520, 14), (60, 150, 10)), end)
    # the skyline, hazy: hills, tents, a stacked tower, a standing ring
    far = look.depth(cv, g, "gloss-depth", DEPTH_BLUR)
    cv.path(far, "M-20 900 Q160 770 360 860 Q520 790 700 850 Q880 760 1100 880 L1100 920 L-20 920 Z",
            gloss.mix("#c9a6ee", HAZE, 0.35))  # fmt: skip
    for cx, w, h, a, b in ((150, 230, 170, "#ff9cc8", "#fff1f7"), (930, 260, 190, "#8fd9cf", "#f4fffc")):
        tent = cv.group(far, cv.uid("g"))
        cv.path(tent, _dome(cx, 900, w, h), gloss.mix(a, HAZE, 0.35))
        for k in range(-2, 3):
            cv.path(tent, f"M{cx + k * w / 6:g} 900 Q{cx + k * w / 9:g} {900 - h * 0.7:g} {cx:g} {900 - h:g}",
                    stroke=gloss.mix(b, HAZE, 0.3), sw=12)  # fmt: skip
        cv.path(tent, f"M{cx:g} {900 - h:g} L{cx:g} {870 - h:g} L{cx + 34:g} {880 - h:g} L{cx:g} {890 - h:g}",
                gloss.mix("#ffd45e", HAZE, 0.3), gloss.mix(LINE, HAZE, 0.5), 3)  # fmt: skip
    for k, c in enumerate(("#ffd45e", "#b59cff", "#ff9cc8", "#7fd6c9")):
        cv.rect(far, 330 - 34 + 6 * (k % 2), 860 - 66 * (k + 1), 68, 66, gloss.mix(c, HAZE, 0.4), radius=10)
    cv.ellipse(far, 680, 640, 190, 250, cv.clear, gloss.mix("#ffd45e", HAZE, 0.35), 34)
    look.fade(cv, g, "gloss-plaza-air", HAZE + "cc", 920, 560, W)
    cv.ellipse(g, 40, 720, 330, 330, gloss.vinyl(cv, "#ff8cc0", sphere=True), LINE, LINE_W)  # a giant ball, sunk
    gloss.sheen(cv, g, 90, 760, 110, 64)
    cv.path(g, "M700 905 L790 640 L880 905 Z", gloss.vinyl(cv, "#7fd6c9"), LINE, LINE_W)  # a striped cone
    for k in range(1, 4):
        y = 640 + k * 65
        half = 90 * (y - 640) / 265
        cv.path(g, f"M{790 - half:g} {y:g} L{790 + half:g} {y:g}", stroke="#ffffff", sw=14, opacity=0.85)
    cv.path(g, "M770 690 L742 790", stroke="#ffffff", sw=8, opacity=0.6)
    cv.ellipse(g, 450, 846, 190, 76, cv.clear, gloss.vinyl(cv, "#ffd45e"), 26)  # a torus lying on the horizon
    cv.ellipse(g, 450, 846, 190, 76, cv.clear, LINE, 3)
    cv.path(g, "M470 862 Q520 846 580 848", stroke="#ffffff", sw=6, opacity=0.8)
    _floor(cv, g, 900, "#fff3f8", "#ffb5d8")
    _bunting(cv, g, 96, 40, end)
    for x, y, s, colour, phase in ((210, 560, 90, "#7fd6c9", 0.0), (900, 620, 70, "#ffd45e", 0.5),
                                   (620, 470, 56, "#c6a8ff", 0.9)):  # fmt: skip
        _block(cv, g, x, y, s, colour, end, phase)
    if sign:
        cv.rect(g, 148, 960, 14, 300, gloss.vinyl(cv, "#c9c4d6"), LINE, LINE_W, radius=6)
        for dy, rot, colour in ((0, -8, "#7fd6c9"), (64, 10, "#ffd45e"), (128, -4, "#c6a8ff")):
            arm = cv.group(g, cv.uid("g"), rotation=rot)
            camera.anchor(arm, 155, 1000 + dy, place=True)
            cv.path(arm, f"M84 {975 + dy} L262 {975 + dy} L292 {1000 + dy} L262 {1025 + dy} L84 {1025 + dy} Z",
                    gloss.vinyl(cv, colour), LINE, LINE_W)  # fmt: skip
            gloss.letters(cv, arm, "YOU ARE HERE", 98, 992 + dy, 16, TEXT, weight=7)
    _caption_shade(cv, g)
    _marks(cv, g, (1000, 1290), (40, 1880))


def _dome(cx: float, base: float, w: float, h: float) -> str:
    """A big-top dome ``w`` wide and ``h`` tall standing on ``base``."""
    return (f"M{cx - w / 2:g} {base:g} Q{cx - w / 2:g} {base - h * 0.55:g} {cx:g} {base - h:g} "
            f"Q{cx + w / 2:g} {base - h * 0.55:g} {cx + w / 2:g} {base:g} Z")  # fmt: skip


@register(
    "location",
    "gloss-activity",
    summary="The Activity Room: cold bevelled white panels under a glowing strip light, a dark observation window "
    "with someone's eye glowing in it, a big seven-segment room number, and a lit pink target pad on a glossy "
    "grey checker floor",
)
def activity(cv: Canvas, parent, *, end: float, number: str = "07") -> None:
    """The Activity Room for ``end`` seconds; ``number`` (digits) is stencilled on the wall."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, W, 1000, cv.grad("gloss-lab-wall", [(0, "#e9e4f6"), (0.5, "#f7f4fd"), (1, "#ddd6ee")],
                                      (0, 0, 0, 1)))  # fmt: skip
    panel = cv.grad("gloss-lab-panel", [(0, "#fbfaff"), (1, "#e6e0f3")], (0, 0, 0, 1))
    for x in range(0, W, 216):
        for y in range(236, 1000, 216):
            cv.rect(g, x + 6, y + 6, 204, 204, panel, radius=10)
            cv.path(g, f"M{x + 12} {y + 8} L{x + 204} {y + 8}", stroke="#ffffff", sw=3, opacity=0.9)
            cv.path(g, f"M{x + 12} {y + 208} L{x + 204} {y + 208}", stroke="#c9c0de", sw=3)
    cv.rect(g, 0, 140, W, 96, cv.grad("gloss-lab-soffit", [(0, "#d8d0ea"), (1, "#f0ecf8")], (0, 0, 0, 1)))
    lamp = cv.group(g, cv.uid("g"))
    cv.rect(lamp, 120, 196, 840, 26, "#ffffff", LINE, 3, radius=13)
    cv.apply(lamp, cv.effect("gloss-lamp", "glow", radius=26, intensity=0.9, color="#e8fbff"))
    beam = cv.group(g, cv.uid("g"), opacity=0.32)  # the strip light's fall onto the pad
    cv.path(beam, "M180 222 L900 222 L1040 1250 L60 1250 Z", cv.grad("gloss-lab-beam", [(0, "#ffffff"),
            (1, "#ffffff00")], (0, 0, 0, 1)))  # fmt: skip
    cv.apply(beam, cv.effect("gloss-lab-beam-soft", "blur", radius=30))
    window = cv.group(g, cv.uid("g"))  # the observation window, below the board
    cv.rect(window, 640, 600, 330, 170, "#e9e4f6", LINE, LINE_W, radius=26)
    cv.rect(window, 656, 616, 298, 138, cv.grad("gloss-lab-glass", [(0, "#4a3a70"), (1, "#1c1430")],
                                               (0, 0, 0.3, 1)), radius=18)  # fmt: skip
    eye = cv.group(window, cv.uid("g"))  # someone is watching
    look.pool(cv, eye, "gloss-lab-eye", "#ffd45e", 740, 630, 130, 110, opacity=0.75)
    cv.ellipse(eye, 790, 672, 30, 26, "#fff2b8")
    cv.keys(eye, "opacity", [(0, 1), (end * 0.6, 1), (end * 0.6 + 0.08, 0.2), (end * 0.6 + 0.2, 1)])
    cv.path(window, "M672 632 L742 632 L682 712 Z", "#ffffff", opacity=0.14)
    cv.path(window, "M760 632 L790 632 L740 700 L726 700 Z", "#ffffff", opacity=0.08)
    digits(cv, g, number, 110, 620, 170, "#9a7fd1")  # a stencil that reads across the room
    gloss.letters(cv, g, "ACTIVITY ROOM", 110, 812, 28, "#8a7aa8")
    _floor(cv, g, 1000, "#e3dfee", "#cdc6de", vp=600)
    look.pool(cv, g, "gloss-lab-pool", "#ffffff", 160, 1120, 760, 260, opacity=0.7)
    pad = cv.group(g, cv.uid("g"))
    look.pool(cv, pad, "gloss-lab-pad-glow", "#ff5fa2", 340, 1190, 400, 160, opacity=0.45)
    cv.ellipse(pad, 400, 1222, 280, 96, gloss.vinyl(cv, "#ff5fa2"), LINE, LINE_W)
    cv.ellipse(pad, 440, 1236, 200, 68, gloss.vinyl(cv, "#ffd0e4"), LINE, 3)
    cv.path(pad, "M500 1252 L580 1286 M580 1252 L500 1286", stroke=LINE, sw=8)
    cv.path(pad, "M430 1232 Q470 1222 520 1224", stroke="#ffffff", sw=6, opacity=0.8)
    _caption_shade(cv, g)
    _marks(cv, g, (1000, 1290), (40, 1880))


@register(
    "location",
    "gloss-waiting",
    summary="The Waiting Room: a mint wall over a lit wainscot, a glowing NOW SERVING display whose seven-segment "
    "number changes on cue, a clock with no hands, a YOUR WAIT MATTERS poster, a row of glossy moulded chairs, a "
    "ticket dispenser and a plastic plant",
)
def waiting(cv: Canvas, parent, *, end: float, serving: Sequence[tuple[float, str]] = ((0, "3"),)) -> None:
    """The Waiting Room for ``end`` seconds; the display shows each ``(second, number)`` of ``serving`` in turn."""
    _check_end(end)
    if not serving:
        raise GlossError("the NOW SERVING display needs at least one number")
    _rising([t for t, _ in serving[1:]], end, "a NOW SERVING change")
    if serving[0][0] != 0:
        raise GlossError("the NOW SERVING display shows its first number from the start of the shot")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, W, 1000, cv.grad("gloss-wait-wall", [(0, "#c3ebdf"), (0.6, "#dcf5ee"), (1, "#cdeee4")],
                                      (0, 0, 0, 1)))  # fmt: skip
    look.pool(cv, g, "gloss-wait-wash", "#ffffff", 160, 160, 760, 560, opacity=0.55)
    cv.rect(g, 0, 840, W, 160, cv.grad("gloss-wait-wainscot", [(0, "#a9dccd"), (1, "#8fcdbb")], (0, 0, 0, 1)))
    cv.rect(g, 0, 834, W, 12, "#ecfbf6", LINE, 2)
    clock = cv.group(g, cv.uid("g"))  # a clock with no hands
    cv.ellipse(clock, 110, 330, 170, 170, gloss.vinyl(cv, "#ffffff", sphere=True), LINE, LINE_W)
    cv.ellipse(clock, 124, 344, 142, 142, cv.clear, "#d6cdea", 3)
    for k in range(12):
        a = math.pi * k / 6
        cv.line(clock, 195 + 62 * math.cos(a), 415 + 62 * math.sin(a), 195 + 52 * math.cos(a),
                415 + 52 * math.sin(a), LINE, 4)  # fmt: skip
    gloss.sheen(cv, clock, 134, 350, 54, 30, hot=False)
    cv.rect(g, 336, 312, 480, 250, "#3a1f5c", opacity=0.25, radius=22)  # the display's shadow on the wall
    cv.rect(g, 330, 300, 480, 250, cv.grad("gloss-wait-display", [(0, "#3a2c58"), (1, "#1a1028")], (0, 0, 0, 1)),
            LINE, LINE_W, radius=22)  # fmt: skip
    label = cv.group(g, cv.uid("g"))
    gloss.letters(cv, label, "NOW SERVING", 570 - gloss.letters_width("NOW SERVING", 36) / 2, 322, 36, "#ffd45e")
    cv.apply(label, cv.effect("gloss-led-amber", "glow", radius=10, intensity=0.7, color="#ffb03a"))
    starts = [t for t, _ in serving] + [end]
    for (a, number), b in zip(serving, starts[1:], strict=False):
        shown = cv.group(g, cv.uid("g"))
        h = 150
        digits(cv, shown, number, 570 - digits_width(number, h) / 2, 380, h, "#ff4d5e", ghost="#3e1f34")
        cv.apply(shown, cv.effect("gloss-led-red", "glow", radius=14, intensity=0.8, color="#ff2d4a"))
        if len(serving) > 1:
            cv.gate(shown, [(a, b)])
    cv.path(g, "M350 316 L520 316 L420 420 L350 420 Z", "#ffffff", opacity=0.06)
    poster = cv.group(g, cv.uid("g"), rotation=2)  # the motivational poster
    camera.anchor(poster, 880, 700, place=True)
    cv.rect(poster, 812, 596, 196, 212, "#fff8ee", LINE, LINE_W, radius=8)
    cv.rect(poster, 828, 612, 164, 110, cv.grad("gloss-poster", [(0, "#ffb3d6"), (1, "#c6a8ff")], (0, 0, 1, 1)))
    cv.ellipse(poster, 880, 640, 60, 60, "#ffd45e")
    for k, word in enumerate(("YOUR WAIT", "MATTERS")):
        gloss.letters(cv, poster, word, 910 - gloss.letters_width(word, 18) / 2, 736 + k * 28, 18, TEXT, weight=7)
    _floor(cv, g, 1000, "#f0eaf8", "#ddd3ee", vp=640, step=34)
    for i in range(5):  # moulded chairs
        x = 230 + i * 150
        colour = ("#ff9cc8", "#7fd6c9", "#ffd45e")[i % 3]
        cv.line(g, x - 40, 1144, x - 40, 1190, LINE, 6)
        cv.line(g, x + 40, 1144, x + 40, 1190, LINE, 6)
        cv.ellipse(g, x - 70, 1180, 140, 22, "#3a1f5c", opacity=0.12)
        cv.rect(g, x - 56, 1010, 112, 120, gloss.vinyl(cv, colour), LINE, LINE_W, radius=34)
        cv.rect(g, x - 62, 1110, 124, 34, gloss.vinyl(cv, gloss.mix(colour, "#4a2470", 0.12)), LINE, LINE_W,
                radius=14)  # fmt: skip
        cv.path(g, f"M{x - 34} 1030 Q{x - 42} 1060 {x - 36} 1096", stroke="#ffffff", sw=8, opacity=0.6)
    cv.rect(g, 70, 950, 12, 290, gloss.vinyl(cv, "#c9c4d6"), LINE, LINE_W, radius=5)  # the ticket dispenser
    cv.rect(g, 36, 900, 80, 90, gloss.vinyl(cv, "#e2422e"), LINE, LINE_W, radius=18)
    cv.rect(g, 60, 984, 34, 26, "#fff8ee", LINE, 3)
    cv.path(g, "M48 914 Q46 940 52 960", stroke="#ffffff", sw=6, opacity=0.6)
    for d in ("M1025 1080 Q980 1000 1000 940", "M1025 1080 Q1030 980 1060 930", "M1025 1080 Q1070 1020 1075 990"):
        cv.path(g, d, stroke="#2f9e68", sw=22)
        cv.path(g, d, stroke="#5fd39a", sw=12)
    cv.rect(g, 990, 1080, 70, 90, gloss.vinyl(cv, "#ff9cc8"), LINE, LINE_W, radius=10)  # a plastic plant
    _caption_shade(cv, g)
    _marks(cv, g, (1000, 1290), (40, 1880))


# -- props ------------------------------------------------------------------------------------------------------------
@register(
    "prop",
    "gloss-board",
    summary="The Joy Points board: a glossy cream panel that switches cards on the shot's clock, a small label over "
    "a toned title and wrapped body, and on a scored card a big +/− points badge that pops",
)
def board(
    cv: Canvas,
    parent,
    cards: Sequence[Card],
    *,
    end: float,
    font: bytes,
    box: tuple[float, float, float, float] | None = None,
) -> list:
    """Each card from its start to the next one's (the last to ``end``) at the top of ``box`` (x, y, w and the most
    height it may take; :data:`BOARD_BOX` by default), as tall as its label, title (48 px) and body (38 px),
    measured with ``font``. The first card pops in about its centre; a points badge pops on every scored card."""
    _check_end(end)
    if not cards:
        raise GlossError("a board needs at least one card")
    x, y, w, most = box if box is not None else BOARD_BOX
    if w < 420 or most < BOARD_MIN:
        raise GlossError(f"a board box is at least 420 wide and {BOARD_MIN} tall, got {w} × {most}")
    if x < SAFE[0] or x + w > SAFE[2] or y < SAFE[1] or y + most > SAFE[3]:
        raise GlossError(f"a board box {(x, y, w, most)} leaves the safe region {SAFE}")
    _rising([c.start for c in cards], end, "a card")
    for c in cards:
        if c.tone and c.tone not in TONES:
            raise GlossError(f"card {c.title!r}: tone {c.tone!r} is not one of {sorted(TONES)}")
        if c.carried and (c.start != 0 or c is not cards[0]):
            raise GlossError(f"card {c.title!r}: a carried card is the first, on from the cut (start 0)")
    out = []
    starts = [c.start for c in cards] + [end]
    for i, (c, b) in enumerate(zip(cards, starts[1:], strict=False)):
        a = c.start
        g = cv.group(parent, cv.uid("g"))
        cv.gate(g, [(a, b)])
        tone = c.colour
        tx = x + 36 + (BADGE_W + 20 if c.points is not None else 0)
        tw = x + w - 30 - tx
        head = 40 if c.heading else 0
        title = wrap(font, c.title, 48, tw, 2)
        room = int((most - 2 * BOARD_PAD - head - 56 * len(title) - 8) // 46)
        body = wrap(font, c.body, 38, tw, max(1, room)) if c.body else []
        h = 2 * BOARD_PAD + head + 56 * len(title) + (8 + 46 * len(body) if body else 0)
        h = max(h, BOARD_MIN if c.points is not None else 0)
        pop = cv.group(g, cv.uid("g"))
        camera.anchor(pop, x + w / 2, y + h / 2, place=True)
        pops = i == 0 and not c.carried
        if pops:
            keys = [(0.0, 0.08), (a, 0.08), (round(a + POP_OPEN, 4), 1.04), (round(a + 0.26, 4), 1.0)]
            cv.keys(pop, "scaleY", keys if a > 0 else keys[1:], hold=False)
        cv.apply(
            cv.rect(pop, x, y, w, h, PAPER, cv.ink, INK_W, radius=30), _card_shadow(cv)
        )  # opaque: text keeps its contrast over any set
        cv.rect(pop, x + 18, y + 10, w - 36, 14, "#ffffff", radius=7, opacity=0.9)
        words = cv.group(pop, cv.uid("g"))
        if pops:  # no squashed lettering while the card opens
            cv.gate(words, [(min(round(a + POP_OPEN, 4), (a + b) / 2), b)])
        ty = y + BOARD_PAD
        if c.heading:
            look.label(cv, words, c.heading, tx, ty, tw, 36, 28, tone, "start")
            ty += head
        if c.points is not None:
            badge = cv.group(pop, cv.uid("g"))
            bx, by, bh = x + 24, y + (h - 110) / 2, 110
            camera.anchor(badge, bx + BADGE_W / 2, by + bh / 2, place=True)
            if not c.carried:
                bounce = [(0, 0.2), (a, 0.2), (round(a + 0.14, 4), 1.15), (round(a + 0.26, 4), 1.0)]
                cv.keys(badge, "scaleX", bounce, hold=False)
                cv.keys(badge, "scaleY", bounce, hold=False)
            cv.rect(badge, bx, by, BADGE_W, bh, tone, cv.ink, 5, radius=26)
            cv.rect(badge, bx + 14, by + 8, BADGE_W - 28, 12, "#ffffff", radius=6, opacity=0.35)
            sign = "+" if c.points > 0 else "−" if c.points < 0 else "±"
            look.label(cv, badge, f"{sign}{abs(c.points):,}", bx, by + 14, BADGE_W, bh - 28, 60, "#ffffff")
        look.label(cv, words, "\n".join(title), tx, ty, tw, 56 * len(title), 48, TEXT, "start")
        if body:
            look.label(cv, words, "\n".join(body), tx, ty + 56 * len(title) + 8, tw, 46 * len(body), 38, tone, "start")
        out.append(g)
    return out


def _leaf(cv: Canvas, g, x: float, y: float, w: float, h: float, colour: str, painted: bool) -> None:
    gloss.lit(cv, g, lambda node, fill, line, sw: cv.rect(node, x, y, w, h, fill, line, sw, radius=10),
              gloss.vinyl(cv, colour))  # fmt: skip
    for py in (y + h * 0.08, y + h * 0.55):
        cv.rect(g, x + w * 0.14, py, w * 0.72, h * 0.36, gloss.vinyl(cv, gloss.mix(colour, "#4a2470", 0.1)),
                cv.ink, 4, radius=8)  # fmt: skip
        cv.path(g, f"M{x + w * 0.2:g} {py + 8:g} L{x + w * 0.8:g} {py + 8:g}", stroke="#ffffff", sw=4, opacity=0.6)
    cv.ellipse(g, x + w * 0.78, y + h * 0.5, w * 0.1, w * 0.1, gloss.vinyl(cv, "#ffd45e", sphere=True), cv.ink, 4)
    if painted:  # brush strokes: it is a picture of a door
        for k in range(3):
            cv.path(g, f"M{x + 8:g} {y + h * (0.2 + 0.3 * k):g} q{w * 0.3:g} -14 {w * 0.6:g} 4",
                    stroke="#ffffff", sw=8, opacity=0.45)  # fmt: skip


@register(
    "prop",
    "gloss-door",
    summary="The exit door under a red EXIT sign: painted on a freestanding board (it never opens), or real, "
    "swinging open on a smaller door inside, and that on a smaller one, until the last opens on a ticket dispenser",
)
def door(
    cv: Canvas,
    parent,
    *,
    at: tuple[float, float],
    end: float,
    scale: float = 1.0,
    opens: Sequence[float] = (),
    painted: bool = False,
    depth: int | None = None,
    opened: int = 0,
):
    """A door whose foot is centred on ``at``, 260 × 440 at scale 1, with ``depth`` doors nested in it (at most
    :data:`DOORS_MAX`; by default as many as open). The first ``opened`` stand open from the start of the shot (a
    door carried on from an earlier one), each second of ``opens`` swings the next one open, and behind the last is
    the ticket dispenser. A painted door never opens."""
    _check_end(end)
    if not (math.isfinite(scale) and scale > 0):
        raise GlossError(f"a door's scale must be > 0, got {scale}")
    if painted and (opens or opened):
        raise GlossError("a painted door does not open")
    if opened < 0:
        raise GlossError(f"a door cannot have {opened} doors open")
    depth = max(1, opened + len(opens)) if depth is None else depth
    if not 1 <= depth <= DOORS_MAX:
        raise GlossError(f"a door nests 1 to at most {DOORS_MAX} doors, got {depth}")
    if opened + len(opens) > depth:
        raise GlossError(f"a door of {depth} cannot open {opened} + {len(opens)} doors")
    _rising(opens, end, "a door opening")
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1], scaleX=scale, scaleY=scale)
    if painted:
        gloss.lit(cv, g, lambda node, fill, line, sw: cv.rect(node, -190, -500, 380, 500, fill, line, sw, radius=14),
                  gloss.vinyl(cv, "#c6a8ff"))  # fmt: skip
        cv.rect(g, -170, 0, 30, 40, gloss.vinyl(cv, "#c9c4d6"), cv.ink, 4)
        cv.rect(g, 140, 0, 30, 40, gloss.vinyl(cv, "#c9c4d6"), cv.ink, 4)
    shadow = cv.group(g, cv.uid("g"), opacity=0.35)
    cv.ellipse(shadow, -180, -22, 360, 44, "#3a1f5c")
    gloss.soft(cv, shadow, 10)
    gloss.lit(cv, g, lambda node, fill, line, sw: cv.rect(node, -150, -460, 300, 460, fill, line, sw, radius=12),
              gloss.vinyl(cv, "#6b4f9a"))  # the frame  # fmt: skip
    sign = cv.group(g, cv.uid("g"))
    cv.rect(sign, -84, -540, 168, 64, gloss.vinyl(cv, "#e2422e"), cv.ink, 5, radius=12)
    lit_letters = cv.group(sign, cv.uid("g"))
    gloss.letters(cv, lit_letters, "EXIT", -gloss.letters_width("EXIT", 40) / 2, -528, 40, "#ffffff", weight=7)
    cv.apply(lit_letters, cv.effect("gloss-exit-glow", "glow", radius=10, intensity=0.8, color="#ffe0d8"))

    def level(k: int, x: float, y: float, w: float, h: float) -> None:
        """Door ``k``: its doorway, what is behind it (door ``k + 1`` or, behind the last, the dispenser) and its
        leaf, which swings open at ``opens[k]``."""
        cv.rect(g, x, y, w, h, "#3b2d58")  # the doorway's dark inside
        cv.rect(g, x, y + h * 0.85, w, h * 0.15, "#2a1f3d")
        if k + 1 < depth:
            iw, ih = w * 0.62, h * 0.66
            ix, iy = x + (w - iw) / 2, y + h - ih
            cv.rect(g, ix - 10, iy - 10, iw + 20, ih + 10, "#5b3f86", cv.ink, 4, radius=8)
            level(k + 1, ix, iy, iw, ih)
        elif opened or opens:
            cx = x + w / 2
            cv.rect(g, cx - 4, y + h * 0.35, 8, h * 0.65, "#b9b4c4")
            cv.rect(g, cx - w * 0.22, y + h * 0.2, w * 0.44, h * 0.22, "#e2422e", cv.ink, 3, radius=6)
            cv.rect(g, cx - w * 0.1, y + h * 0.4, w * 0.2, h * 0.08, "#fff8ee", cv.ink, 2)
        leaf = cv.group(g, cv.uid("g"))
        camera.anchor(leaf, x, y + h / 2, place=True)
        _leaf(cv, leaf, x, y, w, h, ("#ff9cc8", "#7fd6c9", "#ffd45e", "#c6a8ff")[k % 4], painted)
        if k < opened:
            cv.keys(leaf, "scaleX", [(0, 0.08)])
        elif k - opened < len(opens):
            t = opens[k - opened]
            cv.keys(leaf, "scaleX", [(0, 1), (t, 1), (round(t + 0.35, 4), 0.08)], kind="cubic-out")

    level(0, -130, -440, 260, 440)
    return g


@register(
    "prop",
    "gloss-ticket",
    summary="A queue ticket: a cream paper slip with torn edges and its number in plum seven-segment digits",
)
def ticket(cv: Canvas, parent, *, at: tuple[float, float], end: float, number: str, scale: float = 1.0):
    """A ticket centred on ``at`` showing ``number`` (digits), 300 wide at scale 1."""
    _check_end(end)
    if not (math.isfinite(scale) and scale > 0):
        raise GlossError(f"a ticket's scale must be > 0, got {scale}")
    g = cv.group(parent, cv.uid("g"), x=at[0], y=at[1], scaleX=scale, scaleY=scale, rotation=-6)
    teeth = " ".join(f"L{-150 + 15 * i} {-80 + (8 if i % 2 else 0)}" for i in range(21))
    bottom = " ".join(f"L{150 - 15 * i} {80 - (8 if i % 2 else 0)}" for i in range(21))
    cv.path(g, f"M-150 -80 {teeth} L150 80 {bottom} Z", "#fff8ee", cv.ink, 5)
    cv.rect(g, -130, -60, 260, 16, "#ff9cc8", radius=6)
    h = 70 if len(number) <= 4 else 46
    digits(cv, g, number, -digits_width(number, h) / 2, -20, h, TEXT)
    return g


# -- graphics ---------------------------------------------------------------------------------------------------------
@register(
    "graphic",
    "gloss-hook",
    summary="The hook: a small Sunny in the top-left corner asking the reel's question on a cream card beside it",
)
def hook(cv: Canvas, parent, text: str, *, end: float, font: bytes, talk: Talk = ()):
    """The question at the top of the safe area beside a small, speaking Sunny, from 0 to ``end``."""
    _check_end(end)
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(0, end)])
    lines = wrap(font, text, 48, 600, 4)
    h = 40 + 56 * len(lines)
    cv.apply(cv.rect(g, 206, 228, 706, h, PAPER, cv.ink, INK_W, radius=26), _card_shadow(cv))
    look.label(cv, g, "\n".join(lines), 236, 248, 650, 56 * len(lines), 48, TEXT, "start")
    gloss.sunny(cv, g, at=(SAFE[0] + 62, 300), scale=0.42, talk=talk, end=end)
    return g


@register(
    "graphic",
    "gloss-notice",
    summary="The Plaza Notice that buttons every reel: a cream notice card on the pink checkerboard, Sunny reading "
    "it from the corner, the title in plum and the footnote typed out",
)
def notice(cv: Canvas, parent, title: str, body: str, *, end: float, font: bytes, talk: Talk = (), settle: float = 0.0):
    """A full-frame Plaza Notice: ``title``, then ``body`` typed out over the first seconds; Sunny speaks
    ``talk`` from the card's corner. The backdrop takes the style's grade, the card does not; its words show from
    ``settle`` on, once a crossfade into the notice has finished."""
    _check_end(end)
    if not (math.isfinite(settle) and 0 <= settle < end):
        raise GlossError(f"a notice's words settle inside the shot (0..{end}), not at {settle}")
    g = cv.group(parent, cv.uid("g"))
    back = cv.group(g, cv.uid("g"))
    finish(cv, back)
    cv.rect(back, 0, 0, W, H, "#f4c9e6")
    _floor(cv, back, 0, "#f4c9e6", "#ffb3d6", vp=-400, step=60)
    _caption_shade(cv, back)
    t_lines = wrap(font, title, 66, 700, 2)
    b_lines = wrap(font, body, 46, 700, 9)
    h = 150 + 76 * len(t_lines) + 56 * len(b_lines) + 150  # label, title, body, the sign-off and Sunny's corner
    top = round((H - h) / 2 - 140)  # centred a little high: the caption band stays clear below it
    cv.apply(cv.rect(g, 90, top, 860, h, PAPER, cv.ink, INK_W * 1.5, radius=48), _card_shadow(cv))
    cv.rect(g, 120, top + 20, 800, 20, "#ffffff", radius=10)
    words = cv.group(g, cv.uid("g"))
    if settle > 0:
        cv.gate(words, [(settle, end)])
    look.label(cv, words, "PLAZA NOTICE", 150, top + 70, 520, 46, 36, TONES["plum"], "start")
    look.label(cv, words, "\n".join(t_lines), 150, top + 130, 700, 76 * len(t_lines), 66, TEXT, "start")
    by = top + 170 + 76 * len(t_lines)
    layer = look.label(cv, words, "\n".join(b_lines), 150, by, 700, 56 * len(b_lines), 46, TEXT, "start")
    cv.animate_text(layer, "typewriter", presetStart=max(0.3, settle), presetDuration=round(min(2.4, end * 0.6), 3))
    foot = by + 56 * len(b_lines) + 40
    cv.line(g, 150, foot, 640, foot, "#e5d9f2", 4)
    look.label(cv, words, "Thank you for existing at the Plaza.", 150, foot + 20, 520, 40, 30, TONES["plum"], "start")
    gloss.sunny(cv, g, at=(840, top + h - 20), scale=1.0, talk=talk, end=end)
    signature.code(cv, g, 920, 1700, 14, color=TEXT, align="end")
    return g


SETS = {"plaza": plaza, "activity": activity, "waiting": waiting}
PROPS = {"door": door, "ticket": ticket}

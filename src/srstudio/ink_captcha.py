"""The Ink captcha: the "I'm not a robot" card and the 3×3 picture grid, drawn in the style's pen stroke for a
shot that shows the screen (:mod:`srstudio.ink`).

The grid's prompt sits in an ink band with white lettering, the nine tiles are doodles of a few kinds
(:data:`TILES`), a pick greys its tile and stamps a tick from its moment, and a verdict covers the grid with a
banner. Every time is on the shot's own clock (seconds into the take), like the rest of the style. The grid's
card carries the signature code (ADR 0001), small, in its corner.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import signature
from .canvas import Canvas
from .errors import SrstudioError
from .ink import ellipse, group, path
from .registry import register

__all__ = ["CaptchaError", "TILES", "captcha", "checkbox"]

TILES = ("light", "happy-light", "sad-light", "car", "tree", "laptop")
PROMPT_MAX = 60
LABEL_MAX = 24
CARD = (190, 250, 700, 800)  # x, y, width, height: under the caption band of the square frame
BAND = 150
TILE, GAP = 206, 10


class CaptchaError(SrstudioError, ValueError):
    """A prompt, a tile, a pick or a verdict the card cannot show."""


def _check_time(at: float, what: str) -> float:
    if not isinstance(at, (int, float)) or at < 0:
        raise CaptchaError(f"{what}: a time is seconds into the take, from 0, got {at!r}")
    return float(at)


def _text(cv: Canvas, parent, value: str, x, y, w, h, size, color: str) -> None:
    aid = cv.uid("txt")
    cv.assets.add_text(
        id=aid,
        text=value,
        width=w,
        height=h,
        size=size,
        fontAsset=cv.font_asset,
        color=color,
        align="center",
        verticalAlign="middle",
        wrap="word",
    )
    parent.add_layer(id=cv.uid("label"), asset=aid, x=x, y=y)


def _appear(cv: Canvas, node, at: float) -> None:
    """Hidden until ``at``, then shown (shown from the start when ``at`` is 0)."""
    if at == 0:
        node.opacity = 1
        return
    cv.keys(node, "opacity", [(0.0, 0.0), (at, 1.0)])


def _tick(cv: Canvas, parent, x, y, s: float, colour: str | None = None) -> None:
    path(cv, parent, f"M {x} {y + 30 * s} L {x + 26 * s} {y + 58 * s} L {x + 74 * s} {y}", stroke=colour, sw=7 * s)


# -- the tiles, each drawn in a TILE × TILE box at its origin ---------------------------------------------------------
def _light(cv: Canvas, g, face: str = "") -> None:
    """A traffic light; with a ``face`` (``happy`` or ``sad``) its middle lamp is a large face, read at tile size."""
    path(cv, g, "M 100 168 L 100 196", sw=4)
    if not face:
        path(cv, g, "M 70 22 Q 70 12 80 12 L 120 12 Q 130 12 130 22 L 130 160 Q 130 170 120 170 L 80 170 "
                    "Q 70 170 70 160 Z", cv.white, sw=3)  # fmt: skip
        for i, cy in enumerate((44, 91, 138)):
            ellipse(cv, g, 84, cy - 16, 32, 32, cv.ink if i == 0 else cv.shade if i == 1 else cv.white, sw=2.2)
        return
    path(cv, g, "M 56 22 Q 56 12 66 12 L 134 12 Q 144 12 144 22 L 144 160 Q 144 170 134 170 L 66 170 "
                "Q 56 170 56 160 Z", cv.white, sw=3)  # fmt: skip
    ellipse(cv, g, 88, 20, 24, 24, cv.ink, sw=2)
    ellipse(cv, g, 88, 138, 24, 24, cv.white, sw=2)
    ellipse(cv, g, 64, 52, 72, 72, cv.white, sw=2.6)  # the face
    ellipse(cv, g, 82, 74, 9, 11, cv.ink, sw=0)
    ellipse(cv, g, 109, 74, 9, 11, cv.ink, sw=0)
    if face == "sad":
        path(cv, g, "M 80 70 L 92 66 M 120 70 L 108 66", sw=2.4)  # the brows tip up in the middle
        path(cv, g, "M 82 110 Q 100 94 118 110", sw=3.2)
        path(cv, g, "M 120 84 Q 126 96 120 100 Q 114 96 120 84 Z", cv.shade, sw=1.6)  # a tear
    else:
        path(cv, g, "M 80 98 Q 100 116 120 98", sw=3.2)


def _car(cv: Canvas, g) -> None:
    path(cv, g, "M 22 128 L 30 98 Q 36 84 52 84 L 140 84 Q 156 84 164 98 L 182 128 Z", cv.white, sw=3)
    path(cv, g, "M 56 92 L 96 92 L 96 118 L 46 118 Z M 106 92 L 144 92 L 156 118 L 106 118 Z", cv.shade, sw=2)
    path(cv, g, "M 18 128 L 188 128 L 188 150 L 18 150 Z", cv.white, sw=3)
    for cx in (58, 150):
        ellipse(cv, g, cx - 18, 136, 36, 36, cv.ink, sw=2)


def _tree(cv: Canvas, g) -> None:
    path(cv, g, "M 92 196 L 96 132 L 108 132 L 112 196 Z", cv.shade, sw=2.4)
    path(cv, g, "M 100 18 Q 150 24 160 70 Q 184 104 150 132 Q 104 152 56 134 Q 20 108 46 70 Q 52 24 100 18 Z",
         cv.white, sw=3)  # fmt: skip
    path(cv, g, "M 70 80 Q 84 70 96 82 M 112 104 Q 128 94 140 106", sw=1.8)


def _laptop(cv: Canvas, g) -> None:
    path(cv, g, "M 40 40 L 166 44 L 156 136 L 32 132 Z", cv.white, sw=3)
    path(cv, g, "M 48 50 L 156 54 L 148 126 L 40 122 Z", cv.shade, sw=1.6)
    path(cv, g, "M 32 132 L 156 136 L 176 152 L 14 148 Z", cv.white, sw=3)


def _tile(cv: Canvas, parent, kind: str, x: float, y: float, name: str) -> object:
    g = parent.add_group(id=name, x=x, y=y)
    path(cv, g, f"M 0 0 L {TILE} 0 L {TILE} {TILE} L 0 {TILE} Z", cv.white, sw=2)
    if kind == "light":
        _light(cv, g)
    elif kind in ("happy-light", "sad-light"):
        _light(cv, g, kind.split("-")[0])
    elif kind == "car":
        _car(cv, g)
    elif kind == "tree":
        _tree(cv, g)
    else:
        _laptop(cv, g)
    return g


@register(
    "prop",
    "ink-captcha",
    summary="A picture captcha: a prompt in an ink band over a 3×3 grid of doodles, picks that tick and a verdict",
    style="ink",
)
def captcha(
    cv: Canvas,
    parent,
    *,
    prompt: str,
    tiles: Sequence[str],
    picks: Sequence[tuple[float, int]] = (),
    verdict: tuple[float, str] | None = None,
):
    """The grid card under the caption band: ``prompt`` (1 to :data:`PROMPT_MAX` characters) in white on the ink
    band, nine ``tiles`` (kinds from :data:`TILES`, row by row), each ``(seconds, index)`` in ``picks`` greying its
    tile and ticking it from that moment, and ``verdict`` (``(seconds, text)``) covering the grid with a banner."""
    if not prompt.strip() or len(prompt) > PROMPT_MAX:
        raise CaptchaError(f"the prompt is 1 to {PROMPT_MAX} characters, got {len(prompt)}")
    if len(tiles) != 9:
        raise CaptchaError(f"a grid has nine tiles, got {len(tiles)}")
    unknown = sorted({k for k in tiles if k not in TILES})
    if unknown:
        raise CaptchaError(f"unknown tile kinds {unknown}; one of {TILES}")
    picked = [i for _, i in picks]
    for at, i in picks:
        _check_time(at, f"the pick of tile {i}")
        if not (isinstance(i, int) and 0 <= i < 9):
            raise CaptchaError(f"there is no tile {i}: tiles are 0 to 8, row by row")
    if len(set(picked)) != len(picked):
        raise CaptchaError(f"a tile is picked twice: {picked}")
    if verdict is not None:
        _check_time(verdict[0], "the verdict")
        if not verdict[1].strip():
            raise CaptchaError("the verdict needs its text")
    x0, y0, w, h = CARD
    g = group(cv, parent)
    path(cv, g, f"M {x0 + 10} {y0 + 12} L {x0 + w + 10} {y0 + 12} L {x0 + w + 10} {y0 + h + 12} L {x0 + 10} "
                f"{y0 + h + 12} Z", cv.shade, sw=0)  # fmt: skip
    path(cv, g, f"M {x0} {y0} L {x0 + w} {y0} L {x0 + w} {y0 + h} L {x0} {y0 + h} Z", cv.white, sw=3)
    path(cv, g, f"M {x0} {y0} L {x0 + w} {y0} L {x0 + w} {y0 + BAND} L {x0} {y0 + BAND} Z", cv.ink, sw=3)
    _text(cv, g, prompt, x0 + 30, y0 + 10, w - 60, BAND - 20, 46, cv.white)
    gx = x0 + (w - (3 * TILE + 2 * GAP)) / 2
    gy = y0 + BAND + 22
    for i, kind in enumerate(tiles):
        tx, ty = gx + (i % 3) * (TILE + GAP), gy + (i // 3) * (TILE + GAP)
        _tile(cv, g, kind, tx, ty, cv.uid(f"tile-{i}-"))
    for at, i in picks:
        tx, ty = gx + (i % 3) * (TILE + GAP), gy + (i // 3) * (TILE + GAP)
        mark = group(cv, g)
        path(cv, mark, f"M {tx} {ty} L {tx + TILE} {ty} L {tx + TILE} {ty + TILE} L {tx} {ty + TILE} Z", cv.shade,
             sw=0, opacity=0.45)  # fmt: skip
        ellipse(cv, mark, tx + 8, ty + 8, 58, 58, cv.ink, sw=0)
        _tick(cv, mark, tx + 21, ty + 24, 0.42, cv.white)  # white on the ink stamp
        mark.opacity = 0
        _appear(cv, mark, at)
    signature.code(cv, g, x0 + w - 12, y0 + h - 22, 12, align="end", color=cv.shade)
    if verdict is not None:
        at, text = verdict
        banner = group(cv, g)
        by = gy + (3 * TILE + 2 * GAP) / 2 - 110
        path(cv, banner, f"M {x0 - 30} {by} L {x0 + w + 30} {by + 12} L {x0 + w + 24} {by + 232} L {x0 - 24} "
                         f"{by + 220} Z", cv.white, sw=4)  # fmt: skip
        path(cv, banner, f"M {x0 + 20} {by + 70} L {x0 + 110} {by + 160} M {x0 + 110} {by + 70} L {x0 + 20} "
                         f"{by + 160}", sw=9)  # fmt: skip
        _text(cv, banner, text, x0 + 130, by + 20, w - 120, 200, 64, cv.ink)
        banner.opacity = 0
        _appear(cv, banner, _check_time(at, "the verdict"))
    return g


@register(
    "prop",
    "ink-checkbox",
    summary='The "I\'m not a robot" card: an empty box and its label, ticked on the click',
    style="ink",
)
def checkbox(cv: Canvas, parent, label: str, *, tick_at: float | None = None):
    """The checkbox card in the middle of the square frame: the box, ``label`` (1 to :data:`LABEL_MAX`
    characters) and a recycling-arrows badge; with ``tick_at`` the tick appears at that second."""
    if not label.strip() or len(label) > LABEL_MAX:
        raise CaptchaError(f"the label is 1 to {LABEL_MAX} characters, got {len(label)}")
    if tick_at is not None:
        _check_time(tick_at, "the tick")
    x0, y0, w, h = 140, 430, 800, 230
    g = group(cv, parent)
    path(cv, g, f"M {x0 + 10} {y0 + 12} L {x0 + w + 10} {y0 + 12} L {x0 + w + 10} {y0 + h + 12} L {x0 + 10} "
                f"{y0 + h + 12} Z", cv.shade, sw=0)  # fmt: skip
    path(cv, g, f"M {x0} {y0} L {x0 + w} {y0} L {x0 + w} {y0 + h} L {x0} {y0 + h} Z", cv.white, sw=3)
    bx, by = x0 + 50, y0 + 65
    path(cv, g, f"M {bx} {by} L {bx + 100} {by} L {bx + 100} {by + 100} L {bx} {by + 100} Z", cv.white, sw=4)
    _text(cv, g, label, bx + 130, by - 10, 420, 120, 58, cv.ink)
    ax, ay = x0 + w - 110, y0 + 115  # the badge: two chasing arrows
    path(cv, g, f"M {ax - 40} {ay} A 40 40 0 0 1 {ax + 30} {ay - 26} M {ax + 40} {ay} A 40 40 0 0 1 {ax - 30} "
                f"{ay + 26}", sw=5)  # fmt: skip
    path(cv, g, f"M {ax + 18} {ay - 40} L {ax + 34} {ay - 24} L {ax + 12} {ay - 16}", sw=4)
    path(cv, g, f"M {ax - 18} {ay + 40} L {ax - 34} {ay + 24} L {ax - 12} {ay + 16}", sw=4)
    if tick_at is not None:
        tick = group(cv, g)
        _tick(cv, tick, bx + 12, by + 14, 1.0)
        tick.opacity = 0
        _appear(cv, tick, tick_at)
    return g

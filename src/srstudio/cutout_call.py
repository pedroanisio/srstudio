"""Cutout, an interview on a laptop: a video tile with someone in it, and the phone on the desk beside it.

The tile is invented and copies no real app: a plain room, a frame and, when the reel gives one, a name on a plate. It
letters nothing else, so it can never repeat a caption. Whoever is on the call is the reel's own drawing, through
``inside``: this module draws no one. The phone lies on the desk seen from above, buzzes, takes lines as they land and
can lie face down until it turns over. Every refusal is a :class:`CutoutCallError`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = ["CutoutCallError", "PHONE_CHARS", "PHONE_LINES", "PLATE_CHARS", "desk_phone", "video_tile"]

BEZEL = "#22262C"
TILE_WALL = "#C9D3D6"
TILE_FLOOR = "#AEBBC0"
PLATE = "#1E2C3C"
PLATE_CHARS = 18
PLATE_HEIGHT = 76
FRAME_WIDTH = 34  # the laptop's edge round the picture
BELOW = 900  # the bezel runs on under the tile, far enough to hide any sitter's legs
PHONE_WIDTH, PHONE_HEIGHT = 470.0, 900.0
PHONE_CHARS = 12  # the most characters on a line of the lock screen, at its size
PHONE_LINES = 2
SHAKE = 0.04  # seconds between a buzzing phone's shakes
TURN = 0.22  # seconds a phone takes to turn over
SCREEN = "#16202B"


class CutoutCallError(SrstudioError, ValueError):
    """A tile or a phone asked for with arguments it cannot be drawn from."""


def _times(values, what: str) -> list[tuple[float, float]]:
    out = []
    for span in values:
        try:
            a, b = span
        except (TypeError, ValueError):
            raise CutoutCallError(f"{what} is a (start, end) pair, got {span!r}") from None
        if not (checks.number(a) and checks.number(b) and 0 <= a < b):
            raise CutoutCallError(f"{what} needs 0 <= start < end, got {span!r}")
        out.append((float(a), float(b)))
    return out


@register(
    "prop",
    "video-tile",
    style="cutout",
    summary="An invented video call on a laptop's screen: a plain room, whoever the reel seats in it, a name plate",
)
def video_tile(
    cv: Canvas,
    parent,
    x=60,
    y=350,
    *,
    width: float = 960,
    height: float = 1000,
    plate: str = "",
    inside: Callable[[object], None] | None = None,
    id: str = "video-tile",
):
    """The picture's top left at (``x``, ``y``), ``width`` by ``height``. ``inside`` draws who is on the call in the
    tile's own units, (0, 0) at its top left; the frame goes on after, so a figure cut by the tile's edge stays cut."""
    if not (checks.number(x) and checks.number(y)):
        raise CutoutCallError(f"a tile's position needs finite numeric coordinates, got {x!r}, {y!r}")
    if not (checks.number(width) and width > 0 and checks.number(height) and height > 0):
        raise CutoutCallError(f"a tile has a positive size, got {width!r} by {height!r}")
    if not isinstance(plate, str) or (plate and (not plate.strip() or len(plate) > PLATE_CHARS)):
        raise CutoutCallError(f"a plate has 1 to {PLATE_CHARS} characters, got {plate!r}")
    if inside is not None and not callable(inside):
        raise CutoutCallError(f"inside draws the tile's sitter and must be callable, got {inside!r}")
    if plate:
        cv.require_font("a video tile's name plate", CutoutCallError)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y)
    cv.rect(g, 0, 0, width, height, TILE_WALL)
    cv.rect(g, 0, height * 0.72, width, height * 0.28, TILE_FLOOR)
    cv.line(g, 0, height * 0.72, width, height * 0.72, "#8FA0A6", 3)
    if inside is not None:
        inside(g)
    frame = cv.group(g, f"{id}-frame")
    edge = FRAME_WIDTH
    cv.rect(frame, -edge, -edge, width + 2 * edge, edge, BEZEL)
    cv.rect(frame, -edge, height, width + 2 * edge, BELOW, BEZEL)
    cv.rect(frame, -edge, 0, edge, height, BEZEL)
    cv.rect(frame, width, 0, edge, height, BEZEL)
    cv.rect(frame, -edge, -edge, width + 2 * edge, height + 2 * edge, cv.clear, ink, 4, radius=26)
    cv.rect(frame, 0, 0, width, height, cv.clear, "#000000", 3)
    if plate:
        wide = 30.0 * len(plate) + 44
        cv.rect(g, 24, height - PLATE_HEIGHT - 24, wide, PLATE_HEIGHT, PLATE, cv.clear, 0, radius=12)
        cv.text(g, f"{id}-plate", plate, 24, height - PLATE_HEIGHT - 24, int(wide), PLATE_HEIGHT, 38, "#FFFFFF")
    return g


@register(
    "prop",
    "desk-phone",
    style="cutout",
    summary="A phone on a desk seen from above: it buzzes, takes lines as they land and can turn itself over",
)
def desk_phone(
    cv: Canvas,
    parent,
    x=540,
    y=900,
    *,
    scale: float = 1.0,
    title: str = "",
    lines: Sequence[tuple[float, str]] = (),
    buzzes: Sequence[tuple[float, float]] = (),
    turns: float | None = None,
    id: str = "desk-phone",
):
    """Centred on (``x``, ``y``), :data:`PHONE_WIDTH` by :data:`PHONE_HEIGHT` at scale 1. ``title`` tops the lock
    screen; ``lines`` (time, text) land under it and stay; ``buzzes`` shake it, (start, end) spans; given ``turns``, it
    lies face down until that time and turns over."""
    if not (checks.number(x) and checks.number(y)):
        raise CutoutCallError(f"a phone's position needs finite numeric coordinates, got {x!r}, {y!r}")
    if not (checks.number(scale) and scale > 0):
        raise CutoutCallError(f"scale must be a positive number, got {scale!r}")
    spans = _times(buzzes, "a buzz")
    if turns is not None and not (checks.number(turns) and turns >= 0):
        raise CutoutCallError(f"a phone turns over at a time, got {turns!r}")
    if not isinstance(title, str) or len(title) > PHONE_CHARS:
        raise CutoutCallError(f"a title has up to {PHONE_CHARS} characters, got {title!r}")
    if len(lines) > PHONE_LINES:
        raise CutoutCallError(f"a phone shows up to {PHONE_LINES} lines, got {lines!r}")
    last = 0.0
    for row in lines:
        if not isinstance(row, tuple | list) or len(row) != 2:
            raise CutoutCallError(f"a phone line is a (time, text) pair, got {row!r}")
        at, text = row
        if not (checks.number(at) and at >= last):
            raise CutoutCallError(f"lines land in time order from zero or later, got {lines!r}")
        if not (isinstance(text, str) and text.strip() and len(text) <= PHONE_CHARS):
            raise CutoutCallError(f"a line has 1 to {PHONE_CHARS} characters, got {text!r}")
        last = at
    if title or lines:
        cv.require_font("a phone's screen copy", CutoutCallError)
    ink = cv.ink
    w, h = PHONE_WIDTH, PHONE_HEIGHT
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -w / 2 + 14, -h / 2 + 22, w, h, "#000000", cv.clear, 0, radius=54, opacity=0.25)
    body = cv.group(g, f"{id}-body")
    if spans:
        keys: list[tuple[float, float]] = [(0.0, 0.0)]
        for a, b in spans:
            at, sign = a, 1.0
            while at < b:
                keys.append((round(at, 6), 7.0 * sign))
                at += SHAKE
                sign = -sign
            keys.append((b, 0.0))
        cv.keys(body, "x", keys, hold=False)
    face = cv.group(body, f"{id}-face")
    cv.rect(face, -w / 2, -h / 2, w, h, BEZEL, ink, 5, radius=54)
    cv.rect(face, -w / 2 + 18, -h / 2 + 20, w - 36, h - 40, SCREEN, radius=38)
    if title:
        cv.text(face, f"{id}-title", title, -w / 2 + 30, -h / 2 + 120, int(w - 60), 90, 58, "#FFFFFF")
    for k, (at, text) in enumerate(lines):
        row = cv.group(face, f"{id}-line-{k}", start=at)
        top = -h / 2 + 300 + 170 * k
        cv.rect(row, -w / 2 + 36, top, w - 72, 130, "#F2F4F6", radius=28)
        cv.text(row, f"{id}-line-{k}-text", text, -w / 2 + 48, top, int(w - 96), 130, 58, "#16202B")
    if turns is not None:
        turn = float(turns)
        cv.keys(face, "scaleX", [(0.0, 0.0), (turn + TURN / 2, 0.0), (turn + TURN, 1.0)], hold=False)
        back = cv.group(body, f"{id}-back")
        cv.keys(back, "scaleX", [(0.0, 1.0), (turn, 1.0), (turn + TURN / 2, 0.0)], hold=False)
        cv.rect(back, -w / 2, -h / 2, w, h, "#39424C", ink, 5, radius=54)
        cv.rect(back, -w / 2 + 40, -h / 2 + 40, 120, 170, BEZEL, "#5C6670", 3, radius=30)
        cv.ellipse(back, -w / 2 + 100, -h / 2 + 95, 26, 26, "#10161D", "#5C6670", 3)
    return g

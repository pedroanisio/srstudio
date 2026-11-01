"""An invented chat on a Toon phone: a message window that fills on cue, the phone's back until it is turned round, and
the chip that lands over it.

:func:`chat_phone` draws the phone by itself, the same body as :func:`srstudio.toon_everyday.phone` around a window that
copies no real app; each :class:`Bubble` comes in at its second and every word is measured in the style's font, wrapped
to the bubble, so a message that cannot be read on a phone is refused here and not found in a render. :func:`chat_chip`
is the short line that lands over it, wider than the phone, for a beat a viewer has to read from across the frame.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy
from .toon_everyday import (
    CAPTION_BAND,
    FRAME,
    PHONE_BODY,
    PHONE_BOX,
    PHONE_EDGE,
    PHONE_H,
    PHONE_W,
    SCREEN_BOX,
    SHADOW,
    SIGNATURE_BOX,
    Box,
    Measure,
    _ellipse,
    _overlaps,
    _place,
    _rect,
    _shown,
)
from .toon_props import BUZZ_SHAKE

__all__ = ["CHAT_APP", "Bubble", "chat_chip", "chat_phone", "wrapped"]

CHAT_APP = "Advisor"  # the invented window's title
BUBBLE_SIZE, TITLE_SIZE = 26, 24
BUBBLE_PAD = 6.0  # reference units inside a bubble
BUBBLE_GAP = 8.0  # reference units between two bubbles
LINE_H = 16.5  # reference units a row of a bubble takes
SCREEN_TOP = -192.0  # under the window's title
THEIRS, MINE, INK = "#ffffff", "#cfe8ff", "#1b1b2a"
WINDOW, BAR = "#eef0f6", "#5b6b8c"
LENS = "#14151b"
CHIP_SIZE = 36
CHIP_H = 62.0  # frame pixels
CHIP_PAD = 44.0  # frame pixels added to the text's width
CHIP_INK, CHIP_FILL, CHIP_DOT = "#1b1b2a", "#ffffff", "#34c759"
CHIP_POP = ((0.0, 0.7), (0.1, 1.08), (0.18, 1.0))  # seconds, scale


@dataclass(frozen=True)
class Bubble:
    """A message that comes in at ``at`` project seconds, the advisor's unless ``mine``."""

    at: float
    text: str
    mine: bool = False


def wrapped(text: str, measure: Measure, size: float, width: float) -> list[str]:
    """``text`` broken at spaces into rows that each fit ``width`` frame pixels at ``size``."""
    rows: list[str] = []
    for word in text.split():
        if measure(word, size) > width:
            raise ToonDataError(f"{word!r} is wider than a {width} px bubble at {size} px")
        if rows and measure(f"{rows[-1]} {word}", size) <= width:
            rows[-1] = f"{rows[-1]} {word}"
        else:
            rows.append(word)
    return rows


def _laid_out(bubbles: Sequence[Bubble], measure: Measure) -> list[tuple[Bubble, list[str], float, float]]:
    """Each bubble with its rows, top and height, reference units; the screen holds them all or nothing is drawn."""
    if not bubbles:
        raise ToonDataError("a chat needs at least one bubble")
    last = None
    out = []
    y = SCREEN_TOP
    _, top, _, screen_h = SCREEN_BOX
    wide = fh(SCREEN_BOX[2] - 2 * BUBBLE_PAD - 4)
    for b in bubbles:
        if not isinstance(b, Bubble) or not checks.number(b.at) or b.at < 0:
            raise ToonDataError(f"a chat's bubble comes in at a second >= 0, got {b!r}")
        if last is not None and b.at <= last:
            raise ToonDataError(f"a chat's bubbles rise in time: {b.at} came after {last}")
        last = b.at
        rows = wrapped(b.text, measure, BUBBLE_SIZE, wide)
        if not rows:
            raise ToonDataError("a bubble needs some text")
        h = len(rows) * LINE_H + 2 * BUBBLE_PAD
        if y + h > top + screen_h - 4:
            raise ToonDataError(f"{b.text!r} runs off the phone's screen")
        out.append((b, rows, y, h))
        y += h + BUBBLE_GAP
    return out


def _clear(what: str, box: Box) -> None:
    if _overlaps(box, CAPTION_BAND):
        raise ToonDataError(f"a {what} at {box} sits in the caption band")
    if _overlaps(box, SIGNATURE_BOX):
        raise ToonDataError(f"a {what} at {box} sits on the signature marks")


@register(
    "prop",
    "toon-chat-phone",
    summary="A phone whose invented chat window fills on cue, its back to the viewer until it is turned round",
)
def chat_phone(
    cv: Canvas,
    parent,
    bubbles: Sequence[Bubble],
    *,
    measure: Measure,
    at: tuple[float, float] = (300.0, 820.0),
    scale: float = 1.0,
    face_from: float = 0.0,
    buzz: Sequence[float] = (),
    id: str = "chat-phone",
):
    """The phone with its base at reference ``at``. Its back shows until ``face_from``, then the window, each of
    ``bubbles`` from its second; it shakes at each of ``buzz``. Returns the phone's group."""
    box = _place("chat phone", at, scale, PHONE_BOX)
    _clear("chat phone", box)
    if not (checks.number(face_from) and face_from >= 0):
        raise ToonDataError(f"a phone's face_from is a second >= 0, got {face_from!r}")
    laid = _laid_out(bubbles, measure)
    x, y = at
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    _ellipse(cv, g, -62, -6, 124, 12, SHADOW, 0, opacity=0.16)
    _rect(cv, g, -PHONE_W / 2, -PHONE_H, PHONE_W, PHONE_H, PHONE_BODY, INK_W * 0.8, radius=18)
    if face_from > 0:
        back = cv.group(g, f"{id}-back")
        _shown(cv, back, 0.0, face_from)
        _rect(cv, back, -42, -222, 44, 44, PHONE_EDGE, FINE_W * 0.6, radius=10)
        _ellipse(cv, back, -34, -214, 28, 28, LENS, FINE_W * 0.5)
    face = cv.group(g, f"{id}-face")
    _shown(cv, face, face_from, None)
    sx, sy, sw, sh = SCREEN_BOX
    _rect(cv, face, sx, sy, sw, sh, WINDOW, 0, radius=10)
    _rect(cv, face, sx, sy, sw, 26, BAR, 0, radius=10)
    cv.text(face, cv.uid("chat-title"), CHAT_APP, fh(sx), fh(sy), int(fh(sw)), int(fh(26)), TITLE_SIZE, color="#ffffff")
    for k, (b, rows, top, h) in enumerate(laid):
        note = cv.group(face, f"{id}-bubble-{k}")
        _shown(cv, note, b.at, None)
        _rect(cv, note, sx + 3, top, sw - 6, h, MINE if b.mine else THEIRS, FINE_W * 0.4, radius=8)
        for r, row in enumerate(rows):
            cv.text(note, cv.uid("chat-text"), row, fh(sx + 3 + BUBBLE_PAD), fh(top + BUBBLE_PAD + r * LINE_H),
                    int(fh(sw - 6 - 2 * BUBBLE_PAD)), int(fh(LINE_H)), BUBBLE_SIZE, color=INK, align="start",
                    wrap="none")  # fmt: skip
    if buzz:
        rest = fx(x)
        keys = [(0.0, rest)]
        for t in buzz:
            keys += [(t + dt, round(rest + fh(dx) * scale, 2)) for dt, dx in BUZZ_SHAKE]
        cv.keys(g, "x", keys, hold=False, local=False)
    return g


@register("prop", "toon-chat-chip", summary="One short line landing over a phone in a white chip, with a pop")
def chat_chip(
    cv: Canvas,
    parent,
    text: str,
    start: float,
    end: float,
    *,
    measure: Measure,
    at: tuple[float, float] = (296.0, 760.0),
    size: int = CHIP_SIZE,
    id: str = "chat-chip",
):
    """``text`` in a white chip centred on reference ``at`` from ``start`` to ``end``."""
    if not isinstance(text, str) or not text.strip():
        raise ToonDataError(f"a chip's text is a non-empty text, got {text!r}")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a chip needs 0 <= start < end, got {start!r}..{end!r}")
    width = round(measure(text, size) + CHIP_PAD, 2)
    half = width / fh(1.0) / 2
    height = CHIP_H / fh(1.0)
    x, y = at
    box = (x - half, y - height / 2, x + half, y + height / 2)
    if box[0] < FRAME[0] or box[2] > FRAME[2]:
        raise ToonDataError(f"the chip {text!r} is {width} px wide, too wide for its place at {at}")
    _clear("chat chip", box)
    g = cv.group(parent, id, start=start, end=end, x=fx(x), y=fy(y))
    cv.keys(g, "scaleX", [(start + dt, s) for dt, s in CHIP_POP], hold=False, local=False)
    cv.keys(g, "scaleY", [(start + dt, s) for dt, s in CHIP_POP], hold=False, local=False)
    cv.rect(g, round(-width / 2, 2), -CHIP_H / 2, width, CHIP_H, CHIP_FILL, cv.ink, FINE_W, radius=round(CHIP_H / 2, 2))
    cv.text(g, cv.uid("chat-chip-text"), text, round(-width / 2, 2), -CHIP_H / 2, int(width), int(CHIP_H), size,
            color=CHIP_INK, wrap="none")  # fmt: skip
    return g

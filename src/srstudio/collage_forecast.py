"""Collage, an evening's forecast: a paper weather map with an arrow sliding across it, and a phone open on a thread.

Both are invented. The map's land is a hand-cut shape that is no real coast, with no place named, no channel's graphic
and no temperature: it letters only the arrow and the clock a caller gives it. The thread has a clock, one contact name
and messages, in no real app's look: no avatar, no number, no address, no read mark. Everything on it is the caller's
words, so nothing personal can arrive by default. Paper like the rest of the style (ADR 0026). Neither holds timing but
what a caller gives it on the project clock, so a recording that re-times the beats moves them too. A refusal is a
:class:`ForecastError`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from . import checks, ink_meter
from .canvas import Canvas
from .collage import INK, _cut, _paper, _poly, draw_shapes
from .collage_everyday import BEZEL, CARD_GLYPH, CARD_LEADING, _letter, bubble, phone
from .errors import SrstudioError
from .registry import register

__all__ = ["FOREVER", "ForecastError", "Message", "thread", "weather_map"]

FOREVER = 86400.0  # the end of a span that runs on: past any reel
SEA, LAND, FRONT = "#bfe0ea", "#e3d9b0", "#2b6cb0"
ISOBAR = "#6f9fb3"
CARD = "#ffd166"
MAP_MIN = 120.0
ARROW_SIZE = 0.2  # of the map's width, the arrow's lettering
ARROW_TRAVEL = 0.22  # of the map's height, how far the arrow slides
CLOCK_SIZE = 0.15  # of the map's width, the clock card's lettering
SCREEN, BAR, STRIP, CALL = "#fffaf0", "#2b2733", "#e4dfd2", "#3ddc6e"
UNIT = 700.0  # the phone's width all of a thread's sizes are given for
BAR_H, CONTACT_H, CALL_H = 70.0, 96.0, 70.0
BAR_SIZE, CONTACT_SIZE, CALL_SIZE, MESSAGE_SIZE = 46.0, 62.0, 42.0, 60.0
PAD, GAP = 34.0, 28.0
MESSAGE_PAD = 26.0
BUBBLE_INSET = 26.0  # the bubble's own margin round its words, at any size
SLIDE = 0.12  # seconds a message takes to come up
RISE = 30.0  # px it rises, at a 700 px phone


class ForecastError(SrstudioError, ValueError):
    """A map or a thread asked for at a size it cannot draw, or with words it could not show whole."""


@dataclass(frozen=True)
class Message:
    """A bubble that lands at ``at``, project seconds: theirs on the left in grey, or ``mine`` on the right in green."""

    text: str
    at: float
    mine: bool = False


def _capitals(text: str) -> None:
    if text != text.upper():
        raise ForecastError(f"{text!r}: the style's font has capitals only")


def _rows(text: str, per_line: int) -> list[str]:
    rows: list[str] = []
    for word in text.split():
        if rows and len(rows[-1]) + 1 + len(word) <= per_line:
            rows[-1] += " " + word
        else:
            rows.append(word)
    return rows


def _gated(cv: Canvas, parent, a: float, b: float):
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(a, b)])
    return g


@register("prop", "collage-weather-map", summary="A paper weather map of invented land: a lettered arrow, a clock card")
def weather_map(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    arrow: str | None = None,
    slide: tuple[float, float] | None = None,
    clock: tuple[str, tuple[float, float]] | None = None,
) -> object:
    """A map ``w`` by ``h`` with its top-left at ``x, y``. ``arrow`` letters the big arrow down it, ``""`` draws it bare
    (for a framing that would cut its word), and it slides over ``slide`` (start, stop, project seconds) when given;
    ``clock`` is a card's text and the span it shows. Returns the group."""
    if not (checks.number(w) and w >= MAP_MIN):
        raise ForecastError(f"a map {w!r} wide is too small to read: at least {MAP_MIN}")
    if not (checks.number(h) and h >= MAP_MIN):
        raise ForecastError(f"a map {h!r} tall is too small to read: at least {MAP_MIN}")
    _capitals(arrow or "")
    size = w * ARROW_SIZE
    if len(arrow or "") * size * CARD_GLYPH > w * 0.9:
        raise ForecastError(f"{arrow!r} does not fit a map {w} wide at {size} px")
    if slide is not None and not (checks.number(slide[0]) and checks.number(slide[1]) and 0 <= slide[0] < slide[1]):
        raise ForecastError(f"slide {slide!r} needs 0 <= start < stop")
    if clock is not None:
        text, (a, b) = clock
        _capitals(text)
        if not (text and checks.number(a) and checks.number(b) and 0 <= a < b):
            raise ForecastError(f"clock {clock!r} needs a text and 0 <= start < stop")
    g = cv.group(parent, cv.uid("g"), x=x, y=y)
    draw_shapes(cv, g, _paper(_cut("weather-sheet", [(0, 0), (w, 0), (w, h), (0, h)], 3), SEA))
    coast = [(0.0, 0.3), (0.22, 0.26), (0.34, 0.4), (0.3, 0.58), (0.46, 0.7), (0.4, 0.86), (0.2, 1.0), (0.0, 1.0)]
    draw_shapes(cv, g, _paper(_cut("weather-land", [(px * w, py * h) for px, py in coast], 6), LAND, shadow=False))
    isle = [(0.66, 0.74), (0.84, 0.7), (0.92, 0.82), (0.78, 0.92), (0.62, 0.86)]
    draw_shapes(cv, g, _paper(_cut("weather-isle", [(px * w, py * h) for px, py in isle], 5), LAND, shadow=False))
    for i in range(3):  # inside the sheet: nothing on it runs past its edge
        wide, tall = w * (0.34 + i * 0.1), h * (0.08 + i * 0.03)
        cv.ellipse(g, w * 0.72 - wide / 2, h * 0.84 - tall / 2, wide, tall, cv.clear, ISOBAR, 4, opacity=0.5)
    if arrow is not None:
        moved = cv.group(g, cv.uid("g"))
        if slide is not None:
            cv.keys(moved, "y", [(slide[0], -h * ARROW_TRAVEL), (slide[1], 0.0)], kind="cubic-out", local=False)
        cx, top, wide = w * 0.5, h * 0.26, w * 0.64
        shaft = h * 0.26
        points = [(cx - wide / 2, top), (cx + wide / 2, top), (cx + wide / 2, top + shaft),
                  (cx + wide * 0.7, top + shaft), (cx, top + shaft + h * 0.24),
                  (cx - wide * 0.7, top + shaft), (cx - wide / 2, top + shaft)]  # fmt: skip
        draw_shapes(cv, moved, [(_poly(_cut("weather-arrow", points, 4)), FRONT, INK, 5.0, 1.0)])
        if arrow:
            _letter(cv, moved, "weather", arrow, cx - wide / 2, top, wide, shaft, size, color="#fffaf0")
    if clock is not None:
        text, (a, b) = clock
        card = _gated(cv, g, a, b)
        cw, ch = w * 0.5, w * 0.26
        px, py = w - cw - w * 0.04, h - ch - w * 0.04
        draw_shapes(cv, card, _paper(_cut(f"weather-card-{text}", [(px, py), (px + cw, py), (px + cw, py + ch),
                                                                    (px, py + ch)], 3), CARD))  # fmt: skip
        _letter(cv, card, "weather", text, px, py, cw, ch, w * CLOCK_SIZE, color=INK)
    return g


def _clock_spans(clock: Sequence[tuple[float, str]]) -> list[tuple[str, float, float]]:
    """Each time of a clock and when it shows: until the next one, the last one on and on."""
    stops = [at for at, _ in clock[1:]] + [FOREVER]
    return [(text, at, stop) for (at, text), stop in zip(clock, stops, strict=True)]


def _check_thread(w: float, h: float, contact: str, clock, call: str, messages: Sequence[Message]) -> float:
    if not (checks.number(w) and w > 2 * BEZEL):
        raise ForecastError(f"a phone {w!r} wide is too small")
    if not (checks.number(h) and h > 2 * BEZEL):
        raise ForecastError(f"a phone {h!r} tall is too small")
    if not contact.strip():
        raise ForecastError("a thread needs a contact")
    _capitals(contact)
    _capitals(call)
    if not clock or any(b[0] <= a[0] for a, b in zip(clock, clock[1:], strict=False)):
        raise ForecastError(f"a thread needs a clock, its times rising, got {clock!r}")
    for text in (t for _, t in clock):
        _capitals(text)
    for m in messages:
        if not (m.text.strip() and checks.number(m.at) and m.at >= 0):
            raise ForecastError(f"a message needs words and a time from 0, got {m!r}")
        _capitals(m.text)
    if any(b.at < a.at for a, b in zip(messages, messages[1:], strict=False)):
        raise ForecastError("messages land in order")
    k = w / UNIT
    if BAR_SIZE * k < ink_meter.LEGIBLE_PX:
        raise ForecastError(f"a thread {w} wide is under the legibility floor of {ink_meter.LEGIBLE_PX}")
    return k


@register("prop", "collage-thread", summary="A phone open on an invented thread: a clock, a contact, bubbles, no app")
def thread(
    cv: Canvas,
    parent,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    contact: str,
    clock: Sequence[tuple[float, str]],
    call: str = "",
    messages: Sequence[Message] = (),
    tilt: float = 0.0,
) -> object:
    """A phone ``w`` by ``h`` with its top-left at ``x, y``, turned ``tilt`` degrees about its centre, open on a thread
    with ``contact``. ``clock`` is ``(at, text)`` rows for the top bar, ``call`` a strip naming who is on a live call,
    and each message lands at its time. Returns the group."""
    k = _check_thread(w, h, contact, clock, call, messages)
    page_w, page_h = w - 2 * BEZEL, h - 2 * BEZEL
    g = cv.group(parent, cv.uid("g"))
    page = phone(cv, g, x, y, w, h, screen=SCREEN, tilt=tilt)
    cv.rect(page, 0, 0, page_w, BAR_H * k, BAR, radius=14)
    for text, a, b in _clock_spans(clock):
        _letter(cv, _gated(cv, page, a, b), "thread-clock", text, 0, 0, page_w, BAR_H * k, BAR_SIZE * k, color=SCREEN)
    top = BAR_H * k
    cv.rect(page, 0, top, page_w, CONTACT_H * k, STRIP)
    _letter(cv, page, "thread", contact, 0, top, page_w, CONTACT_H * k, CONTACT_SIZE * k, color=INK)
    top += CONTACT_H * k
    if call:
        cv.rect(page, 0, top, page_w, CALL_H * k, CALL)
        _letter(cv, page, "thread", call, 0, top, page_w, CALL_H * k, CALL_SIZE * k, color=INK)
        top += CALL_H * k
    top += GAP * k
    size = MESSAGE_SIZE * k
    wide = page_w - 2 * PAD * k
    per_line = int((wide * 0.84 - 2 * BUBBLE_INSET) / (size * CARD_GLYPH))
    for m in messages:
        rows = _rows(m.text, per_line)
        tall = len(rows) * size * CARD_LEADING + 2 * MESSAGE_PAD * k
        longest = max(len(r) for r in rows)
        if longest > per_line or top + tall > page_h:
            raise ForecastError(f"{m.text!r} does not fit a page {page_w} by {page_h}")
        across = longest * size * CARD_GLYPH + 2 * BUBBLE_INSET + size
        left = page_w - PAD * k - across if m.mine else PAD * k
        shown = _gated(cv, page, m.at, FOREVER)
        cv.keys(shown, "y", [(m.at, RISE * k), (m.at + SLIDE, 0.0)], kind="cubic-out", local=False)
        bubble(cv, shown, m.text, left, top, across, tall, size=size, mine=m.mine)
        top += tall + GAP * k
    return g

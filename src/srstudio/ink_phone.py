"""The Ink phone: a chat on a held phone, drawn in the style's pen stroke for a shot that shows the screen
(:mod:`srstudio.ink`).

The contact's name sits in the header, my bubbles are ink with white lettering on the right, theirs are white with
an ink outline on the left, and each bubble arrives at its own moment. The delivery status (:data:`STATUS_TEXT`)
sits under the last of my bubbles and changes on the shot's clock; the typing dots pulse in their own bubble. Every
time is seconds into the take, like the rest of the style. The phone's chin carries the signature code (ADR 0001).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import checks, look, signature
from .canvas import Canvas
from .errors import SrstudioError
from .ink import ellipse, group, path
from .registry import register

__all__ = ["Bubble", "PhoneError", "STATUS_TEXT", "phone", "phone_shot"]

STATUS_TEXT = {"sending": "Sending...", "failed": "! Not delivered", "sent": "Delivered", "read": "Read"}
CONTACT_MAX = 16
TEXT_MAX = 60
BODY = (270, 250, 540, 800)  # x, y, width, height: under the caption band of the square frame
BEZEL, HEADER, CHIN = 22, 96, 70
SIZE, LINE, PER_LINE = 44, 52, 15  # bubble lettering: size, line height, characters per line
BUBBLE_W, PAD, GAP = 360, 16, 16
STATUS_H, TYPING_H = 48, 76


class PhoneError(SrstudioError, ValueError):
    """A contact, a bubble, a status or a typing span the phone cannot show."""


@dataclass(frozen=True)
class Bubble:
    """One message: ``text`` (1 to :data:`TEXT_MAX` characters), ``mine`` (sent by the holder) and the second it
    arrives on screen."""

    text: str
    mine: bool = True
    at: float = 0.0


def _check_time(at: float, what: str) -> float:
    return checks.second(at, PhoneError, f"{what}: a time is seconds into the take, from 0, got {at!r}")


def _text(cv: Canvas, parent, value: str, x, y, w, h, size, color: str, align: str = "center") -> None:
    """``value`` wrapped at words in the box, its size in whole pixels."""
    look.text(
        cv, parent, value, x, y, round(w), round(h), size, color, align=align, wrap="word", asset="txt", layer="label"
    )


def _visible(cv: Canvas, node, start: float, end: float | None = None) -> None:
    """Shown from ``start`` (from the first frame when it is 0) until ``end``, if any."""
    keys = [(0.0, 1.0)] if start == 0 else [(0.0, 0.0), (start, 1.0)]
    if end is not None:
        keys.append((end, 0.0))
    if len(keys) == 1:
        node.opacity = 1
        return
    cv.keys(node, "opacity", keys)


def _box(x: float, y: float, w: float, h: float, r: float = 22) -> str:
    return (f"M {x + r} {y} L {x + w - r} {y} Q {x + w} {y} {x + w} {y + r} L {x + w} {y + h - r} "
            f"Q {x + w} {y + h} {x + w - r} {y + h} L {x + r} {y + h} Q {x} {y + h} {x} {y + h - r} "
            f"L {x} {y + r} Q {x} {y} {x + r} {y} Z")  # fmt: skip


def _size(text: str) -> tuple[float, float]:
    lines = max(1, math.ceil(len(text) / PER_LINE))
    width = BUBBLE_W if lines > 1 else min(BUBBLE_W, len(text) * SIZE * 0.5 + 2 * PAD + 10)
    return width, lines * LINE + 2 * PAD


def _validate(contact, bubbles, status, typing) -> None:
    if not contact.strip() or len(contact) > CONTACT_MAX:
        raise PhoneError(f"the contact is 1 to {CONTACT_MAX} characters, got {len(contact)}")
    if not bubbles:
        raise PhoneError("a chat needs at least one bubble")
    last = 0.0
    for b in bubbles:
        if not b.text.strip() or len(b.text) > TEXT_MAX:
            raise PhoneError(f"a bubble is 1 to {TEXT_MAX} characters, got {len(b.text)}: {b.text!r}")
        at = _check_time(b.at, f"the bubble {b.text!r}")
        if at < last:
            raise PhoneError(f"bubbles arrive in order: {b.text!r} at {at} comes after one at {last}")
        last = at
    if status:
        if not any(b.mine for b in bubbles):
            raise PhoneError("a status sits under one of mine: the chat has no bubble of mine")
        times = [_check_time(t, "a status") for t, _ in status]
        if any(b <= a for a, b in zip(times, times[1:], strict=False)):
            raise PhoneError(f"each status follows the previous one in time, got {times}")
        unknown = sorted({k for _, k in status if k not in STATUS_TEXT})
        if unknown:
            raise PhoneError(f"unknown status {unknown}; one of {tuple(STATUS_TEXT)}")
    if typing is not None:
        a, b = typing
        if _check_time(a, "the typing start") >= _check_time(b, "the typing end"):
            raise PhoneError(f"the typing span ends after it starts, got {typing}")


@register(
    "prop",
    "ink-phone",
    summary="A held phone with a chat: the contact, my and their bubbles arriving in turn, a delivery status that "
    "changes and the typing dots",
    style="ink",
)
def phone(
    cv: Canvas,
    parent,
    contact: str,
    bubbles: Sequence[Bubble],
    *,
    status: Sequence[tuple[float, str]] = (),
    typing: tuple[float, float] | None = None,
):
    """The phone under the caption band: ``contact`` (1 to :data:`CONTACT_MAX` characters) in the header,
    ``bubbles`` stacked from the top in arrival order, each ``(seconds, kind)`` in ``status`` shown under the last
    of my bubbles until the next one (from that bubble's arrival: one replaced before it arrives never shows), and
    ``typing`` (``(start, end)``) pulsing three dots in their bubble, in the slot of the first bubble that arrives
    at or after its end (after the last bubble when none does)."""
    _validate(contact, bubbles, status, typing)
    x0, y0, w, h = BODY
    sx, sy, sw_, sh = x0 + BEZEL, y0 + BEZEL, w - 2 * BEZEL, h - BEZEL - CHIN
    top, bottom = sy + HEADER + GAP, sy + sh - GAP
    slots: list[float] = []
    y: float = top
    last_mine = max((i for i, b in enumerate(bubbles) if b.mine), default=None)
    typing_slot = None
    for i, b in enumerate(bubbles):
        if typing is not None and typing_slot is None and b.at >= typing[1] and not b.mine:
            typing_slot = y  # the dots hold the place their reply arrives in
        slots.append(y)
        y += _size(b.text)[1] + GAP
        if i == last_mine and status:
            y += STATUS_H
    if typing is not None and typing_slot is None:
        typing_slot = y
        y += TYPING_H + GAP
    if y - GAP > bottom:
        raise PhoneError(f"the chat does not fit the screen: {y - GAP - top:.0f} px of {bottom - top:.0f}")

    g = group(cv, parent)
    path(cv, g, _box(x0 + 12, y0 + 14, w, h, 56), cv.shade, sw=0)
    path(cv, g, _box(x0, y0, w, h, 56), cv.white, sw=4)
    path(cv, g, _box(sx, sy, sw_, sh, 30), cv.white, sw=2.5)
    path(cv, g, f"M {sx} {sy + HEADER} L {sx + sw_} {sy + HEADER}", sw=2.5)
    path(cv, g, f"M {sx + 30} {sy + HEADER / 2 - 14} L {sx + 16} {sy + HEADER / 2} L {sx + 30} {sy + HEADER / 2 + 14}",
         sw=3.5)  # fmt: skip
    ellipse(cv, g, sx + 52, sy + HEADER / 2 - 26, 52, 52, cv.shade, sw=2.5)
    _text(cv, g, contact[0].upper(), sx + 52, sy + HEADER / 2 - 26, 52, 52, 32, cv.ink)
    _text(cv, g, contact, sx + 118, sy + 12, sw_ - 140, HEADER - 24, 44, cv.ink, align="start")
    for b, by in zip(bubbles, slots, strict=True):
        bw, bh = _size(b.text)
        bx = sx + sw_ - 18 - bw if b.mine else sx + 18
        node = group(cv, g)
        path(cv, node, _box(bx, by, bw, bh), cv.ink if b.mine else cv.white, sw=0 if b.mine else 3)
        _text(cv, node, b.text, bx + PAD, by + PAD, bw - 2 * PAD, bh - 2 * PAD, SIZE, cv.white if b.mine else cv.ink)
        _visible(cv, node, b.at)
    if status and last_mine is not None:
        mine = bubbles[last_mine]
        ly = slots[last_mine] + _size(mine.text)[1] + 4
        for k, (at, kind) in enumerate(status):
            end = status[k + 1][0] if k + 1 < len(status) else None
            if end is not None and end <= mine.at:
                continue  # replaced before the bubble it sits under arrives
            node = group(cv, g)
            _text(cv, node, STATUS_TEXT[kind], sx + 18, ly, sw_ - 36, STATUS_H - 4, 36, cv.ink, align="end")
            _visible(cv, node, max(float(at), mine.at), end)
    if typing is not None and typing_slot is not None:
        start, end = (float(v) for v in typing)
        dots = group(cv, g)
        path(cv, dots, _box(sx + 18, typing_slot, 130, TYPING_H, 30), cv.white, sw=3)
        for d in range(3):
            dot = ellipse(cv, dots, sx + 44 + d * 30, typing_slot + TYPING_H / 2 - 9, 18, 18, cv.ink, sw=0)
            keys, t, up = [(start, 0.3)], start + 0.15 * d + 0.2, True
            while t < end:
                keys.append((round(t, 3), 1.0 if up else 0.3))
                t, up = t + 0.3, not up
            keys.append((end, 0.3))
            cv.keys(dot, "opacity", keys, hold=False)
        _visible(cv, dots, start, end)
    ellipse(cv, g, x0 + w / 2 - 14, y0 + h - CHIN / 2 - 14, 28, 28, cv.white, sw=2.5)
    signature.code(cv, g, x0 + w - 40, y0 + h - CHIN / 2 - 6, 12, align="end", color=cv.shade)
    return g


@register(
    "location", "ink-phone-shot", summary="The phone held over the desk line, the cactus in the corner", style="ink"
)
def phone_shot(cv: Canvas, parent, contact: str, bubbles: Sequence[Bubble], **chat):
    """The shot of the screen: the desk line and the signature cactus behind :func:`phone` (``chat`` is its
    ``status`` and ``typing``)."""
    path(cv, parent, "M 15 986 L 1065 986", sw=2)
    signature.cactus(cv, parent, 940, 986, 0.45)
    return phone(cv, parent, contact, bubbles, **chat)

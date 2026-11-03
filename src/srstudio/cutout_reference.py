"""Cutout, a reference given from home: cue cards, two bills, and a blazer over a bathrobe.

Each prop is drawn at ``x``, ``y`` in its parent's pixels and keyed on the episode's clock; the worn one is drawn in the
actor's own units. Every refusal is a :class:`CutoutHandedError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import _cutout_contracts
from .canvas import Canvas
from .cutout_handed import PAGE, CutoutHandedError, _check_scale, _check_spans
from .registry import register

__all__ = ["banknotes", "cue_cards", "robe_and_blazer"]

CUE_CARD_CHARS = 14


@register(
    "prop",
    "cue-cards",
    style="cutout",
    summary="A stack of cue cards held up, the top card lettered by hand",
    contract=_cutout_contracts.contract('cue-cards'),
)
def cue_cards(
    cv: Canvas,
    parent,
    x=540,
    y=900,
    *,
    words: Sequence[str] = ("SAY YES",),
    spans: Sequence[tuple[float, float]] = (),
    scale: float = 1.0,
    id: str = "cue-cards",
):
    """The stack's centre is (``x``, ``y``), 300 by 200. Each of ``words`` is a top card: with several, ``spans`` says
    when each one shows, in rising order, one span a card."""
    cv.require_font("a cue card's words are set in it", CutoutHandedError)
    _check_scale(scale)
    words = list(words)
    if not words or any(not isinstance(w, str) or not 0 < len(w.strip()) <= CUE_CARD_CHARS for w in words):
        raise CutoutHandedError(f"cue cards carry 1 to {CUE_CARD_CHARS} characters each, got {words!r}")
    spans = list(spans)
    if spans:
        _check_spans(spans, "card spans")
    if len(words) > 1 and len(spans) != len(words):
        raise CutoutHandedError(f"{len(words)} cards need {len(words)} spans, got {len(spans)}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    for k, turn in enumerate((5, -3)):
        cv.rect(cv.group(g, f"{id}-under-{k}", rotation=turn), -150, -100, 300, 200, "#EFEBDD", ink, 3.5)
    for k, word in enumerate(words):
        card = cv.group(g, f"{id}-card-{k}")
        if spans:
            cv.gate(card, [spans[k]])
        cv.rect(card, -150, -100, 300, 200, PAGE, ink, 4)
        cv.text(card, f"{id}-word-{k}", word, -140, -60, 280, 120, 48, "#21305C")
    return g


BILL = "#A6C29A"


@register(
    "prop",
    "banknotes",
    style="cutout",
    summary="A pair of plain banknotes, fanned, lettered with their value",
    contract=_cutout_contracts.contract('banknotes'),
)
def banknotes(
    cv: Canvas, parent, x=540, y=900, *, value: str = "20", count: int = 2, scale: float = 1.0, id: str = "banknotes"
):
    """The fan's centre is (``x``, ``y``), each bill 220 by 100."""
    cv.require_font("a bill's value is set in it", CutoutHandedError)
    _check_scale(scale)
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 5:
        raise CutoutHandedError(f"a fan holds 1 to 5 bills, got {count!r}")
    if not isinstance(value, str) or not 0 < len(value.strip()) <= 4:
        raise CutoutHandedError(f"a bill's value has 1 to 4 characters, got {value!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    for k in range(count):
        bill = cv.group(g, f"{id}-{k}", x=(k - (count - 1) / 2) * 28, rotation=(k - (count - 1) / 2) * 7)
        cv.rect(bill, -110, -50, 220, 100, BILL, ink, 4, radius=4)
        cv.rect(bill, -96, -38, 192, 76, "#BCD3B0", "#5F7D57", 2.5)
        cv.ellipse(bill, -30, -30, 60, 60, BILL, "#5F7D57", 2.5)
        cv.text(bill, f"{id}-value-{k}", value, -30, -30, 60, 60, 30, "#3F5C39")
    return g


ROBE = "#E5B7BE"
ROBE_DARK = "#CF9AA3"
BLAZER = "#3C4A5C"
BLAZER_DARK = "#2C3746"


@register(
    "prop",
    "robe-and-blazer",
    style="cutout",
    summary="A blazer over a bathrobe, worn on a Cutout actor",
    contract=_cutout_contracts.contract('robe-and-blazer'),
)
def robe_and_blazer(cv: Canvas, parent, *, id: str = "robe-and-blazer"):
    """Drawn in the actor's own units, from the shoulders to the waist, so hang it on ``actor.group``: a video call's
    worth of dressing, and the terry collar still shows."""
    ink = cv.ink
    g = cv.group(parent, id)
    cv.path(g, "M-74 322 L-80 146 Q-78 118 -46 114 L46 114 Q78 118 80 146 L74 322Z", ROBE, ink, 4)
    for side in (-1, 1):
        cv.path(g, f"M{side * 84} 146 Q{side * 80} 118 {side * 46} 114 L{side * 30} 200 L{side * 26} 324 "
                   f"L{side * 80} 324Z", BLAZER, ink, 4)  # fmt: skip
        cv.path(g, f"M{side * 62} 118 L{side * 84} 170 L{side * 54} 190 L{side * 60} 224 L{side * 30} 214Z",
                BLAZER_DARK, ink, 3)  # fmt: skip
    cv.path(g, "M-60 110 Q-30 100 -14 114 L6 222 L-6 232 L-34 230 Q-58 170 -60 110Z", ROBE_DARK, ink, 3.5)
    cv.path(g, "M60 110 Q30 100 14 114 L-6 222 L6 232 L34 230 Q58 170 60 110Z", ROBE_DARK, ink, 3.5)
    for x, y in [(-40, 130), (-34, 170), (-24, 206), (40, 130), (34, 170), (24, 206)]:
        cv.path(g, f"M{x - 8} {y} q8 -8 16 0", stroke=ROBE, sw=3)
    cv.rect(g, -32, 234, 64, 22, ROBE_DARK, ink, 3.5, radius=8)
    cv.path(g, "M-8 254 L-22 322 L-6 322 L2 256 M8 254 L24 322 L8 322 L0 256Z", ROBE_DARK, ink, 3)
    return g

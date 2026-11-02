"""Small Print's marks: the channel's colours, the typed-question card and the finding stamp (ADR 0195).

They draw on any canvas with nothing of the show around them, so importing the library registers them; the show that
places them is :mod:`srstudio.smallprint`.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import _presentation_contracts as dc
from . import host_kit
from .errors import SrstudioError
from .registry import register

__all__ = [
    "ACTIVE",
    "COPPER",
    "INK",
    "LEFT",
    "PAPER",
    "RIGHT",
    "RULED",
    "SHADE",
    "STAMP",
    "Measure",
    "ScriptError",
    "Stamp",
    "card",
    "label",
    "stamp",
    "wrap",
]

# The channel's own colours: a page of fine print, its ink, the stamp and the ruled lines. Nothing here is Okayville's
# or News Compiler's: those are warm-dark and lit-screen; this is a sheet of paper.
PAPER, INK, STAMP, RULED, SHADE = "#F4F0E6", "#1C2A4A", "#A82E22", "#9AA6BF", "#E2DACA"
ACTIVE = "#FF9F7A"  # the spoken word in a caption: the stamp's red, lifted to read on the ink band
COPPER = "#B5683B"
LEFT, RIGHT = host_kit.TEXT_LEFT, host_kit.TEXT_RIGHT
CARD_Y, CARD_SIZE, CARD_PAD = 236.0, 44.0, 26.0
STAMP_SIZE, SOURCE_SIZE = 58.0, 30.0
STAMP_Y = 980.0  # the stamp's top on a panel: low, so the diagram above it is the picture
TILT = -4.0  # degrees a stamp lands at
LANDS_FROM = 1.6  # the scale a stamp comes down from, when the frame has room for it


class ScriptError(SrstudioError, ValueError):
    """A beat or a script this show cannot stage."""


@dataclass(frozen=True)
class Stamp:
    """The finding: one line in the stamp's capitals, and the named source and year it comes from."""

    text: str
    source: str


Measure = Callable[[str, float], float]


def label(cv, parent, text: str, x, y, w, h, size, colour, align: Any = "start") -> None:
    """One line of ``text`` in the box ``x, y, w, h``, never wrapped: the callers measure and break it."""
    cv.text(parent, cv.uid("sp-text"), text, x, y, round(w), round(h), size, color=colour, align=align, wrap="none")


def wrap(text: str, size: float, width: float, measure: Measure) -> list[str]:
    """``text`` in lines no wider than ``width`` at ``size``, or :class:`ScriptError` for a word that cannot fit."""
    rows: list[str] = []
    for word in text.split():
        if measure(word, size) > width:
            raise ScriptError(f"{word!r} is wider than {width:.0f} px at {size}")
        if rows and measure(f"{rows[-1]} {word}", size) <= width:
            rows[-1] = f"{rows[-1]} {word}"
        else:
            rows.append(word)
    return rows


@register(
    "graphic",
    "smallprint-card",
    summary="The question as people type it, in a search box at the top of the frame",
    contract=dc.contract("smallprint-card"),
)
def card(cv, parent, question: str, start: float, end: float, measure: Measure, id: str = "smallprint-card"):
    """The question in a search box over his head from ``start`` to ``end``: paper, an ink rule, a lens, two lines at
    most. Returns its group."""
    if end <= start:
        raise ScriptError(f"the card needs time on screen, got {start}..{end}")
    host_kit.check_copy(question)
    inner = RIGHT - LEFT - 2 * CARD_PAD - 70.0
    size = CARD_SIZE
    rows = wrap(question, size, inner, measure)
    while len(rows) > 2 and size > 32.0:
        size -= 2.0
        rows = wrap(question, size, inner, measure)
    if len(rows) > 2:
        raise ScriptError(f"{question!r} does not fit the card in two lines")
    tall = size * 1.25
    h = len(rows) * tall + 2 * CARD_PAD
    g = cv.group(parent, id, start=start, end=end, x=0.0, y=-12.0)
    cv.rect(g, LEFT + 6, CARD_Y + 10, RIGHT - LEFT, h, "#00000040", radius=h / 2 if len(rows) == 1 else 34.0)
    cv.rect(g, LEFT, CARD_Y, RIGHT - LEFT, h, PAPER, stroke=INK, sw=5.0, radius=h / 2 if len(rows) == 1 else 34.0)
    lens_x, lens_y = LEFT + CARD_PAD + 20.0, CARD_Y + h / 2 - 6.0
    cv.ellipse(g, lens_x - 16, lens_y - 16, 32, 32, PAPER, stroke=INK, sw=6.0)
    cv.line(g, lens_x + 11, lens_y + 11, lens_x + 24, lens_y + 24, INK, 7.0)
    for i, row in enumerate(rows):
        label(cv, g, row, LEFT + CARD_PAD + 66.0, CARD_Y + CARD_PAD + i * tall, inner, tall, size, INK)
    cv.keys(g, "y", [(start, -12.0), (start + 0.18, 0.0)], hold=False, kind="cubic-out", local=False)
    return g


def spread(text: str, size: float, measure: Measure) -> float:
    """How wide a stamp of ``text`` at ``size`` stands across the frame, turned :data:`TILT` degrees."""
    turn = math.radians(abs(TILT))
    return (measure(text, size) + 80.0) * math.cos(turn) + size * 1.6 * math.sin(turn)


@register(
    "graphic",
    "smallprint-stamp",
    summary="A finding stamped in red on a panel, its source in ink under it",
    contract=dc.contract("smallprint-stamp"),
)
def stamp(cv, parent, finding: Stamp, start: float, end: float, measure: Measure):
    """``finding`` stamped at ``start``, a little crooked, the way a stamp lands, its source under it. Returns its
    group."""
    if end <= start:
        raise ScriptError(f"the stamp needs time on screen, got {start}..{end}")
    room = RIGHT - LEFT
    size = STAMP_SIZE
    while spread(finding.text, size, measure) > room and size > 36.0:
        size -= 2.0
    if spread(finding.text, size, measure) > room:
        raise ScriptError(f"{finding.text!r} does not fit a stamp")
    wide, tall = measure(finding.text, size) + 80.0, size * 1.6
    cx, cy = (LEFT + RIGHT) / 2, STAMP_Y + tall / 2  # the safe area's middle, which is left of the frame's
    x = round(cx - wide / 2, 2)
    g = cv.group(
        parent, cv.uid("smallprint-stamp"), start=start, end=end, x=cx, y=cy, anchorX=cx, anchorY=cy, rotation=TILT
    )
    cv.rect(g, x, STAMP_Y, wide, tall, "#F4F0E6E6", stroke=STAMP, sw=7.0, radius=10.0)
    cv.rect(g, x + 10, STAMP_Y + 10, wide - 20, tall - 20, "#00000000", stroke=STAMP, sw=2.5, radius=6.0)
    label(cv, g, finding.text, x, STAMP_Y, wide, tall, size, STAMP, "center")
    cv.pop_in(
        g, start, from_=min(LANDS_FROM, room / spread(finding.text, size, measure)), over=0.94, rise=0.09, settle=0.2
    )
    cv.keys(g, "opacity", [(start, 0.0), (start + 0.06, 1.0)], hold=False, local=False)
    source = cv.group(parent, cv.uid("smallprint-source"), start=start + 0.2, end=end)
    rows = wrap(finding.source, SOURCE_SIZE, RIGHT - LEFT, measure)
    for i, row in enumerate(rows[:2]):
        label(cv, source, row, LEFT, STAMP_Y + tall + 34.0 + i * 38.0, RIGHT - LEFT, 38.0, SOURCE_SIZE, INK, "center")
    return g

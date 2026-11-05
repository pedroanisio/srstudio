"""Small Print's marks: the channel's colours, the typed-question card and the finding stamp (ADR 0195).

They draw on any canvas with nothing of the show around them, so importing the library registers them; the show that
places them is :mod:`srstudio.smallprint`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
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
    "REPEATS",
    "RIGHT",
    "RULED",
    "SHADE",
    "STAMP",
    "Measure",
    "ScriptError",
    "Stamp",
    "card",
    "label",
    "repeats",
    "source_chip",
    "stamp",
    "stamp_layout",
    "stamp_reach",
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

REPEATS = 0.5  # the most of a stamp's own words its caption may already say: more, and it is read twice
_SMALL = frozenset(
    "a an and are as at be been but by can could did do does even for from had has have he her his how i in into is it"
    " its just not of on only or our out over said say says she so than that the their them then there these they"
    " this those to up very was we were what when which who why will with would you".split()
)


def _stem(word: str) -> str:
    for end in ("ing", "ed", "es", "s"):
        if word.endswith(end) and len(word) - len(end) >= 3:
            return word[: -len(end)]
    return word


def _words(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _SMALL]


def repeats(text: str, line: str) -> float:
    """The share of a stamp's ``text`` that its caption ``line`` already says: its own words (not the small ones that
    join them), each cut to its stem, that the line also has. A stamp over :data:`REPEATS` is a second read of one
    idea; it should carry what the line does not say. :class:`ScriptError` for a stamp with no word of its own."""
    own = _words(text)
    if not own:
        raise ScriptError(f"the stamp {text!r} has no word of its own")
    said = set(_words(line))
    return sum(w in said for w in own) / len(own)


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


def stamp_layout(
    finding: Stamp, measure: Measure, top: float = STAMP_Y
) -> tuple[float, tuple[float, float, float, float], list[tuple[float, float, float, float]], list[str]]:
    """Where :func:`stamp` puts ``finding`` with its top at ``top``: its size, the frame box the turned stamp covers,
    a box for each source row, and the rows. Or :class:`ScriptError` for a finding no stamp fits."""
    room = RIGHT - LEFT
    size = STAMP_SIZE
    while spread(finding.text, size, measure) > room and size > 36.0:
        size -= 2.0
    if spread(finding.text, size, measure) > room:
        raise ScriptError(f"{finding.text!r} does not fit a stamp")
    wide, tall = measure(finding.text, size) + 80.0, size * 1.6
    cx, cy = (LEFT + RIGHT) / 2, top + tall / 2
    turn = math.radians(abs(TILT))
    half_w = (wide * math.cos(turn) + tall * math.sin(turn)) / 2
    half_h = (wide * math.sin(turn) + tall * math.cos(turn)) / 2
    rows = wrap(finding.source, SOURCE_SIZE, room, measure)[:2]
    sources = []
    for i, row in enumerate(rows):
        w = measure(row, SOURCE_SIZE)
        y = top + tall + 34.0 + i * 38.0
        sources.append((cx - w / 2, y, cx + w / 2, y + 38.0))
    return size, (cx - half_w, cy - half_h, cx + half_w, cy + half_h), sources, rows


def stamp_reach(finding: Stamp, measure: Measure) -> tuple[float, float]:
    """How far :func:`stamp`'s turned text box reaches above its middle (its half height on the frame, as the engine
    measures a text layer against the safe area) and the stamp's own half height."""
    size, _, _, _ = stamp_layout(finding, measure)
    wide, tall = measure(finding.text, size) + 80.0, size * 1.6
    turn = math.radians(abs(TILT))
    return (round(wide) * math.sin(turn) + round(tall) * math.cos(turn)) / 2, tall / 2


CHIP_PAD = (18.0, 6.0)  # the paper chip under a source reaches this far past its rows, across and down


def source_chip(sources: Sequence[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    """The paper chip :func:`stamp` lays under the source rows ``sources`` (boxes from :func:`stamp_layout`)."""
    if not sources:
        raise ScriptError("a source chip needs a source row")
    px, py = CHIP_PAD
    return (min(b[0] for b in sources) - px, sources[0][1] - py, max(b[2] for b in sources) + px, sources[-1][3] + py)


@register(
    "graphic",
    "smallprint-stamp",
    summary="A finding stamped in red on a panel, its source in ink under it",
    contract=dc.contract("smallprint-stamp"),
)
def stamp(
    cv,
    parent,
    finding: Stamp,
    start: float,
    end: float,
    measure: Measure,
    top: float = STAMP_Y,
    chip: bool = False,
    ceiling: float | None = None,
):
    """``finding`` stamped at ``start``, a little crooked, the way a stamp lands, its source under it, the stamp's
    top at ``top``. With ``chip`` the source sits on a paper chip, to read over a picture. ``ceiling`` is the highest
    row the stamp may reach as it comes down onto its place (the safe area's top), so it lands from less high when
    it lands near the top. Returns its group."""
    if end <= start:
        raise ScriptError(f"the stamp needs time on screen, got {start}..{end}")
    room = RIGHT - LEFT
    size, _, sources, rows = stamp_layout(finding, measure, top)
    wide, tall = measure(finding.text, size) + 80.0, size * 1.6
    cx, cy = (LEFT + RIGHT) / 2, top + tall / 2  # the safe area's middle, which is left of the frame's
    x = round(cx - wide / 2, 2)
    g = cv.group(
        parent, cv.uid("smallprint-stamp"), start=start, end=end, x=cx, y=cy, anchorX=cx, anchorY=cy, rotation=TILT
    )
    cv.rect(g, x, top, wide, tall, "#F4F0E6E6", stroke=STAMP, sw=7.0, radius=10.0)
    cv.rect(g, x + 10, top + 10, wide - 20, tall - 20, "#00000000", stroke=STAMP, sw=2.5, radius=6.0)
    label(cv, g, finding.text, x, top, wide, tall, size, STAMP, "center")
    lands = min(LANDS_FROM, room / spread(finding.text, size, measure))
    if ceiling is not None:
        reach, _ = stamp_reach(finding, measure)
        if cy - reach < ceiling:
            raise ScriptError(f"a stamp at row {top} reaches over its ceiling at row {ceiling}")
        lands = min(lands, (cy - ceiling) / reach)
    cv.pop_in(g, start, from_=lands, over=0.94, rise=0.09, settle=0.2)  # whole from its first frame: a stamp slams
    source = cv.group(parent, cv.uid("smallprint-source"), start=start + 0.2, end=end)
    if chip and sources:
        x0, y0, x1, y1 = source_chip(sources)
        cv.rect(source, x0, y0, x1 - x0, y1 - y0, "#F4F0E6EB", radius=(y1 - y0) / 2 if len(sources) == 1 else 18.0)
    for i, row in enumerate(rows):
        label(cv, source, row, LEFT, top + tall + 34.0 + i * 38.0, RIGHT - LEFT, 38.0, SOURCE_SIZE, INK, "center")
    return g

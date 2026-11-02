"""Soft inbox: what a phone's ``screen`` shows of mail, of a call and of its own charge, all of it invented.

Each one draws in a phone's glass, the box from (-65, -130) to (65, 130) of :func:`srstudio.soft_props.phone`, and takes
``x``, ``y`` and ``scale`` so it can also stand alone. There is no app in any of them: an envelope with a count, a plain
list of subjects, a caller over a red and a green button, and a percentage over a plain battery, which is no phone's
status bar. No name, no address, no logo.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import NamedTuple

from . import _soft_scene_contracts as dc
from . import checks
from .canvas import Canvas
from .registry import register
from .soft_props import SoftPropError

__all__ = ["Count", "Level", "battery_screen", "call_screen", "charge_width", "mail_list", "mail_screen"]

BADGE = "#C8321F"  # white letters on it read at 5.4:1
PAPER = "#F3E9D6"
GLASS = "#DCE7EE"
MARKED = "#FFD966"
ROW_INK = "#2B2A28"
MAX_COUNT = 7  # characters a badge holds
MAX_ROW = 22  # characters a subject holds over two lines
MAX_ROWS = 4
MAX_CALLER = 16  # characters a caller holds over two lines
BATTERY_OK = "#3F9C5A"
BATTERY_GLASS = "#F3F6F8"
LOW = 20  # percent: from here down the charge and its number go red
CELL = (-46.0, 22.0, 84.0, 44.0)  # x, y, width and height the charge fills, in the glass
SLIVER = 4.0  # px of charge left to see at the very bottom
GLASS_WIDE = 130  # the glass's width
NUMBER, NUMBER_PAD = 46, 4.0  # a battery number's size, and its box's margin each side of a measured number


class Count(NamedTuple):
    """From ``at`` until ``until`` the badge reads ``text``."""

    text: str
    at: float
    until: float


class Level(NamedTuple):
    """From ``at`` until ``until`` the battery reads ``percent``; with ``number`` False only the charge shows, for a
    phone whose lettering would leave the safe area in that shot."""

    percent: int
    at: float
    until: float
    number: bool = True


def _place(what: str, x: float, y: float, scale: float) -> None:
    if not (checks.number(x) and checks.number(y)):
        raise SoftPropError(f"{what}'s place must be numbers, got {x!r}, {y!r}")
    if not (checks.number(scale) and scale > 0):
        raise SoftPropError(f"{what}'s scale must be a positive number, got {scale!r}")


@register(
    "prop",
    "soft-mail-screen",
    contract=dc.contract('soft-mail-screen'),
    summary="A phone's glass: one envelope and a red badge whose count ticks up",
)
def mail_screen(
    cv: Canvas,
    parent,
    x: float = 0,
    y: float = 0,
    *,
    counts: Sequence[Count] = (Count("41,382", 0.0, 1.0), Count("41,383", 1.0, 2.0)),
    scale: float = 1,
    id: str = "soft-mail-screen",
):
    """An envelope in the glass and a badge at its corner, reading each of ``counts`` in turn."""
    _place("a mail screen", x, y, scale)
    rows = list(counts)
    if not rows:
        raise SoftPropError("a mail screen counts something: give it at least one count")
    for row in rows:
        if not (checks.number(row.at) and checks.number(row.until) and row.at < row.until):
            raise SoftPropError(f"a count shows for some time, got {row!r}")
        if not row.text.strip() or len(row.text) > MAX_COUNT:
            raise SoftPropError(f"a badge reads 1 to {MAX_COUNT} characters, got {row.text!r}")
    if any(a.until > b.at for a, b in zip(rows, rows[1:], strict=False)):
        raise SoftPropError(f"counts run in order and never overlap, got {rows!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    ink = cv.ink
    cv.rect(g, -65, -130, 130, 260, GLASS, radius=14)
    cv.rect(g, -50, -30, 100, 72, PAPER, ink, 3, radius=8)
    cv.line(g, -48, -28, 0, 12, ink, 3)
    cv.line(g, 48, -28, 0, 12, ink, 3)
    cv.rect(g, -32, -62, 88, 34, BADGE, ink, 3, radius=17)
    for k, row in enumerate(rows):
        shown = cv.group(g, f"{id}-count-{k}")
        cv.gate(shown, [(row.at, row.until)])
        cv.text(shown, f"{id}-text-{k}", row.text, -30, -60, 84, 30, 18, color="#FFFFFF")
    return g


@register(
    "prop",
    "soft-mail-list",
    contract=dc.contract('soft-mail-list'),
    summary="A phone's glass: a plain list of subjects that stops on the marked one",
)
def mail_list(
    cv: Canvas,
    parent,
    x: float = 0,
    y: float = 0,
    *,
    rows: Sequence[str] = ("TOWING NOTICE", "LEASE ENDED", "WELCOME TO\nTHE TEAM!"),
    marked: int | None = None,
    scroll: Sequence[tuple[float, float]] = (),
    scale: float = 1,
    id: str = "soft-mail-list",
):
    """``rows`` from the top of the glass, row ``marked`` lit. ``scroll`` is (time, px) keys of the list's offset."""
    _place("a mail list", x, y, scale)
    if not 1 <= len(rows) <= MAX_ROWS:
        raise SoftPropError(f"a mail list shows 1 to {MAX_ROWS} rows, got {len(rows)}")
    for row in rows:
        if not row.strip() or len(row) > MAX_ROW or row.count("\n") > 1:
            raise SoftPropError(f"a row reads 1 to {MAX_ROW} characters on at most two lines, got {row!r}")
    if marked is not None and not 0 <= marked < len(rows):
        raise SoftPropError(f"row {marked!r} is not on a list of {len(rows)}")
    if any(not (checks.number(at) and checks.number(px)) for at, px in scroll):
        raise SoftPropError(f"a scroll is (time, px) keys, got {scroll!r}")
    if any(a[0] >= b[0] for a, b in zip(scroll, scroll[1:], strict=False)):
        raise SoftPropError(f"a scroll's keys run in order, got {scroll!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -65, -130, 130, 260, "#FFFFFF", radius=14)
    page = cv.group(g, f"{id}-page")
    if scroll:
        cv.keys(page, "y", list(scroll), False)
    top = -116.0
    for k, row in enumerate(rows):
        lit = k == marked
        fill, stroke, sw = (MARKED, cv.ink, 2) if lit else ("#EEF1F3", None, 0)
        cv.rect(page, -60, top, 120, 52, fill, stroke, sw, radius=8)
        cv.text(page, f"{id}-row-{k}", row, -56, top + 2, 112, 48, 12, color=ROW_INK)
        top += 58.0
    return g


@register(
    "prop",
    "soft-call-screen",
    contract=dc.contract('soft-call-screen'),
    summary="A phone's glass ringing: a caller over a red and a green round button",
)
def call_screen(
    cv: Canvas,
    parent,
    x: float = 0,
    y: float = 0,
    *,
    caller: str = "UNKNOWN\nNUMBER",
    pressed: float | None = None,
    scale: float = 1,
    id: str = "soft-call-screen",
):
    """``caller`` over two buttons, red on the left at (-34, 62) and green on the right. At ``pressed`` the red one
    goes dark."""
    _place("a call screen", x, y, scale)
    if not caller.strip() or len(caller) > MAX_CALLER or caller.count("\n") > 1:
        raise SoftPropError(f"a caller reads 1 to {MAX_CALLER} characters on at most two lines, got {caller!r}")
    if pressed is not None and not checks.number(pressed):
        raise SoftPropError(f"a press happens at a time, got {pressed!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    ink = cv.ink
    cv.rect(g, -65, -130, 130, 260, "#26343C", radius=14)
    cv.text(g, f"{id}-caller", caller, -60, -96, 120, 76, 19, color="#FFFFFF")
    cv.ellipse(g, -56, 40, 44, 44, BADGE, ink, 3)
    cv.line(g, -41, 55, -27, 69, "#FFFFFF", 5)
    cv.line(g, -27, 55, -41, 69, "#FFFFFF", 5)
    cv.ellipse(g, 12, 40, 44, 44, "#3F9C5A", ink, 3)
    cv.line(g, 24, 63, 31, 70, "#FFFFFF", 5)
    cv.line(g, 31, 70, 44, 55, "#FFFFFF", 5)
    if pressed is not None:
        dark = cv.group(g, f"{id}-pressed")
        cv.gate(dark, [(pressed, 1e6)])
        cv.ellipse(dark, -56, 40, 44, 44, "#7E1E12", ink, 3)
    return g


def _number_box(text: str, measure: Callable[[str, float], float]) -> int:
    """The width of the box that holds ``text`` at the battery number's size: the measured number and its margins."""
    advance = measure(text, NUMBER)
    if not (checks.number(advance) and 0 < advance and advance + 2 * NUMBER_PAD <= GLASS_WIDE):
        raise SoftPropError(f"a battery number {text!r} measured {advance!r} px wide: it needs a box on the glass")
    return math.ceil(advance + 2 * NUMBER_PAD)


def charge_width(percent: int) -> float:
    """How much of the cell ``percent`` fills, never so little it cannot be seen."""
    return max(SLIVER, CELL[2] * percent / 100)


@register(
    "prop",
    "soft-battery-screen",
    contract=dc.contract('soft-battery-screen'),
    summary="A phone's glass: a plain battery and its percentage, going down by steps and red when low",
)
def battery_screen(
    cv: Canvas,
    parent,
    x: float = 0,
    y: float = 0,
    *,
    levels: Sequence[Level] = (Level(2, 0.0, 1.0),),
    scale: float = 1,
    measure: Callable[[str, float], float] | None = None,
    id: str = "soft-battery-screen",
):
    """A percentage over a battery in the glass, reading each of ``levels`` in turn. The number sits in the top half,
    so a phone held at the chest keeps it in the safe area. With ``measure`` (the reel's font: text and size to its
    advance) each number's box is only as wide as the number, which keeps a phone's number inside the safe area at
    the frame edge: the engine checks the box, not the letters. Without it the box is the glass's width."""
    _place("a battery screen", x, y, scale)
    rows = list(levels)
    if not rows:
        raise SoftPropError("a battery screen shows a charge: give it at least one level")
    for row in rows:
        if isinstance(row.percent, bool) or not isinstance(row.percent, int) or not 0 <= row.percent <= 100:
            raise SoftPropError(f"a battery reads a whole percent from 0 to 100, got {row.percent!r}")
        if not (checks.number(row.at) and checks.number(row.until) and row.at < row.until):
            raise SoftPropError(f"a level shows for some time, got {row!r}")
        if not isinstance(row.number, bool):
            raise SoftPropError(f"a level shows its number or not: number is True or False, got {row.number!r}")
    if any(a.until > b.at for a, b in zip(rows, rows[1:], strict=False)):
        raise SoftPropError(f"levels run in order and never overlap, got {rows!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    ink = cv.ink
    cx, cy, width, height = CELL
    cv.rect(g, -65, -130, 130, 260, BATTERY_GLASS, radius=14)
    cv.rect(g, cx - 6, cy - 6, width + 12, height + 12, "#FFFFFF", ink, 4, radius=10)
    cv.rect(g, cx + width + 6, cy + 12, 8, height - 24, ink, radius=3)
    for k, row in enumerate(rows):
        low = row.percent <= LOW
        shown = cv.group(g, f"{id}-level-{k}")
        cv.gate(shown, [(row.at, row.until)])
        cv.rect(shown, cx, cy, charge_width(row.percent), height, BADGE if low else BATTERY_OK, radius=4)
        if row.number:
            text = f"{row.percent}%"
            wide = 120 if measure is None else _number_box(text, measure)
            cv.text(shown, f"{id}-text-{k}", text, -wide / 2, -68, wide, 64, NUMBER, color=BADGE if low else ROW_INK)
    return g

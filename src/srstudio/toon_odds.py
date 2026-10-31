"""Toon odds and ends: small props the everyday reels need, each a thing one sketch asks of a room.

:func:`pipe` is a leaking wall pipe whose drips are keyed to the sketch, ending in a spray if the sketch asks. Every
prop stands at a reference point (screen pixels as :func:`srstudio.toon.fx`/``fy`` map them), its cue times in project
seconds; a bad cue is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy

__all__ = [
    "DRIP_FALL",
    "balled_sheets",
    "folded_sheet",
    "mosquito",
    "padlock",
    "paper_insert",
    "pipe",
    "rolled_towel",
    "tasting_spoons",
    "wrestled_sheet",
]

Point = tuple[float, float]

PIPE, PIPE_SHADE, JOINT = "#aeb7c0", "#8e98a3", "#6f7a86"
WATER = "#7fc4ee"
PIPE_RUN = 200.0  # reference pixels from the joint up to where the pipe leaves the wall
DRIP_FALL = 0.32  # seconds a drip takes to fall
DRIP_DROP = 210.0  # reference pixels it falls
SPRAY = 5  # the jets of a burst joint
TITLE_MAX, LINES_MAX, LINE_MAX = 40, 4, 26
INSERT_PUSH = 1.05
SHEETS_RISE = 0.7  # seconds


def _cues(cues: Sequence[float], end: float, what: str) -> list[float]:
    times = [float(t) for t in cues]
    if not all(checks.number(t) and 0 <= t < end for t in times) or times != sorted(times):
        raise ToonDataError(f"{what} are rising seconds before {end}, got {cues!r}")
    return times


@register("prop", "toon-pipe", summary="A leaking wall pipe that drips on cue and can burst into a spray", style="toon")
def pipe(
    cv: Canvas,
    parent,
    at: Point = (470.0, 560.0),
    drips: Sequence[float] = (0.2, 1.1, 2.0),
    burst: float | None = None,
    end: float = 4.0,
):
    """A pipe coming down the wall to an elbow and a bad joint at ``at``, a drip falling from the joint at every
    second of ``drips``, and, from ``burst`` to ``end``, thin jets of water out of the joint."""
    times = _cues(drips, end, "a pipe's drips")
    if burst is not None and not (checks.number(burst) and 0 <= burst < end):
        raise ToonDataError(f"a pipe bursts before its end {end}, got {burst!r}")
    x, y = at
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x - 26), fy(y - PIPE_RUN), fh(52), fh(PIPE_RUN - 16), PIPE, cv.ink, INK_W * 0.7, radius=0)
    cv.rect(g, fx(x + 8), fy(y - PIPE_RUN), fh(12), fh(PIPE_RUN - 16), PIPE_SHADE, cv.clear, 0, radius=0)
    cv.rect(g, fx(x - 40), fy(y - 30), fh(80), fh(46), JOINT, cv.ink, INK_W * 0.7, radius=fh(8))
    for at_t in times:
        drop = cv.group(g, cv.uid("g"), start=at_t, end=min(end, at_t + DRIP_FALL))
        size = fh(15)
        cv.ellipse(drop, fx(x) - size / 2, fy(y + 20), size, size * 1.5, WATER, cv.ink, FINE_W * 0.5)
        cv.keys(drop, "y", [(at_t, 0.0), (at_t + DRIP_FALL, fh(DRIP_DROP))], hold=False, local=False)
    if burst is not None:
        jets = cv.group(g, cv.uid("g"), start=burst, end=end)
        for n in range(SPRAY):
            lean = (n - (SPRAY - 1) / 2) * 34.0
            cv.rect(jets, fx(x + lean), fy(y - 4 + abs(lean) * 0.3), fh(13), fh(220 - abs(lean)), WATER, radius=fh(4))
    return g


@register(
    "prop", "toon-paper-insert", summary="A full-frame paper held to the lens: an invoice, a card, a form", style="toon"
)
def paper_insert(
    cv: Canvas, parent, title: str, lines: Sequence[str], start: float, end: float, paper: str = "#fff6c9"
):
    """A sheet filling the frame from ``start`` to ``end``, ``title`` in capitals over ``lines``, tipped a little on a
    dark surface and pushing in slowly: evidence a viewer can read on a phone."""
    if not title.strip() or len(title) > TITLE_MAX or len(lines) > LINES_MAX or any(len(t) > LINE_MAX for t in lines):
        raise ToonDataError(f"an insert has a title to {TITLE_MAX} and {LINES_MAX} lines to {LINE_MAX}, got {title!r}")
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"an insert needs 0 <= start < end, got {start}..{end}")
    w, h = cv.width, cv.height
    g = cv.group(parent, cv.uid("g"), start=start, end=end, anchorX=w / 2, anchorY=h / 2, x=w / 2, y=h / 2)
    cv.rect(g, -40, -40, w + 80, h + 80, "#3c332e", cv.clear, 0, radius=0)
    sheet = cv.group(g, cv.uid("g"), anchorX=w / 2, anchorY=h / 2, x=w / 2, y=h / 2)
    sheet.rotation = -3
    x0, y0, width, height = 100, 500, w - 200, 860
    cv.rect(sheet, x0 + 16, y0 + 22, width, height, "#000000", cv.clear, 0, radius=10, opacity=0.25)
    cv.rect(sheet, x0, y0, width, height, paper, cv.ink, INK_W, radius=10)
    cv.text(sheet, cv.uid("insert-title"), title, x0 + 40, y0 + 60, width - 80, 220, 76, color=cv.ink, wrap="word")
    cv.rect(sheet, x0 + 60, y0 + 300, width - 120, 8, cv.ink, cv.clear, 0, radius=0)
    for k, text in enumerate(lines):
        cv.text(sheet, cv.uid("insert-line"), text, x0 + 40, y0 + 350 + k * 120, width - 80, 110, 60, color=cv.ink)
    cv.keys(g, "scaleX", [(start, 1.0), (end, INSERT_PUSH)], hold=False)
    cv.keys(g, "scaleY", [(start, 1.0), (end, INSERT_PUSH)], hold=False)
    return g


@register(
    "prop", "toon-mosquito", summary="A mosquito that wanders a keyed path with a jitter, or sits still", style="toon"
)
def mosquito(cv: Canvas, parent, path: Sequence[tuple[float, float, float]], end: float = 4.0, id: str = "mosquito"):
    """A mosquito through ``path``, ``(second, x, y)`` keys in rising seconds on reference pixels, from the first key
    to ``end``, its wings blurring while it flies; two keys at one place land it."""
    if len(path) < 2 or [k[0] for k in path] != sorted(k[0] for k in path) or not 0 <= path[0][0] < end:
        raise ToonDataError(f"a mosquito needs two rising keys before {end}, got {path!r}")
    g = cv.group(parent, cv.uid(id), start=path[0][0], end=end)
    cv.keys(g, "x", [(t, fx(x)) for t, x, _ in path], hold=False, local=False)
    cv.keys(g, "y", [(t, fy(y)) for t, _, y in path], hold=False, local=False)
    size = fh(9)
    cv.ellipse(g, -size * 1.6, -size * 1.8, size * 1.6, size * 2.6, "#d7e3ea", cv.ink, FINE_W * 0.35, opacity=0.8)
    cv.ellipse(g, size * 0.1, -size * 1.8, size * 1.6, size * 2.6, "#d7e3ea", cv.ink, FINE_W * 0.35, opacity=0.8)
    cv.ellipse(g, -size * 0.5, -size * 0.6, size, size * 1.8, "#2a2226", cv.ink, FINE_W * 0.3)
    cv.rect(g, -size * 0.1, size * 0.9, size * 0.2, size * 1.3, "#2a2226", cv.clear, 0, radius=0)
    return g


@register("prop", "toon-rolled-towel", summary="A rolled towel in a fist, raised and swung on cue", style="toon")
def rolled_towel(
    cv: Canvas,
    parent,
    root: Point = (470.0, 900.0),
    swings: Sequence[tuple[float, float]] = ((0.0, 0.0),),
    start: float = 0.0,
    end: float = 4.0,
    colour: str = "#5d8fc9",
):
    """An arm up from ``root`` holding a towel twisted into a club, turned by the ``(second, degrees)`` of ``swings``
    about ``root``, from ``start`` to ``end``."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end) or not swings:
        raise ToonDataError(f"a towel needs swings and 0 <= start < end, got {swings!r}, {start!r}..{end!r}")
    x, y = fx(root[0]), fy(root[1])
    g = cv.group(parent, cv.uid("g"), start=start, end=end, anchorX=x, anchorY=y, x=x, y=y)
    cv.keys(g, "rotation", list(swings), hold=False, local=False)
    arm, club = fh(66), fh(58)
    cv.rect(g, x - arm / 2, y - fh(190), arm, fh(230), "#a9744f", cv.ink, INK_W, radius=arm / 2)
    cv.rect(g, x - club / 2, y - fh(430), club, fh(280), colour, cv.ink, INK_W, radius=club / 2)
    for k in range(4):
        cv.rect(g, x - club / 2, y - fh(390 - k * 60), club, fh(5), cv.ink, cv.clear, 0, radius=0, opacity=0.45)
    return g

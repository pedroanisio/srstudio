"""Toon odds and ends: small props the everyday reels need, each a thing one sketch asks of a room.

:func:`pipe` is a leaking wall pipe whose drips are keyed to the sketch, ending in a spray if the sketch asks. Every
prop stands at a reference point (screen pixels as :func:`srstudio.toon.fx`/``fy`` map them), except the paper insert,
which uses frame pixels. Most animation keys use composition seconds; the paper insert follows Canvas.local_time.
Visibility uses parent seconds. A bad cue is a :class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import _toon_household_contracts as hc
from . import anatomy_ledger, checks
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
    "faucet",
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
FAUCET_RISE, FAUCET_REACH, FAUCET_W = 104.0, 62.0, 18.0  # reference pixels: top of the arc, spout, tube width
TITLE_MAX, LINES_MAX, LINE_MAX = 40, 4, 26
INSERT_PUSH = 1.05
SHEETS_RISE = 0.7  # seconds


def _cues(cues: Sequence[float], end: float, what: str) -> list[float]:
    times = [float(t) for t in cues]
    if not all(checks.number(t) and 0 <= t < end for t in times) or times != sorted(times):
        raise ToonDataError(f"{what} are rising seconds before {end}, got {cues!r}")
    return times


@register(
    "prop",
    "toon-pipe",
    contract=hc.contract('toon-pipe'),
    summary="A leaking wall pipe that drips on cue and can burst into a spray",
    style="toon",
)
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
    "prop",
    "toon-faucet",
    contract=hc.contract('toon-faucet'),
    summary="A kitchen tap on the counter, a bad joint that drips and can burst",
    style="toon",
)
def faucet(
    cv: Canvas,
    parent,
    x: float = 420.0,
    counter: float = 500.0,
    drips: Sequence[float] = (0.2, 1.1, 2.0),
    burst: float | None = None,
    end: float = 4.0,
):
    """A tap standing on a counter whose top is at ``counter``, its riser at ``x`` and its spout curving left, a drip
    falling from the spout to the counter at every second of ``drips``, and, from ``burst`` to ``end``, thin jets out of
    the bad joint on the riser."""
    times = _cues(drips, end, "a faucet's drips")
    if burst is not None and not (checks.number(burst) and 0 <= burst < end):
        raise ToonDataError(f"a faucet bursts before its end {end}, got {burst!r}")
    g = cv.group(parent, cv.uid("g"))
    top, mouth = counter - FAUCET_RISE, x - FAUCET_REACH
    arc = (
        f"M{fx(x)} {fy(counter - 12)} L{fx(x)} {fy(top + 40)} C{fx(x)} {fy(top - 12)} {fx(mouth)} {fy(top - 12)} "
        f"{fx(mouth)} {fy(top + 44)}"
    )
    cv.path(g, arc, None, cv.ink, fh(FAUCET_W + 8))
    cv.path(g, arc, None, PIPE, fh(FAUCET_W))
    cv.rect(g, fx(mouth - 13), fy(top + 40), fh(26), fh(14), JOINT, cv.ink, INK_W * 0.6, radius=fh(3))
    cv.rect(g, fx(x - 38), fy(counter - 10), fh(76), fh(12), JOINT, cv.ink, INK_W * 0.7, radius=fh(4))
    collar = counter - FAUCET_RISE * 0.42
    cv.rect(g, fx(x - 22), fy(collar - 13), fh(44), fh(26), JOINT, cv.ink, INK_W * 0.7, radius=fh(6))
    fall = counter - (top + 58)
    for at_t in times:
        drop = cv.group(g, cv.uid("g"), start=at_t, end=min(end, at_t + DRIP_FALL))
        size = fh(13)
        cv.ellipse(drop, fx(mouth) - size / 2, fy(top + 54), size, size * 1.4, WATER, cv.ink, FINE_W * 0.5)
        cv.keys(drop, "y", [(at_t, 0.0), (at_t + DRIP_FALL, fh(fall))], hold=False, local=False)
    if burst is not None:
        jets = cv.group(g, cv.uid("g"), start=burst, end=end)
        for n in range(SPRAY):
            lean = (n - (SPRAY - 1) / 2) * 16.0
            tall = 96.0 - abs(lean) * 0.8
            cv.rect(jets, fx(x + lean - 5), fy(collar - 12 - tall), fh(10), fh(tall), WATER, radius=fh(4))
    return g


@register(
    "prop",
    "toon-paper-insert",
    contract=hc.contract('toon-paper-insert'),
    summary="A full-frame paper held to the lens: an invoice, a card, a form",
    style="toon",
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
    "prop",
    "toon-mosquito",
    contract=hc.contract('toon-mosquito'),
    summary="A mosquito that wanders a keyed path with a jitter, or sits still",
    style="toon",
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


@register(
    "prop",
    "toon-rolled-towel",
    contract=hc.contract('toon-rolled-towel'),
    summary="A rolled towel in a fist, raised and swung on cue",
    style="toon",
)
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


@register(
    "prop",
    "toon-wrestled-sheet",
    contract=hc.contract('toon-wrestled-sheet'),
    summary="A sheet in a losing fight with someone, heaving on the beat",
    style="toon",
)
def wrestled_sheet(cv: Canvas, parent, start: float = 0.0, end: float = 4.0, y: float = 760.0, beat: float = 0.28):
    """A billowing sheet over someone's arms at height ``y`` from ``start`` to ``end``, heaving every ``beat`` s."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end) or not 0.1 <= beat <= 1:
        raise ToonDataError(f"a sheet heaves over 0 <= start < end every 0.1..1 s, got {start!r}..{end!r} {beat!r}")
    x0, y0 = fx(190), fy(y)
    g = cv.group(parent, cv.uid("g"), start=start, end=end, anchorX=x0, anchorY=y0, x=x0, y=y0)
    n = int((end - start) / beat) + 1
    cv.keys(
        g, "scaleY", [(start + k * beat, 1.0 if k % 2 else 1.18) for k in range(n)], kind="sine-in-out", local=False
    )
    cv.keys(g, "rotation", [(start + k * beat, -5 if k % 2 else 6) for k in range(n)], kind="sine-in-out", local=False)
    for dx, dy, w, h in ((-250, -70, 300, 170), (-30, -110, 300, 210), (150, -50, 220, 150), (-120, 10, 360, 150)):
        cv.ellipse(g, x0 + fh(dx), y0 + fh(dy), fh(w), fh(h), "#fbfbf5", cv.ink, INK_W * 0.8)
    for dx, dy, w in ((-160, -40, 150), (40, -60, 130)):
        cv.rect(g, x0 + fh(dx), y0 + fh(dy), fh(w), fh(5), "#c6ccd6", cv.clear, 0, radius=fh(3))
    return g


@register(
    "prop",
    "toon-balled-sheets",
    contract=hc.contract('toon-balled-sheets'),
    summary="An avalanche of balled-up white sheets, rising or already there",
    style="toon",
)
def balled_sheets(cv: Canvas, parent, top: float = 700.0, start: float | None = 0.5, end: float = 4.0):
    """The heap's top edge at reference ``top``: rising there over :data:`SHEETS_RISE` from ``start``, or there already
    (``start`` None) until ``end``."""
    if not (checks.number(top) and 200 <= top <= 900):
        raise ToonDataError(f"a heap's top stands between 200 and 900, got {top!r}")
    if start is not None and not (checks.number(start) and 0 <= start and start + SHEETS_RISE <= end):
        raise ToonDataError(f"a heap rises in {SHEETS_RISE} s from {start!r} before {end!r}")
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    if start is not None:
        cv.keys(g, "y", [(start, fh(1200 - top)), (start + SHEETS_RISE, 0.0)], kind="cubic-out", local=False)
    cv.rect(g, fx(-20), fy(top + 80), fh(640), fh(1200 - top), "#eef1f4", cv.clear, 0, radius=0)
    for row in range(5):
        for col in range(5):
            x, y = -40 + col * 140 + (row % 2) * 60, top + row * 86
            cv.ellipse(
                g, fx(x), fy(y), fh(170), fh(124), "#fbfbf5" if (row + col) % 3 else "#e8ecf2", cv.ink, INK_W * 0.6
            )
            cv.rect(g, fx(x + 50), fy(y + 52), fh(60), fh(5), "#c6ccd6", cv.clear, 0, radius=fh(3))
    return g


@register(
    "prop",
    "toon-folded-sheet",
    contract=hc.contract('toon-folded-sheet'),
    summary="One impossibly square folded sheet, held out on two paws",
    style="toon",
)
def folded_sheet(
    cv: Canvas, parent, at: Point = (190.0, 700.0), coat: str = "#a9744f", start: float = 0.0, end: float = 4.0
):
    """A folded sheet with knife edges, its bottom edge on reference ``at``, resting on two paws of ``coat``."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a sheet is held over 0 <= start < end, got {start!r}..{end!r}")
    anatomy_ledger.loose_hand(cv, "toon-folded-sheet")
    x, y = at
    g = cv.group(parent, cv.uid("g"), start=start, end=end)
    cv.rect(g, fx(x - 110), fy(y - 120), fh(220), fh(120), "#fbfbf5", cv.ink, INK_W, radius=fh(4))
    for k in range(1, 5):
        cv.rect(g, fx(x - 110), fy(y - 120 + k * 24), fh(220), fh(3), "#c6ccd6", cv.clear, 0, radius=0)
    for side in (-1, 1):
        cv.ellipse(g, fx(x + side * 90 - 40), fy(y - 20), fh(80), fh(62), coat, cv.ink, FINE_W * 1.2)
    return g


@register(
    "prop",
    "toon-padlock",
    contract=hc.contract('toon-padlock'),
    summary="A brass padlock on a door that drops away when it is unlocked",
    style="toon",
)
def padlock(cv: Canvas, parent, at: Point = (400.0, 540.0), start: float = 0.0, opened: float = 4.0, end: float = 4.0):
    """A padlock at reference ``at`` from ``start``, falling out of frame at ``opened``."""
    if not (checks.number(start) and checks.number(opened) and 0 <= start <= opened <= end):
        raise ToonDataError(f"a padlock needs 0 <= start <= opened <= end, got {start!r}, {opened!r}, {end!r}")
    x, y = fx(at[0]), fy(at[1])
    g = cv.group(parent, cv.uid("g"), start=start, end=min(end, opened + 0.6))
    cv.keys(g, "y", [(opened, 0.0), (opened + 0.6, fh(700))], kind="cubic-in", local=False)
    cv.ellipse(g, x - fh(24), y - fh(52), fh(48), fh(70), cv.clear, "#7c8691", INK_W * 0.9)
    cv.rect(g, x - fh(44), y - fh(16), fh(88), fh(76), "#e0b13c", cv.ink, INK_W * 0.8, radius=fh(10))
    cv.ellipse(g, x - fh(8), y + fh(4), fh(16), fh(16), cv.ink)
    cv.rect(g, x - fh(4), y + fh(14), fh(8), fh(22), cv.ink, cv.clear, 0, radius=0)
    return g


@register(
    "prop",
    "toon-tasting-spoons",
    contract=hc.contract('toon-tasting-spoons'),
    summary="Tiny tasting spoons that pile up on a counter, one per cue",
    style="toon",
)
def tasting_spoons(cv: Canvas, parent, cues: Sequence[float], at: Point = (450.0, 880.0), end: float = 4.0):
    """One small pink spoon appears at reference ``at`` per cue. ``end`` bounds the cues, not visibility;
    give the parent a visibility end to hide the pile."""
    times = _cues(cues, end, "a pile's spoons")
    x0, y0 = at
    g = cv.group(parent, cv.uid("g"))
    per_row = 7
    for k, t in enumerate(times):
        row, col = k // per_row, k % per_row
        x, y = x0 - 96 + col * 32 + (row % 2) * 14, y0 - row * 16
        s = cv.group(g, cv.uid("g"), start=t, anchorX=fx(x), anchorY=fy(y), x=fx(x), y=fy(y))
        s.rotation = 18 + (k * 53) % 130
        cv.rect(s, fx(x) - fh(5), fy(y) - fh(38), fh(10), fh(60), "#ff9ab8", cv.ink, FINE_W * 0.4, radius=fh(4))
        cv.ellipse(s, fx(x) - fh(11), fy(y) - fh(50), fh(22), fh(26), "#ff9ab8", cv.ink, FINE_W * 0.4)
    return g

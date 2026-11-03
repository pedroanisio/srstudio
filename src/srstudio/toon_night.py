"""A car at night, from the dashboard: the cabin behind the two front seats, the dark dash, and the call on it.

:func:`night_cabin` is the set: a dark roof, the back window with the night in it and the two front seats, for
characters drawn over it. :func:`night_dash` is the dash in front of them. :func:`call_chip` is a dashboard call
readout copying no real car, a name and a running timer: dim, so a viewer may miss it, until ``lit_from``. The timer's
digits are drawn second by second on the project clock, and a digit that a cut would leave on screen too briefly to
read stays on the one beside it (:func:`ticks`).
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks, signature, toon_cars
from ._toon_story_contracts import contract
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, ToonDataError, fh, fx, fy
from .toon_everyday import CAPTION_BAND, FRAME, SIGNATURE_BOX, Measure, _overlaps

__all__ = ["CHIP_AT", "SEATS", "call_chip", "night_cabin", "night_dash", "reading", "ticks"]

SEATS = (146.0, 424.0)
ROOF, GLASS, SEAT, SEAT_EDGE = "#1a2036", "#0e1830", "#2f3855", "#262d46"
DASH_TOP, DASH_FRONT, DASH_CODE = "#262c40", "#171c2c", "#8c94a8"
VENT, VENT_SLAT = "#0e1320", "#2c3448"
DASH_LIP = 801.0  # as a desk's top
VENTS = (36.0, 430.0)  # reference x of the two vents' left edges
FAR_LIGHTS = ((96.0, 262.0, 7.0), (214.0, 240.0, 5.0), (398.0, 250.0, 6.0), (480.0, 268.0, 8.0))
CHIP_AT = (296.0, 985.0)
CHIP_SIZE = 34  # frame pixels, read on a phone
CHIP_H = 38.0  # reference units
CHIP_PAD = 14.0  # reference units, on each side
CHIP_GAP = 10.0  # reference units between the name and the timer
CHIP_NUDGE = 4.0  # reference units: a timer is measured at its widest, so its row sits a little right of centre
PANEL = {False: "#0c111b", True: "#10231c"}
LABEL = {False: "#7d919c", True: "#eafff4"}  # dim still reads: 5.8:1 on its panel
EDGE = {False: "#2a3244", True: "#3fe08a"}
LEAST = 0.84  # seconds a reading stays up: the engine's least display time, on the safe side
DIGITS = "00:00"  # the widest the timer is measured at, so nothing moves as it counts


def reading(seconds: int) -> str:
    """``seconds`` as a call timer reads them, minutes and seconds."""
    if not (isinstance(seconds, int) and not isinstance(seconds, bool) and 0 <= seconds < 6000):
        raise ToonDataError(f"a call timer reads 0 to 99:59, got {seconds!r}")
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def ticks(start: float, end: float, reads: tuple[float, int]) -> list[tuple[float, float, str]]:
    """The readings from ``start`` to ``end``: ``(from, to, text)``, the timer showing ``reads[1]`` at ``reads[0]`` and
    counting. A reading a cut would cut under :data:`LEAST` is left out and the one beside it stays up instead."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a timer runs over 0 <= start < end, got {start!r}..{end!r}")
    if end - start < LEAST:
        raise ToonDataError(f"a timer needs {LEAST} s to be read, got {end - start:.2f} s")
    at, shown = reads
    if shown + (start - at) < 0:
        raise ToonDataError(f"the timer would read under zero at {start} s")
    whole = int((start - at) // 1)  # the reading standing at ``start``, counted from ``reads``
    edges = [start, *(at + n for n in range(whole + 1, int((end - at) // 1) + 2) if start < at + n < end), end]
    while len(edges) > 2 and edges[1] - edges[0] < LEAST:
        del edges[1]
    while len(edges) > 2 and edges[-1] - edges[-2] < LEAST:
        del edges[-2]
    out = []
    for a, b in zip(edges, edges[1:], strict=False):
        count = int((a - at + 1e-6) // 1)
        out.append((round(a, 6), round(b, 6), reading(shown + count)))
    return out


def _lights_on(readings: Sequence[tuple[float, float, str]], lit_from: float | None) -> float | None:
    """The reading's edge the chip lights on: the first at or after ``lit_from``, so no text is split into a piece too
    brief to read. None when it never lights."""
    if lit_from is None:
        return None
    return next((a for a, _, _ in readings if a >= lit_from), None)


@register(
    "location",
    "toon-night-cabin",
    summary="A car's cabin at night seen from the dash: roof, back window, seats",
    contract=contract('toon-night-cabin'),
)
def night_cabin(cv: Canvas, parent) -> None:
    """The cabin, for two characters drawn over it, on :data:`SEATS`."""
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, ROOF, cv.clear, 0, radius=0)
    cv.rect(g, fx(44), fy(150), fh(504), fh(190), GLASS, cv.ink, FINE_W, radius=fh(40))
    for x, y, r in FAR_LIGHTS:
        cv.ellipse(g, fx(x - r), fy(y - r), fh(2 * r), fh(2 * r), "#ffd28a", opacity=0.55)
    for x in SEATS:
        toon_cars.seat(cv, g, x, SEAT)


def _vent(cv: Canvas, g, x: float, y: float, w: float = 128.0, h: float = 54.0) -> None:
    cv.rect(g, fx(x), fy(y), fh(w), fh(h), VENT, VENT_SLAT, FINE_W, radius=fh(12))
    for k in range(3):
        cv.rect(g, fx(x + 10), fy(y + 12 + 12 * k), fh(w - 20), fh(4), VENT_SLAT, cv.clear, 0, radius=0)


@register(
    "prop",
    "toon-night-dash",
    summary="A dark dashboard in front of the seats, marks where a desk has them",
    contract=contract('toon-night-dash'),
)
def night_dash(cv: Canvas, parent, close: bool = False) -> None:
    """The dash in front of the characters; ``close``, the same dash filling the frame above its lip too, for a shot
    that has come down to it."""
    g = cv.group(parent, cv.uid("g"))
    if close:
        cv.rect(g, fx(-10), 0, fh(612), cv.height, DASH_FRONT, cv.clear, 0, radius=0)
        for x in VENTS:
            _vent(cv, g, x, 420.0, 128.0, 92.0)
    cv.rect(g, fx(-10), fy(DASH_LIP + 47), fh(612), fh(300), DASH_FRONT, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(DASH_LIP), fh(612), fh(47), cv.ink, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(DASH_LIP + 12), fh(612), fh(31), DASH_TOP, cv.clear, 0, radius=0)
    for x in VENTS:
        _vent(cv, g, x, 884.0)
    signature.cactus(cv, g, fx(548), fy(838), 0.7)
    signature.code(cv, g, fx(580), fy(866), 14, color=DASH_CODE, opacity=0.9, align="end")


@register(
    "prop",
    "toon-call-chip",
    summary="A dashboard call readout: a name and a running timer, dim until lit",
    contract=contract('toon-call-chip'),
)
def call_chip(
    cv: Canvas,
    parent,
    name: str,
    reads: tuple[float, int],
    start: float,
    end: float,
    *,
    measure: Measure,
    at: tuple[float, float] = CHIP_AT,
    scale: float = 1.0,
    lit_from: float | None = None,
    id: str = "call-chip",
):
    """``CALL: NAME`` and a timer centred on reference ``at`` from ``start`` to ``end``, the timer reading ``reads[1]``
    at second ``reads[0]`` and counting; dim until the first new reading at or after ``lit_from``, if one comes."""
    if not (isinstance(name, str) and name.strip()):
        raise ToonDataError(f"a call names someone, got {name!r}")
    if not (checks.number(scale) and 0.8 <= scale <= 2.5):
        raise ToonDataError(f"a call chip's scale is between 0.8 and 2.5, got {scale!r}")
    if lit_from is not None and not (checks.number(lit_from) and lit_from >= 0):
        raise ToonDataError(f"a chip lights at a second >= 0, got {lit_from!r}")
    label = f"CALL: {name.upper()}"
    label_w = measure(label, CHIP_SIZE) / fh(1.0)
    digits_w = measure(DIGITS, CHIP_SIZE) / fh(1.0)
    half = (label_w + digits_w + CHIP_GAP) / 2 + CHIP_PAD
    x, y = at
    box = (x - scale * half, y - scale * CHIP_H / 2, x + scale * half, y + scale * CHIP_H / 2)
    if box[0] < FRAME[0] or box[1] < FRAME[1] or box[2] > FRAME[2] or box[3] > FRAME[3]:
        raise ToonDataError(f"a call chip at {at} spans {box}, leaving the frame")
    if _overlaps(box, CAPTION_BAND):
        raise ToonDataError(f"a call chip at {at} sits in the caption band")
    if _overlaps(box, SIGNATURE_BOX):
        raise ToonDataError(f"a call chip at {at} sits on the signature marks")
    readings = ticks(start, end, reads)
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    lit_at = _lights_on(readings, lit_from)
    spans = [(start, end, lit_at == start)] if lit_at is None or lit_at == start else [
        (start, lit_at, False), (lit_at, end, True)]  # fmt: skip
    left, top = -fh(half), -fh(CHIP_H / 2)
    for a, b, lit in spans:
        state = cv.group(g, cv.uid("state"), start=a, end=b)
        cv.rect(state, round(left, 2), round(top, 2), round(-2 * left, 2), fh(CHIP_H), PANEL[lit], EDGE[lit], FINE_W,
                radius=fh(CHIP_H / 2))  # fmt: skip
        cv.text(state, cv.uid("call-name"), label, round(left + fh(CHIP_PAD + CHIP_NUDGE), 2), round(top, 2),
                int(fh(label_w) + 2),
                int(fh(CHIP_H)), CHIP_SIZE, color=LABEL[lit], align="start", wrap="none")  # fmt: skip
    timer_x = round(left + fh(CHIP_PAD + CHIP_NUDGE + label_w + CHIP_GAP), 2)
    for k, (a, b, text) in enumerate(readings):
        lit = lit_at is not None and a >= lit_at
        tick = cv.group(g, f"{id}-tick-{k}", start=a, end=b)
        cv.text(tick, cv.uid("call-timer"), text, timer_x, round(top, 2), int(fh(digits_w) + 2), int(fh(CHIP_H)),
                CHIP_SIZE, color=LABEL[lit], align="start", wrap="none")  # fmt: skip
    return g

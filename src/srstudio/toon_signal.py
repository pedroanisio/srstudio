"""The one good spot in the house: a chair to climb on, an arm that holds a phone up, the upload's chip, and lunch.

:func:`climb_chair` is a kitchen chair seen from behind, its back hiding whoever stands on it from the waist down.
:func:`raised_phone` is a forearm in a character's colours running up to a paw and a phone whose signal bars read on
their own clock: it never moves, which is the point of it. :func:`upload_chip` shows a progress figure and its bar from
:mod:`srstudio.readings`, each reading held long enough to read. :func:`broom` is a broom held head up with a sandwich
balanced on it, bitten at a second. The interfaces are invented and none copies a real app.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from ._toon_story_contracts import contract
from .canvas import Canvas
from .readings import Reading
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy
from .toon_everyday import CAPTION_BAND, FRAME, SIGNATURE_BOX, Measure, _overlaps

__all__ = ["BARS", "broom", "climb_chair", "raised_phone", "table_legs", "upload_chip"]

WOOD, WOOD_DARK = "#b98a58", "#8d6238"
CHAIR_W, CHAIR_H = 276.0, 270.0
BACK_TOP, BACK_BOTTOM = 270.0, 112.0  # how far the chair's back runs above its feet, reference units
LEG_W, RAIL_W = 22.0, 24.0
BARS = 4
PHONE_W, PHONE_H = 112.0, 182.0
CASE, SCREEN, BAR_ON, BAR_OFF, NO_SIGNAL = "#23262e", "#10222f", "#7ff0b0", "#2c3f4c", "#ff6b5e"
ARM_W, ARM_DOWN = 58.0, 340.0
CHIP_W, CHIP_H = 204.0, 88.0
CHIP_SIZE = 50  # frame pixels, read on a phone
CHIP_PAD = 14.0
TRACK_H, TRACK_BOTTOM = 12.0, 10.0
PANEL, EDGE, LABEL, TRACK, FILL, DONE = "#101726", "#3b4a66", "#f2f6ff", "#2c3650", "#5fb4ff", "#3fe08a"
HANDLE, HANDLE_EDGE = "#c9a26d", "#8d6238"
BRISTLE, BRISTLE_DARK, COLLAR = "#e0c15f", "#b8953d", "#a33a3a"
HANDLE_LONG = 760.0
BREAD, CRUST, FILLING, LEAF = "#f2d7a2", "#c99a58", "#c9574b", "#7fbf58"
TABLE_APRON, FLOOR_AT = 905.0, 1040.0
TABLE_LEGS = (30.0, 492.0)
TABLE_LEG_W = 60.0
UNDER, FLOOR, LEG, LEG_LIGHT = "#cfd6c2", "#a98f72", "#8d6238", "#a97b4c"
TILT = -14.0  # degrees: the handle leans from the holder to the one who eats


def _box(what: str, box: tuple[float, float, float, float], band: bool = False) -> None:
    if box[0] < FRAME[0] or box[1] < FRAME[1] or box[2] > FRAME[2] or box[3] > FRAME[3]:
        raise ToonDataError(f"a {what} spanning {box} leaves the frame")
    if band and _overlaps(box, CAPTION_BAND):
        raise ToonDataError(f"a {what} spanning {box} sits in the caption band")
    if _overlaps(box, SIGNATURE_BOX):
        raise ToonDataError(f"a {what} spanning {box} sits on the signature marks")


@register(
    "prop",
    "toon-climb-chair",
    summary="A kitchen chair from behind, its back hiding who stands on it",
    contract=contract('toon-climb-chair'),
)
def climb_chair(cv: Canvas, parent, at: tuple[float, float] = (210.0, 806.0)) -> None:
    """The chair from behind, the middle of its feet at reference ``at``, in a group a keyed rotation can tip."""
    x, y = at
    half = CHAIR_W / 2
    if y - CHAIR_H < 200.0:
        raise ToonDataError(f"a chair at {at} rises out of the frame")
    _box("chair", (x - half, y - CHAIR_H, x + half, y))
    g = cv.group(parent, cv.uid("g"))
    for leg in (x - half + 8.0, x + half - 8.0 - LEG_W):
        cv.rect(g, fx(leg), fy(y - BACK_BOTTOM), fh(LEG_W), fh(BACK_BOTTOM), WOOD_DARK, cv.ink, INK_W * 0.7,
                radius=fh(4))  # fmt: skip
    cv.rect(g, fx(x - half), fy(y - BACK_TOP), fh(CHAIR_W), fh(BACK_TOP - BACK_BOTTOM), WOOD, cv.ink, INK_W * 0.8,
            radius=fh(18))  # fmt: skip
    for row in (0.3, 0.62):
        rail = y - BACK_TOP + (BACK_TOP - BACK_BOTTOM) * row
        cv.rect(g, fx(x - half + 22.0), fy(rail), fh(CHAIR_W - 44.0), fh(RAIL_W), WOOD_DARK, cv.ink, FINE_W * 0.6,
                radius=fh(6))  # fmt: skip


@register(
    "prop",
    "toon-table-legs",
    summary="A desk's front turned into a table: an apron, two legs, the floor behind",
    contract=contract('toon-table-legs'),
)
def table_legs(cv: Canvas, parent) -> None:
    """Over a ledge's front: an apron under the top, the wall and floor seen under it, and two turned legs."""
    y0, y1 = TABLE_APRON, FRAME[3] + 4.0
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(-10.0), fy(y0), fh(612.0), fh(FLOOR_AT - y0), UNDER, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10.0), fy(FLOOR_AT), fh(612.0), fh(y1 - FLOOR_AT), FLOOR, cv.clear, 0, radius=0)
    cv.line(g, fx(-10.0), fy(FLOOR_AT), fx(602.0), fy(FLOOR_AT), cv.ink, INK_W * 0.6)
    for x in TABLE_LEGS:
        cv.rect(g, fx(x), fy(y0 - 4.0), fh(TABLE_LEG_W), fh(y1 - y0), LEG, cv.ink, INK_W * 0.8, radius=fh(6))
        cv.rect(g, fx(x + 8.0), fy(y0 + 6.0), fh(TABLE_LEG_W - 28.0), fh(y1 - y0), LEG_LIGHT, cv.clear, 0, radius=fh(4))
    cv.rect(g, fx(-10.0), fy(y0 - 4.0), fh(612.0), fh(8.0), cv.ink, cv.clear, 0, radius=0)


@register(
    "prop",
    "toon-raised-phone",
    summary="A forearm holding a phone up, its signal bars on a clock",
    contract=contract('toon-raised-phone'),
)
def raised_phone(
    cv: Canvas,
    parent,
    hand: tuple[float, float],
    colour: str,
    dark: str,
    bars: Sequence[tuple[float, int]],
    start: float,
    end: float,
    *,
    down: float = ARM_DOWN,
    id: str = "raised-phone",
) -> None:
    """A forearm running up to a paw at reference ``hand``, in the character's ``colour`` and ``dark``, and the phone
    held above it, reading ``bars`` (``(second, lit)``, the first at ``start``) until ``end``. The forearm runs ``down``
    reference units, to end behind the character. It never moves."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a phone's clock runs from a start to a later end, got {start!r}..{end!r}")
    if not bars or bars[0][0] != start:
        raise ToonDataError(f"the first bar reading is at the phone's start, {start} s")
    for (a, _), (b, _) in zip(bars, bars[1:], strict=False):
        if b <= a:
            raise ToonDataError(f"bar readings run in order, got {b} after {a}")
    if bars[-1][0] >= end:
        raise ToonDataError(f"bar readings stop before the end at {end} s")
    for _, count in bars:
        if not (isinstance(count, int) and 0 <= count <= BARS):
            raise ToonDataError(f"a phone has 0 to {BARS} bars, got {count!r}")
    if not (checks.number(down) and down > 0):
        raise ToonDataError(f"a forearm runs down over 0, got {down!r}")
    x, y = hand
    _box("raised phone", (x - PHONE_W / 2, y - PHONE_H - 8.0, x + PHONE_W / 2, y + 30.0))
    g = cv.group(parent, id, start=start, end=end)
    cv.rect(g, fx(x - ARM_W / 2), fy(y), fh(ARM_W), fh(down), colour, cv.ink, INK_W * 0.8, radius=fh(26))
    cv.rect(g, fx(x + ARM_W / 2 - 16.0), fy(y + 30.0), fh(12.0), fh(down - 40.0), dark, cv.clear, 0, radius=fh(6))
    px, py = x - PHONE_W / 2, y - PHONE_H + 12.0
    cv.rect(g, fx(px), fy(py), fh(PHONE_W), fh(PHONE_H), CASE, cv.ink, INK_W * 0.8, radius=fh(14))
    cv.rect(g, fx(px + 8.0), fy(py + 10.0), fh(PHONE_W - 16.0), fh(PHONE_H - 34.0), SCREEN, cv.clear, 0, radius=fh(6))
    ends, veined = [at for at, _ in bars[1:]] + [end], 17.0
    for k, ((at, count), stop) in enumerate(zip(bars, ends, strict=True)):
        state = cv.group(g, f"signal-{k}", start=at, end=stop)
        for bar in range(BARS):
            high = 22.0 + bar * 26.0
            cv.rect(state, fx(px + 14.0 + bar * 22.0), fy(py + 118.0 - high), fh(veined), fh(high),
                    BAR_ON if bar < count else BAR_OFF, cv.clear, 0, radius=fh(3))  # fmt: skip
        if count == 0:
            for a, b in ((-1.0, 1.0), (1.0, -1.0)):
                cv.line(state, fx(px + PHONE_W / 2 + a * 22.0), fy(py + 60.0 - 22.0), fx(px + PHONE_W / 2 + b * 22.0),
                        fy(py + 60.0 + 22.0), NO_SIGNAL, INK_W)  # fmt: skip
    cv.ellipse(g, fx(x - 46.0), fy(y - 24.0), fh(92.0), fh(56.0), colour, cv.ink, INK_W * 0.8)
    for finger in range(3):
        cv.ellipse(g, fx(x - 38.0 + finger * 26.0), fy(y - 34.0), fh(24.0), fh(30.0), colour, cv.ink, FINE_W)


@register(
    "prop",
    "toon-upload-chip",
    summary="An upload's figure and its bar, each reading held to be read",
    contract=contract('toon-upload-chip'),
)
def upload_chip(
    cv: Canvas,
    parent,
    readings: Sequence[Reading],
    shares: Sequence[float],
    *,
    measure: Measure,
    at: tuple[float, float] = (420.0, 380.0),
    id: str = "upload",
) -> None:
    """The chip centred on reference ``at``, showing each of ``readings`` over a bar filled to its one of ``shares``;
    the bar turns green once it is full."""
    if len(readings) != len(shares):
        raise ToonDataError(f"one share per reading: {len(readings)} readings, {len(shares)} shares")
    for share in shares:
        if not (checks.number(share) and 0 <= share <= 1):
            raise ToonDataError(f"a share runs from 0 to 1, got {share!r}")
    x, y = at
    _box("upload chip", (x - CHIP_W / 2, y - CHIP_H / 2, x + CHIP_W / 2, y + CHIP_H / 2), band=True)
    inner = CHIP_W - 2 * CHIP_PAD
    for r in readings:
        if measure(r.text, CHIP_SIZE) > fh(inner):
            raise ToonDataError(f"{r.text!r} is too wide for an upload chip")
    g = cv.group(parent, f"{id}-chip", x=fx(x), y=fy(y), start=readings[0].start, end=readings[-1].end)
    left, top = -fh(CHIP_W / 2), -fh(CHIP_H / 2)
    cv.rect(g, left, top, fh(CHIP_W), fh(CHIP_H), PANEL, EDGE, FINE_W, radius=fh(14))
    track_y = fh(CHIP_H / 2 - TRACK_BOTTOM - TRACK_H)
    cv.rect(g, left + fh(CHIP_PAD), track_y, fh(inner), fh(TRACK_H), TRACK, cv.clear, 0, radius=fh(6))
    for k, (r, share) in enumerate(zip(readings, shares, strict=True)):
        state = cv.group(g, f"{id}-read-{k}", start=r.start, end=r.end)
        cv.text(state, cv.uid("upload-figure"), r.text, left, top + fh(6.0), int(fh(CHIP_W)), int(fh(CHIP_H - 30.0)),
                CHIP_SIZE, color=LABEL, align="center", wrap="none")  # fmt: skip
        if share > 0:
            bar = cv.group(g, f"{id}-bar-{k}", start=r.start, end=r.end)
            cv.rect(bar, left + fh(CHIP_PAD), track_y, fh(inner * share), fh(TRACK_H), DONE if share == 1 else FILL,
                    cv.clear, 0, radius=fh(6))  # fmt: skip


def _sandwich(cv: Canvas, g, bitten: bool) -> None:
    """Two slices with a filling and a leaf between them, the eater's end torn off unevenly once ``bitten``."""
    gone = (30.0, 40.0, 34.0, 44.0) if bitten else (0.0, 0.0, 0.0, 0.0)
    rows = ((12.0, 16.0, BREAD), (-2.0, 8.0, LEAF), (-12.0, 12.0, FILLING), (-30.0, 20.0, BREAD))
    for (y, h, colour), bite in zip(rows, gone, strict=True):
        edge = CRUST if colour == BREAD else cv.ink
        cv.rect(g, fh(-60.0 + bite), fh(y), fh(120.0 - bite), fh(h), colour, edge, FINE_W, radius=fh(6))


@register(
    "prop",
    "toon-sandwich-broom",
    summary="A broom held head up with a sandwich balanced on it",
    contract=contract('toon-sandwich-broom'),
)
def broom(
    cv: Canvas,
    parent,
    moves: Sequence[tuple[float, float, float]],
    start: float,
    end: float,
    bite: float,
    *,
    tilt: float = TILT,
    id: str = "broom",
) -> None:
    """The broom from ``start`` to ``end``, its sandwich's middle travelling through ``moves`` (``(second, x, y)``,
    reference units) and bitten at ``bite``."""
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"a broom's clock runs from a start to a later end, got {start!r}..{end!r}")
    if len(moves) < 2:
        raise ToonDataError("a broom has at least two stops")
    times = [m[0] for m in moves]
    if times != sorted(times) or len(set(times)) != len(times):
        raise ToonDataError(f"a broom's stops run in order, got {times}")
    if not (checks.number(bite) and start < bite < end):
        raise ToonDataError(f"the bite comes while the broom is up, got {bite!r}")
    _, x, y = moves[0]
    g = cv.group(parent, id, x=fx(x), y=fy(y), rotation=tilt, start=start, end=end)
    cv.rect(g, -fh(9.0), fh(70.0), fh(18.0), fh(HANDLE_LONG), HANDLE, HANDLE_EDGE, FINE_W, radius=fh(5))
    cv.rect(g, -fh(20.0), fh(60.0), fh(40.0), fh(18.0), COLLAR, cv.ink, FINE_W, radius=fh(4))
    fan = f"M {-fh(18.0)} {fh(62.0)} L {-fh(62.0)} {fh(30.0)} L {fh(62.0)} {fh(30.0)} L {fh(18.0)} {fh(62.0)} Z"
    cv.path(g, fan, BRISTLE, cv.ink, FINE_W)
    for k in (-34.0, -12.0, 12.0, 34.0):
        cv.line(g, fh(k), fh(32.0), fh(k * 0.4), fh(60.0), BRISTLE_DARK, FINE_W * 0.6)
    whole = cv.group(g, "sandwich-whole", start=start, end=bite)
    _sandwich(cv, whole, False)
    eaten = cv.group(g, "sandwich-bitten", start=bite, end=end)
    _sandwich(cv, eaten, True)
    cv.keys(g, "x", [(t, fx(px)) for t, px, _ in moves], hold=False, kind="sine-in-out", local=False)
    cv.keys(g, "y", [(t, fy(py)) for t, _, py in moves], hold=False, kind="sine-in-out", local=False)

"""Cutout across a counter: what a bank or a café leaves out for the customer, and how much of it he may keep.

Every drawing here is a prop: it takes its parent and where it stands, draws in the parent's coordinates, and refuses
arguments it cannot be drawn from with :class:`CutoutCounterError`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import checks, locations, signature
from .canvas import Canvas, Spans
from .errors import SrstudioError
from .registry import register

__all__ = [
    "ChainRun",
    "CutoutCounterError",
    "back_room",
    "chain_run",
    "jump_clock",
    "paper_poster",
    "pen_on_chain",
    "sandwich",
]

Point = tuple[float, float]
Grip = tuple[float, float, float]  # time, x, y

CHAIN_LINKS = 30
CHAIN_STEP = 1 / 30  # seconds between the keys of a moving chain: one per frame
CHAIN_TWANG = 0.30  # seconds a chain pulled taut goes on shaking
CHAIN_RECOIL = 0.30  # seconds a let-go pen takes to fly home
CHAIN_SETTLE = 0.70  # seconds the chain goes on swinging once the pen is home
CHAIN_SAG = 0.42  # how far a slack chain hangs, of half its slack
CHAIN_LOOP = 34  # how wide a slack chain opens, px
CHAIN_METAL = "#8D949B"
PEN_BODY = "#1F2B4A"
CLOCK_SPIN = 0.75  # seconds a jump takes the hands, whatever the minutes
ROOM_FAR = 0.5  # the back room's scale through its door, before the push
HALL_NEAR = 3.6  # the hall's scale once the push has gone through it
DOOR = (540, 960)  # the door's opening, width and height, about the frame's centre (540, 900)


class CutoutCounterError(SrstudioError, ValueError):
    """A prop asked for with arguments it cannot be drawn from."""


@dataclass(frozen=True)
class ChainRun:
    """When a pen on a chain did what: ``taut`` the chain ran out, ``snap`` the hand lost the pen, ``home`` it landed.
    A pen never carried to the end of its chain has ``taut`` None, and one never let go ``snap`` and ``home`` None."""

    taut: float | None
    snap: float | None
    home: float | None


def _along(grip: Sequence[Grip], t: float) -> Point:
    """Where the hand has the pen at ``t``, straight between the rows; it holds at either end of them."""
    if t <= grip[0][0]:
        return grip[0][1], grip[0][2]
    for (a, ax, ay), (b, bx, by) in zip(grip, grip[1:], strict=False):
        if t <= b:
            share = (t - a) / (b - a)
            return ax + (bx - ax) * share, ay + (by - ay) * share
    return grip[-1][1], grip[-1][2]


def _check_chain(x: float, y: float, length: float, grip: Sequence[Grip], snap: float | None) -> None:
    if not (checks.number(x) and checks.number(y)):
        raise CutoutCounterError(f"the chain's foot is a finite point, got {x!r}, {y!r}")
    if not (checks.number(length) and length > 0):
        raise CutoutCounterError(f"a chain's length is a positive number, got {length!r}")
    if len(grip) < 2 or not all(len(row) == 3 and all(checks.number(v) for v in row) for row in grip):
        raise CutoutCounterError(f"a grip is at least two (time, x, y) rows, got {grip!r}")
    times = [row[0] for row in grip]
    if times[0] < 0 or any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise CutoutCounterError(f"a grip's times start at or after 0 and rise strictly, got {times!r}")
    if snap is not None and not checks.number(snap):
        raise CutoutCounterError(f"a snap is a finite time, got {snap!r}")


def chain_run(
    x: float, y: float, length: float, grip: Sequence[Grip], snap: float | None = None, *, recoil: float = CHAIN_RECOIL
) -> ChainRun:
    """When the chain of ``length`` from (``x``, ``y``) runs out along ``grip``, without drawing it, so a script can
    put the yank and the rattle on the moment. A snap before the chain is taut raises: nothing has pulled yet."""
    _check_chain(x, y, length, grip, snap)
    taut = None
    for (a, ax, ay), (b, bx, by) in zip(grip, grip[1:], strict=False):
        if math.hypot(bx - x, by - y) < length:
            continue
        low, high = 0.0, 1.0  # the walk leaves the circle once: bisect the row that crosses it
        if math.hypot(ax - x, ay - y) >= length:
            high = 0.0
        for _ in range(40):
            mid = (low + high) / 2
            inside = math.hypot(ax + (bx - ax) * mid - x, ay + (by - ay) * mid - y) < length
            low, high = (mid, high) if inside else (low, mid)
        taut = a + (b - a) * high
        break
    if snap is None:
        return ChainRun(taut, None, None)
    if taut is None or snap < taut:
        raise CutoutCounterError(f"a pen is pulled from the hand once the chain is taut ({taut}), not at {snap}")
    return ChainRun(taut, snap, snap + recoil)


def _pen_at(x: float, y: float, length: float, grip: Sequence[Grip], run: ChainRun, t: float) -> Point:
    """Where the pen is at ``t``: in the hand, stopped by the chain, flying home, or on its cradle."""
    if t <= grip[0][0]:
        return x, y
    if run.home is not None and t >= run.home:
        return x, y
    px, py = _along(grip, t if run.taut is None else min(t, run.taut))
    if run.snap is not None and t > run.snap:
        share = ((t - run.snap) / (run.home - run.snap)) ** 2
        return px + (x - px) * share, py + (y - py) * share
    return px, py


def _link(x: float, y: float, pen: Point, length: float, share: float, shake: float) -> Point:
    """A link ``share`` of the way along the chain: a sagging curve while it has slack, a line once it has none, and
    ``shake`` across the line."""
    px, py = pen
    gap = math.hypot(px - x, py - y)
    slack = max(0.0, 1 - gap / length)
    sag = CHAIN_SAG * math.sqrt(max(0.0, length * length - gap * gap)) / 2 * 4 * share * (1 - share)
    bow = shake * math.sin(math.pi * share) + CHAIN_LOOP * slack * math.sin(2 * math.pi * share)
    nx, ny = ((py - y) / gap, -(px - x) / gap) if gap > 1e-6 else (1.0, 0.0)
    return x + (px - x) * share + nx * bow, y + (py - y) * share + sag + ny * bow


def _shake(t: float, run: ChainRun) -> float:
    """How far the chain's middle stands off its line at ``t``: the twang at the end of it, the swing back home."""
    if run.taut is not None and t >= run.taut and (run.snap is None or t <= run.snap):
        since = t - run.taut
        return 26 * math.exp(-since / (CHAIN_TWANG / 3)) * math.sin(2 * math.pi * 11 * since)
    if run.snap is not None and t > run.snap:
        since = t - run.snap
        return 60 * math.exp(-since / (CHAIN_SETTLE / 2.5)) * math.sin(2 * math.pi * 3.5 * since)
    return 0.0


@register(
    "prop",
    "pen-on-chain",
    style="cutout",
    summary="A counter pen on its ball chain: it follows a hand, stops dead at the end of the chain, and snaps home",
)
def pen_on_chain(
    cv: Canvas,
    parent,
    x=300,
    y=1060,
    *,
    length: float = 520,
    grip: Sequence[Grip] = ((0.0, 300, 1060), (1.0, 300, 1060)),
    snap: float | None = None,
    scale: float = 1.0,
    id: str = "pen-on-chain",
) -> ChainRun:
    """A pen on a cradle at (``x``, ``y``), on a slack chain of ``length``. From ``grip``'s first time a hand carries
    it along ``grip``'s ``(time, x, y)`` rows until the chain runs out, where it stops dead however far the hand means
    to go and the chain twangs. At ``snap`` the chain takes the pen back: it flies home over :data:`CHAIN_RECOIL` and
    the chain swings out over :data:`CHAIN_SETTLE`. Nothing moves before the grip. Returns the :class:`ChainRun`."""
    if not (checks.number(scale) and scale > 0):
        raise CutoutCounterError(f"scale must be a positive number, got {scale!r}")
    run = chain_run(x, y, length, grip, snap)
    ink = cv.ink
    g = cv.group(parent, id)
    start = grip[0][0]
    if run.home is not None:
        end = run.home + CHAIN_SETTLE
    elif run.taut is not None:
        end = run.taut + CHAIN_TWANG
    else:
        end = grip[-1][0]
    steps = math.ceil((end - start) / CHAIN_STEP)
    times = [start + i * CHAIN_STEP for i in range(steps + 1)]
    cv.rect(g, x - 34 * scale, y - 14 * scale, 68 * scale, 18 * scale, "#3A3F46", ink, 3, radius=7)  # the cradle
    pens = [_pen_at(x, y, length, grip, run, t) for t in times]
    for k in range(1, CHAIN_LINKS):
        link = cv.group(g, f"{id}-link-{k}")
        share = k / CHAIN_LINKS
        rows = [_link(x, y, p, length, share, _shake(t, run)) for t, p in zip(times, pens, strict=True)]
        rest = _link(x, y, (x, y), length, share, 0.0)
        cv.keys(link, "x", [(0, rest[0]), *((t, r[0]) for t, r in zip(times, rows, strict=True))], hold=False)
        cv.keys(link, "y", [(0, rest[1]), *((t, r[1]) for t, r in zip(times, rows, strict=True))], hold=False)
        cv.ellipse(link, -4.5 * scale, -4.5 * scale, 9 * scale, 9 * scale, CHAIN_METAL, ink, 1.5)
    pen = cv.group(g, f"{id}-pen")
    cv.keys(pen, "x", [(0, x), *((t, p[0]) for t, p in zip(times, pens, strict=True))], hold=False)
    cv.keys(pen, "y", [(0, y), *((t, p[1]) for t, p in zip(times, pens, strict=True))], hold=False)
    tilt = [(0, -18.0), (start, -18.0), (start + 0.12, 62.0)]
    if run.home is not None:
        tilt += [(run.snap, 62.0), (run.home, -30.0), (run.home + 0.1, -12.0), (run.home + 0.2, -18.0)]
    cv.keys(pen, "rotation", tilt, hold=False)
    cv.rect(pen, -6 * scale, -66 * scale, 12 * scale, 74 * scale, PEN_BODY, ink, 2.5, radius=4)
    cv.rect(pen, -6 * scale, -66 * scale, 12 * scale, 12 * scale, "#C9A24E", ink, 2)  # the end the chain is fixed to
    cv.path(pen, f"M{-5 * scale} {8 * scale} L0 {20 * scale} L{5 * scale} {8 * scale}Z", "#D8D2C4", ink, 2)
    return run


@register("prop", "paper-poster", style="cutout", summary="A cheerful paper poster taped up, a little crooked")
def paper_poster(
    cv: Canvas,
    parent,
    x=700,
    y=590,
    *,
    text: str = "WE'RE\nHERE\nFOR YOU",
    width: float = 210,
    height: float = 240,
    size: int = 36,
    tilt: float = -2.5,
    id: str = "paper-poster",
):
    """A sheet ``width`` by ``height`` with its top left at (``x``, ``y``), taped at the corners, lettered ``text``."""
    if not text.strip():
        raise CutoutCounterError("a poster says something")
    if not (checks.number(width) and checks.number(height) and width > 0 and height > 0):
        raise CutoutCounterError(f"a poster has a positive size, got {width!r} by {height!r}")
    if not (checks.number(size) and size > 0) or not checks.number(tilt):
        raise CutoutCounterError(f"a poster's size is positive and its tilt finite, got {size!r}, {tilt!r}")
    g = cv.group(parent, id, x=x + width / 2, y=y + height / 2, rotation=tilt)
    left, top = -width / 2, -height / 2
    cv.rect(g, left + 6, top + 8, width, height, "#2A2018", opacity=0.3)
    cv.rect(g, left, top, width, height, "#FFFDF4", cv.ink, 3)
    cv.rect(g, left, top, width, 18, "#D9472B")
    for cx, cy in ((left, top), (-left, top)):
        cv.rect(g, cx - 22, cy - 9, 44, 18, "#E9DFAE", opacity=0.85)
    cv.text(g, f"{id}-words", text, left + 8, top + 34, width - 16, height - 42, size, "#1F2B4A")
    return g


@register(
    "prop", "jump-clock", style="cutout", summary="A wall clock whose hands race on between one shot and the next"
)
def jump_clock(
    cv: Canvas,
    parent,
    x=540,
    y=300,
    *,
    start: tuple[int, int] = (3, 10),
    jumps: Sequence[tuple[float, float]] = (),
    spin: float = CLOCK_SPIN,
    radius: float = 80,
    id: str = "jump-clock",
):
    """A clock centred on (``x``, ``y``) reading ``start`` (hour, minute). Each jump ``(time, minutes)`` takes the hands
    on that many minutes over ``spin`` seconds from its time, the hour hand in step, and then they stop: the wait the
    next shot picks up from. Between jumps it is still. Jumps rise, never overlap, and go forward."""
    hour, minute = start
    if not (isinstance(hour, int) and isinstance(minute, int) and 1 <= hour <= 12 and 0 <= minute < 60):
        raise CutoutCounterError(f"a clock starts at an hour 1 to 12 and a minute under 60, got {start!r}")
    if not (checks.number(radius) and radius > 0):
        raise CutoutCounterError(f"a clock's radius is positive, got {radius!r}")
    if not (checks.number(spin) and spin > 0):
        raise CutoutCounterError(f"a jump takes a positive time, got {spin!r}")
    if not all(len(j) == 2 and checks.number(j[0]) and j[0] >= 0 and checks.number(j[1]) and j[1] > 0 for j in jumps):
        raise CutoutCounterError(f"a jump is (time, minutes), with both positive, got {jumps!r}")
    if any(b[0] < a[0] + spin for a, b in zip(jumps, jumps[1:], strict=False)):
        raise CutoutCounterError(f"a jump starts after the one before it has stopped, got {jumps!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y)
    cv.ellipse(g, -radius - 7, -radius - 3, 2 * radius + 14, 2 * radius + 14, "#2A2018", opacity=0.28)
    cv.ellipse(g, -radius, -radius, 2 * radius, 2 * radius, "#FFFDF4", ink, radius * 0.09)
    for k in range(12):
        angle = math.radians(30 * k)
        inner = radius * (0.76 if k % 3 == 0 else 0.84)
        cv.line(
            g,
            inner * math.sin(angle),
            -inner * math.cos(angle),
            radius * 0.9 * math.sin(angle),
            -radius * 0.9 * math.cos(angle),
            ink,
            radius * (0.05 if k % 3 == 0 else 0.03),
        )
    hours = cv.group(g, f"{id}-hour")
    minutes = cv.group(g, f"{id}-minute")
    gone, big, small = 0.0, [(0.0, 6.0 * minute)], [(0.0, 30.0 * hour + 0.5 * minute)]
    for at, more in jumps:
        big += [(at, 6.0 * minute + 6 * gone), (at + spin, 6.0 * minute + 6 * (gone + more))]
        small += [(at, 30.0 * hour + 0.5 * (minute + gone)), (at + spin, 30.0 * hour + 0.5 * (minute + gone + more))]
        gone += more
    cv.keys(minutes, "rotation", big, hold=False)
    cv.keys(hours, "rotation", small, hold=False)
    cv.line(hours, 0, radius * 0.1, 0, -radius * 0.5, ink, radius * 0.1)
    cv.line(minutes, 0, radius * 0.14, 0, -radius * 0.74, "#B03A2E", radius * 0.07)
    cv.ellipse(g, -radius * 0.08, -radius * 0.08, radius * 0.16, radius * 0.16, ink)
    return g


@register("prop", "sandwich", style="cutout", summary="A sandwich with a bite gone, on white bread")
def sandwich(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, id: str = "sandwich"):
    """Centred on (``x``, ``y``), its bitten corner up."""
    if not (checks.number(scale) and scale > 0):
        raise CutoutCounterError(f"scale must be a positive number, got {scale!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    bread = "M-60 -22 Q-64 -44 -40 -42 L6 -42 Q2 -30 14 -28 Q30 -26 30 -40 L40 -40 Q62 -44 60 -22 Z"
    cv.rect(g, -60, 12, 120, 26, "#F2E2BE", ink, 3, radius=9)
    cv.path(g, "M-64 12 Q-46 0 -28 12 Q-10 0 8 12 Q26 0 44 12 Q56 2 66 12 L60 18 L-60 18Z", "#7FA45F", ink, 2.5)
    cv.rect(g, -56, -6, 112, 12, "#C9573F", ink, 2.5, radius=4)
    cv.rect(g, -58, -20, 116, 14, "#F0C655", ink, 2.5, radius=3)
    cv.path(g, bread, "#F2E2BE", ink, 3)
    return g


def _folding_chair(cv: Canvas, g, x: float, floor: float, name: str) -> None:
    ink = cv.ink
    grey = "#9AA3A8"
    chair = cv.group(g, name)
    cv.path(
        chair, f"M{x - 84} {floor} L{x + 74} {floor - 250} M{x + 84} {floor} L{x - 74} {floor - 250}", stroke=ink, sw=13
    )
    cv.path(
        chair, f"M{x - 84} {floor} L{x + 74} {floor - 250} M{x + 84} {floor} L{x - 74} {floor - 250}", stroke=grey, sw=7
    )
    cv.rect(chair, x - 90, floor - 262, 180, 30, grey, ink, 4, radius=9)
    cv.rect(chair, x - 74, floor - 520, 148, 90, grey, ink, 4, radius=12)
    for side in (-1, 1):
        cv.line(chair, x + side * 66, floor - 430, x + side * 66, floor - 240, ink, 9)


@register(
    "location",
    "back-room",
    style="cutout",
    summary="A hall door with a nameplate, and behind it a cupboard: shelves, a bare bulb, two folding chairs",
)
def back_room(
    cv: Canvas,
    parent,
    in_room: locations.Slot = None,
    id="back-room",
    shots: Spans | None = None,
    *,
    plate: str = "MANAGER",
    push: tuple[float, float] = (0.0, 3.0),
    opens: float = 0.0,
):
    """The door to a cupboard, seen from the hall. At ``opens`` the door swings in, and over ``push`` (start, end) the
    hall goes past the frame and the room grows to fill it, the hall faster, so it is a push through a door and not a
    zoom. ``in_room`` draws on the room's own 1080 by 1920, in front of its back wall and its chairs."""
    start, end = push
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise CutoutCounterError(f"a push runs from a start to a later end, got {push!r}")
    if not (checks.number(opens) and 0 <= opens <= start):
        raise CutoutCounterError(f"the door opens by the time the push starts, got {opens!r} for {push!r}")
    if not plate.strip():
        raise CutoutCounterError("a nameplate says something")
    ink = cv.ink
    g = cv.group(parent, id)
    if shots is not None:
        cv.gate(g, shots)
    room = cv.group(g, f"{id}-room", x=540, y=900)
    for prop in ("scaleX", "scaleY"):
        cv.keys(room, prop, [(0, ROOM_FAR), (start, ROOM_FAR), (end, 1.0)], kind="sine-in-out")
    inner = cv.group(room, f"{id}-inside", x=-540, y=-900)
    wall = cv.grad(f"{id}-wall", [(0, "#8C8672"), (0.7, "#A8A18A"), (1, "#7E7966")], (0, 0, 0, 1))
    floor = cv.grad(f"{id}-floor", [(0, "#6A5F50"), (1, "#8A7D6B")], (0, 0, 0, 1))
    cv.rect(inner, -700, -700, 2480, 2120, wall)  # past the frame: the hall lets go of the room before it fills it
    cv.rect(inner, -700, 1420, 2480, 1200, floor)
    cv.line(inner, -700, 1420, 1780, 1420, ink, 4)
    for yy in (330, 620):
        cv.rect(inner, 40, yy, 1000, 20, "#B9A27E", ink, 4)
        for xx in (70, 1000):
            cv.path(inner, f"M{xx} {yy + 20} L{xx} {yy + 60} L{xx + 12} {yy + 20}Z", "#5C5546", ink, 2)
    for x, y, w, h, paint in (
        (90, 214, 190, 116, "#C8AE86"),
        (300, 244, 120, 86, "#D9C39B"),
        (700, 224, 170, 106, "#B99C74"),
        (880, 270, 110, 60, "#D9C39B"),
        (70, 540, 150, 80, "#D9C39B"),
        (760, 500, 220, 120, "#C8AE86"),
    ):
        cv.rect(inner, x, y, w, h, paint, ink, 3.5)
        cv.line(inner, x + w / 2, y, x + w / 2, y + h * 0.3, "#E9DFAE", 8)
    signature.code(cv, inner, 868, 550, 11, color="#5C4D3E")
    signature.cactus(cv, inner, 330, 618, 0.7)
    cv.line(inner, 540, -40, 540, 96, ink, 4)
    cv.rect(inner, 520, 96, 40, 26, "#3A3F46", ink, 3)
    cv.ellipse(inner, 512, 118, 56, 66, "#FFF2C4", ink, 4)
    cv.path(inner, "M360 180 L720 180 L1000 1420 L80 1420Z", "#FFF2C4", cv.clear, 0, opacity=0.12)  # under the bulb
    _folding_chair(cv, inner, 230, 1560, f"{id}-chair-left")
    _folding_chair(cv, inner, 850, 1560, f"{id}-chair-right")
    locations._call(in_room, inner)
    hall = cv.group(g, f"{id}-hall", x=540, y=900)
    for prop in ("scaleX", "scaleY"):
        cv.keys(hall, prop, [(0, 1.0), (start, 1.0), (end, HALL_NEAR)], kind="sine-in-out")
    w, h = DOOR
    paint = "#5F6F7C"
    for x, y, rw, rh in (
        (-1600, -1600, 3200, 1600 - h / 2),
        (-1600, h / 2, 3200, 1600 - h / 2),
        (-1600, -h / 2, 1600 - w / 2, h),
        (w / 2, -h / 2, 1600 - w / 2, h),
    ):
        cv.rect(hall, x, y, rw, rh, paint)
    cv.rect(hall, -w / 2 - 22, -h / 2 - 22, w + 44, h + 22, cv.clear, "#E4DFD0", 22)
    cv.rect(hall, -w / 2 - 34, -h / 2 - 34, w + 68, h + 34, cv.clear, ink, 4)
    cv.rect(hall, -1600, h / 2, 3200, 30, "#3A3F46", ink, 3)
    door = cv.group(hall, f"{id}-door", x=-w / 2, y=0)
    cv.keys(door, "scaleX", [(0, 1.0), (opens, 1.0), (opens + 0.5, 0.06)], kind="sine-in-out")
    cv.rect(door, 0, -h / 2, w, h, "#A98B66", ink, 4)
    for y in (-h / 2 + 50, 40):
        cv.rect(door, 60, y, w - 120, h / 2 - 100, "#B99C74", ink, 3)
    cv.rect(door, 120, -h / 2 + 110, w - 240, 84, "#E4DFD0", ink, 4, radius=8)
    cv.text(door, f"{id}-plate", plate, 124, -h / 2 + 124, w - 248, 60, 42, "#1F2B4A")
    cv.ellipse(door, w - 62, 30, 34, 34, "#D9B44A", ink, 3)
    return g

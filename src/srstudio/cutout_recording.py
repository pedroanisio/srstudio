"""Cutout, a one-way video interview: an invented recording window, and what comes through the door behind you.

The window copies no real product: a plain dark frame, a red dot and a clock that counts down one label a second. Its
meters are bars with a word beside them, and a tracked face is four corner marks. The bowl, the spoon and the door are
generic. Every refusal is a :class:`CutoutRecordingError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = [
    "CutoutRecordingError",
    "cereal_bowl",
    "face_box",
    "green_tick",
    "meter_panel",
    "recording_window",
    "room_door",
    "spoon",
]

FRAME = (40.0, 96.0, 1000.0, 1544.0)  # the video's pane inside the window: x, y, width, height
CHROME = "#14171C"
SIGNAL = "#6FE39A"
RED = "#E5392F"
MOST_SECONDS = 600
MOST_METERS = 4
LABEL = 10  # the most characters beside a bar
METER_W, METER_H = 276.0, 22.0
BLINK = 0.6  # seconds the red dot stays on, and off


class CutoutRecordingError(SrstudioError, ValueError):
    """A prop asked for with arguments it cannot be drawn from."""


def _scale(scale) -> None:
    checks.positive(scale, CutoutRecordingError, f"scale must be a positive number, got {scale!r}")


def _at(at) -> None:
    checks.non_negative(at, CutoutRecordingError, f"a time is a number of at least 0, got {at!r}")


@register("prop", "recording-window", style="cutout", summary="An invented recording window: red dot and a countdown")
def recording_window(
    cv: Canvas, parent, *, seconds: int = 30, end: float = 20.0, stop: float | None = None, id: str = "recording-window"
):
    """Dark chrome round :data:`FRAME`, drawn over the shot, with the clock top left. It starts at ``seconds`` at t 0
    and drops one label a second; ``stop`` freezes it and puts the red dot out, and ``end`` is when the reel ends."""
    if not isinstance(seconds, int) or isinstance(seconds, bool) or not 1 <= seconds <= MOST_SECONDS:
        raise CutoutRecordingError(f"seconds is a whole number from 1 to {MOST_SECONDS}, got {seconds!r}")
    checks.positive(end, CutoutRecordingError, f"end must be a positive number, got {end!r}")
    if stop is not None:
        _at(stop)
        if stop >= end:
            raise CutoutRecordingError(f"the clock stops inside the reel: stop {stop!r}, end {end!r}")
    x, y, w, h = FRAME
    g = cv.group(parent, id)
    cv.rect(g, -20, -20, 1120, y + 20, CHROME)
    cv.rect(g, -20, y + h, 1120, 1960 - y - h, CHROME)
    cv.rect(g, -20, y, x + 20, h, CHROME)
    cv.rect(g, x + w, y, 60, h, CHROME)
    cv.rect(g, x, y, w, h, cv.clear, "#3A4048", 4)
    pill = cv.group(g, f"{id}-clock", x=70, y=226)
    cv.rect(pill, 0, 0, 240, 72, CHROME, radius=14)
    dot = cv.group(pill, f"{id}-dot")
    stops = stop if stop is not None else end
    on = []
    at = 0.0
    while at < stops:
        on.append((at, min(at + BLINK, stops)))
        at += 2 * BLINK
    cv.gate(dot, on)
    cv.ellipse(dot, 22, 20, 32, 32, RED)
    last = min(int(stops), seconds)
    for n in range(last + 1):
        left = seconds - n
        label = cv.group(pill, f"{id}-at-{left}")
        cv.gate(label, [(float(n), end if n == last else float(n + 1))])
        cv.text(label, f"{id}-time-{left}", f"{left // 60}:{left % 60:02d}", 68, 8, 160, 56, 44, "#F6F3EA")
    return g


@register("prop", "meter-panel", style="cutout", summary="Up to four labelled bars that move at the reel's times")
def meter_panel(
    cv: Canvas,
    parent,
    x=80,
    y=1250,
    meters: Sequence[tuple[str, Sequence[tuple[float, float]]]] = (("EYES", ((0.0, 0.5),)),),
    *,
    id: str = "meter-panel",
):
    """Its top left on (``x``, ``y``). Each meter is a label and (time, fraction) keys, fractions from 0 to 1."""
    if not 1 <= len(meters) <= MOST_METERS:
        raise CutoutRecordingError(f"a panel holds 1 to {MOST_METERS} meters, got {len(meters)}")
    for label, keys in meters:
        if not isinstance(label, str) or not label.strip() or len(label) > LABEL:
            raise CutoutRecordingError(f"a meter's label is 1 to {LABEL} characters, got {label!r}")
        if not keys:
            raise CutoutRecordingError(f"meter {label!r} has no keys")
        times = [t for t, _ in keys]
        if times != sorted(times) or not all(checks.number(t) and t >= 0 for t in times):
            raise CutoutRecordingError(f"meter {label!r} needs rising times, got {times!r}")
        if not all(checks.number(f) and 0 <= f <= 1 for _, f in keys):
            raise CutoutRecordingError(f"meter {label!r} needs fractions from 0 to 1, got {keys!r}")
    row = 46.0
    g = cv.group(parent, id, x=x, y=y)
    cv.rect(g, 0, 0, 520, 16 + row * len(meters), CHROME, radius=14)
    for i, (label, keys) in enumerate(meters):
        yy = 8 + row * i
        cv.text(g, f"{id}-label-{i}", label, 16, yy + 5, 206, 40, 26, "#F6F3EA")
        cv.rect(g, 228, yy + 12, METER_W, METER_H, "#3A4048", radius=6)
        fill = cv.group(g, f"{id}-fill-{i}", x=228, y=yy + 12)
        cv.keys(fill, "scaleX", [(t, max(f, 0.001)) for t, f in keys], hold=False)
        cv.rect(fill, 0, 0, METER_W, METER_H, SIGNAL, radius=6)
    return g


@register("prop", "face-box", style="cutout", summary="Four corner marks round a tracked face")
def face_box(
    cv: Canvas,
    parent,
    x=540,
    y=800,
    size: float = 300,
    *,
    spans: Sequence[tuple[float, float]] = (),
    color: str = SIGNAL,
    id: str = "face-box",
):
    """Centred on (``x``, ``y``), ``size`` from the middle to a side. ``spans`` are when it shows; none means always."""
    checks.positive(size, CutoutRecordingError, f"size must be a positive number, got {size!r}")
    g = cv.group(parent, id, x=x, y=y)
    if spans:
        cv.gate(g, spans)
    arm = size * 0.3
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * size, sy * size
            cv.path(g, f"M{cx - sx * arm} {cy} L{cx} {cy} L{cx} {cy - sy * arm}", stroke=color, sw=7)
    return g


@register("prop", "green-tick", style="cutout", summary="A green disc with a tick that lands at the reel's time")
def green_tick(cv: Canvas, parent, x=900, y=500, *, at: float = 0.0, scale: float = 1.0, id: str = "green-tick"):
    """Centred on (``x``, ``y``), 160 across at scale 1, off until ``at``, then popped in and kept."""
    _at(at)
    _scale(scale)
    g = cv.group(parent, id, x=x, y=y)
    cv.keys(g, "opacity", [(0, 0.0), (at, 1.0)])
    inner = cv.group(g, f"{id}-pop")
    cv.pop_in(inner, at, rest=scale, from_=scale * 0.4, over=scale * 1.12)
    cv.ellipse(inner, -80, -80, 160, 160, "#2FB56A", cv.ink, 5)
    cv.path(inner, "M-40 2 L-10 34 L44 -30", stroke="#FFFFFF", sw=16)
    return g


@register("prop", "cereal-bowl", style="cutout", summary="A bowl of cereal, seen from the side, about half eaten")
def cereal_bowl(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, id: str = "cereal-bowl"):
    """Its foot's middle stands on (``x``, ``y``), 190 wide at scale 1."""
    _scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -92, -102, 184, 34, "#FBF6EA", ink, 3.5)
    for dx, dy, tone in ((-52, -92, "#D79A3E"), (-20, -96, "#E9B455"), (14, -91, "#C9862E"), (46, -94, "#E9B455")):
        cv.ellipse(g, dx - 11, dy - 7, 22, 14, tone, ink, 2)
    cv.path(g, "M-95 -86 Q-84 -8 -36 -6 L36 -6 Q84 -8 95 -86 Q0 -60 -95 -86Z", "#5E8FA8", ink, 4)
    cv.rect(g, -34, -8, 68, 10, "#4A7389", ink, 3, radius=3)
    return g


@register("prop", "spoon", style="cutout", summary="A plain spoon, its bowl at the grip's far end")
def spoon(cv: Canvas, parent, x=540, y=900, *, scale: float = 1.0, rotation: float = 0, id: str = "spoon"):
    """The grip is on (``x``, ``y``) and it points up, ``rotation`` degrees round; 170 long at scale 1."""
    _scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=rotation)
    cv.path(g, "M-5 40 L-4 -90 L4 -90 L5 40 Q0 48 -5 40Z", "#C9CFD3", ink, 3)
    cv.ellipse(g, -21, -130, 42, 56, "#DDE2E5", ink, 3)
    return g


@register("prop", "room-door", style="cutout", summary="A plain white room door in its frame, opening inwards")
def room_door(
    cv: Canvas, parent, x=520, y=960, *, opens: float | None = None, scale: float = 1.0, id: str = "room-door"
):
    """Its foot's middle stands on (``x``, ``y``), 190 by 560 at scale 1, hinged on the left. ``opens`` swings the
    panel back over 0.35 s onto the dark behind it; ``None`` leaves it shut."""
    if opens is not None:
        _at(opens)
    _scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -107, -574, 214, 574, "#EDE6D6", ink, 4)
    cv.rect(g, -95, -560, 190, 560, "#2C2A2E", ink, 3)
    panel = cv.group(g, f"{id}-panel", x=-95, y=-560)
    if opens is not None:
        cv.keys(panel, "scaleX", [(0, 1.0), (opens, 1.0), (opens + 0.35, 0.2)], hold=False, kind="sine-in-out")
    cv.rect(panel, 0, 0, 190, 560, "#F4EFE2", ink, 3)
    cv.rect(panel, 24, 30, 142, 220, "#E6DFCE", "#C7BFAC", 2.5)
    cv.rect(panel, 24, 300, 142, 230, "#E6DFCE", "#C7BFAC", 2.5)
    cv.ellipse(panel, 158, 270, 18, 18, "#C9A24E", ink, 2.5)
    return g

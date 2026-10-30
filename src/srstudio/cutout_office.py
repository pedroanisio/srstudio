"""Cutout at the office, off the clock: the break room, the retirement party, and the props of a long career.

Each set follows :mod:`srstudio.locations`: it draws in z-order, calls its slots at the right depth, gates its root
group before drawing, and places both signature marks. A set's far plane is its own blurred group, so the cast, the
props and the marks stay sharp.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from . import checks, locations, look, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

Slot = locations.Slot

__all__ = [
    "BOARD_CHARS",
    "BREAK_COUNTER_Y",
    "CutoutOfficeError",
    "MUG_LABEL",
    "PLANNER_WEEKS",
    "PARTY_BANNER_CHARS",
    "break_room",
    "days_board",
    "drip_machine",
    "gold_watch",
    "office_mug",
    "office_party",
    "party_crowd",
    "stage_mic",
    "wall_planner",
]

BREAK_COUNTER_Y = 1140  # the counter's far edge: whoever stands behind it is hidden below this line
BOARD_CHARS = 7  # the most characters the days board holds
MUG_LABEL = 8  # the most characters a mug's lettering holds
PLANNER_WEEKS = 5  # rows on a page of the planner
PARTY_BANNER_CHARS = 14
SHADOW = "#2A2018"
RED_PEN = "#D23A2E"


class CutoutOfficeError(SrstudioError, ValueError):
    """A prop or a set asked for with arguments it cannot be drawn from."""


def _check_scale(scale) -> None:
    checks.positive(scale, CutoutOfficeError, f"scale must be a positive number, got {scale!r}")


def _readings(values: Sequence[tuple[float, str]], limit: int, what: str) -> None:
    """Timed text from 0 in strictly rising order, each 1 to ``limit`` characters."""
    times = [t for t, _ in values]
    if not values or times[0] != 0 or any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise CutoutOfficeError(f"{what} start at 0 and rise strictly, got {times!r}")
    for _, text in values:
        if not text.strip() or len(text) > limit:
            raise CutoutOfficeError(f"each of the {what} has 1 to {limit} characters, got {text!r}")


def _timed(cv: Canvas, g, name: str, values: Sequence[tuple[float, str]], index: int) -> object:
    """The group that shows reading ``index`` of ``values`` until the next one."""
    start = values[index][0]
    until = values[index + 1][0] if index + 1 < len(values) else 3600.0
    shown = cv.group(g, f"{name}-{index + 1}")
    cv.gate(shown, [(start, until)])
    return shown


@register(
    "prop",
    "drip-machine",
    style="cutout",
    summary="An office drip coffee machine with a glass carafe and a thin stream that runs on cue",
)
def drip_machine(
    cv: Canvas,
    parent,
    x=540,
    y=1140,
    *,
    pours: Sequence[tuple[float, float]] = (),
    scale: float = 1.0,
    id: str = "drip-machine",
):
    """The foot's middle stands on (``x``, ``y``); the stream runs in each of the ``pours`` spans."""
    _check_scale(scale)
    checks.spans(
        pours, CutoutOfficeError, lambda s: f"a pour is a rising span, got {s!r}", ordered="pours run in order"
    )
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    look.pool(cv, g, f"{id}-contact", SHADOW + "CC", -130, -24, 300, 48, opacity=0.5)
    steel = cv.grad(f"{id}-body", [(0, "#4A5157"), (0.5, "#2F353A"), (1, "#1F2327")], (0, 0, 1, 0.3))
    cv.rect(g, -120, -22, 240, 22, "#1F2327", ink, 4, radius=6)
    cv.rect(g, 66, -300, 54, 290, steel, ink, 4, radius=8)
    cv.rect(g, -120, -340, 240, 74, steel, ink, 4, radius=14)
    cv.rect(g, -100, -326, 90, 8, "#FFFFFF", radius=4, opacity=0.35)
    cv.ellipse(g, 74, -312, 18, 18, "#E2574A", ink, 2.5)
    cv.path(g, "M-104 -196 L-92 -14 Q-20 -2 40 -14 L52 -196 L30 -216 L-82 -216Z", "#DDEBEE", ink, 4)
    cv.path(g, "M-97 -96 Q-30 -82 45 -96 L38 -20 Q-20 -8 -90 -20Z", "#5A3921", ink, 3)
    cv.path(g, "M-86 -186 L-84 -40", stroke="#FFFFFF", sw=7, opacity=0.6)
    if pours:
        stream = cv.group(g, f"{id}-stream")
        cv.gate(stream, list(pours))
        cv.line(stream, -26, -266, -26, -96, "#5A3921", 7)
    return g


@register(
    "prop",
    "office-mug",
    style="cutout",
    summary="A plain office mug in any colour, with up to eight characters of lettering",
)
def office_mug(
    cv: Canvas,
    parent,
    x=540,
    y=1140,
    *,
    colour: str = "#F2EDE0",
    label: str | None = None,
    scale: float = 1.0,
    id: str = "office-mug",
):
    """The mug's foot stands on (``x``, ``y``), 120 wide and 130 tall at scale 1, handle to the right."""
    _check_scale(scale)
    if label is not None:
        if not label.strip() or len(label) > MUG_LABEL:
            raise CutoutOfficeError(f"a mug's label is 1 to {MUG_LABEL} characters or None, got {label!r}")
        cv.require_font("a mug's lettering is set in it", CutoutOfficeError)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.path(g, "M56 -104 Q104 -104 100 -66 Q96 -34 54 -34", stroke=ink, sw=20)
    cv.path(g, "M56 -104 Q104 -104 100 -66 Q96 -34 54 -34", stroke=colour, sw=11)
    cv.path(g, "M-60 -130 L-54 -10 Q-52 0 -42 0 L42 0 Q52 0 54 -10 L60 -130Z", colour, ink, 4.5)
    cv.path(g, "M-44 -116 L-40 -22", stroke="#FFFFFF", sw=7, opacity=0.55)
    if label is not None:
        cv.text(g, f"{id}-label", label, -56, -96, 112, 50, 24, ink)
    return g


@register(
    "prop",
    "days-board",
    style="cutout",
    summary="A wall board in the manner of a workplace safety sign: a heading, and a day count that changes on cue",
)
def days_board(
    cv: Canvas,
    parent,
    x=540,
    y=130,
    *,
    heading: str = "DAYS SINCE",
    counts: Sequence[tuple[float, str]] = ((0.0, "0"),),
    scale: float = 1.0,
    id: str = "days-board",
):
    """The board's top middle hangs at (``x``, ``y``), 620 × 300 at scale 1. ``counts`` are ``(time, text)`` from 0 in
    rising order, each held until the next (1 to :data:`BOARD_CHARS` characters)."""
    cv.require_font("the board is lettered in it", CutoutOfficeError)
    _check_scale(scale)
    _readings(counts, BOARD_CHARS, "counts")
    if not heading.strip():
        raise CutoutOfficeError("a board needs a heading")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    look.pool(cv, g, f"{id}-contact", SHADOW + "AA", -296, 26, 620, 300, opacity=0.45)
    cv.rect(g, -310, 0, 620, 300, "#FBFAF2", ink, 5, radius=14)
    cv.rect(g, -310, 0, 620, 96, "#2E7D4F", ink, 5, radius=14)
    cv.text(g, f"{id}-heading", heading, -300, 12, 600, 72, 46, "#FFFFFF")
    cv.rect(g, -220, 118, 440, 158, "#1E2226", ink, 4, radius=8)
    for k, (_, text) in enumerate(counts):
        cv.text(
            _timed(cv, g, f"{id}-count", counts, k), f"{id}-digits-{k + 1}", text, -214, 124, 428, 146, 112, "#FFFFFF"
        )
    return g


@register(
    "prop",
    "wall-planner",
    style="cutout",
    summary="A month of a wall planner with its every Friday circled in red pen, its pages flipping on cue",
)
def wall_planner(
    cv: Canvas,
    parent,
    x=90,
    y=260,
    *,
    months: Sequence[tuple[float, str]] = ((0.0, "MARCH"),),
    note: str = "QUIT",
    scale: float = 1.0,
    id: str = "wall-planner",
):
    """The page's top left is (``x``, ``y``), 900 × 1000 at scale 1. ``months`` are ``(time, name)`` from 0 in rising
    order, each page held until the next; every page has its Friday column circled with ``note`` in it."""
    cv.require_font("the planner is printed in it", CutoutOfficeError)
    _check_scale(scale)
    _readings(months, 12, "months")
    if not note.strip():
        raise CutoutOfficeError("a planner's circles need a note")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    look.pool(cv, g, f"{id}-contact", SHADOW + "CC", 30, 40, 900, 1000, opacity=0.55)
    rng = random.Random(21)
    for k, (_, name) in enumerate(months):
        page = _timed(cv, g, f"{id}-page", months, k)
        cv.rect(page, 0, 0, 900, 1000, "#FBFAF2", ink, 4)
        cv.rect(page, 0, 0, 900, 150, "#C8352B", ink, 4)
        cv.text(page, f"{id}-month-{k + 1}", name, 0, 26, 900, 100, 72, "#FFFFFF")
        cell, top = 128.0, 210.0
        for d, day in enumerate("MTWTFSS"):
            cv.text(page, f"{id}-day-{k + 1}-{d}", day, d * cell + 2, 158, 128, 44, 32, "#6A6A62")
        for row in range(PLANNER_WEEKS + 1):
            cv.line(page, 2, top + row * 150, 898, top + row * 150, "#C9C4B4", 3)
        for col in range(1, 7):
            cv.line(page, col * cell, top, col * cell, top + PLANNER_WEEKS * 150, "#C9C4B4", 3)
        for row in range(PLANNER_WEEKS):
            cx, cy = 4.5 * cell + rng.uniform(-6, 6), top + (row + 0.5) * 150 + rng.uniform(-5, 5)
            cv.text(page, f"{id}-note-{k + 1}-{row}", note, cx - 62, cy - 26, 124, 52, 34, RED_PEN)
            cv.path(page, f"M{cx - 66:.1f} {cy:.1f} Q{cx:.1f} {cy - 88:.1f} {cx + 62:.1f} {cy - 6:.1f} "
                          f"Q{cx + 6:.1f} {cy + 84:.1f} {cx - 60:.1f} {cy + 10:.1f}", stroke=RED_PEN, sw=7)  # fmt: skip
    return g


@register("prop", "gold-watch", style="cutout", summary="A gold presentation watch on a gold strap, with a gleam")
def gold_watch(
    cv: Canvas, parent, x=540, y=900, *, gleam: float | None = None, scale: float = 1.0, id: str = "gold-watch"
):
    """The dial's centre is (``x``, ``y``). ``gleam`` is when a highlight crosses it."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    strap = cv.grad(f"{id}-gold", [(0, "#F7DE85"), (0.5, "#D9A93A"), (1, "#A9771F")], (0, 0, 1, 1))
    cv.rect(g, -32, -128, 64, 256, strap, ink, 4, radius=10)
    for yy in (-104, -78, 62, 88):
        cv.line(g, -30, yy, 30, yy, "#8A6118", 3)
    cv.ellipse(g, -66, -66, 132, 132, strap, ink, 5)
    cv.ellipse(g, -50, -50, 100, 100, "#FBFAF2", ink, 3.5)
    cv.line(g, 0, 0, 0, -36, ink, 5)
    cv.line(g, 0, 0, 26, 12, ink, 5)
    if gleam is not None:
        shine = cv.group(g, f"{id}-gleam", x=-90)
        cv.gate(shine, [(gleam, gleam + 0.5)])
        cv.keys(shine, "x", [(0, -90), (gleam, -90), (gleam + 0.5, 90)], hold=False)
        cv.path(shine, "M-14 -74 L14 -74 L2 74 L-26 74Z", "#FFFFFF", opacity=0.75)
    return g


@register("prop", "stage-mic", style="cutout", summary="A microphone on a straight stand, seen from the front")
def stage_mic(cv: Canvas, parent, x=540, y=1100, *, height: float = 420, scale: float = 1.0, id: str = "stage-mic"):
    """The capsule's top is ``height`` above (``x``, ``y``), the foot of the stand."""
    _check_scale(scale)
    checks.positive(height, CutoutOfficeError, f"height must be positive, got {height!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.line(g, 0, 0, 0, -height + 90, "#1F2327", 13)
    cv.rect(g, -13, -height + 70, 26, 66, "#3A4046", ink, 3.5, radius=6)
    cv.ellipse(g, -28, -height, 56, 84, "#8E959C", ink, 4)
    for k in range(1, 5):
        cv.line(g, -24, -height + k * 16, 24, -height + k * 16, "#4C5258", 3)
    return g


@register(
    "prop",
    "party-crowd",
    style="cutout",
    summary="The backs of an audience's heads, out of focus across the foot of the frame, hands up clapping on cue",
)
def party_crowd(
    cv: Canvas, parent, y=1500, *, claps: Sequence[tuple[float, float]] = (), seed: int = 3, id: str = "party-crowd"
):
    """Heads along ``y``, dark and blurred, so a caption reads across them. Hands clap in each of ``claps``."""
    checks.spans(
        claps, CutoutOfficeError, lambda s: f"a clap is a rising span, got {s!r}", ordered="claps run in order"
    )
    rng = random.Random(seed)
    g = cv.group(parent, id)
    soft = look.depth(cv, g, f"{id}-depth", 9.0)
    for k, x in enumerate(range(-40, 1200, 210)):
        tone = rng.choice(("#2A3038", "#34302C", "#3A2C2C", "#26323A"))
        top = y + rng.uniform(-40, 40)
        cv.ellipse(soft, x - 92, top, 184, 200, tone)
        cv.path(soft, f"M{x - 170} {top + 620} Q{x - 150} {top + 200} {x} {top + 180} Q{x + 150} {top + 200} "
                      f"{x + 170} {top + 620}Z", tone)  # fmt: skip
        if claps and k % 2 == 1:
            hands = cv.group(soft, f"{id}-hands-{k}", x=x + 86, y=top + 40)
            cv.gate(hands, list(claps))
            keys: list[tuple[float, float]] = [(0.0, 0.0)]
            for a, b in claps:
                at, sign = a, 1
                while at < b:
                    keys.append((at, sign * 14.0))
                    at, sign = at + 0.11, -sign
            cv.keys(hands, "y", keys, hold=False)
            cv.ellipse(hands, -34, -30, 68, 60, "#C9B7A0")
    return g


@register(
    "location",
    "break-room",
    style="cutout",
    summary="An office break room: mustard wall, cupboards and a fridge out of focus, a counter across the foot of "
    "the frame",
)
def break_room(
    cv: Canvas,
    parent,
    behind_counter: Slot = None,
    on_counter: Slot = None,
    id: str = "location-break-room",
    shots=None,
    on_wall: Slot = None,
    *,
    depth: float = 8.0,
):
    """``on_wall`` hangs in focus on the wall; ``behind_counter`` draws whoever stands there, above
    :data:`BREAK_COUNTER_Y`; ``on_counter`` draws in front of them. A ceiling tube lights it from the top left."""
    ink = cv.ink
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    far = look.depth(cv, g, f"break-depth-{depth:g}", depth)
    wall = cv.grad("break-wall", [(0, "#EBCF8E"), (0.6, "#E0BD73"), (1, "#C9A25C")], (0, 0, 1, 0.5))
    cv.rect(far, -300, -300, 1680, 2000, wall)
    for x in (-60, 250, 560):  # the wall cupboards
        cv.rect(far, x, -40, 290, 320, "#F4EFE0", "#B6AC93", 6)
        cv.ellipse(far, x + 250, 230, 18, 18, "#8A8474")
    cv.rect(far, 880, 60, 300, 1100, "#D9DEDF", "#AEB6B8", 6, radius=20)  # the fridge
    cv.line(far, 880, 430, 1180, 430, "#AEB6B8", 6)
    for yy, colour in ((480, "#D9694F"), (560, "#3F7F8C"), (640, "#F0C655")):
        cv.rect(far, 930, yy, 90, 66, colour)
    light = cv.group(g, f"{id}-light")
    look.pool(cv, light, "break-tube", "#FFF6D8AA", -80, 40, 800, 900)
    locations._call(on_wall, g)
    locations._call(behind_counter, g)
    top = cv.grad("break-counter", [(0, "#8FA39D"), (0.3, "#7B918B"), (1, "#566A66")], (0, 0, 0.2, 1))
    cv.rect(g, -300, BREAK_COUNTER_Y, 1680, 1200, top, ink, 4)
    cv.rect(g, -300, BREAK_COUNTER_Y + 4, 1680, 8, "#FFFFFF", opacity=0.45)
    signature.code(cv, g, 1000, BREAK_COUNTER_Y + 40, 10, color="#32403D", align="end")
    signature.cactus(cv, g, 120, BREAK_COUNTER_Y + 92, 0.55)
    locations._call(on_counter, g)
    return g


@register(
    "location",
    "office-party",
    style="cutout",
    summary="A function room dressed for a leaving do: a dark teal wall, paper streamers and fairy lights out of "
    "focus, and a banner hung in focus",
)
def office_party(
    cv: Canvas,
    parent,
    stage: Slot = None,
    front: Slot = None,
    id: str = "location-office-party",
    shots=None,
    *,
    banner: str = "THANK YOU",
    depth: float = 8.0,
):
    """``stage`` draws whoever is up front, under the banner; ``front`` draws nearest the lens. ``banner`` is 1 to
    :data:`PARTY_BANNER_CHARS` characters."""
    cv.require_font("the banner is lettered in it", CutoutOfficeError)
    if not banner.strip() or len(banner) > PARTY_BANNER_CHARS:
        raise CutoutOfficeError(f"a banner is 1 to {PARTY_BANNER_CHARS} characters, got {banner!r}")
    ink = cv.ink
    g = cv.group(parent, id)
    if shots:
        cv.gate(g, shots)
    cv.rect(g, -10, -10, 1100, 1940, "#1F5860")  # the frame's edge, where the blur thins out
    far = look.depth(cv, g, f"party-depth-{depth:g}", depth)
    wall = cv.grad("party-wall", [(0, "#1E5A63"), (0.6, "#2B6F74"), (1, "#184A52")], (0, 0, 1, 0.6))
    cv.rect(far, -300, -300, 1680, 2400, wall)
    rng = random.Random(11)
    for x in range(-40, 1160, 150):  # streamers
        cv.path(
            far,
            f"M{x} -20 Q{x + 60} 300 {x + rng.uniform(-40, 40):.1f} 640",
            stroke=rng.choice(("#F0C655", "#E2574A", "#F4EFE0")),
            sw=12,
        )
    for k in range(16):  # fairy lights
        cv.ellipse(far, k * 76 - 20, 600 + 70 * ((k % 4) / 3), 34, 34, "#FFE9A8")
    glow = cv.group(g, f"{id}-light")
    look.pool(cv, glow, "party-spot", "#FFE7B8AA", 60, 240, 960, 1000)
    # the banner: paper on a string
    cv.path(g, "M-20 120 Q540 84 1100 120", stroke="#3A2A1C", sw=5)
    cv.path(g, "M60 124 L1020 116 L1012 300 L68 312Z", "#FBF6E6", ink, 5)
    cv.text(g, f"{id}-banner", banner, 70, 136, 940, 150, 112, "#C8352B")
    signature.code(cv, g, 1000, 332, 10, color="#CFE3DF", align="end")
    cv.rect(g, 36, 1200, 170, 16, "#6E5236", ink, 3)  # a small wall shelf
    cv.path(g, "M70 1216 L70 1256 L110 1216Z", "#6E5236", ink, 3)
    signature.cactus(cv, g, 120, 1200, 0.55)
    locations._call(stage, g)
    locations._call(front, g)
    return g

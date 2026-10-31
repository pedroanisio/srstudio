"""Soft sets for a close shot: frontal rooms a medium or a close-up can sit in, each with a far plane out of focus.

The Soft rooms of :mod:`srstudio.blob` are 3/4 views drawn for the whole body at :data:`~srstudio.blob.SCALE`; cut in on
them and the frame is mostly furniture. These are drawn straight on, for a cast at about twice that size, in three
planes: a far plane under :func:`srstudio.look.depth`, the set, and a foreground the ``cast`` slot draws behind.
:func:`finish` is the opt-in grade of a reel drawn in them. Time is part of each set: a park grows (``growth``), a room
goes dark (``dark``), so a reel moves the world and leaves the cast alone.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import NamedTuple

from . import checks, look, signature
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register
from .soft_props import bench as park_bench

__all__ = ["CAPTIONS", "FINISH", "Dim", "Light", "Shot", "SoftSetError", "bedroom", "finish", "park", "playroom"]

WIDTH, HEIGHT = 1080, 1920
Slot = Callable[[object], object] | None
Stages = Sequence[tuple[float, int]]

CAPTIONS = dict(
    x=80, y=250, width=840, height=180, size=58, color="#1A1714", stroke="#FFFFFF", stroke_width=7, shadow=None
)  # the Soft style's caption look (ADR 0048), for ``Episode.captions``
FINISH: dict[str, dict[str, float | str]] = {  # warm corners and a soft lift on what is bright; no grain, no blur
    "vignette": dict(amount=0.22, radius=0.95, softness=0.8, color="#3B2A1E"),
    "bloom": dict(threshold=0.9, radius=16, intensity=0.14),
}
FAR_BLUR = 7.0  # px: the far plane of a set
HORIZON = 1130.0  # where the lawn meets the far plane
TREE_FOOT = 1240.0  # the tree stands on the lawn, behind the path
BENCH_SEAT = 1750.0  # the seat's front edge: a seated head lands where a standing one stood
INK_LINE = 4.0
LEAF_DARK, LEAF_LIT = "#5F9E6A", "#8CC47A"
BARK, BARK_DARK = "#8A6242", "#6B4A30"


NIGHT, NIGHT_CLEAR = "#0B1026FB", "#0B102600"  # the engine composites in linear light: a lit wall needs 98 % to go dark
LIGHTS = ("day", "phone", "dark")
FLICKER = (1.0, 0.93, 0.98, 0.9, 1.0, 0.95, 0.91, 0.99)  # a screen's light changing with what is on it
FLICKER_STEP = 0.14  # seconds a flicker value holds
OVER = 600  # px a room runs past the frame on every side


class Light(NamedTuple):
    """From ``time``, the room is lit by ``state``: ``day``, ``dark``, or a ``phone`` pooled on (``x``, ``y``)."""

    time: float
    state: str
    x: float = 540.0
    y: float = 1040.0


class Shot(NamedTuple):
    """From ``time``, the room is framed ``scale`` times closer, with (``x``, ``y``) in the middle of the frame."""

    time: float
    scale: float = 1.0
    x: float = 540.0
    y: float = 960.0


class Dim(NamedTuple):
    """The room goes dark around (``x``, ``y``): it starts at ``start``, is dark ``fade`` seconds on and ends at
    ``end``."""

    start: float
    fade: float
    end: float
    x: float = 540.0
    y: float = 1100.0


class SoftSetError(SrstudioError, ValueError):
    """A Soft set asked for something it cannot draw."""


def finish(cv: Canvas, parent, id: str = "soft-finish"):
    """A group in ``parent`` graded by :data:`FINISH`, for a reel to draw its set and cast into. Opt-in: nothing
    drawn outside it changes. A camera move goes on a group inside it, so the grade holds still on the frame."""
    return look.grade(cv, cv.group(parent, id), "soft", FINISH)


def _stages(name: str, stages: Stages, count: int) -> list[tuple[float, float, int]]:
    """``(time, stage)`` rows as ``(start, end, stage)`` spans, the last open to a far time; refused unless they start
    at 0, rise and name a stage below ``count``."""
    times = [t for t, _ in stages]
    if not stages or times[0] != 0 or any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise SoftSetError(f"{name} is (time, stage) rows from 0 in rising time, got {list(stages)!r}")
    if not all(checks.number(t) for t in times) or not all(s in range(count) for _, s in stages):
        raise SoftSetError(f"{name} names stages 0 to {count - 1} at finite times, got {list(stages)!r}")
    ends = [*times[1:], 1e6]
    return [(t, e, s) for (t, s), e in zip(stages, ends, strict=True)]


def _spans_of(rows: list[tuple[float, float, int]], stage: int) -> list[tuple[float, float]]:
    return [(a, b) for a, b, s in rows if s == stage]


def _crown(cv: Canvas, g, cx: float, cy: float, r: float, lobes: Sequence[tuple[float, float, float]]) -> None:
    """A leaf crown: lobes of a shared outline, a lit fill and a darker underside, all from the upper left."""
    for dx, dy, k in lobes:
        cv.ellipse(g, cx + dx * r - k * r, cy + dy * r - k * r, 2 * k * r, 2 * k * r, cv.ink, cv.ink, 2 * INK_LINE)
    for dx, dy, k in lobes:
        cv.ellipse(g, cx + dx * r - k * r, cy + dy * r - k * r, 2 * k * r, 2 * k * r, LEAF_DARK)
    for dx, dy, k in lobes:
        q = k * 0.8
        cv.ellipse(g, cx + (dx - 0.06) * r - q * r, cy + (dy - 0.08) * r - q * r, 2 * q * r, 2 * q * r, LEAF_LIT)


LOBES = ((0.0, -0.1, 0.72), (-0.62, 0.12, 0.52), (0.62, 0.12, 0.52), (-0.3, 0.42, 0.46), (0.34, 0.42, 0.46))
TREES = (  # (trunk width at the foot, at the top, crown centre over the foot, crown radius), by stage
    (12.0, 7.0, 520.0, 0.0),
    (26.0, 16.0, 500.0, 130.0),
    (64.0, 40.0, 640.0, 250.0),
    (150.0, 96.0, 760.0, 420.0),
    (330.0, 230.0, 900.0, 640.0),
)


def _tree(cv: Canvas, parent, stage: int, x: float, foot: float, id: str):
    """The park's tree at ``stage``: a staked sapling at 0, a crown wider than the frame at the last."""
    wide, top, over, r = TREES[stage]
    g = cv.group(parent, id)
    if stage == 0:
        cv.line(g, x + 26, foot + 4, x + 26, foot - 420, BARK_DARK, 8)  # the stake
        cv.path(g, f"M {x:g} {foot:g} L {x:g} {foot - over:g}", stroke=cv.ink, sw=wide + 2 * INK_LINE)
        cv.path(g, f"M {x:g} {foot:g} L {x:g} {foot - over:g}", stroke=BARK, sw=wide)
        for sx, sy in ((-1, -over), (1, -over + 62), (-1, -over + 120)):
            cv.path(
                g,
                f"M {x:g} {foot + sy:g} Q {x + sx * 44:g} {foot + sy - 54:g} {x + sx * 100:g} {foot + sy - 34:g} "
                f"Q {x + sx * 60:g} {foot + sy + 16:g} {x:g} {foot + sy:g} Z",
                LEAF_LIT,
                cv.ink,
                INK_LINE,
            )
        return g
    head = foot - over
    right = f"L {x + top / 2:g} {head:g} L {x + wide / 2:g} {foot:g} Z"
    cv.path(g, f"M {x - wide / 2:g} {foot:g} L {x - top / 2:g} {head:g} {right}", BARK, cv.ink, INK_LINE)
    cv.path(g, f"M {x + wide / 8:g} {foot:g} L {x + top / 8:g} {head:g} {right}", BARK_DARK)
    _crown(cv, g, x, head, r, LOBES)
    return g


def _skyline(cv: Canvas, far, rows: list[tuple[float, float, int]], id: str, ground: float) -> None:
    """The town behind the park, a size taller at each stage; the far plane, so it never carries a word."""
    towers = (
        ((120, 170, 90), (260, 130, 110), (760, 150, 120), (900, 190, 90)),
        ((70, 300, 100), (230, 210, 110), (720, 260, 120), (880, 340, 110)),
        ((40, 520, 110), (190, 400, 120), (330, 290, 90), (690, 340, 110), (830, 480, 130)),
        ((10, 760, 120), (160, 620, 130), (310, 460, 110), (660, 520, 120), (800, 700, 140), (950, 600, 120)),
    )
    for stage, row in enumerate(towers):
        spans = _spans_of(rows, stage)
        if not spans:
            continue
        g = cv.group(far, f"{id}-town-{stage}")
        cv.gate(g, spans)
        for k, (x, h, w) in enumerate(row):
            cv.rect(g, x, ground - h, w, h, "#B8C6D2" if k % 2 else "#A9B9C8", radius=8)


def planter(cv: Canvas, parent) -> None:
    """The planter in the frame's bottom right corner, with the cactus in it and the code on it (ADR 0001), for a
    foreground the camera does not move."""
    cv.rect(parent, 846, 1752, 260, 190, "#B67B4E", cv.ink, INK_LINE, radius=14)
    cv.rect(parent, 830, 1736, 290, 36, "#C98C5C", cv.ink, INK_LINE, radius=12)
    signature.cactus(cv, parent, 968, 1744, 0.72)
    signature.code(cv, parent, 880, 1800, 15, color="#F3DFCF")


@register(
    "location",
    "soft-park",
    summary="A park drawn straight on for a close shot: sky, a town out of focus, a lawn and a path, a tree that grows "
    "from a staked sapling to a crown wider than the frame, a town that rises behind it, and the signature cactus in a "
    "planter at the frame's corner",
)
def park(
    cv: Canvas,
    parent,
    *,
    growth: Stages = ((0.0, 0),),
    seated: Sequence[tuple[float, float]] = (),
    cast: Slot = None,
    id: str = "soft-park",
):
    """The park: ``growth`` is (time, stage) rows from 0, a stage indexing the tree's :data:`TREES`, and the town
    rises with it; ``seated`` limits the bench to those spans (none: no bench); ``cast`` draws the cast between the
    set and the foreground planter."""
    rows = _stages("growth", growth, len(TREES))
    g = cv.group(parent, id)
    sky = cv.grad("soft-park-sky", [(0.0, "#BFDDEE"), (0.62, "#EAF2E8"), (1.0, "#F6EBD6")], (0, 0, 0, 1))
    cv.rect(g, 0, 0, WIDTH, HORIZON + 8, sky)
    far = look.depth(cv, g, "soft-park-far", FAR_BLUR)
    town = [(a, b, min(s, 3)) for a, b, s in rows]
    _skyline(cv, far, town, id, HORIZON + 20)
    cv.ellipse(far, -160, HORIZON - 120, 620, 240, "#A5C79E")
    cv.ellipse(far, 620, HORIZON - 150, 640, 300, "#9CC096")
    lawn = cv.grad("soft-park-lawn", [(0.0, "#B9D6A0"), (1.0, "#8FBB7C")], (0, 0, 0, 1))
    cv.rect(g, 0, HORIZON, WIDTH, HEIGHT - HORIZON, lawn)
    cv.path(g, f"M 400 {HORIZON:g} L 680 {HORIZON:g} L 1000 1920 L 80 1920 Z", "#EFE0C4")
    for stage in dict.fromkeys(s for _, _, s in rows):
        tree = _tree(cv, g, stage, 540.0, TREE_FOOT, f"{id}-tree-{stage}")
        cv.gate(tree, _spans_of(rows, stage))
    if seated:
        park_bench(cv, _gated(cv, g, f"{id}-benched", seated), 540, BENCH_SEAT)
    if cast is not None:
        cast(g)
    front = cv.group(g, f"{id}-front")
    cv.ellipse(front, -120, 1740, 330, 300, "#6F9D62")  # a bush the camera looks past
    planter(cv, front)
    return g


@register(
    "location",
    "soft-bedroom",
    summary="A bed seen from its foot: headboard, pillows and a duvet; a phone can be the only light in the room",
)
def bedroom(
    cv: Canvas,
    parent,
    *,
    lights: Sequence[Light] = (Light(0.0, "day"),),
    shots: Sequence[Shot] = (Shot(0.0),),
    cast: Slot = None,
    held: Slot = None,
    id: str = "soft-bedroom",
):
    """The bed: ``cast`` lies against the pillows behind the duvet, ``held`` is above the duvet, and ``lights`` and
    ``shots`` are rows from 0 in rising time. A shot cuts in on everything but the nightstand, the foreground that
    holds the signature marks."""
    if not lights:
        raise SoftSetError("a bedroom needs at least one light")
    _rising("lights", [row.time for row in lights])
    if any(row.state not in LIGHTS for row in lights):
        raise SoftSetError(f"a light is one of {LIGHTS}, got {[row.state for row in lights]!r}")
    g = cv.group(parent, id)
    room = _framed(cv, g, f"{id}-room", shots)
    cv.rect(room, 0, 0, WIDTH, HEIGHT, cv.grad("soft-bedroom-wall", [(0.0, "#E8DCC8"), (1.0, "#D9C7AE")], (0, 0, 0, 1)))
    far = look.depth(cv, room, "soft-bedroom-far", FAR_BLUR)
    cv.rect(far, 742, 118, 280, 420, "#BFDDEE", "#F5EEDF", 16, radius=8)  # the window, out of focus
    cv.line(far, 882, 118, 882, 538, "#F5EEDF", 10)
    cv.rect(room, 56, 740, 968, 900, BARK, cv.ink, INK_LINE, radius=70)
    cv.rect(room, 96, 780, 888, 860, BARK_DARK, radius=46)
    cv.ellipse(room, 40, 1000, 640, 500, "#FFFFFF", cv.ink, INK_LINE)
    cv.ellipse(room, 400, 1000, 640, 500, "#F4F0EA", cv.ink, INK_LINE)
    if cast is not None:
        cast(room)
    duvet = "M -20 1548 Q 180 1490 400 1530 T 800 1520 T 1100 1544 L 1100 1960 L -20 1960 Z"
    cv.path(room, duvet, "#D8836B", cv.ink, INK_LINE)
    cv.path(room, "M 140 1640 Q 300 1610 420 1650 M 620 1600 Q 760 1580 880 1620", stroke="#B9654F", sw=8)
    if held is not None:
        held(room)
    front = cv.group(g, f"{id}-front")
    cv.rect(front, 850, 1680, 280, 300, "#A9744B", cv.ink, INK_LINE, radius=12)
    cv.rect(front, 830, 1662, 320, 34, "#C98C5C", cv.ink, INK_LINE, radius=12)
    signature.cactus(cv, front, 962, 1668, 0.72)
    signature.code(cv, front, 880, 1730, 15, color="#F3DFCF")
    _lights(cv, g, lights, id)
    return g


@register(
    "location",
    "soft-playroom",
    summary="A child's room straight on: a window of sky, a door, a rug and a toy crate in the foreground",
)
def playroom(
    cv: Canvas,
    parent,
    *,
    shots: Sequence[Shot] = (Shot(0.0),),
    dim: Dim | None = None,
    cast: Slot = None,
    id: str = "soft-playroom",
):
    """The room: ``cast`` stands on the rug, ``shots`` cut in on everything but the toy crate, which holds the
    signature marks, and ``dim`` takes the light out of the room in front of them all."""
    if dim is not None:
        fine = all(checks.number(v) for v in dim) and dim.start >= 0 and dim.fade > 0
        if not fine or dim.end < dim.start + dim.fade:
            raise SoftSetError(f"a dim starts, fades and then ends, got {dim!r}")
    g = cv.group(parent, id)
    room = _framed(cv, g, f"{id}-room", shots)
    wall = cv.grad("soft-playroom-wall", [(0.0, "#F4E6C9"), (1.0, "#EFD9B4")], (0, 0, 0, 1))
    cv.rect(room, -OVER, -OVER, WIDTH + 2 * OVER, 1660 + OVER, wall)  # a shot may frame past the room's edge
    floor = cv.grad("soft-playroom-floor", [(0.0, "#C79A6B"), (1.0, "#B3855A")], (0, 0, 0, 1))
    cv.rect(room, -OVER, 1660, WIDTH + 2 * OVER, 260 + OVER, floor)
    cv.rect(room, -OVER, 1640, WIDTH + 2 * OVER, 28, "#FFFFFF", cv.ink, INK_LINE)
    sky = cv.grad("soft-playroom-sky", [(0.0, "#6DB6E8"), (1.0, "#BFE3F5")], (0, 0, 0, 1))
    cv.rect(room, 90, 520, 520, 500, "#FFFFFF", cv.ink, INK_LINE, radius=14)
    cv.rect(room, 116, 546, 468, 448, sky, cv.ink, INK_LINE)
    for cx, cy, w in ((230, 660, 150), (290, 640, 170), (350, 670, 130), (440, 830, 120), (490, 816, 130)):
        cv.ellipse(room, cx - w / 2, cy - w / 3, w, 2 * w / 3, "#FFFFFF")
    cv.line(room, 350, 546, 350, 994, "#FFFFFF", 14)
    cv.rect(room, 70, 1012, 560, 26, "#FFFFFF", cv.ink, INK_LINE, radius=8)  # the sill
    cv.rect(room, 720, 760, 310, 886, "#FFFFFF", cv.ink, INK_LINE)
    cv.rect(room, 744, 784, 262, 862, "#C98C5C", cv.ink, INK_LINE)
    for py in (830, 1250):
        cv.rect(room, 782, py, 186, 360, "#B67B4E", "#8A6242", 4, radius=8)
    cv.ellipse(room, 758, 1250, 34, 34, "#E9C766", cv.ink, INK_LINE)
    cv.ellipse(room, 40, 1700, 1000, 190, "#7FA6C9", cv.ink, INK_LINE)
    cv.ellipse(room, 120, 1722, 840, 146, "#A5C4DD")
    if cast is not None:
        cast(room)
    front = cv.group(g, f"{id}-front")
    cv.rect(front, -30, 1760, 240, 200, "#E2A04C", cv.ink, INK_LINE, radius=14)
    cv.rect(front, -50, 1742, 280, 34, "#EDB768", cv.ink, INK_LINE, radius=12)
    signature.cactus(cv, front, 92, 1752, 0.72)
    signature.code(cv, front, 34, 1810, 15, color="#7A4A1E")
    if dim is not None:
        _dimmed(cv, g, dim, id)
    return g


def _dimmed(cv: Canvas, g, dim: Dim, id: str) -> None:
    pool = cv.rgrad("soft-playroom-pool", [(0.0, "#131A3600"), (0.1, "#131A3600"), (0.4, "#131A36F4")])
    night = cv.group(g, f"{id}-dim")
    cv.gate(night, [(dim.start, dim.end)])
    fade = cv.group(night, f"{id}-dim-fade")
    cv.rect(fade, dim.x - 2000, dim.y - 2000, 4000, 4000, pool)
    cv.keys(fade, "opacity", [(dim.start, 0.0), (dim.start + dim.fade, 1.0)], False)


def _rising(name: str, times: Sequence[float]) -> None:
    rising = all(b > a for a, b in zip(times, times[1:], strict=False))
    if not times or times[0] != 0 or not all(checks.number(t) for t in times) or not rising:
        raise SoftSetError(f"{name} run from 0 in rising time, got {list(times)!r}")


def _framed(cv: Canvas, parent, id: str, shots: Sequence[Shot]):
    """A group in ``parent`` that holds each shot until the next: a shot cuts, it never moves."""
    _rising("shots", [row.time for row in shots])
    if not all(checks.number(row.scale) and row.scale > 0 for row in shots):
        raise SoftSetError(f"a shot's scale is a positive number, got {[row.scale for row in shots]!r}")
    room = cv.group(parent, id)
    if len(shots) > 1:
        for prop, values in (
            ("x", [(s.time, 540 - s.x * s.scale) for s in shots]),
            ("y", [(s.time, 960 - s.y * s.scale) for s in shots]),
            ("scaleX", [(s.time, s.scale) for s in shots]),
            ("scaleY", [(s.time, s.scale) for s in shots]),
        ):
            cv.keys(room, prop, values)
    return room


def _lights(cv: Canvas, g, lights: Sequence[Light], id: str) -> None:
    """The dark over the room: nothing by day, a pool that flickers around a phone, or all of it."""
    pool = cv.rgrad("soft-bedroom-pool", [(0.0, NIGHT_CLEAR), (0.12, NIGHT_CLEAR), (0.34, NIGHT)])
    for k, row in enumerate(lights):
        if row.state == "day":
            continue
        end = lights[k + 1].time if k + 1 < len(lights) else 1e6
        night = cv.group(g, f"{id}-night-{k + 1}")
        cv.gate(night, [(row.time, end)])
        if row.state == "dark":
            cv.rect(night, 0, 0, WIDTH, HEIGHT, NIGHT)
            continue
        lit = cv.group(night, f"{id}-flicker-{k + 1}")  # a gate holds its group's opacity: the flicker sits inside it
        cv.rect(lit, row.x - 2000, row.y - 2000, 4000, 4000, pool)
        beats = int(min(end - row.time, 60.0) / FLICKER_STEP) + 1
        cv.keys(lit, "opacity", [(row.time + n * FLICKER_STEP, FLICKER[n % len(FLICKER)]) for n in range(beats)])


def _gated(cv: Canvas, parent, id: str, spans: Sequence[tuple[float, float]]):
    g = cv.group(parent, id)
    cv.gate(g, spans)
    return g

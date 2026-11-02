"""How well drawn lines hold from one frame to the next, measured on rendered frames.

A line that vanishes between two frames reads as flicker, the fault that decides whether a 3D paint-over can move.
:func:`popped` finds ink with no ink near it in the next frame. Real motion also moves ink further than that reach, so
:func:`flow` reads motion from the same frames with no ink on them and :func:`compare` reports both counts: ``popped``
without motion and ``unexplained`` after it. Only the second is a line failing to hold, and even it still counts ink
behind something that moved in front of it, so a low number is a result and a high one is a lead.

:func:`widths` and :func:`by_width` sort popped ink by the width of the region it outlines, to test whether thin regions
in an id pass are what drops out. A region's width is that of its widest point, so a thin strip joined to a large
region of the same colour reads as wide.

Bad input raises :class:`StabilityError`. Nothing here renders; :func:`measure` reads frames a render left in folders.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage

from . import checks, plates
from .errors import SrstudioError

__all__ = ["Bin", "Chatter", "Reading", "StabilityError", "Stroke", "Swing", "by_width", "chatter", "compare", "drawn"]
__all__ += [
    "flow",
    "ink",
    "labels",
    "measure",
    "popped",
    "specks",
    "strokes",
    "swing",
    "total",
    "width_chatter",
    "widths",
]

_EDGE_REACH = 5  # ink lies beside the edge it draws, so its region is the thinnest one within two pixels
_TIE = 1e-6  # a shift must beat a nearer one by more than this, so a flat picture reads as still


class StabilityError(SrstudioError, ValueError):
    """Frames or settings a line reading cannot use."""


@dataclass(frozen=True)
class Reading:
    """Pixel counts: ``ink`` drawn, ``popped`` with no ink near it next frame, ``unexplained`` after motion."""

    ink: int
    area: int
    popped: int
    unexplained: int

    @property
    def cover(self) -> float:
        return self.ink / self.area if self.area else 0.0

    @property
    def rate(self) -> float:
        return self.popped / self.ink if self.ink else 0.0

    @property
    def unexplained_rate(self) -> float:
        return self.unexplained / self.ink if self.ink else 0.0


@dataclass(frozen=True)
class Bin:
    """Ink on regions narrower than ``below`` and not in an earlier bin."""

    below: float
    ink: int
    popped: int

    @property
    def rate(self) -> float:
        return self.popped / self.ink if self.ink else 0.0


@dataclass(frozen=True)
class Stroke:
    """Where a line crosses a row or column, and how wide it is there in pixels, part-covered pixels counted in part."""

    centre: float
    width: float


@dataclass(frozen=True)
class Chatter:
    """Width changes of strokes followed between frames: the ``worst`` in pixels, over ``pairs`` matched, and ``flips``,
    the times one stroke reversed direction, which a steady push or pull never does."""

    worst: float
    pairs: int
    flips: int


@dataclass(frozen=True)
class Swing:
    """The frame total of ink: the ``largest`` change as a share of the frame before, and ``flips``, its reversals."""

    largest: float
    flips: int


def _pair(a: np.ndarray, b: np.ndarray, *, depth: int) -> None:
    if a.shape != b.shape:
        raise StabilityError(f"frames differ in shape: {a.shape} and {b.shape}")
    if a.ndim != depth:
        raise StabilityError(f"frames need {depth} dimensions, got shape {a.shape}")


def _masks(a: np.ndarray, b: np.ndarray) -> None:
    _pair(a, b, depth=2)
    if a.dtype != bool or b.dtype != bool:
        raise StabilityError(f"a mask holds booleans, got {a.dtype} and {b.dtype}")


def _positive(name: str, value: object) -> None:
    if not checks.number(value) or value <= 0:
        raise StabilityError(f"{name} must be a positive number, got {value!r}")


def ink(inked: np.ndarray, plain: np.ndarray, threshold: float = 0.1) -> np.ndarray:
    """Pixels where ``inked`` leaves ``plain``, the same frame drawn without lines, by over ``threshold`` of full scale
    in any colour channel."""
    _pair(inked, plain, depth=3)
    _positive("threshold", threshold)
    gap = np.abs(inked[..., :3].astype(np.int16) - plain[..., :3].astype(np.int16))
    return np.asarray(gap.max(-1) > threshold * 255)


def _grey(frame: np.ndarray) -> np.ndarray:
    return np.asarray(frame[..., :3].astype(np.float32).mean(-1) / 255)


def _halved(grey: np.ndarray) -> np.ndarray:
    height, width = grey.shape[0] & ~1, grey.shape[1] & ~1
    blocks = grey[:height, :width].reshape(height // 2, 2, width // 2, 2)
    return np.asarray(blocks.mean((1, 3)))


def _square(reach: int) -> list[tuple[int, int]]:
    span = range(-reach, reach + 1)
    return [(dy, dx) for dy in span for dx in span]


def _nearest_first(shifts: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    return sorted(shifts, key=lambda s: (s[0] ** 2 + s[1] ** 2, s))


def _moved(grey: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """``grey`` as seen from ``dy``, ``dx`` away; what falls off the frame is infinitely unlike anything."""
    height, width = grey.shape
    out = np.full(grey.shape, np.inf, grey.dtype)
    out[max(-dy, 0) : height - max(dy, 0), max(-dx, 0) : width - max(dx, 0)] = grey[
        max(dy, 0) : height + min(dy, 0), max(dx, 0) : width + min(dx, 0)
    ]
    return out


def _match(
    a: np.ndarray,
    b: np.ndarray,
    shifts: Iterable[tuple[int, int]],
    window: int,
    around: tuple[np.ndarray, np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """The best of ``shifts`` for each pixel of ``a``, the smallest of equals. With ``around``, a pixel only takes a
    shift within one step of its own. A window costs one shift across all its pixels, or it would measure a mixture."""
    best = np.full(a.shape, np.inf, np.float32)
    found_y, found_x = np.zeros(a.shape, int), np.zeros(a.shape, int)
    for dy, dx in _nearest_first(shifts):
        gap = np.minimum(np.abs(a - _moved(b, dy, dx)), 1.0)
        cost = ndimage.uniform_filter(gap, window, mode="nearest")
        better = cost < best - _TIE
        if around is not None:
            better &= (np.abs(around[0] - dy) <= 1) & (np.abs(around[1] - dx) <= 1)
        best[better] = cost[better]
        found_y[better], found_x[better] = dy, dx
    return found_y, found_x


def flow(a: np.ndarray, b: np.ndarray, *, search: int = 16, window: int = 33) -> tuple[np.ndarray, np.ndarray]:
    """Per-pixel integer motion from ``a`` to ``b``, matching a square of ``window`` pixels up to ``search`` away.

    Both frames should be free of ink, so a flickering line cannot vote for its own excuse. The match runs at half
    size, then settles to the pixel at full size; a place with no detail reads as still.
    """
    _pair(a, b, depth=3)
    if not isinstance(search, int) or search < 1:
        raise StabilityError(f"search must be a positive whole number, got {search!r}")
    if not isinstance(window, int) or window < 3 or window % 2 == 0:
        raise StabilityError(f"window must be an odd whole number of at least 3, got {window!r}")
    grey_a, grey_b = _grey(a), _grey(b)
    small_a, small_b = _halved(grey_a), _halved(grey_b)
    reach = math.ceil(search / 2)
    half_y, half_x = _match(small_a, small_b, _square(reach), window // 2 | 1)
    wanted = [(0, grey_a.shape[0] - half_y.shape[0] * 2), (0, grey_a.shape[1] - half_y.shape[1] * 2)]
    ys = np.pad(half_y.repeat(2, 0).repeat(2, 1) * 2, wanted, mode="edge")
    xs = np.pad(half_x.repeat(2, 0).repeat(2, 1) * 2, wanted, mode="edge")
    rough = set(zip(ys.ravel().tolist(), xs.ravel().tolist(), strict=True))
    steps = _square(1)
    return _match(grey_a, grey_b, {(y + dy, x + dx) for y, x in rough for dy, dx in steps}, window, (ys, xs))


def popped(
    a: np.ndarray,
    b: np.ndarray,
    *,
    reach: int = 2,
    motion: tuple[np.ndarray, np.ndarray] | None = None,
    spread: int = 0,
) -> np.ndarray:
    """Ink of ``a`` with no ink of ``b`` within ``reach`` pixels, after ``motion`` when given. Ink that motion carries
    off the frame has not popped.

    A block match at a silhouette mostly sees what lies behind it, while the line moves with what it outlines, so
    ``spread`` also tries the motion read that many pixels away on each side. Ink is kept only if none of them explains
    it, which is generous to every line and cannot explain ink with nothing near it in ``b``.
    """
    _masks(a, b)
    if not isinstance(reach, int) or reach < 0:
        raise StabilityError(f"reach must be a whole number of at least 0, got {reach!r}")
    if not isinstance(spread, int) or spread < 0:
        raise StabilityError(f"spread must be a whole number of at least 0, got {spread!r}")
    near = ndimage.distance_transform_edt(~b) <= reach if b.any() else np.zeros(b.shape, bool)
    if motion is None:
        return a & ~near
    ys, xs = np.nonzero(a)
    height, width = a.shape
    held = np.zeros(ys.shape, bool)
    for dy, dx in {(0, 0), (spread, 0), (-spread, 0), (0, spread), (0, -spread)}:
        from_y, from_x = (ys + dy).clip(0, height - 1), (xs + dx).clip(0, width - 1)
        to_y, to_x = ys + motion[0][from_y, from_x], xs + motion[1][from_y, from_x]
        inside = (to_y >= 0) & (to_y < height) & (to_x >= 0) & (to_x < width)
        held |= ~inside
        held[inside] |= near[to_y[inside], to_x[inside]]
    gone = np.zeros(a.shape, bool)
    gone[ys[~held], xs[~held]] = True
    return gone


def compare(
    inked_a: np.ndarray,
    inked_b: np.ndarray,
    plain_a: np.ndarray,
    plain_b: np.ndarray,
    *,
    threshold: float = 0.1,
    reach: int = 2,
    search: int = 16,
    window: int = 33,
) -> Reading:
    """One frame pair, drawn with lines and without."""
    a, b = ink(inked_a, plain_a, threshold), ink(inked_b, plain_b, threshold)
    motion = flow(plain_a, plain_b, search=search, window=window)
    return Reading(
        ink=int(a.sum()),
        area=a.size,
        popped=int(popped(a, b, reach=reach).sum()),
        unexplained=int(popped(a, b, reach=reach, motion=motion, spread=window // 2).sum()),
    )


def measure(
    plain: Path,
    inked: Sequence[Path],
    frames: Iterable[int],
    *,
    threshold: float = 0.1,
    reach: int = 2,
    search: int = 16,
    window: int = 33,
) -> dict[str, Reading]:
    """Each folder of ``inked`` frames against ``plain``, the same frames with no lines, as one reading per folder over
    each pair ``frame`` and ``frame + 1``. Frames are ``f0000.png`` by number; motion is read once for every folder."""
    numbers = list(frames)
    if not numbers:
        raise StabilityError("no frames to measure")

    rows: dict[str, list[Reading]] = {folder.name: [] for folder in inked}
    for number in numbers:
        first, second = _frame(plain, number), _frame(plain, number + 1)
        motion = flow(first, second, search=search, window=window)
        for folder in inked:
            a = ink(_frame(folder, number), first, threshold)
            b = ink(_frame(folder, number + 1), second, threshold)
            rows[folder.name].append(
                Reading(
                    ink=int(a.sum()),
                    area=a.size,
                    popped=int(popped(a, b, reach=reach).sum()),
                    unexplained=int(popped(a, b, reach=reach, motion=motion, spread=window // 2).sum()),
                )
            )
    return {name: total(readings) for name, readings in rows.items()}


def width_chatter(
    plain: Path,
    inked: Path,
    frames: Iterable[int],
    colour: tuple[float, float, float],
    *,
    rows: Sequence[int] = (),
    columns: Sequence[int] = (),
) -> Chatter:
    """Width chatter of the strokes crossing each of ``rows`` and ``columns`` over a run of frames from two folders,
    all lines added up: the worst change and the reversals of every stroke followed."""
    numbers = list(frames)
    if len(numbers) < 2:
        raise StabilityError("width chatter needs two frames or more")
    if not rows and not columns:
        raise StabilityError("name a row or a column to read widths on")
    pictures = [(_frame(inked, n), _frame(plain, n)) for n in numbers]
    worst, pairs, flips = 0.0, 0, 0
    lines = [{"row": r} for r in rows] + [{"column": c} for c in columns]
    for line in lines:
        got = chatter([drawn(a, b, colour, **line) for a, b in pictures])
        worst, pairs, flips = max(worst, got.worst), pairs + got.pairs, flips + got.flips
    return Chatter(worst, pairs, flips)


def _frame(folder: Path, number: int) -> np.ndarray:
    path = folder / f"f{number:04d}.png"
    if not path.is_file():
        raise StabilityError(f"no frame {path}")
    return plates.pixels(path)


def total(readings: Iterable[Reading]) -> Reading:
    """Several pairs as one reading, weighted by their pixels."""
    rows = list(readings)
    if not rows:
        raise StabilityError("no readings to add up")
    return Reading(
        ink=sum(r.ink for r in rows),
        area=sum(r.area for r in rows),
        popped=sum(r.popped for r in rows),
        unexplained=sum(r.unexplained for r in rows),
    )


def specks(mask: np.ndarray, *, largest: int = 4) -> int:
    """How many separate islands of ``mask`` hold ``largest`` pixels or fewer; a diagonal is one stroke."""
    _positive("largest", largest)
    islands, count = ndimage.label(mask, np.ones((3, 3), bool))
    if count == 0:
        return 0
    return int((np.bincount(islands.ravel())[1:] <= largest).sum())


def strokes(cover: np.ndarray) -> list[Stroke]:
    """The strokes along one line of ``cover``, each pixel's share of ink from 0 to 1."""
    runs, count = ndimage.label(cover > 0)
    found = []
    for n in range(1, count + 1):
        where = np.nonzero(runs == n)[0]
        amount = cover[where]
        found.append(Stroke(float((amount * (where + 0.5)).sum() / amount.sum()), float(amount.sum())))
    return found


def drawn(
    inked: np.ndarray,
    plain: np.ndarray,
    colour: tuple[float, float, float],
    *,
    row: int | None = None,
    column: int | None = None,
    floor: float = 0.1,
    least: float = 0.15,
) -> list[Stroke]:
    """The strokes of a frame along one ``row`` or ``column``, for ink of ``colour`` (sRGB, 0 to 1).

    A pixel's cover is how far it moved from ``plain`` towards the ink, so a line over a dark wall and one over a pale
    wall read the same width. Where ``plain`` is within ``least`` of the ink colour the cover cannot be read, and the
    pixel counts as fully covered if it moved at all, which overstates a width and never hides a change. Cover under
    ``floor`` is not ink.
    """
    _pair(inked, plain, depth=3)
    if (row is None) == (column is None):
        raise StabilityError("a line is read on a row or a column, one of them")
    if len(colour) != 3 or not all(checks.number(v) and 0 <= v <= 1 for v in colour):
        raise StabilityError(f"an ink colour is three numbers from 0 to 1, got {colour!r}")
    along = 0 if row is not None else 1
    place = row if row is not None else column
    if place is None or not 0 <= place < inked.shape[along]:
        raise StabilityError(f"{place!r} is off the frame of shape {inked.shape}")
    take = (lambda f: f[place]) if row is not None else (lambda f: f[:, place])
    over = take(inked)[..., :3].astype(float) / 255
    under = take(plain)[..., :3].astype(float) / 255
    toward = np.asarray(colour, float) - under
    reach = (toward**2).sum(-1)
    moved = over - under
    cover = (moved * toward).sum(-1) / np.maximum(reach, 1e-12)
    blind = np.sqrt(reach) < least
    cover = np.where(blind, (np.abs(moved).max(-1) > 0).astype(float), cover).clip(0, 1)
    return strokes(np.where(cover < floor, 0.0, cover))


def chatter(frames: Sequence[Sequence[Stroke]], *, reach: float = 4.0) -> Chatter:
    """How much strokes change width from frame to frame, each followed to the nearest stroke within ``reach`` pixels.
    On a slow move a line's width should drift at most, so a stroke that widens and narrows in turn is the fault."""
    _positive("reach", reach)
    worst, pairs, flips = 0.0, 0, 0
    trail: dict[int, float] = {}
    for earlier, later in itertools.pairwise(frames):
        next_trail: dict[int, float] = {}
        for k, stroke in enumerate(earlier):
            near = [(abs(s.centre - stroke.centre), n) for n, s in enumerate(later)]
            if not near or min(near)[0] > reach:
                continue
            n = min(near)[1]
            change = later[n].width - stroke.width
            worst = max(worst, abs(change))
            pairs += 1
            if change * trail.get(k, 0.0) < 0:
                flips += 1
            next_trail[n] = change
        trail = next_trail
    return Chatter(worst, pairs, flips)


def swing(masks: Sequence[np.ndarray]) -> Swing:
    """How the frame total of ink moves over a run of frames."""
    totals = [int(mask.sum()) for mask in masks]
    if len(totals) < 2 or sum(t > 0 for t in totals) < 2:
        raise StabilityError("a swing needs two frames with ink")
    steps = [(b - a) / a for a, b in itertools.pairwise(totals) if a]
    return Swing(max(abs(s) for s in steps), sum(a * b < 0 for a, b in itertools.pairwise(steps)))


def labels(frame: np.ndarray, *, palette: Iterable[str] = (), least: int = 32) -> np.ndarray:
    """One integer per colour of an id frame, with antialiased blends folded into the nearest region. ``palette`` names
    the id colours (``#rrggbb``), and anything else is a blend. Without it, a colour held by fewer than ``least`` pixels
    is one, which misses a blend that recurs along a long straight edge."""
    if frame.ndim != 3:
        raise StabilityError(f"frames need 3 dimensions, got shape {frame.shape}")
    _positive("least", least)
    red, green, blue = (frame[..., i].astype(np.int32) for i in range(3))
    kinds, found, counts = np.unique((red << 16) | (green << 8) | blue, return_inverse=True, return_counts=True)
    found = found.reshape(red.shape)
    named = [int(colour[1:], 16) for colour in palette]
    kept = np.isin(kinds, named)[found] if named else counts[found] >= least
    if not kept.any():
        raise StabilityError(f"none of the {kinds.size} colours here is a region; this is not an id frame")
    nearest = ndimage.distance_transform_edt(~kept, return_distances=False, return_indices=True)
    return np.asarray(found[tuple(nearest)])


def widths(regions: np.ndarray) -> np.ndarray:
    """Each pixel's region width in pixels: twice the distance from the region's edge to its middle. A region's own
    connected pieces are measured apart, and the frame's edge counts as an edge."""
    padded = np.pad(regions, 1, constant_values=int(regions.min()) - 1)
    edge = np.zeros(padded.shape, bool)
    across, down = padded[1:] != padded[:-1], padded[:, 1:] != padded[:, :-1]
    edge[1:] |= across
    edge[:-1] |= across
    edge[:, 1:] |= down
    edge[:, :-1] |= down
    depth = (ndimage.distance_transform_edt(~edge) + 1)[1:-1, 1:-1]
    pieces = np.zeros(regions.shape, int)
    used = 0
    for value in np.unique(regions):
        where = regions == value
        numbered, count = ndimage.label(where)
        pieces[where] = numbered[where] + used
        used += count
    deepest = ndimage.maximum(depth, pieces, np.arange(1, used + 1))
    return np.asarray(2 * np.asarray(deepest)[pieces - 1] - 1)


def by_width(
    drawn: np.ndarray, gone: np.ndarray, regions: np.ndarray, *, edges: tuple[float, ...] = (2, 4, 8, 16)
) -> list[Bin]:
    """Ink and popped ink sorted by the width of the thinnest region beside each pixel, into bins up to each of
    ``edges`` and one beyond the last."""
    _masks(drawn, gone)
    if regions.shape != drawn.shape:
        raise StabilityError(f"regions and mask differ in shape: {regions.shape} and {drawn.shape}")
    for edge in edges:
        _positive("edge", edge)
    if any(low >= high for low, high in itertools.pairwise(edges)):
        raise StabilityError(f"edges must rise, got {edges}")
    beside = ndimage.minimum_filter(widths(regions), size=_EDGE_REACH)
    bins = np.digitize(beside, edges)
    tops = [*map(float, edges), math.inf]
    return [Bin(top, int((drawn & (bins == i)).sum()), int((gone & (bins == i)).sum())) for i, top in enumerate(tops)]

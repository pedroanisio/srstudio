"""Moving a drawing to the music: keys and spans placed on a :class:`~srstudio.music.Groove` (ADR 0088).

A grid is the one source of timing, so a car, the people in it and their mouths keep to the same beat: :func:`ride`
lifts a node on each beat and settles it between, :func:`sway` leans it from beat to beat, and :func:`alternate` swaps
two states on the grid. Times are on the episode's clock. Get a recorded track's grid from ``srstudio beat``.
"""

from __future__ import annotations

from .canvas import Canvas
from .music import Groove, MusicError

__all__ = ["alternate", "ride", "sway"]


def _marks(groove: Groove, start: float, end: float, every: float) -> list[float]:
    marks = groove.between(start, end, every)
    if not marks:
        raise MusicError(f"no beat of the grid falls in {start}..{end}")
    return marks


def ride(cv: Canvas, node, groove: Groove, start: float, end: float, height: float, bar_hit: float = 1.0) -> None:
    """``node`` rises ``height`` px on each beat of the span and settles as far under between beats, ``bar_hit`` times
    as high on a beat that opens a bar. The eased keys carry a beat's lift into the next."""
    if height <= 0 or bar_hit <= 0:
        raise MusicError(f"a ride needs a height and a bar hit above zero, got {height} and {bar_hit}")
    beats = set(groove.between(start, end))
    frames = []
    for t in _marks(groove, start, end, 0.5):
        lift = height * (bar_hit if groove.opens_bar(t) else 1.0)
        frames.append((t, -lift if t in beats else height))
    cv.keys(node, "y", frames, kind="sine-in-out")


def sway(cv: Canvas, node, groove: Groove, start: float, end: float, one: float, other: float) -> None:
    """``node`` leans ``one`` degrees on a beat of the span and ``other`` on the next."""
    frames = [(t, one if k % 2 == 0 else other) for k, t in enumerate(_marks(groove, start, end, 1))]
    cv.keys(node, "rotation", frames, kind="sine-in-out")


def alternate(
    groove: Groove, start: float, end: float, every: float = 0.5, first: bool = True
) -> dict[bool, list[tuple[float, float]]]:
    """The spans of two states swapped on the grid every ``every`` beats, covering ``[start, end)`` and opening on
    ``first``: gate one drawing on each, a mouth open and a mouth shut."""
    inner = [t for t in groove.between(start, end, every) if t > start]
    edges = [start, *inner, end]
    spans: dict[bool, list[tuple[float, float]]] = {True: [], False: []}
    state = first
    for a, b in zip(edges, edges[1:], strict=False):
        spans[state].append((a, b))
        state = not state
    return spans

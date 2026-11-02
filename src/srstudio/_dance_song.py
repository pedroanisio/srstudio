"""A track's shape for a choreographer: energy on every beat, and where phrases get louder or quieter.

Whether a louder part is "the chorus" is a reading of the song this does not claim. It reports the level changes on
the phrase grid, which is what a routine can be aligned to (ADR 0186).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import checks, music
from ._dance_model import DanceError
from .music import Groove

__all__ = ["MAX_SECONDS", "SongMap", "SongMapError", "SongPart", "song_map"]

MAX_SECONDS = 1800.0  # half an hour of track bounds the beats and phrases read
FLOOR_DB = -120.0  # a silent beat's level: log10 of zero has no number


class SongMapError(DanceError):
    """A track or setting a song map cannot be measured from."""


@dataclass(frozen=True)
class SongPart:
    """Bars ``start_bar``..``end_bar`` (end excluded) at one level: ``high``, ``low``, or ``even`` when the track has
    one level throughout. ``level_db`` is relative to the track's loudest beat."""

    start_bar: int
    end_bar: int
    level_db: float
    level: str


@dataclass(frozen=True)
class SongMap:
    """Per-beat ``beat_db`` and per-phrase ``phrase_db`` levels from the loudest beat, and the ``parts`` phrases merge
    into, on ``groove`` with phrases of ``phrase_bars`` bars. A short last phrase keeps the bars it has."""

    groove: Groove
    phrase_bars: int
    beat_db: tuple[float, ...]
    phrase_db: tuple[float, ...]
    parts: tuple[SongPart, ...]

    @property
    def boundaries(self) -> tuple[int, ...]:
        """The bars a new part opens on, after the first."""
        return tuple(part.start_bar for part in self.parts[1:])


def _db(power: np.ndarray, loudest: float) -> np.ndarray:
    safe = np.maximum(power / loudest, 10 ** (FLOOR_DB / 10))
    return 10 * np.log10(safe)


def _map(samples: np.ndarray, rate: int, groove: Groove, phrase_bars: int, change_db: float) -> SongMap:
    per_bar = groove.beats_per_bar
    first = round(groove.offset * rate)
    size = groove.beat * rate
    beats = (len(samples) - first) / size
    bars = math.floor(beats + 1e-9) // per_bar
    if bars < phrase_bars:
        raise SongMapError(f"the track holds {bars} whole bars; a phrase is {phrase_bars}", path="phrase_bars")
    count = bars * per_bar
    edges = first + np.rint(np.arange(count + 1) * size).astype(int)
    squares = np.concatenate(([0.0], np.cumsum(np.square(samples[first:].astype(float)))))
    power = (squares[edges[1:] - first] - squares[edges[:-1] - first]) / np.diff(edges)
    loudest = float(power.max())
    if loudest <= 0:
        raise SongMapError("the track is silent: nothing to map", path="path")
    phrases = [(bar, min(bar + phrase_bars, bars)) for bar in range(0, bars, phrase_bars)]
    levels = [float(power[a * per_bar : b * per_bar].mean()) for a, b in phrases]
    phrase_db = _db(np.array(levels), loudest)
    runs: list[list[int]] = [[0]]
    for i in range(1, len(phrases)):
        if abs(phrase_db[i] - phrase_db[i - 1]) >= change_db:
            runs.append([])
        runs[-1].append(i)
    spans = [(phrases[run[0]][0], phrases[run[-1]][1]) for run in runs]
    values = [float(_db(power[a * per_bar : b * per_bar].mean(keepdims=True), loudest)[0]) for a, b in spans]
    middle = (min(values) + max(values)) / 2
    names = ["even"] if len(values) == 1 else ["high" if v >= middle else "low" for v in values]
    parts = tuple(SongPart(a, b, v, n) for (a, b), v, n in zip(spans, values, names, strict=True))
    return SongMap(
        groove, phrase_bars, tuple(float(v) for v in _db(power, loudest)), tuple(float(v) for v in phrase_db), parts
    )


def song_map(
    path: Path | str,
    groove: Groove,
    *,
    phrase_bars: int = 8,
    change_db: float = 3.0,
    seconds: float | None = None,
    ffmpeg: str = "ffmpeg",
) -> SongMap:
    """The energy and phrase structure of a recorded track on ``groove`` (see :func:`music.reading`), over its first
    ``seconds`` when given. Consecutive phrases at least ``change_db`` apart open a new part; a slow build that never
    steps that far stays one part. A track over ``MAX_SECONDS`` is refused rather than read."""
    if not isinstance(groove, Groove):
        raise SongMapError(f"a song is mapped on a music.Groove, not {type(groove).__name__}", path="groove")
    if type(phrase_bars) is not int or not 1 <= phrase_bars <= 64:
        raise SongMapError(f"phrase_bars {phrase_bars!r} is a whole number in 1..64", path="phrase_bars")
    if not (checks.number(change_db) and change_db > 0):
        raise SongMapError(f"change_db {change_db!r} is above zero", path="change_db")
    if seconds is not None and not (checks.number(seconds) and 0 < seconds <= MAX_SECONDS):
        raise SongMapError(f"seconds {seconds!r} lies in (0, {MAX_SECONDS}]", path="seconds")
    samples = music._decoded(Path(path), seconds if seconds is not None else MAX_SECONDS + 1, ffmpeg)
    if len(samples) > MAX_SECONDS * music._RATE:
        raise SongMapError(f"the track runs past {MAX_SECONDS} s; pass seconds to read its start", path="seconds")
    return _map(samples, music._RATE, groove, phrase_bars, change_db)

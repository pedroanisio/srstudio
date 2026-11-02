"""A routine from a song: moves chosen by its level, changed on its phrases, the same for one seed (ADR 0193).

:func:`choreograph` reads a :class:`dance.SongMap` (or :func:`choreograph_track` maps a recorded track first) and
writes one :class:`dance.Entry` per phrase. A ``low`` part draws from :attr:`Palette.low` (small moves such as a bob
or a nod), a ``high`` part from :attr:`Palette.high` (arm gestures), and an ``even`` track, which has no louder part,
from both. Only moves the character's support allows are drawn: a seated character gets ``seat`` and ``either``
moves, a standing one ``feet`` and ``either``. A move runs for at most ``max_repeat`` phrases in a row, and a repeat
is danced mirrored. Each entry crossfades in over ``transition_beats`` (a phrase shorter than that takes its own
length), and holds one face from the level's palette of :data:`EXPRESSIONS`.

The choice is a ``random.Random(seed)`` draw over the palette in its written order, so a seed and a song give the
same routine every time. Every loop runs over the song's phrases, which are bounded before the first draw.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from . import checks
from ._dance_model import MAX_ENTRIES, MAX_TRACK_BARS, DanceError, Entry, Move, Routine
from ._dance_parse import moves as preset_moves
from ._dance_song import SongMap, song_map
from .music import Groove

__all__ = [
    "EXPRESSIONS",
    "HIGH_FACES",
    "HIGH_MOVES",
    "LEVELS",
    "LOW_FACES",
    "LOW_MOVES",
    "MAX_REPEAT",
    "SUPPORTS",
    "ChoreographyError",
    "Palette",
    "choreograph",
    "choreograph_track",
    "palette_of",
]

EXPRESSIONS = ("eyes-closed", "smirk", "grin", "open-grin")
LOW_FACES = ("eyes-closed", "smirk")
HIGH_FACES = ("grin", "open-grin")
LOW_MOVES = ("seat-groove", "bob", "sway", "head-nod", "shoulder-roll", "shoulder-shimmy", "hip-sway")
HIGH_MOVES = ("arm-pump", "raise-the-roof", "point-up", "clap", "hand-wave-side", "arm-wave-overhead", "bounce")
LEVELS = ("low", "high", "even")
SUPPORTS = ("seat", "feet")
MAX_REPEAT = 64
_ALLOWS = {"seat": frozenset({"seat", "either"}), "feet": frozenset({"feet", "either"})}


class ChoreographyError(DanceError):
    """A song, palette or setting a routine cannot be choreographed from."""


def _names(value: object, what: str, allowed: tuple[str, ...] | None = None) -> tuple[str, ...]:
    if not (isinstance(value, tuple) and value and all(isinstance(v, str) for v in value)):
        raise ChoreographyError(f"{what} is a non-empty tuple of names, not {value!r}", path=what, actual=value)
    if len(set(value)) != len(value):
        raise ChoreographyError(f"{what} names each entry once: {value!r}", path=what, actual=value)
    if allowed is not None and not set(value) <= set(allowed):
        raise ChoreographyError(
            f"{what} {sorted(set(value) - set(allowed))} are not of {allowed}", path=what, actual=value
        )
    return value


@dataclass(frozen=True)
class Palette:
    """What the choreographer draws from, in order: move names for ``low`` and ``high`` parts, and the faces held
    over a phrase at each level. Move names are checked against the library when a routine is made."""

    low: tuple[str, ...] = LOW_MOVES
    high: tuple[str, ...] = HIGH_MOVES
    low_faces: tuple[str, ...] = LOW_FACES
    high_faces: tuple[str, ...] = HIGH_FACES

    def __post_init__(self) -> None:
        _names(self.low, "low")
        _names(self.high, "high")
        _names(self.low_faces, "low_faces", EXPRESSIONS)
        _names(self.high_faces, "high_faces", EXPRESSIONS)

    def pool(self, level: str) -> tuple[str, ...]:
        """The move names a part of ``level`` draws from; an ``even`` track draws from both, low first."""
        if level == "low":
            return self.low
        if level == "high":
            return self.high
        return self.low + tuple(n for n in self.high if n not in self.low)

    def faces(self, level: str) -> tuple[str, ...]:
        if level == "low":
            return self.low_faces
        if level == "high":
            return self.high_faces
        return self.low_faces + tuple(f for f in self.high_faces if f not in self.low_faces)


def _phrases(song: object) -> tuple[SongMap, list[tuple[int, int, str]]]:
    """The song's phrases as ``(start, end, level)``, after checking its parts tile them from bar 0."""
    if not isinstance(song, SongMap):
        raise ChoreographyError(f"a routine is choreographed from a dance.SongMap, not {type(song).__name__}")
    size = song.phrase_bars
    if type(size) is not int or not 1 <= size <= 64:
        raise ChoreographyError(f"phrase_bars {size!r} is a whole number in 1..64", path="phrase_bars")
    if not (isinstance(song.parts, tuple) and song.parts):
        raise ChoreographyError("a song map holds at least one part", path="parts")
    bars = song.parts[-1].end_bar
    if type(bars) is not int or bars < size:
        raise ChoreographyError(f"the song holds {bars!r} bars, shorter than one phrase of {size}", path="parts")
    if bars > MAX_TRACK_BARS or math.ceil(bars / size) > MAX_ENTRIES:
        raise ChoreographyError(
            f"{bars} bars make {math.ceil(bars / size)} phrases; a routine holds at most {MAX_ENTRIES} phrases "
            f"of at most {MAX_TRACK_BARS} bars",
            path="parts",
        )
    reach = 0
    for i, part in enumerate(song.parts):
        if part.level not in LEVELS:
            raise ChoreographyError(f"parts[{i}] level {part.level!r} is one of {LEVELS}", path=f"parts[{i}]")
        if part.start_bar != reach or part.end_bar <= part.start_bar or part.start_bar % size:
            raise ChoreographyError(
                f"parts[{i}] {part.start_bar}..{part.end_bar} does not follow bar {reach} on the {size}-bar phrases",
                path=f"parts[{i}]",
            )
        reach = part.end_bar
    levels = [next(p.level for p in song.parts if p.start_bar <= bar < p.end_bar) for bar in range(0, bars, size)]
    return song, [(bar, min(bar + size, bars), level) for bar, level in zip(range(0, bars, size), levels, strict=True)]


def _library(library: object) -> Mapping[str, Move]:
    found = preset_moves() if library is None else library
    if not (isinstance(found, Mapping) and all(isinstance(m, Move) for m in found.values())):
        raise ChoreographyError("the library is a mapping of names to dance.Move", path="library")
    return found


def energy(move: Move) -> float:
    """How much a move moves: the sum of its patterns' amplitudes in size, radians and head radii alike."""
    return sum(abs(p.amplitude) for p in move.patterns)


def palette_of(
    library: Mapping[str, Move], *, low_faces: tuple[str, ...] = LOW_FACES, high_faces: tuple[str, ...] = HIGH_FACES
) -> Palette:
    """A palette over a whole library: its moves ranked by :func:`energy`, the quieter half for ``low`` parts and
    the louder half for ``high`` ones (the median move dances on both when the count is odd). A library of one
    move draws it everywhere."""
    found = _library(library)
    if not found:
        raise ChoreographyError("a palette needs at least one move", path="library")
    ranked = sorted(found, key=lambda n: (energy(found[n]), n))
    half = len(ranked) // 2
    low = tuple(ranked[: max(1, len(ranked) - half)])
    high = tuple(ranked[len(ranked) - half :]) or low
    return Palette(low, high, low_faces, high_faces)


def _pools(palette: Palette, library: Mapping[str, Move], support: str, levels: set[str]) -> dict[str, tuple[str, ...]]:
    pools = {}
    for level in sorted(levels):
        names = palette.pool(level)
        unknown = [n for n in names if n not in library]
        if unknown:
            raise ChoreographyError(f"{unknown} are not moves in the library", code="dance.move", actual=unknown)
        allowed = tuple(n for n in names if library[n].support in _ALLOWS[support])
        if not allowed:
            raise ChoreographyError(
                f"no {level} move of {names} can be danced on support {support!r}", path="palette", actual=names
            )
        pools[level] = allowed
    return pools


def _settings(support: object, seed: object, transition_beats: object, max_repeat: object) -> None:
    if support not in SUPPORTS:
        raise ChoreographyError(f"support {support!r} is one of {SUPPORTS}", path="support", actual=support)
    if type(seed) is not int or seed < 0:
        raise ChoreographyError(f"seed {seed!r} is a whole number from 0", path="seed", actual=seed)
    if not (checks.number(transition_beats) and 0 <= transition_beats <= 4 * MAX_TRACK_BARS):
        raise ChoreographyError(
            f"transition_beats {transition_beats!r} lies in 0..{4 * MAX_TRACK_BARS}", path="transition_beats"
        )
    if type(max_repeat) is not int or not 1 <= max_repeat <= MAX_REPEAT:
        raise ChoreographyError(f"max_repeat {max_repeat!r} is a whole number in 1..{MAX_REPEAT}", path="max_repeat")


def choreograph(
    song: SongMap,
    *,
    support: str,
    seed: int,
    transition_beats: float = 2.0,
    max_repeat: int = 2,
    palette: Palette | None = None,
    library: Mapping[str, Move] | None = None,
) -> Routine:
    """A routine over ``song``: one entry per phrase, its move drawn by the phrase's level from ``palette`` (the
    defaults when None) among ``library``'s moves (the presets when None) that ``support`` (``seat`` or ``feet``)
    allows. A run of one move is at most ``max_repeat`` phrases, and a pool that cannot change move in time is
    refused rather than broken."""
    _settings(support, seed, transition_beats, max_repeat)
    chosen = Palette() if palette is None else palette
    if not isinstance(chosen, Palette):
        raise ChoreographyError(f"palette is a choreograph.Palette, not {type(chosen).__name__}", path="palette")
    found, phrases = _phrases(song)
    moves = _library(library)
    pools = _pools(chosen, moves, support, {level for _, _, level in phrases})
    per_bar = found.groove.beats_per_bar
    rng = random.Random(seed)
    entries: list[Entry] = []
    last, run = "", 0
    for start, end, level in phrases:
        candidates = [n for n in pools[level] if not (n == last and run >= max_repeat)]
        if not candidates:
            raise ChoreographyError(
                f"bar {start}: the {level} pool {pools[level]} would repeat {last!r} past max_repeat={max_repeat}",
                path="palette",
            )
        name = rng.choice(candidates)
        run = run + 1 if name == last else 1
        face = rng.choice(chosen.faces(level))
        transition = min(float(transition_beats), float((end - start) * per_bar))
        entries.append(
            Entry(start, end, moves[name], mirror=run % 2 == 0, transition_beats=transition, expression=face)
        )
        last = name
    return Routine(phrases[-1][1], tuple(entries), per_bar)


def choreograph_track(
    path: Path | str,
    groove: Groove,
    *,
    support: str,
    seed: int,
    phrase_bars: int = 8,
    change_db: float = 3.0,
    seconds: float | None = None,
    ffmpeg: str = "ffmpeg",
    transition_beats: float = 2.0,
    max_repeat: int = 2,
    palette: Palette | None = None,
    library: Mapping[str, Move] | None = None,
) -> Routine:
    """:func:`choreograph` on :func:`dance.song_map` of a recorded track on ``groove``."""
    song = song_map(path, groove, phrase_bars=phrase_bars, change_db=change_db, seconds=seconds, ffmpeg=ffmpeg)
    return choreograph(
        song,
        support=support,
        seed=seed,
        transition_beats=transition_beats,
        max_repeat=max_repeat,
        palette=palette,
        library=library,
    )

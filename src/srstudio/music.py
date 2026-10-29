"""A beat grid and a small synthesised groove, so dance timing and its music come from one tempo.

:class:`Groove` turns bars and beats into seconds; pose changes and lyric lines are placed with
:meth:`Groove.at` and :meth:`Groove.beats`. :func:`render` plays :class:`Section` s of the grid with
five parts (kick, snare, hat, bass, keys) over a chord loop, deterministically from ``seed``, and
levels the result to ``peak``; :func:`write_wav` stores it as 16-bit mono PCM for the mix.
"""

from __future__ import annotations

import math
import random
import wave
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from . import checks
from .errors import SrstudioError

__all__ = ["CHOKE", "PARTS", "MusicError", "Groove", "Section", "render", "write_wav", "LOOP"]

PARTS = ("kick", "snare", "hat", "bass", "keys")
# A bouncy I–vi–IV–V loop in C major: (bass root, chord tones) as MIDI notes, one chord per bar.
LOOP: tuple[tuple[int, tuple[int, ...]], ...] = (
    (36, (60, 64, 67)),
    (33, (57, 60, 64)),
    (29, (53, 57, 60)),
    (31, (55, 59, 62)),
)


class MusicError(SrstudioError, ValueError):
    """A grid, a section list or a render setting the synthesiser cannot play."""


@dataclass(frozen=True)
class Groove:
    """Tempo and metre: ``at(bar, beat)`` is the second that beat starts, ``offset`` after zero."""

    bpm: float
    beats_per_bar: int = 4
    offset: float = 0.0

    def __post_init__(self) -> None:
        if not (checks.number(self.bpm) and 30 <= self.bpm <= 300):
            raise MusicError(f"bpm {self.bpm} outside 30..300")
        if self.beats_per_bar < 1:
            raise MusicError(f"beats_per_bar {self.beats_per_bar} must be at least 1")
        if not (checks.number(self.offset) and self.offset >= 0):
            raise MusicError(f"offset {self.offset} must be a non-negative number of seconds")

    @property
    def beat(self) -> float:
        return 60.0 / self.bpm

    @property
    def bar(self) -> float:
        return self.beat * self.beats_per_bar

    def at(self, bar: float, beat: float = 0) -> float:
        n = bar * self.beats_per_bar + beat
        if n < 0:
            raise MusicError(f"bar {bar} beat {beat} is before the first beat")
        return self.offset + n * self.beat

    def beats(self, start_bar: float, end_bar: float, every: float = 1) -> list[float]:
        """The beat times from ``start_bar`` up to (not including) ``end_bar``, every ``every`` beats."""
        if every <= 0:
            raise MusicError(f"every {every} must be positive")
        out, n = [], 0.0
        total = (end_bar - start_bar) * self.beats_per_bar
        while n < total - 1e-9:
            out.append(self.at(start_bar, n))
            n += every
        return out


@dataclass(frozen=True)
class Section:
    """Bars ``start_bar``..``end_bar`` (end excluded) playing ``parts``; an empty set is a rest."""

    start_bar: int
    end_bar: int
    parts: frozenset[str] = field(default_factory=lambda: frozenset(PARTS))


def _check(sections: Sequence[Section]) -> None:
    if not sections:
        raise MusicError("render needs at least one section")
    last = 0
    for s in sorted(sections, key=lambda s: s.start_bar):
        if s.start_bar < 0:
            raise MusicError(f"section starts at negative bar {s.start_bar}")
        if s.end_bar <= s.start_bar:
            raise MusicError(f"section {s.start_bar}..{s.end_bar} must end after it starts")
        if s.start_bar < last:
            raise MusicError(f"section {s.start_bar}..{s.end_bar} overlaps the one before it")
        unknown = sorted(set(s.parts) - set(PARTS))
        if unknown:
            raise MusicError(f"unknown parts {unknown}; one of {PARTS}")
        last = s.end_bar


def _hz(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


CHOKE = 0.005  # seconds of fade where a section ends and its notes are cut


def _add(out: list[float], at: float, rate: int, length: float, voice, until: float) -> None:
    """Mix ``voice(t)`` for ``length`` seconds into ``out`` from ``at``, cut (with a short fade) at ``until``."""
    a, stop = round(at * rate), min(len(out), round(until * rate))
    fade = max(1, round(CHOKE * rate))
    for k in range(max(0, min(round(length * rate), stop - a))):
        left = stop - (a + k)
        out[a + k] += voice(k / rate) * (left / fade if left < fade else 1.0)


def render(
    groove: Groove,
    sections: Sequence[Section],
    *,
    rate: int = 48000,
    chords: Sequence[tuple[int, tuple[int, ...]]] = LOOP,
    seed: int = 1,
    peak: float = 0.8,
    tail: float = 0.0,
) -> list[float]:
    """Mono samples in -1..1 for ``sections``, peak-levelled to ``peak``; ``tail`` seconds ring out."""
    _check(sections)
    if not 8000 <= rate <= 192000:
        raise MusicError(f"rate {rate} outside 8000..192000")
    if not 0 < peak <= 1:
        raise MusicError(f"peak {peak} outside (0, 1]")
    if not chords:
        raise MusicError("chords must hold at least one (root, tones) entry")
    end = max(s.end_bar for s in sections)
    out = [0.0] * round((groove.at(end) + max(0.0, tail)) * rate)
    rng = random.Random(seed)
    noise = [rng.uniform(-1, 1) for _ in range(rate)]  # one second of seeded noise, read cyclically
    b = groove.beat

    def kick(t: float) -> float:
        phase = 2 * math.pi * (45 * t + (120 - 45) * 0.03 * (1 - math.exp(-t / 0.03)))
        return 0.9 * math.sin(phase) * math.exp(-t / 0.16)

    def snare(t: float) -> float:
        k = int(t * rate) % rate
        return (0.45 * noise[k] + 0.25 * math.sin(2 * math.pi * 190 * t)) * math.exp(-t / 0.09)

    def hat(t: float) -> float:
        k = int(t * rate) % rate
        return 0.16 * (noise[k] - noise[k - 1]) * math.exp(-t / 0.025)

    def tone(hz: float, decay: float, gain: float, bright: float):
        def voice(t: float) -> float:
            w = 2 * math.pi * hz * t
            return gain * (math.sin(w) + bright * math.sin(2 * w) + bright / 3 * math.sin(3 * w)) * math.exp(-t / decay)

        return voice

    for s in sections:
        until = groove.at(s.end_bar) + (max(0.0, tail) if s.end_bar == end else 0.0)

        def add(at: float, length: float, voice, until: float = until) -> None:
            _add(out, at, rate, length, voice, until)

        for bar in range(s.start_bar, s.end_bar):
            root, tones = chords[bar % len(chords)]
            for n in range(groove.beats_per_bar):
                t = groove.at(bar, n)
                if "kick" in s.parts:
                    add(t, 0.5, kick)
                if "snare" in s.parts and n % 2 == 1:
                    add(t, 0.35, snare)
                if "hat" in s.parts:
                    add(t + b / 2, 0.12, hat)
                if "bass" in s.parts:
                    note = root + (12 if n % 2 else 0)
                    add(t, b * 0.9, tone(_hz(note), b * 0.5, 0.35, 0.15))
                if "keys" in s.parts:
                    for midi in tones:
                        add(t + b / 2, b * 0.9, tone(_hz(midi), b * 0.35, 0.12, 0.5))
    loudest = max(abs(v) for v in out)
    if loudest == 0:
        raise MusicError("the sections are silent: every one is a rest")
    scale = peak / loudest
    return [v * scale for v in out]


def write_wav(path: str | Path, samples: Sequence[float], rate: int) -> Path:
    """16-bit mono PCM; a sample outside -1..1 is refused rather than clipped."""
    if any(not -1 <= v <= 1 for v in samples):
        raise MusicError("samples must lie in -1..1")
    path = Path(path)
    frames = bytearray()
    for v in samples:
        frames += round(v * 32767).to_bytes(2, "little", signed=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return path

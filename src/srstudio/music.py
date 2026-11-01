"""A beat grid and a small synthesised groove, so dance timing and its music come from one tempo.

:class:`Groove` turns bars and beats into seconds; pose changes and lyric lines are placed with
:meth:`Groove.at` and :meth:`Groove.beats`. :func:`render` plays :class:`Section` s of the grid with
five parts (kick, snare, hat, bass, keys) over a chord loop, deterministically from ``seed``, and
levels the result to ``peak``; :func:`write_wav` stores it as 16-bit mono PCM for the mix. :func:`measure` reads the
grid of a track that already exists, so a picture can move to it.
"""

from __future__ import annotations

import math
import random
import subprocess
import wave
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import checks
from .errors import SrstudioError

__all__ = ["CHOKE", "PARTS", "MusicError", "Groove", "Section", "measure", "render", "write_wav", "LOOP"]

PARTS = ("kick", "snare", "hat", "bass", "keys")
# A bouncy I–vi–IV–V loop in C major: (bass root, chord tones) as MIDI notes, one chord per bar.
LOOP: tuple[tuple[int, tuple[int, ...]], ...] = (
    (36, (60, 64, 67)),
    (33, (57, 60, 64)),
    (29, (53, 57, 60)),
    (31, (55, 59, 62)),
)


_RATE, _HOP, _WINDOW = 22050, 220, 1024  # the measure's sound: 22 kHz mono, about a hundred onset frames a second
_LEAD = 3 / 4 * _WINDOW / _RATE  # an onset frame leads its sound: measured on click tracks
_EDGES = (20, 160, 400, 1200, 4000, 10000)  # its bands in Hz; the first holds the kick
SURE_BARS = 8  # fewer than this and one odd bar can move the bar line
STRONG = 0.75  # of the strongest mark's low end: 0.7 and 0.8 read every track of known grid alike


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

    def between(self, start: float, end: float, every: float = 1) -> list[float]:
        """The grid's marks in ``[start, end)`` seconds, every ``every`` beats; the grid runs on before ``offset``."""
        if every <= 0:
            raise MusicError(f"every {every} must be positive")
        if not (checks.number(start) and checks.number(end)):
            raise MusicError(f"the span {start}..{end} is not a span of seconds")
        if end < start:
            raise MusicError(f"the span {start}..{end} ends before it starts")
        step = self.beat * every
        k = range(math.floor((start - self.offset) / step), math.ceil((end - self.offset) / step) + 1)
        marks = (round(self.offset + n * step, 6) for n in k)  # rounded first: a mark given back opens its own span
        return [t for t in marks if start <= t < end]

    def opens_bar(self, t: float) -> bool:
        """Whether the second ``t`` is a beat that opens a bar."""
        turns = (t - self.offset) / self.bar
        return abs(turns - round(turns)) * self.bar < 1e-3


@dataclass(frozen=True)
class Section:
    """Bars ``start_bar``..``end_bar`` (end excluded) playing ``parts``; an empty set is a rest."""

    start_bar: int
    end_bar: int
    parts: frozenset[str] = field(default_factory=lambda: frozenset(PARTS))


def _decoded(path: Path, seconds: float | None, ffmpeg: str) -> np.ndarray:
    take = ["-t", str(seconds)] if seconds is not None else []
    try:
        done = subprocess.run(
            [ffmpeg, "-v", "error", "-i", str(path), *take, "-ac", "1", "-ar", str(_RATE), "-f", "f32le", "-"],
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise MusicError(f"cannot read the sound of {path}: no {ffmpeg} to decode it") from exc
    if done.returncode != 0:
        raise MusicError(f"cannot read the sound of {path}: {done.stderr.decode(errors='replace').strip()}")
    return np.frombuffer(done.stdout, np.float32)


def _spectrum(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The log spectrum, frame by frame, and the frequency of its bins."""
    count = (len(samples) - _WINDOW) // _HOP + 1
    frames = samples[np.arange(_WINDOW) + _HOP * np.arange(count)[:, None]] * np.hanning(_WINDOW)
    return np.log1p(1000 * np.abs(np.fft.rfft(frames, axis=1))), np.fft.rfftfreq(_WINDOW, 1 / _RATE)


def _onsets(power: np.ndarray, hz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Where sound starts, frame by frame: the rise of every band together and of the low band alone."""
    bands = np.array([power[:, (hz >= a) & (hz < b)].mean(1) for a, b in zip(_EDGES, _EDGES[1:], strict=False)])
    rise = np.clip(np.diff(bands, axis=1), 0, None)
    return rise.sum(0), rise[0]


def _bar_line(power: np.ndarray, low: np.ndarray, starts: np.ndarray, per_bar: int) -> int:
    """Which of the first ``per_bar`` marks at ``starts`` opens a bar. The low end picks the strong marks, within
    ``STRONG`` of the strongest, because a kick on one and three makes those two a tie. Among them it is the mark where
    bars cut there turn most: a bar's mean spectrum, which no rhythm inside the bar can change, moves with its chord."""
    peaks = np.array([low[max(f - 3, 0) : f + 10].sum() for f in starts])  # a tenth of a second, a kick's length
    weight = [float(peaks[k::per_bar].mean()) for k in range(per_bar)]
    marks = np.array([power[a:b].mean(0) for a, b in zip(starts, starts[1:], strict=False)])

    def turn(k: int) -> float:
        bars = [marks[j : j + per_bar].mean(0) for j in range(k, len(marks) - per_bar + 1, per_bar)]
        steps = [np.linalg.norm(a - b) for a, b in zip(bars, bars[1:], strict=False)]
        return float(np.mean(steps)) if steps else 0.0

    return max((k for k in range(per_bar) if weight[k] >= STRONG * max(weight)), key=turn)


def _folded(onsets: np.ndarray, period: float, bins: int) -> np.ndarray:
    phase = (np.arange(len(onsets)) / period % 1 * bins).astype(int)
    return np.bincount(phase, onsets, bins) / np.maximum(np.bincount(phase, minlength=bins), 1)


@dataclass(frozen=True)
class Reading:
    """A track's grid, the bars heard to get it, and whether that was enough to trust where the bars open."""

    groove: Groove
    bars: float
    sure: bool


def measure(
    path: Path | str, *, seconds: float | None = None, beats_per_bar: int = 4, ffmpeg: str = "ffmpeg"
) -> Groove:
    """The grid of a recorded track: see :func:`reading`."""
    return reading(path, seconds=seconds, beats_per_bar=beats_per_bar, ffmpeg=ffmpeg).groove


def reading(
    path: Path | str, *, seconds: float | None = None, beats_per_bar: int = 4, ffmpeg: str = "ffmpeg"
) -> Reading:
    """The grid of a recorded track, over its first ``seconds`` when given: the tempo whose beat, double and bar all
    repeat in its onsets, leaning toward 120 BPM, and the beat that opens a bar. Going by the beat alone reads a 3-3-2
    rhythm at two thirds of its tempo. A tempo holds on a few bars; the bar line needs ``SURE_BARS`` of them, and short
    of that the reading says so. An even pulse holds nothing that tells a tempo from its double or half, and the lean
    decides: clicks read true from 75 to 165 BPM, and outside that at the octave inside it. A track that changes tempo
    has no single grid: measure each part of it."""
    if beats_per_bar < 1:
        raise MusicError(f"beats_per_bar {beats_per_bar} must be at least 1")
    samples = _decoded(Path(path), seconds, ffmpeg)
    if len(samples) < 2 * _RATE:
        raise MusicError(f"{path} is too short to hold a tempo: {len(samples) / _RATE:.2f} s")
    if float(np.abs(samples).max()) < 1e-3:
        raise MusicError(f"{path} is silent: nothing to measure")
    power, hz = _spectrum(samples)
    onsets, low = _onsets(power, hz)
    fps = _RATE / _HOP
    pulse = onsets - onsets.mean()
    spectrum = np.fft.rfft(pulse, 2 * len(pulse))
    echo = np.fft.irfft(spectrum * np.conj(spectrum))[: len(pulse)]
    best, best_bpm = -math.inf, 0.0
    for bpm in np.arange(60.0, 200.0, 0.25):
        period = fps * 60.0 / bpm
        marks = [m for m in (period, 2 * period, beats_per_bar * period) if m < len(echo) - 1]
        if not marks:
            continue
        score = float(np.interp(marks, np.arange(len(echo)), echo).mean())  # a clip can be shorter than a slow bar
        score *= math.exp(-0.5 * (math.log2(bpm / 120.0) / 0.8) ** 2)
        if score > best:
            best, best_bpm = score, float(bpm)
    if best <= 0:
        raise MusicError(f"{path} has no steady pulse to measure")
    fine = np.arange(best_bpm - 0.5, best_bpm + 0.51, 0.05)
    folds = [_folded(onsets, fps * 60.0 / bpm, max(4, round(fps * 60.0 / bpm))) for bpm in fine]
    index = int(np.argmax([f.max() - f.mean() for f in folds]))
    best_bpm = round(float(fine[index]), 2)
    best_phase = int(np.argmax(folds[index]))
    beat = 60.0 / best_bpm
    first = best_phase / max(4, round(fps * beat)) * beat + _LEAD
    step = beat / 2  # a song's kick can fall off the beat the onsets folded on
    starts = np.arange(first % step * fps, len(power), step * fps).astype(int)
    if len(starts) < 4 * beats_per_bar + 1:
        raise MusicError(f"{path} is too short for bars of {beats_per_bar}: {len(starts) // 2} beats")
    opening = first % step + step * _bar_line(power, low, starts, 2 * beats_per_bar)
    groove = Groove(best_bpm, beats_per_bar, round(opening, 3) % (beat * beats_per_bar))
    bars = len(samples) / _RATE / (beat * beats_per_bar)
    return Reading(groove, bars, bars >= SURE_BARS)


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

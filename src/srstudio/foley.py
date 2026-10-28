"""Keyboard foley: keystroke bursts where the tracked hand moves, synthesised deterministically.

The reference's typing hand is tracked every 0.25 s (:func:`srstudio.cel.parse_features`); each sample at which
the point moved more than a threshold from the sample before, while the hand is on the keyboard, is a burst of
two to four keystrokes (:func:`taps`), whose onsets also drive the drawn fingers. A keystroke is a few
milliseconds of filtered noise with a soft thump, seeded so the same input gives the same samples. The bed is
levelled to a peak and written as 16-bit mono through :func:`srstudio.music.write_wav`.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from pathlib import Path

from .cel import Feature
from .music import write_wav

__all__ = ["typing_bursts", "taps", "keystrokes", "write_typing", "RATE", "THRESHOLD", "PEAK"]

RATE = 48000
THRESHOLD = 8.0  # pixels the tracked point moves between samples for a burst
PEAK = 0.5
CLICK = 0.012  # seconds of one keystroke's noise
MIN_RATE = 8000


def typing_bursts(
    samples: Sequence[Feature], threshold: float = THRESHOLD, spans: Sequence[tuple[float, float]] | None = None
) -> list[float]:
    """The sample times at which the tracked point moved more than ``threshold`` pixels since the sample before,
    inside one of ``spans`` (``[start, end)``; everywhere when None): the hand typing, not the hand being raised."""
    if not (math.isfinite(threshold) and threshold > 0):
        raise ValueError(f"threshold {threshold} must be positive")
    out = []
    for prev, cur in zip(samples, samples[1:], strict=False):
        if math.hypot(cur.x - prev.x, cur.y - prev.y) > threshold:
            if spans is None or any(a <= cur.time < b for a, b in spans):
                out.append(cur.time)
    return out


def taps(bursts: Sequence[float], seed: int = 0) -> list[float]:
    """Two to four keystroke onsets after each burst time, within about 0.2 s, the same for the same seed; the
    sound (:func:`keystrokes`) and the picture (:class:`srstudio.cel.Hands`) share them."""
    rng = random.Random(seed)
    out = []
    for at in sorted(bursts):
        for _ in range(rng.randint(2, 4)):
            at += rng.uniform(0.02, 0.08)
            out.append(round(at, 6))
    return out


def keystrokes(
    times: Sequence[float], duration: float, rate: int = RATE, seed: int = 0, peak: float = PEAK
) -> list[float]:
    """A mono bed of ``duration`` seconds with one keystroke at each of ``times`` (see :func:`taps`)."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise ValueError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not (math.isfinite(duration) and duration > 0 and all(0 <= t <= duration - 0.1 for t in times)):
        raise ValueError(f"duration {duration} must leave 0.1 s after every keystroke")
    if not (math.isfinite(peak) and 0 < peak <= 1):
        raise ValueError(f"peak {peak} must be in 0..1")
    out = [0.0] * int(round(duration * rate))
    rng = random.Random(seed)
    for at in sorted(times):
        if True:
            start = int(at * rate)
            thump = 90.0 + rng.uniform(-10, 10)
            loud = rng.uniform(0.6, 1.0)
            n = int(CLICK * rate)
            last = 0.0
            for k in range(n):
                if start + k >= len(out):
                    break
                t = k / rate
                noise = rng.uniform(-1, 1)
                last = 0.7 * last + 0.3 * noise  # a touch of low-pass so the click is plastic, not glass
                env = math.exp(-t / 0.003)
                out[start + k] += loud * (last * env + 0.4 * math.sin(2 * math.pi * thump * t) * math.exp(-t / 0.006))
    top = max((abs(v) for v in out), default=0.0)
    if top > 0:
        out = [v * peak / top for v in out]
    return out


def write_typing(
    path: Path, times: Sequence[float], duration: float, rate: int = RATE, seed: int = 0, peak: float = PEAK
) -> Path:
    """The keystroke bed for the given onsets, written to ``path``."""
    return write_wav(path, keystrokes(times, duration, rate, seed, peak), rate)

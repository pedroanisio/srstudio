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
from .errors import SrstudioError
from .music import write_wav

__all__ = [
    "FoleyError",
    "typing_bursts",
    "taps",
    "keystrokes",
    "write_typing",
    "buzz",
    "write_buzz",
    "tones",
    "write_tones",
    "STING",
    "whoosh",
    "write_whoosh",
    "WHOOSH",
    "CHIME",
    "RATE",
    "THRESHOLD",
    "PEAK",
]

RATE = 48000
THRESHOLD = 8.0  # pixels the tracked point moves between samples for a burst
PEAK = 0.5
CLICK = 0.012  # seconds of one keystroke's noise
KEY_TAIL = 0.1  # seconds a keystroke bed runs on after its last keystroke
BUZZ = 0.36  # seconds of one phone buzz: two pulses
BUZZ_TONE = 165.0  # the motor's hum, Hz
BUZZ_RATTLE = 28.0  # how fast the phone rattles on the desk, Hz
MIN_RATE = 8000


class FoleyError(SrstudioError, ValueError):
    """A foley track asked for with a rate, length, level or cue it cannot be made from."""


def typing_bursts(
    samples: Sequence[Feature], threshold: float = THRESHOLD, spans: Sequence[tuple[float, float]] | None = None
) -> list[float]:
    """The sample times at which the tracked point moved more than ``threshold`` pixels since the sample before,
    inside one of ``spans`` (``[start, end)``; everywhere when None): the hand typing, not the hand being raised."""
    if not (math.isfinite(threshold) and threshold > 0):
        raise FoleyError(f"threshold {threshold} must be positive")
    out = []
    for prev, cur in zip(samples, samples[1:], strict=False):
        if math.hypot(cur.x - prev.x, cur.y - prev.y) > threshold:
            if spans is None or any(a <= cur.time < b for a, b in spans):
                out.append(cur.time)
    return out


def taps(bursts: Sequence[float], seed: int = 0, until: float | None = None) -> list[float]:
    """Two to four keystroke onsets after each burst time, within about 0.2 s, the same for the same seed; the
    sound (:func:`keystrokes`) and the picture (:class:`srstudio.cel.Hands`) share them. With ``until``, the
    onsets after it are dropped and the rest are unchanged: a bed of ``until + KEY_TAIL`` seconds takes them."""
    rng = random.Random(seed)
    out = []
    for at in sorted(bursts):
        for _ in range(rng.randint(2, 4)):
            at += rng.uniform(0.02, 0.08)
            out.append(round(at, 6))
    return out if until is None else [t for t in out if t <= until]


def keystrokes(
    times: Sequence[float], duration: float, rate: int = RATE, seed: int = 0, peak: float = PEAK
) -> list[float]:
    """A mono bed of ``duration`` seconds with one keystroke at each of ``times`` (see :func:`taps`)."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise FoleyError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not (math.isfinite(duration) and duration > 0 and all(0 <= t <= duration - KEY_TAIL for t in times)):
        raise FoleyError(f"duration {duration} must leave {KEY_TAIL} s after every keystroke")
    if not (math.isfinite(peak) and 0 < peak <= 1):
        raise FoleyError(f"peak {peak} must be in 0..1")
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


def buzz(
    times: Sequence[float], duration: float, rate: int = RATE, seed: int = 0, peak: float = PEAK, length: float = BUZZ
) -> list[float]:
    """A mono bed of ``duration`` seconds with one phone buzz at each of ``times``: a low hum shaken by the rattle
    of the phone on the desk, in two pulses with a short gap, faded in and out; seeded for the touch of noise."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise FoleyError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not (math.isfinite(length) and 0.05 <= length <= 2.0):
        raise FoleyError(f"length {length} must be within 0.05..2 s")
    if not (math.isfinite(duration) and duration > 0 and all(0 <= t <= duration - length for t in times)):
        raise FoleyError(f"duration {duration} must leave {length} s after every buzz")
    if not (math.isfinite(peak) and 0 < peak <= 1):
        raise FoleyError(f"peak {peak} must be in 0..1")
    out = [0.0] * int(round(duration * rate))
    rng = random.Random(seed)
    pulse = length / 2
    for at in sorted(times):
        start = int(at * rate)
        for k in range(int(length * rate)):
            if start + k >= len(out):
                break
            t = k / rate
            inside = t % pulse
            if inside > pulse * 0.82:  # the gap between the two pulses, and after the second
                continue
            env = min(1.0, inside / 0.008, (pulse * 0.82 - inside) / 0.02)
            hum = math.sin(2 * math.pi * BUZZ_TONE * t) * (0.55 + 0.45 * math.sin(2 * math.pi * BUZZ_RATTLE * t))
            out[start + k] += env * (hum + 0.25 * math.sin(4 * math.pi * BUZZ_TONE * t) + 0.08 * rng.uniform(-1, 1))
    top = max((abs(v) for v in out), default=0.0)
    if top > 0:
        out = [v * peak / top for v in out]
    return out


def write_buzz(
    path: Path, times: Sequence[float], duration: float, rate: int = RATE, seed: int = 0, peak: float = PEAK
) -> Path:
    """The phone-buzz bed for the given onsets, written to ``path``."""
    return write_wav(path, buzz(times, duration, rate, seed, peak), rate)


# -- stings and chimes ------------------------------------------------------------------------------------------------
WHOOSH = 0.3  # seconds of one whoosh: it swells into the moment a crash zoom lands


def whoosh(
    times: Sequence[float], duration: float, length: float = WHOOSH, rate: int = RATE, peak: float = PEAK, seed: int = 0
) -> list[float]:
    """A mono bed of ``duration`` seconds with a whoosh of ``length`` seconds starting at each of ``times``: seeded
    noise through a band that sweeps up from 300 Hz to 3 kHz, swelling to its loudest as it ends, so it lands with a
    crash zoom (:func:`srstudio.camera.crash_zoom` returns the cue)."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise FoleyError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not (math.isfinite(length) and 0.05 <= length <= 2.0):
        raise FoleyError(f"length {length} must be within 0.05..2 s")
    if not (math.isfinite(duration) and duration > 0 and all(0 <= t <= duration - length for t in times)):
        raise FoleyError(f"duration {duration} must leave {length:.2f} s after every cue")
    if not (math.isfinite(peak) and 0 < peak <= 1):
        raise FoleyError(f"peak {peak} must be in 0..1")
    rng = random.Random(seed)
    out = [0.0] * int(round(duration * rate))
    n = int(length * rate)
    for at in sorted(times):
        begin = int(at * rate)
        low = band = 0.0
        for k in range(n):
            if begin + k >= len(out):
                break
            x = k / n
            hz = 300.0 * (10.0**x)  # 300 Hz to 3 kHz, evenly in pitch
            f = 2 * math.sin(math.pi * min(hz, rate / 6) / rate)  # a state-variable band-pass, stable up to rate/6
            noise = rng.uniform(-1.0, 1.0)
            high = noise - low - 0.5 * band
            band += f * high
            low += f * band
            env = (x**2) * min(1.0, (1 - x) / 0.04)  # swell, then a 12 ms fade so it never clicks
            out[begin + k] += env * band
    top = max((abs(v) for v in out), default=0.0)
    if top > 0:
        out = [v * peak / top for v in out]
    return out


def write_whoosh(
    path: Path, times: Sequence[float], duration: float, length: float = WHOOSH, rate: int = RATE, seed: int = 0
) -> Path:
    """The whoosh bed for the given cue times, written to ``path``."""
    return write_wav(path, whoosh(times, duration, length, rate, PEAK, seed), rate)


Glide = tuple[float, float, float]  # (start Hz, end Hz, seconds): one note that slides
STING: tuple[Glide, ...] = ((330.0, 262.0, 0.32), (262.0, 196.0, 0.42))  # the "wah-wah": two sagging notes
CHIME: tuple[Glide, ...] = ((784.0, 784.0, 0.12), (1047.0, 1047.0, 0.22))  # a call's two-note chime


def tones(
    times: Sequence[float], duration: float, notes: Sequence[Glide] = STING, rate: int = RATE, peak: float = PEAK
) -> list[float]:
    """A mono bed of ``duration`` seconds with the ``notes`` played in turn at each of ``times``: each note a soft
    tone (a sine with a touch of its octave) sliding from its start to its end frequency, faded in and out."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise FoleyError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not notes or any(not (20 <= a <= 8000 and 20 <= b <= 8000 and 0.02 <= n <= 3.0) for a, b, n in notes):
        raise FoleyError("notes are (start Hz, end Hz, seconds) within 20..8000 Hz and 0.02..3 s")
    length = sum(n for _, _, n in notes)
    if not (math.isfinite(duration) and duration > 0 and all(0 <= t <= duration - length for t in times)):
        raise FoleyError(f"duration {duration} must leave {length:.2f} s after every cue")
    if not (math.isfinite(peak) and 0 < peak <= 1):
        raise FoleyError(f"peak {peak} must be in 0..1")
    out = [0.0] * int(round(duration * rate))
    for at in sorted(times):
        offset = 0.0
        for start_hz, end_hz, seconds in notes:
            begin = int((at + offset) * rate)
            phase = 0.0
            for k in range(int(seconds * rate)):
                if begin + k >= len(out):
                    break
                t = k / rate
                hz = start_hz + (end_hz - start_hz) * t / seconds
                phase += 2 * math.pi * hz / rate
                env = min(1.0, t / 0.015, (seconds - t) / 0.06)
                out[begin + k] += env * (math.sin(phase) + 0.3 * math.sin(2 * phase)) * (1.0 - 0.35 * t / seconds)
            offset += seconds
    top = max((abs(v) for v in out), default=0.0)
    if top > 0:
        out = [v * peak / top for v in out]
    return out


def write_tones(
    path: Path,
    times: Sequence[float],
    duration: float,
    notes: Sequence[Glide] = STING,
    rate: int = RATE,
    peak: float = PEAK,
) -> Path:
    """The sting or chime bed for the given cue times, written to ``path``."""
    return write_wav(path, tones(times, duration, notes, rate, peak), rate)

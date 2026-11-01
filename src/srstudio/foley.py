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
from dataclasses import dataclass
from pathlib import Path

from . import checks
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
    "Burst",
    "bursts",
    "write_bursts",
    "REMOTE_CLICK",
    "KNOCK",
    "SLAM",
    "SNORE",
    "SCRAPE",
    "SWISH",
    "DING",
    "RING",
    "THUD",
    "CHIRP",
    "CHIRP_SHUT",
    "CHIRP_BURIED",
    "RUMBLE",
    "ROAD",
    "CHOPPER",
    "GULL",
    "PLATES",
    "BITE",
    "CHEW",
    "PAPER_CRUNCH",
    "COIN",
    "GAS_LIFT",
    "CART_WHEELS",
    "PEN",
    "CLACK",
    "FLAP",
    "CLINK",
    "SIP",
    "SIZZLE",
    "PURR",
    "HUM",
    "BIRD",
    "BARK",
    "CREAK",
    "SQUEAK",
    "GROWL",
    "GROWL_REPLY",
    "GROWL_SMALL",
    "GROWL_VAST",
    "STING",
    "whoosh",
    "write_whoosh",
    "WHOOSH",
    "plop",
    "write_plop",
    "PLOP",
    "CHIME",
    "CYCLE_DONE",
    "BELL",
    "air",
    "write_air",
    "jingle",
    "room",
    "write_room",
    "WATER_EDGE",
    "water",
    "write_water",
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
    if not (checks.number(threshold) and threshold > 0):
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
    if not (checks.number(duration) and duration > 0 and all(0 <= t <= duration - KEY_TAIL for t in times)):
        raise FoleyError(f"duration {duration} must leave {KEY_TAIL} s after every keystroke")
    if not (checks.number(peak) and 0 < peak <= 1):
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
    if not (checks.number(length) and 0.05 <= length <= 2.0):
        raise FoleyError(f"length {length} must be within 0.05..2 s")
    if not (checks.number(duration) and duration > 0 and all(0 <= t <= duration - length for t in times)):
        raise FoleyError(f"duration {duration} must leave {length} s after every buzz")
    if not (checks.number(peak) and 0 < peak <= 1):
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
    if not (checks.number(length) and 0.05 <= length <= 2.0):
        raise FoleyError(f"length {length} must be within 0.05..2 s")
    if not (checks.number(duration) and duration > 0 and all(0 <= t <= duration - length for t in times)):
        raise FoleyError(f"duration {duration} must leave {length:.2f} s after every cue")
    if not (checks.number(peak) and 0 < peak <= 1):
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


PLOP = 1.6  # seconds of one plop: the hit, then the bubbles climbing after it


def plop(times: Sequence[float], duration: float, rate: int = RATE, seed: int = 0, peak: float = PEAK) -> list[float]:
    """A mono bed of ``duration`` seconds with something heavy dropped into water at each of ``times``. The weight is
    a body sinking from 130 to 70 Hz with its octave, so it carries on a phone speaker, under a short splash; the
    water closes over it in a bloop rising from 160 to 480 Hz; then seeded bubbles climb and thin out."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise FoleyError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not (checks.number(duration) and duration > 0 and all(0 <= t <= duration - PLOP for t in times)):
        raise FoleyError(f"duration {duration} must leave {PLOP:.2f} s after every cue")
    if not (checks.number(peak) and 0 < peak <= 1):
        raise FoleyError(f"peak {peak} must be in 0..1")
    rng = random.Random(seed)
    out = [0.0] * int(round(duration * rate))
    smooth = 1.0 - math.exp(-2 * math.pi * 1600.0 / rate)

    def rising(begin: int, seconds: float, low_hz: float, high_hz: float, level: float) -> None:
        phase = 0.0
        n = int(seconds * rate)
        for k in range(n):
            x = k / n
            phase += 2 * math.pi * (low_hz + (high_hz - low_hz) * x) / rate
            out[begin + k] += level * math.sin(phase) * min(1.0, k / (0.004 * rate), 8 * (1 - x))

    for at in sorted(times):
        begin = int(at * rate)
        low, body = 0.0, 0.0
        for k in range(int(0.7 * rate)):
            t = k / rate
            body += 2 * math.pi * (70.0 + 60.0 * math.exp(-t / 0.08)) / rate
            low += smooth * (rng.uniform(-1, 1) - low)
            env = min(1.0, t / 0.003) * math.exp(-t / 0.24)
            splash = 0.9 * low * math.exp(-t / 0.035)
            out[begin + k] += env * (math.sin(body) + 0.3 * math.sin(2 * body) + splash)
        rising(begin + int(0.09 * rate), 0.16, 160.0, 480.0, 0.5)
        count = 9
        for i in range(count):
            when = 0.30 + (PLOP - 0.42) * (i + rng.uniform(0.0, 0.7)) / count
            hz = rng.uniform(420.0, 900.0)
            rising(begin + int(when * rate), 0.07, hz, hz * 1.5, 0.3 * (1 - 0.8 * i / count))
    top = max((abs(v) for v in out), default=0.0)
    if top > 0:
        out = [v * peak / top for v in out]
    return out


def write_plop(path: Path, times: Sequence[float], duration: float, rate: int = RATE, seed: int = 0) -> Path:
    """The bed of :func:`plop`, written to ``path``."""
    return write_wav(path, plop(times, duration, rate, seed), rate)


def air(
    times: Sequence[float], duration: float, length: float, rate: int = RATE, peak: float = PEAK, seed: int = 0
) -> list[float]:
    """A mono bed of ``duration`` seconds with air rushing out for ``length`` seconds from each of ``times``: seeded
    noise with its lows taken off, loud at once and thinning to nothing, as a torn bag or a tyre lets go."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise FoleyError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not (checks.number(length) and 0.1 <= length <= 5.0):
        raise FoleyError(f"length {length} must be within 0.1..5 s")
    if not (checks.number(duration) and duration > 0 and all(0 <= t <= duration - length for t in times)):
        raise FoleyError(f"duration {duration} must leave {length:.2f} s after every cue")
    if not (checks.number(peak) and 0 < peak <= 1):
        raise FoleyError(f"peak {peak} must be in 0..1")
    rng = random.Random(seed)
    out = [0.0] * int(round(duration * rate))
    n = int(length * rate)
    for at in sorted(times):
        begin = int(at * rate)
        low = 0.0
        for k in range(n):
            if begin + k >= len(out):
                break
            x = k / n
            noise = rng.uniform(-1.0, 1.0)
            low += 0.12 * (noise - low)  # what is left after taking this off is the hiss
            env = min(1.0, k / (0.02 * rate)) * (1 - x) ** 1.5
            out[begin + k] += env * (noise - low)
    top = max((abs(v) for v in out), default=0.0)
    if top > 0:
        out = [v * peak / top for v in out]
    return out


def write_air(
    path: Path, times: Sequence[float], duration: float, length: float, rate: int = RATE, seed: int = 0
) -> Path:
    """The air bed for the given cue times, written to ``path``."""
    return write_wav(path, air(times, duration, length, rate, PEAK, seed), rate)


ROOM_LOW = 0.02  # share of each noise sample a room keeps: under about 170 Hz at the foley's rate
ROOM_HUM = ((120.0, 0.5), (240.0, 0.2))  # a fridge across the room, in the band a phone speaker still plays
ROOM_EDGE = 0.05  # seconds it fades at each end, so the cut back to the first frame does not click


def room(duration: float, rate: int = RATE, peak: float = PEAK, seed: int = 0) -> list[float]:
    """A mono bed of ``duration`` seconds of an ordinary room: soft low noise and a far fridge. Silence under a held
    pause reads as a dropped file; this keeps the pause in a place, and it never competes with a line."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise FoleyError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not (checks.number(duration) and duration >= 2 * ROOM_EDGE):
        raise FoleyError(f"duration {duration} must be at least {2 * ROOM_EDGE} s")
    if not (checks.number(peak) and 0 < peak <= 1):
        raise FoleyError(f"peak {peak} must be in 0..1")
    rng = random.Random(seed)
    n, edge = int(round(duration * rate)), int(ROOM_EDGE * rate)
    out, low = [0.0] * n, 0.0
    for k in range(n):
        low += ROOM_LOW * (rng.uniform(-1.0, 1.0) - low)
        hum = sum(level * math.sin(2 * math.pi * hz * k / rate) for hz, level in ROOM_HUM)
        out[k] = (low * 6.0 + hum * 0.2) * min(1.0, k / edge, (n - 1 - k) / edge)
    top = max(abs(v) for v in out)
    return [v * peak / top for v in out]


def jingle(at: float, seed: int = 0, shakes: int = 7) -> list[float]:
    """The moments of a bunch of keys coming out of a pocket from second ``at``, for :data:`KEYS`: a loose, uneven run
    that slows as the hand finds the right one."""
    if not (checks.number(at) and at >= 0 and isinstance(shakes, int) and shakes > 0):
        raise FoleyError(f"a jingle needs a time and a count, got {at!r}, {shakes!r}")
    rng = random.Random(seed)
    times, gap = [at], 0.05
    for _ in range(shakes - 1):
        times.append(round(times[-1] + gap * rng.uniform(0.7, 1.3), 4))
        gap *= 1.25
    return times


def write_room(path: Path, duration: float, rate: int = RATE, seed: int = 0) -> Path:
    """The bed of :func:`room`, written to ``path``."""
    return write_wav(path, room(duration, rate, PEAK, seed), rate)


WATER_EDGE = 0.02  # seconds a shower takes to come on or go off: a tap, not a fade


def water(
    spans: Sequence[tuple[float, float]], duration: float, rate: int = RATE, peak: float = PEAK, seed: int = 0
) -> list[float]:
    """A mono bed of ``duration`` seconds with a shower running through each ``(start, end)``: seeded noise with its
    lows and its highest hiss taken off, steady while it runs, and silence between, so the tap is heard."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise FoleyError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not (checks.number(duration) and duration > 0):
        raise FoleyError(f"duration {duration} must be over 0 s")
    if not (checks.number(peak) and 0 < peak <= 1):
        raise FoleyError(f"peak {peak} must be in 0..1")
    last = 0.0
    if not spans:
        raise FoleyError("water needs at least one span")
    for start, end in spans:
        if not (checks.number(start) and checks.number(end) and last <= start < end <= duration):
            raise FoleyError(f"water's spans rise within {duration} s, got span {start!r}..{end!r}")
        last = end
    rng = random.Random(seed)
    out = [0.0] * int(round(duration * rate))
    edge = max(1, int(WATER_EDGE * rate))
    for start, end in spans:
        first, stop = int(start * rate), min(int(end * rate), len(out))
        low = high = 0.0
        for k in range(first, stop):
            noise = rng.uniform(-1.0, 1.0)
            low += 0.06 * (noise - low)  # what is left after taking this off has no rumble
            high += 0.5 * (noise - low - high)  # and this is it with the top rounded
            out[k] = min(1.0, (k - first + 1) / edge, (stop - k) / edge) * high
    top = max(abs(v) for v in out)
    return [v * peak / top for v in out] if top > 0 else out


def write_water(
    path: Path, spans: Sequence[tuple[float, float]], duration: float, rate: int = RATE, seed: int = 0
) -> Path:
    """The shower bed for the given spans, written to ``path``."""
    return write_wav(path, water(spans, duration, rate, PEAK, seed), rate)


Glide = tuple[float, float, float]  # (start Hz, end Hz, seconds): one note that slides
STING: tuple[Glide, ...] = ((330.0, 262.0, 0.32), (262.0, 196.0, 0.42))  # the "wah-wah": two sagging notes
CHIME: tuple[Glide, ...] = ((784.0, 784.0, 0.12), (1047.0, 1047.0, 0.22))  # a call's two-note chime
DING: tuple[Glide, ...] = ((1319.0, 1319.0, 0.07), (1760.0, 1760.0, 0.2))  # a phone's notification
# one ring of a desk phone: two close notes swapping fast, the trill a real bell makes
RING: tuple[Glide, ...] = tuple((1175.0 if i % 2 else 988.0,) * 2 + (0.05,) for i in range(18))
CYCLE_DONE: tuple[Glide, ...] = (  # an appliance pleased with itself: five notes that climb and sit back
    (1047.0, 1047.0, 0.16),
    (1319.0, 1319.0, 0.16),
    (1568.0, 1568.0, 0.16),
    (1319.0, 1319.0, 0.16),
    (2093.0, 2093.0, 0.42),
)


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
    if not (checks.number(duration) and duration > 0 and all(0 <= t <= duration - length for t in times)):
        raise FoleyError(f"duration {duration} must leave {length:.2f} s after every cue")
    if not (checks.number(peak) and 0 < peak <= 1):
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


# -- bursts: one short sound, shaped by numbers ---------------------------------------------------------------------
@dataclass(frozen=True)
class Burst:
    """One sound as numbers: ``seconds`` of noise, smoothed by a one-pole low-pass at ``low_hz``, plus a tone sliding
    from ``tone_hz`` to ``tone_end_hz`` at ``tone`` of the level, rising over ``attack`` seconds and falling away
    exponentially at ``decay`` (the fraction of the sound's length it takes to drop to a third), the whole shaken at
    ``flutter_hz`` when that is set (a snore's rattle, a rotor's chop)."""

    seconds: float
    low_hz: float
    attack: float = 0.002
    decay: float = 0.5
    tone_hz: float = 0.0
    tone_end_hz: float = 0.0
    tone: float = 0.0
    flutter_hz: float = 0.0

    def __post_init__(self) -> None:
        if not (checks.number(self.seconds) and 0.01 <= self.seconds <= 8.0):
            raise FoleyError(f"a burst lasts 0.01..8 s, got {self.seconds}")
        if not (checks.number(self.low_hz) and 20 <= self.low_hz <= 20000):
            raise FoleyError(f"a burst's low-pass is 20..20000 Hz, got {self.low_hz}")
        if not (checks.number(self.attack) and 0 < self.attack < self.seconds):
            raise FoleyError(f"a burst's attack is under its length, got {self.attack}")
        if not (checks.number(self.decay) and self.decay > 0):
            raise FoleyError(f"a burst's decay is positive, got {self.decay}")
        if not (checks.number(self.tone) and 0 <= self.tone <= 1):
            raise FoleyError(f"a burst's tone level is 0..1, got {self.tone}")
        for hz in (self.tone_hz, self.tone_end_hz, self.flutter_hz):
            if not (checks.number(hz) and 0 <= hz <= 8000):
                raise FoleyError(f"a burst's tone and flutter are 0..8000 Hz, got {hz}")


REMOTE_CLICK = Burst(0.03, 6000.0, attack=0.001, decay=0.25, tone_hz=2400.0, tone_end_hz=1800.0, tone=0.5)
KNOCK = Burst(0.12, 900.0, attack=0.002, decay=0.3, tone_hz=170.0, tone_end_hz=120.0, tone=0.7)
SNORE = Burst(1.1, 420.0, attack=0.35, decay=1.2, tone_hz=70.0, tone_end_hz=95.0, tone=0.35, flutter_hz=31.0)
BELL = Burst(0.45, 200.0, attack=0.002, decay=0.45, tone_hz=1760.0, tone_end_hz=1760.0, tone=1.0)
SLAM = Burst(0.5, 800.0, attack=0.001, decay=0.45, tone_hz=120.0, tone_end_hz=46.0, tone=0.65)  # a door, a room off
THUD = Burst(0.25, 500.0, attack=0.003, decay=0.35, tone_hz=90.0, tone_end_hz=55.0, tone=0.8)
CHIRP = Burst(0.08, 200.0, attack=0.001, decay=0.09, tone_hz=3300.0, tone_end_hz=3300.0, tone=1.0)
CHIRP_SHUT = Burst(0.1, 200.0, attack=0.003, decay=0.1, tone_hz=1100.0, tone_end_hz=1100.0, tone=0.5)  # behind a door
CHIRP_BURIED = Burst(0.12, 200.0, attack=0.006, decay=0.12, tone_hz=620.0, tone_end_hz=620.0, tone=0.5)  # under earth
RUMBLE = Burst(1.4, 700.0, attack=0.02, decay=0.9, tone_hz=60.0, tone_end_hz=45.0, tone=0.4, flutter_hz=11.0)
ROAD = Burst(3.0, 380.0, attack=0.12, decay=4.0, tone_hz=64.0, tone_end_hz=72.0, tone=0.3, flutter_hz=7.0)
CHOPPER = Burst(3.0, 520.0, attack=0.5, decay=4.0, tone_hz=48.0, tone_end_hz=48.0, tone=0.4, flutter_hz=13.0)
GULL = Burst(0.5, 300.0, attack=0.02, decay=0.6, tone_hz=1450.0, tone_end_hz=880.0, tone=1.0, flutter_hz=17.0)
SCRAPE = Burst(0.3, 1500.0, attack=0.02, decay=0.5, tone_hz=220.0, tone_end_hz=170.0, tone=0.25, flutter_hz=38.0)
SWISH = Burst(0.6, 2600.0, attack=0.2, decay=0.6, tone_hz=300.0, tone_end_hz=900.0, tone=0.15)
PLATES = Burst(0.3, 9000.0, attack=0.001, decay=0.3, tone_hz=3100.0, tone_end_hz=2900.0, tone=0.35)
KEYS = Burst(0.08, 8000.0, attack=0.001, decay=0.2, tone_hz=4300.0, tone_end_hz=3900.0, tone=0.3)
BITE = Burst(0.1, 3200.0, attack=0.001, decay=0.3, tone_hz=210.0, tone_end_hz=120.0, tone=0.3)  # teeth through bread
CHEW = Burst(0.2, 800.0, attack=0.03, decay=0.5, tone_hz=120.0, tone_end_hz=85.0, tone=0.3, flutter_hz=23.0)
PAPER_CRUNCH = Burst(0.42, 7500.0, attack=0.005, decay=0.45, flutter_hz=47.0)  # a napkin, between the teeth
COIN = Burst(0.26, 9000.0, attack=0.001, decay=0.3, tone_hz=4300.0, tone_end_hz=4240.0, tone=0.55)  # one, on a counter
GAS_LIFT = Burst(0.6, 6500.0, attack=0.015, decay=0.65)  # an office chair letting go; ``seconds`` sets how far it drops
CART_WHEELS = Burst(1.1, 1300.0, attack=0.06, decay=1.6, tone_hz=95.0, tone_end_hz=95.0, tone=0.15, flutter_hz=19.0)
PEN = Burst(0.5, 3800.0, attack=0.03, decay=0.8, flutter_hz=29.0)  # a nib on paper, unhurried
CLACK = Burst(0.05, 7000.0, attack=0.001, decay=0.22, tone_hz=2600.0, tone_end_hz=2300.0, tone=0.45)  # kitchen tongs
FLAP = Burst(0.12, 1800.0, attack=0.004, decay=0.3, tone_hz=240.0, tone_end_hz=140.0, tone=0.3)  # a page, a burger
CLINK = Burst(0.09, 9000.0, attack=0.001, decay=0.2, tone_hz=4300.0, tone_end_hz=4250.0, tone=0.5)  # a coin, a glass
SIP = Burst(0.34, 2600.0, attack=0.1, decay=0.6, tone_hz=520.0, tone_end_hz=760.0, tone=0.12, flutter_hz=31.0)  # a cup
SIZZLE = Burst(4.0, 7000.0, attack=0.3, decay=5.0, flutter_hz=23.0)  # fat on a grill; lay them end to end
PURR = Burst(4.0, 320.0, attack=0.3, decay=6.0, tone_hz=58.0, tone_end_hz=58.0, tone=0.5, flutter_hz=26.0)  # a motor
HUM = Burst(4.0, 200.0, attack=0.2, decay=8.0, tone_hz=100.0, tone_end_hz=100.0, tone=0.8)  # a fridge
BIRD = Burst(0.14, 400.0, attack=0.01, decay=0.5, tone_hz=3400.0, tone_end_hz=4300.0, tone=1.0, flutter_hz=41.0)
BARK = Burst(0.16, 1100.0, attack=0.006, decay=0.4, tone_hz=520.0, tone_end_hz=300.0, tone=0.6, flutter_hz=70.0)
CREAK = Burst(2.4, 520.0, attack=0.25, decay=1.4, tone_hz=210.0, tone_end_hz=120.0, tone=0.55, flutter_hz=17.0)
SQUEAK = Burst(0.3, 900.0, attack=0.02, decay=0.5, tone_hz=1500.0, tone_end_hz=2100.0, tone=0.7, flutter_hz=33.0)
GROWL = Burst(1.5, 240.0, attack=0.12, decay=1.1, tone_hz=88.0, tone_end_hz=190.0, tone=0.6, flutter_hz=14.0)
GROWL_REPLY = Burst(0.9, 300.0, attack=0.08, decay=0.9, tone_hz=150.0, tone_end_hz=250.0, tone=0.6, flutter_hz=17.0)
GROWL_SMALL = Burst(0.5, 260.0, attack=0.05, decay=0.7, tone_hz=210.0, tone_end_hz=140.0, tone=0.6, flutter_hz=21.0)
GROWL_VAST = Burst(4.2, 180.0, attack=0.4, decay=1.6, tone_hz=62.0, tone_end_hz=36.0, tone=0.6, flutter_hz=8.0)


def bursts(
    times: Sequence[float], duration: float, sound: Burst, rate: int = RATE, seed: int = 0, peak: float = PEAK
) -> list[float]:
    """A mono bed of ``duration`` seconds with ``sound`` at each of ``times``, seeded, the last one cut at the end."""
    if not (isinstance(rate, int) and rate >= MIN_RATE):
        raise FoleyError(f"rate {rate} must be an integer of at least {MIN_RATE} Hz")
    if not (checks.number(duration) and duration > 0 and all(0 <= t < duration for t in times)):
        raise FoleyError(f"duration {duration} must hold every cue, got {list(times)}")
    if not (checks.number(peak) and 0 < peak <= 1):
        raise FoleyError(f"peak {peak} must be in 0..1")
    out = [0.0] * int(round(duration * rate))
    rng = random.Random(seed)
    smooth = 1.0 - math.exp(-2 * math.pi * sound.low_hz / rate)
    total = int(sound.seconds * rate)
    for at in sorted(times):
        begin = int(at * rate)
        low, phase = 0.0, 0.0
        for k in range(min(total, len(out) - begin)):
            t = k / rate
            low += smooth * (rng.uniform(-1, 1) - low)
            hz = sound.tone_hz + (sound.tone_end_hz - sound.tone_hz) * t / sound.seconds
            phase += 2 * math.pi * hz / rate
            shake = 0.6 + 0.4 * math.sin(2 * math.pi * sound.flutter_hz * t) if sound.flutter_hz else 1.0
            env = min(1.0, t / sound.attack, (sound.seconds - t) / 0.01) * math.exp(-t / (sound.seconds * sound.decay))
            out[begin + k] += env * shake * ((1 - sound.tone) * low + sound.tone * math.sin(phase))
    top = max((abs(v) for v in out), default=0.0)
    if top > 0:
        out = [v * peak / top for v in out]
    return out


def write_bursts(
    path: Path, times: Sequence[float], duration: float, sound: Burst, rate: int = RATE, seed: int = 0
) -> Path:
    """The bed of :func:`bursts`, written to ``path``."""
    return write_wav(path, bursts(times, duration, sound, rate, seed), rate)

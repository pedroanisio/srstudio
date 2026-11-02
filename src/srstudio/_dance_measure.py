"""The groove check: read a sampled channel back as cycles per beat, strokes, size and the hit against the beat.

The spectrum finds the cycle, and a least-squares fit of repeating curves sharpens it. Samples taken over many cycles
fall at different places in the cycle, so the fit recovers its shape finer than the picture rate; when a cycle is a
whole number of pictures they do not, and the reading says so in ``resolution``. The two seat-groove targets are the car
dance a reel was measured to hold, and :meth:`DanceTarget.misses` is the acceptance test (ADR 0186).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from . import checks
from ._dance_model import DanceError
from .music import Groove

__all__ = ["SEAT_GROOVE_BOB", "SEAT_GROOVE_SWAY", "DanceMeasureError", "DanceReading", "DanceTarget", "measure_dance"]

MAX_SAMPLES = 20_000  # over thirteen minutes at 25 pictures a second
MIN_SAMPLES = 16
MIN_CYCLES = 2  # one cycle says nothing about whether it repeats
_SEARCH = 0.04  # the samples refine the spectrum's cycle within this fraction of it
_STEPS = 41
_PASSES = 3  # each pass searches one step of the last: 41 * 3 fits bound the work on any series
_HARMONICS = 8  # for the search: the picture rate may allow fewer
_SHAPE = 12  # overtones of the final curve, which many cycles carry past the picture rate
_GRID = 2048  # places the fitted curve is read at, a fraction of a millisecond apart on a beat
_FLAT = 1e-9


class DanceMeasureError(DanceError):
    """A series that cannot be read as a dance, or a target that cannot be built."""


@dataclass(frozen=True)
class DanceReading:
    """A channel's groove: ``cycles_per_beat`` over a ``period`` of seconds; ``rise`` and ``fall`` the seconds from its
    low to its high and back; ``snap_ratio`` rise over fall; its ``peak_to_peak`` in the channel's own units; which
    extreme is the ``hit``; ``hit_beats`` its place in the cycle, in beats from the cycle that opens on the grid's
    offset; ``hit_offset`` its distance from the nearest beat, in beats, negative before it; ``resolution`` the widest
    gap, in seconds, the samples leave in the cycle, which no reading of its strokes can beat."""

    cycles_per_beat: float
    period: float
    rise: float
    fall: float
    snap_ratio: float
    peak_to_peak: float
    hit: str
    hit_beats: float
    hit_offset: float
    resolution: float

    @property
    def onto(self) -> float:
        """Seconds of the stroke that lands on the hit."""
        return self.rise if self.hit == "max" else self.fall

    @property
    def away(self) -> float:
        """Seconds of the stroke that leaves the hit."""
        return self.fall if self.hit == "max" else self.rise


def _bad(condition: bool, message: str, path: str) -> None:
    if condition:
        raise DanceMeasureError(message, code="dance.measure", path=path)


@dataclass(frozen=True)
class DanceTarget:
    """What a channel must read: strokes in seconds, peak to peak as a (low, high) range, and the extreme it must hit
    (``min``, ``max``, or ``either`` when a dance may be mirrored)."""

    cycles_per_beat: float
    onto: float
    away: float
    peak_to_peak: tuple[float, float]
    hit: str = "either"
    hit_offset: float = 0.0
    cycle_tolerance: float = 0.02
    time_tolerance: float = 0.02
    hit_tolerance: float = 0.02

    def __post_init__(self) -> None:
        for name in ("cycles_per_beat", "onto", "away", "cycle_tolerance", "time_tolerance", "hit_tolerance"):
            value = getattr(self, name)
            _bad(not (checks.number(value) and value > 0), f"target {name} {value!r} is above zero", name)
        span = self.peak_to_peak
        _bad(
            not (isinstance(span, tuple) and len(span) == 2 and all(checks.number(v) for v in span)),
            "target peak_to_peak is a (low, high) pair",
            "peak_to_peak",
        )
        _bad(not 0 <= span[0] <= span[1], f"target peak_to_peak {span} is an ordered range", "peak_to_peak")
        _bad(self.hit not in ("min", "max", "either"), f"target hit {self.hit!r} is min, max or either", "hit")
        _bad(
            not (checks.number(self.hit_offset) and abs(self.hit_offset) <= 0.5),
            f"target hit_offset {self.hit_offset!r} lies in -0.5..0.5 beats",
            "hit_offset",
        )

    def misses(self, reading: DanceReading) -> tuple[str, ...]:
        """Each way ``reading`` misses this target, in words; none means it meets it."""
        out = []
        if reading.resolution > self.time_tolerance:
            out.append(f"samples {reading.resolution:.3f} s apart cannot show {self.time_tolerance:g} s")
        if abs(reading.cycles_per_beat - self.cycles_per_beat) > self.cycle_tolerance:
            out.append(f"cycles per beat {reading.cycles_per_beat:.3f}, not {self.cycles_per_beat:g}")
        if abs(reading.onto - self.onto) > self.time_tolerance:
            out.append(f"onto the hit in {reading.onto:.3f} s, not {self.onto:g} s")
        if abs(reading.away - self.away) > self.time_tolerance:
            out.append(f"away from the hit in {reading.away:.3f} s, not {self.away:g} s")
        low, high = self.peak_to_peak
        if not low <= reading.peak_to_peak <= high:
            out.append(f"peak to peak {reading.peak_to_peak:.3f}, not {low:g}..{high:g}")
        if self.hit != "either" and reading.hit != self.hit:
            out.append(f"hit at the {reading.hit}, not the {self.hit}")
        seconds = abs(reading.hit_offset - self.hit_offset) * reading.period * reading.cycles_per_beat
        if seconds > self.hit_tolerance:
            out.append(f"hit {reading.hit_offset:+.3f} beats from the beat, not {self.hit_offset:+g}")
        return tuple(out)


# The car dance measured on a reference reel at 129 BPM. The reel's strokes sum to 0.45 s of a 0.465 s beat, and its
# 25 pictures a second resolve 0.04 s: strokes are held to half a picture, the sway's a little wider for that gap.
SEAT_GROOVE_BOB = DanceTarget(1.0, onto=0.19, away=0.26, peak_to_peak=(0.26, 0.50), hit="min")
SEAT_GROOVE_SWAY = DanceTarget(1.0, onto=0.12, away=0.32, peak_to_peak=(0.17, 0.23), time_tolerance=0.025)


def _series(values: object, missing: bool) -> tuple[np.ndarray, np.ndarray]:
    """The series about its mean, and which samples are present: all of them, unless ``missing`` lets a NaN stand
    for a sample that was not seen."""
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise DanceMeasureError("a series is a sequence of numbers", code="dance.measure", path="series")
    _bad(
        not MIN_SAMPLES <= len(values) <= MAX_SAMPLES,
        f"a series holds {MIN_SAMPLES}..{MAX_SAMPLES} samples, not {len(values)}",
        "series",
    )
    gap = (lambda v: isinstance(v, float) and math.isnan(v)) if missing else (lambda v: False)
    _bad(not all(checks.number(v) or gap(v) for v in values), "a series holds finite numbers only", "series")
    x = np.asarray(values, float)
    present = np.isfinite(x)
    _bad(int(present.sum()) < MIN_SAMPLES, f"a series holds at least {MIN_SAMPLES} samples seen", "series")
    _bad(float(np.ptp(x[present])) < _FLAT, "the series does not move: nothing to measure", "series")
    return np.where(present, x - x[present].mean(), 0.0), present


def _cycle(x: np.ndarray, fps: int) -> float:
    """The strongest cycle in Hz: a windowed spectrum, padded and interpolated between its bins."""
    size = 1 << (16 * len(x) - 1).bit_length()
    power = np.abs(np.fft.rfft(x * np.hanning(len(x)), size))
    power[0] = 0.0
    k = int(np.argmax(power))
    below, here, above = power[k - 1], power[k], power[min(k + 1, len(power) - 1)]
    bend = below - 2 * here + above
    return float((k + (0.5 * (below - above) / bend if bend < 0 else 0.0)) * fps / size)


def _basis(times: np.ndarray, hz: float, harmonics: int) -> np.ndarray:
    turns = 2 * np.pi * hz * np.outer(times, np.arange(1, harmonics + 1))
    return np.hstack((np.ones((len(times), 1)), np.cos(turns), np.sin(turns)))


def _fit(x: np.ndarray, basis: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(basis, x, rcond=None)[0]


def _unexplained(x: np.ndarray, times: np.ndarray, hz: float, harmonics: int) -> float:
    """What a repeating curve of ``hz`` leaves of ``x``: least squares, so no bin width favours a wrong period."""
    basis = _basis(times, hz, harmonics)
    return float(np.sum((x - basis @ _fit(x, basis)) ** 2))


def _refined(x: np.ndarray, times: np.ndarray, hz: float, fps: int, span: int) -> float:
    """The spectrum's cycle sharpened on the samples: a search of the width a span of ``span`` pictures can resolve,
    then twice within one step of the best. The period sets every phase, so an error here grows along the series."""
    harmonics = max(1, min(_HARMONICS, int(fps / 2 / hz - 1e-9)))
    width = min(_SEARCH, 2 / (hz * span / fps))
    best = hz
    for _ in range(_PASSES):
        tries = best * (1 + np.linspace(-width, width, _STEPS))
        best = float(tries[int(np.argmin([_unexplained(x, times, f, harmonics) for f in tries]))])
        width *= 2 / (_STEPS - 1)
    return best


def _curve(x: np.ndarray, times: np.ndarray, hz: float) -> tuple[np.ndarray, float]:
    """One cycle read at ``_GRID`` places from the grid's offset, and the widest gap the samples leave in it, as a
    fraction of the cycle. A cycle sampled at only a few places carries only the overtones those places can tell."""
    places = np.sort(times * hz % 1.0)
    gaps = np.diff(places, append=places[0] + 1)
    harmonics = min(_SHAPE, (int(np.sum(gaps > 1e-3)) - 1) // 2)
    _bad(harmonics < 1, "the samples land on too few places in the cycle to show its shape", "series")
    grid = np.arange(_GRID) / _GRID / hz
    return _basis(grid, hz, harmonics) @ _fit(x, _basis(times, hz, harmonics)), float(np.max(gaps))


def measure_dance(
    series: Sequence[float], fps: int, groove: Groove, *, start: float = 0.0, hit: str = "snap", missing: bool = False
) -> DanceReading:
    """A sampled channel's groove against ``groove``; ``series[0]`` is at second ``start``.

    ``hit`` is the extreme to place against the beat: ``max``, ``min``, or ``snap``, where the quicker stroke lands.
    The cost is bounded by ``MAX_SAMPLES``. A flat series, or one under two cycles, raises
    :class:`DanceMeasureError`: a series that does not hold a groove reads as no groove, never as a poor one.

    With ``missing``, a NaN is a sample not seen, as a pose estimator leaves when it loses a dancer (ADR 0200). Nothing
    is filled in: the cycle is found on the series with the gaps at its mean, then fitted, and its shape read, on the
    samples present alone, and ``resolution`` counts the gaps they leave in the cycle."""
    if not isinstance(groove, Groove):
        raise DanceMeasureError(f"a series is read on a music.Groove, not {type(groove).__name__}", path="groove")
    _bad(type(fps) is not int or not 1 <= fps <= 1000, f"fps {fps!r} is a whole number in 1..1000", "fps")
    _bad(not checks.number(start), f"start {start!r} is a finite number of seconds", "start")
    _bad(hit not in ("snap", "max", "min"), f"hit {hit!r} is snap, max or min", "hit")
    x, present = _series(series, missing)
    hz = _cycle(x, fps)
    _bad(
        hz * len(x) / fps < MIN_CYCLES,
        f"the series holds {hz * len(x) / fps:.2f} cycles of its strongest motion; at least {MIN_CYCLES} are needed",
        "series",
    )
    times = (start - groove.offset + np.arange(len(x)) / fps)[present]
    x = x[present]
    hz = _refined(x, times, hz, fps, len(present))
    curve, gap = _curve(x, times, hz)
    low, high = int(np.argmin(curve)) / _GRID, int(np.argmax(curve)) / _GRID
    period = 1 / hz
    rise = (high - low) % 1.0 * period
    fall = period - rise
    side = hit if hit != "snap" else ("max" if rise < fall else "min")
    place = (high if side == "max" else low) * period / groove.beat
    return DanceReading(
        float(hz * groove.beat),
        period,
        rise,
        fall,
        rise / fall,
        float(np.ptp(curve)),
        side,
        place,
        place - round(place),
        gap * period,
    )

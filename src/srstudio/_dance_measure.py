"""The groove check: read a sampled channel back as cycles per beat, strokes, size and the hit against the beat.

The spectrum finds the cycle, and a least-squares fit of repeating curves sharpens it. Samples taken over many cycles
fall at different places in the cycle, so the fit recovers its shape finer than the picture rate; when a cycle is a
whole number of pictures they do not, and the reading says so in ``resolution``. The two seat-groove targets are the car
dance a reel was measured to hold, and :meth:`DanceTarget.misses` is the acceptance test (ADR 0186).

The fitted curve's derivatives are exact, so the reading also carries the gesture's own timing (ADR 0199): where in the
cycle it is fastest, its attack (10% to 90% of the way from the far extreme onto the hit) and release (back off it), its
peak acceleration per beat squared in amplitudes (half the peak to peak), and its velocity profile, normalized to its
fastest moment and read at :data:`PROFILE_POINTS` places from the hit, which :func:`profile_distance` compares.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from . import checks
from ._dance_errors import DanceError
from .music import Groove

__all__ = [
    "MAX_HARMONICS",
    "PROFILE_POINTS",
    "SEAT_GROOVE_BOB",
    "SEAT_GROOVE_SWAY",
    "DanceMeasureError",
    "DanceReading",
    "DanceTarget",
    "measure_dance",
    "profile_distance",
]

MAX_SAMPLES = 20_000  # over thirteen minutes at 25 pictures a second
MIN_SAMPLES = 16
MIN_CYCLES = 2  # one cycle says nothing about whether it repeats
_SEARCH = 0.04  # the samples refine the spectrum's cycle within this fraction of it
_STEPS = 41
_PASSES = 3  # each pass searches one step of the last: 41 * 3 fits bound the work on any series
_HARMONICS = 8  # for the search: the picture rate may allow fewer
_SHAPE = 12  # overtones of the final curve, which many cycles carry past the picture rate
MAX_HARMONICS = 32  # the most a caller may ask for: a sharp strike's acceleration needs about 24 to read within 5%
_GRID = 2048  # places the fitted curve is read at, a fraction of a millisecond apart on a beat
_FLAT = 1e-9
PROFILE_POINTS = 32  # places a velocity profile is read at: a 16th note apart on a two-beat cycle
STROKE = 0.8  # an attack or release runs from 10% to 90% of the way between the extremes: -0.8 to +0.8


class DanceMeasureError(DanceError):
    """A series that cannot be read as a dance, or a target that cannot be built."""


@dataclass(frozen=True)
class DanceReading:
    """A channel's groove: ``cycles_per_beat`` over a ``period`` of seconds; ``rise`` and ``fall`` the seconds from its
    low to its high and back; ``snap_ratio`` rise over fall; its ``peak_to_peak`` in the channel's own units; which
    extreme is the ``hit``; ``hit_beats`` its place in the cycle, in beats from the cycle that opens on the grid's
    offset; ``hit_offset`` its distance from the nearest beat, in beats, negative before it; ``resolution`` the widest
    gap, in seconds, the samples leave in the cycle, which no reading of its strokes can beat.

    The gesture's timing (ADR 0199), counted from the hit: ``peak_speed_phase`` the share of the cycle after the hit at
    which it moves fastest; ``attack`` the seconds from 10% to 90% of the way onto the hit, ``release`` off it;
    ``peak_acceleration`` the largest acceleration in amplitudes (half the peak to peak) per beat squared; ``velocity``
    the speed toward the hit side, over its largest, at :data:`PROFILE_POINTS` places from the hit."""

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
    peak_speed_phase: float | None = None
    attack: float | None = None
    release: float | None = None
    peak_acceleration: float | None = None
    velocity: tuple[float, ...] = ()

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


def _profile(values: object, path: str) -> tuple[float, ...]:
    _bad(
        not (isinstance(values, tuple) and len(values) == PROFILE_POINTS),
        f"a velocity profile is a tuple of {PROFILE_POINTS} numbers",
        path,
    )
    assert isinstance(values, tuple)
    _bad(not all(checks.number(v) and -1 <= v <= 1 for v in values), "a velocity profile lies in -1..1", path)
    return values


def profile_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """How unlike two velocity profiles are: the root mean square of their difference, 0 for the same gesture and up
    to 2 for one played backwards against itself."""
    x, y = _profile(a, "a"), _profile(b, "b")
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(x, y, strict=True)) / PROFILE_POINTS)


def _round_gap(a: float, b: float) -> float:
    """The distance of two places in a cycle, either way round."""
    d = abs(a - b) % 1.0
    return min(d, 1 - d)


@dataclass(frozen=True)
class DanceTarget:
    """What a channel must read: strokes in seconds, peak to peak as a (low, high) range, and the extreme it must hit
    (``min``, ``max``, or ``either`` when a dance may be mirrored).

    A gesture's timing, when given (ADR 0199): ``attack`` and ``release`` in seconds, held to ``time_tolerance``;
    ``peak_speed_phase`` held to ``phase_tolerance`` of the cycle, either way round; ``peak_acceleration`` a range in
    amplitudes per beat squared; and ``velocity`` a profile the reading's must lie within ``profile_tolerance`` of."""

    cycles_per_beat: float
    onto: float
    away: float
    peak_to_peak: tuple[float, float]
    hit: str = "either"
    hit_offset: float = 0.0
    cycle_tolerance: float = 0.02
    time_tolerance: float = 0.02
    hit_tolerance: float = 0.02
    attack: float | None = None
    release: float | None = None
    peak_speed_phase: float | None = None
    peak_acceleration: tuple[float, float] | None = None
    velocity: tuple[float, ...] | None = None
    phase_tolerance: float = 0.03
    profile_tolerance: float = 0.15

    def __post_init__(self) -> None:
        for name in (
            "cycles_per_beat",
            "onto",
            "away",
            "cycle_tolerance",
            "time_tolerance",
            "hit_tolerance",
            "phase_tolerance",
            "profile_tolerance",
        ):
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
        for name in ("attack", "release"):
            value = getattr(self, name)
            _bad(
                value is not None and not (checks.number(value) and value > 0),
                f"target {name} {value!r} is seconds above zero",
                name,
            )
        phase = self.peak_speed_phase
        _bad(
            phase is not None and not (checks.number(phase) and 0 <= phase < 1),
            f"target peak_speed_phase {phase!r} lies in 0..1 of the cycle",
            "peak_speed_phase",
        )
        accel = self.peak_acceleration
        if accel is not None:
            _bad(
                not (isinstance(accel, tuple) and len(accel) == 2 and all(checks.number(v) for v in accel)),
                "target peak_acceleration is a (low, high) pair",
                "peak_acceleration",
            )
            _bad(not 0 <= accel[0] <= accel[1], f"target peak_acceleration {accel} is an ordered range", "acceleration")
        if self.velocity is not None:
            _profile(self.velocity, "velocity")

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
        out.extend(self._timing_misses(reading))
        return tuple(out)

    def _timing_misses(self, reading: DanceReading) -> list[str]:
        out = []
        for name, want, got in (("attack", self.attack, reading.attack), ("release", self.release, reading.release)):
            if want is not None and (got is None or abs(got - want) > self.time_tolerance):
                out.append(f"{name} {got if got is None else round(got, 3)} s, not {want:g} s")
        phase = reading.peak_speed_phase
        if self.peak_speed_phase is not None and (
            phase is None or _round_gap(phase, self.peak_speed_phase) > self.phase_tolerance
        ):
            out.append(f"fastest at {phase} of the cycle, not {self.peak_speed_phase:.3f}")
        accel = reading.peak_acceleration
        if self.peak_acceleration is not None and (
            accel is None or not self.peak_acceleration[0] <= accel <= self.peak_acceleration[1]
        ):
            low, high = self.peak_acceleration
            out.append(f"peak acceleration {accel} amplitudes per beat squared, not {low:g}..{high:g}")
        if self.velocity is not None:
            gap = profile_distance(reading.velocity, self.velocity) if reading.velocity else None
            if gap is None or gap > self.profile_tolerance:
                out.append(f"velocity profile {gap} from the target's, more than {self.profile_tolerance:g}")
        return out


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


def _curve(x: np.ndarray, times: np.ndarray, hz: float, shape: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """One cycle read at ``_GRID`` places from the grid's offset, its first and second derivatives in units per
    second, and the widest gap the samples leave in it, as a fraction of the cycle. A cycle sampled at only a few places
    carries only the overtones those places can tell."""
    places = np.sort(times * hz % 1.0)
    gaps = np.diff(places, append=places[0] + 1)
    harmonics = min(shape, (int(np.sum(gaps > 1e-3)) - 1) // 2)
    _bad(harmonics < 1, "the samples land on too few places in the cycle to show its shape", "series")
    coefficients = _fit(x, _basis(times, hz, harmonics))
    grid = np.arange(_GRID) / _GRID / hz
    k = np.arange(1, harmonics + 1)
    turns = 2 * np.pi * hz * np.outer(grid, k)
    a, b, w = coefficients[1 : harmonics + 1], coefficients[harmonics + 1 :], 2 * np.pi * hz * k
    curve = coefficients[0] + np.cos(turns) @ a + np.sin(turns) @ b
    velocity = np.cos(turns) @ (w * b) - np.sin(turns) @ (w * a)
    acceleration = -(np.cos(turns) @ (w * w * a) + np.sin(turns) @ (w * w * b))
    return curve, velocity, acceleration, float(np.max(gaps))


def _strokes(y: np.ndarray) -> tuple[float, float]:
    """The release and the attack of a cycle that starts at its hit (``y`` from +1 at index 0 to -1), as shares of
    the cycle: from the last place at or over ``STROKE`` before the far extreme to the first at or under ``-STROKE``,
    and from the last at or under ``-STROKE`` after it to the first at or over ``STROKE`` (the hit closes the cycle)."""
    n = len(y)
    far = int(np.argmin(y))
    high, low = np.flatnonzero(y[: far + 1] >= STROKE), np.flatnonzero(y[far:] <= -STROKE) + far
    r0 = int(high[-1])
    r1 = int(np.flatnonzero(y[r0:] <= -STROKE)[0]) + r0
    a0 = int(low[-1])
    after = np.flatnonzero(y[a0:] >= STROKE)
    a1 = int(after[0]) + a0 if len(after) else n
    return (r1 - r0) / n, (a1 - a0) / n


def _timing(
    curve: np.ndarray, velocity: np.ndarray, acceleration: np.ndarray, side: str, beat: float, period: float
) -> tuple[float, float, float, float, tuple[float, ...]]:
    """The gesture's timing from the hit on ``side``: the place of its fastest moment, its attack and release in
    seconds, its peak acceleration per beat squared in amplitudes, and its velocity profile."""
    sign = 1.0 if side == "max" else -1.0
    half = float(np.ptp(curve)) / 2
    hit = int(np.argmax(sign * curve))
    order = np.roll(np.arange(len(curve)), -hit)
    y = sign * (curve[order] - (float(curve.max()) + float(curve.min())) / 2) / half
    v = sign * velocity[order] * beat / half
    a = sign * acceleration[order] * beat * beat / half
    speed = np.abs(v)
    release, attack = _strokes(y)
    profile = v[:: len(v) // PROFILE_POINTS] / float(speed.max())
    return (
        float(np.argmax(speed)) / len(v),
        attack * period,
        release * period,
        float(np.max(np.abs(a))),
        tuple(float(np.clip(p, -1.0, 1.0)) for p in profile),
    )


def measure_dance(
    series: Sequence[float],
    fps: int,
    groove: Groove,
    *,
    start: float = 0.0,
    hit: str = "snap",
    missing: bool = False,
    harmonics: int = _SHAPE,
) -> DanceReading:
    """A sampled channel's groove against ``groove``; ``series[0]`` is at second ``start``.

    ``hit`` is the extreme to place against the beat: ``max``, ``min``, or ``snap``, where the quicker stroke lands.
    The cost is bounded by ``MAX_SAMPLES``. ``harmonics`` (1..``MAX_HARMONICS``) is how many overtones the final curve
    keeps when the samples can tell them: more read a sharp strike's acceleration closer, and more of a noisy track's
    noise. A flat series, or one under two cycles, raises
    :class:`DanceMeasureError`: a series that does not hold a groove reads as no groove, never as a poor one.

    With ``missing``, a NaN is a sample not seen, as a pose estimator leaves when it loses a dancer (ADR 0200). Nothing
    is filled in: the cycle is found on the series with the gaps at its mean, then fitted, and its shape read, on the
    samples present alone, and ``resolution`` counts the gaps they leave in the cycle."""
    if not isinstance(groove, Groove):
        raise DanceMeasureError(f"a series is read on a music.Groove, not {type(groove).__name__}", path="groove")
    _bad(type(fps) is not int or not 1 <= fps <= 1000, f"fps {fps!r} is a whole number in 1..1000", "fps")
    _bad(not checks.number(start), f"start {start!r} is a finite number of seconds", "start")
    _bad(hit not in ("snap", "max", "min"), f"hit {hit!r} is snap, max or min", "hit")
    _bad(
        type(harmonics) is not int or not 1 <= harmonics <= MAX_HARMONICS,
        f"harmonics {harmonics!r} is a whole number in 1..{MAX_HARMONICS}",
        "harmonics",
    )
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
    curve, velocity, acceleration, gap = _curve(x, times, hz, harmonics)
    low, high = int(np.argmin(curve)) / _GRID, int(np.argmax(curve)) / _GRID
    period = 1 / hz
    rise = (high - low) % 1.0 * period
    fall = period - rise
    side = hit if hit != "snap" else ("max" if rise < fall else "min")
    place = (high if side == "max" else low) * period / groove.beat
    timing = _timing(curve, velocity, acceleration, side, groove.beat, period)
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
        *timing,
    )

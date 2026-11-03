"""Bounded target gaze on one performance clock, independent of drawing or camera cuts.

Coordinates share a fixed observer frame: X right, Y down, Z forward, in one
caller-selected unit. Tracks may translate the observer; rotating frames must
be resolved by the caller. Limits and latency are authored animation controls,
not physiological claims. The compiled plan is piecewise linear at its declared
sample grid; target easing is evaluated before that bounded approximation.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass, field, fields
from functools import cached_property
from typing import Literal

from . import checks
from ._curves import progress
from .errors import SrstudioError
from .head_motion import GAZES
from .held_keys import held_key

MAX_KEYS = 1000
MAX_SAMPLES = 20000


class GazeError(SrstudioError, ValueError):
    """Invalid, unsupported or out-of-envelope target gaze, before scene mutation."""


def _fail(path: str, actual: object, expected: object, code: str = 'gaze.input') -> GazeError:
    return GazeError(
        f'{path}: expected {expected}',
        code=code,
        path=path,
        actual=actual,
        expected=expected,
        remedy='Use bounded typed gaze records, one performance clock and a rig with the requested capability.',
    )


def _number(value: object, path: str, low: float, high: float) -> None:
    if not checks.number(value) or not low <= value <= high:
        raise _fail(path, value, f'a finite number in {low}..{high}, excluding booleans')


@dataclass(frozen=True)
class TargetKey:
    time: float
    point: tuple[float, float, float]

    def __post_init__(self) -> None:
        _number(self.time, 'target.time', 0, 600)
        if type(self.point) is not tuple or len(self.point) != 3:
            raise _fail('target.point', self.point, 'an immutable coordinate triple')
        for i, value in enumerate(self.point):
            _number(value, f'target.point[{i}]', -1e6, 1e6)


@dataclass(frozen=True)
class TargetTrack:
    keys: tuple[TargetKey, ...]
    curve: Literal['linear', 'sine-in-out'] = 'sine-in-out'

    def __post_init__(self) -> None:
        if type(self.keys) is not tuple or not 1 <= len(self.keys) <= MAX_KEYS:
            raise _fail('target.keys', None, f'1..{MAX_KEYS} immutable TargetKeys')
        previous = -1.0
        for key in self.keys:
            if type(key) is not TargetKey or round(key.time, 6) <= previous:
                raise _fail('target.keys', None, 'TargetKeys increasing at microsecond clock precision')
            previous = round(key.time, 6)
        if self.keys[0].time != 0 or self.curve not in ('linear', 'sine-in-out'):
            raise _fail('target', None, 'a track starting at zero, with linear or sine-in-out interpolation')

    @cached_property
    def _times(self) -> tuple[float, ...]:
        return tuple(key.time for key in self.keys)

    def sample(self, time: float) -> tuple[float, float, float]:
        """Interpolate, holding endpoints before/after the authored track for latency."""
        _number(time, 'target.sample', -600, 600)
        if time <= 0:
            return self.keys[0].point
        i = bisect_right(self._times, time) - 1
        if i == len(self.keys) - 1:
            return self.keys[i].point
        a, b = self.keys[i : i + 2]
        u = progress(self.curve, (time - a.time) / (b.time - a.time))
        return tuple(x + (y - x) * u for x, y in zip(a.point, b.point, strict=True))  # type: ignore[return-value]


@dataclass(frozen=True)
class GazeLimits:
    """Eye/head yaw and pitch in degrees; independent target latencies in seconds."""

    eye_yaw: float = 25
    eye_pitch: float = 20
    head_yaw: float = 35
    head_pitch: float = 25
    head_share: float = 0.4
    eye_latency: float = 0.03
    head_latency: float = 0.15

    def __post_init__(self) -> None:
        for name in ('eye_yaw', 'eye_pitch', 'head_yaw', 'head_pitch'):
            _number(getattr(self, name), f'limits.{name}', 0.001, 80)
        _number(self.head_share, 'limits.head_share', 0, 1)
        _number(self.eye_latency, 'limits.eye_latency', 0, 5)
        _number(self.head_latency, 'limits.head_latency', self.eye_latency, 5)


_ORIGIN = TargetTrack((TargetKey(0, (0, 0, 0)),))


@dataclass(frozen=True)
class GazeSpec:
    target: TargetTrack
    duration: float
    observer: TargetTrack = _ORIGIN
    limits: GazeLimits = GazeLimits()
    fps: int = 60
    max_samples: int = MAX_SAMPLES

    def __post_init__(self) -> None:
        _number(self.duration, 'duration', 1e-6, 600)
        if round(self.duration, 6) != self.duration:
            raise _fail('duration', self.duration, 'seconds representable at microsecond precision')
        if (
            type(self.target) is not TargetTrack
            or type(self.observer) is not TargetTrack
            or type(self.limits) is not GazeLimits
        ):
            raise _fail('spec', None, 'typed TargetTrack and GazeLimits records')
        for name, high in (('fps', 120), ('max_samples', MAX_SAMPLES)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= high:
                raise _fail(name, value, f'an integer in 1..{high}')
        if any(track.keys[-1].time > self.duration for track in (self.target, self.observer)):
            raise _fail('target.keys', None, 'all keys inside the performance duration')


@dataclass(frozen=True)
class GazeSample:
    time: float
    eye_yaw: float
    eye_pitch: float
    head_yaw: float
    head_pitch: float

    @property
    def values(self) -> tuple[float, float, float, float]:
        return self.eye_yaw, self.eye_pitch, self.head_yaw, self.head_pitch


def _angles(spec: GazeSpec, time: float) -> tuple[float, float]:
    target, origin = spec.target.sample(time), spec.observer.sample(time)
    x, y, z = (a - b for a, b in zip(target, origin, strict=True))
    if z <= 1e-9:
        raise _fail(
            'target', {'time': time, 'relative': (x, y, z)}, 'a target strictly in front of the observer', 'gaze.target'
        )
    return math.degrees(math.atan2(x, z)), math.degrees(math.atan2(y, math.hypot(x, z)))


def _compile(spec: GazeSpec) -> tuple[GazeSample, ...]:
    count = math.ceil(spec.duration * spec.fps)
    limits = spec.limits
    # The conservative sum is checked before allocating either timeline.
    bound = count + 1 + 2 * (len(spec.target.keys) + len(spec.observer.keys))
    if bound > spec.max_samples:
        raise _fail('max_samples', bound, f'at most {spec.max_samples} planned samples', 'gaze.budget')
    times = {round(i / spec.fps, 6) for i in range(count) if i / spec.fps < spec.duration}
    times.add(spec.duration)
    for track in (spec.target, spec.observer):
        for key in track.keys:
            for delay in (limits.eye_latency, limits.head_latency):
                if 0 <= key.time + delay <= spec.duration:
                    times.add(round(key.time + delay, 6))
    samples = []
    for time in sorted(times):
        wanted = _angles(spec, time - limits.eye_latency)
        head = tuple(value * limits.head_share for value in _angles(spec, time - limits.head_latency))
        values = (wanted[0] - head[0], wanted[1] - head[1], *head)
        for name, value in zip(('eye_yaw', 'eye_pitch', 'head_yaw', 'head_pitch'), values, strict=True):
            allowed = getattr(limits, name)
            if abs(value) > allowed + 1e-9:
                raise _fail(name, {'time': time, 'value': value}, f'within +/-{allowed} degrees', 'gaze.bounds')
        samples.append(GazeSample(time, *values))
    return tuple(samples)


@dataclass(frozen=True)
class GazePlan:
    spec: GazeSpec
    samples: tuple[GazeSample, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.spec) is not GazeSpec:
            raise _fail('spec', self.spec, 'a GazeSpec')
        object.__setattr__(self, 'samples', _compile(self.spec))

    @cached_property
    def _times(self) -> tuple[float, ...]:
        return tuple(sample.time for sample in self.samples)

    def sample(self, time: float) -> GazeSample:
        _number(time, 'sample.time', 0, self.spec.duration)
        i = bisect_right(self._times, time) - 1
        if i == len(self.samples) - 1:
            return self.samples[i]
        a, b = self.samples[i : i + 2]
        u = (time - a.time) / (b.time - a.time)
        return GazeSample(time, *(x + (y - x) * u for x, y in zip(a.values, b.values, strict=True)))

    def window(self, start: float, end: float) -> GazeWindow:
        return GazeWindow(self, start, end)

    def describe(self) -> dict:
        return {
            'schema': 'srstudio.gaze-plan/1.0.0',
            'clock': 'performance seconds',
            'coordinates': 'fixed observer frame: X right, Y down, Z forward; common caller-selected units',
            'duration': self.spec.duration,
            'fps': self.spec.fps,
            'samples': len(self.samples),
            'interpolation': 'linear compiled angles; authored target easing sampled before compilation',
            'limits': {f.name: getattr(self.spec.limits, f.name) for f in fields(GazeLimits)},
        }


@dataclass(frozen=True)
class GazeWindow:
    plan: GazePlan
    start: float
    end: float

    def __post_init__(self) -> None:
        if type(self.plan) is not GazePlan:
            raise _fail('window.plan', None, 'a GazePlan')
        _number(self.start, 'window.start', 0, self.plan.spec.duration)
        _number(self.end, 'window.end', 0, self.plan.spec.duration)
        if self.end <= self.start:
            raise _fail('window', (self.start, self.end), 'a positive interval inside the performance')

    def sample(self, time: float) -> GazeSample:
        _number(time, 'window.time', 0, self.end - self.start)
        return self.plan.sample(min(self.plan.spec.duration, self.start + time))


@dataclass(frozen=True)
class NamedGazeMapping:
    """Explicit approximation to named eye offsets, with a maximum error in eye radii."""

    states: tuple[str, ...]
    max_error: float

    def __post_init__(self) -> None:
        if (
            type(self.states) is not tuple
            or not 1 <= len(self.states) <= len(GAZES)
            or any(type(name) is not str or name not in GAZES for name in self.states)
            or len(set(self.states)) != len(self.states)
        ):
            raise _fail('mapping.states', self.states, 'distinct supported named gaze states')
        _number(self.max_error, 'mapping.max_error', 0, 2)


def eye_offset(plan: GazePlan, sample: GazeSample) -> tuple[float, float]:
    """Stylized Toon offsets in eye radii; angular limits map to +/-0.42 X and +/-0.3 Y."""
    return sample.eye_yaw / plan.spec.limits.eye_yaw * 0.42, sample.eye_pitch / plan.spec.limits.eye_pitch * 0.3


def named_gaze(plan: GazePlan, mapping: NamedGazeMapping) -> tuple[tuple[float, str], ...]:
    if type(plan) is not GazePlan or type(mapping) is not NamedGazeMapping:
        raise _fail('mapping', None, 'a GazePlan and explicit NamedGazeMapping')
    result: list[tuple[float, str]] = []
    for i, sample in enumerate(plan.samples):
        point = eye_offset(plan, sample)
        name = min(mapping.states, key=lambda name: math.dist(point, GAZES[name]))
        following = eye_offset(plan, plan.samples[min(i + 1, len(plan.samples) - 1)])
        error = max(math.dist(p, GAZES[name]) for p in (point, following))
        if error > mapping.max_error + 1e-9:
            raise _fail(
                'mapping',
                {'time': sample.time, 'error': error},
                f'error <= {mapping.max_error} eye radii',
                'gaze.mapping',
            )
        # A held eye state is keyed half a frame before the frame that first shows it; of two changes before one
        # frame, the frame shows the later (ADR 0216).
        at = held_key(sample.time, plan.spec.fps)
        if result and result[-1][0] == at:
            result.pop()
        if not result or name != result[-1][1]:
            result.append((at, name))
    return tuple(result)


def _record(value: object, required: set[str], optional: set[str], path: str) -> dict:
    if (
        type(value) is not dict
        or len(value) > len(required | optional)
        or not required <= value.keys() <= required | optional
    ):
        raise _fail(path, None, f'a closed object with required {sorted(required)} and optional {sorted(optional)}')
    return value


def _track(value: object, path: str) -> TargetTrack:
    data = _record(value, {'keys'}, {'curve'}, path)
    keys = data['keys']
    if type(keys) is not list or not 1 <= len(keys) <= MAX_KEYS:
        raise _fail(path + '.keys', None, f'a list of 1..{MAX_KEYS} keys')
    result = []
    for key in keys:
        row = _record(key, {'time', 'point'}, set(), path + '.key')
        point = row['point']
        if type(point) is not list or len(point) != 3:
            raise _fail(path + '.point', None, 'a list of three coordinates')
        result.append(TargetKey(row['time'], tuple(point)))
    return TargetTrack(tuple(result), data.get('curve', 'sine-in-out'))


def parse_gaze(value: object) -> GazeSpec:
    """Parse a closed JSON-compatible object without primitive coercion or callbacks."""
    data = _record(value, {'target', 'duration'}, {'observer', 'limits', 'fps', 'max_samples'}, 'gaze')
    limits = _record(data.get('limits', {}), set(), {f.name for f in fields(GazeLimits)}, 'limits')
    return GazeSpec(
        _track(data['target'], 'target'),
        data['duration'],
        _track(data['observer'], 'observer') if 'observer' in data else _ORIGIN,
        GazeLimits(**limits),
        data.get('fps', 60),
        data.get('max_samples', MAX_SAMPLES),
    )

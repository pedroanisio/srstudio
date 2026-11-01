"""Head-channel interpolation, spring baking and numeric envelopes.

The public API is re-exported by head_motion. This layer depends on shared curve
math and diagnostics, never speech, behavioral planning or character drawings.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import TypeAlias

from . import checks
from ._curves import progress, spline_coefficients, spring_response
from .errors import SrstudioError, _brief

Key: TypeAlias = tuple[float, float]


SPRING_RUN = 8  # longer carried chains are sampled to bound renderer work


_BOUNDED_CURVES = frozenset(
    {
        'linear',
        'hold',
        'step',
        'steps',
        'ease-in',
        'ease-out',
        'ease-in-out',
        'cubic-bezier',
        *(
            f'{family}-{direction}'
            for family in ('sine', 'quad', 'cubic', 'quart', 'quint', 'expo', 'circ', 'bounce')
            for direction in ('in', 'out', 'in-out')
        ),
    }
)


_CURVES = (
    _BOUNDED_CURVES
    | {'catmull-rom', 'tcb', 'spring'}
    | {f'{family}-{direction}' for family in ('back', 'elastic') for direction in ('in', 'out', 'in-out')}
)


class HeadMotionError(SrstudioError, ValueError):
    """Head motion was asked for something it cannot do; the message names what."""


def _invalid(
    code: str, path: str, actual: object, expected: object, remedy: str, message: str | None = None
) -> HeadMotionError:
    return HeadMotionError(
        message or f'{path}: expected {expected}; got {_brief(actual)}',
        code=code,
        path=path,
        actual=actual,
        expected=expected,
        remedy=remedy,
    )


def _precision(actual: object) -> HeadMotionError:
    return _invalid(
        'head.channel.precision',
        'channel.keys',
        actual,
        'distinct times after rounding to six decimals',
        'Space keys farther apart or use a local clock nearer zero.',
        'channel keys exceed the scene clock resolution',
    )


def _budget(actual: object) -> HeadMotionError:
    return _invalid(
        'head.channel.budget',
        'channel.spring',
        actual,
        {'maximum_sampled_keys': 100000},
        'Reduce spring frequency, key count or duration; compile shorter bounded performances.',
        'carried spring exceeds the 100000-key sampling budget',
    )


def _finite(*values: float) -> bool:
    return all(checks.number(v) for v in values)


@dataclass(frozen=True)
class Spring:
    """A spring by its feel: ``frequency`` in Hz, ``damping`` as a ratio (under 1 overshoots, 1 settles without) and
    ``anticipation``, the share of a move taken the other way first."""

    frequency: float
    damping: float
    anticipation: float = 0.0

    def __post_init__(self) -> None:
        for name in ('frequency', 'damping', 'anticipation'):
            value = getattr(self, name)
            if not checks.number(value):
                raise _invalid(
                    'head.spring.number',
                    f'spring.{name}',
                    value,
                    'a finite number, excluding booleans',
                    'Supply a numeric frequency in Hz, damping ratio or anticipation fraction.',
                )
        for name, valid, expected in (
            ('frequency', self.frequency > 0, {'exclusive_minimum': 0, 'unit': 'Hz'}),
            ('damping', 0 < self.damping <= 2, {'exclusive_minimum': 0, 'maximum': 2}),
            ('anticipation', 0 <= self.anticipation <= 0.5, {'minimum': 0, 'maximum': 0.5}),
        ):
            if not valid:
                raise _invalid(
                    'head.spring.range',
                    f'spring.{name}',
                    getattr(self, name),
                    expected,
                    'Choose a value inside the reported spring parameter bounds.',
                )

    @property
    def stiffness(self) -> float:
        return (2.0 * math.pi * self.frequency) ** 2

    @property
    def friction(self) -> float:
        return 2.0 * self.damping * 2.0 * math.pi * self.frequency

    def attributes(self) -> dict[str, str]:
        """The key attributes of the engine's ``spring`` curve, at a mass of 1."""
        return {"stiffness": f"{self.stiffness:.4f}", "damping": f"{self.friction:.4f}", "mass": "1"}


@dataclass(frozen=True)
class Channel:
    """One moving value: ``(project second, value)`` keys on a :class:`Spring`, or on an engine ``curve``."""

    keys: tuple[Key, ...] = ()
    spring: Spring | None = None
    curve: str = "linear"

    def __post_init__(self) -> None:
        if not isinstance(self.curve, str) or self.curve not in _CURVES:
            raise _invalid(
                'head.channel.curve',
                'channel.curve',
                self.curve,
                sorted(_CURVES),
                'Choose a supported interpolation name; supply Spring parameters separately.',
            )
        if self.spring is not None and not isinstance(self.spring, Spring):
            raise _invalid(
                'head.channel.spring',
                'channel.spring',
                self.spring,
                'Spring or None',
                'Construct Spring(frequency, damping) or omit it to use the named curve.',
            )
        if not isinstance(self.keys, tuple):
            raise _invalid(
                'head.channel.keys',
                'channel.keys',
                self.keys,
                'a tuple of (second, value) tuples',
                'Provide immutable key pairs; an empty tuple holds zero.',
            )
        previous = -math.inf
        for i, row in enumerate(self.keys):
            path = f'channel.keys[{i}]'
            if not isinstance(row, tuple) or len(row) != 2:
                raise _invalid(
                    'head.channel.keys',
                    path,
                    row,
                    'a (second, value) tuple',
                    'Give each key exactly one time and one numeric value.',
                )
            for j, value in enumerate(row):
                if not checks.number(value):
                    raise _invalid(
                        'head.channel.number',
                        f'{path}[{j}]',
                        value,
                        'a finite number, excluding booleans',
                        'Use numeric seconds and channel values; remove nonfinite values.',
                    )
            if row[0] <= previous:
                raise _invalid(
                    'head.channel.order',
                    path + '[0]',
                    row[0],
                    {'greater_than': previous},
                    'Order keys by strictly increasing time; resolve duplicate times explicitly.',
                )
            previous = row[0]

    def sample(self, time: float) -> float:
        """Value in project seconds, matching emitted key precision, easing and carried spring history.

        Empty channels return zero; times outside the keys hold the nearest value. Long spring chains use the
        same bounded bake as emission. Preparation is cached with a bounded cache; sampling order has no effect.
        """
        if not _finite(time):
            raise _invalid(
                'head.channel.sample',
                'channel.sample.time',
                time,
                'a finite second',
                'Sample the channel at a finite numeric time.',
            )
        channel = _sampling_channel(self)
        keys = channel.keys
        if not keys:
            return 0.0
        if time <= keys[0][0]:
            return keys[0][1]
        if time >= keys[-1][0]:
            return keys[-1][1]
        index = bisect_right(keys, (time, math.inf)) - 1
        start, a = keys[index]
        end, b = keys[index + 1]
        u = (time - start) / (end - start)
        if channel.spring is not None or channel.curve == 'spring':
            spring = channel.spring
            attrs = spring.attributes() if spring else {'stiffness': '100', 'damping': '10'}
            w = math.sqrt(max(float(attrs['stiffness']), 1e-9))
            z = max(float(attrs['damping']), 0.0) / (2 * w)
            velocity = 0.0
            for i in range(index + 1):
                start, a = keys[i]
                end, b = keys[i + 1]
                span = end - start
                step, release = spring_response(span, w, z)
                tail = (a - b) * (1 - step) + velocity * release

                h = max(1e-9, min(1e-3, 0.1 * span))
                elapsed = time - start if i == index else span - h
                step, release = spring_response(elapsed, w, z)
                value = b + (a - b) * (1 - step) + velocity * release - tail * elapsed / span
                if i == index:
                    return value
                velocity = (b - value) / h if spring else 0.0
        if channel.curve in ('catmull-rom', 'tcb'):
            c3, c2, c1, c0 = _sampling_splines(keys)[index]
            return ((c3 * u + c2) * u + c1) * u + c0
        return a + (b - a) * progress(channel.curve, u)

    def during(self, start: float, end: float) -> Channel:
        """Keep the shot's keys and the curve history needed to preserve its value and tangent at cuts.

        Short carried springs keep their history; long ones are sampled. Both spline modes keep two neighbors per side.
        """
        if self.spring and len(self.keys) > SPRING_RUN:
            baked = _bake_spring(self)
            before = [key for key in baked.keys if key[0] <= start][-4:]
            inside = [key for key in baked.keys if start < key[0] < end]
            after = [key for key in baked.keys if key[0] >= end][:4]
            return replace(baked, keys=(*before, *inside, *after))
        previous = [i for i, key in enumerate(self.keys) if key[0] <= start]
        if self.spring and previous:
            before = list(self.keys[: previous[-1] + 1])
        elif self.curve in ("catmull-rom", "tcb"):
            before = [self.keys[i] for i in previous[-2:]]
        else:
            before = [self.keys[i] for i in previous[-1:]]
        inside = [key for key in self.keys if start < key[0] < end]
        after = [key for key in self.keys if key[0] >= end][: 2 if self.curve in ("catmull-rom", "tcb") else 1]
        return replace(self, keys=(*before, *inside, *after))


@lru_cache(maxsize=64)
def _sampling_channel(channel: Channel) -> Channel:
    channel = _bake_spring(channel)
    keys = tuple((round(t, 6), round(v, 4)) for t, v in channel.keys)
    if any(b[0] <= a[0] for a, b in zip(keys, keys[1:], strict=False)):
        raise _precision(channel.keys)
    return replace(channel, keys=keys)


@lru_cache(maxsize=64)
def _sampling_splines(keys: tuple[Key, ...]) -> tuple[tuple[float, float, float, float], ...]:
    return spline_coefficients(keys)


def _bake_spring(channel: Channel) -> Channel:
    """Sample the renderer's carried spring in linear time, avoiding recursive carry chains."""
    if channel.spring is None or len(channel.keys) <= SPRING_RUN:
        return channel
    return _sample_spring(channel)[0]


def _sample_spring(channel: Channel, *, carry: bool = True) -> tuple[Channel, tuple[float, float]]:
    """Sample carried motion and conservatively bound the continuous curve between samples.

    On each interval, linear-interpolation error is at most max(abs(second derivative)) * step² / 8.
    The spring's homogeneous response gives a global curvature bound; its endpoint correction is linear.
    """
    spring = channel.spring
    assert spring is not None
    if len(channel.keys) < 2:
        held = round(channel.keys[0][1], 4) if channel.keys else 0.0
        return channel, (held, held)
    if spring.frequency > 10000 / 32:
        raise _budget({'frequency': spring.frequency})
    attrs = spring.attributes()
    stiffness, damping = max(float(attrs["stiffness"]), 1e-9), max(float(attrs["damping"]), 0.0)
    w = math.sqrt(stiffness)
    z = damping / (2 * w)
    rate = max(240, math.ceil(spring.frequency * 32))
    spans = tuple(b[0] - a[0] for a, b in zip(channel.keys, channel.keys[1:], strict=False))
    if (
        rate > 10000
        or any(span > 100000 / rate for span in spans)
        or 1 + sum(math.ceil((b[0] - a[0]) * rate) for a, b in zip(channel.keys, channel.keys[1:], strict=False))
        > 100000
    ):
        raise _budget({'sample_rate': rate, 'key_count': len(channel.keys), 'spans': spans})

    def responses(t: float) -> tuple[float, float]:
        return spring_response(t, w, z)

    def value(t: float, a: float, b: float, velocity: float, tail: float, span: float) -> float:
        step, release = responses(t)
        return b + (a - b) * (1 - step) + velocity * release - tail * t / span

    def curvature(a: float, b: float, velocity: float) -> float:
        # Homogeneous energy v² + w²*y² decreases under nonnegative damping. Therefore both |v| and
        # w*|y| are bounded by the initial energy norm, and |y''| <= 2*z*w*|v| + w²*|y|.
        # This stays well conditioned even when the two overdamped roots nearly coincide.
        return w * (2 * z + 1) * math.hypot(velocity, w * (a - b))

    keys: list[Key] = []
    velocity = 0.0
    low, high = math.inf, -math.inf
    for (start, av), (end, bv) in zip(channel.keys, channel.keys[1:], strict=False):
        a, b = round(av, 4), round(bv, 4)
        span = end - start
        step_end, release_end = responses(span)
        tail = (a - b) * (1 - step_end) + velocity * release_end

        count = math.ceil(span * rate)
        margin = curvature(a, b, velocity) * (span / count) ** 2 / 8
        segment_low, segment_high = b, b
        for i in range(count):
            t = round(start + span * i / count, 6)
            if keys and t <= keys[-1][0]:
                raise _precision((start, end))
            sampled = value(span * i / count, a, b, velocity, tail, span)
            segment_low, segment_high = min(segment_low, sampled), max(segment_high, sampled)
            keys.append((t, round(sampled, 6)))
        low, high = min(low, segment_low - margin), max(high, segment_high + margin)
        h = max(1e-9, min(1e-3, 0.1 * span))
        velocity = (b - value(span - h, a, b, velocity, tail, span)) / h if carry else 0.0
    keys.append((round(channel.keys[-1][0], 6), round(channel.keys[-1][1], 4)))
    if len(keys) > 1 and keys[-1][0] <= keys[-2][0]:
        raise _precision(channel.keys[-2:])
    return Channel(tuple(keys), curve="linear"), (low, high)


def _spline_extrema(keys: tuple[Key, ...]) -> list[float]:
    """Exact cubic extrema with sr-eval/channel.rs's nonuniform Catmull-Rom/default TCB tangents."""
    extrema: list[float] = []
    for a, b, c, start in spline_coefficients(keys):
        if a == 0:
            roots = [-c / (2 * b)] if b else []
        else:
            discriminant = 4 * b * b - 12 * a * c
            q = -b - math.copysign(math.sqrt(max(0.0, discriminant)) / 2, b)
            roots = [q / (3 * a), c / q] if discriminant >= 0 and q else []
        extrema.extend(((a * u + b) * u + c) * u + start for u in roots if 0 < u < 1)
    return extrema


def _easing_range(curve: str) -> tuple[float, float]:
    """Continuous progress extrema for the engine's default back/elastic curves, including both endpoints."""
    family, direction = curve.split('-', 1)
    if family == 'back':
        c = 1.70158 * (1.525 if direction == 'in-out' else 1)
        overshoot = 4 * c**3 / (27 * (c + 1) ** 2)
    else:
        # For elastic-out: 1 - exp(-a*u)*cos(w*u). Its extrema satisfy tan(w*u) = -a/w.
        # Elastic-in is its reflection; in-out uses half the excursion and period 0.45.
        a, w = 10 * math.log(2), 2 * math.pi / (0.45 if direction == 'in-out' else 0.3)
        first = (math.pi - math.atan(a / w)) / w
        overshoot = -math.exp(-a * first) * math.cos(w * first)
    if direction == 'in':
        return -overshoot, 1.0
    if direction == 'out':
        return 0.0, 1 + overshoot
    return -overshoot / 2, 1 + overshoot / 2


def _channel_bounds(channel: Channel) -> tuple[float, float]:
    """Bound the emitted curve, including interior extrema, without changing its interpolation."""
    keys = tuple((round(t, 6), round(v, 4)) for t, v in channel.keys)
    if any(b[0] <= a[0] for a, b in zip(keys, keys[1:], strict=False)):
        raise _precision(channel.keys)
    values = [v for _, v in keys]
    if len(keys) < 2:
        return min(values), max(values)
    if channel.spring is not None:
        if len(keys) > SPRING_RUN:
            baked, _ = _sample_spring(channel)
            return min(v for _, v in baked.keys), max(v for _, v in baked.keys)
        return _sample_spring(replace(channel, keys=keys))[1]
    if channel.curve == 'spring':
        # A bare engine spring has k=100, c=10, m=1 and no carried velocity.
        return _sample_spring(Channel(keys, Spring(10 / (2 * math.pi), 0.5)), carry=False)[1]
    if channel.curve in ('catmull-rom', 'tcb'):
        values.extend(_spline_extrema(keys))
    elif channel.curve not in _BOUNDED_CURVES:
        low, high = _easing_range(channel.curve)
        values.extend(a + (b - a) * u for (_, a), (_, b) in zip(keys, keys[1:], strict=False) for u in (low, high))
    return min(values), max(values)

"""Intent-based scalar source curves and bounded, explicitly sampled emission."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .canvas import Canvas
from .errors import SrstudioError
from .head_motion import Channel
from .limbs.math3d import Frame, Vec3
from .limbs.motion import TransformKey, TransformTrack

INTENTS = ('stop-smoothly', 'pass-through', 'intentional-impact')


class CurveError(SrstudioError, ValueError):
    """A curve intent, clock or emission budget cannot be honored."""


def _fail(path, actual, expected):
    return CurveError(
        f'{path}: expected {expected}',
        code='curve.input',
        path=path,
        actual=actual,
        expected=expected,
        remedy='Choose a discovered intent and bounded increasing local seconds.',
    )


def describe(intent: str) -> dict:
    if intent not in INTENTS:
        raise _fail('intent', intent, list(INTENTS))
    continuous = intent != 'intentional-impact'
    return {
        'schema': 'srstudio.curve-intent/1.0.0',
        'intent': intent,
        'source': {'position': True, 'velocity': continuous, 'acceleration': continuous},
        'interior_keys': 'zero velocity and acceleration'
        if intent == 'stop-smoothly'
        else 'shared velocity, zero acceleration'
        if intent == 'pass-through'
        else 'cubic-in arrival; deliberate velocity jump',
        'endpoint_holds': 'zero velocity and acceleration' if continuous else 'velocity jumps on arrival',
        'emission': {'sampling': 'linear', 'inherits_source_derivatives': False},
        'scope': 'scalar source only; geometry, constraints, projection and raster quality are separate',
    }


@dataclass(frozen=True)
class CurveTrack:
    keys: tuple[tuple[float, float], ...]
    intent: str
    _source: TransformTrack | Channel

    def describe(self) -> dict:
        return describe(self.intent)

    def sample(self, time: float) -> float:
        if isinstance(self._source, Channel):
            return self._source.sample(time)
        return self._source.sample(time).origin.x

    def emit(self, cv: Canvas, node, prop: str, *, fps: int = 24, max_keys: int = 20000) -> dict:
        """Emit linear samples on the canvas clock; source derivative guarantees do not survive baking."""
        if type(fps) is not int or not 1 <= fps <= 120:
            raise _fail('fps', fps, 'integer in 1..120')
        if type(max_keys) is not int or not 1 <= max_keys <= 100000:
            raise _fail('max_keys', max_keys, 'integer in 1..100000')
        start, end = self.keys[0][0], self.keys[-1][0]
        count = math.ceil((end - start) * fps)
        if count > max_keys:
            raise _fail('max_keys', max_keys, 'enough keys for the interval and authored events')
        times = sorted({*(start + i / fps for i in range(count)), *(t for t, _ in self.keys)})
        if len(times) > max_keys or len({round(t, 6) for t in times}) != len(times):
            raise _fail('keys', len(times), 'distinct microsecond times within max_keys')
        cv.keys(node, prop, [(t, self.sample(t)) for t in times], kind='linear')
        return {'keys': len(times), 'fps': fps, 'interpolation': 'linear', 'inherits_source_derivatives': False}


def track(keys: Sequence[Sequence[float]], *, intent: str = 'stop-smoothly') -> CurveTrack:
    """Construct a scalar source curve. Endpoints hold; pass-through may overshoot between uneven keys."""
    describe(intent)
    if not isinstance(keys, (list, tuple)) or not 1 <= len(keys) <= 10000:
        raise _fail('keys', None, '1..10000 ordered key pairs')
    if any(not isinstance(key, (tuple, list)) or len(key) != 2 for key in keys):
        raise _fail('keys', None, 'pairs of finite seconds and values')
    frozen = tuple((key[0], key[1]) for key in keys)
    try:
        Channel(frozen)
    except SrstudioError as exc:
        detail = exc.to_dict()
        raise _fail((detail['path'] or 'keys').removeprefix('channel.'), detail['actual'], detail['expected']) from exc
    if frozen[0][0] < 0 or frozen[-1][0] > 600:
        raise _fail('keys', None, '1..10000 ordered keys in local seconds 0..600')
    source: Channel | TransformTrack
    if intent == 'intentional-impact':
        source = Channel(frozen, curve='cubic-in')
    else:
        source = TransformTrack(
            tuple(TransformKey(t, Frame(Vec3(v, 0, 0))) for t, v in frozen),
            interpolation='smooth' if intent == 'stop-smoothly' else 'continuous',
        )
    return CurveTrack(frozen, intent, source)

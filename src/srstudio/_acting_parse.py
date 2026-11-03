"""Strict bounded decoding of the data-only acting score; runtime overrides bind separately."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from . import checks
from .acting import (
    ActingBeat,
    ActingScore,
    ChannelTiming,
    Expression,
    HeadTarget,
    Overrides,
    SpokenLine,
    TransitionPolicy,
    _error,
)
from .head_motion import Spring
from .voice import Alignment

SCHEMA = 'srstudio.acting/1.0.0'
POLICY_SCHEMA = 'srstudio.acting/1.1.0'
BLEND_SCHEMA = 'srstudio.acting/1.2.0'


def _object(value: object, path: str, allowed: set[str], required: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise _error(path, value, 'an object with named fields')
    if set(value) - allowed or (required or set()) - set(value):
        raise _error(path, list(value), {'allowed': sorted(allowed), 'required': sorted(required or ())})
    return value


def _array(value: object, path: str, limit: int = 1000) -> list[Any]:
    if not isinstance(value, list) or len(value) > limit:
        raise _error(path, value, f'an array with at most {limit} items')
    return value


def _number(value: object, path: str) -> float:
    if not checks.number(value):
        raise _error(path, value, 'a finite number, excluding booleans')
    return float(value)


def _name(value: object, path: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise _error(path, value, 'a name of 1..128 characters')
    return value


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        raise _error(path, value, 'a boolean')
    return value


def _policy(value: object, path: str) -> TransitionPolicy:
    data = _object(value, path, {f.name for f in fields(TransitionPolicy)}, {'version'})
    kwargs: dict[str, Any] = {'version': _name(data['version'], path + '.version')}
    if 'curve' in data:
        kwargs['curve'] = _name(data['curve'], path + '.curve')
    for name in ('anticipation', 'anticipation_amount', 'settle', 'overshoot'):
        if name in data:
            kwargs[name] = _number(data[name], f'{path}.{name}')
    if data.get('spring') is not None:
        spring = _object(data['spring'], path + '.spring', {'frequency', 'damping'}, {'frequency', 'damping'})
        frequency = _number(spring['frequency'], path + '.spring.frequency')
        damping = _number(spring['damping'], path + '.spring.damping')
        if not 0.1 <= frequency <= 20 or not 0.1 <= damping <= 2:
            raise _error(path + '.spring', spring, 'frequency 0.1..20 Hz and damping 0.1..2')
        kwargs['spring'] = Spring(frequency, damping)
    timings = []
    for i, row in enumerate(_array(data.get('timing', []), path + '.timing', 11)):
        where = f'{path}.timing[{i}]'
        timing = _object(row, where, {'channel', 'delay', 'duration'}, {'channel'})
        timings.append(
            ChannelTiming(
                _name(timing['channel'], where + '.channel'),
                _number(timing.get('delay', 0), where + '.delay'),
                _number(timing['duration'], where + '.duration') if timing.get('duration') is not None else None,
            )
        )
    kwargs['timing'] = tuple(timings)
    return TransitionPolicy(**kwargs)


def _beat(value: object, path: str, policy_enabled: bool, blend_enabled: bool) -> ActingBeat:
    allowed = {f.name for f in fields(ActingBeat)} - (set() if policy_enabled else {'policy'})
    if not blend_enabled:
        allowed -= {'blend'}
    data = _object(value, path, allowed, {'at'})
    kwargs: dict[str, Any] = {'at': _number(data['at'], path + '.at')}
    for name in ('emotion', 'gaze', 'gesture'):
        if data.get(name) is not None:
            kwargs[name] = _name(data[name], f'{path}.{name}')
    for name in ('transition', 'breath'):
        if name in data and (name == 'transition' or data[name] is not None):
            kwargs[name] = _number(data[name], f'{path}.{name}')
    if 'reset' in data:
        kwargs['reset'] = _boolean(data['reset'], path + '.reset')
    if 'blend' in data:
        kwargs['blend'] = _boolean(data['blend'], path + '.blend')
    if data.get('expression') is not None:
        expression = _object(data['expression'], path + '.expression', {'eyes', 'mouth'}, {'eyes'})
        kwargs['expression'] = Expression(
            _name(expression['eyes'], path + '.expression.eyes'),
            _name(expression['mouth'], path + '.expression.mouth') if expression.get('mouth') is not None else None,
        )
    if data.get('head') is not None:
        head = _object(data['head'], path + '.head', {f.name for f in fields(HeadTarget)})
        kwargs['head'] = HeadTarget(**{k: _number(v, f'{path}.head.{k}') for k, v in head.items() if v is not None})
    if data.get('policy') is not None:
        kwargs['policy'] = _policy(data['policy'], path + '.policy')
    return ActingBeat(**kwargs)


def _line(value: object, path: str) -> SpokenLine:
    data = _object(value, path, {'at', 'alignment', 'levels'}, {'at', 'alignment', 'levels'})
    alignment = _object(data['alignment'], path + '.alignment', set(Alignment.FIELDS), set(Alignment.FIELDS))
    for name in Alignment.FIELDS:
        _array(alignment[name], f'{path}.alignment.{name}', 20_000)
    levels = _array(data['levels'], path + '.levels', 60_000)
    return SpokenLine(
        _number(data['at'], path + '.at'),
        Alignment.parse(alignment, path + '.alignment'),
        tuple(_number(value, f'{path}.levels[{i}]') for i, value in enumerate(levels)),
    )


def decode(data: object, overrides: Overrides | None) -> ActingScore:
    """Parse structure and primitive types; compile_performance validates rig-specific semantics."""
    value = _object(
        data,
        'score',
        {'schema', 'duration', 'beats', 'speech', 'heard', 'seed', 'sample_rate', 'idle'},
        {'schema', 'duration'},
    )
    if value['schema'] not in (SCHEMA, POLICY_SCHEMA, BLEND_SCHEMA):
        raise _error('schema', value['schema'], (SCHEMA, POLICY_SCHEMA, BLEND_SCHEMA))
    if overrides is not None and not isinstance(overrides, Overrides):
        raise _error('overrides', overrides, 'typed runtime Overrides')
    integers = {}
    for name, default in (('seed', 0), ('sample_rate', 30)):
        number = value.get(name, default)
        if type(number) is not int:
            raise _error(name, number, 'an integer')
        integers[name] = number
    speech = {}
    for name in ('speech', 'heard'):
        speech[name] = tuple(_line(row, f'{name}[{i}]') for i, row in enumerate(_array(value.get(name, []), name)))
    beats = tuple(
        _beat(row, f'beats[{i}]', value['schema'] != SCHEMA, value['schema'] == BLEND_SCHEMA)
        for i, row in enumerate(_array(value.get('beats', []), 'beats'))
    )
    return ActingScore(
        _number(value['duration'], 'duration'),
        beats,
        speech=speech['speech'],
        heard=speech['heard'],
        seed=integers['seed'],
        sample_rate=integers['sample_rate'],
        idle=_boolean(value.get('idle', True), 'idle'),
        overrides=overrides or Overrides(),
    )

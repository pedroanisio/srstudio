"""Closed data-only body score decoding; runtime drawing bindings remain separate."""

from dataclasses import fields

from . import checks
from ._body_types import BodyKey, BodyProfile, BodyScore, FootAnchor, Step, fail
from .limbs.errors import LimbError
from .limbs.math3d import Frame, Quaternion, Vec3

SCHEMA = 'srstudio.body/1.0.0'


def obj(value, path, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise fail(path, value, {'allowed': sorted(allowed), 'required': sorted(required)})
    return value


def rows(value, path, limit=1000):
    if not isinstance(value, list) or len(value) > limit:
        raise fail(path, value, f'an array with at most {limit} items')
    return value


def number(value, path):
    if not checks.number(value):
        raise fail(path, value, 'a finite number excluding booleans')
    return value


def vector(value, path, size):
    if not isinstance(value, list) or len(value) != size:
        raise fail(path, value, f'{size} numeric components')
    return tuple(number(v, f'{path}[{i}]') for i, v in enumerate(value))


def rotation(value, path):
    try:
        return Quaternion(*vector(value, path, 4))
    except LimbError as exc:
        raise fail(path, value, 'a nonzero finite quaternion [w,x,y,z]') from exc


def frame(value, path):
    data = obj(value, path, ('origin', 'rotation'), ('origin',))
    return Frame(
        Vec3(*vector(data['origin'], path + '.origin', 3)),
        rotation(data.get('rotation', [1, 0, 0, 0]), path + '.rotation'),
    )


def parse(data: object) -> BodyScore:
    value = obj(
        data,
        'score',
        ('schema', 'duration', 'roots', 'stance', 'steps', 'profile', 'validation_hz'),
        ('schema', 'duration', 'roots', 'stance'),
    )
    if value['schema'] != SCHEMA:
        raise fail('schema', value['schema'], SCHEMA)
    profile = obj(value.get('profile', {}), 'profile', [f.name for f in fields(BodyProfile)])
    parsed_profile = {
        k: vector(v, 'profile.' + k, 2) if k == 'knee_limits' else number(v, 'profile.' + k) for k, v in profile.items()
    }
    roots = []
    for i, raw in enumerate(rows(value['roots'], 'roots')):
        path = f'roots[{i}]'
        row = obj(raw, path, ('time', 'root', 'torso'), ('time', 'root'))
        roots.append(
            BodyKey(
                number(row['time'], path + '.time'),
                frame(row['root'], path + '.root'),
                rotation(row.get('torso', [1, 0, 0, 0]), path + '.torso'),
            )
        )
    stance = []
    for i, raw in enumerate(rows(value['stance'], 'stance', 2)):
        path = f'stance[{i}]'
        row = obj(raw, path, ('side', 'frame'), ('side', 'frame'))
        stance.append(FootAnchor(row['side'], frame(row['frame'], path + '.frame')))
    steps = []
    for i, raw in enumerate(rows(value.get('steps', []), 'steps')):
        path = f'steps[{i}]'
        row = obj(raw, path, ('side', 'start', 'end', 'target', 'clearance'), ('side', 'start', 'end', 'target'))
        steps.append(
            Step(
                row['side'],
                number(row['start'], path + '.start'),
                number(row['end'], path + '.end'),
                frame(row['target'], path + '.target'),
                number(row.get('clearance', 0.08), path + '.clearance'),
            )
        )
    hz = value.get('validation_hz', 60)
    if type(hz) is not int:
        raise fail('validation_hz', hz, 'an integer')
    return BodyScore(
        number(value['duration'], 'duration'),
        tuple(roots),
        tuple(stance),
        tuple(steps),
        BodyProfile(**parsed_profile),
        hz,
    )

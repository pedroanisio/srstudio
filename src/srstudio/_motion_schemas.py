"""Closed JSON document shapes; geometric and cross-record invariants stay in runtime validation."""

from __future__ import annotations

import types
from dataclasses import MISSING, fields, is_dataclass
from typing import Any, Union, get_args, get_origin, get_type_hints

from ._body_types import SIDES, BodyProfile
from .document_schemas import _array, _object
from .limbs.model import ArmProfile, HandProfile
from .limbs.motion import ACTIONS, Motion, Sample


def _vector(size: int) -> dict:
    return {**_array({'type': 'number'}, size), 'minItems': size}


def body_schema(version: str) -> dict:
    number = {'type': 'number'}
    seconds = {'type': 'number', 'minimum': 0, 'maximum': 600}
    frame = _object({'origin': _vector(3), 'rotation': _vector(4)}, ('origin',))
    side = {'enum': list(SIDES)}
    profile = {f.name: number.copy() for f in fields(BodyProfile)}
    profile['knee_limits'] = _vector(2)
    if version == '1.0.0':
        del profile['shoulder_width']
    return {
        **_object(
            {
                'schema': {'const': f'srstudio.body/{version}'},
                'duration': number,
                'roots': _array(_object({'time': seconds, 'root': frame, 'torso': _vector(4)}, ('time', 'root'))),
                'stance': _array(_object({'side': side, 'frame': frame}, ('side', 'frame')), 2),
                'steps': _array(
                    _object(
                        {
                            'side': side,
                            'start': seconds,
                            'end': seconds,
                            'target': frame,
                            'clearance': {'type': 'number', 'minimum': 0.01, 'maximum': 0.25},
                        },
                        ('side', 'start', 'end', 'target'),
                    )
                ),
                'profile': _object(profile),
                'validation_hz': {'type': 'integer', 'x-python-type': 'int'},
            },
            ('schema', 'duration', 'roots', 'stance'),
        ),
        'x-runtime-constraints': [
            'Finite numbers; validation_hz must be a Python int, not float or bool.',
            'Profile lengths and joint envelopes, ordered knee limits and support margin are validated by the parser.',
            'Frames use meters with +y down, yaw-only roots and soles on y=0; rotations are [w,x,y,z].',
            'Compile to check duration, ordered roots, bilateral stance, step ordering, support and work budgets.',
        ],
    }


def _record_shapes(*records: type, limit: int = 4096, string_limit: int | None = 1024) -> tuple[list[dict], dict]:
    definitions: dict[str, Any] = {}

    def shape(kind: Any) -> dict:
        if get_origin(kind) in (types.UnionType, Union):
            return {'anyOf': [shape(item) for item in get_args(kind)]}
        if kind is type(None):
            return {'type': 'null'}
        if kind in (float, int, bool, str):
            result: dict[str, Any] = {'type': {float: 'number', int: 'integer', bool: 'boolean', str: 'string'}[kind]}
            if kind is str and string_limit is not None:
                result['maxLength'] = string_limit
            if kind is int:
                result['x-python-type'] = 'int'
            return result
        if get_origin(kind) is tuple:
            args = get_args(kind)
            if len(args) == 2 and args[1] is Ellipsis:
                return _array(shape(args[0]), limit)
            return {
                'type': 'array',
                'prefixItems': [shape(t) for t in args],
                'minItems': len(args),
                'maxItems': len(args),
            }
        if isinstance(kind, type) and is_dataclass(kind):
            name = kind.__name__
            if name not in definitions:
                definitions[name] = {}
                hints = get_type_hints(kind)
                properties = {f.name: shape(hints[f.name]) for f in fields(kind)}
                if name == 'HandPose':
                    properties['palm'].update(minItems=4, maxItems=4)
                required = tuple(f.name for f in fields(kind) if f.default is MISSING and f.default_factory is MISSING)
                definitions[name] = _object(properties, required)
            return {'$ref': f'#/$defs/{name}'}
        raise TypeError(f'Unsupported motion document type: {kind}')

    return [shape(record) for record in records], definitions


def procedural_schema(version: str) -> dict:
    shapes, definitions = _record_shapes(Motion, limit=10000, string_limit=None)
    properties = definitions['Motion']['properties']
    properties['reach_policy'] = {'enum': ['strict', 'clamp']}
    definitions['Action']['properties']['name'] = {'enum': list(ACTIONS)}
    definitions['ArmProfile']['properties']['side'] = {'enum': ['left', 'right']}
    definitions['TransformTrack']['properties']['interpolation'] = {'enum': ['smooth', 'continuous']}
    definitions['TransformTrack']['properties']['keys']['minItems'] = 1
    if version != '1.4.0':
        del definitions['MotionStyle']['properties']['envelope']
    else:
        definitions['MotionStyle']['properties']['envelope'] = {'enum': ['minimum-jerk', 'legacy']}
    if version not in ('1.3.0', '1.4.0'):
        del properties['joins']
    if version in ('1.0.0', '1.1.0'):
        del definitions['TransformTrack']['properties']['interpolation']
        for name in ('velocity', 'angular_velocity'):
            del definitions['TransformKey']['properties'][name]
    if version == '1.0.0':
        del definitions['DigitProfile']['properties']['bend_axis']
    return {
        **_object(
            {'schema': {'const': f'srstudio.limbs/{version}'}, 'generatedBy': {'type': 'string'}, 'motion': shapes[0]},
            ('schema', 'motion'),
        ),
        '$defs': definitions,
        'x-runtime-constraints': [
            'Finite numbers; decoding is bounded to 100000 items and 32 levels.',
            'Times use motion seconds; canonical world units and radians follow the typed limb records.',
            'Parse to check anatomy, joint limits, ordered actions/contacts and compatible transform controls.',
            'Compile to check geometry, adapter capabilities, frame/node budgets and selected quality limits.',
        ],
    }


def keyed_schema(version: str) -> dict:
    (arm, hand, sample), definitions = _record_shapes(ArmProfile, HandProfile, Sample)

    motion = _object(
        {
            'arm': arm,
            'hand': hand,
            'played': {**_array(sample, 4096), 'minItems': 1},
            'fps': {'type': 'integer', 'minimum': 1, 'maximum': 120, 'x-python-type': 'int'},
        },
        ('arm', 'hand', 'played', 'fps'),
    )
    return {
        **_object(
            {
                'schema': {'const': f'srstudio.limbs-keyed/{version}'},
                'generatedBy': {'type': 'string'},
                'motion': motion,
            },
            ('schema', 'motion'),
        ),
        '$defs': definitions,
        'x-runtime-constraints': [
            'Finite numbers; fps must be a Python int. Decoding is bounded to 2,000,000 items and 32 levels.',
            'Sample times equal i/fps from zero. Playback holds each solved pose; no procedural drivers.',
            'Solved rotations are already unit quaternions; limb lengths, hand geometry and anatomy must agree.',
            'Compile to check adapter capabilities, projection, frame/node budgets and opted-in quality limits.',
        ],
    }

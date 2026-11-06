"""Data document schemas, separate from contracts describing Python call signatures (ADR 0228).

Schemas constrain JSON structure. Parsers still check finite values, equal-length
alignment arrays, ordering and Python integer representation; compilation checks
timing and rig capabilities. No runtime bindings are accepted by these documents.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from ._acting_parse import BLEND_SCHEMA, POLICY_SCHEMA, SCHEMA
from ._body_parse import LEGACY_SCHEMA as BODY_LEGACY_SCHEMA
from ._body_parse import SCHEMA as BODY_SCHEMA
from .acting import HeadTarget
from .errors import SrstudioError
from .limbs import serialization as limb_documents
from .limbs._motion_keyed import SCHEMA as KEYED_SCHEMA

VERSIONS = tuple(s.rsplit('/', 1)[1] for s in (SCHEMA, POLICY_SCHEMA, BLEND_SCHEMA))
_FORMATS = {
    'authoring': (
        ('1.0.0',),
        'srstudio.authoring.parse_request',
        'srstudio.authoring.compile_request',
        'docs/authoring-agents.md',
    ),
    'acting': (
        VERSIONS,
        'srstudio.acting.parse_score',
        'srstudio.acting.compile_performance',
        'docs/authoring-acting.md',
    ),
    'body': (
        tuple(s.rsplit('/', 1)[1] for s in (BODY_LEGACY_SCHEMA, BODY_SCHEMA)),
        'srstudio.body.parse_body',
        'srstudio.body.compile_body',
        'docs/authoring-body.md',
    ),
    'limbs-keyed': (
        (KEYED_SCHEMA.rsplit('/', 1)[1],),
        'srstudio.limbs.serialization.parse_motion',
        'srstudio.limbs.compile.compile_motion',
        'docs/catalog/limbs.md',
    ),
    'limbs': (
        tuple(
            s.rsplit('/', 1)[1]
            for s in (
                limb_documents.LEGACY_SCHEMA,
                limb_documents.ANATOMY_SCHEMA,
                limb_documents.TRANSFORM_SCHEMA,
                limb_documents.JOIN_SCHEMA,
                limb_documents.SCHEMA,
            )
        ),
        'srstudio.limbs.serialization.parse_motion',
        'srstudio.limbs.compile.compile_motion',
        'docs/catalog/limbs.md',
    ),
    'dance-moves': (
        ('1.0.0', '1.1.0'),
        'srstudio.dance.parse_moves',
        'srstudio.dance.sample',
        'docs/authoring-dance.md',
    ),
}


class DocumentSchemaError(SrstudioError, ValueError):
    """The requested document format or version is not supported."""


def catalog() -> dict[str, Any]:
    return {
        'schema': 'srstudio.document-schemas/1.0.0',
        'documents': [
            {
                'name': name,
                'versions': list(versions),
                'default_version': versions[-1],
                'parser': parser,
                'compiler': compiler,
                'guide': guide,
            }
            for name, (versions, parser, compiler, guide) in _FORMATS.items()
        ],
    }


def _object(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    return {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': False}


def _array(items: dict[str, Any], limit: int = 1000) -> dict[str, Any]:
    return {'type': 'array', 'items': items, 'maxItems': limit}


def _nullable(value: dict[str, Any]) -> dict[str, Any]:
    return {'anyOf': [value, {'type': 'null'}]}


def get(name: str, *, version: str | None = None) -> dict[str, Any]:
    """Return a fresh JSON Schema 2020-12 document; default to the latest supported version."""
    versions = _FORMATS.get(name, ((), '', '', ''))[0] if isinstance(name, str) else ()
    version = versions[-1] if version is None and versions else version
    for path, actual, allowed in (('name', name, tuple(_FORMATS)), ('version', version, versions)):
        if actual not in allowed:
            raise DocumentSchemaError(
                f'unknown schema {path}: {actual!r}',
                code='schema.unknown',
                path=path,
                actual=actual,
                expected=list(allowed),
                remedy='Choose a document and version from srstudio schema --json.',
            )
    assert version is not None
    if name != 'acting':
        from ._dance_schema import moves_schema
        from ._motion_schemas import body_schema, keyed_schema, procedural_schema
        from .authoring import schema as authoring_schema

        document = {
            'authoring': authoring_schema,
            'body': body_schema,
            'limbs-keyed': keyed_schema,
            'limbs': procedural_schema,
            'dance-moves': moves_schema,
        }[name](version)
        return {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': f'urn:srstudio:{name}:{version}',
            'title': f'srstudio {name} {version}',
            'x-parser': _FORMATS[name][1],
            'x-validation': 'runtime-required',
            **document,
        }
    from ._acting_transitions import CURVES, VERSION
    from .head_motion import CHANNELS

    number = {'type': 'number'}
    seconds = {'type': 'number', 'minimum': 0, 'maximum': 600}
    fraction = {'type': 'number', 'minimum': 0, 'maximum': 1}
    label = {'type': 'string', 'minLength': 1, 'maxLength': 128}
    expression = _object({'eyes': label, 'mouth': _nullable(label)}, ('eyes',))
    head = _object({f.name: _nullable(number) for f in fields(HeadTarget)})
    spring = _object(
        {
            'frequency': {'type': 'number', 'minimum': 0.1, 'maximum': 20},
            'damping': {'type': 'number', 'minimum': 0.1, 'maximum': 2},
        },
        ('frequency', 'damping'),
    )
    timing = _object(
        {
            'channel': {'enum': [*CHANNELS, 'expression', 'gesture', 'gaze']},
            'delay': seconds,
            'duration': _nullable(seconds),
        },
        ('channel',),
    )
    policy = _object(
        {
            'version': {'const': VERSION},
            'curve': {'enum': list(CURVES)},
            'anticipation': seconds,
            'anticipation_amount': fraction,
            'settle': seconds,
            'overshoot': fraction,
            'spring': _nullable(spring),
            'timing': _array(timing, 11),
        },
        ('version',),
    )
    beat = {
        'at': seconds,
        'emotion': _nullable(label),
        'expression': _nullable(expression),
        'gaze': _nullable(label),
        'gesture': _nullable(label),
        'head': _nullable(head),
        'breath': _nullable(number),
        'transition': seconds,
        'reset': {'type': 'boolean'},
    }
    if version != '1.0.0':
        beat['policy'] = _nullable(policy)
    if version == '1.2.0':
        beat['blend'] = {'type': 'boolean'}
    alignment = _object(
        {
            'characters': _array({'type': 'string', 'minLength': 1, 'maxLength': 1}, 20_000),
            'character_start_times_seconds': _array({'type': 'number', 'minimum': 0}, 20_000),
            'character_end_times_seconds': _array({'type': 'number', 'minimum': 0}, 20_000),
        },
        ('characters', 'character_start_times_seconds', 'character_end_times_seconds'),
    )
    line = _object(
        {'at': number, 'alignment': alignment, 'levels': _array(number, 60_000)}, ('at', 'alignment', 'levels')
    )
    document = _object(
        {
            'schema': {'const': f'srstudio.acting/{version}'},
            'duration': {'type': 'number', 'minimum': 0.0001, 'maximum': 600},
            'beats': _array(_object(beat, ('at',))),
            'speech': _array(line),
            'heard': _array(line),
            'seed': {'type': 'integer', 'x-python-type': 'int'},
            'sample_rate': {'type': 'integer', 'minimum': 1, 'maximum': 120, 'x-python-type': 'int'},
            'idle': {'type': 'boolean'},
        },
        ('schema', 'duration'),
    )
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': f'urn:srstudio:acting:{version}',
        'title': f'srstudio acting score {version}',
        'x-parser': 'srstudio.acting.parse_score',
        'x-validation': 'runtime-required',
        'x-runtime-constraints': [
            'Finite numbers; Python seed/sample_rate must be int, not float or bool.',
            'Alignment arrays have equal lengths and ordered valid spans.',
            'Compile with a rig to validate timing, vocabulary and capabilities.',
        ],
        **document,
    }

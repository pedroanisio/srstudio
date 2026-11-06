"""Versioned JSON shapes for the existing dance-move text parser."""

from ._dance_model import (
    CHAINS,
    CURVE_POINTS,
    FEET,
    MAX_CONTACTS,
    MAX_PATTERNS,
    MAX_ROOT,
    MAX_TURN,
    ROOT,
    SUPPORTS,
    TARGETS,
)
from ._dance_parse import MAX_MOVES
from .document_schemas import _array, _object


def _number(low: float, high: float) -> dict:
    return {'type': 'number', 'minimum': low, 'maximum': high}


def moves_schema(version: str) -> dict:
    text = {'type': 'string', 'maxLength': 512}
    common = {
        'target': {'enum': list(TARGETS)},
        'amplitude': _number(-MAX_ROOT, MAX_ROOT),
        'cycles': _number(0.001, 16),
        'per': {'enum': ['beat', 'bar']},
        'phase': _number(-64, 64),
        'swing': _number(0.5, 0.75),
        'intensity': _number(0, 2),
        'bias': _number(-MAX_ROOT, MAX_ROOT),
    }
    required = ('target', 'amplitude', 'cycles', 'per', 'phase', 'waveform')
    patterns = []
    for waveform in ('sine', 'hold', 'curve') if version != '1.0.0' else ('sine', 'hold'):
        shape = 'curve' if waveform == 'curve' else 'snap'
        value = (
            {**_array(_number(-1, 1), CURVE_POINTS[1]), 'minItems': CURVE_POINTS[0]}
            if shape == 'curve'
            else _number(0.05, 0.5 if waveform == 'hold' else 0.95)
        )
        pattern = _object({**common, 'waveform': {'const': waveform}, shape: value}, (*required, shape))
        pattern['allOf'] = [
            {
                'if': {'properties': {'target': {'enum': list(ROOT)}}},
                'else': {
                    'properties': {'amplitude': _number(-MAX_TURN, MAX_TURN), 'bias': _number(-MAX_TURN, MAX_TURN)}
                },
            }
        ]
        patterns.append(pattern)
    contact = _object(
        {'foot': {'enum': list(FEET)}, 'from': _number(0, 64), 'to': _number(0, 64)}, ('foot', 'from', 'to')
    )
    move = _object(
        {
            'name': {'type': 'string', 'maxLength': 64, 'pattern': '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$'},
            'support': {'enum': list(SUPPORTS)},
            'patterns': {**_array({'oneOf': patterns}, MAX_PATTERNS), 'minItems': 1},
            'description': text,
            'loop_beats': _number(0.25, 64),
            'lags': _object({name: _number(0, 1) for name in CHAINS}),
            'contacts': _array(contact, MAX_CONTACTS),
        },
        ('name', 'support', 'patterns'),
    )
    return {
        **_object(
            {
                'schema': {'const': f'srstudio.dance-moves/{version}'},
                'moves': {**_array(move, MAX_MOVES), 'minItems': 1},
                'generated_by': _object({'tool': text, 'model': text}, ('tool', 'model')),
            },
            ('schema', 'moves'),
        ),
        'x-parser-input': 'JSON text or UTF-8 bytes; serialize the validated object before parse_moves.',
        'x-runtime-constraints': [
            'Finite numbers, unique move names and pattern targets, at most 1000000 bytes of JSON text.',
            'Curves must normalize to their hit and far extreme and pass played-spline bounds.',
            'Loop cycles, support, contacts and nonzero movement require the typed model checks.',
            'Sampling requires a music.Groove; skeleton limits and rendered quality are separate checks.',
        ],
    }

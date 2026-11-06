"""Known authoring constraints and additional motion formats are available before compilation."""

import copy
import json
import math

import pytest
from jsonschema import Draft202012Validator

from srstudio import acting, dance, document_schemas
from srstudio.cli import main
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.motion import Action, Motion
from srstudio.limbs.serialization import motion_dict, parse_motion


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0', '1.2.0'])
@pytest.mark.parametrize(
    'update', [{'duration': -1}, {'duration': 0}, {'duration': 601}, {'sample_rate': 0}, {'sample_rate': 121}]
)
def test_acting_schema_rejects_rig_independent_runtime_bounds(version, update):
    data = {'schema': f'srstudio.acting/{version}', 'duration': 2, **update}
    assert not Draft202012Validator(document_schemas.get('acting', version=version)).is_valid(data)
    with pytest.raises(acting.ActingError):
        acting.compile_performance(acting.BENTO, acting.parse_score(data))


@pytest.mark.parametrize(
    'update',
    [
        {'version': '9.0.0'},
        {'curve': 'typo'},
        {'anticipation': -1},
        {'anticipation_amount': 1.1},
        {'settle': 601},
        {'overshoot': -1},
        {'timing': [{'channel': 'typo'}]},
        {'timing': [{'channel': 'nod', 'delay': -1}]},
    ],
)
def test_acting_schema_publishes_policy_vocabulary_and_bounds(update):
    data = {
        'schema': 'srstudio.acting/1.2.0',
        'duration': 2,
        'beats': [{'at': 0.5, 'head': {'nod': 1}, 'transition': 0.25, 'policy': {'version': '1.0.0', **update}}],
    }
    assert not Draft202012Validator(document_schemas.get('acting')).is_valid(data)
    with pytest.raises(acting.ActingError):
        acting.compile_performance(acting.BENTO, acting.parse_score(data))


def test_acting_valid_boundary_values_remain_accepted():
    for duration, sample_rate in [(0.0001, 1), (2, 120), (600, 1)]:
        data = {'schema': 'srstudio.acting/1.2.0', 'duration': duration, 'sample_rate': sample_rate}
        Draft202012Validator(document_schemas.get('acting')).validate(data)


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0'])
def test_procedural_limb_schema_accepts_a_real_motion_and_rejects_wrong_fields(version):
    data = json.loads(json.dumps(motion_dict(Motion(ArmProfile(), HUMAN, (Action('point'),)))))
    data['schema'] = f'srstudio.limbs/{version}'
    if version != '1.4.0':
        data['motion']['actions'][0]['style'].pop('envelope')
    if version not in ('1.3.0', '1.4.0'):
        data['motion'].pop('joins')
    if version in ('1.0.0', '1.1.0'):
        data['motion']['root'].pop('interpolation')
        for key in data['motion']['root']['keys']:
            key.pop('velocity')
            key.pop('angular_velocity')
    if version == '1.0.0':
        for digit in data['motion']['hand']['digits']:
            digit.pop('bend_axis')
    schema = document_schemas.get('limbs', version=version)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(data)
    assert parse_motion(data).actions[0].name == 'point'
    data['motion']['actions'][0]['target'] = {'position': {'x': 'far'}}
    assert not Draft202012Validator(schema).is_valid(data)


def move_document(version='1.1.0', curved=False):
    pattern = {
        'target': 'chest.front_back',
        'amplitude': 0.2,
        'cycles': 1,
        'per': 'beat',
        'phase': 0,
        'waveform': 'curve' if curved else 'sine',
    }
    pattern.update({'curve': [math.cos(2 * math.pi * i / 16) for i in range(16)]} if curved else {'snap': 0.5})
    return {
        'schema': f'srstudio.dance-moves/{version}',
        'moves': [{'name': 'nod', 'support': 'either', 'patterns': [pattern]}],
    }


@pytest.mark.parametrize('version,curved', [('1.0.0', False), ('1.1.0', False), ('1.1.0', True)])
def test_dance_moves_schema_matches_real_parser_and_keeps_waveform_fields_exclusive(version, curved):
    schema = document_schemas.get('dance-moves', version=version)
    Draft202012Validator.check_schema(schema)
    data = move_document(version, curved)
    Draft202012Validator(schema).validate(data)
    assert 'nod' in dance.parse_moves(json.dumps(data))
    for field, value in [
        ('waveform', 'typo'),
        ('target', 'missing'),
        ('amplitude', True),
        ('cycles', 0),
        ('unexpected', 1),
        ('snap' if curved else 'curve', 0.5 if curved else []),
    ]:
        bad = copy.deepcopy(data)
        bad['moves'][0]['patterns'][0][field] = value
        assert not Draft202012Validator(schema).is_valid(bad), (field, value)
        with pytest.raises(dance.DanceError):
            dance.parse_moves(json.dumps(bad))


def test_legacy_dance_schema_refuses_curve_waveforms():
    assert not Draft202012Validator(document_schemas.get('dance-moves', version='1.0.0')).is_valid(
        move_document('1.0.0', True)
    )


def test_added_formats_are_discoverable_and_cli_schemas_match_python(capsys):
    catalog = {row['name']: row for row in document_schemas.catalog()['documents']}
    for name, parser in [
        ('limbs', 'srstudio.limbs.serialization.parse_motion'),
        ('dance-moves', 'srstudio.dance.parse_moves'),
    ]:
        assert catalog[name]['parser'] == parser
        assert main(['schema', name, '--json']) == 0
        assert json.loads(capsys.readouterr().out) == document_schemas.get(name)

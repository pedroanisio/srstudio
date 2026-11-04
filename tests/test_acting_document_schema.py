"""Published JSON score shapes agree with the strict decoder across supported versions."""

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from srstudio import acting
from srstudio.cli import main


def published(version):
    from srstudio import document_schemas

    return document_schemas.get('acting', version=version)


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0', '1.2.0'])
def test_schema_is_valid_and_accepts_representative_scores(version):
    schema = published(version)
    Draft202012Validator.check_schema(schema)
    beat = {'at': 0, 'emotion': 'neutral', 'head': {'nod': 2}, 'expression': {'eyes': 'open'}}
    if version != '1.0.0':
        beat['policy'] = {
            'version': '1.0.0',
            'spring': {'frequency': 2, 'damping': 0.7},
            'timing': [{'channel': 'nod', 'delay': 0.1}],
        }
    if version == '1.2.0':
        beat['blend'] = True
    data = {
        'schema': f'srstudio.acting/{version}',
        'duration': 2,
        'beats': [beat],
        'speech': [
            {
                'at': 0,
                'alignment': {
                    'characters': ['a'],
                    'character_start_times_seconds': [0],
                    'character_end_times_seconds': [0.1],
                },
                'levels': [0.1, 0.2],
            }
        ],
    }
    Draft202012Validator(schema).validate(data)
    assert acting.parse_score(data).duration == 2


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0', '1.2.0'])
@pytest.mark.parametrize(
    'update',
    [
        {'extra': 1},
        {'duration': True},
        {'duration': '2'},
        {'beats': [{'at': 0, 'extra': 1}]},
        {'beats': [{'at': 0, 'expression': {'eyes': ''}}]},
        {'idle': 'yes'},
        {'seed': True},
        {'beats': [{'at': 0}] * 1001},
        {'speech': [{'at': 0, 'alignment': {}, 'levels': []}]},
    ],
)
def test_schema_and_parser_reject_the_same_malformed_shapes(version, update):
    data = {'schema': f'srstudio.acting/{version}', 'duration': 2, **copy.deepcopy(update)}
    assert not Draft202012Validator(published(version)).is_valid(data)
    with pytest.raises(acting.ActingError):
        acting.parse_score(data)


@pytest.mark.parametrize(
    'version, field, value',
    [('1.0.0', 'policy', {'version': '1.0.0'}), ('1.0.0', 'blend', False), ('1.1.0', 'blend', True)],
)
def test_schema_enforces_version_specific_fields(version, field, value):
    data = {'schema': f'srstudio.acting/{version}', 'duration': 2, 'beats': [{'at': 0, field: value}]}
    assert not Draft202012Validator(published(version)).is_valid(data)
    with pytest.raises(acting.ActingError):
        acting.parse_score(data)


def test_schema_cli_and_python_publish_the_same_document(capsys):
    assert main(['schema', 'acting', '--version', '1.2.0', '--json']) == 0
    assert json.loads(capsys.readouterr().out) == published('1.2.0')
    assert main(['schema', '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['documents'][0]['parser'] == 'srstudio.acting.parse_score'


def test_schema_unknown_version_is_a_repairable_error(capsys):
    assert main(['schema', 'acting', '--version', '9.0.0', '--json']) == 2
    error = json.loads(capsys.readouterr().err)
    assert error['path'] == 'version' and '1.2.0' in error['expected']

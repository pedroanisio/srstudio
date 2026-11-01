"""Agent-authored JSON is parsed strictly before semantic compilation."""

import json

import pytest

from srstudio.acting import BENTO, ActingError, Overrides, compile_performance, parse_score


def document():
    return {
        'schema': 'srstudio.acting/1.0.0',
        'duration': 3,
        'beats': [
            {'at': 0, 'emotion': 'happy', 'transition': 0},
            {'at': 1, 'gaze': 'left', 'head': {'lean': 0.1}, 'transition': 0.25},
        ],
    }


def test_strict_json_becomes_typed_intent_and_accepts_explicit_runtime_bindings():
    score = parse_score(json.loads(json.dumps(document())), overrides=Overrides(mouth=((0, 'closed'),)))
    plan = compile_performance(BENTO, score)
    assert plan.sample(1.5).gaze == 'left'
    assert plan.sample(1.5).head.lean == pytest.approx(0.1)
    assert dict(plan.owners)['mouth'] == 'override'


@pytest.mark.parametrize(
    'data',
    [
        None,
        [],
        {},
        {'schema': 'srstudio.acting/99', 'duration': 3},
        {'schema': 'srstudio.acting/1.0.0', 'duration': True},
        {'schema': 'srstudio.acting/1.0.0', 'duration': 3, 'execute': 'anything'},
        {'schema': 'srstudio.acting/1.0.0', 'duration': 3, 'beats': [{'at': 0, 'gesturee': 'folded'}]},
        {'schema': 'srstudio.acting/1.0.0', 'duration': 3, 'beats': [{'at': 0, 'head': {'turn': '2'}}]},
        {'schema': 'srstudio.acting/1.0.0', 'duration': 3, 'beats': [{'at': 0, 'reset': 'false'}]},
        {'schema': 'srstudio.acting/1.0.0', 'duration': 3, 'sample_rate': 12.5},
        {
            'schema': 'srstudio.acting/1.0.0',
            'duration': 3,
            'beats': [{'at': 0, 'expression': {'eyes': 'happy', 'oops': 1}}],
        },
        {'schema': 'srstudio.acting/1.0.0', 'duration': 3, 'speech': [{'at': 0}]},
        {'schema': 'srstudio.acting/1.0.0', 'duration': 3, 'overrides': {'mouth': []}},
        {'schema': 'srstudio.acting/1.0.0', 'duration': float('nan')},
    ],
)
def test_unknown_missing_or_mistyped_fields_fail_closed(data):
    with pytest.raises(ActingError) as caught:
        parse_score(data)
    details = caught.value.to_dict()
    assert details['path'] and details['expected'] and details['remedy']
    json.dumps(details, allow_nan=False)


def test_parser_bounds_records_without_consuming_arbitrary_iterators():
    data = document()
    data['beats'] = [{'at': 0}] * 1001
    with pytest.raises(ActingError, match='1000'):
        parse_score(data)
    data['beats'] = iter(())
    with pytest.raises(ActingError):
        parse_score(data)


def test_alignment_and_levels_are_typed_before_reaching_the_compiler():
    data = document()
    data['speech'] = [
        {
            'at': 0.5,
            'alignment': {
                'characters': ['h', 'i'],
                'character_start_times_seconds': [0, 0.2],
                'character_end_times_seconds': [0.2, 0.4],
            },
            'levels': [-24] * 40,
        }
    ]
    plan = compile_performance(BENTO, parse_score(data))
    assert plan.sample(0.75).mouth != 'closed'
    data['speech'][0]['levels'][0] = 'bad'
    with pytest.raises(ActingError):
        parse_score(data)

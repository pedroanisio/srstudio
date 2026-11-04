"""Discovery exposes executable intent vocabulary and closed motion documents."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from srstudio import acting, body, document_schemas
from srstudio.cli import main
from srstudio.head_motion import CHANNELS, limit
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.errors import LimbError
from srstudio.limbs.motion import Motion
from srstudio.limbs.serialization import motion_dict, parse_motion


@pytest.mark.parametrize('rig', [acting.BENTO, acting.gloss_actor('nadia'), acting.gloss_actor('sunny')])
def test_rig_advertised_vocabulary_compiles(rig):
    description = rig.describe()
    vocab = description['vocabulary']
    assert set(vocab) == {'eyes', 'mouths', 'gestures', 'gaze', 'visemes'}
    for field in ('eyes', 'mouths', 'gestures', 'gaze'):
        for value in vocab[field]:
            if field in ('eyes', 'mouths'):
                expression = acting.Expression(
                    value if field == 'eyes' else vocab['eyes'][0], value if field == 'mouths' else None
                )
                beat = acting.ActingBeat(0, expression=expression, transition=0)
            else:
                beat = acting.ActingBeat(0, **{'gesture' if field == 'gestures' else field: value}, transition=0)
            acting.compile_performance(rig, acting.ActingScore(1, (beat,)))
    if rig.family == 'gloss':
        assert vocab['mouths'] == vocab['gaze'] == []
        assert description['channels'] == {}
    if rig.gloss_character == 'sunny':
        assert vocab['gestures'] == []
    assert vocab['visemes']
    json.dumps(description, allow_nan=False)


def test_head_channels_describe_runtime_bounds_and_units():
    rig = acting.BENTO
    channels = rig.describe()['channels']
    assert set(channels) == set(CHANNELS)
    for name, info in channels.items():
        assert info['maximum'] == limit(rig.head_rig.style, name)
        assert info['minimum'] == (0 if name == 'breath' else -info['maximum'])
        assert info['unit'] == (
            'normalized'
            if name == 'breath'
            else 'reference pixels'
            if name in ('nod', 'face_x', 'idle_y')
            else 'degrees'
        )
        assert info['input']
    assert channels['idle_y']['input'] == 'overrides.head.idle_y'


def body_document(version='1.1.0'):
    return {
        'schema': f'srstudio.body/{version}',
        'duration': 2,
        'roots': [{'time': 0, 'root': {'origin': [0, -0.88, 0]}}],
        'stance': [{'side': side, 'frame': {'origin': [x, 0, 0]}} for side, x in [('left', -0.12), ('right', 0.12)]],
    }


def keyed_document():
    motion = Motion(ArmProfile(), HUMAN)
    return motion_dict(motion.keyed(tuple(motion.sample(i / 4) for i in range(4)), fps=4))


@pytest.mark.parametrize(
    'name,version,factory,parser',
    [
        ('body', '1.0.0', lambda: body_document('1.0.0'), body.parse_body),
        ('body', '1.1.0', body_document, body.parse_body),
        ('limbs-keyed', '1.0.0', keyed_document, parse_motion),
    ],
)
def test_published_motion_schema_accepts_parser_documents(name, version, factory, parser, capsys):
    schema = document_schemas.get(name, version=version)
    Draft202012Validator.check_schema(schema)
    document = factory()
    Draft202012Validator(schema).validate(document)
    parser(document)
    assert schema['x-runtime-constraints']
    assert main(['schema', name, '--version', version, '--json']) == 0
    assert json.loads(capsys.readouterr().out) == schema
    schema['properties'].clear()
    assert document_schemas.get(name, version=version)['properties']


@pytest.mark.parametrize(
    'path,value',
    [
        (('extra',), 1),
        (('roots', 0, 'root', 'origin'), [0, 0]),
        (('roots', 0, 'torso'), [1, 0, 0]),
        (('stance', 0, 'side'), 'lef'),
        (('profile',), {'shoulder_width': None}),
        (('profile',), {'thigh': True}),
        (('profile',), {'knee_limits': [0.2]}),
        (('validation_hz',), True),
    ],
)
def test_body_schema_rejects_malformed_fields_like_parser(path, value):
    data = body_document()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert not Draft202012Validator(document_schemas.get('body')).is_valid(data)
    with pytest.raises(body.BodyError):
        body.parse_body(data)


@pytest.mark.parametrize(
    'path,value',
    [
        (('motion', 'fps'), True),
        (('motion', 'fps'), 0),
        (('motion', 'fps'), 121),
        (('motion', 'played'), []),
        (('motion', 'actions'), []),
        (('motion', 'played', 0, 'time'), '0'),
        (('motion', 'played', 0, 'arm', 'frame', 'origin', 'x'), True),
        (('motion', 'played', 0, 'hand', 'palm'), []),
        (('motion', 'arm', 'shoulder', 'typo'), 1),
    ],
)
def test_keyed_schema_rejects_malformed_nested_fields_like_parser(path, value):
    data = copy.deepcopy(keyed_document())
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert not Draft202012Validator(document_schemas.get('limbs-keyed')).is_valid(data)
    with pytest.raises(LimbError):
        parse_motion(data)


def test_schema_catalog_lists_body_versions_and_legacy_refuses_shoulder_width():
    catalog = {d['name']: d for d in document_schemas.catalog()['documents']}
    assert catalog['body']['versions'] == ['1.0.0', '1.1.0']
    assert catalog['limbs-keyed']['parser'] == 'srstudio.limbs.serialization.parse_motion'
    data = body_document('1.0.0')
    data['profile'] = {'shoulder_width': 0.3}
    assert not Draft202012Validator(document_schemas.get('body', version='1.0.0')).is_valid(data)
    with pytest.raises(body.BodyError):
        body.parse_body(data)


@pytest.mark.parametrize(
    'path,marker', [('docs/authoring-body.md', 'body-document'), ('docs/catalog/limbs.md', 'keyed-document')]
)
def test_documented_motion_document_roundtrips(path, marker):
    text = (Path(__file__).parents[1] / path).read_text()
    code = text.split(f'<!-- {marker}:start -->')[1].split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, path, 'exec'), namespace)
    Draft202012Validator(namespace['schema']).validate(namespace['document'])


@pytest.mark.parametrize('name', [[], {}, None])
def test_invalid_document_name_remains_a_structured_error(name):
    with pytest.raises(document_schemas.DocumentSchemaError) as caught:
        document_schemas.get(name)
    assert caught.value.to_dict()['path'] == 'name'
    assert 'body' in caught.value.to_dict()['expected']

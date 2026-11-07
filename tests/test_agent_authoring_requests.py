"""JSON tasks bind to Python only at the explicit canvas/parent boundary."""

import copy
import json

import pytest
from jsonschema import Draft202012Validator
from sr_core.scene import Scene

from srstudio import authoring, document_schemas


def canvas(local=False):
    from srstudio import Canvas

    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=6)
    return Canvas(scene, font_asset=None, local_time=local, held_frames=True)


@pytest.mark.parametrize('local', [False, True])
def test_every_discovered_character_recipe_decodes_draws_and_keeps_one_clock(local):
    for recipe in authoring.recipes()['items']:
        if recipe['request']['task'] != 'character':
            continue
        data = copy.deepcopy(recipe['request'])
        data['interval'] = {'start_s': 3, 'end_s': 5}
        Draft202012Validator(document_schemas.get('authoring')).validate(data)
        cv = canvas(local)
        compiled = authoring.compile_request(cv, cv.comp, authoring.parse_request(data), id='character')
        group = compiled.group
        assert compiled.diagnostics == () and compiled.motion_reports == ()
        assert group.attributes()['start'] == '3'
        assert group.attributes()['end'] == '5'
        assert group.attributes()['timeOffset'] == '3'
        assert cv.local_time == local
        assert cv.scene.check() == []
        assert list(group.iter('shape'))
        assert all(a.timeBase == 'local' for a in group.iter('animate'))


@pytest.mark.parametrize('task', ['gesture', 'carry'])
def test_spatial_recipe_binds_typed_motion_and_draws_it(task):
    recipe = next(r for r in authoring.recipes()['items'] if r['request']['task'] == task)
    data = recipe['request']
    Draft202012Validator(document_schemas.get('authoring')).validate(data)
    cv = canvas()
    compiled = authoring.compile_request(cv, cv.comp, authoring.parse_request(data), id=task)
    group = compiled.group
    assert list(group.iter('shape'))
    assert cv.scene.check() == []
    assert recipe['evidence']['limitations']
    assert recipe['evidence']['rendered_review'] == 'not-run'
    json.dumps(recipe, allow_nan=False)


@pytest.mark.parametrize(
    'change',
    [
        {'duration': 2},
        {'interval': {'start_s': 3, 'end_s': 2}},
        {'character': 'invented'},
        {'arguments': {'cv': {}}},
        {'arguments': {'end': 3}},
        {'placement': {'scale': float('nan')}},
    ],
)
def test_ambiguous_clocks_runtime_injection_and_invalid_values_have_repair_fields(change):
    data = copy.deepcopy(authoring.recipes()['items'][0]['request'])
    data.update(change)
    with pytest.raises(authoring.AuthoringError) as caught:
        authoring.parse_request(data)
    details = caught.value.to_dict()
    assert details['path'] and details['remedy']


def test_failed_draw_restores_held_keys_and_allows_retry(monkeypatch):
    cv = canvas()
    request = authoring.parse_request(authoring.recipes()['items'][0]['request'])
    before = cv.scene.to_bytes()
    original = cv.keys

    def fail_after_write(*args, **kwargs):
        original(*args, **kwargs)
        raise ValueError('injected drawing failure')

    with monkeypatch.context() as patch:
        patch.setattr(cv, 'keys', fail_after_write)
        with pytest.raises(ValueError, match='injected'):
            authoring.compile_request(cv, cv.comp, request, id='retry')
    assert cv.scene.to_bytes() == before
    assert cv._held == [] and cv._held_rate is None
    authoring.compile_request(cv, cv.comp, request, id='retry')


def test_cli_recipes_can_be_selected_and_inspection_links_the_adapter(capsys):
    from srstudio import registry
    from srstudio.cli import main

    assert main(['recipes', 'pip', '--json']) == 0
    recipe = json.loads(capsys.readouterr().out)
    assert recipe['request']['character'] == 'pip'
    assert registry.describe('character', 'pip')['contract']['authoring']['clock'] == 'relative:interval.start_s'
    assert main(['recipes', 'unknown', '--json']) == 2
    assert json.loads(capsys.readouterr().err)['path'] == 'recipe'


def test_preview_example_builds_all_recipes_and_preserves_existing_outputs(tmp_path):
    import runpy
    from pathlib import Path

    namespace = runpy.run_path(str(Path(__file__).parents[1] / 'examples/agent_authoring.py'))
    paths = namespace['build'](tmp_path / 'previews')
    assert len(paths) == len(authoring.recipes()['items'])
    for path in paths:
        assert path.is_file()
        report = json.loads(path.with_suffix('.json').read_text())
        assert report['sdk_findings'] == []
        assert report['rendered_review'] == 'not-run'
        assert report['compilation']['group_id'] == path.stem
    before = paths[0].read_bytes()
    with pytest.raises(FileExistsError):
        namespace['build'](tmp_path / 'previews')
    assert paths[0].read_bytes() == before


def test_all_advertised_character_variants_execute_their_family_recipe():
    from srstudio._authoring_records import FAMILIES

    recipes = authoring.recipes()['items']
    for family, (_, names) in FAMILIES.items():
        source = next(
            r['request']
            for r in recipes
            if r['request']['task'] == 'character'
            and authoring.describe_character(r['request']['character'])['family'] == family
        )
        for name in names:
            data = copy.deepcopy(source)
            data['character'] = name
            if name == 'gloss-sunny':
                data['arguments'] = {'face': [[0, 'smile'], [1, 'alert']]}
            Draft202012Validator(document_schemas.get('authoring')).validate(data)
            cv = canvas()
            authoring.compile_request(cv, cv.comp, authoring.parse_request(data), id='variant')
            assert cv.scene.check() == [], name


def test_schema_requires_nondefault_family_inputs_and_matches_recipe_styles():
    from srstudio import registry

    schema = Draft202012Validator(document_schemas.get('authoring'))
    for recipe in authoring.recipes()['items']:
        if recipe['request']['task'] != 'character':
            continue
        assert recipe['style'] == registry.describe('character', recipe['id'])['style']
        if recipe['id'] in ('pip', 'stick-rig', 'toon-sloth'):
            data = copy.deepcopy(recipe['request'])
            del data['arguments']
            assert not schema.is_valid(data)


def test_keyed_gesture_schema_matches_the_parser():
    from srstudio.limbs import HUMAN, ArmProfile
    from srstudio.limbs.motion import Action, Motion
    from srstudio.limbs.serialization import motion_dict

    source = Motion(ArmProfile(), HUMAN, (Action('present', duration=2),))
    keyed = source.keyed(tuple(source.sample(i / 24) for i in range(48)), fps=24)
    data = next(r['request'] for r in authoring.recipes()['items'] if r['id'] == 'gesture')
    data['motion'] = motion_dict(keyed)
    request = authoring.parse_request(data)
    Draft202012Validator(document_schemas.get('authoring')).validate(data)
    cv = canvas()
    authoring.compile_request(cv, cv.comp, request, id='keyed')
    assert cv.scene.check() == []


def test_nested_decode_error_keeps_the_field_agents_must_repair():
    data = next(r['request'] for r in authoring.recipes()['items'] if r['id'] == 'pip')
    data['arguments']['cues'][0]['time'] = 'late'
    with pytest.raises(authoring.AuthoringError) as caught:
        authoring.parse_request(data)
    assert caught.value.to_dict()['path'] == 'arguments.cues[0].time'


def test_documented_request_executes():
    from pathlib import Path

    guide = (Path(__file__).parents[1] / 'docs/authoring-agents.md').read_text()
    block = guide.split('<!-- agent-request:start -->')[1].split('<!-- agent-request:end -->')[0]
    code = block.split('```python\n')[1].split('```')[0]
    exec(compile(code, 'docs/authoring-agents.md', 'exec'), {})

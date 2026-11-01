"""Legacy authoring boundaries expose repair fields without interpreting their prose."""

import json
import pickle
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene, SchemaValueError

from srstudio import Canvas, cast, cli
from srstudio import head_motion as hm
from srstudio.acting import BENTO
from srstudio.canvas import CanvasError
from srstudio.head_motion import Channel, HeadMotionError, HeadPlan, Spring
from srstudio.rig import Performance, RigError, blinks, check_place


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=4)
    return Canvas(scene, font_asset=None)


STYLE = BENTO.head_rig.style


@pytest.mark.parametrize(
    'field,value,code',
    [
        ('signature', '!', 'head.style.signature'),
        ('breath_period', 0, 'head.style.range'),
        ('nod_share', 2, 'head.style.range'),
        ('glance_face', -1, 'head.style.range'),
        ('nod_roll', -1, 'head.style.range'),
        ('breath_scale', 0.1, 'head.style.range'),
        ('idle_hz', 'slow', 'head.style.number'),
        ('follow', None, 'head.style.number'),
        ('seed', 0.5, 'head.style.seed'),
        ('head', 'spring', 'head.style.spring'),
        ('settle', None, 'head.style.spring'),
        ('nod_px', float('nan'), 'head.style.number'),
    ],
)
def test_style_error_names_the_field_and_its_repair(field, value, code):
    with pytest.raises(HeadMotionError) as caught:
        replace(STYLE, **{field: value})
    data = caught.value.to_dict()
    assert data['code'] == code and data['path'] == f'style.{field}'
    assert data['expected'] and data['remedy']
    json.dumps(data, allow_nan=False)


@pytest.mark.parametrize(
    'field,value,code',
    [
        ('frequency', 0, 'head.spring.range'),
        ('damping', 3, 'head.spring.range'),
        ('anticipation', 1, 'head.spring.range'),
        ('frequency', 'fast', 'head.spring.number'),
        ('damping', True, 'head.spring.number'),
        pytest.param('frequency', 10**10000, 'head.spring.number', id='extreme-frequency'),
    ],
)
def test_spring_errors_keep_the_exception_and_report_the_parameter(field, value, code):
    with pytest.raises(HeadMotionError) as caught:
        Spring(**{'frequency': 3, 'damping': 0.8, **{field: value}})
    data = caught.value.to_dict()
    assert data['path'] == f'spring.{field}' and data['code'] == code
    assert data['expected'] and data['remedy']
    assert len(json.dumps(data, allow_nan=False)) < 5000


@pytest.mark.parametrize(
    'kwargs,code,path',
    [
        ({'curve': 'smoth'}, 'head.channel.curve', 'channel.curve'),
        ({'curve': []}, 'head.channel.curve', 'channel.curve'),
        ({'spring': 'spring'}, 'head.channel.spring', 'channel.spring'),
        ({'keys': None}, 'head.channel.keys', 'channel.keys'),
        ({'keys': ((0,),)}, 'head.channel.keys', 'channel.keys[0]'),
        ({'keys': ((0, float('inf')),)}, 'head.channel.number', 'channel.keys[0][1]'),
        ({'keys': ((float('nan'), 0),)}, 'head.channel.number', 'channel.keys[0][0]'),
        ({'keys': ((1, 0), (0, 1))}, 'head.channel.order', 'channel.keys[1][0]'),
    ],
)
def test_channel_failures_are_typed_before_unpacking_or_curve_lookup(kwargs, code, path):
    with pytest.raises(HeadMotionError) as caught:
        Channel(**kwargs)
    data = caught.value.to_dict()
    assert data['code'] == code and data['path'] == path
    assert data['expected'] and data['remedy']


def test_channel_sample_and_plan_bound_failures_are_repairable():
    with pytest.raises(HeadMotionError) as caught:
        Channel().sample(float('inf'))
    assert caught.value.to_dict()['path'] == 'channel.sample.time'
    plan = HeadPlan(turn=Channel(((0, 100),)))
    with pytest.raises(HeadMotionError) as caught:
        plan.check_bounds(STYLE)
    data = caught.value.to_dict()
    assert data['code'] == 'head.bounds' and data['path'] == 'head.turn'
    assert data['actual'] and data['expected'] and data['remedy']


@pytest.mark.parametrize(
    'mouth,code,path',
    [
        (123, 'rig.mouth.shape', 'performance.mouth'),
        (((0,),), 'rig.mouth.shape', 'performance.mouth[0]'),
        (((-1, 'rest'),), 'rig.mouth.time', 'performance.mouth[0][0]'),
        (((0, 'invented'),), 'rig.mouth.pose', 'performance.mouth[0][1]'),
        (((0, 10**10000),), 'rig.mouth.pose', 'performance.mouth[0][1]'),
    ],
)
def test_actor_mouth_failures_leave_scene_and_actor_reusable(mouth, code, path):
    cv = canvas()
    actor = cast.Manager(cv)
    before, state = cv.scene.to_bytes(), vars(actor).copy()
    with pytest.raises(RigError) as caught:
        actor.build(cv.comp, 0, 0, perf=Performance(mouth=mouth))
    data = caught.value.to_dict()
    assert data['code'] == code and data['path'] == path
    assert data['expected'] and data['remedy']
    assert cv.scene.to_bytes() == before and vars(actor) == state
    actor.build(cv.comp, 0, 0)
    fresh = canvas()
    cast.Manager(fresh).build(fresh.comp, 0, 0)
    assert cv.scene.to_bytes() == fresh.scene.to_bytes()


@pytest.mark.parametrize('kwargs,path', [({'end': 0}, 'end'), ({'perf': 123}, 'performance')])
def test_actor_request_fields_fail_before_drawing(kwargs, path):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(RigError) as caught:
        cast.Manager(cv).build(cv.comp, 0, 0, **kwargs)
    assert caught.value.to_dict()['path'] == path
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('field,value', [('period', 0), ('phase', -1), ('end', float('inf'))])
def test_blink_configuration_reports_the_bad_field(field, value):
    cv = canvas()
    eyes = cv.group(cv.comp, 'eyes')
    before = cv.scene.to_bytes()
    with pytest.raises(RigError) as caught:
        blinks(cv, eyes, **{'end': 4, 'period': 3, 'phase': 0.2, 'skip_empty': True, field: value})
    assert caught.value.to_dict()['path'] == f'blink.{field}'
    assert caught.value.to_dict()['remedy']
    assert cv.scene.to_bytes() == before


def test_blink_work_budget_is_checked_before_generating_keys():
    class TinyPeriod(float):
        additions = 0

        def __radd__(self, other):
            self.additions += 1
            if self.additions > 4:
                raise AssertionError('Refuse the oversized schedule before iterating it')
            return other + float(self)

    period = TinyPeriod(1e-8)
    cv = canvas()
    eyes = cv.group(cv.comp, 'eyes')
    before = cv.scene.to_bytes()
    with pytest.raises(RigError) as caught:
        blinks(cv, eyes, 4, period=period, phase=0.2, skip_empty=True)
    assert period.additions == 0
    assert caught.value.to_dict()['code'] == 'rig.blink.budget'
    assert caught.value.to_dict()['path'] == 'blink.period'
    assert cv.scene.to_bytes() == before


def test_visibility_errors_identify_malformed_blink_spans_before_drawing():
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(CanvasError) as caught:
        cast.Manager(cv).build(cv.comp, 0, 0, perf=Performance(blinks=((0,),)))
    data = caught.value.to_dict()
    assert data['path'] == 'visibility[0]' and data['expected'] and data['remedy']
    assert cv.scene.to_bytes() == before


def test_placement_preserves_the_callers_error_type_with_repair_fields():
    with pytest.raises(RigError) as caught:
        check_place(0, 4, RigError)
    assert str(caught.value) == "a character's scale must be > 0, got 0"
    assert caught.value.to_dict()['path'] == 'scale'
    assert caught.value.to_dict()['expected']


@pytest.mark.parametrize(
    'bad,path',
    [(((0, 0), (1, float('nan'))), 'keys.rotation[1][1]'), (((0, 0), (float('inf'), 1)), 'keys.rotation[1][0]')],
)
def test_canvas_keys_supply_repair_fields_before_scene_mutation(bad, path):
    cv = canvas()
    node = cv.group(cv.comp, 'head')
    before = cv.scene.to_bytes()
    with pytest.raises(CanvasError) as caught:
        cv.keys(node, 'rotation', bad, hold=False)
    assert caught.value.to_dict()['path'] == path
    assert caught.value.to_dict()['expected'] and caught.value.to_dict()['remedy']
    assert cv.scene.to_bytes() == before


def test_actual_sdk_failure_keeps_all_repair_fields_through_json_cli(monkeypatch, capsys, tmp_path):
    with pytest.raises(HeadMotionError) as caught:
        replace(STYLE, breath_period=0)
    error = caught.value

    (tmp_path / 'invalid_head_style_plugin.py').write_text(
        'from dataclasses import replace\nfrom srstudio.acting import BENTO\n'
        'replace(BENTO.head_rig.style, breath_period=0)\n'
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    assert cli.main(['inspect', 'character', 'bento', '--plugins', 'invalid_head_style_plugin', '--json']) == 2
    out, err = capsys.readouterr()
    assert not out
    assert json.loads(err) == {**error.to_dict(), 'context': {'command': 'inspect'}}
    assert json.loads(err)['path'] == 'style.breath_period'


def test_repair_errors_do_not_execute_an_invalid_values_repr():
    class Opaque:
        def __repr__(self):
            raise AssertionError('Do not execute arbitrary input while reporting it')

    with pytest.raises(HeadMotionError) as caught:
        replace(STYLE, nod_px=Opaque())
    assert caught.value.to_dict()['actual'] == '<Opaque>'


@pytest.mark.parametrize(
    'operation,path',
    [
        (lambda: hm.Word('', 0, 1, (), False), 'word.chars'),
        (lambda: hm.Word('a', 1, 0, ((1, 0),), False), 'word.end'),
        (lambda: hm.Speech(-1, (), ()), 'speech.at'),
        (lambda: hm.Speech(0, (), (float('nan'),)), 'speech.levels[0]'),
        (lambda: hm.plan(STYLE, [], 0), 'duration'),
        (
            lambda: hm.plan(
                STYLE, [hm.Speech(3, (hm.Word('a', 3, 3.5, ((3, 3.5),), False),), (-20,)), hm.Speech(1, (), (-20,))], 4
            ),
            'speech[1].at',
        ),
        (lambda: hm.plan(STYLE, [hm.Speech(0, (hm.Word('a', 0, 5, ((0, 5),), False),), (-20,))], 4), 'speech[0].words'),
        (lambda: HeadPlan(gaze=((0,),)).check_gaze(), 'gaze[0]'),
        (lambda: HeadPlan(turn='right').check_bounds(STYLE), 'head.turn'),
        (lambda: Channel(((0, 0), (1e-8, 1))).sample(0.1e-8), 'channel.keys'),
        (
            lambda: Channel(tuple((float(i * 100), float(i)) for i in range(10)), Spring(0.5, 0.7)).during(0, 1),
            'channel.spring',
        ),
    ],
)
def test_speech_planning_and_channel_failures_have_explicit_paths(operation, path):
    with pytest.raises(HeadMotionError) as caught:
        operation()
    data = caught.value.to_dict()
    assert data['path'] == path
    assert data['expected'] and data['remedy']


def test_placement_retains_custom_sdk_exception_constructor():
    from srstudio.errors import SrstudioError

    class Custom(SrstudioError, ValueError):
        def __init__(self, message):
            super().__init__(message)

    with pytest.raises(Custom) as caught:
        check_place(1, 0, Custom)
    assert caught.value.args == ('a character is drawn for more than 0 s, got 0',)
    assert caught.value.to_dict()['path'] == 'end'


@pytest.mark.parametrize(
    'facing,path',
    [
        (((0, 0.1, 1),), 'facing[0]'),
        (((0, 1, 1), (0.5, 2, -1)), 'facing[1]'),
        (((float('nan'), 1, 1),), 'facing[0]'),
        (((0,),), 'facing[0]'),
    ],
)
def test_facing_repair_identifies_the_authored_interval(facing, path):
    with pytest.raises(HeadMotionError) as caught:
        hm.plan(STYLE, [], 4, facing=facing)
    assert caught.value.to_dict()['path'] == path
    assert caught.value.to_dict()['remedy']


def test_listening_failure_names_heard_input_instead_of_speaking_input():
    line = hm.Speech(0, (hm.Word('a', 0, 5, ((0, 5),), False),), (-20,))
    with pytest.raises(HeadMotionError) as caught:
        hm.plan(STYLE, [], 4, heard=(line,))
    assert caught.value.to_dict()['path'] == 'heard[0].words'


def test_noise_validation_does_not_stringify_extreme_integers():
    with pytest.raises(HeadMotionError) as caught:
        hm.fbm(10**10000, 0.1, 1, 'idle')
    assert caught.value.to_dict()['path'] == 'noise.t'


def test_extreme_gaze_name_preserves_the_repair_failure():
    with pytest.raises(HeadMotionError) as caught:
        HeadPlan(gaze=((0, 10**10000),)).check_gaze()
    data = caught.value.to_dict()
    assert data['code'] == 'gaze.unknown'
    assert data['path'] == 'gaze[0][1]'
    assert len(json.dumps(data, allow_nan=False)) < 5000


def test_documented_agent_repair_recipe_retries_a_typed_style():
    document = Path(__file__).resolve().parents[1] / 'docs/authoring-diagnostics.md'
    section = (
        document.read_text().split('<!-- diagnostic-repair:start -->')[1].split('<!-- diagnostic-repair:end -->')[0]
    )
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'diagnostic-repair-recipe', 'exec'), namespace)
    assert namespace['failure']['path'] == 'style.breath_period'
    assert namespace['repaired'].breath_period == 3
    assert isinstance(namespace['motion'], HeadPlan)


def test_invalid_key_time_retains_schema_catch_and_round_trip_repair_fields():
    cv = canvas()
    node = cv.group(cv.comp, 'head')
    before = cv.scene.to_bytes()
    with pytest.raises(SchemaValueError) as caught:
        cv.keys(node, 'rotation', ((0, 0), (float('nan'), 1)))
    error = caught.value
    assert isinstance(error, CanvasError)
    assert error.to_dict()['path'] == 'keys.rotation[1][0]'
    assert error.to_dict()['code'] == 'canvas.keys.time'
    assert error.to_dict()['remedy']
    restored = pickle.loads(pickle.dumps(error))
    assert isinstance(restored, SchemaValueError)
    assert restored.to_dict() == error.to_dict()
    assert cv.scene.to_bytes() == before

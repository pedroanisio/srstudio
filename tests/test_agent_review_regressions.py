"""Regressions for the agent API review: clocks, evidence, repair and reusable documents."""

import copy
import json
import subprocess

import pytest
from jsonschema import Draft202012Validator
from sr_core.scene import Scene

from srstudio import Canvas, authoring, document_schemas
from srstudio.held_gate import late_changes
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.motion import Action, Motion
from srstudio.limbs.serialization import motion_dict


def canvas(*, local=False):
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=6)
    return Canvas(scene, font_asset=None, held_frames=True, local_time=local)


def recipe(name):
    return next(r['request'] for r in authoring.recipes()['items'] if r['id'] == name)


@pytest.mark.parametrize('name', ['pip', 'gesture', 'carry'])
@pytest.mark.parametrize('nested', [False, True])
def test_fractional_placement_preserves_held_frame_retiming(name, nested):
    data = recipe(name)
    data['interval'] = {'start_s': 0.013, 'end_s': 2.013}
    cv = canvas(local=nested)
    parent = cv.group(cv.comp, 'parent', start=0.119, end=4, timeOffset=0.119) if nested else cv.comp
    authoring.compile_request(cv, parent, authoring.parse_request(data), id='placed')
    cv.place_held()
    assert not late_changes(cv.scene.to_bytes())
    before = cv.scene.to_bytes()
    cv.place_held()
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('task', ['gesture', 'carry'])
def test_compilation_returns_phase_diagnostics_and_measurements(task):
    data = recipe(task)
    if task == 'gesture':
        data['interval'] = {'start_s': 0, 'end_s': 0.09}
        data['motion']['motion']['actions'][0]['duration'] = 0.09
    else:
        data['fps'] = 1  # Both the stroke and recovery fall between samples.
    cv = canvas()
    result = authoring.compile_request(cv, cv.comp, authoring.parse_request(data), id='brief')
    assert any(d.code == 'motion.phase-sampling' for d in result.diagnostics)
    assert result.group in list(cv.scene.iter())
    assert result.motion_reports and result.frames > 0
    report = result.to_dict()
    assert report['diagnostics'] and report['motion_reports']
    assert report['group_id'] == 'brief'
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize(
    'name,arguments,path',
    [
        ('pip', {'cues': [{'time': 0, 'pose': 'invented'}]}, 'arguments.cues[0].pose'),
        (
            'toon-sloth',
            {'poses': [{'start': 0, 'eyes': 'open', 'mouth': 'smile', 'arms': 'rest'}]},
            'arguments.poses[0].eyes',
        ),
        ('gloss-sunny', {'face': [[0, 'open']]}, 'arguments.face[0][1]'),
        (
            'pip',
            {'cues': [{'time': 0, 'pose': 'stand'}], 'mouth_states': [[0, 'invented']]},
            'arguments.mouth_states[0][1]',
        ),
        ('manager', {'mouth': [[0, 'invented']]}, 'arguments.mouth[0][1]'),
    ],
)
def test_bad_vocabulary_is_refused_with_an_exact_repair_path(name, arguments, path):
    data = recipe('gloss-nadia' if name == 'gloss-sunny' else name)
    data.update(character=name, arguments=arguments)
    assert not Draft202012Validator(document_schemas.get('authoring')).is_valid(data)
    with pytest.raises(authoring.AuthoringError) as caught:
        authoring.parse_request(data)
    diagnostic = caught.value.to_dict()
    assert diagnostic['path'] == path
    assert diagnostic['actual'] and diagnostic['expected'] and diagnostic['remedy']


def test_carry_moves_with_the_hand_then_holds_its_release_frame():
    request = authoring.parse_request(recipe('carry'))
    motion = request.motion
    attachment = next(a for a in motion.attachments if a.name == request.attachment)
    times = [attachment.attach + i * (attachment.release - attachment.attach) / 10 for i in range(11)]
    poses = [motion.prop_frame(attachment.name, t) for t in times]
    assert poses[-1].origin.distance(poses[0].origin) > 0.1
    for time, pose in zip(times, poses, strict=True):
        expected = motion.sample(time).hand.frame.compose(attachment.offset)
        assert pose.origin.distance(expected.origin) < 1e-8
        assert pose.rotation == expected.rotation
    held = motion.prop_frame(attachment.name, attachment.release)
    assert motion.prop_frame(attachment.name, 1.9) == held


def test_builder_semantic_errors_keep_repair_fields_and_rollback():
    data = recipe('pip')
    data['arguments']['cues'][0]['time'] = 0.1  # Structurally valid, but this rig must begin at zero.
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(authoring.AuthoringError) as caught:
        authoring.compile_request(cv, cv.comp, authoring.parse_request(data), id='invalid')
    diagnostic = caught.value.to_dict()
    assert diagnostic['path'] == 'arguments'
    assert diagnostic['actual'] and diagnostic['expected'] and diagnostic['remedy']
    assert cv.scene.to_bytes() == before and cv._held == []


@pytest.mark.parametrize('legacy', [False, True])
def test_exported_motion_is_json_data_and_direct_authoring_input(legacy):
    from srstudio.limbs.motion import MotionStyle

    motion = Motion(
        ArmProfile(),
        HUMAN,
        (Action('present', duration=2, style=MotionStyle(envelope='legacy' if legacy else 'minimum-jerk')),),
    )
    data = recipe('gesture')
    exported = motion_dict(motion)
    assert exported == json.loads(json.dumps(exported))
    data['motion'] = exported
    before = copy.deepcopy(data)
    restored = authoring.parse_request(data).motion
    assert restored.sample(0.3) == motion.sample(0.3)
    assert data == before


@pytest.mark.parametrize('nested', [False, True])
def test_renderer_uses_the_correct_source_frame_after_fractional_placement(scene_render, tmp_path, nested):
    import math

    cv = canvas()
    parent = cv.group(cv.comp, 'parent', start=0.119, end=4, timeOffset=0.119) if nested else cv.comp
    data = recipe('gesture')
    data['interval'] = {'start_s': 0.013, 'end_s': 2.013}
    authoring.compile_request(cv, parent, authoring.parse_request(data), id='placed')
    cv.place_held()
    path = tmp_path / 'placed.xml'
    path.write_bytes(cv.scene.to_bytes())
    origin = 0.013 + (0.119 if nested else 0)
    first = math.ceil(origin * 24)
    for frame in range(first, first + 4):
        time = frame / 24
        result = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        nodes = json.loads(result.stdout)['result']['nodes']
        visible = [n['id'] for n in nodes if '-frame-' in n['id'] and n['opacity'] > 0.99]
        source_frame = math.floor((time - origin) * 24)
        assert visible == [f'placed-motion-frame-{source_frame:06d}-body']

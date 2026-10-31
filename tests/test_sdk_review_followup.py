"""Regression cases for composed blinking, rotation winding and agent-facing discovery/errors."""

import json
import math
import subprocess
from dataclasses import replace
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, cast, describe
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.errors import LimbError
from srstudio.limbs.math3d import Frame, Quaternion, Vec3
from srstudio.limbs.motion import Action, Motion, TransformKey, TransformTrack
from srstudio.limbs.serialization import motion_dict, parse_motion
from srstudio.rig import Performance


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=2)
    return Canvas(scene, font_asset=None)


@pytest.mark.parametrize(
    'spans', [((0.1, 0.3), (0.2, 0.4)), ((0.1, 0.4), (0.2, 0.3)), ((0.1, 0.2), (0.2, 0.4)), ((0.2, 0.2),)]
)
def test_open_and_closed_eyes_are_complementary(spans, scene_render, tmp_path):
    cv = canvas()
    actor = cast.Manager(cv)
    actor.build(cv.comp, 0, 0, 1, Performance(blinks=spans))
    path = tmp_path / 'blink.xml'
    path.write_bytes(cv.scene.to_bytes())
    for t in (0, 0.2, 0.25, 0.35, 0.4):
        result = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(t), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = {n['id']: n for n in json.loads(result.stdout)['result']['nodes']}
        closed = float(any(a <= t < b for a, b in spans))
        assert nodes[actor.blink_id]['world_opacity'] == closed
        assert nodes[actor.eyes.id]['world_opacity'] == 1 - closed


@pytest.mark.parametrize('sign', [-1, 1])
@pytest.mark.parametrize('side', ['left', 'right'])
@pytest.mark.parametrize('phase', ['preparation', 'recovery'])
def test_pole_winding_survives_large_and_repeated_root_turns(sign, side, phase):
    offset, scale = (0, 1) if phase == 'preparation' else (2.25, 0.5)
    root = TransformTrack(
        tuple(
            TransformKey(
                offset + scale * t, Frame(rotation=Quaternion.axis_angle(Vec3(1, 0, 0), math.radians(sign * angle)))
            )
            for t, angle in ((0, 0), (0.3, 170), (0.5, 190), (0.7, 350), (0.9, 370))
        )
    )
    motion = Motion(
        ArmProfile(side=side),
        HUMAN,
        (Action('rest', duration=3, preparation=0.4, hold=0.1, pole=Vec3(0, 1, 0)),),
        root=root,
    )
    persisted = motion_dict(motion)
    for t in (0.4, 0.8):
        t = offset + scale * t
        a, b = motion.sample(t - 1e-7), motion.sample(t + 1e-7)
        assert a.arm.elbow.distance(b.arm.elbow) < 1e-4
        assert a.hand.palm[0].distance(b.hand.palm[0]) < 1e-4
    times = [offset + scale * t for t in (0.1, 0.4, 0.8, 1.0)] + [2.999999, 3]
    expected = {t: motion.sample(t) for t in times}
    fresh = replace(motion)
    assert {t: fresh.sample(t) for t in reversed(expected)} == expected
    assert motion_dict(motion) == persisted


def test_pole_preparation_has_a_finite_work_budget():
    root = TransformTrack(tuple(TransformKey(i / 10000, Frame()) for i in range(3200)))
    motion = Motion(ArmProfile(), HUMAN, (Action('rest', pole=Vec3(0, 1, 0), preparation=0.4, hold=0.1),), root=root)
    with pytest.raises(LimbError, match='pole winding.*budget') as caught:
        motion.sample(0.1)
    assert caught.value.code == 'budget'


def test_optional_target_error_preserves_nested_field_and_expected_type():
    data = motion_dict(Motion(ArmProfile(), HUMAN, (Action('point'),)))
    data['motion']['actions'][0]['target'] = {'position': {'x': 'far', 'y': 0, 'z': 0}, 'space': 'world'}
    with pytest.raises(LimbError, match=r'motion\.actions\[0\]\.target\.position\.x.*finite number'):
        parse_motion(data)


@pytest.mark.parametrize(
    'target, message',
    [
        ({'position': {'x': 0, 'y': 0, 'z': 0}, 'space': 'moon'}, 'target space must be relative or world'),
        ({}, 'missing required fields'),
        ({'positon': {}}, 'unknown fields'),
        ('there', 'expected a Target object'),
    ],
)
def test_optional_target_validation_reports_its_path_and_reason(target, message):
    data = motion_dict(Motion(ArmProfile(), HUMAN, (Action('point'),)))
    data['motion']['actions'][0]['target'] = target
    with pytest.raises(LimbError, match=r'motion\.actions\[0\]\.target.*' + message):
        parse_motion(data)


@pytest.mark.parametrize('name', ['toon-sloth', 'toon-goat', 'toon-hamster'])
def test_critter_inspection_explains_and_executes_pose_recipe(name):
    info = describe('character', name)
    for contract in ('srstudio.toon.Pose', 'EYES', 'MOUTHS', 'ARMS', 'seconds', 'limbs'):
        assert contract in info['documentation']
    assert info['examples']
    for example in info['examples']:
        cv = canvas()
        exec(example, {'ep': SimpleNamespace(cv=cv, comp=cv.comp)})
        assert list(cv.comp.iter('shape'))
        assert cv.scene.check() == []

"""Passing poses preserve linear and angular velocity instead of stopping at every authored key."""

import json
import math
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.errors import LimbError
from srstudio.limbs.math3d import Frame, Quaternion, Vec3
from srstudio.limbs.motion import Motion, TransformKey, TransformTrack
from srstudio.limbs.serialization import motion_dict, parse_motion


def moving():
    return TransformTrack(
        tuple(
            TransformKey(t, Frame(Vec3(t, t / 3, 0), Quaternion.axis_angle(Vec3(0, 0, 1), t / 4)))
            for t in (0, 1, 2.5, 4)
        ),
        interpolation='continuous',
    )


@pytest.mark.parametrize('time', [1, 2.5])
def test_continuous_track_passes_keys_with_nonzero_matching_velocity(time):
    track = moving()
    h = 1e-5
    a, b, c = (track.sample(t) for t in (time - h, time, time + h))
    incoming, outgoing = (b.origin - a.origin) / h, (c.origin - b.origin) / h
    assert incoming.distance(Vec3(1, 1 / 3, 0)) < 1e-5
    assert incoming.distance(outgoing) < 1e-5
    assert b.origin.distance(Vec3(time, time / 3, 0)) < 1e-12
    va = (a.rotation.inverse() * b.rotation).rotation_vector / h
    vb = (b.rotation.inverse() * c.rotation).rotation_vector / h
    assert va.distance(Vec3(0, 0, 0.25)) < 1e-5
    assert va.distance(vb) < 1e-5


def test_explicit_boundary_velocities_are_respected():
    velocity, angular = Vec3(0.4, 0.2, 0), Vec3(0.1, 0, 0)
    track = TransformTrack(
        (
            TransformKey(0, Frame(), velocity=velocity, angular_velocity=angular),
            TransformKey(2, Frame(Vec3(1, 0, 0)), velocity=velocity, angular_velocity=angular),
        ),
        interpolation='continuous',
    )
    h = 1e-5
    for a, b in [(track.sample(0), track.sample(h)), (track.sample(2 - h), track.sample(2))]:
        assert ((b.origin - a.origin) / h).distance(velocity) < 1e-4
        assert ((a.rotation.inverse() * b.rotation).rotation_vector / h).distance(angular) < 1e-4


def test_continuous_track_is_history_independent_and_holds_outside():
    track = moving()
    times = (0, 0.1, 1, 2.1, 4)
    expected = [track.sample(t) for t in times]
    assert [track.sample(t) for t in reversed(times)] == list(reversed(expected))
    assert track.sample(-1) == expected[0]
    assert track.sample(5) == expected[-1]


def test_default_track_keeps_existing_stop_at_key_behavior():
    track = replace(moving(), interpolation='smooth')
    h = 1e-5
    assert track.sample(1).origin.distance(track.sample(1 - h).origin) / h < 1e-6


@pytest.mark.parametrize('change', [{'interpolation': 'typo'}, {'interpolation': 'smooth'}])
def test_velocity_is_not_silently_ignored_by_incompatible_modes(change):
    keys = (TransformKey(0, Frame(), velocity=Vec3(1, 0, 0)), TransformKey(1, Frame()))
    with pytest.raises(LimbError):
        TransformTrack(keys, **change)


def test_rotation_vectors_handle_identity_and_antipodal_quaternions():
    assert Quaternion().rotation_vector == Vec3()
    q = Quaternion.axis_angle(Vec3(0, 1, 0), 0.7)
    assert q.rotation_vector.distance((-q).rotation_vector) < 1e-12
    assert (
        Quaternion.from_rotation_vector(q.rotation_vector).rotate(Vec3(1, 0, 0)).distance(q.rotate(Vec3(1, 0, 0)))
        < 1e-12
    )


def test_excessive_angular_velocity_is_rejected_before_sampling():
    with pytest.raises(LimbError, match='angular'):
        TransformTrack(
            (TransformKey(0, Frame(), angular_velocity=Vec3(10 * math.pi, 0, 0)), TransformKey(1, Frame())),
            interpolation='continuous',
        )


def test_continuous_track_round_trips_through_versioned_motion_document():
    motion = Motion(ArmProfile(), HUMAN, root=moving())
    data = motion_dict(motion)
    assert data['schema'] == 'srstudio.limbs/1.4.0'
    assert parse_motion(data) == motion
    data['schema'] = 'srstudio.limbs/1.1.0'
    del data['motion']['joins']
    with pytest.raises(LimbError, match='1.2.0'):
        parse_motion(data)


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0'])
def test_historical_documents_keep_smooth_track_defaults(version):
    data = motion_dict(Motion(ArmProfile(), HUMAN))
    data['schema'] = f'srstudio.limbs/{version}'
    del data['motion']['joins']
    root = data['motion']['root']
    del root['interpolation']
    for key in root['keys']:
        del key['velocity'], key['angular_velocity']
    if version == '1.0.0':
        for digit in data['motion']['hand']['digits']:
            del digit['bend_axis']
    assert parse_motion(data) == Motion(ArmProfile(), HUMAN)


def test_continuous_root_survives_native_compilation(scene_render, tmp_path):
    from sr_core.scene import Scene

    from srstudio import Canvas
    from srstudio.limbs.compile import BakeOptions, compile_motion
    from srstudio.limbs.projection import Camera

    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=4)
    cv = Canvas(scene, font_asset=None)
    motion = Motion(ArmProfile(), HUMAN, root=moving())
    camera = Camera(origin=(100, 100), scale=50)
    compile_motion(cv, cv.comp, motion, id='flow', backend='native', camera=camera, options=BakeOptions(fps=4))
    path = tmp_path / 'flow.xml'
    path.write_bytes(scene.to_bytes())
    for time in (0.75, 1, 1.25, 2.5):
        result = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            check=True,
            capture_output=True,
            text=True,
        )
        nodes = json.loads(result.stdout)['result']['nodes']
        target = next(node for node in nodes if node['id'] == 'flow-target')
        assert target['world'][4:6] == pytest.approx(camera.project(motion.sample(time).arm.wrist).xy, abs=1e-3)


def test_documented_passing_pose_recipe_runs():
    text = (Path(__file__).resolve().parents[1] / 'docs/catalog/limbs.md').read_text()
    section = text.split('<!-- continuous-track:start -->')[1].split('<!-- continuous-track:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'continuous-track-recipe', 'exec'), namespace)
    track = namespace['track']
    assert (track.sample(1.00001).origin.x - track.sample(0.99999).origin.x) / 0.00002 == pytest.approx(0.2)

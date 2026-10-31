"""Continuity, clock and compilation contracts exposed by the SDK ergonomics review."""

import json
import math
import subprocess
from dataclasses import replace
from unittest.mock import patch

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, staging
from srstudio.limbs import HUMAN, ArmProfile
from srstudio.limbs.compile import BakeOptions, LayerTargets, compile_motion
from srstudio.limbs.integration import LimbTrack, prepare_tracks
from srstudio.limbs.math3d import Frame, Quaternion, Vec3
from srstudio.limbs.motion import Action, Contact, Motion, TransformKey, TransformTrack


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=100, height=100, fps='24', duration=4)
    return Canvas(scene, font_asset=None)


def test_rotating_root_does_not_switch_pole_rotation_branch():
    root = TransformTrack(
        tuple(
            TransformKey(t, Frame(rotation=Quaternion.axis_angle(Vec3(1, 0, 0), angle)))
            for t, angle in ((0, -0.2), (0.8, 0.2))
        )
    )
    motion = Motion(
        ArmProfile(), HUMAN, (Action('rest', duration=2, preparation=0.4, hold=0.2, pole=Vec3(0, 1, 0)),), root=root
    )
    before, after = motion.sample(0.4 - 1e-6), motion.sample(0.4 + 1e-6)
    assert before.arm.elbow.distance(after.arm.elbow) < 1e-4
    assert before.hand.palm[0].distance(after.hand.palm[0]) < 1e-4
    expected = {t: motion.sample(t) for t in (0.1, 0.4, 0.7, 1.5)}
    assert {t: motion.sample(t) for t in reversed(expected)} == expected


@pytest.mark.parametrize('edge', [1, 2])
def test_moving_contact_matches_wrist_velocity_at_acquisition_and_release(edge):
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=3),))
    grip = base.sample(1).hand.frame
    track = TransformTrack(
        (TransformKey(0, grip), TransformKey(3, Frame(grip.origin + Vec3(0.15, 0, 0), grip.rotation)))
    )
    motion = replace(base, contacts=(Contact('moving', 1, 2, track),))
    h = 1e-5
    a, b, c = (motion.sample(t).arm.wrist for t in (edge - h, edge, edge + h))
    assert ((b - a) / h).distance((c - b) / h) < 1e-3
    assert b.distance(track.sample(edge).origin) < 1e-9


@pytest.mark.parametrize('edge', [1, 2])
def test_rotating_contact_matches_hand_angular_speed_at_its_boundaries(edge):
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=3),))
    grip = base.sample(1).hand.frame
    track = TransformTrack(
        (
            TransformKey(0, grip),
            TransformKey(3, Frame(grip.origin, grip.rotation * Quaternion.axis_angle(Vec3(0, 1, 0), 0.1))),
        )
    )
    motion = replace(base, contacts=(Contact('rotating', 1, 2, track),))
    h = 1e-5
    a, b, c = (motion.sample(t).hand.frame.rotation for t in (edge - h, edge, edge + h))

    def speed(a, b):
        q = a.inverse() * b
        return 2 * math.atan2(math.hypot(q.x, q.y, q.z), abs(q.w)) / h

    assert abs(speed(a, b) - speed(b, c)) < 1e-3


@pytest.mark.parametrize('change', ['motion', 'camera', 'options', 'occlusion'])
def test_prepared_track_invalidates_changed_inputs(change):
    from srstudio.limbs.compile import Occlusion
    from srstudio.limbs.projection import Camera

    cv = canvas()
    original = LimbTrack(Motion(ArmProfile(), HUMAN), options=BakeOptions(duration=1))
    prepared = prepare_tracks(cv, (original,), 1)[0]
    updates = {
        'motion': Motion(ArmProfile(), HUMAN, (Action('point', duration=1),)),
        'camera': Camera(scale=45),
        'options': BakeOptions(fps=12, duration=1),
        'occlusion': (Occlusion('palm', 0, 1, visible=False),),
    }
    changed = replace(prepared, **{change: updates[change]})
    changed.draw(cv, LayerTargets(cv.comp, cv.comp, cv.comp), id='arm')
    fresh = canvas()
    replace(changed, _prepared=None).draw(fresh, LayerTargets(fresh.comp, fresh.comp, fresh.comp), id='arm')
    assert fresh.scene.to_bytes() == cv.scene.to_bytes()


def test_prepared_track_keeps_budget_and_failure_atomicity_checks():
    from srstudio.limbs.errors import LimbError
    from srstudio.limbs.motion import Target

    cv = canvas()
    original = LimbTrack(Motion(ArmProfile(), HUMAN), options=BakeOptions(duration=1))
    prepared = prepare_tracks(cv, (original,), 1)[0]
    unreachable = Motion(ArmProfile(), HUMAN, (Action('point', duration=1, target=Target(Vec3(99, 0, 0))),))
    before = cv.scene.to_bytes()
    for changed in (
        replace(prepared, options=BakeOptions(duration=1, max_frames=1)),
        replace(prepared, motion=unreachable),
    ):
        with pytest.raises(LimbError):
            changed.draw(cv, LayerTargets(cv.comp, cv.comp, cv.comp), id='arm')
        assert cv.scene.to_bytes() == before


def test_freeze_refuses_a_curve_crossing_local_freeze_time_atomically():
    from srstudio.staging import StagingError

    cv = canvas()
    shot = cv.group(cv.comp, 'shot')
    node = cv.group(shot, 'moving', start=-1, end=3)
    cv.keys(node, 'x', [(0, 10), (2, 30)], local=True, hold=False)
    before = cv.scene.to_bytes()
    with pytest.raises(StagingError, match='curve'):
        staging.freeze(shot)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('backend', ['native', 'baked'])
def test_implicit_duration_includes_root_track_and_explicit_duration_crops(backend):
    motion = Motion(
        ArmProfile(), HUMAN, root=TransformTrack((TransformKey(0, Frame()), TransformKey(3, Frame(Vec3(0.3, 0, 0)))))
    )
    cv = canvas()
    assert compile_motion(cv, cv.comp, motion, id='full', backend=backend).frames == 72
    assert compile_motion(cv, cv.comp, motion, id='crop', backend=backend, options=BakeOptions(duration=1)).frames == 24


@pytest.mark.parametrize(
    'time_base, keys',
    [
        ('local', [(0, 10), (1, 20), (2, 30)]),
        ('normalized', [(0, 10), (0.25, 20), (0.5, 30)]),
        ('composition', [(-1, 10), (0, 20), (1, 30)]),
    ],
)
def test_freeze_samples_the_nodes_animation_clock(tmp_path, scene_render, time_base, keys):
    cv = canvas()
    shot = cv.group(cv.comp, 'shot')
    node = cv.group(shot, 'moving', start=-1, end=3)
    animation = cv.keys(node, 'x', keys)
    animation.timeBase = time_base
    path = tmp_path / 'clock.xml'

    def position(t):
        path.write_bytes(cv.scene.to_bytes())
        result = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(t), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        return next(n['world'][4] for n in json.loads(result.stdout)['result']['nodes'] if n['id'] == 'moving')

    expected = position(0)
    assert expected == 20
    staging.freeze(shot)
    assert position(0) == position(1) == expected


def test_report_identifies_wrist_metrics_and_reports_elbow_and_hand_rotation():
    cv = canvas()
    motion = Motion(ArmProfile(), HUMAN, (Action('rest', duration=2, pole=Vec3(0, 1, 0)),))
    report = compile_motion(cv, cv.comp, motion, id='moving-elbow').report
    assert report.max_speed == 0
    assert report.max_elbow_speed > 0
    assert report.max_hand_angular_speed > 0
    metadata = report.to_dict()['metric_definitions']
    assert metadata['max_speed'] == {'subject': 'wrist', 'space': 'world', 'unit': 'canonical units/second'}
    assert metadata['max_hand_angular_speed']['unit'] == 'radians/second'


def test_prepared_track_reuses_sampling_and_projection_without_changing_output():
    from srstudio.limbs import compile as compiler

    cv = canvas()
    track = LimbTrack(Motion(ArmProfile(), HUMAN), options=BakeOptions(duration=1))
    with patch.object(Motion, 'sample', autospec=True, side_effect=Motion.sample) as sample:
        with patch.object(compiler, 'project_pose', wraps=compiler.project_pose) as project:
            prepared = prepare_tracks(cv, (track,), 1)[0]
            prepared.draw(cv, LayerTargets(cv.comp, cv.comp, cv.comp), id='arm')
    assert sample.call_count <= 25
    assert project.call_count <= 24
    fresh = canvas()
    track.draw(fresh, LayerTargets(fresh.comp, fresh.comp, fresh.comp), id='arm')
    assert fresh.scene.to_bytes() == cv.scene.to_bytes()

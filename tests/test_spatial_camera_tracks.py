"""Spatial interactions follow a bounded scene camera clock without resetting hand/prop motion."""

import re
from dataclasses import replace

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from srstudio.limbs import HUMAN, ArmProfile, Camera, Frame, LimbError, Vec3
from srstudio.limbs import projection as p
from srstudio.limbs.compile import BakeOptions
from srstudio.limbs.interaction import Participant, PropDrawing, bake_interaction
from srstudio.limbs.motion import Action, Motion, TransformKey, TransformTrack
from support.composition import plate_source, prepared_plate_plan
from test_limbs_interaction import canvas, mesh


def track():
    return p.CameraTrack(
        2,
        (
            p.CameraSample(0, Camera(scale=100)),
            p.CameraSample(0.75, Camera(scale=150, origin=(10, 20))),
            p.CameraSample(2, Camera(scale=200)),
        ),
    )


def test_camera_track_is_held_and_history_independent_including_terminal():
    source = track()
    for time, index in ((0.9, 1), (0, 0), (2, 2), (0.749, 0), (0.75, 1), (0, 0)):
        assert source.sample(time) == source.samples[index].camera


@pytest.mark.parametrize(
    'bad', ['duration', 'empty', 'list', 'record', 'late', 'order', 'outside', 'camera', 'time', 'count']
)
def test_invalid_camera_tracks_are_typed(bad):
    duration, samples = 2, (p.CameraSample(0, Camera()),)
    if bad == 'duration':
        duration = True
    elif bad == 'empty':
        samples = ()
    elif bad == 'list':
        samples = list(samples)
    elif bad == 'record':
        samples = ({},)
    elif bad == 'late':
        samples = (p.CameraSample(0.1, Camera()),)
    elif bad == 'order':
        samples *= 2
    elif bad == 'outside':
        samples += (p.CameraSample(3, Camera()),)
    elif bad == 'count':
        samples *= 4098
    with pytest.raises(LimbError):
        if bad == 'camera':
            p.CameraSample(0, {})
        elif bad == 'time':
            p.CameraSample(float('nan'), Camera())
        else:
            p.CameraTrack(duration, samples)


@pytest.mark.parametrize('time', [True, -0.1, 2.1, float('nan'), 'now'])
def test_camera_track_sampling_rejects_invalid_or_out_of_range_times(time):
    with pytest.raises(LimbError):
        track().sample(time)


def test_scene_timeline_builds_camera_track_with_original_shared_parent_pose():
    source = plate_source()
    base = prepared_plate_plan(source)
    motion = m.SceneMotion(
        transforms=(
            m.TransformTrack(
                'host', (m.TransformKey(0, c.Transform(), 'hold'), m.TransformKey(0.75, c.Transform((0.1, 0, 0))))
            ),
        )
    )
    timeline = m.plan_scene(base.spec, base.bindings, motion, rasters=(source,))
    cameras = m.spatial_cameras(timeline, 'host')
    assert [sample.time for sample in cameras.samples] == [0, 0.75]
    for time in (1, 0.3, 0.75, 0):
        plan = m.sample_scene(base.spec, base.bindings, motion, time)
        assert cameras.sample(time) == c.spatial_camera(plan, 'host')
    with pytest.raises(c.CompositionError):
        m.spatial_cameras(replace(timeline, digest='a' * 64))


def test_interaction_samples_motion_at_the_off_grid_camera_cut_and_preserves_scene_offset():
    cv = canvas()
    motion = TransformTrack((TransformKey(0, Frame()), TransformKey(1, Frame(Vec3(0.3, 0, 0)))))
    prop = PropDrawing(mesh(), motion)
    result = bake_interaction(
        cv, cv.comp, (), (prop,), id='moving', camera=track(), options=BakeOptions(fps=2, duration=1, offset=0.5)
    )
    assert result.frames == 3
    # Source times are 0, .25, .5; scene camera times are .5, .75, 1.
    shapes = list(cv.scene.iter('shape'))
    for shape, local in zip(shapes, (0, 0.25, 0.5), strict=True):
        expected = track().sample(local + 0.5).project(mesh().faces[0].vertices[0], frame=motion.sample(local)).xy
        first = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', shape.attributes()['path'])[:2]]
        assert first == pytest.approx(expected, abs=1e-5)
    assert cv.scene.check(schema=True) == []


def test_interaction_projects_hand_and_prop_through_the_same_camera_samples():
    cv = canvas()
    motion = Motion(ArmProfile(), HUMAN, (Action('point', duration=2),))
    result = bake_interaction(
        cv,
        cv.comp,
        (Participant('right', motion),),
        (PropDrawing(mesh(), TransformTrack.constant(Frame())),),
        id='shared',
        camera=track(),
        options=BakeOptions(fps=2, duration=2),
    )
    assert result.frames == 5
    assert result.reports[0][1].max_bone_error < 1e-8
    assert all(order == tuple(sorted(order, key=lambda item: (item[1], item[0]))) for order in result.depth_orders)
    assert cv.scene.check(schema=True) == []


@pytest.mark.parametrize('bad', ['budget', 'end', 'collapsed'])
def test_camera_timing_failures_leave_interaction_scene_unchanged(bad):
    cv = canvas()
    before = cv.scene.to_bytes()
    camera = track()
    options = BakeOptions(fps=2, duration=2, max_frames=4 if bad == 'budget' else 2400)
    if bad == 'end':
        options = replace(options, offset=0.5)
    elif bad == 'collapsed':
        camera = p.CameraTrack(2, (p.CameraSample(0, Camera()), p.CameraSample(1e-8, Camera(scale=200))))
    with pytest.raises(LimbError):
        bake_interaction(
            cv,
            cv.comp,
            (),
            (PropDrawing(mesh(), TransformTrack.constant(Frame())),),
            id='failed',
            camera=camera,
            options=options,
        )
    assert cv.scene.to_bytes() == before


def test_camera_cut_keeps_exact_scene_time_after_subtracting_the_bake_offset():
    cv = canvas()
    camera = p.CameraTrack(1, (p.CameraSample(0, Camera(scale=100)), p.CameraSample(0.21, Camera(scale=200))))
    assert (0.21 - 0.05) + 0.05 < 0.21  # this float round trip selects the wrong held view
    bake_interaction(
        cv,
        cv.comp,
        (),
        (PropDrawing(mesh(), TransformTrack.constant(Frame())),),
        id='exact',
        camera=camera,
        options=BakeOptions(fps=2, duration=0.5, offset=0.05),
    )
    shape = list(cv.scene.iter('shape'))[1]
    first = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', shape.attributes()['path'])[:2]]
    assert first == pytest.approx(camera.samples[1].camera.project(mesh().faces[0].vertices[0]).xy)


def test_released_prop_holds_its_source_pose_while_the_scene_camera_continues():
    from srstudio.limbs.interaction import AttachedProp
    from srstudio.limbs.motion import Attachment

    cv = canvas()
    base = Motion(ArmProfile(), HUMAN, (Action('grasp', duration=0.5),))
    initial = base.sample(0.1).hand.frame
    motion = replace(base, attachments=(Attachment('panel', 0.1, 0.5, initial),))
    prop = AttachedProp(motion, 'panel')
    result = bake_interaction(
        cv, cv.comp, (), (PropDrawing(mesh(), prop),), id='held', camera=track(), options=BakeOptions(fps=2)
    )
    assert result.frames == 5
    for shape, local in zip(cv.scene.iter('shape'), (0, 0.5, 0.75, 1, 1.5), strict=True):
        expected = track().sample(local).project(mesh().faces[0].vertices[0], frame=prop.sample(min(local, 0.5))).xy
        first = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', shape.attributes()['path'])[:2]]
        assert first == pytest.approx(expected, abs=1e-5)


def test_a_later_near_plane_failure_refuses_the_entire_interaction_before_drawing():
    cv = canvas()
    before = cv.scene.to_bytes()
    camera = p.CameraTrack(
        2, (p.CameraSample(0, Camera()), p.CameraSample(0.75, Camera(projection='perspective', distance=0.05)))
    )
    with pytest.raises(LimbError):
        bake_interaction(
            cv,
            cv.comp,
            (),
            (PropDrawing(mesh(), TransformTrack.constant(Frame())),),
            id='unsafe',
            camera=camera,
            options=BakeOptions(fps=2, duration=2),
        )
    assert cv.scene.to_bytes() == before


def test_engine_observes_exact_camera_cut_with_scene_offset(tmp_path, scene_render):
    import json

    from srstudio._bounded_process import ProcessLimits, run

    cv = canvas()
    camera = p.CameraTrack(2, (p.CameraSample(0, Camera()), p.CameraSample(0.21, Camera(scale=200))))
    bake_interaction(
        cv,
        cv.comp,
        (),
        (PropDrawing(mesh(), TransformTrack.constant(Frame())),),
        id='cut',
        camera=camera,
        options=BakeOptions(fps=2, duration=0.5, offset=0.05),
    )
    path = tmp_path / 'scene.xml'
    path.write_bytes(cv.scene.to_bytes())
    for time, expected in ((0.21, 1), (0.209, 0), (0.3, 1), (0.05, 0), (0.21, 1)):
        result = run(
            (str(scene_render), 'eval', str(path), '--time', str(time), '--json'),
            input=b'',
            limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3, stdout_bytes=65536, stderr_bytes=65536),
        )
        active = [
            node['id']
            for node in json.loads(result.stdout)['result']['nodes']
            if node['id'].startswith('cut-frame-') and node['world_opacity'] > 0.5
        ]
        assert active == [f'cut-frame-{expected:06d}']


def test_documented_spatial_camera_bridge_executes():
    from pathlib import Path

    guide = (Path(__file__).parents[1] / 'docs/composition-preflight.md').read_text()
    namespace = {}
    for title in ('Plan a scene timeline', 'Register a spatial camera'):
        section = guide.split('## ' + title + '\n', 1)[1]
        snippet = section.split('```python\n', 1)[1].split('```', 1)[0]
        exec(compile(snippet, '<spatial-camera-guide>', 'exec'), namespace)
    assert namespace['cameras'].sample(0) == namespace['camera']


def test_camera_bridge_return_types_are_resolvable_for_agent_introspection():
    from typing import get_type_hints

    assert get_type_hints(c.spatial_camera)['return'] is Camera
    assert get_type_hints(m.spatial_cameras)['return'] is p.CameraTrack

"""Frame clocks, directed head motion and actionable quality evidence compose correctly."""

import inspect
import json
import subprocess

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio import head_motion as hm
from srstudio.limbs import HUMAN, ArmProfile, Frame, HandControl, LimbError, Vec3
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.geometry import project_pose
from srstudio.limbs.interaction import Participant, bake_interaction
from srstudio.limbs.motion import Action, Motion, Target, TransformKey, TransformTrack
from srstudio.limbs.projection import Camera
from srstudio.limbs.validation import audit
from srstudio.toon_critters import GOAT_RIG, HAMSTER_RIG, SLOTH_RIG
from srstudio.toon_head import _animate, rest_springs
from support.spring_curve import peak


def canvas(fps=24):
    scene = Scene(version='auto')
    scene.add_project(width=100, height=100, fps=str(fps), duration=4)
    return Canvas(scene, font_asset=None)


def evaluate(engine, path, time):
    result = subprocess.run(
        [str(engine), 'eval', str(path), '--time', str(time), '--json'], capture_output=True, text=True, check=True
    )
    return {node['id']: node for node in json.loads(result.stdout)['result']['nodes']}


@pytest.mark.parametrize('deformation', ['contour', 'skin'])
@pytest.mark.parametrize('fps, offset_frames', [(24, 1), (30, 2)])
def test_native_visibility_and_pose_share_the_offset_frame_clock(
    scene_render, tmp_path, deformation, fps, offset_frames
):
    cv = canvas(fps)
    camera = Camera(origin=(0, 0), scale=100)
    motion = Motion(ArmProfile(), HUMAN, (Action('point', duration=1, target=Target(Vec3(0.65, 0.3, 0))),))
    compile_motion(
        cv,
        cv.comp,
        motion,
        id='arm',
        backend='native',
        deformation=deformation,
        camera=camera,
        options=BakeOptions(fps=fps, offset=offset_frames / fps),
    )
    path = tmp_path / 'offset.xml'
    path.write_bytes(cv.scene.to_bytes())
    for frame in (0, 1, 2, 7, fps - 1):
        nodes = evaluate(scene_render, path, (offset_frames + frame) / fps)
        assert nodes['arm']['world_opacity'] == 1
        assert nodes[f'arm-hand-frame-{frame:06d}-body']['world_opacity'] == 1
        assert nodes['arm-target']['world'][4:6] == pytest.approx(
            camera.project(motion.sample(frame / fps).arm.wrist).xy, abs=1e-4
        )
    assert evaluate(scene_render, path, (offset_frames + fps) / fps)['arm']['world_opacity'] == 0


@pytest.mark.parametrize('rig', [GOAT_RIG, SLOTH_RIG, HAMSTER_RIG], ids=['goat', 'sloth', 'hamster'])
@pytest.mark.parametrize('side', [-1, 1])
def test_directed_facing_takes_precedence_over_idle_glances_and_respects_bounds(rig, side):
    plan = hm.plan(rig.style, [], 20, facing=((0, 18, side),))
    assert not any(t < 18 + hm.FACE_DOWN and name != 'ahead' for t, name in plan.gaze)
    for name in ('turn', 'face_x'):
        assert peak(getattr(plan, name)) <= hm.limit(rig.style, name)


def test_facing_reserves_the_head_return_but_keeps_other_seeded_glances():
    style = GOAT_RIG.style
    ordinary = hm.plan(style, [], 30)
    on, off = ordinary.gaze[0][0], ordinary.gaze[1][0]
    # The eyes have returned before facing starts, but the head is still on its way back.
    directed = hm.plan(style, [], 30, facing=((off + 0.1, off + 1, 1),))
    assert not any(t == on for t, _ in directed.gaze)
    untouched = [(t, name) for t, name in ordinary.gaze if t > off + 1 + hm.FACE_DOWN]
    assert untouched
    assert [(t, name) for t, name in directed.gaze if t > off + 1 + hm.FACE_DOWN] == untouched


@pytest.mark.parametrize('times', [(0, 0.1, 0.2), (0, 0.1, 0.1001), (0, 0.001, 0.1)])
def test_acceleration_audit_handles_nonuniform_sample_intervals(times):
    # At each key x=t²/2, so divided differences must report constant acceleration 1.
    root = TransformTrack(tuple(TransformKey(t, Frame(Vec3(t * t / 2, 0, 0))) for t in times))
    motion = Motion(ArmProfile(), HUMAN, root=root)
    samples = tuple(motion.sample(t) for t in times)
    report = audit(samples, tuple(project_pose(s, Camera(), width=motion.arm.width) for s in samples), motion.arm)
    assert report.max_acceleration == pytest.approx(1, abs=1e-8)


def test_partial_final_frame_does_not_inflate_compiled_acceleration():
    motion = Motion(
        ArmProfile(), HUMAN, root=TransformTrack((TransformKey(0, Frame()), TransformKey(2, Frame(Vec3(1, 0, 0)))))
    )
    for duration in (0.5, 0.5001):
        cv = canvas()
        compiled = compile_motion(
            cv, cv.comp, motion, id='arm', backend='baked', options=BakeOptions(duration=duration), hold_until=2
        )
        assert 1 < compiled.report.max_acceleration < 1.5


def invalid_motion():
    return Motion(
        ArmProfile(),
        HUMAN,
        (
            Action('rest', duration=1),
            Action('point', start=1, duration=2, target=Target(Vec3(0.65, 0.3, 0)), control=HandControl(wrist_flex=2)),
        ),
    )


@pytest.mark.parametrize('backend', ['native', 'baked', 'auto', 'interaction'])
def test_compilation_error_identifies_track_action_time_and_field_before_mutation(backend):
    cv = canvas()
    before = cv.scene.to_bytes()
    motion = invalid_motion()
    with pytest.raises(LimbError) as caught:
        if backend == 'interaction':
            bake_interaction(cv, cv.comp, (Participant('actor-right', motion),), (), id='scene')
        else:
            compile_motion(cv, cv.comp, motion, id='actor-right', backend=backend)
    error = caught.value
    assert error.code == 'joint-limit'
    assert error.context['track'] == 'actor-right'
    assert error.context['action'] == 'point'
    assert error.context['action_index'] == 1
    assert error.context['field'] == 'wrist_flex'
    assert 1 < error.context['time'] < 3
    assert 'actor-right' in str(error) and 'point' in str(error)
    with pytest.raises(LimbError) as sampled:
        motion.sample(error.context['time'])
    assert sampled.value.context['action_index'] == 1
    assert sampled.value.code == error.code and sampled.value.residual == error.residual
    assert cv.scene.to_bytes() == before


def test_contextual_errors_preserve_unreachable_code_and_geometric_residual():
    motion = Motion(ArmProfile(), HUMAN, (Action('point', target=Target(Vec3(5, 0, 0), 'world')),))
    cv = canvas()
    with pytest.raises(LimbError) as compiled:
        compile_motion(cv, cv.comp, motion, id='unreachable')
    error = compiled.value
    with pytest.raises(LimbError) as sampled:
        motion.sample(error.context['time'])
    assert error.code == sampled.value.code == 'unreachable'
    assert error.residual == sampled.value.residual > 0
    assert error.context['track'] == 'unreachable'
    assert error.context['action_index'] == 0
    assert isinstance(error.__cause__, LimbError)


def test_spring_reset_is_documented_as_lossy_and_changes_carried_motion(scene_render, tmp_path):
    cv = canvas()
    channel = hm.Channel(((0, 0), (0.1, 10), (0.2, -10), (0.3, 10), (0.4, 0)), hm.Spring(1.4, 0.75))
    original, reset = (cv.group(cv.comp, name) for name in ('original', 'reset'))
    for group in (original, reset):
        _animate(cv, group, 'x', channel)
    rest_springs(reset, run=2)
    path = tmp_path / 'reset.xml'
    path.write_bytes(cv.scene.to_bytes())
    nodes = evaluate(scene_render, path, 0.25)
    assert abs(nodes['original']['world'][4] - nodes['reset']['world'][4]) > 2
    documentation = inspect.getdoc(rest_springs)
    assert 'lossy' in documentation and 'momentum' in documentation
    assert 'figure' in documentation and 'Channel.during' in documentation

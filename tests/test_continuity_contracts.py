"""Discovery distinguishes sampled motion, estimated joins and derivative-preserving source tracks."""

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.acting import BENTO, TransitionPolicy, compile_performance, gloss_actor
from srstudio.limbs import HUMAN, ArmProfile, Camera, Frame, Quaternion, Vec3
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.motion import ActionJoin, Motion, TransformKey, TransformTrack
from support.acting import numeric
from support.gestures import contact_motion, gestures


def trajectory(mode):
    return TransformTrack(
        tuple(
            TransformKey(
                t,
                Frame(Vec3(x, y, z), Quaternion.axis_angle(Vec3(1, 2, 3), angle)),
                velocity=Vec3(0.2, -0.1, 0.05) if mode == 'explicit' else None,
            )
            for t, x, y, z, angle in (
                (0, 0, 0, 0, 0),
                (0.7, 0.3, -0.2, 0.1, 0.3),
                (2.1, 0.7, 0.4, -0.1, 0.8),
                (4, 1, 0, 0, 1),
            )
        ),
        interpolation='continuous' if mode == 'explicit' else mode,
    )


@pytest.mark.parametrize('mode', ['smooth', 'continuous'])
def test_track_discovery_separates_translation_rotation_and_endpoint_holds(mode):
    track = trajectory(mode)
    before = tuple(track.sample(t) for t in (0.3, 0.7, 1.2, 3))
    info = track.describe_continuity()
    assert info['schema'] == 'srstudio.continuity/1.0.0'
    assert info['interior_keys']['translation'] == dict(position=True, velocity=True, acceleration=True)
    assert info['interior_keys']['rotation'] == dict(
        position=True, velocity=mode == 'smooth', acceleration=mode == 'smooth'
    )
    assert all(
        not row['translation_velocity_jump'] and not row['rotation_velocity_jump'] for row in info['endpoint_holds']
    )
    json.dumps(info, allow_nan=False)
    info['interior_keys']['translation']['velocity'] = False
    assert track.describe_continuity()['interior_keys']['translation']['velocity'] is True
    assert tuple(track.sample(t) for t in (0.3, 0.7, 1.2, 3)) == before


def derivatives(sample, at, direction, h=1e-4):
    a, b, c, d = (sample(at + direction * h * i) for i in range(4))
    return (-a * 3 + b * 4 - c) / (2 * direction * h), (a * 2 - b * 5 + c * 4 - d) / (h * h)


@pytest.mark.parametrize('mode', ['smooth', 'continuous', 'explicit'])
@pytest.mark.parametrize('at', [0.7, 2.1])
def test_claimed_translation_derivatives_match_on_nonuniform_spatial_keys(mode, at):
    track = trajectory(mode)

    def sample(t):
        return track.sample(t).origin

    vl, al = derivatives(sample, at, -1)
    vr, ar = derivatives(sample, at, 1)
    assert vl.distance(vr) < 2e-6
    assert al.length < 2e-4 and ar.length < 2e-4
    if mode == 'smooth':
        assert vl.length < 2e-6
    else:
        assert vl.length > 0.1
    times = (at - 0.04, at, at + 0.07)
    assert [track.sample(t) for t in reversed(times)] == list(reversed([track.sample(t) for t in times]))


@pytest.mark.parametrize('at', [0.7, 2.1])
def test_smooth_rotations_stop_with_zero_angular_velocity_and_acceleration(at):
    track = trajectory('smooth')
    inverse = track.sample(at).rotation.inverse()

    def sample(t):
        return (inverse * track.sample(t).rotation).rotation_vector

    for direction in (-1, 1):
        velocity, acceleration = derivatives(sample, at, direction)
        assert velocity.length < 2e-6 and acceleration.length < 2e-4


def test_explicit_endpoint_velocity_is_not_promised_across_the_outer_hold():
    track = TransformTrack(
        (TransformKey(0, Frame(), Vec3(1, 0, 0), Vec3(0, 0, 0.5)), TransformKey(2, Frame(Vec3(1, 0, 0)))),
        interpolation='continuous',
    )
    first, last = track.describe_continuity()['endpoint_holds']
    assert first == dict(at=0, translation_velocity_jump=True, rotation_velocity_jump=True)
    assert last == dict(at=2, translation_velocity_jump=False, rotation_velocity_jump=False)
    incoming, _ = derivatives(lambda t: track.sample(t).origin, 0, -1)
    outgoing, _ = derivatives(lambda t: track.sample(t).origin, 0, 1)
    assert incoming.length == 0 and outgoing.x == pytest.approx(1, abs=1e-6)
    single = TransformTrack((track.keys[0],), interpolation='continuous').describe_continuity()
    assert single['interior_keys']['rotation']['acceleration'] is True
    assert not any(row['translation_velocity_jump'] for row in single['endpoint_holds'])


def test_join_discovery_reports_estimates_and_does_not_certify_the_whole_motion():
    motion = replace(gestures(moving=True), joins=(ActionJoin(0, 1.4, 2.65),))
    info = motion.describe_continuity()
    (join,) = info['joins']
    assert (join['after'], join['start'], join['end']) == (0, 1.4, 2.65)
    assert join['guarantees'] == dict(position=True, velocity=False, acceleration=False)
    assert join['velocity_matching'] == 'estimated'
    assert join['conditions']
    assert info['whole_motion'] == dict(position=False, velocity=False, acceleration=False)
    assert info['emission']['native']['sampling'] == info['emission']['baked']['sampling'] == 'held'
    assert not info['emission']['native']['inherits_source_derivatives']
    json.dumps(info, allow_nan=False)
    # A position/estimated-velocity match is not an acceleration guarantee.
    _, left = derivatives(lambda t: motion.sample(t).arm.wrist, 2.65, -1)
    _, right = derivatives(lambda t: motion.sample(t).arm.wrist, 2.65, 1)
    assert left.distance(right) > 0.01


def test_introspection_preserves_contacts_and_does_not_populate_join_sampling_cache():
    motion = replace(contact_motion(), joins=(ActionJoin(0, 1.5, 2.5),))
    before = motion.sample(1)
    motion.describe_continuity()
    assert motion._join_plans == {}
    assert motion.sample(1) == before and before.contacts[0].residual < 1e-6
    assert motion.describe_continuity()['joins'][0]['start'] == 1.5


def test_continuous_rotation_small_arc_approximation_does_not_claim_exact_c1():
    axis, velocity = Vec3(0, 0, 1), Vec3(0, 0, 0.5)
    track = TransformTrack(
        tuple(
            TransformKey(t, Frame(rotation=Quaternion.axis_angle(axis, angle)), angular_velocity=velocity)
            for t, angle in ((0, 0), (0.1, 0.05), (2.1, 0.8))
        ),
        interpolation='continuous',
    )
    inverse = track.sample(0.1).rotation.inverse()

    def rotation(t):
        return (inverse * track.sample(t).rotation).rotation_vector

    incoming, _ = derivatives(rotation, 0.1, -1, h=1e-5)
    outgoing, _ = derivatives(rotation, 0.1, 1, h=1e-5)
    assert incoming.distance(velocity) < 1e-4 and outgoing.distance(velocity) < 1e-4
    assert incoming.distance(outgoing) > 1e-6
    assert track.describe_continuity()['interior_keys']['rotation']['velocity'] is False


def test_native_emission_holds_between_frames_even_when_source_track_is_continuous(scene_render, tmp_path):
    root = TransformTrack(
        (TransformKey(0, Frame()), TransformKey(1, Frame(Vec3(0.1, 0, 0)))), interpolation='continuous'
    )
    motion = Motion(ArmProfile(), HUMAN, root=root)
    scene = Scene(version='auto')
    scene.add_project(width=400, height=400, fps='24', duration=1)
    cv = Canvas(scene, font_asset=None)
    camera = Camera(origin=(100, 100), scale=100)
    compile_motion(cv, cv.comp, motion, id='held', backend='native', camera=camera, options=BakeOptions(fps=2))
    path = tmp_path / 'held.xml'
    path.write_bytes(scene.to_bytes())
    result = subprocess.run(
        [str(scene_render), 'eval', str(path), '--time', '0.25', '--json'], capture_output=True, text=True, check=True
    )
    nodes = json.loads(result.stdout)['result']['nodes']
    target = next(node for node in nodes if node['id'] == 'held-target')['world'][4:6]
    assert target == pytest.approx(camera.project(motion.sample(0).arm.wrist).xy, abs=1e-4)
    assert target != pytest.approx(camera.project(motion.sample(0.25).arm.wrist).xy, abs=1e-3)


def test_acting_discovery_distinguishes_emitted_keys_discrete_arrivals_and_cuts():
    for rig in (BENTO, gloss_actor('nadia')):
        transitions = rig.describe()['transitions']
        for info in (transitions['continuity'], transitions['policy']['continuity']):
            assert info['source_curve_derivatives_preserved'] is False
            assert info['discrete'] == dict(position=False, velocity=False, acceleration=False)
            assert info['cuts'] == 'same performance source time'
            json.dumps(info, allow_nan=False)


def test_acting_easing_bake_exhibits_a_velocity_jump_and_retains_cut_samples():
    plan = compile_performance(BENTO, numeric(TransitionPolicy(curve='quad-in')))
    channel = plan.head.turn
    h = 1e-7
    candidates = [t for t, _ in channel.keys if 1.2 < t < 1.3]
    at = max(candidates, key=lambda t: abs(channel.sample(t + h) - 2 * channel.sample(t) + channel.sample(t - h)))
    before = (channel.sample(at) - channel.sample(at - h)) / h
    after = (channel.sample(at + h) - channel.sample(at)) / h
    assert abs(before - after) > 1e-3
    cut = plan.window(1.1, 1.5)
    assert cut.sample(at - 1.1) == plan.sample(at)


def test_documented_continuity_discovery_recipe_uses_real_contracts():
    text = (Path(__file__).resolve().parents[1] / 'docs/catalog/limbs.md').read_text()
    section = text.split('<!-- continuity-discovery:start -->')[1].split('<!-- continuity-discovery:end -->')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'continuity-discovery-recipe', 'exec'), namespace)
    assert namespace['track_info']['interior_keys']['translation']['acceleration'] is True
    assert namespace['motion_info']['joins'][0]['velocity_matching'] == 'estimated'

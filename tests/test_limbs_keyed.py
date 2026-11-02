"""Externally solved samples enter public Motion playback without a private subclass."""

import json
import math
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile, Camera, LimbError, Vec3
from srstudio.limbs.compile import BakeOptions, bake
from srstudio.limbs.motion import Action, Motion
from srstudio.limbs.serialization import motion_dict, parse_motion


def inputs():
    original = Motion(ArmProfile(), HUMAN, (Action('point', duration=1),))
    samples = tuple(original.sample(i / 4) for i in range(4))
    return original, samples


def test_keyed_motion_holds_until_the_exact_next_sample_and_is_random_access():
    original, samples = inputs()
    motion = original.keyed(samples, fps=4)
    assert isinstance(motion, Motion)
    assert motion.end == 1
    for time, index in ((0.5, 2), (0, 0), (0.249999, 0), (0.25, 1), (0.75, 3), (2, 3), (0.5, 2)):
        assert motion.sample(time) == replace(samples[index], time=time)
    assert original.actions and not motion.actions
    assert motion.describe_continuity()['interpolation'] == 'hold'
    assert motion.describe_continuity()['schema'] == 'srstudio.continuity/1.0.0'
    assert motion.describe_continuity()['whole_motion'] == dict(position=False, velocity=False, acceleration=False)


def test_keyed_motion_freezes_the_outer_sample_collection():
    original, samples = inputs()
    supplied = list(samples)
    motion = original.keyed(supplied, 4)
    supplied.clear()
    assert motion.sample(0.25) == samples[1]


@pytest.mark.parametrize('fps', [0, -1, 121, True, 4.5, float('nan'), '4'])
def test_keyed_motion_refuses_invalid_sample_rates(fps):
    original, samples = inputs()
    with pytest.raises(LimbError):
        original.keyed(samples, fps)


@pytest.mark.parametrize(
    'bad', ['empty', 'many', 'type', 'clock', 'order', 'bone', 'frame', 'hand', 'digit', 'control']
)
def test_keyed_motion_refuses_malformed_samples_before_publication(bad):
    original, samples = inputs()
    if bad == 'empty':
        samples = ()
    elif bad == 'many':
        samples = samples[:1] * 4097
    elif bad == 'type':
        samples = (None,)
    elif bad == 'clock':
        samples = (replace(samples[0], time=0.1),)
    elif bad == 'order':
        samples = samples[::-1]
    elif bad == 'bone':
        samples = (replace(samples[0], arm=replace(samples[0].arm, elbow=Vec3())),)
    elif bad == 'frame':
        samples = (
            replace(samples[0], arm=replace(samples[0].arm, frame=replace(samples[0].arm.frame, origin=Vec3()))),
        )
    elif bad == 'hand':
        samples = (replace(samples[0], hand=replace(samples[0].hand, normal=Vec3())),)
    elif bad == 'digit':
        samples = (replace(samples[0], hand=replace(samples[0].hand, digits=())),)
    else:
        samples = (replace(samples[0], control=replace(samples[0].control, forearm_twist=math.tau)),)
    with pytest.raises(LimbError) as caught:
        original.keyed(samples, 4)
    assert caught.value.to_dict()['path'].startswith('keyed.')


def test_keyed_motion_serializes_as_a_closed_distinct_schema():
    original, samples = inputs()
    motion = original.keyed(samples, 4)
    data = motion_dict(motion)
    assert data['schema'] == 'srstudio.limbs-keyed/1.0.0'
    restored = parse_motion(json.loads(json.dumps(data)))
    for time in (0, 0.25, 0.5, 0.75, 1):
        assert restored.sample(time) == motion.sample(time)
    assert motion_dict(restored) == data
    data['motion']['played'][0]['untrusted'] = True
    with pytest.raises(LimbError):
        parse_motion(data)
    assert motion_dict(original)['schema'] == 'srstudio.limbs/1.3.0'


def test_keyed_motion_cannot_silently_retarget_fixed_world_geometry():
    original, samples = inputs()
    motion = original.keyed(samples, 4)
    assert motion.retarget(motion.arm) is motion
    with pytest.raises(LimbError):
        motion.retarget(replace(motion.arm, upper=2))
    with pytest.raises(LimbError):
        motion.chain()


def test_keyed_motion_bakes_its_complete_duration_at_a_different_output_rate():
    original, samples = inputs()
    motion = original.keyed(samples, 4)
    scene = Scene(version='auto')
    scene.add_project(width=320, height=240, fps='8', duration=1)
    cv = Canvas(scene, font_asset=None, width=320, height=240)
    compiled = bake(
        cv, cv.comp, motion, id='keyed', camera=Camera(origin=(160, 60), scale=60), options=BakeOptions(fps=8)
    )
    assert compiled.frames == 8
    assert compiled.report.max_bone_error < 1e-8
    assert scene.check(schema=True) == []


@pytest.mark.parametrize(
    'change',
    [
        'angle',
        'residual',
        'axis',
        'origin',
        'palm',
        'digit-length',
        'digit-count',
        'curl-name',
        'joint-count',
        'mutable',
        'long-label',
        'not-unit',
        'bad-quaternion',
    ],
)
def test_keyed_motion_checks_solved_pose_consistency_and_nested_graphs(change):
    from srstudio.limbs import Quaternion, Vec3

    original, samples = inputs()
    s = samples[0]
    if change == 'angle':
        s = replace(s, arm=replace(s.arm, elbow_angle=0.1))
    elif change == 'residual':
        s = replace(s, arm=replace(s.arm, residual=-1))
    elif change == 'axis':
        s = replace(s, arm=replace(s.arm, frame=replace(s.arm.frame, rotation=Quaternion())))
    elif change == 'origin':
        s = replace(s, hand=replace(s.hand, frame=replace(s.hand.frame, origin=Vec3())))
    elif change == 'palm':
        s = replace(s, hand=replace(s.hand, palm=()))
    elif change in ('digit-length', 'digit-count'):
        d = s.hand.digits[0]
        points = (*d.points[:-1], d.points[-1] + Vec3(1, 0, 0)) if change == 'digit-length' else d.points[:-1]
        s = replace(s, hand=replace(s.hand, digits=(replace(d, points=points), *s.hand.digits[1:])))
    elif change == 'curl-name':
        s = replace(s, control=replace(s.control, curls=(('missing', 0.3),)))
    elif change == 'joint-count':
        s = replace(s, control=replace(s.control, joints=(('thumb', (0.1,)),)))
    elif change == 'mutable':
        s = replace(s, hand=replace(s.hand, palm=list(s.hand.palm)))
    elif change == 'long-label':
        s = replace(s, action='x' * 1025)
    else:
        rotation = Quaternion()
        object.__setattr__(rotation, 'w', 'bad' if change == 'bad-quaternion' else 2)
        s = replace(s, arm=replace(s.arm, frame=replace(s.arm.frame, rotation=rotation)))
    with pytest.raises(LimbError):
        original.keyed((s,), 4)


@pytest.mark.parametrize('field', ['fps', 'played', 'arm', 'hand'])
def test_keyed_document_requires_its_explicit_clock_and_anatomy(field):
    original, samples = inputs()
    data = motion_dict(original.keyed(samples[:1], 4))
    del data['motion'][field]
    with pytest.raises(LimbError):
        parse_motion(data)


def test_keyed_document_rejects_nonunit_rotation_and_procedural_drivers():
    original, samples = inputs()
    data = motion_dict(original.keyed(samples, 4))
    data['motion']['played'][0]['arm']['frame']['rotation']['w'] = 2
    with pytest.raises(LimbError):
        parse_motion(data)
    motion = original.keyed(samples, 4)
    with pytest.raises(LimbError):
        replace(motion, actions=original.actions)


def test_keyed_motion_persists_without_geometric_drift_and_can_be_recropped(tmp_path):
    from srstudio.limbs.serialization import load_motion, save_motion

    original, samples = inputs()
    motion = original.keyed(samples, 4)
    for _ in range(3):
        motion = load_motion(save_motion(motion, tmp_path / 'motion.json'))
    assert motion.sample(0.5) == samples[2]
    assert motion.retarget(motion.arm, motion.hand) is motion
    assert motion.keyed(samples[:1], 4).end == 0.25

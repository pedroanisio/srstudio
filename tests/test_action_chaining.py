"""Adjacent gestures flow through their boundary while preserving endpoint motion and constraints."""

import json
import subprocess
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile, Frame, HandControl, LimbError, Quaternion, Vec3
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.motion import Action, Attachment, Contact, Motion, MotionStyle, Target, TransformKey, TransformTrack
from srstudio.limbs.serialization import motion_dict, parse_motion


def gestures(side='right', moving=False):
    root = TransformTrack.constant(Frame())
    if moving:
        root = TransformTrack(
            tuple(
                TransformKey(t, Frame(Vec3(0.08 * t, 0, 0), Quaternion.axis_angle(Vec3(0, 0, 1), 0.04 * t)))
                for t in (0, 2, 4, 5)
            ),
            interpolation='continuous',
        )
    return Motion(
        ArmProfile(side=side),
        HUMAN,
        (Action('point', duration=2, style=MotionStyle(asymmetry=0.2)), Action('present', start=2, duration=2)),
        root=root,
    )


def points(sample):
    return (
        sample.arm.wrist,
        sample.arm.elbow,
        *sample.hand.palm,
        *(p for digit in sample.hand.digits for p in digit.points),
    )


def assert_continuous(motion, at, tolerance=0.003):
    h = 1e-5
    a, b, c = (motion.sample(t) for t in (at - h, at, at + h))
    for left, center, right in zip(points(a), points(b), points(c), strict=True):
        assert left.distance(right) < 1e-3
        assert ((center - left) / h).distance((right - center) / h) < tolerance
    q = b.hand.frame.rotation
    before = (q.inverse() * a.hand.frame.rotation).rotation_vector * (-1 / h)
    after = (q.inverse() * c.hand.frame.rotation).rotation_vector / h
    assert before.distance(after) < tolerance


def test_chain_flows_through_the_action_boundary_without_changing_untouched_motion():
    source = gestures()
    joined = source.chain()
    assert joined.sample(2).phase == 'transition'
    assert joined.sample(2).arm.wrist.distance(source.sample(2).arm.wrist) > 0.3
    for time in (0, 1, 1.5, 2.8, 3.5, 4, 5):
        assert joined.sample(time) == source.sample(time)
    assert joined.chain() == joined
    assert source.joins == ()


@pytest.mark.parametrize('side', ['left', 'right'])
@pytest.mark.parametrize('moving', [False, True])
def test_position_velocity_and_hand_shape_continue_at_both_join_endpoints(side, moving):
    from srstudio.limbs.motion import ActionJoin

    source = gestures(side, moving)
    # Enter the second action before its stroke completes, so finger velocities are nonzero.
    joined = replace(source, joins=(ActionJoin(0, start=1.4, end=2.65),))
    for time in (1.4, 2, 2.65):
        assert_continuous(joined, time)
    for time in (1.4, 2.65):
        assert joined.sample(time) == source.sample(time)


def test_joined_sampling_is_random_access_and_retargeting_rebuilds_derived_data():
    motion = gestures(moving=True).chain()
    times = (0, 1.49, 1.7, 2, 2.79, 2.8, 4)
    expected = {t: motion.sample(t) for t in times}
    reloaded = parse_motion(json.loads(json.dumps(motion_dict(motion))))
    assert {t: reloaded.sample(t) for t in reversed(times)} == expected
    other = motion.retarget(replace(motion.arm, side='left'))
    assert other.sample(2).arm.wrist != motion.sample(2).arm.wrist
    assert_continuous(other, 2)


def contact_motion():
    source = Motion(ArmProfile(), HUMAN, (Action('rest', duration=2), Action('rest', start=2, duration=2)))
    frame = source.sample(0).hand.frame
    target = TransformTrack(
        (
            TransformKey(0, frame, velocity=Vec3(0.02, 0, 0)),
            TransformKey(4, Frame(frame.origin + Vec3(0.08, 0, 0), frame.rotation), velocity=Vec3(0.02, 0, 0)),
        ),
        interpolation='continuous',
    )
    return replace(source, contacts=(Contact('first', 0.5, 1.5, target), Contact('second', 2.5, 3.5, target)))


def test_a_join_preserves_moving_contact_endpoints_and_a_carried_prop():
    from srstudio.limbs.motion import ActionJoin

    source = contact_motion()
    source = replace(source, attachments=(Attachment('cup', 0.7, 3.7, source.sample(0.7).hand.frame),))
    joined = replace(source, joins=(ActionJoin(0, start=1.5, end=2.5),))
    for time in (1.5, 2.5):
        assert_continuous(joined, time)
    for time in (0.7, 1, 1.8, 2, 2.5, 3):
        assert joined.prop_frame('cup', time) == joined.sample(time).hand.frame
    assert joined.sample(1).contacts[0].residual < 1e-6
    assert joined.sample(3).contacts[0].residual < 1e-6


def test_a_join_cannot_silently_replace_an_active_contact():
    with pytest.raises(LimbError, match='contact') as caught:
        contact_motion().chain()
    assert caught.value.code == 'join.contact'


@pytest.mark.parametrize('joins', [((1, None, None),), ((0, 2, 3),), ((0, 1, 2),), ((0, 1, 3), (0, 1, 3))])
def test_invalid_join_references_windows_and_duplicates_fail(joins):
    from srstudio.limbs.motion import ActionJoin

    with pytest.raises(LimbError):
        replace(gestures(), joins=tuple(ActionJoin(*join) for join in joins))


def test_overlapping_join_windows_are_refused():
    from srstudio.limbs.motion import ActionJoin

    source = replace(gestures(), actions=(*gestures().actions, Action('wave', start=4, duration=2)))
    with pytest.raises(LimbError, match='overlap'):
        replace(source, joins=(ActionJoin(0, end=3.8), ActionJoin(1, start=3.1)))


def test_join_documents_are_versioned_and_old_documents_keep_return_to_rest():
    document = motion_dict(gestures().chain())
    assert document['schema'] == 'srstudio.limbs/1.3.0'
    document['schema'] = 'srstudio.limbs/1.2.0'
    with pytest.raises(LimbError, match='1.3.0'):
        parse_motion(document)
    del document['motion']['joins']
    assert parse_motion(document) == gestures()


@pytest.mark.parametrize('backend', ['native', 'baked'])
def test_joined_motion_uses_existing_compilers_and_preserves_bones(backend):
    motion = Motion(
        ArmProfile(),
        HUMAN,
        (
            Action('point', duration=2, target=Target(Vec3(0.6, 0.2, 0))),
            Action('point', start=2, duration=2, target=Target(Vec3(0.3, 0.4, 0))),
        ),
    ).chain()
    cv = Canvas(Scene(version='auto'), font_asset=None)
    result = compile_motion(cv, cv.comp, motion, id='joined', backend=backend, options=BakeOptions(fps=12))
    assert result.report.max_bone_error < 1e-6
    assert result.backend == backend
    assert result.frames == 48


def test_native_renderer_receives_the_joined_wrist(scene_render, tmp_path):
    from srstudio.limbs import Camera

    motion = Motion(
        ArmProfile(),
        HUMAN,
        (
            Action('point', duration=2, target=Target(Vec3(0.6, 0.2, 0))),
            Action('point', start=2, duration=2, target=Target(Vec3(0.3, 0.4, 0))),
        ),
    ).chain()
    scene = Scene(version='auto')
    scene.add_project(width=400, height=400, fps='24', duration=4)
    cv = Canvas(scene, font_asset=None)
    camera = Camera(origin=(0, 0), scale=100)
    compile_motion(cv, cv.comp, motion, id='joined', backend='native', camera=camera)
    path = tmp_path / 'joined.xml'
    path.write_bytes(scene.to_bytes())
    run = subprocess.run(
        [str(scene_render), 'eval', str(path), '--time', '2', '--json'], check=True, capture_output=True, text=True
    )
    nodes = {n['id']: n for n in json.loads(run.stdout)['result']['nodes']}
    assert nodes['joined-target']['world'][4:6] == pytest.approx(
        camera.project(motion.sample(2).arm.wrist).xy, abs=1e-4
    )


def test_a_fully_curled_hand_can_be_carried_through_a_join_without_false_limit_errors():
    control = HandControl(curl=1, spread=1, opposition=1, cup=1)
    motion = Motion(
        ArmProfile(),
        HUMAN,
        (Action('grasp', duration=2, control=control), Action('grasp', start=2, duration=2, control=control)),
    ).chain()
    for time in (1.6, 1.7, 1.9, 2.1, 2.4, 2.7):
        motion.sample(time)


@pytest.mark.parametrize('backend', ['native', 'baked'])
def test_an_unreachable_join_fails_before_scene_mutation(backend):
    source = gestures()
    root = TransformTrack(
        tuple(TransformKey(t, Frame(Vec3(x, 0, 0))) for t, x in ((0, 0), (1.5, 0), (2, 4), (2.8, 0), (4, 0)))
    )
    motion = replace(source, root=root).chain()
    cv = Canvas(Scene(version='auto'), font_asset=None)
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError) as caught:
        compile_motion(cv, cv.comp, motion, id='invalid-join', backend=backend, options=BakeOptions(fps=12))
    assert caught.value.context['join_after'] == 0
    assert caught.value.context['phase'] == 'transition'
    assert cv.scene.to_bytes() == before


def test_three_actions_can_join_without_a_hold_between_transitions():
    source = gestures(moving=True)
    source = replace(
        source, actions=(source.actions[0], replace(source.actions[1], hold=0), Action('point', start=4, duration=2))
    )
    motion = source.chain()
    assert_continuous(motion, 2.8)


def test_a_long_chain_remains_deterministic_after_bounded_preparation_is_evicted():
    motion = Motion(ArmProfile(), HUMAN, tuple(Action('point', start=2 * i, duration=2) for i in range(72))).chain()
    before = motion_dict(motion)
    first = motion.sample(2)
    for i in range(1, 71):
        motion.sample(2 * i + 2)
    assert len(motion._join_plans) <= 64
    assert motion.sample(2) == first
    assert motion_dict(motion) == before


@pytest.mark.parametrize('hand_name', ['human', 'three-finger', 'mitten', 'paw', 'gripper'])
def test_chains_retarget_effective_joint_angles_to_each_hand_topology(hand_name):
    from srstudio.limbs import HANDS

    motion = gestures().chain().retarget(ArmProfile(), HANDS[hand_name])
    sample = motion.sample(2)
    assert [digit.name for digit in sample.hand.digits] == [digit.name for digit in HANDS[hand_name].digits]
    assert_continuous(motion, 2.8)


@pytest.mark.parametrize('bad', [True, -1, 10000, '0'])
def test_join_indices_are_bounded_integers(bad):
    from srstudio.limbs.motion import ActionJoin

    with pytest.raises(LimbError, match='index'):
        ActionJoin(bad)


def test_unknown_join_fields_in_agent_json_are_rejected():
    data = motion_dict(gestures().chain())
    data['motion']['joins'][0]['duration'] = 1
    with pytest.raises(LimbError, match=r'motion.joins\[0\].*unknown'):
        parse_motion(data)

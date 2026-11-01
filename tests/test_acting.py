"""Acting compiles once; cuts observe the same performance rather than restarting it."""

import json
import subprocess
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.acting import (
    BENTO,
    ActingBeat,
    ActingError,
    ActingScore,
    Expression,
    HeadTarget,
    Overrides,
    SpokenLine,
    compile_performance,
    gloss_actor,
)
from srstudio.character_clips import Placement
from srstudio.head_motion import Channel, HeadPlan
from srstudio.voice import Alignment


def score():
    return ActingScore(
        4,
        (
            ActingBeat(0, emotion='happy', transition=0),
            ActingBeat(1, emotion='concerned', transition=0.5),
            ActingBeat(3, emotion='confident', transition=0.25),
        ),
    )


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='30', duration=12)
    return Canvas(scene, font_asset=None)


def evaluate(engine, path, time):
    result = subprocess.run(
        [str(engine), 'eval', str(path), '--time', str(time), '--json'], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)['result']['nodes']


@pytest.mark.parametrize('rig', [BENTO, gloss_actor('nadia')])
def test_emotion_transitions_are_explicit_and_random_access(rig):
    plan = compile_performance(rig, score())
    assert plan.sample(0).emotion == 'happy'
    assert plan.sample(1.25).emotion == 'happy'
    assert plan.sample(1.5).emotion == 'concerned'
    for t in (3.8, 0, 2.1, 1.5, 1.25, 3.25):
        assert plan.sample(t) == compile_performance(rig, score()).sample(t)
    assert plan.window(1.75, 3.5).sample(0.5) == plan.sample(2.25)


def test_explicit_fields_override_mood_defaults_and_track_overrides_own_the_channel():
    authored = ActingScore(
        3,
        (
            ActingBeat(0, emotion='happy', gesture='folded', expression=Expression('skeptical', 'flat'), transition=0),
            ActingBeat(1, emotion='concerned', transition=0),
        ),
        overrides=Overrides(gesture=((0, 'present'), (2, 'tablet'))),
    )
    plan = compile_performance(BENTO, authored)
    assert plan.sample(0).expression == Expression('skeptical', 'flat')
    assert plan.sample(0).gesture == 'present'
    assert plan.sample(1.5).gesture == 'present'
    assert plan.sample(2).gesture == 'tablet'
    assert dict(plan.owners)['gesture'] == 'override'


def test_head_and_breath_targets_ease_and_keep_their_value_until_reset():
    authored = ActingScore(
        4,
        (
            ActingBeat(0, head=HeadTarget(turn=0), breath=0, transition=0),
            ActingBeat(1, head=HeadTarget(turn=2), breath=1, transition=1),
            ActingBeat(3, reset=True, transition=0.5),
        ),
        idle=False,
    )
    plan = compile_performance(BENTO, authored)
    assert plan.sample(1).head.turn == 0
    assert plan.sample(1.5).head.turn == pytest.approx(1)
    assert plan.sample(2.5).head.turn == 2
    assert plan.sample(1.5).head.breath == pytest.approx(0.5)
    assert plan.sample(3.75).head.turn == pytest.approx(0)


def line():
    return SpokenLine(
        0.5, Alignment(tuple('Hello.'), (0, 0.1, 0.2, 0.3, 0.4, 0.5), (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)), (-24.0,) * 60
    )


@pytest.mark.parametrize('rig', [BENTO, gloss_actor('gus')])
def test_aligned_speech_drives_supported_mouth_tracks_and_returns_to_rest(rig):
    plan = compile_performance(rig, ActingScore(3, speech=(line(),)))
    assert any(plan.sample(t).mouth != 'closed' for t in (0.5, 0.6, 0.7, 0.8, 0.9))
    assert plan.sample(1.2).mouth == 'closed'
    assert plan.sample(0).mouth == 'closed'


def test_listening_uses_existing_prosody_planner_without_speaking():
    plan = compile_performance(BENTO, ActingScore(3, heard=(line(),)))
    assert all(plan.sample(t).mouth == 'closed' for t in (0, 0.7, 1.2, 2.8))
    assert plan.head is not None
    baseline = compile_performance(BENTO, ActingScore(3))
    assert plan.head.nod.sample(1.21) > baseline.head.nod.sample(1.21)


@pytest.mark.parametrize(
    'authored',
    [
        ActingScore(3, (ActingBeat(0, gaze='left'),)),
        ActingScore(3, (ActingBeat(0, head=HeadTarget(turn=1)),)),
        ActingScore(3, (ActingBeat(0, breath=0.5),)),
        ActingScore(3, heard=(line(),)),
        ActingScore(3, idle=False),
    ],
)
def test_unsupported_gloss_controls_fail_before_any_scene_changes(authored):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(ActingError) as caught:
        compile_performance(gloss_actor('nadia'), authored)
    assert caught.value.to_dict()['code'] == 'acting.unsupported'
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize(
    'authored',
    [
        ActingScore(3, (ActingBeat(1, gaze='left'), ActingBeat(1, gaze='right'))),
        ActingScore(
            3,
            (
                ActingBeat(0, head=HeadTarget(turn=1), transition=2),
                ActingBeat(1, head=HeadTarget(turn=0), transition=1),
            ),
        ),
        ActingScore(3, overrides=Overrides(head=HeadPlan.still(), gaze=((0, 'left'),))),
    ],
)
def test_competing_channel_owners_or_overlapping_transitions_are_errors(authored):
    with pytest.raises(ActingError, match='(conflict|overlap)'):
        compile_performance(BENTO, authored)


def test_reset_is_explicit_and_other_beats_preserve_gaze():
    plan = compile_performance(
        BENTO,
        ActingScore(
            4,
            (
                ActingBeat(0, gaze='left', emotion='happy', transition=0),
                ActingBeat(1, gesture='folded', transition=0),
                ActingBeat(3, reset=True, transition=0),
            ),
        ),
    )
    assert plan.window(1, 2.5).sample(1).gaze == 'left'
    assert plan.sample(2).emotion == 'happy'
    assert plan.sample(3).gaze == 'ahead'
    assert plan.sample(3).emotion == 'neutral'


@pytest.mark.parametrize('rig', [BENTO, gloss_actor('gus')])
@pytest.mark.parametrize('sequence_cut', [False, True])
def test_window_drawings_match_uncut_engine_states_at_nonzero_offsets(scene_render, tmp_path, rig, sequence_cut):
    plan = compile_performance(rig, score())
    frames = []
    for start, end, at in ((0, 4, 0), (1.5, 3.5, 5)):
        cv = canvas()
        parent, lead = cv.comp, 0
        if sequence_cut and at:
            sequence = cv.comp.add_sequence(id='shots')
            lead = 3
            sequence.add_group(id='lead', end=lead)
            parent = sequence.add_group(id='shot', end=9)
        plan.window(start, end).place(cv, parent, at=at, id='performance', placement=Placement(10, 20, scale=0.7))
        path = tmp_path / f'{at}.xml'
        path.write_bytes(cv.scene.to_bytes())
        frames.append(
            [
                [
                    (node['kind'], node['world'], node['world_opacity'], node['draw'])
                    for node in evaluate(scene_render, path, lead + at + t - start)
                    if node['id'] not in ('performance', 'shots', 'shot')
                ]
                for t in (1.5, 1.75, 2, 3.25)
            ]
        )
        assert not any(n['id'] == 'performance' for n in evaluate(scene_render, path, lead + at + end - start))
    assert frames[0] == frames[1]


def contact_track():
    from srstudio.limbs import HUMAN, ArmProfile, Camera, Frame, Vec3
    from srstudio.limbs.compile import BakeOptions
    from srstudio.limbs.integration import LimbTrack
    from srstudio.limbs.motion import Action, Contact, Motion, TransformKey, TransformTrack

    target = TransformTrack((TransformKey(0, Frame(origin=Vec3(0.4, 0.2, 0))),))
    motion = Motion(
        ArmProfile(), HUMAN, (Action('press', duration=4),), contacts=(Contact('button', 0.5, 3.5, target),)
    )
    return LimbTrack(
        motion, style='gloss', camera=Camera(origin=(-92, -345), scale=200), options=BakeOptions(fps=4), backend='baked'
    )


def test_contact_state_and_world_anchor_survive_a_cut_without_reacquisition():
    track = contact_track()
    plan = compile_performance(gloss_actor('nadia'), ActingScore(4, overrides=Overrides(limbs=(track,))))
    state = plan.window(2, 4).sample(0)
    assert state == plan.sample(2)
    assert state.limbs[0].contacts == ('button',)
    assert state.limbs[0].pose.arm.wrist.distance(track.motion.contacts[0].frame(2).origin) < 1e-6
    assert plan.sample(3.75).limbs[0].contacts == ()


def test_contact_does_not_activate_before_its_limb_track_offset():
    track = contact_track()
    track = replace(track, options=replace(track.options, offset=0.5))
    plan = compile_performance(gloss_actor('nadia'), ActingScore(5, overrides=Overrides(limbs=(track,))))
    assert plan.sample(0.25).limbs[0].contacts == ()
    assert plan.sample(0.75).limbs[0].contacts == ()
    assert plan.sample(1).limbs[0].contacts == ('button',)


def test_reset_cannot_silently_release_an_explicit_contact():
    with pytest.raises(ActingError, match='contact'):
        compile_performance(
            gloss_actor('gus'),
            ActingScore(4, (ActingBeat(2, reset=True),), overrides=Overrides(limbs=(contact_track(),))),
        )


def test_custom_mood_without_mouth_inherits_the_neutral_mouth():
    from srstudio.acting import Emotion

    rig = replace(BENTO, emotions=(BENTO.emotions[0], Emotion('custom', Expression('wide'), 'folded')))
    plan = compile_performance(rig, ActingScore(2, (ActingBeat(0, emotion='custom', transition=0),)))
    assert plan.sample(1).expression.mouth == BENTO.emotions[0].expression.mouth


def test_gaze_discovery_requires_a_drawing_that_can_move_its_pupils():
    assert BENTO.describe()['capabilities']['gaze'] is True
    look = replace(BENTO.head_rig.look, drawing=object())
    rig = replace(BENTO, head_rig=replace(BENTO.head_rig, look=look))
    assert rig.describe()['capabilities']['gaze'] is False


@pytest.mark.parametrize(
    'authored',
    [
        ActingScore(0),
        ActingScore(float('nan')),
        ActingScore(3, (ActingBeat(-1),)),
        ActingScore(3, (ActingBeat(0, emotion='invented'),)),
        ActingScore(3, (ActingBeat(2.9, transition=1),)),
        ActingScore(3, (ActingBeat(0, gaze='invented'),)),
        ActingScore(3, (ActingBeat(0, breath=float('inf')),)),
        ActingScore(3, (ActingBeat(0, expression=Expression('invented')),)),
        ActingScore(3, speech=(replace(line(), alignment=Alignment(('x',), (0,), (float('nan'),))),)),
        ActingScore(3, speech=(line(), line())),
        ActingScore(3, sample_rate=0),
    ],
)
def test_invalid_input_has_actionable_bounded_diagnostics(authored):
    with pytest.raises(ActingError) as caught:
        compile_performance(BENTO, authored)
    details = caught.value.to_dict()
    assert details['path'] and details['expected'] and details['remedy']
    json.dumps(details, allow_nan=False)


def test_failed_window_draw_restores_scene_ids_and_canvas_clock(monkeypatch):
    plan = compile_performance(gloss_actor('gus'), score())
    cv = canvas()
    cv.local_time = True
    before = cv.scene.to_bytes()
    original = cv.path

    def fail(*args, **kw):
        original(*args, **kw)
        raise RuntimeError('drawing failed')

    monkeypatch.setattr(cv, 'path', fail)
    with pytest.raises(RuntimeError, match='drawing failed'):
        plan.window(1, 3).place(cv, cv.comp, at=4)
    assert cv.scene.to_bytes() == before
    assert cv._serial == 0 and cv.local_time is True


def test_explicit_head_and_mouth_overrides_preserve_channel_curves():
    head = HeadPlan(turn=Channel(((0, 0), (1, 1), (3, 0)), curve='sine-in-out'), gaze=((0, 'right'),))
    plan = compile_performance(BENTO, ActingScore(3, overrides=Overrides(head=head, mouth=((0, 'round'),))))
    assert plan.head is head
    assert plan.sample(0.5).head.turn == pytest.approx(0.5)
    assert plan.sample(0.5).gaze == 'right'
    assert plan.sample(0.5).mouth == 'round'


def test_invalid_head_intent_cannot_be_hidden_by_an_override():
    with pytest.raises(ActingError):
        compile_performance(
            BENTO,
            ActingScore(3, (ActingBeat(0, head=HeadTarget(turn=100)),), overrides=Overrides(head=HeadPlan.still())),
        )


@pytest.mark.parametrize(
    'alignment', [Alignment(('x',), None, (1,)), Alignment(('x',), (0,), ()), Alignment(('x',), (False,), (1,))]
)
def test_directly_constructed_invalid_alignment_is_revalidated(alignment):
    with pytest.raises(ActingError):
        compile_performance(BENTO, ActingScore(3, speech=(SpokenLine(0, alignment, (-20.0,) * 100),)))


@pytest.mark.parametrize(
    'rig',
    [
        replace(BENTO, head_rig='bad'),
        replace(BENTO, name=''),
        replace(BENTO, emotions=(replace(BENTO.emotions[0], expression='bad'),)),
        replace(BENTO, family='gloss', head_rig=None, gloss_character=None),
    ],
)
def test_invalid_profile_is_a_typed_failure(rig):
    with pytest.raises(ActingError):
        compile_performance(rig, ActingScore(3))


def test_contact_samples_are_preserved_in_rendered_cut_windows(scene_render, tmp_path):
    plan = compile_performance(gloss_actor('nadia'), ActingScore(4, overrides=Overrides(limbs=(contact_track(),))))
    frames = []
    for start, at in ((0, 0), (2, 6)):
        cv = canvas()
        plan.window(start, 4).place(cv, cv.comp, at=at, id='contact')
        path = tmp_path / f'{at}.xml'
        path.write_bytes(cv.scene.to_bytes())
        frames.append(
            [
                (n['world'], n['world_opacity'])
                for n in evaluate(scene_render, path, at + 2.25 - start)
                if 'limb' in n['id']
            ]
        )
    assert frames[0] and frames[0] == frames[1]


def test_directed_gaze_owns_eye_direction_and_head_follow_with_a_short_lag():
    plan = compile_performance(BENTO, ActingScore(3, (ActingBeat(0, gaze='left', transition=0),), idle=False))
    assert plan.sample(0).gaze == 'left'
    assert plan.sample(0.04).head.turn == 0
    assert plan.sample(1).head.turn < 0 and plan.sample(1).head.face_x < 0
    assert plan.sample(2).gaze == 'left'


def test_explicit_head_target_takes_precedence_over_gaze_follow():
    plan = compile_performance(
        BENTO, ActingScore(3, (ActingBeat(0, gaze='left', head=HeadTarget(turn=1), transition=0),), idle=False)
    )
    assert plan.sample(1).head.turn == 1
    assert plan.sample(1).head.face_x < 0


def test_gaze_track_override_coordinates_head_follow_too():
    plan = compile_performance(BENTO, ActingScore(3, overrides=Overrides(gaze=((0, 'right'),)), idle=False))
    assert plan.sample(1).head.turn > 0
    assert plan.sample(1).head.face_x > 0


def test_extreme_integer_input_still_has_a_bounded_json_failure():
    with pytest.raises(ActingError) as caught:
        compile_performance(BENTO, ActingScore(10**10000))
    assert len(json.dumps(caught.value.to_dict(), allow_nan=False)) < 2000

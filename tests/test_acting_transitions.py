"""Opt-in acting timing remains bounded, explicit and independent of cuts or sampling order."""

import hashlib
import json
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.acting import (
    BENTO,
    ActingBeat,
    ActingError,
    ActingScore,
    ChannelTiming,
    HeadTarget,
    Overrides,
    TransitionPolicy,
    compile_performance,
    gloss_actor,
    parse_score,
)
from srstudio.head_motion import Spring


def numeric(policy, **kwargs):
    return ActingScore(
        4,
        (
            ActingBeat(0, head=HeadTarget(turn=0), transition=0),
            ActingBeat(1, head=HeadTarget(turn=2), transition=1, policy=policy),
        ),
        idle=False,
        sample_rate=24,
        **kwargs,
    )


def test_policy_free_score_retains_its_serialized_drawing():
    score = ActingScore(
        4,
        (
            ActingBeat(0, emotion='neutral', head=HeadTarget(turn=0), breath=0, transition=0),
            ActingBeat(1, emotion='happy', head=HeadTarget(turn=2), breath=0.4, transition=0.5),
            ActingBeat(3, reset=True, transition=0.5),
        ),
        idle=False,
        sample_rate=24,
    )
    plan = compile_performance(BENTO, score)
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='24', duration=4)
    cv = Canvas(scene, font_asset=None)
    plan.window(0, 4).place(cv, cv.comp, id='baseline')
    assert (
        hashlib.sha256(scene.to_bytes()).hexdigest()
        == 'd31a4de784126b92b929fd3fa548a769362bd755f87189f80ef4bf5cad3d94b3'
    )


def test_easing_is_selectable_without_changing_the_target():
    linear = compile_performance(BENTO, numeric(TransitionPolicy(curve='linear')))
    cubic = compile_performance(BENTO, numeric(TransitionPolicy(curve='cubic-in')))
    assert linear.sample(1.25).head.turn == pytest.approx(0.5, abs=1e-4)
    assert cubic.sample(1.25).head.turn == pytest.approx(0.03125, abs=1e-4)
    assert linear.sample(2.5).head.turn == cubic.sample(2.5).head.turn == 2


@pytest.mark.parametrize('curve', ['sine-in-out', 'spring'])
def test_anticipation_and_settling_are_visible_and_cut_stable(curve):
    policy = TransitionPolicy(curve=curve, anticipation=0.2, anticipation_amount=0.1, settle=0.3, overshoot=0.1)
    plan = compile_performance(BENTO, numeric(policy))
    assert plan.sample(1).head.turn == pytest.approx(-0.2, abs=1e-4)
    assert plan.sample(2).head.turn == pytest.approx(2.2, abs=1e-4)
    assert plan.sample(2.3).head.turn == pytest.approx(2, abs=1e-4)
    for start, end in ((0.85, 1.4), (1.8, 2.8)):
        cut = plan.window(start, end)
        for t in (end - start, 0, (end - start) / 2):
            assert cut.sample(t) == plan.sample(start + t)
    assert plan.sample(1.1) == compile_performance(BENTO, numeric(policy)).sample(1.1)


def test_expression_and_head_can_arrive_at_different_times():
    policy = TransitionPolicy(timing=(ChannelTiming('expression', duration=0), ChannelTiming('turn', delay=0.2)))
    score = numeric(policy)
    score = replace(score, beats=(score.beats[0], replace(score.beats[1], emotion='happy')))
    plan = compile_performance(BENTO, score)
    assert plan.sample(1).emotion == 'happy'
    assert plan.sample(1.1).head.turn == 0
    assert plan.sample(2.2).head.turn == 2


def test_gloss_can_stagger_drawings_but_cannot_request_numeric_springs():
    rig = gloss_actor('nadia')
    score = ActingScore(
        4,
        (
            ActingBeat(
                1,
                emotion='happy',
                transition=0.5,
                policy=TransitionPolicy(timing=(ChannelTiming('gesture', delay=0.2),)),
            ),
        ),
    )
    plan = compile_performance(rig, score)
    assert plan.sample(1.5).emotion == 'happy'
    assert plan.sample(1.6).gesture == 'down'
    assert plan.sample(1.7).gesture == 'up'
    with pytest.raises(ActingError) as caught:
        compile_performance(
            rig, replace(score, beats=(replace(score.beats[0], policy=TransitionPolicy(curve='spring')),))
        )
    assert caught.value.to_dict()['code'] == 'acting.unsupported'


@pytest.mark.parametrize(
    'policy',
    [
        TransitionPolicy(version='99'),
        TransitionPolicy(curve='typo'),
        TransitionPolicy(anticipation=True),
        TransitionPolicy(anticipation=2),
        TransitionPolicy(anticipation_amount=float('nan')),
        TransitionPolicy(settle=3),
        TransitionPolicy(overshoot=0.1),
        TransitionPolicy(spring=Spring(3, 0.7)),
        TransitionPolicy(curve='spring', spring=Spring(100, 0.7)),
        TransitionPolicy(timing=(ChannelTiming('missing'),)),
        TransitionPolicy(timing=(ChannelTiming('turn'), ChannelTiming('turn'))),
        TransitionPolicy(timing=(ChannelTiming('gaze'),)),
        TransitionPolicy(timing=(ChannelTiming('turn', delay=-0.1),)),
    ],
)
def test_malformed_or_ineffective_policies_have_repairable_failures(policy):
    with pytest.raises(ActingError) as caught:
        compile_performance(BENTO, numeric(policy))
    data = caught.value.to_dict()
    assert 'policy' in data['path'] and data['expected'] and data['remedy']
    json.dumps(data, allow_nan=False)


def test_settling_and_anticipation_reserve_the_entire_channel_interval():
    score = numeric(TransitionPolicy(settle=0.4, overshoot=0.1))
    score = replace(
        score,
        beats=(
            *score.beats,
            ActingBeat(2.5, head=HeadTarget(turn=0), transition=0.3, policy=TransitionPolicy(anticipation=0.2)),
        ),
    )
    with pytest.raises(ActingError) as caught:
        compile_performance(BENTO, score)
    assert caught.value.to_dict()['code'] == 'acting.conflict'


def test_overshoot_cannot_escape_the_rig_envelope():
    from srstudio.head_motion import limit

    score = numeric(TransitionPolicy(settle=0.2, overshoot=0.5))
    score = replace(
        score,
        beats=(score.beats[0], replace(score.beats[1], head=HeadTarget(turn=limit(BENTO.head_rig.style, 'turn')))),
    )
    with pytest.raises(ActingError):
        compile_performance(BENTO, score)


def test_discovery_describes_policy_capabilities_and_continuity_limits():
    info = BENTO.describe()['transitions']['policy']
    assert info['version'] == '1.0.0'
    assert 'spring' in info['curves'] and 'turn' in info['numeric_channels']
    assert info['facial_morph'] is False
    assert info['continuity']['velocity'] is False and info['continuity']['acceleration'] is False
    assert gloss_actor('nadia').describe()['transitions']['policy']['numeric_channels'] == []


def document():
    return {
        'schema': 'srstudio.acting/1.1.0',
        'duration': 4,
        'beats': [
            {
                'at': 1,
                'head': {'turn': 2},
                'transition': 1,
                'policy': {
                    'version': '1.0.0',
                    'curve': 'spring',
                    'spring': {'frequency': 3, 'damping': 0.8},
                    'anticipation': 0.2,
                    'settle': 0.3,
                    'timing': [{'channel': 'turn', 'delay': 0.1}],
                },
            }
        ],
    }


def test_versioned_policy_json_builds_typed_records():
    score = parse_score(document())
    assert isinstance(score.beats[0].policy, TransitionPolicy)
    assert score.beats[0].policy.spring == Spring(3, 0.8)
    assert score.beats[0].policy.timing == (ChannelTiming('turn', delay=0.1),)
    compile_performance(BENTO, score)


@pytest.mark.parametrize(
    'field,value',
    [
        ('curve', 'unknown'),
        ('morph', True),
        ('anticipation', '0.2'),
        ('timing', [{'channel': 'turn', 'delai': 1}]),
        ('version', '2.0.0'),
    ],
)
def test_policy_json_rejects_bad_fields_or_values(field, value):
    data = document()
    data['beats'][0]['policy'][field] = value
    with pytest.raises(ActingError):
        compile_performance(BENTO, parse_score(data))


def test_old_schema_cannot_silently_accept_the_new_policy_field():
    data = document()
    data['schema'] = 'srstudio.acting/1.0.0'
    with pytest.raises(ActingError):
        parse_score(data)


@pytest.mark.parametrize(
    'policy',
    [
        'fast',
        TransitionPolicy(curve=[]),
        TransitionPolicy(timing=[]),
        TransitionPolicy(timing=('turn',)),
        TransitionPolicy(timing=(ChannelTiming('turn', duration=True),)),
        TransitionPolicy(anticipation=10**10000),
        TransitionPolicy(anticipation=1e-8),
        TransitionPolicy(curve='spring', spring=Spring(3, 0.7, 0.1)),
    ],
)
def test_adversarial_policy_shapes_are_bounded_typed_failures(policy):
    with pytest.raises(ActingError) as caught:
        compile_performance(BENTO, numeric(policy))
    assert caught.value.to_dict()['path'].startswith('beats[1].policy')
    assert len(json.dumps(caught.value.to_dict(), allow_nan=False)) < 10000


def test_policy_sampling_budget_refuses_long_dense_bakes():
    score = ActingScore(
        100,
        (ActingBeat(1, head=HeadTarget(turn=2), transition=90, policy=TransitionPolicy(curve='spring')),),
        idle=False,
        sample_rate=24,
    )
    with pytest.raises(ActingError) as caught:
        compile_performance(BENTO, score)
    assert caught.value.to_dict()['code'] == 'acting.budget'


def test_zero_duration_numeric_policy_does_not_start_moving_before_its_beat():
    score = numeric(TransitionPolicy())
    score = replace(score, beats=(score.beats[0], replace(score.beats[1], transition=0)))
    plan = compile_performance(BENTO, score)
    assert plan.sample(0.99999).head.turn == 0
    assert plan.sample(1).head.turn == 2


def test_override_cannot_hide_policy_overshoot_beyond_rig_limits():
    from srstudio.head_motion import HeadPlan, limit

    score = numeric(TransitionPolicy(settle=0.2, overshoot=0.5), overrides=Overrides(head=HeadPlan.still()))
    score = replace(
        score,
        beats=(score.beats[0], replace(score.beats[1], head=HeadTarget(turn=limit(BENTO.head_rig.style, 'turn')))),
    )
    with pytest.raises(ActingError):
        compile_performance(BENTO, score)


def test_breath_anticipation_cannot_escape_normalized_expansion():
    score = ActingScore(
        4, (ActingBeat(0, breath=0, transition=0), ActingBeat(1, breath=0.5, policy=TransitionPolicy(anticipation=0.2)))
    )
    with pytest.raises(ActingError) as caught:
        compile_performance(BENTO, score)
    assert caught.value.to_dict()['path'] == 'policy.breath'


def test_policy_face_timing_keeps_contact_ownership_across_a_cut():
    from srstudio.limbs.motion import Attachment
    from test_acting import contact_track

    track = contact_track()
    motion = replace(track.motion, attachments=(Attachment('cup', 0.5, 3.5, track.motion.sample(0.5).hand.frame),))
    track = replace(track, motion=motion)
    policy = TransitionPolicy(timing=(ChannelTiming('expression', delay=0.2),))
    score = ActingScore(4, (ActingBeat(1, emotion='happy', policy=policy),), overrides=Overrides(limbs=(track,)))
    plan = compile_performance(gloss_actor('nadia'), score)
    assert dict(plan.owners)['gesture'] == 'limbs'
    for t in (1.1, 1.5, 2.25, 3.49):
        state = plan.window(1, 4).sample(t - 1)
        assert state.limbs[0].contacts == ('button',)
        assert state.limbs[0].pose == track.motion.sample(t)
        assert dict(state.limbs[0].props)['cup'] == motion.prop_frame('cup', t)


def test_delayed_reset_cannot_cross_a_contact_that_starts_after_the_beat():
    from test_acting import contact_track

    score = ActingScore(
        4,
        (
            ActingBeat(
                0.1,
                reset=True,
                transition=0.2,
                policy=TransitionPolicy(timing=(ChannelTiming('expression', delay=0.5),)),
            ),
        ),
        overrides=Overrides(limbs=(contact_track(),)),
    )
    with pytest.raises(ActingError) as caught:
        compile_performance(gloss_actor('nadia'), score)
    assert caught.value.to_dict()['code'] == 'acting.conflict'


def test_delayed_reset_cannot_cross_a_later_attachment_without_a_contact():
    from srstudio.limbs.motion import Attachment
    from test_acting import contact_track

    track = contact_track()
    motion = replace(track.motion, contacts=())
    motion = replace(motion, attachments=(Attachment('cup', 0.5, 3.5, motion.sample(0.5).hand.frame),))
    score = ActingScore(
        4,
        (
            ActingBeat(
                0.1,
                reset=True,
                transition=0.2,
                policy=TransitionPolicy(timing=(ChannelTiming('expression', delay=0.5),)),
            ),
        ),
        overrides=Overrides(limbs=(replace(track, motion=motion),)),
    )
    with pytest.raises(ActingError) as caught:
        compile_performance(gloss_actor('nadia'), score)
    assert caught.value.to_dict()['code'] == 'acting.conflict'


@pytest.mark.parametrize('curve', ['sine-in-out', 'spring'])
@pytest.mark.parametrize('cut_start', [0.85, 2.1])
def test_rendered_policy_keeps_anticipation_and_settling_in_later_shots(curve, cut_start, scene_render, tmp_path):
    from test_acting import canvas, evaluate

    policy = TransitionPolicy(curve=curve, anticipation=0.2, anticipation_amount=0.1, settle=0.3, overshoot=0.1)
    plan = compile_performance(BENTO, numeric(policy))
    frames = []
    for start, at in ((0, 0), (cut_start, 5)):
        cv = canvas()
        parent = cv.comp
        if at:
            sequence = cv.comp.add_sequence(id='shots')
            sequence.add_group(id='lead', end=2)
            parent = sequence.add_group(id='shot', end=9)
        plan.window(start, 3).place(cv, parent, at=at, id='performance')
        path = tmp_path / f'{curve}-{at}.xml'
        path.write_bytes(cv.scene.to_bytes())
        frames.append(
            [
                [
                    (n['kind'], n['world'], n['world_opacity'], n['draw'])
                    for n in evaluate(scene_render, path, (2 if at else 0) + at + t - start)
                    if n['id'] not in ('performance', 'shots', 'shot')
                ]
                for t in (0.85, 1, 1.25, 2, 2.15, 2.3)
                if t >= cut_start
            ]
        )
    for uncut, cut in zip(*frames, strict=True):
        assert len(uncut) == len(cut)
        for a, b in zip(uncut, cut, strict=True):
            assert a[0] == b[0] and a[2:] == b[2:]
            # Different parent offsets introduce floating-point roundoff in engine time subtraction.
            assert a[1] == pytest.approx(b[1], rel=0, abs=1e-9)

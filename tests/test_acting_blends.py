"""Authored face geometry shares the performance clock with body motion."""

from dataclasses import replace

import pytest

from srstudio import acting
from srstudio.character_clips import ToonClip
from support.acting import canvas


def score(**kwargs):
    return acting.ActingScore(
        3,
        (
            acting.ActingBeat(0, breath=0, head=acting.HeadTarget(lean=0), transition=0),
            acting.ActingBeat(
                1, emotion='concerned', gesture='tablet', head=acting.HeadTarget(lean=0.3), transition=1, blend=True
            ),
        ),
        idle=False,
        sample_rate=12,
        **kwargs,
    )


def test_blend_is_declared_opt_in_and_samples_across_cuts():
    rig = acting.bento_blends()
    assert not acting.BENTO.describe()['capabilities']['expression_blend']
    assert rig.describe()['capabilities']['expression_blend']
    plan = acting.compile_performance(rig, score())
    assert isinstance(plan.clip, ToonClip)
    mid = plan.sample(1.5)
    assert mid.face_blend.weight == pytest.approx(0.5)
    assert mid.face_blend.source.eyes == 'neutral'
    assert mid.face_blend.target.eyes == 'concerned'
    assert mid.head.lean == pytest.approx(0.15)
    assert plan.window(1.25, 2.5).sample(0.25) == mid
    for t in (2.5, 1.5, 1, 0, 1.75, 1.5):
        assert plan.sample(t) == acting.compile_performance(rig, score()).sample(t)
    assert plan.sample(2).face_blend is None
    assert plan.sample(2).expression.eyes == 'concerned'


def test_unsupported_blend_fails_before_drawing():
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(acting.ActingError) as caught:
        acting.compile_performance(acting.BENTO, score()).window(0, 3).place(cv, cv.comp)
    assert caught.value.to_dict()['code'] == 'acting.unsupported'
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('change', [{'emotion': 'happy'}, {'transition': 0}, {'blend': 'true'}, {'emotion': None}])
def test_invalid_blend_requests_are_not_silently_discrete(change):
    authored = score()
    authored = replace(authored, beats=(authored.beats[0], replace(authored.beats[1], **change)))
    with pytest.raises(acting.ActingError):
        acting.compile_performance(acting.bento_blends(), authored)


def test_expression_override_cannot_silently_discard_requested_blend():
    with pytest.raises(acting.ActingError, match='owner'):
        acting.compile_performance(acting.bento_blends(), score(overrides=acting.Overrides(expression=())))


def test_data_contract_requires_new_schema_and_boolean():
    data = {
        'schema': 'srstudio.acting/1.2.0',
        'duration': 3,
        'idle': False,
        'beats': [{'at': 1, 'emotion': 'concerned', 'transition': 1, 'blend': True}],
    }
    parsed = acting.parse_score(data)
    assert parsed.beats[0].blend is True
    acting.compile_performance(acting.bento_blends(), parsed)
    for schema in ('srstudio.acting/1.0.0', 'srstudio.acting/1.1.0'):
        with pytest.raises(acting.ActingError):
            acting.parse_score({**data, 'schema': schema})
    with pytest.raises(acting.ActingError):
        acting.parse_score({**data, 'beats': [{**data['beats'][0], 'blend': 'true'}]})


def test_placing_blend_keeps_body_single_and_source_clock():
    plan = acting.compile_performance(acting.bento_blends(), score())
    cv = canvas()
    group = plan.window(1.25, 2.75).place(cv, cv.comp, at=4)
    assert float(group.timeOffset) == pytest.approx(2.75)
    assert len([g for g in group.iter('group') if g.id.startswith('lean')]) == 1
    frames = [g for g in group.iter('group') if g.id.startswith('face-blend-eyes')]
    assert len(frames) == 12
    assert all(float(g.end) > float(g.start) for g in frames)


@pytest.mark.parametrize('overrides', [acting.Overrides(gaze=((0, 'left'),)), acting.Overrides(mouth=((0, 'open'),))])
def test_competing_facial_owners_fail(overrides):
    with pytest.raises(acting.ActingError):
        acting.compile_performance(acting.bento_blends(), score(overrides=overrides))


def test_expression_delay_moves_face_launch_without_restarting_body():
    authored = score()
    beat = replace(
        authored.beats[1],
        transition=0.5,
        policy=acting.TransitionPolicy(timing=(acting.ChannelTiming('expression', delay=0.25),)),
    )
    plan = acting.compile_performance(acting.bento_blends(), replace(authored, beats=(authored.beats[0], beat)))
    assert plan.sample(1.2).face_blend is None
    assert plan.sample(1.5).face_blend.weight == pytest.approx(0.5)
    assert plan.sample(1.5).head.lean == pytest.approx(0.3)


@pytest.mark.parametrize('curve', ['linear', 'cubic-in-out', 'quint-in-out'])
def test_face_only_policy_accepts_declared_monotone_easing(curve):
    authored = acting.ActingScore(
        3,
        (
            acting.ActingBeat(
                1, emotion='concerned', transition=1, blend=True, policy=acting.TransitionPolicy(curve=curve)
            ),
        ),
        idle=False,
    )
    plan = acting.compile_performance(acting.bento_blends(), authored)
    assert plan.sample(1.5).face_blend.weight == pytest.approx(0.5)
    # The legacy discrete-only contract continues to refuse unused numeric easing.
    with pytest.raises(acting.ActingError):
        acting.compile_performance(acting.BENTO, replace(authored, beats=(replace(authored.beats[0], blend=False),)))

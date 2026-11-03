"""Whole-body intent keeps planted feet in world space and refuses unsupported support."""

from dataclasses import replace

import pytest

from srstudio import body
from srstudio.limbs import Frame, Quaternion, Vec3


def stance():
    return (body.FootAnchor('left', Frame(Vec3(-0.12, 0, 0))), body.FootAnchor('right', Frame(Vec3(0.12, 0, 0))))


def score():
    return body.BodyScore(
        duration=4,
        roots=(
            body.BodyKey(0, Frame(Vec3(0, -0.88, 0))),
            body.BodyKey(1, Frame(Vec3(-0.15, -0.88, 0))),
            body.BodyKey(2.5, Frame(Vec3(-0.15, -0.88, 0))),
            body.BodyKey(4, Frame(Vec3(0, -0.88, 0.1))),
        ),
        stance=stance(),
        steps=(body.Step('right', 1.25, 2.25, Frame(Vec3(0.12, 0, 0.2)), clearance=0.08),),
    )


def test_planted_feet_keep_world_anchors_while_root_moves():
    plan = body.compile_body(score())
    for t in (0, 0.4, 1, 1.25, 1.5, 2.25, 3, 4):
        pose = plan.sample(t)
        left, right = pose.legs
        assert left.side == 'left'
        assert left.sole == stance()[0].frame
        assert left.planted
        if t <= 1.25:
            assert right.sole == stance()[1].frame
        elif t >= 2.25:
            assert right.sole == score().steps[0].target
        else:
            assert not right.planted
            assert right.sole.origin.y < 0
        assert left.hip.distance(left.knee) == pytest.approx(plan.profile.thigh)
        assert right.knee.distance(right.ankle) == pytest.approx(plan.profile.shin)
        assert pose.support_margin >= plan.profile.support_margin - 1e-8


def test_random_access_and_window_observe_identical_skeleton():
    plan = body.compile_body(score())
    for t in (2.25, 0, 1.5, 3.1, 1.25, 1.5, 4):
        assert plan.sample(t) == body.compile_body(score()).sample(t)
    assert plan.window(1.1, 3).sample(0.4) == plan.sample(1.5)


def test_swing_has_exact_endpoints_and_no_impulse_at_lift_or_plant():
    plan = body.compile_body(score())
    epsilon = 1e-4
    for t in (1.25, 2.25):
        a = plan.sample(t - epsilon).legs[1].sole.origin
        b = plan.sample(t).legs[1].sole.origin
        c = plan.sample(t + epsilon).legs[1].sole.origin
        assert a.distance(b) / epsilon < 1e-5
        assert b.distance(c) / epsilon < 1e-5
        assert (c - b * 2 + a).length / epsilon**2 < 0.01


def test_lifting_without_weight_shift_fails_with_repair_fields():
    authored = replace(score(), roots=(score().roots[0],))
    with pytest.raises(body.BodyError) as caught:
        body.compile_body(authored)
    details = caught.value.to_dict()
    assert details['code'] == 'body.support'
    assert details['path'] and details['actual'] is not None and details['remedy']


def test_unreachable_leg_and_overlapping_steps_fail():
    with pytest.raises(body.BodyError):
        body.compile_body(replace(score(), roots=(body.BodyKey(0, Frame(Vec3(0, -1.3, 0))),)))
    with pytest.raises(body.BodyError):
        body.compile_body(
            replace(score(), steps=(*score().steps, body.Step('left', 1.5, 2.5, Frame(Vec3(-0.12, 0, 0.2)))))
        )


@pytest.mark.parametrize(
    'change',
    [
        {'duration': True},
        {'duration': 601},
        {'roots': []},
        {'stance': ()},
        {'steps': (None,)},
        {'validation_hz': 0},
        {'validation_hz': 121},
    ],
)
def test_malformed_or_unbounded_scores_are_typed(change):
    with pytest.raises(body.BodyError):
        body.compile_body(replace(score(), **change))


def test_torso_hip_and_ankle_envelopes_are_enforced():
    authored = score()
    tilted = replace(authored.roots[0], torso=Quaternion.axis_angle(Vec3(0, 0, 1), 0.7))
    with pytest.raises(body.BodyError):
        body.compile_body(replace(authored, roots=(tilted,)))
    for profile in (replace(authored.profile, hip_limit=0.05), replace(authored.profile, ankle_limit=0.05)):
        with pytest.raises(body.BodyError):
            body.compile_body(replace(authored, profile=profile))


def test_twisted_foot_is_not_mistaken_for_a_neutral_ankle():
    turned = Frame(Vec3(0.12, 0, 0), Quaternion.axis_angle(Vec3(0, 1, 0), 1.5))
    with pytest.raises(body.BodyError) as caught:
        body.compile_body(replace(score(), stance=(stance()[0], body.FootAnchor('right', turned))))
    assert caught.value.to_dict()['code'] == 'body.joint'


def test_data_only_body_score_rejects_unknown_and_coerced_fields():
    data = {
        'schema': 'srstudio.body/1.0.0',
        'duration': 2,
        'roots': [{'time': 0, 'root': {'origin': [0, -0.88, 0]}}],
        'stance': [{'side': side, 'frame': {'origin': [x, 0, 0]}} for side, x in [('left', -0.12), ('right', 0.12)]],
    }
    plan = body.compile_body(body.parse_body(data))
    assert all(leg.planted for leg in plan.sample(1).legs)
    for bad in (
        {**data, 'unknown': True},
        {**data, 'duration': '2'},
        {**data, 'validation_hz': True},
        {**data, 'roots': [{'time': 0, 'root': {'origin': [0, -0.88, 0], 'guess': True}}]},
    ):
        with pytest.raises(body.BodyError):
            body.parse_body(bad)


def test_world_transform_preserves_support_and_joint_geometry():
    authored = score()
    transform = Frame(Vec3(2, 0, 1), Quaternion.axis_angle(Vec3(0, 1, 0), 0.3))
    transformed = replace(
        authored,
        roots=tuple(replace(key, root=transform.compose(key.root)) for key in authored.roots),
        stance=tuple(replace(foot, frame=transform.compose(foot.frame)) for foot in authored.stance),
        steps=tuple(replace(step, target=transform.compose(step.target)) for step in authored.steps),
    )
    a, b = body.compile_body(authored).sample(1.75), body.compile_body(transformed).sample(1.75)
    assert b.support_margin == pytest.approx(a.support_margin)
    assert b.center_of_mass.distance(transform.point(a.center_of_mass)) < 1e-12
    for first, second in zip(a.legs, b.legs, strict=True):
        for joint in ('hip', 'knee', 'ankle'):
            assert getattr(second, joint).distance(transform.point(getattr(first, joint))) < 1e-12


def test_distinct_authored_profiles_share_the_support_contract():
    authored = replace(score(), profile=body.BodyProfile(thigh=0.5, shin=0.5, torso_height=0.6))
    plan = body.compile_body(authored)
    for t in (0, 1.5, 2.5, 4):
        sample = plan.sample(t)
        for leg in sample.legs:
            assert leg.hip.distance(leg.knee) == pytest.approx(0.5)
            assert leg.knee.distance(leg.ankle) == pytest.approx(0.5)
        assert sample.support_margin >= plan.profile.support_margin

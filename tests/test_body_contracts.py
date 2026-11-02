"""Adversarial body data, numeric envelopes, support geometry and deterministic bounds."""

from dataclasses import replace

import pytest

from srstudio import body
from srstudio._body_solve import hull, margin
from srstudio.limbs import Frame, Quaternion, Vec3


def score():
    return body.BodyScore(
        2,
        (body.BodyKey(0, Frame(Vec3(0, -0.88, 0))),),
        (body.FootAnchor('left', Frame(Vec3(-0.12, 0, 0))), body.FootAnchor('right', Frame(Vec3(0.12, 0, 0)))),
    )


def data():
    return {
        'schema': 'srstudio.body/1.0.0',
        'duration': 2,
        'roots': [{'time': 0, 'root': {'origin': [0, -0.88, 0]}}],
        'stance': [
            {'side': 'left', 'frame': {'origin': [-0.12, 0, 0]}},
            {'side': 'right', 'frame': {'origin': [0.12, 0, 0]}},
        ],
    }


@pytest.mark.parametrize(
    'value',
    [
        None,
        [],
        {},
        {'schema': 'unknown'},
        {**data(), 'roots': [None]},
        {**data(), 'roots': 'roots'},
        {**data(), 'schema': 'unknown'},
        {**data(), 'profile': {'thigh': '0.43'}},
        {**data(), 'profile': {'knee_limits': [0, '2']}},
        {**data(), 'roots': [{'time': 0, 'root': {'origin': [0, -0.88]}}]},
        {**data(), 'roots': [{'time': 0, 'root': {'origin': [0, -0.88, 0]}, 'torso': [0, 0, 0, 0]}]},
        {**data(), 'steps': [{'side': 'right', 'start': True, 'end': 1, 'target': {'origin': [0, 0, 0]}}]},
    ],
)
def test_malformed_data_never_silently_coerces(value):
    with pytest.raises(body.BodyError):
        body.parse_body(value)


@pytest.mark.parametrize(
    'change',
    [
        {'thigh': 0},
        {'shin': float('nan')},
        {'hip_limit': True},
        {'knee_limits': [0.1, 2]},
        {'knee_limits': (2, 1)},
        {'support_margin': 1},
    ],
)
def test_invalid_profiles_are_rejected(change):
    with pytest.raises(body.BodyError):
        replace(body.BodyProfile(), **change)


@pytest.mark.parametrize(
    'change',
    [
        {'side': 'both'},
        {'start': True},
        {'start': 0.0000001},
        {'end': 0.1},
        {'clearance': 0},
        {'target': 'frame'},
        {'target': Frame(Vec3(0.12, -0.01, 0))},
        {'target': Frame(rotation=Quaternion.axis_angle(Vec3(1, 0, 0), 0.1))},
    ],
)
def test_invalid_steps_do_not_fall_back_to_sliding(change):
    with pytest.raises(body.BodyError):
        replace(body.Step('right', 0, 1, Frame(Vec3(0.12, 0, 0.1))), **change)


@pytest.mark.parametrize(
    'change',
    [
        {'profile': None},
        {'roots': ()},
        {'stance': score().stance[:1]},
        {'roots': (body.BodyKey(1, Frame(Vec3(0, -0.88, 0))),)},
        {'roots': (*score().roots, score().roots[0])},
        {'roots': (*score().roots, body.BodyKey(0.1, Frame(Vec3(0.3, -0.88, 0))))},
        {'steps': (body.Step('right', 0.5, 2, Frame(Vec3(0.12, 0, 0.1))),)},
        {'steps': (body.Step('right', 0.5, 1.5, Frame(Vec3(0.12, 0, 1))),)},
        {'duration': 600},
    ],
)
def test_score_semantic_failures_are_bounded(change):
    with pytest.raises(body.BodyError):
        body.compile_body(replace(score(), **change))


def test_support_hull_and_margin_are_independent_of_corner_order():
    points = [(-1, -1), (1, -1), (1, 1), (-1, 1), (0, 0), (-1, -1)]
    polygon = hull(points)
    assert polygon == hull(list(reversed(points)))
    assert len(polygon) == 4
    assert margin(polygon, Vec3(0, -100, 0)) == 1
    assert margin(polygon, Vec3(2, 0, 0)) == -1


@pytest.mark.parametrize('time', [True, -0.1, 2.1, float('inf')])
def test_sample_bounds_are_typed(time):
    with pytest.raises(body.BodyError):
        body.compile_body(score()).sample(time)


def test_windows_refuse_invalid_spans_and_local_times():
    plan = body.compile_body(score())
    for start, end in ((1, 1), (1.5, 1), (-1, 1), (0, 3)):
        with pytest.raises(body.BodyError):
            plan.window(start, end)
    with pytest.raises(body.BodyError):
        plan.window(0.5, 1).sample(0.6)


def test_discovery_states_supported_physics_units_and_sampling():
    info = body.compile_body(score()).describe()
    assert info['schema'] == 'srstudio.body-plan/1.0.0'
    assert info['units'] == {'distance': 'meters', 'time': 'seconds', 'angle': 'radians'}
    assert info['support']['method'] == 'static mass projection inside planted-foot convex hull'
    assert info['support']['continuous_certificate'] is False
    assert info['capabilities']['flight'] is False
    assert info['capabilities']['rooted_shoulders'] is True
    assert info['drawing']['styles'] == ['solid', 'wire']
    assert info['validation_samples'] == 121

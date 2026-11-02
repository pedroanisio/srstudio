"""Target gaze owns one bounded performance clock, with explicit eye/head coordination."""

import importlib
import math
from dataclasses import replace

import pytest


def api():
    return importlib.import_module('srstudio.gaze')


def make(**kwargs):
    g = api()
    target = g.TargetTrack((g.TargetKey(0, (0, 0, 2)), g.TargetKey(0.5, (0.6, 0.2, 2))))
    return g.GazePlan(g.GazeSpec(target, 1, **kwargs))


def test_eyes_lead_head_and_counter_rotate_to_keep_the_target():
    g = api()
    limits = g.GazeLimits(eye_latency=0.05, head_latency=0.25, head_share=0.4)
    plan = make(limits=limits)
    early = plan.sample(0.2)
    assert early.eye_yaw > 0 and early.head_yaw == 0
    late = plan.sample(1)
    assert late.head_yaw > 0 and late.head_pitch > 0
    assert late.eye_yaw + late.head_yaw == pytest.approx(math.degrees(math.atan2(0.6, 2)))
    assert late.eye_pitch + late.head_pitch == pytest.approx(math.degrees(math.atan2(0.2, math.hypot(0.6, 2))))


def test_translating_observer_and_target_together_preserves_gaze():
    g = api()
    a = make()
    observer = g.TargetTrack((g.TargetKey(0, (1, 3, -2)), g.TargetKey(0.5, (2, 4, -1))))
    target = g.TargetTrack((g.TargetKey(0, (1, 3, 0)), g.TargetKey(0.5, (2.6, 4.2, 1))))
    b = g.GazePlan(replace(a.spec, target=target, observer=observer))
    for t in (0, 0.17, 0.5, 0.73, 1):
        assert b.sample(t).values == pytest.approx(a.sample(t).values)


def test_sampling_and_cut_windows_never_restart_latency_or_depend_on_order():
    plan = make()
    times = (0, 0.11, 0.31, 0.32, 0.8, 1)
    expected = {t: plan.sample(t) for t in times}
    assert {t: plan.sample(t) for t in reversed(times)} == expected
    cut = plan.window(0.31, 1)
    for t in (0.31, 0.32, 0.8, 1):
        assert cut.sample(t - 0.31).values == pytest.approx(expected[t].values)
    assert cut.sample(0).values == plan.sample(0.31).values


def test_source_keys_and_delayed_breakpoints_are_included_in_the_sample_grid():
    g = api()
    target = g.TargetTrack((g.TargetKey(0, (0, 0, 2)), g.TargetKey(0.123, (0.2, 0, 2))))
    spec = g.GazeSpec(target, 1, fps=10, limits=g.GazeLimits(eye_latency=0.02, head_latency=0.07))
    plan = g.GazePlan(spec)
    assert {0, 0.143, 0.193, 1}.issubset({sample.time for sample in plan.samples})
    assert all(abs(s.eye_yaw) <= spec.limits.eye_yaw and abs(s.head_yaw) <= spec.limits.head_yaw for s in plan.samples)


@pytest.mark.parametrize('bad', [True, float('nan'), -1, 601, 1e300])
def test_invalid_duration_is_refused_before_sampling(bad):
    g = api()
    with pytest.raises(g.GazeError) as caught:
        g.GazeSpec(g.TargetTrack((g.TargetKey(0, (0, 0, 1)),)), bad)
    assert caught.value.to_dict()['path'] == 'duration'
    assert caught.value.to_dict()['remedy']


@pytest.mark.parametrize(
    'keys', [(), ((1, (0, 0, 2)),), ((0, (0, 0, 2)), (0, (1, 0, 2))), ((0, (0, 0, 2)), (0.00000001, (1, 0, 2)))]
)
def test_tracks_require_an_owned_bounded_increasing_clock_starting_at_zero(keys):
    g = api()
    with pytest.raises(g.GazeError):
        g.TargetTrack(tuple(g.TargetKey(t, point) for t, point in keys))


@pytest.mark.parametrize('point', [(True, 0, 1), (0, float('nan'), 1), (0, 1), [0, 0, 1], (0, 0, 1e300)])
def test_targets_are_exact_finite_coordinate_triples(point):
    g = api()
    with pytest.raises(g.GazeError):
        g.TargetKey(0, point)


@pytest.mark.parametrize(
    'options',
    [
        {'eye_yaw': 0},
        {'head_share': 2},
        {'eye_latency': -1},
        {'eye_latency': 0.2, 'head_latency': 0.1},
        {'head_pitch': float('inf')},
    ],
)
def test_limits_and_latency_are_explicit_finite_envelopes(options):
    g = api()
    with pytest.raises(g.GazeError):
        g.GazeLimits(**options)


@pytest.mark.parametrize('point', [(0, 0, 0), (1, 0, -1), (100, 0, 1), (0, 100, 1)])
def test_targets_behind_the_observer_or_outside_joint_limits_are_not_silently_clamped(point):
    g = api()
    with pytest.raises(g.GazeError) as caught:
        g.GazePlan(g.GazeSpec(g.TargetTrack((g.TargetKey(0, point),)), 1))
    assert caught.value.to_dict()['code'] in ('gaze.target', 'gaze.bounds')


def test_sample_budget_is_checked_before_constructing_a_large_grid():
    g = api()
    with pytest.raises(g.GazeError) as caught:
        make(fps=120, max_samples=10)
    assert caught.value.to_dict()['code'] == 'gaze.budget'


@pytest.mark.parametrize('time', [True, -0.1, 1.1, float('nan')])
def test_sample_times_must_belong_to_the_performance(time):
    g = api()
    plan = make()
    with pytest.raises(g.GazeError):
        plan.sample(time)


def test_named_mapping_requires_an_explicit_error_allowance_and_supported_states():
    g = api()
    plan = make(limits=g.GazeLimits(head_share=0, eye_yaw=20))
    with pytest.raises(g.GazeError, match='mapping'):
        g.named_gaze(plan, g.NamedGazeMapping(('ahead',), max_error=0))
    keys = g.named_gaze(plan, g.NamedGazeMapping(('ahead', 'left', 'right', 'up'), max_error=0.3))
    assert keys[0] == (0, 'ahead') and keys[-1][1] == 'right'
    assert all(a[0] < b[0] and a[1] != b[1] for a, b in zip(keys, keys[1:], strict=False))
    with pytest.raises(g.GazeError):
        g.NamedGazeMapping(('unknown',), max_error=1)


def test_json_parser_is_closed_and_does_not_coerce_primitives():
    g = api()
    raw = {'duration': 1, 'target': {'keys': [{'time': 0, 'point': [0, 0, 2]}, {'time': 0.5, 'point': [0.6, 0.2, 2]}]}}
    assert g.parse_gaze(raw) == make().spec
    for changed in ({**raw, 'unknown': 1}, {**raw, 'duration': '1'}, {**raw, 'target': {'keys': [], 'extra': True}}):
        with pytest.raises(g.GazeError):
            g.parse_gaze(changed)

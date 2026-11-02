"""Procedural head schedules reject excessive work before sampling or allocation."""

import json
from dataclasses import replace

import pytest

from srstudio import _head_planner
from srstudio.acting import BENTO
from srstudio.head_motion import HeadMotionError, plan


@pytest.mark.parametrize(
    'changes,duration,code,path',
    [
        ({'breath_period': 1e-8}, 4, 'precision', 'style.breath_period'),
        ({'glance_every': 1e-308}, 4, 'precision', 'style.glance_every'),
        ({'idle_hz': 1e308}, 4, 'budget', 'style.idle_hz'),
        ({'idle_hz': 1e6}, 4, 'budget', 'style.idle_hz'),
        ({'breath_period': 0.0001}, 4, 'budget', 'style.breath_period'),
        ({'glance_every': 0.0001}, 4, 'budget', 'style.glance_every'),
        ({'idle_hz': 1e6}, 0.00001, 'precision', 'style.idle_hz'),
        ({'glance_hold': 1e-8}, 4, 'precision', 'style.glance_hold'),
        ({}, 1e-8, 'precision', 'duration'),
        ({}, 1e308, 'precision', 'duration'),
    ],
)
def test_planner_refuses_invalid_schedules_before_generating(monkeypatch, changes, duration, code, path):
    def forbidden(*args, **kwargs):
        pytest.fail('Invalid schedules must fail before procedural generation')

    for name in ('_gaze', '_noise_keys', '_breath_keys'):
        monkeypatch.setattr(_head_planner, name, forbidden)
    style = replace(BENTO.head_rig.style, **changes)
    with pytest.raises(HeadMotionError) as caught:
        plan(style, [], duration)
    diagnostic = caught.value.to_dict()
    assert diagnostic['code'] == f'head.plan.{code}'
    assert diagnostic['path'] == path
    assert diagnostic['expected'] and diagnostic['remedy']
    json.dumps(diagnostic, allow_nan=False)


def test_subnormal_idle_frequency_produces_finite_endpoints():
    style = replace(BENTO.head_rig.style, idle_hz=5e-324)
    motion = plan(style, [], 4)
    assert [t for t, _ in motion.idle_y.keys] == [0, 4]
    motion.check_bounds(style)


def test_repairing_schedule_preserves_repeatable_random_access():
    style = replace(BENTO.head_rig.style, breath_period=3, glance_every=2, idle_hz=0.3)
    a, b = plan(style, [], 8), plan(style, [], 8)
    assert a == b
    for name in ('breath', 'idle_y', 'idle_roll', 'turn'):
        channel = getattr(a, name)
        cut = channel.during(2, 6)
        times = (5.5, 2, 3, 6, 4)
        assert [cut.sample(t) for t in times] == [channel.sample(t) for t in times]

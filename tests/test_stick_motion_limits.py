"""Procedural transport keys fail before mutation when work or numeric ranges are unrepresentable."""

import pytest
from sr_core.scene import Animate

from srstudio import stick, stick_car, stick_windshield
from support.stick_car import canvas


@pytest.mark.parametrize('end,step', [(1e308, 1e-308), (1, 1e-5), (1.7e308, 1e308)])
def test_ride_refuses_unrepresentable_or_over_budget_keys_before_mutation(end, step):
    cv = canvas()
    node = cv.group(cv.comp, 'target', y=300)
    before = cv.scene.to_bytes()
    with pytest.raises(stick.StickDataError):
        stick_car.ride(cv, node, end, step=step)
    assert cv.scene.to_bytes() == before


def test_windshield_preflights_unrepresentable_period_before_drawing():
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(stick.StickDataError):
        stick_windshield.windshield(cv, cv.comp, 1, speed=1e-320)
    assert cv.scene.to_bytes() == before


def test_fast_windshield_cycles_have_ordered_keys():
    cv = canvas()
    stick_windshield.windshield(cv, cv.comp, 0.01, speed=1001)
    animations = list(cv.scene.iter('animate'))
    assert len(animations) == 2
    for animation in animations:
        times = [float(key.time) for key in animation.elements()]
        assert times[0] == 0 and all(a < b for a, b in zip(times, times[1:], strict=False))


@pytest.mark.parametrize('builder', [stick_car.ride, stick_windshield.windshield])
@pytest.mark.parametrize('budget', [True, 1, 20001, 3.5, None])
def test_invalid_key_budget_is_atomic(builder, budget):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(stick.StickDataError, match='max_keys'):
        builder(cv, cv.comp, 1, max_keys=budget)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize(
    'builder,options', [(stick_car.ride, {'step': 0.5}), (stick_windshield.windshield, {'speed': 1})]
)
def test_key_budget_accepts_exact_boundary_and_rejects_one_less(builder, options):
    cv = canvas()
    target = cv.group(cv.comp, 'target', y=300)
    before = cv.scene.to_bytes()
    with pytest.raises(stick.StickDataError, match='max_keys'):
        builder(cv, target, 1, max_keys=2, **options)
    assert cv.scene.to_bytes() == before
    builder(cv, target, 1, max_keys=3, **options)
    animations = list(cv.scene.iter('animate'))
    assert animations and all(len(list(a.elements())) == 3 for a in animations)
    fresh = canvas()
    builder(fresh, fresh.group(fresh.comp, 'target', y=300), 1, max_keys=3, **options)
    assert cv.scene.to_bytes() == fresh.scene.to_bytes()


@pytest.mark.parametrize('end,speed', [(1e308, 1e308), (10000, 1), (1e-6, 1e7), (1e17, 1e-17)])
def test_windshield_refuses_over_budget_or_collapsed_keys_atomically(end, speed):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(stick.StickDataError):
        stick_windshield.windshield(cv, cv.comp, end, speed=speed)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('end,step,base,amplitude', [(1e-5, 1e-5, 0, 1), (1, 0.5, 1.7e308, 1.7e308)])
def test_ride_refuses_collapsed_times_and_overflowing_values(end, step, base, amplitude):
    cv = canvas()
    node = cv.group(cv.comp, 'target', y=base)
    before = cv.scene.to_bytes()
    with pytest.raises(stick.StickDataError):
        stick_car.ride(cv, node, end, step=step, amplitude=amplitude)
    assert cv.scene.to_bytes() == before


def test_zero_motion_does_not_spend_key_budget():
    cv = canvas()
    before = cv.scene.to_bytes()
    stick_car.ride(cv, cv.comp, 1e308, step=1e-308, amplitude=0, max_keys=2)
    assert cv.scene.to_bytes() == before
    stick_windshield.windshield(cv, cv.comp, 1e308, speed=0, max_keys=2)
    assert not list(cv.scene.iter('animate'))


@pytest.mark.parametrize('name', ['stick-ride', 'stick-windshield'])
def test_discovery_declares_key_budget(name):
    from srstudio import registry

    entry = next(e for e in registry.entries() if e.name == name)
    budget = entry.describe()['contract']['arguments']['properties']['max_keys']
    assert budget['type'] == 'integer'
    assert budget['minimum'] == 2 and budget['maximum'] == budget['default'] == 20000


def test_fast_road_shrinks_and_resets_in_engine_at_random_access_times(scene_render, tmp_path):
    from support.acting import evaluate

    cv = canvas(font=None)
    stick_windshield.windshield(cv, cv.comp, 0.002, speed=1000)
    target = next(
        g for g in cv.scene.iter('group') if any(a.property == 'scaleX' for a in g.elements() if isinstance(a, Animate))
    )
    path = tmp_path / 'fast-road.xml'
    path.write_bytes(cv.scene.to_bytes())
    for time, expected in [(0.001, 1), (0.0005, 0.625), (0, 1), (0.00025, 0.8125), (0.001, 1)]:
        node = next(n for n in evaluate(scene_render, path, time) if n['id'] == target.id)
        assert (node['world'][0], node['world'][3]) == pytest.approx((expected, expected))

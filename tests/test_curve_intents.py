"""Intent selection describes source derivatives separately from emitted sampling."""

import pytest

from srstudio import curves


@pytest.mark.parametrize('intent', ['stop-smoothly', 'pass-through'])
def test_continuous_intents_join_without_velocity_or_acceleration_jumps(intent):
    track = curves.track(((0, 0), (1, 1), (2, 3)), intent=intent)
    h = 1e-4
    values = [track.sample(1 + i * h) for i in (-2, -1, 0, 1, 2)]
    assert abs((values[2] - values[1]) / h - (values[3] - values[2]) / h) < 0.001
    assert abs((values[0] - 2 * values[1] + values[2]) / h**2 - (values[4] - 2 * values[3] + values[2]) / h**2) < 0.03
    speed = (values[3] - values[1]) / (2 * h)
    assert abs(speed) < 0.001 if intent == 'stop-smoothly' else speed > 0.5
    assert track.describe()['source']['acceleration'] is True


def test_impact_is_explicitly_discontinuous_and_unknown_intents_are_repairable():
    impact = curves.track(((0, 0), (1, 1)), intent='intentional-impact')
    assert impact.describe()['source']['velocity'] is False
    assert impact.sample(0.5) == pytest.approx(0.125)
    with pytest.raises(curves.CurveError) as caught:
        curves.track(((0, 0), (1, 1)), intent='smoothish')
    assert caught.value.to_dict()['path'] == 'intent'


def test_curve_emission_is_bounded_and_does_not_claim_source_derivatives():
    from sr_core.scene import Scene

    from srstudio import Canvas

    scene = Scene(version='auto')
    scene.add_project(width=100, height=100, fps='24', duration=2)
    cv = Canvas(scene, font_asset=None)
    group = cv.group(cv.comp, 'move')
    track = curves.track(((0, 1), (1, 2)))
    before = scene.to_bytes()
    with pytest.raises(curves.CurveError):
        track.emit(cv, group, 'scaleX', fps=24, max_keys=2)
    assert scene.to_bytes() == before
    report = track.emit(cv, group, 'scaleX', fps=24, max_keys=25)
    assert report['keys'] == 25 and report['interpolation'] == 'linear'
    assert report['inherits_source_derivatives'] is False
    assert scene.check() == []


def test_curve_freezes_caller_owned_key_arrays():
    keys = [[0, 0], [1, 1]]
    track = curves.track(keys)
    keys.clear()
    assert track.keys == ((0, 0), (1, 1))
    assert track.sample(0.5) == pytest.approx(0.5)


@pytest.mark.parametrize('keys', [[(0, 0), (0, 1)], [(0, float('nan'))], [(0, 1, 2)]])
def test_invalid_curve_keys_raise_the_public_curve_error(keys):
    with pytest.raises(curves.CurveError):
        curves.track(keys)

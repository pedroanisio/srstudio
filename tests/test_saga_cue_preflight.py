"""Saga impact and sampled-contact inputs are checked before any scene mutation."""

import math

import pytest

from srstudio import saga_sets as sets
from srstudio.saga import SagaError
from support.saga import canvas


@pytest.mark.parametrize('builder', [sets.cockpit, sets.cockpit_front])
@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize('hit', [True, False, '1', math.nan, math.inf])
def test_hits_are_finite_numeric_cues_before_scene_creation(builder, local, hit):
    cv, control = canvas(), canvas()
    cv.local_time = local
    before = cv.scene.to_bytes()
    with pytest.raises(SagaError, match='hit'):
        builder(cv, cv.comp, end=4, hit=hit)
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize(
    'options',
    [
        {'at': True},
        {'scale': 0},
        {'scale': -1},
        {'scale': True},
        {'scale': math.nan},
        {'elbow': (math.nan, 0)},
        {'elbow': (540,)},
        {'elbow': sets.stick_grip(0)},
        {'elbow': (math.inf, 0)},
    ],
)
def test_jab_geometry_and_time_are_validated_before_drawing(local, options):
    cv, control = canvas(), canvas()
    cv.local_time = local
    before = cv.scene.to_bytes()
    kwargs = dict(at=1, sleeve='#ffffff', hand='#996633', elbow=(404, 1040), scale=1)
    with pytest.raises(SagaError, match='jab'):
        sets.cockpit_front(cv, cv.comp, end=4, jab=sets.Jab(**(kwargs | options)))
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')


@pytest.mark.parametrize('end', [0, True, math.nan, math.inf, 1e308, 20_000 / 24])
def test_jab_sampling_rejects_invalid_or_over_budget_duration(end):
    jab = sets.Jab(1, '#ffffff', '#996633', (404, 1040), 1)
    with pytest.raises(SagaError, match='jab'):
        sets.jab_frames(jab, end)


def test_jab_sampling_budget_is_checked_before_console_or_id_creation():
    cv, control = canvas(), canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(SagaError, match='jab'):
        sets.cockpit_front(cv, cv.comp, end=20_000 / 24, jab=sets.Jab(1, '#ffffff', '#996633', (404, 1040), 1))
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')


@pytest.mark.parametrize('options', [{'scale': 1e308}, {'elbow': (1.7e308, 1.7e308)}])
def test_jab_rejects_overflowing_derived_geometry(options):
    values = dict(at=1, sleeve='#ffffff', hand='#996633', elbow=(404, 1040), scale=1)
    with pytest.raises(SagaError, match='jab'):
        sets.Jab(**(values | options))


@pytest.mark.parametrize(
    'helper,value',
    [('stick_ball', math.nan), ('stick_grip', math.inf), ('stick_ball', True), ('hand_at', math.nan), ('hand_at', '1')],
)
def test_contact_helpers_reject_nonfinite_or_nonnumeric_sample_inputs(helper, value):
    args = (sets.Jab(1, '#ffffff', '#996633', (404, 1040), 1),) if helper == 'hand_at' else ()
    with pytest.raises(SagaError):
        getattr(sets, helper)(*args, value)


def test_jab_frame_budget_includes_the_terminal_sample():
    jab = sets.Jab(1, '#ffffff', '#996633', (404, 1040), 1)
    end = (sets.MAX_JAB_FRAMES - 1) / 24
    frames = sets.jab_frames(jab, end)
    assert len(frames) == sets.MAX_JAB_FRAMES == 20_000
    assert frames[0] == (0, 0) and frames[-1] == (round(end, 4), 10)


@pytest.mark.parametrize('at', [1e308, 1e16])
def test_jab_cue_requires_distinct_representable_phase_times(at):
    with pytest.raises(SagaError, match='jab'):
        sets.Jab(at, '#ffffff', '#996633', (404, 1040), 1)

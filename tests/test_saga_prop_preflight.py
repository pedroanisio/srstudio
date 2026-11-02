"""Invalid Saga prop placement and dimensions fail at the builder boundary."""

import math

import pytest

from srstudio import saga
from srstudio import saga_sets as sets
from srstudio.saga import SagaError
from support.saga import canvas


@pytest.mark.parametrize('builder', [sets.cube_station, sets.freighter, sets.fighter, sets.pebble, saga.handbook])
@pytest.mark.parametrize('at', [(math.nan, 100), (100, math.inf), (True, 100), (100,)])
def test_props_preflight_placement_without_consuming_scene_ids(builder, at):
    cv, control = canvas(), canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(SagaError, match='position'):
        builder(cv, cv.comp, at=at, end=4)
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')


@pytest.mark.parametrize(
    'builder,parameter', [(sets.cube_station, 'size'), (sets.freighter, 'scale'), (sets.fighter, 'scale')]
)
@pytest.mark.parametrize('value', [0, -1, True, math.inf, math.nan])
def test_props_preflight_positive_dimensions(builder, parameter, value):
    cv, control = canvas(), canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(SagaError, match=parameter):
        builder(cv, cv.comp, at=(540, 1000), end=4, **{parameter: value})
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')


@pytest.mark.parametrize('rise', [True, math.nan, math.inf])
def test_pebble_rejects_invalid_travel_before_drawing(rise):
    cv, control = canvas(), canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(SagaError, match='rise'):
        sets.pebble(cv, cv.comp, at=(540, 1000), end=4, rise=rise)
    assert cv.scene.to_bytes() == before
    assert cv.uid('probe') == control.uid('probe')

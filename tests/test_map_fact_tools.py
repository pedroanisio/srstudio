"""The map fact tools: an antipode is the far side of the Earth, a clock is one distinct offset."""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools" / "maps"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


antipodes = _load("antipodes")
time_zones = _load("time_zones")


@pytest.mark.parametrize(
    ("point", "far"), [((40.0, -74.0), (-40.0, 106.0)), ((40.0, 116.0), (-40.0, -64.0)), ((0.0, 0.0), (0.0, 180.0))]
)
def test_an_antipode_flips_the_latitude_and_goes_half_way_round(point, far):
    assert antipodes.antipode(*point) == far


def test_going_to_the_far_side_twice_comes_home():
    assert antipodes.antipode(*antipodes.antipode(21.7, 99.3)) == (21.7, 99.3)


def test_the_sun_is_overhead_at_the_equator_near_an_equinox_noon():
    noon = dt.datetime(2026, 3, 20, 12, 7, tzinfo=dt.timezone.utc)
    assert time_zones.altitude(0.0, 0.0, noon) > 88.0


def test_the_sun_is_below_the_horizon_on_the_far_side():
    noon = dt.datetime(2026, 3, 20, 12, 7, tzinfo=dt.timezone.utc)
    assert time_zones.altitude(0.0, 180.0, noon) < time_zones.HORIZON


def test_a_clock_is_a_distinct_offset_not_a_zone():
    moment = dt.datetime(2026, 1, 15, 12, tzinfo=dt.timezone.utc)
    assert time_zones.clocks(["America/Guadeloupe", "America/Martinique"], moment) == {-4.0}


def test_a_summer_moves_a_clock():
    zones = ["Europe/Paris"]
    winter = dt.datetime(2026, 1, 15, 12, tzinfo=dt.timezone.utc)
    summer = dt.datetime(2026, 7, 15, 12, tzinfo=dt.timezone.utc)
    assert time_zones.clocks(zones, winter) == {1.0}
    assert time_zones.clocks(zones, summer) == {2.0}

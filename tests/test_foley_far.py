"""Sounds of a place: a hum that cuts dead, and an alarm and a dog from across town, thin and in the distance."""

from __future__ import annotations

import pytest

from srstudio import foley
from srstudio.foley import FoleyError


def rms(samples: list[float]) -> float:
    return (sum(v * v for v in samples) / len(samples)) ** 0.5


def test_a_hum_runs_for_as_long_as_it_is_asked():
    assert foley.hum(5.0).seconds == 5.0


def test_a_hum_stops_dead_and_does_not_fade():
    rate = foley.MIN_RATE
    bed = foley.bursts((0.0,), 6.0, foley.hum(4.0), rate=rate)
    before = bed[int(3.6 * rate) : int(3.95 * rate)]
    after = bed[int(4.02 * rate) : int(5.0 * rate)]
    assert rms(after) == 0.0
    assert rms(before) > rms(bed[int(1.0 * rate) : int(1.4 * rate)]) * 0.6  # still at level as it stops


def test_a_hum_is_low():
    assert foley.hum(2.0).tone_hz < 130 and foley.hum(2.0).tone >= 0.6


@pytest.mark.parametrize("bad", [0.0, -1.0, 9.0, "x"])
def test_a_hum_it_cannot_make_is_refused(bad):
    with pytest.raises(FoleyError):
        foley.hum(bad)


def test_a_far_alarm_alternates_its_two_tones_from_its_start():
    cues = foley.far_alarm(10.0, 1.2)
    hi, lo = cues[foley.ALARM_HIGH], cues[foley.ALARM_LOW]
    assert hi[0] == 10.0 and lo[0] > hi[0]
    assert hi[1] > lo[0]
    assert max(*hi, *lo) + foley.ALARM_HIGH.seconds <= 11.2 + 1e-6


def test_a_far_alarm_is_thin():
    assert foley.ALARM_HIGH.low_hz < 900 and foley.ALARM_HIGH.tone_hz > 700


@pytest.mark.parametrize(("start", "seconds"), [(-1.0, 1.0), (1.0, 0.0), (1.0, 0.1), ("x", 1.0)])
def test_an_alarm_it_cannot_play_is_refused(start, seconds):
    with pytest.raises(FoleyError):
        foley.far_alarm(start, seconds)


def test_a_far_bark_is_short_and_comes_in_a_burst():
    assert foley.FAR_BARK.seconds < 0.3
    assert foley.far_barks(4.0, 3) == (4.0, 4.34, 4.68)


def test_no_barks_is_refused():
    with pytest.raises(FoleyError):
        foley.far_barks(4.0, 0)

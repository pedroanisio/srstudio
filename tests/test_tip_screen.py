"""Tip Screen (episode 12) as data: the script, the taps against the tablet's options, and the schedule that lands
each tap right after the number it answers."""

import inspect
import sys
from pathlib import Path

import pytest

from srstudio import props

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import tip_screen_audio

        return tip_screen_audio
    finally:
        sys.path.pop(0)


def test_two_distinct_voices_and_every_line_has_a_speaker(data):
    assert len({v.id for v in data.VOICES.values()}) == 2
    assert {line.role for line in data.SCRIPT} == set(data.VOICES)
    assert data.SCRIPT[0].text.endswith("?")  # the hook is a question


def test_every_tap_is_an_effect_and_picks_an_option_the_tablet_has(data):
    options = inspect.signature(props.tip_tablet).parameters["options"].default
    effects = {e.id for e in data.EFFECTS}
    for tap, (whose, index) in data.TAPS.items():
        assert tap in effects and whose in data.VOICES
        assert 0 <= index < len(options)
    assert options[data.TAPS["tap-1"][1]] == "25%"  # the first tap is Ava's "Twenty-five?"


def test_the_schedule_is_in_order_and_each_tap_follows_its_line(data):
    speech = [1.0 + 0.1 * i for i in range(len(data.SCRIPT))]
    effect = {e.id: e.seconds for e in data.EFFECTS}
    plan = data.schedule(speech, effect)
    assert len(plan.lines) == len(data.SCRIPT)
    assert list(plan.lines) == sorted(plan.lines) and plan.lines[0] == data.LEAD
    for n, tap in enumerate(sorted(data.TAPS), start=5):
        assert plan.effects[tap] == pytest.approx(plan.lines[n] + speech[n] + 0.05)
    assert plan.lines[5] - (plan.effects["tablet-set"] + effect["tablet-set"] + 0.05 + speech[4]) == pytest.approx(
        data.STARE
    )

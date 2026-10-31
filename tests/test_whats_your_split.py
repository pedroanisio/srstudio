"""What's Your Split as data: arm A holds its first frame and the payoff message stays up long enough to read."""

import sys
from pathlib import Path

import pytest

from srstudio import stick_home

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import whats_your_split_audio

        return whats_your_split_audio
    finally:
        sys.path.pop(0)


def test_arm_a_holds_at_least_a_second_with_no_bed(data):
    assert data.SCRIPT.still == data.HELD >= 1.0
    assert data.SCRIPT.bed is None


def test_the_opening_take_speaks_after_the_hold_and_is_not_an_effect(data):
    assert not data.SCRIPT.takes[0].is_effect


def test_the_payoff_message_holds_past_the_ping(data):
    take = next(t for t in data.SCRIPT.takes if t.shot == "dog")
    assert take.seconds + take.hold == pytest.approx(1.8)


def test_both_messages_fit_the_insert():
    assert len("Which dog food do you buy") <= stick_home.MESSAGE_CHARS

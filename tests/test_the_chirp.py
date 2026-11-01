"""The Chirp as data: arm A holds its first frame, the alarm chirps in the voices the story needs, and every line stays
on the premade voices."""

import sys
from pathlib import Path

import pytest

from srstudio import foley

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import the_chirp_audio

        return the_chirp_audio
    finally:
        sys.path.pop(0)


def test_arm_a_holds_at_least_a_second_with_no_bed(data):
    assert data.SCRIPT.still == data.HELD >= 1.0
    assert data.SCRIPT.bed is None


def test_the_opening_take_speaks_after_the_hold_and_is_not_an_effect(data):
    assert not data.SCRIPT.takes[0].is_effect


def test_the_birds_are_one_recording(data):
    prompts = {t.prompt for t in data.SCRIPT.takes if t.text == "[BIRDS]"}
    assert prompts == {data.BIRDS}


def test_the_buried_chirp_sits_below_the_one_behind_the_door():
    assert foley.CHIRP_BURIED.tone_hz < foley.CHIRP_SHUT.tone_hz < foley.CHIRP.tone_hz

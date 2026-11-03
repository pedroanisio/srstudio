"""Trash Day as data: arm B moves at once, the slug stays but the words say trash, and the last line is Walt's."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import bin_day_audio

        return bin_day_audio
    finally:
        sys.path.pop(0)


def test_arm_b_has_no_still_and_speaks_at_once(data):
    assert data.SCRIPT.still == 0
    assert data.SCRIPT.bed is None
    assert not data.SCRIPT.takes[0].is_effect


def test_nobody_says_bin(data):
    assert all("bin" not in take.text.lower().split() for take in data.SCRIPT.takes)
    assert "Trash Day" in data.SCRIPT.title


def test_the_driver_is_held_on(data):
    takes = {take.id: take for take in data.SCRIPT.takes}
    assert takes["14"].actor == "driver" and takes["14"].hold >= 1.2
    assert takes["15"].is_effect and takes["15"].hold >= 1.2


def test_the_last_line_is_walts(data):
    assert data.SCRIPT.takes[-1].text == "Same time next week."


def test_every_shot_is_declared_and_used(data):
    assert {take.shot for take in data.SCRIPT.takes} == set(data.SHOTS)


def test_only_voices_the_reel_is_cleared_for(data):
    ids = {voice.id for voice in data.SCRIPT.voices.values()}
    assert ids == {"JBFqnCBsd6RMkjVDRZzb", "pFZP5JQG7iQjIQuC4Bku", "pqHfZKP75CvOlQylNhV4"}

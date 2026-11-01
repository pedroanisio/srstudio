"""Wave Back as data: arm B moves on frame 1 and speaks at once, the arm is held on, and the last line ends the reel."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import wave_back_audio

        return wave_back_audio
    finally:
        sys.path.pop(0)


def test_arm_b_has_no_still_and_no_bed(data):
    assert data.SCRIPT.still == 0
    assert data.SCRIPT.bed is None


def test_she_speaks_early_and_is_held_on_before_the_turn(data):
    takes = {take.id: take for take in data.SCRIPT.takes}
    assert not takes["01"].is_effect
    assert takes["04"].is_effect and takes["04"].hold >= 1.2
    assert takes["14"].hold >= 1.2


def test_the_last_take_is_his_stretch(data):
    assert data.SCRIPT.takes[-1].text == "...Stretching."
    assert data.SCRIPT.takes[-1].shot == "man"


def test_every_class_member_has_a_look_and_a_place(data):
    places = sum(len(row) for _, _, row in data.ROWS)
    assert places == 6 <= len(data.CLASS)

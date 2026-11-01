"""Seat Belt Sign as data: arm A holds its still, the cabin voice is one line, and the reel ends on Dev, holding."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import seat_belt_sign_audio

        return seat_belt_sign_audio
    finally:
        sys.path.pop(0)


def test_arm_a_holds_a_still_and_has_no_bed(data):
    assert data.SCRIPT.still == data.STILL == 1.0
    assert data.SCRIPT.bed is None


def test_the_hook_is_her_first_line(data):
    assert data.SCRIPT.takes[0].text == data.HOOK


def test_the_rear_door_lands_on_a_held_dev(data):
    takes = {take.id: take for take in data.SCRIPT.takes}
    assert takes["08"].hold >= 1.2  # before the chime
    assert takes["10"].actor == "cabin" and takes["10"].hold >= 1.2


def test_the_reel_ends_on_the_door_behind_him(data):
    last = data.SCRIPT.takes[-1]
    assert last.is_effect and last.shot == "last" and last.hold >= 1.2


def test_every_shot_is_declared_and_used(data):
    assert {take.shot for take in data.SCRIPT.takes} == set(data.SHOTS)


def test_only_voices_the_reel_is_cleared_for(data):
    ids = {voice.id for voice in data.SCRIPT.voices.values()}
    assert ids == {"bIHbv24MWmeRgasZH58o", "cgSgspJ2msm6clMCkdW9", "Xb7hH8MSUJpSbSDYk0k2"}


def test_a_seated_pose_lowered_into_the_hung_row_keeps_its_shape(data):
    seated = data.stick_airport.SQUEEZED["tucked-up"]
    lowered = data.POSES["in-seat"]
    assert lowered.head[0] == seated.head[0] and lowered.head[1] - seated.head[1] == data.SHIFT - (data.DROP - 1700.0)

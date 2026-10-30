"""Hold the Door (Stick 10) as data: the first second is a held frame with nobody moving, the hook is on screen, the
stranger keeps one voice across the years, the cameras keep the door and the face on the glass in frame, no shot
runs on after the door has shut and the button, and the release pins what the build drew."""

import sys
from pathlib import Path

import pytest

from srstudio import stick_door

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import hold_the_door_audio

        return hold_the_door_audio
    finally:
        sys.path.pop(0)


def by_id(data):
    return {t.id: t for t in data.SCRIPT.takes}


def framed(camera, point):
    """Where ``point`` (frame pixels of the uncut set) lands through ``camera`` = (focus, zoom, to)."""
    (fx, fy), zoom, (tx, ty) = camera
    return tx + (point[0] - fx) * zoom, ty + (point[1] - fy) * zoom


def test_the_arm_a_opening_holds_one_second_and_the_hook_is_short(data):
    assert data.SCRIPT.still == pytest.approx(data.STILL) and data.STILL == pytest.approx(1.0)
    assert data.HOOK == "You held the door too early."
    assert data.SCRIPT.bed is None


def test_the_stranger_keeps_one_voice_and_the_button_is_devs(data):
    takes = by_id(data)
    assert takes["01"].actor == takes["09"].actor == "stranger"
    assert takes["12"].actor == "dev" and takes["12"].shot == "end"
    assert data.SCRIPT.takes[-1] is takes["12"]


def test_every_voice_is_a_distinct_premade_one(data):
    voices = list(data.SCRIPT.voices.values())
    assert len(voices) == len(set(voices))


@pytest.mark.parametrize("shot", ["two", "end"])
def test_the_closing_shots_keep_dev_in_frame(data, shot):
    x, y = framed(data.CAMERAS[shot], (834.0, 780.0))
    assert 92 < x < 988 and 200 < y < 1400


def test_the_closing_two_shot_keeps_the_face_on_the_glass(data):
    x, y = framed(
        data.CAMERAS["two"], (data.FACE_AT[0] + 540 * data.FACE_SCALE, data.FACE_AT[1] + 754 * data.FACE_SCALE)
    )
    assert 92 < x < 700 and 200 < y < 1400


def test_the_door_shuts_before_the_face_arrives(data):
    assert data.SWING + stick_door.SWING_STEPS * stick_door.SWING_STEP <= data.HIT


def test_the_crowd_passes_inside_the_limits_of_the_path(data):
    assert 0 < data.PASS_FROM < data.PASS_TO <= stick_door.MAX_DEPTH
    assert all(-1 <= lane <= 1 for lane in data.PASS_LANES)

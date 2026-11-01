"""Pay in Four as data: the two voices, the holds the script asks for, the hook, and the set's cameras that keep the
marks, the hook and the board in frame without running off the set."""

import sys
from pathlib import Path

import pytest

from srstudio import stick_door, stick_porch

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import pay_in_four_audio

        return pay_in_four_audio
    finally:
        sys.path.pop(0)


def by_id(data):
    return {t.id: t for t in data.SCRIPT.takes}


def framed(camera, point):
    (fx, fy), zoom, (tx, ty) = camera
    return tx + (point[0] - fx) * zoom, ty + (point[1] - fy) * zoom


def test_the_voices_are_the_briefs_and_there_is_no_bed(data):
    assert {v.name for v in data.SCRIPT.voices.values()} == {"Jessica", "Callum"}
    assert data.SCRIPT.seed == 3306 and data.SCRIPT.bed is None
    assert data.HOOK == "PAYMENT 3 OF 4: MISSED"


def test_the_lines_run_as_the_script_has_them(data):
    lines = [t.text for t in data.SCRIPT.takes]
    assert lines[0] == "Ma'am. We're here about the burrito." and lines[-1] == "Four easy payments."
    assert "Or two hundred fourteen dollars." in lines and "With guac." in lines and "Can I split that?" in lines


def test_the_holds_are_as_long_as_the_script_says(data):
    takes = by_id(data)
    assert takes["09"].hold == pytest.approx(1.2)
    assert takes["12"].hold == pytest.approx(1.5)
    assert takes["07"].hold > data.TRUCK_RUN + data.HOOK_LAG  # the truck stops and the hook is coming down in the hold
    assert data.AT_NOOR < takes["12"].hold
    assert data.TURN_AFTER < takes["13"].hold


def test_the_door_moves_before_the_first_second(data):
    assert 0 < data.OPENS + stick_door.SWING_STEPS * stick_door.SWING_STEP < 1.0


@pytest.mark.parametrize("shot", ["two", "repo", "noor", "board"])
def test_no_camera_runs_off_the_set(data, shot):
    camera = data.CAMERAS[shot]
    left, top = framed(camera, (0.0, 0.0))
    right, bottom = framed(camera, (1080.0, 1920.0))
    assert left <= 0 and top <= 0 and right >= 1080 and bottom >= 1920


@pytest.mark.parametrize("shot", ["two", "noor", "board"])
def test_the_long_shots_keep_the_cactus(data, shot):
    x, y = framed(data.CAMERAS[shot], (975.0, 1230.0))
    assert 0 < x < 1060 and y < 1560


def test_the_hook_comes_down_in_the_repo_shot_clear_of_the_bug_box(data):
    x, y, scale = stick_porch.truck_place(stick_porch.PARKED)
    hook_x, hook_y = framed(data.CAMERAS["repo"], (x, y + (stick_porch.BOOM_TOP + stick_porch.HOOK_LOW) * scale))
    assert 0 < hook_x < 900 and 332 < hook_y < 1100

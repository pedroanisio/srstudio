"""Consulting as data: the still opening, the held beats, the drawer's turn, and framing that keeps both marks."""

import sys
from pathlib import Path

import pytest

from srstudio import stick_interview, stick_reel

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import consulting_audio

        return consulting_audio
    finally:
        sys.path.pop(0)


def by_id(data):
    return {t.id: t for t in data.SCRIPT.takes}


def test_the_voices_are_the_briefs_and_there_is_no_bed(data):
    assert {v.name for v in data.SCRIPT.voices.values()} == {"Jessica", "Will"}
    assert data.SCRIPT.seed == 3313 and data.SCRIPT.bed is None
    assert data.HOOK == "THAT LINE ON YOUR RESUME"


def test_it_opens_still(data):
    assert data.SCRIPT.still == data.STILL == pytest.approx(0.45)


def test_the_lines_run_as_the_script_has_them(data):
    lines = [t.text for t in data.SCRIPT.takes]
    assert lines[0] == "There's a two-year gap here."
    assert lines[1] == "I was consulting."
    assert lines[5] == "My couch."
    assert lines[8] == "What hours?" and lines[9] == "From noon to noon."
    assert lines[-3:] == ["Consulting.", "From noon to noon?", "From noon to noon."]


def test_the_held_beats_are_real_holds(data):
    takes = by_id(data)
    assert takes["10"].hold == data.STARE_HOLD and data.TURN_AT < data.STARE_HOLD
    assert takes["11"].hold == data.INSERT_AFTER + data.DRAWER_HOLD and data.DRAWER_AT < data.DRAWER_HOLD
    assert takes["12"].hold == data.RESPECT_HOLD
    assert takes["13"].hold == data.SHAKE_HOLD and data.SHAKES[-1] < data.SHAKE_HOLD


def test_the_shots_it_names_are_declared(data):
    assert {t.shot for t in data.SCRIPT.takes} <= set(data.SHOTS)


def test_no_camera_runs_off_the_set(data):
    for focus, zoom, at in data.CAMERAS.values():
        left = at[0] - focus[0] * zoom
        top = at[1] - focus[1] * zoom
        assert left <= 0 and left + 1080 * zoom >= 1080
        assert top <= 0 and top + 1920 * zoom >= 1920


@pytest.mark.parametrize(("shot", "heads"), [("two", ("dev", "noor")), ("dev", ("dev",)), ("noor", ("noor",))])
def test_each_speaking_shot_keeps_its_faces_and_both_marks(data, shot, heads):
    stick_reel.check_framing(
        data.CAMERAS[shot], faces=tuple(data.FACES[h] for h in heads), marks=tuple(data.MARKS.values())
    )


def test_the_drawer_close_up_has_the_turn_in_it(data):
    focus, zoom, at = data.CAMERAS["drawer"]
    left, top, width, height = stick_interview.BOTTOM_DRAWER
    for x, y in ((left, top), (left + width, top + height + stick_interview.DRAWER_OUT)):
        assert 0 < at[0] + (x - focus[0]) * zoom < 1080
        assert 0 < at[1] + (y - focus[1]) * zoom < 1920

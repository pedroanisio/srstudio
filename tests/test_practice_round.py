"""Practice Round as data: the lines as decided, the real holds, and framing that keeps faces and both marks."""

import sys
from pathlib import Path

import pytest

from srstudio import show, stick_reel, stick_table

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import practice_round_audio

        return practice_round_audio
    finally:
        sys.path.pop(0)


def by_id(data):
    return {t.id: t for t in data.SCRIPT.takes}


def test_the_voices_are_the_batch_s_and_there_is_no_bed(data):
    assert {v.name for v in data.SCRIPT.voices.values()} == {"Will", "Jessica"}
    assert data.SCRIPT.seed == 3404 and data.SCRIPT.bed is None and data.SCRIPT.still == 0


def test_two_speak_and_the_last_line_stays_the_author_s(data):
    assert {t.actor for t in data.SCRIPT.takes} == {"dev", "noor"}
    last = data.SCRIPT.takes[-1]
    assert (last.actor, last.text) == ("noor", "We'll let you know.")


def test_the_overlay_never_repeats_a_line(data):
    assert data.HOOK.lower() not in " ".join(t.text.lower() for t in data.SCRIPT.takes)


def test_the_holds_are_the_script_s(data):
    takes = by_id(data)
    assert takes["12"].hold == data.STARE_HOLD == 2.0
    assert takes["13"].hold >= 1.5
    assert takes["10"].hold >= 1.5


def test_the_bedding_lands_after_the_line_and_is_held(data):
    last = data.SCRIPT.takes[-1]
    assert last.hold == data.BEDDING_AT + data.BEDDING_RUN + data.END_HOLD
    assert data.BEDDING_AT > 0 and data.END_HOLD >= 1.2


def test_the_shots_it_names_are_declared(data):
    assert {t.shot for t in data.SCRIPT.takes} <= set(data.SHOTS)


def test_no_camera_runs_off_the_set(data):
    for focus, zoom, at in data.CAMERAS.values():
        left = at[0] - focus[0] * zoom
        top = at[1] - focus[1] * zoom
        assert left <= 0 and left + 1080 * zoom >= 1080
        assert top <= 0 and top + 1920 * zoom >= 1920


@pytest.mark.parametrize(
    ("shot", "heads"),
    [
        ("two", ("dev", "noor")),
        ("dev", ("dev",)),
        ("noor", ("noor",)),
        ("close", ("noor",)),
        ("planks", ("dev",)),
        ("end", ("dev",)),
    ],
)
def test_each_shot_keeps_its_faces_and_both_marks(data, shot, heads):
    stick_reel.check_framing(
        data.CAMERAS[shot], faces=tuple(data.FACES[h] for h in heads), marks=tuple(data.MARKS.values())
    )


def test_noor_standing_stays_off_the_bug_in_the_two_shot(data):
    (fx, fy), zoom, (tx, ty) = data.CAMERAS["two"]
    x = tx + (stick_table.RIGHT_AT[0] - stick_table.POSES["up"].head[0] - fx) * zoom
    y = ty + (stick_table.RIGHT_AT[1] + stick_table.POSES["up"].head[1] - fy) * zoom
    assert x + 100 < show.BUG_BOX[0] or y - 100 > show.BUG_BOX[3]


def test_the_bedding_comes_from_off_the_end_shot_and_stops_on_the_table(data):
    (fx, _), zoom, (tx, _) = data.CAMERAS["end"]
    assert tx + (data.BEDDING_FROM - 120 - fx) * zoom > 1080
    assert stick_table.TABLE_X[0] < data.BEDDING_TO < stick_table.TABLE_X[1]

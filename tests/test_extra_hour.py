"""Extra Hour as data: the lines as decided, the real hold, framing that keeps faces and marks, and the length arm."""

import sys
from pathlib import Path

import pytest

from srstudio import scripting, show, stick_reel, stick_table

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import extra_hour_audio

        return extra_hour_audio
    finally:
        sys.path.pop(0)


LINES = [
    ("noor", "Dishes?"),
    ("dev", "Extra hour."),
    ("noor", "The car?"),
    ("dev", "Extra hour."),
    ("noor", "Your mother?"),
    ("dev", "Extra hour. Clocks went back, babe."),
    ("noor", "You slept till noon."),
    ("dev", "That was the extra hour."),
    ("noor", "You've spent that hour four times."),
    ("dev", "It's a big hour."),
]


def test_the_lines_are_the_punch_up_s(data):
    assert [(t.actor, t.text) for t in data.SCRIPT.takes] == LINES


def test_the_voices_are_the_batch_s_and_there_is_no_bed(data):
    assert {r: v.name for r, v in data.SCRIPT.voices.items()} == {"dev": "Will", "noor": "Jessica"}
    assert data.SCRIPT.bed is None


def test_the_first_line_comes_by_half_a_second(data):
    assert 0 < data.PLATE_DOWN < data.SCRIPT.still < 0.5


def test_the_overlay_never_repeats_a_line(data):
    assert data.HOOK == "ONE FREE HOUR"
    assert data.HOOK.lower() not in " ".join(t.text.lower() for t in data.SCRIPT.takes)


def test_the_hold_is_after_her_line_and_real(data):
    takes = data.SCRIPT.takes
    assert takes[8].hold == data.LOOK_HOLD == pytest.approx(1.4)
    assert data.LOOK_HOLD == pytest.approx(data.NOD_END + 0.1)
    assert max(t.hold for t in takes if t is not takes[8]) < 0.5


def test_the_reel_cuts_on_the_mug(data):
    assert data.SCRIPT.takes[-1].hold == data.CUT_HOLD <= 0.3


def test_the_estimate_is_inside_the_short_arm(data):
    takes = data.SCRIPT.takes
    speech = sum(scripting.line_seconds(t.text) for t in takes)
    total = data.SCRIPT.still + speech + sum(t.hold for t in takes)
    assert 12.0 <= total <= 18.0


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
    [("two", ("dev",)), ("dev", ("dev",)), ("noor", ("dev", "noor")), ("over", ("dev", "noor")), ("close", ("dev",))],
)
def test_each_shot_keeps_its_faces_and_both_marks(data, shot, heads):
    stick_reel.check_framing(
        data.CAMERAS[shot], faces=tuple(data.FACES[h] for h in heads), marks=tuple(data.MARKS.values())
    )


def land(data, shot, point):
    (fx, fy), zoom, (tx, ty) = data.CAMERAS[shot]
    return tx + (point[0] - fx) * zoom, ty + (point[1] - fy) * zoom


def head_on_set(data, pose):
    head = data.POSES[pose].head
    return data.RIGHT[0] - head[0], data.RIGHT[1] + head[1]


def test_noor_never_reaches_the_bug_standing_or_leaning(data):
    for shot in ("two", "noor", "over"):
        for pose in ("stands", "plate-up", "plate", "key", "flick-a", "flick-b"):
            x, y = land(data, shot, head_on_set(data, pose))
            assert x + 110 < show.BUG_BOX[0] or y - 110 > show.BUG_BOX[3]


def test_noor_clears_the_hook_card_while_it_is_up(data):
    card_foot = 530
    zoom = data.CAMERAS["two"][1]
    for pose in ("plate-up", "plate", "key"):
        assert land(data, "two", head_on_set(data, pose))[1] - (92 + 35) * zoom > card_foot  # the head and her bun


def test_the_things_stand_on_the_table_in_their_order(data):
    x0, x1 = stick_table.TABLE_X
    spots = (data.MARKS["cactus"][0], data.MUG_X, data.PHONE_X, data.PLATE_X, data.KEY_X)
    assert x0 < spots[0] < spots[1] < spots[2] < spots[3] < spots[4] < x1
    assert spots[3] - spots[2] >= 100 and spots[2] - spots[1] >= 80

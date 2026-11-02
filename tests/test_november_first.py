"""November First as data: the lines as decided, the real hold, framing that keeps faces and marks, the length arm."""

import sys
from pathlib import Path

import pytest

from srstudio import opener, scripting, show, stick_holiday, stick_reel

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import november_first_audio

        return november_first_audio
    finally:
        sys.path.pop(0)


LINES = [
    ("dev", "It's November 1st."),
    ("noor", "I know. We're late."),
    ("dev", "That was a Halloween pumpkin."),
    ("noor", "He asked to stay."),
    ("dev", "Speaker, play something normal."),
    ("speaker", "Adding Dev to the naughty list."),
    ("dev", "What about Thanksgiving?"),
    ("noor", "Who?"),
]


def test_the_lines_are_the_script_s(data):
    assert [(t.actor, t.text) for t in data.SCRIPT.takes] == LINES


def test_three_speak_in_the_batch_s_voices_and_there_is_no_bed(data):
    voices = {r: v.name for r, v in data.SCRIPT.voices.items()}
    assert voices == {"dev": "Will", "noor": "Jessica", "speaker": "Alice"}
    assert data.SCRIPT.bed is None


def test_the_first_line_comes_by_half_a_second(data):
    assert 0 < data.LIGHTS_ON < data.SCRIPT.still <= 0.5


def test_the_opening_line_never_repeats_a_spoken_line(data):
    assert data.OPENING_TEXT == "my partner on november 1st"
    assert data.OPENING_TEXT not in " ".join(t.text.lower() for t in data.SCRIPT.takes)


def test_the_first_line_is_paced_to_outlast_the_opening_line_s_reading_time(data):
    take = data.SCRIPT.takes[0]
    assert take.speed is not None and take.speed < 1
    spoken = data.SCRIPT.still + scripting.line_seconds(take.text) / take.speed
    assert spoken >= opener.seconds(data.OPENING_TEXT)


def test_the_hold_comes_before_the_last_word_and_is_the_longest(data):
    takes = data.SCRIPT.takes
    assert takes[6].hold == data.HOLD == pytest.approx(1.3)
    assert max(t.hold for t in takes if t is not takes[6]) < data.HOLD


def test_the_last_word_gets_a_beat_then_the_cut(data):
    assert data.SCRIPT.takes[-1].hold == data.CUT_HOLD <= 0.6


def test_the_estimate_is_inside_the_short_arm(data):
    takes = data.SCRIPT.takes
    speech = sum(scripting.line_seconds(t.text) for t in takes)
    total = data.SCRIPT.still + speech + sum(t.hold for t in takes)
    assert 12.0 <= total <= 18.0


def test_the_shots_it_names_are_declared(data):
    assert {t.shot for t in data.SCRIPT.takes} <= set(data.SHOTS)


def test_no_camera_runs_off_the_set(data):
    """The far plane only reaches past the frame by its blur: a camera looking further shows its painted edge."""
    for focus, zoom, at in data.CAMERAS.values():
        left = focus[0] - at[0] / zoom
        right = focus[0] + (1080 - at[0]) / zoom
        top = focus[1] - at[1] / zoom
        assert left >= -5 and right <= 1085
        assert top >= 0 and focus[1] + (1920 - at[1]) / zoom <= 1920


@pytest.mark.parametrize(
    ("shot", "heads"), [("wide", ("dev", "noor")), ("noor", ("noor",)), ("close", ("noor",)), ("dev", ("dev",))]
)
def test_each_figure_shot_keeps_its_faces(data, shot, heads):
    stick_reel.check_framing(data.CAMERAS[shot], faces=tuple(data.FACES[h] for h in heads))


@pytest.mark.parametrize("shot", ["wide", "dev", "pumpkin", "speaker"])
def test_the_worktop_shots_keep_both_marks(data, shot):
    stick_reel.check_framing(data.CAMERAS[shot], marks=tuple(data.MARKS.values()))


def land(data, shot, point):
    (fx, fy), zoom, (tx, ty) = data.CAMERAS[shot]
    return tx + (point[0] - fx) * zoom, ty + (point[1] - fy) * zoom


@pytest.mark.parametrize("shot", ["wide", "noor", "close", "dev"])
def test_no_head_reaches_the_bug(data, shot):
    for point in data.FACES.values():
        x, y = land(data, shot, point)
        radius = 95 * data.CAMERAS[shot][1]
        off = 30 + radius  # and a margin
        off_frame = x - radius > 1080 or x + radius < 0
        assert off_frame or x + off < show.BUG_BOX[0] or y - off > show.BUG_BOX[3] or y + off < show.BUG_BOX[1]


def test_the_heads_stay_under_the_opening_line(data):
    foot = data.OPENER_TOP + 84
    for point in data.FACES.values():
        assert land(data, "wide", point)[1] - 130 > foot


def test_the_bells_stop_before_his_next_line(data):
    hits = data.jingles(7.0, 8.7)
    assert hits[0] == 7.0
    assert hits[-1] + data.JINGLE <= 8.7
    assert data.jingles(7.0, 7.1) == []


def test_the_star_is_in_her_hand_above_the_tree_s_top(data):
    tip = stick_holiday.tree_top(data.TREE_X, data.TREE_FOOT, scale=data.TREE_SCALE)
    hand = data.STAR_HAND
    assert hand[0] == pytest.approx(tip[0], abs=60)
    assert hand[1] == pytest.approx(tip[1], abs=70)

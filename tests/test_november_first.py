"""November First as data: the lines as decided, the real hold, framing that keeps faces and marks, the length arm, the
speaker's answer as a chip on screen and the opening line above every caption."""

import sys
from pathlib import Path

import pytest

from srstudio import opener, scripting, show, stick, stick_holiday, stick_reel

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
    ("dev", "What about Thanksgiving?"),
    ("noor", "Who?"),
]


def test_the_lines_are_the_script_s(data):
    assert [(t.actor, t.text) for t in data.SCRIPT.takes] == LINES


def test_two_speak_in_the_batch_s_voices_and_there_is_no_bed(data):
    voices = {r: v.name for r, v in data.SCRIPT.voices.items()}
    assert voices == {"dev": "Will", "noor": "Jessica"}
    assert data.SCRIPT.bed is None


def test_the_speaker_never_speaks(data):
    """Canon rule systems-answer-in-notifications: a system answers by a notice or a chip, never in a voice."""
    assert {t.actor for t in data.SCRIPT.takes} == {"dev", "noor"}


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


def test_the_hold_comes_before_the_last_word_and_is_the_longest_silence(data):
    """The one longer beat is the speaker's answer, and it is not silent: the chime, the chip and the sleigh bells."""
    takes = data.SCRIPT.takes
    asked, thanksgiving = takes[4], takes[5]
    assert thanksgiving.text == "What about Thanksgiving?"
    assert thanksgiving.hold == data.HOLD == pytest.approx(1.3)
    assert asked.hold == data.BEAT
    assert max(t.hold for t in takes if t not in (asked, thanksgiving)) < data.HOLD


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


def test_the_chip_holds_long_enough_to_read_muted_inside_the_speaker_s_beat(data):
    words = " ".join(data.CHIP_TEXT)
    assert data.CHIP_SECONDS >= max(0.84, opener.seconds(words))
    assert 0 < data.CHIP_AT < data.NAMED_AT < data.CHIP_AT + data.CHIP_SECONDS < data.BEAT
    spoken = " ".join(t.text.lower() for t in data.SCRIPT.takes)
    assert all(line.lower() not in spoken for line in data.CHIP_TEXT)


def test_the_chip_is_in_the_safe_area_clear_of_the_bug_and_the_captions(data):
    left, top, right, bottom = data.CHIP_BOX
    safe = opener.SAFE
    assert safe.x0 <= left < right <= safe.x1 and safe.y0 <= top < bottom <= safe.y1
    bug = show.BUG_BOX
    assert right < bug[0] or top > bug[3] or bottom < bug[1]
    assert bottom < stick_reel.WORDS_Y


@pytest.mark.parametrize("shot", ["speaker", "dev"])
def test_the_chip_covers_no_face_mark_or_speaker_on_the_shots_it_shows_over(data, shot):
    left, top, right, bottom = data.CHIP_BOX
    for point in data.MARKS.values():
        assert land(data, shot, point)[1] > bottom + 40
    if shot == "dev":
        x, y = land(data, shot, data.FACES["dev"])
        assert y - stick_reel.HEAD_RADIUS * data.CAMERAS[shot][1] > bottom + 20
    else:
        speaker_top = data.TOP + 2.0 - 146 * data.SPEAKER_SCALE  # the lit ring's top
        assert land(data, shot, (data.SPEAKER_X, speaker_top))[1] > bottom + 40


def test_the_opening_line_sits_above_the_first_caption(data):
    width = opener.PAD + 600  # wider than the line will be: the pill's top and height do not depend on its width
    left, top, right, bottom = opener.box(width, data.OPENER_TOP)
    assert opener.SAFE.y0 <= top and bottom < stick_reel.WORDS_Y
    assert bottom + 2 * stick.WORD_STROKE < stick_reel.WORDS_Y
    assert top > show.BUG_BOX[3] or right < show.BUG_BOX[0]


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


def test_nothing_of_dev_shows_at_the_left_edge_on_the_first_frame(data):
    """His mug's handle reaches 54 px right of the mug's middle: at the first frame it is all off the frame."""
    mug_x = 432.0 + (data.DEV_FROM - data.DEV_X)
    assert mug_x + 54 + 10 < 0


def test_the_close_shot_leaves_the_worktop_s_end_off_the_frame(data):
    """No cut-off corner of the worktop or the speaker at the frame's edge under the last word."""
    assert land(data, "close", (data.WORKTOP_X[1] + 3, data.TOP))[0] < -5

"""Can't Afford to Save as data: the lines as decided, the two real holds, the cut, framing, and the length arm."""

import sys
from pathlib import Path

import pytest

from srstudio import releases, scripting, show, stick_reel

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import cant_afford_to_save_audio

        return cant_afford_to_save_audio
    finally:
        sys.path.pop(0)


LINES = [
    ("noor", "Is that a second air fryer?"),
    ("dev", "Sixty percent off."),
    ("noor", "We have an air fryer."),
    ("dev", "Not at sixty percent off."),
    ("dev", "We saved $4,000."),
    ("noor", "Did you check the account?"),
    ("dev", "We can't afford to save any more."),
]


def test_the_lines_are_the_script_s(data):
    assert [(t.actor, t.text) for t in data.SCRIPT.takes] == LINES


def test_the_voices_are_the_batch_s_and_there_is_no_bed(data):
    assert {r: v.name for r, v in data.SCRIPT.voices.items()} == {"dev": "Will", "noor": "Jessica"}
    assert data.SCRIPT.bed is None


def test_the_box_lands_and_the_first_line_comes_by_half_a_second(data):
    assert 0 < data.BOX_LANDS < data.SCRIPT.still < 0.5


def test_the_overlay_never_repeats_a_line(data):
    assert data.HOOK == "BLACK FRIDAY WEEK"
    assert data.HOOK.lower() not in " ".join(t.text.lower() for t in data.SCRIPT.takes)


def test_the_holds_are_the_script_s_and_everything_lands_inside_them(data):
    takes = data.SCRIPT.takes
    assert takes[3].hold == data.CUE_TAIL + data.BOXES_HOLD
    assert takes[5].hold == data.CUE_TAIL + data.PHONE_HOLD
    assert (data.BOXES_HOLD, data.PHONE_HOLD) == pytest.approx((0.9, 1.4))
    assert max(t.hold for t in takes if t not in (takes[3], takes[5])) < 0.5
    assert data.SECOND_SLIDES < data.SECOND_LANDS < data.THIRD_DROPS < data.THIRD_LANDS < data.BOXES_HOLD
    assert data.PHONE_UP < data.SINKS < data.HEEL_SLIDES < data.HEEL_TAPS < data.PHONE_HOLD


def test_the_cut_to_the_hold_waits_for_the_cue_of_the_line(data):
    """A word stays up to WORD_LINGER after it is spoken: the hold starts when it has gone, on the speaker till then."""
    assert data.CUE_TAIL >= stick_reel.WORD_LINGER


def test_the_reel_cuts_on_his_last_word(data):
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
    ("shot", "heads"), [("two", ("dev", "noor")), ("dev", ("dev",)), ("noor", ("noor",)), ("hold", ("dev", "noor"))]
)
def test_each_shot_keeps_its_faces_and_both_marks(data, shot, heads):
    stick_reel.check_framing(
        data.CAMERAS[shot], faces=tuple(data.FACES[h] for h in heads), marks=tuple(data.MARKS.values())
    )


def test_nothing_of_the_reel_sits_in_the_bug_box(data):
    left, top, right, bottom = show.BUG_BOX
    for shot in data.CAMERAS.values():
        (fx, fy), zoom, (tx, ty) = shot
        for face in data.FACES.values():
            x, y = tx + (face[0] - fx) * zoom, ty + (face[1] - fy) * zoom
            assert not (left - 110 < x < right + 110 and top - 110 < y < bottom + 110)


def test_the_release_is_the_send_test_s():
    posts = releases.load(EPISODES / "posts")
    release = posts["cant-afford-to-save"]
    assert release.tags.test == "sp-length" and release.tags.arm == "short"
    assert release.tags.also == (("sp-speakers", "a"),)
    assert release.tags.send_to == "your partner"
    assert release.tags.send_line == "We can't afford to save any more."
    assert release.post.title.endswith("?")
    assert len(release.post.hashtags) <= 5 and "#okayville" in release.post.hashtags

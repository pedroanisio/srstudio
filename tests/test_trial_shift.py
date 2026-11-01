"""Trial Shift as data: the lines as decided, the real holds, the voices, and the holdout's post."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "episodes"))

from srstudio.releases import load  # noqa: E402
from trial_shift_audio import BEHIND_HIM, CUE, ON_AVA, SCRIPT, THE_TAG, TURNS, VOICES, extra, schedule  # noqa: E402


class Timing:
    def __init__(self, phrases):
        self.phrases = phrases


SECONDS = [1.2, 2.0, 1.0, 0.5, 0.9, 0.8, 1.4, 0.7, 1.4, 0.7, 0.4, 1.6]


def phrases() -> list[dict]:
    starts = schedule(SECONDS, {}).lines
    return [{"start": at, "end": at + seconds} for at, seconds in zip(starts, SECONDS, strict=True)]


def test_the_lines_are_the_script_in_order():
    assert [(s.role, s.text) for s in SCRIPT] == [
        ("milo", "How long have you worked here?"),
        ("ava", "I don't. It's just a quick trial shift."),
        ("milo", "When did it start?"),
        ("ava", "April."),
        ("milo", "That's not so bad."),
        ("ava", "2019."),
        ("candidate", "They'll let us know Friday."),
        ("milo", "Which Friday?"),
        ("milo", "Has anyone ever been hired?"),
        ("ava", "Of course!"),
        ("milo", "Who?"),
        ("milo", "It's just a quick trial shift."),
    ]


def test_the_callback_is_avas_own_words_in_his_mouth():
    assert SCRIPT[-1].text in SCRIPT[1].text


def test_three_published_voices():
    assert {role: v.name for role, v in VOICES.items()} == {"milo": "Liam", "ava": "Jessica", "candidate": "Will"}


def test_the_first_word_comes_by_half_a_second():
    assert phrases()[0]["start"] <= 0.5


def test_every_line_starts_late_enough_for_the_last_cue_to_hold():
    starts = [p["start"] for p in phrases()]
    assert all(b - a >= CUE - 1e-9 for a, b in zip(starts, starts[1:], strict=False))


def test_the_holds_are_real_holds_with_no_speech():
    p = phrases()
    assert p[6]["start"] - p[5]["end"] >= BEHIND_HIM + THE_TAG
    assert p[8]["start"] - p[7]["end"] >= TURNS - 1e-9
    assert p[11]["start"] - p[10]["end"] >= ON_AVA + 1.5


def test_each_shot_of_the_hold_outlasts_a_text_layers_shortest_span():
    assert BEHIND_HIM >= 0.84 and THE_TAG >= 0.84


def test_the_cuts_rise_and_end_at_the_door():
    cuts = extra(Timing(phrases()))["camera_cuts"]
    times = [c["time"] for c in cuts]
    assert times == sorted(times) and len(set(times)) == len(times)
    assert [cuts[0]["angle"], cuts[-1]["angle"]] == ["open", "door"]


def test_the_tag_shot_comes_after_every_close_on_her_before_it():
    cuts = extra(Timing(phrases()))["camera_cuts"]
    angles = [c["angle"] for c in cuts]
    assert angles.index("tag") > angles.index("ava")


def test_the_holdout_has_no_recipient_no_send_line_and_no_length_arm():
    tags = _release().tags
    assert (tags.test, tags.arm) == ("sp-speakers", "b")
    assert not tags.also and not tags.send_to and not tags.send_line


def test_the_post_is_the_scripts_and_within_the_hashtag_cap():
    post = _release().post
    assert post.title == "Has anyone you know been hired after a trial shift?"
    assert len(post.hashtags) <= 5 and "#okayville" in post.hashtags


def test_both_scores_are_on_the_comedy_floor():
    comedy = _release().comedy
    assert (comedy.author, comedy.reviewer) == (17, 16)


def _release():
    return load(ROOT / "episodes" / "posts")["trial-shift"]

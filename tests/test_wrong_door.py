"""Wrong Door as data: the lines as decided, the door by three seconds, two real holds, and a holdout's post."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "episodes"))

from srstudio.releases import load  # noqa: E402
from wrong_door_audio import ALONE, CUE, DARK, SCRIPT, VOICES, extra, schedule  # noqa: E402

SECONDS = [1.6, 1.6, 1.3, 1.3, 1.2, 0.9, 1.7, 0.4, 2.3, 0.7]


class Timing:
    def __init__(self, phrases):
        self.phrases = phrases


def phrases() -> list[dict]:
    starts = schedule(SECONDS, {}).lines
    return [{"start": at, "end": at + seconds} for at, seconds in zip(starts, SECONDS, strict=True)]


def test_the_lines_are_the_script_in_order():
    assert [(s.role, s.text) for s in SCRIPT] == [
        ("bo", "Great interview, Pip. We'll call you."),
        ("pip", "Thank you, thank you, thank you."),
        ("pip", "Okay. That's a closet."),
        ("pip", "He's still out there."),
        ("pip", "I live here now."),
        ("pip", "Hi! Yes! Totally!"),
        ("bo", "Pip. You've been here since Monday."),
        ("pip", "Yes."),
        ("bo", "First in, last out. You got the job."),
        ("bo", "Other door."),
    ]


def test_two_published_voices():
    assert {role: v.name for role, v in VOICES.items()} == {"pip": "Will", "bo": "Eric"}


def test_the_first_line_comes_by_half_a_second_and_every_cue_can_hold_its_caption():
    starts = schedule(SECONDS, {}).lines
    assert starts[0] <= 0.5
    assert all(b - a >= CUE - 1e-9 for a, b in zip(starts, starts[1:], strict=False))


def test_his_hand_is_on_the_door_by_three_seconds_and_it_shuts_before_the_dark():
    beats = extra(Timing(phrases()))
    assert beats["opens_start"] <= 3.0
    assert beats["opens_start"] < beats["in_start"] < beats["shut_start"] < beats["dark_start"]


def test_the_two_held_brackets_are_real_holds():
    p = phrases()
    beats = extra(Timing(p))
    assert p[2]["start"] - beats["dark_start"] >= DARK - 1e-9 and beats["dark_start"] > p[1]["end"]
    assert p[9]["start"] - beats["alone_start"] >= ALONE - 1e-9 and beats["alone_start"] > p[8]["end"]
    assert beats["alone_start"] < beats["clatter_start"] < p[9]["start"]


def test_the_door_opens_on_wednesday_after_the_dark():
    p = phrases()
    beats = extra(Timing(p))
    assert p[4]["end"] < beats["wednesday_start"] < p[5]["start"]


def test_the_holdout_keeps_its_position_arm_and_names_no_recipient():
    release = load(ROOT / "episodes" / "posts")["wrong-door"]
    assert release.tags.test == "sp-speakers" and release.tags.arm == "a"
    assert (release.tags.territory, release.tags.emotion) == ("job-hunting", "embarrassment")
    assert release.tags.send_to == "" and release.tags.send_line == ""
    assert release.comedy.lower == 17
    assert release.post.hashtags[-1] == "#okayville" and len(release.post.hashtags) <= 5
    assert "send" not in " ".join(s.text.lower() for s in SCRIPT)

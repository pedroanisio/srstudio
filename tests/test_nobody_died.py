"""Nobody Died as data: the lines as decided, three real holds, the voices, and the post."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "episodes"))

from nobody_died_audio import BULB, CUE, PEEK, SCRIPT, TURNS, VOICES, extra, schedule  # noqa: E402
from srstudio.releases import load  # noqa: E402


class Timing:
    def __init__(self, phrases):
        self.phrases = phrases


SECONDS = [1.5, 1.2, 1.5, 1.2, 1.2, 1.0, 1.3, 0.7, 1.8, 1.2, 1.3, 2.0]


def phrases() -> list[dict]:
    starts = schedule(SECONDS, {}).lines
    return [{"start": at, "end": at + seconds} for at, seconds in zip(starts, SECONDS, strict=True)]


def test_the_lines_are_the_script_in_order():
    assert [(s.role, s.text) for s in SCRIPT] == [
        ("manager", "So, tell me about yourself."),
        ("milo", "I'm a hard worker."),
        ("manager", "Do you need to get that?"),
        ("milo", "It's just my mom."),
        ("manager", "And why this company?"),
        ("milo", "I've always admired..."),
        ("milo", "She wrote 'don't worry.'"),
        ("manager", "That's nice."),
        ("milo", "Nobody writes that if it's fine."),
        ("manager", "Take it. Family first."),
        ("milo", "Mom? What happened? Who died?"),
        ("rosa", "Nobody died. Do you want a lamp?"),
    ]


def test_the_manager_is_always_heard_down_the_laptop_and_nobody_else_is():
    assert all(s.phone == (s.role == "manager") for s in SCRIPT)


def test_three_published_voices():
    assert {role: v.name for role, v in VOICES.items()} == {"rosa": "Lily", "milo": "Liam", "manager": "Eric"}


def test_the_first_word_comes_by_half_a_second():
    assert phrases()[0]["start"] <= 0.5


def test_every_line_starts_late_enough_for_the_last_cue_to_hold():
    starts = [p["start"] for p in phrases()]
    assert all(b - a >= CUE - 1e-9 for a, b in zip(starts, starts[1:], strict=False))


def test_the_three_brackets_are_real_holds_with_no_speech():
    p = phrases()
    assert p[6]["start"] - p[5]["end"] >= PEEK - 1e-9
    assert p[9]["start"] - p[8]["end"] >= TURNS - 1e-9
    assert p[11]["start"] - p[10]["end"] >= BULB - 1e-9


def test_rosa_arrives_after_who_died_and_never_before():
    p = phrases()
    cuts = extra(Timing(p))["camera_cuts"]
    assert [c["angle"] for c in cuts].count("rosa") == 1
    assert cuts[-1]["angle"] == "rosa" and cuts[-1]["time"] > p[10]["end"]


def test_the_phone_gets_its_two_inserts_in_the_holds():
    p = phrases()
    cuts = {c["angle"]: c["time"] for c in extra(Timing(p))["camera_cuts"]}
    assert p[5]["end"] < cuts["phone"] < p[6]["start"]
    assert p[8]["end"] < cuts["turns"] < p[9]["start"]


def test_the_release_sits_in_both_tests_and_tells_nobody_to_send_it():
    release = load(ROOT / "episodes" / "posts")["nobody-died"]
    assert release.tags.test == "sp-length" and release.tags.arm == "natural"
    assert release.tags.also == (("sp-speakers", "b"),)
    assert release.tags.send_to == "your mom"
    assert release.post.title == 'Why does "don\'t worry" make it worse?'
    words = " ".join(s.text for s in SCRIPT).lower()
    assert not any(word in words.split() for word in ("send", "tag", "share", "comment"))

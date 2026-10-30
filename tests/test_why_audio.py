"""Why, spoken: the same word five times, the first second silent, and a hold before the pat."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import why_audio
    finally:
        sys.path.pop(0)
    return why_audio


def test_the_child_and_the_parent_have_different_premade_voices(audio):
    voices = audio.INTERVIEW.voices
    assert {line.role for line in audio.SCRIPT} == set(voices) == {"pip", "bo"}
    assert len({voice.id for voice in voices.values()}) == 2


def test_the_first_second_is_silent_for_the_held_frame(audio):
    plan = audio.schedule([1.0] * len(audio.SCRIPT), {})
    assert plan.lines[0] == audio.HELD == 1.0


def test_pip_asks_why_four_times_and_bo_asks_it_last(audio):
    whys = [line.role for line in audio.SCRIPT if line.text == audio.WHY]
    assert whys == ["pip", "pip", "pip", "pip", "bo"]
    assert audio.SCRIPT[-1].role == "bo" and audio.SCRIPT[-1].caption == "...Why?"


def test_the_longest_silences_are_the_floor_and_the_hold_before_the_pat(audio):
    plan = audio.schedule([1.0] * len(audio.SCRIPT), {})
    gaps = [after - before - 1.0 for before, after in zip(plan.lines, plan.lines[1:], strict=False)]
    assert sorted(gaps)[-2:] == pytest.approx(sorted([audio.BLANK, audio.HOLD + audio.PAT]))


def test_no_line_writes_a_number(audio):
    assert not any(ch.isdigit() for line in audio.SCRIPT for ch in line.text)  # speech-to-text writes numbers

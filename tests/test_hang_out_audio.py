"""Hang Out, spoken: the line wears down over the decades, the voices slow, and the bench waits for the last words."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import hang_out_audio
    finally:
        sys.path.pop(0)
    return hang_out_audio


def test_the_two_friends_have_different_premade_voices(audio):
    voices = audio.INTERVIEW.voices
    assert {line.role for line in audio.SCRIPT} == set(voices) == {"juno", "pip"}
    assert len({voice.id for voice in voices.values()}) == 2


def test_the_excuse_wears_down_and_the_voices_slow_with_it(audio):
    crazy = [line.text for line in audio.SCRIPT if "razy" in line.text]
    assert [len(text) for text in crazy] == sorted((len(text) for text in crazy), reverse=True)
    speeds = [line.speed for line in audio.SCRIPT]
    assert speeds[0] > 1.0 and max(speeds[-3:]) < 1.0


def test_the_phones_come_out_in_a_silence_after_more_often(audio):
    plan = audio.schedule([1.0] * len(audio.SCRIPT), {})
    gaps = [after - before - 1.0 for before, after in zip(plan.lines, plan.lines[1:], strict=False)]
    assert plan.lines == sorted(plan.lines)
    assert gaps[-1] == pytest.approx(audio.OUT) and gaps[-1] == max(gaps)
    assert gaps[0] < 0.2 and gaps[1] < 0.2  # the opening exchange is tight

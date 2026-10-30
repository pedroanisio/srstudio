"""Early Night, spoken: the narrator holds the first and last word, each hour reads before its line, the dark waits."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import early_night_audio
    finally:
        sys.path.pop(0)
    return early_night_audio


def test_the_narrator_and_juno_have_different_premade_voices(audio):
    voices = audio.INTERVIEW.voices
    assert {line.role for line in audio.SCRIPT} == set(voices) == {"narrator", "juno"}
    assert len({voice.id for voice in voices.values()}) == 2
    assert [line.role for line in audio.SCRIPT].count("juno") == 1  # she has one line, to nobody


def test_the_key_line_opens_and_no_line_writes_a_number(audio):
    assert audio.SCRIPT[0].caption == "Tonight: bed by ten."
    assert not any(ch.isdigit() for line in audio.SCRIPT for ch in line.text)  # speech-to-text writes numbers


def test_her_comment_gets_a_silence_before_she_speaks(audio):
    plan = audio.schedule([1.0] * len(audio.SCRIPT), {})
    gaps = [after - before - 1.0 for before, after in zip(plan.lines, plan.lines[1:], strict=False)]
    assert plan.lines == sorted(plan.lines)
    assert gaps[3] == pytest.approx(audio.COMMENT + audio.CUT_LEAD) and gaps[3] == max(gaps)


def test_the_alarm_rings_after_a_dark_hold_and_the_reel_stops_soon_after(audio):
    assert audio.INTERVIEW.reaction_after > 1.0
    assert audio.INTERVIEW.reaction_hold < 1.5 and audio.INTERVIEW.end_card == 0

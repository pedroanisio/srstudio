"""Unread as data: the lines in order, the two holds the script brackets, and the rule that comes back reversed."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import unread_audio

        return unread_audio
    finally:
        sys.path.pop(0)


def test_the_rule_opens_his_mouth_and_comes_back_reversed(audio):
    lines = [s.text for s in audio.SCRIPT]
    assert lines[1] == "If it's important, they'll call."
    assert lines[-1] == "If it's important, they'll email."
    assert {s.role for s in audio.SCRIPT} == {"juno", "pip"}


def test_the_first_line_lands_by_half_a_second(audio):
    assert audio.schedule([1.0] * len(audio.SCRIPT), {}).lines[0] <= 0.5


def test_both_held_brackets_stay_silent_for_their_length(audio):
    lengths = [1.0] * len(audio.SCRIPT)
    starts = audio.schedule(lengths, {}).lines
    assert starts[4] - (starts[3] + 1.0) == pytest.approx(audio.HOLD)  # her thumb stops
    assert starts[7] - (starts[6] + 1.0) >= 1.3 - 1e-9  # it rings


def test_every_caption_holds_its_cue_on_a_quick_take(audio):
    starts = audio.schedule([0.3] * len(audio.SCRIPT), {}).lines
    assert all(b - a >= 0.92 - 1e-9 for a, b in zip(starts, starts[1:], strict=False))


def test_his_caption_is_down_before_the_list_cuts_in_and_the_list_still_reads(audio):
    assert audio.CAPTION_TAIL >= 0.3
    phrases = [{"start": 0.0, "end": 1.0}] * 3 + [{"start": 6.0, "end": 7.5}] + [{"start": 9.0, "end": 10.0}] * 3
    timing = SimpleNamespace(phrases=phrases)
    assert audio.extra(timing)["stop_start"] == pytest.approx(7.5 + audio.CAPTION_TAIL)
    shown = audio.HOLD - audio.CAPTION_TAIL - audio.LOOK_UP
    assert shown >= 0.92 - 1e-9  # the row is read, and the check's floor is 0.84 s

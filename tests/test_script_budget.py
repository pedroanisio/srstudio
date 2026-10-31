"""A script's words against the length of the reel, read before a take is paid for."""

from __future__ import annotations

import pytest

from srstudio import scripting
from srstudio.sketch import Line


def lines(*counts: int) -> tuple[Line, ...]:
    return tuple(Line("vera", " ".join(["word"] * n)) for n in counts)


def test_a_reader_counts_a_hyphenated_word_once():
    assert scripting.word_count((Line("gus", "Then a lie-down?"), Line("vera", "Co-host in tears."))) == 6


def test_thirty_seconds_hold_seventy_words():
    assert scripting.word_budget(30.0) == 70


@pytest.mark.parametrize(("words", "over"), [(70, 0), (71, 1), (101, 31), (0, 0)])
def test_the_excess_is_what_has_to_be_cut(words, over):
    assert scripting.over_budget(lines(words), 30.0) == over


def test_the_budget_follows_the_length_of_the_reel():
    assert scripting.over_budget(lines(60), 23.5) == 5
    assert scripting.over_budget(lines(60), 26.0) == 0

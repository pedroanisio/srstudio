"""Balanced word cues: with ``balance=True``, :func:`srstudio.stick.word_cues` splits each take's words where the
shortest cue lasts longest, within the width limit, instead of filling cues greedily from the left."""

from types import SimpleNamespace

import pytest

from srstudio import stick
from srstudio.stick import StickDataError


def take(start: float, end: float, words: list[tuple[str, float, float]]):
    return SimpleNamespace(start=start, end=end, words=[{"text": w, "start": a, "end": b} for w, a, b in words])


PLANE = take(
    10.0,
    11.777,
    [("The", 0.0, 0.11), ("plane", 0.14, 0.39), ("can't", 0.42, 0.63), ("leave", 0.69, 0.87),
     ("without", 0.9, 1.17), ("me.", 1.22, 1.48)],
)  # fmt: skip


def chars(text: str) -> float:
    return 40.0 * len(text)  # every character 40 px wide


def test_greedy_cues_leave_the_first_one_short():
    cues = stick.word_cues([PLANE], min_seconds=1.0, linger=0.9, width=chars, max_width=640, borrow=True, tail=True)
    assert min(c.end - c.start for c in cues) < 0.85


def test_balanced_cues_split_where_the_shortest_lasts_longest():
    cues = stick.word_cues([PLANE], min_seconds=1.0, linger=0.9, width=chars, max_width=880, balance=True)
    assert [c.text for c in cues] == ["The plane can't leave", "without me"]
    assert [(c.start, c.end) for c in cues] == [(10.0, 10.9), (10.9, 11.777)]


def test_a_take_that_fits_one_cue_stays_one_cue():
    cues = stick.word_cues([PLANE], min_seconds=1.0, linger=0.9, width=chars, max_width=2000, balance=True)
    assert [c.text for c in cues] == ["The plane can't leave without me"]


def test_a_word_wider_than_the_limit_still_gets_its_own_cue():
    long = take(0.0, 2.0, [("Supercalifragilistic", 0.0, 0.8), ("yes", 1.0, 1.3)])
    cues = stick.word_cues([long], min_seconds=1.0, linger=0.3, width=chars, max_width=200, balance=True)
    assert [c.text for c in cues] == ["Supercalifragilistic", "yes"]


def test_balance_needs_the_width_and_refuses_tail():
    with pytest.raises(StickDataError, match="width"):
        stick.word_cues([PLANE], min_seconds=1.0, balance=True)
    with pytest.raises(StickDataError, match="tail"):
        stick.word_cues([PLANE], min_seconds=1.0, width=chars, balance=True, tail=True)


def test_balance_off_is_the_greedy_default():
    a = stick.word_cues([PLANE], min_seconds=1.0, linger=0.9, width=chars, max_width=640, borrow=True)
    b = stick.word_cues([PLANE], min_seconds=1.0, linger=0.9, width=chars, max_width=640, borrow=True, balance=False)
    assert a == b

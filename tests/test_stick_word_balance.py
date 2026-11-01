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


TWO_SENTENCES = take(
    20.0,
    21.6,
    [("Bro.", 0.0, 0.2), ("Four", 0.3, 0.5), ("hours", 0.5, 0.8), ("of", 0.8, 0.9), ("cardio?", 0.9, 1.3)],
)  # fmt: skip


def test_balance_alone_runs_a_cue_across_a_sentence_end():
    cues = stick.word_cues([TWO_SENTENCES], min_seconds=0.5, linger=0.3, width=chars, max_width=640, balance=True)
    assert cues[0].text == "Bro Four hours"


def test_sentences_end_a_cue_at_every_sentence_end():
    cues = stick.word_cues(
        [TWO_SENTENCES], min_seconds=0.5, linger=0.3, width=chars, max_width=880, balance=True, sentences=True
    )
    assert [c.text for c in cues] == ["Bro", "Four hours of cardio"]


@pytest.mark.parametrize("end", ["Now!", "Now?", "Now...", "Now.\"", "Now!”", "Now…"])  # fmt: skip
def test_a_sentence_ends_at_each_of_its_marks_and_past_a_closing_quote(end):
    words = take(0.0, 2.0, [(end, 0.0, 0.4), ("Then", 0.5, 0.8), ("go", 0.8, 1.1)])
    cues = stick.word_cues([words], width=chars, max_width=2000, balance=True, sentences=True)
    assert [c.text for c in cues] == ["Now", "Then go"]


def test_a_comma_does_not_end_a_sentence():
    words = take(0.0, 2.0, [("Now,", 0.0, 0.4), ("then", 0.5, 0.8), ("go", 0.8, 1.1)])
    cues = stick.word_cues([words], width=chars, max_width=2000, balance=True, sentences=True)
    assert [c.text for c in cues] == ["Now then go"]


def test_a_take_with_no_sentence_end_splits_as_it_did():
    plain = dict(min_seconds=1.0, linger=0.9, width=chars, max_width=880, balance=True)
    no_stop = take(10.0, 11.777, [(w["text"].rstrip("."), w["start"], w["end"]) for w in PLANE.words])
    assert stick.word_cues([no_stop], sentences=True, **plain) == stick.word_cues([no_stop], **plain)


def test_sentences_need_balance():
    with pytest.raises(StickDataError, match="sentences"):
        stick.word_cues([TWO_SENTENCES], sentences=True)


def test_a_balanced_split_can_refuse_to_end_a_sentence_on_a_lone_word():
    spoken = "I was up at three with him".split()
    late = take(0.0, 3.0, [(w, 0.2 * i, 0.2 * i + 0.1) for i, w in enumerate(spoken[:-1])] + [("him", 1.25, 1.4)])
    kept = stick.word_cues([late], min_seconds=0.85, linger=0.9, width=chars, max_width=880, balance=True)
    assert [c.text for c in kept] == ["I was up at three with", "him"]
    joined = stick.word_cues(
        [late], min_seconds=0.85, linger=0.9, width=chars, max_width=880, balance=True, alone=False
    )
    assert [c.text for c in joined] == ["I was up at three", "with him"]


def test_sentences_and_a_refused_lone_word_hold_together():
    spoken = [("Bro.", 0.0, 0.2), ("I", 0.3, 0.4), ("was", 0.4, 0.5), ("up", 0.5, 0.6), ("late", 1.2, 1.4)]
    cues = stick.word_cues(
        [take(0.0, 2.0, spoken)],
        min_seconds=0.5,
        linger=0.3,
        width=chars,
        max_width=880,
        balance=True,
        alone=False,
        sentences=True,
    )
    assert [c.text for c in cues] == ["Bro", "I was up late"]


TWO_QUICK = take(0.0, 1.6, [("Love", 0.0, 0.2), ("it.", 0.2, 0.5), ("Evenings?", 0.8, 1.4)])
THREE_QUICK = take(
    0.0,
    2.3,
    [
        ("I", 0.0, 0.1),
        ("got", 0.1, 0.2),
        ("you.", 0.2, 0.5),
        ("Breathe.", 1.0, 1.3),
        ("Open", 1.55, 1.8),
        ("it.", 1.8, 2.0),
    ],
)
JOINING = dict(min_seconds=0.875, linger=0.3, width=chars, max_width=880, borrow=True, balance=True, sentences=True)


def test_a_cue_too_short_to_read_joins_its_neighbour_and_keeps_the_marks_of_both_sentences():
    cues = stick.word_cues([TWO_QUICK], join=True, **JOINING)
    assert [c.text for c in cues] == ["Love it. Evenings?"]
    assert (cues[0].start, cues[0].end) == (0.0, 1.6)


def test_only_the_cues_that_are_still_short_join():
    cues = stick.word_cues([THREE_QUICK], join=True, **JOINING)
    assert [c.text for c in cues] == ["I got you", "Breathe. Open it."]
    assert all(c.end - c.start >= 0.875 for c in cues)


def test_a_cue_too_wide_to_join_stays_short():
    cues = stick.word_cues([TWO_QUICK], join=True, **{**JOINING, "max_width": 400})
    assert [c.text for c in cues] == ["Love it", "Evenings"]


def test_without_join_the_cues_stay_as_they_were():
    assert [c.text for c in stick.word_cues([TWO_QUICK], **JOINING)] == ["Love it", "Evenings"]


def test_join_needs_a_shortest_time():
    with pytest.raises(StickDataError, match="join"):
        stick.word_cues([TWO_QUICK], width=chars, balance=True, join=True)


CALLED = take(0.0, 1.9, [("Hey.", 0.0, 0.3), ("Over", 0.6, 0.8), ("here.", 0.8, 1.2), ("Hey!", 1.4, 1.7)])
NEXT_LINE = take(4.0, 5.0, [("Stretching.", 0.0, 0.8)])


def called(**extra):
    return stick.word_cues([CALLED, NEXT_LINE], min_seconds=0.85, linger=0.2, width=chars, max_width=880, balance=True,
                           sentences=True, **extra)  # fmt: skip


def test_a_sentence_end_can_leave_a_cue_too_short_to_read():
    assert min(c.end - c.start for c in called()) < 0.85


def test_hold_keeps_every_cue_up_long_enough_by_running_into_the_silence():
    cues = called(hold=True)
    assert [c.text for c in cues] == ["Hey", "Over here", "Hey", "Stretching"]
    assert min(c.end - c.start for c in cues) >= 0.85 - 1e-9
    assert all(a.end <= b.start for a, b in zip(cues, cues[1:], strict=False))


def test_hold_leaves_the_cue_after_a_long_enough_silence_where_it_was_spoken():
    assert called(hold=True)[-1].start == 4.0


def test_hold_moves_nothing_when_every_cue_is_long_enough():
    plain = take(0.0, 3.0, [("One.", 0.0, 1.0), ("Two.", 1.0, 2.0)])
    args = dict(min_seconds=0.5, linger=0.3, width=chars, max_width=880, balance=True, sentences=True)
    assert stick.word_cues([plain], hold=True, **args) == stick.word_cues([plain], **args)


def test_hold_needs_the_length_it_holds_to():
    with pytest.raises(StickDataError, match="min_seconds"):
        stick.word_cues([PLANE], hold=True)

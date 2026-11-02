"""Where a caption may break (ADR 0173): not after a weak word, inside a number or inside a name, while another
break fits; a sentence end always frees the break, so rule 7's cut is always allowed."""

from __future__ import annotations

import pytest

from srstudio import breaks


def places(text: str, **kw: bool) -> set[int]:
    return set(breaks.kept_together(text.split(), **kw))


def test_no_break_after_a_weak_word():
    assert places("I need the report by Friday") == {1, 3, 5}  # after I, the, by
    assert "the weak word 'the'" in breaks.forbidden("read the report".split())[2]


def test_a_stop_frees_the_break_after_any_word():
    assert places("He said no. The end") == {1, 4}  # after He and The; "no." ends a sentence
    assert places("Wait; and then") == {2}
    assert places("so…   and") == set()


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ("twenty thousand people", {1}),
        ("75 per cent off", {1, 2}),
        ("one in ten people", {1, 2}),
        ("three times in ten", {1, 2, 3}),
        ("ninety-five percent", {1}),
        ("$20 million", {1}),
        ("at 10:30 sharp", {1}),
    ],
)
def test_no_break_inside_a_number(text, kept):
    assert places(text) == kept


def test_numbers_apart_are_not_one_number():
    assert places("buy 3. 4 left") == set()
    assert places("3 dogs 4 cats") == set()


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ("we flew to New York today", {1, 3, 4}),  # after we, to; inside New York
        ("on Apollo 12 we flew", {1, 2, 4}),  # after on; Apollo 12; after we
        ("Then Newton fell", set()),  # Then only opens the sentence
        ("Apollo 12 launched", {1}),  # a digit makes a name even at the start
        ("Hi, Sam", set()),  # a comma closes the first word
        ("I Love it", {1}),  # after I, which is weak, not a name
    ],
)
def test_no_break_inside_a_name(text, kept):
    assert places(text) == kept


def test_a_word_after_a_sentence_end_opens_a_sentence():
    assert places("I left. Then Newton fell") == {1}
    assert places("Then Newton fell", opens=False) == {1}


def test_text_in_capitals_has_no_names():
    assert places("WE FLEW TO NEW YORK") == {1, 3}


def test_is_number():
    for yes in ("1982", "3.8", "95%", "12-km", "twenty", "ninety-five", "half", "$20,", "10:30"):
        assert breaks.is_number(yes), yes
    for no in ("ten-ish", "often", "", "-", "won"):
        assert not breaks.is_number(no), no


def chars(most: int):
    return lambda line: len(line) <= most


def test_lay_out_moves_a_break_off_a_weak_word_when_another_layout_fits():
    words = "and open a candle shop today".split()
    assert breaks.lay_out(words, chars(12), 3) == ["and open", "a candle", "shop today"]


def test_lay_out_takes_a_forbidden_break_only_when_nothing_else_fits():
    assert breaks.lay_out("the the the".split(), chars(3), 3) == ["the", "the", "the"]


def test_lay_out_returns_none_when_no_layout_fits():
    assert breaks.lay_out("a word much too long".split(), chars(3), 5) is None
    assert breaks.lay_out("one two three".split(), chars(5), 2) is None
    assert breaks.lay_out([], chars(5), 2) is None


def test_lay_out_keeps_a_name_whole_when_it_fits_and_breaks_it_only_when_nothing_else_does():
    words = "we flew to New York".split()
    assert breaks.lay_out(words, chars(13), 2) == ["we flew", "to New York"]
    assert breaks.lay_out(words, chars(10), 2) == ["we flew to", "New York"]  # the only layout that fits two lines

"""Every number a real reel states has to appear in its sources, whichever way either of them writes it."""

from __future__ import annotations

import pytest

from srstudio import facts


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("fifteen degrees", 15.0),
        ("Seventeen hundred square feet", 1700.0),
        ("1,700 square feet", 1700.0),
        ("twenty-five days", 25.0),
        ("993 million orders", 993.0),
        ("nine hundred and two", 900.0),
        ("UP TO 15° OFF", 15.0),
        ("1,045 birds", 1045.0),
        ("0.5 s", 0.5),
        ("two thousand", 2000.0),
        ("finish ninth", 9.0),
        ("NEEDED: 9TH.", 9.0),
        ("he came 3rd", 3.0),
        ("the 21st", 21.0),
        ("twenty-third", 23.0),
        ("twentieth", 20.0),
    ],
)
def test_a_number_is_found_written_either_way(text, value):
    assert value in facts.numbers_in(text)


@pytest.mark.parametrize("text", ["a 3D-printed habitat", "at 3:01", "the first year", "no number here"])
def test_a_word_or_a_clock_is_not_a_number(text):
    assert facts.numbers_in(text) == set()


def test_an_ordinal_is_its_own_value_not_the_tens_before_it():
    assert facts.numbers_in("the twenty-third") == {23.0}


@pytest.mark.parametrize("text", ["the second half", "wait a second", "at first", "4the win", "12throw"])
def test_a_word_that_only_looks_ordinal_is_not_a_number(text):
    assert facts.numbers_in(text) == set()


def test_a_place_on_screen_is_checked_against_the_place_in_the_sources():
    sources = "He needed ninth and finished third."
    assert facts.unsourced(("NEEDED: 9TH. FINISHED: 3RD.",), sources) == []
    assert facts.unsourced(("He came fourth.", "FINISHED: 4TH."), sources) == [
        "4 in 'He came fourth.'",
        "4 in 'FINISHED: 4TH.'",
    ]


def test_a_number_in_the_sources_is_found_either_way_round():
    sources = "about 20 minutes, four TPUs, a 1,700-square-foot habitat"
    assert facts.unsourced(("twenty minutes", "4 chips", "Seventeen hundred square feet"), sources) == []


def test_a_number_nobody_sourced_is_named_with_its_line():
    assert facts.unsourced(("up to fifteen degrees", "a fine day"), "as much as 7 degrees") == [
        "15 in 'up to fifteen degrees'"
    ]

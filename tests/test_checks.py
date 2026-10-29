"""The input checks every style shares (srstudio.checks): a number, an end, a second, spans and rising seconds,
each raising the caller's error with the caller's message."""

from __future__ import annotations

import math

import pytest

from srstudio import checks


class StyleError(ValueError):
    pass


NOT_NUMBERS = [True, False, math.nan, math.inf, -math.inf, "1", None]


# -- numbers and ends -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("value", [0, 1, 2.5, -3])
def test_a_finite_int_or_float_is_a_number(value):
    assert checks.number(value)


@pytest.mark.parametrize("value", NOT_NUMBERS)
def test_a_bool_a_non_finite_value_or_a_non_number_is_not(value):
    assert not checks.number(value)


def test_a_positive_value_comes_back_as_a_float():
    assert checks.positive(3, StyleError, "x") == 3.0 and isinstance(checks.positive(3, StyleError, "x"), float)


@pytest.mark.parametrize("value", [0, -1, *NOT_NUMBERS])
def test_positive_refuses_zero_negatives_and_non_numbers_with_the_callers_error(value):
    with pytest.raises(StyleError, match="^a set is drawn for more than 0 s$"):
        checks.positive(value, StyleError, "a set is drawn for more than 0 s")


def test_non_negative_takes_zero():
    assert checks.non_negative(0, StyleError, "x") == 0.0


@pytest.mark.parametrize("value", [-0.01, *NOT_NUMBERS])
def test_non_negative_refuses_negatives_and_non_numbers(value):
    with pytest.raises(StyleError, match="end"):
        checks.non_negative(value, StyleError, "end")


# -- seconds ----------------------------------------------------------------------------------------------------------
def test_a_second_from_zero_has_no_upper_bound_without_an_end():
    assert checks.second(0, StyleError, "x") == 0.0
    assert checks.second(1e6, StyleError, "x") == 1e6


@pytest.mark.parametrize("t", [-1, *NOT_NUMBERS])
def test_a_second_refuses_negatives_bools_and_non_finite_values(t):
    with pytest.raises(StyleError, match="a time"):
        checks.second(t, StyleError, "a time")


def test_a_second_with_an_end_falls_before_it():
    assert checks.second(1.99, StyleError, "x", end=2.0) == 1.99
    with pytest.raises(StyleError, match="drop"):
        checks.second(2.0, StyleError, "drop", end=2.0)


# -- spans ------------------------------------------------------------------------------------------------------------
def bad(span) -> str:
    return f"bad {span[0]}..{span[1]}"


def test_spans_come_back_as_float_pairs():
    assert checks.spans([(0, 1), [1.5, 2]], StyleError, bad) == [(0.0, 1.0), (1.5, 2.0)]


@pytest.mark.parametrize("span", [(1, 1), (2, 1), (-0.5, 1), (True, 2), (0, math.inf), (math.nan, 1), ("0", 1)])
def test_a_span_rises_from_a_second_at_or_after_zero(span):
    with pytest.raises(StyleError, match="^bad "):
        checks.spans([span], StyleError, bad)


@pytest.mark.parametrize("span", [(1,), (0, 1, 2), 3, "ab"])
def test_a_span_is_a_pair(span):
    with pytest.raises(StyleError, match="pairs"):
        checks.spans([span], StyleError, bad, shape=lambda s: f"spans are pairs, got {s!r}")


def test_a_span_that_is_not_a_pair_has_a_default_message():
    with pytest.raises(StyleError, match=r"a span is a \(start, end\) pair, got \(1,\)"):
        checks.spans([(1,)], StyleError, bad)


def test_within_bounds_each_span_by_the_end():
    assert checks.spans([(0, 2.0000005)], StyleError, bad, within=2.0) == [(0.0, 2.0000005)]
    with pytest.raises(StyleError, match="bad 1..2.1"):
        checks.spans([(1, 2.1)], StyleError, bad, within=2.0)


def test_clamp_cuts_each_span_at_the_end_instead_of_refusing_it():
    assert checks.spans([(0, 1), (1, 9)], StyleError, bad, clamp=2.0) == [(0.0, 1.0), (1.0, 2.0)]


@pytest.mark.parametrize("span", [(5, 10), (2.0, 3.0)])
def test_clamp_refuses_a_span_that_starts_at_or_past_the_end_instead_of_inverting_it(span):
    with pytest.raises(StyleError, match=f"^bad {span[0]}..{span[1]}$"):
        checks.spans([(0, 1), span], StyleError, bad, clamp=2.0)


def test_ordered_spans_refuse_an_overlap_or_a_step_back():
    assert checks.spans([(0, 1), (1, 2)], StyleError, bad, ordered="in order") == [(0.0, 1.0), (1.0, 2.0)]
    for spans in ([(0, 1.5), (1, 2)], [(2, 3), (0, 1)]):
        with pytest.raises(StyleError, match="^in order$"):
            checks.spans(spans, StyleError, bad, ordered="in order")


def test_ordered_may_word_its_refusal_from_the_span():
    with pytest.raises(StyleError, match=r"^1\.0\.\.2 overlaps$"):
        checks.spans([(0, 1.5), (1.0, 2)], StyleError, bad, ordered=lambda s: f"{s[0]}..{s[1]} overlaps")


def test_unordered_spans_may_overlap():
    assert checks.spans([(2, 3), (0, 2.5)], StyleError, bad) == [(2.0, 3.0), (0.0, 2.5)]


# -- rising seconds ---------------------------------------------------------------------------------------------------
def late(i: int, t) -> str:
    return f"#{i} at {t}"


def test_rising_seconds_come_back_as_floats():
    assert checks.rising([0, 0.5, 1], StyleError, late, end=2) == [0.0, 0.5, 1.0]


@pytest.mark.parametrize(
    ("seconds", "match"),
    [
        ([0.5, 0.5], "#1 at 0.5"),
        ([1, 0.5], "#1 at 0.5"),
        ([0, 2], "#1 at 2"),
        ([-0.5], "#0 at -0.5"),
        ([True], "#0 at True"),
        ([math.nan], "#0 at nan"),
    ],
)
def test_rising_seconds_rise_strictly_from_zero_and_stay_before_the_end(seconds, match):
    with pytest.raises(StyleError, match=f"^{match}$"):
        checks.rising(seconds, StyleError, late, end=2)

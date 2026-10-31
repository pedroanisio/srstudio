"""The comedy floor (ADR 0064): a new comedy video carries two scores out of 20, and the lower must reach 14.

The scores are written by agents, so they are model output: they are parsed from text into :class:`Scores`, checked,
and refused with a reason. Nothing here decides what is funny; the delivery commands' own tests are in
``tests/test_social.py`` and ``tests/test_publish_pilots.py``."""

from pathlib import Path

import pytest

from srstudio import comedy_floor
from srstudio.comedy_floor import ComedyError, Scores, notes_shortfall, read, refuse, shortfall
from srstudio.social import DeliveryError

SKILL = Path(__file__).resolve().parent.parent / ".claude/skills/funny-reels/SKILL.md"


def notes(*lines: str, body: str = "# Notes\n") -> str:
    return "\n".join(("---", "pilot: real-roast", *lines, "---", "", body))


BOTH = ("comedy-author: 15", "comedy-reviewer: 14")


def test_the_floor_is_fourteen_of_twenty():
    assert (comedy_floor.FLOOR, comedy_floor.TOP) == (14, 20)


def test_the_skill_states_the_floor_the_gate_holds():
    assert f"{comedy_floor.FLOOR}/{comedy_floor.TOP}" in SKILL.read_text()


def test_two_scores_are_read_from_the_frontmatter():
    assert read(notes(*BOTH)) == Scores(author=15, reviewer=14)


def test_the_frontmatter_may_hold_anything_else_and_any_line_ending():
    text = notes("main-trigger: reversal", *BOTH, "date: 2026-10-31").replace("\n", "\r\n")
    assert read(text) == Scores(15, 14)


def test_a_value_may_carry_spaces_around_it():
    assert read(notes("comedy-author:   15  ", "comedy-reviewer:14")) == Scores(15, 14)


def test_the_lower_score_counts():
    assert Scores(20, 9).lower == 9
    assert Scores(9, 20).lower == 9


@pytest.mark.parametrize(
    "text, key",
    [
        ("", "frontmatter"),
        ("# Notes\n\ncomedy-author: 15\ncomedy-reviewer: 14\n", "frontmatter"),
        ("﻿" + notes(*BOTH), "frontmatter"),
        ("\n" + notes(*BOTH), "frontmatter"),
        ("---\ncomedy-author: 15\ncomedy-reviewer: 14\n", "frontmatter"),
        (notes(), "comedy-author"),
        (notes("comedy-reviewer: 14"), "comedy-author"),
        (notes("comedy-author: 15"), "comedy-reviewer"),
        (notes("comedy-author: 15", body="comedy-reviewer: 14\n"), "comedy-reviewer"),
        (notes("comedy-author: 15", "  comedy-reviewer: 14"), "comedy-reviewer"),
        (notes("comedy-author: 15", "Comedy-Reviewer: 14"), "comedy-reviewer"),
        (notes("comedy-author: 15", "# comedy-reviewer: 14"), "comedy-reviewer"),
    ],
)
def test_a_missing_score_is_refused(text, key):
    with pytest.raises(ComedyError, match=f"{key}.*"):
        read(text)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "~",
        "null",
        "true",
        "fourteen",
        "14/20",
        "14.0",
        "14.5",
        "1e1",
        "+14",
        "0x0E",
        "014",
        "'14'",
        '"14"',
        "[14]",
        "14 # generous",
        "14 15",
        "١٤",
        "１４",
        "9" * 5000,
    ],
)
@pytest.mark.parametrize("key", ["comedy-author", "comedy-reviewer"])
def test_a_malformed_score_is_refused_by_its_name(key, value):
    other = "comedy-reviewer: 15" if key == "comedy-author" else "comedy-author: 15"
    with pytest.raises(ComedyError, match=f"{key}.*not a whole number"):
        read(notes(other, f"{key}: {value}"))


@pytest.mark.parametrize("value", ["21", "100", "999", "-1"])
def test_a_score_off_the_scale_is_read_and_then_refused(value):
    assert "between 0 and 20" in shortfall(read(notes("comedy-author: 15", f"comedy-reviewer: {value}")))


@pytest.mark.parametrize("key", ["comedy-author", "comedy-reviewer"])
def test_a_score_given_twice_is_refused(key):
    with pytest.raises(ComedyError, match=f"{key} is given twice"):
        read(notes(*BOTH, f"{key}: 20"))


@pytest.mark.parametrize("key", ["comedy-reviewr", "comedy-review", "comedy-reviewer-2", "comedy-"])
def test_an_unknown_comedy_field_is_refused(key):
    with pytest.raises(ComedyError, match=f"unknown field {key}"):
        read(notes(*BOTH, f"{key}: 20"))


def test_no_scores_at_all_is_a_shortfall():
    assert "no comedy scores" in shortfall(None)


@pytest.mark.parametrize(
    "scores, says",
    [
        (Scores(21, 15), "comedy-author 21 is not between 0 and 20"),
        (Scores(15, 21), "comedy-reviewer 21 is not between 0 and 20"),
        (Scores(-1, 15), "comedy-author -1 is not between 0 and 20"),
        (Scores(15, -1), "comedy-reviewer -1 is not between 0 and 20"),
        (Scores("15", 15), "comedy-author '15' is not a whole number"),  # type: ignore[arg-type]
        (Scores(15, 14.0), "comedy-reviewer 14.0 is not a whole number"),  # type: ignore[arg-type]
        (Scores(True, 15), "comedy-author True is not a whole number"),
        (Scores(15, None), "comedy-reviewer None is not a whole number"),  # type: ignore[arg-type]
    ],
)
def test_scores_that_are_not_on_the_scale_are_a_shortfall(scores, says):
    assert shortfall(scores) == says


@pytest.mark.parametrize(
    "scores, lower",
    [(Scores(13, 13), 13), (Scores(20, 13), 13), (Scores(13, 20), 13), (Scores(0, 0), 0), (Scores(20, 0), 0)],
)
def test_below_the_floor_is_a_shortfall_at_the_lower_score(scores, lower):
    why = shortfall(scores)
    assert why.startswith(f"comedy score {lower} ") and "below the floor of 14" in why


@pytest.mark.parametrize("scores", [Scores(14, 14), Scores(20, 14), Scores(14, 20), Scores(20, 20)])
def test_at_or_above_the_floor_there_is_no_shortfall(scores):
    assert shortfall(scores) == ""


def test_notes_on_the_floor_have_no_shortfall():
    assert notes_shortfall(notes(*BOTH).encode()) == ""


@pytest.mark.parametrize(
    "data, says",
    [
        (b"", "frontmatter"),
        (b"\xff\xfe---\n", "UTF-8"),
        (notes("comedy-author: 15").encode(), "comedy-reviewer"),
        (notes("comedy-author: x", "comedy-reviewer: 14").encode(), "not a whole number"),
        (notes("comedy-author: 21", "comedy-reviewer: 14").encode(), "between 0 and 20"),
        (notes("comedy-author: 20", "comedy-reviewer: 13").encode(), "below the floor"),
    ],
)
def test_notes_that_cannot_clear_say_why(data, says):
    assert says in notes_shortfall(data)


def test_a_refusal_is_typed_and_names_every_slug_and_its_reason():
    with pytest.raises(ComedyError) as refused:
        refuse({"first-reel": "too low", "fine-reel": "", "other-reel": "no scores"})
    assert isinstance(refused.value, DeliveryError)
    assert "first-reel: too low" in str(refused.value) and "other-reel: no scores" in str(refused.value)
    assert "fine-reel" not in str(refused.value)


def test_nothing_short_is_nothing_refused():
    refuse({"fine-reel": ""})
    refuse({})

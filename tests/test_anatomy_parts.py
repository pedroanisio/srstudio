"""Every hand in the library is declared: rule 1's table, read against the registry and the drawings (ADR 0144)."""

from __future__ import annotations

import pytest

from srstudio import anatomy, anatomy_parts, collage_everyday, news_arms, parts, registry, toon_bento
from srstudio.anatomy import Facing, Side
from srstudio.anatomy_parts import CHARACTERS, HAND_PROPS, NOT_A_HAND, Kind


def _base(name: str) -> str:
    return name.partition("@")[0]


def _characters() -> set[str]:
    return {_base(e.name) for e in registry.entries("character")}


def _vocabulary() -> set[str]:
    """Every registered thing but a character whose name or summary speaks of a hand."""
    return {
        _base(e.name)
        for e in registry.entries()
        if e.kind != "character" and anatomy_parts.HAND_WORDS.search(f"{e.name} {e.summary}")
    }


def test_every_registered_character_declares_its_hands():
    assert _characters() - set(CHARACTERS) == set()


def test_the_table_names_no_character_that_is_not_registered():
    assert set(CHARACTERS) - _characters() == set()


def test_every_part_that_speaks_of_a_hand_is_declared_or_listed_as_no_hand():
    assert _vocabulary() - set(HAND_PROPS) - set(NOT_A_HAND) == set()


def test_a_hand_prop_or_a_listed_word_is_a_registered_part():
    names = {_base(e.name) for e in registry.entries()}
    assert (set(HAND_PROPS) | set(NOT_A_HAND)) - names == set()


def test_a_part_is_not_both_a_hand_and_not_one():
    assert set(HAND_PROPS) & set(NOT_A_HAND) == set()


def test_the_word_list_is_closed_against_a_new_hand():
    assert anatomy_parts.HAND_WORDS.search("toon-mitten A mitten for a paw")
    assert anatomy_parts.HAND_WORDS.search("x A hand on a stick")
    assert anatomy_parts.HAND_WORDS.search("x One thumb")
    assert not anatomy_parts.HAND_WORDS.search("toon-mug A mug")


@pytest.mark.parametrize("table", [CHARACTERS, HAND_PROPS, NOT_A_HAND])
def test_every_row_says_why(table):
    for name, row in table.items():
        why = row if isinstance(row, str) else row.why
        assert why.strip(), name


def test_a_declaration_that_is_a_pair_or_single_carries_its_side():
    for name, row in {**CHARACTERS, **HAND_PROPS}.items():
        if row.kind in (Kind.PAIRED, Kind.SINGLE):
            assert row.drawing is not None, name
            assert isinstance(row.drawing.side, Side) and isinstance(row.drawing.facing, Facing), name
        else:
            assert row.drawing is None, name


def test_a_declaration_refuses_a_side_on_a_hand_with_no_thumb():
    drawing = anatomy.Drawing("x", Side.LEFT, Facing.PALM)
    with pytest.raises(anatomy.AnatomyError, match="no thumb"):
        anatomy_parts.Hands(Kind.THUMBLESS, "a ball", drawing)


def test_a_declaration_refuses_a_thumbed_hand_with_no_side():
    with pytest.raises(anatomy.AnatomyError, match="side"):
        anatomy_parts.Hands(Kind.SINGLE, "one hand")


def test_a_declaration_refuses_an_empty_reason():
    with pytest.raises(anatomy.AnatomyError, match="why"):
        anatomy_parts.Hands(Kind.NONE, " ")


def test_the_pair_of_a_character_is_the_contract_its_style_draws_with():
    assert CHARACTERS["news-gus"].drawing == news_arms.DRAWINGS["open"]
    assert CHARACTERS["toon-bento"].drawing == toon_bento.DRAWINGS["open"]
    assert HAND_PROPS["collage-arm"].drawing == collage_everyday.REACHING_HAND


@pytest.mark.parametrize(
    ("part", "versions"), [("news-gus", {2, 3, 4, 5}), ("news-vera", {2, 3, 4, 5}), ("toon-bento", {1})]
)
def test_the_unpaired_versions_are_the_ones_with_one_drawing_on_both_arms(part, versions):
    numbers = {v.number for v in parts.get(part).versions}
    assert {n for n in numbers if anatomy_parts.unpaired(part, n)} == versions


def test_a_version_after_the_fix_and_any_other_part_is_not_unpaired():
    assert not anatomy_parts.unpaired("news-gus", 6)
    assert not anatomy_parts.unpaired("toon-bento", 2)
    assert not anatomy_parts.unpaired("toon-cat", 1)


def test_every_unpaired_part_is_a_declared_pair():
    for part in anatomy_parts.UNPAIRED:
        assert CHARACTERS[part].kind is Kind.PAIRED

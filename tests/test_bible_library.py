"""The shipped bible/ is a valid bible that holds what the spec asks of it: cards, placeholders, sealed worlds."""

import re
from pathlib import Path

import pytest

from srstudio import bible, bible_diagram, bible_lock
from srstudio.cast_card import CAST

LIBRARY = Path(__file__).resolve().parent.parent / "bible"
RETIRED = re.compile(r"tuxmeme|dejavu", re.IGNORECASE)


@pytest.fixture(scope="module")
def shipped() -> bible.Bible:
    return bible.load(LIBRARY)


def test_the_shipped_bible_loads_and_its_changelog_names_its_version(shipped):
    assert re.search(rf"^## {re.escape(shipped.version)}$", (LIBRARY / "CHANGELOG.md").read_text(), re.MULTILINE)


def test_every_cast_card_has_a_character_with_at_least_two_published_reels(shipped):
    for card in CAST:
        found = [c for c in shipped.named(card.name) if c.world == "okayville"]
        assert found and len(found[0].reels) >= 2, card.name


def test_the_placeholders_are_vera_gus_and_rafa_and_lint_is_not_a_character(shipped):
    waiting = {c.slug: (c.name, c.world) for c in shipped.characters if c.status == "placeholder"}
    assert waiting == {"vera": ("Vera", "news"), "news-gus": ("Gus", "news"), "rafa": ("Rafa", "host")}
    assert not shipped.named("lint")
    assert "Lint" in next(c for c in shipped.characters if c.slug == "rafa").open[0].question


def test_no_character_of_a_sealed_world_has_a_pair_in_another_world(shipped):
    world = {c.slug: c.world for c in shipped.characters}
    assert all(world[r.a] == world[r.b] for r in shipped.relationships)
    assert {"saga", "gloss"} <= set(world.values())


def test_every_clash_is_open_and_carries_a_proposal_and_evidence(shipped):
    assert shipped.clashes
    assert all(c.proposal.strip() and c.evidence for c in shipped.clashes)


def test_the_diagram_can_be_drawn_from_the_shipped_pairs(shipped):
    assert {p.world for p in bible_diagram.panels(shipped)} >= {"okayville", "saga", "gloss"}


@pytest.mark.parametrize("name", ["cast.json", "relationships.json", "CHANGELOG.md"])
def test_no_file_of_the_library_names_a_retired_account_or_font(name):
    assert not RETIRED.search((LIBRARY / name).read_text()), name


def test_the_shipped_bible_matches_its_lock_so_no_persona_changed_without_a_new_version():
    assert bible_lock.problems(LIBRARY) == []

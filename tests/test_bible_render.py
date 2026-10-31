"""The readable pages hold every field of the data, show a mark as a mark, and never state what the data does not."""

import re

from srstudio import bible
from srstudio import bible_render as render
from support.bible_docs import cast_document, placeholder, write

MODEL = "Claude Sonnet 5.5 (claude-sonnet-5-5)"


def loaded(tmp_path, edit=None) -> bible.Bible:
    cast = cast_document()
    cast["characters"].append(placeholder("rafa"))
    cast["characters"][0]["reels"] = ["zeta", "alpha"]
    if edit:
        edit(cast)
    return bible.load(write(tmp_path, cast))


def test_a_sheet_has_every_section_the_spec_names_and_the_drawing(tmp_path):
    b = loaded(tmp_path)
    page = render.sheet(b.character("rex"), model=MODEL, version=b.version, order=["alpha", "zeta"], drawing="rex.png")
    for heading in (
        "# Rex",
        "## Identity",
        "## Look",
        "## Voice",
        "## Who they are",
        "## Comic role",
        "## Canon",
        "## Never",
        "## Open",
    ):
        assert heading in page
    assert page.startswith(f"---\ngenerated-by: {MODEL} in Claude Code\nbible-version: 1.0.0\n---\n")
    assert "![Rex](rex.png)" in page and "Slug: `rex`" in page
    for label in (
        "Palette",
        "Provider",
        "Settings",
        "Verbal tics",
        "Words they never use",
        "A normal day",
        "Point of view",
        "What always gets them",
    ):
        assert label in page


def test_the_first_and_latest_reel_follow_the_order_of_the_record_not_the_order_written(tmp_path):
    b = loaded(tmp_path)
    page = render.sheet(b.character("rex"), model=MODEL, version=b.version, order=["alpha", "zeta"])
    assert "First reel: `alpha`" in page and "Latest reel: `zeta`" in page and "Published reels: 2" in page


def test_a_mark_is_shown_as_a_mark_and_a_stated_field_is_shown_as_stated(tmp_path):
    b = loaded(tmp_path)
    page = render.sheet(b.character("rex"), model=MODEL, version=b.version, order=[])
    assert "- Job: **Open.** what does he do?" in page
    assert "- Home: **Proposal.** a flat" in page
    assert "- Wants: " not in page and "- What they want: to win" in page
    assert "open:" not in page and "proposal:" not in page  # the raw mark never reaches a reader


def test_a_placeholder_says_so_and_a_character_with_no_reel_says_it_has_none(tmp_path):
    b = loaded(tmp_path)
    page = render.sheet(b.character("rafa"), model=MODEL, version=b.version, order=[])
    assert "Placeholder. Nothing here is canon" in page
    assert "Approved drawing: **Open.**" in page
    assert "None yet." in page


def test_the_canon_page_lists_each_fact_with_its_reel_and_skips_a_placeholder(tmp_path):
    b = loaded(tmp_path)
    page = render.canon(b, model=MODEL)
    assert "## Rex (Okayville)" in page and "(`cleaning-fee`)" in page
    assert "Rafa" not in page
    assert "### fern and rex" in page


def test_the_world_page_names_places_and_keeps_proposals_apart_from_what_the_reels_establish(tmp_path):
    b = loaded(tmp_path)
    page = render.world(b, model=MODEL)
    assert "### The rental" in page and "Found here: Rex, Fern." in page
    assert "## Proposed rules" in page and "animals talk" in page
    assert "## Rules the reels establish" not in page  # the only rule is a proposal


def test_the_open_decisions_page_counts_the_clashes_and_resolves_none(tmp_path):
    b = loaded(tmp_path)
    page = render.open_decisions(b, model=MODEL)
    assert "Clashes: 1." in page and "## Name clashes" in page
    assert "Proposed resolution: rename the other" in page
    assert "Open questions on characters (3)" in page
    assert re.search(r"Persona fields still marked open or proposal across the cast: \d+", page)


def test_no_page_carries_the_retired_account_name(tmp_path):
    b = loaded(tmp_path)
    pages = [render.sheet(c, model=MODEL, version=b.version, order=[]) for c in b.characters]
    pages += [render.canon(b, model=MODEL), render.world(b, model=MODEL), render.open_decisions(b, model=MODEL)]
    assert not any("tuxmeme" in p.lower() for p in pages)


def test_the_front_page_lists_each_world_links_the_sheets_and_names_the_placeholders(tmp_path):
    b = loaded(tmp_path)
    page = render.readme(b, model=MODEL, sheets=["rex", "fern"])
    assert "[Rex](characters/rex.md)" in page and "![Who knows whom](relationships.png)" in page
    assert "## Placeholders" in page and "Rafa (Okayville)" in page
    assert "srstudio bible check" in page and "cannot tell that a paragraph" in page
    assert render.readme(b, model=MODEL, sheets=[]).count("(characters/") == 0  # no link to a sheet not written

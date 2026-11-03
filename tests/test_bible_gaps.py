"""The gaps list is the work that extends the bible: names that recur with no sheet, sheets that lag their reels."""

from dataclasses import replace

from srstudio import bible, bible_gaps
from srstudio.bible_inventory import Reel
from support.bible_docs import cast_document, character, pair, pairs_document, placeholder, write


def reel(slug: str, *names: str) -> Reel:
    return Reel(
        slug,
        "okayville" if not slug.startswith(("saga-", "gloss-")) else slug.split("-")[0],
        frozenset(names),
        frozenset(),
        frozenset(),
        frozenset(),
    )


def library(tmp_path, *extra: dict, roles=("narrator",)):
    cast = cast_document()
    cast["characters"] += list(extra)
    cast["roles"] = list(roles)
    pairs = pairs_document()
    pairs["relationships"] = [pair("fern", "rex")]
    return bible.load(write(tmp_path / "bible", cast, pairs))


def test_a_name_on_two_reels_with_no_sheet_is_missing_and_one_reel_is_not(tmp_path):
    held = library(tmp_path)
    reels = [reel("a-one", "rex", "bruno"), reel("a-two", "bruno", "rex"), reel("a-three", "zoe")]
    found = bible_gaps.find(held, reels)
    assert found.missing == (("bruno", "okayville", ("a-one", "a-two")),)
    assert bool(found)


def test_a_role_noun_is_never_a_missing_character(tmp_path):
    held = library(tmp_path)
    found = bible_gaps.find(held, [reel("a-one", "narrator"), reel("a-two", "narrator")])
    assert found.missing == ()


def test_the_other_spelling_of_a_role_is_never_a_missing_character(tmp_path):
    held = library(tmp_path, roles=("neighbor",))
    found = bible_gaps.find(held, [reel("a-one", "neighbour"), reel("a-two", "neighbour")])
    assert found.missing == ()


def test_a_sheet_that_lacks_a_reel_naming_it_is_stale_and_a_complete_one_is_not(tmp_path):
    held = library(tmp_path)
    rex = held.character("rex")
    listed = list(rex.reels)
    reels = [reel(s, "rex") for s in listed] + [reel("new-reel", "rex")]
    assert bible_gaps.find(held, reels).stale == (("rex", ("new-reel",)),)
    assert not bible_gaps.find(held, reels[:-1]).stale


def test_a_reel_that_a_clash_cites_or_names_is_on_record_not_stale(tmp_path):
    clash = {
        "id": "rex-name",
        "kind": "name",
        "scope": "within-world",
        "subject": "Rex in odd-reel is another Rex",
        "evidence": [],
        "proposal": "Rename one.",
    }
    cast = cast_document()
    cast["clashes"] = [clash]
    held = bible.load(write(tmp_path / "bible", cast, pairs_document()))
    found = bible_gaps.find(held, [reel(s, "rex") for s in held.character("rex").reels] + [reel("odd-reel", "rex")])
    assert found.stale == ()
    assert bible_gaps.find(held, [reel("odd-reel-two", "rex")]).stale == (("rex", ("odd-reel-two",)),)


def test_a_sealed_world_name_does_not_borrow_the_sheet_of_another_world(tmp_path):
    held = library(tmp_path)
    reels = [reel("saga-one", "rex"), reel("saga-two", "rex")]
    assert bible_gaps.find(held, reels).missing == (("rex", "saga", ("saga-one", "saga-two")),)


def test_placeholders_wait_and_reels_with_no_character_are_counted(tmp_path):
    held = library(tmp_path, placeholder("vera"))
    found = bible_gaps.find(held, [reel("a-one", "zoe")])
    assert found.waiting == ("vera",)
    assert found.bare == ("a-one",)
    assert not found


def test_a_gap_free_bible_is_falsy_and_carries_no_missing_or_stale():
    assert not bible_gaps.Gaps((), (), ("vera",), ())
    assert replace(bible_gaps.Gaps((), (), (), ()), stale=(("a", ("b",)),))


def test_characters_of_one_world_that_share_a_name_share_the_reels_it_is_on(tmp_path):
    twin = character("twin")
    twin["name"] = "Rex"
    twin["reels"] = ["gary-reel"]
    held = library(tmp_path, twin)
    rex = held.character("rex")
    reels = [reel(s, "rex") for s in rex.reels] + [reel("gary-reel", "rex"), reel("new-reel", "rex")]
    assert bible_gaps.find(held, reels).stale == (("rex", ("new-reel",)),)  # gary-reel is the twin's; listed once

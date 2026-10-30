"""Numbered character versions (ADR 0047): the typed table, the default, and what a version may claim."""

import json
from dataclasses import replace

import pytest

from srstudio import characters, registry, sketch, specimens, toon_inked
from srstudio.characters import Approval, Character, CharacterError, NotApprovedError, UnknownVersionError, Version

DIGEST = "a" * 64
WORDS = Approval("2026-10-30", "approved, lets add version to the characters as we will improve then frequently")


def version(number: int = 2, **kw) -> Version:
    fields = {
        "number": number,
        "date": "2026-10-30",
        "note": "A smoother shoulder",
        "status": "approved",
        "proof": "generated/character-proofs/x/x.mp4",
        "drawing": DIGEST,
        "approval": WORDS,
    }
    return Version(**{**fields, **kw})


def baseline() -> Version:
    return version(1, proof="", approval=None)


def test_every_registered_character_has_a_record_and_every_record_a_drawing():
    specimens.load_parts()
    drawn = {e.name for e in registry.entries("character")}
    table = characters.load()
    assert {n for n in drawn if "@" not in n} == set(table)
    for name, character in table.items():
        assert character.style == registry.get("character", name).style
        for v in character.versions:
            assert characters.part_name(name, v.number) in drawn


def test_a_new_reel_gets_the_latest_approved_version_and_can_ask_for_an_older_one():
    assert characters.latest("toon-fox").number == 2
    assert characters.part("toon-fox").builder is toon_inked.fox_inked
    assert characters.part("toon-fox", 1).name == "toon-fox"
    assert sketch.drawer("fox") is toon_inked.fox_inked
    assert sketch.drawer("fox", {"toon-fox": 1}).__name__ == "fox"
    assert characters.latest("toon-bear").number == 1


def test_fox_inked_is_fox_version_two_and_no_longer_a_name():
    assert "fox-inked" not in sketch.CHARACTERS and "fox-inked" not in sketch.LIP_SYNCED
    fox = characters.get("toon-fox").version(2)
    assert fox.status == "approved" and fox.proof.endswith("fox-proof.mp4")
    assert fox.approval is not None and fox.approval.date == "2026-10-30"
    assert fox.approval.words == WORDS.words
    with pytest.raises(registry.NotRegisteredError, match="toon-fox-inked"):
        registry.get("character", "toon-fox-inked")


@pytest.mark.parametrize("call", [characters.part, characters.pin])
def test_an_unknown_version_raises_by_name(call):
    with pytest.raises(UnknownVersionError, match=r"toon-fox has no version 9; it has 1, 2"):
        call("toon-fox", 9)


def test_an_unknown_character_raises_by_name():
    with pytest.raises(CharacterError, match="no character 'toon-unicorn'"):
        characters.get("toon-unicorn")


def test_a_proposed_version_is_never_the_default_and_cannot_be_pinned():
    newer = version(2, status="proposed", approval=None, drawing="")
    fox = Character("toon-fox", "toon", (baseline(), newer))
    assert fox.latest().number == 1
    with pytest.raises(NotApprovedError, match="toon-fox version 2 is proposed"):
        fox.pinned(2)


def test_a_character_with_nothing_approved_has_no_default():
    fresh = Character("toon-sloth", "toon", (version(1, status="proposed", approval=None, drawing="", proof=""),))
    with pytest.raises(NotApprovedError, match="toon-sloth has no approved version"):
        fresh.latest()


@pytest.mark.parametrize(
    ("kw", "why"),
    [
        ({"approval": None}, "whose approval"),
        ({"proof": ""}, "proof"),
        ({"drawing": ""}, "drawing"),
        ({"drawing": "abc"}, "drawing"),
        ({"status": "accepted"}, "status"),
        ({"date": "yesterday"}, "date"),
        ({"note": ""}, "note"),
        ({"note": "two\nlines"}, "note"),
        ({"number": 0}, "number"),
        ({"number": True}, "number"),
        ({"status": "proposed"}, "approval"),
    ],
)
def test_a_version_cannot_claim_what_it_lacks(kw, why):
    with pytest.raises(CharacterError, match=why):
        version(**kw)


@pytest.mark.parametrize(("day", "words", "why"), [("soon", "yes", "date"), ("2026-10-30", " ", "words")])
def test_an_approval_says_when_and_in_whose_words(day, words, why):
    with pytest.raises(CharacterError, match=why):
        Approval(day, words)


def test_only_version_one_is_approved_without_a_proof_or_an_approval():
    assert baseline().approval is None
    assert version(1).approval == WORDS


def test_version_numbers_run_from_one_without_a_gap():
    with pytest.raises(CharacterError, match="1, 2"):
        Character("toon-fox", "toon", (baseline(), version(3)))


def test_a_style_that_does_not_read_pins_cannot_take_a_second_version():
    with pytest.raises(CharacterError, match=r"saga-gloom.*saga.*does not read pins"):
        Character("saga-gloom", "saga", (baseline(), version(2)))


def test_saga_starts_at_one_as_drawn():
    assert all(len(c.versions) == 1 for n, c in characters.load().items() if c.style == "saga")


def table(tmp_path, doc) -> characters.Table:
    path = tmp_path / "characters.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return characters.read(path)


def doc(**extra) -> dict:
    entry = {
        "number": 1,
        "date": "2026-10-30",
        "note": "As published",
        "status": "approved",
        "proof": "",
        "drawing": DIGEST,
        "approval": None,
    }
    return {
        "schema": characters.SCHEMA,
        "characters": {"toon-fox": {"style": "toon", "versions": [{**entry, **extra}]}},
    }


def test_the_table_reads_into_typed_records(tmp_path):
    assert table(tmp_path, doc())["toon-fox"].versions[0].number == 1


@pytest.mark.parametrize(
    "broken",
    [
        {"schema": "9.9.9", "characters": {}},
        {"schema": characters.SCHEMA},
        {"schema": characters.SCHEMA, "characters": {}, "more": 1},
        {"schema": characters.SCHEMA, "characters": {"toon-fox": {"style": "toon"}}},
        {"schema": characters.SCHEMA, "characters": {"toon-fox": {"style": "toon", "versions": [], "x": 1}}},
        doc(unknown=1),
        doc(approval={"date": "2026-10-30", "words": "yes", "who": "me"}),
    ],
)
def test_the_table_refuses_what_it_does_not_know(tmp_path, broken):
    with pytest.raises(CharacterError):
        table(tmp_path, broken)


def test_the_shipped_records_are_frozen():
    v = characters.latest("toon-fox")
    assert replace(v, note="Changed").note == "Changed"
    with pytest.raises(AttributeError):
        v.note = "Changed"  # type: ignore[misc]

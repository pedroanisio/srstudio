"""Numbered versions of every part (ADR 0047): the typed table, the default, and what a version may claim."""

import json
from dataclasses import replace

import pytest

from srstudio import catalog_specimens, parts, registry, sketch, specimens, toon_inked, toon_rigs
from srstudio.parts import (
    Approval,
    NotApprovedError,
    Part,
    PartError,
    Reason,
    Refused,
    Rig,
    UnknownVersionError,
    Version,
)

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


def test_every_registered_part_has_a_record_and_every_record_a_drawing():
    specimens.load_parts()
    drawn = {e.name: e for e in registry.entries()}
    table = parts.load()
    assert {n for n in drawn if "@" not in n} == set(table)
    for name, part in table.items():
        assert (part.kind, part.style) == (drawn[name].kind, drawn[name].style)
        for v in part.versions:
            assert parts.part_name(name, v.number) in drawn


def test_a_part_of_any_kind_draws_its_version():
    assert parts.drawing("coffee-cup").kind == "prop"
    assert parts.drawing("cafe", 1).kind == "location"
    assert parts.resolved("coffee-cup") == 1


@pytest.mark.parametrize(
    ("name", "kind", "style"),
    [("toon-desk", "location", "toon"), ("coffee-cup", "prop", "cutout"), ("saga-gloom", "character", "saga")],
)
def test_a_second_version_is_refused_by_name_until_its_kind_and_style_are_routed(name, kind, style):
    assert (kind, style) not in parts.ROUTED
    with pytest.raises(PartError, match=f"{name}.*does not read pins.*parts.ROUTED"):
        Part(name, kind, style, (baseline(), version(2)))


def test_a_refused_part_has_a_typed_reason_and_no_digest():
    why = Refused(Reason.OVERLAY, "burned captions")
    assert Part("captions", "graphic", "", (version(1, approval=None, proof="", drawing=""),), why).refused == why
    with pytest.raises(PartError, match="a refused part has no digest"):
        Part("captions", "graphic", "", (baseline(),), why)


def test_a_drawn_part_cannot_leave_its_digest_out_when_approved():
    with pytest.raises(PartError, match="an approved version records its drawing"):
        Part("coffee-cup", "prop", "cutout", (version(1, approval=None, proof="", drawing=""),))


@pytest.mark.parametrize(("reason", "detail"), [("overlay", "x"), (Reason.OVERLAY, ""), (Reason.OVERLAY, "a\nb")])
def test_a_refusal_says_why_in_one_line(reason, detail):
    with pytest.raises(PartError, match="refusal"):
        Refused(reason, detail)


def test_every_refusal_in_the_table_is_the_catalog_s_and_nothing_else_is_refused():
    table = parts.load()
    assert {n: p.refused for n, p in table.items() if p.refused} == catalog_specimens.REFUSED
    assert all(not v.drawing for p in table.values() if p.refused for v in p.versions)


def test_a_new_reel_gets_the_latest_approved_version_and_can_ask_for_an_older_one():
    assert parts.latest("toon-fox").number == 2
    assert parts.drawing("toon-fox").builder is toon_inked.fox_inked
    assert parts.drawing("toon-fox", 1).name == "toon-fox"
    assert sketch.drawer("fox") is toon_inked.fox_inked
    assert sketch.drawer("fox", {"toon-fox": 1}).__name__ == "fox"
    assert parts.latest("toon-bear").number == 1


def test_fox_inked_is_fox_version_two_and_no_longer_a_name():
    assert "fox-inked" not in sketch.CHARACTERS and "fox-inked" not in sketch.LIP_SYNCED
    fox = parts.get("toon-fox").version(2)
    assert fox.status == "approved" and fox.proof.endswith("fox-proof.mp4")
    assert fox.approval is not None and fox.approval.date == "2026-10-30"
    assert fox.approval.words == WORDS.words
    with pytest.raises(registry.NotRegisteredError, match="toon-fox-inked"):
        registry.get("character", "toon-fox-inked")


@pytest.mark.parametrize("call", [parts.drawing, parts.pin])
def test_an_unknown_version_raises_by_name(call):
    with pytest.raises(UnknownVersionError, match=r"toon-fox has no version 9; it has 1, 2"):
        call("toon-fox", 9)


def test_an_unknown_part_raises_by_name():
    with pytest.raises(PartError, match="no part 'toon-unicorn'"):
        parts.get("toon-unicorn")


def test_a_proposed_version_is_never_the_default_and_cannot_be_pinned():
    newer = version(2, status="proposed", approval=None, drawing="")
    fox = Part("toon-fox", "character", "toon", (baseline(), newer))
    assert fox.latest().number == 1
    with pytest.raises(NotApprovedError, match="toon-fox version 2 is proposed"):
        fox.pinned(2)


def test_a_character_with_nothing_approved_has_no_default():
    fresh = Part(
        "toon-sloth", "character", "toon", (version(1, status="proposed", approval=None, drawing="", proof=""),)
    )
    with pytest.raises(NotApprovedError, match="toon-sloth has no approved version"):
        fresh.latest()


@pytest.mark.parametrize(
    ("kw", "why"),
    [
        ({"approval": None}, "whose approval"),
        ({"proof": ""}, "proof"),
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
    with pytest.raises(PartError, match=why):
        version(**kw)


@pytest.mark.parametrize(("day", "words", "why"), [("soon", "yes", "date"), ("2026-10-30", " ", "words")])
def test_an_approval_says_when_and_in_whose_words(day, words, why):
    with pytest.raises(PartError, match=why):
        Approval(day, words)


def test_only_version_one_is_approved_without_a_proof_or_an_approval():
    assert baseline().approval is None
    assert version(1).approval == WORDS


def test_version_numbers_run_from_one_without_a_gap():
    with pytest.raises(PartError, match="1, 2"):
        Part("toon-fox", "character", "toon", (baseline(), version(3)))


def test_a_style_that_does_not_read_pins_cannot_take_a_second_version():
    with pytest.raises(PartError, match=r"saga-gloom.*saga character does not read pins"):
        Part("saga-gloom", "character", "saga", (baseline(), version(2)))


def test_saga_starts_at_one_as_drawn():
    assert all(len(c.versions) == 1 for n, c in parts.load().items() if c.style == "saga")


ENTRY = {
    "number": 1,
    "date": "2026-10-30",
    "note": "As published",
    "status": "approved",
    "proof": "",
    "drawing": DIGEST,
    "approval": None,
    "rig": None,
}


def table(tmp_path, doc) -> parts.Table:
    path = tmp_path / "parts.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return parts.read(path)


def doc(**extra) -> dict:
    return {
        "schema": parts.TABLE_SCHEMA,
        "parts": {
            "toon-fox": {"kind": "character", "style": "toon", "refused": None, "versions": [{**ENTRY, **extra}]}
        },
    }


def test_the_table_reads_into_typed_records(tmp_path):
    assert table(tmp_path, doc())["toon-fox"].versions[0].number == 1


@pytest.mark.parametrize(
    "broken",
    [
        {"schema": "9.9.9", "parts": {}},
        {"schema": parts.TABLE_SCHEMA},
        {"schema": parts.TABLE_SCHEMA, "parts": {}, "more": 1},
        {"schema": parts.TABLE_SCHEMA, "parts": {"toon-fox": {"kind": "character", "style": "toon"}}},
        {
            "schema": parts.TABLE_SCHEMA,
            "parts": {"toon-fox": {"kind": "ghost", "style": "", "refused": None, "versions": [ENTRY]}},
        },
        {
            "schema": parts.TABLE_SCHEMA,
            "parts": {
                "toon-fox": {
                    "kind": "prop",
                    "style": "",
                    "refused": {"reason": "bored", "detail": "x"},
                    "versions": [ENTRY],
                }
            },
        },
        doc(unknown=1),
        doc(approval={"date": "2026-10-30", "words": "yes", "who": "me"}),
    ],
)
def test_the_table_refuses_what_it_does_not_know(tmp_path, broken):
    with pytest.raises(PartError):
        table(tmp_path, broken)


def test_the_shipped_records_are_frozen():
    v = parts.latest("toon-fox")
    assert replace(v, note="Changed").note == "Changed"
    with pytest.raises(AttributeError):
        v.note = "Changed"  # type: ignore[misc]


HEADS = Approval("2026-10-30", "head motion approved")


def rig(**kw) -> Rig:
    fields = {
        "date": "2026-10-30",
        "note": "Split at the neck",
        "status": "approved",
        "proof": "generated/character-proofs/head-rig/index.html",
        "drawing": DIGEST,
        "approval": HEADS,
    }
    return Rig(**{**fields, **kw})


def test_a_version_holds_its_rig_as_a_record_of_its_own():
    assert version(rig=rig()).rig == rig()
    assert version().rig is None


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
        ({"status": "proposed"}, "approval"),
    ],
)
def test_a_rig_cannot_claim_what_it_lacks(kw, why):
    with pytest.raises(PartError, match=why):
        rig(**kw)


def test_a_proposed_rig_may_still_be_drawn():
    assert rig(status="proposed", approval=None, drawing="", proof="").status == "proposed"


def test_the_table_reads_a_rig_and_refuses_one_it_does_not_know(tmp_path):
    held = {**vars(rig()), "approval": {"date": "2026-10-30", "words": "head motion approved"}}
    assert table(tmp_path, doc(rig=held))["toon-fox"].versions[0].rig == rig()
    with pytest.raises(PartError):
        table(tmp_path, doc(rig={**held, "who": "me"}))


def test_the_table_and_a_project_record_carry_their_own_schemas():
    assert parts.TABLE_SCHEMA != parts.RECORD_SCHEMA


def test_a_project_record_still_reads_after_the_table_s_schema_moves(tmp_path, monkeypatch):
    parts.write_record(tmp_path, {"toon-fox": 2})
    monkeypatch.setattr(parts, "TABLE_SCHEMA", "9.9.9")
    assert parts.read_record(tmp_path) == {"toon-fox": 2}


def test_every_rig_has_a_record_and_every_record_a_rig():
    recorded = {
        parts.part_name(name, v.number) for name, p in parts.load().items() for v in p.versions if v.rig is not None
    }
    assert recorded == set(toon_rigs.RIGS)


def test_the_approved_rigs_quote_the_operator():
    for name, number in (("toon-sloth", 1), ("toon-goat", 1), ("toon-hamster", 1), ("toon-fox", 2)):
        held = parts.get(name).version(number).rig
        assert held is not None and held.status == "approved"
        assert held.approval is not None and held.approval.words == "head motion approved"
        assert held.proof.startswith("generated/character-proofs/head-")

"""The bible loader parses cast.json and relationships.json strictly and enforces the bible's own rules (ADR 0069).

Each test feeds the loader one broken file next to a good one, and asserts the typed refusal that names the fault.
"""

import copy
import json
from dataclasses import replace

import pytest

from srstudio import bible
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from support.bible_docs import cast_document, fact, pairs_document, placeholder, write


def mutated(edit) -> dict:
    document = copy.deepcopy(cast_document())
    edit(document)
    return document


def test_a_file_may_name_the_model_and_tool_that_wrote_it(tmp_path):
    document = cast_document()
    document["generated_by"] = "Claude Sonnet 5.5 in Claude Code"
    assert bible.load(write(tmp_path, document)).version == "1.0.0"


def test_a_good_bible_loads_with_every_section(tmp_path):
    loaded = bible.load(write(tmp_path))
    assert loaded.version == "1.0.0"
    assert [c.slug for c in loaded.characters] == ["rex", "fern"]
    assert loaded.character("rex").voice.voice == "Charlie"
    assert loaded.relationships[0].a == "fern"
    assert loaded.named("REX")[0].slug == "rex" and loaded.named("nobody") == []
    assert len(loaded.facts()) == len(loaded.characters[0].canon) * 2 + 1 + 1 + 1


@pytest.mark.parametrize(
    "edit, message",
    [
        (lambda d: d.update(extra=1), "unknown field"),
        (lambda d: d.pop("roles"), "missing field"),
        (lambda d: d["characters"][0].update(nickname="x"), "unknown field.*nickname"),
        (lambda d: d["characters"][0]["voice"].update(accent="x"), "unknown field.*accent"),
        (lambda d: d["characters"][0]["look"].update(hat="x"), "unknown field.*hat"),
        (lambda d: d["characters"][0]["canon"][0].update(page=3), "unknown field.*page"),
        (lambda d: d["characters"][0].pop("never"), "missing field.*never"),
        (lambda d: d["characters"][0].update(world="mars"), "not one of"),
        (lambda d: d["characters"][0].update(slug="Rex"), "not a lowercase slug"),
        (lambda d: d["characters"][0]["comic"].update(role="hero"), "not one of"),
        (lambda d: d["characters"][0]["canon"][0].update(field="who.shoe"), "not one of"),
        (lambda d: d["characters"][0]["canon"][0].update(kind="hunch"), "not one of"),
        (lambda d: d["characters"][0]["voice"].update(pace="  "), "nonempty text"),
        (lambda d: d["characters"][0]["voice"].update(pace=3), "nonempty text"),
        (lambda d: d["characters"][0]["look"]["drawing"][0].update(version=0), "version number"),
        (lambda d: d["characters"][0]["look"]["drawing"][0].update(version=True), "version number"),
        (lambda d: d["characters"][0].update(since="v1"), "not a semantic version"),
        (lambda d: d["characters"][0].update(reels="cleaning-fee"), "expected a list"),
        (lambda d: d.update(characters={}), "expected a list"),
        (lambda d: d.update(version="1.0"), "semantic version"),
        (lambda d: d.update(schema="2.0.0"), "schema"),
        (lambda d: d.update(generated_by="  "), "generated_by names the model"),
        (lambda d: d.update(generated_by=3), "generated_by names the model"),
        (lambda d: d["rules"][0].update(status="law"), "not one of"),
        (lambda d: d["clashes"][0].update(scope="somewhere"), "not one of"),
        (lambda d: d["places"][0].update(found="rex"), "expected a list"),
    ],
)
def test_a_malformed_cast_file_is_refused_with_a_typed_error_that_names_the_fault(tmp_path, edit, message):
    with pytest.raises(bible.BibleError, match=message):
        bible.load(write(tmp_path, mutated(edit)))


@pytest.mark.parametrize(
    "edit, message",
    [
        (lambda d: d["characters"][0].update(never=["a", "b"]), "exactly three"),
        (lambda d: d["characters"][0].update(canon=[]), "no fact"),
        (lambda d: d["characters"][1].update(slug="rex"), "appears twice"),
        (
            lambda d: d["characters"][0]["canon"].pop(0),
            "who.age_range|voice.provider|look.palette|comic.role|voice.voice",
        ),
        (lambda d: d["characters"][0]["who"].update(job="a fireman"), "who.job is marked yet|who.job is stated"),
        (lambda d: d["characters"][0]["look"].update(drawing=[]), "no approved drawing"),
        (lambda d: d["places"][0].update(found=["rex", "ghost"]), "ghost is not a character"),
        (lambda d: d["places"].append(copy.deepcopy(d["places"][0])), "appears twice"),
        (lambda d: d["rules"].append(copy.deepcopy(d["rules"][0])), "appears twice"),
    ],
)
def test_the_rules_of_the_bible_refuse_what_the_schema_cannot_express(tmp_path, edit, message):
    with pytest.raises(bible.BibleError, match=message):
        bible.load(write(tmp_path, mutated(edit)))


def test_a_stated_field_with_no_fact_behind_it_is_refused_and_the_message_names_it(tmp_path):
    document = cast_document()
    document["characters"][0]["canon"] = [f for f in document["characters"][0]["canon"] if f["field"] != "who.flaw"]
    with pytest.raises(bible.BibleError, match="who.flaw is stated with no fact behind it"):
        bible.load(write(tmp_path, document))


def test_a_marked_field_that_also_has_a_fact_is_refused(tmp_path):
    document = cast_document()
    document["characters"][0]["canon"].append(fact("who.job"))
    with pytest.raises(bible.BibleError, match="who.job is marked yet has a fact behind it"):
        bible.load(write(tmp_path, document))


def test_a_placeholder_is_all_open_and_holds_no_canon(tmp_path):
    document = cast_document()
    document["characters"].append(placeholder("vera"))
    loaded = bible.load(write(tmp_path, document))
    assert loaded.character("vera").status == "placeholder"


def test_a_placeholder_that_states_something_or_holds_a_fact_is_refused(tmp_path):
    stated = cast_document()
    stated["characters"].append(placeholder("vera"))
    stated["characters"][-1]["who"]["job"] = "a presenter"
    with pytest.raises(bible.BibleError, match="who.job"):
        bible.load(write(tmp_path, stated))
    holding = cast_document()
    holding["characters"].append(placeholder("vera"))
    holding["characters"][-1]["canon"] = [fact("identity")]
    with pytest.raises(bible.BibleError, match="no canon"):
        bible.load(write(tmp_path, holding))


@pytest.mark.parametrize(
    "edit, message",
    [
        (lambda p: p["relationships"][0].update(a="rex", b="fern"), "alphabetically"),
        (lambda p: p["relationships"][0].update(a="rex", b="rex"), "themself"),
        (lambda p: p["relationships"][0].update(b="ghost"), "ghost is not a character"),
        (lambda p: p["relationships"][0].update(status="maybe"), "not one of"),
        (lambda p: p["relationships"][0].update(history=[]), "no history fact"),
        (lambda p: p["relationships"][0].update(tension="open: unknown"), "its status is proposal"),
        (lambda p: p["relationships"][0].update(extra=1), "unknown field"),
        (lambda p: p["relationships"].append(copy.deepcopy(p["relationships"][0])), "appears twice"),
        (lambda p: p.update(version="1.1.0"), "relationships.json"),
    ],
)
def test_a_malformed_relationship_file_is_refused(tmp_path, edit, message):
    document = pairs_document()
    edit(document)
    with pytest.raises(bible.BibleError, match=message):
        bible.load(write(tmp_path, pairs=document))


def test_a_proposed_relationship_may_be_open_and_have_no_history(tmp_path):
    document = pairs_document()
    document["relationships"][0].update(status="proposal", tension="open: unknown", history=[])
    assert bible.load(write(tmp_path, pairs=document)).relationships[0].status == "proposal"


@pytest.mark.parametrize("raw", ["not json", "[]", '{"schema": "1.0.0"}'])
def test_a_file_that_is_not_the_bible_is_refused(tmp_path, raw):
    write(tmp_path)
    (tmp_path / "cast.json").write_text(raw)
    with pytest.raises(bible.BibleError):
        bible.load(tmp_path)


def test_a_missing_file_is_refused_and_named(tmp_path):
    with pytest.raises(bible.BibleError, match="cast.json"):
        bible.load(tmp_path)


def release(slug: str, **kw: object) -> Release:
    return Release(
        slug,
        InstagramPost(title="t", description="Fern paid.", hashtags=("#a",)),
        tags=Tags("money-services", "other-person", "recognition"),
        **kw,
    )


def test_verify_lists_each_fact_its_reel_does_not_bear_out(tmp_path):
    episodes = tmp_path / "episodes"
    (episodes / "cleaning-fee").mkdir(parents=True)
    (episodes / "cleaning-fee" / "script.json").write_text(json.dumps([{"speaker": "rex", "text": "Teamwork!"}]))
    document = cast_document()
    document["characters"][0]["canon"][0]["quote"] = "Not a line anywhere"
    loaded = bible.load(write(tmp_path / "bible", document))
    releases = {"cleaning-fee": release("cleaning-fee", parts={"toon-dog": 1})}
    problems = bible.verify(loaded, releases, {"cleaning-fee"}, episodes, characters={"toon-dog"})
    assert problems == ["rex: cleaning-fee: no line says 'Not a line anywhere'"]


def test_verify_refuses_a_reel_that_is_not_published_and_does_not_hide_a_seen_fact(tmp_path):
    episodes = tmp_path / "episodes"
    (episodes / "cleaning-fee").mkdir(parents=True)
    (episodes / "cleaning-fee" / "script.json").write_text(json.dumps([{"speaker": "rex", "text": "Teamwork!"}]))
    document = cast_document()
    document["characters"][0]["reels"] = ["cleaning-fee", "pilot-one"]
    document["characters"][0]["canon"][1].update(kind="seen", quote="t=1 a badge")
    loaded = bible.load(write(tmp_path / "bible", document))
    releases = {"cleaning-fee": release("cleaning-fee")}
    problems = bible.verify(loaded, releases, {"cleaning-fee"}, episodes, characters=set())
    assert problems == ["rex: reels not published: pilot-one"]


def test_verify_flags_a_name_that_only_a_voice_credit_gives_and_no_reel_says(tmp_path):
    episodes = tmp_path / "episodes"
    (episodes / "cleaning-fee").mkdir(parents=True)
    (episodes / "cleaning-fee" / "script.json").write_text(json.dumps([{"speaker": "boss", "text": "Teamwork!"}]))
    document = cast_document()
    document["characters"][0]["name"] = "Eric"
    loaded = bible.load(write(tmp_path / "bible", document))
    gift = release("cleaning-fee", parts={"toon-dog": 1})
    credit = replace(gift, post=replace(gift.post, credit="ElevenLabs premade voice Eric."))
    problems = bible.verify(loaded, {"cleaning-fee": credit}, {"cleaning-fee"}, episodes, characters={"toon-dog"})
    assert problems == ["rex: the name 'Eric' is in no title, description, line or speaker of its reels"]


def test_verify_accepts_a_name_a_speaker_or_a_line_gives_with_or_without_the_article(tmp_path):
    episodes = tmp_path / "episodes"
    (episodes / "cleaning-fee").mkdir(parents=True)
    (episodes / "cleaning-fee" / "script.json").write_text(
        json.dumps([{"speaker": "x", "text": "Teamwork! Ask the Boss."}])
    )
    document = cast_document()
    document["characters"][0]["name"] = "The Boss"
    document["characters"][1]["name"] = "Teamwork (the second)"  # a bracketed label is the bible's, not the reel's
    loaded = bible.load(write(tmp_path / "bible", document))
    releases = {"cleaning-fee": release("cleaning-fee")}
    assert bible.verify(loaded, releases, {"cleaning-fee"}, episodes, characters=set()) == []


TRAIT = {"word": "Unbothered", "approval": "arc4d3, Slack 1793967529.705339"}


def test_an_approved_trait_loads_and_renders_with_its_approval(tmp_path):
    """A trait is the one word the series puts on screen for a character, with who approved it (J&P, from ep4)."""
    from srstudio import bible_render

    loaded = bible.load(write(tmp_path, mutated(lambda d: d["characters"][0]["comic"].update(trait=TRAIT))))
    rex = loaded.character("rex")
    assert rex.comic.trait == bible.Trait("Unbothered", "arc4d3, Slack 1793967529.705339")
    assert loaded.character("fern").comic.trait is None
    assert "- Trait: Unbothered (approved by arc4d3, Slack 1793967529.705339)" in bible_render.sheet(
        rex, model="fixture", version=loaded.version, order=[]
    )


@pytest.mark.parametrize(
    "trait, message",
    [
        ({"word": "unbothered", "approval": "arc4d3"}, "one capitalised word"),
        ({"word": "Very Calm", "approval": "arc4d3"}, "one capitalised word"),
        ({"word": "Unbothered", "approval": "  "}, "nonempty text"),
        ({"word": "Unbothered"}, "missing field"),
        ({"word": "Unbothered", "approval": "arc4d3", "colour": "red"}, "unknown field"),
        ("Unbothered", "expected an object"),
    ],
)
def test_a_malformed_trait_is_refused(tmp_path, trait, message):
    with pytest.raises(bible.BibleError, match=message):
        bible.load(write(tmp_path, mutated(lambda d: d["characters"][0]["comic"].update(trait=trait))))

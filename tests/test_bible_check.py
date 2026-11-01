"""The canon check names what a reel or a brief gets wrong against the bible (ADR 0069)."""

import json

import pytest

from srstudio import bible, bible_check
from srstudio.releases import Release, Tags
from srstudio.social import DeliveryError, InstagramPost
from support.bible_docs import cast_document, character, placeholder, write


def release(slug: str, *, recurring: tuple[str, ...] = (), parts=None) -> Release:
    return Release(
        slug,
        InstagramPost(title="t", description="d", hashtags=("#a",)),
        tags=Tags("money-services", "other-person", "recognition", recurring=recurring),
        parts=parts,
    )


def project(root, slug, **files):
    (root / slug).mkdir(parents=True)
    for name, data in files.items():
        (root / slug / f"{name}.json").write_text(json.dumps(data))


@pytest.fixture
def loaded(tmp_path):
    document = cast_document()
    document["characters"][0]["look"]["drawing"] = [{"part": "toon-dog", "version": 1}]
    document["characters"][1]["look"]["drawing"] = [{"part": "toon-frog", "version": 1}]
    document["characters"][1]["voice"]["voice"] = "Matilda"
    saga = character("saga-juno", world="saga")
    saga["name"] = "Juno"
    document["characters"].append(saga)
    document["characters"].append(placeholder("vera"))
    return bible.load(write(tmp_path / "bible", document))


CHARACTERS = {"toon-dog", "toon-frog", "toon-bear"}


def test_a_reel_that_uses_the_bibles_names_drawings_and_voices_has_no_finding(tmp_path, loaded):
    project(tmp_path, "new-reel", narration={"voice": {"rex": {"name": "Charlie - Deep"}, "fern": {"name": "Matilda"}}})
    r = release("new-reel", recurring=("rex", "fern"), parts={"toon-dog": 1, "toon-frog": 1})
    assert bible_check.check_release(loaded, r, tmp_path, characters=CHARACTERS) == []


def test_a_name_the_bible_lacks_is_flagged_and_the_drawing_it_borrows_is_named(tmp_path, loaded):
    project(tmp_path, "new-reel", script=[{"speaker": "bruno", "text": "Hi."}])
    r = release("new-reel", parts={"toon-dog": 1})
    (finding, hint) = bible_check.check_release(loaded, r, tmp_path, characters=CHARACTERS)
    assert finding.kind == "unknown-name" and finding.message.startswith("'bruno' is not a character")
    assert "what the bible calls rex" in hint.message and "bruno" in hint.message


def test_a_known_name_with_another_drawing_is_flagged(tmp_path, loaded):
    r = release("new-reel", recurring=("rex",), parts={"toon-frog": 1})
    (finding,) = bible_check.check_release(loaded, r, tmp_path, characters=CHARACTERS)
    assert finding.kind == "drawing" and "toon-dog" in finding.message and "toon-frog" in finding.message


def test_a_character_only_heard_is_not_drawn_so_only_its_name_and_voice_are_checked(tmp_path, loaded):
    project(tmp_path, "new-reel", narration={"voice": {"rex": {"name": "Charlie - Deep"}, "fern": {"name": "Matilda"}}})
    r = release(
        "new-reel", recurring=("rex",), parts={"toon-dog": 1}
    )  # fern speaks off screen; the reel never draws her
    assert bible_check.check_release(loaded, r, tmp_path, characters=CHARACTERS) == []


def test_a_character_only_heard_is_still_refused_in_another_voice(tmp_path, loaded):
    project(
        tmp_path, "new-reel", narration={"voice": {"rex": {"name": "Charlie - Deep"}, "fern": {"name": "Liam - Young"}}}
    )
    r = release("new-reel", recurring=("rex",), parts={"toon-dog": 1})
    (finding,) = bible_check.check_release(loaded, r, tmp_path, characters=CHARACTERS)
    assert finding.kind == "voice" and "'fern'" in finding.message and "Matilda" in finding.message


def test_a_character_the_release_tags_is_still_refused_when_drawn_as_another(tmp_path, loaded):
    project(tmp_path, "new-reel", narration={"voice": {"rex": {"name": "Charlie - Deep"}, "fern": {"name": "Matilda"}}})
    r = release("new-reel", recurring=("rex", "fern"), parts={"toon-dog": 1, "toon-bear": 1})
    (finding,) = bible_check.check_release(loaded, r, tmp_path, characters=CHARACTERS)
    assert finding.kind == "drawing" and "'fern'" in finding.message and "toon-frog" in finding.message


def test_a_part_that_draws_any_figure_never_explains_a_name_so_a_drawn_speaker_is_still_flagged(tmp_path, loaded):
    project(tmp_path, "new-reel", narration={"voice": {"rex": {"name": "Charlie - Deep"}, "fern": {"name": "Matilda"}}})
    r = release("new-reel", recurring=("rex",), parts={"toon-dog": 1})
    (finding,) = bible_check.check_release(loaded, r, tmp_path, characters=CHARACTERS, rigs={"toon-dog"})
    assert finding.kind == "drawing" and "'fern'" in finding.message  # the rig could be drawing fern too


def test_the_rigs_are_the_registered_parts_of_the_stick_style():
    assert {"stick-rig", "stick-figure"} <= bible_check.rig_parts()
    assert "toon-dog" not in bible_check.rig_parts()


def test_a_known_name_in_another_voice_is_flagged(tmp_path, loaded):
    project(tmp_path, "new-reel", narration={"voice": {"rex": {"name": "Liam - Young"}}})
    (finding,) = bible_check.check_release(loaded, release("new-reel", recurring=("rex",)), tmp_path)
    assert finding.kind == "voice" and "Charlie" in finding.message and "Liam" in finding.message


def test_a_voice_the_bible_has_not_settled_is_not_a_finding(tmp_path):
    document = cast_document()
    document["characters"][0]["voice"]["voice"] = "open: which voice?"
    document["characters"][0]["canon"] = [f for f in document["characters"][0]["canon"] if f["field"] != "voice.voice"]
    got = bible.load(write(tmp_path / "bible", document))
    project(tmp_path, "new-reel", narration={"voice": {"rex": {"name": "Liam - Young"}}})
    assert bible_check.check_release(got, release("new-reel", recurring=("rex",)), tmp_path) == []


def test_an_unnamed_role_the_bible_lists_is_not_a_name(tmp_path, loaded):
    project(tmp_path, "new-reel", script=[{"speaker": "narrator", "text": "Once."}])
    assert bible_check.check_release(loaded, release("new-reel"), tmp_path) == []


def test_a_sealed_world_shares_no_canon_so_a_name_from_another_world_is_flagged(tmp_path, loaded):
    r = release("saga-new", recurring=("rex", "juno"))
    (finding,) = bible_check.check_release(loaded, r, tmp_path)
    assert finding.kind == "world" and "'rex'" in finding.message and "okayville only" in finding.message


def test_the_same_name_in_its_own_world_is_the_one_the_bible_means(tmp_path, loaded):
    assert bible_check.check_release(loaded, release("saga-new", recurring=("juno",)), tmp_path) == []


def test_a_release_with_no_project_yet_is_checked_by_its_tags_alone(tmp_path, loaded):
    (finding,) = bible_check.check_release(loaded, release("new-reel", recurring=("ghost",)), tmp_path)
    assert finding.kind == "unknown-name"


def test_a_brief_must_cite_the_bible_with_a_cast_line(tmp_path, loaded):
    (finding,) = bible_check.check_brief(loaded, "Rex calls Fern about the fence.")
    assert finding.kind == "cast-line" and "Cast:" in finding.message
    assert bible_check.check_brief(loaded, "Cast: rex, fern\nWorld: okayville\n\nA scene.") == []


def test_a_brief_that_cites_a_character_the_bible_lacks_or_one_of_another_world_is_flagged(tmp_path, loaded):
    findings = bible_check.check_brief(loaded, "Cast: rex, ghost, saga-juno\nWorld: okayville", where="brief.md")
    assert [(f.kind, f.message.split()[0]) for f in findings] == [("unknown-name", "'ghost'"), ("world", "'saga-juno'")]
    assert all(f.where == "brief.md" for f in findings)


def test_an_empty_cast_line_and_an_unknown_world_are_flagged(tmp_path, loaded):
    kinds = {f.kind for f in bible_check.check_brief(loaded, "Cast:  ,\nWorld: narnia")}
    assert kinds == {"cast-line", "world"}


def test_refusing_names_every_finding_and_is_a_delivery_error(tmp_path, loaded):
    findings = {
        "a": [bible_check.Finding("a", "voice", "x")],
        "b": [bible_check.Finding("b", "drawing", "y"), bible_check.Finding("b", "unknown-name", "z")],
    }
    with pytest.raises(bible_check.BibleCheckError, match="a: voice: x; b: drawing: y; b: unknown-name: z") as raised:
        bible_check.refuse(findings)
    assert isinstance(raised.value, DeliveryError) and len(raised.value.findings) == 3
    bible_check.refuse({"a": []})  # nothing found, nothing raised

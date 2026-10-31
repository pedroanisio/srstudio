"""The inventory counts, by code, who is named or drawn in which published reel (ADR 0069).

The sources are four and each is checked on its own: the release's ``recurring`` tags, the speakers a project's data
files record, the names the caption writes in capitals, and the characters the release pins as drawn.
"""

import json
from pathlib import Path

import pytest

from srstudio import bible_inventory as inv
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost


def release(slug: str, *, recurring: tuple[str, ...] = (), description: str = "A sketch.", parts=None) -> Release:
    return Release(
        slug,
        InstagramPost(title=f"{slug} title", description=description, hashtags=("#a",)),
        tags=Tags("money-services", "other-person", "recognition", recurring=recurring),
        parts=parts,
    )


def project(root: Path, slug: str, **files: object) -> Path:
    folder = root / slug
    folder.mkdir(parents=True)
    for name, data in files.items():
        (folder / f"{name}.json").write_text(json.dumps(data))
    return folder


def test_a_world_is_read_from_the_slug_prefix_of_the_sealed_series():
    assert inv.world_of("saga-update") == "saga"
    assert inv.world_of("gloss-exit") == "gloss"
    assert inv.world_of("cup-fee") == "okayville"
    assert inv.world_of("sagas-fine") == "okayville"  # a prefix is a whole word


def test_the_published_set_is_the_delivery_manifest_and_nothing_else(tmp_path):
    manifest = tmp_path / "outbox.json"
    manifest.write_text(json.dumps({"version": "1.0.0", "videos": {"cup-fee": {}, "tip-screen": {}}}))
    assert inv.published(manifest) == frozenset({"cup-fee", "tip-screen"})


@pytest.mark.parametrize(
    "document",
    ["not json", "[]", json.dumps({"videos": []}), json.dumps({"version": "1.0.0"}), json.dumps({"videos": {"": {}}})],
)
def test_a_manifest_that_cannot_be_trusted_is_refused(tmp_path, document):
    manifest = tmp_path / "outbox.json"
    manifest.write_text(document)
    with pytest.raises(inv.InventoryError, match="outbox.json"):
        inv.published(manifest)


def test_a_missing_manifest_is_refused_not_read_as_nothing_published(tmp_path):
    with pytest.raises(inv.InventoryError, match="cannot read"):
        inv.published(tmp_path / "outbox.json")


def test_speakers_come_from_every_shape_a_project_records_and_variants_fold_into_the_name(tmp_path):
    project(
        tmp_path,
        "a",
        script=[{"speaker": "rex-off", "text": "x"}, {"speaker": "fern-low"}, {"text": "no speaker"}],
        narration={
            "voice": {"rex": {"voice_id": "i", "name": "Charlie - Deep, Confident"}, "fern": {"name": "Matilda"}}
        },
    )
    project(tmp_path, "b", dialogue={"phrases": [{"role": "manager", "voice_name": "Eric"}, {"role": "candidate"}]})
    project(tmp_path, "c", timeline={"voices": {"a": {"name": "Roger - Laid-Back"}}, "items": [{"actor": "a"}]})
    assert inv.speakers(tmp_path / "a") == {"rex": "Charlie", "fern": "Matilda"}
    assert inv.speakers(tmp_path / "b") == {"manager": "Eric", "candidate": ""}
    assert inv.speakers(tmp_path / "c") == {"a": "Roger"}


def test_a_flat_voice_record_is_not_read_as_three_speakers_called_voice_id_name_category(tmp_path):
    project(tmp_path, "a", narration={"voice": {"voice_id": "i", "name": "Rachel", "category": "premade"}})
    assert inv.speakers(tmp_path / "a") == {}


@pytest.mark.parametrize("document", ["not json", "[1, 2]", '{"voice": 3}', '{"voice": {"x": 3}}'])
def test_a_project_file_that_is_not_what_it_claims_is_a_typed_error(tmp_path, document):
    folder = project(tmp_path, "a")
    (folder / "narration.json").write_text(document)
    with pytest.raises(inv.InventoryError, match="narration.json"):
        inv.speakers(folder)


def test_a_project_with_no_data_file_has_no_speakers(tmp_path):
    assert inv.speakers(project(tmp_path, "a")) == {}


def test_the_caption_names_are_the_capitalised_words_of_the_vocabulary_not_the_lowercase_ones():
    text = "Ava and Milo from Tip Screen. The rex of the hour, and a fern on the sill."
    assert inv.mentions(text, {"ava", "milo", "rex", "fern", "tip"}) == {"ava", "milo", "tip"}


def test_a_name_inside_a_longer_word_is_not_a_mention():
    assert inv.mentions("Avatar and Milos", {"ava", "milo"}) == set()


def test_the_collected_reel_joins_the_four_sources(tmp_path):
    project(tmp_path, "cup-fee", script=[{"speaker": "ava"}])
    releases = {
        "cup-fee": release(
            "cup-fee",
            recurring=("milo",),
            description="Ava and Milo at the counter.",
            parts={"barista": 1, "toon-desk": 1},
        )
    }
    (reel,) = inv.collect(
        releases,
        frozenset({"cup-fee"}),
        tmp_path,
        characters=frozenset({"barista"}),
        vocabulary=frozenset({"ava", "milo"}),
    )
    assert reel.world == "okayville"
    assert reel.tagged == {"milo"} and reel.spoke == {"ava"} and reel.named == {"ava", "milo"}
    assert reel.drawn == {"barista"}


def test_only_published_reels_are_collected_and_a_published_slug_with_no_release_is_ignored(tmp_path):
    releases = {"a": release("a"), "pilot": release("pilot")}
    reels = inv.collect(releases, frozenset({"a", "gone"}), tmp_path, characters=frozenset(), vocabulary=frozenset())
    assert [r.slug for r in reels] == ["a"]


def test_the_vocabulary_is_every_tagged_and_spoken_name_of_the_published_reels(tmp_path):
    project(tmp_path, "a", script=[{"speaker": "gary"}])
    releases = {"a": release("a", recurring=("rosa",)), "b": release("b", recurring=("kai",))}
    assert inv.vocabulary(releases, frozenset({"a"}), tmp_path) == {"gary", "rosa"}


def test_a_candidate_is_counted_once_per_reel_however_many_sources_name_it(tmp_path):
    project(tmp_path, "a", script=[{"speaker": "rex"}])
    project(tmp_path, "b")
    releases = {
        "a": release("a", recurring=("rex",), description="Rex calls."),
        "b": release("b", description="Rex again."),
    }
    published = frozenset(releases)
    reels = inv.collect(
        releases, published, tmp_path, characters=frozenset(), vocabulary=inv.vocabulary(releases, published, tmp_path)
    )
    (rex,) = [c for c in inv.candidates(reels) if c.name == "rex"]
    assert rex.reels == ("a", "b") and rex.recurring
    assert rex.sources["a"] == frozenset({"tag", "speaker", "caption"})
    assert rex.sources["b"] == frozenset({"caption"})


def test_the_threshold_decides_who_recurs_and_one_reel_never_does(tmp_path):
    project(tmp_path, "a", script=[{"speaker": "rex"}, {"speaker": "fern"}])
    project(tmp_path, "b", script=[{"speaker": "rex"}])
    releases = {"a": release("a"), "b": release("b")}
    reels = inv.collect(releases, frozenset(releases), tmp_path, characters=frozenset(), vocabulary=frozenset())
    got = {c.name: c.recurring for c in inv.candidates(reels, threshold=2)}
    assert got == {"rex": True, "fern": False}
    with pytest.raises(inv.InventoryError, match="threshold"):
        inv.candidates(reels, threshold=0)


def test_a_name_with_two_voices_or_two_drawings_is_reported_as_a_clash(tmp_path):
    project(tmp_path, "a", narration={"voice": {"rex": {"name": "Charlie - Deep"}}})
    project(tmp_path, "b", narration={"voice": {"rex": {"name": "Liam - Young"}}})
    releases = {"a": release("a", parts={"toon-dog": 1}), "b": release("b", parts={"stick-rig": 1})}
    reels = inv.collect(
        releases, frozenset(releases), tmp_path, characters=frozenset({"toon-dog", "stick-rig"}), vocabulary=frozenset()
    )
    (rex,) = inv.candidates(reels)
    assert rex.voices == {"Charlie": ("a",), "Liam": ("b",)}
    assert inv.clashes(rex) == ["voice: Charlie in a; Liam in b", "drawing: toon-dog in a; stick-rig in b"]


def test_one_voice_in_every_reel_is_not_a_clash(tmp_path):
    project(tmp_path, "a", narration={"voice": {"rex": {"name": "Charlie - Deep"}}})
    project(tmp_path, "b", narration={"voice": {"rex": {"name": "Charlie - Deep"}}})
    releases = {"a": release("a"), "b": release("b")}
    reels = inv.collect(releases, frozenset(releases), tmp_path, characters=frozenset(), vocabulary=frozenset())
    (rex,) = inv.candidates(reels)
    assert inv.clashes(rex) == []


def test_a_quoted_line_is_found_in_the_lines_the_captions_and_the_post_of_that_reel_only(tmp_path):
    project(
        tmp_path,
        "a",
        script=[{"speaker": "rex", "text": "Best money you\u2019ll ever spend!", "caption": "Best money"}],
    )
    project(tmp_path, "b", script=[{"speaker": "rex", "text": "Another line."}])
    releases = {"a": release("a", description="Fern paid the fee."), "b": release("b")}
    ask = dict(releases=releases, published_slugs=frozenset({"a", "b"}), episodes=tmp_path)
    assert inv.cite("a", "line", "best money you'll ever  SPEND", **ask) is None  # case, spacing and the curly quote
    assert inv.cite("a", "line", "Fern paid the fee", **ask) is None  # the post's description
    assert "no line says" in inv.cite("b", "line", "best money", **ask)  # said in another reel
    assert "empty quotation" in inv.cite("a", "line", "  ", **ask)


def test_a_citation_of_a_reel_that_is_not_published_or_has_no_release_fails(tmp_path):
    project(tmp_path, "a", script=[{"speaker": "rex", "text": "Hello."}])
    ask = dict(releases={"a": release("a")}, published_slugs=frozenset({"a"}), episodes=tmp_path)
    assert "not a published reel" in inv.cite("pilot", "line", "Hello.", **ask)
    assert "not a published reel" in inv.cite("a", "line", "Hello.", **{**ask, "published_slugs": frozenset()})


def test_a_drawing_and_a_voice_are_cited_by_what_the_release_pins_and_the_project_records(tmp_path):
    project(tmp_path, "a", narration={"voice": {"rex": {"name": "Charlie - Deep"}}})
    ask = dict(
        releases={"a": release("a", parts={"toon-dog": 1, "toon-desk": 1})},
        published_slugs=frozenset({"a"}),
        episodes=tmp_path,
    )
    assert inv.cite("a", "drawn", "toon-dog", characters={"toon-dog"}, **ask) is None
    assert "not a character it draws" in inv.cite("a", "drawn", "toon-desk", characters={"toon-dog"}, **ask)  # a prop
    assert "not a character it draws" in inv.cite("a", "drawn", "toon-frog", characters={"toon-frog"}, **ask)
    assert inv.cite("a", "voice", "Charlie", **ask) is None
    assert "no voice 'Matilda'" in inv.cite("a", "voice", "Matilda", **ask)


def test_what_was_seen_in_a_render_cannot_be_confirmed_by_code_and_is_never_accepted_silently(tmp_path):
    ask = dict(releases={"a": release("a")}, published_slugs=frozenset({"a"}), episodes=tmp_path)
    assert "cannot be confirmed" in inv.cite("a", "seen", "green sweater", **ask)
    assert "cannot be confirmed" in inv.cite("a", "anything", "x", **ask)


def commit(repo: Path, name: str, when: str) -> None:
    import subprocess

    (repo / name).write_text("x = 1\n")
    env = {
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
        "PATH": __import__("os").environ["PATH"],
    }
    subprocess.run(["git", "-C", str(repo), "add", name], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", name], check=True, env=env)


def test_reels_are_ordered_by_the_commit_that_added_their_release_file(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commit(tmp_path, "later_one.py", "2020-01-02T00:00:00+0000")
    commit(tmp_path, "first_one.py", "2020-01-01T00:00:00+0000")
    releases = {s: release(s) for s in ("first-one", "later-one", "uncommitted")}
    assert inv.added_order(tmp_path, releases) == ["first-one", "later-one", "uncommitted"]


def test_the_order_of_a_folder_that_is_not_a_repository_is_a_typed_error(tmp_path):
    with pytest.raises(inv.InventoryError, match="cannot read the commit order"):
        inv.added_order(tmp_path / "nowhere", {})

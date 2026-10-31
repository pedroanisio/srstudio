"""A persona changes only under a new version with a changelog section; the lock refuses all else (ADR 0069)."""

import json

import pytest

from srstudio import bible_lock
from support.bible_docs import cast_document, character, locked, pair, pairs_document, write


def edit(folder, mutate, *, version=None):
    cast = json.loads((folder / "cast.json").read_text())
    pairs = json.loads((folder / "relationships.json").read_text())
    mutate(cast, pairs)
    for document in (cast, pairs):
        if version:
            document["version"] = version
    (folder / "cast.json").write_text(json.dumps(cast))
    (folder / "relationships.json").write_text(json.dumps(pairs))


def changelog(folder, *versions):
    text = "# Changelog\n\n" + "".join(f"## {v}\n\nA change.\n\n" for v in versions)
    (folder / "CHANGELOG.md").write_text(text)


def test_a_locked_bible_has_no_problem_and_locking_it_again_changes_nothing(tmp_path):
    folder = locked(tmp_path / "bible")
    assert bible_lock.problems(folder) == []
    before = (folder / "lock.json").read_text()
    assert bible_lock.write(folder) > 0 and (folder / "lock.json").read_text() == before


def test_editing_a_persona_without_a_new_version_is_named_and_refused(tmp_path):
    folder = locked(tmp_path / "bible")
    edit(folder, lambda c, p: c["characters"][0]["look"].update(palette="grey and green"))
    found = bible_lock.problems(folder)
    assert found == [
        f"character:{json.loads((folder / 'cast.json').read_text())['characters'][0]['slug']}: "
        "changed without a version bump (locked 1.0.0)"
    ]
    with pytest.raises(bible_lock.LockError, match="changed without a version bump"):
        bible_lock.check(folder)
    with pytest.raises(bible_lock.LockError, match="changed without a version bump"):
        bible_lock.write(folder)  # locking cannot bless the drift


def test_a_new_pair_or_character_without_a_new_version_is_refused(tmp_path):
    folder = locked(tmp_path / "bible")
    edit(
        folder, lambda c, p: (c["characters"].append(character("sam")), p["relationships"].append(pair("fern", "sam")))
    )
    found = bible_lock.problems(folder)
    assert "character:sam: added without a version bump (locked 1.0.0)" in found
    assert "pair:fern+sam: added without a version bump (locked 1.0.0)" in found


def test_removing_a_record_is_refused_without_a_new_version(tmp_path):
    folder = locked(tmp_path / "bible")
    edit(folder, lambda c, p: p.update(relationships=[]))
    assert bible_lock.problems(folder) == ["pair:fern+rex: removed without a version bump (locked 1.0.0)"]


def test_a_new_version_needs_its_changelog_section_and_a_fresh_lock(tmp_path):
    folder = locked(tmp_path / "bible")
    edit(folder, lambda c, p: c["characters"][0]["look"].update(palette="grey"), version="1.0.1")
    found = bible_lock.problems(folder)
    assert any("no '## 1.0.1' section" in p for p in found)
    assert any("the bible is version 1.0.1 and the lock 1.0.0; run srstudio bible lock" in p for p in found)
    with pytest.raises(bible_lock.LockError, match="no '## 1.0.1' section"):
        bible_lock.write(folder)
    changelog(folder, "1.0.1", "1.0.0")
    bible_lock.write(folder)
    assert bible_lock.problems(folder) == []


def test_a_new_record_needs_a_minor_version_and_a_correction_may_be_a_patch(tmp_path):
    folder = locked(tmp_path / "bible")
    changelog(folder, "1.0.1", "1.0.0")
    edit(folder, lambda c, p: c["characters"].append(character("sam")), version="1.0.1")
    with pytest.raises(bible_lock.LockError, match="character:sam: a new record needs a minor version, not a patch"):
        bible_lock.write(folder)
    changelog(folder, "1.1.0", "1.0.0")
    edit(folder, lambda c, p: None, version="1.1.0")
    bible_lock.write(folder)
    assert bible_lock.problems(folder) == []


def test_a_version_below_the_lock_is_refused(tmp_path):
    folder = locked(tmp_path / "bible")
    edit(folder, lambda c, p: None, version="0.9.0")
    changelog(folder, "0.9.0")
    assert any("below the locked 1.0.0" in p for p in bible_lock.problems(folder))


def test_a_missing_or_malformed_lock_is_a_problem_not_a_pass(tmp_path):
    folder = write(tmp_path / "bible")
    changelog(folder, "1.0.0")
    assert "cannot read" in bible_lock.problems(folder)[0]
    (folder / "lock.json").write_text("{not json")
    assert "cannot read" in bible_lock.problems(folder)[0]
    (folder / "lock.json").write_text(json.dumps({"schema": "1.0.0", "version": "1.0.0", "digests": {}, "extra": 1}))
    assert "exactly schema, version and digests" in bible_lock.problems(folder)[0]
    (folder / "lock.json").write_text(json.dumps({"schema": "1.0.0", "version": "1.0.0", "digests": {"a": "xyz"}}))
    assert "sha256 hex digest" in bible_lock.problems(folder)[0]
    (folder / "lock.json").write_text(json.dumps({"schema": "2.0.0", "version": "1.0.0", "digests": {}}))
    assert "schema '2.0.0'" in bible_lock.problems(folder)[0]
    with pytest.raises(bible_lock.LockError):
        bible_lock.check(folder)


def test_a_first_lock_needs_a_changelog_section(tmp_path):
    folder = write(tmp_path / "bible")
    with pytest.raises(bible_lock.LockError, match="CHANGELOG.md cannot be read"):
        bible_lock.write(folder)
    changelog(folder, "0.9.0")
    with pytest.raises(bible_lock.LockError, match="no '## 1.0.0' section"):
        bible_lock.write(folder)
    changelog(folder, "1.0.0")
    assert bible_lock.write(folder) == len(bible_lock.digests(folder)[1])


def test_a_record_with_no_key_cannot_be_locked(tmp_path):
    folder = write(tmp_path / "bible", cast={**cast_document(), "places": [{"name": "no slug"}]})
    with pytest.raises(bible_lock.LockError, match="places\\[0\\] has no slug"):
        bible_lock.digests(folder)
    pairs = pairs_document()
    pairs["relationships"] = [{"a": "fern"}]
    folder = write(tmp_path / "other", pairs=pairs)
    with pytest.raises(bible_lock.LockError, match="no a and b"):
        bible_lock.digests(folder)

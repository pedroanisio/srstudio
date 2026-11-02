"""The delivery gate of the anatomy rules and its listing (ADR 0146)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from srstudio import anatomy_gate, anatomy_ledger, cli, text_rules
from srstudio.anatomy_gate import hand_defects
from srstudio.anatomy_ledger import HAND_NO_SIDE, HAND_UNPAIRED, Exemption, ExemptionError, Note
from srstudio.releases import Release
from srstudio.social import Drift, InstagramPost

POST = InstagramPost(title="t", description="d")
FAULT = Note(HAND_UNPAIRED, "news-gus", "version 3 draws one hand on both arms: use a paired version")
FIRST = {"a-b": "The_Video"}


@pytest.fixture
def reels(tmp_path):
    release = Release("a-b", POST, video="The_Video")
    project = tmp_path / "a-b"
    project.mkdir()
    (project / release.scene_file).write_bytes(b"<scene/>")
    return {"a-b": release}, tmp_path


def test_a_clean_record_passes(reels):
    releases, episodes = reels
    anatomy_ledger.write(episodes / "a-b", [])
    assert hand_defects(releases, episodes, FIRST) == []


def test_a_note_stands_against_a_first_delivery(reels):
    releases, episodes = reels
    anatomy_ledger.write(episodes / "a-b", [FAULT])
    assert hand_defects(releases, episodes, FIRST) == [Drift("The_Video", f"anatomy: {FAULT}")]


def test_a_row_of_the_list_does_not_excuse_a_first_delivery(reels, monkeypatch):
    releases, episodes = reels
    row = Exemption("a-b", HAND_UNPAIRED, "news-gus", "published with it")
    monkeypatch.setattr(anatomy_ledger, "exemptions", lambda: (row,))
    anatomy_ledger.write(episodes / "a-b", [FAULT])
    assert len(hand_defects(releases, episodes, FIRST)) == 1


def test_a_scene_built_before_the_rule_is_refused(reels):
    releases, episodes = reels
    [drift] = hand_defects(releases, episodes, FIRST)
    assert "anatomy.json is missing" in drift.reason


def test_a_reel_already_delivered_meets_no_gate(reels):
    releases, episodes = reels
    anatomy_ledger.write(episodes / "a-b", [FAULT])
    assert hand_defects(releases, episodes, {}) == []


def test_a_project_with_no_scene_has_nothing_to_judge(tmp_path):
    release = Release("a-b", POST, video="The_Video")
    (tmp_path / "a-b").mkdir()
    assert hand_defects({"a-b": release}, tmp_path, FIRST) == []


def test_a_broken_record_is_refused(reels):
    releases, episodes = reels
    (episodes / "a-b" / anatomy_ledger.RECORD).write_text("{}", encoding="utf-8")
    with pytest.raises(ExemptionError):
        hand_defects(releases, episodes, FIRST)


def test_the_listing_names_every_row_and_flags_one_not_published():
    rows = [Exemption("a-b", HAND_NO_SIDE, "collage-arm", "w"), Exemption("c-d", HAND_NO_SIDE, "collage-arm", "w")]
    lines = anatomy_gate.listing(rows, {"a-b"})
    assert lines == [
        "a-b  hand-no-side  collage-arm  w",
        "c-d  hand-no-side  collage-arm  w  (NOT PUBLISHED)",
        "2 exemptions",
    ]


def _manifest(path: Path, *videos: str) -> Path:
    path.write_text(json.dumps({"videos": dict.fromkeys(videos, {})}), encoding="utf-8")
    return path


def test_published_reads_every_manifest(tmp_path):
    one, two = _manifest(tmp_path / "a.json", "a-b"), _manifest(tmp_path / "b.json", "c-d")
    assert anatomy_gate.published([one, two]) == {"a-b", "c-d"}


def test_a_manifest_that_cannot_be_read_is_refused(tmp_path):
    with pytest.raises(ExemptionError):
        anatomy_gate.published([tmp_path / "gone.json"])


def test_the_command_lists_the_closed_list(tmp_path, capsys):
    rows = (*anatomy_ledger.exemptions(), *text_rules.exemptions())
    manifest = _manifest(tmp_path / "m.json", *{row.reel for row in rows})
    assert cli.main(["anatomy", "--manifest", str(manifest)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == f"{len(rows)} exemptions"
    assert not any("NOT PUBLISHED" in line for line in out)


def test_the_command_fails_on_a_manifest_it_cannot_read(tmp_path, capsys):
    assert cli.main(["anatomy", "--manifest", str(tmp_path / "gone.json")]) == 2
    assert "srstudio anatomy" in capsys.readouterr().err

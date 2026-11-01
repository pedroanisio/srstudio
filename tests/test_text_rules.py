"""Rule 7: a caption does not run across a sentence end (ADR 0146)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from srstudio import anatomy_ledger, text_rules
from srstudio.anatomy_ledger import Exemption, ExemptionError
from srstudio.episode import Episode, EpisodeSpec
from srstudio.frame_gates import FrameGateError, RunTogether, broken_off
from srstudio.releases import Release
from srstudio.sample import Line, write_sample_project
from srstudio.social import InstagramPost
from srstudio.text_rules import CAPTION_RUN, TextRefusedError

LINES = ["Take it.", "Whatever you say."]
POST = InstagramPost(title="t", description="d")


def scene(*windows: str) -> bytes:
    texts = "".join(f'<text id="t{i}" text="{w}"/><layer asset="t{i}"/>' for i, w in enumerate(windows))
    return f"<scene><composition>{texts}</composition></scene>".encode()


def project(tmp_path: Path, lines: list[str] = LINES) -> Path:
    (tmp_path / "voice-transcript.json").write_text(
        json.dumps({"lines": [{"expected": line} for line in lines]}), encoding="utf-8"
    )
    return tmp_path


def test_a_window_that_drops_the_stop_is_a_fault(tmp_path):
    [note] = text_rules.caption_notes(scene("Take it Whatever"), project(tmp_path))
    assert note.rule == CAPTION_RUN and note.part == "Take it Whatever"


def test_a_window_that_keeps_the_stop_and_breaks_off_is_a_fault(tmp_path):
    [note] = text_rules.caption_notes(scene("Take it. Whatever"), project(tmp_path))
    assert note.part == "Take it. Whatever"


def test_a_window_with_both_faults_is_noted_once(tmp_path):
    notes = text_rules.caption_notes(scene("Take it Whatever"), project(tmp_path))
    assert len(notes) == 1


def test_a_window_of_whole_sentences_is_not(tmp_path):
    assert text_rules.caption_notes(scene("Take it. Whatever you say."), project(tmp_path)) == []


def test_each_sentence_in_its_own_window_is_not(tmp_path):
    assert text_rules.caption_notes(scene("Take it.", "Whatever you say."), project(tmp_path)) == []


def test_a_silent_reel_has_nothing_to_compare(tmp_path):
    assert text_rules.caption_notes(scene("Take it Whatever"), tmp_path) == []


def test_a_transcript_that_is_not_one_stops_the_rule_with_its_error(tmp_path):
    (tmp_path / "voice-transcript.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FrameGateError):
        text_rules.caption_notes(scene("Take it Whatever"), tmp_path)


def test_broken_off_names_the_last_sentence_end_it_crossed():
    lines = ["Meetings have been reduced to one.", "It is this one, and it does not end."]
    window = "Meetings have been reduced to one. It is"
    assert broken_off(scene(window), lines) == [RunTogether(window, "one.", "It")]


def test_a_stop_that_is_kept_and_a_last_word_that_trails_off_is_a_whole_window():
    assert broken_off(scene("Take it. Whatever..."), LINES) == []


def test_a_window_stripped_of_its_last_stop_is_still_whole():
    assert broken_off(scene("Take it. Whatever you say"), LINES) == []


def test_a_window_with_no_sentence_end_in_it_is_not_broken_off():
    assert broken_off(scene("Whatever you"), LINES) == []


def test_a_new_reel_is_refused(tmp_path):
    with pytest.raises(TextRefusedError, match="caption-run on Take it Whatever"):
        text_rules.refuse_captions("a-new-reel", scene("Take it Whatever"), project(tmp_path))


def test_a_listed_window_of_its_reel_builds_and_no_other(tmp_path, monkeypatch):
    row = Exemption("old-reel", CAPTION_RUN, "Take it Whatever", "published with it")
    monkeypatch.setattr(text_rules, "exemptions", lambda: (row,))
    text_rules.refuse_captions("old-reel", scene("Take it Whatever"), project(tmp_path))
    with pytest.raises(TextRefusedError):
        text_rules.refuse_captions("other-reel", scene("Take it Whatever"), project(tmp_path))
    with pytest.raises(TextRefusedError):
        text_rules.refuse_captions("old-reel", scene("Take it Whatever", "Take it. Whatever"), project(tmp_path))


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    write_sample_project(root, [Line("v", "Take it.", 1000)], angles=["wide"])
    return root


def _episode(root: Path, slug: str) -> Episode:
    episode = Episode(
        EpisodeSpec(slug=slug, title="t", description="t", root=root, seed=1, background="#D5DFDF", signature=False)
    )
    episode.cv.assets.add_text(id="said", text="Take it Whatever", width=200, height=80, size="40")
    episode.comp.add_layer(id="said-layer", asset="said", x=0, y=0)
    return episode


def test_the_build_refuses_before_it_writes_a_scene(project_dir, tmp_path):
    project(project_dir)
    out = tmp_path / "a-new-reel.scene.xml"
    with pytest.raises(TextRefusedError, match="a-new-reel"):
        _episode(project_dir, "a-new-reel").finish(out=out)
    assert not out.exists()


def test_a_published_reel_on_the_list_still_rebuilds(project_dir, tmp_path, monkeypatch):
    project(project_dir)
    row = Exemption("old-reel", CAPTION_RUN, "Take it Whatever", "published with it")
    monkeypatch.setattr(text_rules, "exemptions", lambda: (row,))
    assert _episode(project_dir, "old-reel").finish(out=tmp_path / "old-reel.scene.xml").is_file()


def test_a_first_delivery_answers_for_a_window_that_breaks_off(tmp_path):
    root = tmp_path / "a-b"
    root.mkdir()
    project(root)
    (root / "a-b.scene.xml").write_bytes(scene("Take it. Whatever"))
    release = Release("a-b", POST, video="The_Video")
    [drift] = text_rules.caption_defects({"a-b": release}, tmp_path, {"a-b": "The_Video"})
    assert drift.name == "The_Video" and "breaks off" in drift.reason


def test_a_first_delivery_lists_no_row_of_the_closed_list(tmp_path, monkeypatch):
    root = tmp_path / "a-b"
    root.mkdir()
    project(root)
    (root / "a-b.scene.xml").write_bytes(scene("Take it. Whatever"))
    row = Exemption("a-b", CAPTION_RUN, "Take it. Whatever", "published with it")
    monkeypatch.setattr(text_rules, "exemptions", lambda: (row,))
    assert text_rules.caption_defects({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"})


def test_a_project_with_no_scene_has_nothing_to_read(tmp_path):
    assert text_rules.caption_defects({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"}) == []


def test_the_delivery_gate_runs_the_rule():
    source = (Path(__file__).resolve().parent.parent / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert "text_rules.caption_defects(chosen, _beside(renders), first)" in source
    assert "frame_gates.captions_run_together(chosen, _beside(renders), first)" in source


def test_the_list_is_closed_to_other_rules():
    text = json.dumps(
        {"schema": "1.0.0", "exemptions": [{"reel": "a", "rule": "hand-no-arm", "part": "p", "why": "w"}]}
    )
    with pytest.raises(ExemptionError):
        text_rules.parse(text)


def test_every_row_of_the_list_is_read():
    assert all(row.why.strip() for row in text_rules.exemptions())


def test_a_reel_pulled_from_the_queue_is_not_published_and_not_on_the_list():
    pulled = {"take-my-phone", "what-my-dad-does", "gloss-fewer-meetings"}
    assert not pulled & {row.reel for row in text_rules.exemptions()}


def test_the_anatomy_list_is_still_closed_to_these_rules():
    text = json.dumps({"schema": "1.0.0", "exemptions": [{"reel": "a", "rule": CAPTION_RUN, "part": "p", "why": "w"}]})
    with pytest.raises(ExemptionError):
        anatomy_ledger.parse_exemptions(text)

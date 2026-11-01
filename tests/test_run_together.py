"""Burned captions that run across a sentence end, read from the scene against the reel's sentences (ADR 0073)."""

import json
from pathlib import Path

import pytest

from srstudio import frame_gates
from srstudio.frame_gates import FrameGateError, RunTogether, run_together, sentences_of
from srstudio.releases import Release
from srstudio.social import InstagramPost

POST = InstagramPost(title="t", description="d")
SENTENCES = ["Take it. Whatever I say. Do not let me text him.", "Just to say happy birthday."]


def scene(*windows: str, cues: tuple[str, ...] = ()) -> bytes:
    """A scene burning each window as a text layer, and each of ``cues`` on a burned track."""
    texts = "".join(f'<text id="t{i}" text="{w}"/>' for i, w in enumerate(windows))
    layers = "".join(f'<layer id="l{i}" asset="t{i}"/>' for i in range(len(windows)))
    track = "".join(f'<cue start="0" end="1" text="{c}"/>' for c in cues)
    caption = f'<captionTrack id="c">{track}</captionTrack>'
    return f"<scene><assets>{texts}</assets><group>{layers}</group>{caption}</scene>".encode()


def test_a_window_across_a_sentence_end_is_named_with_its_words():
    found = run_together(scene("Take it Whatever", "I say Do not let", "me text him"), SENTENCES)
    assert found == [RunTogether("Take it Whatever", "it", "Whatever"), RunTogether("I say Do not let", "say", "Do")]


def test_the_words_split_over_two_lines_of_a_window_still_run_together():
    assert run_together(scene("home&#10;He wears a tie"), ["My dad works from home. He wears a tie."]) == [
        RunTogether("home He wears a tie", "home", "He")
    ]


def test_windows_that_break_at_the_sentence_ends_pass():
    assert run_together(scene("Take it", "Whatever I say", "Do not let", "me text him"), SENTENCES) == []


def test_a_window_that_keeps_its_stop_is_read_as_two_sentences():
    assert run_together(scene("Take it. Whatever", "I say! Do not"), SENTENCES) == []


def test_the_end_of_one_line_runs_into_the_next_line():
    assert run_together(scene("text him Just to say"), SENTENCES) == [
        RunTogether("text him Just to say", "him", "Just")
    ]


def test_a_burned_track_is_read_like_layers():
    assert run_together(scene(cues=("Take it Whatever", "I say")), SENTENCES) == [
        RunTogether("Take it Whatever", "it", "Whatever")
    ]


def test_capitals_and_curly_apostrophes_do_not_hide_a_run_on():
    found = run_together(scene("IT\u2019S FINE NO"), ["It's fine. No."])
    assert found == [RunTogether("IT\u2019S FINE NO", "FINE", "NO")]


def test_an_abbreviation_or_an_initial_is_no_sentence_end():
    lines = ["Ask Dr. Patel. The U.S. Mail is late."]
    assert run_together(scene("Ask Dr Patel", "The US Mail"), lines) == []


def test_an_ellipsis_trails_off_inside_its_sentence():
    assert run_together(scene("Call your sister"), ["Call... your... sister."]) == []


def test_a_pair_the_lines_also_say_inside_a_sentence_is_not_a_run_on():
    lines = ["Brought to you by Flush.", "Flush flush, rain tomorrow."]
    assert run_together(scene("Flush flush, rain tomorrow"), lines) == []


def test_text_that_is_never_laid_out_is_not_a_window():
    document = b'<scene><assets><text id="t" text="Take it Whatever"/></assets></scene>'
    assert run_together(document, SENTENCES) == []


def test_a_document_that_is_not_a_scene_is_refused():
    with pytest.raises(FrameGateError, match="not a scene"):
        run_together(b"<scene", SENTENCES)


# -- a reel's sentences -------------------------------------------------------------------------------------------
def project(tmp_path: Path, slug: str = "a-b", *, srt: str = "", transcript: list[str] | None = None) -> Path:
    root = tmp_path / slug
    root.mkdir()
    if srt:
        (root / f"{slug}.srt").write_text(srt)
    if transcript is not None:
        lines = [{"role": "x", "expected": t, "heard": t} for t in transcript]
        (root / "voice-transcript.json").write_text(json.dumps({"lines": lines}))
    return root


def test_the_sentences_come_from_the_script_and_the_subtitles(tmp_path):
    root = project(
        tmp_path, srt="1\n00:00:00,000 --> 00:00:01,000\nOne two.\n\n2\n00:00:01,000 --> 00:00:02,000\nThree.\n",
        transcript=["Four five."],
    )  # fmt: skip
    assert sentences_of(root) == ["Four five.", "One two.", "Three."]


def test_a_silent_project_has_no_sentences(tmp_path):
    assert sentences_of(project(tmp_path)) == []


def test_a_transcript_of_the_wrong_shape_is_refused_not_skipped(tmp_path):
    root = project(tmp_path)
    (root / "voice-transcript.json").write_text('{"lines": [{"role": "x"}]}')
    with pytest.raises(FrameGateError, match="voice-transcript.json"):
        sentences_of(root)


# -- at delivery --------------------------------------------------------------------------------------------------
def built(tmp_path: Path, *windows: str) -> Path:
    root = project(tmp_path, transcript=SENTENCES)
    (root / "a-b.scene.xml").write_bytes(scene(*windows))
    return tmp_path


def test_a_reel_on_its_first_delivery_is_refused_by_name(tmp_path):
    episodes = built(tmp_path, "Take it Whatever")
    drift = frame_gates.captions_run_together({"a-b": Release("a-b", POST)}, episodes, {"a-b": "a-b"})
    assert [str(d) for d in drift] == [
        "a-b: the caption 'Take it Whatever' runs 'it' into 'Whatever' across a sentence end"
    ]


def test_a_reel_named_for_another_video_is_refused_under_the_video(tmp_path):
    episodes = built(tmp_path, "Take it Whatever")
    release = Release("a-b", POST, video="The_Video")
    assert [d.name for d in frame_gates.captions_run_together({"a-b": release}, episodes, {"a-b": "The_Video"})] == [
        "The_Video"
    ]


def test_a_delivered_reel_is_frozen_and_never_read(tmp_path):
    episodes = built(tmp_path, "Take it Whatever")
    assert frame_gates.captions_run_together({"a-b": Release("a-b", POST)}, episodes, {}) == []


def test_refuse_raises_the_typed_error_with_every_reel(tmp_path):
    episodes = built(tmp_path, "Take it Whatever")
    drift = frame_gates.captions_run_together({"a-b": Release("a-b", POST)}, episodes, {"a-b": "a-b"})
    with pytest.raises(FrameGateError, match="a-b: the caption 'Take it Whatever'") as refused:
        frame_gates.refuse(drift)
    assert refused.value.problems == tuple(drift)
    frame_gates.refuse([])

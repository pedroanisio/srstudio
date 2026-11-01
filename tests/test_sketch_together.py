"""Two voices on one beat: a line said together with the line before it, each take heard back alone."""

import json
from dataclasses import replace

import pytest

from srstudio import sketch
from srstudio.sketch import Beat, Line
from support.sketch import SK, SPEAKERS, FakeClient, confirm_stub

LINES = (Line("rex", "Tell me now."), Line("boss", "Stop."), Line("rex", "Stop."), Line("boss", "Fine then."))
TOGETHER = (*LINES[:2], replace(LINES[2], together=True), LINES[3])
BEATS = (
    Beat(0.0, "dog", LINES[0].text, "wide", "open", "desk", 0, 0),
    Beat(2.0, "dog", "Stop.", "half", "flat", "desk", 1, 0),
    Beat(3.5, "dog", "", "half", "flat", "desk"),
    Beat(5.0, "dog", LINES[3].text, "half", "flat", "desk", 3, 0),
)
BOTH = replace(SK, lines=TOGETHER, beats=BEATS, end=7.0)


def recorded(tmp_path, sk=BOTH):
    client = FakeClient(tmp_path)
    return sketch.record(sk, tmp_path / "p", client, confirm=confirm_stub, ffmpeg="ffmpeg"), client


def test_a_line_said_together_needs_no_beat_of_its_own_and_shares_the_span_of_the_line_it_joins():
    sketch.check(BOTH)
    assert sketch.line_spans(BOTH) == [(0.0, 2.0), (2.0, 5.0), (2.0, 5.0), (5.0, 7.0)]


def test_a_sketch_with_no_line_together_spans_as_it_always_did():
    assert sketch.line_spans(SK) == [(0.0, 3.0), (3.0, 4.5), (4.5, 9.0)]


@pytest.mark.parametrize(
    "lines, match",
    [
        ((replace(LINES[0], together=True), *LINES[1:]), "the line before"),
        ((*LINES[:2], Line("boss", "Stop.", together=True), LINES[3]), "another speaker"),
        ((*TOGETHER[:3], replace(LINES[3], together=True)), "another speaker|the line before"),
    ],
)
def test_a_line_with_nothing_to_join_is_refused(lines, match):
    with pytest.raises(sketch.SketchError, match=match):
        sketch.check(replace(BOTH, lines=lines))


def test_a_beat_cannot_start_a_line_said_together():
    beats = (*BEATS[:2], Beat(3.5, "dog", "Stop.", "half", "flat", "desk", 2, 0), BEATS[3])
    with pytest.raises(sketch.SketchError, match="together"):
        sketch.check(replace(BOTH, beats=beats))


def test_both_takes_start_on_one_beat_and_the_next_line_waits_for_the_longer(tmp_path):
    longer = (*TOGETHER[:2], Line("rex", "Stop it right now.", together=True), LINES[3])
    rec, _ = recorded(tmp_path, replace(BOTH, lines=longer))
    joined, joining, after = rec.items[1:4]
    assert joined["start"] == joining["start"]
    assert 0 <= rec.beats[1].start - joined["start"] < 0.1  # the beat is on the heard word, just inside the clip
    assert joining["duration"] > joined["duration"]
    assert after["start"] >= joining["start"] + joining["duration"]


def test_each_take_is_heard_alone_and_a_miss_on_the_second_voice_stops_the_run(tmp_path):
    rec, client = recorded(tmp_path)
    assert [r[0] for r in client.requests].count("Stop.") == 2
    assert [q["id"] for q in rec.items] == ["01", "02", "03", "04"]
    bad = FakeClient(tmp_path, heard={"Stop.": "Top."})
    with pytest.raises(sketch.SketchError, match="speech check failed"):
        sketch.record(BOTH, tmp_path / "q", bad, confirm=confirm_stub, ffmpeg="ffmpeg")


def test_the_recording_reads_back_and_places_again_with_both_voices(tmp_path):
    recorded(tmp_path)
    root = tmp_path / "p"
    takes, _ = sketch.load_speech(root / "voiced" / "speech.json", BOTH.cast)
    assert len(takes) == 4 and takes[1].at == takes[2].at
    before = json.loads((root / "voiced" / "beats.json").read_text())
    assert sketch.place_again(BOTH, root) == sketch.load_beats(root / "voiced" / "beats.json")[0]
    assert json.loads((root / "voiced" / "beats.json").read_text()) == before


def test_a_recording_with_no_line_together_places_as_it_always_did(tmp_path):
    rec, _ = recorded(tmp_path, SK)
    starts = [q["start"] for q in rec.items]
    assert starts == sorted(starts) and len(set(starts)) == 3
    assert SPEAKERS[0].name == "rex"

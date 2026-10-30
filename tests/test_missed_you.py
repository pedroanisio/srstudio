"""Missed You as data: it opens on the promise, the days run in the sheet's order, she blinks once, the note lands
before the only line, and a script that breaks any of it is refused."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import sketch

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import missed_you_data

        return missed_you_data
    finally:
        sys.path.pop(0)


def with_beats(sk, change):
    return replace(sk, beats=tuple(change(b) for b in sk.beats))


def test_the_sketch_is_consistent_and_stops_on_her(data):
    data.validate()
    sk = data.SKETCH
    assert [line.text for line in sk.lines] == ["Sorry we missed you."]
    assert sk.beats[-1].who == "frog" and sk.beats[-1].spoken
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST


def test_the_first_beat_moves_under_the_promise(data):
    assert data.HAUL[0] == 0.0
    assert data.SKETCH.beats[0].caption == data.PROMISE


def test_an_opening_without_the_promise_is_refused(data):
    sk = data.SKETCH
    beats = (replace(sk.beats[0], caption=""), *sk.beats[1:])
    with pytest.raises(sketch.SketchError, match="opens silent"):
        data.validate(replace(sk, beats=beats))


def test_a_second_line_is_refused(data):
    sk = data.SKETCH
    lines = (*sk.lines, sketch.Line("fern", "Hello?"))
    with pytest.raises(sketch.SketchError):
        data.validate(replace(sk, lines=lines))


def test_days_out_of_order_are_refused(data):
    swapped = {"stage:step": "stage:stare", "stage:stare": "stage:step"}
    sk = with_beats(data.SKETCH, lambda b: replace(b, event=swapped.get(b.event, b.event)))
    with pytest.raises(sketch.SketchError, match="stages run"):
        data.validate(sk)


@pytest.mark.parametrize("kind", ["tiptoe", "blink", "day3", "stick"])
def test_a_missing_beat_is_refused(data, kind):
    sk = with_beats(data.SKETCH, lambda b: replace(b, event="") if b.event == kind else b)
    with pytest.raises(sketch.SketchError, match=f"one {kind}"):
        data.validate(sk)


def test_a_second_blink_is_refused(data):
    sk = data.SKETCH
    beats = tuple(replace(b, eyes="closed") if b.start == 9.15 else b for b in sk.beats)
    with pytest.raises(sketch.SketchError, match="blinks once"):
        data.validate(replace(sk, beats=beats))


def test_a_line_before_the_note_lands_is_refused(data):
    sk = data.SKETCH
    spoken = sk.beats[-1]
    stick = data.event(sk.beats, "stick")
    beats = (*sk.beats[:-1], replace(spoken, start=stick + data.STICK_RISE / 2))
    with pytest.raises(sketch.SketchError, match="note lands"):
        data.validate(replace(sk, beats=beats))


def test_an_unknown_event_is_refused(data):
    sk = with_beats(data.SKETCH, lambda b: replace(b, event="parcel") if b.event == "day3" else b)
    with pytest.raises(sketch.SketchError):
        data.validate(sk)


def test_the_foley_follows_the_beats(data):
    moved = data.sounds(data.SKETCH.beats, data.SKETCH.end)
    by_id = {sound.id: sound for sound in moved}
    assert by_id["scrape"].at == data.HAUL
    assert by_id["note"].at == (data.event(data.SKETCH.beats, "stick") + data.STICK_RISE,)

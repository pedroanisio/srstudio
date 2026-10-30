"""I Cleaned as data: it opens in the whirl, the reveals run in the sheet's order, the last word is his, and a script
that breaks any of it is refused."""

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
        import i_cleaned_data

        return i_cleaned_data
    finally:
        sys.path.pop(0)


def swap_events(beats, one, other):
    swapped = {one: other, other: one}
    return tuple(replace(b, event=swapped[b.event]) if b.event in swapped else b for b in beats)


def test_the_sketch_is_consistent_and_ends_on_his_line(data):
    data.validate()
    sk = data.SKETCH
    assert sk.lines[0].text == "I cleaned!" and sk.lines[-1].text == "I cleaned."
    assert sk.beats[-1].who == "raccoon" and sk.beats[-1].spoken
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST


def test_a_line_before_the_whirl_ends_is_refused(data):
    sk = data.SKETCH
    beats = list(sk.beats)
    beats[1] = replace(beats[1], start=0.3)
    with pytest.raises(sketch.SketchError, match="opens on the whirl"):
        data.validate(replace(sk, beats=tuple(beats)))


def test_a_reveal_out_of_order_is_refused(data):
    sk = data.SKETCH
    with pytest.raises(sketch.SketchError, match="reveals run"):
        data.validate(replace(sk, beats=swap_events(sk.beats, "closet", "bury")))


@pytest.mark.parametrize("kind", ["closet", "oven", "pull", "drawer", "bury"])
def test_a_missing_reveal_is_refused(data, kind):
    sk = data.SKETCH
    beats = tuple(replace(b, event="") if b.event == kind else b for b in sk.beats)
    with pytest.raises(sketch.SketchError, match=f"one {kind}"):
        data.validate(replace(sk, beats=beats))


def test_a_stray_event_is_refused(data):
    sk = data.SKETCH
    beats = list(sk.beats)
    beats[1] = replace(beats[1], event="confetti")
    with pytest.raises(sketch.SketchError, match="unknown events"):
        data.validate(replace(sk, beats=tuple(beats)))


def test_the_sounds_land_on_their_events_inside_the_reel(data):
    beats, end = data.SKETCH.beats, data.SKETCH.end
    sounds = {s.id: s for s in data.sounds(beats, end)}
    assert len(sounds["plates"].at) == data.PLATES
    assert all(0 <= t < end for s in sounds.values() for t in s.at)

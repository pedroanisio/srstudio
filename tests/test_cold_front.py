"""Cold Front as data: the forecast's lines in order, the two voices on one beat, the three inserts the recording
places, and the refusal when a recording breaks their order (the shared Collage build is tested elsewhere)."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import sketch
from srstudio.errors import SrstudioError

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import cold_front_data

        return cold_front_data
    finally:
        sys.path.pop(0)


def test_the_forecast_hooks_at_once_and_ends_on_its_send_line(data):
    sk = data.SKETCH
    assert sk.beats[0].start == 0 and sk.lines[0].text.startswith("First frost tonight")
    assert sk.lines[-1].text == "He doesn't miss you. He's cold."
    assert sk.tail == 0.45


def test_priya_and_omar_say_her_name_on_one_beat(data):
    omar, priya = data.LINES[7], data.LINES[8]
    assert (omar.text, priya.text) == ("Deb.", "Deb.")
    assert not omar.together and priya.together and priya.phone


def test_the_inserts_follow_the_buzzes_in_order(data):
    spans = data.inserts(data.SKETCH.beats)
    assert len(spans) == 3 and all(a < b for a, b in spans)
    assert all(c[0] >= p[1] for p, c in zip(spans, spans[1:], strict=False))
    buzzes = [t for t, _ in sketch.events(data.SKETCH.beats, "buzz")]
    assert spans[0][0] == buzzes[0] and spans[1][0] == buzzes[1]


def test_a_recording_that_breaks_the_inserts_order_is_refused(data):
    beats = list(data.SKETCH.beats)
    i = next(k for k, b in enumerate(beats) if b.event == "reveal:cover")
    j = next(k for k, b in enumerate(beats) if b.event == "buzz")
    beats[i], beats[j] = replace(beats[i], event="buzz"), replace(beats[j], event="reveal:cover")
    with pytest.raises(SrstudioError, match="out of order"):
        data.inserts(beats)


def test_her_hand_leaves_the_words_once_the_second_bubble_is_read(data):
    where, times = data._hand(data.SKETCH.beats)
    changed = next(b.start for b in data.SKETCH.beats if b.line == 6)
    assert where(changed) == data.HAND_ABOVE
    assert where(times[-1]) == data.HAND_DOWN


def test_no_cut_falls_inside_a_caption(data):
    sk = data.SKETCH
    cuts = [a.start for a in sketch.appearances(sk.beats, sk.end)][1:]
    starts = [b.start for b in sk.beats]
    spans = []
    for i, b in enumerate(sk.beats):
        if b.caption and (not i or sk.beats[i - 1].caption != b.caption):
            ends = [t for t, q in zip(starts, sk.beats, strict=True) if t > b.start and q.caption != b.caption]
            spans.append((b.start, ends[0] if ends else sk.end))
    assert [(a, b, c) for a, b in spans for c in cuts if a < c < b] == []


def test_each_insert_opens_on_a_cut_with_no_caption_over_it(data):
    beats = data.SKETCH.beats
    for at, _ in sketch.events(beats, "buzz"):
        beat = next(b for b in beats if b.start == at)
        assert beat.caption == "" and beat.who == "deb"


def test_her_forearm_stays_in_sight_above_the_duvet_wherever_the_hand_is(data):
    where, times = data._hand(data.SKETCH.beats)
    over = data.DUVET_TOP - 60.0
    assert all(where(t)[1] < over for t in times)


def test_hey_is_covered_when_it_goes_and_was_up_long_enough_to_read(data):
    beats = data.SKETCH.beats
    where, _ = data._hand(beats)
    gone = data._covered(beats)
    x, y = where(gone)
    assert abs(x - data.BUBBLE_AT[0]) < 15.0 and abs(y - data.BUBBLE_AT[1]) < 40.0
    assert gone - data._at(beats, "cover") >= 0.84

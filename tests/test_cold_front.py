"""Cold Front as data: the forecast's lines in order, the two voices on one beat, the three inserts the recording
places, and the refusal when a recording breaks their order (the shared Collage build is tested elsewhere)."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, collage, flat_counter, sketch
from srstudio.canvas import Signature
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


TAKES = {"deb": 0.576, "scattered": 1.554, "low": 2.742}  # seconds of the pinned takes that end the three silences
LAST_LINE = 2.422  # the send line's pinned take and what the reel holds after it, measured


def _starts(data):
    said = {b.line: b.start for b in data.SKETCH.beats if b.line is not None and b.word == 0}
    return said


def test_the_short_arm_of_sp_length_holds(data):
    assert _starts(data)[9] + LAST_LINE <= 18.0


def test_the_pause_before_the_punch_stays_the_longest_and_over_a_second_and_a_fifth(data):
    said = _starts(data)
    punch = said[9] - (said[7] + TAKES["deb"])
    others = (said[3] - (said[2] + TAKES["scattered"]), said[6] - (said[5] + TAKES["low"]))
    assert punch >= 1.2 and punch >= max(others)


def test_the_cut_back_from_the_first_bubble_is_on_priyas_word_so_a_recording_cannot_pull_it_in(data):
    """A silent beat is placed at most sketch.BLANK_MARGIN before the next line, which took 0.15 s off this insert
    and left HEY under a text layer's shortest span. On the line's own beat the cut stays where the rows put it."""
    cover = next(b for b in data.BEATS if b.event == "reveal:cover")
    assert cover.line == 3 and cover.word == 0


def test_every_insert_holds_past_a_text_layers_shortest_span(data):
    assert all(b - a >= 0.84 for a, b in data.inserts(data.SKETCH.beats))


def test_the_green_bubble_lands_after_a_held_look_at_the_phone_and_can_be_read(data):
    beats = data.SKETCH.beats
    opens, closes = data.inserts(beats)[2]
    answer = data._at(beats, "answer")
    assert answer - opens >= 0.3 and closes - answer >= 0.84


def test_only_the_named_hey_is_gated_on_a_drawn_phone(data):
    """The reply in her hand is under the duvet: its word goes, and the first HEY keeps its own timing."""
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=18.0, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"), signature=Signature())
    cv.font_asset = "font"
    phone = data._thread(cv, cv.group(cv.comp, "phone"), data.PHONE, data.SKETCH.beats)
    data._hide(cv, phone, "HEY", 14.0, last=True)
    hey = {a.id for a in cv.assets.iter() if a.xml_name == "text" and a.text == "HEY"}
    first, reply = [n for n in phone.iter() if n.xml_name == "layer" and n.asset in hey]
    assert any(n.xml_name == "animate" for n in reply.iter())
    assert not any(n.xml_name == "animate" for n in first.iter())


def test_the_cover_is_a_frame_of_her_not_of_the_phone(data):
    sys.path.insert(0, str(EPISODES / "posts"))
    try:
        import cold_front
    finally:
        sys.path.pop(0)
    at = cold_front.RELEASE.post.thumbnail.at
    assert not any(a <= at < b for a, b in data.inserts(data.SKETCH.beats))
    assert next(b for b in reversed(data.SKETCH.beats) if b.start <= at).who == "deb"

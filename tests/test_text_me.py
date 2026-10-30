"""Text Me as data: Mom's first line inside half a second, the son's stages in order, one knock, one send, and every
searcher gone before the end; a script that breaks any of it is refused."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import sketch, toon_world

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import text_me_data

        return text_me_data
    finally:
        sys.path.pop(0)


def test_the_sketch_is_consistent_and_starts_at_once(data):
    data.validate()
    sk = data.SKETCH
    assert next(b for b in sk.beats if b.spoken).start <= 0.5
    assert sk.lines[0].text in sk.lines[-1].text
    assert {s.character for s in sk.speakers} == {"fox", "cat", "sloth"}
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST


def test_a_slow_opening_is_refused(data):
    sk = data.SKETCH
    beats = [replace(b, start=b.start + 1.0) if i else b for i, b in enumerate(sk.beats)]
    with pytest.raises(sketch.SketchError, match="half a second"):
        data.validate(replace(sk, beats=tuple(beats), end=sk.end + 1.0))


def test_a_missing_stage_is_refused(data):
    sk = data.SKETCH
    beats = [replace(b, event="") if b.event == "stage:plug" else b for b in sk.beats]
    with pytest.raises(sketch.SketchError, match="stages run in order"):
        data.validate(replace(sk, beats=tuple(beats)))


def test_a_ding_before_the_send_and_a_stray_event_are_refused(data):
    sk = data.SKETCH
    beats = [replace(b, event="") if b.event == "ding" else b for b in sk.beats]
    beats[1] = replace(beats[1], event="ding")
    with pytest.raises(sketch.SketchError, match="ding after he sends"):
        data.validate(replace(sk, beats=tuple(beats)))
    beats = list(sk.beats)
    beats[1] = replace(beats[1], event="confetti")
    with pytest.raises(sketch.SketchError):
        data.validate(replace(sk, beats=tuple(beats)))


def test_a_stage_on_someone_elses_shot_is_refused(data):
    sk = data.SKETCH
    beats = [replace(b, who="sloth") if b.event == "stage:plug" else b for b in sk.beats]
    with pytest.raises(sketch.SketchError, match="on the son's shot"):
        data.validate(replace(sk, beats=tuple(beats)))


def test_every_searcher_leaves_before_the_end_and_the_sounds_follow(data):
    beats, end = data.SKETCH.beats, data.SKETCH.end
    assert data.dings(beats)[-1] + toon_world.LEAVE < end
    sounds = {s.id: s for s in data.sounds(beats, end)}
    assert sounds["ding"].at == tuple(data.dings(beats)) and len(sounds["knock"].at) == 3

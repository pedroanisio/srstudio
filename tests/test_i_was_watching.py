"""I Was Watching as data: a still opening, the stages in order on Bruno's shots, the one gull, and refusal of a
script that breaks any of it. The sketch's own sounds reach the recording's manifest through the shared hook."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import foley, sketch, toon_sketch

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import i_was_watching_data

        return i_was_watching_data
    finally:
        sys.path.pop(0)


def with_beats(sk, beats):
    return replace(sk, beats=tuple(beats))


def test_the_sketch_is_consistent_and_holds_its_opening(data):
    data.validate()
    sk = data.SKETCH
    assert sk.beats[0].who == "bear" and sk.beats[1].start >= 1.0
    assert sk.lines[0].text == sk.lines[-1].text == "I was watching that."
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST
    assert len({s.voice.id for s in sk.speakers}) == 3


def test_a_moving_opening_is_refused(data):
    sk = data.SKETCH
    beats = list(sk.beats)
    beats[1] = replace(beats[1], start=0.4)
    with pytest.raises(sketch.SketchError, match="opens on a still"):
        data.validate(with_beats(sk, beats))


def test_stages_out_of_order_are_refused(data):
    sk = data.SKETCH
    beats = [replace(b, event="stage:yard") if b.event == "stage:bare" else b for b in sk.beats]
    beats = [replace(b, event="stage:bare") if b.event == "stage:yard" and b is not beats[0] else b for b in beats]
    with pytest.raises(sketch.SketchError):
        data.validate(with_beats(sk, beats))


def test_a_second_gull_and_a_stray_event_are_refused(data):
    sk = data.SKETCH
    plain = next(i for i, b in enumerate(sk.beats) if i and not b.event)
    for event in ("gull", "explosion"):
        beats = list(sk.beats)
        beats[plain] = replace(beats[plain], event=event)
        with pytest.raises(sketch.SketchError):
            data.validate(with_beats(sk, beats))


def test_the_gull_lands_inside_the_dump_and_before_the_last_line(data):
    beats = data.SKETCH.beats
    named = dict((name, at) for at, name in data.stages(beats))
    assert named["dump"] < data.land_of(beats) < max(b.start for b in beats if b.spoken)


def test_the_sounds_follow_the_placed_beats(data):
    beats, end = data.SKETCH.beats, data.SKETCH.end
    sounds = {s.id: s for s in data.sounds(beats, end)}
    assert set(sounds) == {"click", "snore", "road", "gull"}
    assert sounds["click"].at == tuple(data.clicks(beats))
    assert all(0 <= t < end for s in sounds.values() for t in s.at)


def test_a_sound_reaches_the_manifest_and_an_empty_one_does_not(data, tmp_path):
    beats, end = data.SKETCH.beats, data.SKETCH.end

    def asked(_, __):
        return [toon_sketch.Sound("click", foley.REMOTE_CLICK, (1.0,)), toon_sketch.Sound("none", foley.DING, ())]

    effects = toon_sketch.sound_effects(beats, end, [], tmp_path, 3, asked)
    ids = [e["id"] for e in effects]
    assert "click" in ids and "none" not in ids
    assert (tmp_path / "audio" / "click.wav").is_file()

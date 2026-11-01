"""New Challenges as data: the sketch is consistent, its events come once, in order, and a broken copy is refused."""

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
        import new_challenges_data

        return new_challenges_data
    finally:
        sys.path.pop(0)


def test_the_sketch_is_consistent(data) -> None:
    data.validate()


def test_the_first_line_comes_by_half_a_second(data) -> None:
    assert next(b for b in data.SKETCH.beats if b.spoken).start <= 0.5


def test_a_dropped_event_is_refused(data) -> None:
    beats = tuple(replace(b, event="") if b.event == "red" else b for b in data.SKETCH.beats)
    with pytest.raises(sketch.SketchError):
        data.validate(replace(data.SKETCH, beats=beats))


def test_an_event_twice_is_refused(data) -> None:
    once = next(b for b in data.SKETCH.beats if b.event == "red")
    with pytest.raises(sketch.SketchError):
        data.validate(replace(data.SKETCH, beats=(*data.SKETCH.beats, replace(once, start=data.SKETCH.end - 0.2))))


def test_the_master_asks_for_the_channels_loudness() -> None:
    assert 'loudness="-14",' in (EPISODES / "new_challenges.py").read_text()


def test_a_face_on_screen_always_has_a_mouth(data) -> None:
    assert all(b.mouth != "none" for b in data.SKETCH.beats if b.who in data.HEADS)


def test_the_hook_holds_long_enough_to_read_in_every_shot(data) -> None:
    beats = data.SKETCH.beats
    cuts = [b.start for a, b in zip(beats, beats[1:], strict=False) if a.who != b.who]
    seen = [c for c in cuts if c < data.HOOK_END]
    assert all(data.HOOK_END - c >= 0.84 for c in seen)

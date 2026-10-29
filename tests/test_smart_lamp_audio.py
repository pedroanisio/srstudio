"""Smart Lamp as a song: lines on the bar grid in order, a hold before the punchline, the lamp's orders in between."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import smart_lamp_audio
    finally:
        sys.path.pop(0)
    return smart_lamp_audio


def test_the_lines_run_in_order_and_the_punchline_waits(audio):
    starts = [audio.GROOVE.at(*line.at) for line in audio.LINES]
    assert starts == sorted(starts) and len(set(starts)) == len(starts)
    assert starts[9] - starts[8] >= 2.4  # "Cancel the ring!" ... a held pad ... "She said yes."
    assert starts[-1] + 2.0 < audio.PLAN.seconds


def test_the_lamp_wakes_before_it_speaks_and_orders_after_each_offer(audio):
    fx = {e.id: audio.GROOVE.at(*e.at) for e in audio.SONG.effects}
    lines = [audio.GROOVE.at(*line.at) for line in audio.LINES]
    assert lines[1] < fx["wake"] < lines[2]
    assert lines[5] < fx["order-flowers"] < lines[6] and lines[7] < fx["order-ring"] < lines[8]
    assert fx["not-understood"] > lines[-1] and fx["not-understood"] + 0.7 < audio.PLAN.seconds


def test_every_speaker_has_a_premade_voice_and_the_music_is_instrumental_at_120(audio):
    assert {line.role for line in audio.LINES} == set(audio.SONG.voices)
    assert audio.SONG.composition.role is None and audio.GROOVE.bpm == 120
    assert all("steady kick on every beat" in chunk.styles for chunk in audio.PLAN.chunks)
    assert not any(ch.isdigit() for line in audio.LINES for ch in line.text)  # speech-to-text writes numbers

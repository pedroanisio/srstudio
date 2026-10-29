"""Return to Office as a song: lines on the bar grid in order, a hold before the punchline, the lights gag last."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import return_to_office_audio
    finally:
        sys.path.pop(0)
    return return_to_office_audio


def test_the_lines_run_in_order_and_the_punchline_waits_a_bar(audio):
    starts = [audio.GROOVE.at(*line.at) for line in audio.LINES]
    assert starts == sorted(starts) and len(set(starts)) == len(starts)
    assert starts[7] - starts[6] >= 2.4  # "So why am I here?" ... a held pad ... "Someone has to be the culture."
    assert starts[-1] < audio.PLAN.seconds


def test_the_lights_go_off_on_again_and_off_after_the_call_and_inside_the_song(audio):
    fx = {e.id: audio.GROOVE.at(*e.at) for e in audio.SONG.effects}
    assert fx["call-join"] < fx["seagull"] < fx["call-end"] < fx["lights-off"] < fx["lights-on"] < fx["lights-off-2"]
    assert fx["call-end"] > audio.GROOVE.at(*audio.LINES[-1].at)
    assert fx["lights-off-2"] + 0.8 < audio.PLAN.seconds


def test_every_speaker_has_a_premade_voice_and_the_music_is_instrumental_at_120(audio):
    assert {line.role for line in audio.LINES} == set(audio.SONG.voices)
    assert audio.SONG.composition.role is None and audio.GROOVE.bpm == 120
    assert all("steady kick on every beat" in chunk.styles for chunk in audio.PLAN.chunks)

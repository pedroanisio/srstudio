"""The Cake as a song: lines on the bar grid in order, a held pause before the cake turns, a sting right after."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import the_cake_audio
    finally:
        sys.path.pop(0)
    return the_cake_audio


def test_the_lines_run_in_order_and_leave_room_for_the_ending(audio):
    starts = [audio.GROOVE.at(*line.at) for line in audio.LINES]
    assert starts == sorted(starts) and len(set(starts)) == len(starts)
    assert starts[-1] + 2.0 < audio.PLAN.seconds <= 35


def test_the_cake_turns_after_a_hold_and_the_sting_lands_before_pip_speaks(audio):
    fx = {e.id: audio.GROOVE.at(*e.at) for e in audio.SONG.effects}
    lines = [audio.GROOVE.at(*line.at) for line in audio.LINES]
    sweet = audio.LINES.index(next(x for x in audio.LINES if "sweet" in x.text))
    assert fx["turn"] - lines[sweet] >= 3.0  # the line itself takes under two seconds: a hold of over 1.2 s
    assert fx["turn"] < fx["sting"] < lines[sweet + 1]
    assert lines[sweet - 2] < fx["party-horn"] < lines[sweet - 1]  # Bo arrives before he speaks


def test_every_speaker_has_a_premade_voice_and_the_music_is_instrumental_at_120(audio):
    assert {line.role for line in audio.LINES} == set(audio.SONG.voices) == {"juno", "pip", "bo"}
    assert len({s.id for s in audio.SONG.voices.values()}) == 3
    assert audio.SONG.composition.role is None and audio.GROOVE.bpm == 120
    assert all("steady kick on every beat" in chunk.styles for chunk in audio.PLAN.chunks)
    assert not any(ch.isdigit() for line in audio.LINES for ch in line.text)  # speech-to-text writes numbers


def test_the_cake_lettering_fits_the_prop(audio):
    from srstudio import soft_props

    for text in (audio.FRONT, audio.BACK):
        lines = text.split("\n")
        assert len(lines) <= soft_props.CAKE_LINES and all(len(x) <= soft_props.CAKE_LINE for x in lines)

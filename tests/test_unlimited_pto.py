"""Unlimited PTO (episode 13) as data: two voices on the bar grid, a rule of three of declines that each land between
Pip's ask and Bo's reason, a hold before the punchline, and the instrumental bed at 120 bpm."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import unlimited_pto_audio

        return unlimited_pto_audio
    finally:
        sys.path.pop(0)


def test_two_voices_and_an_instrumental_bed_at_120_bpm(data):
    song = data.SONG
    assert {v.id for v in song.voices.values()} == {"cjVigY5qzO86Huf0OWal", "bIHbv24MWmeRgasZH58o"}
    assert {line.role for line in song.lines} == set(song.voices)
    assert song.groove.bpm == 120 and song.composition is not None and song.composition.role is None
    assert all("steady kick on every beat" in chunk.styles and not chunk.lines for chunk in data.PLAN.chunks)
    assert song.lines[0].text.endswith("?") and song.lines[0].role == "bo"  # the hook


def test_lines_rise_on_the_grid_and_each_decline_lands_between_the_ask_and_the_reason(data):
    at = data.GROOVE.at
    starts = [at(*line.at) for line in data.SONG.lines]
    assert starts == sorted(starts) and starts[-1] < data.PLAN.seconds
    effects = {e.id: at(*e.at) for e in data.SONG.effects}
    asks = [i for i, line in enumerate(data.SONG.lines) if line.role == "pip"][:3]
    for n, i in enumerate(asks, start=1):
        assert starts[i] < effects[f"decline-{n}"] < starts[i + 1]
    assert data.SONG.lines[-2].text.startswith("Unlimited.")
    assert starts[-2] - starts[-3] >= 3 * 0.5  # Pip's question gets its line and a hold of at least a beat
    assert effects["approved"] < starts[-1]  # the button: Bo's request is approved before he says goodbye

"""Focus Mode: the song's punchline and callback, and the composed music cut to the grid (the shared steps are
tested in test_song.py and test_compose.py)."""

import math
import sys
from pathlib import Path

import pytest

from srstudio.song import SongError

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        return __import__("focus_mode_audio")
    finally:
        sys.path.pop(0)


def test_the_deadline_pays_off_and_the_dance_returns_as_a_callback(audio):
    lines = audio.SONG.lines
    texts = [line.text for line in lines]
    deadline, punchline, callback = texts.index("Hold on. The deadline."), len(lines) - 2, len(lines) - 1
    assert deadline < punchline and "yesterday" in texts[punchline]
    assert texts[callback] == "Shake it to the beat!" == texts[4]
    assert lines[callback].at == (audio.PLAYS[1][0], 0)  # said on the drop


def test_the_music_is_instrumental_composed_and_lasts_the_whole_grid(audio):
    c = audio.SONG.composition
    assert c is not None and c.role is None and c.plan is audio.PLAN
    assert all(not chunk.lines for chunk in audio.PLAN.chunks)
    assert audio.PLAN.seconds == audio.GROOVE.at(audio.BARS)
    for start, _ in audio.PLAN.windows():
        assert start / audio.GROOVE.bar == int(start / audio.GROOVE.bar)  # every chunk starts on a bar


@pytest.mark.parametrize("phase", [0.0, 0.1, 0.25, 0.3, 0.49])
def test_the_music_is_heard_only_in_its_bars_with_its_beats_on_the_grid(audio, phase):
    spans = audio.music_spans(phase, duration=24.0)
    assert len(spans) == len(audio.PLAYS)
    for (start, clip_in, clip_out), (first, last) in zip(spans, audio.PLAYS, strict=True):
        assert 0 <= clip_in < clip_out <= 24.0
        assert audio.GROOVE.at(first) <= start < audio.GROOVE.at(first) + audio.GROOVE.beat / 2
        assert start + (clip_out - clip_in) <= audio.GROOVE.at(last) + 1e-6
        beat = (start - clip_in + phase) / audio.GROOVE.beat  # where the song's beats play, on the video clock
        assert math.isclose(beat, round(beat), abs_tol=1e-6)
    silent = (audio.GROOVE.at(audio.PLAYS[0][1]), audio.GROOVE.at(audio.PLAYS[1][0]))
    assert spans[0][0] + spans[0][2] - spans[0][1] <= silent[0] + 1e-6 and spans[1][0] >= silent[1]


@pytest.mark.parametrize("phase, duration", [(-0.1, 24.0), (0.5, 24.0), (float("nan"), 24.0), (0.1, 0.0), (0.1, 15.0)])
def test_a_phase_or_length_the_cut_cannot_use_is_refused(audio, phase, duration):
    with pytest.raises(SongError):
        audio.music_spans(phase, duration)

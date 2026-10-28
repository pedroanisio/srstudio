"""The song of Camera Off: Pip sings in the composed music, and the boss and the effects land where it has no
lyrics (the pipeline itself is tested in test_song.py and test_compose.py)."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def song():
    sys.path.insert(0, str(EPISODES))
    try:
        import camera_off_audio
    finally:
        sys.path.pop(0)
    return camera_off_audio


def lyric_free(plan):
    return [w for c, w in zip(plan.chunks, plan.windows(), strict=True) if not c.lines]


def test_pip_is_sung_by_the_composition_and_the_boss_is_spoken(song):
    s = song.SONG
    assert s.composition is not None and s.composition.role == "pip"
    assert all(s.sung(line) for line in s.lines if line.role == "pip")
    assert not any(s.sung(line) for line in s.lines if line.role == "boss")


def test_every_chunk_is_whole_bars_on_the_episode_tempo(song):
    bar = 4 * 60 / song.GROOVE.bpm
    for chunk in song.PLAN.chunks:
        assert chunk.seconds % bar == 0, chunk.name
        assert f"{song.GROOVE.bpm:g} BPM" in chunk.styles, chunk.name


def test_the_boss_and_the_effects_start_over_a_chunk_without_lyrics(song):
    s, free = song.SONG, lyric_free(song.PLAN)
    starts = [song.GROOVE.at(*line.at) for line in s.lines if line.role == "boss"]
    starts += [song.GROOVE.at(*effect.at) for effect in s.effects]
    for start in starts:
        assert any(a <= start < b for a, b in free), start


def test_the_lines_end_with_the_composed_song(song):
    assert song.SONG.lines_end == song.PLAN.seconds == 24.0

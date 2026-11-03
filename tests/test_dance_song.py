"""Song structure from audio: a track synthesised with known sections reads back with those sections."""

import numpy as np
import pytest

from srstudio import music
from srstudio.dance import DanceError, SongMapError, song_map
from srstudio.music import Groove, Section

GRID = Groove(160)  # a bar is 1.5 s, so 24 bars render quickly
QUIET = frozenset({"hat", "keys"})
RATE = 16000


@pytest.fixture(scope="module")
def track(tmp_path_factory):
    """Eight quiet bars, eight full ones, eight quiet: a verse, a chorus, a verse."""
    sections = [Section(0, 8, QUIET), Section(8, 16), Section(16, 24, QUIET)]
    samples = music.render(GRID, sections, rate=RATE)
    return music.write_wav(tmp_path_factory.mktemp("dance") / "song.wav", samples, RATE)


def test_a_song_reads_back_its_known_sections(track):
    found = song_map(track, GRID)
    assert found.boundaries == (8, 16)
    assert [(p.start_bar, p.end_bar, p.level) for p in found.parts] == [(0, 8, "low"), (8, 16, "high"), (16, 24, "low")]
    assert found.parts[1].level_db > found.parts[0].level_db + 3
    assert len(found.phrase_db) == 3


def test_every_beat_has_an_energy_and_the_full_section_is_louder(track):
    found = song_map(track, GRID)
    beats = np.array(found.beat_db)
    assert len(beats) == 24 * 4
    assert beats.max() == pytest.approx(0)
    assert beats[32:64].mean() > beats[:32].mean() + 3


def test_a_shorter_phrase_finds_the_same_boundaries(track):
    assert song_map(track, GRID, phrase_bars=4).boundaries == (8, 16)


def test_a_higher_change_threshold_hears_one_even_part(track):
    found = song_map(track, GRID, change_db=60.0)
    assert found.boundaries == () and [p.level for p in found.parts] == ["even"]


def test_a_track_of_one_level_is_one_even_part(tmp_path):
    samples = music.render(GRID, [Section(0, 16)], rate=RATE)
    path = music.write_wav(tmp_path / "even.wav", samples, RATE)
    found = song_map(path, GRID)
    assert found.boundaries == () and found.parts[0].level == "even"
    assert (found.parts[0].start_bar, found.parts[0].end_bar) == (0, 16)


def test_a_short_last_phrase_keeps_its_bars(track):
    found = song_map(track, GRID, phrase_bars=5)
    assert found.parts[-1].end_bar == 24
    assert len(found.phrase_db) == 5


def test_seconds_reads_the_start_of_the_track(track):
    assert song_map(track, GRID, seconds=12.0).parts[-1].end_bar == 8


def test_an_offset_moves_the_bars(tmp_path):
    grid = Groove(160, offset=0.75)
    path = music.write_wav(
        tmp_path / "late.wav", music.render(grid, [Section(0, 8, QUIET), Section(8, 16)], rate=RATE), RATE
    )
    found = song_map(path, grid)
    assert found.boundaries == (8,)


def test_a_track_too_short_for_a_phrase_is_refused(track):
    with pytest.raises(SongMapError):
        song_map(track, GRID, seconds=3.0)


def test_a_silent_track_is_refused(tmp_path):
    path = music.write_wav(tmp_path / "silent.wav", [0.0] * (RATE * 16), RATE)
    with pytest.raises(SongMapError):
        song_map(path, GRID)


def test_a_track_past_the_bound_is_refused(track, monkeypatch):
    from srstudio import _dance_song

    monkeypatch.setattr(_dance_song, "MAX_SECONDS", 1.0)
    with pytest.raises(SongMapError):
        song_map(track, GRID)


def test_an_unreadable_track_raises_the_music_error(tmp_path):
    with pytest.raises(music.MusicError):
        song_map(tmp_path / "missing.wav", GRID)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"phrase_bars": 0},
        {"phrase_bars": 2.0},
        {"change_db": 0},
        {"change_db": float("nan")},
        {"seconds": 0},
        {"seconds": 1e9},
    ],
)
def test_bad_settings_are_refused(track, kwargs):
    with pytest.raises(SongMapError) as caught:
        song_map(track, GRID, **kwargs)
    assert isinstance(caught.value, DanceError)


def test_a_grid_is_required(track):
    with pytest.raises(SongMapError):
        song_map(track, 160)  # type: ignore[arg-type]

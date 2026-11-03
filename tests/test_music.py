"""The beat grid and the synthesised groove: timing, determinism, rests, level, and refused input."""

import json
import math
import wave

import numpy as np
import pytest

from srstudio import music
from srstudio.cli import main
from srstudio.music import PARTS, Groove, MusicError, Section, render, write_wav


def test_the_grid_turns_bars_and_beats_into_seconds():
    g = Groove(bpm=120, offset=0.25)
    assert (g.beat, g.bar) == (0.5, 2.0)
    assert g.at(0) == 0.25 and g.at(1) == 2.25 and g.at(2, 3) == 5.75 and g.at(0, 0.5) == 0.5
    assert g.beats(1, 2) == [2.25, 2.75, 3.25, 3.75]
    assert g.beats(0, 1, every=2) == [0.25, 1.25]
    assert Groove(bpm=90, beats_per_bar=3).bar == pytest.approx(2.0)


@pytest.mark.parametrize(
    "kw, match",
    [
        (dict(bpm=0), "bpm"),
        (dict(bpm=400), "bpm"),
        (dict(bpm=float("nan")), "bpm"),
        (dict(bpm=120, beats_per_bar=0), "beats_per_bar"),
        (dict(bpm=120, offset=-0.1), "offset"),
    ],
)
def test_a_grid_outside_its_range_is_refused(kw, match):
    with pytest.raises(MusicError, match=match):
        Groove(**kw)


def test_a_time_before_the_first_beat_or_a_bad_step_is_refused():
    g = Groove(bpm=120)
    with pytest.raises(MusicError, match="before"):
        g.at(-1)
    with pytest.raises(MusicError, match="every"):
        g.beats(0, 1, every=0)


def rms(samples, a, b):
    chunk = samples[a:b]
    return math.sqrt(sum(v * v for v in chunk) / len(chunk))


def test_render_is_deterministic_bar_exact_and_peak_levelled():
    g = Groove(bpm=120)
    sections = [Section(0, 2), Section(2, 3, parts=frozenset()), Section(3, 4, parts=frozenset({"kick"}))]
    one = render(g, sections, rate=8000, peak=0.7)
    assert one == render(g, sections, rate=8000, peak=0.7)
    assert len(one) == round(g.at(4) * 8000)
    assert max(abs(v) for v in one) == pytest.approx(0.7)
    # The rest bar is silent; the full groove and the lone kick are not.
    assert rms(one, round(g.at(2) * 8000) + 400, round(g.at(3) * 8000)) < 1e-3
    assert rms(one, 0, round(g.at(2) * 8000)) > 0.05
    # Every kick lands on its beat: the 40 ms after each beat is louder than the 40 ms before it.
    for t in g.beats(3, 4):
        at = round(t * 8000)
        assert rms(one, at, at + 320) > 4 * rms(one, at - 320, at)


def test_render_tail_extends_past_the_last_bar():
    g = Groove(bpm=120)
    out = render(g, [Section(0, 1)], rate=8000, tail=0.5)
    assert len(out) == round((g.at(1) + 0.5) * 8000)


@pytest.mark.parametrize(
    "sections, match",
    [
        ([], "at least one"),
        ([Section(0, 2), Section(1, 3)], "overlap"),
        ([Section(1, 1)], "end after"),
        ([Section(-1, 1)], "negative"),
        ([Section(0, 1, parts=frozenset({"tuba"}))], "tuba"),
    ],
)
def test_bad_sections_are_refused(sections, match):
    with pytest.raises(MusicError, match=match):
        render(Groove(bpm=120), sections, rate=8000)


def test_bad_render_settings_are_refused():
    with pytest.raises(MusicError, match="peak"):
        render(Groove(bpm=120), [Section(0, 1)], rate=8000, peak=1.5)
    with pytest.raises(MusicError, match="rate"):
        render(Groove(bpm=120), [Section(0, 1)], rate=100)
    with pytest.raises(MusicError, match="chords"):
        render(Groove(bpm=120), [Section(0, 1)], rate=8000, chords=())
    with pytest.raises(MusicError, match="silent"):
        render(Groove(bpm=120), [Section(0, 1, parts=frozenset())], rate=8000)


def test_parts_are_named_and_the_wav_is_16_bit_mono(tmp_path):
    assert set(PARTS) == {"kick", "snare", "hat", "bass", "keys"}
    samples = render(Groove(bpm=120), [Section(0, 1)], rate=8000)
    path = write_wav(tmp_path / "groove.wav", samples, 8000)
    with wave.open(str(path), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 8000, len(samples))
    with pytest.raises(MusicError, match="-1..1"):
        write_wav(tmp_path / "bad.wav", [0.0, 1.5], 8000)


def clicks(path, bpm, seconds=12.0, first=0.3, rate=22050, every=4):
    """A click on every beat, longer and louder on the bar's first, as 16-bit mono PCM."""
    beat, samples = 60.0 / bpm, np.zeros(int(seconds * rate))
    n = 0
    while first + n * beat < seconds - 0.2:
        at, loud = int((first + n * beat) * rate), n % every == 0
        length = int(0.09 * rate if loud else 0.03 * rate)
        hz = 70.0 if loud else 1800.0
        tone = np.sin(2 * np.pi * hz * np.arange(length) / rate) * np.exp(-np.arange(length) / (length / 4))
        samples[at : at + length] += tone * (0.9 if loud else 0.45)
        n += 1
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes((samples * 32000).astype("<i2").tobytes())
    return path


@pytest.mark.parametrize("bpm", [96.0, 129.0, 150.0])
def test_a_track_gives_its_tempo_and_where_its_bars_open(tmp_path, bpm):
    found = music.measure(clicks(tmp_path / "a.wav", bpm))
    assert found.bpm == pytest.approx(bpm, abs=0.75)
    assert found.beats_per_bar == 4
    off = (0.3 - found.offset + found.bar / 2) % found.bar - found.bar / 2
    assert abs(off) < 0.021  # within half a frame at 24 fps


def test_a_three_three_two_rhythm_is_read_at_its_beat_and_not_at_two_thirds(tmp_path):
    rate, bpm, seconds = 22050, 129.0, 16.0
    beat, samples = 60.0 / bpm, np.zeros(int(seconds * rate))

    def hit(at, hz, length, loud):
        start, n = int(at * rate), int(length * rate)
        ring = np.arange(n)
        samples[start : start + n] += loud * np.sin(2 * np.pi * hz * ring / rate) * np.exp(-ring / (n / 4))

    bar = 0
    while (bar + 1) * 4 * beat < seconds - 0.3:
        for k in range(4):
            hit(0.2 + (bar * 4 + k) * beat, 70.0, 0.1, 0.6)
        for k in (0.0, 1.5, 3.0):  # the snare's 3-3-2 falls on the bar's 16ths 0, 6, 12
            hit(0.2 + (bar * 4 + k) * beat, 1500.0, 0.05, 0.9)
        bar += 1
    path = tmp_path / "dembow.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes((samples * 30000).astype("<i2").tobytes())
    assert music.measure(path).bpm == pytest.approx(bpm, abs=0.75)


def test_a_measure_is_the_same_on_a_second_run(tmp_path):
    path = clicks(tmp_path / "a.wav", 129.0)
    assert music.measure(path) == music.measure(path)


def test_silence_and_a_scrap_of_sound_have_no_tempo(tmp_path):
    quiet = tmp_path / "quiet.wav"
    with wave.open(str(quiet), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(22050)
        out.writeframes(bytes(22050 * 2 * 6))
    with pytest.raises(music.MusicError, match="silent"):
        music.measure(quiet)
    with pytest.raises(music.MusicError, match="too short"):
        music.measure(clicks(tmp_path / "short.wav", 120.0, seconds=1.0))


def test_a_file_that_is_no_audio_is_a_typed_error(tmp_path):
    bad = tmp_path / "bad.wav"
    bad.write_text("no sound here")
    with pytest.raises(music.MusicError, match="cannot read"):
        music.measure(bad)


def test_the_beat_command_prints_the_grid_it_measured(tmp_path, capsys):
    assert main(["beat", str(clicks(tmp_path / "track.wav", 120)), "--json"]) == 0
    grid = json.loads(capsys.readouterr().out)
    assert grid["bpm"] == pytest.approx(120, abs=0.5) and grid["beats_per_bar"] == 4


def test_the_beat_command_fails_plainly_on_a_file_with_no_sound(tmp_path, capsys):
    broken = tmp_path / "broken.wav"
    broken.write_text("not audio")
    assert main(["beat", str(broken)]) != 0
    assert "beat" in capsys.readouterr().err


@pytest.mark.parametrize("bpm", [92, 110, 128, 140])
def test_a_song_with_its_kick_on_one_and_three_is_read_at_the_right_bar_line(tmp_path, bpm):
    groove = Groove(bpm=bpm, offset=0.25)
    path = tmp_path / "song.wav"
    write_wav(path, render(groove, [Section(0, 12)], rate=22050), 22050)
    found = music.measure(path)
    bar = 4 * 60 / bpm
    assert found.bpm == pytest.approx(bpm, abs=0.5)
    assert (found.offset - 0.25 + bar / 2) % bar - bar / 2 == pytest.approx(0.0, abs=0.04)


def test_a_reading_says_how_many_bars_it_heard_and_doubts_a_short_one(tmp_path):
    short = music.reading(clicks(tmp_path / "short.wav", 120, seconds=8.0))
    long = music.reading(clicks(tmp_path / "long.wav", 120, seconds=20.0))
    assert short.bars == pytest.approx(4, abs=0.1) and not short.sure
    assert long.bars == pytest.approx(10, abs=0.1) and long.sure


def test_the_beat_command_warns_when_it_heard_too_few_bars(tmp_path, capsys):
    assert main(["beat", str(clicks(tmp_path / "short.wav", 120, seconds=8.0))]) == 0
    assert "bars" in capsys.readouterr().err


def test_a_mark_of_a_tempo_with_an_endless_beat_stays_in_its_own_span():
    grid = Groove(129.0)
    one, two, three = grid.between(1.0, 2.5)[:3]
    assert grid.between(one, two) == [one]
    assert grid.between(two, three) == [two]
    assert grid.between(one, three, 0.5)[0] == one


@pytest.mark.parametrize("span", [(math.nan, 1.0), (0.0, math.inf)])
def test_a_span_that_is_no_number_is_refused(span):
    with pytest.raises(MusicError):
        Groove(120.0).between(*span)


def test_a_clip_shorter_than_two_bars_is_refused_and_not_read_at_a_faster_tempo(tmp_path):
    with pytest.raises(MusicError, match="too short for bars"):
        music.reading(clicks(tmp_path / "short.wav", 90, seconds=2.6))


@pytest.mark.parametrize(("played", "read"), [(60, 120), (180, 90)])
def test_a_tempo_past_the_measured_range_reads_at_its_octave(tmp_path, played, read):
    assert music.measure(clicks(tmp_path / "far.wav", played)).bpm == pytest.approx(read, abs=1)


def test_a_bar_of_no_beats_is_refused_before_anything_is_read(tmp_path):
    with pytest.raises(MusicError, match="beats_per_bar"):
        music.reading(tmp_path / "unread.wav", beats_per_bar=0)
    assert main(["beat", str(clicks(tmp_path / "c.wav", 120)), "--beats-per-bar", "0"]) == 1


def test_a_missing_decoder_is_a_music_error(tmp_path):
    with pytest.raises(MusicError, match="no-such-ffmpeg"):
        music.reading(clicks(tmp_path / "c.wav", 120), ffmpeg="no-such-ffmpeg")


@pytest.mark.parametrize("played", [60, 180])
def test_a_hint_near_the_tempo_settles_which_octave_a_reading_takes(tmp_path, played):
    read = music.reading(clicks(tmp_path / "far.wav", played), near=played)
    assert read.groove.bpm == pytest.approx(played, abs=1)


def test_the_hint_reaches_the_beat_command(tmp_path, capsys):
    assert main(["beat", str(clicks(tmp_path / "far.wav", 180)), "--near", "180", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["bpm"] == pytest.approx(180, abs=1)


@pytest.mark.parametrize("near", [0.0, -120.0, math.nan, math.inf])
def test_a_hint_that_is_no_tempo_is_refused_before_anything_is_read(tmp_path, near):
    with pytest.raises(MusicError, match="near"):
        music.reading(tmp_path / "unread.wav", near=near)

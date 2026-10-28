"""The beat grid and the synthesised groove: timing, determinism, rests, level, and refused input."""

import math
import wave

import pytest

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

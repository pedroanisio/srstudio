"""A struck piano note as a burst, so a reel can carry a small melody inside the picture with no music bed."""

import math

import pytest

from srstudio import foley


def test_a_note_name_is_its_equal_tempered_pitch():
    assert foley.note_hz("A4") == pytest.approx(440.0)
    assert foley.note_hz("C4") == pytest.approx(261.63, abs=0.01)
    assert foley.note_hz("F#3") == pytest.approx(185.0, abs=0.01)
    assert foley.note_hz("Bb3") == pytest.approx(foley.note_hz("A#3"))


@pytest.mark.parametrize("name", ["H4", "A", "4", "", "A99", "Cb"])
def test_a_note_that_does_not_exist_is_refused(name):
    with pytest.raises(foley.FoleyError):
        foley.note_hz(name)


def test_a_piano_note_rings_at_its_pitch_and_dies_away():
    note = foley.piano("A4", ring=1.0)
    rate = 16000
    bed = foley.bursts([0.0], 1.0, note, rate=rate, seed=1)
    window = bed[: rate // 5]

    # the note's own pitch dominates: correlate against it and an unrelated one
    def power(hz: float) -> float:
        re = sum(v * math.cos(2 * math.pi * hz * i / rate) for i, v in enumerate(window))
        im = sum(v * math.sin(2 * math.pi * hz * i / rate) for i, v in enumerate(window))
        return re * re + im * im

    assert power(440.0) > 50 * power(700.0)
    early = max(abs(v) for v in bed[: rate // 10])
    late = max(abs(v) for v in bed[rate * 8 // 10 :])
    assert late < early / 4


def test_a_phrase_is_each_note_at_its_times():
    assert foley.phrase(("C4", "E4", "C4"), 1.0, 0.5) == {"C4": (1.0, 2.0), "E4": (1.5,)}


@pytest.mark.parametrize(("start", "step"), [(-1.0, 0.5), (0.0, 0.0), (0.0, -0.5)])
def test_a_phrase_runs_forward_from_a_real_second(start, step):
    with pytest.raises(foley.FoleyError):
        foley.phrase(("C4",), start, step)


def test_a_phrase_needs_notes():
    with pytest.raises(foley.FoleyError):
        foley.phrase((), 0.0, 0.5)

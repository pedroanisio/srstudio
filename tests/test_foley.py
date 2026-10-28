"""Keyboard foley: keystroke bursts where the tracked hand moves, synthesised deterministically."""

import wave

import pytest

from srstudio import cel, foley

SAMPLES = [cel.Feature(i * 0.25, x, 200.0) for i, x in enumerate([100, 100, 100, 80, 100, 100, 70, 100])]


def test_bursts_fall_where_the_hand_moves_more_than_the_threshold_while_on_the_keyboard():
    assert foley.typing_bursts(SAMPLES, threshold=8.0) == [0.75, 1.0, 1.5, 1.75]
    assert foley.typing_bursts(SAMPLES, threshold=50.0) == []
    assert foley.typing_bursts(SAMPLES, threshold=8.0, spans=[(0.0, 1.0), (1.75, 2.0)]) == [0.75, 1.75]
    with pytest.raises(ValueError, match="threshold"):
        foley.typing_bursts(SAMPLES, threshold=0)


def test_taps_are_a_few_keystrokes_shortly_after_each_burst_and_repeat_for_a_seed():
    a = foley.taps([0.75, 2.0], seed=5)
    assert a == foley.taps([2.0, 0.75], seed=5) and a != foley.taps([0.75, 2.0], seed=6)
    first = [t for t in a if t < 2.0]
    assert 2 <= len(first) <= 4 and 0.77 <= first[0] and first[-1] <= 0.75 + 4 * 0.08
    assert a == sorted(a) and all(t > 2.0 for t in a if t not in first)
    assert foley.taps([]) == []


def test_keystrokes_are_deterministic_bounded_and_levelled(tmp_path):
    a = foley.keystrokes([0.75, 1.0], duration=1.5, rate=8000, seed=7, peak=0.5)
    b = foley.keystrokes([0.75, 1.0], duration=1.5, rate=8000, seed=7, peak=0.5)
    assert a == b and len(a) == 12000
    assert 0.49 <= max(abs(v) for v in a) <= 0.5
    assert all(v == 0 for v in a[: int(0.70 * 8000)])  # silence before the first burst
    assert any(v != 0 for v in a[int(0.75 * 8000) : int(1.0 * 8000)])  # strokes after it
    assert foley.keystrokes([], duration=0.5, rate=8000) == [0.0] * 4000
    with pytest.raises(ValueError, match="duration"):
        foley.keystrokes([0.1], duration=0.05, rate=8000)
    with pytest.raises(ValueError, match="peak"):
        foley.keystrokes([], duration=0.1, rate=8000, peak=1.5)
    path = foley.write_typing(tmp_path / "typing.wav", [0.8, 0.85], duration=2.0, rate=8000, seed=3, peak=0.5)
    with wave.open(str(path), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 8000, 16000)
    with pytest.raises(ValueError, match="rate"):
        foley.write_typing(tmp_path / "x.wav", [0.8], duration=2.0, rate=100, seed=3, peak=0.5)

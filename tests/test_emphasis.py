"""Key words stressed by gain on a recorded clip (srstudio.emphasis)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from srstudio import emphasis, prosody
from srstudio.voice import Word

RATE = 48000
TEXT = ("a", "fish", "expert", "says", "weeks")


def _clip(
    path: Path, levels: dict[str, float] | None = None, silent: str = "", said: tuple[str, ...] = TEXT
) -> list[Word]:
    """Five words (or ``said``), 0.3 s of a voice-like tone each with 0.1 s between, all at one level unless
    ``levels`` says."""
    x, words, at = [], [], 0.05
    x.append(np.zeros(round(at * RATE)))
    for i, text in enumerate(said):
        t = np.arange(round(0.3 * RATE)) / RATE
        amp = 0.0 if text == silent else (levels or {}).get(text, 0.25)
        x.append(amp * np.sin(2 * np.pi * (150 + 10 * i) * t))
        words.append(Word(text, round(at, 6), round(at + 0.3, 6), "word"))
        at += 0.3
        x.append(np.zeros(round(0.1 * RATE)))
        at += 0.1
    pcm = (np.concatenate(x) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return words


def _peak(path: Path) -> int:
    with wave.open(str(path), "rb") as w:
        return int(np.max(np.abs(np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.int32))))


def test_a_flat_word_is_raised_to_the_stress_target(tmp_path):
    wav = tmp_path / "vo.wav"
    words = _clip(wav)
    assert prosody.measure(wav, words, ["weeks"]).stressed[0].db < 1.0
    raised = emphasis.lean(wav, words, ["weeks"])
    got = prosody.measure(wav, words, ["weeks"]).stressed[0]
    assert got.db >= prosody.STRESS_DB
    assert raised["weeks"] >= prosody.STRESS_DB


def test_the_clip_peak_never_rises(tmp_path):
    wav = tmp_path / "vo.wav"
    words = _clip(wav, {"weeks": 0.6})  # already the loudest, so raising it would pass the peak
    before = _peak(wav)
    emphasis.lean(wav, words, ["fish"])
    assert _peak(wav) <= before
    assert prosody.measure(wav, words, ["fish"]).stressed[0].db >= prosody.STRESS_DB


def test_a_word_the_take_already_stresses_is_left_alone(tmp_path):
    wav = tmp_path / "vo.wav"
    words = _clip(wav, {"weeks": 0.6})
    before = wav.read_bytes()
    assert emphasis.lean(wav, words, ["weeks"]) == {"weeks": 0.0}
    assert wav.read_bytes() == before


def test_no_stressed_word_touches_nothing(tmp_path):
    wav = tmp_path / "vo.wav"
    words = _clip(wav)
    before = wav.read_bytes()
    assert emphasis.lean(wav, words, []) == {}
    assert wav.read_bytes() == before


def test_a_stressed_word_not_heard_is_refused(tmp_path):
    wav = tmp_path / "vo.wav"
    words = _clip(wav)
    with pytest.raises(emphasis.EmphasisError, match="months.*not heard"):
        emphasis.lean(wav, words, ["months"])


def test_a_word_said_far_too_flat_is_sent_back_for_a_new_take(tmp_path):
    wav = tmp_path / "vo.wav"
    words = _clip(wav, silent="weeks")  # silence raised is still silence
    before = wav.read_bytes()
    with pytest.raises(emphasis.EmphasisError, match="'weeks' would need .* dB, over 9: take the line again"):
        emphasis.lean(wav, words, ["weeks"])
    assert wav.read_bytes() == before


def test_a_word_still_short_after_the_last_pass_is_refused(tmp_path, monkeypatch):
    wav = tmp_path / "vo.wav"
    words = _clip(wav)
    monkeypatch.setattr(emphasis, "TRIES", 1)
    monkeypatch.setattr(emphasis, "MARGIN", -2.5)  # one pass aimed short of the target
    with pytest.raises(emphasis.EmphasisError, match="could not stress weeks .* dB to 3.0 dB in 1 passes"):
        emphasis.lean(wav, words, ["weeks"])


def test_stereo_is_refused(tmp_path):
    wav = tmp_path / "vo.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"\0\0" * 200)
    with pytest.raises(emphasis.EmphasisError, match="mono 16-bit"):
        emphasis.lean(wav, [Word("a", 0.0, 0.001, "word")], ["a"])


# -- the stressed word is one of the words the line's median is taken from ----------------------------------------
def _down(db: float) -> float:
    """The amplitude ``db`` under the clip's usual word level."""
    return 0.25 * 10 ** (-db / 20)


UNEVEN = dict(zip(TEXT, (_down(i) for i in range(len(TEXT))), strict=True))  # each word 1 dB under the one before


def test_a_two_word_line_whose_stressed_word_starts_under_the_median_lands_on_the_target(tmp_path, monkeypatch):
    wav = tmp_path / "vo.wav"
    words = _clip(wav, {"not": _down(1.5)}, said=("I'm", "not"))  # 1.5 dB under "I'm": 0.75 dB under the median
    assert prosody.measure(wav, words, ["not"]).stressed[0].db < 0
    passes = []
    real = emphasis.measure

    def counted(*args):
        passes.append(1)
        return real(*args)

    monkeypatch.setattr(emphasis, "measure", counted)
    raised = emphasis.lean(wav, words, ["not"])
    assert prosody.measure(wav, words, ["not"]).stressed[0].db >= prosody.STRESS_DB
    assert len(passes) <= emphasis.TRIES
    # the median moves by half the gain: 'not' needs 2 x (3 + 0.5 margin) dB and the 1.5 dB it started under "I'm"
    assert raised["not"] == pytest.approx(8.5, abs=0.1)
    assert raised["not"] <= emphasis.MOST


def test_a_two_word_line_that_needs_more_than_most_in_true_gain_is_refused(tmp_path):
    wav = tmp_path / "vo.wav"
    words = _clip(wav, {"not": _down(4.0)}, said=("I'm", "not"))  # true gain 2 x 3.5 + 4 = 11 dB
    before = wav.read_bytes()
    with pytest.raises(emphasis.EmphasisError, match="'not' would need 11.0 dB, over 9: take the line again"):
        emphasis.lean(wav, words, ["not"])
    assert wav.read_bytes() == before


@pytest.mark.parametrize(
    "levels, word, today",
    [
        (None, "weeks", 3.5),  # the median is another word's level, whatever the gain
        (UNEVEN, "weeks", 6.5),  # raised past the median word, the median moves up one word
        (UNEVEN, "says", 5.5),
    ],
)
def test_a_longer_line_is_raised_as_it_was(tmp_path, levels, word, today):
    wav = tmp_path / "vo.wav"
    words = _clip(wav, levels)
    raised = emphasis.lean(wav, words, [word])
    assert raised[word] == pytest.approx(today, abs=0.1)  # what develop a455e253 raised it by
    assert prosody.measure(wav, words, [word]).stressed[0].db >= prosody.STRESS_DB

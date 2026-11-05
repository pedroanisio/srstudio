"""A synthetic voice clip with word timings, shared by test_emphasis.py and test_stress_mix.py."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

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

"""What test_song.py shares with other test modules."""

from __future__ import annotations

import math
import os
import shutil
import wave
from pathlib import Path

import pytest

from srstudio import song as S
from srstudio.music import Groove, Section

GROOVE = Groove(bpm=120)  # one bar = 2 s


def make_song(**changes) -> S.Song:
    kw: dict = dict(
        slug="test-song",
        title="Test Song",
        seed=7,
        groove=GROOVE,
        voices={
            "pip": S.Singer("bIHbv24MWmeRgasZH58o", "Will", {"stability": 0.3, "similarity_boost": 0.75, "style": 0.4})
        },
        lines=[S.Line("pip", "Sit down.", "SIT DOWN.", (0, 0)), S.Line("pip", "Work.", "WORK.", (1, 0), 1.08)],
        sections=[Section(0, 2)],
        effects=[S.Effect("scratch", "a record scratch", seconds=1.0, longest=0.5, peak=0.5, at=(1, 2))],
        lines_end=GROOVE.at(2),
        voice_note="test voices",
    )
    kw.update(changes)
    return S.Song(**kw)


RATE = 48000


def tone(path: Path, seconds: float, lead: float = 0.1, amplitude: float = 0.5) -> Path:
    """``lead`` seconds of silence, then ``seconds`` of tone, then 0.1 s of silence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_lead, n_on, n_tail = round(lead * RATE), round(seconds * RATE), round(0.1 * RATE)
    samples = [0.0] * n_lead + [amplitude * math.sin(i * 0.05) for i in range(n_on)] + [0.0] * n_tail
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(round(s * 32767).to_bytes(2, "little", signed=True) for s in samples))
    return path


# -- the build, through the engine and a fake ElevenLabs ---------------------------------------------------------
def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    return Path(found)

"""What test_sketch.py shares with other test modules."""

import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from srstudio import music
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Alignment, Transcript, Voice, VoiceSettings

SET = VoiceSettings(0.5, 0.75, 0.3)


SPEAKERS = (
    Speaker("rex", Voice("rex", "IKne3meq5aSn8XLyUdCD", "Charlie"), SET, "dog"),
    Speaker("boss", Voice("boss", "JBFqnCBsd6RMkjVDRZzb", "George"), SET),
)


LINES = (
    Line("rex", "The report is due at nine."),
    Line("boss", "How is it going?"),
    Line("rex", "Great. Almost done."),
)


BEATS = (
    Beat(0.0, "dog", "Due at 9", "wide", "open", "desk", 0, 0),
    Beat(1.5, "dog", "Due at 9", "half", "flat", "type"),
    Beat(3.0, "dog", "How is it going?", "shock", "o", "desk", 1, 0, "buzz"),
    Beat(4.5, "dog", "Great", "half", "grin", "desk", 2, 0),
    Beat(5.5, "dog", "Almost done", "half", "grin", "crossed", 2, 1),
    Beat(7.0, "frog", "", "closed", "none", "face", event="clock:01:00"),
)


SK = Sketch("test-sketch", "Test sketch", SPEAKERS, LINES, BEATS, 9.0)


def with_beats(change):
    return replace(SK, beats=tuple(change(list(BEATS))))


class FakeClient:
    """Says each line as a tone, 0.3 s a word after 0.05 s of silence, and hears back what it is told to."""

    def __init__(self, folder: Path, heard: dict | None = None):
        self.folder, self.heard, self.requests, self.said = folder, heard or {}, [], {}

    def synthesize(self, text, voice, settings):
        self.requests.append((text, voice.name, settings.speed))
        words = len(text.split())
        seconds = 0.3 * words
        rate = 8000
        samples = [0.0] * int(0.05 * rate) + [
            0.5 * math.sin(2 * math.pi * 220 * k / rate) for k in range(int(seconds * rate))
        ]
        wav = self.folder / f"{voice.name}-{len(self.requests)}.wav"
        music.write_wav(wav, samples, rate)
        self.said[wav] = text
        n = len(text)
        starts = tuple(round(0.05 + k * seconds / n, 6) for k in range(n))
        ends = tuple(round(s + seconds / n, 6) for s in starts)
        return SimpleNamespace(wav=wav, alignment=Alignment(tuple(text), starts, ends))

    def transcribe(self, audio, language="en"):
        text = self.said[Path(audio)]
        return Transcript("en", 1.0, self.heard.get(text, text), ())


def confirm_stub(cache, key, voice):
    return {"voice_id": voice.id, "name": f"{voice.name} - premade", "category": "premade"}

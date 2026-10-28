"""Offline stand-ins for the ElevenLabs HTTP endpoints, shared by the provider tests.

The fakes answer at the transport boundary only: everything above it (parse, decode, verify,
cache, speech check) is the real code. Audio is a real MP3 made by ffmpeg.
"""

from __future__ import annotations

import base64
import shutil
import subprocess
from pathlib import Path

import pytest

ffmpeg_required = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is required to decode audio")


def make_mp3(path: Path, seconds: float = 1.05, frequency: int = 220) -> bytes:
    """A tone of ``seconds`` as MP3 at ``path``; returns its bytes."""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration={seconds}"]
        + ["-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k", str(path)],
        check=True,
    )
    return path.read_bytes()


def alignment(text: str, step: float = 0.07) -> dict:
    n = len(text)
    return {
        "characters": list(text),
        "character_start_times_seconds": [round(i * step, 3) for i in range(n)],
        "character_end_times_seconds": [round((i + 1) * step, 3) for i in range(n)],
    }


def transcript_body(text: str) -> dict:
    words = []
    for i, w in enumerate(text.split()):
        if i:
            words.append({"text": " ", "start": i * 0.2 - 0.05, "end": i * 0.2, "type": "spacing"})
        words.append({"text": w, "start": i * 0.2, "end": i * 0.2 + 0.15, "type": "word", "logprob": -0.1})
    return {
        "language_code": "eng",
        "language_probability": 0.99,
        "text": text,
        "words": words,
        "transcription_id": "t-1",
    }


class FakeElevenLabs:
    """The three endpoints. Speech aligns to the requested text; the recogniser hears ``heard``
    (default: the last text spoken), so a test can make it mishear."""

    def __init__(self, speech_mp3: bytes | dict[str, bytes], effect_mp3: bytes = b"", heard: str | None = None):
        # one MP3 for every line, or one per line text (identical audio shares a cached transcript)
        self.speech_mp3, self.effect_mp3, self.heard = speech_mp3, effect_mp3, heard
        self.calls: list[tuple[str, object]] = []
        self.last_text = ""

    def tts(self, url, payload, headers):
        self.calls.append(("tts", payload))
        self.last_text = payload["text"]
        audio = self.speech_mp3[payload["text"]] if isinstance(self.speech_mp3, dict) else self.speech_mp3
        body = {
            "audio_base64": base64.b64encode(audio).decode(),
            "alignment": alignment(payload["text"]),
            "normalized_alignment": alignment(payload["text"]),
        }
        return body, "tts-1"

    def binary(self, url, payload, headers):
        self.calls.append(("sfx", payload))
        return self.effect_mp3, "sfx-1"

    def multipart(self, url, fields, files, headers):
        self.calls.append(("stt", fields))
        return transcript_body(self.heard if self.heard is not None else self.last_text), "stt-1"

    def transports(self) -> dict:
        return {"transport": self.tts, "binary_transport": self.binary, "multipart_transport": self.multipart}

"""What test_generated.py shares with other test modules."""

from __future__ import annotations

import wave
from pathlib import Path

from srstudio.generated import Generated

SQUEAK = Generated(
    id="squeak",
    kind="sound-effect",
    provider="srstudio-elevenlabs",
    model="elevenlabs-sound-generation",
    prompt="a chair squeak",
    duration=1.0,
    cache="assets/generated/squeak.wav",
)


SPEECH = Generated(
    id="line-1",
    kind="speech",
    provider="srstudio-elevenlabs",
    model="eleven_multilingual_v2",
    prompt="In your chair.",
    voice="bIHbv24MWmeRgasZH58o?stability=0.42&similarity_boost=0.75&style=0.24&speed=1.0&use_speaker_boost=true",
    language="en",
    seed=52026,
    cache="assets/generated/line-1.wav",
)


def write_wav(path: Path, samples: list[float], rate: int = 48000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(int(max(-1, min(1, s)) * 32767).to_bytes(2, "little", signed=True) for s in samples))
    return path

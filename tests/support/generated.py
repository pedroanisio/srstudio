"""What test_generated.py shares with other test modules."""

from __future__ import annotations

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

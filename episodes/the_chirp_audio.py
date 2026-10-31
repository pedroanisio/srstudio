#!/usr/bin/env python3
"""Stick 15 — The Chirp: who says what, on one take timeline, and how the husband and the wife play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_chirp_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. There is no music bed; the chirps are synthesized at build, in :mod:`srstudio.foley`.

Arm A of the first-second test: the opening is held frozen, silent and uncaptioned for :data:`HELD` seconds. The
birdsong is one recording, played under the whole yard.
"""

from __future__ import annotations

import sys

from srstudio import takes
from srstudio.voice import Voice, VoiceSettings

HELD = 1.4  # seconds of the first frame, frozen, before anything moves or sounds
SETTING = VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0)
ASLEEP = VoiceSettings(stability=0.75, similarity_boost=0.75, style=0.1, speed=0.9)
BIRDS = "Birdsong at dawn in a quiet back garden, gentle and even, no voices, no music"
BIRD_SECONDS = 3.0


def _fx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=0.4)  # fmt: skip


SCRIPT = takes.Script(
    title="The Chirp",
    seed=3109,
    still=HELD,
    voice_note="Premade voices: Will is the husband and Jessica is the wife, who does not wake up to say it.",
    voices={
        "husband": Voice(role="husband", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "wife": Voice(role="wife", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    },
    settings={"husband": SETTING, "wife": ASLEEP},
    takes=(
        takes.Take("01", "husband", "Battery is out.", 3.1, shot="night", mood="calm"),
        takes.Take("02", "wife", "There's another one.", 0.7, shot="night", mood="calm"),
        takes.Take("03", "husband", "That's all five.", 3.0, shot="heap", mood="happy"),
        takes.Take("04", "husband", "Do it in there.", 0.3, shot="fridge", mood="firm"),
        _fx(5, "[SHUT]", 2.9, "shut", "A heavy freezer door slammed shut, one thud, dry, no voices, no music", 0.6),
        _fx(6, "[BIRDS]", 0.0, "yard", BIRDS, BIRD_SECONDS),
        takes.Take("07", "husband", "Rest now.", 2.0, shot="yard", mood="calm"),
        _fx(8, "[BIRDS]", 0.0, "yard", BIRDS, BIRD_SECONDS),
    ),
)

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

#!/usr/bin/env python3
"""Stick 16 — What's Your Split: who says what, on one take timeline, and how the trainer and the member play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 whats_your_split_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. There is no music bed.

The first line waits :data:`HELD` seconds, silent and uncaptioned, while the trainer strides in and takes the wrist.
"""

from __future__ import annotations

import sys

from srstudio import takes
from srstudio.voice import Voice, VoiceSettings

HELD = 1.2  # seconds of silence before the first line
TRAINER_SETTING = VoiceSettings(stability=0.4, similarity_boost=0.75, style=0.45, speed=1.05)
MEMBER_SETTING = VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15, speed=0.95)
PING = "One soft phone message notification ping, close, dry, no voices, no music"


def _fx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=0.4)  # fmt: skip


SCRIPT = takes.Script(
    title="What's Your Split",
    seed=3115,
    still=HELD,
    voice_note="Premade voices: Callum is the trainer, who is delighted, and Roger is the member, who is not.",
    voices={
        "trainer": Voice(role="trainer", id="N2lVS1w4EtoT3dr4eOWO", name="Callum"),
        "member": Voice(role="member", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
    },
    settings={"trainer": TRAINER_SETTING, "member": MEMBER_SETTING},
    takes=(
        takes.Take("01", "trainer", "Bro. Four hours of cardio a day?", 0.25, shot="desk", mood="happy"),
        takes.Take("02", "member", "I suppose.", 0.2, shot="desk", mood="calm"),
        takes.Take("03", "trainer", "What's your split?", 0.2, shot="desk", mood="happy"),
        takes.Take("04", "member", "Mornings I check my bank balance.", 0.2, shot="desk", mood="calm"),
        takes.Take("05", "trainer", "Love it. Evenings?", 0.2, shot="desk", mood="happy"),
        takes.Take("06", "member", "I remember something I said in high school.", 0.2, shot="desk", mood="calm"),
        takes.Take("07", "trainer", "Brutal. How long do you hold it?", 0.2, shot="desk", mood="happy"),
        takes.Take("08", "member", "Till about four.", 0.2, shot="desk", mood="calm"),
        takes.Take("09", "trainer", "Beast.", 0.3, shot="desk", mood="happy"),
        _fx(10, "[BUZZ]", 0.2, "buzz", "A phone buzzing twice on vibrate, close, dry, no voices, no music", 0.7),
        _fx(11, "[PING]", 0.6, "mom", PING, 0.6),
        takes.Take("12", "trainer", "I got you. Breathe. Open it.", 0.2, shot="spot", mood="firm"),
        takes.Take("13", "member", "I can't.", 0.2, shot="spot", mood="firm"),
        takes.Take("14", "trainer", "Yes you can! Light weight! Open it!", 0.2, shot="spot", mood="firm"),
        _fx(15, "[BEEPS]", 0.0, "spot", "A smartwatch beeping fast and rising, close, dry, no voices, no music", 0.9),
        _fx(16, "[PING]", 1.2, "dog", PING, 0.6),  # six words, the payoff: time to read them
        _fx(17, "[SINK]", 0.2, "sink", "A body slowly sinking onto a gym mat, soft creak, dry, no voices", 1.6),
        takes.Take("18", "trainer", "That's the pump!", 0.25, shot="floor", mood="happy"),
        _fx(19, "[BEST]", 0.3, "best", "A cheerful three note smartwatch achievement chime, dry, no voices", 1.2),
    ),
)

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

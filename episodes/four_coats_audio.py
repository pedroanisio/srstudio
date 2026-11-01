#!/usr/bin/env python3
"""Stick 14 — Four Coats: who says what, on one take timeline, and how the traveler and the agent play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 four_coats_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. There is no music bed.

Arm B of the first-second test: the bag lands on the scale on frame one, with no held opening. The traveler's second
voice is the same premade voice held steadier, through every coat she owns.
"""

from __future__ import annotations

import sys

from srstudio import takes
from srstudio.voice import Voice, VoiceSettings

AGENT_SETTING = VoiceSettings(stability=0.7, similarity_boost=0.75, style=0.1, speed=1.0)
TRAVELER_SETTING = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
MUFFLED_SETTING = VoiceSettings(stability=0.85, similarity_boost=0.75, style=0.0, speed=0.9)


def _fx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=0.4)  # fmt: skip


SCRIPT = takes.Script(
    title="Four Coats",
    seed=3104,
    voice_note="Premade voices: Laura is the traveler, muffled by her own coats at the end, and Roger is the agent.",
    voices={
        "traveler": Voice(role="traveler", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"),
        "muffled": Voice(role="muffled", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"),
        "agent": Voice(role="agent", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
    },
    settings={"traveler": TRAVELER_SETTING, "muffled": MUFFLED_SETTING, "agent": AGENT_SETTING},
    takes=(
        _fx(1, "[THUD]", 0.1, "gate", "A heavy suitcase dropped flat on a metal scale, one thud, dry, no voices", 0.6),
        takes.Take("02", "agent", "23.4.", 0.15, shot="gate", mood="calm"),
        # accepted by arc4d3, Slack 1793499862.755999: the recognizer drops the dollars
        takes.Take("03", "agent", "$60.", 0.35, shot="gate", mood="calm", heard=("Sixty",)),
        takes.Take("04", "traveler", "For point four?", 0.3, shot="gate", mood="firm"),
        takes.Take("05", "agent", "It's policy.", 0.55, shot="gate", mood="calm"),
        _fx(
            6, "[ZIP]", 0.0, "gate", "A suitcase zip pulled fast, then a coat pulled on, dry, no voices, no music", 1.0
        ),
        takes.Take("07", "agent", "23.3.", 0.3, shot="gate", mood="calm"),
        _fx(8, "[RUSTLE]", 0.0, "gate", "Frantic rustling of clothes being pulled on, fast, dry, no voices", 1.6),
        takes.Take("09", "agent", "23.1.", 0.3, shot="gate", mood="calm"),
        _fx(10, "[STUFF]", 0.0, "gate", "Heavy fabric stuffed and stretched, seams creak, dry, no voices", 1.8),
        takes.Take("11", "agent", "22.9.", 0.15, shot="gate", mood="calm"),
        takes.Take("12", "agent", "You're good.", 0.4, shot="gate", mood="calm"),
        takes.Take("13", "muffled", "Thank you.", 0.15, shot="gate", mood="calm"),
        _fx(
            14, "[SHUFFLE]", 0.1, "gate", "Three slow heavy padded footsteps, one by one, dry, no voices, no music", 1.5
        ),
        takes.Take("15", "agent", "We've lost your bag. I'm so sorry.", 1.5, shot="arrivals", mood="calm"),
        takes.Take("16", "traveler", "I'm wearing it.", 0.7, shot="arrivals", mood="happy"),
    ),
)

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

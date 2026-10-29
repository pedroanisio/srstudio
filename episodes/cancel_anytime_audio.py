#!/usr/bin/env python3
"""Stick 06 — Cancel Anytime: Theo, Brooke at the front desk and the gym's music, as one take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 cancel_anytime_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and
verified, speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names.
The bed is composed by the ElevenLabs Music API (:data:`BED`, pinned by its seed); speech-to-text must hear no
words in it, and it is cut to the episode with a fade. The key comes from ``ELEVENLABS_API_KEY`` and is never
written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard
takes, a bed with words and malformed scripts; ``tests/test_cancel_anytime.py`` checks this script.

Theo wants to cancel his gym membership. In person: he is here. On a Tuesday: it is Tuesday. Before sunrise: it
is still dark. With a note from his trainer, whom he has never met; the trainer has met him, and is disappointed.
Any other way? A death certificate. Whose? They are flexible. Then the sun comes up.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio.compose import Chunk, Plan
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("wide", "theo", "brooke", "sign")
POLO = "#e85d3f"  # the gym's staff polo
THEO = stick.Look(hair="bald", glasses=True)
BROOKE = stick.Look(hair="spiky", apron=POLO)
SIGN = "CANCEL ANYTIME*"
FINE = "*In person, Tuesdays, before sunrise, with a trainer's note"
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "Leg day",
                40.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "upbeat gym workout pop",
                    "steady kick on every beat",
                    "punchy synth bass and bright claps",
                    "relentlessly motivational",
                ),  # fmt: skip
                (),
                NEG,
            ),
        )
    ),
    seed=40511,
    bpm=120,
    gain_db=-18.0,
    fade=0.8,
)
SCRIPT = takes.Script(
    title="Cancel Anytime — Stick 06",
    seed=1055,
    voices={
        "theo": Voice(role="theo", id="N2lVS1w4EtoT3dr4eOWO", name="Callum"),
        "brooke": Voice(role="brooke", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    },
    settings={
        "theo": VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.25, speed=1.0),
        "brooke": VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45, speed=1.05),
    },
    takes=(
        takes.Take("01", "theo", "How do I cancel my membership?", 0.20, shot="wide", mood="calm"),
        takes.Take("02", "brooke", "Easy! In person.", 0.40, shot="brooke", mood="happy"),
        takes.Take("03", "theo", "I'm here. In person.", 0.15, shot="theo", mood="firm"),
        takes.Take("04", "brooke", "On a Tuesday.", 0.15, shot="brooke", mood="happy"),
        takes.Take("05", "theo", "It's Tuesday.", 0.15, shot="theo", mood="firm"),
        takes.Take("06", "brooke", "Before sunrise.", 0.15, shot="brooke", mood="happy"),
        takes.Take("07", "theo", "It's still dark.", 0.40, shot="wide", mood="firm"),
        takes.Take("08", "brooke", "With a note from your trainer.", 0.80, shot="brooke", mood="happy"),
        takes.Take("09", "theo", "I've never met my trainer.", 0.40, shot="theo", mood="calm"),
        takes.Take("10", "brooke", "He's met you. He's very disappointed.", 0.60, shot="brooke", mood="calm"),
        takes.Take("11", "theo", "Is there any other way?", 1.30, shot="theo", mood="calm"),  # the hold
        takes.Take("12", "brooke", "A death certificate.", 0.30, shot="brooke", mood="happy"),
        takes.Take("13", "theo", "Whose?", 0.60, shot="theo", mood="calm"),
        takes.Take("14", "brooke", "We're flexible.", 0.50, shot="brooke", mood="happy"),
        takes.Take("15", "brooke", "Oh no. Sunrise.", 0.40, shot="wide", mood="calm"),
        takes.Take("16", "brooke", "See you next week!", 1.60, shot="sign", mood="happy"),
    ),
    voice_note="ElevenLabs premade voices Callum and Jessica; no reference-voice cloning. Instrumental music bed "
    "composed with the ElevenLabs Music API.",
    shots=SHOTS,
    bed=BED,
)
SUNRISE = "15"  # the take whose start the sun comes up at: the window turns over stick_gym.DAWN seconds


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

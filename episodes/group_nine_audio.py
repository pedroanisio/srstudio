#!/usr/bin/env python3
"""Stick 08 — Group 9: a passenger, the gate agent and a lounge bed, as one take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 group_nine_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and
verified, speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names.
The bed is composed by the ElevenLabs Music API (:data:`BED`, pinned by its seed); speech-to-text must hear no
words in it, and it is cut to the episode with a fade. The key comes from ``ELEVENLABS_API_KEY`` and is never
written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard
takes, a bed with words and malformed scripts; ``tests/test_group_nine.py`` checks this script.

At the gate, Sam asks if Group 9 is boarding. After the luggage: his bag is Group 4, and it is doing great. Group 8
costs extra, same seat, you just board feeling chosen. The plane can't leave without him? Everyone says that. He
puts on his cap: he's the pilot. Pilots are Group 9. In the cabin, a chime, and the captain speaks from the middle
seat, both armrests taken.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio.compose import Chunk, Plan
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("wide", "sam", "agent", "bag", "cabin")
NAVY = "#1f2a44"
SAM = stick.Look(hair="side-part", tie=NAVY)  # a navy tie: the uniform, before the cap goes on
PILOT = stick.Look(hair="side-part", tie=NAVY, cap=NAVY)
AGENT = stick.Look(hair="bun", tie="#c0453b")  # the airline's red scarf
NEIGHBOURS = (stick.Look(hair="spiky", glasses=True), stick.Look(hair="bald"))  # window seat, aisle seat
GATE, ROW, SEATS, BAG_TAG = "B9", "38", "DEF", "GROUP 4"
BAG_X = 420  # the carry-on's middle on the gate floor: its tag hangs clear of the podium
CAPPED = "09"  # the take he puts the cap on, and every take after it
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "Departure lounge",
                40.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "laid-back airport lounge pop",
                    "soft electric piano and a straight four-on-the-floor groove",
                    "steady kick on every beat",
                    "polite and a little smug",
                ),  # fmt: skip
                (),
                NEG,
            ),
        )
    ),
    seed=40808,
    bpm=120,
    gain_db=-19.0,
    fade=0.8,
)
SCRIPT = takes.Script(
    title="Group 9 — Stick 08",
    seed=1120,
    voices={
        "sam": Voice(role="sam", id="TX3LPaxmHKxFdv7VOQHJ", name="Liam"),
        "agent": Voice(role="agent", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    },
    settings={
        "sam": VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.30, speed=1.0),
        "agent": VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.20, speed=1.0),
    },
    takes=(
        takes.Take("01", "sam", "Is Group 9 boarding yet?", 0.30, shot="wide", mood="question"),
        takes.Take("02", "agent", "Group 9 boards after the luggage.", 0.30, shot="agent", mood="calm"),
        takes.Take("03", "sam", "After the luggage?", 0.30, shot="sam", mood="question"),
        takes.Take("04", "agent", "Your bag is Group 4. It's doing great.", 0.40, shot="bag", mood="happy"),
        takes.Take("05", "sam", "Can I upgrade?", 0.30, shot="sam", mood="calm"),
        takes.Take(
            "06",
            "agent",
            "Group 8 costs extra. Same seat. You just board feeling chosen.",
            0.40,
            shot="agent",
            mood="calm",
        ),  # fmt: skip
        takes.Take("07", "sam", "The plane can't leave without me.", 0.30, shot="sam", mood="firm"),
        takes.Take("08", "agent", "Everyone says that.", 0.40, shot="agent", mood="calm"),
        takes.Take("09", "sam", "I'm the pilot.", 1.30, shot="sam", mood="firm"),  # the hold
        takes.Take("10", "agent", "Pilots are Group 9.", 0.60, shot="wide", mood="calm"),
        takes.Take(
            "11",
            "sfx",
            "[CABIN CHIME]",
            0.20,
            shot="cabin",
            prompt="A single airplane cabin announcement chime, two soft bell tones, clean, no voices, no music",
            seconds=1.0,
            longest=0.9,
            peak=0.45,
        ),
        takes.Take(
            "12", "sam", "This is your captain, speaking from the middle seat.", 1.60, shot="cabin", mood="calm"
        ),  # fmt: skip
    ),
    voice_note="ElevenLabs premade voices Liam and Matilda; no reference-voice cloning. One effect generated with "
    "ElevenLabs; instrumental music bed composed with the ElevenLabs Music API.",
    shots=SHOTS,
    bed=BED,
)
# What the boarding sign calls in each gate take; a take without an entry keeps the last one before it.
NOW = {"01": "GROUP 1", "02": "GROUP 2", "04": "GROUP 4", "06": "GROUP 6", "08": "GROUP 8", "10": "GROUP 9"}


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

#!/usr/bin/env python3
"""Stick 05 — The Viewing: Dev, the agent, Gary and a breezy showcase bed, as one take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_viewing_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and
verified, speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names,
and the effect is length-checked. The bed is composed by the ElevenLabs Music API (:data:`BED`, pinned by its
seed); speech-to-text must hear no words in it, and it is cut to the episode with a fade. The key comes from
``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes, a bed with words and malformed scripts;
``tests/test_the_viewing.py`` checks this script and the staging.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio.compose import Chunk, Plan
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("kitchen", "wide", "window", "dev", "agent", "bed")
DEV = stick.Look()
AGENT = stick.Look(hair="side-part", glasses=True, tie="#7a1f3d")
GARY = stick.Look(hair="spiky")
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "Open house",
                34.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "breezy lounge house for a real-estate showcase",
                    "steady kick on every beat",
                    "four-on-the-floor kick, soft hi-hat on the offbeats",
                    "warm electric piano and muted trumpet",
                    "smug and aspirational",
                ),  # fmt: skip
                (),
                NEG,
            ),
        )
    ),
    seed=50511,
    bpm=120,
    gain_db=-17.0,
    fade=0.8,
)
SCRIPT = takes.Script(
    title="The Viewing — Stick 05",
    seed=1055,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "agent": Voice(role="agent", id="pFZP5JQG7iQjIQuC4Bku", name="Lily"),
        "gary": Voice(role="gary", id="N2lVS1w4EtoT3dr4eOWO", name="Callum"),
    },
    settings={
        "dev": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
        "agent": VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.45, speed=1.04),
        "gary": VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.1, speed=0.88),
    },
    takes=(
        takes.Take("01", "dev", "Is that a toilet in the kitchen?", 0.50, shot="kitchen", mood="calm"),
        takes.Take("02", "agent", "Open plan. You can cook and multitask.", 0.30, shot="agent", mood="happy"),
        takes.Take("03", "dev", "The window's painted on.", 0.50, shot="window", mood="calm"),
        takes.Take("04", "agent", "So the view never changes. Stability.", 0.30, shot="agent", mood="happy"),
        takes.Take("05", "dev", "Where's the bed?", 0.20, shot="dev", mood="calm"),
        takes.Take("06", "agent", "It folds down.", 0.10, shot="bed", mood="happy"),
        takes.Take(
            "07",
            "sfx",
            "[THUD]",
            0.30,
            shot="bed",
            prompt="A heavy wooden fold-down wall bed dropping onto a wooden floor, one solid thud with a short "
            "spring creak, dry room, no voices, no music",
            seconds=1.0,
            longest=0.9,
            peak=0.5,
        ),
        takes.Take("08", "agent", "That's Gary. He comes with the lease.", 0.70, shot="bed", mood="happy"),
        takes.Take("09", "dev", "How much?", 0.20, shot="dev", mood="calm"),
        takes.Take("10", "agent", "Two grand a month. Each.", 1.30, shot="agent", mood="happy"),
        takes.Take("11", "dev", "I'll take it.", 0.30, shot="dev", mood="calm"),
        takes.Take("12", "agent", "Wonderful. You're applicant forty-seven.", 1.20, shot="wide", mood="happy"),
        takes.Take("13", "gary", "Forty-six.", 0.90, shot="bed", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Will, Lily and Callum; no reference-voice cloning. Instrumental music "
    "bed composed with the ElevenLabs Music API.",
    shots=SHOTS,
    bed=BED,
)
DROP = ("07", 0.04)  # the take, and the second in it, at which the bed comes down
GARY_TALKS = "13"  # the take in which Gary answers in his sleep


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

#!/usr/bin/env python3
"""Stick 03 — Repeat After Me: Dev's vows, the phone, the confession and a music bed, as one take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 repeat_after_me_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and
verified, speech-to-text must hear the scripted words, the voice id must resolve to the premade voice Will, and
the effect is length-checked. The bed is composed by the ElevenLabs Music API (:data:`BED`, pinned by its seed);
speech-to-text must hear no words in it, and it is cut to the episode with a fade. ``timeline.json`` lists the
takes with their word and character timings, which Dev's mouth and the word captions follow. The key comes from
``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes, a bed with words and malformed scripts;
``tests/test_repeat_after_me.py`` checks this script.
"""

from __future__ import annotations

import sys

from srstudio import takes
from srstudio.compose import Chunk, Plan
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("drive", "push", "close", "seat")
VOW = "I will not check my email on the drive home."
LEAVE = "I will leave work at work."
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "Commute",
                16.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "breezy lo-fi pop on a car radio",
                    "steady kick on every beat",
                    "warm electric piano chords",
                    "light shaker",
                    "easygoing and a little smug",
                ),  # fmt: skip
                (),
                NEG,
            ),
        )
    ),
    seed=30318,
    bpm=120,
    gain_db=-15.0,
    fade=0.8,
)
SCRIPT = takes.Script(
    title="Repeat After Me — Stick 03",
    seed=1031,
    voices={"dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will")},
    settings={"dev": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0)},
    takes=(
        takes.Take("01", "dev", "Repeat after me.", 0.30, shot="drive", mood="calm"),
        takes.Take("02", "dev", VOW, 0.16, shot="drive", mood="calm"),
        takes.Take("03", "dev", VOW, 0.20, shot="push", mood="firm", speed=1.08),  # the second time, firmer
        takes.Take("04", "dev", LEAVE, 0.14, shot="close", mood="firm"),
        takes.Take("05", "dev", LEAVE, 0.30, shot="close", mood="firm", speed=1.1),
        takes.Take(
            "06",
            "sfx",
            "[BZZT]",
            0.05,
            shot="seat",
            prompt="A smartphone vibrating twice on a car seat, two short buzzes, dry, no voices, no music",
            seconds=1.0,
            longest=0.7,
            peak=0.45,
        ),
        takes.Take("07", "dev", "I answered forty emails at red lights.", 0.40, shot="seat", mood="happy"),
        takes.Take("08", "dev", "Now repeat after me.", 0.70, shot="drive", mood="calm"),
    ),
    voice_note="ElevenLabs premade voice Will; no reference-voice cloning. Instrumental music bed composed with "
    "the ElevenLabs Music API.",
    shots=SHOTS,
    bed=BED,
)


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

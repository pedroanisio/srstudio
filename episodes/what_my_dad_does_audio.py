#!/usr/bin/env python3
"""Stick 07 — What My Dad Does: Dev, his son's teacher and a school-night bed, as one take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 what_my_dad_does_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and
verified, speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names.
The bed is composed by the ElevenLabs Music API (:data:`BED`, pinned by its seed); speech-to-text must hear no
words in it, and it is cut to the episode with a fade. The key comes from ``ELEVENLABS_API_KEY`` and is never
written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard
takes, a bed with words and malformed scripts; ``tests/test_what_my_dad_does.py`` checks this script.

Parent-teacher night. Dev perches on a child's chair while Ms. Reyes reads his son's essay, What My Dad Does: he
works from home, a tie on top and no pants; his job is saying "I think you're on mute"; at three he has Focus Time,
and Focus Time snores. Dev has an answer for each. The last line: Dad says he works from home. Mom says he's just
home. What did he get? An A. His mom helped.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio.compose import Chunk, Plan
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("wide", "dev", "teacher", "essay")
DEV = stick.Look(tie="#c0453b")  # he came straight from a call: the tie is on
TEACHER = stick.Look(hair="bun", glasses=True)
TITLE, BY = "WHAT MY DAD DOES", "by Max, age 8"
LINES = (
    "My dad works from home.",
    "He wears a tie on top. No pants.",
    "His job is saying: I think your on mute.",
    "At 3 he has Focus Time. Focus Time snores.",
    "Dad says he works from home.",
    "Mom says he is just home.",
)
GRADE, NOTE = "A", "Edited by Mom"
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "Open house",
                40.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "playful pizzicato strings and glockenspiel",
                    "steady kick on every beat",
                    "light school-play comedy underscore",
                    "innocent and a little sly",
                ),  # fmt: skip
                (),
                NEG,
            ),
        )
    ),
    seed=40719,
    bpm=120,
    gain_db=-19.0,
    fade=0.8,
)
SCRIPT = takes.Script(
    title="What My Dad Does — Stick 07",
    seed=1119,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "teacher": Voice(role="teacher", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"),
    },
    settings={
        "dev": VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.30, speed=1.0),
        "teacher": VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.20, speed=1.0),
    },
    takes=(
        takes.Take("01", "teacher", "Have you read Max's essay? What My Dad Does.", 0.30, shot="wide", mood="calm"),
        takes.Take("02", "dev", "Oh! Read it to me.", 0.30, shot="dev", mood="happy"),
        takes.Take(
            "03", "teacher", "My dad works from home. He wears a tie on top. No pants.", 0.40, shot="essay", mood="calm"
        ),  # fmt: skip
        takes.Take("04", "dev", "Business on top.", 0.30, shot="dev", mood="firm"),
        takes.Take("05", "teacher", "His job is saying: I think you're on mute.", 0.40, shot="essay", mood="calm"),
        takes.Take("06", "dev", "That's leadership.", 0.30, shot="dev", mood="firm"),
        takes.Take(
            "07", "teacher", "At three, he has Focus Time. Focus Time snores.", 0.40, shot="essay", mood="calm"
        ),  # fmt: skip
        takes.Take("08", "dev", "That's deep work.", 0.40, shot="wide", mood="firm"),
        takes.Take("09", "teacher", "Last line.", 0.30, shot="teacher", mood="calm"),
        takes.Take("10", "teacher", "Dad says he works from home.", 1.30, shot="essay", mood="calm"),  # the hold
        takes.Take("11", "teacher", "Mom says he's just home.", 0.20, shot="essay", mood="calm"),
        takes.Take(
            "12",
            "sfx",
            "[CHALK SQUEAK]",
            0.90,
            shot="dev",
            prompt="A single short squeak of chalk on a school chalkboard, dry and sharp, no voices, no music",
            seconds=0.8,
            longest=0.6,
            peak=0.45,
        ),
        takes.Take("13", "dev", "What grade did he get?", 0.30, shot="dev", mood="calm"),
        takes.Take("14", "teacher", "He got an A. His mom helped.", 1.80, shot="essay", mood="happy"),
    ),
    voice_note="ElevenLabs premade voices Will and Sarah; no reference-voice cloning. One effect generated with "
    "ElevenLabs; instrumental music bed composed with the ElevenLabs Music API.",
    shots=SHOTS,
    bed=BED,
)
# essay take: (lines shown, line marked, the spoken word the highlighter starts on)
PAGES: dict[str, tuple[int, int | None, str]] = {
    "03": (2, 1, "He"),
    "05": (3, 2, "His"),
    "07": (4, 3, "At"),
    "10": (5, 4, "Dad"),
    "11": (6, 5, "Mom"),
    "14": (6, None, ""),
}
GRADED = "14"  # the take that turns the page to its grade and its margin note
NOTE_WORD = "mom"  # the note appears as she says it


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

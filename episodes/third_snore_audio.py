#!/usr/bin/env python3
"""Stick 15 — Third Snore: who says what on one take timeline, what the phone plays, and how they play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 third_snore_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_third_snore.py`` checks this script. There is no music bed.

Each swears the other one snores, and the phone that settles it proves more than either of them wanted. Arm B of the
first-second test: the camera is already pushing in on frame 1.
"""

from __future__ import annotations

import sys

from srstudio import stick, stick_windshield, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("close", "pull", "wide")
HOOK = "3 a.m. The snoring argument."
SCRIPT = takes.Script(
    title="Third Snore — Stick 15",
    seed=3122,
    voices={
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "gary": Voice(role="gary", id="N2lVS1w4EtoT3dr4eOWO", name="Callum"),
    },
    settings={
        "noor": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
        "dev": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
        "gary": VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.1, speed=0.88),
    },
    takes=(
        takes.Take("01", "noor", "You snore.", 0.20, shot="close", mood="firm"),
        takes.Take("02", "dev", "I do not snore.", 0.20, shot="close", mood="firm"),
        takes.Take("03", "noor", "I recorded you.", 0.30, shot="close", mood="calm"),
        takes.Take(
            "04",
            "sfx",
            "[SNORE ONE]",
            0.1,
            shot="close",
            prompt="One long deep rasping human snore like a saw through wood, recorded on a phone, dry, no voices, "
            "no music",
            seconds=1.8,
            longest=1.8,
            peak=0.5,
        ),
        takes.Take("05", "noor", "That's you.", 0.20, shot="close", mood="happy"),
        takes.Take(
            "06",
            "sfx",
            "[SNORE TWO]",
            0.1,
            shot="close",
            prompt="One high thin whistling human snore through the nose, recorded on a phone, dry, no voices, "
            "no music",
            seconds=1.5,
            longest=1.5,
            peak=0.5,
        ),
        takes.Take("07", "dev", "That's you.", 0.40, shot="close", mood="happy"),
        takes.Take(
            "08",
            "sfx",
            "[SNORE THREE]",
            2.1,
            shot="close",
            prompt="One very low slow contented human snore, a long rumbling breath in and out, recorded on a phone, "
            "dry, no voices, no music",
            seconds=2.2,
            longest=2.2,
            peak=0.5,
        ),
        takes.Take("09", "noor", "Who's that?", 2.3, shot="pull", mood="calm"),
        takes.Take("10", "dev", "That's Gary.", 0.25, shot="wide", mood="calm"),
        takes.Take("11", "noor", "Who's Gary?", 0.25, shot="wide", mood="firm"),
        takes.Take("12", "dev", "He came with the flat.", 1.5, shot="wide", mood="calm"),
        takes.Take("13", "gary", "You both snore.", 0.15, shot="wide", mood="calm"),
        takes.Take(
            "14",
            "sfx",
            "[SNORT]",
            0.25,
            shot="wide",
            prompt="One short sharp human snort in the middle of sleep, dry, no voices, no music",
            seconds=0.6,
            longest=0.6,
            peak=0.55,
        ),
    ),
    voice_note="ElevenLabs premade voices Jessica, Will and Callum; no reference-voice cloning. Effects generated "
    "with ElevenLabs.",
    shots=SHOTS,
)

F = stick.Face
TO_HER, TO_HIM = (1.0, 0.0), (1.0, 0.0)  # both mirrored into the bed: +x looks at the other one
DOWN = (0.8, 0.8)  # at the phone
NOOR, DEV = stick_windshield.NOOR, stick.PLAIN
GARY = stick.Look(hair="spiky")  # the man who came with the flat, as drawn in The Viewing
# take: [(seconds into the take, pose from stick_bed.BED, face)]; a take without a row holds the last pose
PARTS: dict[str, dict[str, list[tuple[float, str, stick.Face]]]] = {
    "noor": {
        "01": [(0, "cross", F("half", "angry", "flat", TO_HIM))],
        "03": [(0, "point", F("open", "raised", "smirk", DOWN))],
        "04": [(0, "point", F("open", "raised", "smile", TO_HIM))],
        "05": [(0, "cross", F("happy", "raised", "smile", TO_HIM))],
        "06": [(0, "cross", F("wide", "worried", "flat", DOWN))],
        "07": [(0, "cross", F("half", "angry", "frown", TO_HIM))],
        "08": [(0, "cross", F("happy", "raised", "smile", TO_HIM)), (1.0, "cross", F("open", "raised", "flat", DOWN)),
               (2.6, "sit", F("wide", "raised", "flat", DOWN))],
        "09": [(0, "sit", F("wide", "worried", "flat", DOWN))],
        "10": [(0, "sit", F("wide", "worried", "flat", TO_HIM))],
        "11": [(0, "point", F("wide", "raised", "flat", TO_HIM))],
        "12": [(0, "sit", F("half", "flat", "flat", TO_HIM))],
        "13": [(0, "sit", F("wide", "raised", "flat", DOWN))],
    },
    "dev": {
        "01": [(0, "sit", F("open", "raised", "flat", TO_HER))],
        "02": [(0, "cross", F("half", "angry", "flat", TO_HER))],
        "04": [(0, "cross", F("wide", "worried", "frown", DOWN))],
        "05": [(0, "cross", F("half", "worried", "flat", TO_HER))],
        "06": [(0, "cross", F("open", "raised", "smile", TO_HER))],
        "07": [(0, "point", F("happy", "raised", "smile", TO_HER))],
        "08": [(0, "cross", F("happy", "raised", "smirk", TO_HER)), (1.3, "cross", F("open", "raised", "flat", DOWN)),
               (2.7, "sit", F("wide", "raised", "flat", DOWN))],
        "10": [(0, "sit", F("half", "flat", "flat", TO_HER))],
        "12": [(0, "sit", F("half", "flat", "flat", (0.0, 0.0)))],
        "13": [(0, "sit", F("wide", "raised", "flat", DOWN))],
    },
}  # fmt: skip
CX, CY = 1480.0, 1290.0  # the middle of the bed, the couple's heads
CLOSE_FROM = ((CX, CY), 1.8, (540.0, 860.0))
CLOSE_TO = ((CX, CY), 2.0, (540.0, 860.0))
WIDE = ((CX, 1400.0), 1.45, (540.0, 900.0))
PUSH_TAKES = 8  # the push runs through the first eight takes, to the moment they stop
AT = {"dev": (878.0, 450.0), "noor": (2082.0, 450.0)}  # with scale SCALE, Noor flipped: heads at CX -/+ 170
SCALE = 0.8
GARY_HEAD = (CX, 1490.0)  # where the fold-down bed lays a sleeper's head
PHONE_AT = (CX, 1386.0)  # on the top of the mound
BREATH, BREATH_PX = 3.2, 12.0  # the mound's rise and fall, from frame 1: seconds, px
BIG_BREATH = (0.9, 2.9, 26.0)  # into take 08's hold: when it starts, ends and how far up it goes
PULL_AFTER, PULL = 0.2, 1.9  # into the hold of take 09: when the camera starts back, and how long it takes
SINK = 256.0  # how far the mound drops as the camera rises over it, showing the head behind


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

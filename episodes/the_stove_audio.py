#!/usr/bin/env python3
"""Stick 13 — The Stove: who says what, on one take timeline, and how Dev and Noor play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_stove_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_the_stove.py`` checks this script. There is no music bed.

Arm B of the first-second test: the car is already moving on frame one, with no held opening. An effect used more
than once is one recording, from the client's cache.
"""

from __future__ import annotations

import sys

from srstudio import stick, stick_windshield, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("road1", "turn1", "home1", "knob", "road2", "turn2", "home2", "lock", "road3", "turn3", "sign", "home3", "old")
HOOK = "Did you turn off the stove?"
SETTING = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
OLD = VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.2, speed=0.8)
SCREECH = "Car tyres screeching through a hard U-turn, dry, no voices, no music"
BRAKE = "A car pulling up and braking on a quiet street, dry, no voices, no music"


def _fx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=0.4)  # fmt: skip


SCRIPT = takes.Script(
    title="The Stove",
    seed=1313,
    voice_note="Premade voices: Will is Dev, as in Repeat After Me, and Jessica is Noor.",
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    },
    settings={"dev": SETTING, "noor": SETTING},
    takes=(
        takes.Take("01", "noor", HOOK, 0.30, shot="road1", mood="firm"),
        takes.Take("02", "dev", "Yes.", 0.90, shot="road1", mood="firm"),
        takes.Take("03", "noor", "...Did you?", 0.25, shot="road1", mood="firm"),
        _fx(4, "[SCREECH]", 0.0, "turn1", SCREECH, 1.3),
        _fx(5, "[BRAKE]", 0.1, "home1", BRAKE, 1.0),
        _fx(6, "[CLICK]", 0.5, "knob", "One small click of a stove knob, close, dry, no voices, no music", 0.6),
        takes.Take("07", "noor", "Did you lock the door?", 0.20, shot="road2", mood="firm"),
        _fx(8, "[SCREECH]", 0.0, "turn2", SCREECH, 1.3),
        _fx(9, "[BRAKE]", 0.1, "home2", BRAKE, 1.0),
        _fx(10, "[RATTLE]", 0.45, "lock", "A locked door handle rattled twice, close, dry, no voices, no music", 0.7),
        takes.Take("11", "noor", "The iron.", 0.15, shot="road3", mood="firm"),
        takes.Take("12", "dev", "We don't own an iron.", 0.20, shot="road3", mood="firm"),
        _fx(13, "[SCREECH]", 0.0, "turn3", SCREECH, 1.3),
        _fx(14, "[PASS]", 0.1, "sign", "A car passing a road sign at speed, one soft whoosh, no voices, no music", 0.9),
        _fx(
            15,
            "[BIRDS]",
            1.1,
            "home3",
            "Quiet suburban morning, a few birds, a distant lawn mower, no voices, no music",
            1.6,
        ),
        takes.Take("16", "noor", HOOK, 1.40, shot="old", mood="firm", speed=0.8),
    ),
    shots=SHOTS,
    bed=None,
)

F = stick.Face
NOOR_GO, DEV_GO = stick_windshield.COUPLE["noor"], stick_windshield.COUPLE["dev"]
DEV_OLD = stick.Look(hair="bald", glasses=True)
NOOR_OLD = NOOR_GO  # she has no hair to lose: the wash and the slump age her
NEIGHBOUR = {
    1: stick.Look(hair="spiky"),
    2: stick.Look(hair="spiky", glasses=True),
    3: stick.Look(hair="bald", glasses=True),
}
KID_SCALE = {1: 0.42, 2: 0.52, 3: 0.82}  # how big the children are in the window at each visit
TREE = {1: 0.8, 2: 1.0, 3: 1.45}
WORRIED = F("open", "worried", "flat", (1.0, 0.0))
LEVEL = F("open", "flat", "flat", (0.0, 0.1))
SOUR = F("half", "flat", "flat", (-1.0, 0.0))
STARE = F("wide", "flat", "flat", (0.0, 0.1))
TIRED = F("half", "worried", "flat", (1.0, 0.0))
WEARY = F("half", "flat", "flat", (0.0, 0.1))
SHUT = F("closed", "flat", "flat", (0.0, 0.0))
WAVING = F("happy", "raised", "smile", (0.0, 0.0))
TURN_CUT = 1.5  # into home3: the cut to the window
GREY = "#6f7377"  # the wash over the last drive
CAMERAS = {  # (focus, zoom, to): focus lands at to
    "two": ((540.0, 1023.0), 1.25, (540.0, 960.0)),
    "window": ((790.0, 870.0), 2.2, (540.0, 880.0)),
    "dev": ((stick_windshield.SEATS[1], 960.0), 1.7, (540.0, 760.0)),
}

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

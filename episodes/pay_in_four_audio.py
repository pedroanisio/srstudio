#!/usr/bin/env python3
"""Stick — Pay in Four: who says what, on one take timeline, and how Noor and the repo man play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 pay_in_four_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words and each voice id must resolve to the premade voice it names. The key comes
from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts; ``tests/test_pay_in_four.py`` checks
this script. There is no music bed; the effects are ``foley`` bursts written by the episode.

A repo man comes to Noor's door over a burrito she bought on four easy payments. The truck backs in behind him during
a held beat; the turn is her asking to split the debt, and his first smile.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio import stick_windshield as ws
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("door", "noor", "repo", "truck", "two", "hook", "guac", "small", "board")
HOOK = "PAYMENT 3 OF 4: MISSED"
PLAIN = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
FLAT = VoiceSettings(stability=0.7, similarity_boost=0.75, style=0.1, speed=0.95)  # he has done this before
TRUCK_HOLD, LOOK_HOLD, GUAC_HOLD, TURN_HOLD = 2.9, 1.2, 1.5, 1.2
SCRIPT = takes.Script(
    title="Pay in Four — Stick",
    seed=3306,
    voices={
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
        "repo": Voice(role="repo", id="N2lVS1w4EtoT3dr4eOWO", name="Callum"),
    },
    settings={"noor": PLAIN, "repo": FLAT},
    takes=(
        takes.Take("01", "repo", "Ma'am. We're here about the burrito.", 0.25, shot="door", mood="calm"),
        takes.Take("02", "noor", "What burrito?", 0.2, shot="noor", mood="firm"),
        takes.Take("03", "repo", "Four easy payments. You stopped at two.", 0.25, shot="repo", mood="calm"),
        takes.Take("04", "noor", "It was nine dollars!", 0.2, shot="noor", mood="firm"),
        takes.Take("05", "repo", "In March.", 0.2, shot="repo", mood="calm"),
        takes.Take("06", "noor", "I ate it in March!", 0.2, shot="noor", mood="firm"),
        takes.Take("07", "repo", "So you've eaten our half.", TRUCK_HOLD, shot="truck", mood="calm"),
        takes.Take("08", "noor", "What's that for?", 0.25, shot="two", mood="calm"),
        takes.Take("09", "repo", "The burrito.", LOOK_HOLD, shot="hook", mood="calm"),
        takes.Take("10", "repo", "Or two hundred fourteen dollars.", 0.25, shot="hook", mood="calm"),
        takes.Take("11", "noor", "For a burrito?", 0.25, shot="noor", mood="firm"),
        takes.Take("12", "repo", "With guac.", GUAC_HOLD, shot="guac", mood="calm"),
        takes.Take("13", "noor", "Can I split that?", TURN_HOLD, shot="small", mood="calm", speed=0.9),
        takes.Take("14", "repo", "Four easy payments.", 1.2, shot="board", mood="happy"),
    ),
    voice_note="ElevenLabs premade voices Jessica and Callum; no reference-voice cloning. Sound effects synthesized in "
    "code.",
    shots=SHOTS,
)

F = stick.Face
BLANK = F("open", "flat", "flat", (0.8, 0.0))  # the repo man, at her
READING = F("half", "flat", "flat", (0.5, 0.5))  # at the clipboard
AT_STOMACH = F("open", "flat", "flat", (0.8, 0.6))
SMILE = F("open", "flat", "smile", (0.8, 0.0))  # the first one
NOOR_FLAT = F("open", "flat", "flat", (0.9, 0.0))
NOOR_WHAT = F("open", "raised", "frown", (0.9, 0.0))
NOOR_CROSS = F("wide", "angry", "frown", (0.9, 0.0))
NOOR_PAST = F("wide", "raised", "flat", (0.9, -0.25))  # past him, at the yard
NOOR_HOOK = F("wide", "worried", "frown", (0.8, -0.1))  # at the hook
NOOR_SMALL = F("half", "worried", "flat", (0.7, 0.3))
NOOR_LOOK = ws.NOOR
REPO_LOOK = stick.Look(hair="bald", tie="#2f3a46", cap="#2f3a46", brows=False)
# shot: (focus, zoom, where the focus lands), in frame pixels of the set
CAMERAS = {
    "two": ((540.0, 880.0), 1.0, (540.0, 880.0)),
    "repo": ((370.0, 800.0), 1.45, (530.0, 800.0)),
    "noor": ((800.0, 860.0), 1.32, (715.0, 820.0)),
    "board": ((540.0, 860.0), 1.15, (540.0, 800.0)),
}
OPENS = 0.1  # seconds into the first shot that the door starts to move
TRUCK_FROM, TRUCK_TO = 0.12, 0.62  # its depth along the path
TRUCK_RUN = 1.8  # seconds it takes to back in
HOOK_LAG = 0.1  # seconds after it stops that the hook starts down
LOOKS = (0.3, 0.8)  # seconds into the hold his eyes go to her stomach, then to the clipboard
AT_NOOR = 0.25  # seconds into the hold after "With guac." that the shot goes to her
TURN_AFTER = 0.3  # seconds into the hold after "Can I split that?" that he starts to turn the board
BEEP_GAP = 0.9  # seconds between the truck's reversing beeps


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

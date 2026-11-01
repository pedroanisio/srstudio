#!/usr/bin/env python3
"""Stick — Practice Round: who says what, on one take timeline, and how Dev and Noor play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 practice_round_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words and each voice id must resolve to the premade voice it names. The key comes
from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts; ``tests/test_practice_round.py`` checks
this script. There is no music bed; the effects are ``foley`` bursts written by the episode.

Dev asks Noor to practice interview questions with him, and to be tough. The planks and the drill are in frame from the
first frame and nobody mentions them. The holds are real: nobody speaks in them and no caption comes up.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio import stick_table as st
from srstudio import stick_windshield as ws
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("two", "dev", "noor", "whip", "planks", "close", "stare", "scratch", "push", "with", "end")
HOOK = "PRACTICE INTERVIEW"
PLAIN = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
SETTLE = 1.1  # seconds Dev takes to land and tug his collar, under his first line
WHIP_LOOK, WHIP = 0.5, 0.22  # after "The shelf, Dev.": he has turned; the pan takes this long
SCRATCH_HOLD = 1.9  # the long write after "Really well.", the two-shot, him trying to read it
STARE_HOLD = 2.0  # after "five years?": planks, her, his hands
WRITE_HOLD = 1.9  # after "With you?": one word, the click, the clipboard shut, up
BEDDING_AT, BEDDING_RUN, END_HOLD = 0.55, 0.5, 2.0  # after the last line: it comes, how long it runs, then the hold
SCRIPT = takes.Script(
    title="Practice Round — Stick",
    seed=3404,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    },
    settings={"dev": PLAIN, "noor": PLAIN},
    takes=(
        takes.Take("01", "dev", "Okay. Be tough. Pretend you don't know me.", 0.3, shot="two", mood="calm"),
        takes.Take("02", "noor", "Describe a project you finished.", 0.25, shot="two", mood="calm"),
        takes.Take("03", "dev", "Sure. At my last job...", 0.05, shot="dev", mood="calm"),
        takes.Take("04", "noor", "At home.", 0.3, shot="noor", mood="calm"),
        takes.Take("05", "dev", "This is for a bank.", 0.3, shot="dev", mood="calm"),
        takes.Take("06", "noor", "The shelf, Dev.", WHIP_LOOK + WHIP, shot="whip", mood="calm"),
        takes.Take("07", "dev", "It's nearly up.", 0.3, shot="planks", mood="calm"),
        takes.Take("08", "noor", "Since March.", 0.5, shot="close", mood="calm"),
        takes.Take("09", "noor", "How do you take criticism?", 0.5, shot="close", mood="calm"),
        takes.Take("10", "dev", "Really well.", SCRATCH_HOLD, shot="scratch", mood="calm"),
        takes.Take("11", "dev", "Can we go back to strangers?", 0.5, shot="two", mood="calm"),
        takes.Take("12", "noor", "Where do you see yourself in five years?", STARE_HOLD, shot="push", mood="calm"),
        takes.Take("13", "dev", "With you?", WRITE_HOLD, shot="with", mood="calm"),
        takes.Take("14", "noor", "We'll let you know.", BEDDING_AT + BEDDING_RUN + END_HOLD, shot="end", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Will and Jessica; no reference-voice cloning. Sound effects synthesized in "
    "code.",
    shots=SHOTS,
)

F = stick.Face
AT_HER = (0.9, 0.0)
AT_HIM = (0.9, 0.0)  # mirrored, she looks left at him the same way
AT_PAGE = (0.75, 0.55)  # down at what she holds
NOOR_LOOK = ws.NOOR
DEV_LOOK = stick.Look(tie="#2f5d8c")  # Dev as he always is, in the tie he wears to interviews
POSES = st.POSES
LEFT, RIGHT = st.LEFT_AT, st.RIGHT_AT
DEV_KEEN = F("open", "raised", "smile", AT_HER)
DEV_SMOOTH = F("half", "raised", "smirk", AT_HER)
DEV_THROWN = F("open", "worried", "flat", AT_HER)
DEV_BEHIND = F("open", "raised", "flat", (-0.9, -0.15))  # over his shoulder at the planks
DEV_BRAVE = F("open", "worried", "smile", AT_HER)
DEV_READS = F("wide", "raised", "flat", (0.9, 0.25))  # at her page
DEV_HANDS = F("half", "worried", "flat", (0.8, 0.8))
DEV_ALONE = F("open", "worried", "flat", (0.85, 0.5))  # at the bedding
NOOR_PLAIN = F("open", "flat", "flat", AT_HIM)
NOOR_PAGE = F("half", "flat", "flat", AT_PAGE)
NOOR_ASKS = F("open", "raised", "flat", AT_HIM)
NOOR_DONE = F("half", "flat", "smirk", AT_HIM)
# shot: (focus, zoom, where the focus lands), in frame pixels of the set
CAMERAS = {
    "two": ((540.0, 960.0), 1.12, (540.0, 930.0)),
    "dev": ((302.0, 800.0), 1.7, (470.0, 800.0)),
    "noor": ((778.0, 800.0), 1.7, (610.0, 800.0)),
    "close": ((778.0, 800.0), 2.0, (640.0, 800.0)),
    "planks": ((210.0, 900.0), 1.8, (378.0, 790.0)),
    "end": ((420.0, 900.0), 1.4, (440.0, 850.0)),
}
FACES = {"dev": (302.0, 775.0), "noor": (778.0, 775.0)}  # the heads on the set
MARKS = {"cactus": (480.0, st.TOP), "code": (470.0, st.TOP + 12)}
PLANKS_AT, DRILL_AT, BRACKETS_AT = (-30.0, 1400.0), (150.0, 1250.0), (66.0, 495.0)
MUG_AT = (540.0, st.TOP - 40)
PEN_TILT = {"point": -14.0, "write-a": 62.0, "write-b": 70.0, "click": -60.0}  # degrees off the arm's line; others 0
BEDDING_FROM, BEDDING_TO = 1180.0, 672.0  # x along the table
SCRATCH_RATE = 7.0  # frames of her hand a second, writing

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

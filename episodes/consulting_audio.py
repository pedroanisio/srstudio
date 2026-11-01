#!/usr/bin/env python3
"""Stick — Consulting: who says what, on one take timeline, and how Noor and Dev play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 consulting_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words and each voice id must resolve to the premade voice it names. The key comes
from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts; ``tests/test_consulting.py`` checks
this script. There is no music bed; the effects are ``foley`` bursts written by the episode.

Noor interviews Dev over the two-year gap on his resume: he was consulting, for a couch. The turn is the page at her
elbow and the bottom drawer, in frame and shut from the first frame. A still opening: nobody moves for ``STILL``.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("two", "dev", "noor", "stare", "page", "open", "shake")
HOOK = "THAT LINE ON YOUR RESUME"
STILL = 0.45  # the held first frame
PLAIN = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
STARE_HOLD, TURN_AT = 2.4, 2.0  # the held beat after "From noon to noon.", and where in it the page goes over
DRAWER_HOLD, DRAWER_AT, INSERT_AFTER = 1.8, 0.4, 0.25  # after "Consulting.": seconds, when it opens after the cut, cut
RESPECT_HOLD = 1.5  # after "From noon to noon?"
SHAKE_HOLD = 2.8  # the handshake, slow, after "From noon to noon."
SCRIPT = takes.Script(
    title="Consulting — Stick",
    seed=3313,
    voices={
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
    },
    settings={"noor": PLAIN, "dev": PLAIN},
    takes=(
        takes.Take("01", "noor", "There's a two-year gap here.", 0.55, shot="two", mood="calm"),
        takes.Take("02", "dev", "I was consulting.", 0.25, shot="dev", mood="calm"),
        takes.Take("03", "noor", "Who were your clients?", 0.6, shot="noor", mood="calm"),
        takes.Take("04", "dev", "One client. Very demanding.", 0.25, shot="dev", mood="calm"),
        takes.Take("05", "noor", "Who?", 0.5, shot="noor", mood="calm"),
        takes.Take("06", "dev", "My couch.", 0.3, shot="dev", mood="calm"),
        takes.Take("07", "noor", "What did you deliver?", 0.2, shot="noor", mood="calm"),
        takes.Take("08", "dev", "No, they delivered. To me.", 0.35, shot="dev", mood="calm"),
        takes.Take("09", "noor", "What hours?", 0.2, shot="noor", mood="calm"),
        takes.Take("10", "dev", "From noon to noon.", STARE_HOLD, shot="stare", mood="calm"),
        takes.Take("11", "noor", "Consulting.", INSERT_AFTER + DRAWER_HOLD, shot="page", mood="calm"),
        takes.Take("12", "dev", "From noon to noon?", RESPECT_HOLD, shot="open", mood="calm"),
        takes.Take("13", "noor", "From noon to noon.", SHAKE_HOLD, shot="shake", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Jessica and Will; no reference-voice cloning. Sound effects synthesized in "
    "code.",
    shots=SHOTS,
    still=STILL,
)

F = stick.Face
AT_HER = (0.9, 0.0)
AT_HIM = (0.9, 0.0)  # mirrored, she looks left at him the same way
NOOR_LOOK = stick.Look(hair="bun", glasses=True, neck=True)
DEV_LOOK = stick.Look(neck=True)
NOOR_BLANK = F("open", "flat", "flat", AT_HIM)
NOOR_PAGE = F("half", "flat", "flat", (0.8, 0.5))  # down at his resume
NOOR_RAISED = F("open", "raised", "flat", AT_HIM)
NOOR_SEES = F("wide", "raised", "flat", AT_HIM)
NOOR_KNOWS = F("half", "flat", "smirk", AT_HIM)
NOOR_VET = F("half", "raised", "smirk", AT_HIM)
DEV_BRIGHT = F("open", "raised", "smile", AT_HER)
DEV_PROUD = F("happy", "raised", "smile", AT_HER)
DEV_HONEST = F("half", "raised", "flat", AT_HER)
DEV_DOOR = F("open", "worried", "flat", (0.55, -0.55))  # at the door behind them
DEV_DOWN = F("wide", "raised", "flat", (0.85, 0.6))  # at the drawer
DEV_VET = F("half", "raised", "smirk", AT_HER)
RESUME_AT = (540.0, 1092.0)  # his, on the desk between them, under her finger
HERS_AT = (676.0, 1104.0)  # hers, at her elbow
# shot: (focus, zoom, where the focus lands), in frame pixels of the set
CAMERAS = {
    "two": ((540.0, 960.0), 1.12, (540.0, 930.0)),
    "dev": ((302.0, 800.0), 1.7, (470.0, 800.0)),
    "noor": ((778.0, 800.0), 1.7, (610.0, 800.0)),
    "drawer": ((640.0, 1500.0), 2.6, (540.0, 850.0)),
}
FACES = {"dev": (302.0, 775.0), "noor": (778.0, 775.0)}  # the heads on the set
MARKS = {"cactus": (476.0, 1076.0), "code": (516.0, 1146.0)}
ARM_FROM = (900.0, 1330.0)  # where her arm comes in from in the drawer's close-up
SHAKES = (0.2, 0.65, 1.2, 1.75, 2.3)  # seconds after the last line: reach, then up, down, up, down, slowly
TICK_GAP = 1.0  # a wall clock ticks through the room's silences

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

#!/usr/bin/env python3
"""Stick — In Two Hundred: who says what, on one take timeline, and how Dev, Noor and the map play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 in_two_hundred_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words and each voice id must resolve to the premade voice it names. The key comes
from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts; ``tests/test_in_two_hundred.py`` checks
this script. There is no music bed; the effects are ``foley`` bursts written by the episode.

Late for a wedding, Dev trusts the map over the passenger who grew up here. It drives them into a field, then changes
sides: the map is the one who tells him to apologize.
"""

from __future__ import annotations

import dataclasses
import sys

from srstudio import stick, takes
from srstudio import stick_windshield as ws
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("two", "map", "rough", "stopped", "back")
HOOK = "LATE FOR THE WEDDING"
PLAIN = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
DEVICE = VoiceSettings(
    stability=0.85, similarity_boost=0.75, style=0.0, speed=0.95
)  # a device, and pleased with itself
GRAVEL, GRASS, STOPPING, BEFORE = 0.9, 0.9, 0.8, 0.2  # seconds of each surface, and from the line to the first
FIELD_HOLD = 2.0  # the script's held beat, in the field, nobody speaking
TURN_HOLD = 1.0  # after "At the fence, tell her she was right.": Noor smiles at the dashboard
SCRIPT = takes.Script(
    title="In Two Hundred — Stick",
    seed=3308,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
        "map": Voice(role="map", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    },
    settings={"dev": PLAIN, "noor": PLAIN, "map": DEVICE},
    takes=(
        takes.Take("01", "noor", "It's left.", 0.2, shot="two", mood="firm"),
        takes.Take("02", "map", "Continue straight.", 0.2, shot="map", mood="calm"),
        takes.Take("03", "dev", "It says straight.", 0.2, shot="two", mood="calm"),
        takes.Take("04", "noor", "I grew up here.", 0.2, shot="two", mood="firm"),
        takes.Take("05", "map", "Continue straight.", 0.2, shot="two", mood="calm"),
        takes.Take(
            "06",
            "dev",
            "It has satellites.",
            BEFORE + GRAVEL + GRASS + STOPPING + FIELD_HOLD,
            shot="rough",
            mood="firm",
        ),
        takes.Take("07", "map", "Recalculating.", 0.2, shot="map", mood="calm"),
        takes.Take("08", "dev", "Thank you.", 0.25, shot="stopped", mood="calm"),
        takes.Take("09", "map", "In two hundred feet, apologize.", 0.25, shot="map", mood="calm"),
        takes.Take("10", "dev", "What?", 0.25, shot="stopped", mood="firm"),
        takes.Take("11", "map", "At the fence, tell her she was right.", TURN_HOLD, shot="back", mood="calm"),
        takes.Take("12", "dev", "Whose side are you on?", 0.25, shot="stopped", mood="firm"),
        takes.Take("13", "map", "Your destination is the couch.", 1.2, shot="back", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Will, Jessica and Alice; no reference-voice cloning. Sound effects "
    "synthesized in code.",
    shots=SHOTS,
)

F = stick.Face
AT_ROAD = (0.0, 0.0)  # both of them, facing the camera on the hood
DEV_LOOK = stick.Look(tie="#c0453b", neck=True)  # dressed for the wedding
NOOR_LOOK = dataclasses.replace(ws.NOOR, neck=True)
DEV_SURE = F("open", "raised", "smile", AT_ROAD)
DEV_ROAD = F("open", "flat", "flat", AT_ROAD)
DEV_SAYS = F("open", "raised", "flat", (0.1, 0.45))  # at the phone
DEV_DOWN = F("half", "worried", "frown", (-0.1, 0.45))
DEV_LOST = F("wide", "worried", "frown", AT_ROAD)
DEV_ANGRY = F("wide", "angry", "frown", (-0.25, 0.45))
NOOR_FIRM = F("open", "angry", "frown", (0.5, 0.0))  # at Dev
NOOR_ROAD = F("open", "flat", "frown", AT_ROAD)
NOOR_STILL = F("half", "flat", "flat", AT_ROAD)  # she says nothing
NOOR_AT_MAP = F("happy", "raised", "smile", (0.45, 0.5))
# the screens of the map's lines, by take
SCREENS = {"02": "straight", "07": "recalculating", "09": "apologize", "11": "fence", "13": "couch"}
SURFACES = (("gravel", GRAVEL), ("grass", GRASS))
BUZZ_LEAD = 0.05  # seconds into a map line the phone shakes


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

#!/usr/bin/env python3
"""Stick 10 — Hold the Door: who says what, on one take timeline, and how Dev and the stranger play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 hold_the_door_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_hold_the_door.py`` checks this script. There is no music bed.

You held a door for someone too far away, and now they have to run. Arm A of the first-second test: the held frame
is ``STILL`` seconds of the opening take, nobody moving, before the stranger's first "Sorry!".
"""

from __future__ import annotations

import sys

from srstudio import stick, stick_door, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("open", "dev", "more", "crowd", "time", "race", "old", "nearly", "shut", "end")
HOOK = "You held the door too early."
STILL = 1.0  # the held frame
SETTING = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
SCRIPT = takes.Script(
    title="Hold the Door — Stick 10",
    seed=1310,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "stranger": Voice(role="stranger", id="TX3LPaxmHKxFdv7VOQHJ", name="Liam"),
        "first": Voice(role="first", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"),
        "second": Voice(role="second", id="iP95p4xoKVk53GoZ742B", name="Chris"),
        "third": Voice(role="third", id="pFZP5JQG7iQjIQuC4Bku", name="Lily"),
    },
    settings=dict.fromkeys(("dev", "stranger", "first", "second", "third"), SETTING),
    takes=(
        takes.Take("01", "stranger", "Sorry!", 0.25, shot="open", mood="firm"),
        takes.Take("02", "dev", "No rush!", 0.40, shot="dev", mood="happy"),
        takes.Take(
            "03",
            "sfx",
            "[FEET]",
            0.30,
            shot="more",
            prompt="Light footsteps of two people jogging on a pavement, getting nearer, dry, no voices, no music",
            seconds=1.4,
            longest=1.4,
            peak=0.3,
        ),
        takes.Take("04", "first", "Thanks!", 0.27, shot="crowd", mood="happy"),
        takes.Take("05", "second", "Thank you!", 0.27, shot="crowd", mood="happy"),
        takes.Take("06", "third", "Thanks!", 0.25, shot="crowd", mood="happy"),
        takes.Take(
            "07",
            "sfx",
            "[WIND]",
            1.4,
            shot="time",
            prompt="Cold winter wind blowing softly through an open door, dry, no voices, no music",
            seconds=2.0,
            longest=2.0,
            peak=0.3,
        ),
        takes.Take(
            "08",
            "sfx",
            "[CHEER]",
            0.3,
            shot="race",
            prompt="A distant crowd cheering at a road race, far away, no words, no music",
            seconds=2.0,
            longest=2.0,
            peak=0.25,
        ),
        takes.Take("09", "stranger", "Sorry!", 0.50, shot="old", mood="calm", speed=0.8),
        takes.Take(
            "10",
            "sfx",
            "[FEET]",
            0.8,
            shot="nearly",
            prompt="One tired person's slow footsteps on a pavement, close, dry, no voices, no music",
            seconds=1.2,
            longest=1.2,
            peak=0.3,
        ),
        takes.Take(
            "11",
            "sfx",
            "[THUD]",
            1.7,
            shot="shut",
            prompt="A heavy glass door swinging shut and a face bumping into the glass, one dull thud, dry, no voices, "
            "no music",
            seconds=0.8,
            longest=0.7,
            peak=0.6,
        ),
        takes.Take("12", "dev", "...No rush.", 0.90, shot="end", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Will, Liam, Sarah, Chris and Lily; no reference-voice cloning. Effects "
    "generated with ElevenLabs.",
    shots=SHOTS,
    still=STILL,
)

F = stick.Face
TO_PATH = (0.9, 0.0)  # mirrored: Dev looks left, out of the door
BRIGHT = F("happy", "raised", "smile", TO_PATH)
FIXED = F("open", "raised", "smile", TO_PATH)  # the smile is staying, whatever happens
STRAINED = F("wide", "worried", "smile", TO_PATH)
FROZEN = F("half", "worried", "frown", TO_PATH)
HOPE = F("wide", "raised", "smile", TO_PATH)
GONE = F("wide", "worried", "frown", TO_PATH)
STARE = F("half", "flat", "flat", TO_PATH)
SHY = F("open", "worried", "smile", (0.0, 0.0))  # the stranger, jogging at the camera
OLD_SHY = F("half", "worried", "smile", (0.0, 0.0))
PRESSED = F("wide", "raised", "flat", (0.8, 0.0))  # on the glass, at Dev
GLAD = F("happy", "raised", "smile", (0.6, 0.0))  # the crowd, thanking him
DEV = stick.Look()
STRANGER = stick.Look(hair="side-part")
STRANGER_OLD = stick.Look(hair="bald", glasses=True)
CROWD = (
    stick.Look(hair="bun"),
    stick.Look(hair="spiky"),
    stick.Look(hair="bald", tie="#3d5a80"),
    stick.Look(hair="cowlick", glasses=True),
    stick.Look(hair="side-part", tie="#c0453b"),
)
CUT_AT = STILL  # where the open cuts from the held frame to the long lens
HOLDER = stick_door.HOLDER_AT
# shot: (focus, zoom, where the focus lands), in frame pixels of the set
CAMERAS = {
    "open": ((585.0, 860.0), 1.22, (540.0, 880.0)),
    "dev": ((860.0, 800.0), 1.9, (640.0, 880.0)),
    "time": ((800.0, 790.0), 1.5, (640.0, 880.0)),
    "two": ((575.0, 800.0), 1.42, (540.0, 860.0)),
    "end": ((850.0, 800.0), 1.65, (700.0, 880.0)),  # on Dev, the edge of a face still on the glass behind him
}
FAR = 0.15  # how far down the path the stranger is when the door is held for him
LENS_AT, LENS_SCALE = (-270.0, -330.0), 1.5  # the long lens: the runner's head in the upper half, the wave in frame
FACE_AT, FACE_SCALE = (-205.0, -190.0), 1.25  # the face on the glass, above the door's bar
SNOW_ON = {  # where the snow sits on the mirrored Dev in each of his poses: head, then shoulder
    "hold": ((828.0, 682.0), (772.0, 892.0)),
    "sag": ((820.0, 698.0), (790.0, 908.0)),
    "drop": ((834.0, 708.0), (812.0, 918.0)),
}
PASS_FROM, PASS_TO, PASS_TIME, PASS_GAP = 0.2, 1.38, 1.7, 0.42  # the crowd: depth from and to, seconds each, apart
PASS_LANES = (-0.6, -0.2, -0.9, -0.4, -0.75)
GIVE = 0.45  # seconds before the shot ends that the arm goes
SWING = 0.12  # seconds into the shut take the door starts to move
HIT = SWING + stick_door.SWING_STEPS * stick_door.SWING_STEP  # the face meets the glass


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

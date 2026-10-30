#!/usr/bin/env python3
"""Stick 11 — Take My Phone: who says what, on one take timeline, and how the two friends play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 take_my_phone_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_take_my_phone.py`` checks this script. There is no music bed.

She hands over her phone like a loaded weapon, and twenty seconds later wants it back. Arm A of the first-second
test: the held frame is ``STILL`` seconds of the opening take, before she says a word.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("two", "later", "friend", "chase", "sit", "fridge", "safe", "gulp", "calm", "reply", "win")
HOOK = "Do NOT let me text him."
STILL = 1.0  # the held frame
SETTING = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)

SCRIPT = takes.Script(
    title="Take My Phone",
    seed=1311,
    voice_note="Premade voices: Laura the one with the phone, Alice the friend who has to hold it.",
    voices={
        "her": Voice(role="her", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"),
        "friend": Voice(role="friend", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    },
    settings=dict.fromkeys(("her", "friend"), SETTING),
    takes=(
        takes.Take("01", "her", "Take it. Whatever I say. Do not let me text him.", 0.35, shot="two", mood="firm"),
        takes.Take("02", "her", "Just to say happy birthday.", 0.25, shot="later", mood="happy"),
        takes.Take("03", "friend", "It's not his birthday.", 0.30, shot="friend", mood="firm"),
        takes.Take(
            "04",
            "sfx",
            "[CHASE]",
            0.10,
            shot="chase",
            prompt="Two people running fast around a kitchen table, feet on a wooden floor, a chair scraping, "
            "no voices, no music",
            seconds=2.4,
            longest=2.4,
            peak=0.3,
        ),
        takes.Take(
            "05",
            "sfx",
            "[SIT]",
            0.45,
            shot="sit",
            prompt="A loud wooden thump and creak, a heavy body dropping onto a wooden table, close, "
            "no voices, no music",
            seconds=1.0,
            longest=1.0,
            peak=0.4,
        ),
        takes.Take(
            "06",
            "sfx",
            "[SLAM]",
            0.25,
            shot="fridge",
            prompt="A fridge door slammed shut, bottles rattling inside, dry, no voices, no music",
            seconds=0.9,
            longest=0.9,
            peak=0.4,
        ),
        takes.Take(
            "07",
            "sfx",
            "[SAFE]",
            0.25,
            shot="safe",
            prompt="A heavy small safe door clanging shut and its dial spinning with clicks, dry, no voices, no music",
            seconds=1.2,
            longest=1.2,
            peak=0.4,
        ),
        takes.Take(
            "08",
            "sfx",
            "[GULP]",
            1.35,
            shot="gulp",
            prompt="One loud cartoonish swallow, a single gulp, close, dry, no voices, no music",
            seconds=0.6,
            longest=0.6,
            peak=0.4,
        ),
        takes.Take(
            "09",
            "sfx",
            "[TAP]",
            0.15,
            shot="calm",
            prompt="Fingernails tapping quickly on a phone screen, close, dry, no voices, no music",
            seconds=1.6,
            longest=1.6,
            peak=0.2,
        ),
        takes.Take(
            "10",
            "sfx",
            "[PING]",
            0.60,
            shot="reply",
            prompt="A single soft phone message notification ping, clean, no voices, no music",
            seconds=0.7,
            longest=0.7,
            peak=0.4,
        ),
        takes.Take("11", "her", "He answered!", 1.10, shot="win", mood="excited"),
    ),
    shots=SHOTS,
    bed=None,
    still=STILL,
)

F = stick.Face
HER = stick.Look(hair="side-part")
FRIEND = stick.Look(hair="bun")
HER_PHONE, FRIEND_PHONE = "#1f2430", "#e8558f"
GRAVE = F("wide", "worried", "flat", (0.8, 0.0))  # handing it over
SOLEMN = F("open", "flat", "flat", (-0.8, 0.0))  # taking it
SWEET = F("happy", "raised", "smile", (0.5, 0.0))  # "just to say"
FIRM = F("half", "flat", "frown", (-0.6, 0.0))
FRANTIC = F("wide", "worried", "frown", (0.7, 0.0))
SMUG = F("half", "raised", "smirk", (0.0, 0.0))
GRIM = F("half", "angry", "flat", (0.2, 0.0))
BLANK = F("wide", "flat", "flat", (0.0, 0.0))
TILTED = F("closed", "flat", "flat", (0.0, -0.4))
CALM = F("half", "raised", "smirk", (0.6, 0.0))
LOST = F("wide", "worried", "flat", (-0.5, 0.3))
JOY = F("happy", "raised", "smile", (0.0, 0.0))
DONE = F("half", "flat", "flat", (0.0, 0.0))
CUT_AT = 0.85  # into the gulp's shot: the cut to the two of them staring
CAMERAS = {  # (focus, zoom, to): focus lands at to
    "two": ((540.0, 900.0), 1.25, (540.0, 920.0)),
    "stare": ((540.0, 900.0), 1.25, (540.0, 920.0)),
    "her": ((400.0, 860.0), 1.75, (470.0, 900.0)),
    "friend": ((820.0, 860.0), 1.75, (610.0, 900.0)),
    "fridge": ((780.0, 900.0), 1.25, (640.0, 880.0)),
    "safe": ((330.0, 700.0), 1.25, (440.0, 880.0)),
}
ORBIT, LAP = (540.0, 880.0, 330.0, 500.0), 1.25  # the chase from above: centre, radii, and seconds round the table

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

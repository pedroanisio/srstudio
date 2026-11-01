#!/usr/bin/env python3
"""Stick 23 — Trash Day: who says what on one take timeline, and how Dev and the neighbors play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 bin_day_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_bin_day.py`` checks this script. There is no music bed.

Two neighbors call a man's run for the trash truck like a horse race. Arm B of the first-second test: Dev is already
moving on frame one and the first line starts at once.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("door", "window", "run", "chase", "dive", "arms", "driver", "road", "sip")
HOOK = "He's left it very late."
SETTING = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
CALLING = VoiceSettings(stability=0.35, similarity_boost=0.75, style=0.45, speed=1.05)


def _fx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float, peak: float = 0.4) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=peak)  # fmt: skip


SCRIPT = takes.Script(
    title="Trash Day — Stick 23",
    seed=3123,
    still=0.0,
    voices={
        "walt": Voice(role="walt", id="JBFqnCBsd6RMkjVDRZzb", name="George"),
        "margaret": Voice(role="margaret", id="pFZP5JQG7iQjIQuC4Bku", name="Lily"),
        "driver": Voice(role="driver", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    },
    settings={"walt": CALLING, "margaret": SETTING, "driver": SETTING},
    takes=(
        takes.Take("01", "walt", "And he's out of the door. Robe only.", 0.1, shot="door", mood="firm"),
        _fx(
            2,
            "[BANG]",
            0.1,
            "door",
            "A front door banging, then a truck's reversing beeps down the street, no music",
            1.0,
        ),
        takes.Take("03", "margaret", "He's left it very late, Walt.", 0.2, shot="window", mood="calm"),
        takes.Take("04", "walt", "He's lost a slipper.", 0.1, shot="run", mood="firm"),
        _fx(5, "[SLAP]", 0.1, "run", "One bare foot slapping on a road, three quick steps, no voices, no music", 0.8),
        takes.Take(
            "06", "margaret", "That's the left. He's never been strong on the left.", 0.2, shot="run", mood="calm"
        ),
        takes.Take("07", "walt", "Forty yards. One wheel.", 0.2, shot="chase", mood="firm"),
        takes.Take("08", "margaret", "You can't teach this.", 0.2, shot="chase", mood="calm"),
        _fx(9, "[SCRAPE]", 0.1, "chase", "Metal and plastic scraping along a road at a run, sparks, no voices", 0.9),
        _fx(
            10,
            "[CLANG]",
            0.2,
            "dive",
            "A body sliding on a road and a trash bin clanging into a steel truck, no voices",
            1.2,
        ),
        takes.Take("11", "walt", "He's done it!", 0.1, shot="arms", mood="firm"),
        _fx(
            12, "[CHEER]", 1.0, "arms", "One person cheering from an upstairs window, a short clear yay, no music", 0.8
        ),
        _fx(13, "[BRAKES]", 0.1, "driver", "The hiss of a truck's air brakes, no voices, no music", 0.8),
        takes.Take("14", "driver", "Recycling's next week.", 1.5, shot="driver", mood="calm"),
        _fx(
            15, "[BEEPS]", 1.5, "road", "A truck's reversing beeps fading away down a street, no voices, no music", 1.4
        ),
        takes.Take("16", "margaret", "Oh, that's heartbreaking.", 0.5, shot="sip", mood="calm"),
        takes.Take("17", "walt", "Same time next week.", 0.5, shot="sip", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices George, Lily and Bill; no reference-voice cloning. Effects generated with "
    "ElevenLabs.",
    shots=SHOTS,
)

F = stick.Face
AHEAD = (1.0, 0.0)
PANIC = F("wide", "worried", "frown", AHEAD)
FLAT_OUT = F("wide", "angry", "flat", AHEAD)
JOY = F("happy", "raised", "smile", (0.0, 0.0))
AT_DRIVER = F("happy", "raised", "smile", (1.0, -0.4))
BLANK = F("open", "flat", "flat", (0.0, 0.0))
LANDED = F("wide", "worried", "frown", (1.0, -0.4))
SUNK = F("half", "worried", "frown", (0.0, 0.6))
DRIVER_FACE = F("half", "flat", "flat", (-0.6, 0.7))
WATCHING = F("open", "raised", "flat", (0.0, 0.6))
TALKING = F("open", "raised", "smirk", (1.0, 0.0))
SIPPING = F("closed", "raised", "flat", (0.0, 0.0))
DEV = stick.PLAIN
WALT = stick.Look(hair="bald", glasses=True, tie="#7a5a3a")
MARGARET = stick.Look(hair="bun", apron="#6b7fa8")
DRIVER = stick.Look(hair="spiky", cap="#d98a2b")
ROBE, ROBE_BELT = "#8f7fb0", "#6a5b88"

UP = stick.STANDING["stand"]


def _run(knees, feet, hand) -> stick.RigPose:
    return stick._seat((570, 750), (556, 857), (540, 1190), knees, feet, ((430, 1040), (640, 1040)), (hand, (720, 950)))


POSES: dict[str, stick.RigPose] = {
    "stand": UP,
    "run-a": _run(((450, 1420), (650, 1400)), ((340, 1640), (720, 1610)), (300, 1120)),
    "run-b": _run(((600, 1430), (480, 1420)), ((700, 1660), (360, 1600)), (300, 1120)),
    "dive": stick._seat((830, 1490), (720, 1500), (420, 1530), ((230, 1560), (240, 1590)), ((90, 1600), (110, 1650)),
                        ((900, 1470), (900, 1520)), ((1010, 1460), (1010, 1530))),
    "arms-up": stick._seat((540, 750), UP.neck, UP.hip, UP.knees, UP.feet, ((400, 720), (680, 720)),
                           ((340, 540), (740, 540))),
    "arms-mid": stick._seat((540, 756), UP.neck, UP.hip, UP.knees, UP.feet, ((400, 900), (680, 900)),
                            ((340, 800), (740, 800))),
    "arms-low": stick._seat((540, 770), UP.neck, UP.hip, UP.knees, UP.feet, ((450, 1020), (630, 1020)),
                            ((420, 1110), (660, 1110))),
    "hold-mug": stick._seat((540, 750), UP.neck, UP.hip, UP.knees, UP.feet, ((640, 1040), (640, 1040)),
                            ((700, 960), (700, 960))),
    "sip": stick._seat((540, 750), UP.neck, UP.hip, UP.knees, UP.feet, ((660, 960), (660, 960)),
                       ((610, 840), (610, 840))),
    "lean-out": stick._seat((480, 830), (530, 930), (640, 1190), UP.knees, UP.feet, ((460, 1040), (640, 1040)),
                            ((400, 1000), (700, 1140))),
}  # fmt: skip

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

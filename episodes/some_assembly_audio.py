#!/usr/bin/env python3
"""Stick 24 — Some Assembly: who says what on one take timeline, and how Noor and Dev play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 some_assembly_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_some_assembly.py`` checks this script. There is no music bed.

A couple build a wardrobe from a manual that knows them. Arm A of the first-second test: the held frame is ``STILL``
seconds of the opening take, nobody moving, before "Step one."
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("open", "half", "nine", "ten", "fourteen", "twenty-two", "mom", "later", "last", "bun")
HOOK = "Step one: two people, smiling."
STILL = 1.0
READ = 1.6  # the insert held to read
SETTING = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)


def _fx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float, peak: float = 0.4) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=peak)  # fmt: skip


SCRIPT = takes.Script(
    title="Some Assembly — Stick 24",
    seed=3124,
    still=STILL,
    voices={
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
    },
    settings={"noor": SETTING, "dev": SETTING},
    takes=(
        takes.Take("01", "noor", "Step one. Two people, smiling.", 0.2, shot="open", mood="calm"),
        takes.Take("02", "dev", "Easy.", 0.4, shot="open", mood="calm"),
        _fx(3, "[DRILL]", 0.3, "half", "A cordless drill whirring into wood, then cutting out dead, no voices", 1.2),
        takes.Take("04", "dev", "That's the wrong way round.", 0.45, shot="half", mood="firm"),
        takes.Take("05", "noor", "You said you measured.", 0.75, shot="half", mood="firm"),
        takes.Take("06", "noor", "...Step nine.", READ + 1.0, shot="nine", mood="calm"),
        _fx(7, "[PAGE]", 0.8, "ten", "One page of a paper manual turned, a single crisp flip, no voices", 0.6),
        takes.Take("08", "dev", "It's fine.", 0.2, shot="ten", mood="firm"),
        takes.Take("09", "noor", "It says you say that.", 0.3, shot="ten", mood="calm"),
        _fx(10, "[PAGE]", 0.6, "fourteen", "One page of a paper manual turned, a single crisp flip, no voices", 0.6),
        _fx(11, "[PAGE]", 0.6, "twenty-two", "One page of a paper manual turned quickly, no voices", 0.6),
        _fx(12, "[RING]", 0.1, "mom", "A smartphone ringing on a wooden floor, two short rings, no voices", 1.4),
        takes.Take("13", "noor", "Step twenty-three: Call your mother.", 1.2, shot="mom", mood="calm"),
        takes.Take("14", "dev", "That's normal, right?", 0.2, shot="later", mood="calm"),
        takes.Take("15", "noor", "It says that's normal.", 0.5, shot="later", mood="calm"),
        _fx(16, "[PAGE]", 0.1, "last", "One page of a paper manual turned, a single crisp flip, no voices", 0.6),
        takes.Take("17", "dev", "There's one more.", READ, shot="last", mood="calm"),
        takes.Take("18", "dev", "...That's your bun.", 2.2, shot="bun", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Jessica and Will; no reference-voice cloning. Effects generated with "
    "ElevenLabs.",
    shots=SHOTS,
)

F = stick.Face
AT_PAGE = (0.7, 0.8)
AT_DEV = (1.0, -0.3)
READING = F("open", "flat", "flat", AT_PAGE)
LOOKS_UP = F("open", "raised", "flat", AT_DEV)
SURE = F("happy", "raised", "smile", (0.0, 0.0))
WORK = F("open", "flat", "flat", (1.0, 0.0))
TOLD = F("open", "worried", "frown", (-1.0, 0.3))
FLAT_AT_HIM = F("half", "flat", "flat", AT_DEV)
STARE = F("wide", "flat", "flat", AT_PAGE)
FINE = F("half", "angry", "flat", (-1.0, 0.0))
AT_PHONE = F("wide", "raised", "flat", (1.0, 0.3))
PROUD = F("open", "raised", "smile", (0.0, 0.0))
UNEASY = F("open", "worried", "smile", (0.6, 0.6))
READS_ON = F("open", "flat", "flat", (0.7, 0.8))
AT_MANUAL = F("open", "raised", "flat", (-0.8, 0.6))
AT_BUN = F("wide", "worried", "flat", (0.0, 0.0))
CLOSELY = F("half", "raised", "smirk", (0.5, 0.9))

UP = stick.STANDING["stand"]
_LEGS = (((640, 1500), (660, 1520)), ((780, 1690), (800, 1700)))


def _floor(head, neck, elbows, hands) -> stick.RigPose:
    return stick._seat(head, neck, (440, 1650), *_LEGS, elbows, hands)


POSES: dict[str, stick.RigPose] = {
    "read": _floor((470, 1210), (456, 1317), ((540, 1460), (560, 1480)), ((640, 1400), (660, 1420))),
    "lean": _floor((500, 1230), (476, 1335), ((560, 1470), (580, 1490)), ((640, 1400), (660, 1420))),
    "stand": UP,
    "hold-up": stick._seat((540, 756), UP.neck, UP.hip, UP.knees, UP.feet, ((500, 1040), (620, 1040)),
                           ((620, 950), (660, 960))),
    "work": stick._seat((540, 750), UP.neck, UP.hip, UP.knees, UP.feet, ((510, 1040), (640, 1020)),
                        ((502, 1195), (740, 980))),
    "crossed": stick._seat((540, 750), UP.neck, UP.hip, UP.knees, UP.feet, ((450, 1060), (630, 1060)),
                           ((625, 1025), (455, 1025))),
    "arm-in-arm": stick._seat((540, 750), UP.neck, UP.hip, UP.knees, UP.feet, ((640, 1040), (480, 1040)),
                              ((730, 1090), (430, 1000))),
    "offer": stick._seat((540, 750), UP.neck, UP.hip, UP.knees, UP.feet, ((460, 1040), (650, 1030)),
                         ((380, 1090), (760, 1000))),
}  # fmt: skip

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

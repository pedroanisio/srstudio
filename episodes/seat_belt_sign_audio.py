#!/usr/bin/env python3
"""Stick 22 — Seat Belt Sign: who says what on one take timeline, and how Dev and Noor play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 seat_belt_sign_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_seat_belt_sign.py`` checks this script. There is no music bed; the two cabin tones are stings.

The plane lands and Dev stands up to wait, bent under the bins, and fights his way to row 14; the rear door opens.
Arm A of the first-second test: the held frame is ``STILL`` seconds of the opening take, before "Why are you standing?"
"""

from __future__ import annotations

import sys

from srstudio import stick, stick_airport, stick_windshield, stings, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("row", "squeeze", "moved", "neck", "turn", "noor", "last")
HOOK = "Why are you standing?"
STILL = 1.0
SETTING = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
CABIN = VoiceSettings(stability=0.8, similarity_boost=0.75, style=0.1, speed=1.0)


def _fx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float, peak: float = 0.4) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=peak)  # fmt: skip


SCRIPT = takes.Script(
    title="Seat Belt Sign — Stick 22",
    seed=3122,
    still=STILL,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
        "cabin": Voice(role="cabin", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    },
    settings={"dev": SETTING, "noor": SETTING, "cabin": CABIN},
    takes=(
        takes.Take("01", "noor", "Why are you standing?", 0.2, shot="row", mood="calm"),
        takes.Take("02", "dev", "Head start.", 0.2, shot="row", mood="firm"),
        stings.sting(3, "cabin-ding", 0.1, "row"),
        takes.Take("04", "noor", "The doors aren't open.", 0.7, shot="row", mood="calm"),
        takes.Take("05", "dev", "It's strategy.", 0.2, shot="squeeze", mood="firm"),
        _fx(
            6, "[SQUEEZE]", 0.2, "squeeze", "Bags rubbing and a man grunting as he squeezes past people, no music", 1.2
        ),
        takes.Take("07", "dev", "We moved!", 0.5, shot="moved", mood="firm"),
        takes.Take("08", "dev", "I can't feel my neck.", 1.2, shot="neck", mood="calm"),
        stings.sting(9, "cabin-chime", 0.1, "neck"),
        takes.Take(
            "10", "cabin", "Today we'll be leaving by the rear door.", 1.5, shot="neck", mood="calm", speed=0.82
        ),
        _fx(
            11, "[TURN]", 0.6, "turn", "A whole crowd of people rustling as they all turn round at once, no voices", 0.8
        ),
        _fx(
            12, "[STRETCH]", 1.1, "noor", "A paperback snapping shut and a seat creaking, dry, no voices, no music", 0.8
        ),
        takes.Take("13", "noor", "See you at baggage.", 0.3, shot="noor", mood="calm"),
        _fx(14, "[DOOR]", 1.4, "last", "A heavy aircraft door sighing open, far away, faint, no voices, no music", 1.4),
    ),
    voice_note="ElevenLabs premade voices Will, Jessica and Alice; no reference-voice cloning. Effects generated with "
    "ElevenLabs.",
    shots=SHOTS,
)

F = stick.Face
RIGHT = (1.0, 0.0)
SMUG = F("half", "raised", "smirk", RIGHT)
CALM = F("open", "flat", "flat", (-1.0, 0.0))
DRY = F("half", "raised", "smirk", (1.0, 0.0))
READING = F("half", "flat", "flat", (0.0, 1.0))
PROUD = F("open", "raised", "smile", (0.0, 0.0))
GLAD = F("wide", "raised", "smile", (0.0, 0.0))
NUMB = F("half", "worried", "frown", (0.0, 0.0))
SHOCK = F("wide", "worried", "flat", (0.0, 0.0))
BURIED = F("closed", "worried", "frown", (0.0, 0.0))
DEADPAN = F("half", "flat", "flat", (0.0, 0.0))
UPWARD = F("open", "flat", "flat", (0.6, -0.8))
DEV = stick_windshield.COUPLE["dev"]
NOOR = stick_windshield.COUPLE["noor"]
CHILD = stick.Look(hair="side-part")
STRANGERS = (stick.Look(hair="spiky"), stick.Look(hair="bald"), stick.Look(hair="side-part"))
COATS = ("#7f9fc4", "#6b5a48", "#55704f")

SHIFT = 230.0  # the cabin hangs this much lower in the frame, so a standing head meets the bins and a card clears them
DROP = 1800.0  # where a standing figure's feet are
UP = stick.STANDING["stand"]


def _standing(head, elbows, hands) -> stick.RigPose:
    return stick._seat(head, UP.neck, UP.hip, UP.knees, UP.feet, elbows, hands)


def _lowered(pose: stick.RigPose, by: float) -> stick.RigPose:
    down = lambda point: (point[0], point[1] + by)  # noqa: E731
    pairs = lambda both: (down(both[0]), down(both[1]))  # noqa: E731
    return stick._seat(down(pose.head), down(pose.neck), down(pose.hip), pairs(pose.knees), pairs(pose.feet),
                       pairs(pose.elbows), pairs(pose.hands))  # fmt: skip


POSES: dict[str, stick.RigPose] = {
    "stand": UP,
    "in-seat": _lowered(stick_airport.SQUEEZED["tucked-up"], SHIFT - (DROP - 1700.0)),
    **{name: stick_airport.SQUEEZED[name] for name in ("tucked", "tucked-up")},
    "bent": stick._seat((528, 985), (600, 960), (760, 1010), ((740, 1340), (800, 1340)), ((720, 1700), (820, 1700)),
                        ((560, 1120), (650, 1130)), ((520, 1250), (650, 1270))),
    "reach": _standing((560, 750), ((440, 700), (610, 1040)), ((300, 640), (620, 1190))),
    "wedged": stick._seat((568, 818), (610, 890), (640, 1190), UP.knees, UP.feet, ((480, 1050), (720, 1040)),
                          ((440, 1200), (720, 1190))),
    "limp": stick._seat((558, 838), (610, 900), (640, 1190), UP.knees, UP.feet, ((500, 1090), (720, 1040)),
                        ((500, 1320), (720, 1190))),
    "stretch": _standing((540, 750), ((430, 700), (650, 700)), ((470, 540), (610, 540))),
    "carry": _standing((540, 750), ((510, 1040), (640, 1030)), ((502, 1195), (690, 1190))),
    "kid": _standing((540, 750), ((470, 1020), (610, 1020)), ((460, 1190), (620, 1190))),
}  # fmt: skip

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

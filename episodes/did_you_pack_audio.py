#!/usr/bin/env python3
"""Stick 21 — Did You Pack: who says what on one take timeline, and how Dev, his grandmother and the officer play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 did_you_pack_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_did_you_pack.py`` checks this script. There is no music bed.

A grandmother hears "I'm full" as "more, please", and the meal follows Dev through security. Arm A of the first-second
test: the held frame is ``STILL`` seconds of the opening take, nobody moving, before "You look thin."
"""

from __future__ import annotations

import sys

from srstudio import stick, stick_home, stick_windshield, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("table", "plate", "door", "belt", "medium", "two", "xray", "note", "wobble", "bite")
HOOK = "You look thin."
NOTE = "FOR THE MAN AT SECURITY. YOU LOOK THIN."
STILL = 1.0
SETTING = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)


def _fx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float, peak: float = 0.4) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=peak)  # fmt: skip


SCRIPT = takes.Script(
    title="Did You Pack — Stick 21",
    seed=3121,
    still=STILL,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "grandma": Voice(role="grandma", id="pFZP5JQG7iQjIQuC4Bku", name="Lily"),
        "officer": Voice(role="officer", id="cjVigY5qzO86Huf0OWal", name="Eric"),
    },
    settings=dict.fromkeys(("dev", "grandma", "officer"), SETTING),
    takes=(
        takes.Take("01", "grandma", "You look thin.", 0.25, shot="table", mood="firm"),
        takes.Take("02", "dev", "I'm full, Grandma.", 0.25, shot="table", mood="calm"),
        _fx(
            3,
            "[SPLAT]",
            0.25,
            "plate",
            "A big wet spoonful of food landing on a full plate, close, dry, no voices",
            0.6,
        ),
        takes.Take("04", "grandma", "You ate nothing.", 0.2, shot="plate", mood="firm"),
        takes.Take("05", "dev", "That was four plates.", 0.3, shot="plate", mood="calm"),
        takes.Take("06", "dev", "I have a plane.", 0.2, shot="door", mood="firm"),
        takes.Take("07", "grandma", "For the road.", 0.2, shot="door", mood="calm"),
        takes.Take("08", "dev", "It's a two-hour flight.", 0.2, shot="door", mood="firm"),
        takes.Take("09", "grandma", "Exactly.", 0.2, shot="door", mood="firm"),
        _fx(
            10,
            "[THUD]",
            0.2,
            "door",
            "A suitcase zip pulled shut and one very heavy thud, dry, no voices, no music",
            1.0,
        ),
        _fx(
            11, "[BEEP]", 0.3, "belt", "A security conveyor belt stopping with one loud electronic beep, no voices", 0.9
        ),
        takes.Take("12", "officer", "Did you pack this bag yourself?", 0.35, shot="medium", mood="firm"),
        takes.Take("13", "dev", "...No.", 1.3, shot="two", mood="calm"),
        takes.Take("14", "officer", "Who packed it?", 0.3, shot="xray", mood="firm"),
        takes.Take("15", "dev", "My grandmother.", 0.5, shot="xray", mood="calm"),
        _fx(
            16,
            "[FOIL]",
            1.8,
            "note",
            "Aluminum foil crinkling as it is unwrapped, close, dry, no voices, no music",
            0.9,
        ),
        _fx(17, "[SNIFF]", 1.1, "wobble", "One small quiet sniff of a grown man trying not to cry, dry, no music", 0.6),
        takes.Take("18", "officer", "...She's right.", 0.4, shot="wobble", mood="calm", speed=0.9),
        _fx(19, "[BITE]", 1.0, "bite", "One big bite and slow chewing, close, dry, no voices, no music", 0.9),
    ),
    voice_note="ElevenLabs premade voices Will, Lily and Eric; no reference-voice cloning. Effects generated with "
    "ElevenLabs.",
    shots=SHOTS,
)

F = stick.Face
AT_HER = (1.0, 0.0)  # toward the other one: a mirrored figure's look mirrors with it
FIRM = F("half", "angry", "flat", AT_HER)
SURE = F("open", "raised", "smirk", AT_HER)
FULL = F("half", "worried", "flat", AT_HER)
PLEADING = F("wide", "worried", "frown", AT_HER)
FLAT = F("open", "flat", "flat", AT_HER)
FEAR = F("wide", "worried", "flat", AT_HER)
DUTY = F("open", "angry", "flat", AT_HER)
READING = F("half", "worried", "flat", (0.2, 0.9))
DOWN = F("wide", "worried", "frown", (0.0, 1.0))
WOBBLE_A = F("wide", "worried", "frown", (0.0, 0.0))
WOBBLE_B = F("closed", "worried", "frown", (0.0, 0.0))
FED = F("happy", "worried", "smile", (0.0, 0.0))
DEV = stick_windshield.COUPLE["dev"]
GRANDMA = stick.Look(hair="bun", apron="#c0453b")
OFFICER = stick.Look(hair="bald", tie="#2f4a6d", cap="#2f4a6d")
COAT = "#6b5a48"

UP = stick.STANDING["stand"]


def _arms(head, elbows, hands) -> stick.RigPose:
    return stick._seat(head, UP.neck, UP.hip, UP.knees, UP.feet, elbows, hands)


POSES: dict[str, stick.RigPose] = {
    **stick_home.POSES,
    "seated": stick._seat((540, 930), (540, 1036), (540, 1370), ((640, 1380), (660, 1380)), ((640, 1640), (664, 1640)),
                          ((470, 1180), (620, 1190)), ((560, 1232), (690, 1232))),
    "serve": _arms((560, 760), ((640, 990), (660, 960)), ((740, 980), (780, 920))),
    "zip": stick._seat((600, 800), (580, 900), (540, 1190), UP.knees, UP.feet, ((640, 1060), (660, 1050)),
                       ((720, 1170), (740, 1180))),
    "peer": _arms((560, 770), ((640, 1040), (640, 1040)), ((740, 1130), (740, 1130))),
    "note": _arms((540, 760), ((640, 1010), (640, 1010)), ((700, 920), (700, 920))),
    "bite": _arms((540, 756), ((420, 800), (640, 980)), ((340, 620), (590, 850))),
    "bite-wave": _arms((540, 756), ((400, 880), (640, 980)), ((280, 800), (590, 850))),
}  # fmt: skip
SEAT_X, HER_X = 300.0, 780.0  # across the table
PLATE_AT = (470.0, stick_home.TABLE_TOP)
STREET_Y, STREET_SCALE = 1470.0, 0.78  # the front path: feet and size of a figure at the door
DEV_X, OFFICER_X, BAG_X = 165.0, 960.0, 690.0
BAG_FROM = 460.0  # where the bag is when the shot opens, coming out of the scanner
SIGN = (530, 280, 490, 270)  # the checkpoint's sign, over the terminal's boarding sign
XRAY = (("chicken", 540.0, 500.0, 1.3), ("lasagna", 540.0, 880.0, 1.3), ("rolling-pin", 540.0, 1230.0, 1.2))


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

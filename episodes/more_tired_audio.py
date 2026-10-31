#!/usr/bin/env python3
"""Stick 17 — More Tired: who says what on one take timeline, what comes down the stairs, and how they play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 more_tired_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_more_tired.py`` checks this script. There is no music bed.

Two people compete over who slept less, until the baby cries and both of them are, suddenly, asleep. Arm A of the
first-second test: the kitchen holds for its first .45 s.
"""

from __future__ import annotations

import sys

from srstudio import stick, stick_home, stick_windshield, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("kitchen",)
HOOK = "6 a.m. The sleep contest."
SCRIPT = takes.Script(
    title="More Tired — Stick 17",
    seed=3129,
    voices={
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
    },
    settings={
        "noor": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
        "dev": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
    },
    takes=(
        takes.Take("01", "noor", "I slept two hours.", 0.2, shot="kitchen", mood="firm"),
        takes.Take("02", "dev", "I slept one.", 0.2, shot="kitchen", mood="firm"),
        takes.Take("03", "noor", "I was up at three with him.", 0.6, shot="kitchen", mood="firm"),
        takes.Take("04", "dev", "I was awake when you were up at three.", 0.2, shot="kitchen", mood="firm"),
        takes.Take("05", "noor", "You were snoring.", 0.2, shot="kitchen", mood="firm"),
        takes.Take("06", "dev", "I was resting loudly.", 2.0, shot="kitchen", mood="calm"),
        takes.Take("07", "noor", "I haven't slept since March.", 0.35, shot="kitchen", mood="firm"),
        takes.Take("08", "dev", "Which March?", 0.5, shot="kitchen", mood="calm"),
        takes.Take(
            "09",
            "sfx",
            "[SMALL CRY]",
            0.0,
            shot="kitchen",
            prompt="A baby's small cry from upstairs, far away and muffled through a floor, slowly rising, no voices, "
            "no music",
            seconds=1.6,
            longest=1.6,
            peak=0.25,
        ),
        takes.Take(
            "10",
            "sfx",
            "[HER SNORE]",
            0.1,
            shot="kitchen",
            prompt="One soft fake human snore, a light nasal breath in, dry, no voices, no music",
            seconds=1.2,
            longest=1.2,
            peak=0.35,
        ),
        takes.Take(
            "11",
            "sfx",
            "[HIS SNORE]",
            0.1,
            shot="kitchen",
            prompt="One loud fake human snore, deep and theatrical, dry, no voices, no music",
            seconds=1.4,
            longest=1.4,
            peak=0.5,
        ),
        takes.Take(
            "12",
            "sfx",
            "[BIGGER CRY]",
            0.1,
            shot="kitchen",
            prompt="A baby crying louder from upstairs, muffled through a floor, building, no voices, no music",
            seconds=2.2,
            longest=2.2,
            peak=0.4,
        ),
        takes.Take("13", "noor", "You're resting loudly.", 0.8, shot="kitchen", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Jessica and Will; no reference-voice cloning. Effects generated with "
    "ElevenLabs, the fridge door and the keys synthesized in code.",
    shots=SHOTS,
    still=0.45,
)

F = stick.Face
NOOR, DEV = stick_windshield.NOOR, stick.PLAIN
ACROSS = (1.0, 0.0)  # both faces mirror so +x looks at the other one
FRONT = (0.0, 0.0)
_LEGS = {"hip": (540, 1400), "knees": ((500, 1460), (580, 1460)), "feet": ((500, 1640), (580, 1640))}


def _at_table(head, neck, elbows, hands) -> stick.RigPose:
    return stick._seat(head, neck, _LEGS["hip"], _LEGS["knees"], _LEGS["feet"], elbows, hands)


def _standing(head, elbows, hands) -> stick.RigPose:
    return stick_home._arms(head, elbows, hands)


# Hers sit at the table with her near hand round the mug on it; his stand behind its far end, a mug in his near hand,
# so the fridge is reached with the other one.
POSES: dict[str, stick.RigPose] = {
    "seated": _at_table((540, 930), (540, 1037), ((470, 1140), (640, 1130)), ((500, 1210), (690, 1190))),
    "lean": _at_table((566, 950), (552, 1057), ((470, 1140), (660, 1130)), ((500, 1210), (690, 1190))),
    "head-down": _at_table((560, 1144), (500, 1100), ((440, 1190), (670, 1110)), ((500, 1226), (690, 1190))),
    "hold": _standing((540, 750), ((510, 1040), (620, 1020)), ((502, 1195), (640, 900))),
    "turn": _standing((566, 754), ((510, 1040), (620, 1020)), ((502, 1195), (640, 900))),
    "reach": _standing((506, 756), ((462, 950), (620, 1020)), ((444, 816), (640, 900))),
    "keys": _standing((526, 752), ((478, 1010), (620, 1020)), ((470, 1120), (640, 900))),
}
NOOR_AT, DEV_AT = (-60.0, 0.0), (1400.0, 0.0)  # with flip for him: seated at x 480, standing at x 860
MUG_AT = {"seated": (630.0, 1190.0), "lean": (630.0, 1190.0), "head-down": (630.0, 1190.0)}
# take: [(seconds into the take, pose from POSES, face)]; a take without a row holds the last pose
PARTS: dict[str, dict[str, list[tuple[float, str, stick.Face]]]] = {
    "noor": {
        "01": [(0, "seated", F("half", "flat", "flat", ACROSS))],
        "03": [(0, "lean", F("half", "angry", "flat", ACROSS))],
        "05": [(0, "lean", F("half", "angry", "smirk", ACROSS))],
        "06": [(0, "seated", F("half", "flat", "flat", ACROSS)),
               (0.9, "seated", F("half", "flat", "flat", (1.0, 0.3)))],
        "07": [(0, "seated", F("half", "worried", "flat", FRONT))],
        "09": [(0, "seated", F("half", "worried", "flat", FRONT)),
               (0.3, "seated", F("wide", "flat", "flat", (0.0, -0.6)))],
        "10": [(0, "head-down", F("closed", "flat", "flat", FRONT))],
        "12": [(0, "head-down", F("closed", "flat", "flat", FRONT)),
               (0.5, "head-down", F("peek", "flat", "flat", ACROSS))],
        "13": [(0, "head-down", F("peek", "angry", "flat", ACROSS))],
    },
    "dev": {
        "01": [(0, "hold", F("half", "flat", "flat", ACROSS))],
        "02": [(0, "turn", F("half", "angry", "flat", ACROSS))],
        "04": [(0, "turn", F("half", "raised", "flat", ACROSS))],
        "06": [(0, "turn", F("half", "raised", "flat", ACROSS))],
        "08": [(0, "keys", F("half", "flat", "flat", FRONT))],
        "09": [(0, "keys", F("half", "flat", "flat", FRONT)), (0.3, "keys", F("wide", "flat", "flat", (0.0, -0.6)))],
        "11": [(0, "keys", F("closed", "flat", "flat", FRONT))],
        "12": [(0, "keys", F("closed", "flat", "flat", FRONT)), (1.1, "keys", F("peek", "flat", "flat", ACROSS))],
        "13": [(0, "keys", F("peek", "flat", "flat", ACROSS))],
    },
}  # fmt: skip
# In take 06's hold: the fridge door opens, he reaches in, the keys come out, the door shuts behind him.
FRIDGE_OPENS, REACHES, TAKES_KEYS, FRIDGE_SHUTS = 0.25, 0.45, 1.1, 1.7
DOOR_GAIN, JINGLE_GAIN = -10, -14
EYE_CLOSES = 0.15  # after her last line: the peek ends, and that is the end
KEYS_AT = (956.0, 800.0)  # on the top shelf of the open fridge
DAWN, DAWN_STRENGTH = "#a7a9c4", 0.5
POOL = (700.0, 950.0, 760.0)
CAMERA = ((710.0, 900.0), 1.5, (540.0, 960.0))  # past the safe, the table's near edge above the captions


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

#!/usr/bin/env python3
"""Stick 20 — Wave Back: who says what on one take timeline, and how Noor and the man play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 wave_back_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_wave_back.py`` checks this script. There is no music bed.

Noor waves back at a man who was waving at someone behind her, and the arm has to become something. Arm B of the
first-second test: she is already walking on frame 1.
"""

from __future__ import annotations

import sys

from srstudio import stick, stick_windshield, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("walk", "past", "stretch", "class", "rows", "gym", "door", "man")
HOOK = "He wasn't waving at you."
SETTING = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
CLICK = "One single knuckle or shoulder joint clicking, close, dry, no voices, no music"


def _fx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float, peak: float = 0.4) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=peak)  # fmt: skip


SCRIPT = takes.Script(
    title="Wave Back — Stick 20",
    seed=3120,
    voices={
        "man": Voice(role="man", id="N2lVS1w4EtoT3dr4eOWO", name="Callum"),
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
        "passer": Voice(role="passer", id="pFZP5JQG7iQjIQuC4Bku", name="Lily"),
    },
    settings=dict.fromkeys(("man", "noor", "passer"), SETTING),
    takes=(
        takes.Take("01", "man", "Hey! Over here!", 0.15, shot="walk", mood="happy"),
        takes.Take("02", "noor", "Hey!", 0.5, shot="walk", mood="happy"),
        _fx(
            3, "[FEET]", 0.0, "past", "Quick footsteps walking past on a sidewalk, close, dry, no voices, no music", 1.0
        ),
        _fx(4, "[STING]", 1.5, "past", "One small soft comic deflating note, short, dry, no voices", 0.6),
        _fx(5, "[CLICK]", 0.2, "stretch", CLICK, 0.5, 0.5),
        takes.Take("06", "noor", "Stretching. Just stretching.", 0.3, shot="stretch", mood="calm"),
        takes.Take("07", "passer", "Is this a class?", 0.3, shot="class", mood="happy"),
        takes.Take("08", "noor", "...Yes.", 0.45, shot="class", mood="calm"),
        takes.Take("09", "noor", "And reach. That's twenty bucks.", 0.1, shot="rows", mood="firm"),
        _fx(10, "[COINS]", 0.3, "rows", "A handful of coins dropped in a tin, short, dry, no voices, no music", 0.7),
        _fx(11, "[RING]", 0.4, "gym", "One ring of a front desk telephone, close, dry, no voices, no music", 0.9),
        takes.Take("12", "passer", "Four hundred members, Noor.", 0.5, shot="gym", mood="happy"),
        _fx(13, "[CHIME]", 0.25, "door", "A shop door chime, two soft notes, dry, no voices, no music", 0.7),
        takes.Take("14", "man", "Hey! Noor!", 1.6, shot="door", mood="happy"),
        _fx(15, "[CLICK]", 0.5, "man", CLICK, 0.5, 0.5),
        takes.Take("16", "man", "...Stretching.", 1.1, shot="man", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Callum, Jessica and Lily; no reference-voice cloning. Effects generated with "
    "ElevenLabs.",
    shots=SHOTS,
)

F = stick.Face
AT_HIM = (1.0, 0.0)  # the figure is drawn facing right; mirrored, this is still toward the other one
BEAM = F("happy", "raised", "smile", AT_HIM)
STUCK = F("wide", "raised", "smile", AT_HIM)  # the smile staying on after the news
SINKING = F("wide", "worried", "flat", AT_HIM)
BLAND = F("open", "flat", "smile", (0.0, 0.0))  # at the viewer: nothing happened, she was stretching
NERVOUS = F("wide", "worried", "smile", (0.0, 0.0))
CALM = F("open", "flat", "smile", (0.0, 0.0))
BOSS = F("open", "raised", "smirk", (0.0, 0.0))
GLANCE = F("open", "raised", "flat", AT_HIM)
BEHIND = F("open", "raised", "flat", (-1.0, 0.0))
LEVEL = F("half", "flat", "flat", AT_HIM)  # she has him now
GRIN = F("happy", "raised", "smile", AT_HIM)
BEAMING = F("open", "raised", "smile", AT_HIM)
DYING = F("wide", "worried", "smile", AT_HIM)
CAUGHT = F("wide", "worried", "flat", (0.0, 0.0))
KEEN = F("open", "raised", "smile", (0.0, 0.0))
NOOR = stick_windshield.COUPLE["noor"]
MAN = stick.Look(hair="spiky")
FRIEND = stick.Look(hair="side-part", tie="#3d5a80")
PASSER = stick.Look(hair="cowlick", glasses=True)
CLASS = (
    stick.Look(hair="spiky", glasses=True),
    stick.Look(hair="bald"),
    stick.Look(hair="side-part"),
    stick.Look(hair="bun", glasses=True),
    stick.Look(hair="bald", tie="#c0453b"),
    stick.Look(hair="spiky", tie="#2a9d8f"),
)

UP = stick.STANDING["stand"]


def _arms(head, elbows, hands) -> stick.RigPose:
    return stick._seat(head, UP.neck, UP.hip, UP.knees, UP.feet, elbows, hands)


def _walk(knees, feet) -> stick.RigPose:
    return stick._seat((540, 754), UP.neck, UP.hip, knees, feet, ((470, 1040), (604, 1040)), ((452, 1180), (640, 1170)))


FAR_HANG = ((510, 1040), (502, 1195))
POSES: dict[str, stick.RigPose] = {
    **stick.STANDING,
    "walk-a": _walk(((470, 1440), (610, 1440)), ((424, 1700), (664, 1690))),
    "walk-b": _walk(((540, 1450), (556, 1440)), ((528, 1700), (560, 1690))),
    "wave-walk": stick._seat((540, 754), UP.neck, UP.hip, ((470, 1440), (610, 1440)), ((424, 1700), (664, 1690)),
                             ((470, 1040), (640, 830)), ((452, 1180), (690, 640))),
    "wave-high": _arms((536, 750), (FAR_HANG[0], (640, 820)), (FAR_HANG[1], (680, 620))),
    "wave-off": _arms((536, 750), (FAR_HANG[0], (670, 800)), (FAR_HANG[1], (770, 640))),
    "reach-1": _arms((528, 752), (FAR_HANG[0], (668, 760)), (FAR_HANG[1], (660, 560))),
    "reach-2": stick._seat((506, 758), (526, 858), UP.hip, UP.knees, UP.feet, ((470, 1030), (660, 730)),
                           ((520, 1130), (610, 520))),
    "reach-3": stick._seat((462, 772), (502, 862), UP.hip, UP.knees, UP.feet, ((462, 1030), (640, 700)),
                           ((524, 1130), (500, 500))),
    "hug": _arms((566, 760), ((640, 1000), (650, 960)), ((760, 1010), (770, 960))),
}  # fmt: skip

WALK_RATE = 6.0  # steps a second
FROM_X, TO_X = 170.0, 400.0  # Noor's walk up the sidewalk across the two opening takes
HER_X, HIS_X = 400.0, 860.0
HUG_X = 190.0  # where he ends up, past her
FRIEND_X = 20.0  # the person behind her
RIGHT, LEFT = False, True  # a figure's flip
CARD = "THREE YEARS LATER"
POSTER = "STRETCH WITH NOOR"
ROWS = ((0.47, 1380.0, (140.0, 330.0, 760.0, 950.0)), (0.36, 1190.0, (240.0, 850.0)))  # scale, feet, x: the class


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

#!/usr/bin/env python3
"""Stick — Can't Afford to Save: who says what, on one take timeline, and how Dev and Noor play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 cant_afford_to_save_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words and each voice id must resolve to the premade voice it names. The key comes
from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts; ``tests/test_cant_afford_to_save.py``
checks this script. There is no music bed; the effects are ``foley`` bursts written by the episode.

Black Friday week in the study. Dev has saved so much that the two of them cannot afford it. Boxes keep landing, he
never looks at them, a receipt runs to the floor, and Noor asks one quiet question. Two holds are real: nobody speaks
in them and no caption comes up, and the reel cuts on his last word.
"""

from __future__ import annotations

import sys
from dataclasses import replace

from srstudio import stick, takes
from srstudio import stick_windshield as ws
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("two", "dev", "noor")
HOOK = "BLACK FRIDAY WEEK"
PLAIN = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
OPENING = 0.42  # the box lands inside this, and her first word starts on its thump
BOX_LANDS = 0.36  # seconds into the reel the first box stops at her feet
GAP = 0.22  # between the quick lines
BOXES_HOLD = 0.9  # after "Not at sixty percent off.": two more land behind him
PHONE_HOLD = 1.4  # after "Did you check the account?": he looks, and a box taps his heel
SECOND_SLIDES, SECOND_LANDS, THIRD_DROPS, THIRD_LANDS = 0.04, 0.3, 0.36, 0.58  # into the hold
PHONE_UP, SINKS, HEEL_SLIDES, HEEL_TAPS = 0.12, 0.62, 0.82, 1.1  # into the hold
CUT_HOLD = 0.16  # after the last word
SCRIPT = takes.Script(
    title="Can't Afford to Save — Stick",
    seed=3421,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    },
    settings={"dev": PLAIN, "noor": PLAIN},
    takes=(
        takes.Take("01", "noor", "Is that a second air fryer?", GAP, shot="two", mood="calm"),
        takes.Take("02", "dev", "Sixty percent off.", GAP, shot="two", mood="calm"),
        takes.Take("03", "noor", "We have an air fryer.", GAP, shot="noor", mood="calm"),
        takes.Take("04", "dev", "Not at sixty percent off.", BOXES_HOLD, shot="dev", mood="calm"),
        takes.Take("05", "dev", "We saved $4,000.", GAP, shot="two", mood="calm"),
        takes.Take("06", "noor", "Did you check the account?", PHONE_HOLD, shot="noor", mood="calm"),
        takes.Take("07", "dev", "We can't afford to save any more.", CUT_HOLD, shot="dev", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Will and Jessica; no reference-voice cloning. Sound effects synthesized in "
    "code.",
    shots=SHOTS,
    still=OPENING,
)

F = stick.Face
SCALE = 0.86
FOOT = 1570.0  # where their feet stand, on the study's floor, clear of the caption band
LEFT = (-134.0, FOOT - 1700.0 * SCALE)
RIGHT = (1224.0, FOOT - 1700.0 * SCALE)
AT_HER = (0.9, -0.1)
AT_HIM = (0.9, 0.0)
NOOR_LOOK = ws.NOOR
DEV_LOOK = stick.PLAIN

_STAND = stick.STANDING["stand"]
_HOLDS_OUT = (775.0, 1010.0)  # his far hand, in the figure's coordinates: the receipt hangs from it
_SAGS = (770.0, 1040.0)
_PHONE = (690.0, 860.0)  # his near hand, the phone in front of his chest
_DOWN = (604.0, 1176.0)  # the same hand, come down to his side


def _out(base: stick.RigPose, hand: tuple[float, float]) -> stick.RigPose:
    return stick.reaching(base, hand, far=True)


POSES: dict[str, stick.RigPose] = {
    **stick.STANDING,
    "offers": _out(_STAND, _HOLDS_OUT),
    "phone": stick.reaching(replace(_out(_STAND, _HOLDS_OUT), head=(556.0, 766.0)), _PHONE),
    "sunk": stick.reaching(replace(_out(_STAND, _SAGS), head=(552.0, 786.0)), _DOWN),
    "looks-up": stick.reaching(replace(_out(_STAND, _SAGS), head=(548.0, 764.0)), _DOWN),
}
DEV_PROUD = F("open", "raised", "smile", AT_HER)
DEV_SAYS = F("half", "raised", "smile", AT_HER)
DEV_PITY = F("half", "raised", "flat", AT_HER)
DEV_GLAD = F("open", "raised", "smile", (0.6, 0.5))
DEV_READS = F("open", "flat", "flat", (0.7, 0.75))
DEV_DOWN = F("half", "flat", "flat", (0.7, 0.75))
DEV_QUIET = F("open", "flat", "flat", AT_HER)
NOOR_AT_BOX = F("open", "raised", "flat", (0.5, 0.9))
NOOR_ASKS = F("open", "raised", "flat", AT_HIM)
NOOR_PLAIN = F("open", "flat", "flat", AT_HIM)
NOOR_WATCHES = F("open", "flat", "flat", (0.9, 0.35))
NOOR_UP = F("open", "raised", "flat", (0.9, -0.2))

# shot: (focus, zoom, where the focus lands), in frame pixels of the set
CAMERAS = {
    "two": ((540.0, 960.0), 1.0, (540.0, 960.0)),
    "dev": ((330.0, 753.0), 1.8, (490.0, 670.0)),
    "noor": ((760.0, 753.0), 1.8, (590.0, 670.0)),
    "hold": ((330.0, 900.0), 1.15, (375.0, 830.0)),
}
FACES = {"dev": (330.0, 753.0), "noor": (760.0, 753.0)}
MARKS = {"cactus": (612.0, 1178.0), "code": (585.0, 1200.0)}
FIRST_BOX, BOX_FROM = (640.0, 1590.0), 60.0
STACK_X, STACK_FOOT = 150.0, 1530.0
BOX_W, BOX_H = 190.0, 150.0
HEEL_X, HEEL_FOOT = 202.0, 1582.0  # its near edge on his heel
OFF_LEFT = -130.0
DROP_FROM = 880.0
RECEIPT = 590.0  # px from his hand to the floor

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

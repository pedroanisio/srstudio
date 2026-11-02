#!/usr/bin/env python3
"""Stick — November First: who says what, on one take timeline, and how Dev and Noor play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 november_first_audio.py PROJECT [--font DIR] [--ffmpeg PATH] [--rehearse]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words and each voice id must resolve to the premade voice it names. The key comes
from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts; ``tests/test_november_first.py`` checks
this script. There is no music bed; the effects are ``foley`` bursts written by the episode.

The morning after Halloween, and Noor has decorated overnight. Dev objects three times, and even the speaker sides with
her. The speaker never speaks (canon rule ``systems-answer-in-notifications``): it answers in the beat after his
request, its ring lit, with a chime, the sleigh bells and a chip on screen. The one hold is real: nobody speaks in it
and no caption comes up, and the reel cuts a beat after "Who?".
"""

from __future__ import annotations

import sys
from dataclasses import replace

from srstudio import stick, stick_holiday, takes
from srstudio import stick_windshield as ws
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("wide", "noor", "pumpkin", "dev", "speaker", "stand", "close")
OPENING_TEXT = "my partner on november 1st"
OPENING = 0.45  # Dev is walking in and the lights have blinked on before his first word, inside the half second
OPENER_TOP = 232.0  # frame pixels: over the window, under the lights, above both heads
HOLD = 1.3  # after "What about Thanksgiving?": she stops and turns
# The speaker's answer, in seconds after "Speaker, play something normal." ends: its ring lights and the insert is on
# it; the chip comes up with the chime at CHIP_AT, the cut back to Dev comes at NAMED_AT while it is up, and it is down
# before his next line. CHIP_SECONDS is past the reading time of its words (opener.seconds) and the 0.84 s minimum.
CHIP_TEXT = ("Naughty list", "Added: Dev")  # the list as the notice's title, what was done as its body
CHIP_AT, NAMED_AT, CHIP_SECONDS = 0.25, 0.95, 1.6
BEAT = 2.0  # the hold after his request: the chip's beat, and the bells under it
CHIP_BOX = (240.0, 330.0, 760.0, 470.0)  # frame pixels: in the safe area, above Dev's head on his shot and the speaker
CUT_HOLD = 0.6  # after "Who?": a beat, long enough to read the one word, then the cut
LIGHTS_ON = 0.16  # seconds in: as he comes through the door
INSERT_END = 3  # "That was a Halloween": the insert hands over to Dev on this word's end
PLAIN = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
SCRIPT = takes.Script(
    title="November First — Stick",
    seed=3431,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    },
    settings={"dev": PLAIN, "noor": PLAIN},
    takes=(
        takes.Take("01", "dev", "It's November 1st.", 0.2, shot="wide", mood="calm", speed=0.82),
        takes.Take("02", "noor", "I know. We're late.", 0.22, shot="noor", mood="calm"),
        takes.Take("03", "dev", "That was a Halloween pumpkin.", 0.22, shot="pumpkin", mood="calm"),
        takes.Take("04", "noor", "He asked to stay.", 0.28, shot="noor", mood="calm"),
        takes.Take("05", "dev", "Speaker, play something normal.", BEAT, shot="dev", mood="calm"),
        # no 06: it was the speaker's voice, dropped; the ids stay as recorded
        takes.Take("07", "dev", "What about Thanksgiving?", HOLD, shot="stand", mood="calm"),
        takes.Take("08", "noor", "Who?", CUT_HOLD, shot="close", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Will and Jessica; no reference-voice cloning. "
    "Sound effects synthesized in code.",
    shots=SHOTS,
    still=OPENING,
)

F = stick.Face
FLOOR = 1700.0  # where a standing pose's feet are
DEV_X, DEV_FROM = 290.0, -230.0  # his middle at the end of the walk, and far enough off the left that his mug is too
NOOR_X = 720.0
TREE_X, TREE_SCALE = 920.0, 1.2
TREE_FOOT = 1690.0
TOP = 1180.0  # the worktop's top
WORKTOP_X = (-30.0, 520.0)
PUMPKIN_X, SPEAKER_X = 120.0, 425.0
SPEAKER_SCALE = 0.72
STRIDE = 0.2  # seconds a step of his shuffle takes
WALK_END = 1.0  # seconds into the reel he stops
LIGHTS = (385.0, 158.0, 755.0, 158.0)  # along the top of the window
RAISED = stick_holiday.stool_top(steps=2)
NOOR_AT = (NOOR_X - 540.0, -RAISED)
DEV_AT = (DEV_X - 540.0, 0.0)
NOOR_LOOK = ws.NOOR
DEV_LOOK = stick.Look()  # Dev at home: no tie
AT_THE_TIP = (0.9, -0.35)
DEV_SAYS = F("half", "raised", "flat", (0.9, 0.1))
DEV_AT_PUMPKIN = F("open", "worried", "flat", (-0.8, 0.6))
DEV_AT_SPEAKER = F("open", "flat", "flat", (0.8, 0.7))
DEV_NAMED = F("wide", "worried", "frown", (0.8, 0.7))  # the speaker has said his name
DEV_PLEADS = F("wide", "worried", "flat", (0.9, -0.2))
NOOR_BUSY = F("half", "flat", "flat", AT_THE_TIP)
NOOR_GENTLE = F("half", "raised", "smile", AT_THE_TIP)
NOOR_STOPS = F("open", "flat", "flat", AT_THE_TIP)
NOOR_TURNED = F("open", "raised", "flat", (-0.9, 0.2))  # honestly puzzled, at him, for the first time


def _dev_hand(x: float, y: float) -> tuple[float, float]:
    """A frame point in Dev's own coordinates."""
    return x - DEV_AT[0], y - DEV_AT[1]


def _noor_hand(x: float, y: float) -> tuple[float, float]:
    """A frame point in Noor's own coordinates, stood on the stool."""
    return x - NOOR_AT[0], y - NOOR_AT[1]


_STAND = stick.STANDING["stand"]
_MUG = _dev_hand(432.0, 965.0)  # his near hand, out in front of the robe
_HOLDING = stick.reaching(_STAND, _MUG, bend=1)
_DOWN = (510.0, 1190.0)  # his free hand, by his side
STAR_HAND = (872.0, 648.0)  # where she holds the star, on the frame
_STAR = _noor_hand(*STAR_HAND)  # her near hand, at the tip
_BRANCH = _noor_hand(806.0, 955.0)  # her far hand, low on the tree
_REACHING = stick.reaching(stick.reaching(replace(_STAND, head=(560.0, 748.0)), _STAR), _BRANCH, far=True, bend=1)
POSES: dict[str, stick.RigPose] = {
    "stand": _STAND,
    "holding": stick.reaching(_HOLDING, _DOWN, far=True, bend=-1),
    "shuffle-a": stick.reaching(replace(_HOLDING, head=(544.0, 760.0)), (470.0, 1160.0), far=True, bend=-1),
    "shuffle-b": stick.reaching(replace(_HOLDING, head=(538.0, 752.0)), (600.0, 1150.0), far=True, bend=1),
    "looks": stick.reaching(replace(_HOLDING, head=(566.0, 770.0)), _DOWN, far=True, bend=-1),
    "pleads": stick.reaching(replace(_HOLDING, head=(552.0, 748.0)), (680.0, 880.0), far=True, bend=1),
    "reaching": _REACHING,
    "fiddle": stick.reaching(_REACHING, (_STAR[0] + 26.0, _STAR[1] - 22.0)),
    "turned": replace(_REACHING, head=(540.0, 750.0)),
}
# shot: (focus, zoom, where the focus lands), in frame pixels of the set
CAMERAS = {
    "wide": ((540.0, 960.0), 1.0, (540.0, 960.0)),
    "noor": ((728.0, 590.0), 1.6, (520.0, 640.0)),
    "close": ((728.0, 590.0), 2.3, (460.0, 660.0)),  # the worktop's end and the speaker just off the left edge
    "dev": ((290.0, 750.0), 1.7, (500.0, 700.0)),
    "pumpkin": ((160.0, 1060.0), 2.4, (390.0, 900.0)),
    "speaker": ((380.0, 1100.0), 2.4, (520.0, 1000.0)),
}
FACES = {"dev": (300.0, 750.0), "noor": (728.0, 590.0)}  # the heads on the set
MARKS = {"cactus": (262.0, TOP), "code": (228.0, TOP + 12.0)}

JINGLE = 0.14  # seconds between the sleigh bells' hits


def jingles(start: float, end: float) -> list[float]:
    """When the sleigh bells hit: from ``start``, and the last hit is over by ``end`` (the speaker's last word)."""
    return [start + i * JINGLE for i in range(int((end - start) / JINGLE))]


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

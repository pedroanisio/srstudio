#!/usr/bin/env python3
"""Stick — Extra Hour: who says what, on one take timeline, and how Dev and Noor play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 extra_hour_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words and each voice id must resolve to the premade voice it names. The key comes
from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts; ``tests/test_extra_hour.py`` checks
this script. There is no music bed; the effects are ``foley`` bursts written by the episode.

The clocks went back and Dev has spent the one free hour on everything Noor can name. She stands; he sits with his
mug. The plate, the keys and the phone come to the table one at a time. The one hold is real: nobody speaks in it and no
caption comes up, and the reel cuts on the mug landing on his last word.
"""

from __future__ import annotations

import sys
from dataclasses import replace

from srstudio import stick, takes
from srstudio import stick_table as st
from srstudio import stick_windshield as ws
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("two", "dev", "noor", "charge", "close")
HOOK = "ONE FREE HOUR"
PLAIN = VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0)
OPENING = 0.3  # the plate lands inside this, and "Dishes?" starts on its sound
PLATE_DOWN = 0.17  # seconds into the reel the plate is on the table
GAP = 0.18  # between the quick lines
LOOK_PLATE, LOOK_KEYS, LOOK_PHONE, NOD, NOD_UP, NOD_END = 0.0, 0.38, 0.76, 1.08, 1.2, 1.3  # after her last line
LOOK_HOLD = 1.4
CUT_HOLD = 0.2  # after the last word: the mug has landed
SCRIPT = takes.Script(
    title="Extra Hour — Stick",
    seed=3405,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    },
    settings={"dev": PLAIN, "noor": PLAIN},
    takes=(
        takes.Take("01", "noor", "Dishes?", GAP, shot="two", mood="calm"),
        takes.Take("02", "dev", "Extra hour.", GAP, shot="two", mood="calm"),
        takes.Take("03", "noor", "The car?", GAP, shot="two", mood="calm"),
        takes.Take("04", "dev", "Extra hour.", GAP, shot="two", mood="calm"),
        takes.Take("05", "noor", "Your mother?", 0.25, shot="two", mood="calm"),
        takes.Take("06", "dev", "Extra hour. Clocks went back, babe.", 0.3, shot="dev", mood="calm"),
        takes.Take("07", "noor", "You slept till noon.", 0.25, shot="noor", mood="calm"),
        takes.Take("08", "dev", "That was the extra hour.", 0.35, shot="dev", mood="calm"),
        takes.Take("09", "noor", "You've spent that hour four times.", LOOK_HOLD, shot="charge", mood="calm"),
        takes.Take("10", "dev", "It's a big hour.", CUT_HOLD, shot="close", mood="calm"),
    ),
    voice_note="ElevenLabs premade voices Will and Jessica; no reference-voice cloning. Sound effects synthesized in "
    "code.",
    shots=SHOTS,
    still=OPENING,
)

F = stick.Face
AT_HER = (0.9, -0.1)
AT_HIM = (0.9, 0.25)  # mirrored, she looks left and down at him
AT_TABLE = (0.55, 0.8)
NOOR_LOOK = ws.NOOR
DEV_LOOK = stick.Look()  # Dev at home: no tie
LEFT = st.LEFT_AT
RIGHT = (1160.0, st.RIGHT_AT[1])  # she stands, a little further along than her chair
TOP = st.TOP
PLATE_X, KEY_X, PHONE_X, PHONE_FROM, MUG_X = 648.0, 770.0, 528.0, 705.0, 410.0  # x along the table
PLATE_SCALE, PLATE_HEAP, KEY_SCALE, PHONE_SCALE = 0.33, 2, 1.0, 0.72
PHONE_RUN = 0.42  # how long it slides
DEV_SMUG = F("half", "flat", "smile", (0.75, 0.5))  # at his mug: not looking up
DEV_SAYS = F("half", "raised", "smile", AT_HER)
DEV_GLAD = F("open", "raised", "smile", AT_HER)
DEV_SURE = F("open", "flat", "smirk", AT_HER)
DEV_AT_PLATE = F("open", "flat", "flat", (0.8, 0.7))
DEV_AT_KEYS = F("open", "raised", "flat", (1.0, 0.45))
DEV_AT_PHONE = F("open", "flat", "flat", (0.55, 0.85))
DEV_NODS = F("half", "raised", "smile", (0.6, 0.6))
DEV_CALM = F("half", "raised", "smile", AT_HER)
NOOR_ASKS = F("open", "raised", "flat", AT_HIM)
NOOR_PLAIN = F("open", "flat", "flat", AT_HIM)
NOOR_DOWN = F("half", "flat", "flat", AT_TABLE)
NOOR_WINDOW = F("open", "flat", "flat", (-0.5, -0.8))


def _mug_at(x: float, y: float) -> tuple[float, float]:
    """Where Dev's near hand goes to hold the mug's middle at ``x, y`` of the set."""
    return x - LEFT[0], y - LEFT[1]


_REST = st.POSES["back"]
_DOWN = (MUG_X, TOP - 39.0)  # the mug's middle with its foot on the table
_CRADLE = stick.reaching(_REST, _mug_at(430.0, 925.0), bend=1)
_SPREAD_BASE = stick.reaching(replace(st.POSES["straight"], head=(372.0, 893.0)), _mug_at(482.0, 870.0))


_HER_HIP = (392.0, 1062.0)  # her far hand, on her hip, in the figure's own coordinates


def _noor(hand: tuple[float, float], head: tuple[float, float], neck: tuple[float, float], *, bend: int = 1):
    """Noor bent over the table with her near hand at ``hand`` of the set, at the figure's own coordinates."""
    base = replace(st.POSES["up"], head=head, neck=neck)
    braced = stick.reaching(base, _HER_HIP, far=True, bend=1)
    return stick.reaching(braced, (RIGHT[0] - hand[0], hand[1] - RIGHT[1]), bend=bend)


POSES: dict[str, stick.RigPose] = {
    **st.POSES,
    "stands": stick.reaching(st.POSES["up"], _HER_HIP, far=True, bend=1),
    "cradle": _CRADLE,
    "sip": stick.reaching(replace(_REST, head=(346.0, 898.0)), _mug_at(386.0, 838.0), bend=1),
    "spread": stick.reaching(_SPREAD_BASE, _mug_at(530.0, 1030.0), far=True, bend=1),
    "plate-over": stick.reaching(replace(st.POSES["rest"], head=(392.0, 925.0)), _mug_at(430.0, 925.0)),
    "keys-over": stick.reaching(replace(st.POSES["rest"], head=(404.0, 915.0)), _mug_at(430.0, 925.0)),
    "phone-over": stick.reaching(replace(st.POSES["rest"], head=(384.0, 935.0)), _mug_at(430.0, 925.0)),
    "nod": stick.reaching(replace(st.POSES["rest"], head=(392.0, 950.0)), _mug_at(430.0, 925.0)),
    "mug-up": _CRADLE,
    "mug-low": stick.reaching(_REST, _mug_at(MUG_X, 990.0), bend=1),
    "mug-down": stick.reaching(_REST, _mug_at(*_DOWN), bend=1),
    "plate-up": _noor((PLATE_X, 930.0), (548.0, 780.0), (480.0, 852.0), bend=-1),
    "plate": _noor((PLATE_X, TOP - 30.0), (548.0, 780.0), (480.0, 852.0)),
    "key-up": _noor((KEY_X, 950.0), (505.0, 790.0), (450.0, 866.0), bend=-1),
    "key": _noor((KEY_X, TOP - 30.0), (505.0, 790.0), (450.0, 866.0), bend=-1),
    "flick-a": _noor((PHONE_FROM, TOP - 30.0), (520.0, 790.0), (464.0, 866.0)),
    "flick-b": _noor((PHONE_FROM - 70.0, TOP - 30.0), (548.0, 780.0), (480.0, 852.0)),
}
# shot: (focus, zoom, where the focus lands), in frame pixels of the set
CAMERAS = {
    "two": ((540.0, 960.0), 1.12, (540.0, 1040.0)),
    "dev": ((302.0, 800.0), 1.7, (470.0, 880.0)),
    "noor": ((756.0, 510.0), 1.3, (760.0, 620.0)),
    "over": ((540.0, 960.0), 1.3, (470.0, 1040.0)),
    "close": ((302.0, 800.0), 2.0, (430.0, 800.0)),
}
FACES = {"dev": (280.0, 775.0), "noor": (756.0, 510.0)}  # the heads on the set, Dev sat back
MARKS = {"cactus": (335.0, TOP), "code": (325.0, TOP + 12)}

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

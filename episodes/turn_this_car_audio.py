#!/usr/bin/env python3
"""Stick 16 — Turn This Car: who says what on one take timeline, what the road sounds like, and how they play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 turn_this_car_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_turn_this_car.py`` checks this script. There is no music bed.

The threat every parent makes, and the one parent who kept it, 410 miles back. Arm A of the first-second test: the
mirror holds for its first .45 s, and the reel ends on the same mirror, so it can run again.
"""

from __future__ import annotations

import sys

from srstudio import foley, stick, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("mirror", "car", "beach", "uturn", "home", "dusk", "night")
HOOK = "Five miles from the beach."
HOUR_SIX, TWO_AM = "HOUR SIX.", "2 A.M. Their driveway."
SCRIPT = takes.Script(
    title="Turn This Car — Stick 16",
    seed=3127,
    voices={
        "dad": Voice(role="dad", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "mom": Voice(role="mom", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
        "kid": Voice(role="kid", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    },
    settings={
        "dad": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
        "mom": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
        "kid": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.2, speed=1.0),
    },
    takes=(
        takes.Take("01", "dad", "One more word and I turn this car around.", 0.35, shot="mirror", mood="firm"),
        takes.Take("02", "kid", "Word.", 2.0, shot="car", mood="calm"),
        takes.Take("03", "mom", "We paid for the hotel.", 0.25, shot="car", mood="firm"),
        takes.Take("04", "dad", "I said what I said.", 0.4, shot="car", mood="firm"),
        takes.Take(
            "05",
            "sfx",
            "[SIGN PASSING]",
            0.0,
            shot="beach",
            prompt="A car driving past a road sign at speed on a highway, one soft whoosh, no voices, no music",
            seconds=1.1,
            longest=1.1,
            peak=0.4,
        ),
        takes.Take(
            "06",
            "sfx",
            "[TIRES]",
            0.0,
            shot="uturn",
            prompt="One long car tire squeal through a tight U-turn on a road, no voices, no music",
            seconds=2.2,
            longest=2.2,
            peak=0.5,
        ),
        takes.Take(
            "07",
            "sfx",
            "[SIGN AGAIN]",
            0.1,
            shot="home",
            prompt="A car driving past a road sign at speed on a highway, one soft whoosh, no voices, no music",
            seconds=1.1,
            longest=1.1,
            peak=0.4,
        ),
        takes.Take(
            "08",
            "sfx",
            "[CABIN]",
            0.0,
            shot="dusk",
            prompt="The steady low hum of a car interior on a long highway drive, no voices, no music",
            seconds=1.2,
            longest=1.2,
            peak=0.3,
        ),
        takes.Take("09", "mom", "You can stop this.", 0.3, shot="dusk", mood="calm"),
        takes.Take("10", "dad", "They have to learn.", 0.5, shot="dusk", mood="firm"),
        takes.Take(
            "11",
            "sfx",
            "[ENGINE OFF]",
            0.2,
            shot="night",
            prompt="A parked car engine switched off, a short shudder then quiet, no voices, no music",
            seconds=1.1,
            longest=1.1,
            peak=0.4,
        ),
        takes.Take("12", "dad", "Let that be a lesson.", 2.0, shot="night", mood="calm"),
        takes.Take("13", "kid", "Word.", 0.4, shot="night", mood="calm"),
        takes.Take(
            "14",
            "sfx",
            "[QUIET CABIN]",
            0.1,
            shot="mirror",
            prompt="The near silence of a parked car at night, very faint room tone, no voices, no music",
            seconds=1.8,
            longest=1.8,
            peak=0.08,
        ),
    ),
    voice_note="ElevenLabs premade voices Will, Jessica and River; no reference-voice cloning. Effects generated with "
    "ElevenLabs, the indicator and the engine ticks synthesized in code.",
    shots=SHOTS,
    still=0.45,
)

F = stick.Face
STRAW, CORAL, SKY = "#e8cf8e", "#ee9a6d", "#8fc3d9"
DAD = stick.Look(sunhat=STRAW)
MOM = stick.Look(hair="bun", glasses=True, sunhat=CORAL)
KID = stick.Look(sunhat=SKY)
AHEAD, AT_HIM = (0.0, 0.0), (1.0, 0.0)
GLARE = F("half", "angry", "flat", AHEAD)  # the mirror's face: the reel's first frame and its last
# take: what the mirror's eyes do; the last row of the last take is the first frame again
IN_MIRROR: dict[str, list[tuple[float, stick.Face]]] = {
    "01": [(0, GLARE), (1.55, F("half", "angry", "flat", (0.55, 0.0))), (2.1, GLARE)],
    "14": [(0, F("wide", "raised", "flat", AHEAD)), (0.5, GLARE)],
}
STARE = F("open", "flat", "flat", AHEAD)
TIRED = F("half", "flat", "flat", AHEAD)
# take: [(seconds into the take, pose from stick_windshield.FRONT, face)]; a take without a row holds the last pose
PARTS: dict[str, dict[str, list[tuple[float, str, stick.Face]]]] = {
    "mom": {
        "02": [(0, "sit", STARE), (0.55, "sit", F("open", "flat", "flat", (0.3, 0.0))),
               (1.1, "sit", F("open", "raised", "flat", (0.65, 0.0))),
               (1.65, "sit", F("open", "raised", "flat", AT_HIM))],
        "03": [(0, "cite", F("half", "angry", "frown", AT_HIM))],
        "04": [(0, "crossed", F("half", "angry", "frown", AT_HIM))],
        "08": [(0, "slump", TIRED)],
        "09": [(0, "slump", F("half", "worried", "flat", AT_HIM))],
        "11": [(0, "slump", TIRED)],
        "13": [(0, "slump", F("wide", "flat", "flat", AHEAD))],
    },
    "dad": {
        "02": [(0, "drive", STARE)],
        "04": [(0, "drive", F("half", "angry", "flat", AHEAD))],
        "08": [(0, "drive", TIRED)],
        "10": [(0, "drive", F("half", "angry", "flat", AHEAD))],
        "11": [(0, "drive", TIRED)],
        "12": [(0, "drive", F("half", "flat", "smirk", AHEAD))],
        "13": [(0, "drive", F("wide", "flat", "flat", AHEAD))],
    },
    "kid": {
        "02": [(0, "sit", F("open", "raised", "flat", AHEAD))],
        "03": [(0, "sit", F("open", "flat", "flat", AHEAD))],
        "08": [(0, "sit", F("half", "flat", "flat", AHEAD))],
        "11": [(0, "sit", F("half", "flat", "flat", AHEAD))],
        "13": [(0, "sit", F("open", "flat", "smirk", AHEAD))],
    },
}  # fmt: skip
MIRROR_SCALE = 5.0
MIRROR_AT = (
    540.0 - 540.0 * MIRROR_SCALE,
    900.0 - 930.0 * MIRROR_SCALE,
)  # a FRONT head, its eyes in the glass, its mouth not
KID_SCALE = 0.55
KID_AT = (540.0 - 540.0 * KID_SCALE, 820.0 - 930.0 * KID_SCALE)
ARROW = (540.0, 1405.0)
CLICKS = (0.45, 1.0, 1.55)  # seconds after the line or the cut: the indicator's three clicks, and the last shot's
LAST_CLICKS = (0.1, 0.65, 1.2)
TICKS = (0.3, 0.72, 1.2, 1.75)  # seconds after the line: the engine cooling, each tick later than the last
ROAD_GAIN, CLICK_GAIN, TICK_GAIN = -14, -8, -9
INDICATOR = foley.Burst(0.05, 3200.0, attack=0.001, decay=0.3, tone_hz=1100.0, tone_end_hz=820.0, tone=0.55)
ENGINE_TICK = foley.Burst(0.03, 5000.0, attack=0.001, decay=0.25, tone_hz=2600.0, tone_end_hz=2200.0, tone=0.5)
RINGS = ((262.0, 762.0, 118.0, 74.0, "#d9483b"), (818.0, 762.0, 118.0, 74.0, "#2f7fc1"))  # squashed on the rear glass


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

#!/usr/bin/env python3
"""Not a Robot — Ink 03: the voices, the effect and the take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 not_a_robot_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

One form before lunch. The captcha's questions get more personal until it decides the human is a robot, and the
router from *The Router* welcomes him home. Three premade voices: the human (Chris), the captcha (Sarah) and the
router (Daniel). The recording is :mod:`srstudio.takes`: one request per take, every line heard back by
speech-to-text, the voices confirmed by name, no retries. ``SCREENS`` says what the screen shows in each screen
take (``not_a_robot.py`` draws it).
"""

from __future__ import annotations

import sys

from srstudio import takes
from srstudio.voice import Voice, VoiceSettings

SEED = 1029
TITLE = "Not a Robot — Ink 03"
FONT = ("PatrickHand-Regular.ttf", "font-license.txt")
VOICES = {
    "human": Voice(role="human", id="iP95p4xoKVk53GoZ742B", name="Chris"),
    "captcha": Voice(role="captcha", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"),
    "router": Voice(role="router", id="onwK4e9ZLuTAKqWW03F9", name="Daniel"),
}
SETTINGS = {
    "human": VoiceSettings(stability=0.42, similarity_boost=0.75, style=0.32, speed=1.06),
    "captcha": VoiceSettings(stability=0.80, similarity_boost=0.75, style=0.05, speed=0.96),
    "router": VoiceSettings(stability=0.72, similarity_boost=0.75, style=0.08, speed=0.94),
}
SHOTS = ("desk", "human", "screen", "router", "router-close")

TAKES = (
    takes.Take("01", "human", "One form before lunch. How hard can it be?", 0.30, shot="desk", mood="impatient"),
    takes.Take("02", "captcha", "Please confirm you're not a robot.", 0.90, shot="screen", mood="calm"),
    takes.Take("03", "captcha", "Select all images with traffic lights.", 0.20, shot="screen", mood="calm"),
    takes.Take("04", "human", "Easy.", 1.30, shot="screen", mood="calm"),
    takes.Take("05", "captcha", "Select all traffic lights that are sad.", 0.50, shot="screen", mood="calm"),
    takes.Take("06", "human", "That one's having a day.", 0.40, shot="human", mood="question"),
    takes.Take("07", "captcha", "Select every moment you felt truly alive.", 2.00, shot="screen", mood="calm"),
    takes.Take("08", "human", "Skip?", 0.50, shot="human", mood="question"),
    takes.Take(
        "09",
        "sfx",
        "[ERROR BUZZ]",
        0.10,
        shot="screen",
        prompt="A short harsh computer error buzz, two quick low tones, clean digital interface sound, no voices, "
        "no music",
        seconds=0.8,
        longest=0.7,
        peak=0.45,
    ),
    takes.Take(
        "10",
        "captcha",
        "Verification failed. You hesitated like a human, but you clicked like a robot.",
        0.50,
        shot="screen",
        mood="calm",
    ),
    takes.Take("11", "router", "Welcome, brother.", 0.60, shot="router", mood="calm"),
    takes.Take("12", "human", "I'm not a... Do robots get lunch?", 1.30, shot="human", mood="angry"),
    takes.Take("13", "router", "Only after a reboot.", 0.90, shot="router-close", mood="calm"),
    takes.Take("14", "captcha", "Please confirm you're not a router.", 1.00, shot="screen", mood="calm"),
)


LIGHTS = ("light", "car", "light", "tree", "light", "car", "tree", "car", "light")
SAD = ("happy-light",) * 5 + ("sad-light",) + ("happy-light",) * 3
ALIVE = ("laptop",) * 9
FAILED = "VERIFICATION FAILED"
# What the screen shows in each screen take; times are seconds into the take.
SCREENS = {
    "02": dict(label="I'm not a robot", tick="end"),
    "03": dict(prompt="Select all images with traffic lights.", tiles=LIGHTS),
    "04": dict(
        prompt="Select all images with traffic lights.", tiles=LIGHTS, picks=[(0.6, 0), (0.85, 2), (1.1, 4), (1.35, 8)]
    ),  # fmt: skip
    "05": dict(prompt="Select all traffic lights that are sad.", tiles=SAD),
    "07": dict(prompt="Select every moment you felt truly alive.", tiles=ALIVE),
    "09": dict(prompt="Select every moment you felt truly alive.", tiles=ALIVE, verdict=(0.0, FAILED)),
    "10": dict(prompt="Select every moment you felt truly alive.", tiles=ALIVE, verdict=(0.0, FAILED)),
    "14": dict(label="I'm not a router"),
}


def script() -> takes.Script:
    return takes.Script(
        title=TITLE,
        seed=SEED,
        voices=VOICES,
        settings=SETTINGS,
        takes=TAKES,
        voice_note="ElevenLabs premade voices Chris, Sarah and Daniel; no reference-voice cloning.",
        shots=SHOTS,
        font=FONT,
    )


if __name__ == "__main__":
    sys.exit(takes.main(script()))

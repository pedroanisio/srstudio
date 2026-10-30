#!/usr/bin/env python3
"""Stick 12 — Good, You: who says what, on one take timeline, and how the two coworkers play it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 good_you_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and verified,
speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names, and each
effect is length-checked. The key comes from ``ELEVENLABS_API_KEY`` and is never written; the script runs only with
``SRSTUDIO_ALLOW_CLOUD=1``. ``tests/test_takes.py`` feeds the pipeline misheard takes and malformed scripts;
``tests/test_good_you.py`` checks this script. There is no music bed.

Identical lines are identical on purpose: a repeated line is one recording, from the client's cache, so the deadpan
does not change whatever happens to them. Arm A of the first-second test: the held frame is ``STILL`` seconds of the
opening take.
"""

from __future__ import annotations

import sys

from srstudio import stick, takes
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("mon1", "mon2", "mon3", "mon4", "mon5", "friday", "meteor", "sip")
HOOK = "How was your weekend?"
STILL = 1.0  # the held frame
DEADPAN = VoiceSettings(stability=0.8, similarity_boost=0.75, style=0.0, speed=1.0)
DAYS = {"mon2": "Next Monday", "mon3": "Next Monday", "mon4": "Next Monday", "mon5": "Next Monday", "friday": "Friday"}
HOW, GOOD_YOU, GOOD = "How was your weekend?", "Good, you?", "Good."


def _say(number: int, actor: str, text: str, hold: float, shot: str, mood: str = "firm") -> takes.Take:
    return takes.Take(f"{number:02d}", actor, text, hold, shot=shot, mood=mood)


def _sfx(number: int, tag: str, hold: float, shot: str, prompt: str, seconds: float) -> takes.Take:
    return takes.Take(f"{number:02d}", "sfx", tag, hold, shot=shot, prompt=prompt, seconds=seconds, longest=seconds,
                      peak=0.4)  # fmt: skip


SCRIPT = takes.Script(
    title="Good, You",
    seed=1312,
    voice_note="Premade voices: Roger and River, both held to one flat take of each line.",
    voices={
        "a": Voice(role="a", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
        "b": Voice(role="b", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    },
    settings=dict.fromkeys(("a", "b"), DEADPAN),
    takes=(
        _say(1, "a", HOW, 0.10, "mon1"),
        _say(2, "b", GOOD_YOU, 0.32, "mon1"),
        _say(3, "a", GOOD, 0.55, "mon1"),
        _say(4, "a", HOW, 0.10, "mon2"),
        _say(5, "b", GOOD_YOU, 0.32, "mon2"),
        _say(6, "a", GOOD, 0.45, "mon2"),
        _say(7, "a", HOW, 0.10, "mon3"),
        _say(8, "b", GOOD_YOU, 0.32, "mon3"),
        _sfx(9, "[SQUAWK]", 0.05, "mon3", "One short parrot squawk, close, dry, no voices, no music", 0.6),
        _say(10, "a", GOOD, 0.45, "mon3"),
        _say(11, "b", GOOD_YOU, 0.32, "mon4"),
        _say(12, "a", GOOD, 0.50, "mon4"),
        _say(13, "b", GOOD_YOU, 0.32, "mon5"),
        _say(14, "a", GOOD, 0.65, "mon5"),
        _say(15, "b", "Any plans?", 0.25, "friday"),
        _say(16, "a", "Not much.", 0.35, "friday"),
        _sfx(
            17,
            "[METEOR]",
            0.10,
            "meteor",
            "A meteor screaming down and a huge distant impact boom, rumbling, no voices, no music",
            2.0,
        ),  # fmt: skip
        _sfx(
            18,
            "[SIP]",
            0.70,
            "sip",
            "One small quiet sip of hot coffee from a mug, close, dry, no voices, no music",
            0.8,
        ),
    ),
    shots=SHOTS,
    bed=None,
    still=STILL,
)

F = stick.Face
A = stick.Look(hair="spiky", tie="#35608f")
B = stick.Look(hair="side-part", glasses=True)
FLAT_A = F("half", "flat", "flat", (0.8, 0.0))
FLAT_B = F("half", "flat", "flat", (0.8, 0.0))
FRONT = F("half", "flat", "flat", (0.0, 0.0))  # the meteor lands; neither looks
SIPPING = F("closed", "flat", "flat", (0.0, 0.0))
LAND_AT = 1.1  # seconds into the meteor shot
CAMERAS = {  # (focus, zoom, to): focus lands at to
    "two": ((540.0, 900.0), 1.25, (540.0, 990.0)),
    "sip": ((760.0, 800.0), 1.7, (660.0, 900.0)),
}

if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))

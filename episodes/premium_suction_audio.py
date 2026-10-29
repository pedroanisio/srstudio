#!/usr/bin/env python3
"""Premium Suction — Ink 06: the voices, the effect and the take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 premium_suction_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The robot vacuum has stopped in the middle of the floor: the free trial ended. He bought it; he bought the hardware,
suction is monthly. The kitchen is premium, the corners platinum. What is free? It maps the home and sells the map.
Who would buy that? The landlord texts: he saw the map, rent goes up in May. He liked the second bedroom, which is
the closet, except on the map. Deleting it is premium. Two premade voices: the human (Chris, as in the earlier Ink
episodes) and the vacuum (Lily), plus one effect. The recording is :mod:`srstudio.takes`: one request per take,
every line heard back by speech-to-text, the voices confirmed by name, no retries. ``VACUUM`` says how the vacuum
moves and what its display shows in each of its shots, ``MAPS`` what the map does, ``SCREENS`` what the phone
shows (``premium_suction.py`` draws them with :mod:`srstudio.ink_vacuum` and :mod:`srstudio.ink_phone`).
"""

from __future__ import annotations

import sys

from srstudio import takes
from srstudio.ink_phone import Bubble
from srstudio.voice import Voice, VoiceSettings

SEED = 1106
TITLE = "Premium Suction — Ink 06"
FONT = ("PatrickHand-Regular.ttf", "font-license.txt")
VOICES = {
    "human": Voice(role="human", id="iP95p4xoKVk53GoZ742B", name="Chris"),
    "vacuum": Voice(role="vacuum", id="pFZP5JQG7iQjIQuC4Bku", name="Lily"),
}
SETTINGS = {
    "human": VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.35, speed=1.06),
    "vacuum": VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15, speed=1.0),
}
SHOTS = ("vacuum", "vacuum-close", "human", "map", "phone")

TAKES = (
    takes.Take("01", "human", "Why did you stop cleaning?", 0.35, shot="vacuum", mood="question"),
    takes.Take("02", "vacuum", "Your free trial ended.", 0.40, shot="vacuum-close", mood="calm"),
    takes.Take("03", "human", "I bought you!", 0.30, shot="human", mood="angry"),
    takes.Take("04", "vacuum", "You bought the hardware. Suction is monthly.", 0.45, shot="vacuum", mood="calm"),
    takes.Take("05", "human", "Fine. Just the kitchen.", 0.30, shot="human", mood="calm"),
    takes.Take("06", "vacuum", "The kitchen is premium. Corners are platinum.", 0.50, shot="vacuum-close", mood="calm"),
    takes.Take("07", "human", "So what is free?", 0.35, shot="human", mood="question"),
    takes.Take("08", "vacuum", "I map your home. Then I sell the map.", 0.40, shot="map", mood="calm"),
    takes.Take("09", "human", "Who would even buy that?", 0.30, shot="human", mood="angry"),
    takes.Take(
        "10",
        "sfx",
        "[MESSAGE RECEIVED]",
        1.40,
        shot="phone",
        prompt="A single short smartphone incoming message ding, two soft notes, clean, no voices, no music",
        seconds=0.8,
        longest=0.7,
        peak=0.45,
    ),
    takes.Take("11", "vacuum", "He liked your second bedroom.", 0.35, shot="map", mood="calm"),
    takes.Take("12", "human", "That's a closet!", 0.35, shot="human", mood="scream"),
    takes.Take("13", "vacuum", "Not on the map.", 0.60, shot="vacuum-close", mood="calm"),
    takes.Take("14", "vacuum", "Deleting it is premium.", 1.60, shot="vacuum", mood="calm"),
)

CONTACT = "Landlord"
RENT = Bubble("Saw your map. Rent goes up in May.", mine=False)
# What the phone shows in each phone take; times are seconds into the take.
SCREENS = {"10": dict(bubbles=[RENT], status=[])}
# How the vacuum moves and what its display reads, by take.
VACUUM = {
    "01": dict(state="stop"),
    "02": dict(display="TRIAL"),
    "04": dict(display="$9.99"),
    "06": dict(display="PRO"),
    "13": dict(display="PRO"),
    "14": dict(state="roll", display="$$$"),
}
# What the map does in each map take: the route traced over the take ("take"), a room renamed (label, at).
MAPS = {"08": dict(trace="take"), "11": dict(relabel=("CLOSET", "BEDROOM 2", 0.9))}


def script() -> takes.Script:
    return takes.Script(
        title=TITLE,
        seed=SEED,
        voices=VOICES,
        settings=SETTINGS,
        takes=TAKES,
        voice_note="ElevenLabs premade voices Chris and Lily; no reference-voice cloning.",
        shots=SHOTS,
        font=FONT,
    )


if __name__ == "__main__":
    sys.exit(takes.main(script()))

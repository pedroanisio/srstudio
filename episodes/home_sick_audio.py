#!/usr/bin/env python3
"""Home Sick — Ink 07: the voices, the effects and the take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 home_sick_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The human is home early, sunglasses on his forehead, and his video doorbell will not let him in: the resident is
home sick today. He got better? Then he is late for work. The doorbell asks the street's group chat who he is, from
his own account: never seen him, nope, and, after a hold, his boss: that's my employee. Face recognized, welcome
home, and the boss texts him: feeling better? Nice tan. Two premade voices: the human (Chris, as in the earlier Ink
episodes) and the doorbell (George), plus the effects. The recording is :mod:`srstudio.takes`: one request per
take, every line heard back by speech-to-text, the voices confirmed by name, no retries. ``LENS`` gives the face
box's tags in each shot through the doorbell's camera, ``DOORBELL`` its verdicts, ``SCREENS`` what the phone shows
(``home_sick.py`` draws them with :mod:`srstudio.ink_doorbell` and :mod:`srstudio.ink_phone`).
"""

from __future__ import annotations

import sys

from srstudio import takes
from srstudio.ink_phone import Bubble
from srstudio.voice import Voice, VoiceSettings

SEED = 1107
TITLE = "Home Sick — Ink 07"
FONT = ("PatrickHand-Regular.ttf", "font-license.txt")
VOICES = {
    "human": Voice(role="human", id="iP95p4xoKVk53GoZ742B", name="Chris"),
    "doorbell": Voice(role="doorbell", id="JBFqnCBsd6RMkjVDRZzb", name="George"),
}
SETTINGS = {
    "human": VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.35, speed=1.06),
    "doorbell": VoiceSettings(stability=0.70, similarity_boost=0.75, style=0.10, speed=1.0),
}
SHOTS = ("lens", "doorbell", "doorbell-close", "phone")
DING = "A single short smartphone incoming message ding, two soft notes, clean, no voices, no music"


def _ding(id: str, text: str, hold: float) -> takes.Take:
    return takes.Take(id, "sfx", text, hold, shot="phone", prompt=DING, seconds=0.8, longest=0.7, peak=0.45)


TAKES = (
    takes.Take("01", "human", "Why won't you open the door?", 0.30, shot="lens", mood="question"),
    takes.Take("02", "doorbell", "Face not recognized.", 0.35, shot="doorbell-close", mood="calm"),
    takes.Take("03", "human", "I live here!", 0.30, shot="lens", mood="angry"),
    takes.Take("04", "doorbell", "The resident is home sick today.", 0.45, shot="doorbell", mood="calm"),
    takes.Take("05", "human", "I got better.", 0.40, shot="lens", mood="calm"),
    takes.Take("06", "doorbell", "Then you're late for work.", 0.40, shot="doorbell-close", mood="calm"),
    takes.Take("07", "human", "Just open the door!", 0.30, shot="lens", mood="angry"),
    takes.Take("08", "doorbell", "I asked the neighbors who you are.", 0.30, shot="phone", mood="calm"),
    _ding("09", "[NEW REPLIES]", 1.40),
    _ding("10", "[NEW REPLY]", 0.45),
    takes.Take("11", "human", "Oh no.", 0.45, shot="lens", mood="scream"),
    takes.Take("12", "doorbell", "Face recognized. Welcome home.", 0.45, shot="doorbell", mood="calm"),
    _ding("13", "[MESSAGE RECEIVED]", 1.60),
)

NUMBER = "14"
CLOCK = "MON 2:14 PM"
NEIGHBORS = "Elm St Neighbors"
POST = Bubble("Who is this man?", at=0.5)  # posted from his own account by his doorbell
REPLIES = (Bubble("Ana: Never seen him.", mine=False), Bubble("Raj: Nope.", mine=False, at=0.45))
BOSS = Bubble("Greg: That's my employee.", mine=False, at=0.1)
# What the phone shows in each phone take; times are seconds into the take.
SCREENS = {
    "08": dict(contact=NEIGHBORS, bubbles=[POST]),
    "09": dict(contact=NEIGHBORS, bubbles=[Bubble(POST.text), *REPLIES]),
    "10": dict(contact=NEIGHBORS, bubbles=[Bubble(POST.text), *(Bubble(r.text, False) for r in REPLIES), BOSS]),
    "13": dict(contact="Greg (Boss)", bubbles=[Bubble("Feeling better?", False), Bubble("Nice tan.", False, 1.1)]),
}
# The face box's tags in each shot through the doorbell's camera, (second, tag).
LENS = {
    "01": ((0.0, "UNKNOWN"),),
    "03": ((0.0, "UNKNOWN"),),
    "05": ((0.0, "UNKNOWN"), (0.7, "NOT SICK")),
    "07": ((0.0, "INTRUDER"),),
    "11": ((0.0, "INTRUDER"), (0.25, "EMPLOYEE")),
}
# The doorbell's verdict on its button, by take.
DOORBELL = {"02": dict(mark=("deny", 0.2)), "12": dict(mark=("allow", 0.35))}


def script() -> takes.Script:
    return takes.Script(
        title=TITLE,
        seed=SEED,
        voices=VOICES,
        settings=SETTINGS,
        takes=TAKES,
        voice_note="ElevenLabs premade voices Chris and George; no reference-voice cloning.",
        shots=SHOTS,
        font=FONT,
    )


if __name__ == "__main__":
    sys.exit(takes.main(script()))

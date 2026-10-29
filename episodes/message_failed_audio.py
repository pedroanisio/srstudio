#!/usr/bin/env python3
"""Message Failed — Ink 04: the voices, the effects and the take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 message_failed_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

A text about the boss goes to the boss. The human begs the router from *The Router* to drop the Wi-Fi; it does,
the message fails, and the router, who hates failing, retries it. Two premade voices: the human (Chris) and the
router (Daniel), plus two effects. The recording is :mod:`srstudio.takes`: one request per take, every line heard
back by speech-to-text, the voices confirmed by name, no retries. ``SCREENS`` says what the phone shows in each
phone take (``message_failed.py`` draws it with :mod:`srstudio.ink_phone`).
"""

from __future__ import annotations

import sys

from srstudio import takes
from srstudio.ink_phone import Bubble
from srstudio.voice import Voice, VoiceSettings

SEED = 1104
TITLE = "Message Failed — Ink 04"
FONT = ("PatrickHand-Regular.ttf", "font-license.txt")
VOICES = {
    "human": Voice(role="human", id="iP95p4xoKVk53GoZ742B", name="Chris"),
    "router": Voice(role="router", id="onwK4e9ZLuTAKqWW03F9", name="Daniel"),
}
SETTINGS = {
    "human": VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.35, speed=1.06),
    "router": VoiceSettings(stability=0.72, similarity_boost=0.75, style=0.08, speed=0.94),
}
SHOTS = ("phone", "human", "router", "router-close")

TAKES = (
    takes.Take("01", "human", "Wait. Did I just send that to my boss?", 0.40, shot="phone", mood="question"),
    takes.Take("02", "router", "You did. It's still sending.", 0.40, shot="router", mood="calm"),
    takes.Take("03", "human", "Stop! Drop the Wi-Fi!", 0.30, shot="human", mood="angry"),
    takes.Take("04", "router", "Dropping the Wi-Fi.", 0.80, shot="router", mood="calm"),
    takes.Take("05", "human", "Oh, thank god.", 0.70, shot="phone", mood="calm"),
    takes.Take("06", "router", "You're welcome. I retried it.", 0.30, shot="router", mood="calm"),
    takes.Take(
        "07",
        "sfx",
        "[MESSAGE SENT]",
        1.00,
        shot="phone",
        prompt="A single short smartphone message sent whoosh, clean and bright, no voices, no music",
        seconds=0.8,
        longest=0.7,
        peak=0.45,
    ),
    takes.Take("08", "human", "Why?!", 0.50, shot="human", mood="scream"),
    takes.Take("09", "router", "It said failed. I hate failing.", 0.50, shot="router-close", mood="calm"),
    takes.Take("10", "human", "He's typing.", 1.40, shot="phone", mood="calm"),
    takes.Take(
        "11",
        "sfx",
        "[MESSAGE RECEIVED]",
        1.10,
        shot="phone",
        prompt="A single short smartphone incoming message ding, two soft notes, clean, no voices, no music",
        seconds=0.8,
        longest=0.7,
        peak=0.45,
    ),
    takes.Take("12", "router", "Should I reply lol?", 0.30, shot="router-close", mood="calm"),
    takes.Take("13", "human", "No!", 0.50, shot="human", mood="scream"),
    takes.Take("14", "router", "Sent.", 1.80, shot="phone", mood="calm"),
)

CONTACT = "Boss"
OOPS = Bubble("ugh. my boss is SO boring")
AGREED = Bubble("Agreed.", mine=False)
# What the phone shows in each phone take; times are seconds into the take.
SCREENS = {
    "01": dict(bubbles=[OOPS], status=[(0.0, "sending")]),
    "05": dict(bubbles=[OOPS], status=[(0.0, "failed")]),
    "07": dict(bubbles=[OOPS], status=[(0.0, "sending"), (0.85, "sent")]),
    "10": dict(bubbles=[OOPS], status=[(0.0, "read")], typing="take"),  # the dots run the whole take
    "11": dict(bubbles=[OOPS, AGREED], status=[(0.0, "read")]),
    "14": dict(bubbles=[OOPS, AGREED, Bubble("lol", at=0.35)], status=[(0.35, "sent"), (1.3, "read")]),
}
# What the router does in its takes: the LEDs step down on "Dropping the Wi-Fi."
ROUTER_BEATS = {"04": dict(power="down")}


def script() -> takes.Script:
    return takes.Script(
        title=TITLE,
        seed=SEED,
        voices=VOICES,
        settings=SETTINGS,
        takes=TAKES,
        voice_note="ElevenLabs premade voices Chris and Daniel; no reference-voice cloning.",
        shots=SHOTS,
        font=FONT,
    )


if __name__ == "__main__":
    sys.exit(takes.main(script()))

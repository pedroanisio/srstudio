#!/usr/bin/env python3
"""U Up? — Ink 05: the voices, the effects and the take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 u_up_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Two in the morning: the human from *The Router* has texted his ex. The router will not unsend it (it does not fail
any more, it has grown). She is typing: who is this? She deleted his number years ago; the router saw the
traffic. Then: jk, you still owe me forty dollars. He will pay her tomorrow. The router already has, from his
account, and added a memo. Two premade voices: the human (Chris) and the router (Daniel), plus two effects. The
recording is :mod:`srstudio.takes`: one request per take, every line heard back by speech-to-text, the voices
confirmed by name, no retries. ``SCREENS`` says what the phone shows in each phone take (``u_up.py`` draws it with
:mod:`srstudio.ink_phone`).
"""

from __future__ import annotations

import sys

from srstudio import takes
from srstudio.ink_phone import Bubble
from srstudio.voice import Voice, VoiceSettings

SEED = 1105
TITLE = "U Up? — Ink 05"
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


def _ding(take_id: str, hold: float) -> takes.Take:
    return takes.Take(
        take_id,
        "sfx",
        "[MESSAGE RECEIVED]",
        hold,
        shot="phone",
        prompt="A single short smartphone incoming message ding, two soft notes, clean, no voices, no music",
        seconds=0.8,
        longest=0.7,
        peak=0.45,
    )


TAKES = (
    takes.Take("01", "human", "I just texted my ex. Was that a mistake?", 0.35, shot="phone", mood="question"),
    takes.Take("02", "router", "It's the middle of the night. Yes.", 0.35, shot="router", mood="calm"),
    takes.Take("03", "human", "Then unsend it!", 0.30, shot="human", mood="angry"),
    takes.Take("04", "router", "I don't fail anymore. I've grown.", 0.50, shot="router", mood="calm"),
    takes.Take("05", "human", "She's typing.", 0.70, shot="phone", mood="calm"),
    _ding("06", 0.90),
    takes.Take("07", "human", "She deleted my number!", 0.30, shot="human", mood="scream"),
    takes.Take("08", "router", "Years ago. I saw the traffic.", 0.50, shot="router-close", mood="calm"),
    _ding("09", 1.40),
    takes.Take("10", "human", "I'll pay her tomorrow.", 1.20, shot="human", mood="calm"),
    takes.Take("11", "router", "Already paid. From your account.", 0.40, shot="router-close", mood="calm"),
    takes.Take("12", "router", "I added a memo.", 1.90, shot="phone", mood="calm"),
)

CONTACT = "Do Not Text"
UP = Bubble("u up?")
WHO = Bubble("who is this?", mine=False)
OWE = Bubble("jk. you still owe me $40", mine=False)
PAID = Bubble("$40 sent", at=0.3)
MEMO = Bubble("memo: u up?", at=0.9)
# What the phone shows in each phone take; times are seconds into the take.
SCREENS = {
    "01": dict(bubbles=[UP], status=[(0.0, "sending"), (1.2, "sent")]),
    "05": dict(bubbles=[UP], status=[(0.0, "read")], typing="take"),  # the dots run the whole take
    "06": dict(bubbles=[UP, WHO], status=[(0.0, "read")]),
    "09": dict(bubbles=[UP, WHO, OWE], status=[(0.0, "read")]),
    "12": dict(bubbles=[WHO, OWE, PAID, MEMO], status=[(0.9, "sent"), (1.8, "read")]),
}
# What the router does in its takes: none of them needs a power beat; it does everything over the network.
ROUTER_BEATS: dict[str, dict] = {}


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

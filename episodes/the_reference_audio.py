#!/usr/bin/env python3
"""The Reference: generated dialogue, resolved by the engine, and the timeline.

    srstudio record the-reference PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits
(:func:`schedule`) and its cuts (:func:`extra`). Rosa gives Milo a reference over a speakerphone, in a blazer over a
bathrobe, while he kneels by the desk with cue cards. Lily is Rosa, Liam is Milo and Eric is the manager on the line.
There is no music, and the foley is synthesized in the build. It moves from its first frame (arm B of the
``sp-hook_motion`` test): the cards shake and the frame eases back.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, beats, main
from srstudio.song import Singer

SEED = 31281
VOICES = {
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.15)),
    "rosa": Singer("pFZP5JQG7iQjIQuC4Bku", "Lily", dict(stability=0.50, similarity_boost=0.75, style=0.25)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("manager", "You managed Milo for six years?", "You managed Milo\nfor six years?", 1.02),
    Spoken("rosa", "Seven. Felt longer.", "Seven. Felt longer.", 0.95),
    Spoken("manager", "Is he reliable?", "Is he reliable?", 1.00),
    Spoken("rosa", "Very. Apart from the $40.", "Very.\nApart from the forty dollars.", 0.98),
    Spoken("milo", "What $40?", "What forty dollars?", 1.05),
    Spoken("manager", "Would you hire him again?", "Would you hire him again?", 1.00),
    Spoken("rosa", "In a heartbeat.", "In a heartbeat.", 0.98),
    Spoken("manager", "You sound like a wonderful leader. We have an opening above him.",
           "You sound like a\nwonderful leader.\nWe have an opening\nabove him.", 1.00),
    Spoken("rosa", "I'd need a reference.", "I'd need a reference.", 0.95),
    Spoken("milo", "$40.", "Forty dollars.", 0.92, seed=SEED + 20),
]  # fmt: skip
START = 0.30  # the first word: the cards are already shaking
GAPS = (0.20, 0.25, 0.15, 0.10, 0.20, 3.00, 0.25, 2.10, 0.95)  # after each line; the two long ones are the reel
ENDING = 0.45  # stop on the hand
INTERVIEW = Interview(
    slug="the-reference",
    title="The Reference",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Lily, Liam and Eric; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: a quick call, then the two silences it is about."""
    return beats(speech, START, GAPS)


def extra(t: Timing) -> dict:
    """The beats the picture keys on. One room, no cuts: the frame moves instead."""
    p = t.phrases
    sits = p[5]["end"] + 0.15
    wallet = sits + 1.10
    slides = wallet + 0.75
    lowers = p[7]["end"] + 0.90
    return {
        "sits": sits,
        "wallet": wallet,
        "slides": slides,
        "paid": slides + 0.60,
        "lowers": lowers,
        "offers": p[8]["end"] + 0.15,
        "camera_cuts": [{"time": 0, "angle": "study"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

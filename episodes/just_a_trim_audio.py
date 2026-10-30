#!/usr/bin/env python3
"""Just a Trim: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record just-a-trim PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, its effects, and its cuts
(:func:`extra`). Rosa asks for a trim and sits through a hedge trimmer and a lawnmower. Too polite to object, she loves
the result, pays and tips. Its first second is held still (arm A of the ``sp-hook_motion`` test). Rosa is Lily, as in
*Neighbor Names*; the barber is Jessica.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 26171
VOICES = {
    "rosa": Singer("pFZP5JQG7iQjIQuC4Bku", "Lily", dict(stability=0.50, similarity_boost=0.75, style=0.25)),
    "barista": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("rosa", "Just a trim, please.", "Just a trim, please.", 1.00),
    Spoken("barista", "Sure.", "Sure.", 1.00),
    Spoken("barista", "Bit off the sides?", "Bit off the sides?", 1.05),
    Spoken("rosa", "Sure.", "...Sure.", 0.90),
    Spoken("barista", "How's that?", "How's that?", 1.00),
    Spoken("rosa", "Love it.", "Love it.", 1.05),
]
EFFECTS = [
    Sound(
        "cape",
        "A heavy cloth cape flung out and snapping open in the air, one whoosh, no voices, no music",
        0.8,
        0.6,
        0.30,
        seed=SEED + 1,
    ),
    Sound(
        "uncape",
        "A heavy cloth cape flung out and snapping open in the air, one whoosh, no voices, no music",
        0.8,
        0.6,
        0.30,
        seed=SEED + 1,
    ),
    Sound(
        "trimmer",
        "A petrol hedge trimmer revving and cutting, loud, close, no voices, no music",
        2.4,
        2.0,
        0.34,
        seed=SEED + 2,
    ),
    Sound(
        "mower",
        "A petrol lawnmower pull started and running, loud, close, no voices, no music",
        3.4,
        3.0,
        0.34,
        seed=SEED + 3,
    ),
    Sound(
        "paid",
        "A card payment terminal's short approval beep, one clean electronic tone, no voices, no music",
        0.6,
        0.45,
        0.28,
        seed=SEED + 4,
    ),
    Sound(
        "keys",
        "Three quick beeps of buttons pressed on a card terminal keypad, close, no voices, no music",
        0.8,
        0.6,
        0.24,
        seed=SEED + 5,
    ),
]
STILL = 1.05  # the held first second: nothing moves
HOLD = 2.0  # the mirror uncovered, before anyone speaks
READER = 1.80  # the card reader to the end
INTERVIEW = Interview(
    slug="just-a-trim",
    title="Just a Trim",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Lily and Jessica; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.30,
    reaction_hold=READER,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the machines run under the cape and under the barber."""
    starts: list[float] = []
    fx: dict[str, float] = {}

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, STILL + 0.05)
    end = say(1, end + 0.20)
    fx["cape"] = end + 0.25
    fx["trimmer"] = fx["cape"] + 0.35
    fx["mower"] = fx["trimmer"] + 1.40
    end = say(2, fx["mower"] + 0.95)
    say(3, end + 0.30)
    fx["uncape"] = fx["mower"] + effect["mower"] + 0.25  # the machine stops dead, and only then does the cloth drop
    end = say(4, fx["uncape"] + HOLD)
    end = say(5, end + 1.10)
    fx["keys"] = end + 0.20
    fx["paid"] = fx["keys"] + 0.70
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on and the cuts: the mirror, then the till."""
    p, fx = t.phrases, t.effects
    block = fx["mower"] + 0.70
    uncover = fx["uncape"]
    return {
        "cape": fx["cape"],
        "mower": fx["mower"],
        "block": block,
        "uncover": uncover,
        "wobble": [p[4]["end"] + 0.10, p[5]["start"] - 0.10],
        "keys": fx["keys"],
        "paid": fx["paid"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [{"time": 0, "angle": "mirror"}, {"time": p[5]["end"] + 0.10, "angle": "till"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

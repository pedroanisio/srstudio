#!/usr/bin/env python3
"""Episode 12 — Tip Screen: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 tip_screen_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the taps sit between the lines
(:func:`schedule`) and its camera cuts (:func:`extra`).
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 12041
VOICES = {
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "ava": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.3)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("milo", "Can I just get a black coffee?", "Can I just get\na black coffee?", 1.00),
    Spoken("ava", "Of course!", "Of course!", 1.00),
    Spoken("milo", "You poured it from a pot.", "You poured it\nfrom a pot.", 1.00),
    Spoken("ava", "With intention.", "With intention.", 0.95),
    Spoken(
        "milo",
        "Great. And how would you like to tip me for ordering?",
        "Great. And how would you like\nto tip me for ordering?",
        1.00,
    ),
    Spoken("ava", "Twenty-five?", "Twenty-five?", 0.95),
    Spoken("milo", "Thirty.", "Thirty.", 1.00),
    Spoken("ava", "Thirty.", "Thirty.", 1.00),
    Spoken("milo", "Thirty.", "Thirty.", 0.85),
    Spoken("ava", "Thirty.", "Thirty.", 0.85),
]
TAP = "A single fingertip tap on a tablet touchscreen with a soft electronic confirm blip, close, no voices, no music"
EFFECTS = [
    Sound(
        "tablet-swivel",
        "A payment tablet on a counter stand swiveled around to face a customer, a smooth plastic click, close, "
        "no voices, no music",
        1.0,
        0.6,
        0.32,
        seed=SEED,
    ),
    Sound(
        "tablet-set",
        "A second tablet set down firmly on a wooden café counter, a solid knock, close, no voices, no music",
        1.0,
        0.5,
        0.36,
        seed=SEED + 1,
    ),
    Sound("tap-1", TAP, 0.6, 0.35, 0.3, seed=SEED + 2),
    Sound("tap-2", TAP, 0.6, 0.35, 0.3, seed=SEED + 3),
    Sound("tap-3", TAP, 0.6, 0.35, 0.3, seed=SEED + 4),
    Sound("tap-4", TAP, 0.6, 0.35, 0.3, seed=SEED + 5),
    Sound("tap-5", TAP, 0.6, 0.35, 0.3, seed=SEED + 6),
]
INTERVIEW = Interview(
    slug="tip-screen",
    title="Tip Screen — Comedy Cut 12",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Liam and Jessica; no reference-voice cloning.",
    room_tone_seed=12042,
    reaction_after=0.30,
    reaction_hold=1.00,
    end_card=2.60,
)
LEAD = 0.35
STARE = 1.30  # Ava looks at Milo's tablet before she answers it
LATER = 1.40  # the "three hours later" slate between the fourth tap and the last two lines
TAPS = {  # tap: (whose tablet, option index)
    "tap-1": ("milo", 1),
    "tap-2": ("ava", 2),
    "tap-3": ("milo", 2),
    "tap-4": ("ava", 2),
    "tap-5": ("milo", 2),
}


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: each tap lands right after the number it answers."""
    starts: list[float] = []
    fx: dict[str, float] = {}
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    end = say(0)
    cursor = end + 0.20
    end = say(1)
    fx["tablet-swivel"] = end + 0.05
    cursor = fx["tablet-swivel"] + effect["tablet-swivel"] + 0.25
    end = say(2)
    cursor = end + 0.30
    end = say(3)
    cursor = end + 0.55
    fx["tablet-set"] = cursor
    cursor += effect["tablet-set"] + 0.05
    end = say(4)
    cursor = end + STARE
    end = say(5)
    fx["tap-1"] = end + 0.05
    cursor = fx["tap-1"] + effect["tap-1"] + 0.15
    end = say(6)
    fx["tap-2"] = end + 0.05
    cursor = fx["tap-2"] + effect["tap-2"] + 0.15
    end = say(7)
    fx["tap-3"] = end + 0.05
    cursor = fx["tap-3"] + effect["tap-3"] + LATER
    end = say(8)
    fx["tap-4"] = end + 0.05
    cursor = fx["tap-4"] + effect["tap-4"] + 0.15
    end = say(9)
    fx["tap-5"] = end + 0.05
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The swivel, the second tablet, the taps, the slate, and the camera cuts."""
    p, fx = t.phrases, t.effects
    later = fx["tap-3"] + 0.45
    return {
        "swivel_start": fx["tablet-swivel"],
        "set_start": fx["tablet-set"],
        "taps": {k: fx[k] for k in TAPS},
        "later_start": later,
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},
            {"time": p[1]["start"] - 0.1, "angle": "barista"},
            {"time": fx["tablet-swivel"], "angle": "ava-tablet"},
            {"time": p[2]["start"] - 0.1, "angle": "customer"},
            {"time": p[3]["start"] - 0.1, "angle": "barista"},
            {"time": fx["tablet-set"] - 0.1, "angle": "wide"},
            {"time": p[4]["end"] + 0.05, "angle": "milo-tablet"},
            {"time": p[5]["start"] - 0.1, "angle": "barista"},
            {"time": p[6]["start"] - 0.1, "angle": "customer"},
            {"time": p[7]["start"] - 0.1, "angle": "barista"},
            {"time": later, "angle": "later"},
            {"time": t.reaction, "angle": "tablets"},
            {"time": t.ending, "angle": "end"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

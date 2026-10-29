#!/usr/bin/env python3
"""Episode 14 — Culture Fit: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 culture_fit_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the gags sit between the lines
(:func:`schedule`) and its camera cuts (:func:`extra`).
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 14031
VOICES = {  # the same voices as in episode 05 (Milo) and episode 09 (the boss)
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.12)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}

SCRIPT = [  # role, text, caption, speed
    Spoken("milo", "Two hundred applications. Not one reply.", "Two hundred applications.\nNot one reply.", 0.95),
    Spoken(
        "manager", "So. Where do you see yourself in five years?", "So. Where do you see\nyourself in five years?", 0.95
    ),
    Spoken("manager", "Love that. Can you start Monday?", "Love that.\nCan you start Monday?", 1.00),
    Spoken("milo", "Sorry, are you hiring?", "Sorry, are you hiring?", 1.00),
    Spoken("manager", "Not anymore.", "Not anymore.", 0.95),
    Spoken("milo", "I have a master's degree.", "I have a master's degree.", 1.00),
    Spoken("manager", "He works for crumbs.", "He works for crumbs.", 0.92),
    Spoken("milo", "I can do crumbs.", "I can do crumbs.", 0.90),
    Spoken("manager", "We'll keep you on file.", "We'll keep you on file.", 0.95),
]
LEAD = 0.55  # the hook card alone, before the first line
STARE = 1.30  # the boss looks Milo over, then tosses the crumbs: the hold before the punchline
THINK = 1.20  # Milo weighs it up, before the counter-offer
COO = "A single pigeon coo, a soft throaty two-note coo, close, outdoors, no voices, no music"
PING = "A single short smartphone notification ping, bright and clean, no voices, no music"
# Generated effects: requested seconds, longest kept after trimming, peak level in the mix; one seed each.
EFFECTS = [
    Sound(
        "flutter",
        "A pigeon landing on a park path, a short flutter of wings, close, outdoors, no voices, no music",
        1.0,
        0.7,
        0.34,
        seed=SEED,
    ),
    Sound("coo-1", COO, 1.0, 0.8, 0.36, seed=SEED + 1),
    Sound("coo-2", COO, 1.0, 0.8, 0.36, seed=SEED + 2),
    Sound("offer-ping", PING, 0.6, 0.4, 0.30, seed=SEED + 3),
    Sound("coo-3", COO, 1.0, 0.8, 0.36, seed=SEED + 4),
    Sound("connect-ping", PING, 0.6, 0.4, 0.30, seed=SEED + 5),
]
INTERVIEW = Interview(
    slug="culture-fit",
    title="Culture Fit — Comedy Cut 14",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Liam and Eric; no reference-voice cloning.",
    room_tone_seed=14032,
    reaction_after=0.55,
    reaction_hold=1.90,
    end_card=2.60,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the gags sit in the gaps between lines."""
    starts: list[float] = []
    fx: dict[str, float] = {}
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    end = say(0)
    fx["flutter"] = end + 0.20
    cursor = fx["flutter"] + effect["flutter"] + 0.30
    end = say(1)
    fx["coo-1"] = end + 0.35
    cursor = fx["coo-1"] + effect["coo-1"] + 0.15
    end = say(2)
    fx["coo-2"] = end + 0.30
    fx["offer-ping"] = fx["coo-2"] + effect["coo-2"] + 0.10
    cursor = fx["offer-ping"] + effect["offer-ping"] + 0.45
    end = say(3)
    cursor = end + 0.25
    end = say(4)
    cursor = end + 0.35
    end = say(5)
    cursor = end + STARE
    end = say(6)
    fx["coo-3"] = end + 0.15
    cursor = fx["coo-3"] + effect["coo-3"] + THINK
    end = say(7)
    cursor = end + 0.55
    end = say(8)
    fx["connect-ping"] = end + 0.50
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The toss, the notifications, the reaction and end card, and the camera cuts."""
    p, fx = t.phrases, t.effects
    return {
        "toss_start": p[6]["start"] - 0.55,
        "offer_start": fx["offer-ping"],
        "connect_start": fx["connect-ping"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},
            {"time": p[1]["start"] - 0.10, "angle": "boss"},
            {"time": fx["coo-1"] - 0.08, "angle": "pigeon"},
            {"time": p[2]["start"] - 0.05, "angle": "boss"},
            {"time": fx["coo-2"] - 0.08, "angle": "pigeon"},
            {"time": fx["offer-ping"] - 0.10, "angle": "wide"},
            {"time": p[3]["start"] - 0.05, "angle": "milo"},
            {"time": p[4]["start"] - 0.05, "angle": "boss"},
            {"time": p[5]["start"] - 0.05, "angle": "milo"},
            {"time": p[5]["end"] + 0.15, "angle": "boss"},
            {"time": fx["coo-3"] - 0.05, "angle": "pigeon"},
            {"time": fx["coo-3"] + 0.75, "angle": "milo"},
            {"time": p[8]["start"] - 0.05, "angle": "boss"},
            {"time": fx["connect-ping"] - 0.10, "angle": "wide"},
            {"time": t.ending, "angle": "end"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

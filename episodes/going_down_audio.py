#!/usr/bin/env python3
"""Episode 20 — Going Down: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 going_down_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the gags sit between the lines
(:func:`schedule`) and its camera cuts (:func:`extra`). The finale of the office series: the boss (Eric) lays off
the employee from *Market Rate* and *Elevator Pitch* (Will) on the way down, in euphemisms. At floor 4 Kevin, the
pigeon hired in *Culture Fit*, walks in with a pink slip and drops it at the boss's feet. The lobby, then the
bench from *Culture Fit*: two men tossing crumbs. Networking.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 20031
VOICES = {  # the same voices as in the interview series, Market Rate and Elevator Pitch
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.24)),
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.12)),
}

SCRIPT = [  # role, text, caption, speed
    Spoken("candidate", "Am I being fired?", "Am I being fired?", 1.00),
    Spoken("manager", "No. Your role is being sunset.", "No. Your role\nis being sunset.", 1.00),
    Spoken("candidate", "So I'm fired.", "So I'm fired.", 1.00),
    Spoken(
        "manager",
        "You're going fully remote. From your couch. Forever.",
        "You're going fully remote.\nFrom your couch.\nForever.",
        1.05,
    ),
    Spoken("candidate", "Kevin? He's fully remote!", "Kevin?\nHe's fully remote!", 1.00),
    Spoken(
        "manager",
        "He flew in for this. He's Head of People now.",
        "He flew in for this.\nHe's Head of People now.",
        1.00,
    ),
    Spoken("manager", "Kevin, is my role being sunset?", "Kevin…\nis my role being sunset?", 0.95),
    Spoken("candidate", "What are we doing?", "What are we doing?", 1.00),
    Spoken("manager", "Networking.", "Networking.", 0.95),
]
ASK_HOLD = 1.3  # "Kevin, is my role being sunset?" ... the hold before the coo
DING = "A single elevator arrival ding, one clean bell chime, no voices, no music"
COO = "A single pigeon coo, soft and throaty, close up, no other sounds"
# Generated effects: requested seconds, longest kept after trimming, peak level in the mix; one seed each.
EFFECTS = [
    Sound("ding-4", DING, 1.0, 0.9, 0.32, seed=SEED),
    Sound("coo-1", COO, 1.0, 0.8, 0.34, seed=SEED + 1),
    Sound(
        "drop",
        "A thick paper envelope dropped flat onto a hard elevator floor, one soft papery slap, close, no voices, "
        "no music",
        1.0,
        0.6,
        0.36,
        seed=SEED + 2,
    ),
    Sound("coo-2", COO, 1.2, 1.0, 0.40, seed=SEED + 3),
    Sound("ding-1", DING, 1.0, 0.9, 0.32, seed=SEED + 4),
    Sound(
        "flutter",
        "A few pigeons landing on a park path, a short burst of wing flaps, outdoors, no voices, no music",
        1.5,
        1.2,
        0.30,
        seed=SEED + 5,
    ),
    Sound("coo-3", COO, 1.0, 0.8, 0.34, seed=SEED + 6),
]
INTERVIEW = Interview(
    slug="going-down",
    title="Going Down — Comedy Cut 20",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Will and Eric; no reference-voice cloning.",
    room_tone_seed=20032,
    reaction_after=0.30,
    reaction_hold=2.10,
    end_card=2.60,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the gags sit in the gaps between lines."""
    starts: list[float] = []
    fx: dict[str, float] = {}
    cursor = 0.25

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    for i in range(3):
        cursor = say(i) + 0.30
    end = say(3)
    fx["ding-4"] = end + 0.15
    fx["coo-1"] = fx["ding-4"] + effect["ding-4"] + 0.45  # the doors open, Kevin walks in with the slip
    cursor = fx["coo-1"] + effect["coo-1"] + 0.15
    cursor = say(4) + 0.30
    end = say(5)
    fx["drop"] = end + 0.35  # the slip lands at the boss's feet
    cursor = fx["drop"] + effect["drop"] + 0.70  # the name on it reads
    end = say(6)
    fx["coo-2"] = end + ASK_HOLD
    fx["ding-1"] = fx["coo-2"] + effect["coo-2"] + 0.35  # the lobby
    fx["flutter"] = fx["ding-1"] + effect["ding-1"] + 0.30  # the park: the pigeons come for the crumbs
    cursor = fx["flutter"] + effect["flutter"] + 0.20
    cursor = say(7) + 0.30
    end = say(8)
    fx["coo-3"] = end + 0.20  # a pigeon accepts
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The stops and the doors, the drop, the change of room at the lobby, the reaction and end card, the cuts."""
    p, fx = t.phrases, t.effects
    park = fx["flutter"] - 0.15  # the lobby doors open on the ding, then the bench as the pigeons land
    return {
        "ding4_start": fx["ding-4"],
        "coo1_start": fx["coo-1"],
        "drop_start": fx["drop"],
        "coo2_start": fx["coo-2"],
        "ding1_start": fx["ding-1"],
        "park_start": park,
        "flutter_start": fx["flutter"],
        "coo3_start": fx["coo-3"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},
            {"time": p[1]["start"] - 0.05, "angle": "manager"},
            {"time": p[2]["start"] - 0.05, "angle": "candidate"},
            {"time": p[3]["start"] - 0.05, "angle": "manager"},
            {"time": fx["ding-4"] - 0.05, "angle": "wide"},
            {"time": p[4]["start"] - 0.05, "angle": "candidate"},
            {"time": p[5]["start"] - 0.05, "angle": "manager"},
            {"time": fx["drop"] + 0.10, "angle": "slip"},
            {"time": p[6]["start"] - 0.05, "angle": "manager"},
            {"time": p[6]["end"] + 0.40, "angle": "pigeon"},
            {"time": fx["ding-1"] - 0.05, "angle": "display"},
            {"time": park, "angle": "park"},
            {"time": p[8]["start"] - 0.05, "angle": "park-manager"},
            {"time": t.reaction, "angle": "park-pigeon"},
            {"time": t.ending, "angle": "end"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

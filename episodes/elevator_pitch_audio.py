#!/usr/bin/env python3
"""Episode 18 — Elevator Pitch: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 elevator_pitch_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the gags sit between the lines
(:func:`schedule`) and its camera cuts (:func:`extra`). The employee from *Market Rate* (Will) rides the elevator
with the boss (Eric) and pitches working from home before the boss's floor. At floor 4 the pigeon the boss hired in
*Culture Fit* walks in: Kevin, fully remote.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 18031
VOICES = {  # the same voices as in the interview series and Market Rate
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.24)),
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.12)),
}

SCRIPT = [  # role, text, caption, speed
    Spoken(
        "manager",
        "Working from home? Elevator pitch. You've got till my floor.",
        "Working from home?\nElevator pitch.\nYou've got till my floor.",
        1.05,
    ),
    Spoken(
        "candidate",
        "I'm more productive at home. No commute. No meetings.",
        "I'm more productive at home.\nNo commute. No meetings.",
        1.05,
    ),
    Spoken("manager", "Morning, Kevin.", "Morning, Kevin.", 1.00),
    Spoken("candidate", "Is that the pigeon you hired?", "Is that the pigeon you hired?", 1.00),
    Spoken(
        "manager",
        "Kevin's fully remote. He flies in on Tuesdays.",
        "Kevin's fully remote.\nHe flies in on Tuesdays.",
        1.00,
    ),  # fmt: skip
    Spoken("candidate", "So why does he get remote?", "So why does he get remote?", 1.00),
    Spoken("manager", "He negotiated. You took a title.", "He negotiated.\nYou took a title.", 1.00),
    Spoken("manager", "My floor. Kevin, your call.", "My floor.\nKevin, your call.", 1.00),
    Spoken("manager", "Kevin says five days a week.", "Kevin says five days a week.", 0.95),
]
CALL_HOLD = 1.3  # "Kevin, your call." ... the hold before the coo
DING = "A single elevator arrival ding, one clean bell chime, no voices, no music"
COO = "A single pigeon coo, soft and throaty, close up, no other sounds"
# Generated effects: requested seconds, longest kept after trimming, peak level in the mix; one seed each.
EFFECTS = [
    Sound("ding-4", DING, 1.0, 0.9, 0.32, seed=SEED),
    Sound("coo-1", COO, 1.0, 0.8, 0.34, seed=SEED + 1),
    Sound("ding-9", DING, 1.0, 0.9, 0.32, seed=SEED + 2),
    Sound("coo-2", COO, 1.2, 1.0, 0.40, seed=SEED + 3),
]
INTERVIEW = Interview(
    slug="elevator-pitch",
    title="Elevator Pitch — Comedy Cut 18",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Will and Eric; no reference-voice cloning.",
    room_tone_seed=18032,
    reaction_after=0.55,
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

    cursor = say(0) + 0.30
    end = say(1)
    fx["ding-4"] = end + 0.15
    fx["coo-1"] = fx["ding-4"] + effect["ding-4"] + 0.45  # the doors open, the pigeon walks in
    cursor = fx["coo-1"] + effect["coo-1"] + 0.15
    for i, gap in ((2, 0.30), (3, 0.30), (4, 0.30), (5, 0.30)):
        cursor = say(i) + gap
    end = say(6)
    fx["ding-9"] = end + 0.35
    cursor = fx["ding-9"] + effect["ding-9"] + 0.10
    end = say(7)
    fx["coo-2"] = end + CALL_HOLD
    cursor = fx["coo-2"] + effect["coo-2"] + 0.25
    say(8)
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The stops and the doors, the reaction and end card, and the camera cuts."""
    p, fx = t.phrases, t.effects
    return {
        "ding4_start": fx["ding-4"],
        "coo1_start": fx["coo-1"],
        "ding9_start": fx["ding-9"],
        "coo2_start": fx["coo-2"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},
            {"time": p[1]["start"] - 0.05, "angle": "candidate"},
            {"time": fx["ding-4"] - 0.05, "angle": "wide"},
            {"time": p[2]["start"] - 0.05, "angle": "manager"},
            {"time": p[3]["start"] - 0.05, "angle": "candidate"},
            {"time": p[4]["start"] - 0.05, "angle": "manager"},
            {"time": p[5]["start"] - 0.05, "angle": "candidate"},
            {"time": p[6]["start"] - 0.05, "angle": "manager"},
            {"time": fx["ding-9"] - 0.05, "angle": "display"},
            {"time": p[7]["start"] - 0.05, "angle": "manager"},
            {"time": p[7]["end"] + 0.35, "angle": "pigeon"},
            {"time": p[8]["start"] - 0.05, "angle": "manager"},
            {"time": t.reaction, "angle": "candidate"},
            {"time": t.ending, "angle": "end"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

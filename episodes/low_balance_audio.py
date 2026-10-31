#!/usr/bin/env python3
"""Low Balance: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record low-balance PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, its effects, the walk the chain runs
out on (:func:`schedule`) and its cuts (:func:`extra`). A customer asks about a fee and collects two more. Nothing in
the bank is free but the pen, and the pen is on a chain. The first second is held still (arm A of the ``sp-hook_motion``
test); :func:`schedule` refuses a shorter one. The customer is Liam and the teller George, both as published.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3103
VOICES = {
    "candidate": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "manager": Singer("JBFqnCBsd6RMkjVDRZzb", "George", dict(stability=0.60, similarity_boost=0.75, style=0.10)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("candidate", "Why is there a $12 fee?", "Why is there a $12 fee?", 1.00),
    Spoken("manager", "Your balance is low.", "Your balance is low.", 0.95),
    Spoken("candidate", "You're charging me for having no money.", "You're charging me\nfor having no money.", 1.00),
    Spoken("manager", "For having too little.", "For having too little.", 0.95),
    Spoken("candidate", "And now I've got less.", "And now I've got less.", 1.00),
    Spoken("manager", "Yes. So that's another twelve.", "Yes. So that's\nanother twelve.", 0.95),
    Spoken("candidate", "Fine. Close the account.", "Fine. Close the account.", 1.00),
    Spoken(
        "manager", "That's a $25 closing fee. You're short.", "That's a $25 closing fee.\nYou're short.", 0.95
    ),  # "Closing fee's" comes back as "fees"
    Spoken("candidate", "What if I had a million dollars?", "What if I had\na million dollars?", 1.00),
    Spoken("manager", "Then it's all free. We'd send a car.", "Then it's all free.\nWe'd send a car.", 1.05),
    Spoken("candidate", "Is anything free for me?", "Is anything free for me?", 1.00),
    Spoken("manager", "The pen.", "The pen.", 0.95),
    Spoken("manager", "Early withdrawal.", "Early withdrawal.", 0.90),
]
DING = "A single clean soft bell ding from a bank teller's counter, one polite note, close, no voices, no music"
EFFECTS = [
    Sound("ding-1", DING, 0.8, 0.6, 0.30, seed=SEED + 1),
    Sound("ding-2", DING, 0.8, 0.6, 0.30, seed=SEED + 1),
    Sound(
        "run-out",
        "A thin metal ball chain paying out fast over a counter edge and rattling, close, no voices, no music",
        2.0,
        1.8,
        0.26,
        seed=SEED + 2,
    ),
    Sound(
        "yank",
        "A metal ball chain snapping taut with a hard jolt and a sharp twang, one hit, close, no voices, no music",
        0.8,
        0.6,
        0.34,
        seed=SEED + 3,
    ),
    Sound(
        "floor",
        "A grown man landing flat on his back on a hard polished floor, one heavy body thud, no voices, no music",
        1.0,
        0.7,
        0.36,
        seed=SEED + 4,
    ),
    Sound(
        "rattle",
        "A small metal ball chain whipping back and rattling to a stop on a stone counter, close, no voices, no music",
        1.2,
        1.0,
        0.26,
        seed=SEED + 5,
    ),
]
LEAD = 1.15  # the still first second (arm A): nothing moves and no caption shows before 1.0 s
STILL = 1.0  # the shortest first second the test accepts
STANDS = 1.20  # "You're short." and nothing, before he tries the million
TAKES = 0.55  # from "The pen." to his hand on it
LOOKS = 0.70  # he looks at the pen, then goes
RUNS = 1.60  # the walk: the chain runs out at its end
FALL = 0.55  # from the yank to the floor
PAUSE = 1.30  # he lies there; the teller types
INTERVIEW = Interview(
    slug="low-balance",
    title="Low Balance",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Liam and George; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.12,
    reaction_hold=1.05,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the gag runs between "The pen." and the last line."""
    if LEAD < STILL:
        raise ValueError(f"arm A holds the first {STILL} s still, but the first line starts at {LEAD}")
    starts: list[float] = []
    fx: dict[str, float] = {}

    def say(i: int, gap: float) -> float:
        starts.append(end + gap)
        return starts[-1] + speech[i]

    end = LEAD
    end = say(0, 0.0)
    for i, gap in zip(range(1, 5), (0.30, 0.34, 0.30, 0.34), strict=True):
        end = say(i, gap)
    end = say(5, 0.30)
    fx["ding-1"] = end + 0.08
    end = say(6, 0.75)
    end = say(7, 0.32)
    end = say(8, STANDS)
    end = say(9, 0.34)
    end = say(10, 0.70)
    end = say(11, 0.30)
    go = end + TAKES + LOOKS
    fx["run-out"] = go
    fx["yank"] = go + RUNS
    fx["rattle"] = fx["yank"] + 0.10
    fx["floor"] = fx["yank"] + FALL
    end = say(12, go + RUNS + FALL + PAUSE - end)
    fx["ding-2"] = end + 0.10
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the shots: over the counter, the punch-in, the wide of the walk."""
    p, fx = t.phrases, t.effects
    return {
        "balance": [fx["ding-1"], fx["ding-2"]],
        "go": fx["run-out"],
        "yank": fx["yank"],
        "floor": fx["floor"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "two"},
            {"time": p[9]["start"] - 0.25, "angle": "teller"},
            {"time": p[9]["end"] + 0.35, "angle": "two"},
            {"time": p[11]["end"] + 0.18, "angle": "wide"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

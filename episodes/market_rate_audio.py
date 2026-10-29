#!/usr/bin/env python3
"""Episode 16 — Market Rate: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 market_rate_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the gags sit between the lines
(:func:`schedule`) and its camera cuts (:func:`extra`). The candidate from the interview series (Will) got the job;
now he asks the boss (Eric, on the conference-room speakerphone) for a raise.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 16031
VOICES = {  # the same voices as in the interview series (episodes 01 to 06)
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.24)),
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.12)),
}

SCRIPT = [  # role, text, caption, speed
    Spoken("candidate", "Can we talk about my salary?", "Can we talk about my salary?", 1.00),
    Spoken(
        "manager", "Love that. Look at the chart. Record year!", "Love that.\nLook at the chart.\nRecord year!", 1.00
    ),
    Spoken("candidate", "So, a raise?", "So, a raise?", 1.00),
    Spoken("manager", "Better. A title. You're senior now.", "Better. A title.\nYou're Senior now.", 1.00),
    Spoken("candidate", "Does senior pay more?", "Does Senior pay more?", 1.00),
    Spoken("manager", "It's longer.", "It's longer.", 0.92),
    Spoken("candidate", "My job is posted online. Paying more.", "My job is posted online.\nPaying more.", 1.00),
    Spoken("manager", "That's for external talent.", "That's for external talent.", 1.00),
    Spoken("candidate", "So if I quit and reapply?", "So if I quit\nand reapply?", 0.95),
    Spoken("manager", "Hold, please.", "Hold, please.", 0.95),
    Spoken("manager", "Your interview is Thursday.", "Your interview is Thursday.", 0.95),
]
JOIN = 0.15  # after the call chime, before the first line
TITLE_HOLD = 1.25  # "Does Senior pay more?" ... the hold before "It's longer."
PING = "A single short smartphone notification ping, bright and clean, no voices, no music"
# Generated effects: requested seconds, longest kept after trimming, peak level in the mix; one seed each.
EFFECTS = [
    Sound(
        "join",
        "A conference call joining chime from a speakerphone, two short rising electronic tones, no voices, no music",
        1.0,
        0.8,
        0.30,
        seed=SEED,
    ),
    Sound("posting-ping", PING, 0.6, 0.4, 0.30, seed=SEED + 1),
    Sound(
        "hold-music",
        "Cheesy corporate telephone hold music heard through a small speakerphone, a tinny cheerful synth melody, "
        "no voices",
        2.5,
        1.9,
        0.26,
        seed=SEED + 2,
    ),
    Sound("endorse-ping", PING, 0.6, 0.4, 0.30, seed=SEED + 3),
]
INTERVIEW = Interview(
    slug="market-rate",
    title="Market Rate — Comedy Cut 16",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Will and Eric; no reference-voice cloning.",
    room_tone_seed=16032,
    reaction_after=0.55,
    reaction_hold=2.10,
    end_card=2.60,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the gags sit in the gaps between lines."""
    starts: list[float] = []
    fx: dict[str, float] = {"join": 0.05}
    cursor = fx["join"] + effect["join"] + JOIN

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    for i, gap in enumerate((0.30, 0.35, 0.30, 0.40)):
        cursor = say(i) + gap
    cursor = say(4) + TITLE_HOLD
    end = say(5)
    fx["posting-ping"] = end + 0.45
    cursor = fx["posting-ping"] + effect["posting-ping"] + 0.35
    for i, gap in ((6, 0.30), (7, 0.40), (8, 0.45)):
        cursor = say(i) + gap
    end = say(9)
    fx["hold-music"] = end + 0.15
    cursor = fx["hold-music"] + effect["hold-music"] + 0.20
    end = say(10)
    fx["endorse-ping"] = end + 0.65
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The notifications, the hold, the reaction and end card, and the camera cuts."""
    p, fx = t.phrases, t.effects
    return {
        "posting_start": fx["posting-ping"],
        "hold_start": fx["hold-music"],
        "endorse_start": fx["endorse-ping"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},
            {"time": p[1]["start"] - 0.05, "angle": "phone"},
            {"time": p[1]["start"] + 0.9, "angle": "board"},
            {"time": p[2]["start"] - 0.05, "angle": "candidate"},
            {"time": p[3]["start"] - 0.05, "angle": "phone"},
            {"time": p[4]["start"] - 0.05, "angle": "candidate"},
            {"time": p[5]["start"] - 0.05, "angle": "phone"},
            {"time": fx["posting-ping"] - 0.10, "angle": "wide"},
            {"time": p[6]["start"] - 0.05, "angle": "candidate"},
            {"time": p[7]["start"] - 0.05, "angle": "phone"},
            {"time": p[8]["start"] - 0.05, "angle": "candidate"},
            {"time": p[9]["start"] - 0.05, "angle": "phone"},
            {"time": fx["hold-music"] + 0.40, "angle": "candidate"},
            {"time": p[10]["start"] - 0.05, "angle": "phone"},
            {"time": t.reaction, "angle": "candidate"},
            {"time": t.ending, "angle": "end"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

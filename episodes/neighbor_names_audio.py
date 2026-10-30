#!/usr/bin/env python3
"""Neighbor Names — Comedy Cut 25: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record neighbor-names PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the ding and the doors sit between the
lines (:func:`schedule`) and its camera cuts (:func:`extra`). Two neighbors who have shared the elevator for seven years
and never learned each other's names; he nearly asks, and asks about her cardigan instead; a third neighbor greets
them both by the wrong names, and they take them. The opening moves from the first frame (the ``sp-hook_motion``
test's arm B): the greeting is already under way. Rosa is Lily, the applicant Will, the man in the hallway Eric.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 25061
VOICES = {
    "rosa": Singer("pFZP5JQG7iQjIQuC4Bku", "Lily", dict(stability=0.50, similarity_boost=0.75, style=0.25)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.24)),
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.50, similarity_boost=0.75, style=0.20)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("candidate", "Morning!", "Morning!", 1.00),
    Spoken("rosa", "Morning, you!", "Morning... you!", 1.00),
    Spoken("candidate", "Seven years in this building, huh?", "Seven years\nin this building, huh?", 1.00),
    Spoken("rosa", "Seven years!", "Seven years!", 1.00),
    Spoken(
        "candidate",
        "Can I ask you something I should know by now?",
        "Can I ask you something\nI should know by now?",
        1.00,
    ),
    Spoken("rosa", "Anything, dear.", "Anything, dear.", 0.95),
    Spoken("candidate", "Where did you get that cardigan?", "Where did you get\nthat cardigan?", 1.00),
    Spoken("rosa", "I made it.", "I made it.", 1.00),
    Spoken("manager", "Morning, Linda! Morning, Steve!", "Morning, Linda!\nMorning, Steve!", 1.00),
    Spoken("rosa", "Steve.", "Steve.", 0.95),
    Spoken("candidate", "Linda.", "Linda.", 0.95),
]
EFFECTS = [
    Sound(
        "ding",
        "A single soft elevator arrival chime, one clear bell tone, inside the elevator cab, no voices, no music",
        1.0,
        0.8,
        0.30,
        seed=SEED + 1,
    ),
    Sound(
        "doors",
        "Elevator doors sliding open with a smooth rumble and a soft thud, inside the cab, no voices, no music",
        1.2,
        0.9,
        0.22,
        seed=SEED + 2,
    ),
]
INTERVIEW = Interview(
    slug="neighbor-names",
    title="Neighbor Names — Comedy Cut 25",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Lily, Will and Eric; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.50,  # "Linda.", then the two of them, content, as the elevator goes on up
    reaction_hold=1.80,  # both nod to themselves; the last frame
    end_card=0.0,  # no card: the two-shot is the last frame
    font=NOTO_SANS_BOLD,  # the batch's caption face (Google Fonts), pinned under assets/fonts
)
LEAD = 0.30  # the greeting is under way from the first frame (arm B): her wave starts at once
SILENCE = 0.95  # after "Seven years!": the elevator hums; nobody says a name
HESITATE = 0.60  # after "Anything, dear.": he nearly asks
OPEN_AFTER_DING = 0.15  # the doors start to open this long after the ding
SHUT_AFTER = 0.35  # the doors start to shut this long after the hallway greeting ends
TAKE_IN = 1.05  # the doors shut; the names land; then "Steve."


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the ding and the doors after "I made it."."""
    starts: list[float] = []
    fx: dict[str, float] = {}
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    cursor = say(0) + 0.15
    cursor = say(1) + 0.45
    cursor = say(2) + 0.20
    cursor = say(3) + SILENCE
    cursor = say(4) + 0.30
    cursor = say(5) + HESITATE
    cursor = say(6) + 0.25
    cursor = say(7) + 0.35
    fx["ding"] = cursor
    fx["doors"] = cursor + OPEN_AFTER_DING
    cursor = fx["doors"] + 0.55  # the doors open on him
    cursor = say(8) + SHUT_AFTER + TAKE_IN
    cursor = say(9) + 0.45
    say(10)
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The ding, the doors and the camera cuts: the two-shot, each of them close, the hallway."""
    p, fx = t.phrases, t.effects

    def before(i: int) -> float:
        return p[i]["start"] - 0.10

    return {
        "ding_start": fx["ding"],
        "doors_open": fx["doors"],
        "doors_shut": p[8]["end"] + SHUT_AFTER,
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "two"},  # the greeting already under way
            {"time": before(2), "angle": "dev"},
            {"time": before(3), "angle": "rosa"},
            {"time": p[3]["end"] + 0.15, "angle": "two"},  # the silence: both face the doors
            {"time": before(4), "angle": "dev"},
            {"time": before(5), "angle": "rosa"},
            {"time": p[5]["end"] + 0.20, "angle": "dev"},  # he nearly asks
            {"time": before(7), "angle": "rosa"},  # "I made it.": her name on the pocket
            {"time": fx["ding"] - 0.05, "angle": "two"},  # the ding: the doors open on the hallway
            {"time": before(8) + 0.02, "angle": "hall"},
            {"time": p[8]["end"] + SHUT_AFTER, "angle": "two"},  # the doors shut on the names
            {"time": before(9), "angle": "rosa"},
            {"time": before(10), "angle": "dev"},
            {"time": t.reaction - 0.10, "angle": "two"},  # content, both of them, going up
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

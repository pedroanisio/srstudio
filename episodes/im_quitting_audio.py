#!/usr/bin/env python3
"""I'm Quitting: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record im-quitting PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, its effects, and its cuts
(:func:`extra`). He has been quitting at the coffee machine, today, for forty years, and his friend has answered "Mm."
every time. The opening moves from the first frame (the ``sp-hook_motion`` test's arm B): he is already mid-rant. Will
is the man who is quitting, as in *Neighbor Names*; Eric is his friend. Both clinks are one request.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 26101
VOICES = {
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.38, similarity_boost=0.75, style=0.30)),
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.60, similarity_boost=0.75, style=0.10)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("candidate", "That's it. I'm quitting. Today.", "That's it.\nI'm quitting. Today.", 1.10),
    Spoken("manager", "Hmm.", "Mm.", 0.95),  # written as the recogniser hears it
    Spoken("candidate", "This time I mean it.", "This time I mean it.", 1.05),
    Spoken("manager", "Hmm.", "Mm.", 0.95),  # written as the recogniser hears it
    Spoken("manager", "You said Friday.", "You said Friday.", 1.00),
    Spoken("candidate", "Which Friday?", "Which Friday?", 1.00),
    Spoken("manager", "Twelve years of them.", "Twelve years of them.", 1.00),
    Spoken("candidate", "Forty years. Thank you.", "Forty years. Thank you.", 1.00),
    Spoken("candidate", "That's it. I'm quitting.", "That's it. I'm quitting.", 1.00),
    Spoken("manager", "Hmm.", "Mm.", 0.95),  # written as the recogniser hears it
]
CLINK = "A ceramic coffee mug set down on a laminate counter, one short clink, close, no voices, no music"
EFFECTS = [
    Sound(
        "gurgle",
        "An office drip coffee machine gurgling and hissing softly, close, no voices, no music",
        4.0,
        3.4,
        0.14,
        seed=SEED + 1,
    ),
    Sound("clink-1", CLINK, 0.6, 0.45, 0.30, seed=SEED + 2),
    Sound("clink-2", CLINK, 0.6, 0.45, 0.30, seed=SEED + 2),
    Sound(
        "slap",
        "A heavy paper wall planner slapped flat on a counter, one flat smack, close, no voices, no music",
        0.6,
        0.45,
        0.34,
        seed=SEED + 3,
    ),
    Sound(
        "riffle",
        "Calendar pages flipped quickly by a thumb, a fast paper riffle, close, no voices, no music",
        1.6,
        1.5,
        0.24,
        seed=SEED + 4,
    ),
    Sound(
        "applause",
        "Polite applause from about thirty people in a function room, steady then thinning out, no cheering, no music",
        4.5,
        3.6,
        0.26,
        seed=SEED + 5,
    ),
    Sound(
        "tap",
        "A finger tapping a live microphone twice through a small speaker, two soft thumps, no voices, no music",
        0.8,
        0.6,
        0.30,
        seed=SEED + 6,
    ),
]
INTERVIEW = Interview(
    slug="im-quitting",
    title="I'm Quitting",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Will and Eric; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.30,
    reaction_hold=0.85,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the cuts sit on the clinks, the planner on its slap."""
    starts: list[float] = []
    fx: dict[str, float] = {"gurgle": 0.0}

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, 0.05)
    end = say(1, end + 0.22)
    fx["clink-1"] = end + 0.28  # day 2,190
    end = say(2, fx["clink-1"] + 0.20)
    end = say(3, end + 0.22)
    fx["clink-2"] = end + 0.30  # twelve years in
    fx["slap"] = fx["clink-2"] + 0.40
    end = say(4, fx["slap"] + 0.20)
    end = say(5, end + 0.18)
    planner = end + 0.18
    fx["riffle"] = planner + 0.30
    end = say(6, planner + 0.35)
    party = max(end + 0.25, fx["riffle"] + 1.45)
    fx["applause"] = party - 0.05
    end = say(7, party + 0.70)
    fx["tap"] = max(end + 0.85, fx["applause"] + 3.3)
    end = say(8, fx["tap"] + 0.65)
    say(9, end + 0.55)
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on and the cuts: one break-room shot, the planner, the mic, his friend."""
    p, fx = t.phrases, t.effects
    planner = p[5]["end"] + 0.18
    party = fx["applause"] + 0.05
    friend = p[8]["end"] + 0.25
    return {
        "day_six": fx["clink-1"],
        "day_twelve": fx["clink-2"],
        "slap": fx["slap"],
        "riffle": fx["riffle"],
        "applause": [fx["applause"], fx["tap"] - 0.35],
        "tap": fx["tap"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "room"},
            {"time": planner, "angle": "planner"},
            {"time": party, "angle": "mic"},
            {"time": friend, "angle": "friend"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

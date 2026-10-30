#!/usr/bin/env python3
"""Entry Level: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record entry-level PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, its effects, and its cuts
(:func:`extra`). An entry-level job wants ten years, and the applicants get younger until the job goes to someone who
has held it for decades. Its first second is held still (arm A of the ``sp-hook_motion`` test). Eric is the interviewer,
Will the applicant, Liam Milo. The toddler is Brian and the baby George, grown men's voices for applicants who are
never seen. The three desk bells are one request.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 26131
VOICES = {
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.15)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.24)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "toddler": Singer("nPczCjzI2devNBz1zQrb", "Brian", dict(stability=0.55, similarity_boost=0.75, style=0.15)),
    "baby": Singer("JBFqnCBsd6RMkjVDRZzb", "George", dict(stability=0.55, similarity_boost=0.75, style=0.20)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("manager", "It's entry level, so just ten years.", "It's entry level,\nso just ten years.", 1.05),
    Spoken("candidate", "I'm 22.", "I'm 22.", 1.00),
    Spoken("manager", "Have you tried starting earlier?", "Have you tried\nstarting earlier?", 1.00),
    Spoken("toddler", "Been in the role since nursery.", "Been in the role\nsince nursery.", 1.00),
    Spoken("manager", "Promising.", "Promising.", 1.00),
    Spoken("milo", "This software came out in 2024.", "This software\ncame out in 2024.", 1.05),
    Spoken("manager", "We need twenty years in it.", "We need twenty years in it.", 1.00),
    Spoken("baby", "I've been networking since the womb.", "I've been networking\nsince the womb.", 1.00),
    Spoken("manager", "Overqualified. We'd lose you.", "Overqualified.\nWe'd lose you.", 1.00),
    Spoken("candidate", "Who actually got it?", "Who actually got it?", 1.00),
    Spoken("manager", "She's still on probation.", "She's still on probation.", 0.95),
]
BELL = "A single small desk bell, one bright ding, close, no voices, no music"
EFFECTS = [
    Sound("bell-1", BELL, 0.8, 0.5, 0.26, seed=SEED + 1),
    Sound("bell-2", BELL, 0.8, 0.5, 0.26, seed=SEED + 1),
    Sound("bell-3", BELL, 0.8, 0.5, 0.26, seed=SEED + 1),
    Sound(
        "rattle", "A baby's plastic rattle shaken briefly, close, no voices, no music", 0.8, 0.6, 0.24, seed=SEED + 2
    ),
    Sound(
        "snap",
        "A window roller blind snapping up fast and flapping around its roller, close, no voices, no music",
        1.0,
        0.8,
        0.32,
        seed=SEED + 3,
    ),
]
STILL = 1.05  # the held first second: nothing moves
INTERVIEW = Interview(
    slug="entry-level",
    title="Entry Level",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Eric, Will, Liam, Brian and George; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.35,
    reaction_hold=1.60,  # her, in the hat; the last frame
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: each new applicant comes in on the desk bell."""
    starts: list[float] = []
    fx: dict[str, float] = {}

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, STILL + 0.05)
    end = say(1, end + 0.22)
    end = say(2, end + 0.25)
    fx["bell-1"] = end + 0.30
    end = say(3, fx["bell-1"] + 0.35)
    end = say(4, end + 0.25)
    fx["bell-2"] = end + 0.25
    end = say(5, fx["bell-2"] + 0.30)
    end = say(6, end + 0.15)
    fx["bell-3"] = end + 0.25
    fx["rattle"] = fx["bell-3"] + 0.25
    end = say(7, fx["rattle"] + 0.45)
    end = say(8, end + 0.25)
    end = say(9, end + 0.40)
    fx["snap"] = end + 0.65
    say(10, fx["snap"] + 0.75)
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on and the cuts: the desk, then each applicant in the chair opposite."""
    p, fx = t.phrases, t.effects
    return {
        "rattle": [fx["rattle"], fx["rattle"] + 0.6],
        "snap": fx["snap"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "desk"},
            {"time": p[1]["start"] - 0.10, "angle": "applicant"},
            {"time": p[2]["start"] - 0.10, "angle": "desk"},
            {"time": fx["bell-1"] + 0.05, "angle": "toddler"},
            {"time": p[4]["start"] - 0.10, "angle": "desk"},
            {"time": fx["bell-2"] + 0.05, "angle": "tech"},
            {"time": p[6]["start"] - 0.10, "angle": "desk"},
            {"time": fx["bell-3"] + 0.05, "angle": "crib"},
            {"time": p[8]["start"] - 0.10, "angle": "desk"},
            {"time": p[9]["start"] - 0.10, "angle": "door"},
            {"time": p[9]["end"] + 0.15, "angle": "desk"},
            {"time": fx["snap"] + 0.30, "angle": "glass"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

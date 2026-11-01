#!/usr/bin/env python3
"""Many Hats: generated dialogue, resolved by the engine, and the timeline.

    srstudio record many-hats PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits (:func:`schedule`)
and what the picture keys on (:func:`extra`). The job ad said "wears many hats", and the hats are real, and one is
still warm. Eric is the Boss and Will the Candidate, as in the interview reels. There is no music, and the foley is
synthesized in the build. The camera creeps from its first frame, and the first word comes by 0.45 s.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3303
VOICES = {
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.15)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.20)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("manager", "We need someone who wears many hats.", "We need someone who wears many hats.", 1.02),
    Spoken("candidate", "I love hats.", "I love hats.", 1.00),
    Spoken("manager", "Sales.", "Sales.", 1.00),
    Spoken("manager", "Accounting.", "Accounting.", 1.00),
    Spoken("candidate", "This one's warm.", "This one's warm.", 0.95),
    Spoken("manager", "That's Linda's. She left at lunch.", "That's Linda's.\nShe left at lunch.", 1.00),
    Spoken("manager", "Reception. Facilities. The website.", "Reception. Facilities.\nThe website.", 0.88),
    Spoken("candidate", "And the pay?", "And the pay?", 0.92, gain=-2.0),
    Spoken("manager", "The pay is for this one.", "The pay is for this one.", 0.98),
]
START = 0.42  # the first word
FLOOR = 0.96  # a one-word line's start to the next: its cue holds 0.84 s and the next one clears it
SWAY = 1.30  # the held bracket: the stack sways and nobody says anything
FALL = 0.40  # "And the pay?" to the finger
SETTLE = 1.72  # the finger to the last line: the fall, the far thunk, the hand back with the tiny hat
ENDING = 0.85  # the tiny hat, held
INTERVIEW = Interview(
    slug="many-hats",
    title="Many Hats",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Eric and Will; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: a thunk before each hat's word, the sway, the fall and the tiny hat."""
    starts: list[float] = []

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, START)
    end = say(1, end + 0.30)
    end = say(2, end + 0.62)
    end = say(3, max(end + 0.40, starts[2] + FLOOR))
    end = say(4, max(end + 0.85, starts[3] + FLOOR))
    end = say(5, end + 0.35)
    end = say(6, end + 0.55)
    end = say(7, end + SWAY)
    say(8, end + FALL + SETTLE)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on: the three landings between lines, the sway, the finger, the tiny hat."""
    p = t.phrases
    poke = p[7]["end"] + FALL
    return {
        "sales": p[2]["start"] - 0.24,
        "accounting": p[3]["start"] - 0.24,
        "linda": p[4]["start"] - 0.62,
        "steady": p[4]["start"] - 0.34,
        "sway": p[6]["end"] + 0.05,
        "poke": poke,
        "tiny": p[8]["start"] - 0.12,
        "camera_cuts": [{"time": 0, "angle": "desk"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

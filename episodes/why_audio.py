#!/usr/bin/env python3
"""Why: generated dialogue, resolved by the engine, and the timeline.

    srstudio record why PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). A small child asks why, and each answer is shorter than the last, until the parent runs out of
everything and sits down on the floor. Then the child comes back at the door, in a tie, about the bedtime. Jessica is
Pip and Eric is Bo. There is no music: the reel's foley is synthesised in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 42101
VOICES = {
    "pip": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.5, similarity_boost=0.75, style=0.3)),
    "bo": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.5, similarity_boost=0.75, style=0.3)),
}
WHY = "Why?"
SCRIPT = [  # role, text, caption, speed
    Spoken("pip", "Why is the sky blue?", "Why is the sky blue?", 1.05),
    Spoken("bo", "Because of the light.", "Because of the light.", 1.05),
    Spoken("pip", WHY, WHY, 1.0),
    Spoken("bo", "It scatters.", "It scatters.", 1.0),
    Spoken("pip", WHY, WHY, 1.0),
    Spoken("bo", "Molecules.", "Molecules.", 0.95),
    Spoken("pip", WHY, WHY, 1.0),
    Spoken("bo", "Because... of the universe.", "Because... of the universe.", 0.88),
    Spoken("pip", WHY, WHY, 1.0),
    Spoken("bo", "I don't know, Pip.", "I don't know, Pip.", 0.85),
    Spoken("bo", "Nobody knows.", "Nobody knows.", 0.82),
    Spoken("bo", "We just got up one day and did it.", "We just got up one day\nand did it.", 0.85),
    Spoken("pip", "Okay.", "Okay.", 0.95),
    Spoken("pip", "We'll talk about your bedtime.", "We'll talk about\nyour bedtime.", 0.95),
    Spoken("bo", "Why?", "...Why?", 0.8),
]
INTERVIEW = Interview(
    slug="why",
    title="Why",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Jessica and Eric; no reference-voice cloning. Foley synthesised; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.15,
    reaction_hold=0.75,  # the small parent, looking up; the last frame
    end_card=0.0,
    font=SOFT.google_font(),
)
HELD = 1.0  # the first second is a held frame: nobody moves, nobody speaks
BEAT = 0.12  # a "Why?" comes straight back
BLANK = 1.5  # the last "Why?", and he goes down to the floor before he can answer
SHARE = 0.4  # between the things he has to say on the floor
HOLD = 1.0  # after "did it": nothing
PAT = 0.45  # she pats his shoulder before "Okay."
REVERSAL = 0.7  # "Okay.", then the cut to the door


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the whys tight, then the floor, the hold, the pat and the door."""
    starts: list[float] = []
    cursor = HELD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    for i in range(8):
        cursor = say(i) + BEAT
    cursor = say(8) + BLANK
    cursor = say(9) + SHARE
    cursor = say(10) + SHARE
    cursor = say(11) + HOLD + PAT
    cursor = say(12) + REVERSAL
    cursor = say(13) + 0.3
    say(14)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The cuts: on every line of the whys, down to the floor, the pat and the door."""
    p = t.phrases
    return {
        "whys": [round(p[i]["start"], 3) for i in range(2, 9)],
        "floor_start": p[8]["end"] + 0.25,
        "pat_start": p[12]["start"] - PAT,
        "door_start": p[12]["end"] + REVERSAL - 0.2,
        "camera_cuts": [{"time": 0, "angle": "two"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

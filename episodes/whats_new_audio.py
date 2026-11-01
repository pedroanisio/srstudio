#!/usr/bin/env python3
"""What's New: generated dialogue, resolved by the engine, and the timeline.

    srstudio record whats-new PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). An update is a man in your house, and he has moved the sofa. Juno is Laura, Pip is Alice, Bo is
Eric. There is no music: the reel's foley is synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 3403
VOICES = {
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.5, similarity_boost=0.75, style=0.2)),
    "pip": Singer("Xb7hH8MSUJpSbSDYk0k2", "Alice", dict(stability=0.42, similarity_boost=0.75, style=0.4)),
    "bo": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.3)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("juno", "Where's the sofa?", "Where's the sofa?", 1.05),
    Spoken("bo", "Good morning!", "Good morning!", 1.05),
    Spoken("bo", "We've improved your living room.", "We've improved\nyour living room.", 1.05),
    Spoken("pip", "Who are you?", "Who are you?", 1.0),
    Spoken("bo", "Version nine.", "Version nine.", 1.0),
    Spoken("bo", "The sofa's in the hall now.", "The sofa's in the hall now.", 1.02),
    Spoken("juno", "Why?", "Why?", 0.95),
    Spoken("bo", "To bring you closer to the hall.", "To bring you closer\nto the hall.", 1.0),
    Spoken("pip", "Where's the light switch?", "Where's the light switch?", 1.0),
    Spoken("bo", "Under Settings.", "Under Settings.", 1.0),
    Spoken("pip", "We don't have Settings.", "We don't have Settings.", 0.98),
    Spoken("bo", "The fridge.", "The fridge.", 1.0),
    Spoken("bo", "Press and hold.", "Press and hold.", 0.95),
    Spoken("juno", "Put it back.", "Put it back.", 0.92),
    Spoken("bo", "We can't.", "We can't.", 1.0),
    Spoken("bo", "How are we doing?", "How are we doing?", 1.02),
    Spoken("bo", "Good morning!", "Good morning!", 1.05),
]
INTERVIEW = Interview(
    slug="whats-new",
    title="What's New",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Laura, Alice and Eric; no reference-voice cloning. "
    "Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.1,
    reaction_hold=0.5,  # his face in the door, to the cut back to frame 1
    end_card=0.0,
    font=SOFT.google_font(),
)
LEAD = 0.42  # she is already going down on the first frame; the thump lands before the word
BO_IN = 0.55  # he steps in
CUE_MIN = 0.92  # a line's start to the next, so its caption holds its 0.84 s
SWITCH = 0.85  # Pip at the bare wall: click, click on nothing
PRESS = 1.75  # the bracket: a finger on the fridge door, the hum, nothing
LAMP = 0.75  # the lamp behind her comes on, Bo nods
JAB = 1.3  # the insert: her finger comes up, one star, hard
WALK = 2.2  # NEXT MORNING: she walks to the door, sure of herself, and sits
HOLD = 1.3  # the bracket: on the floor, again, nobody speaks


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: quick until the wall, then the two holds the jokes need."""
    gaps = [
        BO_IN,
        0.1,
        0.2,
        0.2,
        0.08,
        0.15,
        0.12,
        SWITCH,
        0.1,
        0.15,
        0.15,
        0.06,
        PRESS + LAMP,
        0.2,
        0.08,
        JAB + WALK + HOLD,
    ]
    starts = [LEAD]
    for length, gap in zip(speech[:-1], gaps, strict=True):
        starts.append(starts[-1] + max(length + gap, CUE_MIN))
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The silent beats, each from the line before it."""
    p = t.phrases
    jab = p[15]["end"] + 0.1
    return {
        "dark_start": p[7]["end"] + 0.04,
        "press_start": p[12]["end"] + 0.1,
        "lamp_start": p[12]["end"] + 0.1 + PRESS,
        "jab_start": jab,
        "next_start": jab + JAB,
        "peek_start": p[16]["start"] - 0.34,
        "camera_cuts": [{"time": 0, "angle": "room"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

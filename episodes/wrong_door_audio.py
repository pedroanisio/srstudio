#!/usr/bin/env python3
"""Wrong Door: generated dialogue, resolved by the engine, and the timeline.

    srstudio record wrong-door PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits
(:func:`schedule`) and its beats (:func:`extra`). Pip is Will and Bo is Eric. There is no music: the foley is
synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 3424
VOICES = {
    "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45)),
    "bo": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.3)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("bo", "Great interview, Pip. We'll call you.", "Great interview, Pip.\nWe'll call you.", 1.05),
    Spoken("pip", "Thank you, thank you, thank you.", "Thank you, thank you,\nthank you.", 1.08),
    Spoken("pip", "Okay. That's a closet.", "Okay. That's a closet.", 0.92),
    Spoken("pip", "He's still out there.", "He's still out there.", 0.92),
    Spoken("pip", "I live here now.", "I live here now.", 0.95),
    Spoken("pip", "Hi! Yes! Totally!", "Hi! Yes! Totally!", 1.05),
    Spoken("bo", "Pip. You've been here since Monday.", "Pip. You've been here\nsince Monday.", 1.0),
    Spoken("pip", "Yes.", "Yes.", 0.95),
    Spoken("bo", "First in, last out. You got the job.", "First in, last out.\nYou got the job.", 0.98),
    Spoken("bo", "Other door.", "Other door.", 0.95),
]  # fmt: skip
LEAD = 0.25  # the handshake is already going
CUE = 0.92  # a line's start to the next, so its caption holds its 0.84 s
ACROSS = 1.80  # after his thanks: he goes in, shuts it with authority, and the shut door holds before the dark
DARK = 1.20  # the held bracket in the closet: the mop goes over and nobody speaks
SAT = 0.60  # after "That's a closet.": the chair creaks outside
LATER = 0.70  # after "I live here now.": the door opens on Wednesday
NEXT_DOOR = 2.20  # after "You got the job.": Bo shuts the closet, the handshake, Pip strides to the next door
ALONE = 0.90  # the held bracket on Bo, and the clatter behind the door
ENDING = 0.35  # out on the last word
INTERVIEW = Interview(
    slug="wrong-door",
    title="Wrong Door",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Will and Eric; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=SOFT.google_font(),
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: quick into the door, then the two holds the jokes need."""
    gaps = [0.1, ACROSS + DARK, SAT, 0.35, LATER, 0.2, 0.15, 0.5, NEXT_DOOR + ALONE]
    starts = [LEAD]
    for length, gap in zip(speech[:-1], gaps, strict=True):
        starts.append(starts[-1] + max(length + gap, CUE))
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The silent beats, each from the line around it."""
    p = t.phrases
    dark = p[2]["start"] - DARK
    opens = p[1]["start"] + 1.0  # his hand is on the door by 3.0 s
    alone = p[9]["start"] - ALONE
    return {
        "dark_start": dark,
        "shut_start": p[1]["end"] + 0.65,
        "in_start": opens + 0.25,
        "opens_start": opens,
        "wednesday_start": p[5]["start"] - 0.55,
        "bo_shuts_start": p[8]["end"] + 0.12,
        "next_shut_start": alone - 0.08,
        "alone_start": alone,
        "clatter_start": alone + 0.42,
        "camera_cuts": [{"time": 0, "angle": "room"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

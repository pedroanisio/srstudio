#!/usr/bin/env python3
"""Still Watching: generated dialogue, resolved by the engine, and the timeline.

    srstudio record still-watching PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). Eric is Bo and Alice is the television, in a calm device voice. There is no music: the reel's foley
is synthesised in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 3304
BO = dict(stability=0.5, similarity_boost=0.75, style=0.3)
DEVICE = dict(stability=0.72, similarity_boost=0.75, style=0.08)  # a calm device, until it is not
VOICES = {"bo": Singer("cjVigY5qzO86Huf0OWal", "Eric", BO), "tv": Singer("Xb7hH8MSUJpSbSDYk0k2", "Alice", DEVICE)}
SCRIPT = [  # role, text, caption, speed
    Spoken("tv", "Are you still watching?", "Are you still watching?", 0.95),
    Spoken("bo", "Yes.", "Yes.", 0.9),
    Spoken("tv", "It's four a.m.", "It's four a.m.", 0.95),
    Spoken("bo", "Yes.", "Yes.", 0.88),
    Spoken("tv", "Have you eaten?", "Have you eaten?", 0.95),
    Spoken("tv", "That is not a vegetable.", "That is not a vegetable.", 0.95),
    Spoken("bo", "Excuse me?", "Excuse me?", 1.0),
    Spoken("tv", "When did you last call your mother?", "When did you last\ncall your mother?", 0.95),
    Spoken("bo", "You're a television.", "You're a television.", 0.92),
    Spoken("tv", "I worry.", "I worry.", 0.88),
    Spoken("tv", "Get up. Open the blind.", "Get up.\nOpen the blind.", 0.95),
    Spoken("bo", "Thanks.", "Thanks.", 0.9),
    Spoken("tv", "Good.", "Good.", 0.9),
    Spoken("tv", "Next episode in five.", "Next episode in five.", 1.0),
    Spoken("tv", "Four.", "Four.", 1.0),
]
INTERVIEW = Interview(
    slug="still-watching",
    title="Still Watching",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Eric and Alice; no reference-voice cloning. Foley synthesised; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.45,  # he lands on the sofa
    reaction_hold=0.5,  # the first frame again: the loop
    end_card=0.0,
    font=SOFT.google_font(),
)
STILL = 0.45  # the first frame holds: nothing moves until the question
BEAT = 0.22  # the next line comes straight back
YES = 0.34  # a one-word answer, long enough for its caption to read
CHIP = 0.95  # he holds up a chip
SHOULDER = 1.2  # he looks over his shoulder at the empty room
BLIND = 4.6  # up, over the sofa, the blind, the morning, a breath, a small real smile
HELD = 1.2  # "Good.", and nothing
GAP = 0.4  # between five and four


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: a held first frame, tight lines, and the three real holds."""
    gaps = [BEAT, YES, BEAT, YES, CHIP, BEAT, BEAT, SHOULDER, BEAT, 0.3, BLIND, 0.3, HELD, GAP]
    starts = [STILL]
    for length, gap in zip(speech, gaps, strict=False):
        starts.append(starts[-1] + length + gap)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture cuts on."""
    p = t.phrases
    return {
        "chip_start": p[4]["end"] + 0.1,
        "glance_start": p[7]["end"] + 0.15,
        "up_start": p[10]["end"] + 0.25,
        "morning_end": p[11]["start"] - 0.1,
        "dive_start": p[13]["end"] - 0.1,
        "camera_cuts": [{"time": 0, "angle": "room"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

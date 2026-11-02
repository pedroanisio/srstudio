#!/usr/bin/env python3
"""Unread: generated dialogue, resolved by the engine, and the timeline.

    srstudio record unread PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). Pip has 41,383 unread and a rule about them, and the rule has cost him a car, a lease and a job he
never knew he had. Juno is Laura, Pip is Will. There is no music: the reel's foley is synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 5206
VOICES = {
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.5, similarity_boost=0.75, style=0.2)),
    "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("juno", "41,000 unread?", "41,000 unread?", 1.05),
    Spoken("pip", "If it's important, they'll call.", "If it's important,\nthey'll call.", 1.0),
    Spoken("juno", "Your car was towed. Your lease ended.", "Your car was towed.\nYour lease ended.", 1.02),
    Spoken("pip", "That explains the new people.", "That explains\nthe new people.", 1.0),
    Spoken("juno", "Someone hired you in April.", "Someone hired you\nin April.", 1.0),
    Spoken("pip", "Why didn't they call?", "Why didn't they call?", 0.95),
    Spoken("juno", "Eleven times.", "Eleven times.", 1.0),
    Spoken("pip", "If it's important, they'll email.", "If it's important,\nthey'll email.", 0.95),
]
INTERVIEW = Interview(
    slug="unread",
    title="Unread",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Laura and Will; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=0.25,  # the cut lands on his last word
    end_card=0.0,
    font=SOFT.google_font(),
)
LEAD = 0.25  # the phone is already rising, and the badge ticks under her question
CUE_MIN = 0.92  # a line's start to the next, so its caption holds its 0.84 s
ANSWER = 0.3  # the two-shot lands before he answers
CAPTION_TAIL = 0.3  # a caption stays up this long past its line
LOOK_UP = 0.34  # the list goes this long before her next line: she looks up at him before she says it
HOLD = 1.56  # the bracket: his caption comes down, her thumb stops on the third row, and she reads it again
RING = 1.35  # the bracket: the phone rings at him and he looks at it, and then at her


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: quick, with the two holds the script brackets."""
    gaps = [ANSWER, 0.22, 0.2, HOLD, 0.25, 0.14, RING]
    starts = [LEAD]
    for length, gap in zip(speech[:-1], gaps, strict=True):
        starts.append(starts[-1] + max(length + gap, CUE_MIN))
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The silent beats, each from the line before it."""
    p = t.phrases
    return {
        "stop_start": p[3]["end"] + CAPTION_TAIL,  # the cut waits for his caption
        "ring_start": max(p[6]["end"] + 0.04, p[6]["start"] + CUE_MIN),  # "Eleven times." keeps its 0.84 s
        "camera_cuts": [{"time": 0, "angle": "room"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

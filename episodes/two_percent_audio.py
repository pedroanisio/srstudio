#!/usr/bin/env python3
"""Two Percent: generated dialogue, resolved by the engine, and the timeline.

    srstudio record two-percent PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). Juno is always on 2% and asks, and Pip says yes until the 2% is his. Juno is Laura, Pip is Will.
There is no music: the reel's foley is synthesized in the build. Two of the gaps are the script's brackets: Pip's
battery going down in its inserts, where nobody speaks, and the hold on the two phones.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 5311
VOICES = {
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.5, similarity_boost=0.75, style=0.2)),
    "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45)),
}
SCRIPT = [  # role, text, caption, speed
    # the pause gives the opening line time to be read
    Spoken("pip", "You're on... two percent?", "You're on 2%?", 1.0),
    Spoken("juno", "Since Tuesday.", "Since Tuesday.", 1.0),
    Spoken("juno", "Can you get the ride? Mine's resting.", "Can you get the ride?\nMine's resting.", 1.0),
    Spoken(
        "juno", "And a photo of us. And text my mom I'm alive.", "And a photo of us.\nAnd text my mom I'm alive.", 1.0
    ),
    Spoken("juno", "You should really charge your phone.", "You should really\ncharge your phone.", 0.95),
]
INTERVIEW = Interview(
    slug="two-percent",
    title="Two Percent",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Laura and Will; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.02,
    reaction_hold=0.06,  # the cut lands on her last word
    end_card=0.0,
    font=SOFT.google_font(),
)
LEAD = 0.45  # his first line by 0.5 s
ANSWER = 0.28  # she answers without looking up
ASK = 0.3  # and asks
STEP = 0.9  # a battery number's hold: each one stays readable, at least 0.84 s
AFTER_ASK = 0.2  # the insert comes in after she has asked
BACK = 0.3  # the two-shot lands before her next line
AFTER_ALIVE = 0.2  # the insert comes in after "alive"
HOLD = 1.3  # the bracket: he shows her his 2%, she looks at it, and at him


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths, with the script's two wordless stretches between them."""
    gaps = [ANSWER, ASK, AFTER_ASK + 2 * STEP + BACK, AFTER_ALIVE + 3 * STEP + HOLD]
    starts = [LEAD]
    for length, gap in zip(speech[:-1], gaps, strict=True):
        starts.append(starts[-1] + length + gap)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The silent beats, each from the line before it."""
    p = t.phrases
    ride = p[2]["end"] + AFTER_ASK
    drain = p[3]["end"] + AFTER_ALIVE
    return {
        "ride_start": ride,
        "ride_end": ride + 2 * STEP,
        "drain_start": drain,
        "drain_end": drain + 3 * STEP,
        "camera_cuts": [{"time": 0, "angle": "room"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

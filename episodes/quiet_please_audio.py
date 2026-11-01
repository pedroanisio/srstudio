#!/usr/bin/env python3
"""Quiet Please: generated dialogue, resolved by the engine, and the timeline.

    srstudio record quiet-please PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). In a silent reading room two stomachs fall for each other in tinted captions, until the librarian's
own answers. Only Bo speaks, and Bo is Eric. There is no music: the stomachs and the room are synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 3118
VOICES = {"bo": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.45, similarity_boost=0.75, style=0.3))}
SCRIPT = [  # role, text, caption, speed
    Spoken("bo", "Shh.", "Shh.", 0.95),
    Spoken("bo", "Shh!", "Shh!", 1.0),
    Spoken("bo", "Shh.", "...Shh.", 0.85),
]
INTERVIEW = Interview(
    slug="quiet-please",
    title="Quiet Please",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voice Eric; no reference-voice cloning. Stomachs synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.35,  # "...Shh.", the yogurt arrives
    reaction_hold=1.45,  # he looks at it; the last frame
    end_card=0.0,
    font=SOFT.google_font(),
)
LEAD = 0.35  # the finger is rising on the first frame
AFTER_SHH = 0.4  # the room, one page
HELLO_Q = 2.2  # the long growl on Pip, "hello?", held
HELLO = 1.6  # the reply on Juno, "hello."
GOSSIP = 1.15  # one exchange in the back and forth
BLUSH = 1.0  # they hold each other's eye
ASK = 1.5  # "are you seeing anyone?"
ANSWER = 1.5  # "just a yogurt", and it holds
WALK = 1.5  # Bo comes up between them
HOLD = 1.25  # the finger is up: nothing
VAST = 2.3  # the crash zoom, the long growl, "HELLO."
SNACKS = 2.3  # "NOTHING SINCE TUESDAY. WHO HAS SNACKS?"


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the stomachs' conversation is what sits between them."""
    first = LEAD
    middle = first + speech[0] + AFTER_SHH + HELLO_Q + HELLO + 4 * GOSSIP + BLUSH + ASK + ANSWER + WALK
    last = middle + speech[1] + HOLD + VAST + SNACKS
    return Schedule([first, middle, last], {})


def extra(t: Timing) -> dict:
    """The stomachs' cues, in order, each from the line before."""
    p = t.phrases
    pip_start = p[0]["end"] + AFTER_SHH
    juno_start = pip_start + HELLO_Q
    gossip_start = juno_start + HELLO
    blush_start = gossip_start + 4 * GOSSIP
    ask_start = blush_start + BLUSH
    answer_start = ask_start + ASK
    walk_start = answer_start + ANSWER
    vast_start = p[1]["end"] + HOLD
    return {
        "pip_start": pip_start,
        "juno_start": juno_start,
        "gossip_start": gossip_start,
        "blush_start": blush_start,
        "ask_start": ask_start,
        "answer_start": answer_start,
        "walk_start": walk_start,
        "vast_start": vast_start,
        "snacks_start": vast_start + VAST,
        "reaction_start": t.reaction,
        "camera_cuts": [{"time": 0, "angle": "room"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

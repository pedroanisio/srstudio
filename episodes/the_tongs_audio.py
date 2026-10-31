#!/usr/bin/env python3
"""The Tongs: generated dialogue, resolved by the engine, and the timeline.

    srstudio record the-tongs PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). Bo runs the grill, and when Pip turns one burger the lawn becomes a Western. Bo is Eric, Pip is
Will, Juno is Laura. There is no music: the reel's foley is synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 3114
VOICES = {
    "bo": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.3)),
    "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.35, similarity_boost=0.75, style=0.4)),
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.5, similarity_boost=0.75, style=0.2)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("bo", "Nobody touches the grill.", "Nobody touches the grill.", 0.92),
    Spoken("juno", "Pip. Don't.", "Pip. Don't.", 0.95),
    Spoken("bo", "Put them down.", "Put them down.", 0.85, gain=-6.0),
    Spoken("pip", "It was burning.", "It was burning.", 1.0),
    Spoken("bo", "That's searing.", "That's searing.", 0.92),
    Spoken("pip", "That's a fire.", "That's a fire.", 1.0),
    Spoken("juno", "He has two.", "He has two.", 0.95),
    Spoken("juno", "Pizza's here.", "Pizza's here.", 1.0),
    Spoken("bo", "Nobody touches the pizza.", "Nobody touches the pizza.", 0.9, gain=-6.0),
]
INTERVIEW = Interview(
    slug="the-tongs",
    title="The Tongs",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Eric, Will, Laura; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.15,  # "pizza.", then the tongs
    reaction_hold=1.0,  # click click, and Bo looking at us; the last frame
    end_card=0.0,
    font=SOFT.google_font(),
)
LEAD = 0.42  # click click, already moving on the first frame
LEAVE = 1.75  # he goes for the sauce; Pip looks round, takes the spare tongs, turns one burger
HUSH = 0.75  # "Don't.", Pip frozen with the burger turned
BACK = 0.75  # the cut to Bo's eyes: no birds, before a word
STARE = 0.7  # "down.", the eyes hold
STANDOFF = 0.75  # the cut to the two of them, tongs at the hip, click click
DRAW = 1.7  # he reaches behind his back, slowly, and draws the second pair
TWO = 1.2  # "He has two.", held
CIRCLE = 2.2  # they circle, the burgers go black, the flames rise, she walks in with the box
DROOP = 1.5  # the tongs droop, Pip goes to the box, Bo's come down on the lid, and it holds


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the three lines of the standoff tight, the holds everywhere else."""
    starts: list[float] = []
    cursor = LEAD
    for i, rest in (
        (0, LEAVE),
        (1, HUSH + BACK),
        (2, STARE + STANDOFF),
        (3, 0.12),
        (4, 0.12),
        (5, DRAW),
        (6, TWO + CIRCLE),
        (7, DROOP),
    ):
        starts.append(cursor)
        cursor += speech[i] + rest
    starts.append(cursor)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The cuts: Bo gone, Bo back at the eyes, the two of them, the low angle, the wide, and the hold on Bo."""
    p = t.phrases
    return {
        "gone_start": p[0]["end"],
        "eyes_start": p[1]["end"] + HUSH,
        "standoff_start": p[2]["end"] + STARE,
        "low_start": p[5]["end"] + 0.2,
        "wide_start": p[6]["end"] + TWO,
        "droop_start": p[7]["end"] + 0.1,
        "bo_start": p[8]["start"] - 0.7,
        "reaction_start": t.reaction,
        "camera_cuts": [{"time": 0, "angle": "lawn"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

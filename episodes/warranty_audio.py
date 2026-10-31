#!/usr/bin/env python3
"""Warranty: generated dialogue, resolved by the engine, and the timeline.

    srstudio record warranty PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). Pip tries to kill the washing machine before its warranty ends, so it dies free. It runs better
than ever until the stroke of midnight, and then the whole house goes. Pip is Will, Juno is Laura. There is no music:
the reel's foley is synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 3116
VOICES = {
    "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.35, similarity_boost=0.75, style=0.4)),
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.5, similarity_boost=0.75, style=0.2)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("juno", "What are you doing?", "What are you doing?", 1.05),
    Spoken("pip", "The warranty ends at midnight.", "The warranty ends at midnight.", 1.0),
    Spoken("pip", "It's going to die the second it's over.", "It's going to die\nthe second it's over.", 1.02),
    Spoken("pip", "They always do.", "They always do.", 1.0, gain=-6.0),
    Spoken("pip", "So it dies now. While it's free.", "So it dies now.\nWhile it's free.", 0.98),
    Spoken("pip", "Spin, you coward.", "Spin, you coward.", 0.95),
    Spoken("juno", "It's never run better.", "It's never run better.", 0.98),
    Spoken("pip", "Oh, you little...", "Oh, you little...", 0.9),
    Spoken("juno", "When did we buy the house?", "When did we buy the house?", 0.95),
    Spoken("pip", "Same day.", "Same day.", 0.9, gain=-7.0),
]
INTERVIEW = Interview(
    slug="warranty",
    title="Warranty",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Will and Laura; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.8,  # "Same day.", nothing
    reaction_hold=2.3,  # the creak, the dust, the two of them looking up; the last frame
    end_card=0.0,
    font=SOFT.google_font(),
)
LEAD = 0.45  # the brick is in the air on the first frame
BRICK = 0.5  # the second brick, after his line
SHOVE = 1.15  # the purr, and he shoves in the ball
FEEDING = 1.3  # 11:56: she pours in the coins, then the shovel
TUNE = 1.3  # the five notes, before 11:59 is over
SPENT = 1.4  # the two of them on the floor, watching it
MIDNIGHT = 1.3  # 12:00, the click, the sigh, the thread of smoke
ROOM = 2.4  # the lamp, the TV, the fridge, one at a time
DARK = 0.9  # near dark, a long pause
HEAR_IT = 1.2  # the question lands in the dark before "Same day."


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the argument tight, the night's holds after it."""
    starts: list[float] = []
    cursor = LEAD
    for i, rest in (
        (0, 0.1),
        (1, BRICK),
        (2, 0.15),
        (3, 0.15),
        (4, SHOVE),
        (5, FEEDING),
        (6, TUNE + SPENT + MIDNIGHT),
        (7, ROOM + DARK),
        (8, HEAR_IT),
    ):
        starts.append(cursor)
        cursor += speech[i] + rest
    starts.append(cursor)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The clock's cuts and the room going out, each from the lines around it."""
    p = t.phrases
    chime = p[6]["end"] + 0.5
    midnight = chime + TUNE + SPENT
    return {
        "second_start": p[1]["end"] + 0.1,
        "ball_start": p[4]["end"] + 0.25,
        "feeding_start": p[5]["end"] + 0.35,
        "floor_start": p[6]["end"] + 0.25,
        "chime_start": chime,
        "midnight_start": midnight,
        "lamp_start": p[7]["end"] + 0.5,
        "creak_start": t.reaction,
        "camera_cuts": [{"time": 0, "angle": "room"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

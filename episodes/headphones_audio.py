#!/usr/bin/env python3
"""Headphones: generated dialogue, resolved by the engine, and the timeline.

    srstudio record headphones PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script and the beats between the lines. Rosa
shouts her husband's rash down a supermarket aisle with her earbuds in. Rosa is Lily at two settings, the shout and the
real, tiny voice, which share a mouth; Milo is Liam; the loudspeaker is Daniel. Every sound but the voices is foley.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 26411
LILY = "pFZP5JQG7iQjIQuC4Bku"
VOICES = {
    "rosa": Singer(LILY, "Lily", dict(stability=0.30, similarity_boost=0.75, style=0.6)),
    "rosa-small": Singer(LILY, "Lily", dict(stability=0.70, similarity_boost=0.75, style=0.0)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "loudspeaker": Singer("onwK4e9ZLuTAKqWW03F9", "Daniel", dict(stability=0.70, similarity_boost=0.75, style=0.1)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("rosa", "THE RASH IS BETTER!", "THE RASH IS BETTER.", 1.00),
    Spoken("rosa", "NO, THE OTHER RASH!", "NO, THE OTHER RASH.", 1.00),
    Spoken(
        "rosa",
        "I TOLD HIM! HAROLD, I SAID, THAT IS NOT A MOLE!",
        "I TOLD HIM. HAROLD, I SAID,\nTHAT IS NOT A MOLE.",
        1.0,
    ),
    Spoken(
        "rosa",
        "HE WON'T SHOW THE DOCTOR! HE SHOWED THE NEIGHBORS!",
        "HE WON'T SHOW THE DOCTOR.\nHE SHOWED THE NEIGHBORS.",
        1.00,
    ),
    Spoken("milo", "Ma'am? You're very loud.", "Ma'am? You're very loud.", 1.00),
    Spoken("rosa-small", "Am I, dear?", "Am I, dear?", 0.90, gain=-9.0),
    Spoken("loudspeaker", "Oatmeal baths are on aisle nine.", "Oatmeal baths are on aisle nine.", 0.95),
]
OPEN = 0.45  # she is already rolling; the first word lands inside half a second
STEP = 0.50  # between the first two shouts
FROZEN = 0.80  # the hold on Milo not moving, after the other rash
NEXT = 0.30  # the next shout, on the heels of the last
TAP = 1.05  # the wide on all those people, then the tap on her arm
TAKES_OUT = 1.05  # the bud comes out in silence
QUIET = 1.50  # after "Am I, dear?": the hold on Rosa
LOOK = 1.20  # the people looking back, in no sound at all
CHIME = 0.75  # the chime, then the voice in the ceiling
ENDING = 1.00  # the hold on Rosa
INTERVIEW = Interview(
    slug="headphones",
    title="Headphones",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Lily, Liam and Daniel; no cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.30,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the shouts run on, then everything stops and the silence is the joke."""
    starts: list[float] = []

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, OPEN)
    end = say(1, end + STEP)
    end = say(2, end + FROZEN)
    end = say(3, end + NEXT)
    end = say(4, end + TAP)
    end = say(5, end + TAKES_OUT)
    say(6, end + QUIET + LOOK + CHIME)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on: the people look back after her hold, and the chime breaks it."""
    p = t.phrases
    look = p[5]["end"] + QUIET
    return {
        "look": look,
        "chime": look + LOOK,
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [{"time": 0, "angle": "aisle"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

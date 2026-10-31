#!/usr/bin/env python3
"""Still Bright: generated dialogue, resolved by the engine, and the timeline.

    srstudio record still-bright PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). Juno wants to buy a twelve dollar lamp. Pip is reading the reviews, and one reviewer, Dale, keeps
updating his. By 2:40 a.m. they have sent him a lamp. Juno is Laura, Pip is Will, Dale is Eric. There is no music: the
reel's foley is synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 3108
VOICES = {
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.35, similarity_boost=0.75, style=0.45)),
    "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45)),
    "dale": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.50, similarity_boost=0.75, style=0.30)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("juno", "It's a $12 lamp.", "It's a $12 lamp.", 1.05),
    Spoken("pip", "Hang on. I'm reading the reviews.", "Hang on.\nI'm reading the reviews.", 1.05),
    Spoken(
        "dale",
        "Bright. Wife says too bright. Four stars.",
        "Bright. Wife says too bright.\nFour stars.",
        0.95,
        gain=-3.0,
    ),
    Spoken("juno", "Just buy it.", "Just buy it.", 1.05),
    Spoken(
        "dale",
        "Update. Wife has left. Lamp still bright.",
        "Update. Wife has left.\nLamp still bright.",
        0.92,
        gain=-3.0,
    ),
    Spoken("juno", "Scroll.", "Scroll.", 0.95, gain=-4.0),
    Spoken("dale", "Update. Met Linda. She likes the lamp.", "Update. Met Linda.\nShe likes the lamp.", 0.95),
    Spoken("pip", "Go on, Dale.", "Go on, Dale.", 0.95),
    Spoken("dale", "Update. Linda took the lamp.", "Update.\nLinda took the lamp.", 0.90, gain=-4.0),
    Spoken("juno", "Send him a lamp.", "Send him a lamp.", 0.95),
    Spoken("pip", "12 bucks. Sent.", "12 bucks. Sent.", 1.0),
    Spoken(
        "dale",
        "Update. A stranger sent me a lamp. It is too bright.",
        "Update. A stranger\nsent me a lamp.\nIt is too bright.",
        0.92,
    ),
    Spoken("dale", "She was right.", "She was right.", 0.88, gain=-6.0),
]
INTERVIEW = Interview(
    slug="still-bright",
    title="Still Bright",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Laura, Will and Eric; no voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.35,  # "She was right."
    reaction_hold=0.85,  # Dale, in the glare; the last frame
    end_card=0.0,
    font=SOFT.google_font(),
)
LEAD = 0.05  # already mid-sentence on the first frame
LATE = 0.95  # "Lamp still bright.", and she sits down
CLOCK = 1.0  # the clock card reads before "Go on, Dale."
GASP = 1.2  # "Linda took the lamp.", and nobody says anything
WAIT = 1.5  # "Sent.", and they wait
PING = 0.6  # the ping, and they lean in
CUT = 0.45  # Dale's room, before he speaks
OVER = 1.0  # "It is too bright.", and then nothing
INSERT_IN, INSERT_OUT = 0.18, 0.12  # the review card, around each of Dale's lines on the phone
ON_PHONE = (2, 4, 6, 8)  # Dale's lines read off the phone


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the first review quick, the night slower, then the holds."""
    starts: list[float] = []
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    for i, rest in (
        (0, 0.10),
        (1, 0.32),
        (2, 0.24),
        (3, 0.32),
        (4, LATE),
        (5, 0.45),
        (6, CLOCK),
        (7, 0.32),
        (8, GASP),
        (9, 0.15),
        (10, WAIT + PING + CUT),
        (11, OVER),
    ):
        cursor = say(i) + rest
    say(12)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The cuts: the card around each review, the clock after "She likes the lamp.", the ping, Dale's room."""
    p = t.phrases
    sent = p[10]["end"]
    return {
        "inserts": [[round(p[i]["start"] - INSERT_IN, 3), round(p[i]["end"] + INSERT_OUT, 3)] for i in ON_PHONE],
        "sit_start": p[4]["end"] + 0.15,
        "clock_start": p[6]["end"] + INSERT_OUT,
        "ping_start": sent + WAIT,
        "dale_start": sent + WAIT + PING,
        "reaction_start": t.reaction,
        "camera_cuts": [{"time": 0, "angle": "two"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

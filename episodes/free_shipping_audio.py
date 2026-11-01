#!/usr/bin/env python3
"""Free Shipping: generated dialogue, resolved by the engine, and the timeline.

    srstudio record free-shipping PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). Juno will not pay six dollars for shipping, so she spends twenty one more to get it free. A week on
the parcels reach the ceiling, and it costs six dollars to send them back. Juno is Laura, Pip is Will. There is no
music: the reel's foley is synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 3113
VOICES = {
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.35, similarity_boost=0.75, style=0.45)),
    "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("juno", "$6 shipping? No way.", "$6 shipping? No way.", 1.0, seed=SEED + 21),
    Spoken("pip", "How much till it's free?", "How much till it's free?", 1.05),
    Spoken("juno", "$21. Tiny whisk.", "$21. Tiny whisk.", 1.05),
    Spoken("pip", "We don't need a tiny whisk.", "We don't need a tiny whisk.", 1.05),
    Spoken("juno", "It saves us $6.", "It saves us $6.", 1.05),
    Spoken("juno", "Egg poacher. Sock stretcher. Bird feeder.", "Egg poacher.\nSock stretcher. Bird feeder.", 1.0),
    Spoken("pip", "We don't have a bird.", "We don't have a bird.", 1.0, gain=-3.0),
    Spoken("juno", "$50.02! Free shipping!", "$50.02! Free shipping!", 1.08),
    Spoken("pip", "Send it all back.", "Send it all back.", 0.92, gain=-4.0),
    Spoken("juno", "Return shipping is $6.", "Return shipping is $6.", 0.92, seed=SEED + 22, gain=-6.0),
    Spoken("pip", "$6? No way.", "$6? No way.", 1.0),
]
INTERVIEW = Interview(
    slug="free-shipping",
    title="Free Shipping",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Laura and Will; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.2,  # "No way."
    reaction_hold=0.5,  # the frame the reel opened on, the seats swapped; the last frame
    end_card=0.0,
    font=SOFT.google_font(),
)
OPENING = 1.0  # arm A: nothing moves and nothing is said or written for this long
LEAD = OPENING + 0.05
FANFARE = 0.75  # "Free shipping!", the punch and the sting
LOOK = 0.7  # a week on: the parcels and the whisk, before a word
SLIP = 1.2  # "Send it all back.", and she reads the slip
SWAP = 1.5  # "six dollars.", and he goes and sits down


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the checkout tight, then the three holds."""
    starts: list[float] = []
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    for i, rest in (
        (0, 0.12),
        (1, 0.12),
        (2, 0.12),
        (3, 0.12),
        (4, 0.4),
        (5, 0.12),
        (6, 0.12),
        (7, FANFARE + LOOK),
        (8, SLIP),
        (9, SWAP),
    ):
        cursor = say(i) + rest
    say(10)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The cart's ticks and the week's cut: each item ticks as it is named, the last one tips it over fifty."""
    p = t.phrases
    items = p[5]
    third = (items["end"] - items["start"]) / 3
    return {
        "added": [round(p[4]["end"] + 0.1, 3), *(round(items["start"] + k * third + 0.1, 3) for k in range(3))],
        "cart_start": p[2]["start"],
        "free_start": p[7]["start"] + 0.62 * (p[7]["end"] - p[7]["start"]),
        "week_start": p[7]["end"] + FANFARE,
        "sit_start": p[9]["end"] + 0.25,
        "reaction_start": t.reaction,
        "camera_cuts": [{"time": 0, "angle": "two"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

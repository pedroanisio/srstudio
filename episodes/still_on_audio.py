#!/usr/bin/env python3
"""Still On: generated dialogue, resolved by the engine, and the timeline.

    srstudio record still-on PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). Laura is Juno and Alice is Pip. There is no music: the reel's foley is synthesised in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 3324
BRIGHT = dict(stability=0.42, similarity_boost=0.75, style=0.4)
VOICES = {
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", BRIGHT),
    "pip": Singer("Xb7hH8MSUJpSbSDYk0k2", "Alice", BRIGHT),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("juno", "Still on for tonight!", "Still on for tonight!", 1.05),
    Spoken("pip", "Can't wait!", "Can't wait!", 1.05),
    Spoken("pip", "Please cancel.", "Please cancel.", 0.85),
    Spoken("juno", "Please cancel. Please.", "Please cancel. Please.", 0.88),
    Spoken("juno", "If you're tired, we can move it.", "If you're tired,\nwe can move it.", 1.05),
    Spoken("pip", "I'm great if you're great!", "I'm great if you're great!", 1.08),
    Spoken("juno", "So great!", "So great!", 1.05),
    Spoken("pip", "So excited!", "So excited!", 1.05),
    Spoken("pip", "You look nice.", "You look nice.", 0.95),
    Spoken("juno", "Same time next year?", "Same time next year?", 1.0),
    Spoken("pip", "Can't wait!", "Can't wait!", 1.05),
]
INTERVIEW = Interview(
    slug="still-on",
    title="Still On",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Laura and Alice; no reference-voice cloning. Foley synthesised; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.15,
    reaction_hold=0.6,  # the smile, held, to the cut
    end_card=0.0,
    font=SOFT.google_font(),
)
FIRST = 0.2  # typing from the first frame, her first word right after it
DROP = 0.6  # she sends, and her face drops
FALL = 0.55  # his face falls
SAG = 0.5  # both sag
LOOK = 0.55  # both look at the door
RISE = 0.6  # both get up
ARRIVE = 1.2  # they walk in from either side
HUG = 1.3  # the hug, and over each shoulder the smile goes
TILT = 0.6
SLIPPERS = 2.0  # the held bracket: four slippers
BACK = 0.45  # the camera comes back up


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the cuts get faster, then the long silent walk to the door."""
    outside = SAG + LOOK + RISE + ARRIVE + HUG + TILT + SLIPPERS + BACK
    gaps = [DROP, FALL, 0.3, 0.2, 0.15, 0.12, 0.16, outside, 0.2, 0.2]
    starts = [FIRST]
    for length, gap in zip(speech, gaps, strict=False):
        starts.append(starts[-1] + length + gap)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The silent stretch's beats, from the end of the last line indoors."""
    sag = t.phrases[7]["end"] + 0.1
    return {"sag_start": sag, "out_start": sag + SAG + LOOK + RISE, "camera_cuts": [{"time": 0, "angle": "split"}]}


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

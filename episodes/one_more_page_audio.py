#!/usr/bin/env python3
"""One More Page, a Soft sketch: generated dialogue, resolved by the engine, and the timeline.

    srstudio record one-more-page PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:data:`GAPS`). Pip is four, in a tie, with a case open on the quilt, and negotiates a bedtime with a man who is tired.
The deal is signed at eight; at 9:40 Bo falls asleep in the middle of the second story and Pip takes the win to the
kitchen. Will is Pip, and Eric is Bo. There is no music: the reel's foley is synthesised in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, beats, chain, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 31241
VOICES = {
    "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45)),
    "bo": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.5, similarity_boost=0.75, style=0.3)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("bo", "One story. Then lights out.", "One story.\nThen lights out.", 1.02),
    Spoken("pip", "Two stories, water, hall light.", "Two stories, water,\nhall light.", 1.05),
    Spoken("bo", "You're four.", "You're four.", 0.98),
    Spoken("pip", "And you're tired.", "And you're tired.", 0.95),
    Spoken("bo", "One story. And water.", "One story. And water.", 0.92, seed=SEED + 20),
    Spoken("pip", "You said that at eight.", "You said that at eight.", 1.0),
    Spoken("bo", "And the little bear... went... to...", "And the little bear...\nwent... to...", 0.78),
    Spoken("pip", "Pleasure doing business.", "Pleasure doing business.", 0.95),
]
START = 0.50  # the first word; the frame holds still until the line lands
SHAKE = 1.00  # the handshake, in close
CARD = 0.40  # 9:40 is on the screen before Bo reads
GAPS = (
    0.20,
    0.20,
    0.15,
    1.20,  # Bo looks at the clock
    0.20,
    0.30 + SHAKE + CARD,
    5.75,  # the book, two seconds of snoring, the wave, the tie, the quilt, the lamp
)
OUT = 2.20  # the walk, the door, the fridge
INTERVIEW = Interview(
    slug="one-more-page",
    title="One More Page",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Will and Eric; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=OUT,
    end_card=0.0,
    font=SOFT.google_font(),
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the deal, and then the two silences it was for."""
    return beats(speech, START, GAPS)


def extra(t: Timing) -> dict:
    """The beats the picture keys on."""
    p = t.phrases
    clock = p[3]["end"] + 0.15
    shake = p[5]["end"] + 0.30
    silent = chain(p[6]["end"], book=0.15, snore=0.55, wave=2.00, tie=1.05, quilt=0.75, click=0.85)
    return {
        **silent,
        "clock": clock,
        "shake": shake,
        "card": shake + SHAKE,
        "walk": p[7]["end"] + 0.10,
        "door": t.last_end + 1.20,
        "fridge": t.last_end + 1.65,
        "camera_cuts": [{"time": 0, "angle": "bed"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

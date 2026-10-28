#!/usr/bin/env python3
"""Episode 07 — Focus Mode: sung lines, a record scratch and the groove, all on one beat grid.

    python3 focus_mode_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline (engine-resolved lines and effect, speech-to-text check, placement on the beat, synthesised
groove) is :mod:`srstudio.song`; this file is the song.
"""

from __future__ import annotations

from srstudio.music import Groove, Section
from srstudio.song import Effect, Line, Singer, Song, main

GROOVE = Groove(bpm=120)  # one bar = 2 s
SONG = Song(
    slug="focus-mode",
    title="Focus Mode — Pip 01",
    seed=72026,
    groove=GROOVE,
    voices={"pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45))},
    lines=[
        Line("pip", "Okay. Sit down.", "Okay. SIT DOWN.", (0, 0.5)),
        Line("pip", "Time to do some work.", "Time to do some WORK", (1, 0)),
        Line("pip", "Typing, typing, typing!", "Typing, typing,\ntyping!", (2, 0), 1.08),
        Line("pip", "Wiggle, wiggle, wiggle!", "Wiggle, wiggle,\nwiggle!", (3, 0), 1.08),
        Line("pip", "Shake it to the beat!", "Shake it to the BEAT!", (4, 0)),
        Line("pip", "Hold on. The deadline.", "Hold on.\nThe DEADLINE.", (6, 0.5)),
        Line("pip", "Sit down. Focus.", "Sit down. FOCUS.", (7, 0), 0.95),
    ],
    sections=[
        Section(0, 6),  # the groove under the work and the dance
        Section(8, 9, parts=frozenset({"hat", "keys"})),  # bars 6–7 rest: the deadline; then it creeps back
        Section(9, 10),
    ],
    effects=[
        Effect(
            "record-scratch",
            "A single short vinyl record scratch that stops the music, dry, no voices, no music after it",
            seconds=1.0,
            longest=0.6,
            peak=0.5,
            at=(6, 0),
        )
    ],
    lines_end=GROOVE.at(8),
    voice_note="ElevenLabs premade voice Will; no reference-voice cloning. Music synthesised by srstudio.music.",
)


def extra(starts: dict[str, float]) -> dict:
    return {
        "scratch_start": starts["record-scratch"],
        "music_return_start": GROOVE.at(8),
        "camera_cuts": [{"time": 0, "angle": "wide"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

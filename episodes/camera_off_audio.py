#!/usr/bin/env python3
"""Episode 08 — Camera Off: Pip's sung lines, the boss on the call, two effects and the groove.

    python3 camera_off_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline (engine-resolved lines and effects, speech-to-text check, placement on the beat, synthesised
groove) is :mod:`_song`; this file is the song. Two voices: Pip sings, the boss talks from the laptop.
"""

from __future__ import annotations

from _song import Effect, Line, Song, Voice, main
from srstudio.music import Groove, Section

GROOVE = Groove(bpm=120)  # one bar = 2 s
MUZAK = frozenset({"hat", "keys"})
SONG = Song(
    slug="camera-off",
    title="Camera Off — Pip 02",
    seed=82026,
    groove=GROOVE,
    voices={
        "pip": Voice("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45)),
        "boss": Voice("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.15)),
    },
    lines=[
        Line("pip", "Camera on. Nod, nod, nod.", "Camera ON.\nNod, nod, NOD.", (0, 0.5)),
        Line("pip", "Very professional.", "Very PROFESSIONAL.", (1, 2)),
        Line("boss", "Next, all forty slides.", "BOSS: Next...\nall FORTY slides.", (2, 0.5), 0.95),
        Line("pip", "Camera off.", "Camera... OFF.", (3, 1)),
        Line("pip", "Pajamas on the beat!", "PAJAMAS\non the beat!", (4, 0)),
        Line("pip", "Nobody can see me!", "Nobody can\nSEE ME!", (5, 0)),
        Line("pip", "Best meeting ever!", "Best meeting\nEVER!", (7, 0)),
        Line("boss", "Pip, can you share your screen?", "BOSS: Pip, can you\nshare your SCREEN?", (8, 0.5)),
        Line("pip", "Yes! Totally!", "YES! Totally!", (9, 1)),
        Line("pip", "I was taking notes.", "I was taking...\nNOTES.", (10, 0)),
    ],
    sections=[
        Section(0, 3, parts=MUZAK),  # the meeting: polite hat and keys
        Section(4, 8),  # camera off: the whole groove
        Section(10, 12, parts=MUZAK),  # bars 8–9 rest: the boss asks; then back to polite
    ],
    effects=[
        Effect(
            "camera-click",
            "A single crisp computer mouse click, dry, close up, no other sounds",
            seconds=0.5,
            longest=0.25,
            peak=0.55,
            at=(3, 0.5),
        ),
        Effect(
            "call-chime",
            "A short bright two-note video call notification chime, dry, no voices, no music",
            seconds=1.0,
            longest=0.8,
            peak=0.5,
            at=(8, 0),
        ),
    ],
    lines_end=GROOVE.at(11, 2),
    voice_note="ElevenLabs premade voices Will (Pip) and Eric (boss); no reference-voice cloning. "
    "Music synthesised by srstudio.music.",
)


def extra(starts: dict[str, float]) -> dict:
    return {
        "click_start": starts["camera-click"],
        "chime_start": starts["call-chime"],
        "camera_cuts": [{"time": 0, "angle": "wide"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

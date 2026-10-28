#!/usr/bin/env python3
"""Episode 08 — Camera Off: Pip's song from the ElevenLabs Music API, the boss on the call, two effects.

    python3 camera_off_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.song`; this file is the song. Pip sings in the composed music (:data:`PLAN`,
pinned by its seed): the take must keep 120 bpm and every lyric must be heard, in order, inside its chunk, or
the build stops. The boss talks from the laptop over the two instrumental chunks, on his beats.
"""

from __future__ import annotations

from srstudio.compose import Chunk, Plan
from srstudio.music import Groove
from srstudio.song import Composition, Effect, Line, Singer, Song, main

GROOVE = Groove(bpm=120)  # one bar = 2 s
NEG = ("slow tempo", "rubato", "fade in", "spoken word")
VOCAL = "male tenor lead vocal sings every lyric, upfront and clear"
# Chunks of whole bars. The boss speaks only over the lyric-free chunks: a chunk with lyrics can be sung anywhere
# in it, and an inline "instrumental" direction was ignored in the takes we tried.
PLAN = Plan(
    (
        Chunk(
            "Camera On",
            4.0,
            (
                "120 BPM",
                "4/4",
                "playful office-pop jingle",
                VOCAL,
                "clear diction",
                "light hi-hat and electric piano",
                "cheeky and bright",
            ),
            ("Camera on. Nod, nod, nod.", "Very professional."),
            NEG,
        ),
        Chunk(
            "Forty Slides",
            4.0,
            ("120 BPM", "instrumental", "sparse muted hi-hat and soft electric piano", "tense pause"),
            (),
            NEG,
        ),
        Chunk(
            "Pajamas",
            8.0,
            ("120 BPM", "full groove drop", "funky slap bass", "tight claps on 2 and 4", "bright synth stabs", VOCAL),
            ("Camera off.", "Pajamas on the beat!", "Nobody can see me!", "Best meeting ever!"),
            NEG,
        ),
        Chunk(
            "Share Screen",
            4.0,
            ("120 BPM", "instrumental", "sudden drop to a muted kick and soft pads", "nervous"),
            (),
            NEG,
        ),
        Chunk(
            "Taking Notes",
            4.0,
            ("120 BPM", "groove returns, light and bright", VOCAL, "clear diction", "button ending on the last word"),
            ("Yes! Totally!", "I was taking notes."),
            NEG,
        ),
    )
)
SEED = 82043  # the take that passed the tempo and lyric checks (seeds 82031-82033 and 82041-82042 did not)
SONG = Song(
    slug="camera-off",
    title="Camera Off — Pip 02",
    seed=82026,
    groove=GROOVE,
    voices={"boss": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.15))},
    lines=[
        Line("pip", "Camera on. Nod, nod, nod.", "Camera ON.\nNod, nod, NOD.", None),
        Line("pip", "Very professional.", "Very PROFESSIONAL.", None),
        Line("boss", "Next, all forty slides.", "BOSS: Next...\nall FORTY slides.", (2, 0.5), 0.95),
        Line("pip", "Camera off.", "Camera... OFF.", None),
        Line("pip", "Pajamas on the beat!", "PAJAMAS\non the beat!", None),
        Line("pip", "Nobody can see me!", "Nobody can\nSEE ME!", None),
        Line("pip", "Best meeting ever!", "Best meeting\nEVER!", None),
        Line("boss", "Pip, can you share your screen?", "BOSS: Pip, can you\nshare your SCREEN?", (8, 0.5)),
        Line("pip", "Yes! Totally!", "YES! Totally!", None),
        Line("pip", "I was taking notes.", "I was taking...\nNOTES.", None),
    ],
    sections=[],
    composition=Composition(PLAN, seed=SEED, role="pip"),
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
    lines_end=PLAN.seconds,
    voice_note="Pip is sung by the ElevenLabs Music API (music_v2) in the composed song; the boss is the "
    "ElevenLabs premade voice Eric. No reference-voice cloning.",
)


def extra(starts: dict[str, float]) -> dict:
    return {
        "click_start": starts["camera-click"],
        "chime_start": starts["call-chime"],
        "camera_cuts": [{"time": 0, "angle": "wide"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

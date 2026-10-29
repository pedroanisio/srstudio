#!/usr/bin/env python3
"""Episode 15 — Return to Office: composed instrumental music from the ElevenLabs Music API, Pip's and Bo's lines and
six effects.

    python3 return_to_office_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.song`; this file is the song. Day one of the return to office: Pip (the premade voice
Will) has commuted two hours to an empty meeting room, and Bo (Eric) welcomes the team back on the wall screen, from
a beach. The music is instrumental (a take in which words are heard is refused) at 120 bpm: office-pop for the
welcome, a steel-drum groove for Bali, a held pad for the hold before the punchline, and almost nothing for the
motion-sensor lights.
"""

from __future__ import annotations

from srstudio.compose import Chunk, Plan
from srstudio.music import Groove
from srstudio.song import Composition, Effect, Line, Singer, Song, main

GROOVE = Groove(bpm=120)  # one bar = 2 s
NEG = ("slow tempo", "rubato", "fade in", "vocals", "singing", "spoken word")
BASE = ("120 BPM", "4/4", "instrumental", "steady kick on every beat")
PLAN = Plan(
    (
        Chunk("Commute", 4.0, (*BASE, "upbeat corporate office-pop", "bright synth stabs"), (), NEG),
        Chunk("Welcome Back", 4.0, (*BASE, "the same office-pop groove", "hand claps", "a little smug"), (), NEG),
        Chunk("Wave", 4.0, (*BASE, "the office-pop groove thins out", "muted plucks"), (), NEG),
        Chunk("Bali", 4.0, (*BASE, "sunny tropical steel drum vacation groove", "ukulele"), (), NEG),
        Chunk("Culture", 4.0, (*BASE, "almost silent", "a single held low synth pad", "very soft kick"), (), NEG),
        Chunk("Lights", 8.0, (*BASE, "minimal and sparse", "only a soft kick and a ticking hi-hat"), (), NEG),
    )
)
SEED = 15101
PIP = Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.35, similarity_boost=0.75, style=0.40))
BO = Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.50, similarity_boost=0.75, style=0.30))
LIGHT_OFF = (
    "A big office light switching off with a single relay clunk and a short fluorescent hum dying, no voices, no music"
)
LINES = [
    Line("pip", "Two hours on a train. For this?", "Two hours on a train.\nFor THIS?", (0, 0.5)),
    Line("bo", "Welcome back, team! Feel that energy?", "Welcome back, team!\nFeel that ENERGY?", (1, 2)),
    Line("pip", "I'm the only one here.", "I'm the only one here.", (3, 0)),
    Line("bo", "And we can all see you. Wave!", "And we can all see you.\nWAVE!", (3, 3)),
    Line("pip", "Where are you?", "Where are you?", (5, 2)),
    Line("bo", "Bali. Leadership is hybrid.", "Bali.\nLeadership is hybrid.", (6, 1)),
    Line("pip", "So why am I here?", "So why am I here?", (7, 2)),
    Line("bo", "Someone has to be the culture.", "Someone has to be\nthe CULTURE.", (8, 3)),
    Line("bo", "Same time tomorrow! In person!", "Same time tomorrow!\nIn PERSON!", (10, 0)),
]
SONG = Song(
    slug="return-to-office",
    title="Return to Office — Comedy Cut 15",
    seed=15100,
    groove=GROOVE,
    voices={"pip": PIP, "bo": BO},
    lines=LINES,
    sections=[],
    composition=Composition(PLAN, seed=SEED, role=None),
    effects=[
        Effect(
            "call-join",
            "A short bright video call joining chime, two rising notes, dry, no voices, no music",
            seconds=1.0,
            longest=0.7,
            peak=0.5,
            at=(1, 0),
        ),
        Effect(
            "seagull",
            "A single seagull call on a sunny beach, close, short, no voices, no music",
            seconds=1.2,
            longest=0.9,
            peak=0.45,
            at=(6, 0),
        ),
        Effect(
            "call-end",
            "A short video call ending tone, two falling notes, dry, no voices, no music",
            seconds=1.0,
            longest=0.7,
            peak=0.5,
            at=(11, 0),
        ),
        Effect("lights-off", LIGHT_OFF, seconds=1.0, longest=0.8, peak=0.5, at=(11, 2)),
        Effect(
            "lights-on",
            "A big office light switching on with a single relay clunk and a fluorescent tube flicker, no voices, "
            "no music",
            seconds=1.0,
            longest=0.8,
            peak=0.5,
            at=(12, 1),
        ),
        Effect("lights-off-2", LIGHT_OFF, seconds=1.0, longest=0.8, peak=0.5, at=(13, 0)),
    ],
    lines_end=PLAN.seconds,
    voice_note="Pip is the ElevenLabs premade voice Will and Bo is Eric; the music is composed by the ElevenLabs "
    "Music API (music_v2), instrumental. No reference-voice cloning.",
)


def extra(starts: dict[str, float]) -> dict:
    return {
        "join_start": starts["call-join"],
        "seagull_start": starts["seagull"],
        "call_end_start": starts["call-end"],
        "dark_start": starts["lights-off"],
        "light_start": starts["lights-on"],
        "dark2_start": starts["lights-off-2"],
        "camera_cuts": [{"time": 0, "angle": "wide"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

#!/usr/bin/env python3
"""Episode 13 — Unlimited PTO: composed instrumental music from the ElevenLabs Music API, Bo's and Pip's lines and
four effects.

    python3 unlimited_pto_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.song`; this file is the song. A one-on-one in the meeting room: Bo (the premade voice
Eric, the boss of *Camera Off*) announces unlimited time off, and Pip (Will) asks for less and less of it. The
music is instrumental (a take in which words are heard is refused) at 120 bpm: office-pop while Bo sells it, a
held pad for the hold before the punchline, and a steel-drum vacation groove for the button.
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
        Chunk("Big News", 4.0, (*BASE, "upbeat corporate office-pop", "bright synth stabs", "hand claps"), (), NEG),
        Chunk("Friday", 4.0, (*BASE, "the same office-pop groove, a little smug"), (), NEG),
        Chunk("Afternoon", 4.0, (*BASE, "the office-pop groove thins out", "muted plucks"), (), NEG),
        Chunk("Lunch", 4.0, (*BASE, "the office-pop groove, only kick and a ticking hi-hat"), (), NEG),
        Chunk("How Many", 4.0, (*BASE, "almost silent", "a single held low synth pad", "very soft kick"), (), NEG),
        Chunk("Bali", 4.0, (*BASE, "sunny tropical steel drum vacation groove", "ukulele", "button ending"), (), NEG),
    )
)
SEED = 13101
BO = Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.50, similarity_boost=0.75, style=0.30))
PIP = Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.35, similarity_boost=0.75, style=0.40))
DECLINE = "A short soft user-interface rejection blip, two quick descending notes, dry, no voices, no music"
LINES = [
    Line("bo", "Who wants unlimited vacation?", "Who wants\nUNLIMITED vacation?", (0, 0.5)),
    Line("pip", "Me! Friday?", "Me! Friday?", (1, 2)),
    Line("bo", "During Q4? Brave.", "During Q4?\nBrave.", (2, 2)),
    Line("pip", "Friday afternoon?", "Friday afternoon?", (3, 2)),
    Line("bo", "Optics.", "Optics.", (4, 2)),
    Line("pip", "Lunch?", "Lunch?", (5, 1)),
    Line("bo", "Let's eat at our desks. As a family.", "Let's eat at our desks.\nAs a FAMILY.", (5, 3)),
    Line("pip", "So how many days is unlimited?", "So how many days\nis unlimited?", (7, 1)),
    Line("bo", "Unlimited. That's why nobody needs one.", "Unlimited. That's why\nNOBODY needs one.", (8, 3)),
    Line("bo", "Anyway! See you in December.", "Anyway!\nSee you in DECEMBER.", (10, 1)),
]
SONG = Song(
    slug="unlimited-pto",
    title="Unlimited PTO — Comedy Cut 13",
    seed=13100,
    groove=GROOVE,
    voices={"bo": BO, "pip": PIP},
    lines=LINES,
    sections=[],
    composition=Composition(PLAN, seed=SEED, role=None),
    effects=[
        Effect("decline-1", DECLINE, seconds=0.8, longest=0.5, peak=0.5, at=(2, 1)),
        Effect("decline-2", DECLINE, seconds=0.8, longest=0.5, peak=0.5, at=(4, 1)),
        Effect("decline-3", DECLINE, seconds=0.8, longest=0.5, peak=0.5, at=(5, 2.5)),
        Effect(
            "approved",
            "A bright cheerful two-note approval chime, like a request being approved in an app, dry, no voices, "
            "no music",
            seconds=1.0,
            longest=0.8,
            peak=0.55,
            at=(10, 0),
        ),
    ],
    lines_end=PLAN.seconds,
    voice_note="Bo is the ElevenLabs premade voice Eric and Pip is Will; the music is composed by the ElevenLabs "
    "Music API (music_v2), instrumental. No reference-voice cloning.",
)


def extra(starts: dict[str, float]) -> dict:
    return {
        "decline1_start": starts["decline-1"],
        "decline2_start": starts["decline-2"],
        "decline3_start": starts["decline-3"],
        "approved_start": starts["approved"],
        "camera_cuts": [{"time": 0, "angle": "wide"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

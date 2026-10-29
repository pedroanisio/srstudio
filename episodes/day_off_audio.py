#!/usr/bin/env python3
"""Pip 04 — Day Off: composed instrumental music from the ElevenLabs Music API, Pip's lines and three effects.

    python3 day_off_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.song`; this file is the song. Saturday on the sofa: the music is instrumental (a take
in which words are heard is refused) and keeps 120 bpm, and Pip (the premade voice Will) speaks each line on its
beat, heard by speech-to-text as written. Sung lyrics were tried first: in eleven takes the model blurred a word in
a different line each time ("study babe" for "Saturday", "tucking" for "typing"), so the words are spoken.
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
        Chunk("Saturday", 4.0, (*BASE, "lazy lo-fi weekend groove", "warm electric piano"), (), NEG),
        Chunk("Air Typing", 4.0, (*BASE, "the same groove", "a nervous ticking hi-hat creeps in"), (), NEG),
        Chunk("Lamp", 4.0, (*BASE, "upbeat corporate office-pop", "bright synth stabs"), (), NEG),
        Chunk("Any Time", 4.0, (*BASE, "back to the lazy groove, a little too insistent"), (), NEG),
        Chunk("Sofa Meeting", 4.0, (*BASE, "the groove melts into soft dreamy pads", "very calm"), (), NEG),
        Chunk("Running Over", 4.0, (*BASE, "frantic office-pop, fast hi-hats", "button ending"), (), NEG),
    )
)
SEED = 93101
PIP = Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45))
SONG = Song(
    slug="day-off",
    title="Day Off — Pip 04",
    seed=93100,
    groove=GROOVE,
    voices={"pip": PIP},
    lines=[
        Line("pip", "Saturday. No work. Just me.", "Saturday.\nNo work. Just ME.", (0, 0.5)),
        Line("pip", "My hands are typing on nothing.", "My hands are typing...\non NOTHING.", (2, 0)),
        Line("pip", "Yes, totally. Great point, Mister Lamp.", "Yes, totally.\nGreat point, MISTER LAMP.", (4, 0)),
        Line("pip", "I can stop. I can stop anytime.", "I can stop.\nI can stop ANYTIME.", (6, 0)),
        Line("pip", "Booked a meeting with the sofa.", "Booked a meeting\nwith the SOFA.", (8, 1)),
        Line("pip", "Running over! Sorry, sofa!", "Running over!\nSORRY, SOFA!", (10, 1)),
    ],
    sections=[],
    composition=Composition(PLAN, seed=SEED, role=None),
    effects=[
        Effect(
            "calendar-ping",
            "A short soft calendar invite notification ping, single note, dry, no voices, no music",
            seconds=1.0,
            longest=0.7,
            peak=0.5,
            at=(8, 0),
        ),
        Effect(
            "meeting-ended",
            "A short descending two-note video call ended chime, dry, no voices, no music",
            seconds=1.0,
            longest=0.8,
            peak=0.55,
            at=(10, 0),
        ),
        Effect(
            "tap",
            "A single soft fingertip tap on a phone screen, dry, close up, no other sounds",
            seconds=0.5,
            longest=0.25,
            peak=0.5,
            at=(11, 2),
        ),
    ],
    lines_end=PLAN.seconds,
    voice_note="Pip is the ElevenLabs premade voice Will; the music is composed by the ElevenLabs Music API "
    "(music_v2), instrumental. No reference-voice cloning.",
)


def extra(starts: dict[str, float]) -> dict:
    return {
        "ping_start": starts["calendar-ping"],
        "ended_start": starts["meeting-ended"],
        "tap_start": starts["tap"],
        "camera_cuts": [{"time": 0, "angle": "wide"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

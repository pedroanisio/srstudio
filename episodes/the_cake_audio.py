#!/usr/bin/env python3
"""Episode 19 — The Cake: composed instrumental music from the ElevenLabs Music API, three voices and three effects.

    python3 the_cake_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.song`; this file is the song. In the break room Juno (the premade voice Laura) collects
ten bucks from Pip (Will) for a cake: not a birthday, someone is leaving. Bo (Eric) arrives with it, delighted: the
company saved a whole salary. The cake says WE'LL MISS YOU; Pip finds that sweet. Bo turns the cake round: BYE PIP.
Pip paid for it; Bo thanks him for the team spirit; it is vanilla, budget cuts; Juno asks for his chair. The music is
instrumental at 120 bpm: an office-party groove, a held pad for the pause before the cake turns, and a cheerful outro.
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
        Chunk("Collection", 8.0, (*BASE, "light office sitcom groove", "pizzicato strings", "muted guitar"), (), NEG),
        Chunk("Party", 6.0, (*BASE, "cheesy office party groove", "bright brass stabs", "hand claps"), (), NEG),
        Chunk("Hold", 4.0, (*BASE, "almost silent", "a single held warm pad", "very soft kick"), (), NEG),
        Chunk("Fallout", 8.0, (*BASE, "the office party groove, deflated", "lonely kazoo melody"), (), NEG),
        Chunk(
            "Outro", 6.0, (*BASE, "the office sitcom groove returns", "pizzicato strings", "warm and silly"), (), NEG
        ),
    )
)
SEED = 19101
JUNO = Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.35, similarity_boost=0.75, style=0.45))
PIP = Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45))
BO = Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.50, similarity_boost=0.75, style=0.30))
FRONT = "WE'LL MISS\nYOU"  # the cake's lettering, front and back
BACK = "BYE PIP"
LINES = [
    Line("juno", "Pip! Ten bucks for the cake?", "JUNO: Pip! Ten bucks\nfor the CAKE?", (0, 0.5)),
    Line("pip", "Sure! Whose birthday?", "PIP: Sure!\nWhose birthday?", (1, 2)),
    Line("juno", "Not a birthday. Someone's leaving.", "JUNO: Not a birthday.\nSomeone's LEAVING.", (2, 2)),
    Line("pip", "Oh no. Who?", "PIP: Oh no. Who?", (3, 3)),
    Line("bo", "Surprise! We saved a whole salary!", "BO: Surprise! We saved\na whole SALARY!", (5, 0)),
    Line("pip", "We'll miss you? That's so sweet.", "PIP: \"We'll miss you\"?\nThat's so SWEET.", (6, 1)),
    Line("pip", "I paid ten bucks for this?", "PIP: I paid TEN BUCKS\nfor this?", (9, 1)),
    Line("bo", "And we thank you. That's team spirit.", "BO: And we thank you.\nThat's TEAM SPIRIT.", (10, 2)),
    Line("pip", "Is it at least chocolate?", "PIP: Is it at least\nchocolate?", (12, 0)),
    Line("bo", "Vanilla. Budget cuts.", "BO: Vanilla.\nBudget cuts.", (13, 0)),
    Line("juno", "Can I have his chair?", "JUNO: Can I have\nhis CHAIR?", (14, 0)),
]
SONG = Song(
    slug="the-cake",
    title="The Cake — Comedy Cut 19",
    seed=19100,
    groove=GROOVE,
    voices={"juno": JUNO, "pip": PIP, "bo": BO},
    lines=LINES,
    sections=[],
    composition=Composition(PLAN, seed=SEED, role=None),
    effects=[
        Effect(
            "party-horn",
            "A single short party blower horn toot, paper unrolling, dry, no voices, no music",
            seconds=1.0,
            longest=0.8,
            peak=0.5,
            at=(4, 1),
        ),
        Effect(
            "turn",
            "A ceramic cake plate turned on a stone counter, a short scrape, dry, no voices, no music",
            seconds=0.8,
            longest=0.6,
            peak=0.45,
            at=(8, 0),
        ),
        Effect(
            "sting",
            "A comedy sad trombone, wah wah wah waaah, descending, dry, no voices",
            seconds=2.0,
            longest=1.9,
            peak=0.5,
            at=(8, 1),
        ),
    ],
    lines_end=PLAN.seconds,
    voice_note="Juno is the ElevenLabs premade voice Laura, Pip is Will and Bo is Eric; the music is composed by the "
    "ElevenLabs Music API (music_v2), instrumental. No reference-voice cloning.",
)


def extra(starts: dict[str, float]) -> dict:
    return {
        "horn_start": starts["party-horn"],
        "turn_start": starts["turn"],
        "sting_start": starts["sting"],
        "camera_cuts": [{"time": 0, "angle": "wide"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

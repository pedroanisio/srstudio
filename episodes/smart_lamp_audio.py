#!/usr/bin/env python3
"""Episode 17 — Smart Lamp: composed instrumental music from the ElevenLabs Music API, three voices and four effects.

    python3 smart_lamp_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.song`; this file is the song. At home, Juno (the premade voice Laura) tells Pip (Will)
he never listens, and the smart floor lamp (Matilda) agrees: it has recordings. It orders flowers with a card that
says sorry, then a ring. Pip cancels the ring; the lamp says she said yes. Who is she marrying? The lamp did not catch
that. The music is instrumental at 120 bpm: a domestic sitcom groove, a shopping-channel bounce for the orders, a
held pad for the hold before the punchline, and a soft outro.
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
        Chunk("Argument", 6.0, (*BASE, "light sitcom funk", "slap bass", "a little tense"), (), NEG),
        Chunk("Recordings", 6.0, (*BASE, "the sitcom funk groove", "a smug synth arpeggio"), (), NEG),
        Chunk("Shopping", 8.0, (*BASE, "bouncy shopping-channel jingle groove", "bright marimba"), (), NEG),
        Chunk("Proposal", 4.0, (*BASE, "almost silent", "a single held warm pad", "very soft kick"), (), NEG),
        Chunk("Outro", 6.0, (*BASE, "the sitcom funk groove returns", "warm and silly", "hand claps"), (), NEG),
    )
)
SEED = 17101
JUNO = Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.35, similarity_boost=0.75, style=0.45))
PIP = Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45))
LAMP = Singer("XrExE9yKIg1WjnnlVkGX", "Matilda", dict(stability=0.75, similarity_boost=0.75, style=0.05))
LINES = [
    Line("juno", "You never listen to me.", "JUNO: You never\nLISTEN to me.", (0, 0.5)),
    Line("pip", "I always listen!", "PIP: I ALWAYS listen!", (1, 2)),
    Line("lamp", "He doesn't. I have recordings.", "LAMP: He doesn't.\nI have RECORDINGS.", (2, 2)),
    Line("pip", "Nobody asked you!", "PIP: Nobody asked you!", (4, 0)),
    Line("juno", "See? It gets me.", "JUNO: See?\nIt GETS me.", (5, 0)),
    Line(
        "lamp",
        "I've ordered flowers. The card says sorry.",
        "LAMP: I've ordered flowers.\nThe card says SORRY.",
        (6, 0),
    ),
    Line("pip", "I'm not sorry!", "PIP: I'm NOT sorry!", (7, 2)),
    Line("lamp", "And a ring.", "LAMP: And a RING.", (8, 1)),
    Line("pip", "Cancel the ring!", "PIP: CANCEL the ring!", (9, 0)),
    Line("lamp", "She said yes.", "LAMP: She said YES.", (10, 2)),
    Line("juno", "Yes!", "JUNO: YES!", (11, 1)),
    Line("pip", "Who is she marrying?", "PIP: Who is she\nMARRYING?", (12, 0)),
    Line("lamp", "Sorry, I didn't catch that.", "LAMP: Sorry,\nI didn't catch that.", (13, 0)),
]
ORDER = "A short cheerful online order confirmation chime, two bright notes, dry, no voices, no music"
SONG = Song(
    slug="smart-lamp",
    title="Smart Lamp — Comedy Cut 17",
    seed=17100,
    groove=GROOVE,
    voices={"juno": JUNO, "pip": PIP, "lamp": LAMP},
    lines=LINES,
    sections=[],
    composition=Composition(PLAN, seed=SEED, role=None),
    effects=[
        Effect(
            "wake",
            "A smart speaker wake-up tone, a soft rising electronic blip, dry, no voices, no music",
            seconds=1.0,
            longest=0.6,
            peak=0.5,
            at=(2, 1),
        ),
        Effect("order-flowers", ORDER, seconds=1.0, longest=0.7, peak=0.5, at=(7, 1)),
        Effect("order-ring", ORDER, seconds=1.0, longest=0.7, peak=0.5, at=(8, 3)),
        Effect(
            "not-understood",
            "A smart speaker error tone, a short low two-note descending bloop, dry, no voices, no music",
            seconds=1.0,
            longest=0.7,
            peak=0.5,
            at=(14, 0),
        ),
    ],
    lines_end=PLAN.seconds,
    voice_note="Juno is the ElevenLabs premade voice Laura, Pip is Will and the lamp is Matilda; the music is composed "
    "by the ElevenLabs Music API (music_v2), instrumental. No reference-voice cloning.",
)


def extra(starts: dict[str, float]) -> dict:
    return {
        "wake_start": starts["wake"],
        "flowers_start": starts["order-flowers"],
        "ring_start": starts["order-ring"],
        "error_start": starts["not-understood"],
        "camera_cuts": [{"time": 0, "angle": "wide"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

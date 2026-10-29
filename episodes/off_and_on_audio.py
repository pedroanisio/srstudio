#!/usr/bin/env python3
"""Episode 10 — Off and On: Remy's jingle from the ElevenLabs Music API, three spoken voices, five effects.

    python3 off_and_on_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.song`; this file is the song. Remy sings his one fix as an infomercial jingle in
the composed music (:data:`PLAN`, pinned by its seed): the take must keep 120 bpm and every lyric must be heard,
in order, inside its chunk, or the build stops. The refrain climbs from the machine to the lights to Remy himself.
Juno, Pip and the IT hotline speak over the instrumental chunks, on their beats; the hotline's hold music is a
chunk of its own.
"""

from __future__ import annotations

from srstudio.compose import Chunk, Plan
from srstudio.music import Groove
from srstudio.song import Composition, Effect, Line, Singer, Song, main

GROOVE = Groove(bpm=120)  # one bar = 2 s
NEG = ("slow tempo", "rubato", "fade in", "spoken word", "sad")
VOCAL = "cheesy male tenor lead vocal sings the lyric once, upfront and clear, clear diction"
JINGLE = ("120 BPM", "4/4", "cheesy 80s TV infomercial jingle", "bright synth brass stabs", "slap bass", VOCAL)
# No two refrains share three words in a row: the model folds look-alike lyrics into one hook (every seed tried
# sang "Turn it off" for "Turn him off" and for "Turn Pip off"). It sings each on the second bar of its chunk.
REFRAINS = ("Turn it off and on again!", "Lights off! Lights on!", "Somebody reboot me!")
# Two-bar chunks. The voices speak only over the lyric-free chunks: a chunk with lyrics can be sung anywhere in it.
PLAN = Plan(
    (
        Chunk("Broken", 4.0, ("120 BPM", "4/4", "instrumental", "light office funk", "muted guitar and bass"), (), NEG),
        Chunk("Fix It", 4.0, JINGLE, (REFRAINS[0],), NEG),
        Chunk("Monday", 4.0, ("120 BPM", "instrumental", "the same funk, sparse and droopy", "muted bass"), (), NEG),
        Chunk("Fix Him", 4.0, JINGLE, (REFRAINS[1],), NEG),
        Chunk("Reboot", 4.0, ("120 BPM", "instrumental", "stiff robotic 8-bit bleeps", "square wave bass"), (), NEG),
        Chunk("Hotline", 4.0, ("120 BPM", "instrumental", "telephone hold music", "cheap bossa nova organ"), (), NEG),
        Chunk(
            "Fix Me", 6.0, (*JINGLE, "big gospel choir backing", "button ending on the last word"), (REFRAINS[2],), NEG
        ),
    )
)
SEED = 102033  # the take that passed the tempo and lyric checks (102031-102032 and 102034-102035 did not)
CUTS = (  # (bar, beat) -> angle: who is on screen from that beat
    ((0, 0), "break"),
    ((1, 2), "meeting"),
    ((4, 0), "break"),
    ((6, 0), "meeting"),
    ((7, 1), "dark"),  # on the sung "off"
    ((7, 3), "break"),  # on the sung "on"
    ((9, 2.5), "meeting"),
)
SONG = Song(
    slug="off-and-on",
    title="Off and On — Pip 03",
    seed=102026,
    groove=GROOVE,
    voices={
        "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.35, similarity_boost=0.75, style=0.45)),
        "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45)),
        "robot": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=1.0, similarity_boost=0.75, style=0.0)),
        "hotline": Singer("IKne3meq5aSn9XLyUdCD", "Charlie", dict(stability=0.70, similarity_boost=0.75, style=0.10)),
    },
    lines=[
        Line(
            "juno", "Remy! The coffee machine is broken!", "JUNO: Remy! The coffee\nmachine is BROKEN!", (0, 0.5), 1.1
        ),
        Line("remy", REFRAINS[0], "REMY: Turn it OFF\nand ON again!", None),
        Line("pip", "It's Monday. I'm broken.", "PIP: It's Monday.\nI'm BROKEN.", (5, 0)),
        Line("remy", REFRAINS[1], "REMY: Lights OFF!\nLights ON!", None),
        Line("robot", "Hello. I love Mondays.", "PIP: Hello.\nI LOVE Mondays.", (8, 2), 0.85),
        Line(
            "hotline",
            "Have you tried turning it off and on again?",
            "IT HOTLINE: Have you tried\nturning it off and on again?",
            (10, 0.5),
            1.1,
        ),
        Line("remy", REFRAINS[2], "REMY: Somebody\nREBOOT ME!", None),
    ],
    sections=[],
    composition=Composition(PLAN, seed=SEED, role="remy"),
    effects=[
        Effect(
            "machine-reset",
            "Two quick plastic power button clicks on a kitchen appliance, off then on, dry, no voices, no music",
            seconds=0.8,
            longest=0.6,
            peak=0.5,
            at=(4, 0.5),
        ),
        Effect(
            "coffee-brew",
            "A coffee machine gurgles and pours a short stream into a mug, dry, no voices, no music",
            seconds=1.0,
            longest=0.9,
            peak=0.45,
            at=(4, 1.5),
        ),
        Effect(
            "lights-off",
            "A loud clack of a wall light switch flipped off, then a short descending power-down whine, dry, no music",
            seconds=0.8,
            longest=0.7,
            peak=0.55,
            at=(7, 1),
        ),
        Effect(
            "lights-on",
            "A single heavy wall light switch flicked on with a bright fluorescent ping, dry, no voices, no music",
            seconds=0.8,
            longest=0.7,
            peak=0.55,
            at=(7, 3),
        ),
        Effect(
            "screen-dies",
            "A computer monitor switching off with a falling electronic whine and a tiny pop, dry, no music",
            seconds=1.0,
            longest=0.6,
            peak=0.5,
            at=(9, 3),
        ),
        Effect(
            "startup-chime",
            "A short bright cheerful computer startup chime, one warm major chord, dry, no voices",
            seconds=1.5,
            longest=1.2,
            peak=0.5,
            at=(14, 2),
        ),
    ],
    lines_end=PLAN.seconds,
    voice_note="Remy is sung by the ElevenLabs Music API (music_v2) in the composed jingle; Juno is the ElevenLabs "
    "premade voice Laura, Pip is Will (flat and slow once rebooted) and the IT hotline is Charlie. No "
    "reference-voice cloning.",
)


def extra(starts: dict[str, float]) -> dict:
    return {
        "reset_start": starts["machine-reset"],
        "brew_start": starts["coffee-brew"],
        "dark_start": starts["lights-off"],
        "light_start": starts["lights-on"],
        "screen_dies_start": starts["screen-dies"],
        "startup_start": starts["startup-chime"],
        "camera_cuts": [{"time": GROOVE.at(*at), "angle": angle} for at, angle in CUTS],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

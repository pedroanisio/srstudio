#!/usr/bin/env python3
"""Episode 07 — Focus Mode: spoken lines, a record scratch and composed music, all on one beat grid.

    python3 focus_mode_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline (engine-resolved lines and effect, speech-to-text check, placement on the beat, the composed song
verified for length and tempo, and heard to be instrumental) is :mod:`srstudio.song`; this file is the song.
The music is the ElevenLabs Music API's (:data:`PLAN`, pinned by :data:`MUSIC_SEED`). It is not trusted to stop:
:func:`music_spans` plays it only in :data:`PLAYS`, so bars 6–8 (the scratch, the deadline, the punchline) are
silent whatever the take holds there, and the drop returns on bar 9.
"""

from __future__ import annotations

import math

from srstudio.compose import Chunk, Plan
from srstudio.music import Groove
from srstudio.song import Composition, Effect, Line, Singer, Song, SongError, main

GROOVE = Groove(bpm=120)  # one bar = 2 s
BARS = 12
PLAYS = ((0, 6), (9, BARS))  # bars the music is heard in: the work and the dance, then the drop to the end
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "slow tempo", "rubato", "fade in")
PLAN = Plan(
    (
        Chunk(
            "Groove",
            GROOVE.at(6),
            (
                "120 BPM",
                "4/4",
                "instrumental",
                "playful lo-fi office funk",
                "tight kick on every beat",
                "clean electric piano chords",
                "bouncy slap bass",
                "cheeky and light",
            ),  # fmt: skip
            (),
            NEG,
        ),
        Chunk("Break", GROOVE.at(9) - GROOVE.at(6), ("120 BPM", "instrumental", "sparse muted hi-hat only"), (), NEG),
        Chunk(
            "Drop",
            GROOVE.at(BARS) - GROOVE.at(9),
            (
                "120 BPM",
                "4/4",
                "instrumental",
                "full funk drop, bigger than before",
                "bright brass stabs",
                "slap bass",
                "four-on-the-floor kick",
                "ends on one final brass hit on the last beat",
            ),  # fmt: skip
            (),
            NEG,
        ),
    )
)
MUSIC_SEED = 72071
MUSIC_GAIN = -8.0  # under the voice
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
        Line("pip", "Wait. It was yesterday.", "Wait...\nit was YESTERDAY.", (8, 0)),
        Line("pip", "Shake it to the beat!", "SHAKE IT\nto the beat!", (9, 0)),
    ],
    sections=[],
    composition=Composition(PLAN, seed=MUSIC_SEED, role=None),
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
    lines_end=GROOVE.at(11),
    voice_note="ElevenLabs premade voice Will; no reference-voice cloning. Instrumental music composed with "
    "the ElevenLabs Music API (music_v2).",
)


def music_spans(phase: float, duration: float) -> list[tuple[float, float, float]]:
    """``(start, clip_in, clip_out)`` of each part of the song that is heard (:data:`PLAYS`), its beats on the grid.

    ``phase`` is the measured time of the song's first beat, modulo one beat: up to half a beat the song is
    entered that much late, past it the song starts that much before the next beat."""
    beat = GROOVE.beat
    if not (math.isfinite(phase) and 0 <= phase < beat) or not (math.isfinite(duration) and duration > 0):
        raise SongError(f"music phase {phase!r} must lie in 0..{beat} s and duration {duration!r} be positive")
    shift = phase if phase <= beat / 2 else phase - beat
    spans = []
    for first, last in PLAYS:
        start, clip_in, clip_out = GROOVE.at(first), GROOVE.at(first) + shift, min(GROOVE.at(last) + shift, duration)
        if clip_in < 0:
            start, clip_in = start - clip_in, 0.0
        if clip_out <= clip_in:
            raise SongError(f"the song ({duration:.3f} s) ends before bar {first}")
        spans.append((round(start, 6), round(clip_in, 6), round(clip_out, 6)))
    return spans


def extra(starts: dict[str, float]) -> dict:
    return {
        "scratch_start": starts["record-scratch"],
        "music_return_start": GROOVE.at(9),
        "camera_cuts": [{"time": 0, "angle": "wide"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(SONG, extra))

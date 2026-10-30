#!/usr/bin/env python3
"""Out of Cyan: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record out-of-cyan PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, its effects, where the whirs, the
pages and the card reader's beeps sit between the lines (:func:`schedule`) and its cuts (:func:`extra`). Rosa wants one
black page. The printer wants cyan, holds the page to ransom in cut-out letters, refuses the cartridge she bought, and
sends a photo. The printer never speaks: its side of the talk is on the pages. Its first second is held still (arm A of
the ``sp-hook_motion`` test). Rosa is Lily, as in *Neighbor Names*. Only Rosa speaks. The repeated effects share one
prompt and seed, so each is one request.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 26051
VOICES = {"rosa": Singer("pFZP5JQG7iQjIQuC4Bku", "Lily", dict(stability=0.50, similarity_boost=0.75, style=0.25))}
SCRIPT = [  # role, text, caption, speed
    Spoken("rosa", "It's black and white.", "It's black and white.", 1.00),
    Spoken("rosa", "I beg your pardon?", "I beg your pardon?", 1.00),
    Spoken("rosa", "$64.", "Sixty-four dollars.", 1.00),  # written as the recogniser hears it
    Spoken("rosa", "It's blue, dear.", "It's blue, dear.", 1.00),  # "cyan" comes back as "Khan"
    Spoken("rosa", "Don't hurt it.", "Don't hurt it.", 0.90),
]
WHIR = (
    "A small home inkjet printer working: the print head rattling back and forth and paper feeding, close, "
    "mechanical, no voices, no music"
)
PAID = "A card payment terminal's short approval beep, one clean electronic tone, no voices, no music"
HIT = "A single low dramatic thud, one deep impact, short, no melody, no voices, no music"
CLICK = "A small plastic ink cartridge clicking firmly into a printer, one click, close, no voices, no music"
LENGTHS = {1: 0.95, 2: 0.75, 3: 0.75, 4: 0.75, 5: 1.70}  # seconds of whir before each page lands


def _whir(n: int) -> Sound:
    return Sound(f"whir-{n}", WHIR, 3.0, LENGTHS[n], 0.30, seed=SEED + 1)


EFFECTS = [
    Sound(
        "beep",
        "A flat low two-tone electronic error beep from a home printer, short, close, no voices, no music",
        0.8,
        0.5,
        0.26,
        seed=SEED + 2,
    ),
    *[_whir(n) for n in LENGTHS],
    Sound("hit-1", HIT, 1.0, 0.8, 0.34, seed=SEED + 3),
    Sound("hit-2", HIT, 1.0, 0.8, 0.34, seed=SEED + 3),
    Sound("paid-1", PAID, 0.6, 0.45, 0.26, seed=SEED + 4),
    Sound("paid-2", PAID, 0.6, 0.45, 0.26, seed=SEED + 4),
    Sound("paid-3", PAID, 0.6, 0.45, 0.26, seed=SEED + 4),
    Sound("click-1", CLICK, 0.6, 0.4, 0.28, seed=SEED + 5),
    Sound("click-2", CLICK, 0.6, 0.4, 0.28, seed=SEED + 5),
]
STILL = 1.05  # the held first second: nothing moves, and the error beep ends it
PAGE_HOLD = (1.75, 1.60, 1.30, 1.25)  # how long each ransom page stays up before anything else happens
READER = 0.25  # into a card-reader shot before its beep
PAID_HOLD = 0.85  # the beep, then the bag and the price on screen
LAST_PAID = 0.55  # after "Don't hurt it.": the photo, then the third payment
CYAN_HOLD = 1.45  # the page itself
INTERVIEW = Interview(
    slug="out-of-cyan",
    title="Out of Cyan",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voice Lily; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=LAST_PAID + READER + PAID_HOLD + LENGTHS[5] + CYAN_HOLD,  # the third payment, the whir, the page
    reaction_hold=2.30,  # her face; the last frame
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: each whir ends on the page it prints."""
    starts: list[float] = []
    fx: dict[str, float] = {"beep": STILL}

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    def whir(n: int, at: float) -> float:
        fx[f"whir-{n}"] = at
        return at + LENGTHS[n]

    end = say(0, STILL + 0.30)
    page = whir(1, end + 0.15)
    fx["hit-1"] = page
    end = say(1, page + PAGE_HOLD[0] + 0.15)
    page = whir(2, end + 0.20)
    reader = page + PAGE_HOLD[1]
    fx["paid-1"] = reader + READER
    end = say(2, fx["paid-1"] + 0.20)
    fx["click-1"] = end + 0.20
    page = whir(3, fx["click-1"] + 0.25)
    end = say(3, page + PAGE_HOLD[2] + 0.10)
    fx["paid-2"] = end + 0.15 + READER
    fx["click-2"] = fx["paid-2"] + PAID_HOLD
    page = whir(4, fx["click-2"] + 0.25)
    fx["hit-2"] = page
    end = say(4, page + PAGE_HOLD[3])
    fx["paid-3"] = end + LAST_PAID + READER
    whir(5, fx["paid-3"] + PAID_HOLD)
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on and the cuts: the two-shot, Rosa close, the pages and the card reader."""
    p, fx = t.phrases, t.effects
    pages = [fx[f"whir-{n}"] + LENGTHS[n] for n in LENGTHS]
    return {
        "pages": pages,
        "whirs": [[fx[f"whir-{n}"], pages[n - 1]] for n in LENGTHS],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "two"},
            {"time": pages[0], "angle": "page-1"},
            {"time": p[1]["start"] - 0.15, "angle": "rosa"},
            {"time": p[1]["end"] + 0.15, "angle": "two"},
            {"time": pages[1], "angle": "page-2"},
            {"time": fx["paid-1"] - READER, "angle": "reader-1"},
            {"time": fx["click-1"] - 0.05, "angle": "two"},
            {"time": pages[2], "angle": "page-3"},
            {"time": p[3]["start"] - 0.10, "angle": "rosa"},
            {"time": fx["paid-2"] - READER, "angle": "reader-2"},
            {"time": fx["click-2"] - 0.05, "angle": "two"},
            {"time": pages[3], "angle": "page-4"},
            {"time": fx["paid-3"] - READER, "angle": "reader-3"},
            {"time": fx["whir-5"], "angle": "two"},
            {"time": pages[4], "angle": "page-5"},
            {"time": t.reaction, "angle": "rosa"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

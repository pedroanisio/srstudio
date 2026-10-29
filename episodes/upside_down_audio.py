#!/usr/bin/env python3
"""Episode 09 — Upside Down: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 upside_down_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the gags sit between the lines
(:func:`schedule`) and its camera cuts (:func:`extra`).
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 92026
VOICES = {
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.12)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.24)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}

SCRIPT = [  # role, text, caption, speed
    Spoken("milo", "Hi! I'm here for the quarterly review.", "Hi! I'm here for\nthe quarterly review.", 1.00),
    Spoken("candidate", "Conference room. Bring tissues.", "Conference room.\nBring tissues.", 0.98),
    Spoken(
        "manager", "Third quarter. Sales are down forty percent.", "Third quarter. Sales\nare down forty percent.", 0.95
    ),
    Spoken("candidate", "Sir? Your board is upside down.", "SPEAKER: Sir? Your board\nis upside down.", 1.00),
    Spoken("manager", "Record quarter! Bonuses for everyone!", "Record quarter!\nBonuses for everyone!", 1.05),
    Spoken("candidate", "Including reception?", "SPEAKER: Including\nreception?", 1.00),
    Spoken("manager", "It's upside down again.", "It's upside down\nagain.", 0.92),
]
LEAD = 0.85  # the door chime, before the first line
AFTER_RECEPTION = 0.75  # from "Bring tissues." to the boss
BEEP_GAP = 0.32  # silence before a speakerphone beep, and between the beep and the voice (x 0.5)
FLIP_GAP = 0.30  # from the line to the flip
STARE = 0.70  # the boss staring at the speakerphone before he flips the board back
BEEP = "A single short conference speakerphone connection beep, clean electronic tone, no voices, no music"
FLIP = (
    "A whiteboard on a wall being flipped over fast, a plastic clatter and a quick whoosh, close, no voices, no music"
)
# Generated effects: requested seconds, longest kept after trimming, peak level in the mix; one seed each.
EFFECTS = [
    Sound(
        "door-chime",
        "A short electronic two-tone shop door entry chime in a quiet office lobby, no voices, no music",
        1.2,
        0.9,
        0.30,
        seed=SEED,
    ),
    Sound("speaker-beep", BEEP, 0.6, 0.35, 0.32, seed=SEED + 1),
    Sound("speaker-beep-2", BEEP, 0.6, 0.35, 0.32, seed=SEED + 2),
    Sound("board-flip", FLIP, 1.0, 0.6, 0.42, seed=SEED + 3),
    Sound("board-flip-back", FLIP, 1.0, 0.6, 0.42, seed=SEED + 4),
]
INTERVIEW = Interview(
    slug="upside-down",
    title="Upside Down — The Interview 07",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Eric, Will and Liam; no reference-voice cloning.",
    room_tone_seed=92027,
    reaction_after=0.30,
    reaction_hold=1.05,
    end_card=2.60,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the gags sit in the gaps between lines."""
    starts: list[float] = []
    fx: dict[str, float] = {"door-chime": 0.10}
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    end = say(0)
    cursor = end + 0.25
    end = say(1)
    cursor = end + AFTER_RECEPTION
    end = say(2)
    fx["speaker-beep"] = end + BEEP_GAP
    cursor = fx["speaker-beep"] + effect["speaker-beep"] + BEEP_GAP / 2
    end = say(3)
    fx["board-flip"] = end + FLIP_GAP
    cursor = fx["board-flip"] + effect["board-flip"] + 0.15
    end = say(4)
    fx["speaker-beep-2"] = end + BEEP_GAP
    cursor = fx["speaker-beep-2"] + effect["speaker-beep-2"] + BEEP_GAP / 2
    end = say(5)
    fx["board-flip-back"] = end + STARE
    cursor = fx["board-flip-back"] + effect["board-flip-back"] + 0.20
    say(6)
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The flips, the reaction and end card, and the camera cuts."""
    p, fx = t.phrases, t.effects
    return {
        "flip_start": fx["board-flip"],
        "flip_back_start": fx["board-flip-back"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "reception"},
            {"time": p[1]["start"] - 0.15, "angle": "clerk"},
            {"time": p[1]["end"] + 0.35, "angle": "conference"},
            {"time": fx["speaker-beep"] - 0.10, "angle": "speaker"},
            {"time": fx["board-flip"] - 0.12, "angle": "board"},
            {"time": p[4]["start"] - 0.05, "angle": "manager"},
            {"time": fx["speaker-beep-2"] - 0.10, "angle": "speaker"},
            {"time": p[5]["end"] + 0.15, "angle": "manager"},
            {"time": fx["board-flip-back"] - 0.12, "angle": "board"},
            {"time": p[6]["start"] - 0.05, "angle": "manager"},
            {"time": t.reaction, "angle": "conference"},
            {"time": t.ending, "angle": "end"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

#!/usr/bin/env python3
"""Only Your Aunt: generated dialogue, resolved by the engine, and the timeline.

    srstudio record only-your-aunt PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits (:func:`schedule`)
and its beats (:func:`extra`). A mother told one person. Milo is Liam and Rosa is Lily, heard over the phone until the
last shot. There is no music, and the foley is synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3401
VOICES = {
    "rosa": Singer("pFZP5JQG7iQjIQuC4Bku", "Lily", dict(stability=0.50, similarity_boost=0.75, style=0.25)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("milo", "Mom, it's one interview. Don't tell anyone.", "Mom, it's one interview.\nDon't tell anyone.", 1.05),
    Spoken("rosa", "Who would I tell?", "Who would I tell?", 1.00, phone=True),
    Spoken("milo", "My coffee says good luck at the bank.", "My coffee says\ngood luck at the bank.", 1.00),
    Spoken("rosa", "What a nice town.", "What a nice town.", 0.98, phone=True),
    Spoken("milo", "A man just gave me his son's resume.", "A man just gave me\nhis son's resume.", 1.00),
    Spoken("rosa", "Is he a nice boy?", "Is he a nice boy?", 1.00, phone=True),
    Spoken("milo", "Mom. There's a cake.", "Mom. There's a cake.", 0.92),
    Spoken("rosa", "Is it chocolate?", "Is it chocolate?", 1.02, phone=True),
    Spoken("milo", "I haven't had the interview! Who did you tell?", "I haven't had the interview!\nWho did you tell?", 1.08),
    Spoken("rosa", "Nobody! Your aunt doesn't count.", "Nobody!\nYour aunt doesn't count.", 0.96),
]  # fmt: skip
CUE = 0.86  # the least a line starts after the one before, so that one's caption cue holds
START = 0.30  # the first word: he is already through the door
SLIDE = 1.05  # after "Who would I tell?": the cup comes down the counter into his hand
BENCH = 1.70  # after "What a nice town.": the man sits, lays the page down, pats it twice and goes
ROOM = 3.30  # after "Is he a nice boy?": he walks in on the cake, and nobody speaks for the held bracket
WOUNDED = 1.25  # after "Who did you tell?": the held bracket on Rosa
ENDING = 1.00  # the slice held out, on Milo
INTERVIEW = Interview(
    slug="only-your-aunt",
    title="Only Your Aunt",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Liam and Lily; no voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: a walking call, three stops, and the two held brackets."""
    starts: list[float] = []

    def say(i: int, gap: float) -> float:
        """Line ``i``, ``gap`` after the last one ends, and never before the last one's cue has held."""
        at = max(end + gap, starts[-1] + CUE) if starts else gap
        starts.append(at)
        return at + speech[i]

    end = 0.0
    end = say(0, START)
    end = say(1, 0.20)
    end = say(2, SLIDE)
    end = say(3, 0.25)
    end = say(4, BENCH)
    end = say(5, 0.25)
    end = say(6, ROOM)
    end = say(7, 0.30)
    end = say(8, 0.25)
    say(9, WOUNDED)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the cuts: the cafe and the cup, the park, reception, Rosa."""
    p = t.phrases
    flick = p[1]["end"] + 0.10
    bench = p[3]["end"] + 0.15
    room = p[5]["end"] + 0.25
    home = p[8]["end"] + 0.12
    return {
        "flick": flick,
        "caught": flick + 0.75,
        "sits": bench + 0.10,
        "pats": bench + 0.90,
        "leaves": bench + 1.30,
        "stops": room + 0.85,
        "cuts": p[6]["start"] - 1.55,
        "camera_cuts": [
            {"time": 0, "angle": "cafe"},
            {"time": p[2]["start"] - 0.15, "angle": "cup"},
            {"time": p[2]["end"] + 0.12, "angle": "cafe"},
            {"time": bench, "angle": "park"},
            {"time": room, "angle": "reception"},
            {"time": home, "angle": "home"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

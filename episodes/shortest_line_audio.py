#!/usr/bin/env python3
"""Shortest Line: generated dialogue, resolved by the engine, and the timeline.

    srstudio record shortest-line PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script and the beats between the lines. Rosa
gets in front of Milo in every line he picks, on purpose. Rosa is Lily and Milo is Liam, as in the café and store reels;
her last two lines sit under the rest, said close and then over her shoulder. Every sound but the voices is foley.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 26421
VOICES = {
    "rosa": Singer("pFZP5JQG7iQjIQuC4Bku", "Lily", dict(stability=0.50, similarity_boost=0.75, style=0.25)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("rosa", "I've just got a few, dear.", "I've just got a few, dear.", 1.00),
    Spoken("milo", "Sorry. I'll just...", "Sorry. I'll just...", 1.00),
    Spoken("rosa", "Hello again.", "Hello again.", 1.00),
    Spoken("milo", "You were over there.", "You were over there.", 1.00),
    Spoken("rosa", "Was I?", "Was I?", 1.00),
    Spoken("rosa", "One.", "One.", 0.90),
    Spoken("milo", "You don't need anything, do you?", "You don't need anything, do you?", 1.00),
    Spoken(
        "rosa",
        "I'm seventy-nine, dear. I've got nowhere to be.",
        "I'm seventy-nine, dear.\nI've got nowhere to be.",
        1.0,
    ),
    Spoken("rosa", "I like your face when it happens.", "I like your face when it happens.", 0.95, gain=-4.0),
    Spoken("rosa", "Same time tomorrow?", "Same time tomorrow?", 1.00, gain=-6.0),
]
OPEN = 0.45  # she rolls in on her first word
COUNTS = 1.25  # three coins in the purse, and his eyes go to the next lane
NEXT_LANE = 1.45  # he leaves, he arrives, she rolls in ahead of him
FROZEN = 0.80  # the hold on him, in the same framing as before
THIRD_LANE = 1.70  # he leaves, arrives, looks left at her, looks right at her
ANSWER = 0.25
TO_COIN = 0.95  # the punch-in, then the hand with the coin
SECOND_COIN = 1.50  # the hold between the coins
INSERT = 1.20  # he looks in the cart, one tin of peas
BACK = 0.45
THE_TURN = 0.90  # she turns, the glasses catch the light
LEANS = 0.80
FACE = 1.40  # the hold on Milo, before she goes
ENDING = 1.00  # the hold on Milo, alone
INTERVIEW = Interview(
    slug="shortest-line",
    title="Shortest Line",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Lily and Liam; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.30,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: every lane change and every coin takes as long as it takes."""
    starts: list[float] = []

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, OPEN)
    end = say(1, end + COUNTS)
    end = say(2, end + NEXT_LANE)
    end = say(3, end + FROZEN + THIRD_LANE)
    end = say(4, end + ANSWER)
    end = say(5, end + TO_COIN)
    end = say(6, end + SECOND_COIN + INSERT)
    end = say(7, end + BACK + THE_TURN)
    end = say(8, end + LEANS)
    say(9, end + FACE)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on: three lanes, two coins and the tin."""
    p = t.phrases
    left = p[1]["end"] + 0.10
    second_lane = left + 0.30
    third = p[2]["end"] + FROZEN
    third_lane = third + 0.30
    coin_shot = p[4]["end"] + 0.45
    second_coin = p[5]["end"] + SECOND_COIN
    return {
        "left": left,
        "second_lane": second_lane,
        "left_again": third,
        "third_lane": third_lane,
        "coin_shot": coin_shot,
        "second_coin": second_coin,
        "tin": second_coin + 0.65,
        "turn": p[6]["end"] + BACK,
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [{"time": 0, "angle": "lane"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

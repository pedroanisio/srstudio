#!/usr/bin/env python3
"""Sinking Chair: generated dialogue, resolved by the engine, and the timeline.

    srstudio record sinking-chair PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script and the beats between the lines. The
chair sinks a little further with every claim he makes about rising. The Candidate is Will and the Boss is Eric, as in
the interview reels; the lower he goes, the smaller he sounds. Every sound but the voices is foley.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 26431
VOICES = {
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.1)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
GROWTH = "Three years in that chair. You've never said a word."
SCRIPT = [  # role, text, caption, speed
    Spoken("manager", "Let's talk about your growth.", "Let's talk about your growth.", 1.00),
    Spoken("candidate", "I've really grown this year.", "I've really grown this year.", 1.05),
    Spoken("candidate", "I'm ready to step up.", "I'm ready to step up.", 1.05),
    Spoken("candidate", "I've risen to every challenge.", "I've risen to every challenge.", 1.05),
    Spoken("manager", "And long term?", "And long term?", 1.00),
    Spoken("candidate", "I see myself... higher.", "I see myself... higher.", 0.95, gain=-5.0),
    Spoken("manager", GROWTH, "Three years in that chair.\nYou've never said a word.", 1.00),
    Spoken("candidate", "Is there a raise?", "Is there a raise?", 1.00, gain=-7.0),
    Spoken("manager", "Your salary works the same way.", "Your salary works the same way.", 1.00),
]
OPEN = 0.45  # he is already dropping when the Boss starts
ANSWER = 0.30
STEP = 0.75  # pssht, and his chin comes up
CLAIM = 0.85  # pssht, and his shoulders reach the desk
PULLS = 0.25  # the lever, smiling
NOTHING = 0.55  # the lever did nothing
GOES = 0.50  # and then it did
TO_BOSS = 0.60
PEN = 1.00  # the hold on the Boss's pen
LOW = 0.45  # pssht, low and small
HIGHER = 1.50  # the hold on the eyes
OVER = 0.45  # he looks over the edge
ASKS = 0.35
NOTES = 0.45
HOLD = 0.80  # the salary lands
SINK = 2.40  # one long pssht
INTERVIEW = Interview(
    slug="sinking-chair",
    title="Sinking Chair",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Eric and Will; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=HOLD + SINK + 0.25,
    reaction_hold=1.25,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: each claim gets its drop, and the lever gets its nothing."""
    starts: list[float] = []

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, OPEN)
    end = say(1, end + ANSWER)
    end = say(2, end + STEP)
    end = say(3, end + CLAIM)
    end = say(4, end + PULLS + NOTHING + GOES + TO_BOSS)
    end = say(5, end + PEN + LOW)
    end = say(6, end + HIGHER + OVER)
    end = say(7, end + ASKS)
    say(8, end + NOTES)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on: each drop, the lever, and the last long sink."""
    p = t.phrases
    lever = p[3]["end"] + PULLS
    return {
        "drops": [0.08, p[1]["end"] + 0.15, p[2]["end"] + 0.15, lever + NOTHING, p[4]["end"] + PEN],
        "lever": lever,
        "low": p[5]["end"] + HIGHER,
        "sink": p[8]["end"] + HOLD,
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [{"time": 0, "angle": "reverse"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

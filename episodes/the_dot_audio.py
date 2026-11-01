#!/usr/bin/env python3
"""The Dot: generated dialogue, resolved by the engine, and the timeline.

    srstudio record the-dot PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits (:func:`schedule`)
and its beats (:func:`extra`). A first date, a phone on speaker and a mother with the family map. Rosa is Lily and is
only ever heard, Milo is Liam and Ava is Jessica. There is no music, and the foley is synthesized in the build. The
phone is already ringing on the first frame, and the first word comes by 0.45 s.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3322
VOICES = {
    "rosa": Singer("pFZP5JQG7iQjIQuC4Bku", "Lily", dict(stability=0.50, similarity_boost=0.75, style=0.25)),
    "customer": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "barista": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("rosa", "Why are you at a restaurant?", "Why are you at a restaurant?", 1.05),
    Spoken("customer", "Mom, how do you...", "Mom, how do you...", 1.08),
    Spoken("rosa", "The dot. Forty minutes. Who is she?", "The dot. Forty minutes.\nWho is she?", 1.02),
    Spoken("barista", "Who's that?", "Who's that?", 1.00),
    Spoken("customer", "Nobody. Mom.", "Nobody. Mom.", 1.05),
    Spoken("rosa", "Tuesday the dot was at a pharmacy.", "Tuesday the dot\nwas at a pharmacy.", 1.04),
    Spoken("rosa", "Eleven minutes. Are you dying?", "Eleven minutes.\nAre you dying?", 1.02),
    Spoken("barista", "Are you dying?", "Are you dying?", 1.00),
    Spoken("customer", "It was shampoo!", "It was shampoo!", 1.10),
    Spoken(
        "rosa", "Thursday night the dot was at some Sandra's.", "Thursday night the dot\nwas at some Sandra's.", 0.98
    ),
    Spoken("barista", "Hi. Where was he on the 14th?", "Hi. Where was he\non the fourteenth?", 0.96),
    Spoken("rosa", "Do you have a pen, dear?", "Do you have a pen, dear?", 0.96),
]
CUE = 0.86  # the least a line starts after the one before, so that one's caption cue holds
START = 0.44  # the first word: he has picked up on the first ring
HOLD = 1.60  # after "some Sandra's.": the held bracket, the fork and the phone, no speech and no new caption
PAUSE = 1.10  # after "the fourteenth?": the line goes quiet, and a chair is pulled up far away
ENDING = 3.20  # the buzz, the chip, and Milo watching the two of them
INTERVIEW = Interview(
    slug="the-dot",
    title="The Dot",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Lily, Liam and Jessica; no voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: a fast interrogation, then the hold, the quiet line and the pen."""
    starts: list[float] = []

    def say(i: int, gap: float) -> float:
        """Line ``i``, ``gap`` after the last one ends, and never before the last one's cue has held."""
        at = max(end + gap, starts[-1] + CUE) if starts else gap
        starts.append(at)
        return at + speech[i]

    end = 0.0
    end = say(0, START)
    end = say(1, 0.25)
    end = say(2, 0.20)
    end = say(3, 0.30)
    end = say(4, 0.20)
    end = say(5, 0.30)
    end = say(6, 0.20)
    end = say(7, 0.25)
    end = say(8, 0.15)
    end = say(9, 0.25)
    end = say(10, HOLD)
    say(11, PAUSE)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the one cut: over Ava's shoulder, for the chip."""
    p = t.phrases
    buzz = p[11]["end"] + 0.40
    chip = buzz + 0.60
    return {
        "put": p[9]["end"] + 0.15,
        "take": p[9]["end"] + 0.85,
        "chair": p[10]["end"] + 0.40,
        "buzz": buzz,
        "chip": chip,
        "camera_cuts": [{"time": 0, "angle": "table"}, {"time": chip, "angle": "chip"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

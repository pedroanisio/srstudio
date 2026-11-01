#!/usr/bin/env python3
"""One Way Video: generated dialogue, resolved by the engine, and the timeline.

    srstudio record one-way-video PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits (:func:`schedule`)
and its beats (:func:`extra`). A one-way video interview, shot from the laptop, with a housemate and a bowl of cereal in
the door behind him. The Candidate is Will, Milo is Liam and the System is Alice, a calm device voice. There is no
music, and the foley is synthesized in the build. The timer runs on the first frame and the first word comes by 0.45 s.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3315
VOICES = {
    "system": Singer("Xb7hH8MSUJpSbSDYk0k2", "Alice", dict(stability=0.80, similarity_boost=0.75, style=0.05)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.20)),
    "customer": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("system", "Why are you the right person? Thirty seconds.", "Why are you the right person?\nThirty seconds."),
    Spoken("candidate", "Hi! Hello. There's nobody there. Hi.", "Hi! Hello.\nThere's nobody there. Hi.", 1.02),
    Spoken("system", "Eye contact: low.", "Eye contact: low.", 1.00),
    Spoken("candidate", "I'm a people person.", "I'm a people person.", 1.00),
    Spoken("system", "Smile: forty percent sincere.", "Smile: forty percent sincere.", 1.00),
    Spoken("candidate", "Milo, go away.", "Milo, go away.", 0.94),
    Spoken("customer", "Who are you talking to?", "Who are you talking to?", 1.00),
    Spoken("system", "Second candidate detected.", "Second candidate detected.", 1.00),
    Spoken("candidate", "No. No, no.", "No. No, no.", 1.08),
    Spoken("customer", "Hey.", "Hey.", 0.95),
    Spoken("system", "Confidence: excellent.", "Confidence: excellent.", 1.00),
    Spoken("system", "Congratulations, Milo.", "Congratulations, Milo.", 1.00),
    Spoken("customer", "For what?", "For what?", 0.96),
]
START = 0.42  # the first word: the clock is already running
HOLD = 1.50  # after "Confidence: excellent.": the held bracket, chewing and a green tick, no new caption
DOOR = 0.70  # "Eye contact: low." to his next line: he stares at the dot and the door opens behind him
NEAR = 0.75  # "Forty percent" to "Milo, go away.": Milo comes closer, chewing
WAVE = 0.85  # "No, no." to "Hey.": another spoonful, the lens, the spoon
HEY = 0.86  # from "Hey." starting to the next line, so its one word holds as a cue
ENDING = 1.30  # the last line, then he keeps chewing
INTERVIEW = Interview(
    slug="one-way-video",
    title="One Way Video",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Alice, Will and Liam; no voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the System's flat pace, the three gaps Milo walks in, and the held tick."""
    starts: list[float] = []

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, START)
    end = say(1, max(end + 0.30, 3.10))
    end = say(2, end + 0.25)
    end = say(3, end + DOOR)
    end = say(4, end + 0.30)
    end = say(5, end + NEAR)
    end = say(6, end + 0.25)
    end = say(7, end + 0.20)
    end = say(8, end + 0.20)
    hey = end + WAVE
    end = say(9, hey)
    end = say(10, max(end + 0.25, hey + HEY))
    end = say(11, end + HOLD)
    say(12, end + 0.30)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on."""
    p = t.phrases
    return {
        "door": p[2]["end"] + 0.10,
        "near": p[4]["end"] + 0.10,
        "spoon": p[8]["end"] + 0.10,
        "tick": p[10]["end"] + 0.25,
        "camera_cuts": [{"time": 0, "angle": "lens"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

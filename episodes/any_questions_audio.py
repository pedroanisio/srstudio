#!/usr/bin/env python3
"""Any Questions: generated dialogue, resolved by the engine, and the timeline.

    srstudio record any-questions PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits
(:func:`schedule`) and its cuts (:func:`extra`). An interview ends on the usual question, the candidate asks the one
nobody asks, and the two of them end up in each other's chairs. Eric is the manager and Will the candidate, as in the
interview reels. There is no music, and the foley is synthesized in the build. The camera moves from its first frame
(arm B of the ``sp-hook_motion`` test), the first line at 0.5 s. The manager's voice falls as the desk stops being his:
each ``level`` is a choice in the mix, so the takes and the timing stay as recorded.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 31211
VOICES = {
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.15)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.20)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("manager", "Do you have any questions for us?", "Do you have any questions for us?", 1.02),
    Spoken("candidate", "Just one. Are you happy here?", "Just one.\nAre you happy here?", 1.00),
    Spoken("manager", "We have free fruit.", "We have free fruit.", 0.95, level=-2),
    Spoken("candidate", "When was your last vacation?", "When was your last vacation?", 1.00),
    Spoken("manager", "What year is it?", "What year is it?", 0.92, level=-3),
    Spoken("candidate", "Take your time.", "Take your time.", 0.95),
    Spoken(
        "manager",
        "It's just bananas. Since March. Just bananas.",
        "It's just bananas.\nSince March.\nJust bananas.",
        0.92,
        level=-4,
    ),  # fmt: skip
    Spoken("candidate", "What's your greatest weakness?", "What's your greatest weakness?", 1.00),
    Spoken("manager", "I stayed.", "I stayed.", 0.88, level=-7),
    Spoken("candidate", "We'll be in touch.", "We'll be in touch.", 1.00),
    Spoken("manager", "Will you?", "Will you?", 0.90, level=-5),
]
START = 0.50  # the first word, on the held frame's last moment
FALL = 2.0  # the smile holds, and goes on one side
SLIDE = 0.55  # the glass crosses the desk
DRINK = 1.10  # the manager drinks, both hands, before anyone speaks
SWAP = 0.45  # bananas, and the cut to the other chairs
WEAK = 1.50  # "I stayed.": nothing, and the folder closes
STAND = 0.35  # the candidate is up before the line
ENDING = 0.80  # "Will you?" and the small man in the chair
INTERVIEW = Interview(
    slug="any-questions",
    title="Any Questions",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Eric and Will; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: tight exchanges, the two long holds, the slide and the drink."""
    starts: list[float] = []
    cursor = START

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    cursor = say(0) + 0.20
    cursor = say(1) + FALL
    cursor = say(2) + 0.25
    cursor = say(3) + 0.15
    cursor = say(4) + 0.20 + SLIDE
    cursor += DRINK * 0.4
    cursor = say(5) + DRINK * 0.6
    cursor = say(6) + SWAP
    cursor = say(7) + 0.20
    cursor = say(8) + WEAK
    cursor = say(9) + 0.70
    say(10)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the cuts: desk and chair, the chairs swap, then the slow push."""
    p = t.phrases
    fall = p[1]["end"] + 0.25
    slide = p[4]["end"] + 0.20
    drink = slide + SLIDE
    swap = p[6]["end"] + SWAP
    closes = p[8]["end"] + WEAK * 0.45
    stands = p[9]["start"] - STAND
    return {
        "fall": fall,
        "smile_gone": fall + FALL * 0.62,
        "slide": slide,
        "drink": drink,
        "drunk": p[6]["start"] - 0.10,
        "swap": swap,
        "closes": closes,
        "stands": stands,
        "camera_cuts": [
            {"time": 0, "angle": "desk"},
            {"time": p[1]["start"] - 0.05, "angle": "chair"},
            {"time": p[1]["end"] + 0.15, "angle": "desk"},
            {"time": p[3]["start"] - 0.05, "angle": "chair"},
            {"time": p[4]["start"] - 0.05, "angle": "desk"},
            {"time": slide, "angle": "chair"},
            {"time": drink, "angle": "desk"},
            {"time": swap, "angle": "desk-after"},
            {"time": p[8]["start"] - 0.05, "angle": "chair-after"},
            {"time": closes - 0.30, "angle": "desk-after"},
            {"time": p[10]["start"] - 0.40, "angle": "chair-after"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

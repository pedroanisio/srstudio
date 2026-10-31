#!/usr/bin/env python3
"""Don't Move: generated dialogue, resolved by the engine, and the timeline.

    srstudio record dont-move PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits
(:func:`schedule`) and its cuts (:func:`extra`). Ava talks Milo through a phone six years deep in a stranger's photos.
Jessica is Ava and Liam is Milo, as in the café reels. There is no music, the foley is synthesized in the build, and
Diane's message is read, not voiced. It moves from its first frame (arm B of the ``sp-hook_motion`` test): the opening
is pulling back off a hand on a wrist.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 31251
VOICES = {
    "ava": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("ava", "Don't. Move. Your thumb.", "Don't. Move.\nYour thumb.", 0.98),
    Spoken("milo", "I'm in my ex's new girlfriend's mother's photos.",
           "I'm in my ex's\nnew girlfriend's\nmother's photos.", 1.04),
    Spoken("ava", "How far back?", "How far back?", 0.98),
    Spoken("milo", "2016.", "2016.", 0.92),
    Spoken("ava", "Okay. Scroll up. Slowly. Like a surgeon.", "Okay. Scroll up.\nSlowly. Like a surgeon.", 0.98),
    Spoken("ava", "Don't breathe on it.", "Don't breathe on it.", 0.90),
    Spoken("milo", "It's red.", "It's red.", 0.90),
    Spoken("ava", "I never knew you.", "I never knew you.", 0.95),
    Spoken("ava", "Milo. No.", "Milo. No.", 0.92),
    Spoken("milo", "What do I bring?", "...What do I bring?", 1.00),
]  # fmt: skip
START = 0.30  # the first word: the frame is already moving
WATCH = 1.75  # the watch comes off, the cup goes
TICKS = 1.10  # on the phone before she speaks
AFTER = 0.75  # after "Don't breathe on it.", before the cup
SILENCE = 2.00  # the heart is red
COAT = 1.05  # up, and the coat on
TOAST = 4.00  # the cut, the slide, and long enough to read it twice
AT_DOOR = 0.75  # she stops, his thumbs start
NOW_TYPING = 0.40
ENDING = 0.35
INTERVIEW = Interview(
    slug="dont-move",
    title="Don't Move",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Jessica and Liam; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: quick at the table, then the two holds the reel stands on."""
    starts: list[float] = []
    cursor = START

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    cursor = say(0) + 0.20
    cursor = say(1) + 0.20
    cursor = say(2) + 0.12
    cursor = say(3) + WATCH
    cursor = say(4) + 0.12 + TICKS
    cursor = say(5) + AFTER + SILENCE
    cursor = say(6) + COAT
    cursor = say(7) + TOAST + AT_DOOR
    cursor = say(8) + NOW_TYPING
    say(9)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the cuts: the table, the phone, the table, the phone, the door."""
    p = t.phrases
    let_go = p[3]["end"] + 0.05
    phone = p[4]["end"] + 0.12
    crash = p[5]["end"] + AFTER
    back = crash + 0.85
    stands = p[6]["end"] + 0.12
    toast = p[7]["end"] + 0.25
    door = toast + TOAST - 0.25
    return {
        "let_go": let_go,
        "crash": crash,
        "stands": stands,
        "toast": toast,
        "door": door,
        "camera_cuts": [
            {"time": 0, "angle": "table"},
            {"time": phone, "angle": "phone"},
            {"time": back, "angle": "table"},
            {"time": toast, "angle": "phone"},
            {"time": door, "angle": "table"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

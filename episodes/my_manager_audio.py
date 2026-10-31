#!/usr/bin/env python3
"""My Manager: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record my-manager PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, its effects, the waits the clock jumps
over and the two dead airs (:func:`schedule`), and its cuts (:func:`extra`). A car salesman goes to ask his manager,
twice, and comes back worse each time; Rosa follows him the third time. The first second is held still (arm A of the
``sp-hook_motion`` test); :func:`schedule` refuses a shorter one. The salesman is George and Rosa is Lily, as published.
The repeated effects share one prompt and seed, so each is one request.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3117
VOICES = {
    "manager": Singer("JBFqnCBsd6RMkjVDRZzb", "George", dict(stability=0.55, similarity_boost=0.75, style=0.15)),
    "rosa": Singer("pFZP5JQG7iQjIQuC4Bku", "Lily", dict(stability=0.50, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("manager", "Let me talk to my manager.", "Let me talk to my manager.", 1.00),
    Spoken("manager", "He says twenty three nine.", "He says twenty-three nine.", 0.95),
    Spoken("rosa", "Twenty two.", "Twenty-two.", 1.00),
    Spoken("manager", "He'll kill me.", "He'll kill me.", 0.95),
    Spoken("manager", "He cried. Twenty three eight.", "He cried.\nTwenty-three eight.", 0.90),
    Spoken("rosa", "Twenty two five.", "Twenty-two five.", 1.00),
    Spoken("manager", "I've got kids.", "I've got kids.", 0.90),
    Spoken("manager", "Twenty two five, Gerald. I told her.", "Twenty-two five, Gerald.\nI told her.", 0.95),
    Spoken("rosa", "Twenty three. Final.", "Twenty-three. Final.", 0.95),
    Spoken("manager", "He says deal.", "He says deal.", 0.95),
]
DOOR = "A plain office door pulled shut with a soft click, close, no voices, no music"
WHIR = "A wall clock's hands racing forward, a fast mechanical ticking whir, short, close, no voices, no music"
EFFECTS = [
    Sound("door-1", DOOR, 0.8, 0.6, 0.26, seed=SEED + 1),
    Sound("door-2", DOOR, 0.8, 0.6, 0.26, seed=SEED + 1),
    Sound("door-3", DOOR, 0.8, 0.6, 0.26, seed=SEED + 1),
    Sound("whir-1", WHIR, 1.0, 0.85, 0.26, seed=SEED + 2),
    Sound("whir-2", WHIR, 1.0, 0.85, 0.26, seed=SEED + 2),
    Sound(
        "creak",
        "A wooden door slowly creaking open on an old hinge, close, no voices, no music",
        1.4,
        1.2,
        0.28,
        seed=SEED + 3,
    ),
    Sound(
        "sit",
        "A metal folding chair creaking as someone sits down on it, close, no voices, no music",
        0.9,
        0.7,
        0.26,
        seed=SEED + 4,
    ),
]
LEAD = 1.15  # the still first second (arm A): nothing moves and no caption shows before 1.0 s
STILL = 1.0  # the shortest first second the test accepts
LEAVE = 0.50  # he crosses out of frame, and back
ALONE = 0.90  # she sits there before the clock shows what that cost her
JUMP = 0.95  # the shot of the clock
BACK = 0.70  # from the clock to his next line: he walks back in
HOLD = 2.00  # the dead air, both times
SITS = 1.30  # she crosses the cupboard and sits
INTERVIEW = Interview(
    slug="my-manager",
    title="My Manager",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices George and Lily; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.15,
    reaction_hold=0.75,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the clock jumps and the dead airs sit between the lines."""
    if LEAD < STILL:
        raise ValueError(f"arm A holds the first {STILL} s still, but the first line starts at {LEAD}")
    starts: list[float] = []
    fx: dict[str, float] = {}

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    end = say(0, LEAD)
    fx["door-1"] = end + 0.2 + LEAVE
    end = say(1, end + 0.2 + LEAVE + ALONE + JUMP + BACK)
    fx["whir-1"] = starts[1] - BACK - JUMP + 0.05
    end = say(2, end + 0.30)
    end = say(3, end + 0.30)
    fx["door-2"] = end + 0.2 + LEAVE
    end = say(4, end + 0.2 + LEAVE + ALONE + JUMP + BACK)
    fx["whir-2"] = starts[4] - BACK - JUMP + 0.05
    end = say(5, end + 0.30)
    end = say(6, end + 0.30)
    fx["door-3"] = end + 0.2 + LEAVE
    door = end + 0.2 + LEAVE + 0.90 + 0.65 + 0.25  # the beat she waits, her getting up, and then the door
    fx["creak"] = door + 0.75
    end = say(7, door + 2.60)
    sees = end + 1.30  # he listens to the plant, and nods
    end = say(8, sees + HOLD + SITS + 0.30)
    fx["sit"] = starts[8] - 0.30 - 0.40
    say(9, end + HOLD)
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the shots: the desk, the clock twice, and the door."""
    p, fx = t.phrases, t.effects
    door = fx["creak"] - 0.75
    clock = [p[1]["start"] - BACK - JUMP, p[4]["start"] - BACK - JUMP]
    return {
        "leaves": [p[0]["end"] + 0.2, p[3]["end"] + 0.2, p[6]["end"] + 0.2],
        "clock": clock,
        "follows": p[6]["end"] + 0.2 + LEAVE + 0.90,
        "opens": door + 0.75,
        "sees": p[7]["end"] + 1.30,
        "sits": p[8]["start"] - 0.30 - SITS,
        "leaf": p[8]["end"] + 0.40,
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "desk"},
            {"time": clock[0], "angle": "clock"},
            {"time": clock[0] + JUMP, "angle": "desk"},
            {"time": clock[1], "angle": "clock"},
            {"time": clock[1] + JUMP, "angle": "desk"},
            {"time": door, "angle": "door"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

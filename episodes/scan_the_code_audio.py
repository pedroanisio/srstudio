#!/usr/bin/env python3
"""Scan the Code: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 scan_the_code_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, its effects, the beats between the
lines (:func:`schedule`) and its shots (:func:`extra`). The opening moves from the first frame (the ``sp-hook_motion``
test's arm B): Ava is already crossing to the table, and :func:`schedule` refuses a first line held any later.
The plop itself is synthesized in the builder, from :func:`srstudio.foley.plop`.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3120
VOICES = {
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "ava": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.3)),
    "phone": Singer("Xb7hH8MSUJpSbSDYk0k2", "Alice", dict(stability=0.80, similarity_boost=0.75, style=0.05)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("milo", "Could I see a menu?", "Could I see a menu?", 1.00),
    Spoken("ava", "Scan the code.", "Scan the code.", 0.95),
    Spoken("milo", "It wants my email.", "It wants my email.", 1.00),
    Spoken("ava", "For the soup.", "For the soup.", 0.95),
    Spoken("milo", "Now it wants my location.", "Now it wants my location.", 1.00),
    Spoken("ava", "You're at table four.", "You're at table four.", 0.95),
    Spoken("milo", "You're looking at me. Can I just order?", "You're looking at me.\nCan I just order?", 1.00),
    Spoken("ava", "Scan me.", "Scan me.", 0.90),
    Spoken("phone", "Hi Milo! How's Ava doing so far?", "Hi Milo!\nHow's Ava doing so far?", 1.00),
    Spoken("milo", "Why does the pigeon have a menu?", "Why does the pigeon\nhave a menu?", 1.00),
    Spoken("ava", "He doesn't have a phone.", "He doesn't have a phone.", 0.95),
]
EFFECTS = [
    Sound(
        "scan",
        "A single short rising electronic beep from a phone scanning a code, clean, close, no voices, no music",
        0.7,
        0.4,
        0.26,
        seed=SEED + 1,
    ),
    Sound(
        "chime",
        "A bright friendly two-note notification chime from a phone, close, no voices, no music",
        1.0,
        0.7,
        0.30,
        seed=SEED + 2,
    ),
    Sound(
        "bowl",
        "A ceramic soup bowl set down on a cloth-covered café table, one soft solid knock, close, no voices, no music",
        0.8,
        0.6,
        0.30,
        seed=SEED + 3,
    ),
    Sound(
        "menu",
        "A single sheet of stiff paper laid down flat on a table with a light slap, close, no voices, no music",
        0.7,
        0.5,
        0.34,
        seed=SEED + 4,
    ),
]
LEAD = 0.35  # arm B: she is moving on frame one and he asks while she is still arriving
BUSY = 0.6  # the latest the first line may start: anything later is a held opening
SCANS = 1.15  # from "Scan the code." to the beep
TURN = 0.36  # she turns, the code on her apron coming round
WAITS = 1.20  # the code held on him before he lifts the phone
LIFTS = 1.05  # the phone comes up to her: he feels every second of it
STILL_FACE = 1.30  # after the phone's question, Ava looks at him and does not help
SOUP = 0.75  # into the pigeon's table: the bowl lands this long after the cut
LOOK = 0.75  # his answer lands and he looks at the phone
OVER = 1.30  # the phone held over the glass
FALLS = 0.26  # hand open to the water
BUBBLES = 1.50  # the plop and the bubbles, held
MENU_LANDS = 0.55  # her hand and the menu come in
SEEN = 0.55  # the menu lies there
FACE = 1.70  # the last hold: Ava's face
INTERVIEW = Interview(
    slug="scan-the-code",
    title="Scan the Code",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Liam, Jessica and Alice; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.0,
    reaction_hold=LOOK + OVER + FALLS + BUBBLES + MENU_LANDS + SEEN + FACE,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths; the drop and the menu run after the last line."""
    if LEAD > BUSY:
        raise ValueError(f"arm B moves from the first frame, but the first line waits until {LEAD}")
    starts: list[float] = []
    fx: dict[str, float] = {}

    def say(i: int, gap: float) -> float:
        starts.append(end + gap)
        return starts[-1] + speech[i]

    end = LEAD
    end = say(0, 0.0)
    end = say(1, 0.25)
    fx["scan"] = end + SCANS
    end = say(2, SCANS + effect["scan"] + 0.05)
    end = say(3, 0.28)
    end = say(4, 0.45)
    end = say(5, 0.28)
    end = say(6, 0.40)
    end = say(7, 0.35)
    turned = end + 0.10 + TURN
    fx["chime"] = turned + WAITS + LIFTS
    end = say(8, fx["chime"] + effect["chime"] - end)
    stares = end + STILL_FACE
    fx["bowl"] = stares + SOUP
    end = say(9, fx["bowl"] + effect["bowl"] - end)
    end = say(10, 0.35)
    fx["menu"] = end + LOOK + OVER + FALLS + BUBBLES + MENU_LANDS
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the shots."""
    p, fx = t.phrases, t.effects
    end = p[7]["end"]
    turn = end + 0.10
    lift = turn + TURN + WAITS
    stares = p[8]["end"] + STILL_FACE
    look = p[10]["end"] + LOOK
    plop = look + OVER + FALLS
    return {
        "turn": turn,
        "lift": lift,
        "pigeon": stares,
        "over": look,
        "let_go": look + OVER,
        "plop": plop,
        "cues": {k: fx[k] for k in ("scan", "chime", "bowl", "menu")},
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},
            {"time": p[1]["start"] - 0.1, "angle": "ava"},
            {"time": p[1]["end"] + 0.15, "angle": "tent"},
            {"time": p[3]["start"] - 0.1, "angle": "ava"},
            {"time": p[4]["start"] - 0.1, "angle": "tent"},
            {"time": p[5]["start"] - 0.1, "angle": "ava"},
            {"time": p[6]["start"] - 0.1, "angle": "milo"},
            {"time": p[7]["start"] - 0.1, "angle": "wide"},
            {"time": lift, "angle": "held-up"},
            {"time": stares, "angle": "pigeon"},
            {"time": p[10]["start"] - 0.1, "angle": "ava"},
            {"time": look, "angle": "glass"},
            {"time": fx["menu"] + SEEN, "angle": "face"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

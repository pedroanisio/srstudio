#!/usr/bin/env python3
"""Nobody Died: generated dialogue, resolved by the engine, and the timeline.

    srstudio record nobody-died PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, where each line sits (:func:`schedule`)
and its beats (:func:`extra`). Milo is Liam, Rosa is Lily and the manager is Eric, heard down a laptop's speaker. There
is no music, and the foley is synthesized in the build.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 3423
VOICES = {
    "rosa": Singer("pFZP5JQG7iQjIQuC4Bku", "Lily", dict(stability=0.50, similarity_boost=0.75, style=0.25)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.15)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("manager", "So, tell me about yourself.", "So, tell me about yourself.", 1.00, phone=True),
    Spoken("milo", "I'm a hard worker.", "I'm a hard worker.", 1.00),
    Spoken("manager", "Do you need to get that?", "Do you need to get that?", 1.00, phone=True),
    Spoken("milo", "It's just my mom.", "It's just my mom.", 1.00),
    Spoken("manager", "And why this company?", "And why this company?", 1.00, phone=True),
    Spoken("milo", "I've always admired...", "I've always admired...", 0.95),
    Spoken("milo", "She wrote 'don't worry.'", "She wrote 'don't worry.'", 0.92),
    Spoken("manager", "That's nice.", "That's nice.", 1.00, phone=True),
    Spoken("milo", "Nobody writes that if it's fine.", "Nobody writes that\nif it's fine.", 0.95),
    Spoken("manager", "Take it. Family first.", "Take it. Family first.", 0.98, phone=True),
    Spoken("milo", "Mom? What happened? Who died?", "Mom? What happened?\nWho died?", 1.12),
    Spoken("rosa", "Nobody died. Do you want a lamp?", "Nobody died.\nDo you want a lamp?", 0.98),
]  # fmt: skip
CUE = 0.86  # the least a line starts after the one before, so that one's caption cue holds
START = 0.25  # the manager's first word: the phone is already buzzing
PEEK = 1.00  # after "I've always admired...": the phone, close, CALL ME and then the line under it
TURNS = 0.95  # after "Nobody writes that if it's fine.": the phone turns itself over
BULB = 1.30  # after "Who died?": the held bracket on Rosa under the bulb
ENDING = 0.45  # the lamp under her arm, and out on the last word
INTERVIEW = Interview(
    slug="nobody-died",
    title="Nobody Died",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Liam, Lily and Eric; no voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.05,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: an interview going on over a phone, and the three held brackets."""
    starts: list[float] = []

    def say(i: int, gap: float) -> float:
        """Line ``i``, ``gap`` after the last one ends, and never before the last one's cue has held."""
        at = max(end + gap, starts[-1] + CUE) if starts else gap
        starts.append(at)
        return at + speech[i]

    end = 0.0
    end = say(0, START)
    end = say(1, 0.20)
    end = say(2, 0.25)
    end = say(3, 0.20)
    end = say(4, 0.30)
    end = say(5, 0.25)
    end = say(6, PEEK)
    end = say(7, 0.25)
    end = say(8, 0.25)
    end = say(9, TURNS)
    end = say(10, 0.25)
    say(11, BULB)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the cuts: Milo, the tile, the phone, Rosa."""
    p = t.phrases
    peek = p[5]["end"] + 0.05
    turn = p[8]["end"] + 0.05
    return {
        "face_down": p[3]["start"] - 0.05,
        "peek": peek,
        "worry": peek + 0.48,
        "turn": turn + 0.22,
        "camera_cuts": [
            {"time": 0, "angle": "milo"},
            {"time": p[2]["start"] - 0.05, "angle": "tile"},
            {"time": p[3]["start"] - 0.05, "angle": "milo"},
            {"time": peek, "angle": "phone"},
            {"time": p[6]["start"] - 0.05, "angle": "close"},
            {"time": p[7]["start"] - 0.05, "angle": "tile"},
            {"time": p[8]["start"] - 0.05, "angle": "close"},
            {"time": turn, "angle": "turns"},
            {"time": p[9]["start"] - 0.05, "angle": "tile"},
            {"time": p[10]["start"] - 0.05, "angle": "close"},
            {"time": p[10]["end"] + 0.10, "angle": "rosa"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

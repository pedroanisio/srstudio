#!/usr/bin/env python3
"""How Is Everything: generated dialogue, resolved by the engine, and the timeline.

    srstudio record how-is-everything PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script and the beats between the lines. Ava
only ever asks with Milo's mouth full, so he tests her with a bite of nothing, and finally bites a napkin to get the
check. Milo is Liam, Ava is Jessica, as in the café reels. Every sound but the voices is foley, built with the picture.
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer

SEED = 26401
VOICES = {
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
    "ava": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.3)),
}
ASK = "How is everything?"
MUFFLED = "Mm-hmm."  # written as the recogniser hears it; the caption stays "Mmf."
SCRIPT = [  # role, text, caption, speed
    Spoken("ava", ASK, ASK, 1.10),
    Spoken("milo", MUFFLED, "Mmf.", 1.00),
    Spoken("ava", ASK, ASK, 1.10),
    Spoken("milo", MUFFLED, "Mmf.", 1.00),
    Spoken("milo", "Got you.", "Got you.", 0.95),
    Spoken("ava", ASK, ASK, 1.10),
    Spoken("milo", MUFFLED, "Mmf!", 1.00),
    Spoken("milo", "Excuse me? Hello? Check, please?", "Excuse me? Hello?\nCheck, please?", 1.00),
    Spoken("ava", ASK, ASK, 1.10),
    Spoken("milo", MUFFLED, "Mmf.", 1.00),
]
FIRST_BITE = 0.22  # the sandwich is already on its way on the first frame
ARRIVES = 0.14  # after a bite, she is simply there
ASKS = 0.10  # and the question is already in the air
LEAVES = 0.30  # after his answer, gone
CHEWS = 1.05  # swallowing, watching her wipe a far table
LIFT = 1.0  # the sandwich comes up slowly, watching her
FAKE_AFTER = 1.0  # the second mouthful down, the idea arrives
AIR = 1.05  # chewing nothing
ROUND = 1.45  # looking round the room, nobody coming: the hold before "Got you."
REAL_AFTER = 0.75  # the smile, then the real bite
EMPTY_AFTER = 0.75  # the jump to the empty plate
CALLS = 0.75  # the hand goes up before he calls
NAPKIN_LOOK = 1.25  # the napkin, then her: the hold before he bites it
TO_MOUTH = 1.0  # the napkin comes up
BEEP_AFTER = 0.10  # the card reader, after his answer
ENDING = 2.5  # the napkin, the wet eyes, nothing else
INTERVIEW = Interview(
    slug="how-is-everything",
    title="How Is Everything",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Liam and Jessica; no reference-voice cloning. Foley synthesized; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.35,
    reaction_hold=ENDING,
    end_card=0.0,
    font=NOTO_SANS_BOLD,
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: every question lands on a bite, and the holds between them are his."""
    starts: list[float] = []

    def say(i: int, at: float) -> float:
        starts.append(at)
        return at + speech[i]

    def asked(i: int, bite: float) -> float:
        end = say(i, bite + ARRIVES + ASKS)
        return say(i + 1, end + 0.10)

    end = asked(0, FIRST_BITE)
    bite = end + LEAVES + CHEWS + LIFT
    end = asked(2, bite)
    fake = end + LEAVES + FAKE_AFTER
    end = say(4, fake + AIR + ROUND)
    bite = end + REAL_AFTER
    end = asked(5, bite)
    empty = end + EMPTY_AFTER
    end = say(7, empty + CALLS)
    bite = end + NAPKIN_LOOK + TO_MOUTH
    asked(8, bite)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the one jump cut, to the empty plate."""
    p = t.phrases
    second = p[2]["start"] - ASKS - ARRIVES
    fake = p[3]["end"] + LEAVES + FAKE_AFTER
    third = p[5]["start"] - ASKS - ARRIVES
    empty = p[6]["end"] + EMPTY_AFTER
    napkin = p[8]["start"] - ASKS - ARRIVES
    return {
        "bites": [FIRST_BITE, second, third],
        "fake": fake,
        "air_stop": fake + AIR,
        "empty": empty,
        "napkin": napkin,
        "beep": p[9]["end"] + BEEP_AFTER,
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [{"time": 0, "angle": "table"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

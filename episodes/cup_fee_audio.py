#!/usr/bin/env python3
"""Cup Fee — Comedy Cut 22: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record cup-fee PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the card reader's beeps sit between
the lines (:func:`schedule`) and its camera cuts (:func:`extra`). Milo orders a black coffee; Ava adds a fee for
the cup, a lid fee, a service fee and, when he offers cash, a cash fee, each one a beep and a higher total on the
card reader; the coffee itself turns out to be free, and the three bucks are the coffee fee. The tip tablet from *Tip
Screen* swivels round. The opening second is still (the ``sp-hook_motion`` test's arm A): the first line starts
after :data:`LEAD`. The voices are the café's own, Jessica (Ava) and Liam (Milo).
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 22041
VOICES = {  # the café's voices, as in Tip Screen
    "ava": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.3)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("ava", "One black coffee. Three bucks.", "One black coffee.\nThree bucks.", 1.00),
    # rewritten after the recogniser heard "Plus the cut fee": a new line, not a retry
    Spoken("ava", "Plus a fee for the cup.", "Plus a fee for the cup.", 1.00),
    Spoken("ava", "And the lid fee.", "And the lid fee.", 1.00),
    Spoken("milo", "It's a lid.", "It's a lid.", 0.95),
    Spoken("ava", "And a service fee.", "And a service fee.", 1.00),
    Spoken("milo", "For what?", "For what?", 1.00),
    Spoken("ava", "For serving you.", "For serving you.", 0.95),
    Spoken("milo", "Fine. I'll pay cash.", "Fine. I'll pay cash.", 1.00),
    Spoken("ava", "That's a cash fee.", "That's a cash fee.", 1.00),  # rewritten: "Cash fee." was heard "Cashfy"
    Spoken("milo", "How much is the actual coffee?", "How much is\nthe actual coffee?", 1.00),
    Spoken("ava", "Oh, the coffee's free.", "Oh, the coffee's free.", 0.95),
    Spoken("milo", "Then what are the three bucks for?", "Then what are\nthe three bucks for?", 1.00),
    Spoken("ava", "The coffee fee.", "The coffee fee.", 0.95),
]
BEEP = (
    "A card payment terminal's short electronic beep, one bright double chirp as an amount is keyed in, close, "
    "dry, no voices, no music"
)
FEES = ("beep-1", "beep-2", "beep-3", "beep-4")  # cup, lid, service, cash: each a beep and a higher total
EFFECTS = [
    *(Sound(fee, BEEP, 0.6, 0.35, 0.30, seed=SEED + 1 + i) for i, fee in enumerate(FEES)),
    Sound(
        "tablet-swivel",
        "A payment tablet on a counter stand swiveled around to face a customer, a smooth plastic click, close, "
        "no voices, no music",
        1.0,
        0.6,
        0.32,
        seed=SEED + 5,
    ),
]
INTERVIEW = Interview(
    slug="cup-fee",
    title="Cup Fee — Comedy Cut 22",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Jessica and Liam; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.70,  # "The coffee fee.", a beat, then the tip tablet swivels round to him
    reaction_hold=1.70,  # the tablet faces him; his blink; the last frame
    end_card=0.0,  # no card: the tablet is the last frame
    font=NOTO_SANS_BOLD,  # the batch's caption face (Google Fonts), pinned under assets/fonts
)
LEAD = 1.15  # the still first second (arm A): nothing moves and no caption shows before 1.0 s
STARE = 0.90  # after "Cash fee.": the reader, then Milo, before he asks
HOLD = 1.30  # after "How much is the actual coffee?": Ava smiles and says nothing
READINGS = (  # the card reader's total: at the start, then on each beep
    ("$3.00", "black coffee"),
    ("$3.75", "+ cup fee"),
    ("$4.25", "+ lid fee"),
    ("$6.25", "+ service fee"),
    ("$7.75", "+ cash fee"),
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: each fee's beep lands just after the line naming it."""
    starts: list[float] = []
    fx: dict[str, float] = {}
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    def beep(fee: str, end: float, after: float) -> float:
        fx[fee] = end + 0.05
        return fx[fee] + effect[fee] + after

    cursor = say(0) + 0.45
    cursor = beep("beep-1", say(1), 0.20)
    cursor = beep("beep-2", say(2), 0.15)
    cursor = say(3) + 0.30
    cursor = beep("beep-3", say(4), 0.20)
    cursor = say(5) + 0.20
    cursor = say(6) + 0.45
    cursor = say(7) + 0.20
    cursor = beep("beep-4", say(8), STARE)
    cursor = say(9) + HOLD
    cursor = say(10) + 0.70
    cursor = say(11) + 0.30
    end = say(12)
    fx["tablet-swivel"] = end + INTERVIEW.reaction_after
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beeps, the swivel and the camera cuts: Ava and Milo shot and reverse, the reader on each fee."""
    p, fx = t.phrases, t.effects

    def before(i: int) -> float:
        return p[i]["start"] - 0.10

    return {
        "beeps": [fx[fee] for fee in FEES],
        "swivel_start": fx["tablet-swivel"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "two"},  # the still first second, then the order in the two-shot
            {"time": before(1), "angle": "barista"},
            {"time": fx["beep-1"] - 0.05, "angle": "reader"},  # the cup fee lands; the lid fee is heard over it
            {"time": before(3), "angle": "customer"},
            {"time": before(4), "angle": "barista"},
            {"time": fx["beep-3"] - 0.05, "angle": "reader"},
            {"time": before(5), "angle": "customer"},
            {"time": before(6), "angle": "barista"},
            {"time": before(7), "angle": "customer"},
            {"time": before(8), "angle": "barista"},
            {"time": fx["beep-4"] - 0.05, "angle": "reader"},
            {"time": fx["beep-4"] + 0.55, "angle": "customer"},  # he takes it in, then asks
            {"time": p[9]["end"] + 0.10, "angle": "barista"},  # the hold: she smiles and says nothing
            {"time": before(11), "angle": "customer"},
            {"time": before(12), "angle": "barista"},
            {"time": t.reaction - 0.10, "angle": "end"},  # the wide: the tablet swivels round to him
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

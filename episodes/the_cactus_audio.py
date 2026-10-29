#!/usr/bin/env python3
"""The Cactus — Comedy Cut 21: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 the_cactus_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its four effects, where the gags sit between the lines
(:func:`schedule`) and its camera cuts (:func:`extra`). The cast finally notices the potted cactus that has signed
every video since *Five Years* (ADR 0001): it is on the interviewer's desk, then by the coffee Ava sets down, then
on the bench before Milo gets there, then in the executive chair. The interviewer reads the code on its pot, and
ends up in the applicant's chair asking it the *Five Years* question. It blooms. The voices are the series' own:
the interviewer and the applicant of the interview series (Eric and Will), Ava and Milo of the café (Jessica and
Liam).
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 21039
VOICES = {  # the series' voices: Five Years (Eric, Will), Tip Screen (Jessica) and Culture Fit (Liam)
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.12)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.24)),
    "ava": Singer("cgSgspJ2msm6clMCkdW9", "Jessica", dict(stability=0.45, similarity_boost=0.75, style=0.3)),
    "milo": Singer("TX3LPaxmHKxFdv7VOQHJ", "Liam", dict(stability=0.45, similarity_boost=0.75, style=0.25)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("manager", "Has this always been here?", "Has this always\nbeen here?", 1.00),
    Spoken("candidate", "It came with the chair.", "It came with the chair.", 1.00),
    Spoken("milo", "Is that yours?", "Is that yours?", 1.00),
    Spoken("ava", "I thought it was yours.", "I thought it was yours.", 1.00),
    Spoken("milo", "I bought a coffee! I did everything right!", "I bought a coffee!\nI did everything right!", 1.05),
    Spoken("manager", "No.", "…No.", 0.90),
    Spoken(
        "manager",
        "S-R... one-oh-two-eight?",
        "S-R…\none-oh-two-eight?",
        0.95,
        seed=SEED + 20,  # the re-take
        heard=("SAR 1028",),  # approved by the operator 2026-10-29: the recognizer runs the spelled letters together
    ),
    Spoken("candidate", "That's its employee number.", "That's its\nemployee number.", 1.00),
    Spoken(
        "manager",
        "So... where do you see yourself in five years?",
        "So… where do you see\nyourself in five years?",
        0.95,
    ),
]
# Generated effects: requested seconds, longest kept after trimming, peak level in the mix; one seed each.
EFFECTS = [
    Sound(
        "cup",
        "A ceramic coffee cup set down on a wooden café counter, one soft clink, close, no voices, no music",
        1.0,
        0.6,
        0.34,
        seed=SEED,
    ),
    Sound(
        "flutter",
        "A single pigeon taking off from a park path, a short burst of wing flaps fading away, outdoors, no voices, "
        "no music",
        1.5,
        1.2,
        0.30,
        seed=SEED + 1,
    ),
    Sound(
        "swivel",
        "An old leather executive office chair slowly swivelling round, one long comedic creaking squeak, close, "
        "dry room, no voices, no music",
        2.0,
        1.8,
        0.40,
        seed=SEED + 2,
    ),
    Sound(
        "pop",
        "A single soft cartoon pop, like a flower bud bursting open, short and bright, no voices, no music",
        0.5,
        0.4,
        0.36,
        seed=SEED + 3,
    ),
]
INTERVIEW = Interview(
    slug="the-cactus",
    title="The Cactus — Comedy Cut 21",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Eric, Will, Jessica and Liam; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=1.30,  # the question hangs before the cut to the cactus: the hold before the punchline
    reaction_hold=1.00,  # the bloom and its pop, then the hard cut
    end_card=0.0,  # no card: the bloom is the last frame
)
LEAD = 0.80  # the interviewer looks up from the CV at the cactus before he speaks
SWING = 1.60  # the executive chair's slow turn, back to front, under the swivel's creak
REVEAL_HOLD = 1.20  # the cactus faces him, held, before "No."
PUSH = 1.20  # the push-in has the code filling the frame before he reads it
BLOOM_AFTER = 0.45  # from the cut to the cactus to the bloom
SEAT = (560, 1150, 2.0)  # the cactus in the executive chair: x, y of its pot's base on the seat, scale
PUSH_TO = 8.0  # the push-in's last scale, about the code on the pot: the code fills the frame
PUSH_Y = 1150  # where the push holds the code on screen: above the captions, the papers' code pushed off the bottom


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the gags sit in the gaps between lines."""
    starts: list[float] = []
    fx: dict[str, float] = {}
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    cursor = say(0) + 0.50
    end = say(1)
    fx["cup"] = end + 0.80  # the café: Ava sets the coffee down beside the cactus
    cursor = fx["cup"] + effect["cup"] + 0.45
    cursor = say(2) + 0.40
    end = say(3)
    cursor = end + 2.60  # they stare, the snap to the cactus; the park: Milo's double take, the pigeon's look
    end = say(4)
    fx["flutter"] = end + 0.70  # the pigeon looks at the cactus and leaves
    fx["swivel"] = fx["flutter"] + effect["flutter"] + 0.90  # the office: the chair's back, then the turn
    cursor = fx["swivel"] + max(effect["swivel"], SWING) + REVEAL_HOLD
    cursor = say(5) + 0.70  # the push-in starts on the cut
    cursor += PUSH
    cursor = say(6) + 0.45
    cursor = say(7) + 0.90  # the reverse: he sits in the applicant's chair
    end = say(8)
    fx["pop"] = end + INTERVIEW.reaction_after + BLOOM_AFTER
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The beats the picture keys on, and the cuts between the four places."""
    p, fx = t.phrases, t.effects
    cafe = fx["cup"] - 0.30
    park = p[3]["end"] + 1.20
    chair = fx["swivel"] - 0.80  # the chair's back, held, after the flutter has gone
    push = p[5]["end"] + 0.30
    sit = p[7]["end"] + 0.20
    return {
        "cafe_start": cafe,
        "cup_start": fx["cup"],
        "turn_start": p[3]["end"] + 0.10,  # both stare; the flower turns toward them
        "park_start": park,
        "flutter_start": fx["flutter"],
        "chair_start": chair,
        "swivel_start": fx["swivel"],
        "push_start": push,
        "sit_start": sit,
        "bloom_start": fx["pop"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},
            {"time": p[1]["start"] - 0.05, "angle": "candidate"},
            {"time": cafe, "angle": "cafe"},
            {"time": park, "angle": "park"},
            {"time": chair, "angle": "chair"},
            {"time": fx["swivel"] + SWING + 0.30, "angle": "manager"},
            {"time": push, "angle": "code"},
            {"time": sit, "angle": "applicant"},
            {"time": t.reaction, "angle": "bloom"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

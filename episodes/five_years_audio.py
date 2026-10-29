#!/usr/bin/env python3
"""Episode 06 — Five Years: generated dialogue and effects, resolved by the engine, and the timeline.

    python3 five_years_audio.py PROJECT --key-stdin < key [--engine path/to/scene-render]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its three chair effects, the pauses between the
lines with the loud squeak alone before the punchline (:func:`schedule`) and its camera cuts (:func:`extra`).
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

VOICES = {  # the series' settings: a steadier interviewer, a looser applicant
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.12)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.24)),
}
SCRIPT = [
    Spoken("manager", "Where do you see yourself in five years?", "Where do you see yourself\nin five years?", 1.00),
    Spoken("candidate", "In your chair.", "In your chair.", 1.00),
    Spoken("manager", "Bold. You want my job?", "Bold. You want my job?", 0.98),
    Spoken("candidate", "No. Just the chair.", "No. Just the chair.", 0.96),
]
PAUSES = (0.30, 0.34, 0.78)  # silence after each line but the last
SQUEAK_LEAD, SQUEAK_TAIL = 0.26, 0.16  # the loud squeak: after line 3 ends, before line 4 starts
LEAD = 0.62  # room for the opening squeak before the first line
SOFT_SQUEAK = 0.14
SPIN_AFTER_END_CARD = 0.10
# Generated effects: requested seconds, longest kept after trimming, peak level in the mix.
EFFECTS = [
    Sound(
        "chair-squeak",
        "A single short squeak of a cheap office chair as a person shifts their weight, close, dry room, "
        "no voices, no music",
        0.8,
        0.42,
        0.30,
    ),
    Sound(
        "chair-squeak-loud",
        "One loud, comedic, high-pitched creaking squeak of an old office chair, close microphone, "
        "dry room, no voices, no music",
        1.0,
        0.55,
        0.48,
    ),
    Sound(
        "swivel-spin",
        "A leather executive office chair spinning around twice on its swivel base, smooth rotating "
        "whoosh with a soft bearing whirr, no voices, no music",
        2.5,
        2.45,
        0.26,
    ),
]
INTERVIEW = Interview(
    slug="five-years",
    title="Five Years — The Interview 06",
    seed=52026,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Eric and Will; no reference-voice cloning.",
    room_tone_seed=52027,
    reaction_after=0.38,  # silence before the manager's reaction push-in
    reaction_hold=1.05,  # reaction length before the end card
    end_card=2.60,  # the spin and the five-year plan card
)


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """The lines with their pauses; the loud squeak alone in the pause before the punchline, the spin on the card.
    Line ends are taken as recorded (to the microsecond), as the gags were first timed."""
    starts, ends, cursor = [], [], LEAD
    for i, length in enumerate(speech):
        if i == 3:
            cursor = ends[2] + SQUEAK_LEAD + effect["chair-squeak-loud"] + SQUEAK_TAIL
        starts.append(cursor)
        ends.append(round(cursor + length, 6))
        cursor = cursor + length + (PAUSES[i] if i < len(PAUSES) else 0.0)
    ending = ends[-1] + INTERVIEW.reaction_after + INTERVIEW.reaction_hold
    return Schedule(
        starts,
        {
            "chair-squeak": SOFT_SQUEAK,
            "chair-squeak-loud": ends[2] + SQUEAK_LEAD,
            "swivel-spin": ending + SPIN_AFTER_END_CARD,
        },
    )


def extra(t: Timing) -> dict:
    """The squeaks and the spin, the reaction and end card, and the camera cuts."""
    p, fx = t.phrases, t.effects
    return {
        "squeak_soft_start": fx["chair-squeak"],
        "squeak_loud_start": fx["chair-squeak-loud"],
        "spin_start": fx["swivel-spin"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "wide"},
            {"time": p[1]["start"] - 0.15, "angle": "candidate"},
            {"time": p[2]["start"] - 0.16, "angle": "wide"},
            {"time": fx["chair-squeak-loud"] - 0.12, "angle": "candidate-punchline"},
            {"time": t.reaction, "angle": "manager-reaction"},
            {"time": t.ending, "angle": "candidate-ending"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

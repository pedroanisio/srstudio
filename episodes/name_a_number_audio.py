#!/usr/bin/env python3
"""Name a Number — Comedy Cut 24: generated dialogue and effects, resolved by the engine, and the timeline.

    srstudio record name-a-number PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview` (resolve, the speech check, trimming, levelling, the room tone and
``dialogue.json``); this file is the episode: its script, its effects, where the scribbles and the paper flip sit
between the lines (:func:`schedule`) and its camera cuts (:func:`extra`). The salary talk: whoever names a number
first loses, so the interviewer and the applicant say everything but a number, then write theirs down and turn the
papers over. The opening second is still (the ``sp-hook_motion`` test's arm A): the job ad on the desk, with the
first line after :data:`LEAD`. The voices are the Interview's own, Eric (the interviewer) and Will (the applicant).
"""

from __future__ import annotations

from srstudio.interview import NOTO_SANS_BOLD, Interview, Schedule, Sound, Spoken, Timing, main
from srstudio.song import Singer

SEED = 24051
VOICES = {  # the Interview's settings: a steadier interviewer, a looser applicant
    "manager": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.55, similarity_boost=0.75, style=0.12)),
    "candidate": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.42, similarity_boost=0.75, style=0.24)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("manager", "So. What number did you have in mind?", "So. What number\ndid you have in mind?", 1.00),
    Spoken("candidate", "What's the range?", "What's the range?", 1.00),
    Spoken("manager", "What would make you happy?", "What would\nmake you happy?", 1.00),
    Spoken("candidate", "What would make you happy?", "What would\nmake you happy?", 0.96),
    Spoken("manager", "I asked first.", "I asked first.", 1.00),
    Spoken("candidate", "The ad said competitive.", "The ad said\ncompetitive.", 1.00),
    Spoken("manager", "Extremely competitive.", "Extremely competitive.", 0.96),
    Spoken("candidate", "Competitive with what?", "Competitive\nwith what?", 1.00),
    Spoken("manager", "Other ads.", "Other ads.", 0.95),
    Spoken("manager", "Tell you what. We both write it down.", "Tell you what.\nWe both write it down.", 1.00),
    Spoken("manager", "Great. We're aligned.", "Great.\nWe're aligned.", 0.96),
    Spoken("candidate", "Are we?", "Are we?", 1.00),
    Spoken("manager", "Competitively.", "Competitively.", 0.95),
]
EFFECTS = [
    Sound(
        "scribble",
        "Two ballpoint pens scribbling fast on paper on a wooden desk at the same time, a few quick strokes, close, "
        "dry office room, no voices, no music",
        1.6,
        1.3,
        0.30,
        seed=SEED + 1,
    ),
    Sound(
        "paper-flip",
        "Two sheets of paper slapped face up onto a wooden desk at once, one crisp flat slap, close, dry room, "
        "no voices, no music",
        0.6,
        0.4,
        0.36,
        seed=SEED + 2,
    ),
]
INTERVIEW = Interview(
    slug="name-a-number",
    title="Name a Number — Comedy Cut 24",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=EFFECTS,
    voice_note="ElevenLabs premade voices Eric and Will; no reference-voice cloning.",
    room_tone_seed=SEED + 10,
    reaction_after=0.50,  # "Competitively.", then the wide holds on the two of them
    reaction_hold=1.60,  # the interviewer's satisfied nod; the applicant does not move; the last frame
    end_card=0.0,  # no card: the wide is the last frame
    font=NOTO_SANS_BOLD,  # the batch's caption face (Google Fonts), pinned under assets/fonts
)
LEAD = 1.15  # the still first second (arm A): the job ad, still, and no caption before 1.0 s
ECHO = 0.55  # after "What would make you happy?" said back: the interviewer takes it in
BEAT = 0.70  # after "Other ads.": the applicant takes that in
REVEAL = 1.55  # the two papers face up, read in the insert, before "Great. We're aligned."


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts and effect starts from the clip lengths: the scribbles and the flip between lines 10 and 11."""
    starts: list[float] = []
    fx: dict[str, float] = {}
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    cursor = say(0) + 0.35
    cursor = say(1) + 0.30
    cursor = say(2) + 0.25
    cursor = say(3) + ECHO
    cursor = say(4) + 0.30
    cursor = say(5) + 0.30
    cursor = say(6) + 0.30
    cursor = say(7) + 0.25
    cursor = say(8) + BEAT
    cursor = say(9) + 0.15
    fx["scribble"] = cursor
    fx["paper-flip"] = cursor + effect["scribble"] + 0.10
    cursor = fx["paper-flip"] + REVEAL
    cursor = say(10) + 0.35
    cursor = say(11) + 0.45
    say(12)
    return Schedule(starts, fx)


def extra(t: Timing) -> dict:
    """The scribble, the flip and the camera cuts: the ad, the interviewer and the applicant, the papers."""
    p, fx = t.phrases, t.effects

    def before(i: int) -> float:
        return p[i]["start"] - 0.10

    return {
        "scribble_start": fx["scribble"],
        "flip_start": fx["paper-flip"],
        "reaction_start": t.reaction,
        "end_card_start": t.ending,
        "camera_cuts": [
            {"time": 0, "angle": "ad"},  # the still first second: the job ad on the desk; his question over it
            {"time": before(1), "angle": "candidate"},
            {"time": before(2), "angle": "manager"},
            {"time": before(3), "angle": "candidate"},
            {"time": before(4), "angle": "manager"},
            {"time": before(5), "angle": "candidate"},
            {"time": before(6), "angle": "manager"},
            {"time": before(7), "angle": "candidate"},
            {"time": before(8), "angle": "manager"},
            {"time": before(9), "angle": "wide"},  # "We both write it down": the two of them, heads down
            {"time": fx["paper-flip"] - 0.04, "angle": "papers"},  # the reveal: both papers face up
            {"time": before(10), "angle": "manager"},
            {"time": before(11), "angle": "candidate"},
            {"time": before(12), "angle": "wide"},  # "Competitively.": the wide holds to the end
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

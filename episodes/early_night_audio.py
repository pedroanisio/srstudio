#!/usr/bin/env python3
"""Early Night: generated dialogue, resolved by the engine, and the timeline.

    srstudio record early-night PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). A narrator announces an early night over a woman on her phone, and goes on narrating as the clock
runs away from him: a shovel, Bulgarian beekeepers, her opinions about the beekeepers. Brian is the narrator and Laura
is Juno, who has one line, to nobody. There is no music: the reel's foley is synthesised in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 41601
VOICES = {
    "narrator": Singer("nPczCjzI2devNBz1zQrb", "Brian", dict(stability=0.6, similarity_boost=0.75, style=0.2)),
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.55, similarity_boost=0.75, style=0.1)),
}
SCRIPT = [  # role, text, caption, speed
    Spoken("narrator", "Tonight: bed by ten.", "Tonight: bed by ten.", 1.0),
    Spoken("narrator", "Just one more.", "Just one more.", 1.0),
    Spoken(
        "narrator", "Just one more. About Bulgarian beekeepers.", "Just one more. About\nBulgarian beekeepers.", 1.05
    ),
    Spoken("narrator", "She has opinions about the beekeepers.", "She has opinions\nabout the beekeepers.", 1.05),
    Spoken(
        "juno",
        "And that is why you never sand against the rust.",
        "...and that is why you never\nsand against the rust.",
        0.95,
    ),
    Spoken("narrator", "She has work at seven.", "She has work at seven.", 0.95),
]
INTERVIEW = Interview(
    slug="early-night",
    title="Early Night",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Brian and Laura; no reference-voice cloning. Foley synthesised; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=1.5,  # "seven.", the phone goes down, the dark, and then the alarm
    reaction_hold=1.25,  # the eye; the last frame
    end_card=0.0,
    font=SOFT.google_font(),
)
LEAD = 0.05  # the thumb is already going on the first frame
CUT_LEAD = 0.3  # a new hour reads this long before the narrator speaks over it
SCROLL = 0.75  # the shovel on her phone, after "Just one more."
COMMENT = 1.6  # her comment, typed in silence


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: one hour to a line, her comment in silence, the alarm after a dark hold."""
    starts: list[float] = []
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    cursor = say(0) + 0.15 + CUT_LEAD
    cursor = say(1) + SCROLL + CUT_LEAD
    cursor = say(2) + 0.35 + CUT_LEAD
    cursor = say(3) + COMMENT + CUT_LEAD
    cursor = say(4) + 0.25
    say(5)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The cuts: each hour just before its line, the comment after hers, the phone down, then the alarm."""
    p = t.phrases
    return {
        "hours": [round(p[i]["start"] - CUT_LEAD, 3) for i in (1, 2, 3, 4)],
        "comment_start": p[3]["end"] + 0.05,
        "down_start": p[5]["end"] + 0.2,
        "alarm_start": t.reaction,
        "camera_cuts": [{"time": 0, "angle": "bed"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

#!/usr/bin/env python3
"""Hang Out: generated dialogue, resolved by the engine, and the timeline.

    srstudio record hang-out PROJECT [--engine path/to/scene-render]   # the key from ELEVENLABS_API_KEY

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The pipeline is :mod:`srstudio.interview`; this file is the episode: its script, and where each line sits
(:func:`schedule`). Two best friends agree they have to catch up, and offer each other March. The years flick past, one
"This week's crazy." at a time, and the line wears down to one word. Fifty-odd years on they are on a bench at last, and
it is so good to see each other, and they take out their phones. Juno is Laura, Pip is Will, the old lines are the same
voices taken slower. There is no music: the reel's foley is synthesised in the build.
"""

from __future__ import annotations

from srstudio.interview import Interview, Schedule, Spoken, Timing, main
from srstudio.song import Singer
from srstudio.styles import SOFT

SEED = 40601
VOICES = {
    "juno": Singer("FGY2WhTYpPnrIDTdsKH5", "Laura", dict(stability=0.35, similarity_boost=0.75, style=0.45)),
    "pip": Singer("bIHbv24MWmeRgasZH58o", "Will", dict(stability=0.30, similarity_boost=0.75, style=0.45)),
}
CRAZY = "This week's crazy."
SCRIPT = [  # role, text, caption, speed
    Spoken("juno", "We have to catch up!", "We HAVE to catch up!", 1.05),
    Spoken("pip", "So bad! I'm free... March?", "So bad! I'm free...\nMarch?", 1.05),
    Spoken("juno", "I'm away in March.", "I'm away in March.", 1.05),
    Spoken("juno", CRAZY, CRAZY, 1.05),
    Spoken("pip", CRAZY, CRAZY, 1.05),
    Spoken("juno", CRAZY, CRAZY, 0.92),
    Spoken("pip", "Week's crazy.", "Week's crazy.", 0.88),
    Spoken("juno", "Crazy.", "Crazy.", 0.85),
    Spoken("pip", "So good to see you.", "So good to see you.", 0.78),
    Spoken("juno", "We should do this more often!", "We should do this\nmore often!", 0.82),
    Spoken("pip", "I'm free... March?", "I'm free...\nMarch?", 0.78),
]
INTERVIEW = Interview(
    slug="hang-out",
    title="Hang Out",
    seed=SEED,
    voices=VOICES,
    lines=SCRIPT,
    effects=[],
    voice_note="ElevenLabs premade voices Laura and Will; no reference-voice cloning. Foley synthesised; no music.",
    room_tone_seed=SEED + 10,
    reaction_after=0.45,  # "March?", then the cut to the two phones
    reaction_hold=1.6,  # the phones; the last frame
    end_card=0.0,
    font=SOFT.google_font(),
)
LEAD = 0.05  # already mid-sentence on the first frame
YEAR_HOLD = 0.32  # the new year reads before the line
OUT = 1.15  # "more often!", then the phones come out, in silence
BENCH_LEAD = 0.35  # the cut to the bench, this long before "So good to see you."


def schedule(speech: list[float], effect: dict[str, float]) -> Schedule:
    """Line starts from the clip lengths: the exchange tight, each year a cut, then the bench."""
    starts: list[float] = []
    cursor = LEAD

    def say(i: int) -> float:
        starts.append(cursor)
        return cursor + speech[i]

    cursor = say(0) + 0.10
    cursor = say(1) + 0.12
    cursor = say(2) + 0.45 + YEAR_HOLD
    for i, rest in ((3, 0.32), (4, 0.30), (5, 0.26), (6, 0.22)):
        cursor = say(i) + rest + YEAR_HOLD
    cursor = say(7) + 0.75  # the last "Crazy.", and then nothing for a beat
    cursor = say(8) + 0.25
    cursor = say(9) + OUT
    say(10)
    return Schedule(starts, {})


def extra(t: Timing) -> dict:
    """The cuts: a year before each of lines 4 to 8, the bench before line 9, the phones after the last line."""
    p = t.phrases
    return {
        "years": [round(p[i]["start"] - YEAR_HOLD, 3) for i in range(3, 8)],
        "bench_start": p[8]["start"] - BENCH_LEAD,
        "phones_start": p[9]["end"] + 0.35,
        "reaction_start": t.reaction,
        "camera_cuts": [{"time": 0, "angle": "two"}],
    }


if __name__ == "__main__":
    raise SystemExit(main(INTERVIEW, schedule, extra))

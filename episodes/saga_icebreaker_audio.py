#!/usr/bin/env python3
"""Saga — Icebreaker: the dark lord opens the team meeting with fun facts, and his fun fact ends the meeting.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_icebreaker_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _saga import Reel, effect, line, record
from srstudio.saga_reel import Entry, Move, Place, Stage
from srstudio.saga_sets import Panel

TEAM = (Place("seven", 220), Place("gloom", 540), Place("droid", 860, flip=True))
ICE = Panel(0, "ICEBREAKER", "One fun fact about yourself.", tone="gold")
TAKES = (
    line("01", "narrator", "Is there anything worse than a team icebreaker?", 0.3),
    line("02", "gloom", "Icebreaker. One fun fact about yourself.", 0.3),
    line("03", "seven", "I have never hit a target.", 0.2),
    line("04", "gloom", "We know.", 0.4),
    line("05", "droid", "I am technically a toaster!", 0.2),
    line("06", "gloom", "We know.", 0.4),
    line("07", "seven", "And your fun fact, my lord?", 0.3),
    line("08", "gloom", "I can hear your thoughts.", 1.8),
    line("09", "seven", "Great icebreaker, my lord!", 0.3),
    line("10", "gloom", "Thank you, Seven.", 0.4),
    line("11", "gloom", "Now say it in your head.", 1.0),
    effect("12", "[ALARM]", "A short spaceship alarm klaxon, two blasts, muffled", 1.2, 0.3, peak=0.4),
    line("13", "narrator", "The Directorate no longer runs icebreakers. It runs the silent meeting.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def at(*panels: Panel, **kw) -> Stage:
        return Stage("bridge", cast=TEAM, panels=panels, **kw)

    seven = Panel(0, "SEVEN · FUN FACT", "Has never hit a target.", face="seven")
    droid = Panel(0, "DROID · FUN FACT", "Technically a toaster.", face="droid")
    gloom = Panel(0, "LORD GLOOM · FUN FACT", "Can hear your thoughts.", tone="alert", face="gloom")
    heard = Panel(0, "THOUGHT DETECTED", "Seven: this meeting could have been an email.", tone="alert", face="seven")
    return {
        "01": Stage("bridge", cast=TEAM),
        "02": at(ICE),
        "03": at(seven),
        "04": at(seven),
        "05": at(droid),
        "06": at(droid),
        "07": at(ICE),
        "08": at(gloom, move=Move("push", 0, 1.15, 540, 850, until=t["08"].duration)),
        "09": at(heard, move=Move("crash", 0.05, 1.25, 220, 800)),
        "10": at(heard),
        "11": at(heard, move=Move("push", 0, 1.15, 540, 850, until=t["11"].duration)),
        "12": at(heard, shake=((0.0, t["12"].duration),)),
        "13": Stage(
            entry=Entry(
                "Icebreaker", "A game that helps a team get to know each other. Under Lord Gloom, it works too well."
            )
        ),
    }


REEL = Reel(
    slug="saga-icebreaker",
    number="S8",
    title="Icebreaker — Saga 08",
    description="Portrait space-opera parody: the dark lord opens the team meeting with an icebreaker, and his fun "
    "fact is the last one anyone shares. Native vector animation; ElevenLabs voices, effect and music bed.",
    accessible="Cartoon space opera: an enforcer, a dark lord and a copper service droid stand on the bridge while "
    "a hologram shows each fun fact, then the thought the enforcer had; word-by-word captions.",
    takes=TAKES,
    hook="Is there anything worse than a team icebreaker?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))

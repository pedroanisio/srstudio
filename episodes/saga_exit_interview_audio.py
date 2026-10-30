#!/usr/bin/env python3
"""Saga — Exit Interview: an enforcer resigns, and the dark lord's retention plan is a pizza party.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_exit_interview_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _saga import Reel, line, record
from srstudio.saga_reel import Entry, Move, Place, Stage
from srstudio.saga_sets import Panel

TWO_SHOT = (Place("gloom", 300), Place("seven", 780, flip=True))
EXIT = Panel(0, "EXIT INTERVIEW", "Enforcer Seven. Notice period: today.")
TAKES = (
    line("01", "narrator", "Why does nobody ever quit the Directorate?", 0.3),
    line("02", "gloom", "Seven. You are leaving us?", 0.3),
    line("03", "seven", "Yes, my lord. I got another offer.", 0.3),
    line("04", "gloom", "Is it the pay?", 0.2),
    line("05", "seven", "No.", 0.2),
    line("06", "gloom", "The hours?", 0.2),
    line("07", "seven", "No.", 0.2),
    line("08", "gloom", "The airlock?", 0.3),
    line("09", "seven", "You threw Gary out of it.", 0.4),
    line("10", "gloom", "Gary was not a culture fit.", 1.0),
    line("11", "gloom", "What if we threw you a pizza party?", 1.6),
    line("12", "seven", "What kind of pizza?", 1.2),
    line("13", "narrator", "Enforcer Seven stayed. The pizza was a hologram. The airlock was not.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def at(*panels: Panel, **kw) -> Stage:
        return Stage("bridge", cast=TWO_SHOT, panels=panels, **kw)

    reasons = Panel(0, "REASON FOR LEAVING", "Pay? Hours? Airlock?")
    airlock = Panel(0, "AIRLOCK", "Used for: Gary.", tone="alert", face="gary")
    fit = Panel(0, "GARY", "Not a culture fit.", tone="alert", face="gary")
    pizza = Panel(0, "RETENTION PLAN", "One pizza party. Attendance mandatory.", tone="gold")
    return {
        "01": Stage("bridge", cast=TWO_SHOT),
        "02": at(EXIT),
        "03": at(EXIT),
        "04": at(reasons),
        "05": at(reasons),
        "06": at(reasons),
        "07": at(reasons),
        "08": at(reasons, move=Move("push", 0, 1.12, 300, 900, until=t["08"].duration)),
        "09": at(airlock, move=Move("crash", 0.05, 1.25, 780, 800)),
        "10": at(fit),
        "11": at(pizza, move=Move("push", 0, 1.15, 300, 850, until=t["11"].duration)),
        "12": at(pizza, move=Move("crash", 0.05, 1.3, 780, 760)),
        "13": Stage(
            entry=Entry("Retention", "The Directorate keeps nine in ten enforcers. The tenth is kept in the airlock.")
        ),
    }


REEL = Reel(
    slug="saga-exit-interview",
    number="S9",
    title="Exit Interview — Saga 09",
    description="Portrait space-opera parody: an enforcer resigns from the Directorate, and the dark lord's "
    "retention plan is a pizza party. Native vector animation; ElevenLabs voices and music bed.",
    accessible="Cartoon space opera: a dark lord holds an exit interview with an armoured enforcer on the bridge, "
    "a hologram listing the reasons for leaving; word-by-word captions.",
    takes=TAKES,
    hook="Why does nobody ever quit the Directorate?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))

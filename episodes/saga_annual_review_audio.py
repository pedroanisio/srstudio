#!/usr/bin/env python3
"""Saga 02 — Annual Review: nine thousand shots, zero hits, and the Directorate makes him enforcer of the year;
the ones who hit things are not discussed.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_annual_review_audio.py PROJECT --font DIR

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

TWO_SHOT = (Place("gloom", 300), Place("seven", 780, flip=True))
REVIEW = Panel(0, "ANNUAL REVIEW", "Enforcer Seven. Blasters division.")
TAKES = (
    line("01", "narrator", "Why do the Directorate's enforcers never hit anything?", 0.3),
    line("02", "gloom", "Your annual review, Seven.", 0.3),
    line("03", "gloom", "Shots fired this year: nine thousand.", 0.3),
    line("04", "gloom", "Hits: zero.", 0.6),
    line("05", "seven", "I can explain, my lord.", 0.3),
    line("06", "gloom", "Zero damage. Zero complaints. Zero paperwork.", 0.3),
    line("07", "gloom", "Enforcer of the year.", 0.2),
    effect("08", "[FANFARE]", "A short tinny triumphant trumpet fanfare from a cheap speaker", 1.5, 0.2, peak=0.45),
    line("09", "seven", "What happens to the ones who hit things?", 1.6),
    line("10", "gloom", "We don't talk about Gary.", 1.0),
    line("11", "narrator", "Gary hit the exhaust port of the battle cube. From the inside. By accident.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def at(*panels: Panel, **kw) -> Stage:
        return Stage("bridge", cast=TWO_SHOT, panels=panels, **kw)

    shots = Panel(0, "SHOTS FIRED: 9,000")
    hits = Panel(0, "SHOTS FIRED: 9,000", "Hits: 0", tone="alert")
    zero = Panel(0, "DAMAGE: 0", "Complaints: 0. Paperwork: 0.", tone="ok")
    award = Panel(0, "ENFORCER OF THE YEAR", "Seven. For outstanding restraint.", tone="gold")
    return {
        "01": Stage("bridge", cast=TWO_SHOT),
        "02": at(REVIEW),
        "03": at(shots),
        "04": at(hits, move=Move("crash", 0.1, 1.25, 450, 420)),
        "05": at(hits),
        "06": at(zero),
        "07": at(award),
        "08": at(award, move=Move("push", 0, 1.15, 780, 950, until=t["08"].duration)),
        "09": at(award),
        "10": at(
            Panel(0, "GARY", "Hit one thing. Once.", tone="alert", face="gary"), move=Move("crash", 0.05, 1.3, 450, 500)
        ),
        "11": Stage(
            entry=Entry("Gary", "Former enforcer. Hit one thing in his whole career. It was the thing that mattered.")
        ),
    }


REEL = Reel(
    slug="saga-annual-review",
    number="S2",
    title="Annual Review — Saga 02",
    description="Portrait space-opera parody: an enforcer who has never hit anything gets the best review in the "
    "Directorate. Native vector animation; ElevenLabs voices, effect and music bed.",
    accessible="Cartoon space opera: a dark lord gives an armoured enforcer his annual review on a hologram; "
    "word-by-word captions.",
    takes=TAKES,
    hook="Why do the Directorate's enforcers never hit anything?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))

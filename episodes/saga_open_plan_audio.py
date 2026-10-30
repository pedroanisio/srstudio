#!/usr/bin/env python3
"""Saga 07 — Open Plan: the trash compactor's walls are closing in because the workspace is being upgraded, and
Seven is only in on Tuesdays.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_open_plan_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _saga import Reel, effect, line, record
from srstudio.saga_reel import Entry, Move, Place, Stage
from srstudio.saga_sets import FLOOR, Panel

STUCK = (Place("juno", 360), Place("rook", 730, flip=True))
WITH_SEVEN = (  # Seven stands a step back between them
    Place("seven", 545, FLOOR - 40, scale=0.85),
    Place("juno", 320, scale=0.95),
    Place("rook", 770, flip=True, scale=0.95),
)
FACILITIES = Panel(0, "FACILITIES", "Your workspace is being upgraded!", face="droid")
TICKET = Panel(0, "TICKET #4471", "Position in queue: 4,470", tone="alert", face="droid")
DONE = Panel(0, "OPEN PLAN COMPLETE", "Desks: 0 · Synergy: 100%", tone="ok")
STEP = 50  # px the walls close per shot
TAKES = (
    line("01", "narrator", "Why are the walls of this trash compactor closing in?", 0.3),
    line("02", "droid", "Good news! Your workspace is being upgraded.", 0.3),
    line("03", "rook", "Stop the walls!", 0.2, mood="angry"),
    line("04", "droid", "Please submit a facilities ticket.", 0.3),
    line("05", "juno", "How long does that take?", 0.2),
    line("06", "droid", "About nine years.", 0.6),
    effect("07", "[CLUNK]", "A heavy metal wall slamming to a stop with a hollow clang", 1.0, 0.8, peak=0.6),
    line("08", "seven", "Morning. Is this desk taken?", 0.3),
    line("09", "rook", "This is a trash compactor.", 0.3),
    line("10", "seven", "I'm only in on Tuesdays.", 1.2),
    line(
        "11", "narrator", "The compactor is now the Directorate's most productive office. Nobody can leave early.", 1.2
    ),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def squeeze(n: int, end: float) -> dict:
        return {"walls": (0.0, end), "travel": STEP, "start_px": n * STEP}

    def room(n: int, take: str, *panels: Panel, **kw) -> Stage:
        return Stage("compactor", squeeze(n, t[take].duration), cast=STUCK, panels=panels, **kw)

    return {
        "01": room(0, "01"),
        "02": room(1, "02", FACILITIES),
        "03": room(2, "03", FACILITIES, move=Move("crash", 0.05, 1.2, 730, 1150)),
        "04": room(3, "04", Panel(0, "FACILITIES", "Please submit a ticket.", face="droid")),
        "05": Stage("compactor", {"start_px": 200}, cast=STUCK, panels=(TICKET,)),
        "06": Stage(
            "compactor",
            {"start_px": 200},
            cast=STUCK,
            panels=(TICKET,),
            move=Move("push", 0, 1.1, 540, 1000, until=t["06"].duration),
        ),
        "07": Stage(
            "compactor",
            {"walls": (0.0, 0.25), "travel": 60, "start_px": 200},
            cast=STUCK,
            panels=(DONE,),
            shake=((0.25, 0.6),),
        ),
        "08": Stage("compactor", {"start_px": 260, "door": 0.0}, cast=WITH_SEVEN, panels=(DONE,)),
        "09": Stage("compactor", {"start_px": 260}, cast=WITH_SEVEN, move=Move("crash", 0.05, 1.2, 760, 1150)),
        "10": Stage(
            "compactor",
            {"start_px": 260},
            cast=WITH_SEVEN,
            panels=(Panel(0, "HOT DESK BOOKED", "Tuesdays. Bring your own air.", tone="gold"),),
        ),
        "11": Stage(
            entry=Entry(
                "Open plan", "A workspace with no walls. Achieved here by bringing the walls very close together."
            )
        ),
    }


REEL = Reel(
    slug="saga-open-plan",
    number="S7",
    title="Open Plan — Saga 07",
    description="Portrait space-opera parody: the trash compactor walls are closing in, and facilities calls it an "
    "upgrade. Native vector animation; ElevenLabs voices, effect and music bed.",
    accessible="Cartoon space opera: a young hero and a smuggler in a trash compactor as the walls close, a droid on "
    "a hologram, and an enforcer who walks in looking for a desk; word-by-word captions.",
    takes=TAKES,
    hook="Why are the walls of this trash compactor closing in?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))

#!/usr/bin/env python3
"""Saga — Expense Report: the dark lord files a planet on expenses, and the service droid wants a photo of it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_expense_report_audio.py PROJECT --font DIR

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

DESK = (Place("gloom", 300), Place("droid", 780, flip=True))
CLAIM = Panel(0, "EXPENSE CLAIM", "One planet. Destroyed.")
TAKES = (
    line("01", "narrator", "Who approves a dark lord's expenses?", 0.3),
    line("02", "gloom", "Expense report. One planet, destroyed.", 0.3),
    line("03", "droid", "Lovely! Do you have a receipt?", 0.3),
    line("04", "gloom", "It exploded. That is the receipt.", 0.4),
    line("05", "droid", "The cape is personal.", 0.2),
    line("06", "droid", "The helmet is personal.", 0.2),
    line("07", "droid", "The breathing machine is personal.", 0.3),
    line("08", "gloom", "I need it to live!", 0.3),
    line("09", "droid", "So it's personal.", 0.8),
    line("10", "gloom", "And the planet?", 0.3),
    line("11", "droid", "Approved! Just attach a photo of the planet.", 1.6),
    effect("12", "[SLOW CREAK]", "A single slow creak of a leather glove tightening into a fist", 1.2, 0.3, peak=0.4),
    line("13", "droid", "Then it's personal.", 1.2),
    line("14", "narrator", "Lord Gloom is still paying off the planet on his own card. Minimum payments.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def at(*panels: Panel, **kw) -> Stage:
        return Stage("bridge", cast=DESK, panels=panels, **kw)

    receipt = Panel(0, "RECEIPT REQUIRED", "Claims without a receipt are personal.", tone="alert")
    cape = Panel(0, "CAPE", "Personal.", tone="alert")
    helmet = Panel(0, "HELMET", "Personal.", tone="alert")
    lungs = Panel(0, "BREATHING MACHINE", "Personal.", tone="alert")
    approved = Panel(0, "PLANET: APPROVED", "Attach a photo of the planet.", tone="ok")
    personal = Panel(0, "PLANET: PERSONAL", "Charged to your own card.", tone="alert")
    return {
        "01": Stage("bridge", cast=DESK),
        "02": at(CLAIM),
        "03": at(receipt),
        "04": at(receipt, move=Move("push", 0, 1.12, 300, 900, until=t["04"].duration)),
        "05": at(cape),
        "06": at(helmet),
        "07": at(lungs, move=Move("crash", 0.05, 1.25, 300, 700)),
        "08": at(lungs),
        "09": at(lungs),
        "10": at(CLAIM),
        "11": at(approved),
        "12": at(approved, move=Move("push", 0, 1.15, 300, 800, until=t["12"].duration)),
        "13": at(personal, move=Move("crash", 0.05, 1.3, 780, 800)),
        "14": Stage(
            entry=Entry(
                "Expense Policy",
                "Planets are reimbursable with a photo of the planet. The photo must be taken after the claim.",
            )
        ),
    }


REEL = Reel(
    slug="saga-expense-report",
    number="S11",
    title="Expense Report — Saga 11",
    description="Portrait space-opera parody: a dark lord files a destroyed planet on expenses, and the service "
    "droid needs a receipt. Native vector animation; ElevenLabs voices, effect and music bed.",
    accessible="Cartoon space opera: a dark lord in black armour argues with a cheerful copper service droid on the "
    "bridge while a hologram stamps each claim personal; word-by-word captions.",
    takes=TAKES,
    hook="Who approves a dark lord's expenses?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))

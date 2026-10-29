#!/usr/bin/env python3
"""Saga 04 — Card Reader: a smuggler buys one drink in the cantina, and the droid behind the bar turns the card
reader round.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_card_reader_audio.py PROJECT --font DIR

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

BAR = (Place("droid", 700, behind=True), Place("rook", 330))
TIP = Panel(0, "ADD A TIP?", "20%  ·  25%  ·  30%", tone="gold")
MORE = Panel(0, "ADD A TIP?", "40%  ·  60%  ·  Your ship", tone="gold")
SURE = Panel(0, "ARE YOU SURE?", "4 bounty hunters are watching.", tone="alert")
TAKES = (
    line("01", "narrator", "What does a smuggler fear more than bounty hunters?", 0.3),
    line("02", "rook", "One drink. That's it.", 0.3),
    line("03", "droid", "Lovely! Just tap here.", 0.4),
    line("04", "rook", "A tip? You poured it.", 0.3),
    line("05", "droid", "And I didn't report you, sir!", 0.5),
    line("06", "rook", "No tip.", 0.2),
    effect("07", "[BEEP]", "A single flat low error beep from a payment terminal", 0.6, 1.6, peak=0.45),
    line("08", "rook", "Fine. The biggest one.", 0.4),
    line("09", "droid", "Thank you! Your receipt has been sent to the Directorate.", 1.2),
    line("10", "narrator", "Most smugglers are caught by their receipts. The rest are caught by the tip screen.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def bar(*panels: Panel, **kw) -> Stage:
        return Stage("cantina", cast=BAR, panels=panels, **kw)

    stare = ((0.0, t["07"].duration),)
    return {
        "01": bar(),
        "02": bar(),
        "03": bar(TIP),
        "04": bar(TIP, move=Move("crash", 0.05, 1.2, 330, 1100)),
        "05": bar(MORE),
        "06": bar(MORE),
        "07": Stage(
            "cantina",
            {"stare": stare},
            cast=BAR,
            panels=(SURE,),
            move=Move("push", 0, 1.12, 330, 1100, until=t["07"].duration),
        ),
        "08": bar(Panel(0, "TIP: YOUR SHIP", "Thank you for your generosity!", tone="ok")),
        "09": bar(
            Panel(0, "RECEIPT SENT", "To: The Directorate. Cc: Gary.", tone="alert"),
            move=Move("crash", 0.1, 1.25, 700, 1000),
        ),
        "10": Stage(
            entry=Entry(
                "Tipping",
                "A custom older than the galaxy and twice as hard to leave. Suggested amounts start at everything.",
            )
        ),
    }


REEL = Reel(
    slug="saga-card-reader",
    number="S4",
    title="Card Reader — Saga 04",
    description="Portrait space-opera parody: a smuggler buys one drink in a rough cantina and meets the tip screen. "
    "Native vector animation; ElevenLabs voices, effect and music bed.",
    accessible="Cartoon space opera: a smuggler at a cantina bar, a droid bartender and a hologram tip screen while "
    "the regulars stare; word-by-word captions.",
    takes=TAKES,
    hook="What does a smuggler fear more than bounty hunters?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

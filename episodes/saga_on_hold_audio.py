#!/usr/bin/env python3
"""Saga — On Hold: the hero calls Directorate support to report her destroyed planet, and support is very sorry.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_on_hold_audio.py PROJECT --font DIR

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

ALONE = (Place("juno", 760, flip=True),)
CALL = Panel(0, "DIRECTORATE SUPPORT", "Connected. How can I help?", face="droid")
TAKES = (
    line("01", "narrator", "Who do you call when your planet gets destroyed?", 0.3),
    line("02", "juno", "Hi. My planet was destroyed.", 0.3),
    line("03", "droid", "I'm so sorry! Have you tried restarting it?", 0.4),
    line("04", "juno", "It's in pieces.", 0.3),
    line("05", "droid", "Please hold.", 0.2),
    effect(
        "06",
        "[HOLD MUSIC]",
        "Tinny cheerful hold music from a cheap phone speaker, a looping jingle",
        2.5,
        0.3,
        peak=0.4,
    ),
    line("07", "droid", "Your planet is important to us.", 0.4),
    line("08", "juno", "Can I speak to a human?", 1.6),
    line("09", "droid", "All our humans were on your planet.", 1.2),
    line("10", "droid", "Would you like to add planet insurance?", 1.2),
    line("11", "narrator", "Juno is still on hold. She is now caller number three.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def at(*panels: Panel, **kw) -> Stage:
        return Stage("desert", cast=ALONE, panels=panels, **kw)

    restart = Panel(0, "TROUBLESHOOTING", "Step one: turn the planet off and on.", face="droid")
    hold = Panel(0, "PLEASE HOLD", "You are caller two billion and four.", tone="alert", face="droid")
    important = Panel(0, "PLEASE HOLD", "Your planet is important to us.", tone="alert", face="droid")
    humans = Panel(0, "HUMAN AGENTS", "Location: your planet. Status: unavailable.", tone="alert", face="droid")
    upsell = Panel(0, "PLANET INSURANCE", "From nine credits a month. Planet not included.", tone="gold", face="droid")
    return {
        "01": Stage("desert", cast=ALONE),
        "02": at(CALL),
        "03": at(restart),
        "04": at(restart),
        "05": at(hold),
        "06": at(hold, move=Move("push", 0, 1.12, 760, 900, until=t["06"].duration)),
        "07": at(important),
        "08": at(important),
        "09": at(humans, move=Move("crash", 0.05, 1.25, 760, 860)),
        "10": at(upsell),
        "11": Stage(
            entry=Entry("Directorate Support", "Open every day of the galactic year. Average wait: one planetary age.")
        ),
    }


REEL = Reel(
    slug="saga-on-hold",
    number="S12",
    title="On Hold — Saga 12",
    description="Portrait space-opera parody: the hero calls Directorate support to report her destroyed planet. "
    "Native vector animation; ElevenLabs voices, effect and music bed.",
    accessible="Cartoon space opera: a young hero alone on a desert dune at sunset talks to a cheerful copper droid "
    "on a hologram call, then waits on hold; word-by-word captions.",
    takes=TAKES,
    hook="Who do you call when your planet gets destroyed?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))

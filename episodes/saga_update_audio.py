#!/usr/bin/env python3
"""Saga 05 — Update: mid-chase, the freighter's jump drive needs to install an update first, and asks if tonight
works.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_update_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys
from dataclasses import replace

from _saga import Reel, effect, line, record
from srstudio.saga_reel import Entry, Move, Place, Prop, Stage
from srstudio.saga_sets import Panel

SEATS = (Place("rook", 330, behind=True), Place("juno", 760, flip=True, behind=True))
INSTALL = Panel(0, "INSTALLING UPDATE", "1 of 47. Do not turn off your ship.")
TONIGHT = Panel(0, "REMIND ME LATER?", "Tonight  ·  Tomorrow  ·  Now (recommended)")
TAKES = (
    line("01", "narrator", "What is the worst possible time for a software update?", 0.3),
    line("02", "rook", "Kid, punch it!", 0.2, mood="angry"),
    line("03", "juno", "Punching it!", 0.4),
    effect("04", "[BOOM]", "A close laser blast hitting a spaceship hull with a metallic rattle", 1.2, 0.1, peak=0.6),
    line("05", "rook", "Skip it!", 0.2, mood="angry"),
    line("06", "juno", "It wants to know if tonight works.", 0.3),
    line("07", "rook", "Tonight! Tonight works!", 0.3, mood="angry"),
    effect("08", "[POWER DOWN]", "A spaceship powering down, a long descending electrical whine", 1.6, 1.8, peak=0.5),
    line("09", "juno", "Is this tonight?", 1.2),
    line("10", "narrator", "The update also removed the jump drive. For security reasons.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def cockpit(*panels: Panel, **kw) -> Stage:
        return Stage("cockpit", cast=SEATS, panels=panels, **kw)

    chase = (
        Prop("freighter", 560, 900, {"scale": 0.9}),
        Prop("fighter", 200, 640, {"scale": 0.8}),
        Prop("fighter", 860, 1180, {"scale": 0.7}),
    )
    boom, power = t["04"].duration, t["08"].duration
    return {
        "01": Stage("space", props=chase, shake=((0.4, 0.9),)),
        "02": cockpit(move=Move("crash", 0.05, 1.2, 330, 1150)),
        "03": cockpit(replace(INSTALL, start=0.3)),
        "04": cockpit(INSTALL, shake=((0.0, boom),)),
        "05": cockpit(Panel(0, "SKIP?", "Skipping is not available on the free plan.", tone="alert")),
        "06": cockpit(TONIGHT),
        "07": cockpit(TONIGHT, move=Move("push", 0, 1.12, 330, 1150, until=t["07"].duration)),
        "08": cockpit(Panel(round(power - 0.5, 3), "WELCOME TO DARK MODE", tone="gold"), dark=((0.4, power),)),
        "09": cockpit(
            Panel(0, "WELCOME TO DARK MODE", "Restart required: 46 more times.", tone="gold"),
            dark=((0.0, t["09"].duration),),
        ),
        "10": Stage(
            entry=Entry(
                "Updates", "Mandatory, overnight, and always the night you are being shot at. Release notes: bug fixes."
            )
        ),
    }


REEL = Reel(
    slug="saga-update",
    number="S5",
    title="Update — Saga 05",
    description="Portrait space-opera parody: mid-chase, the freighter's jump drive insists on installing an update. "
    "Native vector animation; ElevenLabs voices, effects and music bed.",
    accessible="Cartoon space opera: a freighter chased by fighters; in the cockpit a pilot and a young hero read a "
    "hologram update prompt until the lights go out; word-by-word captions.",
    takes=TAKES,
    hook="What is the worst possible time for a software update?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

#!/usr/bin/env python3
"""Saga — Moving Day: the hero finds out the smuggler owns a ship, and the smuggler finds out what that costs.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_moving_day_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _saga import Reel, line, record, word_at
from srstudio.saga_reel import Entry, Move, Place, Prop, Stage
from srstudio.saga_sets import FLOOR, Panel

DUNE = (Place("juno", 300), Place("rook", 780, flip=True))
LIST = Panel(0, "MOVING LIST", "A few boxes.")
TAKES = (
    line("01", "narrator", "What does it really cost to own a ship?", 0.3),
    line("02", "juno", "Rook! You have a ship, right?", 0.3),
    line("03", "rook", "Why?", 0.4),
    line("04", "juno", "I'm moving. It's just a few boxes.", 0.3),
    line("05", "juno", "And a couch.", 0.2),
    line("06", "juno", "And my aunt's water tower.", 0.2),
    line("07", "juno", "And my aunt.", 0.4),
    line("08", "rook", "Where to?", 0.2),
    line("09", "juno", "The top floor of the battle cube. The lift is broken.", 0.6),
    line("10", "rook", "You're the chosen one. Lift it with the Flow.", 1.6),
    line("11", "juno", "I'm on the free plan.", 0.4),
    line("12", "juno", "It does pebbles.", 1.2),
    line("13", "narrator", "Rook moved the couch, the tower and the aunt. The aunt never left the ship.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def at(*panels: Panel, props=(), **kw) -> Stage:
        return Stage("desert", cast=DUNE, panels=panels, props=props, **kw)

    couch = Panel(0, "MOVING LIST", "A few boxes. A couch.")
    farm = Panel(0, "MOVING LIST", "A few boxes. A couch. A water tower.")
    aunt = Panel(0, "MOVING LIST", "A few boxes. A couch. A water tower. An aunt.", tone="alert")
    cube = Panel(0, "NEW ADDRESS", "Battle cube, top floor. Lift: out of order.", tone="alert")
    free = Panel(0, "THE FLOW · FREE PLAN", "Lift up to 200 grams.")
    return {
        "01": Stage("desert", cast=DUNE),
        "02": at(),
        "03": at(move=Move("crash", 0.05, 1.25, 780, 900)),
        "04": at(LIST),
        "05": at(couch),
        "06": at(farm),
        "07": at(aunt, move=Move("crash", 0.05, 1.25, 300, 880)),
        "08": at(aunt),
        "09": at(cube, move=Move("push", 0, 1.12, 540, 900, until=t["09"].duration)),
        "10": at(cube),
        "11": at(free),
        "12": at(free, props=(Prop("pebble", 540, FLOOR - 10, {"lift": word_at(t["12"], "pebbles"), "rise": 160}),)),
        "13": Stage(
            entry=Entry(
                "Freighter",
                "A ship. Once your friends know you own one, you will never fly it anywhere you want again.",
            )
        ),
    }


REEL = Reel(
    slug="saga-moving-day",
    number="S10",
    title="Moving Day — Saga 10",
    description="Portrait space-opera parody: the hero is moving, and the smuggler made the mistake of owning a "
    "ship. Native vector animation; ElevenLabs voices and music bed.",
    accessible="Cartoon space opera: a young hero lists everything she needs moved to a grumpy smuggler on a desert "
    "dune, the list growing on a hologram; word-by-word captions.",
    takes=TAKES,
    hook="What does it really cost to own a ship?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

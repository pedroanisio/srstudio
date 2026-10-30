#!/usr/bin/env python3
"""Saga 06 — Free Tier: an old master teaches the young hero to feel the Flow, the energy that binds the galaxy,
on the free plan.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_free_tier_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys
from dataclasses import replace

from _saga import Reel, line, record, word_at
from srstudio.saga_reel import Entry, Move, Place, Prop, Stage
from srstudio.saga_sets import FLOOR, Panel

LESSON = (Place("mabel", 300), Place("juno", 780, flip=True))
RISEN = Prop("pebble", 540, FLOOR - 170, {"rise": 0})  # where the first lift left it, bobbing
FREE = Panel(0, "THE FLOW · FREE PLAN", "Lift up to 200 grams.")
TAKES = (
    line("01", "narrator", "Can you feel the energy that binds the galaxy together?", 0.3),
    line("02", "mabel", "Close your eyes. Feel the Flow.", 0.5),
    line("03", "juno", "I feel it!", 0.4),
    line("04", "juno", "It's a pebble.", 0.4),
    line("05", "mabel", "Upgrade to Flow Plus for boulders.", 0.3),
    line("06", "juno", "And mind tricks?", 0.2),
    line("07", "mabel", "Flow Premium. Billed yearly.", 0.3),
    line("08", "juno", "What does free get me?", 1.6),
    line("09", "mabel", "Commercials.", 0.5),
    line("10", "juno", "I sense a great disturbance.", 0.3),
    line("11", "mabel", "That's the renewal.", 1.2),
    line(
        "12",
        "narrator",
        "Elder Mabel has been trying to cancel for nine hundred years. The button is in another galaxy.",
        1.2,
    ),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def lesson(*panels: Panel, **kw) -> Stage:
        return Stage("desert", cast=LESSON, panels=panels, props=(RISEN,), **kw)

    plus = Panel(0, "FLOW PLUS", "Boulders. Small moons on request.", tone="gold")
    premium = Panel(0, "FLOW PREMIUM", "Mind tricks. Billed yearly. No refunds.", tone="gold")
    return {
        "01": Stage("desert", cast=LESSON, props=(Prop("pebble", 540, FLOOR - 10, {"lift": 0.8, "rise": 0}),)),
        "02": Stage(
            "desert",
            cast=LESSON,
            props=(Prop("pebble", 540, FLOOR - 10, {"lift": 0.5, "rise": 0}),),
            move=Move("push", 0, 1.1, 300, 1000, until=t["02"].duration),
        ),
        "03": Stage(
            "desert",
            cast=LESSON,
            panels=(replace(FREE, start=round(t["03"].duration * 0.5, 3)),),
            props=(Prop("pebble", 540, FLOOR - 10, {"lift": word_at(t["03"], "feel"), "rise": 160}),),
        ),
        "04": lesson(FREE, move=Move("crash", 0.05, 1.3, 540, FLOOR - 170)),
        "05": lesson(plus),
        "06": lesson(plus),
        "07": lesson(premium),
        "08": lesson(premium),
        "09": lesson(
            Panel(0, "FEELING A DISTURBANCE?", "Try Flow Premium. Ad 1 of 6.", tone="alert"),
            move=Move("crash", 0.05, 1.25, 450, 480),
        ),
        "10": lesson(Panel(0, "FEELING A DISTURBANCE?", "Try Flow Premium. Ad 2 of 6.", tone="alert")),
        "11": lesson(
            Panel(0, "FLOW PREMIUM: RENEWED", "119.88 credits charged. Thank you!", tone="ok"),
            move=Move("push", 0, 1.12, 780, 1000, until=t["11"].duration),
        ),
        "12": Stage(
            entry=Entry(
                "The Flow",
                "An energy field that binds the galaxy together. Lifting rocks over 200 grams requires a subscription.",
            )
        ),
    }


REEL = Reel(
    slug="saga-free-tier",
    number="S6",
    title="Free Tier — Saga 06",
    description="Portrait space-opera parody: an old master teaches the young hero the energy that binds the galaxy, "
    "on the free plan. Native vector animation; ElevenLabs voices and music bed.",
    accessible="Cartoon space opera: an elder with a cane and a young hero on a desert dune, a floating pebble and a "
    "hologram subscription screen; word-by-word captions.",
    takes=TAKES,
    hook="Can you feel the energy that binds the galaxy together?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))

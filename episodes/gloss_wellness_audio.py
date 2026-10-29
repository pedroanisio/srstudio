#!/usr/bin/env python3
"""Gloss 06 — Wellness: the mandatory smile check, escalated to a manager.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_wellness_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_gloss`; ``tests/test_gloss_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _gloss import Reel, effect, line, record, word_at
from srstudio.gloss_reel import Move, Notice, Place, Stage
from srstudio.gloss_sets import Card

GUS = Place("gus", 620, scale=0.9)
FLAT = ((0, "flat"),)
TAKES = (
    line("01", "sunny", "When did wellness become mandatory?", 0.3),
    line("02", "sunny", "Time for your wellness check, Gus. Please hold still.", 0.3),
    effect("03", "[SCAN]", "a soft electronic scanning beam sweep, a rising synth hum, one pass", 1.4, 0.3),
    line("04", "sunny", "Twelve percent. Please smile harder.", 0.3),
    line("05", "gus", "This is my face.", 0.4),
    line("06", "sunny", "Your face has been escalated to a manager.", 1.2),
    effect("07", "[WHOOSH]", "a quick cartoon whoosh, something zipping past", 0.6, 0.2),
    line("08", "sunny", "Hello. I am the manager.", 0.3),
    line("09", "gus", "You are the same ball.", 0.4),
    line("10", "sunny", "I am a different ball. I have a tie.", 1.2),
    line("11", "sunny", "Your wellbeing is our top priority. It is ranked fourth.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    scanner = Place("sunny", 620, 520, scale=0.6)
    smile = Card(0, "Smile detected: 12%", "Required: 90%.", label="SMILE CHECK", tone="alert", carried=True)
    manager = Place("sunny", 370, 450, scale=0.75, flip=True, traits={"tie": True})
    gus = Place("gus", 620, scale=0.9, face=FLAT)
    return {
        "01": Stage("activity", cast=(GUS,)),
        "02": Stage("activity", cast=(GUS, scanner)),
        "03": Stage(
            "activity",
            cast=(
                Place("gus", 620, scale=0.9, face=((0, "open"), (0.5, "flat"))),
                Place("sunny", 620, 520, scale=0.6, traits={"scan": ((0.05, t["03"].duration - 0.1),)}),
            ),  # fmt: skip
            cards=(Card(round(t["03"].duration * 0.7, 3), smile.title, smile.body, label="SMILE CHECK", tone="alert"),),
        ),
        "04": Stage("activity", cast=(gus, scanner), cards=(smile,)),
        "05": Stage("activity", cast=(gus, scanner), cards=(smile,)),
        "06": Stage(
            "activity",
            cast=(gus, Place("sunny", 620, 520, scale=0.6, face=((0, "alert"),))),
            move=Move("push", word_at(t["06"], "escalated"), 1.15, 620, 900, until=t["06"].duration),
        ),
        "07": Stage("activity", cast=(gus, manager)),
        "08": Stage("activity", cast=(gus, manager)),
        "09": Stage(
            "activity", cast=(gus, Place("sunny", 370, 450, scale=0.75, flip=True, face=FLAT, traits={"tie": True}))
        ),  # fmt: skip
        "10": Stage(
            "activity",
            cast=(gus, manager),
            move=Move("crash", word_at(t["10"], "tie"), 1.35, 370, 520, back=t["10"].duration - 0.1),
        ),
        "11": Stage(
            notice=Notice(
                "Wellness", "Your wellbeing is our top priority, ranked fourth, after uptime, smiles and ties."
            )  # fmt: skip
        ),
    }


REEL = Reel(
    slug="gloss-wellness",
    number="G6",
    title="Wellness — Gloss 06",
    description="Portrait satire: the Plaza's mandatory smile check, escalated to a manager who is the same orb in "
    "a tie. Native vector animation; ElevenLabs voices and music bed.",
    accessible="A floating orb host scans a deadpan cartoon toy doll for smiles in a white activity room, then "
    "returns wearing a tie as the manager; word-by-word captions.",
    takes=TAKES,
    hook="When did wellness become mandatory?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

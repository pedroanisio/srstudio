#!/usr/bin/env python3
"""Gloss 03 — Trust Exercise: the Activity Room's trust fall, and nobody catches anyone.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_trust_fall_audio.py PROJECT --font DIR

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

HOST = Place("sunny", 870, 430, scale=0.65)
GUS = Place("gus", 1030, 1090, scale=0.55, face=((0, "shut"),), traits={"fall": 0.0})  # he fell in March; at the back
TAKES = (
    line("01", "sunny", "How much should you trust your workplace?", 0.3),
    line("02", "sunny", "Today's activity is a trust fall. Nadia, please fall backwards.", 0.3),
    line("03", "nadia", "Who is catching me?", 0.4),
    line("04", "sunny", "Trust.", 1.4),
    effect("05", "[THUD]", "a heavy hollow plastic thud of a toy doll falling flat on a hard floor, one hit", 0.8, 0.4),
    line("06", "sunny", "Thank you. The floor has been informed of your trust.", 0.3),
    line("07", "nadia", "Nobody caught me.", 0.4),
    line("08", "sunny", "Correct. Catching was not in the budget.", 1.2),
    line("09", "gus", "I fell in March. Still waiting for the trust.", 1.0),
    line("10", "sunny", "Please remain on the floor for scoring.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    down = Place("nadia", 640, face=((0, "flat"),), traits={"fall": 0.0})
    activity = Card(0, "Trust Fall", "Step one: fall. Step two: trust.", label="ACTIVITY", carried=True)
    fall_at = round(max(0.1, word_at(t["04"], "trust") + 0.5), 3)
    return {
        "01": Stage("activity", cast=(GUS, Place("nadia", 640))),
        "02": Stage(
            "activity",
            cast=(GUS, Place("nadia", 640), HOST),
            cards=(
                Card(word_at(t["02"], "trust"), "Trust Fall", "Step one: fall. Step two: trust.", label="ACTIVITY"),
            ),
        ),
        "03": Stage(
            "activity",
            cast=(GUS, Place("nadia", 640, face=((0, "wide"),), pose=((0, "shrug"),)), HOST),
            cards=(activity,),
        ),  # fmt: skip
        "04": Stage(
            "activity",
            cast=(GUS, Place("nadia", 640, face=((0, "shut"),), traits={"fall": fall_at}), HOST),
            cards=(activity,),
        ),
        "05": Stage("activity", cast=(GUS, down, HOST), shake=((0.0, 0.3),), cards=(Card(0.2, "Trusted", points=1),)),
        "06": Stage("activity", cast=(GUS, down, HOST), cards=(Card(0, "Trusted", points=1, carried=True),)),
        "07": Stage("activity", cast=(GUS, down, HOST), move=Move("push", 0.0, 1.2, 200, 1150, until=t["07"].duration)),
        "08": Stage(
            "activity",
            cast=(GUS, down, HOST),
            cards=(Card(word_at(t["08"], "budget"), "Catching", "Not in the budget.", label="ACTIVITY", tone="alert"),),
        ),  # fmt: skip
        "09": Stage(
            "activity",
            cast=(Place("gus", 1030, 1090, scale=0.55, face=((0, "flat"),), traits={"fall": 0.0}), down, HOST),
            move=Move("crash", 0.05, 1.4, 760, 1030, back=t["09"].duration - 0.1),
        ),
        "10": Stage(
            notice=Notice(
                "Trust Exercise Results", "You trusted. The floor did not. Please remain on the floor for scoring."
            )  # fmt: skip
        ),
    }


REEL = Reel(
    slug="gloss-trust-fall",
    number="G3",
    title="Trust Exercise — Gloss 03",
    description="Portrait satire: the Activity Room's trust fall, where nobody catches anyone and the floor is "
    "informed. Native vector animation; ElevenLabs voices and music bed.",
    accessible="Cartoon glossy toy dolls in a white activity room; one falls backwards onto a pink pad while a "
    "floating orb host watches; another has been lying at the edge all along; word-by-word captions.",
    takes=TAKES,
    hook="How much should you trust your workplace?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

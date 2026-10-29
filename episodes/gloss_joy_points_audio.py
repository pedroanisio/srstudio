#!/usr/bin/env python3
"""Gloss 02 — Joy Points: every small act at the Plaza is scored, and breathing costs forty.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_joy_points_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_gloss`; ``tests/test_gloss_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _gloss import Reel, line, record, word_at
from srstudio.gloss_reel import Move, Notice, Place, Prop, Stage
from srstudio.gloss_sets import Card

HOST = Place("sunny", 840, 600, scale=0.8)
DOOR = Prop("door", 470, 1270, {"scale": 0.75, "opened": 1})
TAKES = (
    line("01", "sunny", "What if every tiny thing you did was being scored?", 0.3),
    line("02", "sunny", "Gus held a door. Plus two.", 0.3),
    line("03", "tamsin", "Thank you, Gus!", 0.3, mood="excited"),
    line("04", "gus", "Okay.", 0.9, mood="weary sigh"),
    line("05", "gus", "I was breathing.", 0.3),
    line("06", "sunny", "Heavily.", 0.9),
    line("07", "gus", "What are the points even for?", 0.3),
    line("08", "sunny", "Points can be redeemed for more points.", 1.3),
    line("09", "tamsin", "I have nine million! I am saving up for points!", 0.8, mood="excited"),
    line("10", "sunny", "Balance does not roll over. Neither do you.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    gus = Place("gus", 260, pose=((0, "point"),))
    tamsin = Place("tamsin", 620)
    held = Card(0, "Held a door", points=2, carried=True)
    thanks = Card(0, "Said thank you", points=1, carried=True)
    exhaled = Card(0, "Exhaled audibly in a joyful space", points=-40, carried=True)
    return {
        "01": Stage(
            "plaza",
            cast=(gus, Place("tamsin", 980, flip=True, walk=(0.3, min(2.0, t["01"].duration - 0.1), 620))),
            props=(DOOR,),
        ),
        "02": Stage(
            "plaza",
            cast=(gus, tamsin, HOST),
            props=(DOOR,),
            cards=(Card(word_at(t["02"], "plus"), "Held a door", points=2),),
        ),
        "03": Stage(
            "plaza",
            cast=(
                gus,
                Place("tamsin", 620, pose=((0, "up"),), traits={"bounce": ((0.1, t["03"].duration - 0.1),)}),
                HOST,
            ),  # fmt: skip
            props=(DOOR,),
            cards=(held, Card(round(t["03"].duration * 0.5, 3), "Said thank you", points=1)),
        ),
        "04": Stage(
            "plaza",
            cast=(Place("gus", 260, face=((0, "flat"),)), tamsin, HOST),
            cards=(thanks, Card(round(t["04"].duration - 0.85, 3), "Exhaled audibly in a joyful space", points=-40)),
        ),
        "05": Stage(
            "plaza", cast=(Place("gus", 260, face=((0, "flat"),), pose=((0, "shrug"),)), tamsin, HOST), cards=(exhaled,)
        ),  # fmt: skip
        "06": Stage(
            "plaza",
            cast=(Place("gus", 260, face=((0, "wide"),)), tamsin, HOST),
            cards=(exhaled,),
            move=Move("crash", 0.05, 1.3, 260, 900, back=t["06"].duration - 0.1),
        ),
        "07": Stage("plaza", cast=(Place("gus", 260, face=((0, "flat"),), pose=((0, "shrug"),)), tamsin, HOST)),
        "08": Stage(
            "plaza",
            cast=(Place("gus", 260, face=((0, "flat"),), traits={"unwound": t["08"].duration - 0.9}), tamsin, HOST),
            move=Move("push", 0.0, 1.12, 300, 1000, until=t["08"].duration),
        ),
        "09": Stage(
            "plaza",
            cast=(
                Place("gus", 260, face=((0, "flat"),), traits={"unwound": 0.0}),
                Place("tamsin", 620, pose=((0, "up"),), traits={"bounce": ((0.0, t["09"].duration - 0.2),)}),
                HOST,
            ),
            cards=(Card(0, "Tamsin's balance", "Nine million. Saving for points.", label="JOY POINTS", tone="plum"),),
        ),
        "10": Stage(
            notice=Notice(
                "Joy Points",
                "Earned for everything. Lost for breathing. Balance does not roll over, and neither do you.",
            )  # fmt: skip
        ),
    }


REEL = Reel(
    slug="gloss-joy-points",
    number="G2",
    title="Joy Points — Gloss 02",
    description="Portrait satire: in a cheerful forever-plaza every tiny act is scored, and breathing costs "
    "forty points. Native vector animation; ElevenLabs voices and music bed.",
    accessible="Cartoon glossy toy dolls on a pastel plaza; a points board scores every action while a floating "
    "orb host announces the totals; word-by-word captions.",
    takes=TAKES,
    hook="What if every tiny thing you did was being scored?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

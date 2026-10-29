#!/usr/bin/env python3
"""Gloss 05 — Exit: what is behind the Plaza's exit door is another door, and a queue.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_exit_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_gloss`; ``tests/test_gloss_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _gloss import Reel, effect, line, record
from srstudio.gloss_reel import Move, Notice, Place, Prop, Stage

CREAK = "a slow creaking toy door hinge opening, one creak"


def door(opened: int, opens: tuple[float, ...] = ()) -> Prop:
    return Prop("door", 640, 1270, {"scale": 1.1, "depth": 3, "opened": opened, "opens": opens})


GUS = Place("gus", 270, scale=0.9)
TAKES = (
    line("01", "sunny", "What is really behind the exit door?", 0.3),
    line("02", "gus", "Forty years I have looked for this door.", 0.4),
    effect("03", "[CREAK]", CREAK, 1.0, 0.3),
    line("04", "gus", "Another door.", 0.4),
    effect("05", "[CREAK]", CREAK, 1.0, 0.3),
    line("06", "gus", "A smaller door.", 0.4),
    effect("07", "[CREAK]", CREAK, 1.0, 1.2),
    line("08", "sunny", "Please take a number.", 0.4),
    line("09", "gus", "Four million and six.", 0.4),
    effect("10", "[DING]", "a single bright service bell ding, a queue number display changing", 0.7, 0.3),
    line("11", "sunny", "Now serving: three.", 1.2),
    line("12", "sunny", "Waiting is the attraction.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    flat, wide = ((0, "flat"),), ((0, "wide"),)
    ticket = Prop("ticket", 720, 1010, {"number": "4000006", "scale": 0.75}, front=True)
    end = t["02"].duration
    return {
        "01": Stage("plaza", cast=(GUS,), props=(door(0),)),
        "02": Stage("plaza", cast=(GUS,), props=(door(0),), move=Move("push", 0.0, 1.12, 640, 1000, until=end)),
        "03": Stage("plaza", cast=(GUS,), props=(door(0, (0.15,)),)),
        "04": Stage("plaza", cast=(Place("gus", 270, scale=0.9, face=flat),), props=(door(1),)),
        "05": Stage("plaza", cast=(Place("gus", 270, scale=0.9, face=flat),), props=(door(1, (0.15,)),)),
        "06": Stage("plaza", cast=(Place("gus", 270, scale=0.9, face=flat),), props=(door(2),)),
        "07": Stage(
            "plaza",
            cast=(Place("gus", 270, scale=0.9, face=((0, "flat"), (0.6, "wide"))),),
            props=(door(2, (0.15,)),),
            move=Move("crash", 0.55, 1.35, 640, 1080, back=t["07"].duration - 0.1),
        ),
        "08": Stage(
            "plaza",
            cast=(Place("gus", 270, scale=0.9, face=wide), Place("sunny", 820, 560, scale=0.7)),
            props=(door(3),),
        ),  # fmt: skip
        "09": Stage(
            "waiting",
            cast=(Place("gus", 540, face=flat, pose=((0, "point"),)),),
            props=(ticket,),
            move=Move("push", 0.0, 1.15, 700, 1000, until=t["09"].duration),
        ),
        "10": Stage(
            "waiting",
            {"serving": ((0, "3"), (0.1, "4"))},
            cast=(Place("gus", 540, face=wide, pose=((0, "point"),)),),
            props=(ticket,),
        ),
        "11": Stage(
            "waiting",
            {"serving": ((0, "4"), (round(min(0.6, t["11"].duration / 3), 3), "3"))},
            cast=(Place("gus", 540, face=flat),),
            props=(ticket,),
        ),
        "12": Stage(
            notice=Notice("Exits", "Processed in the order they are never received. Waiting is the attraction.")
        ),
    }


REEL = Reel(
    slug="gloss-exit",
    number="G5",
    title="Exit — Gloss 05",
    description="Portrait satire: behind the Plaza's exit door is another door, a smaller door, and a queue. "
    "Native vector animation; ElevenLabs voices and music bed.",
    accessible="A cartoon glossy toy doll opens an exit door onto nested smaller doors and a ticket dispenser, then "
    "waits in a waiting room under a NOW SERVING display; word-by-word captions.",
    takes=TAKES,
    hook="What is really behind the exit door?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

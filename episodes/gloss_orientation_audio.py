#!/usr/bin/env python3
"""Gloss 01 — Orientation: the newest guest of the Plaza asks where the exit is.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_orientation_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_gloss`; ``tests/test_gloss_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _gloss import Reel, effect, line, record, word_at
from srstudio.gloss_reel import Move, Notice, Place, Prop, Stage
from srstudio.gloss_sets import Card

DOOR = Prop("door", 880, 1270, {"scale": 0.8, "painted": True})
TAKES = (
    line("01", "sunny", "Have you ever woken up inside a mandatory team building exercise?", 0.4),
    line("02", "sunny", "Welcome to the Plaza, Nadia. Your stay is permanent, and fun.", 0.3),
    line("03", "nadia", "Great. Where is the exit?", 0.4),
    line("04", "sunny", "Right behind you.", 0.9),
    effect("05", "[BONK]", "a hollow plastic bonk, a toy head hitting a painted wooden wall, one hit", 0.8, 0.5),
    line("06", "tamsin", "Oh, that one is painted on! I tried it for eleven years!", 0.3, mood="excited"),
    line("07", "nadia", "Eleven years?", 1.4),
    line("08", "gus", "Eleven? Cute. I am still on my free trial.", 1.0),
    line("09", "sunny", "Day one of forever. The exit is available in a future update.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    host = Place("sunny", 760, 600, scale=0.8)
    behind = word_at(t["04"], "behind")
    walk_from = min(behind + 0.3, t["04"].duration - 0.5)
    at_door = Place("nadia", 760, flip=True, face=((0, "shut"),))
    return {
        "01": Stage("plaza", cast=(Place("nadia", 540, face=((0, "wide"),)),)),
        "02": Stage(
            "plaza",
            cast=(Place("nadia", 360), host),
            cards=(Card(round(t["02"].duration * 0.45, 3), "Stay: permanent", "Fun: mandatory.", label="WELCOME"),),
        ),
        "03": Stage("plaza", cast=(Place("nadia", 360, pose=((0, "shrug"),)), host)),
        "04": Stage(
            "plaza",
            cast=(Place("nadia", 360, flip=True, face=((0, "open"),), walk=(walk_from, t["04"].duration - 0.05, 760)),),
            props=(DOOR,),
            move=Move("crash", behind, 1.2, 860, 1000, back=min(behind + 0.6, t["04"].duration - 0.05)),
        ),
        "05": Stage(
            "plaza",
            cast=(at_door,),
            props=(DOOR,),
            shake=((0.0, 0.35),),
            cards=(Card(0.25, "Ran into decor", points=-3),),
        ),
        "06": Stage(
            "plaza",
            cast=(
                at_door,
                Place("tamsin", 1250, walk=(0.0, 0.6, 420), pose=((0.6, "up"),), traits={"bounce": ((0.6, 1.4),)}),
            ),
            props=(DOOR,),
        ),
        "07": Stage(
            "plaza",
            cast=(
                Place(
                    "nadia", 760, flip=True, face=((0, "wide"),), traits={"peel": (round(t["07"].duration * 0.4, 3),)}
                ),
                Place("tamsin", 420),
            ),
            props=(DOOR,),
            move=Move("push", 0.0, 1.15, 760, 960, until=t["07"].duration),
        ),
        "08": Stage(
            "plaza",
            cast=(
                Place("gus", 140, scale=0.85, face=((0, "flat"),), traits={"unwound": t["08"].duration - 0.2}),
                Place("tamsin", 480),
                Place("nadia", 800, flip=True, face=((0, "wide"),)),
            ),
            props=(DOOR,),
        ),
        "09": Stage(notice=Notice("Orientation", "Day one of forever. The exit is available in a future update.")),
    }


REEL = Reel(
    slug="gloss-orientation",
    number="G1",
    title="Orientation — Gloss 01",
    description="Portrait satire: the newest guest of a cheerful forever-plaza asks where the exit is. Native "
    "vector animation; ElevenLabs voices and music bed.",
    accessible="Cartoon glossy toy dolls on a pastel checkerboard plaza with a floating orb host; a painted-on exit "
    "door, a points board and word-by-word captions.",
    takes=TAKES,
    hook="Have you ever woken up inside a mandatory team building exercise?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

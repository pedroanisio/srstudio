#!/usr/bin/env python3
"""Saga 18 — Friday Deploy: Seven ships one tiny fix at five on a Friday, the bridge goes dark, and the only person
who can roll it back is on leave until Monday.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_friday_deploy_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging. It opens
moving (the ``b`` arm of the first-second test): the camera pushes in on the bridge as the narrator asks.
"""

from __future__ import annotations

import sys
from functools import partial

from _saga import Reel, effect, line, record, word_at
from srstudio import saga_sets
from srstudio.saga_reel import Entry, Move, Place, Stage
from srstudio.saga_sets import FLOOR

Panel = partial(saga_sets.Panel, fade=True)  # fades in, so each panel is judged as read (strict contrast)

STAND = (Place("gloom", 330), Place("seven", 700, flip=True))  # Seven clear of the console's SR-1028
ALONE = (Place("gloom", 330),)
DEPLOY = Panel(0, "DEPLOYING", "fix: button color · Friday, 16:58", tone="gold", face="seven")
DOWN = Panel(0, "ALL SYSTEMS DOWN", "Lights. Doors. Gravity. Coffee.", tone="alert")
AWAY = Panel(0, "OUT OF OFFICE", "Seven is on leave until Monday.", tone="gold", face="seven")
TAKES = (
    line("01", "narrator", "When is the worst time to change anything on a starship?", 0.3),
    line("02", "seven", "Just one tiny fix before the weekend.", 0.3),
    line("03", "gloom", "Seven. It is Friday.", 0.3),
    line("04", "seven", "What could go wrong?", 0.3),
    effect(
        "05", "[POWER DOWN]", "A huge ship losing power, a descending electrical whine into silence", 1.8, 0.4, peak=0.5
    ),  # fmt: skip
    line("06", "gloom", "Who deployed?", 0.4),
    line("07", "seven", "It works on my machine.", 0.4),
    line("08", "gloom", "Your machine is the ship.", 0.5),
    line("09", "gloom", "Roll it back.", 0.3),
    line("10", "seven", "Only I can. And I am on leave until Monday.", 0.3),
    effect("11", "[DOOR]", "A sliding metal door hissing open and shut", 1.0, 1.4, peak=0.45),
    line("12", "narrator", "The bridge stayed dark all weekend. The button is a lovely shade of blue.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def bridge(*panels: saga_sets.Panel, cast=STAND, **kw) -> Stage:
        return Stage("bridge", cast=cast, panels=panels, **kw)

    fix = round(max(min(word_at(t["02"], "fix"), t["02"].duration - 0.9), 0.0), 3)
    out = round(min(0.5, t["05"].duration / 3), 3)
    ship = word_at(t["08"], "ship")
    return {
        "01": bridge(move=Move("push", 0, 1.1, 540, FLOOR, until=t["01"].duration)),
        "02": bridge(Panel(fix, DEPLOY.title, DEPLOY.body, tone="gold", face="seven")),
        "03": bridge(DEPLOY, move=Move("crash", 0.05, 1.2, 600, FLOOR)),
        "04": bridge(DEPLOY),
        "05": bridge(shake=((0.0, out),), dark=((out, t["05"].duration),)),
        "06": bridge(dark=((0.0, t["06"].duration),)),  # a voice in the dark
        "07": bridge(DOWN),
        "08": bridge(DOWN, move=Move("crash", ship, 1.25, 700, FLOOR)),
        "09": bridge(DOWN),
        "10": bridge(AWAY),
        "11": bridge(AWAY, cast=ALONE, move=Move("push", 0.1, 1.1, 330, FLOOR, until=t["11"].duration)),
        "12": Stage(
            entry=Entry(
                "Friday Deploy", "A change too small to test, made at the one hour nobody can undo it.", fade=True
            )
        ),
    }


REEL = Reel(
    slug="saga-friday-deploy",
    number="S18",
    title="Friday Deploy — Saga 18",
    description="Portrait space-opera parody: an enforcer ships one tiny fix at five on a Friday, the bridge goes "
    "dark, and the only person who can roll it back is him, on leave until Monday. Native vector animation; "
    "ElevenLabs voices, effects and music bed.",
    accessible="Cartoon space opera: a dark lord in a horned helmet and a white-armoured enforcer on a command bridge; "
    "a hologram shows a deploy, the bridge goes dark, then all systems down and an out-of-office notice as the "
    "enforcer leaves; word-by-word captions.",
    takes=TAKES,
    hook="When is the worst time to change anything on a starship?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))

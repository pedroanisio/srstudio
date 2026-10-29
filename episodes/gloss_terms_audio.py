#!/usr/bin/env python3
"""Gloss 07 — Terms: the guests are asked to accept the new terms of existence.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_terms_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_gloss`; ``tests/test_gloss_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _gloss import Reel, line, record, word_at
from srstudio import gloss_reel
from srstudio.gloss_reel import Move, Notice, Place, Stage
from srstudio.gloss_sets import Card

HOST = Place("sunny", 870, 520, scale=0.6)
TAKES = (
    line("01", "sunny", "Did anyone actually read the new terms of existence?", 0.3),
    line("02", "sunny", "We have updated our terms of existence. Please accept.", 0.3),
    line("03", "tamsin", "Accept!", 0.3, mood="excited"),
    line("04", "nadia", "Wait, what changed?", 0.3),
    line("05", "sunny", "Section four. Hope is now a premium feature.", 0.4),
    line("06", "gus", "And if I decline?", 0.3),
    line("07", "sunny", "Declining has been added to section four.", 1.3),
    line("08", "nadia", "Is any of this even real?", 0.3),
    # the operator accepted the homophone speech-to-text hears; the spoken word is still "Real"
    line("09", "sunny", "Real is also premium.", 1.2, heard=("Reel is also premium.",)),
    line("10", "sunny", "By continuing to exist, you agree to continue existing.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    terms = Card(0, "Terms of Existence, version 9000", "Accept?", label="TERMS", carried=True)
    hope = Card(0, "Section 4: Hope", "Now a premium feature.", label="TERMS", tone="plum", carried=True)

    def trio(nadia=(), gus=(), tamsin=(), tamsin_traits=None, nadia_pose=()) -> tuple:
        return (
            Place("nadia", 200, face=nadia, pose=nadia_pose),
            Place("tamsin", 540, pose=tamsin, traits=tamsin_traits or {}),
            Place("gus", 880, flip=True, face=gus),
            HOST,
        )

    flat, wide = ((0, "flat"),), ((0, "wide"),)
    return {
        "01": Stage("plaza", cast=trio()[:3]),
        "02": Stage(
            "plaza", cast=trio(), cards=(Card(word_at(t["02"], "accept"), terms.title, terms.body, label="TERMS"),)
        ),  # fmt: skip
        "03": Stage(
            "plaza",
            cast=trio(tamsin=((0, "up"),), tamsin_traits={"bounce": ((0.0, t["03"].duration - 0.1),)}),
            cards=(terms, Card(0.2, "Accepted without reading", points=5)),
        ),  # fmt: skip
        "04": Stage("plaza", cast=trio(nadia_pose=((0, "shrug"),))),
        "05": Stage(
            "plaza",
            cast=trio(nadia=wide),
            cards=(Card(word_at(t["05"], "hope"), hope.title, hope.body, label="TERMS", tone="plum"),),
        ),  # fmt: skip
        "06": Stage("plaza", cast=trio(gus=flat), cards=(hope,)),
        "07": Stage(
            "plaza",
            cast=trio(gus=flat),
            cards=(
                Card(
                    word_at(t["07"], "added"),
                    "Section 4.2",
                    "Declining counts as accepting.",
                    label="TERMS",
                    tone="alert",
                ),
            ),
        ),  # fmt: skip
        "08": Stage(
            "plaza", cast=trio(nadia=wide, gus=flat), move=Move("push", 0.0, 1.15, 220, 1000, until=t["08"].duration)
        ),
        "09": Stage(
            "plaza",
            cast=trio(nadia=flat, gus=flat),
            move=Move("crash", word_at(t["09"], "premium"), 1.3, 220, 960, back=t["09"].duration - 0.1),
        ),
        "10": Stage(notice=Notice("Terms of Existence", "By continuing to exist, you agree to continue existing.")),
    }


REEL = Reel(
    slug="gloss-terms",
    number="G7",
    title="Terms — Gloss 07",
    description="Portrait satire: the guests of a cheerful forever-plaza are asked to accept the new terms of "
    "existence. Native vector animation; ElevenLabs voices and music bed.",
    accessible="Cartoon glossy toy dolls on a pastel plaza read new terms on a board while a floating orb host "
    "asks them to accept; word-by-word captions.",
    takes=TAKES,
    hook="Did anyone actually read the new terms of existence?",
    stages=stages,
    captions=gloss_reel.LOOK,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

#!/usr/bin/env python3
"""Gloss 04 — Feedback: the guests are asked to rate a place they can never leave.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_feedback_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_gloss`; ``tests/test_gloss_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _gloss import Reel, line, record, word_at
from srstudio.gloss_reel import Move, Notice, Place, Stage
from srstudio.gloss_sets import Card

HOST = Place("sunny", 870, 520, scale=0.6)
TAKES = (
    line("01", "sunny", "Have you ever been asked to rate a place you can never leave?", 0.3),
    line("02", "sunny", "Please rate your eternal stay, from one to five.", 0.3),
    line("03", "tamsin", "Five! Five forever!", 0.3, mood="excited"),
    line("04", "gus", "Zero.", 0.6),
    line("05", "sunny", "Zero is not an option. I have recorded one.", 0.4),
    line("06", "nadia", "Can I leave a comment?", 0.3),
    line("07", "sunny", "Of course. Comments go straight into the bin.", 0.4),
    line("08", "sunny", "Based on your feedback, we have added more plaza.", 1.2),
    line("09", "gus", "That was the complaint.", 1.0),
    line("10", "sunny", "Your feedback is stored somewhere very safe, and never opened.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    survey = Card(0, "How was forever?", "1 · 2 · 3 · 4 · 5", label="SURVEY", carried=True)

    def trio(nadia=(), gus=(), tamsin=(), gus_traits=None, tamsin_traits=None, nadia_pose=()) -> tuple:
        return (
            Place("nadia", 200, face=nadia, pose=nadia_pose),
            Place("gus", 880, flip=True, face=gus, traits=gus_traits or {}),
            Place("tamsin", 540, pose=tamsin, traits=tamsin_traits or {}),
            HOST,
        )

    flat = ((0, "flat"),)
    return {
        "01": Stage("plaza", cast=trio()[:3]),
        "02": Stage(
            "plaza", cast=trio(), cards=(Card(word_at(t["02"], "rate"), survey.title, survey.body, label="SURVEY"),)
        ),  # fmt: skip
        "03": Stage(
            "plaza",
            cast=trio(tamsin=((0, "up"),), tamsin_traits={"bounce": ((0.0, t["03"].duration - 0.1),)}),
            cards=(survey,),
        ),  # fmt: skip
        "04": Stage("plaza", cast=trio(gus=flat), cards=(survey,)),
        "05": Stage(
            "plaza",
            cast=trio(gus=flat),
            cards=(Card(word_at(t["05"], "recorded"), "Gus: one star", "(generous)", label="SURVEY"),),
        ),  # fmt: skip
        "06": Stage("plaza", cast=trio(gus=flat, nadia_pose=((0, "point"),))),
        "07": Stage(
            "plaza",
            cast=trio(gus=flat),
            cards=(
                Card(
                    word_at(t["07"], "bin"),
                    "Delivered to: the bin",
                    "Bin full since launch.",
                    label="COMMENTS",
                    tone="alert",
                ),
            ),
        ),  # fmt: skip
        "08": Stage(
            "plaza", cast=trio(gus=flat), cards=(Card(word_at(t["08"], "added"), "Acres of plaza added", points=400),)
        ),  # fmt: skip
        "09": Stage(
            "plaza",
            cast=trio(gus=((0, "wide"),), nadia=flat),
            move=Move("crash", 0.05, 1.3, 860, 950, back=t["09"].duration - 0.1),
        ),
        "10": Stage(notice=Notice("Your Feedback Matters", "It is stored somewhere very safe, and never opened.")),
    }


REEL = Reel(
    slug="gloss-feedback",
    number="G4",
    title="Feedback — Gloss 04",
    description="Portrait satire: the guests of a cheerful forever-plaza are asked to rate a place they can never "
    "leave. Native vector animation; ElevenLabs voices and music bed.",
    accessible="Cartoon glossy toy dolls on a pastel plaza answer a satisfaction survey on a points board while a "
    "floating orb host records the answers; word-by-word captions.",
    takes=TAKES,
    hook="Have you ever been asked to rate a place you can never leave?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

#!/usr/bin/env python3
"""Saga 01 — Known Issue: the battle cube's fatal hole was reported nine years ago; the more urgent it gets, the
lower its priority, and once the cube is gone the ticket is closed as cannot reproduce.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_known_issue_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes` through :mod:`_saga` (one request per take, speech-to-text must hear the
scripted words, voices confirmed by name, no retries); ``tests/test_saga_episodes.py`` checks the script and the
staging against a synthetic recording.
"""

from __future__ import annotations

import sys

from _saga import Reel, effect, line, record, word_at
from srstudio.saga_reel import Entry, Move, Place, Prop, Stage
from srstudio.saga_sets import Panel

TICKET = Panel(0, "TICKET #4471", "Small hole. Goes straight to the reactor. Seems bad?")
TWO_SHOT = (Place("gloom", 300), Place("seven", 780, flip=True))
TAKES = (
    line("01", "narrator", "Why did the deadliest station in the galaxy have a hole that blows it up?", 0.25),
    line("02", "narrator", "Somebody did report it. Nine years ago.", 0.4),
    line("03", "gloom", "Seven. Is the hole fixed?", 0.25),
    line("04", "seven", "It's on the list, my lord.", 0.3),
    line("05", "gloom", "Priority?", 0.2),
    line("06", "seven", "Medium.", 0.5),
    line("07", "gloom", "Rebels are flying at it.", 0.2),
    line("08", "seven", "Low priority, then.", 0.5),
    line("09", "gloom", "They are shooting into it!", 0.15, mood="angry"),
    line("10", "seven", "Nice to have.", 0.7),
    effect("11", "[BOOM]", "A huge deep rumbling space explosion with a long tail", 2.5, 0.1, peak=0.7),
    effect("12", "[DING]", "A cheerful two-note software notification chime", 1.0, 1.6, peak=0.45),
    line("13", "narrator", "The Directorate has since built a new cube. The hole is now listed as a feature.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    cube = Prop("cube", 540, 900)
    return {
        "01": Stage("space", props=(cube,)),
        "02": Stage("space", props=(cube,), panels=(Panel(word_at(t["02"], "report"), TICKET.title, TICKET.body),)),
        "03": Stage("bridge", cast=TWO_SHOT, panels=(TICKET,)),
        "04": Stage("bridge", cast=TWO_SHOT, panels=(Panel(0, "BACKLOG", "4,471 items. Sorted by vibes."),)),
        "05": Stage("bridge", cast=TWO_SHOT, panels=(Panel(0, "BACKLOG", "4,471 items. Sorted by vibes."),)),
        "06": Stage("bridge", cast=TWO_SHOT, panels=(Panel(0, "PRIORITY: MEDIUM"),)),
        "07": Stage("bridge", cast=TWO_SHOT, panels=(Panel(0, "PRIORITY: MEDIUM"),)),
        "08": Stage("bridge", cast=TWO_SHOT, panels=(Panel(0, "PRIORITY: LOW", tone="alert"),)),
        "09": Stage(
            "bridge",
            cast=TWO_SHOT,
            panels=(Panel(0, "PRIORITY: LOW", tone="alert"),),
            move=Move("push", 0, 1.12, 300, 950, until=t["09"].duration),
        ),
        "10": Stage(
            "bridge",
            cast=TWO_SHOT,
            panels=(Panel(0, "PRIORITY: NICE TO HAVE", tone="gold"),),
            move=Move("crash", 0.05, 1.3, 500, 420, back=None),
        ),
        "11": Stage("space", props=(Prop("cube", 540, 900, {"boom": 0.05}),), shake=((0.05, 1.0),)),
        "12": Stage("space", panels=(Panel(0, "TICKET #4471", "Status: CLOSED. Cannot reproduce.", tone="ok"),)),
        "13": Stage(
            entry=Entry(
                "Battle Cube, The",
                "Moon-sized. Planet-ending. One known issue, open for nine years, closed the day it mattered.",
            )
        ),
    }


REEL = Reel(
    slug="saga-known-issue",
    number="S1",
    title="Known Issue — Saga 01",
    description="Portrait space-opera parody: the battle cube's fatal hole sat in the backlog for nine years. Native "
    "vector animation; ElevenLabs voices, effects and music bed.",
    accessible="Cartoon space opera: a cube-shaped battle station, a dark lord and an armoured enforcer on a bridge, "
    "and a hologram ticket; word-by-word captions.",
    takes=TAKES,
    hook="Why did the battle cube have a hole that blows it up?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))

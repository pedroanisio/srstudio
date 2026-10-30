#!/usr/bin/env python3
"""Gloss 08 — Fewer Meetings: the Plaza holds a meeting about having fewer meetings.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_fewer_meetings_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_gloss`; ``tests/test_gloss_episodes.py`` checks the staging. The
reel opens still (the ``sp-hook_motion`` test's arm A): the recording puts :data:`STILL` seconds of silence inside
the first take, and :func:`srstudio.gloss_reel.build` holds the first shot and the hook on their first frame until
Sunny's first word.
"""

from __future__ import annotations

import sys

from _gloss import Reel, line, record, word_at
from srstudio import gloss_reel
from srstudio.gloss_reel import Move, Notice, Place, Stage
from srstudio.gloss_sets import Card

STILL = 1.1  # the still first second: the room, the trio and the hook, before a word is said
ROOM = "12"
TAKES = (
    line("01", "sunny", "Who is ready for our meeting about having fewer meetings?", 0.3),
    line("02", "nadia", "Could this have been an email?", 0.3),
    line("03", "sunny", "Great idea. We will schedule a meeting about emails.", 0.4),
    line("04", "tamsin", "I made an agenda!", 0.3, mood="excited"),
    line("05", "sunny", "Item one. Schedule the next meeting.", 0.4),
    line("06", "nadia", "When does it end?", 0.3),
    line("07", "sunny", "When everyone agrees there are too many meetings.", 0.3),
    line("08", "gus", "We agree.", 0.4),
    line("09", "sunny", "Wonderful. I will send a follow up.", 1.3),
    line("10", "sunny", "Meetings have been reduced to one. It is this one, and it does not end.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    invite = Card(0, "Meeting: Fewer Meetings", "Ends: when resolved.", label="CALENDAR", tone="plum")
    emails = Card(0, "Meeting: About Emails", "Ends: after the email.", label="CALENDAR", tone="plum", carried=True)
    agenda = Card(0, "Agenda", "Item one: schedule the next meeting.", label="AGENDA", carried=True)
    flat = ((0, "flat"),)

    def trio(nadia=(), gus=(), tamsin=(), *, nadia_pose=(), tamsin_pose=(), tamsin_traits=None, host=None) -> tuple:
        cast = (
            Place("nadia", 210, face=nadia, pose=nadia_pose),
            Place("tamsin", 540, face=tamsin, pose=tamsin_pose, traits=tamsin_traits or {}),
            Place("gus", 870, flip=True, face=gus),
        )
        return cast + ((host,) if host else ())

    host = Place("sunny", 870, 500, scale=0.6)
    return {
        # the still first second: the room and the trio waiting under the hook; Sunny is heard, not seen
        "01": Stage("activity", {"number": ROOM}, cast=trio(nadia=flat, gus=flat)),
        "02": Stage("activity", {"number": ROOM}, cast=trio(nadia_pose=((0, "shrug"),), gus=flat), cards=(invite,)),
        "03": Stage(
            "activity",
            {"number": ROOM},
            cast=trio(nadia=((0, "open"), (word_at(t["03"], "meeting"), "flat")), gus=flat, host=host),
            cards=(Card(word_at(t["03"], "meeting"), emails.title, emails.body, label="CALENDAR", tone="plum"),),
        ),
        "04": Stage(
            "activity",
            {"number": ROOM},
            cast=trio(
                nadia=flat,
                gus=flat,
                tamsin_pose=((0, "up"),),
                tamsin_traits={"bounce": ((0.0, t["04"].duration - 0.1),)},
            ),  # fmt: skip
            cards=(Card(0.3, agenda.title, agenda.body, label="AGENDA"),),
        ),
        "05": Stage("activity", {"number": ROOM}, cast=trio(nadia=flat, gus=flat, host=host), cards=(agenda,)),
        "06": Stage("activity", {"number": ROOM}, cast=trio(nadia=((0, "wide"),), gus=flat), cards=(agenda,)),
        "07": Stage(
            "activity",
            {"number": ROOM},
            cast=trio(nadia=flat, gus=flat, host=host),
            move=Move("push", 0.0, 1.18, 540, 900, until=t["07"].duration),
        ),
        "08": Stage(
            "activity",
            {"number": ROOM},
            cast=trio(nadia=flat, gus=flat, tamsin=flat, nadia_pose=((0, "up"),), tamsin_pose=((0, "up"),)),
            cards=(Card(0, "Vote: too many meetings", "Passed. Everyone agrees.", label="MINUTES", points=3),),
        ),
        "09": Stage(  # no board: nothing is left up to fade through the crossfade into the notice
            "activity",
            {"number": ROOM},
            cast=trio(nadia=flat, gus=((0, "flat"), (word_at(t["09"], "follow"), "shut")), tamsin=flat, host=host),
            move=Move("push", word_at(t["09"], "follow"), 1.2, 540, 980, until=t["09"].duration),
        ),
        "10": Stage(
            notice=Notice("Meetings Update", "Meetings have been reduced to one. It is this one, and it does not end.")
        ),  # fmt: skip
    }


REEL = Reel(
    slug="gloss-fewer-meetings",
    number="G8",
    title="Fewer Meetings — Gloss 08",
    description="Portrait satire: the cheerful forever-plaza holds a meeting about having fewer meetings, and it "
    "schedules more of them. Native vector animation; ElevenLabs voices and music bed.",
    accessible="Three glossy toy dolls stand in a pale activity room under a calendar board while a floating orb "
    "host schedules a meeting about meetings; word-by-word captions.",
    takes=TAKES,
    hook="Who is ready for our meeting about having fewer meetings?",
    stages=stages,
    captions=gloss_reel.LOOK_INK,
    still=STILL,
    crf="20",  # 30 s of plaza: the series' crf 18 comes to 22 MB, over the 20 MB master cap
)

if __name__ == "__main__":
    sys.exit(record(REEL))

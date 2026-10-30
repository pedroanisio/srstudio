#!/usr/bin/env python3
"""Gloss 09 — Notifications: the Plaza asks whether the guests would like notifications, and tells them anyway.

    SRSTUDIO_ALLOW_CLOUD=1 python3 gloss_notifications_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_gloss`; ``tests/test_gloss_episodes.py`` checks the staging. The
reel opens moving (the ``sp-hook_motion`` test's arm B): the camera pushes in on Sunny from the first frame.
"""

from __future__ import annotations

import sys

from _gloss import Reel, effect, line, record, word_at
from srstudio import gloss_reel
from srstudio.gloss_reel import Move, Notice, Place, Stage
from srstudio.gloss_sets import Card

TAKES = (
    line("01", "sunny", "Would you like to turn on notifications?", 0.3),
    line("02", "gus", "No thank you.", 0.3),
    effect("03", "[PING]", "a single bright cheerful smartphone notification chime, one short ping", 0.6, 0.6),
    line("04", "nadia", "Did it just notify him that he said no?", 0.3),
    line("05", "sunny", "Notifications keep you up to date.", 0.3),
    line("06", "tamsin", "Turn mine on! All of them!", 0.3, mood="excited"),
    effect(
        "07",
        "[PING PING PING]",
        "a rapid cascade of many bright cheerful smartphone notification chimes, overlapping, getting faster",
        1.8,
        0.4,
    ),
    line("08", "gus", "How do I turn them off?", 0.3),
    line("09", "sunny", "We will notify you when that is possible.", 1.3),
    line("10", "sunny", "To stop receiving notices, please turn on notifications.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    host = Place("sunny", 540, 470, scale=0.7)
    flat = ((0, "flat"),)
    said_no = Card(0, "New notification", "Gus said no thank you.", label="PING", tone="plum", carried=True)

    def room(nadia=(), gus=(), tamsin=(), *, tamsin_pose=(), tamsin_traits=None, sunny=None) -> tuple:
        cast = (
            Place("nadia", 200, face=nadia),
            Place("tamsin", 540, face=tamsin, pose=tamsin_pose, traits=tamsin_traits or {}),
            Place("gus", 880, flip=True, face=gus),
        )
        return cast + ((sunny,) if sunny else ())

    serving = {"serving": ((0, "41"),)}
    d7 = t["07"].duration
    pings = (  # each up long enough to read
        Card(0, "Tamsin blinked", label="PING", tone="plum"),
        Card(round(d7 * 0.5, 3), "You have notifications", "About your notifications.", label="PING", tone="plum"),
    )
    return {
        # arm B: the push on Sunny starts on the first frame
        "01": Stage(
            "waiting", serving, cast=room(sunny=host), move=Move("push", 0.0, 1.18, 540, 640, until=t["01"].duration)
        ),  # fmt: skip
        "02": Stage("waiting", serving, cast=room(gus=flat)),
        "03": Stage(
            "waiting",
            serving,
            cast=room(gus=((0, "open"), (0.2, "flat"))),
            cards=(Card(0, said_no.title, said_no.body, label="PING", tone="plum"),),
        ),  # fmt: skip
        "04": Stage("waiting", serving, cast=room(nadia=((0, "wide"),), gus=flat), cards=(said_no,)),
        "05": Stage("waiting", serving, cast=room(nadia=flat, gus=flat, sunny=host), cards=(said_no,)),
        "06": Stage(
            "waiting",
            serving,
            cast=room(
                nadia=flat,
                gus=flat,
                tamsin_pose=((0, "up"),),
                tamsin_traits={"bounce": ((0.0, t["06"].duration - 0.1),)},
            ),  # fmt: skip
        ),
        "07": Stage(
            "waiting",
            {"serving": ((0, "41"), (round(d7 * 0.5, 3), "42"))},
            cast=room(
                nadia=flat,
                gus=flat,
                tamsin=((0, "open"), (round(d7 * 0.6, 3), "wide")),
                tamsin_traits={"bounce": ((0.0, round(d7 * 0.5, 3)),)},
            ),  # fmt: skip
            cards=pings,
            shake=((round(d7 * 0.5, 3), round(d7 - 0.2, 3)),),
        ),
        "08": Stage(
            "waiting",
            {"serving": ((0, "42"),)},
            cast=room(nadia=flat, gus=flat, tamsin=((0, "wide"),)),
            cards=(Card(0, "Turn off notifications", "Coming soon.", label="SETTINGS", tone="alert"),),
        ),
        "09": Stage(  # no board: nothing is left up to fade through the crossfade into the notice
            "waiting",
            {"serving": ((0, "42"),)},
            cast=room(nadia=flat, gus=flat, tamsin=flat, sunny=host),
            move=Move("crash", word_at(t["09"], "notify"), 1.3, 880, 960, back=t["09"].duration - 0.1),
        ),
        "10": Stage(
            notice=Notice("Notification Settings", "To stop receiving notices, please turn on notifications.")
        ),  # fmt: skip
    }


REEL = Reel(
    slug="gloss-notifications",
    number="G9",
    title="Notifications — Gloss 09",
    description="Portrait satire: the cheerful forever-plaza asks whether its guests would like notifications, "
    "and notifies them that they said no. Native vector animation; ElevenLabs voices, sound effects and music bed.",
    accessible="Three glossy toy dolls wait in a mint waiting room while a floating orb host asks about "
    "notifications and a board pings with every one; word-by-word captions.",
    takes=TAKES,
    hook="Would you like to turn on notifications?",
    stages=stages,
    captions=gloss_reel.LOOK_INK,
)

if __name__ == "__main__":
    sys.exit(record(REEL))

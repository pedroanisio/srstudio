#!/usr/bin/env python3
"""Saga 19, Your Half: mid-battle, one pilot bills the other for half a ration bar, and then for the missile.

    SRSTUDIO_ALLOW_CLOUD=1 python3 your_half_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`. No music and no closing Handbook entry: the reel ends on the
send line, on Rook, on its last word.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from functools import partial

from _saga import Reel, effect, line, record
from srstudio import saga_sets
from srstudio.saga_reel import Place, Prop, Stage

Panel = partial(saga_sets.Panel, fade=True)  # fades in, so each panel is judged as read (strict contrast)

SEATS = (Place("rook", 330, behind=True), Place("juno", 760, flip=True, behind=True))
ROOK_CLOSE = (Place("rook", 500, 1560, scale=1.55, behind=True),)  # a cast placed closer, so the console's marks stay
JUNO_CLOSE = (Place("juno", 580, 1560, scale=1.55, flip=True, behind=True),)
BITE = Panel(0, "ROOK REQUESTS 3.40 CR", "Half a ration bar.", tone="gold")
MISSILE = Panel(0, "ROOK REQUESTS 897.40 CR", "Missile damage.", tone="alert")
PAID = Panel(0, "PAID: 897 CR", tone="gold")
FIGHTERS = (Prop("fighter", 800, 330, {"scale": 0.4}), Prop("fighter", 480, 470, {"scale": 0.3}))  # in the window
PING = "A single soft cheerful two-note app notification ping, clean"
TAKES = (
    line("01", "narrator", "Who is the deadliest roommate in the galaxy?", 0.15),
    effect("02", "[FIRE]", "Distant laser fire, three shots, then a single soft two-note app ping", 1.1, 0.0, peak=0.5),
    line("03", "juno", "We're under fire. You're billing me?", 0.25, mood="angry"),
    line("04", "rook", "You said one bite.", 0.3),
    effect("05", "[HIT]", "A missile hit on a spaceship hull, sparks, a short alarm, then quiet", 1.2, 0.0, peak=0.6),
    effect("06", "[PING]", PING, 0.6, 0.3, peak=0.5),
    line("07", "juno", "You're billing me for the missile?", 0.25, mood="angry"),
    line("08", "rook", "It hit your side.", 0.25),
    effect(
        "09",
        "[PAID]",
        "One sharp fingertip tap on glass, a beat of silence, then a soft two-note ping",
        1.6,
        0.2,
        peak=0.5,
    ),
    line("10", "rook", "You rounded down.", 0.1),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def cockpit(*panels: saga_sets.Panel, close=SEATS, **kw) -> Stage:
        return Stage("cockpit", cast=close, panels=panels, **kw)

    hit, jab = t["05"].duration, t["09"].duration
    return {
        "01": cockpit(shake=((0.2, 0.75), (1.4, 1.9)), props=FIGHTERS),
        "02": cockpit(BITE),
        "03": cockpit(BITE, close=JUNO_CLOSE),
        "04": cockpit(BITE, close=ROOK_CLOSE),
        "05": cockpit(shake=((0.0, hit * 0.6),), options={"jump": ((hit * 0.35, hit),)}),
        "06": cockpit(MISSILE),
        "07": cockpit(MISSILE, close=JUNO_CLOSE),
        "08": cockpit(MISSILE, close=ROOK_CLOSE),
        "09": cockpit(MISSILE, replace(PAID, start=round(jab - 0.9, 3)), close=JUNO_CLOSE),
        "10": cockpit(PAID, close=ROOK_CLOSE),
    }


REEL = Reel(
    slug="your-half",
    number="S19",
    title="Your Half — Saga 19",
    description="Portrait space-opera parody: under fire, one pilot sends the other a payment request for half a "
    "ration bar, and then for the missile. Native vector animation; ElevenLabs voices and effects, no music.",
    accessible="Cartoon space opera: two pilots in a cockpit under fire; a hologram shows a payment request for half a "
    "ration bar, a missile hits, a second request for the damage, and she pays it, rounded down; word-by-word "
    "captions.",
    takes=TAKES,
    hook="YOUR HALF",
    stages=stages,
    bleed=True,
    bed=False,
    loudness="-14",
)

if __name__ == "__main__":
    sys.exit(record(REEL))

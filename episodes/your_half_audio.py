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
from srstudio import saga, saga_sets
from srstudio.saga_reel import Place, Prop, Stage, Throw

Panel = partial(saga_sets.Panel, fade=True)  # fades in, so each panel is judged as read (strict contrast)

SEATS = (Place("rook", 330, behind=True), Place("juno", 760, flip=True, behind=True))
THROWN = (  # the missile comes in on her side: she goes first and hardest, he follows two frames on
    Place(
        "rook",
        330,
        behind=True,
        lurch=((0.0, 0, 0), (0.12, -26, -5.0), (0.4, 14, 2.5), (0.7, -6, -1.0), (1.0, 0, 0)),
        mouth=((0.1, "round"), (0.85, "closed")),
    ),
    Place(
        "juno",
        760,
        flip=True,
        behind=True,
        lurch=((0.0, -12, -2.0), (0.08, -48, -9.0), (0.35, 22, 4.0), (0.62, -10, -1.5), (0.95, 0, 0)),
        mouth=((0.0, "shout"), (0.9, "closed")),
    ),
)
THROW = Throw(  # the cabin rolls away from the hit: the scale keeps the set past the frame through the roll and shake
    roll=((0.0, 2.0), (0.06, 5.0), (0.3, -3.0), (0.55, 1.4), (0.8, -0.5), (1.05, 0.0)),
    scale=((0.0, 1.18), (0.35, 1.12), (0.7, 1.05), (1.05, 1.0)),
)
JAB = saga_sets.Jab(  # her right arm comes over the console from the sleeve, and the hand stays on the stick
    at=0.2, sleeve="#efe2c4", hand=saga.SKIN["deep"], elbow=(404, 1040), scale=1.55
)
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

    def cockpit(*panels: saga_sets.Panel, close=SEATS, front=None, **kw) -> Stage:
        return Stage("cockpit", cast=close, panels=panels, front={"ledge": True, **(front or {})}, **kw)

    hit, jab = t["05"].duration, t["09"].duration
    return {
        "01": cockpit(shake=((0.2, 0.75), (1.4, 1.9)), props=FIGHTERS),
        "02": cockpit(BITE),
        "03": cockpit(BITE, close=JUNO_CLOSE),
        "04": cockpit(BITE, close=ROOK_CLOSE),
        "05": cockpit(
            close=THROWN, shake=((0.0, hit * 0.6),), options={"hit": 0.0}, front={"hit": 0.0}, thrown=THROW
        ),  # on the first frame of the effect, whose bang is its first quarter second
        "06": cockpit(MISSILE),
        "07": cockpit(MISSILE, close=JUNO_CLOSE),
        "08": cockpit(MISSILE, close=ROOK_CLOSE),
        "09": cockpit(MISSILE, replace(PAID, start=round(jab - 0.9, 3)), close=JUNO_CLOSE, front={"jab": JAB}),
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

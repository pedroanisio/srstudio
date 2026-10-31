#!/usr/bin/env python3
"""Stick 22 — Seat Belt Sign, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 seat_belt_sign_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build seat-belt-sign PROJECT                                      # → PROJECT/seat-belt-sign.scene.xml

Dev stands the second the plane lands, fights his way up to row 14, and the cabin leaves by the rear door. The rows are
``stick_airport.cabin`` hung lower in the frame; the aisle, the turning queue, the book and the bags are ``stick_odds``.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from seat_belt_sign_audio import (
    BURIED,
    CALM,
    CHILD,
    COATS,
    DEADPAN,
    DEV,
    DROP,
    DRY,
    GLAD,
    HOOK,
    NOOR,
    NUMB,
    POSES,
    PROUD,
    READING,
    SHIFT,
    SHOCK,
    SMUG,
    STRANGERS,
    UPWARD,
)
from srstudio import SPEECH_MOUTH, Episode, stick, stick_airport, stick_odds, stick_reel

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "seat-belt-sign",
        "R22",
        "Seat Belt Sign — Stick 22",
        "Portrait stick-figure cartoon: a man stands up the second the plane lands and fights his way forward, then "
        "the cabin leaves by the rear door. Native vector animation; ElevenLabs voices and effects.",
        3122,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
K = stick.RigKey
FLOOR = 1700.0
SEAT_X = 840.0  # Noor's seat, on the aisle
BIG, BIG_DROP = 1.45, 2100.0  # the tight shots
BOOK_AT = (866.0, 1250.0)
OPEN_AT = (814.0, 1250.0)  # the same book, in the mirrored figure's hand
DEV_X = 430.0  # Dev, bent double in the row
EXIT = -860.0  # Dev's slide along the row, gone from the frame


def figure(parent, keys, end: float, look, x: float, take=None, *, who: str = "", flip: bool = False,
           scale: float = 1.0, floor: float = DROP):  # fmt: skip
    """A figure with its pose's middle at ``x`` and its feet on ``floor``."""
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}
    at = (x + 540 * scale if flip else x - 540 * scale, floor - FLOOR * scale)
    return stick.rig(cv, parent, keys, end, poses=POSES, look=look, at=at, scale=scale, flip=flip, mouth=SPEECH_MOUTH,
                     **speaks)  # fmt: skip


def row(parent, number: str) -> None:
    """The cabin, hung lower: what shows over the bins is the ceiling."""
    stick.box(cv, parent, 0, 0, cv.width, SHIFT + 20, stick_airport.CABIN_TOP)
    stick_airport.cabin(cv, cv.group(parent, cv.uid("row"), y=SHIFT), row=number)


def noor_seated(parent, take, end: float, *, face, keys=None) -> None:
    speaks = dict(phones=take.phones, mood=take.mood) if take.actor == "noor" else {}
    stick.rig(cv, parent, keys or [K(0, "tucked-up", face)], end, poses=POSES, look=NOOR, at=(SEAT_X - 540, SHIFT),
              mouth=SPEECH_MOUTH, **speaks)  # fmt: skip


def strangers(parent, end: float) -> None:
    for x, look, colour in zip((70.0, 225.0), STRANGERS, COATS, strict=False):
        keys = [K(0, "stand", DEADPAN)]
        figure(parent, keys, end, look, x)
        stick_odds.robe(cv, parent, keys, end, POSES, at=(x - 540, DROP - FLOOR), colour=colour, belt="#3b4048")


def wedged(parent, take, end: float, pose: str, face, *, bag: bool) -> None:
    """Row 14, tight: a stranger's arm up at the bin and Dev's ear in the armpit, in a figure big enough to read."""
    row(parent, "14")
    keys = [K(0, "reach", DEADPAN)]
    figure(parent, keys, end, STRANGERS[0], 790.0, scale=BIG, floor=BIG_DROP)
    stick_odds.robe(cv, parent, keys, end, POSES, at=(790 - 540 * BIG, BIG_DROP - FLOOR * BIG), scale=BIG,
                    colour=COATS[0], belt="#3b4048")  # fmt: skip
    figure(parent, [K(0, pose, face)], end, DEV, 620.0, take, who="dev", scale=BIG, floor=BIG_DROP)
    if bag:
        stick_odds.duffel(cv, parent, 380.0, 960.0, scale=1.3)


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "row":
        row(g, "31")
        strangers(g, end)
        noor_seated(g, take, end, face=CALM if take.actor == "noor" else READING)
        stick_odds.book(cv, g, *BOOK_AT)
        figure(g, [K(0, "bent", SMUG)], end, DEV, DEV_X, take, who="dev")
        stick_odds.duffel(cv, g, 490.0, 880.0, scale=0.9)
    elif take.shot == "squeeze":
        row(g, "31")
        strangers(g, end)
        noor_seated(g, take, end, face=READING)
        stick_odds.book(cv, g, *BOOK_AT)
        moving = cv.group(g, cv.uid("dev"))
        if take.is_effect:
            cv.keys(moving, "x", [(0.0, -200.0), (end, EXIT)], kind="linear")
        else:
            cv.keys(moving, "x", [(0.0, 0.0), (end, -200.0)], kind="linear")
        figure(moving, [K(0, "bent", SMUG)], end, DEV, DEV_X, take, who="dev")
    elif take.shot == "moved":
        wedged(g, take, end, "wedged", GLAD, bag=False)
        stick.card(cv, g, "9 minutes", size=78)
    elif take.shot == "neck":
        heard = take.actor == "cabin" or take.is_effect
        wedged(g, take, end, "limp", SHOCK if heard else NUMB, bag=True)
        figure(g, [K(0, "kid", UPWARD)], end, CHILD, 220.0, scale=0.55, floor=1880.0)
        stick.card(cv, g, "16 minutes", size=78)
    elif take.shot == "turn":
        stick_odds.aisle(cv, g)
        stick_odds.queue(cv, g, end, turn=end * 0.4)
    elif take.shot == "noor":
        row(g, "31")
        if take.is_effect:
            keys = [K(0, "in-seat", READING), K(0.5, "stand", PROUD), K(0.9, "stretch", PROUD), K(1.4, "carry", DRY)]
        else:
            keys = [K(0, "carry", DRY)]
        stick_airport.carry_on(cv, g, 690.0, DROP, tag=None)
        figure(g, keys, end, NOOR, SEAT_X, take, who="noor", flip=True)
        if take.is_effect:
            cv.gate(stick_odds.book(cv, g, *OPEN_AT), [(0, 0.2)])
            cv.gate(stick_odds.book(cv, g, *OPEN_AT, shut=True), [(0.2, 0.5)])
    else:  # last
        wedged(g, take, end, "limp", BURIED, bag=True)


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=78)
cv.gate(hook, [(0, t.takes[2].start)])
spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({}), loudness="-14")
stick_reel.close(ep, POSTS["seat-belt-sign"], hook, spoken)

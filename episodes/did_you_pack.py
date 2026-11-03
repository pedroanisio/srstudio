#!/usr/bin/env python3
"""Stick 21 — Did You Pack, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 did_you_pack_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build did-you-pack PROJECT                                      # → PROJECT/did-you-pack.scene.xml

Grandma feeds Dev past full and packs his bag for a two-hour flight; the scanner finds a chicken, a lasagna and a
rolling pin, and on top a note for the man at security. The sets are ``stick_home``, ``stick_street`` and
``stick_airport``; the scanner and the food are ``stick_odds``; the figures are ``stick.rig``.
"""

import os

from _common import project_root
from did_you_pack_audio import (
    BAG_FROM,
    BAG_X,
    COAT,
    DEV,
    DEV_X,
    DOWN,
    DUTY,
    FEAR,
    FED,
    FIRM,
    FLAT,
    FULL,
    GRANDMA,
    HER_X,
    HOOK,
    NOTE,
    OFFICER,
    OFFICER_X,
    PLATE_AT,
    PLEADING,
    POSES,
    READING,
    SEAT_X,
    SIGN,
    STILL,
    STREET_SCALE,
    STREET_Y,
    SURE,
    WOBBLE_A,
    WOBBLE_B,
    XRAY,
)
from instagram_posts import POSTS
from srstudio import (
    SPEECH_MOUTH,
    Episode,
    signature,
    stick,
    stick_airport,
    stick_home,
    stick_odds,
    stick_reel,
    stick_street,
)

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "did-you-pack",
        "R21",
        "Did You Pack — Stick 21",
        "Portrait stick-figure cartoon: a grandmother packs a meal into her grandson's bag and it reaches airport "
        "security. Native vector animation; ElevenLabs voices and effects.",
        3121,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
K = stick.RigKey
FLOOR = 1700.0


def figure(parent, keys, end: float, look, x: float, take=None, *, who: str = "", flip: bool = False,
           scale: float = 1.0, floor: float = FLOOR, blinks=()):  # fmt: skip
    """A figure with its middle at ``x`` and its feet on ``floor``, facing right unless ``flip``."""
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}
    at = (x + 540 * scale if flip else x - 540 * scale, floor - FLOOR * scale)
    return stick.rig(cv, parent, keys, end, poses=POSES, look=look, at=at, scale=scale, flip=flip, mouth=SPEECH_MOUTH,
                     blinks=blinks, **speaks)  # fmt: skip


def kitchen(parent, take, end: float, *, heap: int, spooned: bool) -> None:
    stick_home.kitchen(cv, parent)
    figure(parent, [K(0, "seated", FULL)], end, DEV, SEAT_X, take, who="dev")
    stick_home.table(cv, parent)
    figure(parent, [K(0, "serve", FIRM)], end, GRANDMA, HER_X, take, who="grandma", flip=True)
    stick_odds.plate(cv, parent, *PLATE_AT, heap=heap, scale=1.1)
    stick_odds.spoon(cv, parent, (560, 925), (520, 1020) if spooned else (470, 1000), full=not spooned)


def officer(parent, keys, end: float, take=None) -> None:
    figure(parent, keys, end, OFFICER, OFFICER_X, take, who="officer", flip=True)


def checkpoint(parent) -> None:
    """The terminal, with the checkpoint's own sign hung where the boarding sign was."""
    stick_airport.gate(cv, parent, gate="S1", now="SECURITY")
    stick_odds.poster(cv, parent, *SIGN, "SECURITY", size=74)
    cv.line(parent, 243, 892, 243, 1000, cv.ink, 6)  # the rear gear's own leg is behind the window's bar


def lane(parent, end: float, *, bag: float, keys, dev_keys, take=None) -> None:
    checkpoint(parent)
    signature.cactus(cv, parent, 80, 1384, scale=0.42)  # on a seat: the belt stands in front of the terminal's own
    figure(parent, dev_keys, end, DEV, DEV_X, take, who="dev")
    officer(parent, keys, end, take)
    stick_odds.scan_belt(cv, parent)
    moving = cv.group(parent, cv.uid("bag"))
    if bag != BAG_X:
        cv.keys(moving, "x", [(0.0, bag - BAG_X), (end * 0.7, 0.0)], kind="linear")
    stick_airport.carry_on(cv, moving, BAG_X, stick_odds.BELT_TOP, tag=None, hanging=True)


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "table":
        kitchen(g, take, end, heap=2, spooned=False)
        signature.cactus(cv, g, 930, 1560, scale=0.42)  # the hook card covers the window's
    elif take.shot == "plate":
        frame = stick.camera(cv, g, (570, 1120), zoom=1.35, to=(540, 900))
        kitchen(frame, take, end, heap=3, spooned=True)
        signature.code(cv, g, 40, 1885, 9, color="#3d2c1c")  # the push leaves the kitchen's own below the frame
    elif take.shot == "door":
        stick_street.street(cv, g)
        signature.cactus(cv, g, 110, 1400, scale=0.42)  # the suitcase stands in front of the street's own
        dev_keys = [K(0, "stand", PLEADING if take.actor == "dev" else FULL)]
        figure(g, dev_keys, end, DEV, 300.0, take, who="dev", scale=STREET_SCALE, floor=STREET_Y)
        stick_odds.robe(cv, g, dev_keys, end, POSES, at=(300.0 - 540 * STREET_SCALE, STREET_Y - FLOOR * STREET_SCALE),
                        scale=STREET_SCALE, colour=COAT, belt="#4a3f33")  # fmt: skip
        stick_airport.carry_on(cv, g, 610.0, STREET_Y, tag=None, hanging=True)
        figure(g, [K(0, "zip", SURE if take.is_effect else FIRM)], end, GRANDMA, 830.0, take, who="grandma", flip=True,
               scale=STREET_SCALE, floor=STREET_Y)  # fmt: skip
    elif take.shot == "belt":
        lane(g, end, bag=BAG_FROM, keys=[K(0, "stand", DUTY)], dev_keys=[K(0, "stand", FEAR)])
    elif take.shot == "medium":
        frame = stick.camera(cv, g, (1080, 0), zoom=1.35, to=(1080, 0))
        lane(frame, end, bag=BAG_X, keys=[K(0, "peer", DUTY)], dev_keys=[K(0, "stand", FLAT)], take=take)
    elif take.shot == "two":
        lane(g, end, bag=BAG_X, keys=[K(0, "peer", DUTY)], dev_keys=[K(0, "stand", FEAR)], take=take)
    elif take.shot == "xray":
        stick_odds.xray(cv, g, end, XRAY)
        signature.cactus(cv, g, 960, 1440, scale=0.42)  # no room in this shot: both marks stay on the screen
        signature.code(cv, g, 40, 1885, 9, color="#7f9bb0")
    elif take.shot == "note":
        stick_odds.foil_note(cv, g, NOTE)
        signature.cactus(cv, g, 900, 1268, scale=0.42)  # she signs her notes with it
        signature.code(cv, g, 40, 1885, 9, color="#3d4650")
    elif take.shot == "wobble":
        checkpoint(g)
        if take.is_effect:
            keys = [K(0, "note", READING), K(0.45, "note", DOWN), K(0.85, "note", WOBBLE_A), K(1.0, "note", WOBBLE_B)]
        else:
            keys = [K(0, "note", WOBBLE_A)]
        figure(g, keys, end, OFFICER, 540.0, take, who="officer", flip=True, scale=1.2, floor=1960.0)
        stick_odds.foil_parcel(cv, g, 420.0, 1000.0, scale=0.9)
    else:  # bite
        checkpoint(g)
        keys = [K(i * 0.3, "bite-wave" if i % 2 else "bite", FED) for i in range(int(end / 0.3) + 1)]
        figure(g, keys, end, OFFICER, 540.0, flip=True, scale=1.2, floor=1960.0)
        stick_odds.foil_parcel(cv, g, 440.0, 992.0, scale=0.8)  # at his hand, clear of his face


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=78)
cv.gate(hook, [(0, STILL)])  # it stops where the same words start as spoken words
spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({}), loudness="-14")
stick_reel.close(ep, POSTS["did-you-pack"], hook, spoken, first_word=True)

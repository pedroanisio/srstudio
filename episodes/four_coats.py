#!/usr/bin/env python3
"""Stick 14 — Four Coats, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 four_coats_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build four-coats PROJECT                                      # → PROJECT/four-coats.scene.xml

A bag at 23.4 costs sixty dollars, so the traveler wears it. One wide at the gate and one at the other end, same agent.
The scale's readout and the coat ball are ``stick_airport``; the camera never moves, the sphere does.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, stick, stick_airport, stick_reel

os.umask(0o077)
ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "four-coats",
        "R14",
        "Four Coats — Stick 14",
        "Portrait stick-figure cartoon: a traveler wears her whole suitcase to save sixty dollars. Native vector "
        "animation; ElevenLabs voices and effects.",
        3104,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")

TRAVELER = stick.Look(hair="bun")
AGENT = stick.Look(hair="side-part", glasses=True, tie="#2a9d8f")
AT = (-150.0, 0.0)  # the traveler, at x 390, facing the podium
X, CHIN = 390, 842  # where the ball hangs
BAG_X, BAG_Y = 560, 1664
READOUT = (772, 1215, 290, 170)  # right of the luggage tag
TO_THE_DESK = stick.Face("open", "flat", "flat", look=(1, 0))
HURT = stick.Face("wide", "raised", "frown", look=(1, 0))
PLOT = stick.Face("half", "angry", "smirk", look=(1, 0))
DONE = stick.Face("open", "flat", "smile", look=(1, 0))
PEACE = stick.Face("happy", "flat", "smile", look=(1, 0))
DEADPAN = stick.Face("half", "flat", "flat", look=(1, 0))
SORRY = stick.Face("half", "worried", "frown", look=(1, 0))

# What she has on, in order; a stage is the coat_ball's radius and keywords, with what is left in the bag.
ONE = (180, dict(layers=1))
TWO = (220, dict(layers=2, hats=1, trousers=True))
THREE = (255, dict(layers=2, hats=2, trousers=True))
FOUR = (285, dict(layers=3, hats=3, scarves=1, trousers=True))
FIVE = (305, dict(layers=3, hats=3, scarves=2, trousers=True, shoes=True))
SPHERE = (325, dict(layers=4, hats=4, scarves=3, trousers=True, shoes=True))
SLAM = ((0.0, "0.0"), (0.08, "12.7"), (0.2, "31.9"), (0.32, "19.6"), (0.44, "23.4"))
WEIGHED = {"02": "23.4", "03": "23.4", "04": "23.4", "05": "23.4", "07": "23.3", "09": "23.1", "11": "22.9",
           "12": "22.9", "13": "22.9", "14": "22.9"}  # fmt: skip
CHANGING = {"06": ((0.0, "23.4"), (0.72, "23.3")), "08": ((0.0, "23.3"), (0.8, "23.2"), (1.3, "23.1")),
            "10": ((0.0, "23.1"), (0.7, "23.0"), (1.4, "22.9")), "01": SLAM}  # fmt: skip
BAG_LEFT = {"01": 1.0, "02": 1.0, "03": 1.0, "04": 1.0, "05": 1.0, "06": 0.9, "07": 0.9, "08": 0.78, "09": 0.72,
            "10": 0.6, "11": 0.5, "12": 0.5, "13": 0.5, "14": 0.5}  # fmt: skip
DRESSING = {"06": ((0.0, None), (0.55, ONE)), "08": ((0.0, ONE), (0.3, TWO), (0.75, THREE), (1.2, FOUR)),
            "10": ((0.0, FOUR), (0.6, FIVE), (1.2, SPHERE))}  # fmt: skip
WORN = {"07": ONE, "09": FOUR, "11": SPHERE, "12": SPHERE, "13": SPHERE, "14": SPHERE, "15": SPHERE,
        "16": SPHERE}  # fmt: skip


def dressed(parent, stages, end: float) -> None:
    """The ball through ``stages``, each from its start until the next."""
    for (start, stage), until in zip(stages, [*[s for s, _ in stages[1:]], end], strict=True):
        if stage is None:
            continue
        one = cv.group(parent, cv.uid("worn"))
        cv.gate(one, [(start, until)])
        stick_airport.coat_ball(cv, one, X, CHIN, stage[0], **stage[1])


def bag(parent, left: float, end: float, *, drop: bool = False) -> None:
    """The carry-on on the platter, squashed to what is ``left`` of it; on frame one it is still landing."""
    g = cv.group(parent, cv.uid("bag"), x=BAG_X, y=BAG_Y, anchorX=BAG_X, anchorY=BAG_Y, scaleY=left)
    if drop:
        cv.keys(g, "y", [(0, BAG_Y - 760), (0.09, BAG_Y), (0.17, BAG_Y - 36), (0.27, BAG_Y)], kind="linear")
    stick_airport.carry_on(cv, g, BAG_X, BAG_Y, tag="GROUP 4")


def agent(parent, keys, end: float, take=None) -> None:
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == "agent" else {}
    stick.rig(cv, parent, keys, end, poses=stick.STANDING, look=AGENT, at=stick_airport.AGENT_AT, flip=True,
              mouth=SPEECH_MOUTH, **speaks)  # fmt: skip


def traveler(parent, keys, end: float, take=None) -> None:
    hers = take is not None and take.actor in ("traveler", "muffled")
    speaks = dict(phones=take.phones, mood=take.mood) if hers else {}
    stick.rig(cv, parent, keys, end, poses=stick.STANDING, look=TRAVELER, at=AT, mouth=SPEECH_MOUTH, **speaks)


def sweat(parent, end: float) -> None:
    """Drops running off the ball onto the floor, each on its own loop."""
    for i, (x, top) in enumerate(((120, 1120), (640, 1090), (200, 1320), (580, 1310), (390, 1490), (300, 1460))):
        for start in [0.13 * i + 0.6 * k for k in range(int(end / 0.6) + 1)]:
            if start >= end:
                continue
            until = min(end, start + 0.5)
            drop = cv.group(parent, cv.uid("drop"), x=0, y=0)
            cv.gate(drop, [(start, until)])
            cv.keys(drop, "y", [(start, 0), (until, 230)], kind="linear")
            stick.oval(cv, drop, x - 15, top, 30, 48, "#6fb7e6")


def gate_shot(take, g, end: float) -> None:
    stick_airport.gate(cv, g, gate="B9", now="LAST CALL", boarding_size=stick_airport.BOARDING_SIZE)
    face = DEADPAN
    agent(g, [stick.RigKey(0, "stand", face)], end, take)
    stick_airport.podium(cv, g, gate="B9", plate=False)
    readings = CHANGING.get(take.id, ((0.0, WEIGHED.get(take.id)),))
    stick.box(cv, g, 716, 1266, 56, 108, stick_airport.PODIUM_FRONT)  # the blank plate, beside the readout
    stick_airport.bag_scale(cv, g, BAG_X, 1700, readings, end, readout=READOUT)
    bag(g, BAG_LEFT[take.id], end, drop=take.id == "01")
    body = cv.group(g, cv.uid("body"))
    if take.id == "14":
        cv.keys(body, "x", [(0, 0), (0.25, -60), (0.75, -120), (1.25, -180)], hold=True)
        keys = [stick.RigKey(0, "stand", stick.Face("happy", "flat", "smile", look=(0.4, 0))),
                stick.RigKey(0.5, "stand", stick.Face("happy", "flat", "smile", look=(0, 0))),
                stick.RigKey(1.0, "stand", stick.Face("happy", "flat", "smile", look=(-1, 0)))]  # fmt: skip
    elif take.id == "04":
        keys = [stick.RigKey(0, "shrug", HURT)]
    elif take.id == "05":
        keys = [stick.RigKey(0, "shrug", HURT), stick.RigKey(0.5, "stand", PLOT)]
    elif take.id in ("12", "13"):
        keys = [stick.RigKey(0, "stand", DONE)]
    elif take.id in DRESSING or take.id in WORN:
        keys = [stick.RigKey(0, "stand", PLOT)]
    else:
        keys = [stick.RigKey(0, "stand", TO_THE_DESK)]
    traveler(body, keys, end, take)
    if take.id in DRESSING:
        dressed(body, DRESSING[take.id], end)
    elif take.id in WORN:
        dressed(body, ((0.0, WORN[take.id]),), end)


def arrivals_shot(take, g, end: float) -> None:
    stick_airport.gate(cv, g, gate="A1", now="WELCOME 38°", boarding_size=stick_airport.BOARDING_SIZE)
    stick.oval(cv, g, 310, 330, 170, 170, "#ffd23f")  # the sun in the window
    stick_airport.palm(cv, g, 200, 1180, height=640)
    stick.box(cv, g, 0, 0, cv.width, cv.height, "#ff9d2e", opacity=0.2)
    face = SORRY
    agent(g, [stick.RigKey(0, "stand", face)], end, take)
    stick_airport.podium(cv, g, gate="LOST")
    traveler(g, [stick.RigKey(0, "stand", PEACE)], end, take)
    dressed(g, ((0.0, WORN[take.id]),), end)
    sweat(g, end)


for take in t.takes:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "gate":
        gate_shot(take, g, end)
    else:
        arrivals_shot(take, g, end)

spoken = stick_reel.words(ep, t.takes, sentences=True)
ep.audio(take=stick_reel.placing({}))
stick_reel.close(ep, POSTS["four-coats"], spoken)

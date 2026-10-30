#!/usr/bin/env python3
"""Stick 13 — The Stove, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_stove_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build the-stove PROJECT                                      # → PROJECT/the-stove.scene.xml

Dev and Noor leave for a holiday, and turn back for the stove, and for the door, and for an iron they do not own.
They never reach the airport. The car is ``stick_windshield``; the road home is ``stick_street``.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, stick, stick_reel
from srstudio import stick_street as st
from srstudio import stick_windshield as ws
from the_stove_audio import (
    CAMERAS,
    DEV_GO,
    DEV_OLD,
    GREY,
    HOOK,
    KID_SCALE,
    LEVEL,
    NEIGHBOUR,
    NOOR_GO,
    NOOR_OLD,
    SHUT,
    SOUR,
    STARE,
    TIRED,
    TREE,
    TURN_CUT,
    WAVING,
    WEARY,
    WORRIED,
)

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "the-stove",
        "R13",
        "The Stove — Stick 13",
        "Portrait stick-figure cartoon: a couple turn back to check the stove, and never stop. Native vector "
        "animation; ElevenLabs voices and effects.",
        1313,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
SEAT = {"noor": ws.PASSENGER_AT, "dev": ws.DRIVER_AT}
SPEED = 2.5


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def drive(parent, take, *, looks, noor, dev, pose="drive") -> None:
    """The couple through the windshield, the holiday on the back seat behind them."""
    end = take.duration
    ws.windshield(cv, parent, end, speed=SPEED)
    st.suitcases(cv, parent, 540.0, 980.0)
    for who, face, stance in (("noor", noor, "sit"), ("dev", dev, pose)):
        speaks = dict(phones=take.phones, mood=take.mood) if take.actor == who else {}
        stick.rig(cv, parent, [stick.RigKey(0, stance, face)], end, poses=ws.FRONT, look=looks[who], at=SEAT[who],
                  mouth=SPEECH_MOUTH, **speaks)  # fmt: skip
    ws.dashboard(cv, parent, end)


def u_turn(parent, take, scars: int) -> None:
    """The road from above; the car comes up it, swings round and goes back the way it came."""
    end = take.duration
    st.road_plan(cv, parent, scars=scars)
    a, b, c = end * 0.3, end * 0.55, end * 0.8
    points = ((0.0, 740.0, 1700.0, 0.0), (a, 740.0, 1000.0, 0.0), (b, 540.0, 640.0, -90.0), (c, 340.0, 1000.0, -180.0),
              (end, 340.0, 1500.0, -180.0))  # fmt: skip
    g = stick._group(cv, parent, x=740.0, y=1700.0, rotation=0.0)
    for i, prop in ((1, "x"), (2, "y"), (3, "rotation")):
        cv.keys(g, prop, [(p[0], p[i]) for p in points], hold=False)
    st.top_car(cv, g)


def home(parent, take, visit: int, *, end=None) -> None:
    """The house, a little older: the neighbour waves, the children wave, and the car pulls up."""
    end = end or take.duration
    st.street(cv, parent, tree=TREE[visit])
    room = st.in_window(cv, parent)
    scale = KID_SCALE[visit]
    for x, hair in ((700.0, "bun"), (880.0, "cowlick")):
        head_y = 880.0
        at = (x - 540 * scale, head_y - 750 * scale)
        stick.rig(cv, room, [stick.RigKey(0, "wave", WAVING)], end, poses=stick.STANDING, look=stick.Look(hair=hair),
                  at=at, scale=scale)  # fmt: skip
    st.window_frame(cv, parent)
    stick.rig(cv, parent, [stick.RigKey(0, "wave", WAVING)], end, poses=stick.STANDING, look=NEIGHBOUR[visit],
              at=(70.0, 330.0), scale=0.62)  # fmt: skip
    car = stick._group(cv, parent, x=-760.0, y=1640.0)
    cv.keys(car, "x", [(0.0, -760.0), (min(0.7, end * 0.6), 190.0)], hold=False)
    st.side_car(cv, car)


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    shot = take.shot
    young = {"noor": NOOR_GO, "dev": DEV_GO}
    if shot in ("road1", "road2", "road3"):
        speaking = {"01": (WORRIED, LEVEL), "02": (WORRIED, LEVEL), "03": (WORRIED, STARE), "07": (WORRIED, STARE),
                    "11": (TIRED, STARE), "12": (TIRED, SOUR)}[take.id]  # fmt: skip
        drive(camera(g, "two"), take, looks=young, noor=speaking[0], dev=speaking[1])
    elif shot.startswith("turn"):
        u_turn(g, take, int(shot[-1]) - 1)
    elif shot == "home1":
        home(g, take, 1)
    elif shot == "home2":
        home(g, take, 2)
    elif shot == "knob":
        st.stove_knob(cv, g)
    elif shot == "lock":
        st.door_lock(cv, g)
    elif shot == "sign":
        st.road_ahead(cv, g)
        st.road_sign(cv, g, end, text="AIRPORT 2")
    elif shot == "home3":
        wide = cv.group(g, cv.uid("street"))
        cv.gate(wide, [(0, TURN_CUT)])
        home(wide, take, 3)
        close = cv.group(g, cv.uid("window"))
        cv.gate(close, [(TURN_CUT, end)])
        home(camera(close, "window"), take, 3)
    else:  # old
        frame = cv.group(g, cv.uid("old"))
        turn = take.speech_duration + 0.35
        two = cv.group(frame, cv.uid("two"))
        cv.gate(two, [(0, turn)])
        drive(camera(two, "two"), take, looks={"noor": NOOR_OLD, "dev": DEV_OLD}, noor=TIRED, dev=WEARY, pose="slump")
        close = cv.group(frame, cv.uid("dev"))
        cv.gate(close, [(turn, end)])
        inner = camera(close, "dev")
        drive(inner, take, looks={"noor": NOOR_OLD, "dev": DEV_OLD}, noor=TIRED, dev=SHUT, pose="slump")
        stick.box(cv, g, 0, 0, cv.width, cv.height, GREY, opacity=0.38)


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, t.takes[1].start)])
spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({}))
stick_reel.close(ep, POSTS["the-stove"], hook, spoken)

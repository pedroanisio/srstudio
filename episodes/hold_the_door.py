#!/usr/bin/env python3
"""Stick 10 — Hold the Door, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 hold_the_door_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build hold-the-door PROJECT                                      # → PROJECT/hold-the-door.scene.xml

Dev holds a glass door for a stranger who is far too far away. The stranger starts the apologetic jog, and they are
both committed. A crowd goes through; day turns to night; it snows; a marathon goes by. Three steps from the door,
years later, Dev's arm gives out. The set is ``stick_door``; the figures are ``stick.rig``.
"""

import os

from _common import project_root
from hold_the_door_audio import (
    BRIGHT,
    CAMERAS,
    CROWD,
    CUT_AT,
    DEV,
    FACE_AT,
    FACE_SCALE,
    FAR,
    FIXED,
    FROZEN,
    GIVE,
    GLAD,
    GONE,
    HIT,
    HOLDER,
    HOOK,
    HOPE,
    LENS_AT,
    LENS_SCALE,
    OLD_SHY,
    PASS_FROM,
    PASS_GAP,
    PASS_LANES,
    PASS_TIME,
    PASS_TO,
    PRESSED,
    SHY,
    SNOW_ON,
    STARE,
    STRAINED,
    STRANGER,
    STRANGER_OLD,
    SWING,
)
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, stick, stick_reel
from srstudio import stick_door as sd

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "hold-the-door",
        "R10",
        "Hold the Door — Stick 10",
        "Portrait stick-figure cartoon: Dev holds a door for a stranger far too far away, for years. Native vector "
        "animation; ElevenLabs voices and effects.",
        1310,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
DUSK = ((0.0, 0.0), (1.5, 0.45), (2.6, 0.85))  # day to night through the snow
NIGHT = ((0.0, 0.85),)
DAWN = ((0.0, 0.85), (1.1, 0.45), (2.0, 0.2))  # the race goes by at first light
PALE = ((0.0, 0.2),)


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def holder(parent, keys, end: float, take=None, *, cap: int = 0, pose: str = "hold"):
    """Dev in the lobby, mirrored, holding the door; ``cap`` is the snow on him, settled for ``pose``."""
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None else {}
    g = stick.rig(cv, parent, keys, end, poses=sd.HOLD, look=DEV, at=HOLDER, flip=True, mouth=SPEECH_MOUTH,
                  blinks=(0.7,) if end > 1.0 and keys[0].face.eyes != "happy" else (), **speaks)  # fmt: skip
    if cap:
        settle(parent, cap, pose)
    return g


def settle(parent, step: int, pose: str = "hold") -> None:
    """The snow on his head and on his shoulder, wherever ``pose`` has put them."""
    head, shoulder = SNOW_ON[pose]
    sd.snow_cap(cv, parent, *head, step, width=150)
    sd.snow_cap(cv, parent, *shoulder, step, width=70)


def walker(parent, keys, end: float, look, face, *, rate: float = 6.0, lane: float = 0.0):
    """A jogger coming down the path through ``keys``."""
    return sd.jogger(cv, sd.approach(cv, parent, keys, lane=lane), end, look=look, face=face, rate=rate)


def lobby(parent, end: float, *, night=((0.0, 0.0),), clock: float = 0.0, shut=None, outside=None):
    """The set, whoever is on the path, then the door over them."""
    sd.entrance(cv, parent, end, night=night, clock=clock)
    if outside is not None:
        outside(sd.through(cv, parent))
    sd.door(cv, parent, end, shut=shut)


def on_the_glass(parent, end: float) -> None:
    """The stranger against the shut door, on the near side of its tint so the face stays the point of the shot."""
    stick.rig(cv, sd.through(cv, parent), [stick.RigKey(0, "stand", PRESSED)], end, poses=stick.STANDING,
              look=STRANGER_OLD, at=FACE_AT, scale=FACE_SCALE)  # fmt: skip


def crowd(parent, end: float, since: float) -> None:
    """The people who overtook the stranger, through the door and past the camera; ``since`` is how long ago the
    first of them set off, so they keep moving across the three takes of thanks."""
    speed = (PASS_TO - PASS_FROM) / PASS_TIME
    for k in reversed(range(len(CROWD))):
        start = k * PASS_GAP - since  # the moment this one sets off, on the shot's clock
        enter, leave = max(0.0, start), min(end, start + PASS_TIME)
        if leave <= enter:
            continue
        one = cv.group(parent, cv.uid("thanks"))
        cv.gate(one, [(enter, leave)])
        path = tuple((at, PASS_FROM + speed * (at - start)) for at in (enter, leave))
        walker(one, path, end, CROWD[k], GLAD, rate=8.0, lane=PASS_LANES[k])


def stage(take) -> None:
    """Draw ``take``'s shot."""
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "open":
        held = cv.group(g, cv.uid("held"))
        cv.gate(held, [(0, CUT_AT)])
        frame = camera(held, "open")
        far_x, far_y, far = sd.on_path(FAR)

        def waiting(m):
            stick.rig(cv, m, [stick.RigKey(0, "stand", SHY)], end, poses=stick.STANDING, look=STRANGER,
                      at=(far_x, far_y), scale=far)  # fmt: skip

        lobby(frame, end, outside=waiting)
        holder(frame, [stick.RigKey(0, "hold", BRIGHT)], end)
        lens = cv.group(g, cv.uid("lens"))
        cv.gate(lens, [(CUT_AT, end)])
        sd.street(cv, lens, end)
        sd.jogger(cv, lens, end, look=STRANGER, face=SHY, at=LENS_AT, scale=LENS_SCALE, phones=take.phones,
                  mood=take.mood, mouth=SPEECH_MOUTH)  # fmt: skip
    elif take.shot == "dev":
        frame = camera(g, "dev")
        lobby(frame, end, outside=lambda m: walker(m, ((0.0, FAR),), end, STRANGER, SHY))
        holder(frame, [stick.RigKey(0, "hold", BRIGHT)], end, take)
    elif take.shot == "more":
        frame = camera(g, "open")

        def behind(m):
            walker(m, ((0.5, 0.1), (end, 0.14)), end, CROWD[0], SHY, lane=-0.5)
            walker(m, ((0.2, 0.13), (end, 0.17)), end, CROWD[1], SHY, lane=0.6)
            walker(m, ((0.0, FAR), (end, FAR + 0.03)), end, STRANGER, SHY)

        lobby(frame, end, outside=behind)
        holder(frame, [stick.RigKey(0, "hold", FIXED), stick.RigKey(0.8, "hold", STRAINED)], end)
    elif take.shot == "crowd":
        frame = camera(g, "open")
        lobby(frame, end, outside=lambda m: walker(m, ((0.0, FAR + 0.03),), end, STRANGER, SHY))
        holder(frame, sd.shaking(0.0, end, STRAINED), end)
        crowd(frame, end, take.start - t.takes[3].start)
    elif take.shot == "time":
        frame = camera(g, "time")
        lobby(frame, end, night=DUSK, clock=1.6, outside=lambda m: sd.snow(cv, m, end, x=100, y=240, w=600, h=1260))
        holder(frame, sd.shaking(0.0, end, FROZEN, rate=8), end)
        marks = (end * 0.3, end * 0.6, end)
        for k, (a, b) in enumerate(zip(marks, marks[1:], strict=False)):
            cap = cv.group(frame, cv.uid("settled"))
            cv.gate(cap, [(a, b)])
            settle(cap, k + 1)
    elif take.shot == "race":
        frame = camera(g, "open")
        lobby(frame, end, night=DAWN, outside=lambda m: sd.marathon(cv, m, end * 0.75))
        holder(frame, sd.shaking(0.0, end, FROZEN, rate=8), end, cap=3)
    elif take.shot == "old":
        sd.street(cv, g, end, night=PALE)
        sd.jogger(cv, g, end, look=STRANGER_OLD, face=OLD_SHY, rate=3.0, at=LENS_AT, scale=LENS_SCALE,
                  phones=take.phones, mood=take.mood, mouth=SPEECH_MOUTH)  # fmt: skip
    elif take.shot == "nearly":
        frame = camera(g, "open")
        lobby(frame, end, night=PALE,
              outside=lambda m: walker(m, ((0.0, 0.55), (end, 0.8)), end, STRANGER_OLD, OLD_SHY, rate=3.0))  # fmt: skip
        drop = end - GIVE
        keys = [stick.RigKey(0, "hold-a", HOPE), *sd.shaking(0.3, drop, HOPE), stick.RigKey(drop, "sag", GONE)]
        holder(frame, keys, end)
        for name, span in (("hold", (0, drop)), ("sag", (drop, end))):
            settled = cv.group(frame, cv.uid("settled"))
            cv.gate(settled, [span])
            settle(settled, 3, name)
    elif take.shot == "shut":
        frame = camera(g, "two")
        sd.entrance(cv, frame, end, night=PALE)
        run = cv.group(frame, cv.uid("still-running"))
        cv.gate(run, [(0, HIT)])
        walker(sd.through(cv, run), ((0.0, 0.82), (HIT, 0.9)), end, STRANGER_OLD, OLD_SHY, rate=3.0)
        sd.door(cv, frame, end, shut=SWING)
        hit = cv.group(frame, cv.uid("on-the-glass"))
        cv.gate(hit, [(HIT, end)])
        on_the_glass(hit, end)
        holder(frame, [stick.RigKey(0, "drop", GONE), stick.RigKey(HIT + 0.5, "drop", STARE)], end, cap=3, pose="drop")
    else:  # end
        frame = camera(g, "end")
        sd.entrance(cv, frame, end, night=PALE)
        sd.door(cv, frame, end, closed=True)
        on_the_glass(frame, end)
        holder(frame, [stick.RigKey(0, "drop", STARE)], end, take, cap=3, pose="drop")


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, t.takes[2].start)])
spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({"11": SWING}))
stick_reel.close(ep, POSTS["hold-the-door"], hook, spoken)

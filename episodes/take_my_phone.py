#!/usr/bin/env python3
"""Stick 11 — Take My Phone, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 take_my_phone_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build take-my-phone PROJECT                                      # → PROJECT/take-my-phone.scene.xml

She hands her friend her phone: whatever she says, do not let her text him. Twenty seconds later she wants it back.
The friend runs, sits on it, freezes it, locks it up and swallows the key, and she has already lifted the friend's
own phone. The set is ``stick_home``; the figures are ``stick.rig``.
"""

import math
import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, stick, stick_reel
from srstudio import stick_home as sh
from srstudio.stick_shop import hand
from take_my_phone_audio import (
    BLANK,
    CALM,
    CAMERAS,
    CUT_AT,
    DONE,
    FIRM,
    FRANTIC,
    FRIEND,
    FRIEND_PHONE,
    GRAVE,
    GRIM,
    HER,
    HER_PHONE,
    HOOK,
    JOY,
    LAP,
    LOST,
    ORBIT,
    SMUG,
    SOLEMN,
    SWEET,
    TILTED,
)

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "take-my-phone",
        "R11",
        "Take My Phone — Stick 11",
        "Portrait stick-figure cartoon: a friend is told not to let her text him, and tries. Native vector animation; "
        "ElevenLabs voices and effects.",
        1311,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
POCKET = (sh.RIGHT_AT[0] - 590, 1180.0)  # the friend's own phone, in her pocket until it is not


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def her(parent, keys, end: float, take=None, *, at=sh.LEFT_AT):
    speaks = dict(phones=take.phones, mood=take.mood, mouth=SPEECH_MOUTH) if take is not None else {}
    return stick.rig(cv, parent, keys, end, poses=sh.POSES, look=HER, at=at, **speaks)


def friend(parent, keys, end: float, take=None, *, at=sh.RIGHT_AT, flip=True):
    speaks = dict(phones=take.phones, mood=take.mood, mouth=SPEECH_MOUTH) if take is not None else {}
    return stick.rig(cv, parent, keys, end, poses=sh.POSES, look=FRIEND, at=at, flip=flip, **speaks)


def set_at(parent) -> None:
    sh.kitchen(cv, parent)
    sh.table(cv, parent)


def orbit(parent, end: float, *, hair: str, phone=None, ahead: float = 0.0):
    """A figure from above, running clockwise round the table for the shot; ``ahead`` is degrees up the track."""
    keys = []
    for k in range(int(end / LAP * 12) + 2):
        at = k * LAP / 12
        a = math.radians(k * 30 + ahead)
        x, y = ORBIT[0] + ORBIT[2] * math.sin(a), ORBIT[1] - ORBIT[3] * math.cos(a)
        heading = math.degrees(math.atan2(ORBIT[2] * math.cos(a), ORBIT[3] * math.sin(a))) % 360
        heading += 360 * ((k * 30 + ahead) // 360)
        keys.append((round(at, 4), round(x, 2), round(y, 2), round(heading, 2)))
    g = stick._group(cv, parent, x=keys[0][1], y=keys[0][2], rotation=keys[0][3])
    for i, prop in ((1, "x"), (2, "y"), (3, "rotation")):
        cv.keys(g, prop, [(key[0], key[i]) for key in keys], hold=False)
    sh.from_above(cv, g, end, hair=hair, phone=phone)
    return g


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "two":
        frame = camera(g, "two")
        sh.kitchen(cv, frame)
        her(frame, [stick.RigKey(0, "offer", GRAVE)], end, take)
        friend(frame, [stick.RigKey(0, "stand", SOLEMN)], end)
        x, y = hand(sh.POSES["offer"], at=sh.LEFT_AT)
        sh.handset(cv, frame, x + 14, y - 10, colour=HER_PHONE)
        sh.handset(cv, frame, *POCKET, colour=FRIEND_PHONE, scale=0.7)
        sh.table(cv, frame)
    elif take.shot == "later":
        frame = camera(g, "her")
        sh.kitchen(cv, frame)
        friend(frame, [stick.RigKey(0, "keep", FIRM)], end)
        her(frame, [stick.RigKey(0, "plead", SWEET)], end, take)
        sh.table(cv, frame)
        stick.card(cv, g, "20 seconds later", size=50)
    elif take.shot == "friend":
        frame = camera(g, "friend")
        sh.kitchen(cv, frame)
        her(frame, [stick.RigKey(0, "plead", SWEET)], end)
        friend(frame, [stick.RigKey(0, "keep", FIRM)], end, take)
        x, y = hand(sh.POSES["keep"], at=sh.RIGHT_AT, flip=True)
        sh.handset(cv, frame, x, y, colour=HER_PHONE)
        sh.table(cv, frame)
    elif take.shot == "chase":
        sh.plan(cv, g)
        orbit(g, end, hair="bun", phone=HER_PHONE, ahead=75.0)
        orbit(g, end, hair="side-part")
    elif take.shot == "sit":
        frame = camera(g, "two")
        sh.kitchen(cv, frame)
        her(frame, [stick.RigKey(0, "offer", FRANTIC)], end)
        sh.table(cv, frame)
        friend(frame, [stick.RigKey(0, "perch", SMUG)], end, at=(1200.0, 0.0))
    elif take.shot == "fridge":
        frame = camera(g, "fridge")
        set_at(frame)
        slam = 0.42
        opened = cv.group(frame, cv.uid("open"))
        cv.gate(opened, [(0, slam)])
        sh.fridge_open(cv, opened)
        friend(frame, [stick.RigKey(0, "push", GRIM)], end, at=(160.0, 0.0), flip=False)
        x, y = hand(sh.POSES["push"], at=(160.0, 0.0))
        held = cv.group(frame, cv.uid("phone"))
        cv.gate(held, [(0, slam)])
        sh.handset(cv, held, x, y, colour=HER_PHONE)
    elif take.shot == "safe":
        frame = camera(g, "safe")
        set_at(frame)
        slam = 0.46
        opened = cv.group(frame, cv.uid("open"))
        cv.gate(opened, [(0, slam)])
        sh.safe_open(cv, opened)
        sh.handset(cv, opened, 215, 512, colour=HER_PHONE)
        friend(frame, [stick.RigKey(0, "reach-up", GRIM)], end, at=(1120.0, 0.0))
    elif take.shot == "gulp":
        close = cv.group(g, cv.uid("gulp"))
        cv.gate(close, [(0, CUT_AT)])
        frame = camera(close, "friend")
        set_at(frame)
        friend(frame, [stick.RigKey(0, "swallow", TILTED)], end)
        x, y = hand(sh.POSES["swallow"], at=sh.RIGHT_AT, flip=True)
        held = cv.group(frame, cv.uid("key"))
        cv.gate(held, [(0, 0.3)])
        sh.key(cv, held, x + 30, y - 10, scale=1.1)
        lump = stick._group(cv, frame, x=820.0, y=850.0)
        stick.oval(cv, lump, -9, -9, 18, 18, cv.ink)
        cv.keys(lump, "y", [(0.3, 850.0), (CUT_AT, 1090.0)], hold=False)
        cv.gate(lump, [(0.3, CUT_AT)])
        stare = cv.group(g, cv.uid("stare"))
        cv.gate(stare, [(CUT_AT, end)])
        frame = camera(stare, "stare")
        sh.kitchen(cv, frame)
        her(frame, [stick.RigKey(0, "stand", BLANK)], end)
        friend(frame, [stick.RigKey(0, "stand", BLANK)], end)
        sh.table(cv, frame)
    elif take.shot == "calm":
        frame = camera(g, "two")
        sh.kitchen(cv, frame)
        beat = 0.11
        count = int(end / beat)
        keys = [stick.RigKey(round(i * beat, 4), "type-a" if i % 2 else "type-b", CALM) for i in range(count)]
        her(frame, [stick.RigKey(0, "raise", CALM), *keys[4:]], end)
        x, y = hand(sh.POSES["raise"], at=sh.LEFT_AT)
        sh.handset(cv, frame, x, y - 40, colour=FRIEND_PHONE, lit=True)
        pats = [stick.RigKey(round(i * 0.24, 4), "pat-b" if i % 2 else "pat-a", LOST) for i in range(int(end / 0.24))]
        friend(frame, [stick.RigKey(0, "stand", BLANK), *pats[1:]], end)
        sh.table(cv, frame)
    elif take.shot == "reply":
        sh.reply(cv, g, name="Him", sent="just saying happy birthday", answer="who is this")
    else:  # win
        cheer = cv.group(g, cv.uid("cheer"))
        turn = take.words[-1]["end"] + 0.25 if take.words else end - 1.0
        cv.gate(cheer, [(0, turn)])
        frame = camera(cheer, "two")
        sh.kitchen(cv, frame)
        her(frame, [stick.RigKey(0, "cheer", JOY)], end, take)
        x, y = hand(sh.POSES["cheer"], at=sh.LEFT_AT)
        sh.handset(cv, frame, x, y - 30, colour=FRIEND_PHONE, lit=True)
        friend(frame, [stick.RigKey(0, "stand", DONE)], end)
        sh.table(cv, frame)
        last = cv.group(g, cv.uid("friend"))
        cv.gate(last, [(turn, end)])
        frame = camera(last, "friend")
        set_at(frame)
        friend(frame, [stick.RigKey(0, "stand", DONE)], end)


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, t.takes[1].start)])
spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({}))
stick_reel.close(ep, POSTS["take-my-phone"], hook, spoken)

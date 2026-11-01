#!/usr/bin/env python3
"""Stick — Consulting, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 consulting_audio.py PROJECT --font DIR   # voices, timeline.json
    srstudio build consulting PROJECT                                      # → PROJECT/consulting.scene.xml

Noor interviews Dev over a two-year gap. The set is ``stick_interview``: the page at her elbow lies face down from the
first frame and the bottom drawer is in frame and shut until the turn. The effects are ``foley`` bursts.
"""

import os

from _common import project_root
from consulting_audio import (
    ARM_FROM,
    CAMERAS,
    DEV_BRIGHT,
    DEV_DOOR,
    DEV_DOWN,
    DEV_HONEST,
    DEV_LOOK,
    DEV_PROUD,
    DEV_VET,
    DRAWER_AT,
    FACES,
    HERS_AT,
    HOOK,
    INSERT_AFTER,
    MARKS,
    NOOR_BLANK,
    NOOR_KNOWS,
    NOOR_LOOK,
    NOOR_PAGE,
    NOOR_RAISED,
    NOOR_SEES,
    NOOR_VET,
    RESUME_AT,
    SHAKES,
    TICK_GAP,
    TURN_AT,
)
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, foley, stick, stick_reel
from srstudio import stick_interview as si

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "consulting",
        "205",
        "Consulting — Stick",
        "Portrait stick-figure cartoon: Noor asks Dev about the gap on his resume, and the page at her elbow and her "
        "bottom drawer answer. Native vector animation; ElevenLabs voices.",
        3313,
        bleed=True,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
said = {x.id: x for x in t.takes}


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def speaks(take, who: str) -> dict:
    return dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}


def scene(parent, end, dev, noor, *, take=None, opens=None, is_open=False, turned=None, up=False, blink=()):
    """The room, the two pages, the two of them, and the desk over their knees. ``turned``: when her page goes over;
    ``up``: it is already over."""
    si.room(cv, parent, end)
    si.page(cv, parent, *RESUME_AT)
    if turned is not None:
        down = cv.group(parent, cv.uid("page-down"))
        cv.gate(down, [(0, turned)])
        si.page(cv, down, *HERS_AT, face_down=True)
        over = cv.group(parent, cv.uid("page-up"))
        cv.gate(over, [(turned, end)])
        si.page(cv, over, *HERS_AT, ringed=True)
    else:
        si.page(cv, parent, *HERS_AT, face_down=not up, ringed=up)
    stick.rig(cv, parent, dev, end, poses=si.POSES, look=DEV_LOOK, at=si.LEFT_AT, mouth=SPEECH_MOUTH, blinks=blink,
              **speaks(take, "dev"))  # fmt: skip
    stick.rig(cv, parent, noor, end, poses=si.POSES, look=NOOR_LOOK, at=si.RIGHT_AT, flip=True, mouth=SPEECH_MOUTH,
              **speaks(take, "noor"))  # fmt: skip
    si.desk(cv, parent, end, opens=opens, is_open=is_open)


def k(start: float, pose: str, face) -> stick.RigKey:
    return stick.RigKey(start, pose, face)


def stage(take) -> None:
    """Draw ``take``'s shot."""
    g = ep.shot(shots, take)
    end, line = take.duration, take.speech_duration
    if take.shot == "two":
        scene(camera(g, "two"), end, [k(0, "rest", DEV_BRIGHT)], [k(0, "finger", NOOR_PAGE)], take=take)
    elif take.shot == "dev":
        pose, face = {
            "02": ("rest", DEV_BRIGHT),
            "04": ("explain", DEV_BRIGHT),
            "06": ("rest", DEV_PROUD),
            "08": ("explain", DEV_HONEST),
        }[take.id]
        scene(camera(g, "dev"), end, [k(0, pose, face)], [k(0, "finger", NOOR_PAGE)], take=take)
    elif take.shot == "noor":
        face = {"03": NOOR_BLANK, "05": NOOR_RAISED, "07": NOOR_RAISED, "09": NOOR_BLANK}[take.id]
        scene(camera(g, "noor"), end, [k(0, "rest", DEV_BRIGHT)], [k(0, "rest", face)], take=take)
    elif take.shot == "stare":
        frame = camera(g, "two")
        turn = line + TURN_AT
        scene(frame, end, [k(0, "rest", DEV_HONEST), k(line + 0.5, "rest", DEV_DOOR)],
              [k(0, "rest", NOOR_BLANK), k(line + 0.3, "rest", NOOR_SEES), k(turn - 0.3, "page", NOOR_SEES)], take=take,
              turned=turn)  # fmt: skip
    elif take.shot == "page":
        cut = line + INSERT_AFTER
        insert = cv.group(g, cv.uid("insert"))
        cv.gate(insert, [(0, cut)])
        si.resume_insert(cv, insert, end)
        close = cv.group(g, cv.uid("close"))
        cv.gate(close, [(cut, end)])
        frame = camera(close, "drawer")
        opens = cut + DRAWER_AT
        scene(frame, end, [k(0, "rest", DEV_DOOR)], [k(0, "down", NOOR_KNOWS)], opens=opens, up=True)
        for step in range(si.DRAWER_STEPS + 1):
            arm = cv.group(frame, cv.uid("arm"))
            at = opens + (step - 1) * si.DRAWER_STEP if step else 0.0
            until = opens + step * si.DRAWER_STEP if step < si.DRAWER_STEPS else end
            cv.gate(arm, [(at, until)])
            hx, hy = si.drawer_handle(step / si.DRAWER_STEPS)
            d = f"M {ARM_FROM[0]} {ARM_FROM[1]} L {hx + 150} {hy - 60} L {hx + 24} {hy}"
            stick.shape(cv, arm, d, sw=10, stroke=cv.ink)
    elif take.shot == "open":
        scene(camera(g, "two"), end, [k(0, "rest", DEV_DOWN), k(line + 0.5, "rest", DEV_VET)],
              [k(0, "rest", NOOR_KNOWS)], take=take, is_open=True, up=True)  # fmt: skip
    else:  # shake
        reach, up, down, up2, down2 = (line + s for s in SHAKES)
        keys = [(0, "rest"), (reach, "reach"), (up, "shake-up"), (down, "shake-down"), (up2, "shake-up"),
                (down2, "shake-down")]  # fmt: skip
        scene(camera(g, "two"), end, [k(s, p, DEV_VET) for s, p in keys], [k(s, p, NOOR_VET) for s, p in keys],
              take=take, is_open=True, up=True)  # fmt: skip


def sound() -> list:
    """A wall clock through the room's holds; the page going over; the drawer's run and stop; the slow clasp."""
    stare, page, shake = said["10"], said["11"], said["13"]
    run = ROOT / "audio"
    tick = foley.Burst(0.05, 3000.0, attack=0.002, decay=0.25, tone_hz=1500.0, tone_end_hz=1300.0, tone=0.25)
    holds = [(stare.start + stare.speech_duration, stare.end), (shake.start, t.duration)]
    ticks = [a + i * TICK_GAP for a, b in holds for i in range(1 + int((b - a) / TICK_GAP))]
    foley.write_bursts(run / "tick.wav", ticks, t.duration, tick)
    turn = stare.start + stare.speech_duration + TURN_AT
    foley.write_bursts(run / "page.wav", [turn - 0.1], t.duration, foley.SWISH)
    opens = page.start + page.speech_duration + INSERT_AFTER + DRAWER_AT
    foley.write_bursts(run / "slide.wav", [opens + i * 0.06 for i in range(5)], t.duration, foley.SCRAPE, seed=5)
    foley.write_bursts(run / "stop.wav", [opens + 0.33], t.duration, foley.KNOCK)
    clasp = shake.start + shake.speech_duration + SHAKES[1]
    foley.write_bursts(run / "clasp.wav", [clasp], t.duration, foley.KNOCK)
    return [
        ("tick", "audio/tick.wav", {"role": "effects", "gain": -15}),
        ("page", "audio/page.wav", {"role": "effects", "gain": -12}),
        ("slide", "audio/slide.wav", {"role": "effects", "gain": -7}),
        ("stop", "audio/stop.wav", {"role": "effects", "gain": -6}),
        ("clasp", "audio/clasp.wav", {"role": "effects", "gain": -10}),
    ]


for take in t.takes:
    stage(take)

for shot, faces in (("two", tuple(FACES.values())), ("dev", (FACES["dev"],)), ("noor", (FACES["noor"],))):
    stick_reel.check_framing(CAMERAS[shot], faces=faces, marks=MARKS.values())
hook = stick.card(cv, cv.comp, HOOK, size=58, width=stick_reel.CARD_CLEAR)
cv.gate(hook, [(0, min(3.0, t.takes[2].start))])
spoken = stick_reel.words(ep, t.takes, sentences=True)
ep.audio(take=stick_reel.placing({}), loudness="-14", extra=sound())
stick_reel.close(ep, POSTS["consulting"], hook, spoken)

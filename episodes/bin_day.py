#!/usr/bin/env python3
"""Stick 23 — Trash Day, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 bin_day_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build bin-day PROJECT                                      # → PROJECT/bin-day.scene.xml

Dev hears the truck from bed and runs for it in a robe, losing a slipper and a wheel, while two neighbors call it
from their window like a race. The street is ``stick_street``; the robe, the bin, the truck and the sparks are
``stick_odds``.
"""

import os

from _common import project_root
from bin_day_audio import (
    AT_DRIVER,
    BLANK,
    DEV,
    DRIVER,
    DRIVER_FACE,
    FLAT_OUT,
    HOOK,
    JOY,
    LANDED,
    MARGARET,
    PANIC,
    POSES,
    ROBE,
    ROBE_BELT,
    SIPPING,
    SUNK,
    TALKING,
    WALT,
    WATCHING,
)
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, stick, stick_odds, stick_office, stick_reel, stick_street

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "bin-day",
        "R23",
        "Trash Day — Stick 23",
        "Portrait stick-figure cartoon: a man in a robe chases the trash truck while two neighbors call it from their "
        "window like a horse race. Native vector animation; ElevenLabs voices and effects.",
        3123,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
K = stick.RigKey
FLOOR = 1700.0
ROAD = 1530.0  # Dev's feet in the road
RATE = 6.0  # strides a second
WX, WY, WW, WH = stick_street.HOUSE_WINDOW
ZOOM = 2.6
WINDOW_AT = (WX + WW / 2, WY + WH / 2)


def figure(parent, keys, end: float, look, x: float, take=None, *, who: str = "", flip: bool = False,
           scale: float = 1.0, floor: float = ROAD):  # fmt: skip
    """A figure with its pose's middle at ``x`` and its feet on ``floor``."""
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}
    at = (x + 540 * scale if flip else x - 540 * scale, floor - FLOOR * scale)
    return stick.rig(cv, parent, keys, end, poses=POSES, look=look, at=at, scale=scale, flip=flip, mouth=SPEECH_MOUTH,
                     **speaks)  # fmt: skip


def robed(parent, keys, end: float, x: float, *, scale: float = 1.0, floor: float = ROAD) -> None:
    """Dev in his robe."""
    figure(parent, keys, end, DEV, x, scale=scale, floor=floor)
    stick_odds.robe(cv, parent, keys, end, POSES, at=(x - 540 * scale, floor - FLOOR * scale), scale=scale,
                    colour=ROBE, belt=ROBE_BELT)  # fmt: skip


def strides(end: float, face) -> list[stick.RigKey]:
    return [K(round(i / RATE, 4), "run-b" if i % 2 else "run-a", face) for i in range(max(1, int(end * RATE)))]


def sliding(parent, frm: float, to: float, end: float):
    g = cv.group(parent, cv.uid("runner"))
    cv.keys(g, "x", [(0.0, frm), (end, to)], kind="linear")
    return g


def mugs(parent, keys, end: float, x: float, floor: float, scale: float) -> None:
    """A mug in the near hand of a figure at ``x``, wherever each of its keys puts that hand."""
    for i, key in enumerate(keys):
        hand = POSES[key.pose].hands[1]
        at = cv.group(parent, cv.uid("mug"), x=x + (hand[0] - 540) * scale, y=floor - (FLOOR - hand[1]) * scale,
                      scaleX=scale, scaleY=scale)  # fmt: skip
        stick_office.mug(cv, at, 0, 0)
        cv.gate(at, [(key.start, keys[i + 1].start if i + 1 < len(keys) else end)])


def neighbors(parent, take, end: float, *, scale: float, walt_keys, margaret_keys) -> None:
    """The two of them in the window, each with a mug, drawn in the house."""
    room = stick_street.in_window(cv, parent)
    floor = WY + 110 + (FLOOR - 750) * scale
    pair = ((WX + WW * 0.27, walt_keys, WALT, "walt"), (WX + WW * 0.72, margaret_keys, MARGARET, "margaret"))
    for x, keys, look, who in pair:
        figure(room, keys, end, look, x, take, who=who, scale=scale, floor=floor)
        mugs(room, keys, end, x, floor, scale)
    stick_street.window_frame(cv, parent)


def window_shot(parent, take, end: float, *, sipping: bool) -> None:
    frame = stick.camera(cv, parent, WINDOW_AT, zoom=ZOOM, to=(540, 1010))
    stick_street.street(cv, frame)
    walt = TALKING if take.actor == "walt" else WATCHING
    margaret = [K(0, "hold-mug", WATCHING)]
    if sipping and take.actor == "walt":
        margaret = [K(0, "hold-mug", WATCHING), K(0.1, "sip", SIPPING)]
    neighbors(frame, take, end, scale=0.42, walt_keys=[K(0, "hold-mug", walt)], margaret_keys=margaret)


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "door":
        stick_street.street(cv, g)
        stick.box(cv, g, 500, 800, 110, 340, "#23252b")  # the door stands open on the dark hall
        neighbors(g, None, end, scale=0.2, walt_keys=[K(0, "hold-mug", WATCHING)],
                  margaret_keys=[K(0, "hold-mug", WATCHING)])  # fmt: skip
        here = cv.group(g, cv.uid("runner"))
        if take.is_effect:
            cv.keys(here, "x", [(0.0, -300.0), (end, -420.0)], kind="linear")
            cv.keys(here, "y", [(0.0, 300.0), (end, 330.0)], kind="linear")
        else:
            cv.keys(here, "x", [(0.0, 0.0), (end, -300.0)], kind="linear")
            cv.keys(here, "y", [(0.0, 150.0), (end, 300.0)], kind="linear")
        stick_odds.wheelie_bin(cv, here, 390.0, 1190.0, lean=24, scale=0.75)
        robed(here, strides(end, PANIC), end, 560.0, scale=0.72, floor=1190.0)
    elif take.shot == "window":
        window_shot(g, take, end, sipping=False)
    elif take.shot == "run":
        stick_street.street(cv, g)
        starts = (100.0, 480.0) if take.actor == "walt" else (480.0, 620.0) if take.is_effect else (620.0, 980.0)
        here = sliding(g, *starts, end)
        stick_odds.wheelie_bin(cv, here, -230.0, ROAD, lean=30, scale=0.9)
        robed(here, strides(end, FLAT_OUT), end, 0.0, scale=0.9)
        if take.actor == "walt":
            shoe = stick_odds.slipper(cv, g, 330.0, ROAD - 40)
            cv.keys(shoe, "y", [(0.0, ROAD - 40), (end * 0.5, ROAD - 420), (end, ROAD + 20)], kind="linear")
            cv.keys(shoe, "x", [(0.0, 330.0), (end, 140.0)], kind="linear")
            cv.keys(shoe, "rotation", [(0.0, 0.0), (end, -420.0)], kind="linear")
    elif take.shot == "chase":
        stick_street.street(cv, g)
        cab = sliding(g, 560.0, 900.0, end)
        stick_odds.trash_truck(cv, cab, 0.0, ROAD - 10, scale=0.8)
        here = sliding(g, 270.0, 520.0, end)
        stick_odds.wheelie_bin(cv, here, -210.0, ROAD, wheels=1, lean=62, scale=0.9)
        stick_odds.sparks(cv, here, -270.0, ROAD - 10, end, scale=1.7)
        robed(here, strides(end, FLAT_OUT), end, 0.0, scale=0.8)
        wheel = cv.group(g, cv.uid("wheel"))
        stick.oval(cv, wheel, 0, ROAD - 58, 58, 58, "#23252b")
        cv.keys(wheel, "x", [(0.0, 40.0), (end, 560.0)], kind="linear")
    elif take.shot == "dive":
        stick_street.street(cv, g)
        stick_odds.trash_truck(cv, g, 640.0, ROAD - 10, scale=0.8)
        crash = min(0.9, end * 0.7)
        bin_ = cv.group(g, cv.uid("bin"))
        cv.keys(bin_, "x", [(0.0, 120.0), (crash, 540.0), (end, 500.0)], kind="linear")
        stick_odds.wheelie_bin(cv, bin_, 0.0, ROAD, wheels=1, lean=8, scale=0.9)
        here = sliding(g, -320.0, -60.0, end)
        pose = POSES["dive"]
        lying = cv.group(here, cv.uid("lying"), x=135.0, y=ROAD - FLOOR * 0.75, scaleX=0.75, scaleY=0.75)
        path = f"M {pose.neck[0]} {pose.neck[1]} L {pose.hip[0]} {pose.hip[1]}"
        stick.shape(cv, lying, path, sw=110, stroke=ROBE)  # a robe flat out in the air is a thick line
        figure(here, [K(0, "dive", FLAT_OUT)], end, DEV, 540.0, scale=0.75)
    elif take.shot == "arms":
        stick_street.street(cv, g)
        robed(g, [K(0, "arms-up", JOY)], end, 540.0, scale=1.3, floor=1960.0)
    elif take.shot == "driver":
        stick_street.street(cv, g)
        stick_odds.trash_truck(cv, g, -930.0, 1560.0, scale=1.9)
        cab = cv.group(g, cv.uid("cab"))
        cab.add_mask(type="path", path="M 560 700 L 900 700 L 900 1055 L 560 1055 Z")
        figure(cab, [K(0, "lean-out", DRIVER_FACE)], end, DRIVER, 760.0, take, who="driver", flip=True, scale=0.95,
               floor=1720.0)  # fmt: skip
        stick_odds.wheelie_bin(cv, g, 620.0, ROAD + 60, wheels=1, scale=0.9)
        if take.is_effect:
            dev_keys = [K(0, "arms-up", AT_DRIVER)]
        else:
            turn = stick_odds.double_take(take.speech_duration + 0.2, "arms-up", LANDED, BLANK, LANDED)
            dev_keys = [K(0, "arms-up", AT_DRIVER), *turn]
        robed(g, dev_keys, end, 240.0, scale=0.8, floor=ROAD + 60)
    elif take.shot == "road":
        stick_street.street(cv, g)
        cab = sliding(g, 760.0, 1500.0, end)
        stick_odds.trash_truck(cv, cab, 0.0, ROAD - 10, scale=0.6)
        keys = [K(0, "arms-up", SUNK), K(end * 0.45, "arms-mid", SUNK), K(end * 0.8, "arms-low", SUNK)]
        robed(g, keys, end, 400.0, scale=0.45)
        stick_odds.wheelie_bin(cv, g, 230.0, ROAD, wheels=1, scale=0.45)
    else:  # sip
        window_shot(g, take, end, sipping=True)


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=78)
cv.gate(hook, [(0, t.takes[3].start)])
spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({}), loudness="-14")
stick_reel.close(ep, POSTS["bin-day"], hook, spoken)

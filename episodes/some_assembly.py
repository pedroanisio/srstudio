#!/usr/bin/env python3
"""Stick 24 — Some Assembly, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 some_assembly_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build some-assembly PROJECT                                      # → PROJECT/some-assembly.scene.xml

Noor and Dev build a wardrobe from a manual that has read them: it knows the argument, it knows the sofa, and its last
page has a bun on it. The flat is ``stick_flat``; the wardrobe, the pile, the drill, the screws, the pages and the
ringing phone are ``stick_odds``.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from some_assembly_audio import (
    AT_BUN,
    AT_MANUAL,
    AT_PHONE,
    CLOSELY,
    FINE,
    FLAT_AT_HIM,
    HOOK,
    LOOKS_UP,
    POSES,
    PROUD,
    READ,
    READING,
    READS_ON,
    STARE,
    STILL,
    SURE,
    TOLD,
    UNEASY,
    WORK,
)
from srstudio import SPEECH_MOUTH, Episode, stick, stick_flat, stick_odds, stick_reel, stick_windshield

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "some-assembly",
        "R24",
        "Some Assembly — Stick 24",
        "Portrait stick-figure cartoon: a couple build a flat-pack wardrobe from a manual whose steps know exactly how "
        "the evening will go. Native vector animation; ElevenLabs voices and effects.",
        3124,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
K = stick.RigKey
NOOR, DEV = stick_windshield.COUPLE["noor"], stick_windshield.COUPLE["dev"]
FOOT = 1700.0
ROOM_FLOOR = 1590.0  # where a figure stands in the flat
SEAT_X = 270.0  # Noor on the floor: her pose's x 540 lands here
DEV_X = 610.0
NOOR_X, DEV_END_X = 300.0, 490.0  # arm in arm by the finished wardrobe
WARDROBE_X, WARDROBE_FOOT = 648.0, 1510.0
MANUAL = "#f4f1ea"
ZOOM = 1.9


def figure(parent, keys, end: float, look, x: float, take=None, *, who: str = "", flip: bool = False,
           scale: float = 0.85, floor: float = ROOM_FLOOR):  # fmt: skip
    """A figure with its pose's x 540 at ``x`` and its feet on ``floor``."""
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}
    at = (x + 540 * scale if flip else x - 540 * scale, floor - FOOT * scale)
    return stick.rig(cv, parent, keys, end, poses=POSES, look=look, at=at, scale=scale, flip=flip, mouth=SPEECH_MOUTH,
                     **speaks)  # fmt: skip


def on_floor(parent, face, end: float, take=None, *, pose: str = "read") -> None:
    """Noor on the floor with the manual on her knees."""
    figure(parent, [K(0, pose, face)], end, NOOR, SEAT_X, take, who="noor", floor=1600.0)
    hand = POSES[pose].hands[1]
    stick_odds.book(cv, parent, SEAT_X + (hand[0] - 540) * 0.85, 1600.0 - (FOOT - hand[1]) * 0.85 - 30,
                    scale=1.15, colour=MANUAL)  # fmt: skip


def page(parent, step: int, drawing: str, *, bubble: str = "", at: tuple[float, float] | None = None, end: float = 0):
    """A manual page, for the whole shot or for the window ``at`` of it."""
    g = cv.group(parent, cv.uid("page"))
    stick_odds.manual_page(cv, g, step, drawing, bubble=bubble)
    if at is not None:
        cv.gate(g, [(at[0], min(at[1], end))])
    return g


def wide(
    parent, end: float, stage: str | None, *, noor_face, dev_keys, take=None, phase: tuple[float, float] | None = None
):
    """The flat from the door: the pile or the wardrobe on the right, Noor on the floor, Dev standing."""
    g = cv.group(parent, cv.uid("wide"))
    stick_flat.studio(cv, g)
    if stage is None:
        stick_odds.planks(cv, g, 640.0, WARDROBE_FOOT + 30)
    else:
        stick_odds.wardrobe(cv, g, WARDROBE_X, WARDROBE_FOOT, stage)
    on_floor(g, noor_face, end, take)
    figure(g, dev_keys, end, DEV, DEV_X, take, who="dev")
    if phase is not None:
        cv.gate(g, [phase])
    return g


def noor_close(parent, take, end: float, face) -> None:
    """Noor on the floor, close, with the manual."""
    g = stick.camera(cv, parent, (210.0, 1170.0), zoom=ZOOM, to=(390, 800))
    stick_flat.studio(cv, g)
    on_floor(g, face, end, take)


def finished(parent, end: float, take=None, *, noor_face=PROUD, dev_face=UNEASY):
    """The wardrobe standing and the two of them arm in arm, four screws in Dev's hand and the manual in hers."""
    room = cv.group(parent, cv.uid("room"))
    stick_flat.studio(cv, room)
    stick_odds.wardrobe(cv, room, WARDROBE_X, WARDROBE_FOOT, "done")
    figure(room, [K(0, "arm-in-arm", noor_face)], end, NOOR, NOOR_X, take, who="noor")
    hand = POSES["arm-in-arm"].hands[1]
    stick_odds.book(cv, room, NOOR_X + (hand[0] - 540) * 0.85, ROOM_FLOOR - (FOOT - hand[1]) * 0.85, scale=0.9,
                    colour=MANUAL)  # fmt: skip
    figure(room, [K(0, "offer", dev_face)], end, DEV, DEV_END_X, take, who="dev")
    palm = POSES["offer"].hands[1]
    stick_odds.screws(cv, room, DEV_END_X + (palm[0] - 540) * 0.85 - 40, ROOM_FLOOR - (FOOT - palm[1]) * 0.85 - 40,
                      scale=1.3)  # fmt: skip
    return room


def dev_close(parent, take, end: float, phase: tuple[float, float]) -> None:
    """Dev by the wardrobe, close: he reads the page, then he looks up."""
    g = stick.camera(cv, parent, (DEV_END_X, 900.0), zoom=ZOOM, to=(540, 900))
    stick_flat.studio(cv, g)
    stick_odds.wardrobe(cv, g, WARDROBE_X, WARDROBE_FOOT, "done")
    figure(g, [K(0, "stand", READS_ON), K(0.5, "stand", AT_BUN)], end, DEV, DEV_END_X, take, who="dev")
    cv.gate(g, [phase])


def noor_reading(parent, end: float, face, phase: tuple[float, float]) -> None:
    """Noor on her feet, close, with the manual up in front of her: where the reel ends."""
    g = stick.camera(cv, parent, (NOOR_X, 960.0), zoom=ZOOM, to=(470, 900))
    stick_flat.studio(cv, g)
    figure(g, [K(0, "hold-up", face)], end, NOOR, NOOR_X)
    hand = POSES["hold-up"].hands[1]
    stick_odds.book(cv, g, NOOR_X + (hand[0] - 540) * 0.85, ROOM_FLOOR - (FOOT - hand[1]) * 0.85, scale=0.9,
                    colour=MANUAL)  # fmt: skip
    cv.gate(g, [phase])


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "open":
        if take.id == "01":
            step_in = STILL + 0.95
            wide(g, end, None, noor_face=READING, dev_keys=[K(0, "stand", SURE)], take=take, phase=(0, step_in))
            page(g, 1, "smiling", at=(step_in, end), end=end)
        else:
            wide(g, end, None, noor_face=READING, dev_keys=[K(0, "stand", SURE)], take=take)
    elif take.shot == "half":
        if take.is_effect:
            keys = [K(0, "work", WORK)]
        elif take.actor == "dev":
            keys = [K(0, "work", TOLD)]
        else:
            keys = [K(0, "stand", TOLD)]
        wide(g, end, "half", noor_face=LOOKS_UP if take.actor == "noor" else READING, dev_keys=keys, take=take)
        if keys[0].pose == "work":
            hand = POSES["work"].hands[1]
            stick_odds.drill(cv, g, DEV_X + (hand[0] - 540) * 0.85, ROOM_FLOOR - (FOOT - hand[1]) * 0.85)
    elif take.shot == "nine":
        said = take.speech_duration + 0.1
        wide(g, end, "half", noor_face=READING, dev_keys=[K(0, "stand", TOLD)], take=take, phase=(0, said))
        page(g, 9, "argument", bubble="YOU SAID YOU MEASURED", at=(said, said + READ), end=end)
        wide(g, end, "half", noor_face=STARE, dev_keys=[K(0, "stand", STARE)], phase=(said + READ, end))
    elif take.shot == "ten":
        if take.is_effect:
            page(g, 10, "crossed")
        elif take.actor == "dev":
            wide(g, end, "half", noor_face=READING, dev_keys=[K(0, "crossed", FINE)], take=take)
        else:
            wide(g, end, "half", noor_face=FLAT_AT_HIM, dev_keys=[K(0, "crossed", FINE)], take=take)
    elif take.shot == "fourteen":
        page(g, 14, "sofa")
    elif take.shot == "twenty-two":
        page(g, 22, "suitcase")
    elif take.shot == "mom":
        noor_close(g, take, end, AT_PHONE if take.is_effect else READING)
        ring = (0.0, 0.5, 1.0) if take.is_effect else ()
        stick_odds.caller(cv, g, 850.0, 1330.0, "MOM", ring=ring, scale=1.3)
    elif take.shot == "later":
        finished(g, end, take)
        if take.actor == "noor":
            page(g, 40, "hug", at=(0.45, end), end=end)
    elif take.shot == "last":
        room = finished(g, end, take, noor_face=AT_MANUAL, dev_face=AT_MANUAL)
        if not take.is_effect:
            said = take.speech_duration + 0.1
            cv.gate(room, [(0, said)])
            page(g, 41, "bun", at=(said, end), end=end)
    else:  # bun
        said = take.speech_duration + 0.8
        dev_close(g, take, end, (0, said))
        noor_reading(g, end, CLOSELY, (said, end))


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=78)
cv.gate(hook, [(0, STILL + 0.95)])
spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({}), loudness="-14")
stick_reel.close(ep, POSTS["some-assembly"], hook, spoken)

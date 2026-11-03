#!/usr/bin/env python3
"""Stick — Pay in Four, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 pay_in_four_audio.py PROJECT --font DIR   # voices, timeline.json
    srstudio build pay-in-four PROJECT                                      # → PROJECT/pay-in-four.scene.xml

A repo man at Noor's front door, over a burrito on four easy payments. The set is ``stick_porch``: the truck backs up
the path through the doorway behind him. The effects are ``foley`` bursts, written next to the takes.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from pay_in_four_audio import (
    AT_NOOR,
    AT_STOMACH,
    BEEP_GAP,
    BLANK,
    CAMERAS,
    HOOK,
    HOOK_LAG,
    LOOKS,
    NOOR_CROSS,
    NOOR_FLAT,
    NOOR_HOOK,
    NOOR_LOOK,
    NOOR_PAST,
    NOOR_SMALL,
    NOOR_WHAT,
    OPENS,
    READING,
    REPO_LOOK,
    SMILE,
    TRUCK_FROM,
    TRUCK_RUN,
    TRUCK_TO,
    TURN_AFTER,
)
from srstudio import SPEECH_MOUTH, Episode, foley, stick, stick_reel
from srstudio import stick_door as sd
from srstudio import stick_porch as sp

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "pay-in-four",
        "198",
        "Pay in Four — Stick",
        "Portrait stick-figure cartoon: a repo man comes to Noor's door over a burrito on four easy payments. Native "
        "vector animation; ElevenLabs voices.",
        3306,
        bleed=True,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
REPO_AT = sd.on_path(sp.VISITOR, sp.VISITOR_LANE)[:2]
REPO_SCALE = sd.on_path(sp.VISITOR, sp.VISITOR_LANE)[2]
NOOR_AT, NOOR_SCALE = sp.HOUSEHOLDER_AT, sp.HOUSEHOLDER_SCALE
spoken_by = {x.id: x for x in t.takes}


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def noor(parent, keys, end: float, take=None):
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None else {}
    return stick.rig(cv, parent, keys, end, poses=sp.POSES, look=NOOR_LOOK, at=NOOR_AT, scale=NOOR_SCALE, flip=True,
                     mouth=SPEECH_MOUTH, blinks=(0.9,) if end > 1.6 else (), **speaks)  # fmt: skip


def repo(parent, keys, end: float, take=None, *, turned: float | None = None):
    """The repo man on the step, the board in his hand: edge on, then flat to the viewer from ``turned``."""
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None else {}
    place = dict(poses=sp.POSES, at=REPO_AT, scale=REPO_SCALE)
    stick.rig(cv, parent, keys, end, look=REPO_LOOK, mouth=SPEECH_MOUTH, **speaks, **place)
    hand = stick.held(cv, parent, keys, end, **place)
    if turned is None:
        sp.clipboard(cv, hand)
        return
    if turned > 0:
        edge = cv.group(hand, cv.uid("board-edge"))
        cv.gate(edge, [(0, turned)])
        sp.clipboard(cv, edge)
    page = cv.group(hand, cv.uid("board-page"))
    cv.gate(page, [(turned, end)])
    sp.clipboard(cv, page, turned=True)


def scene(parent, end: float, keys, *, take=None, noor_keys=None, noor_take=None, opens=None, truck=None, turned=None):
    """The hall, the yard with the truck and the repo man in it, the door over them, then Noor."""
    sp.hall(cv, parent, end)
    yard = sp.outside(cv, parent)
    if truck is not None:
        sp.tow_truck(cv, yard, end, **truck)
    repo(yard, keys, end, take, turned=turned)
    sp.front_door(cv, parent, end, opens=opens)
    noor(parent, noor_keys or [stick.RigKey(0, "hands-hips", NOOR_FLAT)], end, noor_take)


def stage(take) -> None:
    """Draw ``take``'s shot."""
    g = ep.shot(shots, take)
    end, said = take.duration, take.speech_duration
    still = [stick.RigKey(0, "board", BLANK)]
    if take.shot == "door":
        frame = camera(g, "two")
        scene(frame, end, still, take=take, opens=OPENS,
              noor_keys=[stick.RigKey(0, "knob", NOOR_FLAT),
                         stick.RigKey(OPENS + 0.5, "hands-hips", NOOR_FLAT)])  # fmt: skip
    elif take.shot == "noor":
        frame = camera(g, "noor")
        mad = NOOR_WHAT if take.id == "02" else NOOR_CROSS
        scene(frame, end, still, noor_keys=[stick.RigKey(0, "hands-hips", mad)], noor_take=take,
              truck={} if take.id == "11" else None)  # fmt: skip
    elif take.shot == "repo":
        scene(camera(g, "repo"), end, [stick.RigKey(0, "read", READING)], take=take)
    elif take.shot == "truck":
        frame = camera(g, "two")
        stop = said + 0.15 + TRUCK_RUN
        scene(frame, end, [stick.RigKey(0, "read", READING)], take=take,
              noor_keys=[stick.RigKey(0, "hands-hips", NOOR_FLAT), stick.RigKey(said + 0.5, "hands-hips", NOOR_PAST)],
              truck=dict(path=((said + 0.15, TRUCK_FROM), (stop, TRUCK_TO)), drop=stop + HOOK_LAG))  # fmt: skip
    elif take.shot == "two":
        scene(
            camera(g, "two"), end, still, truck={}, noor_keys=[stick.RigKey(0, "hands-hips", NOOR_PAST)], noor_take=take
        )
    elif take.shot == "hook":
        frame = camera(g, "repo")
        keys = still
        if take.id == "09":
            keys = [stick.RigKey(0, "board", BLANK), stick.RigKey(said + LOOKS[0], "board", AT_STOMACH),
                    stick.RigKey(said + LOOKS[1], "read", READING)]  # fmt: skip
        scene(frame, end, keys, take=take, truck={})
    elif take.shot == "guac":
        cut = said + AT_NOOR
        near = cv.group(g, cv.uid("guac-repo"))
        cv.gate(near, [(0, cut)])
        scene(camera(near, "repo"), end, still, take=take, truck={})
        back = cv.group(g, cv.uid("guac-noor"))
        cv.gate(back, [(cut, end)])
        scene(camera(back, "noor"), end, still, truck={}, noor_keys=[stick.RigKey(0, "hands-hips", NOOR_HOOK)])
    elif take.shot == "small":
        cut = said + 0.05
        near = cv.group(g, cv.uid("small-noor"))
        cv.gate(near, [(0, cut)])
        scene(camera(near, "noor"), end, still, truck={}, noor_keys=[stick.RigKey(0, "small", NOOR_SMALL)],
              noor_take=take)  # fmt: skip
        back = cv.group(g, cv.uid("small-repo"))
        cv.gate(back, [(cut, end)])
        turn = said + TURN_AFTER
        scene(camera(back, "board"), end, [stick.RigKey(0, "board", BLANK), stick.RigKey(turn - 0.25, "board", SMILE),
                                           stick.RigKey(turn, "offer", SMILE)],
              truck={}, turned=turn, noor_keys=[stick.RigKey(0, "small", NOOR_SMALL)])  # fmt: skip
    else:  # board
        scene(camera(g, "board"), end, [stick.RigKey(0, "offer", SMILE)], take=take, truck={}, turned=0.0,
              noor_keys=[stick.RigKey(0, "small", NOOR_SMALL)])  # fmt: skip


def sound() -> list:
    """The latch, the beeper down the truck's run, its engine, the hook's chain and its stop, and the page."""
    truck = spoken_by["07"]
    small = spoken_by["13"]
    backs = truck.start + truck.speech_duration + 0.15
    stops = backs + TRUCK_RUN
    drops = stops + HOOK_LAG
    run = ROOT / "audio"
    foley.write_bursts(run / "latch.wav", [OPENS], t.duration, foley.REMOTE_CLICK)
    foley.write_bursts(run / "swing.wav", [OPENS + 0.06], t.duration, foley.SWISH)
    beep = foley.Burst(0.34, 300.0, attack=0.004, decay=2.0, tone_hz=1050.0, tone_end_hz=1050.0, tone=1.0)
    beeps = [backs + k * BEEP_GAP for k in range(1 + int((stops - backs) / BEEP_GAP))]
    foley.write_bursts(run / "beep.wav", beeps, t.duration, beep)
    engine = foley.Burst(3.6, 500.0, attack=0.4, decay=1.0, tone_hz=52.0, tone_end_hz=58.0, tone=0.45, flutter_hz=14.0)
    foley.write_bursts(run / "engine.wav", [backs - 0.1], t.duration, engine)
    foley.write_bursts(run / "chain.wav", [drops + k * 0.09 for k in range(8)], t.duration, foley.SCRAPE, seed=3)
    foley.write_bursts(run / "clunk.wav", [drops + 0.82], t.duration, foley.THUD)
    foley.write_bursts(run / "page.wav", [small.start + small.speech_duration + TURN_AFTER], t.duration, foley.SWISH)
    return [
        ("latch", "audio/latch.wav", {"role": "effects", "gain": -6}),
        ("swing", "audio/swing.wav", {"role": "effects", "gain": -16}),
        ("beep", "audio/beep.wav", {"role": "effects", "gain": -9}),
        ("engine", "audio/engine.wav", {"role": "ambience", "gain": -6}),
        ("chain", "audio/chain.wav", {"role": "effects", "gain": -8}),
        ("clunk", "audio/clunk.wav", {"role": "effects", "gain": -6}),
        ("page", "audio/page.wav", {"role": "effects", "gain": -14}),
    ]


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=58, width=stick_reel.CARD_CLEAR)
cv.gate(hook, [(0, min(3.0, t.takes[2].start))])
spoken = stick_reel.words(ep, t.takes, sentences=True)
ep.audio(take=stick_reel.placing({}), loudness="-14", extra=sound())
stick_reel.close(ep, POSTS["pay-in-four"], hook, spoken, first_word=True)

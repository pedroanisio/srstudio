#!/usr/bin/env python3
"""Stick — In Two Hundred, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 in_two_hundred_audio.py PROJECT --font DIR   # voices, timeline.json
    srstudio build in-two-hundred PROJECT                                      # → PROJECT/in-two-hundred.scene.xml

Noor says left, the map says straight, Dev believes the satellites, and the road gives out into a field. The two-shot
is ``stick_windshield``; the road ahead and the phone are ``stick_satnav``. The effects are ``foley`` bursts.
"""

import os

from _common import project_root
from in_two_hundred_audio import (
    BEFORE,
    BUZZ_LEAD,
    DEV_ANGRY,
    DEV_DOWN,
    CAR_MARKS,
    DEV_LOOK,
    DEV_LOST,
    DEV_ROAD,
    DEV_SAYS,
    DEV_SURE,
    GRASS,
    GRAVEL,
    HOOK,
    NOOR_AT_MAP,
    NOOR_FIRM,
    NOOR_LOOK,
    NOOR_ROAD,
    NOOR_STILL,
    SCREENS,
    STOPPING,
)
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, foley, stick, stick_reel
from srstudio import stick_satnav as nav
from srstudio import stick_windshield as ws

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "in-two-hundred",
        "200",
        "In Two Hundred — Stick",
        "Portrait stick-figure cartoon: Dev trusts the map over Noor, and the map drives them into a field and takes "
        "her side. Native vector animation; ElevenLabs voices.",
        3308,
        bleed=True,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
said = {x.id: x for x in t.takes}


def speaks(take, who: str) -> dict:
    return dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}


def two_shot(
    parent, end, *, take=None, speed=2.5, ground="road", dev, noor, noor_pose="sit", dev_pose="drive", buzz=()
):
    """The two of them through the windshield."""
    ws.windshield(cv, parent, end, speed=speed, ground=ground)
    stick.rig(cv, parent, [stick.RigKey(0, dev_pose, dev)], end, poses=nav.POSES, look=DEV_LOOK, at=ws.DRIVER_AT,
              mouth=SPEECH_MOUTH, blinks=(0.8,) if end > 1.4 else (), **speaks(take, "dev"))  # fmt: skip
    keys = noor if isinstance(noor, list) else [stick.RigKey(0, noor_pose, noor)]
    stick.rig(cv, parent, keys, end, poses=nav.POSES, look=NOOR_LOOK, at=ws.PASSENGER_AT, mouth=SPEECH_MOUTH,
              **speaks(take, "noor"))  # fmt: skip
    ws.dashboard(cv, parent, end, buzz=buzz, marks=CAR_MARKS)


def drive_on(take, g, end: float) -> None:
    """The moving two-shot of the first five takes."""
    if take.id == "01":
        two_shot(g, end, take=take, dev=DEV_ROAD, noor=NOOR_FIRM, noor_pose="point")
    elif take.id == "03":
        two_shot(g, end, take=take, dev=DEV_SAYS, noor=NOOR_ROAD)
    elif take.id == "04":
        two_shot(g, end, take=take, dev=DEV_ROAD, noor=NOOR_FIRM, noor_pose="crossed")
    else:  # 05: the map again, on the dash
        two_shot(g, end, take=take, dev=DEV_SURE, noor=NOOR_ROAD, noor_pose="crossed", buzz=(BUZZ_LEAD,))


def stage(take) -> None:
    """Draw ``take``'s shot."""
    g = ep.shot(shots, take)
    end, line = take.duration, take.speech_duration
    if take.shot == "two":
        drive_on(take, g, end)
    elif take.shot == "map":
        nav.nav_insert(cv, g, end, screen=SCREENS[take.id], buzz=(BUZZ_LEAD,))
    elif take.shot == "rough":
        marks = [line + BEFORE, line + BEFORE + GRAVEL, line + BEFORE + GRAVEL + GRASS]
        stops = marks[2] + STOPPING
        moving = cv.group(g, cv.uid("still-sure"))
        cv.gate(moving, [(0, marks[0])])
        two_shot(moving, end, take=take, dev=DEV_SURE, noor=NOOR_ROAD, noor_pose="crossed")
        for name, a, b, fence in (("gravel", marks[0], marks[1], None), ("grass", marks[1], marks[2], None),
                                  ("grass", marks[2], stops, stops - marks[2])):  # fmt: skip
            view = cv.group(g, cv.uid("ahead"))
            cv.gate(view, [(a, b)])
            nav.ahead(cv, view, end, surface=name, fence=fence)
        field = cv.group(g, cv.uid("stopped"))
        cv.gate(field, [(stops, end)])
        two_shot(field, end, speed=0, ground="field", dev=DEV_LOST, noor=NOOR_STILL, noor_pose="crossed")
    elif take.shot == "stopped":
        faces = {"08": DEV_SAYS, "10": DEV_LOST, "12": DEV_ANGRY}
        two_shot(g, end, take=take, speed=0, ground="field", dev=faces[take.id], noor=NOOR_STILL, noor_pose="crossed")
    else:  # back: the phone for its line, then the two of them taking it
        cut = line + 0.1
        phone = cv.group(g, cv.uid("phone"))
        cv.gate(phone, [(0, cut)])
        nav.nav_insert(cv, phone, end, screen=SCREENS[take.id], buzz=(BUZZ_LEAD,))
        back = cv.group(g, cv.uid("back"))
        cv.gate(back, [(cut, end)])
        two_shot(back, end, speed=0, ground="field", dev=DEV_DOWN if take.id == "13" else DEV_LOST, noor=NOOR_AT_MAP,
                 noor_pose="sit")  # fmt: skip


def sound() -> list:
    """The road, the gravel, the grass, the stop, the engine ticking in the field, and a soft chime before each line
    of the map's."""
    rough = said["06"]
    start = rough.start + rough.speech_duration + BEFORE
    run = ROOT / "audio"
    road = foley.ROAD
    foley.write_bursts(run / "road.wav", [k * 2.6 for k in range(1 + int(start / 2.6))], t.duration, road, seed=8)
    gravel = foley.Burst(1.0, 3200.0, attack=0.04, decay=3.0, tone_hz=70.0, tone_end_hz=70.0, tone=0.2, flutter_hz=26.0)
    grass = foley.Burst(1.1, 1500.0, attack=0.05, decay=3.0, tone_hz=60.0, tone_end_hz=50.0, tone=0.15, flutter_hz=9.0)
    foley.write_bursts(run / "gravel.wav", [start], t.duration, gravel, seed=2)
    foley.write_bursts(run / "grass.wav", [start + GRAVEL, start + GRAVEL + GRASS * 0.8], t.duration, grass, seed=4)
    stop = start + GRAVEL + GRASS + STOPPING
    foley.write_bursts(run / "stop.wav", [stop], t.duration, foley.THUD)
    tick = foley.Burst(0.05, 2600.0, attack=0.002, decay=0.3, tone_hz=1800.0, tone_end_hz=1500.0, tone=0.3)
    foley.write_bursts(run / "tick.wav", [stop + 0.5, stop + 1.15, stop + 1.7], t.duration, tick)
    chime = foley.Burst(0.3, 300.0, attack=0.004, decay=0.5, tone_hz=1175.0, tone_end_hz=1175.0, tone=1.0)
    times = [x.start + 0.0 for x in t.takes if x.actor == "map"]
    foley.write_bursts(run / "chime.wav", times, t.duration, chime)
    return [
        ("road", "audio/road.wav", {"role": "ambience", "gain": -8}),
        ("gravel", "audio/gravel.wav", {"role": "effects", "gain": -7}),
        ("grass", "audio/grass.wav", {"role": "effects", "gain": -9}),
        ("stop", "audio/stop.wav", {"role": "effects", "gain": -6}),
        ("tick", "audio/tick.wav", {"role": "effects", "gain": -14}),
        ("chime", "audio/chime.wav", {"role": "effects", "gain": -16}),
    ]


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, min(3.0, t.takes[3].start))])
spoken = stick_reel.words(ep, t.takes, sentences=True)
ep.audio(take=stick_reel.placing({}), loudness="-14", extra=sound())
stick_reel.close(ep, POSTS["in-two-hundred"], hook, spoken)

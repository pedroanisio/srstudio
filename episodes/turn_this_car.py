#!/usr/bin/env python3
"""Stick 16 — Turn This Car, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 turn_this_car_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build turn-this-car PROJECT                                      # → PROJECT/turn-this-car.scene.xml

One more word, says Dad, and the kid says it. Five miles from the beach he turns the car around, and 410 miles later
nobody has taken off a hat. The car is ``stick_windshield``, the road ``stick_street``, the mirror, the rings and the
indicator ``stick_roadtrip``, the hour ``stick_bed.lights_low``. The first shot and the last are the same mirror.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, foley, stick, stick_bed, stick_reel, stick_roadtrip, stick_street
from srstudio import stick_windshield as ws
from turn_this_car_audio import (
    ARROW,
    CLICK_GAIN,
    CLICKS,
    CODE,
    DAD,
    ENGINE_TICK,
    HOOK,
    HOUR_SIX,
    IN_MIRROR,
    INDICATOR,
    KID,
    KID_AT,
    KID_SCALE,
    LAST_CLICKS,
    MIRROR_AT,
    MIRROR_SCALE,
    MOM,
    PARTS,
    RINGS,
    ROAD_GAIN,
    TICK_GAIN,
    TICKS,
    TWO_AM,
)

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "turn-this-car",
        "R16",
        "Turn This Car — Stick 16",
        "Portrait stick-figure cartoon: a father keeps the threat every parent makes, 410 miles back from the beach. "
        "Native vector animation; ElevenLabs voices and effects, synthesized indicator.",
        3127,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
ids = [take.id for take in t.takes]
LOOKS = {"dad": DAD, "mom": MOM, "kid": KID}
SPEED = {"car": 2.5, "dusk": 2.5, "night": 0.0}
TONE = {"dusk": ("#e39a5e", 0.34, (540.0, 900.0, 900.0)), "night": (stick_bed.NIGHT, 0.72, (540.0, 1000.0, 560.0))}
SIGNS = {"beach": "BEACH 5", "home": "HOME 410"}
SPOT = {"mom": ws.PASSENGER_AT, "dad": ws.DRIVER_AT, "kid": KID_AT}
take_02, take_12 = t.takes[1], t.takes[11]
last = t.takes[-1]
parked = t.takes[10]
CLICK_AT = {"01": [], "02": [take_02.speech_duration + c for c in CLICKS], "14": list(LAST_CLICKS)}


def part(who: str, take_id: str) -> list[tuple[float, str, stick.Face]]:
    """The rows of the last take up to this one that gives ``who`` any; held from the shot's first frame."""
    rows = PARTS[who]
    if take_id in rows:
        return rows[take_id]
    earlier = [i for i in ids[: ids.index(take_id)] if i in rows]
    time, pose, face = rows[earlier[-1]][-1] if earlier else rows["02"][0]
    return [(0, pose, face)]


def figure(g, who: str, take, end: float, *, scale: float = 1.0) -> None:
    speaks = dict(phones=take.phones, mood=take.mood) if take.actor == who else {}
    keys = [stick.RigKey(at, pose, face) for at, pose, face in part(who, take.id)]
    stick.rig(
        cv, g, keys, end, poses=ws.FRONT, look=LOOKS[who], at=SPOT[who], scale=scale, mouth=SPEECH_MOUTH, **speaks
    )


def in_mirror(glass, take, end: float) -> None:
    """Dad's eyes, drawn large into the glass; nothing in the frame says what hour it is."""
    keys = [stick.RigKey(at, "drive", face) for at, face in IN_MIRROR[take.id]]
    stick.rig(cv, glass, keys, end, poses=ws.FRONT, look=DAD, at=MIRROR_AT, scale=MIRROR_SCALE)


def mirror(g, take, end: float) -> None:
    stick_roadtrip.rear_view(cv, g, lambda glass: in_mirror(glass, take, end))
    if take.id in CLICK_AT:
        stick_roadtrip.blinker(cv, g, 540.0, 1330.0, end, CLICK_AT[take.id], scale=1.2)


def car(g, take, end: float) -> None:
    ws.windshield(cv, g, end, speed=SPEED[take.shot])
    for x, y, rx, ry, band in RINGS:
        stick_roadtrip.swim_ring(cv, g, x, y, rx=rx, ry=ry, band=band)
    figure(g, "kid", take, end, scale=KID_SCALE)
    figure(g, "mom", take, end)
    figure(g, "dad", take, end)
    ws.dashboard(cv, g, end, code=CODE)
    if take.id in CLICK_AT:
        stick_roadtrip.blinker(cv, g, *ARROW, end, CLICK_AT[take.id], scale=0.8)
    if take.shot in TONE:
        tint, strength, pool = TONE[take.shot]
        stick_bed.lights_low(cv, g, tint=tint, strength=strength, pool=pool)


def u_turn(parent, take) -> None:
    """The road from above; the car comes up it, swings round and goes back the way it came."""
    end = take.duration
    stick_street.road_plan(cv, parent)
    a, b, c = end * 0.3, end * 0.55, end * 0.8
    points = ((0.0, 740.0, 1700.0, 0.0), (a, 740.0, 1000.0, 0.0), (b, 540.0, 640.0, -90.0), (c, 340.0, 1000.0, -180.0),
              (end, 340.0, 1500.0, -180.0))  # fmt: skip
    g = stick._group(cv, parent, x=740.0, y=1700.0, rotation=0.0)
    for i, prop in ((1, "x"), (2, "y"), (3, "rotation")):
        cv.keys(g, prop, [(p[0], p[i]) for p in points], hold=False)
    stick_street.top_car(cv, g)


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "mirror":
        mirror(g, take, end)
    elif take.shot == "uturn":
        u_turn(g, take)
    elif take.shot in SIGNS:
        stick_street.road_ahead(cv, g)
        stick_street.road_sign(cv, g, end, text=SIGNS[take.shot])
    else:
        car(g, take, end)


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, t.takes[0].start + t.takes[0].duration)])
hour = stick.card(cv, cv.comp, HOUR_SIX, size=58)
dusk = [x for x in t.takes if x.shot == "dusk"]
cv.gate(hour, [(dusk[0].start, dusk[1].start + dusk[1].duration)])
two = stick.card(cv, cv.comp, TWO_AM, size=58)
cv.gate(two, [(parked.start, take_12.start + take_12.speech_duration)])
spoken = stick_reel.words(ep, t.takes)

ROAD_ENDS = parked.start
road = [k * 2.8 for k in range(int(ROAD_ENDS / 2.8) + 1)]
clicks = [take_02.start + c for c in CLICK_AT["02"]] + [last.start + c for c in LAST_CLICKS]
ticks = [take_12.start + take_12.speech_duration + c for c in TICKS]
foley.write_bursts(ROOT / "assets" / "road.wav", road, ROAD_ENDS, foley.ROAD, seed=31271)
foley.write_bursts(ROOT / "assets" / "clicks.wav", clicks, t.duration, INDICATOR, seed=31272)
foley.write_bursts(ROOT / "assets" / "ticks.wav", ticks, t.duration, ENGINE_TICK, seed=31273)
ep.audio(
    take=stick_reel.placing({}),
    loudness="-14",
    extra=[
        ("road", "assets/road.wav", {"role": "ambience", "gain": ROAD_GAIN}),
        ("clicks", "assets/clicks.wav", {"role": "effects", "gain": CLICK_GAIN}),
        ("ticks", "assets/ticks.wav", {"role": "effects", "gain": TICK_GAIN}),
    ],
)
stick_reel.close(ep, POSTS["turn-this-car"], hook, hour, two, spoken)

#!/usr/bin/env python3
"""Stick 15 — The Chirp, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_chirp_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build the-chirp PROJECT                                      # → PROJECT/the-chirp.scene.xml

Five smoke alarms, three in the morning, and none of them will say which. The chirps are ``foley`` bursts, written at
build at times read from the recorded speech, so the gags stay on the timing the takes actually have.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, foley, stick, stick_home, stick_reel
from the_chirp_audio import HELD, SCRIPT

os.umask(0o077)
ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "the-chirp",
        "R15",
        "The Chirp — Stick 15",
        "Portrait stick-figure cartoon: a man removes every smoke alarm in the house, and one keeps chirping. Native "
        "vector animation; ElevenLabs voices and effects.",
        3109,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
OPENING = t.takes[0].words[0]["start"]
if SCRIPT.still < 1.0 or SCRIPT.still != HELD or OPENING < 1.0:
    raise stick.StickDataError(f"arm A holds the first frame at least 1 s, got {OPENING}")

UP = stick.STANDING["stand"]
POSES = {
    "stand": UP,
    "hold": stick._seat((540, 750), UP.neck, UP.hip, UP.knees, UP.feet, ((450, 1010), (630, 1010)), ((384, 930), (696, 930))),
    "fall": stick._seat((540, 770), UP.neck, UP.hip, UP.knees, UP.feet, ((470, 1040), (612, 1040)), ((440, 1120), (640, 1120))),
    "load": stick._seat((560, 754), UP.neck, UP.hip, UP.knees, UP.feet, ((640, 1000), (650, 950)), ((780, 960), (790, 900))),
    "lean": stick._seat((580, 790), UP.neck, UP.hip, UP.knees, UP.feet, ((610, 1090), (640, 1040)), ((692, 1060), (692, 1040))),
}  # fmt: skip
HUSBAND = stick.PLAIN
CHAIR_AT = (160.0, -150.0)  # up on the chair, right of the bed
BLANK = stick.Face("open", "flat", "flat", look=(-1, 0))
AT_ALARM = stick.Face("wide", "raised", "flat", look=(-1, 0))
AT_BATTERY = stick.Face("wide", "raised", "flat", look=(1, 0))
FRONT = stick.Face("open", "flat", "flat")
PROUD = stick.Face("happy", "flat", "smile")
SMILING = stick.Face("open", "raised", "smirk")
DEAD = stick.Face("half", "flat", "frown")
AT_PEACE = stick.Face("half", "flat", "smile", look=(1, 0))
HEAP = ((640, 1500), (790, 1510), (940, 1495), (710, 1420), (860, 1415))
DIRT = ((470, 1030), (610, 1120), (540, 1260), (500, 1500), (600, 1420), (560, 700), (470, 800))


def spoken_end(take) -> float:
    """When the last word of ``take`` ends, on its own clock."""
    return take.words[-1]["end"]


def boxers(parent, cx: float, y: float) -> None:
    """His underwear, on whatever he is standing in."""
    stick.box(cv, parent, cx - 74, y - 40, 148, 120, "#e8e4d6", 5, r=14)
    for dx, dy in ((-40, -10), (20, -14), (-20, 34), (36, 30)):
        stick.oval(cv, parent, cx + dx, y + dy, 18, 18, "#c0453b")
    stick.shape(cv, parent, f"M {cx} {y + 20} L {cx} {y + 80}", sw=5, stroke=cv.ink)


def battery(parent, x: float, y: float) -> None:
    stick.box(cv, parent, x - 30, y - 46, 60, 92, "#2e3136", 4, r=6)
    stick.box(cv, parent, x - 30, y - 46, 60, 34, "#d9a441", 4, r=6)
    stick.box(cv, parent, x - 18, y - 60, 12, 14, "#b7c0c7", 3)
    stick.box(cv, parent, x + 6, y - 60, 12, 14, "#b7c0c7", 3)


def husband(parent, keys, end: float, take=None, *, at=(0.0, 0.0)) -> None:
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == "husband" else {}
    stick.rig(cv, parent, keys, end, poses=POSES, look=HUSBAND, at=at, mouth=SPEECH_MOUTH, **speaks)
    boxers(parent, at[0] + 540, UP.hip[1] + at[1])


def night_shot(take, g, end: float) -> list[float]:
    """The first wide; returns the chirps of this take, on the episode clock."""
    stick_home.bedroom(cv, g)
    stick_home.chair(cv, g, 700, 1710)
    if take.id == "01":
        chirp = spoken_end(take) + 1.5
        keys = [stick.RigKey(0, "hold", BLANK), stick.RigKey(chirp + 0.15, "hold", AT_ALARM),
                stick.RigKey(chirp + 1.05, "hold", AT_BATTERY)]  # fmt: skip
        flashes, sounds = (chirp,), [take.start + chirp]
    else:
        keys = [stick.RigKey(0, "hold", AT_BATTERY), stick.RigKey(0.25, "hold", AT_ALARM)]
        flashes, sounds = (), []
        talk = cv.group(g, cv.uid("asleep"))
        cv.gate(talk, stick_reel.turns(spoken_end(take), 7.0)[0])
        stick.oval(cv, talk, 196, 1180, 34, 26, "#3a2226")  # eyes shut, mouth going
    husband(g, keys, end, take, at=CHAIR_AT)
    stick_home.smoke_alarm(cv, g, 544, 760, scale=0.72, flashes=flashes)
    battery(g, 856, 760)
    return sounds


def heap_shot(take, g, end: float) -> list[float]:
    stick_home.bedroom(cv, g)
    chirp = spoken_end(take) + 2.0
    keys = [stick.RigKey(0, "stand", FRONT), stick.RigKey(spoken_end(take) + 0.9, "stand", SMILING),
            stick.RigKey(spoken_end(take) + 1.5, "stand", PROUD), stick.RigKey(chirp + 0.05, "fall", DEAD)]  # fmt: skip
    husband(g, keys, end, take, at=(250.0, 0.0))
    for i, (x, y) in enumerate(HEAP):
        stick_home.smoke_alarm(cv, g, x, y, flashes=(chirp,) if i == 3 else ())
    return [take.start + chirp]


def fridge_shot(take, g, end: float, *, shut: bool) -> list[float]:
    stick_home.kitchen(cv, g)
    stick.box(cv, g, 0, 0, cv.width, cv.height, "#1f2645", opacity=0.55)
    if not shut:
        stick_home.fridge_open(cv, g)
        for x, y in ((880, 660), (980, 690), (900, 900), (990, 880), (930, 1120)):
            stick_home.smoke_alarm(cv, g, x, y, scale=0.5)
        husband(g, [stick.RigKey(0, "load", FRONT)], end, take, at=(-40.0, 0.0))
        return []
    chirp = 2.45
    keys = [stick.RigKey(0, "stand", PROUD), stick.RigKey(chirp + 0.05, "stand", DEAD)]
    husband(g, keys, end, None, at=(-40.0, 0.0))
    return [take.start + chirp]


def yard_shot(take, g, end: float) -> list[float]:
    stick.yard(cv, g, (), 3109)
    stick.box(cv, g, 0, 0, cv.width, cv.height, "#ffb27a", opacity=0.3)
    stick_home.mound(cv, g, 660, 1500, words="ALL 5")
    stick_home.shovel(cv, g, 430, 1660)
    husband(g, [stick.RigKey(0, "lean", AT_PEACE)], end, take if take.actor == "husband" else None, at=(-260.0, 0.0))
    for x, y in DIRT:
        stick.oval(cv, g, x - 260, y, 34, 22, "#59391f")
    if take.id != "08":
        return []
    return [take.start + 1.9]


loud, shut, buried = [], [], []
for take in t.takes:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "night":
        loud += night_shot(take, g, end)
    elif take.shot == "heap":
        loud += heap_shot(take, g, end)
    elif take.shot == "fridge":
        fridge_shot(take, g, end, shut=False)
    elif take.shot == "shut":
        shut += fridge_shot(take, g, end, shut=True)
    else:
        buried += yard_shot(take, g, end)

spoken = stick_reel.words(ep, t.takes)
chirps = (("loud", loud, foley.CHIRP), ("shut", shut, foley.CHIRP_SHUT), ("buried", buried, foley.CHIRP_BURIED))
for name, times, sound in chirps:
    foley.write_bursts(ROOT / "audio" / f"chirp-{name}.wav", times, t.duration, sound)
birds = next(x for x in t.takes if x.id == "06")
line = next(x for x in t.takes if x.id == "07")
ep.audio(
    take=stick_reel.placing({}),
    extra=[
        ("chirp-loud", "audio/chirp-loud.wav", {"role": "effects"}),
        ("chirp-shut", "audio/chirp-shut.wav", {"role": "effects", "gain": -8}),
        ("chirp-buried", "audio/chirp-buried.wav", {"role": "effects", "gain": -6}),
        ("birds-under", birds.audio, {"role": "ambience", "start": line.start}),
    ],
)
stick_reel.close(ep, POSTS["the-chirp"], spoken)

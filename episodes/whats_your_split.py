#!/usr/bin/env python3
"""Stick 16 — What's Your Split, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 whats_your_split_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build whats-your-split PROJECT                                      # → PROJECT/whats-your-split.scene.xml

A trainer reads an anxious man's smartwatch as an athlete's. The phone messages are ``stick_home.message``, set big
enough to read on a phone in the 1.2 s they hold.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, stick, stick_gym, stick_home, stick_reel
from whats_your_split_audio import HELD, SCRIPT

os.umask(0o077)
ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "whats-your-split",
        "R16",
        "What's Your Split — Stick 16",
        "Portrait stick-figure cartoon: a trainer reads an anxious man's smartwatch as an athlete's. Native vector "
        "animation; ElevenLabs voices and effects.",
        3115,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
OPENING = t.takes[0].words[0]["start"]
if SCRIPT.still < 1.0 or SCRIPT.still != HELD or OPENING < 1.0:
    raise stick.StickDataError(f"arm A holds the first frame at least 1 s, got {OPENING}")

UP = stick.STANDING["stand"]


def arms(head, elbows, hands) -> stick.RigPose:
    """The standing body with its head and arms somewhere else."""
    return stick._seat(head, UP.neck, UP.hip, UP.knees, UP.feet, elbows, hands)


POSES = {
    **stick.STANDING,
    "wrist": arms((540, 750), ((510, 1040), (640, 1000)), ((502, 1195), (740, 950))),
    "read": arms((528, 760), ((470, 1040), (572, 1040)), ((432, 975), (584, 1195))),
    "phone": arms((540, 770), ((470, 1040), (620, 1050)), ((502, 1195), (600, 920))),
    "spot": arms((540, 760), ((440, 1040), (640, 1040)), ((510, 950), (570, 950))),
    "spotter": arms((540, 740), ((370, 1040), (510, 1040)), ((300, 1062), (500, 1062))),
    "sag-1": stick._seat((540, 830), (540, 935), (540, 1290), ((470, 1450), (610, 1450)), ((512, 1700), (566, 1700)),
                         ((490, 1080), (590, 1080)), ((470, 1240), (610, 1240))),
    "sag-2": stick._seat((540, 960), (540, 1060), (540, 1410), ((440, 1480), (640, 1480)), ((512, 1700), (566, 1700)),
                         ((480, 1210), (600, 1210)), ((440, 1370), (640, 1370))),
    "sit": stick._seat((540, 1130), (540, 1235), (540, 1620), ((400, 1520), (680, 1520)), ((380, 1700), (700, 1700)),
                       ((470, 1400), (610, 1400)), ((430, 1540), (650, 1540))),
    "sit-up": stick._seat((540, 1130), (540, 1235), (540, 1620), ((400, 1520), (680, 1520)), ((380, 1700), (700, 1700)),
                          ((470, 1400), (640, 1000)), ((430, 1540), (700, 760))),
    "ref": arms((540, 750), ((470, 880), (620, 1040)), ((420, 770), (640, 1190))),
}  # fmt: skip
TRAINER = stick.Look(hair="spiky", tie=None, cap="#e85d3f")
MEMBER = stick.Look(hair="side-part", glasses=True)
MEMBER_AT = (-240.0, 0.0)
TRAINER_AT = (60.0, 0.0)
SPOT_AT, SPOTTER_AT = (-80.0, 0.0), (60.0, -6.0)
SIT_AT = (-170.0, 0.0)
BESIDE = (110.0, 0.0)
EAGER = stick.Face("wide", "raised", "smile", look=(-1, 0))
STUNNED = stick.Face("wide", "raised", "smile", look=(-1, 0))
THRILLED = stick.Face("happy", "raised", "smile", look=(-1, 0))
INTENT = stick.Face("open", "angry", "smirk", look=(-1, 0))
FLAT = stick.Face("half", "worried", "flat", look=(1, 0))
AWAY = stick.Face("half", "worried", "frown", look=(0, 0))
DOWN = stick.Face("wide", "worried", "frown", look=(1, 0.6))
TERROR = stick.Face("wide", "worried", "frown", look=(0.4, 0.6))
GONE = stick.Face("half", "flat", "frown", look=(0, 0))


def member(parent, keys, end: float, take=None, *, at=MEMBER_AT, gray: bool = False) -> None:
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == "member" else {}
    stick.rig(cv, parent, keys, end, poses=POSES, look=MEMBER, at=at, mouth=SPEECH_MOUTH, **speaks)
    if gray:
        x, y = POSES[keys[0].pose].head
        stick.oval(cv, parent, at[0] + x - 88, at[1] + y - 88, 176, 176, "#7f8a8c", opacity=0.55)


def trainer(parent, keys, end: float, take=None, *, at=TRAINER_AT) -> None:
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == "trainer" else {}
    stick.rig(cv, parent, keys, end, poses=POSES, look=TRAINER, at=at, mouth=SPEECH_MOUTH, **speaks)


def watch(parent, x: float, y: float, *, lit: bool = False) -> None:
    stick.box(cv, parent, x - 26, y - 22, 52, 44, "#16080a" if not lit else "#ffd23f", 4, r=10)


def room(parent, end: float) -> None:
    stick_gym.gym(cv, parent, end, sunrise=0)
    stick.box(cv, parent, 0, 1040, 590, 440, "#cfd6dc", 4)  # the mirror: black limbs do not read on the dark wall
    stick.box(cv, parent, 30, 1500, 560, 270, "#aeb6c0", 4, r=18)  # the mat
    stick_gym.counter(cv, parent, sign="PERSONAL TRAINING", fine="*RESULTS NOT TYPICAL")


def desk_shot(take, g, end: float) -> None:
    room(g, end)
    trainer(g, [stick.RigKey(0, "read", EAGER if take.id in ("01", "02") else INTENT)], end, take)
    member(g, [stick.RigKey(0, "wrist", FLAT)], end, take)
    watch(g, 500, 950)


def buzz_shot(g, end: float) -> None:
    room(g, end)
    trainer(g, [stick.RigKey(0, "read", STUNNED)], end)
    member(g, [stick.RigKey(0, "phone", DOWN)], end, gray=True)
    stick_home.handset(cv, g, 360, 920, lit=True, scale=1.1)


def spot_shot(take, g, end: float) -> None:
    room(g, end)
    trainer(g, [stick.RigKey(0, "spotter", INTENT)], end, take, at=SPOTTER_AT)
    member(g, [stick.RigKey(0, "spot", TERROR)], end, take, at=SPOT_AT)
    stick_home.handset(cv, g, 460, 930, lit=True, scale=1.1)
    watch(g, 470, 1000)


def sink_shot(g, end: float) -> None:
    room(g, end)
    trainer(g, [stick.RigKey(0, "stand", stick.Face("open", "raised", "smile", look=(-1, 0.4)))], end, at=BESIDE)
    keys = [stick.RigKey(0, "spot", GONE), stick.RigKey(0.4, "sag-1", GONE), stick.RigKey(0.85, "sag-2", GONE),
            stick.RigKey(1.3, "sit", GONE)]  # fmt: skip
    member(g, keys, end, at=SIT_AT)


def floor_shot(take, g, end: float) -> None:
    room(g, end)
    trainer(g, [stick.RigKey(0, "stand", THRILLED)], end, take, at=BESIDE)
    member(g, [stick.RigKey(0, "sit", GONE)], end, at=SIT_AT)


def best_shot(g, end: float) -> None:
    room(g, end)
    trainer(g, [stick.RigKey(0, "ref", THRILLED)], end, at=BESIDE)
    member(g, [stick.RigKey(0, "sit-up", GONE)], end, at=SIT_AT)
    watch(g, 500, 830, lit=True)
    stick.card(cv, g, "NEW PERSONAL BEST", size=72)


for take in t.takes:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "desk":
        desk_shot(take, g, end)
    elif take.shot == "buzz":
        buzz_shot(g, end)
    elif take.shot == "mom":
        stick_home.message(cv, g, sender="MOM", text="We need to talk.")
    elif take.shot == "spot":
        spot_shot(take, g, end)
    elif take.shot == "dog":
        stick_home.message(cv, g, sender="MOM", text="Which dog food do you buy")
    elif take.shot == "sink":
        sink_shot(g, end)
    elif take.shot == "floor":
        floor_shot(take, g, end)
    else:
        best_shot(g, end)

spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({}))
stick_reel.close(ep, POSTS["whats-your-split"], spoken)

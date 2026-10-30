#!/usr/bin/env python3
"""Stick 12 — Good, You, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 good_you_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build good-you PROJECT                                      # → PROJECT/good-you.scene.xml

Two coworkers, a coffee machine, Monday. "How was your weekend?" "Good, you?" "Good." Every Monday, whatever has
happened to them. The set is ``stick_office``; the figures are ``stick.rig``, and the injuries sit on them.
"""

import os

from _common import project_root
from good_you_audio import CAMERAS, DAYS, FLAT_A, FLAT_B, FRONT, HOOK, LAND_AT, SIPPING, A, B
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, stick, stick_reel
from srstudio import stick_office as so

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "good-you",
        "R12",
        "Good, You — Stick 12",
        "Portrait stick-figure cartoon: two coworkers have the same Monday conversation whatever happens to them. "
        "Native vector animation; ElevenLabs voices and effects.",
        1312,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
LEFT = so.on_figure(so.POSES["mug"], at=so.LEFT_AT)
RIGHT = so.on_figure(so.POSES["mug"], at=so.RIGHT_AT, flip=True)
SIP = so.on_figure(so.POSES["sip"], at=so.RIGHT_AT, flip=True)


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def voiced(take, actor: str) -> dict:
    """The mouth of ``actor`` if ``take`` is theirs."""
    if take is None or take.actor != actor:
        return {}
    return dict(phones=take.phones, mood=take.mood, mouth=SPEECH_MOUTH)


def left(parent, end: float, take=None, *, burning: bool = False) -> None:
    speaks = (
        dict(phones=take.phones, mood=take.mood, mouth=SPEECH_MOUTH) if take is not None and take.actor == "a" else {}
    )
    stick.rig(cv, parent, [stick.RigKey(0, "mug", FLAT_A)], end, poses=so.POSES, look=A, at=so.LEFT_AT, **speaks)
    if burning:
        so.flames(cv, parent, LEFT["head"][0] - 6, LEFT["head"][1] - 92, end)
        so.flames(cv, parent, LEFT["hand"][0] - 150, LEFT["neck"][1] + 40, end)


def right(parent, end: float, take=None, *, hurt: bool = False, face=FLAT_B, pose: str = "mug") -> None:
    speaks = (
        dict(phones=take.phones, mood=take.mood, mouth=SPEECH_MOUTH) if take is not None and take.actor == "b" else {}
    )
    at = dict(at=so.RIGHT_AT, flip=True)
    stick.rig(cv, parent, [stick.RigKey(0, pose, face)], end, poses=so.POSES, look=B, **at, **speaks)
    if hurt:
        so.brace(cv, parent, *RIGHT["neck"])
        so.parrot(cv, parent, RIGHT["neck"][0] + 70, RIGHT["neck"][1] + 14, facing=-1)


def beat(g, take) -> None:
    """One Monday of the corner, and what the week left."""
    end = take.duration
    frame = camera(g, "two")
    so.corner(cv, frame)
    week = take.shot
    if week == "mon5" or week == "friday":
        so.tombstone(cv, frame, 310.0, words="GOOD.")
    else:
        left(frame, end, take, burning=week == "mon4")
        if week in ("mon2", "mon3", "mon4"):
            so.cast(cv, frame, LEFT["elbow"], LEFT["hand"])
        so.mug(cv, frame, *LEFT["hand"])
    right(frame, end, take, hurt=week in ("mon3", "mon4", "mon5", "friday"))
    so.mug(cv, frame, *RIGHT["hand"])
    so.counter(cv, frame)
    if week in ("mon5", "friday"):
        so.mug(cv, frame, 410.0, so.COUNTER_TOP - 40.0)
    if week in DAYS:
        stick.card(cv, g, DAYS[week], size=50)


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "meteor":
        frame = camera(g, "two")
        so.corner(cv, frame)
        so.meteor(cv, so.view(cv, frame), end, land=LAND_AT)
        so.tombstone(cv, frame, 310.0, words="GOOD.")
        right(frame, end, hurt=True, face=FRONT)
        so.mug(cv, frame, *RIGHT["hand"])
        so.counter(cv, frame)
        so.mug(cv, frame, 410.0, so.COUNTER_TOP - 40.0)
    elif take.shot == "sip":
        frame = camera(g, "sip")
        so.corner(cv, frame)
        so.meteor(cv, so.view(cv, frame), end + 0.1, land=0.05)
        right(frame, end, hurt=False, face=SIPPING, pose="sip")
        so.brace(cv, frame, *SIP["neck"])
        so.parrot(cv, frame, SIP["neck"][0] + 70, SIP["neck"][1] + 14, facing=-1)
        so.mug(cv, frame, *SIP["hand"])
        so.counter(cv, frame)
    else:
        beat(g, take)


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, t.takes[3].start)])
spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({}))
stick_reel.close(ep, POSTS["good-you"], hook, spoken)

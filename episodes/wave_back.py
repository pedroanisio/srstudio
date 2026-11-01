#!/usr/bin/env python3
"""Stick 20 — Wave Back, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 wave_back_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build wave-back PROJECT                                      # → PROJECT/wave-back.scene.xml

Noor waves back at a man who was waving at somebody else, turns the arm into a stretch, the stretch into a class and
the class into a gym; then he walks in and waves at her, and she keeps her arm down. The street is
``stick_door.street``, the gym ``stick_gym``, and the figures are ``stick.rig``.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, stick, stick_door, stick_gym, stick_odds, stick_reel
from wave_back_audio import (
    BEAM,
    BEAMING,
    BEHIND,
    BLAND,
    BOSS,
    CALM,
    CARD,
    CAUGHT,
    CLASS,
    DYING,
    FRIEND,
    FRIEND_X,
    FROM_X,
    GLANCE,
    GRIN,
    HER_X,
    HIS_X,
    HOOK,
    HUG_X,
    KEEN,
    LEFT,
    LEVEL,
    MAN,
    NERVOUS,
    NOOR,
    PASSER,
    POSES,
    POSTER,
    RIGHT,
    ROWS,
    SINKING,
    STUCK,
    TO_X,
    WALK_RATE,
)

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "wave-back",
        "R20",
        "Wave Back — Stick 20",
        "Portrait stick-figure cartoon: a woman waves back at a man who was waving at someone else, and has to do "
        "something with the arm. Native vector animation; ElevenLabs voices and effects.",
        3120,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
K = stick.RigKey
FLOOR = 1700.0
DESK_X = 880.0  # Noor behind her desk
walk = t.takes[0].start, t.takes[1].start + t.takes[1].duration


def figure(parent, keys, end: float, look, x: float, take=None, *, who: str = "", flip: bool = RIGHT,
           scale: float = 1.0, floor: float = FLOOR, blinks=()):  # fmt: skip
    """A figure with its middle at ``x`` and its feet on ``floor``, facing right unless ``flip``."""
    speaks = dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}
    at = (x + 540 * scale if flip else x - 540 * scale, floor - FLOOR * scale)
    return stick.rig(cv, parent, keys, end, poses=POSES, look=look, at=at, scale=scale, flip=flip, mouth=SPEECH_MOUTH,
                     blinks=blinks, **speaks)  # fmt: skip


def steps(end: float, first: str, second: str, face, *, rate: float = WALK_RATE) -> list[stick.RigKey]:
    """A walk: two poses turn about, ``rate`` steps a second, for ``end`` seconds."""
    count = max(1, int(end * rate))
    return [K(round(i / rate, 4), second if i % 2 else first, face) for i in range(count)]


def sliding(parent, frm: float, to: float, end: float):
    """A group carrying what is drawn in it from ``frm`` to ``to`` pixels across, over the shot."""
    g = cv.group(parent, cv.uid("walker"))
    cv.keys(g, "x", [(0.0, frm), (end, to)], kind="linear")
    return g


def gym(parent, end: float) -> None:
    stick_gym.gym(cv, parent, end, sunrise=0)
    stick_odds.poster(cv, parent, 545, 118, 530, 440, POSTER, size=78)


def desk(parent, end: float, take, keys, *, x: float = DESK_X) -> None:
    """Noor behind her own desk, the sign over her legs."""
    figure(parent, keys, end, NOOR, x, take, who="noor", flip=LEFT)
    stick_gym.counter(cv, parent, sign=POSTER)
    stick_odds.headset(cv, parent, x, 750, flip=True)


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    speech = take.speech_duration
    if take.shot == "walk":
        stick_door.street(cv, g, end)
        now = take.start - walk[0]
        span = walk[1] - walk[0]
        here = FROM_X + (TO_X - FROM_X) * now / span
        there = FROM_X + (TO_X - FROM_X) * (now + end) / span
        her = sliding(g, here, there, end)
        keys = (
            steps(end, "walk-a", "walk-b", BEAM) if take.id == "01" else steps(end, "wave-walk", "wave-walk", BEAM)[:1]
        )
        figure(her, keys, end, NOOR, 0.0, take, who="noor")
        keys = [K(round(i * 0.17, 3), "wave-off" if i % 2 else "wave-high", GRIN) for i in range(int(end / 0.17))]
        figure(g, keys, end, MAN, HIS_X, take, who="man", flip=LEFT)
    elif take.id == "03":
        stick_door.street(cv, g, end)
        figure(g, [K(0, "wave-high", BEAM), K(end * 0.5, "wave-high", STUCK)], end, NOOR, HER_X)
        him = sliding(g, HIS_X, HUG_X + 20, end)
        figure(him, steps(end, "walk-a", "walk-b", GRIN), end, MAN, 0.0, flip=LEFT)
    elif take.id == "04":
        frame = stick.camera(cv, g, (HER_X, 900), zoom=1.3, push=end * 0.8, to=(500, 860))
        stick_door.street(cv, frame, end)
        figure(frame, [K(0, "hug", GRIN)], end, FRIEND, FRIEND_X)
        figure(frame, [K(0, "hug", GRIN)], end, MAN, HUG_X, flip=LEFT)
        figure(frame, [K(0, "wave-high", STUCK), K(0.7, "wave-high", SINKING)], end, NOOR, HER_X, blinks=(1.2,))
    elif take.shot == "stretch":
        frame = stick.camera(cv, g, (HER_X, 900), zoom=1.3, to=(500, 860))
        stick_door.street(cv, frame, end)
        if take.id == "05":
            figure(frame, [K(0, "wave-high", SINKING), K(0.35, "reach-1", SINKING)], end, NOOR, HER_X)
        else:
            keys = [K(0, "reach-1", NERVOUS), K(0.3, "reach-2", NERVOUS), K(0.7, "reach-3", BLAND)]
            figure(frame, keys, end, NOOR, HER_X, take, who="noor", blinks=(1.1,))
    elif take.shot == "class":
        stick_door.street(cv, g, end)
        figure(g, [K(0, "reach-3", BLAND if take.actor == "passer" else NERVOUS)], end, NOOR, HER_X, take, who="noor")
        figure(g, [K(0, "reach-3", KEEN)], end, PASSER, 780.0, take, who="passer")
    elif take.shot == "rows":
        stick_door.street(cv, g, end)
        crowd = iter(CLASS)
        for scale, floor, row in reversed(ROWS):
            for x in row:
                look = next(crowd, PASSER)
                figure(g, [K(0, "reach-3", KEEN)], end, look, x, scale=scale, floor=floor)
        figure(g, [K(0, "reach-3", BOSS)], end, NOOR, 540.0, take, who="noor", scale=0.92, floor=1760.0)
    elif take.shot == "gym":
        gym(g, end)
        figure(g, [K(0, "stand", KEEN)], end, PASSER, 300.0, take, who="passer")
        desk(g, end, take, [K(0, "stand", CALM)])
    elif take.shot == "door":
        wide = cv.group(g, cv.uid("wide"))
        cut = round(speech + 0.1, 4) if speech else end
        cv.gate(wide, [(0, cut)])
        gym(wide, end)
        figure(wide, [K(0, "wave-high", GRIN)], end, MAN, 300.0, take, who="man")
        desk(wide, end, None, [K(0, "stand", GLANCE)])
        if take.speech_duration:
            close = cv.group(g, cv.uid("close"))
            cv.gate(close, [(cut, end)])
            frame = stick.camera(cv, close, (1080, 0), zoom=1.4, to=(1080, 0))  # her poster stays in the frame
            gym(frame, end)
            turned = cut + 0.35
            desk(frame, end, None, [K(0, "stand", GLANCE), K(turned, "stand", BEHIND), K(turned + 0.6, "stand", LEVEL)])
    else:  # man
        gym(g, end)
        if take.is_effect:
            keys = [K(0, "wave-high", BEAMING), K(0.3, "reach-1", DYING)]
        else:
            keys = [K(0, "reach-1", DYING), K(0.2, "reach-2", CAUGHT), K(0.45, "reach-3", CAUGHT)]
        desk(g, end, None, [K(0, "stand", LEVEL)])  # the rack and treadmill stand behind it: without it they float
        figure(g, keys, end, MAN, 300.0, take, who="man", scale=1.3, floor=1900.0, blinks=(0.9,) if end > 1.2 else ())


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=78)
cv.gate(hook, [(0, t.takes[2].start)])
gym_take = next(x for x in t.takes if x.shot == "gym")
years = stick.card(cv, cv.comp, CARD, size=72)
cv.gate(years, [(gym_take.start, gym_take.start + 1.5)])
spoken = stick_reel.words(ep, t.takes, sentences=True, hold=True)
ep.audio(take=stick_reel.placing({}), loudness="-14")
stick_reel.close(ep, POSTS["wave-back"], hook, years, spoken, first_word=True)

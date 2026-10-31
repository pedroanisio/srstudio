#!/usr/bin/env python3
"""Stick 15 — Third Snore, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 third_snore_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build third-snore PROJECT                                      # → PROJECT/third-snore.scene.xml

Noor and Dev settle who snores with a recording. The phone lies on the duvet between them and plays his snore, her
snore, and one that is neither. The duvet has been breathing since the first frame. The camera pulls back and the mound
sinks: Gary, who came with the flat, in an eye mask. The set is ``stick_flat`` with its bed down, the night and the
duvet are ``stick_bed``, and the figures are ``stick.rig``.
"""

import math
import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, stick, stick_bed, stick_flat, stick_reel
from third_snore_audio import (
    AT,
    BIG_BREATH,
    BREATH,
    BREATH_PX,
    CLOSE_FROM,
    CLOSE_TO,
    CX,
    DEV,
    GARY,
    GARY_HEAD,
    HOOK,
    NOOR,
    PARTS,
    PHONE_AT,
    PULL,
    PULL_AFTER,
    PUSH_TAKES,
    SCALE,
    SINK,
    WIDE,
)

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "third-snore",
        "R15",
        "Third Snore — Stick 15",
        "Portrait stick-figure cartoon: a couple settle who snores with a recording, and hear a third. Native vector "
        "animation; ElevenLabs voices and effects.",
        3122,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
ids = [take.id for take in t.takes]
LOOKS = {"dev": DEV, "noor": NOOR}
SNORES = {"04": 1, "06": 2, "08": 3}
pushed = t.takes[PUSH_TAKES - 1]
PUSH_END = pushed.start + pushed.duration
AREA = (0.0, 0.0, stick_flat.SET_W, 2400.0)


def part(who: str, take_id: str) -> list[tuple[float, str, stick.Face]]:
    """The rows of the last take up to this one that gives ``who`` any; held from the shot's first frame."""
    rows = PARTS[who]
    if take_id in rows:
        return rows[take_id]
    earlier = [i for i in ids[: ids.index(take_id)] if i in rows]
    time, pose, face = rows[earlier[-1]][-1]
    return [(0, pose, face)]


def breath(take, end: float) -> list[tuple[float, float]]:
    """The mound's lift through a shot, on the reel's clock so that it carries across the cuts."""
    lift = []
    for at in (*(k / 12 for k in range(math.ceil(end * 12))), end):
        now = take.start + at
        rise = BREATH_PX * math.sin(math.pi * now / BREATH) ** 2
        if take.id == "08" and BIG_BREATH[0] <= at <= BIG_BREATH[1]:
            u = (at - BIG_BREATH[0]) / (BIG_BREATH[1] - BIG_BREATH[0])
            rise += BIG_BREATH[2] * math.sin(math.pi * u)
        lift.append((min(round(at, 4), end), round(-rise, 2)))
    return lift


def sinking(take, end: float) -> list[tuple[float, float]]:
    start = take.speech_duration + PULL_AFTER
    rows = [(a, b) for a, b in breath(take, end) if a < start]
    return [*rows, (round(start + PULL, 4), SINK), (end, SINK)]


def framed(g, take, end: float):
    """The camera of ``take``: a push through the opening takes, the pull back, then the wide."""
    if take.shot == "close":
        into = lambda at: min(1.0, at / PUSH_END)  # noqa: E731
        return stick.dolly(cv, g, stick.between(CLOSE_FROM, CLOSE_TO, into(take.start)),
                           stick.between(CLOSE_FROM, CLOSE_TO, into(take.start + end)), end, kind="linear")  # fmt: skip
    if take.shot == "pull":
        return stick.dolly(cv, g, CLOSE_TO, WIDE, PULL, start=round(take.speech_duration + PULL_AFTER, 4))
    return stick.dolly(cv, g, WIDE, WIDE, end)


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    frame = framed(g, take, end)
    stick_flat.studio(cv, frame)
    shown = take.shot != "close"
    talk = ((0.0, round(take.speech_duration, 3)),) if take.actor == "gary" else ()
    # behind the mound he is not drawn at all: his snoring letters would stand between the couple
    stick_flat.murphy_bed(cv, frame, end, drop_at=0.0, sleeper=GARY if shown else None, talk=talk)
    if shown:
        stick_bed.eye_mask(cv, frame, *GARY_HEAD, scale=0.8)
    blinks = (0.9,) if end > 1.6 else ()
    for who in ("dev", "noor"):
        speaks = dict(phones=take.phones, mood=take.mood) if take.actor == who else {}
        keys = [stick.RigKey(at, pose, face) for at, pose, face in part(who, take.id)]
        stick.rig(cv, frame, keys, end, poses=stick_bed.BED, look=LOOKS[who], at=AT[who], scale=SCALE,
                  flip=who == "noor", blinks=blinks, mouth=SPEECH_MOUTH, **speaks)  # fmt: skip
    mound = stick_bed.duvet(cv, frame, end, x=CX, lift=sinking(take, end) if take.shot == "pull" else
                            (breath(take, end) if take.shot == "close" else [(0.0, SINK)]))  # fmt: skip
    if take.shot != "wide":
        heard = max((SNORES[i] for i in ids[: ids.index(take.id) + 1] if i in SNORES), default=0)
        stick_bed.recorder(cv, mound, *PHONE_AT, end, lines=heard, live=take.id in SNORES)
    stick_bed.lights_low(cv, frame, area=AREA, pool=(CX, 1220.0, 620.0))


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, t.takes[2].start)])
spoken = stick_reel.words(ep, t.takes)
ep.audio(take=stick_reel.placing({}), loudness="-14")
stick_reel.close(ep, POSTS["third-snore"], hook, spoken)

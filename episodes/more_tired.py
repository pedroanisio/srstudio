#!/usr/bin/env python3
"""Stick 17 — More Tired, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 more_tired_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    srstudio build more-tired PROJECT                                      # → PROJECT/more-tired.scene.xml

At six in the morning Noor and Dev compete over who slept less, and he finds his keys in the fridge without surprise.
The baby cries, and both fall asleep where they are, each with one eye open for the other. The kitchen is
``stick_home``, the hour ``stick_bed.lights_low``, the mugs ``stick_office``, the eye the rig's ``peek``.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from more_tired_audio import (
    CAMERA,
    DAWN,
    DAWN_STRENGTH,
    DEV,
    DEV_AT,
    DOOR_GAIN,
    EYE_CLOSES,
    FRIDGE_OPENS,
    FRIDGE_SHUTS,
    HOOK,
    JINGLE_GAIN,
    KEYS_AT,
    MUG_AT,
    NOOR,
    NOOR_AT,
    PARTS,
    POOL,
    POSES,
    REACHES,
    TAKES_KEYS,
)
from srstudio import SPEECH_MOUTH, Episode, foley, stick, stick_bed, stick_home, stick_office, stick_reel

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "more-tired",
        "R17",
        "More Tired — Stick 17",
        "Portrait stick-figure cartoon: two parents compete over who slept less until the baby cries, and both are "
        "suddenly asleep. Native vector animation; ElevenLabs voices and effects.",
        3129,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
ids = [take.id for take in t.takes]
LOOKS = {"dev": DEV, "noor": NOOR}
AT = {"dev": DEV_AT, "noor": NOOR_AT}
last = t.takes[-1]
AFTER_KEYS = ids[ids.index("06") + 1 :]


def part(who: str, take_id: str) -> list[tuple[float, str, stick.Face]]:
    """The rows of the last take up to this one that give ``who`` any; held from the shot's first frame."""
    rows = PARTS[who]
    if take_id in rows:
        return rows[take_id]
    earlier = [i for i in ids[: ids.index(take_id)] if i in rows]
    time, pose, face = rows[earlier[-1]][-1]
    return [(0, pose, face)]


def hand_of(pose: str) -> tuple[float, float]:
    return stick_office.on_figure(POSES[pose], at=DEV_AT, flip=True)["hand"]


def key_hand() -> tuple[float, float]:
    """Where the keys hang from his free hand once he has them."""
    x, y = POSES["keys"].hands[0]
    return DEV_AT[0] - x, DEV_AT[1] + y


def spans(rows, end: float) -> list[tuple[float, float, str]]:
    return [(r[0], rows[i + 1][0] if i + 1 < len(rows) else end, r[1]) for i, r in enumerate(rows)]


def performance(who: str, take) -> list[tuple[float, str, stick.Face]]:
    """Her rows as written, and in take 06's hold his trip to the fridge; in the last take his eye shuts after her
    line, and that is the end."""
    rows = list(part(who, take.id))
    if who == "dev" and take.id == "06":
        said = take.speech_duration
        face = rows[0][2]
        return [*rows, (said + REACHES, "reach", face), (said + TAKES_KEYS, "keys", face)]
    if who == "dev" and take.id == "13":
        return [
            *rows,
            (take.speech_duration + EYE_CLOSES, rows[0][1], stick.Face("closed", "flat", "flat", (0.0, 0.0))),
        ]
    return rows


def stage(take) -> None:
    g = ep.shot(shots, take)
    end = take.duration
    frame = stick.dolly(cv, g, CAMERA, CAMERA, end)
    stick_home.kitchen(cv, frame)
    if take.id == "06":
        said = take.speech_duration
        opened = stick_home.fridge_open(cv, frame)
        cv.gate(opened, [(said + FRIDGE_OPENS, said + FRIDGE_SHUTS)])
        keys = stick_home.key(cv, opened, *KEYS_AT, scale=1.6)
        cv.gate(keys, [(0.0, said + TAKES_KEYS)])
    blinks = (0.8,) if end > 1.4 else ()
    for who in ("noor", "dev"):
        speaks = dict(phones=take.phones, mood=take.mood) if take.actor == who else {}
        rows = performance(who, take)
        keys_ = [stick.RigKey(at, pose, face) for at, pose, face in rows]
        stick.rig(cv, frame, keys_, end, poses=POSES, look=LOOKS[who], at=AT[who], flip=who == "dev", blinks=blinks,
                  mouth=SPEECH_MOUTH, **speaks)  # fmt: skip
        if who == "dev":
            for start, stop, pose in spans(rows, end):
                cv.gate(stick_office.mug(cv, frame, *hand_of(pose)), [(start, stop)])
    stick_home.table(cv, frame)
    x, y = MUG_AT["seated"]
    stick_office.mug(cv, frame, x, y, colour="#d9694c")
    if take.id == "06":
        held = stick_home.key(cv, frame, *key_hand(), scale=1.6)
        cv.gate(held, [(take.speech_duration + TAKES_KEYS, end)])
    if take.id in AFTER_KEYS:
        stick_home.key(cv, frame, *key_hand(), scale=1.6)
    stick_bed.lights_low(cv, frame, tint=DAWN, strength=DAWN_STRENGTH, pool=POOL)


for take in t.takes:
    stage(take)

hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, t.takes[2].start)])
spoken = stick_reel.words(ep, t.takes)

trip = t.takes[ids.index("06")]
at = trip.start + trip.speech_duration
foley.write_bursts(ROOT / "assets" / "door.wav", [at + FRIDGE_OPENS], t.duration, foley.SCRAPE, seed=31291)
foley.write_bursts(ROOT / "assets" / "shut.wav", [at + FRIDGE_SHUTS], t.duration, foley.THUD, seed=31292)
foley.write_bursts(ROOT / "assets" / "jingle.wav", [at + TAKES_KEYS], t.duration, foley.PLATES, seed=31293)
ep.audio(
    take=stick_reel.placing({}),
    loudness="-14",
    extra=[
        ("door", "assets/door.wav", {"role": "effects", "gain": DOOR_GAIN}),
        ("shut", "assets/shut.wav", {"role": "effects", "gain": DOOR_GAIN}),
        ("jingle", "assets/jingle.wav", {"role": "effects", "gain": JINGLE_GAIN}),
    ],
)
stick_reel.close(ep, POSTS["more-tired"], hook, spoken)

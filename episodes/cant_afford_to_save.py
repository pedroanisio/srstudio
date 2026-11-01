#!/usr/bin/env python3
"""Stick — Can't Afford to Save, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 cant_afford_to_save_audio.py PROJECT --font DIR   # voices, timeline.json
    srstudio build cant-afford-to-save PROJECT                     # → PROJECT/cant-afford-to-save.scene.xml

On Black Friday one person in every couple saves so much money that the two of them cannot afford it. The study from
``stick.room``, out of focus, with the marks on the desk between them; plain ``stick_odds.carton`` boxes keep landing,
and Dev does not look at one of them. The effects are ``foley`` bursts.
"""

import os

from _common import project_root
from cant_afford_to_save_audio import (
    BOX_FROM,
    BOX_H,
    BOX_LANDS,
    BOX_W,
    CAMERAS,
    DEV_DOWN,
    DEV_GLAD,
    DEV_LOOK,
    DEV_PITY,
    DEV_PROUD,
    DEV_QUIET,
    DEV_READS,
    DEV_SAYS,
    DROP_FROM,
    FACES,
    FIRST_BOX,
    HEEL_FOOT,
    HEEL_SLIDES,
    HEEL_TAPS,
    HEEL_X,
    HOOK,
    LEFT,
    MARKS,
    NOOR_ASKS,
    NOOR_AT_BOX,
    NOOR_LOOK,
    NOOR_PLAIN,
    NOOR_UP,
    NOOR_WATCHES,
    OFF_LEFT,
    PHONE_UP,
    POSES,
    RECEIPT,
    RIGHT,
    SCALE,
    SECOND_LANDS,
    SECOND_SLIDES,
    SINKS,
    STACK_FOOT,
    STACK_X,
    THIRD_DROPS,
    THIRD_LANDS,
)
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, Episode, foley, look, signature, stick, stick_home, stick_odds, stick_reel

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "cant-afford-to-save"
ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        SLUG,
        "201",
        "Can't Afford to Save — Stick",
        "Portrait stick-figure cartoon: Black Friday week, and Dev has saved so much that he and Noor can no longer "
        "afford it. Native vector animation; ElevenLabs voices.",
        3421,
        bleed=True,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
said = {x.id: x for x in t.takes}
K = stick.RigKey
HOLD_AT = said["04"].speech_duration
PHONE_AT = said["06"].speech_duration


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def speaks(take, who: str) -> dict:
    return dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}


def box(parent, x: float, foot: float) -> None:
    stick_odds.carton(cv, parent, x, foot, w=BOX_W, h=BOX_H)


def first_box(parent, take) -> None:
    """The box at her feet: it slides in on the first frames and stays."""
    g = cv.group(parent, cv.uid("first-box"))
    if take.id == "01":
        cv.keys(g, "x", [(0.0, BOX_FROM - FIRST_BOX[0]), (BOX_LANDS, 0.0)], kind="cubic-out")
    box(g, *FIRST_BOX)


def stack(parent, take) -> None:
    """Two boxes behind him, once they have landed: one along the floor, one dropped on it."""
    if take.id < "04":
        return
    low = cv.group(parent, cv.uid("second-box"))
    high = cv.group(parent, cv.uid("third-box"))
    if take.id == "04":
        cv.gate(low, [(HOLD_AT + SECOND_SLIDES, take.duration)])
        cv.gate(high, [(HOLD_AT + THIRD_DROPS, take.duration)])
        cv.keys(
            low, "x", [(HOLD_AT + SECOND_SLIDES, OFF_LEFT - STACK_X), (HOLD_AT + SECOND_LANDS, 0.0)], kind="cubic-out"
        )
        cv.keys(
            high,
            "y",
            [(HOLD_AT + THIRD_DROPS, DROP_FROM - STACK_FOOT), (HOLD_AT + THIRD_LANDS, -BOX_H)],
            kind="cubic-in",
        )
    box(low, STACK_X, STACK_FOOT)
    box(high, STACK_X, STACK_FOOT if take.id == "04" else STACK_FOOT - BOX_H)


def heel_box(parent, take) -> None:
    """The last box, along the floor to his heel, in the hold."""
    if take.id < "06":
        return
    g = cv.group(parent, cv.uid("heel-box"))
    if take.id == "06":
        cv.gate(g, [(PHONE_AT + HEEL_SLIDES, take.duration)])
        cv.keys(g, "x", [(PHONE_AT + HEEL_SLIDES, OFF_LEFT - HEEL_X), (PHONE_AT + HEEL_TAPS, 0.0)], kind="cubic-in")
    box(g, HEEL_X, HEEL_FOOT)


def in_his_hands(parent, take, keys, end: float) -> None:
    """The receipt, from when he brings it out, hanging from his far hand; the phone in his near one in the hold."""
    if take.id < "05":
        return
    hand = stick.held(cv, parent, keys, end, poses=POSES, far=True, at=LEFT, scale=SCALE)
    unroll = (0.12, take.speech_duration - 0.1) if take.id == "05" else None
    stick_odds.receipt(cv, hand, 0.0, 6.0, RECEIPT / SCALE, unroll=unroll)
    if take.id == "05":
        return
    near = stick.held(cv, parent, keys, end, poses=POSES, at=LEFT, scale=SCALE)
    phone = cv.group(near, cv.uid("phone"))
    if take.id == "06":
        cv.gate(phone, [(PHONE_AT + PHONE_UP, end)])
    stick_home.handset(cv, phone, 0.0, -30.0, lit=True, scale=0.7)


def scene(parent, end: float, dev_keys, noor_keys, *, take) -> None:
    """The study out of focus, the boxes behind him, the two of them, what is in his hands, the box at her feet in
    front of everything, and the marks on the desk between them."""
    far = look.depth(cv, parent, "study-far", 5.0, overscan=True)
    stick.room(cv, far, marks=False)
    signature.cactus(cv, parent, *MARKS["cactus"], scale=0.42)
    signature.code(cv, parent, *MARKS["code"], 9, color="#4a3520")
    stack(parent, take)
    heel_box(parent, take)
    in_his_hands(parent, take, dev_keys, end)
    stick.rig(cv, parent, noor_keys, end, poses=POSES, look=NOOR_LOOK, at=RIGHT, scale=SCALE, flip=True,
              mouth=SPEECH_MOUTH, **speaks(take, "noor"))  # fmt: skip
    him = cv.group(parent, cv.uid("him"))
    if take.id == "06":  # the last box nudges him, and he does not look
        tap = PHONE_AT + HEEL_TAPS
        cv.keys(him, "x", [(tap - 0.01, 0.0), (tap + 0.06, 10.0), (tap + 0.18, 0.0)], hold=False, kind="sine-out")
    stick.rig(cv, him, dev_keys, end, poses=POSES, look=DEV_LOOK, at=LEFT, scale=SCALE, mouth=SPEECH_MOUTH,
              **speaks(take, "dev"))  # fmt: skip
    first_box(parent, take)


def split(g, take, line: float, near: str, wide: str, *dev_noor) -> None:
    """The line on ``near``, the hold after it on ``wide``, one drawing each."""
    him_near, her_near, him_wide, her_wide = dev_noor
    close = cv.group(g, cv.uid("line"))
    cv.gate(close, [(0, line)])
    scene(camera(close, near), take.duration, him_near, her_near, take=take)
    room = cv.group(g, cv.uid("hold"))
    cv.gate(room, [(line, take.duration)])
    scene(camera(room, wide), take.duration, him_wide, her_wide, take=take)


def stage(take) -> None:
    """Draw ``take``'s shot."""
    g = ep.shot(shots, take)
    end, line = take.duration, take.speech_duration
    if take.id == "01":
        her = [K(0, "stand", NOOR_AT_BOX), K(BOX_LANDS + 0.34, "stand", NOOR_ASKS)]
        scene(camera(g, "two"), end, [K(0, "stand", DEV_PROUD)], her, take=take)
    elif take.id == "02":
        him = [K(0, "stand", DEV_SAYS), K(0.14, "hands-hips", DEV_SAYS)]
        scene(camera(g, "two"), end, him, [K(0, "stand", NOOR_PLAIN)], take=take)
    elif take.id == "03":
        scene(camera(g, "noor"), end, [K(0, "hands-hips", DEV_PROUD)], [K(0, "stand", NOOR_PLAIN)], take=take)
    elif take.id == "04":
        him = [K(0, "hands-hips", DEV_PITY)]
        her = [K(0, "stand", NOOR_PLAIN), K(HOLD_AT + 0.1, "stand", NOOR_WATCHES), K(HOLD_AT + 0.5, "stand", NOOR_UP)]
        split(g, take, line, "dev", "two", him, her, him, her)
    elif take.id == "05":
        him = [K(0, "hands-hips", DEV_SAYS), K(0.1, "offers", DEV_GLAD)]
        scene(camera(g, "two"), end, him, [K(0, "stand", NOOR_UP), K(line, "hands-hips", NOOR_PLAIN)], take=take)
    elif take.id == "06":
        him = [K(0, "offers", DEV_GLAD), K(line + PHONE_UP, "phone", DEV_READS), K(line + SINKS, "sunk", DEV_DOWN)]
        her = [K(0, "hands-hips", NOOR_ASKS)]
        split(g, take, line, "noor", "hold", him, her, him, her)
    else:
        him = [K(0, "looks-up", DEV_QUIET)]
        scene(camera(g, "dev"), end, him, [K(0, "hands-hips", NOOR_PLAIN)], take=take)


def sound() -> list:
    """The first box and its stop, two more, the receipt, the last soft one, and the room in the long hold."""
    run = ROOT / "audio"
    fourth, fifth, sixth = said["04"], said["05"], said["06"]
    hold = fourth.start + HOLD_AT
    tap = sixth.start + PHONE_AT + HEEL_TAPS
    foley.write_bursts(run / "slides.wav", [0.04, hold + SECOND_SLIDES], t.duration, foley.SCRAPE, seed=3431)
    foley.write_bursts(run / "thumps.wav", [BOX_LANDS, hold + SECOND_LANDS, hold + THIRD_LANDS], t.duration, foley.THUD,
                       seed=3432)  # fmt: skip
    foley.write_bursts(run / "receipt.wav", [fifth.start + 0.1], t.duration, foley.SWISH, seed=3433)
    foley.write_bursts(run / "tap.wav", [tap], t.duration, foley.KNOCK, seed=3434)
    room = foley.Burst(sixth.end - sixth.start - PHONE_AT, 140.0, attack=0.2, decay=0.8, tone_hz=60.0, tone_end_hz=60.0,
                       tone=0.6)  # fmt: skip
    foley.write_bursts(run / "room.wav", [sixth.start + PHONE_AT], t.duration, room, seed=3435)
    return [
        ("slides", "audio/slides.wav", {"role": "effects", "gain": -12}),
        ("thumps", "audio/thumps.wav", {"role": "effects", "gain": -5}),
        ("receipt", "audio/receipt.wav", {"role": "effects", "gain": -16}),
        ("tap", "audio/tap.wav", {"role": "effects", "gain": -12}),
        ("room", "audio/room.wav", {"role": "ambience", "gain": -20}),
    ]


for take in t.takes:
    stage(take)

for shot, faces in (("two", tuple(FACES.values())), ("dev", (FACES["dev"],)), ("noor", (FACES["noor"],)),
                    ("hold", tuple(FACES.values()))):  # fmt: skip
    stick_reel.check_framing(CAMERAS[shot], faces=faces, marks=MARKS.values())
hook = stick.card(cv, cv.comp, HOOK, size=58, width=stick_reel.CARD_CLEAR)
cv.gate(hook, [(0, 3.0)])
spoken = stick_reel.words(ep, t.takes, sentences=True, hold=True, join=True, least=stick_reel.WORD_MIN)
ep.audio(take=stick_reel.placing({}), loudness="-14", extra=sound())
stick_reel.close(ep, POSTS[SLUG], hook, spoken, first_word=True)

#!/usr/bin/env python3
"""Stick — November First, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 november_first_audio.py PROJECT --font DIR   # voices, timeline.json
    srstudio build november-first PROJECT                                       # → PROJECT/november-first.scene.xml

In every couple one person starts Christmas the morning after Halloween, and the other one wakes up inside it. The set
is ``stick_home.kitchen`` out of focus with ``stick_holiday`` over it: Noor on a step stool with the star, Dev behind
the worktop with his mug, the pumpkin in its hat and the speaker in front of him. The speaker answers on screen,
never in a voice: its ring lights, a chime, the sleigh bells and a chip. The effects are ``foley`` bursts, and the
opening line is ``srstudio.opener``.
"""

import os
from functools import partial

from _common import project_root
from instagram_posts import POSTS
from november_first_audio import (
    CAMERAS,
    CHIP_AT,
    CHIP_BOX,
    CHIP_SECONDS,
    CHIP_TEXT,
    DEV_AT,
    DEV_AT_PUMPKIN,
    DEV_AT_SPEAKER,
    DEV_FROM,
    DEV_LOOK,
    DEV_NAMED,
    DEV_PLEADS,
    DEV_SAYS,
    DEV_X,
    FACES,
    INSERT_END,
    LIGHTS,
    LIGHTS_ON,
    MARKS,
    NAMED_AT,
    NOOR_AT,
    NOOR_BUSY,
    NOOR_GENTLE,
    NOOR_LOOK,
    NOOR_STOPS,
    NOOR_TURNED,
    NOOR_X,
    OPENER_TOP,
    OPENING_TEXT,
    POSES,
    PUMPKIN_X,
    SPEAKER_SCALE,
    SPEAKER_X,
    STRIDE,
    TOP,
    TREE_FOOT,
    TREE_SCALE,
    TREE_X,
    WALK_END,
    WORKTOP_X,
    jingles,
)
from srstudio import (
    SPEECH_MOUTH,
    Episode,
    foley,
    fonts,
    look,
    opener,
    signature,
    stick,
    stick_holiday,
    stick_home,
    stick_odds,
    stick_office,
    stick_reel,
)

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "november-first"
ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        SLUG,
        "210",
        "November First — Stick",
        "Portrait stick-figure cartoon: the morning after Halloween, Noor has decorated overnight, and every objection "
        "Dev has is already decided against him. Native vector animation; ElevenLabs voices.",
        3431,
        bleed=True,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
said = {x.id: x for x in t.takes}
K = stick.RigKey
STOOL_STEPS = 2


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def speaks(take, who: str) -> dict:
    return dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}


def dev(parent, keys, end: float, take) -> None:
    """Dev in his robe, the mug in his near hand, the hand drawn over it."""
    mug = stick.held(cv, parent, keys, end, poses=POSES, at=DEV_AT)
    stick_office.mug(cv, mug, 0.0, 0.0)
    stick.rig(cv, parent, keys, end, poses=POSES, look=DEV_LOOK, at=DEV_AT, mouth=SPEECH_MOUTH, **speaks(take, "dev"))
    stick_odds.robe(cv, parent, keys, end, POSES, at=DEV_AT)


def noor(parent, keys, end: float, take) -> None:
    """Noor on the stool, the star in her near hand."""
    stick.rig(cv, parent, keys, end, poses=POSES, look=NOOR_LOOK, at=NOOR_AT, mouth=SPEECH_MOUTH,
              **speaks(take, "noor"))  # fmt: skip
    hand = stick.held(cv, parent, keys, end, poses=POSES, at=NOOR_AT)
    stick_holiday.tree_star(cv, hand, 0.0, 0.0, scale=0.72)


def scene(parent, end: float, dev_keys, noor_keys, *, take, lights_on=None, glow=(), dev_from: float = 0.0) -> None:
    """The kitchen out of focus, the lights, the tree and the stool, the two of them, then the worktop over Dev's hips
    with the pumpkin, the speaker and the marks on it. An insert passes no keys: it is what Dev is looking at."""
    far = look.depth(cv, parent, "november-far", 5.0, overscan=True)
    stick_home.kitchen(cv, far, marks=False, safe=False)
    stick_holiday.light_string(cv, parent, *LIGHTS, end, on=lights_on)
    stick_holiday.tree(cv, parent, TREE_X, TREE_FOOT, scale=TREE_SCALE, star=False)
    stick_holiday.step_stool(cv, parent, NOOR_X, stick.STANDING["stand"].feet[0][1], steps=STOOL_STEPS)
    if noor_keys:
        noor(parent, noor_keys, end, take)
    if dev_keys:
        walker = cv.group(parent, cv.uid("dev"))
        if dev_from:
            cv.keys(walker, "x", [(0.0, dev_from - DEV_X), (WALK_END, 0.0)], kind="linear")
        dev(walker, dev_keys, end, take)
    stick_holiday.worktop(cv, parent, *WORKTOP_X, TOP)
    stick_holiday.pumpkin(cv, parent, PUMPKIN_X, TOP + 2.0)
    stick_holiday.smart_speaker(cv, parent, SPEAKER_X, TOP + 2.0, scale=SPEAKER_SCALE, glow=glow)
    signature.cactus(cv, parent, *MARKS["cactus"], scale=0.42)
    signature.code(cv, parent, *MARKS["code"], 9, color="#4a3520")


def split(g, take, cut: float, first, second) -> None:
    """``first`` until ``cut`` seconds into the shot, then ``second``."""
    a = cv.group(g, cv.uid("first"))
    cv.gate(a, [(0.0, cut)])
    first(a)
    b = cv.group(g, cv.uid("second"))
    cv.gate(b, [(cut, take.duration)])
    second(b)


def chip(parent, start: float) -> None:
    """The speaker's answer on screen from ``start`` for :data:`CHIP_SECONDS`: a white notice with the speaker's coral
    ring, the list as its title and what was done under it, over every shot and outside any camera."""
    left, top, right, bottom = CHIP_BOX
    w, h = right - left, bottom - top
    cx, cy = (left + right) / 2, (top + bottom) / 2
    g = cv.group(parent, cv.uid("speaker-chip"), x=cx, y=cy, anchorX=cx, anchorY=cy)
    cv.gate(g, [(start, start + CHIP_SECONDS)])
    cv.pop_in(g, start)
    cv.rect(g, left + 6, top + 9, w, h, cv.ink, radius=28, opacity=0.18)
    cv.rect(g, left, top, w, h, "#ffffff", cv.ink, 5, radius=28)
    ring = 50.0
    stick.oval(cv, g, left + 34, cy - ring / 2, ring, ring, stick_holiday.RING)
    stick.oval(cv, g, left + 34 + ring * 0.25, cy - ring / 4, ring / 2, ring / 2, "#ffffff")
    title, body = CHIP_TEXT
    text_left = round(left + 34 + ring + 26)
    room = round(right - text_left - 24)
    look.text(cv, g, title, text_left, round(top + 14), room, 58, 46, cv.ink, weight=700, align="start")
    look.text(cv, g, body, text_left, round(top + 72), room, 54, 40, stick_holiday.BODY, weight=700, align="start")


def fiddling(end: float, face) -> list:
    """Noor at the tip of the tree, her star hand going to it twice, not looking round."""
    return [K(0, "reaching", face), K(round(end * 0.35, 3), "fiddle", face), K(round(end * 0.7, 3), "reaching", face)]


def shuffle(face) -> list:
    """His shuffle in: a step every :data:`STRIDE`, then he stops."""
    steps = int(WALK_END / STRIDE)
    keys = [K(round(i * STRIDE, 4), "shuffle-b" if i % 2 else "shuffle-a", face) for i in range(steps)]
    return [*keys, K(WALK_END, "holding", face)]


HOME = [K(0, "reaching", NOOR_BUSY)]


def stage(take) -> None:
    """Draw ``take``'s shot."""
    g = ep.shot(shots, take)
    end, line = take.duration, take.speech_duration
    if take.id == "01":
        scene(camera(g, "wide"), end, shuffle(DEV_SAYS), fiddling(end, NOOR_BUSY), take=take,
              lights_on=LIGHTS_ON, dev_from=DEV_FROM)  # fmt: skip
    elif take.id == "02":
        scene(camera(g, "noor"), end, None, fiddling(end, NOOR_BUSY), take=take)  # Dev is off the frame: no mug sliver
    elif take.id == "03":
        cut = take.words[INSERT_END]["end"]
        split(g, take, cut,
              lambda a: scene(camera(a, "pumpkin"), end, None, None, take=take),
              lambda b: scene(camera(b, "dev"), end, [K(0, "looks", DEV_AT_PUMPKIN)], HOME, take=take))  # fmt: skip
    elif take.id == "04":
        scene(camera(g, "noor"), end, None, [K(0, "reaching", NOOR_GENTLE)], take=take)
    elif take.id == "05":
        # his request on him; then the insert on the speaker, its ring lit, as the chip comes up; then back on him,
        # named, while it is still up
        glow = ((line, line + CHIP_AT + CHIP_SECONDS),)
        split(g, take, line,
              lambda a: scene(camera(a, "dev"), end, [K(0, "looks", DEV_AT_SPEAKER)], HOME, take=take),
              lambda b: split(b, take, line + NAMED_AT,
                              lambda c: scene(camera(c, "speaker"), end, None, None, take=take, glow=glow),
                              lambda d: scene(camera(d, "dev"), end, [K(0, "looks", DEV_NAMED)], HOME, take=take,
                                              glow=glow)))  # fmt: skip
    elif take.id == "07":
        stops, turns = line + 0.3, line + 0.75
        her = [K(0, "reaching", NOOR_BUSY), K(line + 0.12, "fiddle", NOOR_BUSY), K(stops, "reaching", NOOR_STOPS),
               K(turns, "turned", NOOR_TURNED)]  # fmt: skip
        split(g, take, line,
              lambda a: scene(camera(a, "dev"), end, [K(0, "pleads", DEV_PLEADS)], HOME, take=take),
              lambda b: scene(camera(b, "close"), end, [K(0, "pleads", DEV_PLEADS)], her, take=take))  # fmt: skip
    else:
        scene(camera(g, "close"), end, [K(0, "pleads", DEV_PLEADS)], [K(0, "turned", NOOR_TURNED)], take=take)


def sound() -> list:
    """His slippers on the way in, the lights, the speaker's chime and the sleigh bells under its chip, stopped before
    his next line, and the room under the hold."""
    run = ROOT / "audio"
    up = answered()
    seven = said["07"]
    click = foley.Burst(0.03, 3600.0, attack=0.001, decay=0.3, tone_hz=2400.0, tone_end_hz=1800.0, tone=0.2)
    bell = foley.Burst(0.07, 9000.0, attack=0.001, decay=0.35, tone_hz=5200.0, tone_end_hz=5150.0, tone=0.55)
    hold_at = seven.start + seven.speech_duration
    steps = [i * STRIDE for i in range(int(WALK_END / STRIDE))]
    foley.write_bursts(run / "shuffle.wav", steps, t.duration, foley.SCRAPE, seed=5)
    foley.write_bursts(run / "lights.wav", [LIGHTS_ON, LIGHTS_ON + 0.16], t.duration, click)
    chime = foley.Burst(0.45, 5000.0, attack=0.004, decay=0.3, tone_hz=1100.0, tone_end_hz=1650.0, tone=0.85)
    foley.write_bursts(run / "chime.wav", [up], t.duration, chime)
    foley.write_bursts(run / "bells.wav", jingles(up, up + CHIP_SECONDS), t.duration, bell, seed=13)
    room = foley.Burst(seven.end - hold_at, 140.0, attack=0.2, decay=0.8, tone_hz=60.0, tone_end_hz=60.0, tone=0.6)
    foley.write_bursts(run / "room.wav", [hold_at], t.duration, room)
    return [
        ("shuffle", "audio/shuffle.wav", {"role": "effects", "gain": -16}),
        ("lights", "audio/lights.wav", {"role": "effects", "gain": -9}),
        ("chime", "audio/chime.wav", {"role": "effects", "gain": -14}),
        ("bells", "audio/bells.wav", {"role": "effects", "gain": -20}),
        ("room", "audio/room.wav", {"role": "ambience", "gain": -20}),
    ]


def answered() -> float:
    """When the speaker's chip comes up, on the episode clock: :data:`CHIP_AT` after his request ends."""
    asked = said["05"]
    return asked.start + asked.speech_duration + CHIP_AT


for take in t.takes:
    stage(take)
chip(cv.comp, answered())

for shot, faces in (("wide", tuple(FACES.values())), ("noor", (FACES["noor"],)), ("close", (FACES["noor"],)),
                    ("dev", (FACES["dev"],))):  # fmt: skip
    stick_reel.check_framing(CAMERAS[shot], faces=faces)
for shot in ("wide", "dev", "pumpkin", "speaker"):
    stick_reel.check_framing(CAMERAS[shot], marks=MARKS.values())
first = t.takes[0]
pill = opener.draw(
    cv,
    cv.comp,
    OPENING_TEXT,
    first.start + first.speech_duration,
    measure=partial(fonts.text_width, (ep.root / str(ep.spec.font)).read_bytes()),
    top=OPENER_TOP,
    names=("dev", "noor"),
)
spoken = stick_reel.words(ep, t.takes, sentences=True, hold=True, join=True, asks=True, least=stick_reel.WORD_MIN)
ep.audio(take=stick_reel.placing({}), loudness="-14", extra=sound())
stick_reel.close(ep, POSTS[SLUG], pill, spoken, first_word=True)

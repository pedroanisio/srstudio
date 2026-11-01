#!/usr/bin/env python3
"""Stick — Extra Hour, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 extra_hour_audio.py PROJECT --font DIR   # voices, timeline.json
    srstudio build extra-hour PROJECT                                       # → PROJECT/extra-hour.scene.xml

The clocks went back and Dev has spent the one free hour on everything Noor can name. The set is ``stick_table`` in the
kitchen, with no safe and no calendar: she stands, he sits, and the plate, the keys and the phone come to the table one
at a time. The effects are ``foley`` bursts.
"""

import os

from _common import project_root
from extra_hour_audio import (
    CAMERAS,
    DEV_AT_KEYS,
    DEV_AT_PHONE,
    DEV_AT_PLATE,
    DEV_CALM,
    DEV_GLAD,
    DEV_LOOK,
    DEV_NODS,
    DEV_SAYS,
    DEV_SMUG,
    DEV_SURE,
    FACES,
    HOOK,
    KEY_SCALE,
    KEY_X,
    LEFT,
    LOOK_KEYS,
    LOOK_PHONE,
    LOOK_PLATE,
    MARKS,
    NOD,
    NOD_END,
    NOD_UP,
    NOOR_ASKS,
    NOOR_DOWN,
    NOOR_LOOK,
    NOOR_PLAIN,
    NOOR_WINDOW,
    PHONE_FROM,
    PHONE_RUN,
    PHONE_SCALE,
    PHONE_X,
    PLATE_DOWN,
    PLATE_HEAP,
    PLATE_SCALE,
    PLATE_X,
    POSES,
    RIGHT,
    TOP,
)
from instagram_posts import POSTS
from srstudio import (
    SPEECH_MOUTH,
    Episode,
    foley,
    look,
    signature,
    stick,
    stick_home,
    stick_odds,
    stick_office,
    stick_reel,
)
from srstudio import stick_table as st

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "extra-hour",
        "197",
        "Extra Hour — Stick",
        "Portrait stick-figure cartoon: the clocks went back, and Dev has spent the one free hour on everything Noor "
        "can name. Native vector animation; ElevenLabs voices.",
        3405,
        bleed=True,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
said = {x.id: x for x in t.takes}
K = stick.RigKey
PHONE_AT = 0.12  # into "Your mother?": her hand starts the phone along the table
KEY_DOWN = 0.2  # into "The car?": the keys land
ON_TABLE = {"plate": "01", "key": "03", "phone": "05"}  # the take each thing arrives in


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def speaks(take, who: str) -> dict:
    return dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}


def plate(parent, x: float, y: float) -> None:
    stick_odds.plate(cv, parent, x, y, heap=PLATE_HEAP, scale=PLATE_SCALE)


def keys(parent, x: float, y: float) -> None:
    """Two keys on a ring, the way a car's are left on a table, facing back towards her."""
    first = cv.group(parent, cv.uid("key"), x=x, y=y, scaleX=-1)
    stick_home.key(cv, first, 0.0, 0.0, scale=KEY_SCALE)
    second = cv.group(first, cv.uid("key"), rotation=-24.0)
    stick_home.key(cv, second, 0.0, 0.0, scale=KEY_SCALE * 0.9)


def phone(parent, x: float, y: float):
    """The phone on its long edge, screen to the viewer, its middle at ``x, y``."""
    g = cv.group(parent, cv.uid("phone"), x=x, y=y, rotation=-90.0)
    stick_home.handset(cv, g, 0.0, 0.0, lit=True, scale=PHONE_SCALE)
    return g


def table_things(parent, take, end: float) -> None:
    """What is on the table by ``take``, in the order it came."""
    if take.id >= ON_TABLE["plate"]:
        g = cv.group(parent, cv.uid("plate-down"))
        plate(g, PLATE_X, TOP - 4.0)  # its foot clear of the table, drawn over it
        if take.id == ON_TABLE["plate"]:
            cv.gate(g, [(PLATE_DOWN, end)])
    if take.id >= ON_TABLE["phone"]:
        y = TOP - 37 * PHONE_SCALE
        if take.id == ON_TABLE["phone"]:
            g = phone(parent, PHONE_FROM, y)
            cv.keys(g, "x", [(PHONE_AT, PHONE_FROM), (PHONE_AT + PHONE_RUN, PHONE_X)], kind="cubic-out")
        else:
            phone(parent, PHONE_X, y)


def keys_down(parent, take, end: float) -> None:
    """The keys, once she has put them down: in front of her legs, which stand behind that end of the table."""
    if take.id >= ON_TABLE["key"]:
        g = cv.group(parent, cv.uid("keys-down"))
        keys(g, KEY_X, TOP - 16 * KEY_SCALE)
        if take.id == ON_TABLE["key"]:
            cv.gate(g, [(KEY_DOWN, end)])


def in_hand(parent, keys_: list, end: float, draw, until: float) -> None:
    """What Noor's near hand carries until it lands at ``until``."""
    hand = stick.held(cv, parent, keys_, end, poses=POSES, at=RIGHT, flip=True)
    g = cv.group(hand, cv.uid("carried"))
    cv.gate(g, [(0, until)])
    draw(g)


def scene(parent, end: float, dev_keys, noor_keys, *, take) -> None:
    """The kitchen out of focus, what is on the table and what is in a hand, then the two of them, so every hand shows
    on what it holds, the table over their knees, the keys, and the marks on top of everything."""
    far = look.depth(cv, parent, "extra-far", 5.0, overscan=True)
    stick_home.kitchen(cv, far, marks=False, safe=False)
    st.seats(cv, parent)
    table_things(parent, take, end)
    mug = stick.held(cv, parent, dev_keys, end, poses=POSES, at=LEFT)
    stick_office.mug(cv, mug, 0.0, 0.0)
    if take.id == "01":
        in_hand(parent, noor_keys, end, lambda g: plate(g, 0.0, 30.0), PLATE_DOWN)
    elif take.id == "03":
        in_hand(parent, noor_keys, end, lambda g: keys(g, 0.0, 14.0), KEY_DOWN)
    stick.rig(cv, parent, noor_keys, end, poses=POSES, look=NOOR_LOOK, at=RIGHT, flip=True, mouth=SPEECH_MOUTH,
              **speaks(take, "noor"))  # fmt: skip
    stick.rig(cv, parent, dev_keys, end, poses=POSES, look=DEV_LOOK, at=LEFT, mouth=SPEECH_MOUTH, **speaks(take, "dev"))
    st.table(cv, parent)
    keys_down(parent, take, end)
    signature.cactus(cv, parent, *MARKS["cactus"], scale=0.42)
    signature.code(cv, parent, *MARKS["code"], 9, color="#4a3520")


def stage(take) -> None:
    """Draw ``take``'s shot."""
    g = ep.shot(shots, take)
    end, line = take.duration, take.speech_duration
    if take.id == "01":
        her = [K(0, "plate-up", NOOR_DOWN), K(PLATE_DOWN, "plate", NOOR_ASKS)]
        scene(camera(g, "two"), end, [K(0, "sip", DEV_SMUG)], her, take=take)
    elif take.id == "02":
        her = [K(0, "plate", NOOR_PLAIN)]
        scene(camera(g, "two"), end, [K(0, "cradle", DEV_SAYS)], her, take=take)
    elif take.id == "03":
        her = [K(0, "key-up", NOOR_DOWN), K(KEY_DOWN, "key", NOOR_ASKS)]
        scene(camera(g, "two"), end, [K(0, "sip", DEV_SMUG)], her, take=take)
    elif take.id == "04":
        scene(camera(g, "two"), end, [K(0, "cradle", DEV_SAYS)], [K(0, "key", NOOR_PLAIN)], take=take)
    elif take.id == "05":
        her = [K(0, "flick-a", NOOR_DOWN), K(PHONE_AT + 0.08, "flick-b", NOOR_ASKS), K(line, "stands", NOOR_PLAIN)]
        scene(camera(g, "two"), end, [K(0, "sip", DEV_SMUG)], her, take=take)
    elif take.id == "06":
        him = [K(0, "cradle", DEV_SAYS), K(said["06"].words[1]["end"] + 0.1, "spread", DEV_GLAD)]
        scene(camera(g, "dev"), end, him, [K(0, "stands", NOOR_PLAIN)], take=take)
    elif take.id == "07":
        her = [K(0, "stands", NOOR_WINDOW), K(0.3, "stands", NOOR_PLAIN)]
        scene(camera(g, "noor"), end, [K(0, "spread", DEV_GLAD)], her, take=take)
    elif take.id == "08":
        scene(camera(g, "dev"), end, [K(0, "cradle", DEV_SURE)], [K(0, "stands", NOOR_PLAIN)], take=take)
    elif take.id == "09":
        charge(g, take, end, line)
    else:
        last(g, take, end)


def charge(g, take, end: float, line: float) -> None:
    """Her count on her, from the table to him; then the hold: he goes over the plate, the keys and the phone, and
    nods."""
    near = cv.group(g, cv.uid("her-count"))
    cv.gate(near, [(0, line)])
    her = [K(0, "stands", NOOR_DOWN), K(line * 0.4, "stands", NOOR_PLAIN)]
    scene(camera(near, "noor"), end, [K(0, "cradle", DEV_SURE)], her, take=take)
    wide = cv.group(g, cv.uid("his-look"))
    cv.gate(wide, [(line, end)])
    him = [K(0, "cradle", DEV_SURE)]
    him += [K(line + LOOK_PLATE, "plate-over", DEV_AT_PLATE), K(line + LOOK_KEYS, "keys-over", DEV_AT_KEYS)]
    him += [K(line + LOOK_PHONE, "phone-over", DEV_AT_PHONE), K(line + NOD, "nod", DEV_NODS)]
    him += [K(line + NOD_UP, "phone-over", DEV_NODS), K(line + NOD_END, "cradle", DEV_CALM)]
    scene(camera(wide, "over"), end, him, [K(0, "stands", NOOR_PLAIN)], take=take)


def landing(take) -> float:
    """Where in his last word the mug lands, on the shot's clock."""
    return take.words[-1]["end"] - 0.06


def last(g, take, end: float) -> None:
    """Close on Dev: the mug comes down through the line and lands on its last word, and the reel cuts on it."""
    land = landing(take)
    him = [K(0, "mug-up", DEV_CALM), K(land - 0.3, "mug-low", DEV_CALM), K(land, "mug-down", DEV_SAYS)]
    scene(camera(g, "close"), end, him, [K(0, "stands", NOOR_PLAIN)], take=take)


def sound() -> list:
    """The plate, the keys, the phone along the table and its stop, the room under the hold, and the mug."""
    run = ROOT / "audio"
    third, fifth, ninth, tenth = said["03"], said["05"], said["09"], said["10"]
    keys_at = third.start + KEY_DOWN
    phone_at = fifth.start + PHONE_AT
    hold_at = ninth.start + ninth.speech_duration
    foley.write_bursts(run / "plate.wav", [PLATE_DOWN - 0.02], t.duration, foley.PLATES)
    foley.write_bursts(run / "keys.wav", [keys_at, keys_at + 0.05, keys_at + 0.11], t.duration, foley.CLINK)
    foley.write_bursts(run / "slide.wav", [phone_at + i * 0.07 for i in range(5)], t.duration, foley.SCRAPE, seed=9)
    room = foley.Burst(ninth.end - hold_at, 140.0, attack=0.2, decay=0.8, tone_hz=60.0, tone_end_hz=60.0, tone=0.6)
    foley.write_bursts(run / "room.wav", [hold_at], t.duration, room)
    foley.write_bursts(run / "mug.wav", [tenth.start + landing(tenth) - 0.02], t.duration, foley.KNOCK)
    return [
        ("plate", "audio/plate.wav", {"role": "effects", "gain": -10}),
        ("keys", "audio/keys.wav", {"role": "effects", "gain": -12}),
        ("slide", "audio/slide.wav", {"role": "effects", "gain": -14}),
        ("room", "audio/room.wav", {"role": "ambience", "gain": -20}),
        ("mug", "audio/mug.wav", {"role": "effects", "gain": -6}),
    ]


for take in t.takes:
    stage(take)

for shot, faces in (("two", (FACES["dev"],)), ("dev", (FACES["dev"],)), ("noor", tuple(FACES.values())),
                    ("over", tuple(FACES.values())), ("close", (FACES["dev"],))):  # fmt: skip
    stick_reel.check_framing(CAMERAS[shot], faces=faces, marks=MARKS.values())
hook = stick.card(cv, cv.comp, HOOK, size=58, width=stick_reel.CARD_CLEAR)
cv.gate(hook, [(0, 3.0)])
spoken = stick_reel.words(ep, t.takes, sentences=True, hold=True, join=True, least=stick_reel.WORD_MIN)
ep.audio(take=stick_reel.placing({}), loudness="-14", extra=sound())
stick_reel.close(ep, POSTS["extra-hour"], hook, spoken, first_word=True)

#!/usr/bin/env python3
"""Nobody Died, built with srstudio: a final interview, and a mother who never says why she is calling.

    srstudio record nobody-died PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build nobody-died PROJECT    # → PROJECT/nobody-died.scene.xml

Milo at his desk in his interview tie, a manager on the laptop. "So, tell me about yourself." The phone buzzes itself
along the desk: MOM. "It's just my mom." He turns it over. "I've always admired..." He lifts a corner: CALL ME. Under
it, DON'T WORRY, and the color goes out of him. "Nobody writes that if it's fine." The phone turns itself over: MOM (9).
"Take it. Family first." "Mom? What happened? Who died?" Rosa at a cupboard under a bare bulb, a lamp under her arm.
"Nobody died. Do you want a lamp?"

The manager is heard down the laptop's speaker. No music: the foley is synthesized here. It declares no engine safe
area, so captions are placed inside x 80–920 by hand.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from nobody_died_audio import INTERVIEW
from srstudio import (
    CAFE,
    Episode,
    EpisodeSpec,
    cast,
    cutout_arm,
    cutout_call,
    cutout_counter,
    cutout_home,
    cutout_key,
    cutout_locate,
    cutout_store,
    foley,
    props,
    signature,
)
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="nobody-died",
        title=INTERVIEW.title,
        description="Job-hunting comedy: a final interview, a mother who writes CALL ME and nothing else, and the "
        "lamp it was all about. Native vector animation; ElevenLabs dialogue, synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=3423,
        background="#E4DBC4",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        bleed=True,
    )
)
t, cv = ep.t, ep.cv
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
FACE_DOWN, PEEK, WORRY, TURN = (float(t.meta[k]) for k in ("face_down", "peek", "worry", "turn"))

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))
AT_DESK = spans["milo"] + spans["close"]
CLOSES = spans["close"]
TILES = spans["tile"]
PHONE_SHOT = spans["phone"][0]
TURN_SHOT = spans["turns"][0]
ROSA_SHOT = spans["rosa"][0]

MILO = (415.0, 560.0, 2.15)
PALE = CLOSES[0][0]  # the color goes out of him on the cut after DON'T WORRY, and does not come back
ASHEN = "#E4DCCB"
COLLAR = (
    "M-34 118 L0 160 L34 118 L46 150 L0 186 L-46 150Z"  # over his hoodie: dressed for the interview, for the desk up
)
TIE = "M-11 158 L11 158 L6 176 L18 262 L0 284 L-18 262 L-6 176Z"
WARM = [s for s in AT_DESK if s[1] <= PALE]
COLD = [s for s in AT_DESK if s[0] >= PALE]
PHONE_AT = (222.0, 1195.0)
CREEP = 34.0  # how far along the desk the first two buzzes walk it
LAPTOP_OFFSET = (-205.0, -180.0)  # the laptop's art is drawn at the frame's right edge
BUZZES = [
    (0.10, 0.75),
    (L[1].start, L[1].start + 0.6),
    (L[5].start + 0.1, L[5].start + 0.8),
    (PEEK + 0.0, PEEK + 0.28),
]  # fmt: skip
LIT = [(0.0, FACE_DOWN), (TURN, DURATION)]  # screen up until he turns it over, and again once it turns itself
OVER = (PHONE_AT[0] + CREEP + 10, PHONE_AT[1] - 12)  # his hand on the phone
HANDS = (
    (
        (0.0, 300.0, 1110.0),
        (FACE_DOWN - 0.3, 300.0, 1110.0),
        (FACE_DOWN, *OVER),
        (FACE_DOWN + 0.45, *OVER),
        (L[4].start + 0.1, 395.0, 1095.0),
        (L[5].start, 395.0, 1095.0),
        (L[5].start + 0.35, *OVER),
        (L[6].start - 0.2, *OVER),
        (L[6].start, 310.0, 1110.0),
        (L[10].start - 0.1, 310.0, 1110.0),
        (L[10].start + 0.1, 400.0, 1125.0),
    ),
    (
        (0.0, 540.0, 1120.0),
        (L[4].start + 0.1, 470.0, 1095.0),
        (L[5].start, 470.0, 1095.0),
        (L[6].start, 540.0, 1120.0),
        (L[10].start, 540.0, 1120.0),
        (L[10].start + 0.1, 590.0, 1135.0),
    ),
)  # his hands in the set's units: the desk is drawn over him, so they lie on it from the front


foley.write_buzz(
    ROOT / "assets" / "buzz.wav",
    [a for a, _ in BUZZES] + [WORRY, TURN_SHOT[0], TURN_SHOT[0] + 0.3, TURN],
    DURATION,
    seed=3424,
)
foley.write_bursts(ROOT / "assets" / "clack.wav", [FACE_DOWN + 0.28], DURATION, foley.KNOCK, seed=3425)
foley.write_bursts(ROOT / "assets" / "pen.wav", [TILES[2][0] + 0.5], DURATION, foley.CLACK, seed=3426)
BREATH = foley.Burst(0.34, 2600.0, attack=0.12, decay=0.3)
foley.write_bursts(ROOT / "assets" / "breath.wav", [WORRY + 0.12], DURATION, BREATH, seed=3427)
RING = replace(foley.BELL, seconds=0.2)  # picked up before it finishes
SHELF = replace(foley.CREAK, seconds=0.9)
foley.write_bursts(ROOT / "assets" / "ring.wav", [L[10].start - 0.32], DURATION, RING, seed=3428)
foley.write_bursts(ROOT / "assets" / "creak.wav", [ROSA_SHOT[0] + 0.15], DURATION, SHELF, seed=3429)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("buzz", "assets/buzz.wav", {"role": "effects", "gain": -16}),
        ("clack", "assets/clack.wav", {"role": "effects", "gain": -18}),
        ("pen", "assets/pen.wav", {"role": "effects", "gain": -14}),
        ("breath", "assets/breath.wav", {"role": "effects", "gain": -16}),
        ("ring", "assets/ring.wav", {"role": "effects", "gain": -18}),
        ("creak", "assets/creak.wav", {"role": "effects", "gain": -14}),
    ],
    loudness="-14",
)


def milo(g):
    def one(tag, shots, skin):
        group = cv.group(g, f"milo-{tag}-shots")
        cv.gate(group, shots)
        who = cast.Customer(cv, tag=f"milo-{tag}")
        ep.perform(
            who,
            group,
            *MILO,
            mouth=ep.mouth("milo"),
            blinks=[(1.4, 1.54), (L[3].end + 0.1, L[3].end + 0.24), (L[8].start - 0.2, L[8].start - 0.06)],
            nods=[(0, 0), (L[1].start, 2), (L[3].start, 2), (L[3].start + 0.2, -2), (L[5].start, -2), (L[5].end, 4)],
            free_arms=("left", "right"),
            skin=skin,
        )
        looks = [(0, 14), (L[5].start + 0.2, 14), (L[5].start + 0.5, -6), (L[6].start, -6), (L[8].start, 0)]
        cv.keys(who.eyes, "x", looks, hold=False)
        cv.path(who.group, COLLAR, "#F6F1E6", cv.ink, 3)
        cv.path(who.group, TIE, "#7A2F35", cv.ink, 3)

    one("warm", WARM, "#F1D0AA")
    one("ashen", COLD, ASHEN)


def on_desk(g):
    creeping = cv.group(g, "phone-creeps")
    second = L[1].start
    walked = [(0.0, 0.0), (0.75, CREEP * 0.5), (second, CREEP * 0.5), (second + 0.6, CREEP)]
    cv.keys(creeping, "x", walked, hold=False)
    speaking = [(L[10].start, L[10].end)]
    cutout_locate.table_phone(
        cv, creeping, *PHONE_AT, rings=BUZZES[:3], lit=LIT, speaker=speaking, scale=1.4, id="milos-phone"
    )
    name = cv.group(creeping, "phone-name")
    cv.gate(name, LIT[:1])
    cv.text(name, "phone-mom", "MOM", PHONE_AT[0] - 70, PHONE_AT[1] - 20, 140, 40, 32, "#16202B")
    laptop = cv.group(g, "milos-laptop", x=LAPTOP_OFFSET[0], y=LAPTOP_OFFSET[1])
    props.laptop(cv, laptop)
    x, y, size = MILO
    for tag, skin, shots in (("warm", "#F1D0AA", WARM), ("ashen", ASHEN, COLD)):
        hands = cv.group(g, f"milo-hands-{tag}")
        cv.gate(hands, shots)
        for side, shoulder, track in zip(("left", "right"), ((-72, 143), (73, 144)), HANDS, strict=True):
            root = (x + shoulder[0] * size, y + shoulder[1] * size)
            bend = -1 if side == "left" else 1
            cutout_arm.arm(cv, hands, f"milo-{tag}-{side}", root, list(track), upper=175, fore=175, bend=bend,
                           width=10.0, hand=78.0, skin=skin)  # fmt: skip


home = cutout_home.home_study(cv, ep.comp, behind_desk=milo, on_desk=on_desk, shots=AT_DESK)
FRAMED = (1.08, -30.0, -60.0)
CLOSE = (1.42, -130.0, -345.0)  # held: a push rescales the blurred room each frame, and that ran the GPU out of memory
SET = (-300.0, -300.0, 1380.0, 2360.0)
moves = [(0.0, FRAMED)]
for a, b in CLOSES:
    moves += [(a, FRAMED), (a, CLOSE), (b, CLOSE), (b, FRAMED)]
cutout_key.camera(cv, home, moves, box=SET)


def sitter(g):
    who = cast.Manager(cv, tag="manager-tile")
    ep.perform(
        who,
        g,
        470.0,
        380.0,
        2.3,
        mouth=ep.mouth("manager"),
        blinks=[(TILES[0][0] + 0.5, TILES[0][0] + 0.64), (TILES[1][0] + 0.3, TILES[1][0] + 0.44)],
        nods=[(0, 0), (TILES[1][0], 3), (TILES[2][0], 3), (TILES[2][0] + 0.3, -2)],
        free_arms=("right",),
    )
    writes, stops = TILES[1][0], TILES[2][0] + 0.28
    near = (120.0, 210.0)
    track = [
        (0.0, 118.0, 300.0),
        (writes, 118.0, 300.0),
        (writes + 0.2, *near),
        (writes + 0.4, 136.0, 214.0),
        (writes + 0.6, *near),
        (stops, *near),
        (stops + 0.25, 130.0, 300.0),
    ]
    arm = cutout_arm.arm(cv, who.group, "manager-pen", (67, 148), track, upper=96, fore=96, bend=-1, hand=30.0)
    cv.path(arm.grip, "M-3 -38 L3 -38 L3 22 L0 34 L-3 22Z", "#2B3A55", cv.ink, 2)


tile = cv.group(ep.comp, "the-tile")
cv.gate(tile, TILES)
cv.rect(tile, 0, 0, 1080, 1920, "#22262C")
cutout_call.video_tile(cv, tile, inside=sitter, plate="HIRING MANAGER")
signature.code(cv, tile, 980, 1320, 12, color="#5C625D", align="end")
signature.cactus(cv, tile, 880, 1070, 0.5)

corner = cv.group(ep.comp, "phone-peek")
cv.gate(corner, [PHONE_SHOT])
cutout_home.desk_top(cv, corner)
signature.cactus(cv, corner, 110, 620, 0.8)
signature.code(cv, corner, 1020, 1560, 12, color="#F3DCA4", align="end")


def peeked(group):
    lines = [(PEEK, "CALL ME"), (WORRY, "DON'T WORRY")]
    buzz = [(WORRY - 0.03, WORRY + 0.3)]
    cutout_call.desk_phone(cv, group, 0, -420, scale=0.92, title="MOM", lines=lines, buzzes=buzz)


cutout_counter.reaching_hand(cv, corner, 520, 1200, scale=1.1, rotation=8, grip=200, holds=peeked, id="milo-lifts-it")

turning = cv.group(ep.comp, "phone-turns")
cv.gate(turning, [TURN_SHOT])
cutout_home.desk_top(cv, turning, id="study-desk-top-2")
signature.cactus(cv, turning, 110, 620, 0.8)
signature.code(cv, turning, 1020, 1560, 12, color="#F3DCA4", align="end")
SHAKES = [(TURN_SHOT[0], TURN + 0.1), (TURN + 0.24, TURN + 0.5)]
cutout_call.desk_phone(cv, turning, 540, 880, title="MOM (9)", turns=TURN, buzzes=SHAKES, id="turned-phone")


ROSA = (470.0, 800.0, 1.45)
ROOM_FRAME = (1.2, -108.0, -110.0)
ROOM_BOX = (-700.0, -700.0, 1780.0, 2620.0)
EAR = (-114.0, 6.0)
SHIFT = L[11].start + 0.1


def rosa(g):
    who = cast.Rosa(cv, tag="rosa-cupboard")
    ep.perform(
        who,
        g,
        *ROSA,
        mouth=ep.mouth("rosa"),
        blinks=[(ROSA_SHOT[0] + 0.4, ROSA_SHOT[0] + 0.54), (L[11].start - 0.2, L[11].start - 0.06)],
        nods=[(0, 0), (ROSA_SHOT[0], 0), (ROSA_SHOT[0] + 0.5, 6), (L[11].start - 0.1, 6), (L[11].start + 0.2, 0)],
        free_arms=("left", "right"),
        legs="standing",
    )
    cv.keys(who.eyes, "x", [(0, 0), (ROSA_SHOT[0] + 0.5, 14), (L[11].start, 14), (L[11].start + 0.1, 0)], hold=False)
    arm = cutout_arm.arm(cv, who.group, "rosa-phone-arm", (-72, 143), [(0.0, *EAR)], upper=96, fore=96, bend=1)
    cutout_locate.held_phone(cv, arm.grip, 8, -18, scale=0.6, id="rosa-phone")
    carried = cv.group(who.group, "rosa-lamp", x=118, y=232, rotation=24)
    cv.keys(carried, "y", [(0.0, 232.0), (SHIFT, 232.0), (SHIFT + 0.16, 214.0), (SHIFT + 0.3, 224.0)], hold=False)
    cutout_store.table_lamp(cv, carried, 0, 120, scale=0.8)
    cutout_arm.arm(cv, who.group, "rosa-lamp-arm", (67, 148), [(0.0, 104.0, 286.0)], upper=96, fore=96, bend=1)


cupboard = cutout_counter.back_room(cv, ep.comp, in_room=rosa, shots=[ROSA_SHOT], push=(0.0, 0.01), opens=0.0)
cutout_key.camera(cv, cupboard, [(0.0, ROOM_FRAME)], box=ROOM_BOX)

hook = cutout_key.key_line(cv, ep.comp, "FINAL INTERVIEW", 0.0, 3.0, top=250, font=(ROOT / ep.spec.font).read_bytes())
spoken = ep.captions(ep.spoken_captions(min_seconds=0.84), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(hook, *spoken)
ep.markers(extra=[("marker-peek", PEEK, "Call me"), ("marker-lamp", L[11].start, "The lamp")])
ep.instagram(POSTS["nobody-died"])
ep.finish()

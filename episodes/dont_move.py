#!/usr/bin/env python3
"""Don't Move, built with srstudio: a thumb, a heart, a casserole from 2016.

    srstudio record dont-move PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build dont-move PROJECT    # → PROJECT/dont-move.scene.xml

From the first frame the camera is pulling back off Ava's hand on Milo's wrist. "Don't. Move. Your thumb." "I'm in my
ex's new girlfriend's mother's photos." "How far back?" "2016." She takes off her watch and moves her cup. On the phone:
a dish, an empty heart, his thumb a hair above it, ticking. "Don't breathe on it." Off, a cup smashes: the thumb
twitches, the heart goes red. Two seconds of nothing. "It's red." She stands and puts on her coat. "I never knew you."
Diane's message slides in. She stops at the door; his thumbs are moving. "Milo. No." "...What do I bring?"

Arm B of the ``sp-hook_motion`` test: the frame moves from its first frame. No music: the foley is synthesized here. It
declares no engine safe area, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from dont_move_audio import INTERVIEW, MESSAGE_SHIFT
from instagram_posts import POSTS
from srstudio import CAFE, Episode, EpisodeSpec, cast, cutout_handed, cutout_office, foley, locations, props, signature
from srstudio import interview as iv_audio
from srstudio.cutout_reach import hand_at, reach

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="dont-move",
        title=INTERVIEW.title,
        description="Own-worst-enemy comedy: a man six years deep in a stranger's photos, a friend talking him out, "
        "and a heart that goes red. Native vector animation; ElevenLabs dialogue, synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=31252,
        background="#D4B390",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
t, cv = ep.t, ep.cv
LET_GO, CRASH, STANDS = float(t.meta["let_go"]), float(t.meta["crash"]), float(t.meta["stands"])
TOAST, DOOR = float(t.meta["toast"]), float(t.meta["door"])
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
AVA_AT = (245, 800, 1.5)
MITTS_IN = 48  # the photo's mitts stay inside the phone's screen
MILO_AT = (810, 800, 1.5)
UP = 545  # Ava's y on her feet
AT_DOOR = (138, 650, 1.2)  # further off, and smaller
TABLE_Y = 1180
CLAMP = (626, 1132)
WRIST = (92, 1118)  # her own: the watch
ON_TABLE = (432, 1262)
CUP = (330, 1252)
CUP_AWAY = (150, 1252)
RESTS = (350, 1216)
MARK_CACTUS = (76, 1908)  # the table under the phone, left of the thumb
MARK_CODE = (128, 1872)

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))
PHONE_1, PHONE_2 = spans["phone"]

TAKE = LET_GO + 0.40
PUT = TAKE + 0.45
AT_CUP = PUT + 0.22
PUSHED = AT_CUP + 0.32
tremble = [
    (k * 0.13, CLAMP[0] + (3 if k % 2 else -3), CLAMP[1] + (2 if k % 3 else -2)) for k in range(int(LET_GO / 0.13))
]
HAND = [
    *tremble,
    (LET_GO, *CLAMP),
    (TAKE, WRIST[0] + 22, WRIST[1]),
    (PUT, ON_TABLE[0], ON_TABLE[1] - 18),
    (AT_CUP, CUP[0] + 34, CUP[1]),
    (PUSHED, CUP_AWAY[0] + 34, CUP_AWAY[1]),
    (PUSHED + 0.25, *RESTS),
]
samples = [k / 30 for k in range(int((PUSHED + 0.3) * 30))]

ticks = [PHONE_1[0] + 0.1 + 0.5 * n for n in range(int((CRASH - PHONE_1[0]) / 0.5))]
keys = [L[8].start - 0.42 + 0.11 * n for n in range(4)] + [L[8].end + 0.04 + 0.13 * n for n in range(3)]
keys += [L[9].end + 0.06]
for name, times, burst, seed in (
    ("tick", ticks, foley.REMOTE_CLICK, 31253),
    ("put", [PUT], foley.KNOCK, 31254),
    ("slide", [AT_CUP + 0.02], foley.SCRAPE, 31255),
    ("smash", [CRASH, CRASH + 0.05, CRASH + 0.11, CRASH + 0.2, CRASH + 0.34], foley.PLATES, 31256),
    ("smash-low", [CRASH], foley.THUD, 31257),
    ("pop", [CRASH + 0.14], foley.REMOTE_CLICK, 31258),
    ("coat", [STANDS + 0.2], foley.SWISH, 31259),
    ("ding", [TOAST + 0.12], foley.BELL, 31260),
):
    foley.write_bursts(ROOT / "assets" / f"{name}.wav", times, DURATION, burst, seed=seed)
foley.write_typing(ROOT / "assets" / "thumbs.wav", keys, DURATION, seed=31261)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("tick", "assets/tick.wav", {"role": "effects", "gain": -9}),
        ("put", "assets/put.wav", {"role": "effects", "gain": -10}),
        ("slide", "assets/slide.wav", {"role": "effects", "gain": -9}),
        ("smash", "assets/smash.wav", {"role": "effects", "gain": -3}),
        ("smash-low", "assets/smash-low.wav", {"role": "effects", "gain": -6}),
        ("pop", "assets/pop.wav", {"role": "effects", "gain": -9}),
        ("coat", "assets/coat.wav", {"role": "effects", "gain": -9}),
        ("ding", "assets/ding.wav", {"role": "effects", "gain": -14}),
        ("thumbs", "assets/thumbs.wav", {"role": "effects", "gain": -6}),
    ],
    loudness="-14",
)


def ava(g):
    """She sits with one arm across the table, stands, and is at the door by the last cut."""
    who = cast.Barista(cv, tag="ava-character")
    node = ep.perform(
        who,
        g,
        *AVA_AT,
        mouth=ep.mouth("ava"),
        blinks=[(L[1].end - 0.2, L[1].end - 0.06), (PUSHED + 0.4, PUSHED + 0.54), (L[6].end - 0.1, L[6].end + 0.04)],
        nods=[(0, 7), (L[3].end, 7), (LET_GO + 0.1, 0), (TAKE, 6), (PUT, 8), (L[4].start, 2), (L[4].end, 4),
              (STANDS, 4), (STANDS + 0.3, 0), (L[8].start, 0), (L[8].start + 0.2, 6)],
        free_arms=("right",),
    )  # fmt: skip
    cv.keys(who.eyes, "x", [(0, 8), (LET_GO, 8), (LET_GO + 0.1, -8), (PUT, -8), (PUT + 0.1, 6), (STANDS, 6),
                            (STANDS + 0.2, 9)], hold=False)  # fmt: skip
    cv.keys(who.eyes, "y", [(0, 8), (STANDS, 8), (STANDS + 0.2, 0)], hold=False)
    cv.keys(node, "y", [(0, AVA_AT[1]), (CRASH, AVA_AT[1]), (CRASH + 0.05, AVA_AT[1] - 12), (CRASH + 0.2, AVA_AT[1]),
                        (STANDS, AVA_AT[1]), (STANDS + 0.32, UP), (DOOR - 0.2, UP), (DOOR - 0.1, AT_DOOR[1])],
            hold=False)  # fmt: skip
    cv.keys(node, "x", [(0, AVA_AT[0]), (DOOR - 0.2, AVA_AT[0]), (DOOR - 0.1, AT_DOOR[0])], hold=False)
    for prop in ("scaleX", "scaleY"):
        cv.keys(node, prop, [(0, AVA_AT[2]), (DOOR - 0.2, AVA_AT[2]), (DOOR - 0.1, AT_DOOR[2])], hold=False)
    cv.rect(who.group, -62, 318, 124, 230, "#2E3A44", cv.ink, 4)  # trousers, under the table until she stands
    cutout_handed.coat_over(cv, who.group, STANDS + 0.28, STANDS + 0.58, bottom=490)


def milo(g):
    """Both hands on the phone, head down. Only the thumbs move, and only at the end."""
    who = cast.Customer(cv, tag="milo-character", seated=True)
    ep.perform(
        who,
        g,
        *MILO_AT,
        mouth=ep.mouth("milo", smile=[(L[9].end - 0.05, DURATION)]),
        blinks=[
            (L[3].end + 0.3, L[3].end + 0.44),
            (L[6].end + 0.2, L[6].end + 0.34),
            (L[8].end + 0.1, L[8].end + 0.24),
        ],
        nods=[
            (0, 9),
            (L[1].start, 9),
            (L[1].start + 0.2, 6),
            (L[1].end, 9),
            (CRASH, 9),
            (CRASH + 0.06, 3),
            (CRASH + 0.3, 9),
            (DOOR, 11),
        ],
        free_arms=("left", "right"),
    )
    cv.keys(who.eyes, "y", [(0, 10)], hold=False)
    hands = cv.group(who.group, "milo-hands")
    start = L[8].start - 0.42
    busy = [(start + k * 0.055, -3.0 if k % 2 else 3.0) for k in range(int((DURATION - start) / 0.055))]
    cv.keys(hands, "y", [(0, 0.0), (start, 0.0), *busy], hold=False)
    cv.path(hands, "M-72 143 L-112 222 M73 144 L-34 214", stroke=cv.ink, sw=5)
    cv.rect(hands, -94, 160, 50, 84, "#293F49", cv.ink, 2.5, radius=7)
    cv.ellipse(hands, -131, 198, 38, 46, who.skin, cv.ink, 2.5)
    cv.ellipse(hands, -52, 192, 40, 46, who.skin, cv.ink, 2.5)


def at_table(g):
    cutout_handed.cafe_door(cv, g)
    ava(g)
    milo(g)
    cv.rect(g, -300, TABLE_Y, 1700, 900, "#B98A5E", cv.ink, 5)
    cv.rect(g, -300, TABLE_Y + 6, 1700, 14, "#D7AE7E", opacity=0.6)
    for x, y in [(120, 1330), (520, 1500), (860, 1340), (300, 1640), (780, 1700)]:
        cv.path(g, f"M{x - 180} {y} Q{x} {y - 26} {x + 200} {y + 6}", stroke="#A67B50", sw=3, opacity=0.7)
    cv.ellipse(g, 842, 1214, 150, 46, "#7F5B3C", opacity=0.3)
    props.coffee_cup(cv, g, 900, 1190, 1.15)  # his
    cup = cv.group(g, "her-cup")
    cv.keys(cup, "x", [(0, 0.0), (AT_CUP, 0.0), (PUSHED, float(CUP_AWAY[0] - CUP[0]))], kind="sine-in-out")
    props.coffee_cup(cv, cup, CUP[0], CUP[1] - 62, 1.15)
    watch = cv.group(g, "her-watch", x=WRIST[0], y=WRIST[1], rotation=80)
    path = [(s, hand_at(HAND, s)) for s in samples if TAKE <= s <= PUT]
    cv.keys(
        watch, "x", [(0, WRIST[0]), (TAKE, WRIST[0]), *[(s, p[0]) for s, p in path], (PUT, ON_TABLE[0])], hold=False
    )
    cv.keys(
        watch, "y", [(0, WRIST[1]), (TAKE, WRIST[1]), *[(s, p[1]) for s, p in path], (PUT, ON_TABLE[1])], hold=False
    )
    cutout_office.gold_watch(cv, watch, 0, 0, scale=0.42)
    arm = cv.group(g, "ava-reach")
    cv.gate(arm, [(0, STANDS)])
    _, grip = reach(cv, arm, "ava-arm", (347, 1012), HAND, skin=cast.Barista.skin, hand=58, width=7.5)
    for k in range(3):
        cv.line(grip, -14 + k * 14, -30, -12 + k * 14, 32, cv.ink, 3)


finish = locations.finish(cv, ep.comp)
room = locations.cafe(cv, finish, at_counter=at_table, shots=spans["table"], code_on_shelf=True)

HEART_X, HEART_Y = cutout_handed.POST_HEART[0] + 540, cutout_handed.POST_HEART[1] + 900
insert = cv.group(finish, "phone-insert")
cv.gate(insert, spans["phone"])
cv.rect(insert, -20, -20, 1120, 1960, "#3A2B20")
cv.rect(insert, -20, -20, 1120, 1960, "#B98A5E", opacity=0.22)
push = cv.group(insert, "phone-push")
scale = [(0.0, 1.0), (PHONE_1[0], 1.0), (CRASH, 1.24), (CRASH + 0.01, 1.0)]
for prop, values in (
    ("scaleX", scale),
    ("scaleY", scale),
    ("x", [(a, HEART_X * (1 - b)) for a, b in scale]),
    ("y", [(a, HEART_Y * (1 - b)) for a, b in scale]),
):
    cv.keys(push, prop, values, hold=False)
cutout_handed.phone_post(
    cv,
    push,
    liked_at=CRASH + 0.12,
    message=("Diane", "Thank you, dear.\nNobody ever likes my photos.\nAre you coming Sunday?"),
    message_at=TOAST + 0.15,
    message_shift=MESSAGE_SHIFT,
    mitts_in=MITTS_IN,
)
thumb = cv.group(insert, "thumb-move")
shake = [(PHONE_1[0] + k * 0.09, 4.0 if k % 2 else -4.0) for k in range(int((CRASH - PHONE_1[0]) / 0.09))]
cv.keys(
    thumb, "y", [(0, 0.0), *shake, (CRASH, 0.0), (CRASH + 0.05, 36.0), (CRASH + 0.5, 30.0), (TOAST, 900.0)], hold=False
)
cv.gate(thumb, [(0, CRASH + 0.85)])
cutout_handed.big_thumb(cv, thumb, HEART_X + 34, HEART_Y - 20, rotation=-24)
marks = cv.group(insert, "phone-marks")  # outside the push: on the table by the phone, whose bottom edge stops at 1832
signature.cactus(cv, marks, *MARK_CACTUS, 0.6)
signature.code(cv, marks, *MARK_CODE, 30, color="#D7AE7E")

SIZE = 1.12
OUT, IN = L[1].start + 0.4, L[9].start - 0.3
OPEN_X = 520  # the middle of the two of them: at SIZE both whole faces stay in the frame
LAST = 1.28
MILO_FACE = (770, 930)  # his face, for the last push
for prop, values in (
    ("scaleX", [(0.0, SIZE), (OUT, 1.0), (IN, 1.0), (DURATION, LAST)]),
    ("scaleY", [(0.0, SIZE), (OUT, 1.0), (IN, 1.0), (DURATION, LAST)]),
    ("x", [(0.0, 540 - OPEN_X * SIZE), (OUT, 0.0), (IN, 0.0), (DURATION, 540 - MILO_FACE[0] * LAST)]),
    ("y", [(0.0, 900 - CLAMP[1] * SIZE), (OUT, 0.0), (IN, 0.0), (DURATION, 900 - MILO_FACE[1] * LAST)]),
):
    cv.keys(room, prop, values, hold=False)

spoken = ep.captions(ep.spoken_captions(), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-crash", CRASH, "The cup"), ("marker-toast", TOAST, "Diane")])
ep.instagram(POSTS["dont-move"])
ep.finish()

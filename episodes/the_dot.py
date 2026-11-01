#!/usr/bin/env python3
"""The Dot, built with srstudio: a first date, a phone on speaker, and a mother with the family map.

    srstudio record the-dot PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build the-dot PROJECT    # → PROJECT/the-dot.scene.xml

A café at night, candles, his phone ringing on the table. He answers. "Why are you at a restaurant?" "Mom, how do
you..." "The dot. Forty minutes. Who is she?" A map chip with a dot. "Who's that?" "Nobody. Mom." "Tuesday the dot was
at a pharmacy. Eleven minutes. Are you dying?" "Are you dying?" "It was shampoo!" "Thursday night the dot was at some
Sandra's." Nothing. Ava puts down her fork and slowly takes the phone. "Hi. Where was he on the fourteenth?" The line
goes quiet and a chair is pulled up, far away. "Do you have a pen, dear?" Her own phone buzzes, and the chip lands on
it. Milo watches the two of them.

Rosa is never drawn. It declares no engine safe area, so captions are placed inside x 80–920 by hand. No music: the
foley is synthesized here.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import (
    CAFE,
    Episode,
    EpisodeSpec,
    cast,
    cutout_arm,
    cutout_counter,
    cutout_key,
    cutout_locate,
    cutout_store,
    foley,
    locations,
    look,
)
from srstudio import interview as iv_audio
from the_dot_audio import INTERVIEW

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="the-dot",
        title=INTERVIEW.title,
        description="Everyday-tech comedy: a first date with a phone on speaker and a mother reading the family "
        "location map, until the date asks for the map herself. Native vector animation; ElevenLabs dialogue, "
        "synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=3322,
        background="#141C3A",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        bleed=True,
    )
)
t, cv = ep.t, ep.cv
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
PUT, TAKE, CHAIR, BUZZ, CHIP = (float(t.meta[k]) for k in ("put", "take", "chair", "buzz", "chip"))
TOOK = TAKE + 0.45  # the hand closes on the phone
LANDS = CHIP + 0.15  # the chip lands
UP = L[10].start - 0.15  # the phone is at her mouth
DATE = [(0.0, CHIP)]
ROSA = (0, 2, 5, 6, 9, 11)

AVA = (245.0, 800.0, 1.5)
MILO = (810.0, 800.0, 1.5)
TABLE_Y = 1160
PHONE = (560.0, 1228.0)
HER_PHONE = (130.0, 1228.0)
PLATE = (290.0, 1224.0)
NIGHT = "#141C3A"
FLAMES = ((518.0, 985.0), (540.0, 971.0), (562.0, 990.0))

foley.write_buzz(ROOT / "assets" / "ring.wav", [0.0], DURATION, seed=3323)
foley.write_bursts(ROOT / "assets" / "fork.wav", [PUT + 0.3], DURATION, foley.PLATES, seed=3324)
foley.write_bursts(ROOT / "assets" / "chair.wav", [CHAIR], DURATION, foley.SCRAPE, seed=3325)
foley.write_buzz(ROOT / "assets" / "buzz.wav", [BUZZ, LANDS], DURATION, seed=3326)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("ring", "assets/ring.wav", {"role": "effects", "gain": -10}),
        ("fork", "assets/fork.wav", {"role": "effects", "gain": -14}),
        ("chair", "assets/chair.wav", {"role": "effects", "gain": -18}),
        ("buzz", "assets/buzz.wav", {"role": "effects", "gain": -10}),
    ],
    loudness="-14",
)


def night_pane(g):
    """The set's window with the night behind it; the mullions go back over it."""
    cv.rect(g, 637, 249, 331, 396, "#1A2546", radius=3)
    cv.ellipse(g, 880, 300, 56, 56, "#EFE6C4")
    for xx, yy in ((670, 560), (720, 590), (900, 520), (850, 600)):
        cv.rect(g, xx, yy, 18, 24, "#E8C76E", opacity=0.8)
    cv.line(g, 803, 245, 803, 650, "#5B7776", 7)
    cv.line(g, 638, 455, 969, 455, "#5B7776", 6)


def ava(g):
    cv.gate(g, DATE)
    who = cast.Barista(cv, tag="ava-date")
    ep.perform(
        who,
        g,
        *AVA,
        mouth=ep.mouth("barista", smile=[(0.0, L[3].start)]),
        blinks=[(L[1].end, L[1].end + 0.14), (L[5].end - 0.2, L[5].end - 0.06), (L[9].end + 0.2, L[9].end + 0.34)],
        nods=[(0, 0), (L[3].start, 0), (L[3].start + 0.2, 4), (L[3].end, 0), (L[10].start, 0), (L[10].start + 0.3, -3)],
        free_arms=("right",),
    )
    cv.keys(who.eyes, "x", [(0, 7), (L[3].start, 7), (L[3].start + 0.1, 11), (TAKE, 11), (TAKE + 0.2, 4)], hold=False)


def milo(g):
    who = cast.Customer(cv, tag="milo-date", seated=True)
    node = ep.perform(
        who,
        g,
        *MILO,
        mouth=ep.mouth("customer"),
        blinks=[(L[3].end, L[3].end + 0.14), (L[9].end + 0.5, L[9].end + 0.64), (LANDS + 0.9, LANDS + 1.04)],
        nods=[(0, 0), (L[8].start, 0), (L[8].start + 0.12, -5), (L[8].end, 0)],
        free_arms=("left", "right"),
    )
    down = [(0, -6), (0.3, 3), (L[1].start, 3), (L[3].start, -8), (L[9].end, -8), (CHIP, -14), (DURATION, -14)]
    cv.keys(who.eyes, "x", down, hold=False)
    return who, node


def milo_arms(g, skin):
    shoulder = (MILO[0] - 66 * MILO[2], MILO[1] + 140 * MILO[2])
    rest = (682.0, 1200.0)
    track = [
        (0.0, 640.0, 1190.0),
        (0.24, PHONE[0] + 12, PHONE[1] - 8),
        (0.36, PHONE[0] + 12, PHONE[1] - 8),
        (0.8, *rest),
    ]
    cutout_arm.arm(cv, g, "milo-answers", shoulder, track, upper=150, fore=150, bend=-1, width=6.5, hand=50, skin=skin)
    shoulder = (MILO[0] + 68 * MILO[2], MILO[1] + 141 * MILO[2])
    rest = (930.0, 1196.0)
    up = (976.0, 1010.0)
    a, b = L[8].start - 0.1, L[8].end + 0.05
    track = [(0.0, *rest), (a, *rest), (a + 0.14, *up), (a + 0.3, up[0] - 30, up[1] + 8), (a + 0.46, *up), (b, *up),
             (b + 0.3, *rest)]  # fmt: skip
    cutout_arm.arm(cv, g, "milo-protests", shoulder, track, upper=150, fore=150, bend=1, width=6.5, hand=50, skin=skin)


def ava_arm(g):
    g_date = cv.group(g, "ava-arm-date")
    cv.gate(g_date, DATE)
    shoulder = (AVA[0] + 68 * AVA[2], AVA[1] + 141 * AVA[2])
    fork_at, plate = (416.0, 1120.0), (PLATE[0] + 44, PLATE[1] - 14)
    lifted = (428.0, 1006.0)
    track = [(0.0, *fork_at), (L[2].start, *fork_at), (PUT, *fork_at), (PUT + 0.3, *plate), (TAKE, *plate),
             (TOOK, *PHONE), (TOOK + 0.08, *PHONE), (UP, *lifted), (CHIP, *lifted)]  # fmt: skip
    arm = cutout_arm.arm(
        cv,
        g_date,
        "ava-reach",
        shoulder,
        track,
        upper=160,
        fore=160,
        bend=-1,
        width=6.5,
        hand=50,
        skin=cast.Barista.skin,
    )
    fork = cv.group(arm.grip, "fork-in-hand")
    cv.gate(fork, [(0.0, PUT + 0.3)])
    cutout_locate.table_fork(cv, fork, 0, 0, scale=0.8, rotation=8)
    held = cv.group(arm.grip, "phone-in-hand")
    cv.gate(held, [(TOOK + 0.08, CHIP)])
    cutout_locate.held_phone(cv, held, 0, -60, scale=0.9)


def the_table(g):
    cutout_store.taper_candles(cv, g, 540, 1168, scale=0.72)
    for k, (x, y) in enumerate(FLAMES):
        flame = cv.group(g, f"flame-{k}", x=x, y=y)
        keys = [(n * 0.23 + 0.05 * k, 1.0 if n % 2 else 0.84) for n in range(int(DURATION / 0.23) + 1)]
        cv.keys(flame, "scaleY", keys, hold=False)
        cv.path(flame, "M0 -24 Q13 -4 7 6 Q0 13 -7 6 Q-13 -4 0 -24Z", "#F6C65B", cv.ink, 2.5)
    cutout_counter.cafe_table(cv, g, 540, TABLE_Y, width=1500)
    look.pool(cv, g, "candle-on-cloth", "#F8C877", 180, 1120, 720, 170, opacity=0.5)
    cutout_locate.dinner_plate(cv, g, *PLATE, id="her-plate")
    cutout_locate.dinner_plate(cv, g, 810, 1224, id="his-plate")
    left = cv.group(g, "fork-on-plate")
    cv.gate(left, [(PUT + 0.3, DURATION)])
    cutout_locate.table_fork(cv, left, PLATE[0] + 44, PLATE[1] - 14, scale=0.7, rotation=74, id="fork-left")
    speaking = [(L[i].start, L[i].end) for i in ROSA if L[i].end <= TOOK]
    phone = cv.group(g, "phone-on-table")
    cv.gate(phone, [(0.0, TOOK + 0.08)])
    cutout_locate.table_phone(cv, phone, *PHONE, rings=[(0.0, 0.3)], speaker=speaking, lit=[(0.0, TOOK + 0.08)])
    hers = cv.group(g, "her-phone-on-table")
    cv.gate(hers, DATE)
    cutout_locate.table_phone(cv, hers, *HER_PHONE, rings=[(BUZZ, CHIP)], lit=[(BUZZ, CHIP)], id="her-phone")
    cv.rect(g, -300, 1296, 1680, 900, NIGHT, opacity=0.62)  # the cloth falls away from the candles, under the captions


finish = locations.finish(cv, ep.comp)
room = cv.group(finish, "the-room")
locations.cafe(cv, room, behind_counter=night_pane)
cv.rect(room, -1200, -1700, 3500, 4300, NIGHT, opacity=0.68)
look.pool(cv, room, "lamp-left", "#FFD48A", 60, 60, 480, 420, opacity=0.34)
look.pool(cv, room, "lamp-right", "#FFD48A", 610, 60, 480, 420, opacity=0.34)
look.pool(cv, room, "candles-up", "#FFC56B", 200, 690, 680, 520, opacity=0.36)
ava(cv.group(room, "ava-at-the-table"))
who, node = milo(cv.group(room, "milo-at-the-table"))
the_table(cv.group(room, "the-table"))
milo_arms(cv.group(room, "milo-arms"), who.skin)
ava_arm(cv.group(room, "ava-arm"))

SIZE, AT_X, AT_Y = 1.3, -333.0, -260.0  # over her shoulder: Milo right of the phone
for prop, wide, near in (("scaleX", 1.0, SIZE), ("scaleY", 1.0, SIZE), ("x", 0.0, AT_X), ("y", 0.0, AT_Y)):
    cv.keys(room, prop, [(0.0, wide), (CHIP, near)])

cutout_locate.location_chip(
    cv,
    finish,
    540,
    440,
    [
        (max(L[2].start + 0.2, 3.02), L[3].start, "table"),  # once the hook is off
        (L[5].start + 0.1, L[7].start, "cross"),
        (L[9].start + 0.4, TOOK, "moon"),
    ],
)


def her_phone(g):
    cutout_locate.notice_phone(cv, g, 0, 0, ("ROSA ADDED", "YOU TO FAMILY"), at=LANDS, scale=0.76)


hand = cv.group(finish, "her-hand")
cv.gate(hand, [(CHIP, DURATION)])
cutout_counter.reaching_hand(
    cv,
    hand,
    330,
    1010,
    scale=1.58,
    rotation=-4,
    grip=120,
    skin=cast.Barista.skin,
    sleeve="#F5EAD4",
    holds=her_phone,
    id="her-hand-holds",
)

hook = cutout_key.key_line(cv, ep.comp, "FIRST DATE", 0.0, 3.0, top=300, font=(ROOT / ep.spec.font).read_bytes())
spoken = ep.captions(ep.spoken_captions(min_seconds=0.84), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(hook, *spoken)
ep.markers(extra=[("marker-take", TAKE, "She takes the phone"), ("marker-chip", CHIP, "The chip")])
ep.instagram(POSTS["the-dot"])
ep.finish()

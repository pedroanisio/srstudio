#!/usr/bin/env python3
"""Many Hats, built with srstudio: the job ad said "wears many hats", and they keep landing on him.

    srstudio record many-hats PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build many-hats PROJECT    # → PROJECT/many-hats.scene.xml

One held two-shot behind the desk, the camera creeping. "We need someone who wears many hats." A hat lands. "I love
hats." Thunk, "Sales." Thunk, "Accounting." Thunk: he steadies it. "This one's warm." "That's Linda's. She left at
lunch." Three more on three words, and the stack leaves the top of the frame. It sways, and he does not move his neck.
"And the pay?" One finger: the whole stack goes over and out of the frame. The Boss sets down one tiny hat. "The pay is
for this one."

The Boss is mirrored so that the arm the rig can hide is the one nearest the Candidate, and the stack goes over away
from the show's bug. No music: every hat is foley synthesized here. It declares no engine safe area, so captions are
placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from many_hats_audio import INTERVIEW
from srstudio import (
    OFFICE,
    Episode,
    EpisodeSpec,
    cast,
    cutout_arm,
    cutout_hats,
    cutout_hiring,
    cutout_key,
    foley,
    locations,
)
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="many-hats",
        title=INTERVIEW.title,
        description="Job-hunting comedy: the job ad said wears many hats, and every one of them lands on the "
        "candidate's head. Native vector animation; ElevenLabs dialogue, synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=3303,
        background="#66798B",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        bleed=True,
    )
)
t, cv = ep.t, ep.cv
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
SALES, ACCOUNTING, LINDA = float(t.meta["sales"]), float(t.meta["accounting"]), float(t.meta["linda"])
STEADY, SWAY, POKE, TINY = float(t.meta["steady"]), float(t.meta["sway"]), float(t.meta["poke"]), float(t.meta["tiny"])
FIRST = iv_audio.said(ROOT, L[0], "hats") + 0.08
RECEPTION = iv_audio.said(ROOT, L[6], "reception") + 0.02
FACILITIES = iv_audio.said(ROOT, L[6], "facilities") + 0.02
WEBSITE = iv_audio.said(ROOT, L[6], "website") + 0.02
HATS = (
    ("trilby", FIRST),
    ("boater", SALES),
    ("visor", ACCOUNTING),
    ("beanie", LINDA),
    ("headset", RECEPTION),
    ("hard-hat", FACILITIES),
    ("chef", WEBSITE),
)
LANDINGS = [at for _, at in HATS]
HIT = {"trilby": -6, "boater": -5, "visor": -7, "beanie": -9, "headset": -8, "hard-hat": -2, "chef": -6}
FALLS = [POKE + d for d in (0.34, 0.46, 0.56, 0.64, 0.72, 0.78)]
FAR = POKE + 1.16  # the last one lands a long way off

CANDIDATE = (310, 694, 1.6)
BOSS = (715, 600, 1.72)
BRIM = -104  # on his head, in his own units
CARRY = 70  # the hand is this far right of what it sets down, so the arm stays off his face
TOP = (CANDIDATE[0], CANDIDATE[1] + BRIM * CANDIDATE[2])

for name, times, burst, seed in (
    ("thunk", [at for k, at in HATS if k != "hard-hat" and k != "beanie"], foley.THUD, 3304),
    ("hard", [dict(HATS)["hard-hat"]], foley.KNOCK, 3305),
    ("soft", [LINDA], foley.THUD, 3306),
    ("poke", [POKE], foley.KNOCK, 3307),
    ("falling", FALLS, foley.THUD, 3308),
    ("far", [FAR], foley.THUD, 3309),
    ("tiny", [TINY + 0.04], foley.REMOTE_CLICK, 3310),
):
    foley.write_bursts(ROOT / "assets" / f"{name}.wav", times, DURATION, burst, seed=seed)
LEVELS = {"thunk": -6, "hard": -5, "soft": -8, "poke": -8, "falling": -6, "far": -12, "tiny": -6}
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        *((n, f"assets/{n}.wav", {"role": "effects", "gain": g}) for n, g in LEVELS.items()),
    ],
    loudness="-14",
)  # fmt: skip


def dips(landings):
    """Every hat pushes him down a little, and he comes back."""
    keys = [(0.0, 0.0)]
    for at in landings:
        keys += [(at, 0.0), (at + 0.06, 9.0), (at + 0.26, 0.0)]
    return keys


def the_candidate(g):
    who = cast.Candidate(cv, tag="candidate-character")
    node = ep.perform(
        who,
        g,
        *CANDIDATE,
        mouth=ep.mouth("candidate"),
        blinks=[(L[0].start + 1.2, L[0].start + 1.34), (LINDA + 0.1, LINDA + 0.24), (L[6].end + 0.3, L[6].end + 0.44)],
        nods=[(0, 0), (L[1].start, 0), (L[1].start + 0.2, 3), (L[1].end, 0)],
        arms="articulated",
    )
    cv.keys(node, "y", [(at, CANDIDATE[1] + d) for at, d in dips(LANDINGS)], hold=False)
    cv.keys(who.eyes, "x", [(0, 0), (FIRST - 0.2, 0), (FIRST, 6), (L[2].start, 6), (L[2].start + 0.2, 0)], hold=False)
    cv.keys(who.eyes, "y", [(0, 0), (TINY, 0), (TINY + 0.14, -9)], hold=False)  # he looks up at it, and that is the end
    # his hand on the brim from the warm one to the fall
    down, up = STEADY, POKE - 0.3
    cv.gate(who.right_arm, [(0.0, down), (up + 0.3, DURATION)])
    arm = cutout_arm.arm(cv, who.group, "candidate-steady", (67, 148),
                         [(down, 150, 240), (down + 0.2, 112, BRIM + 18), (up, 112, BRIM + 18), (up + 0.3, 150, 240)],
                         bend=-1)  # fmt: skip
    cv.gate(arm.group, [(down, up + 0.3)])
    cutout_hats.hat_stack(cv, who.head, 0, BRIM, HATS, sway=_sway(), topple=(POKE, -1))
    tiny = cv.group(who.head, "tiny-on-head")
    cv.gate(tiny, [(TINY, DURATION)])
    cutout_hats.tiny_hat(cv, tiny, 0, BRIM - 12, scale=1.15, id="tiny-worn")


def _sway():
    """Still until the last hat, then a slow lean each way, each one more than the last, until the finger."""
    keys = [(0.0, 0.0), (SWAY, 0.0)]
    at, amp, side = SWAY, 0.7, 1
    while at + 0.5 < POKE:
        at += 0.5
        keys.append((at, amp * side))
        amp, side = amp + 0.14, -side
    return keys + [(POKE, 0.0)]


def the_boss(g):
    """Mirrored, so the rig's arm is the one nearest the Candidate. Everything here is in his own, flipped units."""
    mirrored = cv.group(g, "boss-mirrored", x=1080, scaleX=-1)
    who = cast.Manager(cv, tag="boss-character")
    x, y, size = 1080 - BOSS[0], BOSS[1], BOSS[2]
    ep.perform(
        who,
        mirrored,
        x,
        y,
        size,
        mouth=ep.mouth("manager", smile=[(0.0, L[0].start), (L[8].end, DURATION)]),
        blinks=[(L[1].end - 0.1, L[1].end + 0.04), (L[5].end + 0.05, L[5].end + 0.19), (L[7].end, L[7].end + 0.14)],
        nods=[(0, 0), (L[2].start, 0), (L[2].start + 0.12, 3), (L[3].start, 0), (L[3].start + 0.12, -3),
              (L[5].start, 0), (L[6].end, 0)],
        brows=([(0, 0), (L[7].end - 0.3, 0), (L[7].end, 7)], [(0, 0), (L[7].end - 0.3, 0), (L[7].end, -3)]),
        arms="articulated",
    )  # fmt: skip

    def local(px, py):  # a frame point in his own units
        return (1080 - px - x) / size, (py - y) / size

    start, lift, touch = POKE - 0.55, POKE - 0.05, POKE
    away = POKE + 0.30
    fetch, rises, sets = POKE + 0.62, TINY - 0.34, TINY
    done = TINY + 0.42
    rest = (150.0, 250.0)
    poke_at = local(TOP[0] + 112, TOP[1] - 22)
    set_at = local(TOP[0] + CARRY, TOP[1] - 30)
    over = local(TOP[0] + CARRY + 60, TOP[1] + 20)
    below = local(600, 1090)
    track = [(start, *rest), (lift, poke_at[0] - 24, poke_at[1] + 8), (touch, *poke_at),
             (away, poke_at[0] + 8, poke_at[1] + 30), (fetch, *below), (rises, *below),
             (sets - 0.12, *over), (sets, *set_at), (done, *rest)]  # fmt: skip
    cv.gate(who.right_arm, [(0.0, start), (done, DURATION)])
    arm = cutout_arm.arm(
        cv, who.group, "boss-reach", (67, 148), track, upper=124, fore=124, bend=-1, finger=True, hand=40
    )
    cv.gate(arm.group, [(start, done)])
    held = cv.group(arm.grip, "boss-tiny", x=CARRY / size)
    cv.gate(held, [(rises - 0.12, sets)])
    cutout_hats.tiny_hat(cv, held, 0, 0, scale=1.15 / size * CANDIDATE[2], id="tiny-carried")


def behind_desk(g):
    the_candidate(cv.group(g, "at-the-desk-left"))
    the_boss(cv.group(g, "at-the-desk-right"))


def on_desk(g):
    cutout_hiring.job_ad(cv, g, 540, 1372, heading="NOW HIRING", lines=("FULL TIME", "WEARS MANY HATS"), scale=0.82)


finish = locations.finish(cv, ep.comp)
office = cutout_hiring.hiring_office(cv, finish, behind_desk=behind_desk, on_desk=on_desk)
CREEP = 1.06
for prop, values in (
    ("scaleX", [(0.0, 1.0), (POKE, CREEP)]),
    ("scaleY", [(0.0, 1.0), (POKE, CREEP)]),
    ("x", [(0.0, 0.0), (POKE, 540 * (1 - CREEP))]),
    ("y", [(0.0, 0.0), (POKE, 820 * (1 - CREEP))]),
):
    cv.keys(office, prop, values, hold=False)

hook = cutout_key.key_line(cv, ep.comp, "ONE POSITION", 0.0, 3.0, top=300, font=(ROOT / ep.spec.font).read_bytes())
spoken = ep.captions(ep.spoken_captions(min_seconds=0.84), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(hook, *spoken)
ep.markers(
    extra=[
        ("marker-stack", WEBSITE, "The stack"),
        ("marker-poke", POKE, "The finger"),
        ("marker-tiny", TINY, "The tiny hat"),
    ]
)
ep.instagram(POSTS["many-hats"])
ep.finish()

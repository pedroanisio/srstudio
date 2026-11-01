#!/usr/bin/env python3
"""How Is Everything, built with srstudio: she only ever comes when his mouth is full.

    srstudio record how-is-everything PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build how-is-everything PROJECT    # → PROJECT/how-is-everything.scene.xml

Milo bites. Ava is at his elbow. "How is everything?" "Mmf." She is gone, wiping a far table. He watches her, lifts the
sandwich slowly, bites: she is there. He tests her with a bite of air, and nobody comes. "Got you." A real bite: there.
The plate is empty and now she cannot see him. He looks at the napkin. He looks at her. He bites the napkin, and she is
at his elbow. He holds up his card, chewing. She leaves with it, and he goes on chewing, eyes wet, undefeated.

The first frame already moves (arm B of the ``sp-hook_motion`` test): the sandwich is on its way up. It declares no
engine safe area, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from how_is_everything_audio import INTERVIEW
from instagram_posts import POSTS
from srstudio import CAFE, Episode, EpisodeSpec, camera, cast, cutout_odds, foley, locations, look, signature
from srstudio import interview as iv_audio
from srstudio.cutout_reach import reach

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="how-is-everything",
        title=INTERVIEW.title,
        description="Service comedy: the waiter only ever asks how everything is when his mouth is full, so he bites "
        "a napkin to get the check. Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=26401,
        background="#E9D7BC",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
t, cv = ep.t, ep.cv
P = t.phrases
DURATION = t.duration
BITES = [float(b) for b in t.meta["bites"]]
FAKE, AIR_END, EMPTY, NAPKIN, BEEP = (float(t.meta[k]) for k in ("fake", "air_stop", "empty", "napkin", "beep"))
LEAVE = [P[i].end + 0.30 for i in (1, 3, 6, 9)]
ARRIVE = [*(b + 0.14 for b in BITES), NAPKIN + 0.14]
ROOMS = 1560.0  # off frame, right
ELBOW = 835.0
FLOOR = 1165.0  # the far side's, under Ava and her table
MILO = (300.0, 730.0, 2.1)
FPS = 30

chews = [
    (BITES[0] + 0.1, P[1].end + 1.2),
    (BITES[1] + 0.1, P[3].end + 0.7),
    (FAKE + 0.1, AIR_END),
    (BITES[2] + 0.1, P[6].end + 0.5),
    (NAPKIN + 0.1, DURATION),
]
ticks = [
    at + 0.28 * n
    for at, end in chews
    for n in range(int((end - at) / 0.28))
    if not (NAPKIN < at and at + 0.28 * n > LEAVE[3] + 1.2 and n % 2)  # the last chew slows down
]
whips = [a - 0.12 for a in ARRIVE] + [x - 0.02 for x in LEAVE]
foley.write_bursts(ROOT / "assets" / "bite.wav", [*BITES, FAKE + 0.02], DURATION, foley.BITE, seed=26402)
foley.write_bursts(ROOT / "assets" / "chew.wav", ticks, DURATION, foley.CHEW, seed=26403)
foley.write_bursts(ROOT / "assets" / "napkin.wav", [NAPKIN], DURATION, foley.PAPER_CRUNCH, seed=26404)
foley.write_whoosh(ROOT / "assets" / "whip.wav", sorted(whips), DURATION, length=0.14, seed=26405)
foley.write_tones(ROOT / "assets" / "beep.wav", [BEEP], DURATION, ((1568.0, 1568.0, 0.12),))
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("bite", "assets/bite.wav", {"role": "effects", "gain": 0}),
        ("chew", "assets/chew.wav", {"role": "effects", "gain": -9}),
        ("napkin", "assets/napkin.wav", {"role": "effects", "gain": -2}),
        ("whip", "assets/whip.wav", {"role": "effects", "gain": -6}),
        ("beep", "assets/beep.wav", {"role": "effects", "gain": -10}),
    ]
)


def chewing(states):
    """His mouth works in every chew span, whatever the take does: he answers with his mouth full."""
    out = []
    for at, pose in states:
        span = next((s for s in chews if s[0] <= at < s[1]), None)
        if span:
            beat = int((at - span[0]) / 0.14)
            pose = "small" if beat % 2 else "rest"
        if FAKE - 0.2 <= at < FAKE + 0.02:
            pose = "open"
        out.append((at, pose))
    return out


def milo_keys():
    """His head goes with his jaw; his eyes follow what he is thinking about."""
    bob = [(0.0, 0.0)]
    for at, end in chews:
        n = 0
        while at + 0.14 * n < end:
            bob.append((at + 0.14 * n, 2.0 if n % 2 else -1.0))
            n += 1
        bob.append((end, 0.0))
    return sorted(set(bob))


RIGHT_REST = (150.0, 232.0)
MOUTH = (112.0, 62.0)
LEFT_REST = (-122.0, 238.0)
right_hand = [
    (0.0, 170.0, 150.0),
    (BITES[0], *MOUTH),
    (BITES[0] + 0.3, *MOUTH),
    (BITES[0] + 0.7, *RIGHT_REST),
    (BITES[1] - 1.0, *RIGHT_REST),
    (BITES[1] - 0.02, *MOUTH),
    (BITES[1] + 0.3, *MOUTH),
    (BITES[1] + 0.7, *RIGHT_REST),
    (BITES[2] - 0.5, *RIGHT_REST),
    (BITES[2], *MOUTH),
    (BITES[2] + 0.3, *MOUTH),
    (BITES[2] + 0.7, *RIGHT_REST),
    (EMPTY + 0.25, *RIGHT_REST),
    (EMPTY + 0.6, 180.0, -120.0),
    (EMPTY + 0.8, 150.0, -136.0),
    (EMPTY + 1.0, 180.0, -120.0),
    (EMPTY + 1.2, 150.0, -136.0),
    (EMPTY + 1.4, 180.0, -120.0),
    (P[7].end + 0.1, 180.0, -120.0),
    (P[7].end + 0.5, *RIGHT_REST),
    (NAPKIN + 0.16, *RIGHT_REST),
    (P[8].start, 130.0, -70.0),
    (LEAVE[3] - 0.05, 130.0, -70.0),
    (LEAVE[3] + 0.5, *RIGHT_REST),
]
left_hand = [
    (0.0, *LEFT_REST),
    (P[7].end + 0.2, *LEFT_REST),
    (NAPKIN - 1.0, *LEFT_REST),
    (NAPKIN - 0.6, -86.0, 240.0),
    (NAPKIN - 0.4, -86.0, 240.0),
    (NAPKIN, -30.0, 66.0),
    (NAPKIN + 0.5, -30.0, 66.0),
    (NAPKIN + 1.0, *LEFT_REST),
]


def spans_far():
    """Ava is at the far table in every stretch she is not at his elbow or crossing behind him."""
    edges = [*zip(LEAVE[:2], ARRIVE[1:3], strict=True)]
    return [(a + 0.05, b - 0.1) for a, b in edges] + [(LEAVE[2] + 0.05, P[7].start + 0.2), (P[7].end, ARRIVE[3] - 0.1)]


def far_side(g):
    """The far table, and Ava standing behind it whenever she is not at his elbow."""
    cv.rect(g, -600, FLOOR, 2300, 300, "#A68D70")  # the room's floor, which ends behind the counter
    cv.line(g, -600, FLOOR, 1700, FLOOR, "#7D6750", 5)
    away = cv.group(g, "ava-far")
    cv.gate(away, spans_far())
    sway = [(0.0, 0.0)]
    at = 0.0
    while at < DURATION:
        sway += [(at + 0.25, -7.0), (at + 0.5, 7.0)]
        at += 0.5
    cv.keys(away, "rotation", sway, hold=False)
    ep.perform(
        cast.Barista(cv, tag="ava-far-character"), away, 730, 840, 0.72, mouth=[(0.0, "rest")], name=None, legs=True
    )
    cutout_odds.bistro_table(cv, g, 720, 1050, width=250, id="far-table")
    cloth = cv.group(g, "far-cloth", x=690, y=1038)
    cv.gate(cloth, spans_far())
    wipe = [(0.25 * n, 660.0 if n % 2 else 780.0) for n in range(int(DURATION / 0.25))]
    cv.keys(cloth, "x", wipe, hold=False)
    cv.rect(cloth, -28, -8, 56, 14, "#F5EAD4", cv.ink, 2.5, radius=4)


def milo_in_chair(g):
    actor = cast.Customer(cv, tag="milo-character", seated=False)
    ep.perform(
        actor,
        g,
        *MILO,
        mouth=chewing(ep.mouth("milo")),
        blinks=[(3.1, 3.24), (9.6, 9.74), (P[7].end + 0.5, P[7].end + 0.64), (DURATION - 1.2, DURATION - 1.06)],
        free_arms=("left", "right"),
    )
    cv.keys(actor.head, "y", milo_keys(), hold=False)
    looks = [
        (0.0, 0.0),
        (LEAVE[0] + 0.2, 0.0),
        (LEAVE[0] + 0.3, 12.0),
        (BITES[1] + 0.2, 12.0),
        (BITES[1] + 0.3, 0.0),
        (AIR_END, 0.0),
        (AIR_END + 0.1, -14.0),
        (AIR_END + 0.7, -14.0),
        (AIR_END + 0.8, 14.0),
        (AIR_END + 1.3, 14.0),
        (AIR_END + 1.4, 0.0),
        (P[7].end + 0.2, 0.0),
        (P[7].end + 0.3, -8.0),
        (NAPKIN - 0.95, -8.0),
        (NAPKIN - 0.85, 14.0),
        (NAPKIN - 0.2, 14.0),
        (NAPKIN - 0.1, 0.0),
    ]
    cv.keys(actor.eyes, "x", looks, hold=False)
    corner = cv.group(actor.head, "napkin-corner")
    cv.gate(corner, [(NAPKIN, DURATION)])
    cv.path(corner, "M-5 45 L9 44 L23 70 L5 73Z", "#FBF8F0", cv.ink, 3)  # what is left hangs out of his mouth
    cv.ellipse(corner, -13, 39, 26, 12, "#3B2A26", cv.ink, 3)  # the lips shut on it, over the napkin's torn edge
    cheek = cv.group(actor.head, "full-cheek")
    cv.gate(cheek, [(a, min(b, a + 2.0)) for a, b in chews if a != FAKE + 0.1])
    cv.path(cheek, "M66 22 Q104 44 72 74", "#F1D0AA", cv.ink, 3.5)
    tears = cv.group(actor.head, "wet-eyes")
    cv.gate(tears, [(LEAVE[3] + 0.5, DURATION)])
    for side, x in enumerate((-46, 46)):
        drop = cv.group(tears, f"tear-{side}", x=x, y=24)
        cv.keys(drop, "y", [(LEAVE[3] + 0.5, 24.0), (DURATION, 50.0 + 12 * side)], hold=False)
        cv.ellipse(drop, -6, 0, 12, 17, "#9FD3E8", cv.ink, 2)
    return actor


def on_table(g):
    x, y, scale = MILO
    cv.rect(
        g, -600, 1660, 2300, 500, "#A5704E"
    )  # the counter runs to the frame's foot: whoever sits behind it has no legs
    look.pool(cv, g, "plate-shadow", "#2A2018AA", 270, 1254, 400, 44, opacity=0.5)
    cv.ellipse(g, 280, 1236, 380, 54, "#FBF8F0", cv.ink, 4)
    cv.ellipse(g, 320, 1244, 300, 36, "#EFE7D6", "#D6CFBF", 2)
    signature.cactus(cv, g, 830, 1262, scale=0.5)  # the wall's cactus is behind Milo's head from the first frame on
    lying = cv.group(g, "lying-napkin")
    cv.gate(lying, [(0.0, NAPKIN - 0.5)])
    cutout_odds.paper_napkin(cv, lying, 120, 1272, id="table-napkin")
    hands = cv.group(g, "milo-hands", x=x, y=y, scaleX=scale, scaleY=scale)
    _, left = reach(cv, hands, "milo-left-arm", (-73, 146), left_hand, width=5.0, hand=44.0)
    _, right = reach(cv, hands, "milo-right-arm", (73, 146), right_hand, width=5.0, hand=44.0)
    food = cv.group(right, "held-sandwich", x=-46, y=-8, scaleX=-1)
    cv.gate(food, [(0.0, EMPTY)])
    cutout_odds.eaten_sandwich(cv, food, 0, 0, bites=BITES, scale=0.72)
    card = cv.group(right, "held-card", x=8, y=-40)
    cv.gate(card, [(NAPKIN + 0.2, LEAVE[3] - 0.05)])
    cv.rect(card, -34, -22, 68, 44, "#2F5D8C", cv.ink, 2.5, radius=5)
    cv.rect(card, -34, -12, 68, 9, "#16151B")
    held = cv.group(left, "held-napkin", x=0, y=-4)
    cv.gate(held, [(NAPKIN - 0.5, NAPKIN + 0.05)])
    cutout_odds.paper_napkin(cv, held, 0, 0, scale=0.5, id="lifted-napkin")


def ava_elbow(g):
    near = cv.group(g, "ava-near", x=ROOMS)
    keys = [(0.0, ROOMS)]
    for a, b in zip(ARRIVE, LEAVE, strict=True):
        keys += [(a - 0.12, ROOMS), (a - 0.02, ELBOW), (b - 0.02, ELBOW), (b + 0.08, ROOMS)]
    cv.keys(near, "x", keys, hold=False)
    actor = cast.Barista(cv, tag="ava-near-character")
    ep.perform(
        actor,
        near,
        0,
        780,
        2.1,
        mouth=ep.mouth("ava"),
        blinks=[(P[2].end + 0.05, P[2].end + 0.2)],
        nods=[(0.0, -3.0)],
        name=None,
    )
    card = cv.group(actor.group, "ava-card")
    cv.gate(card, [(LEAVE[3] - 0.05, DURATION)])
    cv.rect(card, 76, 170, 68, 44, "#2F5D8C", cv.ink, 2.5, radius=5)


def walks_past(g):
    """Ava crossing behind him, deaf, while he calls."""
    walk = cv.group(g, "ava-walking", x=1400, y=800)
    cv.gate(walk, [(P[7].start - 0.1, P[7].end + 0.2)])
    cv.keys(walk, "x", [(P[7].start - 0.1, 1400.0), (P[7].end + 0.2, -340.0)], hold=False)
    n = int((P[7].end - P[7].start) / 0.2) + 2
    cv.keys(walk, "y", [(P[7].start + 0.2 * k, 800.0 if k % 2 else 786.0) for k in range(n)], hold=False)
    ep.perform(
        cast.Barista(cv, tag="ava-walking-character"), walk, 0, 0, 1.2, mouth=[(0.0, "rest")], name=None, legs=True
    )


def behind(g):
    far_side(g)
    walks_past(g)
    milo_in_chair(g)
    ava_elbow(g)


finish = locations.finish(cv, ep.comp)
shot = cv.group(finish, "camera")
camera.anchor(shot, 340, 700, place=True)
PUNCH, CRASH = 1.22, 1.3
LOOK = NAPKIN - 1.05  # the crash zoom lands as he looks at the napkin
zoom = [(0.0, 1.0), (BITES[2], 1.0), (BITES[2] + 0.12, PUNCH), (EMPTY - 1 / FPS, PUNCH), (EMPTY, 1.0)]
zoom += [(LOOK, 1.0), (LOOK + 0.15, CRASH)]
cv.keys(shot, "scaleX", zoom, hold=False)
cv.keys(shot, "scaleY", zoom, hold=False)
locations.cafe(cv, shot, behind_counter=behind, at_counter=on_table)
signature.code(cv, shot, 760, 1600, 11, color="#D9B48A", align="end")  # Milo's head hides the one by the menu board

spoken = ep.captions(ep.spoken_captions(), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-air", FAKE, "A bite of nothing"), ("marker-napkin", NAPKIN, "The napkin")])
ep.instagram(POSTS["how-is-everything"])
ep.finish()

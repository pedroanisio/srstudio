#!/usr/bin/env python3
"""Headphones, built with srstudio: she has earbuds in, and the whole store knows about Harold.

    srstudio record headphones PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build headphones PROJECT    # → PROJECT/headphones.scene.xml

Rosa wheels in, serene, earbuds in, shouting. Milo freezes with a box. "THE RASH IS BETTER." She reads a tin. "NO, THE
OTHER RASH." He edges away and she follows the same way. Harold's mole. The shelves stop shaking when she stops. Wider:
the aisle has stopped, a row of still people. "HE SHOWED THE NEIGHBORS." Milo taps her arm and mimes the earbuds. She
takes one out. "Am I, dear?" in her real, tiny voice. She looks down the aisle and they all look back, in no sound at
all. The loudspeaker clicks on, soft and kind: oatmeal baths are on aisle nine.

The first frame already moves (arm B of the ``sp-hook_motion`` test): her cart is rolling in. It declares no engine safe
area, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from headphones_audio import INTERVIEW
from instagram_posts import POSTS
from srstudio import CAFE, Episode, EpisodeSpec, camera, cast, cutout_odds, cutout_store, foley, locations, signature
from srstudio import interview as iv_audio
from srstudio.cutout_reach import reach

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="headphones",
        title=INTERVIEW.title,
        description="Own-worst-enemy comedy: a woman with earbuds in shouts her husband's rash down a supermarket "
        "aisle. Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=26411,
        background="#E7E3D6",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
t, cv = ep.t, ep.cv
P = t.phrases
DURATION = t.duration
LOOK, CHIME = float(t.meta["look"]), float(t.meta["chime"])
EPS = 1 / 30
ROSA_Y, ROSA_SCALE = 560.0, 1.5
MILO_Y, MILO_SCALE = 570.0, 1.75
FLOOR = 1409.0  # where her cart's wheels stand

WIDE = P[3].start - 0.08  # the aisle has stopped
TIN_UP = P[1].start - 0.30
CLOSE = P[4].start - 0.75  # back to the two of them for the tap
EDGES = (P[2].start + 0.25, P[2].start + 1.25)  # he edges away, twice
FOLLOWS = (EDGES[0] + 0.45, EDGES[1] + 0.45)
TAKES_OUT = P[5].start - 0.80  # the hand goes to her ear
BUD_OUT = P[5].start - 0.38

rattle = [P[0].start + 0.07 * n for n in range(int((P[2].end - P[0].start) / 0.07))]
foley.write_bursts(
    ROOT / "assets" / "wheels.wav", [0.0, FOLLOWS[0], FOLLOWS[1]], DURATION, foley.CART_WHEELS, seed=26412
)
foley.write_bursts(ROOT / "assets" / "rattle.wav", rattle, DURATION, foley.COIN, seed=26413)
foley.write_bursts(ROOT / "assets" / "click.wav", [CHIME - 0.08], DURATION, foley.REMOTE_CLICK, seed=26414)
foley.write_tones(ROOT / "assets" / "chime.wav", [CHIME], DURATION, foley.CHIME)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("wheels", "assets/wheels.wav", {"role": "effects", "gain": -5}),
        ("rattle", "assets/rattle.wav", {"role": "effects", "gain": -24}),
        ("click", "assets/click.wav", {"role": "effects", "gain": -8}),
        ("chime", "assets/chime.wav", {"role": "effects", "gain": -9}),
    ]
)


def shake():
    """The shelves tremble while she shouts, and stop dead with her."""
    keys = [(0.0, 0.0), (P[0].start, 0.0)]
    at, sign = P[0].start + 0.04, 1
    while at < P[2].end:
        keys.append((at, 3.0 * sign))
        at += 0.04
        sign = -sign
    return [*keys, (P[2].end + 0.02, 0.0)]


def rosa_cart(g):
    cutout_odds.store_box(cv, g, -170, -260, id="cart-box")
    cutout_odds.tin_of_peas(cv, g, 20, -230, id="cart-tin-a")
    cutout_odds.tin_of_peas(cv, g, 112, -226, id="cart-tin-b")
    # The cart stays in the close shots that lose the shelf's own marks.
    signature.cactus(cv, g, -30, -176, scale=0.5)
    signature.code(cv, g, -160, -200, 9, color="#FBF8F0")


def other_cart(g):
    cutout_odds.store_box(cv, g, 60, -250, id="other-cart-box")


def milo(g):
    at = cv.group(g, "milo-at", x=790)
    keys = [(0.0, 790.0), (EDGES[0], 790.0), (EDGES[0] + 0.3, 840.0), (EDGES[1], 840.0), (EDGES[1] + 0.3, 880.0)]
    keys += [(CLOSE - EPS, 880.0), (CLOSE, 790.0)]
    cv.keys(at, "x", keys, hold=False)
    actor = cast.Customer(cv, tag="milo-character")
    ep.perform(
        actor,
        at,
        0,
        MILO_Y,
        MILO_SCALE,
        mouth=ep.mouth("milo"),
        blinks=[(P[2].end - 0.4, P[2].end - 0.26), (P[5].end + 0.5, P[5].end + 0.64)],
        free_arms=("left", "right"),
    )
    side = [(0.0, 0.0), (0.5, 0.0), (0.6, -12.0), (P[1].end + 0.1, -12.0), (P[1].end + 0.2, 0.0), (CLOSE, 0.0)]
    cv.keys(actor.eyes, "x", [*side, (CLOSE + 0.1, -14.0)], hold=False)
    hands = cv.group(at, "milo-hands", x=0, y=MILO_Y, scaleX=MILO_SCALE, scaleY=MILO_SCALE)
    rest = (-66.0, 214.0)
    arm = (-146.0, 206.0)  # her sleeve, from where he stands for the tap
    ear = (-108.0, 8.0)
    tap = CLOSE + 0.08
    left = [(0.0, *rest), (tap, *rest), (tap + 0.2, *arm), (tap + 0.3, arm[0] + 12, arm[1] - 8), (tap + 0.4, *arm)]
    left += [(tap + 0.5, arm[0] + 12, arm[1] - 8), (P[4].start, arm[0] + 12, arm[1] - 8)]
    left += [(P[4].start + 0.25, *ear), (P[4].start + 0.5, ear[0], ear[1] + 10), (P[4].start + 0.75, *ear)]
    left += [(P[4].end + 0.1, *ear), (P[4].end + 0.4, *rest)]
    reach(cv, hands, "milo-left-arm", (-73, 146), left, width=5.0, hand=44.0)
    _, grip = reach(cv, hands, "milo-right-arm", (73, 146), [(0.0, 70.0, 222.0)], width=5.0, hand=44.0)
    cutout_odds.store_box(cv, grip, 0, -20, scale=0.72, id="milo-box")


def rosa(g):
    at = cv.group(g, "rosa-at", x=-420)
    x = [(0.0, -420.0), (0.8, 300.0), (FOLLOWS[0], 300.0), (FOLLOWS[0] + 0.3, 360.0), (FOLLOWS[1], 360.0)]
    x += [(FOLLOWS[1] + 0.3, 420.0)]
    cv.keys(at, "x", x, hold=False)
    roll = [(0.07 * n, 3.0 if n % 2 else -3.0) for n in range(12)] + [(0.84, 0.0)]
    cv.keys(at, "y", roll, hold=False)
    actor = cast.Rosa(cv, tag="rosa-character")
    spans = [(P[i].start, P[i].end) for i in (0, 1, 2, 3, 5)]
    ep.perform(
        actor,
        at,
        0,
        ROSA_Y,
        ROSA_SCALE,
        mouth=ep.mouth("rosa", speaking=spans),
        blinks=[(1.0, 1.14), (P[2].start + 1.5, P[2].start + 2.3), (P[3].start + 0.5, P[3].start + 0.64)],
        legs="standing",
        free_arms=("left", "right"),
        stitch=None,
    )
    down = [(0.0, 0.0), (TIN_UP + 0.1, 0.0), (TIN_UP + 0.2, 12.0), (P[1].end + 0.4, 12.0), (P[1].end + 0.5, 0.0)]
    down += [(P[6].start + 0.1, 0.0), (P[6].start + 0.25, -14.0)]  # up at the voice in the ceiling
    cv.keys(actor.eyes, "y", down, hold=False)
    glance = [(0.0, 0.0), (LOOK - 0.75, 0.0), (LOOK - 0.65, -16.0), (LOOK - 0.3, -16.0), (LOOK - 0.2, 16.0)]
    glance += [(CHIME, 16.0), (CHIME + 0.5, 0.0)]
    cv.keys(actor.eyes, "x", glance, hold=False)
    still_in = cv.group(actor.head, "rosa-bud-left")
    cutout_odds.earbud(cv, still_in, -102, 8, id="left-bud")
    going = cv.group(actor.head, "rosa-bud-right")
    cv.gate(going, [(0.0, BUD_OUT)])
    cutout_odds.earbud(cv, going, 102, 8, flip=True, id="right-bud")
    cutout_store.shopping_cart(cv, at, 0, FLOOR, contents=rosa_cart, scale=0.85, id="rosa-cart")
    hands = cv.group(at, "rosa-hands", x=0, y=ROSA_Y, scaleX=ROSA_SCALE, scaleY=ROSA_SCALE)
    bar_left, bar_right = (-120.0, 232.0), (120.0, 232.0)
    tin = (86.0, 150.0)
    ear = (112.0, 24.0)
    lap = (116.0, 150.0)
    right = [(0.0, *bar_right), (TIN_UP - 0.2, *bar_right), (TIN_UP, 60.0, 300.0), (TIN_UP + 0.25, *tin)]
    right += [(P[1].end + 0.45, *tin), (P[1].end + 0.7, *bar_right), (TAKES_OUT, *bar_right)]
    right += [(TAKES_OUT + 0.35, *ear), (BUD_OUT + 0.05, *ear), (BUD_OUT + 0.35, *lap)]
    reach(cv, hands, "rosa-left-arm", (-66, 146), [(0.0, *bar_left)], width=5.0, hand=36.0)
    _, grip = reach(cv, hands, "rosa-right-arm", (66, 146), right, width=5.0, hand=36.0)
    held = cv.group(grip, "rosa-tin")
    cv.gate(held, [(TIN_UP, P[1].end + 0.7)])
    cutout_odds.tin_of_peas(cv, held, 0, -20, scale=0.72, id="held-tin")
    bud = cv.group(grip, "rosa-bud-held")
    cv.gate(bud, [(BUD_OUT, DURATION)])
    cutout_odds.earbud(cv, bud, 0, -30, id="held-bud")


def shoppers(g):
    """The aisle, stopped: everyone in it holding what they were holding."""
    people = cv.group(g, "shoppers")
    cv.gate(people, [(WIDE, CLOSE), (LOOK, CHIME)])
    feet = 1262.0
    row = [  # three people, once each: Milo and Rosa stand in the same aisle. Spread for the wide, closer for the look.
        (cast.Manager, -120.0, 330.0, {"legs": "standing"}, 648.0),
        (cast.Barista, 10.0, 570.0, {"name": None, "legs": True}, 489.0),
        (cast.Candidate, 1250.0, 780.0, {"legs": "standing"}, 648.0),
    ]
    for n, (kind, wide, close, extras, tall) in enumerate(row):
        scale = 0.9
        at = cv.group(people, f"shopper-{n}-at", x=wide)
        cv.keys(at, "x", [(0.0, wide), (LOOK, close)])
        actor = kind(cv, tag=f"shopper-{n}")
        ep.perform(actor, at, 0.0, feet - tall * scale, scale, mouth=[(0.0, "rest")], **extras)
        if n == 0:
            cutout_store.hand_basket(cv, at, -70, feet + 30, scale=0.7, id="shopper-basket")
    cutout_store.shopping_cart(cv, people, 790, feet + 60, contents=other_cart, scale=0.6, id="shopper-cart")


def in_aisle(g):
    lower = cv.group(g, "floor-below")  # a wide shot sees past the floor's foot
    cv.gate(lower, [(WIDE, CLOSE), (LOOK, CHIME)])
    cv.rect(lower, -900, 2130, 2900, 1200, "#B7B3A5")
    shoppers(g)
    duo = cv.group(g, "the-two-of-them")
    cv.gate(duo, [(0.0, LOOK), (CHIME, DURATION)])
    milo(duo)
    rosa(duo)


finish = locations.finish(cv, ep.comp)
shot = cv.group(finish, "camera")
MEDIUM = (1.0, 0.0, 0.0)
ON_MILO = (1.28, 540 - 1.28 * 880, 640 - 1.28 * 570)
AISLE = (0.65, 189.0, 195.0)
ON_ROSA = (1.8, 540 - 1.8 * 420, 640 - 1.8 * 560)
LOOKING = (1.0, 0.0, 0.0)
camera.reframe(
    cv,
    shot,
    [
        (0.0, *MEDIUM),
        (P[1].end + 0.05, *ON_MILO),
        (P[2].start - 0.1, *MEDIUM),
        (WIDE, *AISLE),
        (CLOSE, *MEDIUM),
        (TAKES_OUT, *ON_ROSA),
        (LOOK, *LOOKING),
        (CHIME, *ON_ROSA),
    ],
)
cutout_store.store_aisle(cv, shot, in_aisle=in_aisle, drift=shake())

spoken = ep.captions(ep.spoken_captions(), x=80, y=1470, width=920, size=54)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-aisle", WIDE, "The aisle has stopped"), ("marker-look", LOOK, "They look back")])
ep.instagram(POSTS["headphones"])
ep.finish()

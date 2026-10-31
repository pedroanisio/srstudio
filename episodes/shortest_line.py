#!/usr/bin/env python3
"""Shortest Line, built with srstudio: she is ahead of him in every line, and she likes his face when it happens.

    srstudio record shortest-line PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build shortest-line PROJECT    # → PROJECT/shortest-line.scene.xml

Milo slides into the shortest line with one thing. Rosa's cart rolls in ahead of him. "I've just got a few, dear." She
opens her purse and counts; he moves. Same framing, next number: "Hello again." Third lane: he looks left, she is there;
he looks right, she is in front. "You were over there." "Was I?" One coin on the belt. After a while, a second. He
looks in her cart: one tin of peas. "You don't need anything, do you?" Her glasses catch the light. "I'm seventy-nine,
dear. I've got nowhere to be." She leans in. "I like your face when it happens." She rolls on, over her shoulder:
"Same time tomorrow?" It stays on him.

The first frame already moves (arm B of the ``sp-hook_motion`` test): he is sliding in. Ahead, towards the till, is
screen right. It declares no engine safe area, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from shortest_line_audio import INTERVIEW
from srstudio import CAFE, Episode, EpisodeSpec, camera, cast, cutout_home, cutout_odds, cutout_store, foley, locations
from srstudio import interview as iv_audio
from srstudio.cutout_reach import reach

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="shortest-line",
        title=INTERVIEW.title,
        description="Service comedy: the old lady ahead of you in every line you pick is doing it on purpose. Native "
        "vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=26421,
        background="#E7E3D6",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
t, cv = ep.t, ep.cv
P = t.phrases
DURATION = t.duration
LEFT, LANE_2, LEFT_AGAIN, LANE_3 = (float(t.meta[k]) for k in ("left", "second_lane", "left_again", "third_lane"))
COIN_SHOT, COIN_2, TIN, TURN = (float(t.meta[k]) for k in ("coin_shot", "second_coin", "tin", "turn"))
EPS = 1 / 30
ROSA_Y, ROSA_SCALE = 700.0, 1.5
MILO_Y, MILO_SCALE = 700.0, 1.75
FLOOR = 1549.0
LANE_TOP = 1290.0
AHEAD = 790.0  # where she stands, every time
BACK_X, THIRD_X = 300.0, 420.0  # where he stands
OVER_THERE = 70.0

ROLLS = (0.20, LANE_2 + 0.65)  # she rolls in
ROLL = 0.50
LOOK_LEFT = LANE_3 + 0.55
LOOK_RIGHT = LANE_3 + 1.05
COIN_1 = P[5].start - 0.05
GLINT = P[7].start - 0.35
INSERT_BACK = P[6].start + 0.50
LEAN = P[7].end + 0.25
TO_MILO = P[8].end + 0.05
GOES = P[9].start - 0.35
COUNT = [P[0].end + 0.25, P[0].end + 0.60, P[0].end + 0.95]

foley.write_bursts(
    ROOT / "assets" / "wheels.wav", [ROLLS[0], ROLLS[1], LOOK_RIGHT, GOES], DURATION, foley.CART_WHEELS, seed=26422
)
foley.write_bursts(ROOT / "assets" / "coin.wav", [*COUNT, COIN_1, COIN_2], DURATION, foley.COIN, seed=26423)
foley.write_whoosh(
    ROOT / "assets" / "slide.wav", [0.0, LEFT, LANE_2, LEFT_AGAIN, LANE_3], DURATION, length=0.2, seed=26424
)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("wheels", "assets/wheels.wav", {"role": "effects", "gain": -5}),
        ("coin", "assets/coin.wav", {"role": "effects", "gain": -3}),
        ("slide", "assets/slide.wav", {"role": "effects", "gain": -14}),
    ]
)


def rosa_x():
    """Off frame, or ahead of him, or over there, or ahead of him again; never seen crossing."""
    keys = [(0.0, 1320.0), (ROLLS[0], 1320.0), (ROLLS[0] + ROLL, AHEAD), (LEFT, AHEAD), (LANE_2 - EPS, AHEAD)]
    keys += [
        (LANE_2, 1320.0),
        (ROLLS[1], 1320.0),
        (ROLLS[1] + ROLL, AHEAD),
        (LANE_3 - EPS, AHEAD),
        (LANE_3, OVER_THERE),
    ]
    keys += [(LOOK_RIGHT - EPS, OVER_THERE), (LOOK_RIGHT, AHEAD), (LEAN, AHEAD), (LEAN + 0.35, AHEAD - 70.0)]
    return [*keys, (TO_MILO - EPS, AHEAD - 70.0), (TO_MILO, AHEAD), (GOES, AHEAD), (P[9].end + 0.2, 1400.0)]


def rosa(g):
    at = cv.group(g, "rosa-at", x=1320)
    cv.keys(at, "x", rosa_x(), hold=False)
    actor = cast.Rosa(cv, tag="rosa-character")
    blinks = [(P[2].end + 0.6, P[2].end + 0.74), (P[5].end + 0.7, P[5].end + 0.84), (P[8].end - 0.5, P[8].end - 0.36)]
    ep.perform(
        actor,
        at,
        0,
        ROSA_Y,
        ROSA_SCALE,
        mouth=ep.mouth("rosa"),
        blinks=blinks,
        legs="standing",
        free_arms=("left", "right"),
        stitch=None,
    )
    side = [(0.0, 0.0), (LOOK_RIGHT + 0.1, 0.0), (LOOK_RIGHT + 0.2, -14.0), (COIN_SHOT - 0.1, -14.0), (COIN_SHOT, 0.0)]
    side += [(TURN, 0.0), (TURN + 0.1, -16.0), (DURATION, -16.0)]
    cv.keys(actor.eyes, "x", side, hold=False)
    count = [(COUNT[0] - 0.2, 0.0), (COUNT[0] - 0.1, 12.0), (LEFT, 12.0), (LEFT + 0.1, 0.0)]
    coins = [(COIN_SHOT, 0.0), (COIN_SHOT + 0.1, 12.0), (TURN, 12.0), (TURN + 0.1, 0.0)]
    cv.keys(actor.eyes, "y", [(0.0, 0.0), *count, *coins], hold=False)
    cutout_odds.glasses_glint(cv, actor.head, at=GLINT, seconds=0.45)
    cutout_store.shopping_cart(cv, at, 0, FLOOR, scale=0.85, id="rosa-cart")


def rosa_hands(g):
    """Her arms, over the belt: one hand holds the purse up, the other counts and lays the coins down."""
    at = cv.group(g, "rosa-hands-at", x=1320)
    cv.keys(at, "x", rosa_x(), hold=False)
    hands = cv.group(at, "rosa-hands", x=0, y=ROSA_Y, scaleX=ROSA_SCALE, scaleY=ROSA_SCALE)
    bar_left, bar_right = (-120.0, 232.0), (120.0, 232.0)
    purse = (80.0, 170.0)
    dip = (62.0, 150.0)
    spot = (-66.0, 437.0)
    spot_2 = (-30.0, 443.0)
    right = [(0.0, *bar_right), (ROLLS[0] + ROLL, *bar_right), (ROLLS[0] + ROLL + 0.3, *purse)]
    right += [(ROLLS[1], *purse), (ROLLS[1] + 0.05, *bar_right), (ROLLS[1] + ROLL, *bar_right)]
    right += [(ROLLS[1] + ROLL + 0.3, *purse), (GOES, *purse), (GOES + 0.3, *bar_right)]
    left = [(0.0, *bar_left), (ROLLS[0] + ROLL + 0.3, *bar_left)]
    for c in COUNT:
        left += [(c - 0.15, *dip), (c, dip[0], dip[1] + 16), (c + 0.15, *dip)]
    left += [(LEFT, -100.0, 200.0), (COIN_SHOT, -100.0, 200.0), (COIN_1 - 0.3, spot[0], spot[1] - 70), (COIN_1, *spot)]
    left += [(COIN_1 + 0.3, spot[0], spot[1] - 70), (COIN_2 - 0.4, spot_2[0], spot_2[1] - 70), (COIN_2, *spot_2)]
    left += [(COIN_2 + 0.3, spot_2[0], spot_2[1] - 70), (COIN_2 + 0.6, *bar_left), (DURATION, *bar_left)]
    _, counting = reach(cv, hands, "rosa-left-arm", (-66, 146), left, width=5.0, hand=36.0)
    for n, span in enumerate(((COIN_SHOT, COIN_1), (COIN_1 + 0.3, COIN_2))):
        coin = cv.group(counting, f"coin-in-hand-{n}", x=0, y=8)
        cv.gate(coin, [span])
        cutout_odds.small_coin(cv, coin, 0, 0, scale=0.7, id=f"held-coin-{n}")
    _, grip = reach(cv, hands, "rosa-right-arm", (66, 146), right, width=5.0, hand=36.0)
    held = cv.group(grip, "rosa-purse")
    cv.gate(held, [(ROLLS[0] + ROLL + 0.3, GOES)])
    cutout_odds.coin_purse(cv, held, -10, -44, opens=[(COUNT[0] - 0.2, LEFT), (COIN_SHOT, COIN_2 + 0.3)], scale=0.8)


def coins(g):
    for n, (x, y, at) in enumerate(((691.0, 1356.0, COIN_1), (745.0, 1365.0, COIN_2))):
        down = cv.group(g, f"belt-coin-{n}")
        cv.gate(down, [(at, DURATION)])
        cutout_odds.small_coin(cv, down, x, y, id=f"coin-{n}")


def milo(g):
    at = cv.group(g, "milo-at", x=1000)
    x = [(0.0, 1000.0), (0.35, BACK_X), (LEFT, BACK_X), (LEFT + 0.25, -320.0), (LANE_2 - EPS, -320.0), (LANE_2, 1000.0)]
    x += [(LANE_2 + 0.35, BACK_X), (LEFT_AGAIN, BACK_X), (LEFT_AGAIN + 0.25, -320.0), (LANE_3 - EPS, -320.0)]
    x += [(LANE_3, 1000.0), (LANE_3 + 0.35, THIRD_X)]
    cv.keys(at, "x", x, hold=False)
    actor = cast.Customer(cv, tag="milo-character")
    blinks = [(P[2].end + 0.4, P[2].end + 0.54), (P[5].end + 1.0, P[5].end + 1.14), (DURATION - 0.7, DURATION - 0.56)]
    ep.perform(actor, at, 0, MILO_Y, MILO_SCALE, mouth=ep.mouth("milo"), blinks=blinks, free_arms=("left", "right"))
    glance = P[0].end + 0.65
    keys = [(0.0, 0.0), (ROLLS[0] + ROLL, 0.0), (ROLLS[0] + ROLL + 0.1, 14.0), (glance, 14.0), (glance + 0.1, -14.0)]
    keys += [(LEFT, -14.0), (LANE_2 + 0.5, 0.0), (ROLLS[1] + ROLL, 0.0), (ROLLS[1] + ROLL + 0.1, 14.0)]
    keys += [(LOOK_LEFT - 0.1, 14.0), (LOOK_LEFT, -14.0), (LOOK_RIGHT - 0.1, -14.0), (LOOK_RIGHT, 14.0)]
    cv.keys(actor.eyes, "x", [*keys, (DURATION, 14.0)], hold=False)
    down = [(0.0, 0.0), (COIN_2 + 0.3, 0.0), (COIN_2 + 0.4, 10.0), (P[6].start, 10.0), (P[6].start + 0.1, 0.0)]
    cv.keys(actor.eyes, "y", down, hold=False)
    hands = cv.group(at, "milo-hands", x=0, y=MILO_Y, scaleX=MILO_SCALE, scaleY=MILO_SCALE)
    reach(cv, hands, "milo-left-arm", (-73, 146), [(0.0, -100.0, 250.0)], width=5.0, hand=44.0)
    _, grip = reach(cv, hands, "milo-right-arm", (73, 146), [(0.0, 112.0, 200.0)], width=5.0, hand=44.0)
    cutout_odds.store_box(cv, grip, 8, 120, scale=0.42, id="milo-one-thing")
    cutout_store.hand_basket(cv, grip, 0, 178, scale=0.6, id="milo-basket")


def one_tin(g):
    cutout_odds.tin_of_peas(cv, g, 20, -226, id="the-tin")


def insert(g):
    """The cart, from above the handle: all those coins, for this."""
    cut = cv.group(g, "cart-insert")
    cv.gate(cut, [(TIN, INSERT_BACK)])
    cv.rect(cut, -10, -10, 1100, 1940, cv.grad("insert-floor", [(0, "#DAD6C8"), (1, "#B7B3A5")], (0, 0, 0, 1)))
    cutout_store.shopping_cart(cv, cut, 540, 1420, contents=one_tin, scale=1.55, id="insert-cart")


finish = locations.finish(cv, ep.comp)
shot = cv.group(finish, "camera")
MEDIUM = (1.0, 0.0, 0.0)
ON_COIN = (2.3, 540 - 2.3 * 745, 860 - 2.3 * 1340)
ON_ROSA = (1.7, 540 - 1.7 * AHEAD, 640 - 1.7 * 690)
LEANT = (1.7, 540 - 1.7 * (AHEAD - 70), 640 - 1.7 * 690)
ON_MILO = (1.6, 540 - 1.6 * THIRD_X, 640 - 1.6 * 700)
camera.reframe(
    cv,
    shot,
    [
        (0.0, *MEDIUM),
        (COIN_SHOT, *ON_COIN),
        (COIN_2 + 0.35, *MEDIUM),
        (P[6].end + 0.1, *ON_ROSA),
        (LEAN, *LEANT),
        (TO_MILO, *ON_MILO),
    ],
)
cutout_home.shop_till(cv, cv.group(shot, "till-at", y=170))  # the counter behind them drops to the belt
cutout_odds.lane_sign(cv, shot, 540, 250, scale=1.4, numbers=[(0.0, "4"), (LANE_2, "5"), (LANE_3, "6")])
milo(shot)
rosa(shot)
cutout_store.checkout_lane(cv, shot, LANE_TOP, running=(0.0, 0.6))
coins(shot)
rosa_hands(shot)
insert(finish)

spoken = ep.captions(ep.spoken_captions(), x=80, y=1484, width=920, size=54)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-third", LANE_3, "The third lane"), ("marker-tin", TIN, "One tin of peas")])
ep.instagram(POSTS["shortest-line"])
ep.finish()

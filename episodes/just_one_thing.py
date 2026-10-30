#!/usr/bin/env python3
"""Just One Thing, built with srstudio: he went in for light bulbs.

    srstudio record just-one-thing PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build just-one-thing PROJECT    # → PROJECT/just-one-thing.scene.xml

Already walking, a very small basket: "I only need light bulbs." A cart: a lamp, three candles, a plant. "We do need a
plant." A bigger cart: a ladder, a kayak. "It was on sale." Bigger again: a paddle, a life ring. "That's just safety."
At the till the screen says $412, then rolls on, and he is proud of it. At home, in the dark, sitting in the kayak:
click. Click. Click. A long nothing. Click. It stops on his eyes.

He moves from the first frame (arm B of the ``sp-hook_motion`` test). It declares no engine safe area, so captions are
placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from just_one_thing_audio import INTERVIEW
from srstudio import OFFICE, Episode, EpisodeSpec, cast, cutout_store, locations, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="just-one-thing",
        title="Just One Thing",
        description="Shopping comedy: a man goes into a big store for light bulbs and comes out with everything else. "
        "Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        **iv_audio.spec_font(INTERVIEW.font, project_root(__file__)),
        seed=26201,
        background="#0E0F14",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv = ep.t, ep.cv
TILL = float(t.meta["till"])
CLICKS = tuple(float(x) for x in t.meta["clicks"])
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
EYES = (540, 716)  # his eyes at home, in the frame

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))
DARK = spans["dark"][0][0]


def walking(g, angle: str, reach: float = 11.0):
    """Bob ``g`` at a walking pace through the shot's span, from its first frame."""
    a, b = spans[angle][0]
    cv.gate(g, [(a, b)])
    keys, at, up = [], a, True
    while at < b:
        keys.append((at, 0.0 if up else reach))
        at += 0.26
        up = not up
    cv.keys(g, "y", keys, hold=False)


def milo(g, name: str, x, y, scale, *, seated: bool = False, smile=(), **kw):
    actor = cast.Customer(cv, tag=f"{name}-character", seated=seated)
    ep.perform(actor, g, x, y, scale, mouth=ep.mouth("milo", smile=smile), **kw)


def plant(g, x, y, scale, id: str):
    """The office plant standing on (``x``, ``y``); it is drawn at one size in absolute coordinates."""
    holder = cv.group(g, f"{id}-holder", x=x - 80 * scale, y=y - 1139 * scale, scaleX=scale, scaleY=scale)
    props.plant(cv, holder, id=id)


def first_cart(g):
    cutout_store.table_lamp(cv, g, -170, -190, id="cart-lamp")
    cutout_store.taper_candles(cv, g, 0, -190, id="cart-candles")
    plant(g, 170, -190, 0.62, "cart-plant")


def bigger_cart(g):
    cutout_store.kayak(cv, g, 100, -860, length=1500, rotation=-64, id="bigger-kayak")
    cutout_store.step_ladder(cv, g, 230, -180, height=780, id="bigger-ladder")
    cutout_store.table_lamp(cv, g, -210, -190, id="bigger-lamp")
    cutout_store.taper_candles(cv, g, -60, -190, id="bigger-candles")
    plant(g, 90, -190, 0.5, "bigger-plant")


def biggest_cart(g):
    cutout_store.kayak(cv, g, 150, -860, length=1500, rotation=-64, id="biggest-kayak")
    cutout_store.paddle(cv, g, -60, -560, length=760, rotation=14, id="biggest-paddle")
    cutout_store.step_ladder(cv, g, 250, -180, height=820, id="biggest-ladder")
    cutout_store.table_lamp(cv, g, -220, -190, id="biggest-lamp")
    cutout_store.taper_candles(cv, g, -70, -190, id="biggest-candles")
    plant(g, 90, -190, 0.5, "biggest-plant")


def in_aisle(g):
    basket = cv.group(g, "shot-basket")
    walking(basket, "basket")
    milo(basket, "basket", 470, 660, 2.3, blinks=[(L[0].end + 0.05, L[0].end + 0.18)], held_cup=())
    swing = cv.group(basket, "basket-swing", x=778, y=1070)
    a, b = spans["basket"][0]
    keys, at, sign = [], a, 1
    while at < b:
        keys.append((at, 7.0 * sign))
        at += 0.52
        sign = -sign
    cv.keys(swing, "rotation", keys, hold=False)
    cutout_store.hand_basket(cv, swing, 0, 170, scale=0.62, id="tiny-basket")

    cart = cv.group(g, "shot-cart")
    walking(cart, "cart", 8.0)
    milo(cart, "cart", 540, 530, 1.75)
    cutout_store.shopping_cart(cv, cart, 540, 1400, contents=first_cart, id="first-cart")

    bigger = cv.group(g, "shot-bigger")
    walking(bigger, "bigger", 8.0)
    milo(bigger, "bigger", 330, 470, 1.6)
    cutout_store.shopping_cart(cv, bigger, 540, 1410, contents=bigger_cart, scale=1.2, id="bigger-cart")

    biggest = cv.group(g, "shot-biggest")
    walking(biggest, "biggest", 8.0)
    milo(biggest, "biggest", 250, 500, 1.5)
    cutout_store.shopping_cart(cv, biggest, 560, 1416, contents=biggest_cart, scale=1.34, id="biggest-cart")
    cutout_store.life_ring(cv, biggest, 560, 980, scale=1.1, id="biggest-ring")

    till = cv.group(g, "shot-till")
    cv.gate(till, spans["till"])
    milo(
        till,
        "till",
        320,
        700,
        2.5,
        blinks=[(TILL + 0.9, TILL + 1.04)],
        nods=[(0, 0), (TILL, 0), (TILL + 0.8, -4), (TILL + 1.8, -9)],
        smile=[(TILL + 1.0, DARK)],
    )


def front(g):
    till = cv.group(g, "front-till")
    cv.gate(till, spans["till"])
    cutout_store.checkout_lane(cv, till, 1200, running=(TILL, DARK))
    roll = 0.35
    amounts = ("$412", "$538", "$697", "$874", "$1,046", "$1,204")
    readings = ((0, amounts[0], "TOTAL"), *((TILL + 0.45 + k * roll, a, "TOTAL") for k, a in enumerate(amounts) if k))
    cutout_store.long_receipt(cv, till, 790, 1150, length=800, printing=(TILL + 0.45, DARK), id="till-receipt")
    props.card_reader(cv, till, 790, 1210, readings=readings, scale=1.5)


finish = locations.finish(cv, ep.comp)
cutout_store.store_aisle(
    cv, finish, in_aisle=in_aisle, front=front, shots=[(0.0, DARK)], drift=[(0.0, 0.0), (TILL, -3900.0)]
)

dark = cv.group(finish, "the-dark")
cv.gate(dark, spans["dark"])
cv.rect(dark, -900, -900, 2900, 3700, "#3A4150")


def in_the_kayak(g):
    milo(g, "home", 0, -500, 1.75, seated=True)
    cv.rect(g, -1500, 24, 3000, 1400, "#2A2F3A")  # the floor, over his legs: the hull's near side is drawn on it


cutout_store.kayak(cv, dark, 540, 1200, length=1040, beam=150, rider=in_the_kayak, id="home-kayak")
cv.rect(dark, -900, -900, 2900, 3700, "#05060A", opacity=0.93)
dim = cv.group(dark, "dim-switch", opacity=0.45)
cutout_store.light_switch(cv, dim, 140, 760, flips=CLICKS, id="dead-switch")
cutout_store.dark_eyes(
    cv,
    dark,
    *EYES,
    scale=0.72,
    blinks=[(CLICKS[0] + 0.25, CLICKS[0] + 0.37), (CLICKS[2] + 1.0, CLICKS[2] + 1.12)],
    glances=[
        (0.0, 0.0),
        (CLICKS[0] - 0.15, 0.0),
        (CLICKS[0], -24.0),
        (CLICKS[3] + 0.5, -24.0),
        (CLICKS[3] + 0.75, 0.0),
    ],
)
push = (CLICKS[2] + 0.4, DURATION)
for prop, rest, to in (
    ("scaleX", 1.0, 1.8),
    ("scaleY", 1.0, 1.8),
    ("x", 0.0, 540 - EYES[0] * 1.8),
    ("y", 0.0, 760 - EYES[1] * 1.8),
):
    cv.keys(dark, prop, [(push[0], rest), (push[1], to)], hold=False)

specs = [(max(p.start - 0.05, 0.0), p.end + 0.2, p.caption, f"dialogue-{i + 1}") for i, p in enumerate(t.phrases)]
heard = [(at, at + 0.5, "Click.", f"said-click-{k + 1}") for k, at in enumerate(CLICKS)]
spoken = ep.captions(specs + heard, x=80, y=1420, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-till", TILL, "The till"), ("marker-dark", DARK, "The dark")])
ep.instagram(POSTS["just-one-thing"])
ep.finish()

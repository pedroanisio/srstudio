#!/usr/bin/env python3
"""Comedy Cut 05 — The Wi-Fi Password, rebuilt with srstudio: new cast, café and park."""

from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from srstudio import CAFE, Episode, EpisodeSpec, camera, cast, graphics, locations, props

ep = Episode(
    EpisodeSpec(
        slug="wifi-password",
        number="05",
        title="The Wi-Fi Password — Comedy Cut 05",
        description=(
            "New characters Ava the barista, Milo the customer and a park pigeon. Native "
            "café and park locations with ElevenLabs dialogue."
        ),
        signature=False,  # shipped before ADR 0001; the package must reproduce element for element
        root=project_root(__file__),
        seed=52027,
        background="#F0DDC0",
        palette=CAFE,  # Cutout in its warm palette; the café mouth model follows from it
        font_id="font",
        font_credit=None,
        font_license="DejaVu Fonts license; assets/FONT-LICENSE.txt",
        audio_credit="ElevenLabs premade voices Jessica and Liam; original procedural café and park effects.",
    )
)
t, cv, P = ep.t, ep.cv, ep.P
REACTION, ENDING, DURATION, PARK = t.reaction, t.ending, t.duration, t.park_start

# The customer's performance is shared by both instances (café and park bench).
customer_mouth = ep.mouth("customer", smile=[(P(3).end, P(4).start)])
customer_blinks = [
    (P(2).start + 0.21, P(2).start + 0.35),
    (REACTION + 0.10, REACTION + 0.31),
    (P(6).end + 0.40, P(6).end + 0.61),
]
customer_nods = [
    (0, 0),
    (P(2).start, 0),
    (P(2).start + 0.22, 3),
    (P(2).end, 0),
    (REACTION, 0),
    (REACTION + 0.30, -6),
    (PARK, -6),
    (P(6).start, -4),
    (P(6).end, 1),
]

barista = cast.Barista(cv)
customer = cast.Customer(cv)


def on_counter(g):
    delivered = props.coffee_cup(cv, g, 690, 1187, 1.06)
    cv.gate(delivered, [(P(3).start - 0.05, P(3).end + 0.03)])
    cv.keys(delivered, "x", [(0, 690), (P(3).start, 690), (P(3).start + 0.45, 436)], hold=False)


cafe = ep.setup(
    locations.cafe,
    [(0, PARK)],
    behind_counter=lambda g: ep.perform(
        barista,
        g,
        750,
        800,
        1.35,
        mouth=ep.mouth("barista", style=replace(ep.spec.mouth_style, idle="smile")),
        blinks=[(P(1).end + 0.04, P(1).end + 0.18), (P(5).start + 0.31, P(5).start + 0.45)],
        nods=[(0, 0), (P(1).start, 0), (P(1).start + 0.22, -3), (P(1).end, 0), (P(5).start, 0), (P(5).end, -4)],
    ),
    on_counter=on_counter,
    at_counter=lambda g: ep.perform(
        customer,
        g,
        270,
        1035,
        1.53,
        mouth=customer_mouth,
        blinks=customer_blinks,
        nods=customer_nods,
        held_cup=[(P(3).end - 0.05, PARK)],
    ),
)

# Native camera reframing: establishing shot, alternating new characters, reaction.
moves = []
for cut in t.cuts:
    if cut.angle == "park-bench":
        continue
    if cut.angle == "cafe-wide":
        sx, tx, ty = 1.0, 0, 0
    elif cut.angle == "barista":
        sx = 1.55
        tx = 540 - 750 * sx
        ty = 775 - 800 * sx
    elif cut.angle == "customer":
        sx = 1.40
        tx = 540 - 270 * sx
        ty = 775 - 1035 * sx
    else:
        sx = 1.63
        tx = 540 - 270 * sx
        ty = 775 - 1035 * sx
    moves.append((cut.time, sx, tx, ty))
camera.reframe(cv, cafe, moves)

seated = cast.Customer(cv, seated=True)
park = ep.setup(
    locations.park,
    [(PARK, DURATION)],
    on_bench=lambda g: ep.perform(
        seated, g, 510, 770, 1.62, mouth=customer_mouth, blinks=customer_blinks, nods=customer_nods
    ),
    beside_bench=lambda g: cast.pigeon(
        cv,
        g,
        nods=[(0, 0), (ENDING, 0), (ENDING + 0.20, -7), (ENDING + 0.35, 0), (ENDING + 0.53, 4), (ENDING + 0.70, 0)],
    ),
)

# Reveal exactly when the barista says 'No spaces'.
REVEAL = t.word_time(5, "no spaces")
graphics.password_card(cv, ep.comp, "CAFÉ WI-FI", "buyacoffeefirst", "NO SPACES", show=(REVEAL, REACTION + 0.30))
graphics.location_slate(cv, ep.comp, "LATER, AT THE PARK", show=(PARK, PARK + 1.00))
graphics.connected_card(cv, ep.comp, "WI-FI CONNECTED", "buyacoffeefirst", show=(PARK + 0.23, DURATION))
graphics.episode_slate(
    cv,
    ep.comp,
    "05",
    "THE WI-FI PASSWORD",
    x=58,
    w=476,
    h=76,
    bg="#355C53",
    badge="#E0B46C",
    badge_h=52,
    number_color=cv.ink,
    title_color=cv.white,
    title_x=82,
    title_w=375,
    title_size=25,
    radius=14,
    badge_radius=8,
    fade=(0.12, 0.72, 1.03),
)

# Caption pages preserve both reveals rather than displaying punchlines early.
specs = []
for i, p in enumerate(ep.phrases):
    end = t.cuts[i + 1].time if i < 5 else REACTION if i == 5 else p.end + 0.12
    if i == 5:
        specs.append((p.start - 0.04, REVEAL, "Buy a coffee first.", "password-setup"))
        specs.append((REVEAL, end, "No spaces.", "password-payoff"))
    else:
        specs.append((p.start - 0.04, end, p.caption, f"line-{i + 1}"))
ep.captions(
    specs,
    x=40,
    y=1488,
    width=1000,
    weight=None,
    line_height="1.12",
    stroke=cv.ink,
    shadow="#00000055",
    highlights={
        "line-7": [("Five bucks for a\n", False), ("spelling lesson.", True)],
        "password-payoff": [("No spaces.", True)],
    },
)
ep.audio_mix(track_id="voice-and-effects")
ep.markers(name="{name}-marker", extra=[("park-location-marker", PARK, "LOCATION TWO: public park bench")])
ep.instagram(POSTS["wifi-password"])
ep.finish()

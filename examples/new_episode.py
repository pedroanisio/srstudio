#!/usr/bin/env python3
"""A new episode from existing parts, plus one new prop and one new location registered on the fly.

    python3 examples/new_episode.py [OUT_DIR]

It writes a synthetic project (dialogue, tone-burst soundtrack, font) and builds ``coffee-review.scene.xml``:
Ava the barista interviews the candidate at the café counter, then the manager reacts in the office.
"""

from __future__ import annotations

import sys
from pathlib import Path

from srstudio import CAFE, CAFE_MOUTH, Episode, EpisodeSpec, cast, graphics, locations, register
from srstudio.sample import Line, write_sample_project

OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out" / "coffee-review"
write_sample_project(
    OUT,
    [
        Line("barista", "Describe your ideal workplace.", 1.4),
        Line("candidate", "Somewhere with free coffee.", 1.3),
        Line("barista", "This is a job interview, not a café.", 1.6),
        Line("candidate", "Then why is the coffee so good?", 1.5),
    ],
    angles=["cafe-wide", "customer", "barista", "customer"],
)


# -- extending: a new prop and a new location, registered so ``srstudio catalog`` lists them --------
@register("prop", "tip_jar", summary="A glass tip jar with a hand-written label", episodes=("example",))
def tip_jar(cv, parent, x, y, scale=1.0):
    g = cv.group(parent, cv.uid("tip-jar"), x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -40, -90, 80, 100, radius=10, fill="#DDEAF2", stroke=cv.ink, sw=3, opacity=0.9)
    cv.rect(g, -44, -98, 88, 14, radius=4, fill="#8C9AA0", stroke=cv.ink, sw=3)
    cv.rect(g, -30, -60, 60, 36, radius=4, fill=cv.white, stroke=cv.ink, sw=2)
    cv.text(g, cv.uid("tip-label"), "TIPS", -30, -62, 60, 36, 18, color=cv.ink)
    return g


@register(
    "location", "cafe_with_tips", summary="The café counter with a tip jar beside the register", episodes=("example",)
)
def cafe_with_tips(cv, parent, behind_counter=None, at_counter=None, shots=None, id="location-cafe-tips"):
    def on_counter(g):
        tip_jar(cv, g, 905, 1190, 1.1)

    return locations.cafe(
        cv, parent, behind_counter=behind_counter, at_counter=at_counter, on_counter=on_counter, shots=shots, id=id
    )


ep = Episode(
    EpisodeSpec(
        slug="coffee-review",
        title="Coffee Review — example",
        description="srstudio example episode",
        root=OUT,
        seed=7,
        background="#F0DDC0",
        palette=CAFE,
        mouth_style=CAFE_MOUTH,
        font_id="font",
        font_license="DejaVu Fonts license; assets/FONT-LICENSE.txt",
    )
)
t, P = ep.t, ep.P
barista, customer = cast.Barista(ep.cv), cast.Customer(ep.cv)
cafe = ep.setup(
    cafe_with_tips,
    [(0, t.duration)],
    behind_counter=lambda g: ep.perform(
        barista,
        g,
        750,
        800,
        1.35,
        blinks=[(P(1).start + 0.2, P(1).start + 0.34)],
        nods=[(0, 0), (P(2).start, 0), (P(2).start + 0.2, -3), (P(2).end, 0)],
    ),
    at_counter=lambda g: ep.perform(
        customer, g, 270, 1035, 1.53, smile=[(P(3).end, t.duration)], blinks=[(P(0).end, P(0).end + 0.14)]
    ),
)
graphics.episode_slate(
    ep.cv,
    ep.comp,
    "EX",
    "COFFEE REVIEW",
    x=58,
    w=476,
    h=76,
    bg="#355C53",
    badge="#E0B46C",
    badge_h=52,
    number_color=ep.cv.ink,
    title_color=ep.cv.white,
    title_x=82,
    title_w=375,
    title_size=25,
    radius=14,
    badge_radius=8,
)
graphics.connected_card(ep.cv, ep.comp, "VERDICT", "hired (for the coffee)", show=(t.ending, t.duration))
ep.captions(x=40, y=1488, width=1000, weight=None, line_height="1.12", stroke=ep.cv.ink, shadow="#00000055")
ep.audio(track_id="sample-dialogue")
ep.markers()
ep.finish()

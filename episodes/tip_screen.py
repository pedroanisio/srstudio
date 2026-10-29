#!/usr/bin/env python3
"""Episode 12 — Tip Screen, built with srstudio: Ava and Milo from episode 05, back in the café.

    python3 tip_screen_audio.py PROJECT --key-stdin < key   # generated clips, resolved and pinned by the engine
    python3 tip_screen.py PROJECT                            # → PROJECT/tip-screen.scene.xml

Milo asks for a black coffee. Ava swivels the tablet: 20%, 25%, 30%. "You poured it from a pot." "With intention."
Milo sets down a tablet of his own: "how would you like to tip me for ordering?" A long look. "Twenty-five?" Tap.
"Thirty." Tap. "Thirty." Tap. Three hours later they are still at it, and the scorecard nets it out: nothing.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import CAFE, Episode, EpisodeSpec, camera, cast, graphics, locations, props
from tip_screen_audio import TAPS

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="tip-screen",
        number="12",
        title="Tip Screen — Comedy Cut 12",
        description="Café comedy: a black coffee, a tip screen, and a customer who brought his own. Native vector "
        "animation in the café; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        seed=12041,
        background="#F0DDC0",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        # no engine safe area: the camera reframes the menu board and the tablets out of frame on purpose, which
        # the text check (SA01) refuses; captions and cards are placed inside layout.VERTICAL by hand instead
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
SWIVEL, SET, LATER, REACTION, ENDING, DURATION = (
    t.swivel_start,
    t.set_start,
    t.later_start,
    t.reaction,
    t.ending,
    t.duration,
)
TAP_AT = {k: float(v) for k, v in t.meta["taps"].items()}
AVA_AT, MILO_AT = (750, 800, 1.35), (270, 1035, 1.53)
AVA_TABLET, MILO_TABLET = (845, 1240, 0.9), (575, 1240, 0.85)  # Milo's clears his own head
TURN = 0.22  # the swivel: edge-on to facing the customer


def picks(whose: str) -> tuple[tuple[float, int], ...]:
    return tuple((TAP_AT[k], i) for k, (who, i) in TAPS.items() if who == whose)


def screen_centre(at) -> tuple[float, float]:
    x, y, s = at
    return x, y - s * (70 + 24 + props.TIP_SCREEN[1] / 2)


def on_counter(g):
    props.coffee_cup(cv, g, 600, 1187, 1.06)
    ava = cv.group(g, "ava-tablet-swivel", x=AVA_TABLET[0], y=AVA_TABLET[1])
    cv.gate(ava, [(SWIVEL, DURATION)])
    cv.keys(ava, "scaleX", [(0, 0.03), (SWIVEL, 0.03), (SWIVEL + TURN, 1.04), (SWIVEL + TURN + 0.08, 1)], hold=False)
    props.tip_tablet(cv, ava, 0, 0, heading="Add a tip", picks=picks("ava"), scale=AVA_TABLET[2])
    milo = cv.group(g, "milo-tablet-drop", x=MILO_TABLET[0], y=MILO_TABLET[1])
    cv.gate(milo, [(SET - 0.12, DURATION)])
    cv.keys(milo, "y", [(0, MILO_TABLET[1] - 60), (SET - 0.12, MILO_TABLET[1] - 60), (SET, MILO_TABLET[1])],
            hold=False)  # fmt: skip
    props.tip_tablet(cv, milo, 0, 0, heading="Tip for ordering?", picks=picks("milo"), scale=MILO_TABLET[2])


ava = cast.Barista(cv)
milo = cast.Customer(cv)
taps = sorted(TAP_AT.values())
cafe = ep.setup(
    locations.cafe,
    [(0, DURATION)],
    behind_counter=lambda g: ep.perform(
        ava,
        g,
        *AVA_AT,
        name=None,  # the tablet close-ups would carry the lettered tag out of the safe area
        mouth=ep.mouth("ava", smile=[(0, P(2).start), (P(3).start, P(4).end)]),
        blinks=[(P(1).end + 0.05, P(1).end + 0.19), (P(4).end + 0.5, P(4).end + 0.9), (LATER + 0.6, LATER + 1.1)],
        nods=[
            (0, 0),
            (P(1).start, 0),
            (P(1).start + 0.2, -4),
            (P(1).end, 0),
            (P(3).start, 0),
            (P(3).start + 0.3, 5),
            (P(3).end, 0),
            (P(5).start, 0),
            (P(5).start + 0.3, -3),
            (LATER, -3),
            (LATER + 0.2, 6),
        ],
    ),  # fmt: skip
    on_counter=on_counter,
    at_counter=lambda g: ep.perform(
        milo,
        g,
        *MILO_AT,
        mouth=ep.mouth("milo", smile=[(P(4).start, P(4).end)]),
        blinks=[(P(0).end + 0.3, P(0).end + 0.44), (P(3).end + 0.1, P(3).end + 0.5), (LATER + 0.3, LATER + 0.9)],
        nods=[
            (0, 0),
            (P(0).start, 0),
            (P(0).start + 0.3, 3),
            (P(0).end, 0),
            (P(2).start, 0),
            (P(2).start + 0.3, -5),
            (P(2).end, 0),
            (P(4).start, 0),
            (P(4).start + 0.4, 4),
            (P(4).end, 0),
            (LATER, 0),
            (LATER + 0.2, 7),
        ],
    ),  # fmt: skip
)


def close(at, scale, to=(540, 860)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


FRAMES = {  # angle -> scale, x, y
    "wide": (1.0, 0, 0),
    "later": (1.0, 0, 0),
    "end": (1.0, 0, 0),
    "barista": close(AVA_AT[:2], 1.55, (540, 775)),
    "customer": close(MILO_AT[:2], 1.40, (540, 775)),
    "ava-tablet": close(screen_centre(AVA_TABLET), 2.4),
    "milo-tablet": close(screen_centre(MILO_TABLET), 2.5),
    "tablets": close(((AVA_TABLET[0] + MILO_TABLET[0]) / 2, screen_centre(AVA_TABLET)[1]), 1.6),
}
camera.reframe(cv, cafe, [(c.time, *FRAMES[c.angle]) for c in t.cuts])

graphics.episode_slate(cv, ep.comp, "12", "TIP SCREEN", x=90, y=235)
graphics.location_slate(cv, ep.comp, "THREE HOURS LATER", show=(LATER, LATER + 1.6), x=90, y=235)
graphics.scorecard(
    cv,
    ep.comp,
    "TODAY'S TIPS",
    [("AVA", "+$0.00", "#E6AA92"), ("MILO", "+$0.00", "#E6AA92"), ("COFFEE", "COLD", "#AAD6BD")],
    show=(ENDING + 0.3, DURATION),
    x=90,
    y=235,
    w=820,
    value_w=330,
    label_w=360,
)
specs = []
for i, p in enumerate(t.phrases):
    until = t.phrases[i + 1].start - 0.02 if i + 1 < len(t.phrases) else REACTION + 0.6
    specs.append((max(0.0, p.start - 0.05), until, p.caption, f"dialogue-{i + 1}"))
spoken = ep.captions(
    specs,
    x=80,
    y=1240,
    width=840,
    highlights={
        "dialogue-4": [("With intention.", True)],
        "dialogue-5": [("Great. And how would you\n", False), ("like to tip me for ordering?", True)],
    },
)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-later", LATER, "Three hours later")])
ep.instagram(POSTS["tip-screen"])
ep.finish()

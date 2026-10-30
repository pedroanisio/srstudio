#!/usr/bin/env python3
"""Comedy Cut 22 — Cup Fee, built with srstudio: Ava and Milo, back in the café, and what a coffee costs.

    srstudio record cup-fee PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build cup-fee PROJECT    # → PROJECT/cup-fee.scene.xml

"One black coffee. Three bucks." The card reader on the counter says $3.00. "Plus a fee for the cup." Beep:
$3.75. "And the lid fee." Beep. "It's a lid." "And a service fee." "For what?" "For serving you." "Fine. I'll pay
cash." "That's a cash fee." Beep: $7.75. "How much is the actual coffee?" A held smile. "Oh, the coffee's free."
"Then what are the three bucks for?" "The coffee fee." The tip tablet from *Tip Screen* swivels round to him.

The first second is still (arm A of the ``sp-hook_motion`` test): the two-shot frames the café without the espresso
machine's breathing steam, the first reading is drawn still, and no blink, nod, mouth or caption moves before the
first line at ``LEAD``. Like *Tip Screen*, the episode declares no engine safe area, because its close-ups reframe
the menu board's lettering out of frame, which the SA01 text check refuses; captions are placed inside x 80–920 by
hand.
"""

import os

from _common import project_root
from cup_fee_audio import READINGS
from instagram_posts import POSTS
from srstudio import CAFE, Episode, EpisodeSpec, camera, cast, locations, props

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="cup-fee",
        number="22",
        title="Cup Fee — Comedy Cut 22",
        description="Café comedy: a three-dollar black coffee, a card reader that beeps a new fee onto it with every "
        "line, and the price of the coffee itself. Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        seed=22042,
        background="#F0DDC0",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
BEEPS, SWIVEL, REACTION, DURATION = [float(b) for b in t.meta["beeps"]], t.swivel_start, t.reaction, t.duration
AVA_AT, MILO_AT = (750, 800, 1.35), (270, 1035, 1.53)
READER = (545, 1240, 0.82)  # the card reader on the counter, between them, its screen toward the camera
TABLET = (820, 1240, 0.9)  # the tip tablet in front of Ava, edge-on until the swivel
TURN = 0.22  # the swivel: edge-on to facing the customer
MENU = ("COFFEE   $3", "PASTRY   $3", "*FEES APPLY")  # the board agrees with the reader, and warns in small print


def on_counter(g):
    props.coffee_cup(cv, g, 395, 1187, 1.06)
    readings = tuple((0.0 if i == 0 else BEEPS[i - 1], amount, label) for i, (amount, label) in enumerate(READINGS))
    props.card_reader(cv, g, *READER[:2], readings=readings, scale=READER[2])
    tablet = cv.group(g, "tip-tablet-swivel", x=TABLET[0], y=TABLET[1])
    cv.keys(tablet, "scaleX", [(0, 0.03), (SWIVEL, 0.03), (SWIVEL + TURN, 1.04), (SWIVEL + TURN + 0.08, 1)], hold=False)
    props.tip_tablet(cv, tablet, 0, 0, heading="Add a tip", scale=TABLET[2])


ava = cast.Barista(cv)
milo = cast.Customer(cv)
L = [P(i) for i in range(len(t.phrases))]
cafe = locations.cafe(
    cv,
    locations.finish(cv, ep.comp),  # the Cutout grade over the set; the camera moves inside it
    shots=[(0, DURATION)],
    behind_counter=lambda g: ep.perform(
        ava,
        g,
        *AVA_AT,
        name=None,  # the close-ups would carry the lettered tag out of frame
        mouth=ep.mouth(
            "ava",
            smile=[(L[0].start, L[1].start), (L[6].start, L[7].start), (L[9].end, L[11].start), (L[12].end, DURATION)],
        ),  # fmt: skip
        blinks=[
            (L[1].end + 0.05, L[1].end + 0.19),
            (L[4].end + 0.10, L[4].end + 0.24),
            (L[8].end + 0.30, L[8].end + 0.44),
            (L[11].end + 0.05, L[11].end + 0.19),
        ],
        nods=[
            (0, 0),
            (L[0].start, 0),
            (L[0].start + 0.3, 3),
            (L[1].start, 3),
            (L[1].start + 0.25, -3),  # brightly, each fee
            (L[4].start, 0),
            (L[4].start + 0.25, -4),
            (L[6].start, -4),
            (L[6].start + 0.3, 4),  # "for serving you": a little bow
            (L[8].start, 0),
            (L[8].start + 0.2, -5),
            (L[10].start, -5),
            (L[10].start + 0.3, 3),
            (L[12].start, 3),
            (L[12].start + 0.3, -4),
            (SWIVEL, -4),
            (SWIVEL + 0.25, 4),  # toward the tablet
        ],
    ),
    on_counter=on_counter,
    menu=MENU,
    at_counter=lambda g: ep.perform(
        milo,
        g,
        *MILO_AT,
        held_cup=[],  # his coffee is on the counter, not in his hand
        mouth=ep.mouth("milo"),
        blinks=[
            (BEEPS[0] + 0.15, BEEPS[0] + 0.29),
            (BEEPS[3] + 0.45, BEEPS[3] + 0.85),  # the slow blink at $7.75
            (L[10].end + 0.30, L[10].end + 0.44),
            (SWIVEL + 0.60, SWIVEL + 1.10),  # the last, slowest blink at the tablet
        ],
        nods=[
            (0, 0),
            (L[0].start, 0),
            (L[0].start + 0.3, 4),  # he nods along to the order
            (L[1].start, 4),
            (L[1].start + 0.3, 0),
            (L[3].start, 0),
            (L[3].start + 0.3, -5),
            (L[3].end, -5),
            (L[7].start, -5),
            (L[7].start + 0.3, 3),
            (L[9].start, 3),
            (L[9].start + 0.3, -3),
            (L[11].start, -3),
            (L[11].start + 0.3, 5),
            (SWIVEL, 5),
            (SWIVEL + 0.4, 9),  # down at the tablet
        ],
    ),
)


def close(at, scale, to=(540, 860)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


READER_SCREEN = (READER[0], READER[1] - READER[2] * (props.READER_SCREEN[1] + 150 - 18 - props.READER_SCREEN[1] / 2))
FRAMES = {  # angle -> scale, x, y
    "two": (1.25, -40, -330),  # the espresso machine's steam stays right of the frame
    "barista": close(AVA_AT[:2], 1.55, (540, 775)),
    "customer": close(MILO_AT[:2], 1.40, (540, 775)),
    "reader": close(READER_SCREEN, 2.6, (540, 700)),  # the total above the captions
    "end": (1.2, -120, -300),  # Milo, the reader and the tablet side by side
}
camera.reframe(cv, cafe, [(c.time, *FRAMES[c.angle]) for c in t.cuts])

specs = []
for i, p in enumerate(t.phrases):
    nxt = t.phrases[i + 1].start - 0.02 if i + 1 < len(t.phrases) else REACTION - 0.12  # off before the wide
    specs.append((max(1.0, p.start - 0.05), nxt, p.caption, f"dialogue-{i + 1}"))
spoken = ep.captions(
    specs,
    x=80,
    y=1240,
    width=840,
    highlights={
        "dialogue-11": [("Oh, ", False), ("the coffee's free.", True)],
        "dialogue-13": [("The coffee fee.", True)],
    },
)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-cash", BEEPS[3], "Cash fee"), ("marker-swivel", SWIVEL, "The tip tablet")])
ep.instagram(POSTS["cup-fee"])
ep.finish()

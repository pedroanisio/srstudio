#!/usr/bin/env python3
"""Comedy Cut 25 — Neighbor Names, built with srstudio: seven years of sharing an elevator, and nobody's name.

    srstudio record neighbor-names PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build neighbor-names PROJECT    # → PROJECT/neighbor-names.scene.xml

"Morning!" "Morning... you!" "Seven years in this building, huh?" "Seven years!" A silence. "Can I ask you something
I should know by now?" "Anything, dear." "Where did you get that cardigan?" "I made it." (Her name is stitched on its
pocket: ROSA. His parcel says DEV.) Ding: the doors open on a third neighbor. "Morning, Linda! Morning, Steve!" The
doors shut. "Steve." "Linda."

The first frame already moves (arm B of the ``sp-hook_motion`` test): the greeting is under way, his hand up and her
lean toward him, with no camera move. The hallway seen through the doors is blurred (``elevator(depth=)``) and the
neighbor waiting there stands in it, in focus (``hallway=``); every rider has a contact shadow under the one ceiling
light, and the cab is drawn into ``locations.finish``.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from neighbor_names_audio import INTERVIEW
from srstudio import OFFICE, Episode, EpisodeSpec, cast, locations, look, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="neighbor-names",
        number="25",
        title="Neighbor Names — Comedy Cut 25",
        description="Neighbor comedy: two neighbors who have shared an elevator for seven years and never learned each "
        "other's names, until a third greets them both by the wrong ones. Native vector animation; ElevenLabs "
        "dialogue and sound effects.",
        root=project_root(__file__),
        **iv_audio.spec_font(INTERVIEW.font, project_root(__file__)),  # the pinned Google caption face
        seed=25062,
        background="#D5DFDF",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        # no engine safe area: each close-up reframes the other rider's lettering (her stitched name, his parcel's
        # label) out of frame, which the text check (SA01) refuses; captions are placed inside x 80–920 by hand
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv = ep.t, ep.cv
DING, OPEN, SHUT, REACTION, DURATION = (
    t.ding_start,
    float(t.meta["doors_open"]),
    float(t.meta["doors_shut"]),
    t.reaction,
    t.duration,
)
L = [ep.P(i) for i in range(len(t.phrases))]
SCALE, HALL_SCALE = 1.2, 0.85
DEV_X, ROSA_X, HALL_X = 320, 770, 540
DEV_Y = locations.elevator_stand_y(cast.Candidate.bottom, SCALE)
ROSA_Y = locations.elevator_stand_y(cast.Rosa.bottom, SCALE)
BASE = locations.ELEVATOR_BACK[3]  # the hallway floor line, seen through the doorway
HALL_Y = BASE - (cast.Manager.bottom + cast.OfficeActor.STANDING_LEGS) * HALL_SCALE
PARCEL = (DEV_X, DEV_Y + 290 * SCALE, 0.9)  # held against his chest, its label toward us
SHADE = "#1E1A17"
FLOORS = [(0.0, 7), (2.4, 6), (6.6, 5), (DING - 0.6, 4), (SHUT + 2.2, 3)]
EPS = 0.001

dev = cast.Candidate(cv, tag="dev-character")
rosa = cast.Rosa(cv)
neighbor = cast.Manager(cv, tag="hall-character")


def shadow(g, x, y, w):
    """A rider's contact shadow under the ceiling light, straight down."""
    look.pool(cv, g, cv.uid("contact"), SHADE + "AA", x - w / 2, y - 22, w, 50, opacity=0.8)


def riders(g):
    shadow(g, DEV_X, locations.ELEVATOR_FLOOR, 300)
    shadow(g, ROSA_X, locations.ELEVATOR_FLOOR, 300)
    ep.perform(
        dev,
        g,
        DEV_X,
        DEV_Y,
        SCALE,
        legs="standing",
        arms="articulated",
        forearm=[(0, -120), (0.30, -135), (0.70, -120), (1.0, -10), (1.2, 0)],  # a little raised hand: hey
        pointing=[(0, 1.0)],
        mouth=ep.mouth("candidate", smile=[(0, L[0].start), (L[0].end, L[2].start), (REACTION, DURATION)]),
        blinks=[
            (L[1].end + 0.20, L[1].end + 0.34),
            (L[3].end + 0.35, L[3].end + 0.75),  # the silence: a slow blink at the doors
            (L[7].end + 0.10, L[7].end + 0.24),
            (SHUT + 0.30, SHUT + 0.70),  # the names land
        ],
        nods=[
            (0, 0),
            (0.05, -2),
            (0.35, 6),  # nodding into the greeting from the first frame
            (0.65, -1),
            (L[2].start, -1),
            (L[2].start + 0.3, 4),
            (L[4].start, 4),
            (L[4].start + 0.3, -3),
            (L[6].start, -3),
            (L[6].start + 0.25, 3),
            (L[10].start, 3),
            (L[10].start + 0.35, 7),  # "Linda.": a firm, final nod
            (L[10].end + 0.4, 0),
        ],
    )
    props.parcel(cv, g, *PARCEL[:2], label="DEV 7C", scale=PARCEL[2], id="dev-parcel")
    ep.perform(
        rosa,
        g,
        ROSA_X,
        ROSA_Y,
        SCALE,
        legs="standing",
        mouth=ep.mouth("rosa", smile=[(0, L[1].end + 0.3), (L[5].start, L[6].start), (L[9].start, DURATION)]),
        blinks=[
            (L[0].end + 0.05, L[0].end + 0.19),
            (L[3].end + 0.50, L[3].end + 0.64),
            (L[6].end + 0.05, L[6].end + 0.19),
            (SHUT + 0.20, SHUT + 0.34),
        ],
        nods=[
            (0, 0),
            (0.05, 2),
            (0.40, -7),  # her greeting, chin up, from the first frame
            (0.80, 3),
            (1.10, -4),
            (L[3].start, -4),
            (L[3].start + 0.25, 5),
            (L[5].start, 5),
            (L[5].start + 0.3, -3),
            (L[7].start, -3),
            (L[7].start + 0.25, -8),  # "I made it.": proudly
            (L[9].start, -8),
            (L[9].start + 0.3, 4),
            (L[9].end + 0.3, 0),
        ],
    )
    # she leans in toward him on the greeting, then straightens up
    cv.keys(rosa.group, "rotation", [(0, 0), (0.05, 0), (0.45, -5), (1.2, -5), (1.6, 0)], hold=False)
    for who, toward in ((dev, 10), (rosa, -10)):  # each glances at the other on their line, at the doors on the ding
        cv.keys(
            who.eyes,
            "x",
            [(0, toward), (L[1].end + 0.2, toward), (L[1].end + 0.4, 0), (L[4].start, 0), (L[4].start + 0.2, toward),
             (L[7].end, toward), (L[7].end + 0.2, 0), (SHUT, 0), (SHUT + 0.6, toward), (L[10].end + 0.3, toward),
             (L[10].end + 0.6, 0)],
            hold=False,
        )  # fmt: skip


def hallway(g):
    """The neighbor waiting for the elevator: seen while the doors are open, greeting both by the wrong names."""
    waiting = cv.group(g, "hall-waiting")
    cv.gate(waiting, [(OPEN, SHUT + locations.DOOR_SLIDE)])
    shadow(waiting, HALL_X, BASE, 200)
    ep.perform(
        neighbor,
        waiting,
        HALL_X,
        HALL_Y,
        HALL_SCALE,
        legs="standing",
        mouth=ep.mouth("manager", smile=[(OPEN, L[8].start), (L[8].end, DURATION)]),
        blinks=[(L[8].end + 0.05, L[8].end + 0.19)],
        nods=[(0, 0), (L[8].start, 0), (L[8].start + 0.25, -6), (L[8].start + 0.75, 4), (L[8].end, -3)],
        pupils=[(0, -31)],
    )
    # "Morning, Linda!" to her, "Morning, Steve!" to him: he turns from one to the other
    half = (L[8].start + L[8].end) / 2
    cv.keys(neighbor.group, "rotation", [(0, 4), (half - 0.1, 4), (half + 0.1, -4)], hold=False)


cab = locations.elevator(
    cv,
    locations.finish(cv, ep.comp),
    riders=riders,
    hallway=hallway,
    floors=FLOORS,
    doors=((OPEN, SHUT),),
    lit=1,
    going="down",
    depth=3.0,
)


def framing(at, scale, to=(540, 820)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


FRAMES = {  # angle -> scale, x, y
    "two": (1.0, 0.0, 0.0),
    "dev": framing((DEV_X + 40, DEV_Y + 170), 1.9),
    "rosa": framing((ROSA_X - 30, ROSA_Y + 170), 1.9),
    "hall": framing((HALL_X, HALL_Y + 120), 1.7, (540, 760)),
}
rows = [(c.time, *FRAMES[c.angle]) for c in t.cuts]
for prop, column in [("scaleX", 1), ("scaleY", 1), ("x", 2), ("y", 3)]:
    values = [(0.0, rows[0][column])]
    for prev, row in zip(rows, rows[1:], strict=False):
        values += [(row[0] - EPS, prev[column]), (row[0], row[column])]
    cv.keys(cab, prop, values, hold=False)

spoken = ep.captions(
    x=80,
    y=1240,
    width=840,
    highlights={
        "dialogue-9": [("Morning, ", False), ("Linda!", True), ("\nMorning, ", False), ("Steve!", True)],
        "dialogue-10": [("Steve.", True)],
        "dialogue-11": [("Linda.", True)],
    },
)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-ding", DING, "The ding"), ("marker-names", L[8].start, "The wrong names")])
ep.instagram(POSTS["neighbor-names"])
ep.finish()

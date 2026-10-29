#!/usr/bin/env python3
"""Episode 20 — Going Down, built with srstudio: the boss lays the employee off on the way down.

    python3 going_down_audio.py PROJECT --key-stdin < key   # generated clips, resolved and pinned by the engine
    python3 going_down.py PROJECT                            # → PROJECT/going-down.scene.xml

The finale of the office series. Floor 9, going down. "Am I being fired?" "No. Your role is being sunset." "So
I'm fired." "You're going fully remote. From your couch. Forever." Ding, floor 4: Kevin, the pigeon from *Culture
Fit*, walks in with a pink slip in his beak. "Kevin? He's fully remote!" "He flew in for this. He's Head of People
now." The slip lands at the boss's feet, and it says ERIC. "Kevin... is my role being sunset?" A long hold. Coo.
Ding, the lobby. The bench from *Culture Fit*: two men tossing crumbs to the pigeons. "What are we doing?"
"Networking." Coo.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import OFFICE, Episode, EpisodeSpec, camera, cast, graphics, locations, props

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="going-down",
        number="20",
        title="Going Down — Comedy Cut 20",
        description="Office comedy: the boss lays an employee off in the elevator on the way down, until the pigeon "
        "who is Head of People drops a pink slip at his own feet. Native vector animation; ElevenLabs dialogue and "
        "sound effects.",
        root=project_root(__file__),
        seed=20041,
        background="#D5DFDF",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        # no engine safe area: the park sign's lettering sits right of x 920 (as in Culture Fit), which the text
        # check (SA01) refuses; captions and cards are placed inside x 80–920 by hand instead
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
DING4, COO1, DROP, COO2, DING1 = t.ding4_start, t.coo1_start, t.drop_start, t.coo2_start, t.ding1_start
PARK, FLUTTER, COO3 = t.park_start, t.flutter_start, t.coo3_start
REACTION, ENDING, DURATION = t.reaction, t.ending, t.duration
SCALE = 1.2
CANDIDATE_X, MANAGER_X = 320, 770
KEVIN_X, KEVIN_DOOR_Y, KEVIN_FLOOR_Y = 560, 1440, 1690  # the pigeon walks from the doorway to the boss's feet
SLIP_AT = (640, 1712)  # where the slip lands, under Kevin's beak, at the boss's feet
OPEN4 = DING4 + 0.15
SHUT4 = P(4).start + 0.6  # once Kevin is in
OPEN1 = DING1 + 0.15
TOP, STOP4, LOBBY = 9, 4, 1


def descend(first: int, last: int, start: float, end: float) -> list[tuple[float, int]]:
    """The display counting down from ``first`` to ``last`` evenly between ``start`` and ``end``."""
    n = first - last
    return [(start + (end - start) * k / n, first - k) for k in range(n + 1)]


FLOORS = [(0.0, TOP), *descend(TOP, STOP4, 0.9, DING4 - 0.1)[1:], *descend(STOP4, LOBBY, SHUT4 + 1.0, DING1 - 0.1)[1:]]
DOORS = ((OPEN4, SHUT4), (OPEN1, PARK))

candidate = cast.Candidate(cv)
manager = cast.Manager(cv)


def riders(g):
    ep.perform(
        candidate,
        g,
        CANDIDATE_X,
        locations.elevator_stand_y(cast.Candidate.bottom, SCALE),
        SCALE,
        legs="standing",
        arms="articulated",
        forearm=[(0, 0), (P(4).start, 0), (P(4).start + 0.15, -125), (P(4).end + 0.3, -125), (P(4).end + 0.5, 0)],
        pointing=[(P(4).start + 0.15, P(4).end + 0.3)],  # at Kevin
        mouth=ep.mouth("candidate"),
        blinks=[
            (1.9, 2.04),
            (P(2).end + 0.2, P(2).end + 0.6),
            (P(5).end + 0.1, P(5).end + 0.24),
            (COO2 + 0.2, COO2 + 0.6),
        ],
        nods=[
            (0, 0),
            (P(0).start, 0),
            (P(0).start + 0.25, -5),
            (P(2).start, -5),
            (P(2).start + 0.3, 6),
            (P(3).end, 6),
            (P(3).end + 0.3, 0),
        ],
    )
    ep.perform(
        manager,
        g,
        MANAGER_X,
        locations.elevator_stand_y(cast.Manager.bottom, SCALE),
        SCALE,
        legs="standing",
        pupils=[
            (0, -31),
            (COO1, -31),
            (COO1 + 0.15, -16),  # down at Kevin
            (P(4).end, -16),
            (P(4).end + 0.2, -31),
            (DROP, -31),
            (DROP + 0.15, -16),  # down at the slip
            (P(6).start + 0.3, -16),
        ],  # fmt: skip
        brows=([(0, 0), (DROP, 0), (DROP + 0.2, -8)], [(0, 0), (DROP, 0), (DROP + 0.2, 8)]),
        mouth=ep.mouth(
            "manager", smile=[(P(1).start, P(1).end + 0.3), (P(3).start, P(3).end + 0.3), (P(5).start, P(5).end)]
        ),
        blinks=[(2.6, 2.74), (P(3).end + 0.3, P(3).end + 0.44), (COO2 + 0.15, COO2 + 0.75)],
    )


def kevin(g):
    """The pigeon walks in through the doors at floor 4 with the slip in his beak and drops it at the boss's feet;
    he nods at each coo."""
    walk = cv.group(g, "kevin-walk", x=KEVIN_X, y=KEVIN_DOOR_Y, scaleX=0.55, scaleY=0.55)
    arrive = OPEN4 + 0.35
    cv.keys(walk, "opacity", [(0, 0), (OPEN4 + 0.1, 0), (OPEN4 + 0.2, 1)], hold=False)
    cv.keys(walk, "y", [(0, KEVIN_DOOR_Y), (arrive, KEVIN_DOOR_Y), (arrive + 0.9, KEVIN_FLOOR_Y)], hold=False)
    for prop in ("scaleX", "scaleY"):
        cv.keys(walk, prop, [(0, 0.55), (arrive, 0.55), (arrive + 0.9, 1.0)], hold=False)
    bob = cv.group(walk, "kevin-bob")  # a pigeon's head-bob walk: a hop each step
    steps = [(arrive + k * 0.15, -18 if k % 2 else 0) for k in range(7)]
    cv.keys(bob, "y", [(0, 0), *steps, (arrive + 1.05, 0)], hold=False)
    nods = [(0, 0), (DROP - 0.12, 0), (DROP, 16), (DROP + 0.25, 0)]  # he lets go
    for coo in (COO1, COO2):
        nods += [(coo, 0), (coo + 0.12, 14), (coo + 0.3, -4), (coo + 0.45, 12), (coo + 0.65, 0)]
    bird = cast.pigeon(cv, bob, x=-60, y=-70, scale=0.83, flip=False, nods=sorted(nods), id="kevin")
    props.pink_slip(cv, bird, 128, -70, name=None, scale=0.5, rotation=12, show=(OPEN4, DROP))  # its back to us
    beak_y = KEVIN_FLOOR_Y - 124
    props.pink_slip(cv, g, *SLIP_AT, name="ERIC", rotation=-6, fall=(DROP, SLIP_AT[1] - beak_y))


room = ep.setup(locations.elevator, [(0, PARK)], riders=riders, on_floor=kevin, floors=FLOORS, doors=DOORS,
                lit=LOBBY, going="down")  # fmt: skip

# The bench from Culture Fit: the two of them on their lunch break, tossing crumbs to the pigeons.
PARK_SCALE = 1.25
WILL_AT = (370, locations.park_seat_y(cast.Candidate.bottom, PARK_SCALE), PARK_SCALE)
ERIC_AT = (720, locations.park_seat_y(cast.Manager.bottom, PARK_SCALE), PARK_SCALE)
WILL_HAND = (WILL_AT[0] + 82 * PARK_SCALE, WILL_AT[1] + 300 * PARK_SCALE)
ERIC_HAND = (ERIC_AT[0] - 82 * PARK_SCALE, ERIC_AT[1] + 300 * PARK_SCALE)
PATH_Y = 1547
FLOCK = ((300, 0.95, False), (560, 1.05, False), (800, 0.95, True))  # x, scale, flipped: the pigeons on the path


def peck(at: float) -> list[tuple[float, float]]:
    return [(at, 0), (at + 0.08, 32), (at + 0.18, 4), (at + 0.26, 32), (at + 0.36, 4), (at + 0.6, 0)]


def flock(g):
    """Three pigeons drop in on the flutter and peck at the crumbs; the middle one coos back at the last line."""
    for k, (x, s, flip) in enumerate(FLOCK):
        land = FLUTTER + 0.12 * k
        drop = cv.group(g, f"flock-landing-{k}")
        cv.keys(drop, "opacity", [(0, 0), (land, 1)])
        cv.keys(drop, "y", [(land, -260), (land + 0.30, 8), (land + 0.40, 0)], hold=False)
        cv.keys(drop, "x", [(land, 120 if flip else -120), (land + 0.30, 0)], hold=False)
        nods = [(0, 0), *peck(P(7).start + 0.2 * k)]
        if k == 1:
            nods += [(COO3, 0), (COO3 + 0.12, 14), (COO3 + 0.3, -4), (COO3 + 0.45, 12), (COO3 + 0.65, 0)]
        cast.pigeon(cv, drop, x, PATH_Y, s, flip=flip, nods=sorted(nods), id=f"flock-{k}")
    props.crumbs(cv, g, *WILL_HAND, PATH_Y + 50, toss=PARK + 0.35, count=6, seed=20, id="crumbs-will")
    props.crumbs(cv, g, *ERIC_HAND, PATH_Y + 50, toss=PARK + 0.75, count=6, seed=21, id="crumbs-eric")
    props.crumbs(cv, g, *ERIC_HAND, PATH_Y + 50, toss=P(8).start, count=7, seed=22, id="crumbs-networking")


will = cast.Candidate(cv, tag="candidate-park")
eric = cast.Manager(cv, tag="manager-park")
park = ep.setup(
    locations.park,
    [(PARK, DURATION)],
    on_bench=lambda g: (
        ep.perform(
            will,
            g,
            *WILL_AT,
            legs="seated",
            mouth=ep.mouth("candidate"),
            blinks=[(PARK + 1.0, PARK + 1.14), (REACTION + 0.3, REACTION + 0.8)],
            nods=[(0, 0), (P(7).start, 0), (P(7).start + 0.25, -5), (P(8).end, -5), (P(8).end + 0.3, 6)],
        ),
        ep.perform(
            eric,
            g,
            *ERIC_AT,
            legs="seated",
            pupils=[(0, -16), (P(8).start, -16), (P(8).start + 0.2, -31)],  # from the pigeons to Will
            mouth=ep.mouth("manager", smile=[(P(8).start, DURATION)]),
            blinks=[(PARK + 1.4, PARK + 1.54), (COO3 + 0.3, COO3 + 0.44)],
            nods=[(0, 0), (P(8).start, 0), (P(8).start + 0.25, 7), (P(8).end + 0.2, 0)],
        ),
    ),
    beside_bench=flock,
)


def close(at, scale, to=(540, 760)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


HEAD_C = locations.elevator_stand_y(cast.Candidate.bottom, SCALE)
HEAD_M = locations.elevator_stand_y(cast.Manager.bottom, SCALE)
WIDE = (1.0, 0, 0)
ELEVATOR = {  # angle -> scale, x, y
    "wide": WIDE,
    "candidate": close((CANDIDATE_X + 60, HEAD_C + 120), 1.7, (540, 820)),
    "manager": close((MANAGER_X - 60, HEAD_M + 120), 1.7, (540, 820)),
    "slip": close(SLIP_AT, 2.4, (540, 900)),  # the name on the slip, above the captions
    "pigeon": close((KEVIN_X, KEVIN_FLOOR_Y - 120), 2.0, (540, 900)),
    "display": close((540, 520), 2.2, (540, 700)),  # the 1, the doors opening under it
}
BENCH = {
    "park": WIDE,
    "end": WIDE,
    "park-manager": close(ERIC_AT[:2], 1.65),
    "park-pigeon": close((FLOCK[1][0] + 42, PATH_Y - 42), 2.4, (540, 950)),
}
camera.reframe(cv, room, [(c.time, *ELEVATOR[c.angle]) for c in t.cuts if c.angle in ELEVATOR])
camera.reframe(cv, park, [(c.time, *BENCH[c.angle]) for c in t.cuts if c.angle in BENCH])

hook = graphics.location_slate(cv, ep.comp, "GOING DOWN", show=(0, P(1).start - 0.1), x=90, y=235)
graphics.scorecard(
    cv,
    ep.comp,
    "RESTRUCTURING",
    [("WILL", "REMOTE", "#E6AA92"), ("ERIC", "SUNSET", "#E6AA92"), ("KEVIN", "PROMOTED", "#AAD6BD")],
    show=(ENDING + 0.3, DURATION),
    x=90,
    y=235,
    w=820,
    value_w=380,
    label_w=360,
)
specs = []
for i, p in enumerate(t.phrases):
    until = t.phrases[i + 1].start - 0.02 if i + 1 < len(t.phrases) else REACTION + 0.6
    if p.start < DING1 < until:
        until = DING1  # the question stays through the hold and the coo, not into the lobby and the park
    specs.append((max(0.0, p.start - 0.05), until, p.caption, f"dialogue-{i + 1}"))
spoken = ep.captions(
    specs,
    x=80,
    y=1240,
    width=840,
    highlights={
        "dialogue-2": [("No. Your role\nis being ", False), ("sunset.", True)],
        "dialogue-7": [("Kevin…\nis my role being ", False), ("sunset?", True)],
        "dialogue-9": [("Networking.", True)],
    },
)
ep.hide_on_cover(hook, *spoken)
ep.markers(
    extra=[
        ("marker-floor-4", DING4, "Floor 4: Kevin"),
        ("marker-drop", DROP, "The slip says ERIC"),
        ("marker-coo", COO2, "Kevin answers"),
        ("marker-park", PARK, "The bench"),
    ]
)
ep.instagram(POSTS["going-down"])
ep.finish()

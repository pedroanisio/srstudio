#!/usr/bin/env python3
"""Episode 18 — Elevator Pitch, built with srstudio: the employee pitches working from home before the boss's floor.

    python3 elevator_pitch_audio.py PROJECT --key-stdin < key   # generated clips, resolved and pinned by the engine
    python3 elevator_pitch.py PROJECT                            # → PROJECT/elevator-pitch.scene.xml

The employee from *Market Rate* rides the elevator with the boss. "Working from home? Elevator pitch. You've got
till my floor." He pitches: more productive, no commute, no meetings. Ding, floor 4: the doors open and the pigeon
the boss hired in *Culture Fit* walks in. "Morning, Kevin." Kevin is fully remote; he flies in on Tuesdays. Why
does he get remote? "He negotiated. You took a title." Ding, floor 9. "My floor. Kevin, your call." Coo. "Kevin
says five days a week."
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import OFFICE, Episode, EpisodeSpec, camera, cast, graphics, layout, locations

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="elevator-pitch",
        number="18",
        title="Elevator Pitch — Comedy Cut 18",
        description="Office comedy: an employee pitches working from home to the boss in the elevator, and a pigeon "
        "who is fully remote gets the final say. Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        seed=18041,
        background="#D5DFDF",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # text and captions held inside x 80–920, y 220–1420 by the engine
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
DING4, COO1, DING9, COO2 = t.ding4_start, t.coo1_start, t.ding9_start, t.coo2_start
REACTION, ENDING, DURATION = t.reaction, t.ending, t.duration
FX = {s.name: s for s in t.sound_effects}
SCALE = 1.2
CANDIDATE_X, MANAGER_X = 320, 770
KEVIN_X, KEVIN_DOOR_Y, KEVIN_FLOOR_Y = 540, 1440, 1690  # the pigeon walks from the doorway to between them
OPEN4 = DING4 + 0.15
SHUT4 = P(2).start + 0.6  # once Kevin is in
OPEN9 = DING9 + 0.15
STOP4, STOP9, BOSS_FLOOR = 4, 9, 9


def climb(first: int, last: int, start: float, end: float) -> list[tuple[float, int]]:
    """The display counting from ``first`` to ``last`` evenly between ``start`` and ``end``."""
    n = last - first
    return [(start + (end - start) * k / n, first + k) for k in range(n + 1)]


FLOORS = [(0.0, 1), *climb(1, STOP4, 0.9, DING4 - 0.1)[1:], *climb(STOP4, STOP9, SHUT4 + 1.2, DING9 - 0.1)[1:]]
DOORS = ((OPEN4, SHUT4), (OPEN9, DURATION))

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
        forearm=[(0, 0), (P(3).start, 0), (P(3).start + 0.15, -125), (P(3).end + 0.3, -125), (P(3).end + 0.5, 0)],
        pointing=[(P(3).start + 0.15, P(3).end + 0.3)],  # at Kevin
        mouth=ep.mouth("candidate", smile=[(P(1).start, P(1).end + 0.3)]),
        blinks=[
            (1.4, 1.54),
            (P(2).end + 0.2, P(2).end + 0.34),
            (P(6).end + 0.1, P(6).end + 0.6),
            (REACTION + 0.3, REACTION + 0.8),
        ],  # fmt: skip
        nods=[
            (0, 0),
            (P(1).start, 0),
            (P(1).start + 0.25, -5),
            (P(1).end, 0),
            (P(5).start, 0),
            (P(5).start + 0.2, -6),
            (P(5).end + 0.3, 0),
            (REACTION, 0),
            (REACTION + 0.3, 8),
        ],  # fmt: skip
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
            (COO1 + 0.15, -16),
            (P(3).start, -31),
            (P(7).start + 0.6, -16),
            (P(8).start, -16),
            (P(8).start + 0.2, -31),
        ],  # fmt: skip  # down at Kevin, and back
        brows=([(0, 0), (P(6).start, 0), (P(6).start + 0.15, -8)], [(0, 0), (P(6).start, 0), (P(6).start + 0.15, 8)]),
        mouth=ep.mouth("manager", smile=[(P(2).start, P(2).end + 0.3), (P(8).start, REACTION)]),
        blinks=[(2.3, 2.44), (P(4).end + 0.2, P(4).end + 0.34), (COO2 + 0.2, COO2 + 0.34)],
    )


def kevin(g):
    """The pigeon walks in through the open doors at floor 4, coming forward and growing; he nods at each coo."""
    walk = cv.group(g, "kevin-walk", x=KEVIN_X, y=KEVIN_DOOR_Y, scaleX=0.55, scaleY=0.55)
    arrive = OPEN4 + 0.35
    cv.keys(walk, "opacity", [(0, 0), (OPEN4 + 0.1, 0), (OPEN4 + 0.2, 1)], hold=False)
    cv.keys(walk, "y", [(0, KEVIN_DOOR_Y), (arrive, KEVIN_DOOR_Y), (arrive + 0.9, KEVIN_FLOOR_Y)], hold=False)
    for prop in ("scaleX", "scaleY"):
        cv.keys(walk, prop, [(0, 0.55), (arrive, 0.55), (arrive + 0.9, 1.0)], hold=False)
    bob = cv.group(walk, "kevin-bob")  # a pigeon's head-bob walk: a hop each step
    steps = [(arrive + k * 0.15, -18 if k % 2 else 0) for k in range(7)]
    cv.keys(bob, "y", [(0, 0), *steps, (arrive + 1.05, 0)], hold=False)
    nods = [(0, 0)]
    for coo in (COO1, COO2):
        nods += [(coo, 0), (coo + 0.12, 14), (coo + 0.3, -4), (coo + 0.45, 12), (coo + 0.65, 0)]
    cast.pigeon(cv, bob, x=-60, y=-70, scale=0.83, flip=False, nods=nods, id="kevin")


room = ep.setup(locations.elevator, [(0, DURATION)], riders=riders, on_floor=kevin, floors=FLOORS, doors=DOORS,
                lit=BOSS_FLOOR)  # fmt: skip


def close(at, scale, to=(540, 760)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


HEAD_C = locations.elevator_stand_y(cast.Candidate.bottom, SCALE)
HEAD_M = locations.elevator_stand_y(cast.Manager.bottom, SCALE)
FRAMES = {  # angle -> scale, x, y
    "wide": (1.0, 0, 0),
    "end": (1.0, 0, 0),
    "candidate": close((CANDIDATE_X + 60, HEAD_C + 120), 1.7, (540, 820)),
    "manager": close((MANAGER_X - 60, HEAD_M + 120), 1.7, (540, 820)),
    "display": close((540, 520), 2.2, (540, 700)),  # the 9, the doors opening under it
    "pigeon": close((KEVIN_X, KEVIN_FLOOR_Y - 120), 2.0, (540, 900)),
}
camera.reframe(cv, room, [(c.time, *FRAMES[c.angle]) for c in t.cuts])

hook = graphics.location_slate(cv, ep.comp, "ELEVATOR PITCH", show=(0, P(1).start - 0.1), x=90, y=235)
graphics.scorecard(
    cv,
    ep.comp,
    "REMOTE WORK REVIEW",
    [("YOU", "5 DAYS", "#E6AA92"), ("KEVIN", "REMOTE", "#AAD6BD"), ("PITCH", "FLOOR 9", "#E6AA92")],
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
    specs.append((max(0.0, p.start - 0.05), until, p.caption, f"dialogue-{i + 1}"))
spoken = ep.captions(
    specs,
    x=80,
    y=1240,
    width=840,
    highlights={
        "dialogue-7": [("He negotiated.\nYou took a ", False), ("title.", True)],
        "dialogue-9": [("Kevin says ", False), ("five days a week.", True)],
    },
)
ep.hide_on_cover(hook, *spoken)
ep.markers(
    extra=[
        ("marker-floor-4", DING4, "Floor 4: Kevin"),
        ("marker-floor-9", DING9, "Floor 9: the boss's floor"),
        ("marker-coo", COO2, "Kevin decides"),
    ]
)
ep.instagram(POSTS["elevator-pitch"])
ep.finish()

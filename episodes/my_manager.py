#!/usr/bin/env python3
"""My Manager, built with srstudio: a car, a price, and the man the salesman keeps going to see.

    srstudio record my-manager PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build my-manager PROJECT    # → PROJECT/my-manager.scene.xml

The salesman goes to ask his manager. The clock on the wall jumps twenty minutes, and he comes back with a number and
his tie looser. The third time Rosa follows him, through a door marked MANAGER, to a cupboard, a folding chair and a
potted plant. She takes the other chair. He drops into his own chair in the first second.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from my_manager_audio import INTERVIEW, JUMP, LEAVE, SITS
from srstudio import OFFICE, Episode, EpisodeSpec, camera, cast, cutout_counter, cutout_hiring, locations, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="my-manager",
        title="My Manager",
        description="Car lot comedy: a salesman goes to talk to his manager, and a customer finally goes with him. "
        "Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        **iv_audio.spec_font(INTERVIEW.font, project_root(__file__)),
        seed=3117,
        background="#2A2018",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        # no engine safe area: the clock shot crops the set on purpose; captions stay inside the layout by hand
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv = ep.t, ep.cv
L = [ep.P(i) for i in range(len(t.phrases))]
DURATION = t.duration
FIRST, SECOND, THIRD = (float(v) for v in t.meta["leaves"])
CLOCKS = [float(v) for v in t.meta["clock"]]
FOLLOWS, OPENS, SEES, SITS_AT, LEAF = (float(t.meta[k]) for k in ("follows", "opens", "sees", "sits", "leaf"))
DOOR = next(c.time for c in t.cuts if c.angle == "door")
SALESMAN_AT = (540, 790, 1.15)
ROSA_AT = (230, 1340, 1.55)
CLOCK_AT = (838, 112, 78)
GONE_X = 1290  # past the frame's right edge
SITS_DOWN = ((0.0, -230), (0.55, 18), (0.72, -6), (0.86, 0))  # seconds, pixels: he drops into his chair, and settles
RETURNS = [CLOCKS[0] + JUMP - 0.1, CLOCKS[1] + JUMP - 0.1]  # he is walking back in as the clock lets go
IN_ROOM_SALESMAN = (850, 1040, 1.1)
IN_ROOM_ROSA = (230, 1040, 1.1)
PLANT_AT = (540, 1420, 0.72)


def walking(x0: float, leaves: list[float], returns: list[float]) -> list:
    """Out of frame and back on each pair, and out for good on the last."""
    keys = [(0, x0)]
    for gone, back in zip(leaves, returns, strict=False):
        keys += [(gone, x0), (gone + LEAVE, GONE_X), (back, GONE_X), (back + LEAVE, x0)]
    keys += [(leaves[-1], x0), (leaves[-1] + LEAVE, GONE_X)]
    return keys


salesman = cast.Manager(cv, tag="salesman-character")
gerald_man = cast.Manager(cv, tag="cupboard-character")
rosa = cast.Rosa(cv, tag="rosa-character")
sitter = cast.Rosa(cv, tag="rosa-in-the-cupboard")


def behind_desk(g):
    cutout_counter.jump_clock(
        cv, g, *CLOCK_AT[:2], radius=CLOCK_AT[2], start=(3, 10), jumps=[(c + 0.05, 20) for c in CLOCKS]
    )
    cutout_counter.paper_poster(cv, g, 62, 700, text="ZERO\nDOWN\nDAYS", width=200, height=250, size=38)
    man = ep.perform(
        salesman,
        g,
        *SALESMAN_AT,
        arms="articulated",
        mouth=ep.mouth("manager", smile=[(0, L[1].start - 0.3)]),
        blinks=[
            (L[1].end + 0.1, L[1].end + 0.24),
            (L[3].end + 0.02, L[3].end + 0.16),
            (L[4].end + 0.3, L[4].end + 0.44),
        ],
        nods=[
            (0, 0),
            (L[0].start, 0),
            (L[0].start + 0.3, 3),
            (L[0].end, 0),
            (L[1].start, 0),
            (L[1].start + 0.3, -3),
            (L[1].end, 0),
            (L[3].start, 0),
            (L[3].start + 0.2, 6),
            (L[3].end, 0),
            (L[4].start, 0),
            (L[4].start + 0.5, 5),
            (L[4].end, 0),
            (L[6].start, 0),
            (L[6].start + 0.3, 7),
            (L[6].end, 2),
        ],
    )
    cv.keys(man, "x", walking(SALESMAN_AT[0], [FIRST, SECOND, THIRD], RETURNS), hold=False)
    cv.keys(man, "y", [(at, SALESMAN_AT[1] + dy) for at, dy in SITS_DOWN], hold=False)
    worse = [(RETURNS[1] - 0.1, DOOR)]
    loose = cv.group(man, "salesman-loose-tie")
    cv.gate(loose, worse)
    cv.rect(loose, -30, 116, 60, 180, "#FFFFFF")
    cv.path(loose, "M-12 118 L22 150 M12 118 L-22 150", stroke=cv.ink, sw=4)  # the collar, undone
    cv.path(loose, "M8 170 L30 174 L26 196 L6 192Z", cv.ink, cv.clear, 0)
    cv.path(loose, "M9 195 L24 198 L14 300 L-2 312 L-8 296Z", cv.ink, cv.clear, 0)
    wet = cv.group(man, "salesman-forehead")
    cv.gate(wet, worse)
    for x, y, s in ((-60, -92, 1.0), (46, -96, 0.8), (72, -58, 1.1), (-82, -40, 0.7)):
        cv.path(wet, f"M{x} {y} q{-9 * s} {18 * s} 0 {26 * s} q{9 * s} {-8 * s} 0 {-26 * s}Z", "#9CD0E4", cv.ink, 2)


def on_desk(g):
    props.papers(cv, g, 610, 1130, 1.0, -4)
    node = ep.perform(
        rosa,
        g,
        *ROSA_AT,
        arms="articulated",
        legs="seated",
        mouth=ep.mouth("rosa"),
        blinks=[
            (0.62, 0.76),  # the chair
            (CLOCKS[0] - 0.5, CLOCKS[0] - 0.36),
            (CLOCKS[0] + JUMP + 0.1, CLOCKS[0] + JUMP + 0.6),  # twenty minutes in
            (L[3].end + 0.6, L[3].end + 0.74),
            (CLOCKS[1] + JUMP + 0.1, CLOCKS[1] + JUMP + 0.7),
            (THIRD + 0.45, THIRD + 0.59),
        ],
        nods=[
            (0, 0),
            (L[2].start, 0),
            (L[2].start + 0.2, -4),
            (L[2].end, 0),
            (L[5].start, 0),
            (L[5].start + 0.2, -4),
            (L[5].end, 0),
            (FOLLOWS - 0.2, 0),
            (FOLLOWS, 6),
        ],
    )
    cv.keys(node, "x", [(0, ROSA_AT[0]), (FOLLOWS, ROSA_AT[0]), (FOLLOWS + 0.65, 1400)], hold=False)
    cv.keys(node, "y", [(0, ROSA_AT[1]), (FOLLOWS, ROSA_AT[1]), (FOLLOWS + 0.25, ROSA_AT[1] - 90)], hold=False)


finish = locations.finish(cv, ep.comp)  # the Cutout grade over both sets
office = cutout_hiring.hiring_office(cv, finish, behind_desk=behind_desk, on_desk=on_desk, shots=[(0, DOOR)])
camera.reframe(
    cv,
    office,
    [
        (0, 1.0, 0, 0),
        *(
            row
            for at in CLOCKS
            for row in ((at, 5.0, 540 - CLOCK_AT[0] * 5.0, 590 - CLOCK_AT[1] * 5.0), (at + JUMP, 1.0, 0, 0))
        ),
    ],
)


def in_room(g):
    ep.perform(
        gerald_man,
        g,
        *IN_ROOM_SALESMAN,
        arms="articulated",
        legs="seated",
        mouth=ep.mouth("manager"),
        brows=([(0, 0), (SEES, 0), (SEES + 0.12, -9)], [(0, 0), (SEES, 0), (SEES + 0.12, 9)]),
        nods=[
            (0, 0),
            (L[7].start, 0),
            (L[7].start + 0.3, -6),
            (L[7].end + 0.3, -6),
            (L[7].end + 0.55, -2),
            (L[7].end + 0.8, -6),
            (L[7].end + 1.05, -2),
            (SEES, -2),
            (SEES + 0.12, 2),
            (LEAF + 1.5, 2),
            (L[9].start, 2),
            (L[9].start + 0.3, -5),
        ],
        blinks=[(L[7].end + 0.2, L[7].end + 0.34), (SITS_AT + 1.2, SITS_AT + 1.34)],
    )
    cv.keys(
        gerald_man.forearm,
        "rotation",
        [
            (0, -150),
            (L[7].end + 0.1, -150),
            (L[7].end + 0.4, -168),
            (L[7].end + 0.7, -150),
            (L[7].end + 1.0, -168),
            (SEES, -168),
        ],
        hold=False,
    )
    cutout_counter.sandwich(cv, gerald_man.forearm, -10, 100, scale=0.85)
    grown = cv.group(g, "gerald", x=PLANT_AT[0], y=PLANT_AT[1], scaleX=PLANT_AT[2], scaleY=PLANT_AT[2])
    props.plant(cv, cv.group(grown, "gerald-at", x=-80, y=-1139), id="gerald-plant")
    cv.rect(g, 470, 1420, 140, 16, "#6B5A45", cv.ink, 4)  # the stool
    cv.line(g, 490, 1436, 470, 1640, cv.ink, 10)
    cv.line(g, 590, 1436, 610, 1640, cv.ink, 10)
    leaf = cv.group(g, "gerald-loses-a-leaf", x=610, y=1020)
    cv.gate(leaf, [(LEAF - 0.05, DURATION)])
    cv.keys(
        leaf,
        "x",
        [(0, 610), (LEAF, 610), (LEAF + 0.35, 650), (LEAF + 0.7, 600), (LEAF + 1.05, 640), (LEAF + 1.4, 615)],
        kind="sine-in-out",
    )
    cv.keys(leaf, "y", [(0, 1020), (LEAF, 1020), (LEAF + 1.4, 1640)], hold=False)
    cv.keys(
        leaf,
        "rotation",
        [(0, 20), (LEAF, 20), (LEAF + 0.35, -30), (LEAF + 0.7, 30), (LEAF + 1.05, -20), (LEAF + 1.4, 80)],
        hold=False,
    )
    cv.path(leaf, "M0 -30 Q20 -6 0 30 Q-20 -6 0 -30Z", "#7FA45F", cv.ink, 2.5)
    stand = cv.group(g, "rosa-comes-in")
    cv.gate(stand, [(SEES - 0.1, DURATION)])
    x0, y0, s = IN_ROOM_ROSA
    node = ep.perform(
        sitter,
        stand,
        x0,
        y0,
        s,
        arms="articulated",
        legs="seated",
        mouth=ep.mouth("rosa"),
        blinks=[(SITS_AT - 0.5, SITS_AT - 0.36), (LEAF + 1.5, LEAF + 1.9)],
        nods=[(0, 0), (L[8].start, 0), (L[8].start + 0.3, 6), (LEAF, 6)],
    )
    cv.keys(
        node,
        "x",
        [(0, -240), (SEES - 0.1, -240), (SEES + 0.2, 150), (SITS_AT, 150), (SITS_AT + SITS * 0.7, x0)],
        hold=False,
    )
    cv.keys(node, "y", [(0, y0 - 110), (SITS_AT + SITS * 0.6, y0 - 110), (SITS_AT + SITS, y0)], hold=False)


room = cutout_counter.back_room(
    cv,
    finish,
    in_room=in_room,
    shots=[(DOOR, DURATION)],
    plate="MANAGER",
    opens=OPENS,
    push=(OPENS + 0.15, OPENS + 2.6),
)
lines = ep.spoken_captions(tail=0.25)
at_desk = ep.captions([c for c in lines if c[0] < DOOR], x=400, y=1290, width=640, size=60)  # beside Rosa
in_the_cupboard = ep.captions([c for c in lines if c[0] >= DOOR], x=80, y=1440, width=920, size=60)
ep.hide_on_cover(*at_desk, *in_the_cupboard)
ep.markers(
    extra=[("marker-door", DOOR, "The door"), ("marker-sees", SEES, "Sees her"), ("marker-leaf", LEAF, "The leaf")]
)
ep.instagram(POSTS["my-manager"])
ep.finish()

#!/usr/bin/env python3
"""Quiet Please, built with srstudio: two stomachs fall in love in a silent reading room.

    srstudio record quiet-please PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build quiet-please PROJECT    # → PROJECT/quiet-please.scene.xml

Bo hushes the room under a sign. Pip's stomach growls, and across the table Juno's answers. They talk, in tinted
captions, cross-cut: breakfast, a rice cake, are you seeing anyone. Bo walks up between them, finger rising, and his own
stomach shakes the table. HELLO. He keeps the finger on his lips. Pip slides him a yogurt.

The first frame already moves (arm B of the ``sp-hook_motion`` test): Bo's finger is rising to his lips.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from quiet_please_audio import INTERVIEW
from srstudio import SOFT, Episode, EpisodeSpec, blob, camera, foley, layout, soft_odds, soft_sets

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="quiet-please",
        title=INTERVIEW.title,
        description="Office comedy: in a silent reading room two stomachs start talking, and the one who keeps "
        "shushing them has the loudest of all. Native vector animation; ElevenLabs dialogue, synthesized foley.",
        root=ROOT,
        seed=INTERVIEW.seed,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions stay inside x 80–920
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
ON_PIP, ON_JUNO, GOSSIP, BLUSH = t.pip_start, t.juno_start, t.gossip_start, t.blush_start
ASK, ANSWER, WALK, VAST, SNACKS = t.ask_start, t.answer_start, t.walk_start, t.vast_start, t.snacks_start
LAST = t.reaction_start
FPS = 15
SCALE = blob.SCALE
BO_SCALE = 1.5
PIP_AT = blob.SEAT
JUNO_SIDE = 1020.0  # her chair is the room's, mirrored about this line
JUNO_AT = (JUNO_SIDE - PIP_AT[0], PIP_AT[1])
BO_WALL_AT = (540.0, 2000.0)
BO_WALL_SCALE = 2.2
BO_FROM, BO_TO = (540.0, 2800.0), (540.0, 1900.0)
SLIDE_FROM, SLIDE_TO = (650.0, 1160.0), (505.0, 1150.0)  # along the table, to behind his head
BOOK = 0.62
PIP_TINT, JUNO_TINT = "#1F5E9E", "#B8326E"
EYE_SLIDE = ON_PIP + 1.5  # the cut back to Bo
SHAKE = VAST + 0.55  # the room shakes this long, then the zoom
BO_SPANS = [(0.0, ON_PIP), (EYE_SLIDE, ON_JUNO)]
CRASH, CRASH_AT = 2.1, (560.0, 1664.0)  # his face and finger under the caption, the belly filling the rest
PIP_BELLY, JUNO_BELLY, BO_BELLY = (770.0, 1270.0), (250.0, 1270.0), (540.0, 1555.0)
REACH = 150.0  # the raised hand of "step", across to his lips
EXCHANGE = (BLUSH - GOSSIP) / 4
TALK = [GOSSIP + EXCHANGE * n for n in range(4)]
PIP_GROWLS = [ON_PIP + 0.1, *TALK[::2], ASK + 0.1]
JUNO_GROWLS = [ON_JUNO + 0.1, *TALK[1::2], ANSWER + 0.1]

foley.write_bursts(ROOT / "assets" / "pip.wav", [ON_PIP + 0.1], DURATION, foley.GROWL, seed=3141)
foley.write_bursts(ROOT / "assets" / "juno.wav", [ON_JUNO + 0.1], DURATION, foley.GROWL_REPLY, seed=3142)
foley.write_bursts(ROOT / "assets" / "talk-a.wav", [*TALK[::2], ASK + 0.1], DURATION, foley.GROWL_SMALL, seed=3143)
foley.write_bursts(ROOT / "assets" / "talk-b.wav", [*TALK[1::2], ANSWER + 0.1], DURATION, foley.GROWL_REPLY, seed=3144)
foley.write_bursts(ROOT / "assets" / "vast.wav", [VAST], DURATION, foley.GROWL_VAST, seed=3145)
foley.write_bursts(ROOT / "assets" / "steps.wav", [WALK + 0.2 + 0.32 * n for n in range(4)], DURATION, foley.THUD)
foley.write_bursts(ROOT / "assets" / "page.wav", [P[0].end + 0.1], DURATION, foley.FLAP, seed=3146)
foley.write_bursts(ROOT / "assets" / "squeak.wav", [P[2].end + 0.02], DURATION, foley.SQUEAK, seed=3147)
foley.write_bursts(
    ROOT / "assets" / "clock.wav", [n * 1.0 for n in range(int(WALK) + 1)], DURATION, foley.REMOTE_CLICK, seed=3148
)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("clock", "assets/clock.wav", {"role": "ambience", "gain": -24}),
        ("page", "assets/page.wav", {"role": "effects", "gain": -16}),
        ("pip-growl", "assets/pip.wav", {"role": "effects", "gain": -5}),
        ("juno-growl", "assets/juno.wav", {"role": "effects", "gain": -5}),
        ("talk-a", "assets/talk-a.wav", {"role": "effects", "gain": -6}),
        ("talk-b", "assets/talk-b.wav", {"role": "effects", "gain": -6}),
        ("vast", "assets/vast.wav", {"role": "effects", "gain": -1}),
        ("steps", "assets/steps.wav", {"role": "effects", "gain": -16}),
        ("squeak", "assets/squeak.wav", {"role": "effects", "gain": -10}),
    ]
)


def cue(time: float, pose: str, spot=None, *, scale: float = SCALE, **kw):
    return blob.cue(time, pose, spot, scale=scale, **kw)


def quiet(cues, lines):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for start, stop in lines:
        for edge in (start, stop):
            held = [c for c in cues if c.time <= edge][-1]
            if held.time != edge:
                later.append(replace(held, time=edge, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, DURATION, FPS)


pip = [
    cue(0, "sit", PIP_AT, eyes="closed", mouth="flat"),
    cue(ON_PIP + 0.1, "sit", PIP_AT, eyes="wide", mouth="flat"),
    cue(ON_JUNO + 0.2, "sit", PIP_AT, eyes="look", mouth="small"),
    cue(BLUSH, "sit", PIP_AT, eyes="happy", mouth="smile"),
    cue(WALK + 0.6, "sit", PIP_AT, eyes="wide", mouth="flat"),
    cue(VAST + 0.2, "sit", PIP_AT, eyes="wide", mouth="o"),
    cue(P[2].end, "sit", PIP_AT, eyes="happy", mouth="small"),
]
juno = [
    cue(0, "sit", JUNO_AT, eyes="closed", mouth="flat", flip=True),
    cue(ON_JUNO + 0.1, "sit", JUNO_AT, eyes="wide", mouth="flat", flip=True),
    cue(GOSSIP, "sit", JUNO_AT, eyes="open", mouth="small", flip=True),
    cue(BLUSH, "sit", JUNO_AT, eyes="happy", mouth="smile", flip=True),
    cue(WALK + 0.6, "sit", JUNO_AT, eyes="wide", mouth="flat", flip=True),
    cue(VAST + 0.2, "sit", JUNO_AT, eyes="wide", mouth="o", flip=True),
]
bo_wall = quiet(
    [
        cue(0, "stand", BO_WALL_AT, scale=BO_WALL_SCALE, eyes="squint", mouth="flat"),
        cue(0.25, "step", BO_WALL_AT, scale=BO_WALL_SCALE, ease=0.2, eyes="squint", mouth="flat"),
        cue(EYE_SLIDE, "step", BO_WALL_AT, scale=BO_WALL_SCALE, eyes="wide", mouth="flat"),
    ],
    [(P[0].start, P[0].end)],
)
steps = [
    cue(
        WALK + (P[1].start - 0.2 - WALK) * k / 5,
        "walk-a" if k % 2 else "walk-b",
        (BO_FROM[0], BO_FROM[1] + (BO_TO[1] - BO_FROM[1]) * k / 5),
        scale=BO_SCALE,
        ease=0.2,
        eyes="squint",
        mouth="flat",
    )
    for k in range(6)
]
bo_up = quiet(
    [
        cue(0, "stand", BO_FROM, scale=BO_SCALE, eyes="squint", mouth="flat"),
        *steps,
        cue(P[1].start - 0.15, "step", BO_TO, scale=BO_SCALE, ease=0.12, eyes="squint", mouth="flat"),
        cue(VAST + 0.2, "step", BO_TO, scale=BO_SCALE, eyes="wide", mouth="flat"),
        cue(SNACKS, "step", BO_TO, scale=BO_SCALE, eyes="closed", mouth="flat"),
        cue(LAST, "step", BO_TO, scale=BO_SCALE, eyes="wide", mouth="flat"),
    ],
    [(P[1].start, P[1].end), (P[2].start, P[2].end)],
)


def frame(scale: float, x: float, y: float) -> tuple[float, float, float]:
    return scale, 540 - x * scale, 960 - y * scale


WIDE = (1.0, 0.0, 0.0)
PIP_SHOT = frame(1.75, 768.0, 1030.0)  # 540 / 1.75 from the x = 1080 edge of the set, no further
JUNO_SHOT = frame(1.75, 315.0, 1030.0)
BO_SHOT = frame(1.15, 540.0, 1085.0)
graded = soft_sets.finish(cv, ep.comp)
crash = cv.group(graded, "crash")
camera.anchor(crash, *CRASH_AT, place=True)
camera.crash_zoom(cv, crash, SHAKE, CRASH, back=SNACKS)
shaker = cv.group(crash, "shaker")
cv.keys(shaker, "x", [(0.0, 0.0), *((VAST + 0.06 * n, (-1.0) ** n * 9.0) for n in range(9)), (VAST + 0.54, 0.0)])
world = cv.group(shaker, "world")
blob.meeting_room(cv, world)
mirror = cv.group(world, "juno-side", x=JUNO_SIDE, scaleX=-1)
blob.swivel_chair(cv, mirror, id="juno-chair")
blob.juno(cv, world, juno, end=DURATION, scale=SCALE, fps=FPS, id="juno")
blob.pip(cv, world, pip, end=DURATION, scale=SCALE, fps=FPS, id="pip")
for name, who, tilt, color in (("pip", pip, 12, "#C9734A"), ("juno", juno, -12, "#5C8A6B")):
    hands = blob.held(cv, world, who, end=DURATION, scale=SCALE, fps=FPS, id=f"{name}-hands")
    soft_odds.book(cv, hands, 0, 0, scale=BOOK, angle=tilt, color=color, id=f"{name}-book")
soft_odds.rumble(cv, world, *PIP_BELLY, [(g, g + 0.9) for g in PIP_GROWLS], scale=1.1, color=PIP_TINT, id="pip-rumble")
soft_odds.rumble(
    cv, world, *JUNO_BELLY, [(g, g + 0.9) for g in JUNO_GROWLS], scale=1.1, color=JUNO_TINT, id="juno-rumble"
)
slid = cv.group(world, "yogurt-slide", x=SLIDE_FROM[0], y=SLIDE_FROM[1])
cv.gate(slid, [(P[2].end, DURATION)])
cv.keys(slid, "x", [(P[2].end, SLIDE_FROM[0]), (P[2].end + 0.4, SLIDE_TO[0])], False)
cv.keys(slid, "y", [(P[2].end, SLIDE_FROM[1]), (P[2].end + 0.4, SLIDE_TO[1])], False)
soft_odds.yogurt(cv, slid, 0, 0, scale=0.85)
blob.bo(cv, world, bo_up, end=DURATION, scale=BO_SCALE, mouth_states=ep.mouth("bo"), fps=FPS, id="bo")
bo_hand = soft_odds.in_hand(cv, world, bo_up, "right", end=DURATION, scale=BO_SCALE, fps=FPS, id="bo-hand")
cv.gate(bo_hand, [(P[1].start - 0.1, DURATION)])
soft_odds.hush_finger(cv, bo_hand, 0, 0, reach=REACH, scale=BO_SCALE, id="bo-finger")
soft_odds.rumble(cv, world, *BO_BELLY, [(VAST, SNACKS)], scale=1.05, id="bo-rumble")
camera.reframe(
    cv,
    world,
    [
        (0.0, *WIDE),
        (ON_PIP, *PIP_SHOT),
        (ON_JUNO, *JUNO_SHOT),
        *((at, *(PIP_SHOT if n % 2 == 0 else JUNO_SHOT)) for n, at in enumerate(TALK)),
        (BLUSH, *WIDE),
        (SNACKS, *BO_SHOT),
    ],
)

bo_shot = cv.group(graded, "bo-shot")
cv.gate(bo_shot, BO_SPANS)
wall = cv.group(bo_shot, "bo-wall")
blob.meeting_room(cv, wall, id="room-behind-bo")
camera.reframe(cv, wall, [(0.0, *frame(2.1, 640.0, 720.0))])
blob.bo(
    cv, bo_shot, bo_wall, end=DURATION, scale=BO_WALL_SCALE, mouth_states=ep.mouth("bo"), fps=FPS, id="bo-wall-cast"
)
wall_hand = soft_odds.in_hand(cv, bo_shot, bo_wall, "right", end=DURATION, scale=BO_WALL_SCALE, fps=FPS, id="wall-hand")
cv.gate(wall_hand, [(0.3, DURATION)])
soft_odds.hush_finger(cv, wall_hand, 0, 0, reach=REACH, scale=BO_WALL_SCALE, id="wall-finger")
soft_odds.notice(cv, bo_shot, 540, 590, shown=BO_SPANS)
soft_sets.planter(cv, cv.group(graded, "room-front"))  # the room's own marks stay behind the cast and out of frame

spoken = [(max(0.0, p.start - 0.05), p.end + 0.5, p.caption, f"caption-{i + 1}") for i, p in enumerate(P)]
ep.captions(spoken, **soft_sets.CAPTIONS)
pip_words = [
    (ON_PIP + 0.2, EYE_SLIDE + 0.5, "hello?", "stomach-1"),
    (TALK[0], TALK[1] - 0.05, "he skipped breakfast", "stomach-3"),
    (TALK[2], TALK[3] - 0.05, "a what?", "stomach-5"),
    (ASK + 0.1, ANSWER - 0.05, "are you seeing anyone?", "stomach-7"),
]
juno_words = [
    (ON_JUNO + 0.2, GOSSIP - 0.05, "hello.", "stomach-2"),
    (TALK[1], TALK[2] - 0.05, "she had a rice cake", "stomach-4"),
    (TALK[3], BLUSH - 0.05, "i know", "stomach-6"),
    (ANSWER + 0.1, WALK + 0.8, "just a yogurt", "stomach-8"),
]
ep.captions(pip_words, **{**soft_sets.CAPTIONS, "color": PIP_TINT})
ep.captions(juno_words, **{**soft_sets.CAPTIONS, "color": JUNO_TINT})
ep.captions([(SHAKE + 0.2, SNACKS - 0.05, "HELLO.", "stomach-big")], **{**soft_sets.CAPTIONS, "size": 150})
ep.captions([(SNACKS, P[2].start - 0.1, "NOTHING SINCE TUESDAY.\nWHO HAS SNACKS?", "stomach-bo")], **soft_sets.CAPTIONS)
ep.markers(extra=[("marker-hello", ON_PIP, "Hello?"), ("marker-vast", VAST, "HELLO.")])
ep.instagram(POSTS["quiet-please"])
out = ep.finish()
ep.check_overlays(out, [])

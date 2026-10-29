#!/usr/bin/env python3
"""Episode 19 — The Cake, built with srstudio: Juno, Pip and Bo in the polished break room.

    python3 the_cake_audio.py PROJECT --key-stdin < key   # the music, three voices and three effects → dialogue.json
    python3 the_cake.py PROJECT                            # → PROJECT/the-cake.scene.xml

Juno collects ten bucks from Pip for a cake: not a birthday, someone is leaving. Bo walks in carrying it (a party
horn): the company saved a whole salary. The camera cuts to the cake, WE'LL MISS YOU, and Pip finds that sweet. Bo
holds, grinning, and turns the cake on its plate (``soft-cake``): BYE PIP. A sad trombone. Pip paid ten bucks for
this; Bo thanks him for his team spirit; it is vanilla, budget cuts; and Juno asks for his chair. Every pose lands on
the beat.
"""

import os
from dataclasses import replace
from functools import partial

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, camera, layout, soft_props
from srstudio.blob import FLOOR, SCALE, SEAT
from the_cake_audio import BACK, FRONT

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="the-cake",
        number="19",
        title="The Cake — Comedy Cut 19",
        description="Pose-to-pose comedy on a beat: Pip chips in ten bucks for a leaving cake, and the boss turns it "
        "round. Native vector animation in the polished Soft break room; music composed by ElevenLabs Music, voices "
        "and effects by ElevenLabs.",
        root=project_root(__file__),
        seed=19100,
        style=SOFT,
        safe_area=layout.VERTICAL,  # the top captions stay inside x 80–920, y 220–1420
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
HORN, TURN, STING = t.horn_start, t.turn_start, t.sting_start
SING = "sing"
BEAT, EIGHTH = 0.3, 0.125  # in-between time before a pose lands on the beat (four drawings) or the eighth (two)
FPS = 15
POP = 0.08
ep.audio(extra=[("music", "assets/music.wav", {"role": "music", "gain": -6})], duck=-8)

JUNO_AT, JUNO_ASIDE = (300.0, FLOOR), (430.0, FLOOR)  # she makes room for Bo when he arrives
BO_FROM, BO_AT = (-260.0, FLOOR + 60), (200.0, FLOOR + 60)  # a step nearer the lens than Juno
ARRIVE = P[4].start  # Bo lands on "Surprise!"
CAKE_HANDS = 192 * SCALE - 14  # the plate's bottom, at the hands of the standing pose (rig y -192)
CAKE_SCALE = 0.9
cue = partial(blob.cue, scale=SCALE, ease=BEAT)


def spoken(cues: list, role: str) -> list:
    """One cue per time (the later wins), then the singing mouth on every hold that overlaps a line of ``role``."""
    cues = list({round(c.time, 6): c for c in sorted(cues, key=lambda c: c.time)}.values())
    holds = zip(cues, [c.time for c in cues[1:]] + [DURATION], strict=True)
    mine = [p for p in P if p.role == role]
    cues = [
        replace(c, mouth=SING) if any(p.start < until and c.time < p.end for p in mine) else c for c, until in holds
    ]
    return blob.settle(cues, FPS, published_full_gap_ease=True)


juno = spoken(
    [
        cue(0, "clasp", JUNO_AT, eyes="happy", mouth="smile", flip=True),  # "Ten bucks for the cake?"
        cue(P[1].start, "stand", JUNO_AT, eyes="look", mouth="smile", flip=True),
        cue(P[2].start, "clasp", JUNO_AT, eyes="squint", mouth="flat", flip=True),  # "Someone's leaving."
        cue(HORN + 0.25, "stand", JUNO_ASIDE, ease=0.5, eyes="wide", mouth="o"),  # the horn: here he comes
        cue(ARRIVE, "clasp", JUNO_ASIDE, eyes="happy", mouth="smile"),
        cue(P[5].start, "stand", JUNO_ASIDE, eyes="look", mouth="smile"),
        cue(TURN + 0.15, "stand", JUNO_ASIDE, ease=0, eyes="wide", mouth="o"),
        cue(STING + 0.5, "clasp", JUNO_ASIDE, eyes="squint", mouth="flat", flip=True),
        cue(P[7].start, "clasp", JUNO_ASIDE, eyes="happy", mouth="smile"),  # "That's team spirit."
        cue(P[8].start, "stand", JUNO_ASIDE, eyes="look", mouth="flat", flip=True),
        cue(P[10].start, "wave-a", JUNO_ASIDE, ease=EIGHTH, eyes="happy", mouth="grin", flip=True, overshoot=POP),
        cue(P[10].start + 0.5, "wave-b", JUNO_ASIDE, ease=EIGHTH, eyes="happy", mouth="grin", flip=True),
        cue(P[10].start + 1.0, "wave-a", JUNO_ASIDE, ease=EIGHTH, eyes="happy", mouth="grin", flip=True),
        cue(P[10].start + 1.5, "clasp", JUNO_ASIDE, eyes="happy", mouth="smile", flip=True),
    ],
    "juno",
)
pip = spoken(
    [
        cue(0, "sit", SEAT, eyes="look", mouth="smile"),
        cue(P[1].start, "sit", SEAT, ease=EIGHTH, eyes="happy", mouth="grin", overshoot=POP),  # "Sure!"
        cue(P[2].start + 0.3, "sit", SEAT, eyes="look", mouth="small"),
        cue(P[3].start, "sit", SEAT, ease=EIGHTH, eyes="wide", mouth="o"),  # "Oh no. Who?"
        cue(HORN + 0.25, "sit", SEAT, eyes="look", mouth="small", turn=-4),
        cue(ARRIVE, "sit", SEAT, eyes="happy", mouth="smile"),
        cue(P[5].start, "nod", SEAT, eyes="happy", mouth="smile"),  # "That's so sweet."
        cue(P[5].end + 0.1, "sit", SEAT, eyes="happy", mouth="smile"),
        cue(TURN + 0.15, "sit", SEAT, ease=0, eyes="wide", mouth="o"),  # BYE PIP
        cue(STING + 0.6, "sit", SEAT, ease=0.4, eyes="open", mouth="flat"),  # the stare, under the trombone
        cue(P[6].start, "sit", SEAT, eyes="squint", mouth="flat", turn=-4),  # "I paid ten bucks for this?"
        cue(P[7].start, "sit", SEAT, eyes="open", mouth="flat"),
        cue(P[8].start, "nod", SEAT, eyes="look", mouth="small"),  # "Is it at least chocolate?"
        cue(P[9].start + 0.6, "sit", SEAT, ease=0.4, eyes="closed", mouth="flat"),  # "Budget cuts."
        cue(P[10].start + 0.5, "sit", SEAT, ease=0, eyes="wide", mouth="o", turn=-6),  # his chair
    ],
    "pip",
)
steps = [HORN + 0.25 * k for k in range(1, int((ARRIVE - HORN) / 0.25))]
walk = [
    cue(
        w,
        "stand",
        (BO_FROM[0] + (BO_AT[0] - BO_FROM[0]) * (w - HORN) / (ARRIVE - HORN), BO_AT[1]),
        ease=0.25,
        eyes="happy",
        mouth="grin",
        lift=24 * (k % 2),
    )
    for k, w in enumerate(steps)
]
bo = spoken(
    [
        cue(0, "stand", BO_FROM, eyes="happy", mouth="grin"),
        *walk,
        cue(ARRIVE, "stand", BO_AT, ease=0.25, eyes="happy", mouth="grin", lift=30, overshoot=POP),  # "Surprise!"
        cue(ARRIVE + 0.5, "stand", BO_AT, eyes="happy", mouth="grin"),
        cue(P[5].start, "stand", BO_AT, eyes="happy", mouth="smile"),
        cue(P[5].end + 0.2, "stand", BO_AT, eyes="squint", mouth="grin"),  # the hold: he knows
        cue(TURN + 0.3, "stand", BO_AT, ease=EIGHTH, eyes="happy", mouth="grin", lift=16, overshoot=POP),
        cue(STING + 0.5, "stand", BO_AT, eyes="happy", mouth="smile"),
        cue(P[7].start, "stand", BO_AT, eyes="happy", mouth="smile", lift=10),  # "That's team spirit."
        cue(P[9].start, "stand", BO_AT, eyes="squint", mouth="flat"),  # "Vanilla. Budget cuts."
        cue(P[10].start, "stand", BO_AT, eyes="look", mouth="smile"),
    ],
    "bo",
)

room = blob.break_room(cv, ep.comp)
blob.juno(cv, room, juno, end=DURATION, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=True)
blob.pip(cv, room, pip, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=True)
blob.bo(cv, room, bo, end=DURATION, scale=SCALE, mouth_states=ep.mouth("bo"), fps=FPS, shadow=True)
carried = cv.group(room, "cake-carried")  # the cake rides in Bo's hands, a step behind his glide
cv.keys(carried, "x", [(0, BO_FROM[0]), (HORN, BO_FROM[0]), (ARRIVE, BO_AT[0])], hold=False)
cv.keys(carried, "y", [(0, BO_AT[1] - CAKE_HANDS)])
# The lettering is text, which the engine holds inside the safe area: it shows once Bo has landed, and not while the
# camera is on Pip and the cake is out of frame.
READABLE = [(ARRIVE + 0.05, P[6].start - 0.1), (P[7].start - 0.05, DURATION)]
soft_props.cake(cv, carried, FRONT, back=BACK, turn_at=TURN, scale=CAKE_SCALE, lettering=READABLE, id="cake")

# Cut to the cake as Pip reads it, hold through the turn and the trombone, cut to Pip for his line, then back wide.
CAKE_FOCUS = (BO_AT[0], BO_AT[1] - CAKE_HANDS - 100)
PIP_FOCUS = (SEAT[0], SEAT[1] - 330)
camera.anchor(room, 540, 960)


def framed(time: float, scale: float, focus=(540.0, 960.0), at=(540.0, 960.0)) -> tuple:
    """A cut at ``time`` that puts the room point ``focus`` at the screen point ``at``, magnified ``scale``."""
    return (time, scale, at[0] + scale * (540 - focus[0]), at[1] + scale * (960 - focus[1]))


camera.reframe(
    cv,
    room,
    [
        framed(0, 1.0),
        framed(P[5].start - 0.05, 2.0, CAKE_FOCUS, (540, 1250)),
        framed(P[6].start - 0.1, 1.6, PIP_FOCUS, (540, 1150)),
        framed(P[7].start - 0.05, 1.0),
    ],
)
specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.02 if i + 1 < len(P) else DURATION
    specs.append((max(0.0, p.start - 0.05), min(until, p.end + 1.2), p.caption, f"caption-{i + 1}"))
ep.captions(
    specs, x=80, y=250, width=840, height=180, size=58, color="#1A1714", stroke="#FFFFFF", stroke_width=7, shadow=None
)
ep.markers(
    extra=[
        ("marker-horn", HORN, "Bo arrives"),
        ("marker-turn", TURN, "The cake turns"),
        ("marker-sting", STING, "Sad trombone"),
    ]
)
ep.instagram(POSTS["the-cake"])
ep.finish()

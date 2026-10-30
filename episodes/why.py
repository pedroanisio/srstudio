#!/usr/bin/env python3
"""Why, built with srstudio: five whys to the edge of what anyone knows.

    srstudio record why PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build why PROJECT    # → PROJECT/why.scene.xml

A tall parent, a small child, a window full of sky. "Why is the sky blue?" Each answer is shorter than the last and each
"Why?" is the same shot, while the parent's close-up comes in a little more every time. At "the universe" he goes down
to the floor and the light goes out of the room. "We just got up one day and did it." Pip pats his shoulder. "Okay."
Then the same room with the sizes swapped: Pip at the door, tall, in a tie, with a briefcase. Bo, small, under the
window. "We'll talk about your bedtime." "...Why?"

The first second is a held frame (arm A of the ``sp-hook_motion`` test): nobody moves and nobody speaks until 1 s.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, layout, soft_props, soft_sets
from srstudio.soft_sets import Dim, Shot
from why_audio import INTERVIEW

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="why",
        title=INTERVIEW.title,
        description="Family comedy: a four-year-old's why walks a parent to the edge of human knowledge, and then "
        "brings up the bedtime. Native vector animation; ElevenLabs dialogue, synthesised foley, no music.",
        root=ROOT,
        seed=42102,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions stay inside x 80–920
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
WHYS = [float(w) for w in t.meta["whys"]]
FLOOR, PAT, DOOR = t.floor_start, t.pat_start, t.door_start
FPS = 15
TALL, SMALL = 2.3, 1.25
BO_AT, PIP_AT = (760.0, 1900.0), (290.0, 1800.0)
BO_SAT = (820.0, 2040.0)  # sitting on the floor, in front of the rug
PIP_BY = (440.0, 2010.0)  # beside him, nearer us, a hand up to his shoulder
PIP_TALL, BO_SMALL = (760.0, 1900.0), (290.0, 1800.0)  # the sizes swap, and the spots stay
PIP_CLOSE = Shot(0.0, 2.7, 300.0, 1210.0)
BO_CLOSES = [Shot(0.0, 1.5 + 0.28 * k, 760.0, 900.0) for k in range(4)]

foley.write_whoosh(ROOT / "assets" / "sit.wav", [FLOOR + 0.1], DURATION, length=0.4, seed=42103)
foley.write_typing(ROOT / "assets" / "pat.wav", [PAT + 0.1, PAT + 0.25, PAT + 0.4], DURATION, seed=42104)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("sit", "assets/sit.wav", {"role": "effects", "gain": -9}),
        ("pat", "assets/pat.wav", {"role": "effects", "gain": -6}),
    ]
)


def spans(role: str) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role]


def tall(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=TALL, **kw)


def small(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SMALL, **kw)


def quiet(cues, lines, end):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for _, stop in lines:
        held = [c for c in cues if c.time <= stop][-1]
        if held.time != stop:
            later.append(replace(held, time=stop, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, end, FPS)


bo_then = quiet(
    [
        tall(0, "stand", BO_AT, eyes="look", mouth="smile"),
        tall(WHYS[1], "stand", BO_AT, eyes="look", mouth="smile"),
        tall(WHYS[3], "stand", BO_AT, eyes="squint", mouth="flat"),
        tall(WHYS[5], "stand", BO_AT, eyes="wide", mouth="flat"),
        tall(WHYS[6], "stand", BO_AT, eyes="wide", mouth="small"),
        tall(FLOOR + 0.5, "sit", BO_SAT, ease=0.5, eyes="wide", mouth="flat"),
        tall(P[10].start, "sit", BO_SAT, eyes="squint", mouth="flat"),
        tall(P[11].start, "sit", BO_SAT, eyes="closed", mouth="flat"),
        tall(P[11].end, "sit", BO_SAT, eyes="open", mouth="flat"),
    ],
    [s for s in spans("bo") if s[0] < DOOR],
    DOOR,
)
pip_then = quiet(
    [
        small(0, "stand", PIP_AT, eyes="look", mouth="smile", flip=True),
        small(FLOOR, "stand", PIP_AT, eyes="wide", mouth="small", flip=True),
        small(P[11].end, "step", PIP_BY, ease=0.4, eyes="look", mouth="smile", flip=True),
        small(PAT + 0.1, "wave-a", PIP_BY, eyes="happy", mouth="smile"),
        small(PAT + 0.25, "wave-b", PIP_BY, eyes="happy", mouth="smile"),
        small(PAT + 0.4, "wave-a", PIP_BY, eyes="happy", mouth="smile"),
    ],
    [s for s in spans("pip") if s[0] < DOOR],
    DOOR,
)
pip_now = quiet(
    [tall(0, "stand", PIP_TALL, eyes="open", mouth="flat")], [s for s in spans("pip") if s[0] >= DOOR], DURATION
)
bo_now = quiet(
    [small(0, "sit", BO_SMALL, eyes="wide", mouth="flat", flip=True)],
    [s for s in spans("bo") if s[0] >= DOOR],
    DURATION,
)


def cast(g):
    then = cv.group(g, "then")
    cv.gate(then, [(0.0, DOOR)])
    blob.bo(cv, then, bo_then, end=DOOR, scale=TALL, mouth_states=ep.mouth("bo"), fps=FPS, shadow=False)
    blob.pip(cv, then, pip_then, end=DOOR, scale=SMALL, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False)
    now = cv.group(g, "now")
    cv.gate(now, [(DOOR, DURATION)])
    blob.pip(
        cv, now, pip_now, end=DURATION, scale=TALL, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False, id="pip-now"
    )
    blob.bo(cv, now, bo_now, end=DURATION, scale=SMALL, mouth_states=ep.mouth("bo"), fps=FPS, shadow=False, id="bo-now")
    soft_props.necktie(cv, now, PIP_TALL[0], 1290, scale=2.0)
    soft_props.briefcase(cv, now, PIP_TALL[0] + 255, 1440, scale=1.5)


shots = [Shot(0.0)]
for k, at in enumerate(WHYS):
    shots.append(PIP_CLOSE._replace(time=at) if k % 2 == 0 else BO_CLOSES[k // 2]._replace(time=at))
shots += [
    Shot(FLOOR),
    Shot(P[9].start - 0.05, 1.5, 740.0, 1220.0),
    Shot(P[11].end + 0.3, 1.25, 620.0, 1260.0),
    Shot(DOOR),
]

graded = soft_sets.finish(cv, ep.comp)
soft_sets.playroom(cv, graded, shots=shots, dim=Dim(FLOOR + 0.2, 1.6, DOOR, 700.0, 1260.0), cast=cast)

CUTS = [*WHYS, FLOOR, P[9].start, DOOR]
speech = {"pip": [], "bo": []}
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    after = [c for c in CUTS if c > p.start + 0.05]
    cut = min(after) if after else DURATION
    start = 0.0 if i == 0 else max(0.0, p.start - 0.05)  # the question is on the held frame, a second early
    end = DURATION if i + 1 == len(P) else max(p.end, min(until, cut, p.end + 0.45))  # the holds stay silent to read
    speech[p.role].append((start, end, p.caption, f"caption-{i + 1}"))
ep.captions(speech["pip"], **{**soft_sets.CAPTIONS, "color": "#2F5D8C"})
ep.captions(speech["bo"], **soft_sets.CAPTIONS)
ep.markers(extra=[("marker-floor", FLOOR, "The floor"), ("marker-door", DOOR, "The door")])
ep.instagram(POSTS["why"])
ep.finish()

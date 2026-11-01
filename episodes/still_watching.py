#!/usr/bin/env python3
"""Still Watching, built with srstudio: the only thing that checks on you at 4 a.m.

    srstudio record still-watching PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build still-watching PROJECT    # → PROJECT/still-watching.scene.xml

Bo on the sofa, blue light, a bag of chips. Nothing moves. "Are you still watching?" The television goes on to his
eating, and then his mother. He climbs over the sofa, raises the blind and morning comes in on his face. "Thanks."
"Good." Then the countdown, the blind drops, the night comes back and he dives over the sofa into the first frame.

The first frame is held to .45 s (the reel's STILL arm of ``sp-hook_motion``): nothing moves until the question.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, layout, soft_home, soft_props, soft_sets
from srstudio.soft_props import TimeState
from srstudio.soft_sets import Shot
from still_watching_audio import INTERVIEW, STILL

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "still-watching"
ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug=SLUG,
        title=INTERVIEW.title,
        description="Everyday-tech comedy: at four in the morning the only one checking on Bo is the television. "
        "Native vector animation; ElevenLabs dialogue, synthesised foley, no music.",
        root=ROOT,
        seed=3304,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions stay inside x 80–920
        bleed=True,  # the window's far plane is blurred
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
CHIP, GLANCE, UP, MORNING, DIVE = t.chip_start, t.glance_start, t.up_start, t.morning_end, t.dive_start
FPS = 15
SCALE = 1.8
SEAT = (640.0, 1500.0)  # the hip on the sofa
WINDOW = (775.0, 1640.0)  # standing behind the sofa, a hand on the cord
LANDED = P[14].end + 0.28
OVER_TOP = UP + 0.5  # the climb's middle: from here he is behind the sofa
OVER_BACK = DIVE + 0.3  # the dive's middle: from here he is on it again
BLIND_UP = UP + 1.2  # the cord comes down
OPEN = BLIND_UP + 1.9  # the blind is up and the room is morning
BLIND_DROP = DIVE + 0.1
COUNT = P[13].start + 0.5  # the voice bars give way to the digits

foley.write_bursts(
    ROOT / "assets" / "cord.wav", [BLIND_UP + 0.25 * k for k in range(7)], DURATION, foley.SCRAPE, seed=3305
)
foley.write_dawn(
    ROOT / "assets" / "dawn.wav",
    [BLIND_UP + 0.9, OPEN - 0.2, OPEN + 0.55, OPEN + 1.25, OPEN + 1.9],
    DURATION,
    seed=3306,
)
foley.write_whoosh(ROOT / "assets" / "blind.wav", [BLIND_DROP + 0.26], DURATION, length=0.3, seed=3307)
foley.write_bursts(ROOT / "assets" / "land.wav", [LANDED - 0.02], DURATION, foley.THUD, seed=3308)
foley.write_bursts(ROOT / "assets" / "climb.wav", [UP + 0.2, UP + 0.72], DURATION, foley.KNOCK, seed=3309)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("cord", "assets/cord.wav", {"role": "effects", "gain": -16}),
        ("dawn", "assets/dawn.wav", {"role": "effects", "gain": -15}),
        ("blind", "assets/blind.wav", {"role": "effects", "gain": -10}),
        ("land", "assets/land.wav", {"role": "effects", "gain": -7}),
        ("climb", "assets/climb.wav", {"role": "effects", "gain": -16}),
    ],
    loudness="-14",
)


def spans(role: str) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role]


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def quiet(cues, lines, end):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for at in sorted(t for span in lines for t in span):  # a hold splits at a line, so only the line itself talks
        held = [c for c in cues if c.time <= at][-1]
        if held.time != at:
            later.append(replace(held, time=at, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, end, FPS)


bo = quiet(
    [
        cue(0, "sit", SEAT, eyes="open", mouth="flat"),
        cue(P[2].start, "sit", SEAT, eyes="open", mouth="flat"),
        cue(CHIP + 0.32, "sit-show", SEAT, ease=0.28, eyes="look", mouth="flat"),
        cue(P[5].start + 0.5, "sit-show", SEAT, eyes="squint", mouth="flat"),
        cue(P[6].start, "sit", SEAT, ease=0.12, eyes="wide", mouth="small"),
        cue(P[6].end, "sit", SEAT, eyes="wide", mouth="flat"),
        cue(GLANCE + 0.25, "sit-back", SEAT, ease=0.22, eyes="look", mouth="flat"),
        cue(P[8].start - 0.1, "sit", SEAT, ease=0.2, eyes="open", mouth="flat"),
        cue(P[9].start + 0.25, "sit", SEAT, eyes="open", mouth="flat"),
        cue(UP, "sit", SEAT, eyes="open", mouth="flat"),
        cue(UP + 0.95, "stand", WINDOW, ease=0.9, lift=60, eyes="open", mouth="flat"),
        cue(BLIND_UP, "wave-a", WINDOW, ease=0.22, eyes="open", mouth="flat"),
        cue(BLIND_UP + 0.95, "wave-a", WINDOW, eyes="squint", mouth="flat"),
        cue(OPEN, "wave-b", WINDOW, ease=0.5, eyes="closed", mouth="flat"),
        cue(OPEN + 0.6, "stand", (WINDOW[0], WINDOW[1] - 26), ease=0.55, eyes="closed", mouth="flat"),
        cue(OPEN + 1.15, "stand", WINDOW, ease=0.5, eyes="closed", mouth="flat"),
        cue(MORNING - 0.35, "stand", WINDOW, ease=0.3, eyes="open", mouth="smile"),
        cue(P[12].start, "stand", WINDOW, eyes="happy", mouth="smile"),
        cue(P[13].start + 0.6, "stand", WINDOW, eyes="wide", mouth="flat"),
        cue(DIVE, "cheer-b", WINDOW, ease=0.16, eyes="wide", mouth="flat"),
        cue(LANDED, "sit", SEAT, ease=LANDED - DIVE - 0.02, lift=170, eyes="wide", mouth="flat"),
        cue(LANDED + 0.2, "sit", SEAT, eyes="open", mouth="flat"),
    ],
    spans("bo"),
    DURATION,
)


def rig(parent, id: str, spans_on):
    g = cv.group(parent, f"{id}-gate")
    cv.gate(g, spans_on)
    blob.bo(cv, g, bo, end=DURATION, scale=SCALE, mouth_states=ep.mouth("bo"), fps=FPS, shadow=False, id=id)


def behind(g):
    rig(g, "bo-window", [(OVER_TOP, OVER_BACK)])


def cast(g):
    soft_home.chip_bag(cv, g, 880, 1512, scale=1.15)
    rig(g, "bo", [(0.0, OVER_TOP), (OVER_BACK, DURATION)])
    hands = blob.held(cv, g, bo, end=DURATION, scale=SCALE, fps=FPS, id="bo-hands")
    cv.gate(hands, [(CHIP + 0.2, P[6].start)])
    soft_home.chip(cv, hands, 0, -26, scale=1.2)


def lit(g):
    soft_home.television(
        cv,
        g,
        x=206,
        y=1280,
        still=STILL,
        talks=[*spans("tv")[:-2], (P[13].start, COUNT)],
        counts=(("5", COUNT, P[14].start), ("4", P[14].start, DURATION)),
    )


CLOSE = Shot(P[7].start, 1.32, 520.0, 940.0)
shots = [Shot(0.0), CLOSE, Shot(UP), Shot(BLIND_UP + 0.5, 1.28, 760.0, 900.0), Shot(P[13].start)]
day = ((0.0, 0.0), (BLIND_UP, 0.0), (OPEN, 1.0), (BLIND_DROP, 1.0), (BLIND_DROP + 0.28, 0.0))
graded = soft_sets.finish(cv, ep.comp)
soft_home.den(cv, graded, end=DURATION, day=day, still=STILL, shots=shots, behind=behind, cast=cast, lit=lit)
card = soft_props.time_card(cv, ep.comp, [TimeState("4:02 AM", 0.0, P[2].start)], (332, 446, 416, 118), size=80)

specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    specs.append((p.role, p.start - 0.03, min(until, max(p.end + 0.35, p.start + 0.86)), p.caption, f"caption-{i + 1}"))
shown = [
    *ep.captions([s[1:] for s in specs if s[0] == "bo"], **soft_sets.CAPTIONS),
    *ep.captions([s[1:] for s in specs if s[0] == "tv"], **{**soft_sets.CAPTIONS, "color": "#2F5D8C"}),
]
ep.hide_on_cover(card, *shown)
ep.markers(extra=[("marker-glance", GLANCE, "The empty room"), ("marker-open", OPEN, "Morning")])
if SLUG in POSTS:
    ep.instagram(POSTS[SLUG])
ep.finish()

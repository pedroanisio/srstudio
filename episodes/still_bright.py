#!/usr/bin/env python3
"""Still Bright, built with srstudio: a twelve dollar lamp, and the man who reviewed it.

    srstudio record still-bright PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build still-bright PROJECT    # → PROJECT/still-bright.scene.xml

Juno wants to buy the lamp. Pip reads the reviews, and one reviewer keeps updating his. The phone fills the frame for
every update, and the stars go 4, 4, 5, 1. It gets dark, the clock says 2:40 a.m., and they send him a lamp. For the
first time we see Dale, alone at a table, eyes shut to slits behind the lamp they sent. She was right.

The first frame already moves (arm B of the ``sp-hook_motion`` test): Juno is mid-bounce on her first word.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, layout, soft_props, soft_sets
from srstudio.soft_props import TimeState
from still_bright_audio import INTERVIEW

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="still-bright",
        title=INTERVIEW.title,
        description="Everyday comedy: two people read a stranger's lamp reviews until two in the morning, and send him "
        "a lamp. Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        seed=INTERVIEW.seed,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions, the clock and the review card's lettering stay inside x 80–920
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
INSERTS = [(float(a), float(b)) for a, b in t.meta["inserts"]]
SIT, CLOCK, PING, DALE = t.sit_start, t.clock_start, t.ping_start, t.dale_start
FPS = 15
SCALE = blob.SCALE
JUNO_AT = (215.0, 1590.0)  # on her feet on the rug, ready to go
JUNO_SEAT = (320.0, 1155.0)  # the sofa's far end
PIP_SEAT = (680.0, 1395.0)
DALE_SEAT = blob.SEAT
LAMP_AT = (500.0, 1185.0)  # on the table, between Dale and the room
GLARE_REACH = 320.0  # behind Dale and short of the far wall: the bloom must not take his arm, the cactus or the mark
NIGHT = "#1E2A3A"
REVIEWER = "Dale R."
STARS = (4, 4, 5, 1)  # the rating moves with the marriage

foley.write_whoosh(ROOT / "assets" / "flip.wav", [a for a, _ in INSERTS], DURATION, length=0.2, seed=INTERVIEW.seed + 1)
foley.write_bursts(ROOT / "assets" / "ping.wav", [PING], DURATION, foley.BELL, seed=INTERVIEW.seed + 2)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("flip", "assets/flip.wav", {"role": "effects", "gain": -14}),
        ("ping", "assets/ping.wav", {"role": "effects", "gain": -8}),
    ]
)


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def spans(role: str) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role]


def quiet(cues, lines):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for _, stop in lines:
        held = [c for c in cues if c.time <= stop][-1]
        if held.time != stop:
            later.append(replace(held, time=stop, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, DURATION, FPS)


juno = quiet(
    [
        cue(0, "clasp", JUNO_AT, flip=True, eyes="squint", mouth="small"),
        cue(0.28, "clasp", JUNO_AT, flip=True, ease=0.26, lift=30, eyes="squint", mouth="small"),
        cue(0.56, "clasp", JUNO_AT, flip=True, ease=0.26, lift=18, eyes="look", mouth="flat"),
        cue(P[3].start, "clasp", JUNO_AT, flip=True, ease=0.12, eyes="squint", mouth="flat"),
        cue(SIT + 0.5, "sit", JUNO_SEAT, flip=True, ease=0.5, eyes="look", mouth="flat"),
        cue(P[5].start, "sit", JUNO_SEAT, flip=True, ease=0.1, eyes="look", mouth="small"),
        cue(CLOCK + 0.35, "type-a", JUNO_SEAT, flip=True, ease=0.35, eyes="wide", mouth="flat"),
        cue(P[8].end + 0.05, "sit", JUNO_SEAT, flip=True, ease=0.15, lift=14, eyes="wide", mouth="o"),
        cue(P[9].start, "type-a", JUNO_SEAT, flip=True, ease=0.2, eyes="squint", mouth="flat"),
        cue(P[10].end, "type-a", JUNO_SEAT, flip=True, eyes="look", mouth="flat"),
        cue(PING + 0.25, "type-a", JUNO_SEAT, flip=True, ease=0.15, lift=12, eyes="wide", mouth="o"),
    ],
    spans("juno"),
)
pip = quiet(
    [
        cue(0, "sit", PIP_SEAT, eyes="look", mouth="flat"),
        cue(P[1].start, "sit", PIP_SEAT, ease=0.1, eyes="look", mouth="small"),
        cue(CLOCK + 0.35, "type-a", PIP_SEAT, ease=0.35, eyes="wide", mouth="flat"),
        cue(P[10].end, "type-a", PIP_SEAT, eyes="look", mouth="flat"),
        cue(PING + 0.25, "type-a", PIP_SEAT, ease=0.15, lift=12, eyes="wide", mouth="o"),
    ],
    spans("pip"),
)
dale = quiet(
    [
        cue(0, "sit", DALE_SEAT, eyes="squint", mouth="flat"),
        cue(P[11].end, "sit", DALE_SEAT, eyes="squint", mouth="flat"),
        cue(P[12].end, "sit", DALE_SEAT, eyes="closed", mouth="flat"),
    ],
    [(a, b) for a, b in spans("dale") if a >= DALE],
)


def on_sofa(g):
    blob.juno(cv, g, juno, end=DURATION, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=False)
    blob.pip(cv, g, pip, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False)
    hands = blob.held(cv, g, pip, end=DURATION, scale=SCALE, fps=FPS, id="pip-hands")
    soft_props.phone(cv, hands, scale=0.7, id="pip-phone")


graded = soft_sets.finish(cv, ep.comp)
blob.home(cv, graded, shots=[(0.0, DALE)], on_sofa=on_sofa)
night = cv.group(graded, "night")
cv.gate(night, [(CLOCK, DALE)])
cv.rect(night, 0, 0, 1080, 1920, NIGHT, opacity=0.45)

room = cv.group(graded, "dales-room")
cv.gate(room, [(DALE, DURATION)])
blob.office(cv, room)
cv.rect(room, 0, 0, 1080, 1920, NIGHT, opacity=0.8)
soft_props.glare_lamp(cv, room, *LAMP_AT, reach=GLARE_REACH)
blob.bo(cv, room, dale, end=DURATION, scale=SCALE, mouth_states=ep.mouth("dale"), fps=FPS, shadow=False)

soft_props.time_card(cv, ep.comp, [TimeState("2:40 AM", CLOCK, DALE)], (465, 470, 440, 118))

for i, (span, stars) in enumerate(zip(INSERTS, STARS, strict=True), start=1):
    insert = cv.group(ep.comp, f"review-{i}")
    cv.gate(insert, [span])
    cv.rect(insert, 0, 0, 1080, 1920, "#2E3A33", opacity=0.72)
    soft_props.phone(
        cv,
        insert,
        x=540,
        y=960,
        scale=2.3,
        screen=lambda g, stars=stars, i=i: soft_props.review_view(cv, g, REVIEWER, stars, id=f"review-view-{i}"),
        id=f"review-phone-{i}",
    )

CUTS = [*(b for _, b in INSERTS), CLOCK, DALE]
specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    later = [c for c in CUTS if c > p.start]
    cut = min(later, default=DURATION)
    end = DURATION if i + 1 == len(P) else min(until, cut, p.end + 0.6)
    specs.append((max(0.0, p.start - 0.05), end, p.caption, f"caption-{i + 1}"))
ep.captions(specs, **soft_sets.CAPTIONS)
ep.markers(extra=[("marker-clock", CLOCK, "2:40 a.m."), ("marker-dale", DALE, "Dale")])
ep.instagram(POSTS["still-bright"])
out = ep.finish()
ep.check_overlays(out, ["soft-time-card"])

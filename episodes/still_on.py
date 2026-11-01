#!/usr/bin/env python3
"""Still On, built with srstudio: the best news in friendship is the other person canceling first.

    srstudio record still-on PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build still-on PROJECT    # → PROJECT/still-on.scene.xml

Two homes cut in two, two matching blankets. "Still on for tonight!" "Can't wait!" Each face falls when the message
goes. "Please cancel." Neither will. They go, hug outside the restaurant, and over each shoulder the smile goes. The
camera tilts down to four slippers. "Same time next year?" "Can't wait!"

The first frame already moves (the reel's arm of ``sp-hook_motion``): both are typing, and Juno speaks by .5 s.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, layout, soft_home, soft_props, soft_sets
from srstudio.soft_sets import Shot
from still_on_audio import ARRIVE, BACK, HUG, INTERVIEW, LOOK, SAG, SLIPPERS, TILT

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "still-on"
ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug=SLUG,
        title=INTERVIEW.title,
        description="Friendship comedy: two friends who would both love to cancel, and neither of whom will. Native "
        "vector animation; ElevenLabs dialogue, synthesised foley, no music.",
        root=ROOT,
        seed=3324,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions stay inside x 80–920
        bleed=True,  # the street's far plane is blurred
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
SAGGED, OUT = t.sag_start, t.out_start
FPS = 15
HOME, STREET = 1.2, 2.2
JUNO_SEAT, PIP_SEAT = (352.0, 1296.0), (728.0, 1296.0)
JUNO_UP, PIP_UP = (300.0, 1404.0), (780.0, 1404.0)
FLOOR = 2120.0  # the street is a medium: feet, and what is on them, stay below the frame until the tilt
PIP_HUG, JUNO_HUG = (250.0, FLOOR), (830.0, FLOOR)
HUGGED = OUT + ARRIVE
GONE = HUGGED + 0.55  # over each shoulder, the smile goes
DOWN = HUGGED + HUG
UP = DOWN + TILT + SLIPPERS
DROP = 620.0

foley.write_typing(ROOT / "assets" / "keys.wav", [0.1, 0.3, 0.5, 0.7], DURATION, seed=3325)
foley.write_bursts(ROOT / "assets" / "sent.wav", [P[0].end + 0.05, P[1].end + 0.03], DURATION, foley.CHIRP, seed=3326)
foley.write_bursts(
    ROOT / "assets" / "steps.wav", [OUT + 0.1 + 0.28 * k for k in range(4)], DURATION, foley.KNOCK, seed=3327
)
foley.write_whoosh(ROOT / "assets" / "tilt.wav", [DOWN + TILT - 0.02], DURATION, length=0.45, seed=3328)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("keys", "assets/keys.wav", {"role": "effects", "gain": -15}),
        ("sent", "assets/sent.wav", {"role": "effects", "gain": -18}),
        ("steps", "assets/steps.wav", {"role": "effects", "gain": -18}),
        ("tilt", "assets/tilt.wav", {"role": "effects", "gain": -14}),
    ],
    loudness="-14",
)


def spans(role: str) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role]


def quiet(cues, lines, end):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for at in sorted(x for span in lines for x in span):  # a hold splits at a line, so only the line itself talks
        held = [c for c in cues if c.time <= at][-1]
        if held.time != at:
            later.append(replace(held, time=at, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, end, FPS)


def home(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=HOME, **kw)


def street(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=STREET, **kw)


def typing(seat, until: float, **kw):
    n = int(until / 0.2) + 1
    return [home(k * 0.2, "type-a" if k % 2 else "type-b", seat, **kw) for k in range(n)]


def walking(start_x: float, spot, side: bool):
    steps = 4
    rows = []
    for k in range(steps):
        x = start_x + (spot[0] - start_x) * (k + 1) / steps
        at = OUT + ARRIVE * (k + 1) / steps
        rows.append(street(at, "walk-b" if k % 2 else "walk-a", (x, FLOOR), ease=ARRIVE / steps, flip=side))
    return [replace(c, eyes="happy", mouth="grin") for c in rows]


juno_home = quiet(
    [
        *typing(JUNO_SEAT, P[0].end, eyes="happy", mouth="grin"),
        home(P[0].end + 0.12, "sit", JUNO_SEAT, eyes="open", mouth="flat"),
        home(P[1].start + 0.4, "sit", JUNO_SEAT, eyes="open", mouth="flat"),
        home(P[3].start, "sit", JUNO_SEAT, eyes="wide", mouth="flat"),
        home(P[4].start, "nod", JUNO_SEAT, ease=0.1, eyes="happy", mouth="grin"),
        home(P[5].start, "sit", JUNO_SEAT, eyes="squint", mouth="flat"),
        home(P[6].start, "nod", JUNO_SEAT, ease=0.1, eyes="happy", mouth="grin"),
        home(SAGGED + SAG, "lounge", JUNO_SEAT, ease=SAG, eyes="closed", mouth="flat"),
        home(SAGGED + SAG + LOOK, "sit", JUNO_SEAT, ease=0.25, eyes="look", mouth="flat"),
        home(OUT - 0.02, "stand", JUNO_UP, ease=0.5, lift=30, eyes="open", mouth="flat"),
    ],
    [s for s in spans("juno") if s[0] < OUT],
    OUT,
)
pip_home = quiet(
    [
        *typing(PIP_SEAT, P[1].start, eyes="open", mouth="smile", flip=True),
        home(P[1].start, "type-a", PIP_SEAT, eyes="happy", mouth="grin", flip=True),
        home(P[1].end + 0.14, "sit", PIP_SEAT, eyes="open", mouth="flat", flip=True),
        home(P[2].start, "sit", PIP_SEAT, eyes="wide", mouth="flat", flip=True),
        home(P[5].start, "nod", PIP_SEAT, ease=0.1, eyes="happy", mouth="grin", flip=True),
        home(P[6].start, "sit", PIP_SEAT, eyes="squint", mouth="flat", flip=True),
        home(P[7].start, "nod", PIP_SEAT, ease=0.1, eyes="happy", mouth="grin", flip=True),
        home(SAGGED + SAG, "lounge", PIP_SEAT, ease=SAG, eyes="closed", mouth="flat", flip=True),
        home(SAGGED + SAG + LOOK, "sit", PIP_SEAT, ease=0.25, eyes="look", mouth="flat", flip=True),
        home(OUT - 0.02, "stand", PIP_UP, ease=0.5, lift=30, eyes="open", mouth="flat", flip=True),
    ],
    [s for s in spans("pip") if s[0] < OUT],
    OUT,
)
pip_out = quiet(
    [
        street(0, "walk-a", (-280.0, FLOOR), eyes="happy", mouth="grin"),
        *walking(-280.0, PIP_HUG, False),
        street(HUGGED + 0.14, "hug", PIP_HUG, ease=0.14, eyes="happy", mouth="grin"),
        street(GONE, "hug", PIP_HUG, eyes="open", mouth="flat"),
        street(DOWN + 0.5, "stand", PIP_HUG, ease=0.4, eyes="look", mouth="flat"),
        street(UP + BACK + 0.05, "stand", PIP_HUG, eyes="happy", mouth="grin"),
    ],
    [s for s in spans("pip") if s[0] >= OUT],
    DURATION,
)
juno_out = quiet(
    [
        street(0, "walk-a", (1360.0, FLOOR), eyes="happy", mouth="grin", flip=True),
        *walking(1360.0, JUNO_HUG, True),
        street(HUGGED + 0.14, "hug", JUNO_HUG, ease=0.14, eyes="happy", mouth="grin", flip=True),
        street(GONE, "hug", JUNO_HUG, eyes="closed", mouth="flat", flip=True),
        street(DOWN + 0.5, "stand", JUNO_HUG, ease=0.4, eyes="look", mouth="flat", flip=True),
        street(UP + BACK + 0.05, "stand", JUNO_HUG, eyes="happy", mouth="grin", flip=True),
    ],
    [s for s in spans("juno") if s[0] >= OUT],
    DURATION,
)
PHONES = (0.0, SAGGED + 0.1)


def indoors(g):
    for name, cues, draw, color, nudge in (
        ("pip", pip_home, blob.pip, "#6C8FB5", -24.0),
        ("juno", juno_home, blob.juno, "#6C8FB5", 24.0),
    ):
        draw(cv, g, cues, end=OUT, scale=HOME, mouth_states=ep.mouth(name), fps=FPS, shadow=False, id=f"{name}-home")
        wrap = blob.worn(cv, g, cues, end=OUT, scale=HOME, fps=FPS, id=f"{name}-wrapped")
        soft_home.blanket(cv, wrap, nudge, 30, scale=HOME * 0.78, color=color, id=f"{name}-blanket")
        hands = blob.held(cv, g, cues, end=OUT, scale=HOME, fps=FPS, id=f"{name}-hands")
        cv.gate(hands, [PHONES])
        soft_props.phone(cv, hands, y=-20, scale=0.5, id=f"{name}-phone")


def outdoors(g):
    for name, cues, draw, color, slipper, spot in (
        ("pip", pip_out, blob.pip, "#3E7FC8", "#8FC7B0", PIP_HUG),
        ("juno", juno_out, blob.juno, "#C8473E", "#E79BB0", JUNO_HUG),
    ):
        draw(
            cv,
            g,
            cues,
            end=DURATION,
            scale=STREET,
            mouth_states=ep.mouth(name),
            fps=FPS,
            shadow=False,
            id=f"{name}-out",
        )
        wrap = blob.worn(cv, g, cues, end=DURATION, scale=STREET, fps=FPS, id=f"{name}-worn")
        soft_home.scarf(cv, wrap, 0, 0, scale=STREET, color=color, id=f"{name}-scarf")
        soft_home.slippers(cv, g, spot[0], FLOOR - 16, scale=STREET, color=slipper, id=f"{name}-slippers")


LEFT, RIGHT = Shot(0.0, 2.0, 270.0, 960.0), Shot(0.0, 2.0, 810.0, 960.0)
shots = [
    Shot(0.0),
    RIGHT._replace(time=P[1].start - 0.05),
    LEFT._replace(time=P[3].start - 0.05),
    RIGHT._replace(time=P[5].start - 0.04),
    LEFT._replace(time=P[6].start - 0.03),
    RIGHT._replace(time=P[7].start - 0.03),
    Shot(SAGGED),
]
graded = soft_sets.finish(cv, ep.comp)
inside = cv.group(graded, "indoors")
cv.gate(inside, [(0.0, OUT)])
soft_home.flats(cv, inside, shots=shots, cast=indoors)
outside = cv.group(graded, "outdoors")
cv.gate(outside, [(OUT, DURATION)])
soft_home.doorway(cv, outside, tilt=DOWN, back=UP, drop=DROP, seconds=TILT, cast=outdoors)
card = soft_home.hook_card(cv, ep.comp, "DINNER TONIGHT", (250, 446, 580, 104), end=P[1].start)

specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    specs.append(
        (p.role, max(0.0, p.start - 0.03), min(until, max(p.end + 0.35, p.start + 0.86)), p.caption, f"caption-{i + 1}")
    )
shown = [
    *ep.captions([s[1:] for s in specs if s[0] == "juno"], **soft_sets.CAPTIONS),
    *ep.captions([s[1:] for s in specs if s[0] == "pip"], **{**soft_sets.CAPTIONS, "color": "#2F5D8C"}),
]
ep.hide_on_cover(card, *shown)
ep.markers(extra=[("marker-out", OUT, "The door"), ("marker-slippers", DOWN + TILT, "Four slippers")])
if SLUG in POSTS:
    ep.instagram(POSTS[SLUG])
ep.finish()

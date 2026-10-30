#!/usr/bin/env python3
"""Hang Out, built with srstudio: two friends who have to catch up, for fifty-odd years.

    srstudio record hang-out PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build hang-out PROJECT    # → PROJECT/hang-out.scene.xml

"We HAVE to catch up!" "So bad! I'm free... March?" "I'm away in March." The two-shot never changes, and everything
behind it does: the year card flips, the staked sapling between them grows into a crown wider than the frame, a town
rises. "This week's crazy." wears down to "Crazy." Then the bench, two canes, and it is so good to see each other. They
take out their phones. "I'm free... March?" The last frame is the two phones, the same month, and hers is already
stamped AWAY.

The first frame already moves (arm B of the ``sp-hook_motion`` test): Juno is mid-bounce on her first word.
"""

import os

from _common import project_root
from hang_out_audio import INTERVIEW
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, layout, soft_props, soft_sets
from srstudio.soft_props import TimeState
from srstudio.soft_sets import BENCH_SEAT

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="hang-out",
        title=INTERVIEW.title,
        description="Friendship comedy: two best friends who have to catch up, and offer each other March for fifty "
        "years. Native vector animation; ElevenLabs dialogue, synthesised foley, no music.",
        root=ROOT,
        seed=40602,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions, the year card and the phones' lettering stay inside x 80–920
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
YEARS = [float(y) for y in t.meta["years"]]
BENCH, PHONES, LAST = t.bench_start, t.phones_start, t.reaction
FPS = 15
SCALE = 2.2
FLOOR = 2000.0  # below the frame: a medium, the heads where the bench's will be
PIP_AT, JUNO_AT = (262.0, FLOOR), (818.0, FLOOR)
PIP_SEAT, JUNO_SEAT = (178.0, BENCH_SEAT), (902.0, BENCH_SEAT)
APART = 70.0  # on the bench their hands meet: each phone sits this far toward its owner
BOUNCE = 0.3

ROWS = [(0.0, 0), *zip(YEARS, (1, 2, 3, 3, 4), strict=True)]
LABELS = ("2028", "2031", "2039", "2052", "2067")

ticks = [*YEARS, BENCH]
foley.write_whoosh(ROOT / "assets" / "flip.wav", ticks, DURATION, length=0.22, seed=40603)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("flip", "assets/flip.wav", {"role": "effects", "gain": -14}),
    ]
)


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def spans(role: str) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role]


juno = blob.speaking(
    [
        cue(0, "clasp", JUNO_AT, eyes="happy", mouth="grin"),
        cue(0.30, "clasp", JUNO_AT, ease=0.28, lift=36, eyes="happy", mouth="grin"),
        cue(0.62, "clasp", JUNO_AT, ease=0.28, lift=24, eyes="happy", mouth="grin"),
        cue(P[1].start + 0.1, "clasp", JUNO_AT, eyes="look", mouth="smile"),
        cue(P[2].start, "clasp", JUNO_AT, ease=0.12, eyes="squint", mouth="small"),
        cue(YEARS[0], "clasp", JUNO_AT, eyes="squint", mouth="flat"),
        cue(P[4].start, "clasp", JUNO_AT, ease=0.12, eyes="look", mouth="small"),
        cue(YEARS[2], "clasp", JUNO_AT, eyes="squint", mouth="flat"),
        cue(P[6].start, "clasp", JUNO_AT, ease=0.12, eyes="look", mouth="flat"),
        cue(YEARS[4], "clasp", JUNO_AT, eyes="closed", mouth="flat"),
        cue(BENCH, "lounge", JUNO_SEAT, eyes="happy", mouth="smile"),
        cue(P[9].start, "lounge", JUNO_SEAT, eyes="happy", mouth="grin", turn=2),
        cue(PHONES - 0.9, "sit", JUNO_SEAT, ease=0.5, eyes="open", mouth="flat"),
    ],
    spans("juno"),
    DURATION,
    FPS,
)
pip = blob.speaking(
    [
        cue(0, "clasp", PIP_AT, eyes="look", mouth="smile", flip=True),
        cue(P[1].start, "clasp", PIP_AT, ease=0.1, lift=26, eyes="happy", mouth="grin", flip=True),
        cue(P[2].start, "clasp", PIP_AT, ease=0.12, eyes="look", mouth="small", flip=True),
        cue(YEARS[0], "clasp", PIP_AT, eyes="look", mouth="flat", flip=True),
        cue(P[4].start, "clasp", PIP_AT, ease=0.12, eyes="squint", mouth="small", flip=True),
        cue(YEARS[2], "clasp", PIP_AT, eyes="look", mouth="flat", flip=True),
        cue(P[6].start, "clasp", PIP_AT, ease=0.12, eyes="squint", mouth="flat", flip=True),
        cue(YEARS[4], "clasp", PIP_AT, eyes="closed", mouth="flat", flip=True),
        cue(BENCH, "lounge", PIP_SEAT, eyes="happy", mouth="smile", flip=True),
        cue(P[9].start, "lounge", PIP_SEAT, eyes="happy", mouth="smile", flip=True),
        cue(PHONES - 0.9, "sit", PIP_SEAT, ease=0.5, eyes="open", mouth="flat", flip=True),
        cue(P[10].end, "sit", PIP_SEAT, eyes="look", mouth="smile", flip=True),
    ],
    spans("pip"),
    DURATION,
    FPS,
)
DOWN = (0.0, BENCH)  # phones in the hands while they stand
OUT = (PHONES - 0.75, DURATION)  # and out again on the bench


def world(g):
    blob.pip(cv, g, pip, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False)
    blob.juno(cv, g, juno, end=DURATION, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=False)
    for name, cues in (("pip", pip), ("juno", juno)):
        hands = blob.held(cv, g, cues, end=DURATION, scale=SCALE, fps=FPS, id=f"{name}-hands")
        cv.gate(hands, [DOWN, OUT])
        side = cv.group(hands, f"{name}-held")
        cv.keys(side, "x", [(0.0, 0.0), (BENCH, -APART if name == "pip" else APART)])
        soft_props.phone(cv, side, scale=0.85, id=f"{name}-phone")
    canes = cv.group(g, "canes")
    cv.gate(canes, [(BENCH, DURATION)])
    soft_props.cane(cv, canes, 30, 1900, height=600, lean=2, id="pip-cane")
    soft_props.cane(cv, canes, 1050, 1900, height=600, lean=-2, flip=True, id="juno-cane")


graded = soft_sets.finish(cv, ep.comp)
soft_sets.park(cv, graded, growth=ROWS, seated=[(BENCH, DURATION)], cast=world)

ends = [*YEARS[1:], BENCH]
card = soft_props.time_card(
    cv,
    ep.comp,
    [
        *(TimeState(label, a, b) for label, a, b in zip(LABELS, YEARS, ends, strict=True)),
        TimeState("2079", BENCH, LAST),
    ],
    (380, 452, 320, 118),
)

insert = cv.group(ep.comp, "phones-insert")
cv.gate(insert, [(LAST, DURATION)])
cv.rect(insert, 0, 0, 1080, 1920, "#2E3A33", opacity=0.72)
for name, x, stamp in (("left", 270, ""), ("right", 730, "AWAY")):
    soft_props.phone(
        cv,
        insert,
        x=x,
        y=860,
        scale=2.3,
        screen=lambda g, stamp=stamp, name=name: soft_props.month_view(
            cv, g, "MARCH", "2080", stamp=stamp, id=f"month-{name}"
        ),
        id=f"insert-phone-{name}",
    )

CUTS = [*YEARS, BENCH, LAST]
specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else LAST
    cut = min(c for c in CUTS if c > p.start)  # a line's caption leaves with its shot
    specs.append((max(0.0, p.start - 0.05), min(until, cut, p.end + 0.7), p.caption, f"caption-{i + 1}"))
ep.captions(specs, **soft_sets.CAPTIONS)
ep.markers(extra=[("marker-bench", BENCH, "The bench"), ("marker-phones", LAST, "The phones")])
ep.instagram(POSTS["hang-out"])
out = ep.finish()
ep.check_overlays(out, ["soft-time-card"])

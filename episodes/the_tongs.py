#!/usr/bin/env python3
"""The Tongs, built with srstudio: a family barbecue, played as a Western.

    srstudio record the-tongs PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build the-tongs PROJECT    # → PROJECT/the-tongs.scene.xml

Bo clicks his tongs at the lens: nobody touches the grill. He goes for the sauce, and Pip turns one burger. Bo comes
back, the birds stop, and the two of them face off across the grill with their tongs at the hip. Bo draws a second pair.
They circle while the lunch burns, and Juno walks in between them with a pizza. Both tongs droop, and Bo's come down,
gently, on the lid. Nobody touches the pizza.

The first frame already moves (arm B of the ``sp-hook_motion`` test): the tongs are clicking and the grill is smoking.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, camera, foley, layout, soft_odds, soft_props, soft_sets
from the_tongs_audio import INTERVIEW

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="the-tongs",
        title=INTERVIEW.title,
        description="Family comedy: at a barbecue one man holds the tongs, and when his brother turns a burger the "
        "lawn becomes a Western. Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        seed=INTERVIEW.seed,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions stay inside x 80–920
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
GONE, EYES, STANDOFF, LOW, WIDE = t.gone_start, t.eyes_start, t.standoff_start, t.low_start, t.wide_start
DROOP, ON_BO, LAST = t.droop_start, t.bo_start, t.reaction_start
FPS = 15
SCALE = 1.05
FLOOR = 1560.0
BO_AT, PIP_AT = (305.0, FLOOR), (770.0, FLOOR)
GRILL_AT = (545.0, FLOOR + 10)
BENCH_X, BENCH_Y = 975.0, 1236.0
JUNO_SCALE = 0.6
OFF_LEFT = (-260.0, FLOOR)
BOX_AT = (545.0, 1640.0)  # where Juno stops, in front of the grill
BO_MID, PIP_MID = (545.0, 1740.0), (545.0, 1420.0)  # Bo round the front of the grill, Pip round the back
BO_END, PIP_END, PIP_NEAR = (900.0, 1640.0), (170.0, 1640.0), (295.0, 1640.0)  # they have swapped sides
FROM_GATE = (-260.0, 1640.0)
LOW_SCALE, LOW_AT = 3.0, (540.0, 2350.0)
TONGS = 0.68
LOW_TONGS = 0.42 * LOW_SCALE

click_at = [0.05, 0.25, P[0].end + 0.05]  # at the lens, and once more as he leaves
SNAP2 = [STANDOFF + 0.18, STANDOFF + 0.4]
DRAWN = LOW + 1.25  # the second pair is out
DRAW3 = [DRAWN + 0.1, DRAWN + 0.3, DRAWN + 0.5]
LAST2 = [LAST + 0.05, LAST + 0.27]
TURN = P[1].start - 0.45  # Pip turns the burger
REACH = TURN - 0.6  # he reaches for the spare pair
CHAR = WIDE + 0.2

BIRDS = sorted(0.2 + 0.31 * n + (0.11 if n % 3 == 1 else 0.0) for n in range(int((EYES - 0.5) / 0.31)))
SIZZLE = [n * 3.9 for n in range(int(DURATION / 3.9) + 1)]
foley.write_bursts(ROOT / "assets" / "clack.wav", [*click_at, *SNAP2, *DRAW3, *LAST2], DURATION, foley.CLACK, seed=3121)
foley.write_bursts(ROOT / "assets" / "birds.wav", BIRDS, DURATION, foley.BIRD, seed=3122)
foley.write_bursts(ROOT / "assets" / "sizzle.wav", SIZZLE, DURATION, foley.SIZZLE, seed=3123)
foley.write_bursts(ROOT / "assets" / "flip.wav", [TURN], DURATION, foley.FLAP, seed=3124)
foley.write_bursts(ROOT / "assets" / "door.wav", [WIDE + 0.75], DURATION, foley.THUD, seed=3125)
foley.write_bursts(ROOT / "assets" / "dog.wav", [WIDE + 1.15, WIDE + 1.42], DURATION, foley.BARK, seed=3126)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("clack", "assets/clack.wav", {"role": "effects", "gain": -7}),
        ("birds", "assets/birds.wav", {"role": "ambience", "gain": -20}),
        ("sizzle", "assets/sizzle.wav", {"role": "ambience", "gain": -20}),
        ("flip", "assets/flip.wav", {"role": "effects", "gain": -10}),
        ("door", "assets/door.wav", {"role": "effects", "gain": -18}),
        ("dog", "assets/dog.wav", {"role": "effects", "gain": -24}),
    ]
)


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def spans(role: str, a: float = 0.0, b: float = DURATION) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role and a <= p.start < b]


def quiet(cues, lines):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for start, stop in lines:
        for edge in (start, stop):
            held = [c for c in cues if c.time <= edge][-1]
            if held.time != edge:
                later.append(replace(held, time=edge, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, DURATION, FPS)


def walking(points, start, stop, *, step=0.2, flip=False, **kw):
    """Cues that walk along ``points`` between ``start`` and ``stop``, a stride every ``step`` seconds."""
    n = max(2, int((stop - start) / step))
    legs = len(points) - 1
    out = []
    for k in range(1, n + 1):
        u = k / n * legs
        leg = min(int(u), legs - 1)
        a, b, v = points[leg], points[leg + 1], u - leg
        spot = (a[0] + (b[0] - a[0]) * v, a[1] + (b[1] - a[1]) * v)
        out.append(
            cue(start + (stop - start) * k / n, "walk-a" if k % 2 else "walk-b", spot, flip=flip, ease=step, **kw)
        )
    return out


SWING = WIDE + 0.05  # the circling starts on the cut
SWUNG = DROOP - 0.1
bo = quiet(
    [
        cue(0, "step", BO_AT, eyes="squint", mouth="flat"),
        *walking((BO_AT, OFF_LEFT), GONE + 0.15, GONE + 0.95, eyes="look", mouth="flat"),
        cue(EYES, "stand", BO_AT, flip=True, eyes="open", mouth="flat"),
        cue(STANDOFF, "stand", BO_AT, flip=True, eyes="squint", mouth="flat"),
        *walking((BO_AT, BO_MID, BO_END), SWING + 0.1, SWUNG, step=0.28, flip=True, eyes="squint", mouth="flat"),
        cue(SWUNG + 0.1, "stand", BO_END, flip=True, eyes="squint", mouth="flat"),
        cue(ON_BO + 0.3, "step", BO_END, flip=True, ease=0.6, eyes="squint", mouth="flat"),
    ],
    spans("bo"),
)
pip = quiet(
    [
        cue(0, "stand", PIP_AT, eyes="look", mouth="flat"),
        cue(GONE + 0.15, "stand", PIP_AT, flip=True, eyes="look", mouth="flat"),
        cue(GONE + 0.5, "stand", PIP_AT, eyes="look", mouth="flat"),
        cue(REACH + 0.25, "lean", PIP_AT, flip=True, ease=0.2, eyes="wide", mouth="flat"),
        cue(TURN - 0.05, "step", PIP_AT, flip=True, ease=0.2, eyes="wide", mouth="small"),
        cue(P[1].start, "step", PIP_AT, flip=True, eyes="wide", mouth="o"),
        cue(STANDOFF, "stand", PIP_AT, eyes="look", mouth="flat"),
        *walking((PIP_AT, PIP_MID, PIP_END), SWING + 0.1, SWUNG, step=0.28, eyes="squint", mouth="flat"),
        cue(SWUNG + 0.1, "stand", PIP_END, flip=True, eyes="look", mouth="flat"),
        cue(ON_BO, "lean", PIP_NEAR, ease=0.5, eyes="wide", mouth="small"),
    ],
    spans("pip"),
)
juno_bench = quiet([cue(0, "nod", (0.0, 0.0), eyes="look", mouth="flat")], spans("juno", 0.0, WIDE))
juno_box = quiet(
    [
        cue(0, "clasp", FROM_GATE, flip=True, eyes="look", mouth="flat"),
        *walking((FROM_GATE, BOX_AT), WIDE + 0.9, P[7].start - 0.1, step=0.22, flip=True, eyes="look", mouth="flat"),
        cue(P[7].start, "clasp", BOX_AT, eyes="look", mouth="smile"),
    ],
    spans("juno", WIDE),
)
bo_low = quiet(
    [
        cue(0, "stand", LOW_AT, eyes="squint", mouth="flat"),
        cue(LOW + 1.0, "lean", LOW_AT, ease=0.95, eyes="squint", mouth="flat"),
        cue(DRAWN, "cheer-b", LOW_AT, ease=0.2, overshoot=0.08, eyes="squint", mouth="flat"),
    ],
    [],
)


def low_cue_scale(c):
    return replace(c, x=c.x * SCALE / LOW_SCALE, y=c.y * SCALE / LOW_SCALE)


bo_low = [low_cue_scale(c) for c in bo_low]


def tongs_for(g, cues, side, id, angles, clicks=(), scale=SCALE, shown=None, size=TONGS):
    """Tongs in one hand, turned as ``angles`` say, in view through ``shown``."""
    hand = soft_odds.in_hand(cv, g, cues, side, end=DURATION, scale=scale, fps=FPS, id=id)
    cv.keys(hand, "rotation", angles)
    if shown is not None:
        cv.gate(hand, shown)
    soft_odds.tongs(cv, hand, scale=size, clicks=clicks, id=f"{id}-tongs")
    return hand


def behind_the_grill(g):
    bench = cv.group(g, "back-bench", x=BENCH_X, y=BENCH_Y, scaleX=0.36, scaleY=0.36)
    soft_props.bench(cv, bench, 0, 0)
    gone = cv.group(g, "juno-sat", x=BENCH_X + 30, y=BENCH_Y - 48)
    cv.gate(gone, [(0.0, WIDE)])
    blob.juno(
        cv, gone, juno_bench, end=DURATION, scale=JUNO_SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=False
    )
    hands = blob.held(cv, gone, juno_bench, end=DURATION, scale=JUNO_SCALE, fps=FPS, id="juno-phone")
    soft_props.phone(cv, hands, scale=0.3, id="bench-phone")


def on_the_lawn(g):
    behind_the_grill(g)
    blob.pip(cv, g, pip, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False)
    soft_odds.smoke(cv, g, GRILL_AT[0], GRILL_AT[1] - 340, ((0.0, 2), (GONE, 3)), end=DURATION, id="grill-smoke")
    soft_odds.grill(
        cv,
        g,
        *GRILL_AT,
        end=DURATION,
        char=CHAR,
        flip=TURN,
        flames=((0.0, 0), (STANDOFF, 1), (WIDE, 2), (WIDE + 1.0, 3)),
    )
    spare = cv.group(g, "spare-tongs")
    cv.gate(spare, [(0.0, REACH + 0.25)])
    soft_odds.tongs(cv, spare, GRILL_AT[0] + 140, GRILL_AT[1] - 306, scale=0.62, angle=90, id="spare")
    tongs_for(
        g,
        pip,
        "left",
        "pip-hand",
        [(0.0, -40.0), (TURN - 0.05, -140.0), (STANDOFF, -150.0), (DROOP, -175.0)],
        clicks=SNAP2,
        shown=[(REACH + 0.25, DURATION)],
    )
    blob.bo(cv, g, bo, end=DURATION, scale=SCALE, mouth_states=ep.mouth("bo"), fps=FPS, shadow=False)
    tongs_for(g, bo, "right", "bo-hand", [(0.0, 25.0), (EYES, 150.0), (DROOP, 175.0)], clicks=[*click_at, *SNAP2])
    sauce = soft_odds.in_hand(cv, g, bo, "left", end=DURATION, scale=SCALE, fps=FPS, id="bo-sauce-hand")
    cv.gate(sauce, [(EYES, STANDOFF)])
    soft_odds.bottle(cv, sauce, 0, -30, scale=0.7)
    walk_in = cv.group(g, "juno-in")
    cv.gate(walk_in, [(WIDE, DURATION)])
    blob.juno(
        cv,
        walk_in,
        juno_box,
        end=DURATION,
        scale=SCALE,
        mouth_states=ep.mouth("juno"),
        fps=FPS,
        shadow=False,
        id="juno-box",
    )
    box = blob.held(cv, walk_in, juno_box, end=DURATION, scale=SCALE, fps=FPS, id="juno-box-hands")
    soft_odds.pizza_box(cv, box, 0, 0, scale=0.82)
    tongs_for(
        g,
        bo,
        "left",
        "bo-second",
        [(0.0, -150.0), (DROOP, -175.0), (ON_BO + 0.3, -125.0)],
        clicks=LAST2,
        shown=[(WIDE, DURATION)],
    )


graded = soft_sets.finish(cv, ep.comp)
world = cv.group(graded, "lawn")
soft_sets.park(cv, world, growth=((0.0, 1),), cast=on_the_lawn)


def frame(scale: float, x: float, y: float) -> tuple[float, float, float]:
    return scale, 540 - x * scale, 960 - y * scale


FAMILY = frame(1.25, 595.0, 1150.0)
camera.reframe(
    cv,
    world,
    [
        (0.0, *FAMILY),
        (EYES, *frame(6.2, BO_AT[0], FLOOR - 478)),
        (STANDOFF, *FAMILY),
        (P[3].start, *frame(2.5, PIP_AT[0], FLOOR - 400)),
        (P[4].start, *frame(2.5, BO_AT[0] + 40, FLOOR - 400)),
        (P[5].start, *frame(2.5, PIP_AT[0], FLOOR - 400)),
        (WIDE, 1.0, 0.0, 0.0),
        (ON_BO, *frame(1.3, 590.0, 1270.0)),
    ],
)

low_shot = cv.group(graded, "low-angle")
cv.gate(low_shot, [(LOW, WIDE)])
sky = cv.grad("low-sky", [(0.0, "#8FC3E4"), (1.0, "#DCEBEF")], (0, 0, 0, 1))
cv.rect(low_shot, 0, 0, 1080, 1920, sky)
soft_odds.smoke(cv, low_shot, 860, 1920, ((0.0, 3),), end=DURATION, scale=1.6, id="low-smoke")
tilted = cv.group(low_shot, "low-tilt", x=540, y=1500, rotation=-4)
towering = cv.group(tilted, "low-bo", x=-540, y=-1500)
blob.bo(cv, towering, bo_low, end=DURATION, scale=LOW_SCALE, mouth_states=ep.mouth("bo"), fps=FPS, id="bo-low")
tongs_for(
    towering,
    bo_low,
    "right",
    "low-right",
    [(0.0, 150.0), (DRAWN, -18.0)],
    clicks=DRAW3,
    scale=LOW_SCALE,
    size=LOW_TONGS,
)
tongs_for(
    towering,
    bo_low,
    "left",
    "low-left",
    [(0.0, 18.0)],
    clicks=DRAW3,
    scale=LOW_SCALE,
    size=LOW_TONGS,
    shown=[(DRAWN - 0.1, DURATION)],
)

specs = []
CUTS = sorted({EYES, STANDOFF, LOW, WIDE, ON_BO, DURATION})
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    cut = min(c for c in CUTS if c > p.start)
    end = DURATION if i + 1 == len(P) else min(until, cut, p.end + 0.6)
    specs.append((max(0.0, p.start - 0.05), end, p.caption, f"caption-{i + 1}"))
ep.captions(specs, **soft_sets.CAPTIONS)
ep.markers(extra=[("marker-eyes", EYES, "The eyes"), ("marker-wide", WIDE, "The wide")])
ep.instagram(POSTS["the-tongs"])
out = ep.finish()
ep.check_overlays(out, [])

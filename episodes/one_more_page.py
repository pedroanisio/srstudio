#!/usr/bin/env python3
"""One More Page, built with srstudio: a bedtime negotiated with a four-year-old in a tie.

    srstudio record one-more-page PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build one-more-page PROJECT    # → PROJECT/one-more-page.scene.xml

Pip sits up in bed in a necktie, a case open on the quilt, and Bo sits on the edge of it. "One story. Then lights out."
"Two stories, water, hall light." "You're four." "And you're tired." Bo looks at the clock and gives up one point. They
shake on it. At 9:40 Bo is lying down reading, and stops in the middle of a sentence. The book slides off. He snores.
Pip waves a hand at him, loosens the tie, pulls the quilt up, turns off the lamp. "Pleasure doing business." The door
shuts behind the case. Somewhere, a fridge opens.

The first frame holds still (arm A of the ``sp-hook_motion`` test): nothing moves before the first word, and the tie and
the case are already there.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from one_more_page_audio import INTERVIEW
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, layout, soft_bedtime, soft_props, soft_sets
from srstudio.soft_bedtime import BookSlide
from srstudio.soft_props import TimeState
from srstudio.soft_sets import Light, Shot

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="one-more-page",
        title=INTERVIEW.title,
        description="Family comedy: a four-year-old in a necktie negotiates his bedtime with a tired father and wins. "
        "Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        seed=31241,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions and the hour card stay inside x 80–920
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
CLOCK, SHAKE, CARD, BOOK, SNORE = (float(t.meta[k]) for k in ("clock", "shake", "card", "book", "snore"))
WAVE, TIE, QUILT, CLICK = (float(t.meta[k]) for k in ("wave", "tie", "quilt", "click"))
WALK, DOOR, FRIDGE = (float(t.meta[k]) for k in ("walk", "door", "fridge"))
FPS = 15
PIP_SCALE, BO_SCALE, OUT_SCALE = 1.85, 2.45, 1.5
PIP_BED, PIP_LEAN = (690.0, 1980.0), (560.0, 1960.0)
BO_EDGE = (370.0, 2040.0)  # sitting on the edge of the bed, in front of the quilt
BO_UP, BO_LOWER, BO_DOWN = (300.0, 2350.0), (300.0, 2400.0), (290.0, 2450.0)  # he goes down the headboard as he reads
LAMP_X = 975.0
LAMP_AT = (LAMP_X, 1480.0)
CASE_AT = (760.0, 1610.0)
FLOOR = 1880.0
HALL = (-300.0, 1300.0)  # the door is off the left of the frame and the hall light comes through it
CLOSES = (-760.0, 1300.0)  # the same light as the door swings to
STEP = 0.18

snores = [SNORE + 1.3 * n for n in range(8) if SNORE + 1.3 * n < FRIDGE - 0.3]
steps = [WALK + STEP * n for n in range(1, 6)]
foley.write_bursts(ROOT / "assets" / "snore.wav", snores, DURATION, foley.SNORE, seed=31242)
foley.write_bursts(ROOT / "assets" / "book.wav", [BOOK + 0.62], DURATION, foley.THUD, seed=31243)
foley.write_bursts(ROOT / "assets" / "click.wav", [CLICK], DURATION, foley.REMOTE_CLICK, seed=31244)
foley.write_bursts(ROOT / "assets" / "steps.wav", steps, DURATION, foley.KNOCK, seed=31245)
foley.write_bursts(ROOT / "assets" / "door.wav", [DOOR], DURATION, foley.THUD, seed=31246)
foley.write_bursts(ROOT / "assets" / "shut.wav", [TIE + 0.72], DURATION, foley.KNOCK, seed=31250)
foley.write_bursts(ROOT / "assets" / "shake.wav", [SHAKE + 0.33, SHAKE + 0.66], DURATION, foley.KNOCK, seed=31247)
FRIDGE_SEAL = foley.Burst(0.18, 700.0, attack=0.004, decay=0.4, tone_hz=210.0, tone_end_hz=120.0, tone=0.3)
FRIDGE_HUM = foley.Burst(1.0, 240.0, attack=0.06, decay=2.0, tone_hz=118.0, tone_end_hz=118.0, tone=0.5)
foley.write_bursts(ROOT / "assets" / "seal.wav", [FRIDGE], DURATION, FRIDGE_SEAL, seed=31248)
foley.write_bursts(ROOT / "assets" / "hum.wav", [FRIDGE + 0.05], DURATION, FRIDGE_HUM, seed=31249)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("snore", "assets/snore.wav", {"role": "effects", "gain": -8}),
        ("book", "assets/book.wav", {"role": "effects", "gain": -10}),
        ("click", "assets/click.wav", {"role": "effects", "gain": -4}),
        ("steps", "assets/steps.wav", {"role": "effects", "gain": -16}),
        ("door", "assets/door.wav", {"role": "effects", "gain": -7}),
        ("shut", "assets/shut.wav", {"role": "effects", "gain": -10}),
        ("shake", "assets/shake.wav", {"role": "effects", "gain": -14}),
        ("seal", "assets/seal.wav", {"role": "effects", "gain": -9}),
        ("hum", "assets/hum.wav", {"role": "effects", "gain": -14}),
    ],
    loudness="-14",
)


def spans(role: str, start: float = 0.0, end: float = DURATION) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role and start <= p.start < end]


def small(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=PIP_SCALE, **kw)


def big(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=BO_SCALE, **kw)


def out(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=OUT_SCALE, **kw)


def quiet(cues, lines, end):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for _, stop in lines:
        held = [c for c in cues if c.time <= stop][-1]
        if held.time != stop:
            later.append(replace(held, time=stop, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, end, FPS)


pip_bed = quiet(
    [
        small(0, "clasp", PIP_BED, eyes="look", mouth="flat", flip=True),
        small(P[3].end, "clasp", PIP_BED, eyes="squint", mouth="smile", flip=True),
        small(CARD, "clasp", PIP_BED, eyes="open", mouth="flat", flip=True),  # 9:40, and wide awake
        small(BOOK, "clasp", PIP_BED, eyes="look", mouth="flat", flip=True),
        small(WAVE, "wave-a", PIP_LEAN, ease=0.3, eyes="open", mouth="flat", flip=True),
        small(WAVE + 0.2, "wave-b", PIP_LEAN, eyes="open", mouth="flat", flip=True),
        small(WAVE + 0.4, "wave-a", PIP_LEAN, eyes="open", mouth="flat", flip=True),
        small(WAVE + 0.6, "wave-b", PIP_LEAN, eyes="open", mouth="flat", flip=True),
        small(TIE - 0.15, "clasp", PIP_BED, ease=0.3, eyes="happy", mouth="smile", flip=True),
        small(QUILT, "clasp", PIP_LEAN, ease=0.3, eyes="look", mouth="smile", flip=True),
        small(CLICK - 0.35, "wave-a", PIP_BED, ease=0.3, eyes="look", mouth="smile"),
    ],
    spans("pip", 0.0, CLICK),
    CLICK,
)
bo_edge = quiet(
    [
        big(0, "sit", BO_EDGE, eyes="look", mouth="smile"),
        big(P[2].end, "sit", BO_EDGE, eyes="open", mouth="flat"),
        big(P[3].end, "sit", BO_EDGE, eyes="squint", mouth="flat"),
        big(CLOCK, "sit", BO_EDGE, eyes="wide", mouth="flat", turn=-6),
        big(P[4].start, "sit", BO_EDGE, eyes="closed", mouth="flat"),
        big(P[4].end, "sit", BO_EDGE, eyes="squint", mouth="flat"),
    ],
    spans("bo", 0.0, CARD),
    CARD,
)
bo_bed = blob.speaking(
    [
        big(0, "clasp", BO_UP, eyes="look", mouth="flat"),
        big(CARD, "clasp", BO_UP, eyes="look", mouth="flat"),
        big(P[6].start + 0.8, "clasp", BO_LOWER, ease=0.5, eyes="squint", mouth="flat", turn=-5),
        big(P[6].end, "clasp", BO_DOWN, ease=0.6, eyes="closed", mouth="flat", turn=-11),
        *(
            big(at, "clasp", BO_DOWN, eyes="closed", mouth=shape, turn=-11)
            for snore in snores
            for at, shape in ((snore, "o"), (snore + 0.8, "flat"))
        ),
    ],
    spans("bo", CARD),
    DURATION,
    FPS,
)
left = -240.0
strides = int((DOOR - 0.35 - WALK) / STEP)
pip_out = quiet(
    [
        out(0, "stand", (620.0, FLOOR), eyes="look", mouth="smile", flip=True),
        out(WALK - 0.2, "stand", (620.0, FLOOR), eyes="happy", mouth="smile", flip=True),
        *(
            out(
                WALK + STEP * n,
                "walk-a" if n % 2 == 0 else "walk-b",
                (620.0 + (left - 620.0) * n / strides, FLOOR),
                ease=STEP,
                eyes="happy",
                mouth="smile",
                flip=True,
            )
            for n in range(1, strides + 1)
        ),
    ],
    spans("pip", CLICK),
    DOOR,
)


def cast(g):
    soft_bedtime.wall_clock(cv, g, 250, 590, time="8:40", scale=0.9)
    bed = cv.group(g, "in-bed")
    cv.gate(bed, [(CARD, DURATION)])
    blob.bo(cv, bed, bo_bed, end=DURATION, scale=BO_SCALE, mouth_states=ep.mouth("bo"), fps=FPS, shadow=False)
    up = cv.group(g, "pip-up")
    cv.gate(up, [(0.0, CLICK)])
    blob.pip(cv, up, pip_bed, end=CLICK, scale=PIP_SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False)
    tie = soft_props.necktie(cv, up, PIP_BED[0], 1404, scale=0.72)
    x, y = PIP_BED[0], 1404.0
    lean = PIP_LEAN[0]
    cv.keys(
        tie,
        "x",
        [
            (0, x),
            (WAVE - 0.3, x),
            (WAVE, lean),
            (TIE - 0.45, lean),
            (TIE - 0.15, x),
            (TIE + 0.40, x),
            (TIE + 0.70, CASE_AT[0]),
        ],
        hold=False,
    )
    cv.keys(
        tie,
        "y",
        [(0, y), (TIE, y), (TIE + 0.15, y + 16), (TIE + 0.40, y + 16), (TIE + 0.55, y - 60), (TIE + 0.70, 1600)],
        hold=False,
    )
    cv.keys(tie, "rotation", [(0, 0), (TIE, 0), (TIE + 0.15, 16), (TIE + 0.40, 16), (TIE + 0.70, 120)], hold=False)
    cv.gate(tie, [(0.0, TIE + 0.72)])


def held(g):
    edge = cv.group(g, "on-the-edge")
    cv.gate(edge, [(0.0, CARD)])
    blob.bo(
        cv, edge, bo_edge, end=CARD, scale=BO_SCALE, mouth_states=ep.mouth("bo"), fps=FPS, shadow=False, id="bo-edge"
    )
    on_the_quilt = cv.group(g, "on-the-quilt")
    cv.gate(on_the_quilt, [(0.0, CLICK)])
    soft_bedtime.open_briefcase(cv, on_the_quilt, *CASE_AT, shut=TIE + 0.72, scale=0.95)  # shut on the tie
    reading = cv.group(g, "reading")
    cv.gate(reading, [(CARD, DURATION)])
    soft_bedtime.picture_book(cv, reading, 300, 1500, slide=BookSlide(BOOK, 0.6, 90.0, 240.0, 22.0), scale=1.05)
    pull = cv.group(g, "pulled")
    cv.gate(pull, [(QUILT, DURATION)])
    soft_bedtime.quilt_pull(cv, pull, -40, 1560, 1450, QUILT, 0.45, width=640)
    soft_bedtime.bedside_lamp(cv, g, LAMP_X, 1672, off=CLICK, scale=0.85)
    leaving = cv.group(g, "leaving")
    cv.gate(leaving, [(CLICK, DOOR)])
    blob.pip(
        cv,
        leaving,
        pip_out,
        end=DOOR,
        scale=OUT_SCALE,
        mouth_states=ep.mouth("pip"),
        fps=FPS,
        shadow=False,
        id="pip-out",
    )
    case = soft_props.briefcase(cv, leaving, 640, 1560, scale=0.8)
    cv.keys(case, "x", [(0, 720), (WALK, 720), (DOOR - 0.35, left + 100)], hold=False)


PIP_CLOSE = Shot(0.0, 1.5, 680.0, 1160.0)
BO_CLOSE = Shot(0.0, 1.45, 330.0, 1200.0)
shots = [
    Shot(0.0),
    PIP_CLOSE._replace(time=P[1].start - 0.05),
    BO_CLOSE._replace(time=P[2].start - 0.05),
    Shot(P[3].start - 0.05, 1.9, 690.0, 1180.0),
    Shot(CLOCK, 2.4, 250.0, 620.0),
    BO_CLOSE._replace(time=P[4].start - 0.05),
    PIP_CLOSE._replace(time=P[5].start - 0.05),
    Shot(CARD),
    Shot(BOOK + 0.8, 1.35, 420.0, 1240.0),
    Shot(WAVE - 0.3),
]
lights = [
    Light(0.0, "lamp", *LAMP_AT),
    Light(CLICK, "lamp", *HALL),
    Light(DOOR - 0.25, "lamp", *CLOSES),
    Light(DOOR, "dark"),
]

graded = soft_sets.finish(cv, ep.comp)
soft_sets.bedroom(cv, graded, lights=lights, shots=shots, cast=cast, held=held)
soft_bedtime.handshake(cv, graded, SHAKE, CARD, pumps=2)
soft_props.time_card(cv, ep.comp, [TimeState("9:40", CARD, BOOK)], (380, 452, 320, 118))

CUTS = [P[1].start, P[2].start, P[3].start, CLOCK, P[4].start, P[5].start, SHAKE, CARD, CLICK]
speech = {"pip": [], "bo": []}
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    after = [c for c in CUTS if c > p.start + 0.1]
    cut = min(after) if after else DURATION
    end = max(p.end, min(until, cut, p.end + 0.45))
    speech[p.role].append((max(0.0, p.start - 0.05), end, p.caption, f"caption-{i + 1}"))
spoken = [
    *ep.captions(speech["pip"], **{**soft_sets.CAPTIONS, "color": "#2F5D8C"}),
    *ep.captions(speech["bo"], **soft_sets.CAPTIONS),
]
ep.captions(
    [(FRIDGE - 0.05, DURATION, "(a fridge door opens)", "caption-fridge")],
    **{**soft_sets.CAPTIONS, "y": 860, "color": "#FFFFFF", "stroke": "#1A1714"},
)
ep.markers(
    extra=[("marker-deal", SHAKE, "The deal"), ("marker-asleep", SNORE, "Asleep"), ("marker-door", DOOR, "The door")]
)
ep.hide_on_cover(*spoken)
ep.instagram(POSTS["one-more-page"])
ep.finish()

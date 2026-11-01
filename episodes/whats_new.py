#!/usr/bin/env python3
"""What's New, built with srstudio: every app update moves the one thing you use and calls it an improvement.

    srstudio record whats-new PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build whats-new PROJECT    # → PROJECT/whats-new.scene.xml

Juno sits down with her coffee where the sofa was. A cheerful man has improved the living room: version nine, the sofa
is in the hall, to bring you closer to the hall. The light switch is under Settings, which is in the fridge. Press and
hold. Nothing, and then the lamp behind Pip. It cannot be put back, and how is he doing? One star, hard. Next morning
Juno walks to the sofa's new place, sure of herself, and sits on the floor. Good morning!

The first frame already moves: Juno is on her way down, and the thump lands before her first word.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from srstudio import (
    SOFT,
    Episode,
    EpisodeSpec,
    blob,
    foley,
    layout,
    look,
    soft_bedtime,
    soft_front,
    soft_odds,
    soft_sets,
)
from srstudio.soft_sets import Shot
from whats_new_audio import INTERVIEW

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "whats-new"
ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug=SLUG,
        title=INTERVIEW.title,
        description="Everyday-tech comedy: a software update is a man in your house, and he has moved the sofa. Native "
        "vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        seed=INTERVIEW.seed,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions stay inside x 80–920
        bleed=True,  # the window and the hall are out of focus
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
DARK, PRESS, LAMP, JAB, NEXT, PEEK = t.dark_start, t.press_start, t.lamp_start, t.jab_start, t.next_start, t.peek_start
FPS = 15
SCALE = 1.25
FLOOR = 1590.0
THUMP = 0.33
TAP = JAB + 0.62  # the finger lands
SAT = PEEK - 1.3  # the second thump
JUNO_HIGH, JUNO_DOWN = (770.0, 1500.0), (770.0, 1650.0)
BO_AT, BO_FRIDGE, BO_NOD, BO_CARD = (440.0, FLOOR), (250.0, FLOOR), (640.0, FLOOR), (900.0, FLOOR)
PIP_AT, PIP_WALL, PIP_PRESS, PIP_OFF = (165.0, 1560.0), (470.0, 1560.0), (400.0, 1560.0), (150.0, 1560.0)
SWITCH_AT = (665.0, 1010.0)
FRIDGE_AT, LAMP_AT, SHELF_Y = (170.0, 1300.0), (640.0, 850.0), 850.0
DOOR_SEAT = (930.0, 1570.0)
PEEK_FROM, PEEK_TO = (520.0, 1290.0), (690.0, 1290.0)
HALL_SCALE = 0.95
CLICKS = [DARK + 0.22, DARK + 0.5, DARK + 0.74]
STEPS = [NEXT + 0.2 + 0.28 * k for k in range(6)]
HUM_LAST = LAMP + 1.2


def bed(sound: foley.Burst, first: float, last: float) -> list[float]:
    """Cues that lay a looping ``sound`` end to end from ``first`` so that it stops at ``last``."""
    gap = sound.seconds * 0.9
    return [first + n * gap for n in range(int((last - first - sound.seconds) / gap) + 1)] + [last - sound.seconds]


foley.write_bursts(ROOT / "assets" / "thump.wav", [THUMP, SAT], DURATION, foley.THUD, seed=3411)
foley.write_bursts(ROOT / "assets" / "clicks.wav", [*CLICKS, LAMP], DURATION, foley.REMOTE_CLICK, seed=3412)
foley.write_bursts(ROOT / "assets" / "hum.wav", bed(foley.HUM, PRESS, HUM_LAST), DURATION, foley.HUM, seed=3413)
foley.write_bursts(ROOT / "assets" / "tap.wav", [TAP], DURATION, foley.KNOCK, seed=3414)
foley.write_bursts(ROOT / "assets" / "steps.wav", STEPS, DURATION, foley.KNOCK, seed=3415)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("thump", "assets/thump.wav", {"role": "effects", "gain": -6}),
        ("clicks", "assets/clicks.wav", {"role": "effects", "gain": -9}),
        ("hum", "assets/hum.wav", {"role": "ambience", "gain": -16}),
        ("tap", "assets/tap.wav", {"role": "effects", "gain": -6}),
        ("steps", "assets/steps.wav", {"role": "effects", "gain": -18}),
    ],
    loudness="-14",
)


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def spans(role: str, a: float = 0.0, b: float = 1e6) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role and a <= p.start < b]


def quiet(cues, lines, end=DURATION):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for at in sorted(x for span in lines for x in span):
        held = [c for c in cues if c.time <= at][-1]
        if held.time != at:
            later.append(replace(held, time=at, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, end, FPS)


def walking(points, start, stop, *, step=0.22, flip=False, make=cue, **kw):
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
            make(start + (stop - start) * k / n, "walk-a" if k % 2 else "walk-b", spot, flip=flip, ease=step, **kw)
        )
    return out


juno = quiet(
    [
        cue(0, "sit", JUNO_HIGH, eyes="happy", mouth="smile"),
        cue(THUMP, "floor", JUNO_DOWN, ease=0.2, eyes="wide", mouth="o"),
        cue(P[1].start, "floor", JUNO_DOWN, eyes="look", mouth="flat"),
        cue(P[5].end, "floor", JUNO_DOWN, eyes="look", mouth="flat"),
        cue(P[7].end, "floor", JUNO_DOWN, eyes="closed", mouth="flat"),
        cue(DARK + 0.5, "floor", JUNO_DOWN, eyes="look", mouth="flat"),
        cue(P[13].start, "floor", JUNO_DOWN, eyes="open", mouth="flat"),
    ],
    spans("juno", 0.0, NEXT),
    NEXT,
)
juno_next = quiet(
    [
        cue(0, "walk-a", (-220.0, 1620.0), flip=True, eyes="happy", mouth="smile"),
        *walking(((-220.0, 1620.0), (910.0, 1500.0)), NEXT + 0.1, SAT - 0.55, flip=True, eyes="happy", mouth="smile"),
        cue(SAT - 0.3, "stand", (910.0, 1500.0), eyes="happy", mouth="smile"),
        cue(SAT, "floor", DOOR_SEAT, ease=0.2, eyes="wide", mouth="o"),
        cue(SAT + 0.5, "floor", DOOR_SEAT, eyes="closed", mouth="flat"),
    ],
    [],
)
bo = quiet(
    [
        cue(0, "walk-a", (-260.0, FLOOR), eyes="happy", mouth="grin"),
        *walking(((-260.0, FLOOR), BO_AT), P[0].end - 0.3, P[1].start + 0.2, eyes="happy", mouth="grin"),
        cue(P[1].start + 0.25, "wave-a", BO_AT, eyes="happy", mouth="grin"),
        cue(P[2].start, "clasp", BO_AT, eyes="happy", mouth="grin"),
        cue(P[3].start, "stand", BO_AT, eyes="open", mouth="smile"),
        cue(P[4].start, "clasp", BO_AT, eyes="happy", mouth="grin"),
        cue(P[5].start, "wave-b", BO_AT, eyes="happy", mouth="grin"),
        cue(P[6].start, "stand", BO_AT, eyes="open", mouth="smile"),
        cue(P[7].start, "clasp", BO_AT, eyes="happy", mouth="grin"),
        cue(DARK, "stand", BO_FRIDGE, eyes="open", mouth="smile"),
        cue(P[9].start, "clasp", BO_FRIDGE, eyes="happy", mouth="grin"),
        cue(P[10].start, "stand", BO_FRIDGE, eyes="open", mouth="smile"),
        cue(P[11].start, "wave-b", BO_FRIDGE, flip=True, eyes="happy", mouth="grin"),
        cue(PRESS, "clasp", BO_NOD, eyes="happy", mouth="smile"),
        cue(LAMP + 0.18, "clasp", BO_NOD, ease=0.1, turn=7, eyes="happy", mouth="grin"),
        cue(LAMP + 0.4, "clasp", BO_NOD, ease=0.1, eyes="happy", mouth="grin"),
        cue(P[14].start, "wave-b", BO_CARD, flip=True, eyes="happy", mouth="grin"),
    ],
    spans("bo", 0.0, NEXT),
    NEXT,
)
pip = quiet(
    [
        cue(0, "walk-a", (-300.0, 1560.0), eyes="wide", mouth="flat"),
        *walking(((-300.0, 1560.0), PIP_AT), P[1].start + 0.1, P[2].start + 0.4, eyes="wide", mouth="flat"),
        cue(P[2].start + 0.45, "stand", PIP_AT, eyes="look", mouth="flat"),
        cue(P[3].start, "clasp", PIP_AT, eyes="wide", mouth="flat"),
        cue(DARK, "wave-a", PIP_WALL, eyes="look", mouth="flat"),
        cue(CLICKS[1], "wave-b", PIP_WALL, eyes="look", mouth="flat"),
        cue(CLICKS[2], "wave-a", PIP_WALL, eyes="look", mouth="flat"),
        cue(P[9].start, "stand", PIP_WALL, flip=True, eyes="look", mouth="flat"),
        cue(P[10].start, "clasp", PIP_WALL, flip=True, eyes="open", mouth="flat"),
        cue(PRESS, "wave-b", PIP_PRESS, flip=True, eyes="look", mouth="flat"),
        cue(PRESS + 0.95, "wave-b", PIP_PRESS, flip=True, eyes="squint", mouth="flat"),
        cue(P[13].start - 0.04, "stand", PIP_OFF, ease=0.0, eyes="open", mouth="flat"),
    ],
    spans("pip", 0.0, NEXT),
    NEXT,
)
bo_peek = quiet(
    [
        blob.cue(0, "lean", PEEK_FROM, scale=HALL_SCALE, eyes="happy", mouth="grin"),
        blob.cue(PEEK, "lean", PEEK_FROM, scale=HALL_SCALE, eyes="happy", mouth="grin"),
        blob.cue(PEEK + 0.26, "lean", PEEK_TO, scale=HALL_SCALE, ease=0.26, eyes="happy", mouth="grin"),
    ],
    spans("bo", NEXT),
)


def in_the_hall(g):
    shown = cv.group(g, "hall-cast")
    cv.gate(shown, [(NEXT, DURATION)])
    blob.bo(
        cv,
        shown,
        bo_peek,
        end=DURATION,
        scale=HALL_SCALE,
        mouth_states=ep.mouth("bo"),
        fps=FPS,
        shadow=False,
        id="bo-peek",
    )


def against_the_wall(g):
    soft_odds.home_fridge(cv, g, *FRIDGE_AT, end=DURATION, scale=0.82)
    cv.rect(g, 420, SHELF_Y, 280, 22, "#C98C5C", cv.ink, 4, radius=8)
    glow = cv.group(g, "lamp-lit-glow")
    cv.gate(glow, [(LAMP, NEXT)])
    look.pool(cv, glow, "lamp-spill", "#FFE9A0", 390, 420, 500, 500, 0.8)
    soft_bedtime.bedside_lamp(cv, g, *LAMP_AT, on=LAMP, off=NEXT, scale=0.8)
    cv.rect(g, SWITCH_AT[0] - 28, SWITCH_AT[1] - 44, 56, 88, "#F9EEDF", "#E2C8A8", 4, radius=6)  # where the switch was


def on_the_rug(g):
    room_cast = cv.group(g, "cast-day")
    cv.gate(room_cast, [(0.0, NEXT)])
    blob.pip(cv, room_cast, pip, end=NEXT, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False)
    blob.bo(cv, room_cast, bo, end=NEXT, scale=SCALE, mouth_states=ep.mouth("bo"), fps=FPS, shadow=False)
    blob.juno(cv, room_cast, juno, end=NEXT, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=False)
    card = soft_odds.in_hand(cv, room_cast, bo, "left", end=NEXT, scale=SCALE, fps=FPS, id="bo-card")
    cv.gate(card, [(P[14].start, NEXT)])
    soft_front.star_card(cv, card, -100, -90, scale=0.7, id="held-star-card")
    hands = blob.held(cv, room_cast, juno, end=NEXT, scale=SCALE, fps=FPS, id="juno-hands")
    soft_front.mug(cv, hands, 0, -14, scale=0.62, id="juno-mug")
    morning = cv.group(g, "cast-morning")
    cv.gate(morning, [(NEXT, DURATION)])
    blob.juno(
        cv,
        morning,
        juno_next,
        end=DURATION,
        scale=SCALE,
        mouth_states=ep.mouth("juno"),
        fps=FPS,
        shadow=False,
        id="juno-next",
    )
    carried = soft_odds.in_hand(
        cv, morning, juno_next, "right", end=DURATION, scale=SCALE, fps=FPS, id="juno-next-hand"
    )
    soft_front.mug(cv, carried, 0, -14, scale=0.62, id="juno-next-mug")


WIDE = Shot(0.0)
JUNO_CLOSE = (2.1, 740.0, 1240.0)
shots = [
    WIDE,
    Shot(P[1].start - 0.06, 1.3, 470.0, 1200.0),
    Shot(P[3].start - 0.04, 2.0, 65.0, 1060.0),
    Shot(P[4].start - 0.04, 1.3, 620.0, 1200.0),
    Shot(P[6].start - 0.04, *JUNO_CLOSE),
    Shot(P[7].start - 0.03, 2.1, 480.0, 1130.0),
    Shot(DARK, 1.36, 430.0, 1170.0),
    Shot(PRESS, 1.4, 450.0, 1140.0),
    Shot(P[13].start - 0.04, *JUNO_CLOSE),
    Shot(P[14].start - 0.04, 1.5, 750.0, 1240.0),
    Shot(NEXT, 1.0, 540.0, 960.0),
]
graded = soft_sets.finish(cv, ep.comp)
soft_front.front_room(
    cv, graded, shots=shots, wedged=[(0.0, NEXT)], hall=in_the_hall, behind=against_the_wall, cast=on_the_rug
)
soft_odds.dimmer(cv, graded, ((0.0, 0.0), (DARK, 0.3), (LAMP, 0.0)))

insert = cv.group(graded, "insert")
cv.gate(insert, [(JAB, NEXT)])
cv.rect(insert, 0, 0, 1080, 1920, "#E8D4B4")
soft_front.star_card(cv, insert, 540, 1000, tap=TAP, scale=2.1, id="soft-star-card")
arm = cv.group(insert, "juno-arm", x=210, y=1010)
cv.keys(
    arm,
    "y",
    [(JAB, 2000.0), (JAB + 0.3, 1500.0), (TAP - 0.1, 1520.0), (TAP, 1040.0), (TAP + 0.1, 1120.0), (TAP + 0.3, 1720.0)],
    False,
)
for colour, width in ((cv.ink, 92), (blob.JUNO_FILL, 80)):
    cv.line(arm, 0, 0, 40, 1000, colour, width)
    cv.ellipse(arm, -width / 2, -width / 2, width, width, colour)

over = soft_odds.notice(cv, ep.comp, 540, 524, "NEW AND IMPROVED", scale=0.82, shown=[(0.0, min(P[3].start, 3.0))])
later = soft_odds.notice(cv, ep.comp, 540, 524, "NEXT MORNING", scale=0.82, shown=[(NEXT, NEXT + 1.7)], id="soft-chip")

specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    specs.append(
        (p.role, max(0.0, p.start - 0.03), min(until, max(p.end + 0.3, p.start + 0.87)), p.caption, f"caption-{i + 1}")
    )
shown = [
    *ep.captions([s[1:] for s in specs if s[0] != "bo"], **soft_sets.CAPTIONS),
    *ep.captions([s[1:] for s in specs if s[0] == "bo"], **{**soft_sets.CAPTIONS, "color": "#2F5D8C"}),
]
ep.hide_on_cover(over, later, *shown)
ep.markers(extra=[("marker-press", PRESS, "Press and hold"), ("marker-next", NEXT, "Next morning")])
if SLUG in POSTS:
    ep.instagram(POSTS[SLUG])
ep.finish()

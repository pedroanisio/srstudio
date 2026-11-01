#!/usr/bin/env python3
"""Unread, built with srstudio: if it's important, they'll call, and they did, eleven times.

    srstudio record unread PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build unread PROJECT    # → PROJECT/unread.scene.xml

A phone fills the frame: one envelope, 41,382 and then 41,383. It is Pip's, and Juno has it. He sits in the sun at
peace. His car was towed, his lease ended, and that explains the new people. Her thumb stops on WELCOME TO THE TEAM!
Someone hired him in April. Why didn't they call? Eleven times. The phone rings at him, UNKNOWN NUMBER, and he presses
decline, gently, and the sound stops. If it's important, they'll email.

The first frame already moves: the phone is still rising when her first word lands.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, layout, soft_inbox, soft_odds, soft_props, soft_sets
from srstudio.soft_inbox import Count
from srstudio.soft_sets import BENCH_SEAT, Shot
from unread_audio import INTERVIEW

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "unread"
ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug=SLUG,
        title=INTERVIEW.title,
        description="Everyday-tech comedy: he never opens his email, because if it's important they'll call, and "
        "they did. Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        seed=INTERVIEW.seed,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions and the phone's lettering stay inside x 80–920
        bleed=True,  # the park's far plane is out of focus
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
STOP, RING = t.stop_start, t.ring_start
FPS = 15
SCALE = 2.2
PIP_SEAT, JUNO_SEAT = (178.0, BENCH_SEAT), (902.0, BENCH_SEAT)
PHONE_AT, PHONE_SCALE = (540.0, 1125.0), 3.4
HOOK_END = P[1].start - 0.08  # the two-shot lands before he answers
TICK = min(0.92, HOOK_END - 0.86)  # the badge goes up by one: each count holds 0.84 s
STOPPED = STOP + 0.26  # the list has stopped; the row is read from here
INSERT_END = P[4].start - 0.34  # she looks up at him before she says it
RING_INSERT = RING + 0.36  # he has looked at it
PRESS = P[7].start - 0.12  # the thumb lands and the ring stops
INSERT_LAST = P[7].start - 0.02
SCROLLS = [P[2].start + k * 0.34 for k in range(7)]
BIRDS = [HOOK_END + 0.2, HOOK_END + 0.5, HOOK_END + 0.72, P[3].start + 0.2, P[3].start + 0.45]

foley.write_bursts(ROOT / "assets" / "birds.wav", BIRDS, DURATION, foley.BIRD, seed=5207)
foley.write_bursts(
    ROOT / "assets" / "tick.wav", [TICK, *SCROLLS, STOP, STOP + 0.2], DURATION, foley.REMOTE_CLICK, seed=5208
)
foley.write_tones(ROOT / "assets" / "ring.wav", [RING], DURATION, (foley.RING * 2)[: int((PRESS - RING) / 0.05)])
foley.write_bursts(ROOT / "assets" / "press.wav", [PRESS], DURATION, foley.REMOTE_CLICK, seed=5209)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("birds", "assets/birds.wav", {"role": "ambience", "gain": -24}),
        ("tick", "assets/tick.wav", {"role": "effects", "gain": -18}),
        ("ring", "assets/ring.wav", {"role": "effects", "gain": -12}),
        ("press", "assets/press.wav", {"role": "effects", "gain": -14}),
    ],
    loudness="-14",
)


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def spans(role: str) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role]


pip = blob.quieted(
    [
        cue(0, "lounge", PIP_SEAT, eyes="closed", mouth="smile", flip=True),
        cue(P[3].start, "lounge", PIP_SEAT, eyes="happy", mouth="smile", flip=True),
        cue(P[3].end, "lounge", PIP_SEAT, eyes="closed", mouth="smile", flip=True),
        cue(P[4].start, "lounge", PIP_SEAT, eyes="wide", mouth="flat", flip=True),
        cue(P[5].start, "lounge", PIP_SEAT, eyes="open", mouth="small", flip=True),
        cue(P[5].end, "lounge", PIP_SEAT, eyes="open", mouth="flat", flip=True),  # the phone is where the camera is
        cue(P[7].start - 0.02, "lounge", PIP_SEAT, eyes="closed", mouth="smile", flip=True),
    ],
    spans("pip"),
    DURATION,
    FPS,
)
juno = blob.quieted(
    [
        cue(0, "sit", JUNO_SEAT, eyes="look", mouth="flat"),
        cue(P[2].start, "sit", JUNO_SEAT, eyes="look", mouth="small"),
        cue(STOP, "sit", JUNO_SEAT, eyes="wide", mouth="flat"),
        cue(INSERT_END, "sit", JUNO_SEAT, eyes="look", mouth="flat"),
        cue(P[6].start, "sit", JUNO_SEAT, eyes="look", mouth="flat"),
    ],
    spans("juno"),
    DURATION,
    FPS,
)


def world(g):
    blob.pip(cv, g, pip, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False)
    blob.juno(cv, g, juno, end=DURATION, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=False)
    hands = blob.held(cv, g, juno, end=DURATION, scale=SCALE, fps=FPS, id="juno-hands")
    soft_props.phone(cv, hands, scale=0.85, id="juno-phone")


TWO = Shot(0.0)
JUNO_CLOSE = (1.5, 720.0, 1042.0)  # her bun clears the caption
PIP_CLOSE = (1.5, 360.0, 1020.0)  # and so does his sprout
shots = [
    TWO,
    Shot(P[2].start - 0.05, *JUNO_CLOSE),
    Shot(P[3].start - 0.05, *PIP_CLOSE),
    Shot(INSERT_END, *JUNO_CLOSE),
    Shot(P[5].start - 0.05, *PIP_CLOSE),
    Shot(P[6].start - 0.05, 1.0, 540.0, 960.0),
    Shot(RING, *PIP_CLOSE),
]
graded = soft_sets.finish(cv, ep.comp)
soft_sets.park(cv, graded, seated=[(0, DURATION)], cast=world, shots=shots)


def inserted(name: str, spans_: list[tuple[float, float]]):
    g = cv.group(ep.comp, name)
    cv.gate(g, spans_)
    cv.rect(g, 0, 0, 1080, 1920, "#2E3A33", opacity=0.72)
    return g


def finger(g, name: str, fill: str, x: float, keys: list[tuple[float, float]], lean: float):
    """A fingertip on the screen, its arm running off the bottom of the frame."""
    arm = cv.group(g, name, x=x, y=0)
    cv.keys(arm, "y", keys, False)
    for colour, width in ((cv.ink, 92), (fill, 80)):
        cv.line(arm, 0, 0, lean, 1000, colour, width)
        cv.ellipse(arm, -width / 2, -width / 2, width, width, colour)
    return arm


hook = inserted("mail-insert", [(0.0, HOOK_END)])
rise = cv.group(hook, "mail-rise")
cv.keys(rise, "y", [(0.0, 90.0), (0.4, 0.0)], False)
soft_props.phone(
    cv,
    rise,
    x=PHONE_AT[0],
    y=PHONE_AT[1],
    scale=PHONE_SCALE,
    screen=lambda g: soft_inbox.mail_screen(
        cv, g, counts=(Count("41,382", 0.0, TICK), Count("41,383", TICK, HOOK_END + 0.1))
    ),
    id="mail-phone",
)

reading = inserted("list-insert", [(STOP, INSERT_END)])
soft_props.phone(
    cv,
    reading,
    x=PHONE_AT[0],
    y=PHONE_AT[1],
    scale=PHONE_SCALE,
    screen=lambda g: soft_inbox.mail_list(cv, g, marked=2, scroll=((STOP, 22.0), (STOPPED, 0.0))),
    id="list-phone",
)
finger(reading, "juno-thumb", blob.JUNO_FILL, 700, [(STOP, 1660.0), (STOPPED, 1560.0)], 120)

calling = inserted("call-insert", [(RING_INSERT, INSERT_LAST)])
soft_props.phone(
    cv,
    calling,
    x=PHONE_AT[0],
    y=PHONE_AT[1],
    scale=PHONE_SCALE,
    screen=lambda g: soft_inbox.call_screen(cv, g, pressed=PRESS),
    id="call-phone",
)
button = PHONE_AT[0] - 34 * PHONE_SCALE
finger(
    calling, "pip-thumb", cv.white, button,
    [(RING_INSERT, 2100.0), (PRESS - 0.26, 1620.0), (PRESS, PHONE_AT[1] + 66 * PHONE_SCALE)], -180,
)  # fmt: skip

CUT = P[2].start - 0.05
over = soft_odds.notice(cv, ep.comp, 540, 524, "LAST OPENED:\n2021", scale=0.82, size=50, shown=[(0.0, CUT)])

specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    held = min(until, max(p.end + 0.3, p.start + 0.87))
    specs.append((max(0.0, p.start - 0.03), RING if i == 6 else held, p.caption, f"caption-{i + 1}"))
ep.hide_on_cover(over, *ep.captions(specs, **soft_sets.CAPTIONS))
ep.markers(extra=[("marker-stop", STOP, "Her thumb stops"), ("marker-ring", RING, "It rings")])
if SLUG in POSTS:
    ep.instagram(POSTS[SLUG])
ep.finish()

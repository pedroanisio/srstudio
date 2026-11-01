#!/usr/bin/env python3
"""Wrong Door, built with srstudio: a good interview, and a confident exit into a closet.

    srstudio record wrong-door PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build wrong-door PROJECT    # → PROJECT/wrong-door.scene.xml

"Great interview, Pip. We'll call you." Pip thanks him three times, strides across the room and shuts a door behind him
with authority. Black, one line of light, a mop going over. "Okay. That's a closet." Bo is still out there, so Pip lives
here now. WEDNESDAY: the door opens on Bo with an empty mug, and on Pip with a row of crumbs and his tie on the mop.
"You've been here since Monday." "Yes." "First in, last out. You got the job." Pip beams, strides to the next door and
shuts it behind him with authority. A clatter. "Other door."

The first frame already moves: the handshake is going before Bo's first word.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import (
    SOFT,
    Episode,
    EpisodeSpec,
    blob,
    camera,
    foley,
    layout,
    signature,
    soft_bedtime,
    soft_closet,
    soft_front,
    soft_odds,
    soft_sets,
)
from srstudio.soft_closet import Door
from wrong_door_audio import CUE_LEAD, CUE_TAIL, INTERVIEW, SHAKE

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "wrong-door"
ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug=SLUG,
        title=INTERVIEW.title,
        description="Job-hunting comedy: a good interview, a confident exit, and the closet he lives in by Wednesday. "
        "Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        seed=INTERVIEW.seed,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions stay inside x 80–920
        bleed=True,
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
OPENS, IN, SHUT, DARK = t.opens_start, t.in_start, t.shut_start, t.dark_start
WEDNESDAY, WIDE, BO_SHUTS, NEXT_SHUT, ALONE, CLATTER = (
    t.wednesday_start,
    t.wide_start,
    t.bo_shuts_start,
    t.next_shut_start,
    t.alone_start,
    t.clatter_start,
)
FPS = 15
SCALE = 0.85
BO_SCALE = 1.15
CLOSE_END = P[1].start - 0.05  # off the hands, onto the room, as the first caption goes
AGAIN = t.again_start, t.again_start + SHAKE  # the same handshake, the job in it this time
LEAVES = WIDE + 0.1  # out of the doorway, on the wide
AT_DOOR = OPENS - 0.1
SIP = P[9].start - 0.5
DOOR_A = (135.0, 345.0)
DOOR_B = (355.0, 525.0)
UP = 640.0
A_FOOT = (590.0, 1128.0)  # behind the table's end, at the handle
B_FOOT = (775.0, 1098.0)
A_STAND = (548.0, 1138.0)  # in the doorway, on the closet's floor
PIP_START, AROUND = (590.0, 1570.0), (705.0, 1330.0)
SLIT = (632.0, 682.0)
BO_NEAR = (365.0, 1560.0)  # right of the table's marks, so a close on him keeps them

patted = [0.2, 0.62, 1.04, 1.46, AGAIN[0] + 0.1, AGAIN[0] + 0.45]
foley.write_bursts(ROOT / "assets" / "pats.wav", patted, DURATION, foley.CHEW, seed=3431)
steps_there = [P[1].start + 0.05 + 0.23 * k for k in range(4)]
steps_on = [AGAIN[1] + 0.05 + 0.22 * k for k in range(3)]
foley.write_bursts(ROOT / "assets" / "steps.wav", steps_there + steps_on, DURATION, foley.KNOCK, seed=3432)
clicks = [OPENS, SHUT, WEDNESDAY, BO_SHUTS, NEXT_SHUT - 0.4, NEXT_SHUT]
foley.write_bursts(ROOT / "assets" / "click.wav", clicks, DURATION, foley.REMOTE_CLICK, seed=3433)
foley.write_bursts(ROOT / "assets" / "shut.wav", [SHUT + 0.01, NEXT_SHUT + 0.01], DURATION, foley.KNOCK, seed=3434)
foley.write_bursts(ROOT / "assets" / "creak.wav", [DARK + 0.12], DURATION, foley.CREAK, seed=3435)
foley.write_bursts(ROOT / "assets" / "clatter.wav", [P[2].start - 0.14, CLATTER], DURATION, foley.PLATES, seed=3436)
foley.write_bursts(ROOT / "assets" / "thud.wav", [P[2].start - 0.16, CLATTER - 0.02], DURATION, foley.THUD, seed=3437)
foley.write_bursts(ROOT / "assets" / "chair.wav", [P[2].end + 0.1], DURATION, foley.CREAK, seed=3438)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("pats", "assets/pats.wav", {"role": "effects", "gain": -9}),
        ("steps", "assets/steps.wav", {"role": "effects", "gain": -18}),
        ("click", "assets/click.wav", {"role": "effects", "gain": -12}),
        ("shut", "assets/shut.wav", {"role": "effects", "gain": -12}),
        ("creak", "assets/creak.wav", {"role": "effects", "gain": -16}),
        ("clatter", "assets/clatter.wav", {"role": "effects", "gain": -15}),
        ("thud", "assets/thud.wav", {"role": "effects", "gain": -14}),
        ("chair", "assets/chair.wav", {"role": "effects", "gain": -24}),
    ],
    loudness="-14",
)


def cue(time, pose, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def bo_cue(time, pose, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=BO_SCALE, **kw)


def walking(points, start, stop, **kw):
    return blob.walking(points, start, stop, scale=SCALE, **kw)


def spans(role: str) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role]


pip = blob.quieted(
    [
        cue(0, "stand", PIP_START, eyes="happy", mouth="grin"),
        *walking((PIP_START, AROUND, A_FOOT), P[1].start + 0.02, AT_DOOR, eyes="happy", mouth="grin"),
        cue(AT_DOOR + 0.02, "wave-b", A_FOOT, eyes="happy", mouth="grin"),
        cue(OPENS + 0.25, "stand", A_STAND, eyes="happy", mouth="grin"),
        cue(WEDNESDAY, "stand", A_STAND, eyes="wide", mouth="smile"),
        cue(P[5].start, "wave-a", A_STAND, eyes="wide", mouth="grin"),
        cue(P[6].start, "stand", A_STAND, eyes="wide", mouth="flat"),
        cue(P[7].start, "clasp", A_STAND, eyes="open", mouth="smile"),
        cue(P[8].start, "stand", A_STAND, eyes="happy", mouth="smile"),
        *walking((A_STAND, A_FOOT), WIDE + 0.02, BO_SHUTS - 0.1, eyes="happy", mouth="grin"),
        cue(BO_SHUTS - 0.08, "stand", A_FOOT, eyes="happy", mouth="grin"),
        *walking((A_FOOT, B_FOOT), AGAIN[1], NEXT_SHUT - 0.5, eyes="happy", mouth="grin"),
        cue(NEXT_SHUT - 0.45, "stand", B_FOOT, eyes="happy", mouth="grin"),
    ],
    spans("pip"),
    DURATION,
    FPS,
)
bo = blob.quieted(
    [
        bo_cue(0, "stand", BO_NEAR, eyes="happy", mouth="smile"),
        bo_cue(WEDNESDAY, "stand", BO_NEAR, eyes="open", mouth="flat"),
        bo_cue(P[6].start, "clasp", BO_NEAR, ease=0.0, eyes="open", mouth="flat"),
        bo_cue(P[8].start, "clasp", BO_NEAR, eyes="happy", mouth="smile"),
        bo_cue(BO_SHUTS, "stand", BO_NEAR, ease=0.0, eyes="happy", mouth="smile"),
        bo_cue(ALONE, "stand", BO_NEAR, eyes="open", mouth="flat"),
        bo_cue(SIP, "wave-b", BO_NEAR, eyes="closed", mouth="flat"),
        bo_cue(P[9].start - 0.04, "stand", BO_NEAR, eyes="open", mouth="flat"),
    ],
    spans("bo"),
    DURATION,
    FPS,
)
OUT = [(CLOSE_END, OPENS + 0.25), (LEAVES, NEXT_SHUT - 0.42)]
IN_DOOR = [(OPENS + 0.25, SHUT), (WEDNESDAY, LEAVES), (NEXT_SHUT - 0.42, NEXT_SHUT)]
A_SHUT = [(0.0, OPENS), (SHUT, WEDNESDAY), (BO_SHUTS, DURATION)]
B_SHUT = [(0.0, NEXT_SHUT - 0.4), (NEXT_SHUT, DURATION)]


def pip_rig(g, shown, tag):
    group = cv.group(g, f"pip-{tag}")
    cv.gate(group, shown)
    blob.pip(cv, group, pip, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False,
             id=f"pip-rig-{tag}")  # fmt: skip


def in_the_doorway(g):
    life = cv.group(g, "a-small-life")
    cv.gate(life, [(WEDNESDAY, BO_SHUTS)])
    soft_closet.mop(cv, life, 650, 1140, scale=0.8, lean=2.0, id="closet-mop")
    cv.path(life, "M 648 722 L 668 722 L 672 850 L 658 872 L 644 850 Z", "#C9544A", cv.ink, 3)
    cv.rect(life, 600, 904, 76, 12, "#C9A36F", stroke=cv.ink, sw=3)  # a shelf, and the neat row of crumbs on it
    for k in range(4):
        cv.ellipse(life, 622 + 15 * k, 898, 5.5, 4.5, "#E9CD9A", cv.ink, 1.5)
    pip_rig(g, IN_DOOR, "in")


def framed(time, scale, x, y):
    """A held frame: ``(x, y)`` of the room sits at the middle of the picture, ``scale`` times its size."""
    return time, scale, 540 - scale * x, 960 - scale * y


graded = soft_sets.finish(cv, ep.comp)
world = cv.group(graded, "world")
cv.gate(world, [(0.0, DARK), (WEDNESDAY, DURATION)])  # nothing to draw behind the dark
camera.reframe(
    cv,
    world,
    [
        framed(0.0, 1.0, 540, 960),
        framed(WEDNESDAY, 1.5, 470, 850),  # medium on Pip, Bo in the foreground
        framed(P[6].start - CUE_LEAD, 2.4, 225, 1134),  # close on Bo, the left of the frame on the set's edge
        framed(P[7].start - CUE_LEAD, 2.05, 545, 815),  # close on Pip
        framed(P[8].start - CUE_LEAD, 2.4, 225, 1134),
        framed(WIDE, 1.0, 540, 960),
        framed(ALONE, 1.3, 560, 1100),  # Bo and both doors behind him
    ],
)
room = cv.group(world, "room")
blob.meeting_room(cv, room, chair=False)
soft_closet.doors(
    cv,
    room,
    [Door(*DOOR_A, UP, A_SHUT), Door(*DOOR_B, UP, B_SHUT, hinge="right")],
    end=DURATION,
    between=in_the_doorway,
)
pip_rig(room, OUT, "out")
blob.bo(cv, room, bo, end=DURATION, scale=BO_SCALE, mouth_states=ep.mouth("bo"), fps=FPS, shadow=False)
carried = soft_odds.in_hand(cv, room, bo, "right", end=DURATION, scale=BO_SCALE, fps=FPS, id="bo-mug-hand")
cv.gate(carried, [(WEDNESDAY, DURATION)])
held = cv.group(carried, "mug-held")
cv.gate(held, [(WEDNESDAY, SIP), (P[9].start - 0.04, DURATION)])
soft_front.mug(cv, held, 0, -14, scale=0.62, empty=True, id="bo-mug")
sipped = cv.group(carried, "mug-sipped")  # the empty mug up at his mouth
cv.gate(sipped, [(SIP + 0.08, P[9].start - 0.04)])
soft_front.mug(cv, sipped, -92, 62, scale=0.62, empty=True, id="bo-mug-sip")

hands = cv.group(graded, "handshakes", x=1080.0, scaleX=-1.0)  # Bo stands left in the wides: his arm comes from there
soft_bedtime.handshake(cv, hands, 0.0, CLOSE_END, pumps=3)
soft_bedtime.handshake(cv, hands, *AGAIN, pumps=2, id="soft-handshake-again")


def dark_pip(g):
    soft_closet.mop(cv, g, 760, 1640, scale=1.5, tips=(DARK + 0.1, P[2].start - 0.16), to=62.0, id="dark-mop")
    in_dark = blob.quieted(
        [
            blob.cue(0, "stand", (560.0, 1850.0), scale=2.1, eyes="wide", mouth="flat"),
            blob.cue(P[3].start - 0.2, "stand", (560.0, 1850.0), scale=2.1, eyes="look", mouth="flat"),
            blob.cue(P[4].start - 0.2, "stand", (560.0, 1850.0), scale=2.1, eyes="open", mouth="flat"),
        ],
        [(P[i].start, P[i].end) for i in (2, 3, 4)],
        DURATION,
        FPS,
    )
    blob.pip(
        cv, g, in_dark, end=DURATION, scale=2.1, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False, id="pip-dark"
    )
    cv.rect(g, 540, 574, 260, 18, "#C9A36F", stroke=cv.ink, sw=3)  # a shelf: only what the slit crosses shows
    signature.cactus(cv, g, 657, 574, 0.36)
    signature.code(cv, g, 634.5, 578, 8, color="#2F2A26")


dark = soft_closet.closet(cv, graded, DARK, WEDNESDAY, slit=SLIT, behind=dark_pip)
PUSH = (P[4].start - 0.3, WEDNESDAY)  # he makes up his mind: the one slow move in the dark
for prop, at_rest, pushed in (("scaleX", 1, 1.12), ("scaleY", 1, 1.12), ("x", 0, 540 * -0.12), ("y", 0, 800 * -0.12)):
    cv.keys(dark, prop, [(0.0, at_rest), (PUSH[0], at_rest), (PUSH[1], pushed)], hold=False)

note = soft_odds.notice(cv, ep.comp, 540, 524, "WEDNESDAY", scale=0.82, shown=[(WEDNESDAY, WEDNESDAY + 1.7)])
specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    specs.append(
        (
            p.role,
            max(0.0, p.start - CUE_LEAD),
            min(until, max(p.end + CUE_TAIL, p.start + 0.87)),
            p.caption,
            f"caption-{i + 1}",
        )
    )
shown = [
    *ep.captions([s[1:] for s in specs if s[0] != "bo"], **soft_sets.CAPTIONS),
    *ep.captions([s[1:] for s in specs if s[0] == "bo"], **{**soft_sets.CAPTIONS, "color": "#2F5D8C"}),
]
ep.hide_on_cover(note, *shown)
ep.markers(extra=[("marker-closet", DARK, "That's a closet"), ("marker-wednesday", WEDNESDAY, "Wednesday")])
if SLUG in POSTS:
    ep.instagram(POSTS[SLUG])
ep.finish()

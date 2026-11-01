#!/usr/bin/env python3
"""Free Shipping, built with srstudio: six dollars is too much, and fifty dollars and two cents is free.

    srstudio record free-shipping PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build free-shipping PROJECT    # → PROJECT/free-shipping.scene.xml

Juno, at the laptop, jaw set, refuses six dollars shipping and adds a tiny whisk, an egg poacher, a sock stretcher and a
bird feeder to get it free. The same frame a week on: parcels to the ceiling, and Pip holds the whisk to the light. Send
it all back. Return shipping's six dollars. Pip goes and sits down where she sat, and says her first line, on the frame
the reel opened on with the seats swapped.

The first second is a held frame (arm A of the ``sp-hook_motion`` test): nothing moves, nothing is said and nothing is
written until :data:`~free_shipping_audio.OPENING`, and this file refuses to build otherwise.
"""

import os
from dataclasses import replace

from _common import project_root
from free_shipping_audio import INTERVIEW, OPENING
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, layout, soft_props, soft_sets
from srstudio.soft_props import BadgeState

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="free-shipping",
        title=INTERVIEW.title,
        description="Money comedy: a couple spends twenty one dollars to save six on shipping, and it costs six to "
        "send it back. Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        seed=INTERVIEW.seed,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions and the cart's lettering stay inside x 80–920
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
ADDED = [float(a) for a in t.meta["added"]]
CART, FREE, WEEK, SIT = t.cart_start, t.free_start, t.week_start, t.sit_start
FPS = 15
SCALE = blob.SCALE
SEAT = blob.SEAT
BESIDE = (300.0, 1300.0)  # on their feet behind the desk, the laptop's lid between them and the seat
FRONT = (800.0, 1740.0)  # in the room, in front of the chair, a week on
CEILING_ROWS, BOX = 8, 176.0
PRICES = ("$38.00", "$41.50", "$44.00", "$50.02")
RED, GREEN, GOLD = "#D9534F", "#4CAF50", "#F2A93B"
SITTING = 1.1  # he goes down slowly

foley.write_typing(ROOT / "assets" / "keys.wav", ADDED, DURATION, seed=INTERVIEW.seed + 1)
foley.write_tones(ROOT / "assets" / "fanfare.wav", [FREE], DURATION)
foley.write_whoosh(ROOT / "assets" / "cut.wav", [WEEK], DURATION, length=0.3, seed=INTERVIEW.seed + 2)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("keys", "assets/keys.wav", {"role": "effects", "gain": -9}),
        ("fanfare", "assets/fanfare.wav", {"role": "effects", "gain": -8}),
        ("cut", "assets/cut.wav", {"role": "effects", "gain": -14}),
    ]
)


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def spans(role: str, a: float = 0.0, b: float = DURATION) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role and a <= p.start < b]


def quiet(cues, lines):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for _, stop in lines:
        held = [c for c in cues if c.time <= stop][-1]
        if held.time != stop:
            later.append(replace(held, time=stop, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, DURATION, FPS)


juno_seated = quiet(
    [
        cue(0, "type-a", SEAT, eyes="squint", mouth="flat"),
        cue(ADDED[0], "type-b", SEAT, ease=0.08, eyes="squint", mouth="flat"),
        cue(ADDED[1], "type-a", SEAT, ease=0.08, eyes="squint", mouth="flat"),
        cue(ADDED[2], "type-b", SEAT, ease=0.08, eyes="squint", mouth="flat"),
        cue(ADDED[3], "type-a", SEAT, ease=0.08, eyes="squint", mouth="flat"),
        cue(FREE, "cheer-a", SEAT, ease=0.1, lift=20, eyes="happy", mouth="grin"),
        cue(FREE + 0.3, "cheer-b", SEAT, ease=0.12, eyes="happy", mouth="grin"),
    ],
    spans("juno", 0.0, WEEK),
)
juno_standing = quiet(
    [
        cue(0, "clasp", BESIDE, eyes="look", mouth="flat"),
        cue(P[8].end + 0.2, "clasp", BESIDE, eyes="squint", mouth="flat"),
        cue(P[9].end, "clasp", BESIDE, eyes="look", mouth="flat"),
    ],
    spans("juno", WEEK),
)
pip_standing = quiet(
    [
        cue(0, "clasp", BESIDE, eyes="look", mouth="flat"),
        cue(ADDED[3], "clasp", BESIDE, eyes="squint", mouth="flat"),
        cue(FREE, "clasp", BESIDE, eyes="closed", mouth="flat"),
    ],
    spans("pip", 0.0, WEEK),
)
pip_seated = quiet(
    [
        cue(0, "clasp", FRONT, eyes="look", mouth="flat"),
        cue(P[9].end, "clasp", FRONT, eyes="closed", mouth="flat"),
        cue(SIT + SITTING, "type-a", SEAT, ease=SITTING, eyes="squint", mouth="flat"),
    ],
    spans("pip", WEEK),
)

for name, cues in (("juno", juno_seated), ("pip", pip_standing)):
    moved = [c for c in cues if 0.0 < c.time < OPENING or (c.time >= OPENING and c.time - c.ease < OPENING)]
    if moved:
        raise ValueError(f"arm A: {name} moves inside the held opening: {moved}")
if P[0].start < OPENING:
    raise ValueError(f"arm A: the first line starts at {P[0].start}, inside the held opening of {OPENING} s")


def behind_desk(g):
    blob.pip(
        cv,
        g,
        pip_standing,
        end=DURATION,
        scale=SCALE,
        mouth_states=ep.mouth("pip"),
        fps=FPS,
        shadow=False,
        id="pip-beside",
    )
    hands = blob.held(cv, g, pip_standing, end=DURATION, scale=SCALE, fps=FPS, id="pip-mug")
    cv.rect(hands, -30, -84, 60, 66, "#F7F2E8", cv.ink, 4, radius=8)
    cv.rect(hands, 26, -68, 20, 32, None, cv.ink, 5, radius=8)
    cv.gate(g, [(0.0, WEEK)])


graded = soft_sets.finish(cv, ep.comp)
stack = cv.group(graded, "stack")
cv.gate(stack, [(WEEK, DURATION)])
soft_props.parcels(cv, stack, -60, 1300, columns=7, rows=CEILING_ROWS, size=BOX)
behind = cv.group(graded, "behind-desk")
behind_desk(behind)
hers = cv.group(graded, "juno-at-the-slip")
cv.gate(hers, [(WEEK, DURATION)])
blob.juno(
    cv,
    hers,
    juno_standing,
    end=DURATION,
    scale=SCALE,
    mouth_states=ep.mouth("juno"),
    fps=FPS,
    shadow=False,
    id="juno-beside",
)
slip = blob.held(cv, hers, juno_standing, end=DURATION, scale=SCALE, fps=FPS, id="juno-slip")
cv.rect(slip, -38, -120, 76, 104, "#F7F2E8", cv.ink, 4, radius=3)
for k in range(3):
    cv.rect(slip, -24, -102 + 20 * k, 48, 6, "#9AA3A8")
blob.office(cv, graded)
seated = cv.group(graded, "juno-at-the-laptop")
cv.gate(seated, [(0.0, WEEK)])
blob.juno(cv, seated, juno_seated, end=DURATION, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=False)
front = cv.group(graded, "pip-in-the-room")
cv.gate(front, [(WEEK, DURATION)])
blob.pip(cv, front, pip_seated, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False)
held = blob.held(cv, front, pip_seated, end=DURATION, scale=SCALE, fps=FPS, id="pip-whisk")
cv.gate(held, [(WEEK, SIT)])
soft_props.whisk(cv, held, 0, 20, scale=1.1)
put_down = cv.group(graded, "whisk-on-the-desk", x=120, y=1262, rotation=78)
cv.gate(put_down, [(SIT, DURATION)])
soft_props.whisk(cv, put_down, 0, 0, id="whisk-put-down")

CART_BOX = (450, 470, 450, 96)
opening = cv.group(ep.comp, "cart-opening")
cv.gate(opening, [(0.0, CART)])
with cv.frozen():  # a badge pops in on its first frame, and nothing moves in the held opening
    soft_props.status_badge(
        cv, opening, [BadgeState("shipping", "$6 SHIPPING", RED, 0.0, CART)], CART_BOX, id="cart-then"
    )
steps = [CART, *ADDED, FREE, WEEK]
soft_props.status_badge(
    cv,
    ep.comp,
    [
        BadgeState("cart", "$29.00", GOLD, CART, steps[1]),
        *(BadgeState(f"cart-{i}", p, GOLD, steps[i], steps[i + 1]) for i, p in enumerate(PRICES, start=1)),
        BadgeState("free", "FREE SHIPPING", GREEN, FREE, WEEK),
        BadgeState("again", "$6 SHIPPING", RED, SIT + SITTING, DURATION),
    ],
    CART_BOX,
    id="cart",
)

specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    end = DURATION if i + 1 == len(P) else min(until, p.end + 0.6, *([WEEK] if p.start < WEEK else []))
    specs.append((p.start - 0.05, end, p.caption, f"caption-{i + 1}"))
if specs[0][0] < OPENING:
    raise ValueError(f"arm A: the first caption starts at {specs[0][0]}, inside the held opening of {OPENING} s")
ep.captions(specs, **soft_sets.CAPTIONS)
ep.markers(extra=[("marker-free", FREE, "Free shipping"), ("marker-week", WEEK, "A week later")])
ep.instagram(POSTS["free-shipping"])
out = ep.finish()
ep.check_overlays(out, ["cart-then", "cart"])

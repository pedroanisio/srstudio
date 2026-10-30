#!/usr/bin/env python3
"""Comedy Cut 23 — Storage Full, built with srstudio: Milo on the park bench, a pigeon, and a full phone.

    srstudio record storage-full PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build storage-full PROJECT    # → PROJECT/storage-full.scene.xml

A pigeon walks up the park path and does a backflip in front of Milo's bench. "No way. Do that again!" The pigeon
nods: ready. The phone: "Storage full." "Delete something!" It offers fourteen photos of the same sunset; yes;
"Still full." The pigeon looks away. "Delete your wedding video?" Milo and the pigeon look at each other. "...Yes."
"Recording." The pigeon flies off. A message from his wife: can he send her their wedding video? Milo looks into
the lens.

The first frame already moves (arm B of the ``sp-hook_motion`` test): the pigeon is walking in from the right and the
camera is pushing in from the first key. Like *Culture Fit*, the episode declares no engine safe area (the opening
wide holds the park sign's lettering right of x 920); captions and phone cards are placed by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import CAFE, Episode, EpisodeSpec, cast, graphics, locations

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="storage-full",
        number="23",
        title="Storage Full — Comedy Cut 23",
        description="Park comedy: a pigeon does a backflip, the phone is full, and Milo decides what to delete to "
        "film the encore. Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        seed=23042,
        background="#CFE3E6",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
FLIP, FLIP_END, STARE = t.flip_start, t.flip_end, t.stare_start
CHIMES = [float(c) for c in t.meta["chimes"]]
FLUTTER, REACTION, DURATION = t.flutter_start, t.reaction, t.duration
SCALE = 1.25
MILO_AT = (330, locations.park_seat_y(300, SCALE), SCALE)  # the seated café rig ends its torso at 300
BIRD = (640, 1500, 0.9)  # where it stops on the path in front of the bench, facing Milo
WALK = 1.0  # seconds of the walk-up from the right
STRIDE = 0.125
BODY = (-52 * BIRD[2], -5 * BIRD[2])  # the mirrored rig's body centre, from its feet: the flip turns about it
L = [P(i) for i in range(len(t.phrases))]


def nod(at: float, depth: float = -14, hold: float = 0.22) -> list[tuple[float, float]]:
    return [(at, 0), (at + 0.10, depth), (at + 0.10 + hold, depth), (at + 0.22 + hold, 0)]


def bird(g):
    """It walks up the path, backflips, nods, looks away bored, stares back during the standoff and flies off."""
    x, y, s = BIRD
    leaving = cv.group(g, "pigeon-leaving")
    cv.gate(leaving, [(0, FLUTTER + 1.2)])
    cv.keys(leaving, "y", [(FLUTTER, 0), (FLUTTER + 1.1, -1100)], kind="sine-in")  # up past the bench, on camera
    cv.keys(leaving, "x", [(FLUTTER, 0), (FLUTTER + 1.1, 320)], kind="sine-in")
    walk = cv.group(leaving, "pigeon-walk")
    cv.keys(walk, "x", [(0, 300), (WALK, 0)], hold=False)
    steps = round(WALK / STRIDE)
    cv.keys(walk, "y", [(i * STRIDE, -9 * (i % 2)) for i in range(steps + 1)], hold=False)
    hop = cv.group(walk, "pigeon-flip", x=x + BODY[0], y=y + BODY[1])
    cv.keys(hop, "rotation", [(0, 0), (FLIP, 0), (FLIP_END, 360)], kind="sine-in-out")  # head up and over, back
    cv.keys(hop, "y", [(0, y + BODY[1]), (FLIP, y + BODY[1]), (FLIP + 0.25, y + BODY[1] - 230),
                       (FLIP_END, y + BODY[1])], kind="sine-in-out")  # fmt: skip
    turn = cv.group(hop, "pigeon-turn")
    away, back = L[5].end + 0.30, STARE + 0.12
    cv.keys(turn, "scaleX", [(0, 1), (away, 1), (away + 0.10, -1), (back, -1), (back + 0.10, 1)], hold=False)
    bob = [(i * STRIDE, -7 * (i % 2)) for i in range(steps + 1)]
    nods = (
        bob
        + nod(L[1].end + 0.35)  # ready
        + [(STARE + 0.30, 0), (STARE + 0.55, -12), (STARE + 1.10, -12), (STARE + 1.40, 0)]  # the slow nod
        + [(FLUTTER - 0.15, 0), (FLUTTER, 10)]  # up, and off
    )
    cast.pigeon(cv, turn, -BODY[0], -BODY[1], s, flip=True, nods=nods, id="park-pigeon")


milo = cast.Customer(cv, seated=True)
park = ep.setup(
    lambda cv_, parent, shots, **slots: locations.park(cv_, locations.finish(cv_, parent), shots=shots, **slots),
    [(0, DURATION)],
    on_bench=lambda g: ep.perform(
        milo,
        g,
        *MILO_AT,
        mouth=ep.mouth("milo", smile=[(FLIP_END, L[1].end + 0.6), (L[5].start, L[5].end)]),
        blinks=[
            (L[2].end + 0.20, L[2].end + 0.34),
            (L[6].end + 0.10, L[6].end + 0.50),  # "Still full.": the slow blink
            (L[8].end + 0.25, L[8].end + 0.39),
            (CHIMES[2] + 0.10, CHIMES[2] + 0.24),
        ],
        nods=[
            (0, 6),
            (FLIP, 6),
            (FLIP + 0.25, -6),  # the head follows the flip up
            (FLIP_END, 4),
            (L[1].start, 4),
            (L[1].start + 0.25, -4),  # "Do that again!"
            (CHIMES[0], -4),
            (CHIMES[0] + 0.25, 8),  # down at the phone
            (L[3].start, 8),
            (L[3].start + 0.2, 2),
            (L[5].start, 2),
            (L[5].start + 0.2, 10),  # "Yes!"
            (STARE, 10),
            (STARE + 0.3, 2),  # up at the pigeon: the standoff
            (L[8].start, 2),
            (L[8].start + 0.3, 9),  # "...Yes."
            (L[9].end, 9),
            (L[9].end + 0.3, -4),  # up after the bird
            (CHIMES[2], -4),
            (CHIMES[2] + 0.25, 8),  # the message
            (REACTION, 8),
            (REACTION + 0.30, 0),  # into the lens
        ],
    ),
    beside_bench=bird,
    cactus=None,
)
cv.keys(milo.eyes, "x", [(0, 12), (CHIMES[0], 12), (CHIMES[0] + 0.12, -10), (STARE, -10), (STARE + 0.15, 12),
                         (L[8].start - 0.25, 12), (L[8].start - 0.10, -10), (L[9].end, -10), (L[9].end + 0.15, 12),
                         (CHIMES[2], 12), (CHIMES[2] + 0.12, -10), (REACTION, -10), (REACTION + 0.15, 0)],
        hold=False)  # fmt: skip  # the bird, the phone, the bird, the phone, the lens
cv.keys(milo.eyes, "y", [(0, 6), (FLIP, 6), (FLIP + 0.2, -6), (FLIP_END, 6), (FLUTTER, 6), (FLUTTER + 0.3, -10),
                         (CHIMES[2], -10), (CHIMES[2] + 0.12, 4), (REACTION, 4), (REACTION + 0.15, 0)],
        hold=False)  # fmt: skip


def close(at, scale, to):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


WIDE = (1.1, -54, -100)  # the bench and the path, the bird below the captions
OPENING = close((500, 1180), 1.3, (540, 1000))  # the push ends on Milo and the bird, the flip big in frame
FRAMES = {  # angle -> scale, x, y
    "wide": WIDE,
    "milo": close(MILO_AT[:2], 1.45, (480, 1000)),  # his head below the phone cards
    "pigeon": close((BIRD[0] + BODY[0], BIRD[1] - 40), 2.4, (540, 950)),  # the frame still ends on the path
}
EPS = 1 / 120
keys: dict[str, list[tuple[float, float]]] = {"scale": [(0, 1.0)], "x": [(0, 0)], "y": [(0, 0)]}
cuts = list(t.cuts)
for i, c in enumerate(cuts):
    s, x, y = OPENING if i == 0 else FRAMES[c.angle]
    end = cuts[i + 1].time - EPS if i + 1 < len(cuts) else DURATION
    if i == 0:  # the opening push: from the full set at 0 in on the bench by the first cut, easing out
        for k in range(1, 7):
            u = k / 6
            e = 1 - (1 - u) ** 2
            at = end * u
            keys["scale"].append((at, 1.0 + (s - 1.0) * e))
            keys["x"].append((at, x * e))
            keys["y"].append((at, y * e))
        continue
    for prop, v in (("scale", s), ("x", x), ("y", y)):
        keys[prop] += [(c.time, v), (end, v)]
for prop in ("scaleX", "scaleY"):
    cv.keys(park, prop, keys["scale"], hold=False)
cv.keys(park, "x", keys["x"], hold=False)
cv.keys(park, "y", keys["y"], hold=False)


def phone_card(index: int, who: str, status: str, show: tuple[float, float]):
    """A push notification, at two and a quarter times the café card, high in the frame."""
    holder = cv.group(ep.comp, f"push-holder-{index}", x=215, y=300, scaleX=2.25, scaleY=2.25)
    graphics.notification(cv, holder, index, who, status, show, x=0, y=0, id_prefix="push")


phone_card(1, "Phone", "Storage full", (CHIMES[0], L[4].start))
phone_card(2, "Storage", "Delete 14 sunsets?", (L[4].start, L[6].start))
phone_card(3, "Phone", "Still full", (L[6].start, CHIMES[1]))
phone_card(4, "Storage", "Delete Wedding.mp4?", (CHIMES[1], L[9].start))
phone_card(5, "Camera", "● Recording", (L[9].start, FLUTTER + 1.0))
phone_card(6, "Wife", "Send me Wedding.mp4?", (CHIMES[2], DURATION))

specs = []
for i, p in enumerate(t.phrases):
    until = t.phrases[i + 1].start - 0.02 if i + 1 < len(t.phrases) else REACTION + 0.2
    specs.append((p.start - 0.05, until, p.caption, f"dialogue-{i + 1}"))
spoken = ep.captions(
    specs, x=80, y=1240, width=840, highlights={"dialogue-8": [("Delete your\n", False), ("wedding video?", True)]}
)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-flip", FLIP, "The backflip"), ("marker-standoff", STARE, "The standoff")])
ep.instagram(POSTS["storage-full"])
ep.finish()

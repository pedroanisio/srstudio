#!/usr/bin/env python3
"""Comedy Cut 21 — The Cactus, built with srstudio: the signature cactus finally performs (ADR 0039).

    python3 the_cactus_audio.py PROJECT --key-stdin < key   # generated clips, resolved and pinned by the engine
    python3 the_cactus.py PROJECT                            # → PROJECT/the-cactus.scene.xml

The potted cactus that has signed every video since *Five Years* (ADR 0001) is noticed at last. "Has this always
been here?" "It came with the chair." In the café it is by the coffee Ava sets down, and its flower turns toward
them: "Is that yours?" "I thought it was yours." Milo flees to the park; it is already on the bench, and the pigeon
leaves. Back in the office the executive chair creaks round, and the cactus is in it. "...No." The push-in on its
pot: "S-R... one-oh-two-eight?" "That's its employee number." The interviewer sits in the applicant's chair: "So...
where do you see yourself in five years?" It blooms. Hard cut.

Every shot shows exactly one cactus: each location hands its own signature cactus to this episode through its
``cactus=`` slot (:func:`srstudio.signature.home_cactus`), and every hand-off draws the same performer, one
:class:`srstudio.signature.Act` on the episode's clock, so its flower and bloom match across the cuts. Departures
from the backlog script, accepted by the orchestrator on 2026-10-29: the office set has no door, so the
interviewer's return is the creak of the chair, not a door shutting; there is no tip-jar prop, so the cactus sits
on the counter beside the coffee Ava sets down; the last question is asked from the applicant's chair with the
cactus over his shoulder, then the cut to the cactus in the executive chair for the bloom. The candidate is heard,
not seen, over the push-in: the code fills the frame. While the push-in moves, the papers' code on the desk crosses
the bottom edge for a few frames, whole before it and off frame while the push holds (accepted: motion, not a hold).

Every set's lettering is framed fully inside the vertical safe area or left out: the café is held wide, its menu
inside the safe area; the park is framed closer, about the bench, and drawn with ``sign_lettering=False``, because
the sign is off frame at the park framing, and SA01 measures text layers off frame too (the sign's board and the
park's signature code stay). The picture keys on the takes' own words (:func:`srstudio.interview.said`), the
effects and the cuts.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import OFFICE, Episode, EpisodeSpec, camera, cast, graphics, layout, locations, props, signature
from srstudio.interview import said
from the_cactus_audio import PUSH_TO, PUSH_Y, SEAT, SWING

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="the-cactus",
        number="21",
        title="The Cactus — Comedy Cut 21",
        description="Office and café comedy: the potted cactus that has been in every video since Five Years "
        "follows the cast from the office to the café to the park, and ends up in the executive chair. Native "
        "vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        seed=21041,
        background="#D5DFDF",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # every set's lettering framed fully inside it or fully off frame
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
CAFE_AT, CUP, TURN, PARK, FLUTTER = t.cafe_start, t.cup_start, t.turn_start, t.park_start, t.flutter_start
CHAIR, SWIVEL, PUSH, SIT, BLOOM = t.chair_start, t.swivel_start, t.push_start, t.sit_start, t.bloom_start
REACTION, DURATION = t.reaction, t.duration
FLOWER = -24  # degrees: the flower leans toward whoever it is looking at (negative: to the left)
THIS = said(ep.root, P(0), "this")  # "Has this always been here?"
NO = said(ep.root, P(5), "No")

ACT = signature.Act(
    end=DURATION,
    turn=(
        (THIS + 0.20, 0),
        (THIS + 0.70, FLOWER / 2),  # a first small turn toward him: it's alive
        (TURN, FLOWER / 2),
        (TURN + 0.60, FLOWER),  # toward Ava and Milo, as they stare
        (SWIVEL + SWING, FLOWER),
        (SWIVEL + SWING + 0.50, -FLOWER),  # toward the interviewer as the chair faces him
        (REACTION, -FLOWER),
        (REACTION + 0.30, 0),  # upright for the bloom
    ),
    bloom=BLOOM,
)


def performer(x: float, y: float, scale: float, into=None):
    """The one cactus of a shot, handed over by its location (ADR 0039); ``into`` is a group made before it."""
    return lambda g: signature.cactus(cv, into if into is not None else g, x, y, scale, act=ACT)


def close(at, scale, to=(540, 800)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


# -- 1. the office, wide: he looks up from the CV at the cactus on his desk ----------------------------------------
manager = cast.Manager(cv)
wide = ep.setup(
    locations.office_wide,
    t.shots({"wide"}),
    at_desk=lambda g: ep.perform(
        manager,
        g,
        560,
        724,
        1.45,
        arms="articulated",
        blinks=[(0.45, 0.59), (P(0).end + 0.15, P(0).end + 0.29)],
        nods=[(0, 6), (0.35, 6), (0.65, -2), (THIS, -2), (THIS + 0.25, 5)],  # up from the CV, then over to it
        brows=([(0, 0), (THIS, 0), (THIS + 0.2, 9)], [(0, 0), (THIS, 0), (THIS + 0.2, -9)]),
        pupils=[(0, -18), (0.6, -18), (0.75, -31), (THIS, -31), (THIS + 0.15, -16)],  # down at it
    ),
    cactus=performer(735, 1205, 1.6),  # big enough to read on a phone before the push
)
cv.keys(manager.eyes, "x", [(0, 0), (THIS, 0), (THIS + 0.15, 20)], hold=False)  # on "this": at the cactus
camera.anchor(wide, 700, 1080, place=True)
for axis in ("scaleX", "scaleY"):  # the push onto him and the cactus as he asks
    cv.keys(wide, axis, [(0, 1.0), (THIS, 1.0), (THIS + 0.9, 1.45)], kind="sine-in-out")
cv.keys(wide, "y", [(0, 1080), (THIS, 1080), (THIS + 0.9, 1050)], kind="sine-in-out")  # its pot above the captions

# -- 2. the reverse: the applicant knows exactly where it came from -------------------------------------------------
candidate = cast.Candidate(cv)
reverse = ep.setup(
    locations.office_reverse,
    t.shots({"candidate"}),
    in_chair=lambda g: ep.perform(
        candidate,
        g,
        540,
        737,
        2.07,
        smile=[(P(1).end + 0.05, P(1).end + 0.8)],
        blinks=[(P(1).start - 0.12, P(1).start + 0.02)],
        nods=[(0, 0), (P(1).start, 0), (P(1).start + 0.25, -3), (P(1).end, 0)],
    ),
    cactus=performer(150, 1620, 0.9),  # on the near desk, below the captions
)
cv.keys(candidate.eyes, "x", [(0, 0), (P(1).start, 0), (P(1).start + 0.2, -11)], hold=False)  # down at the cactus

# -- 3. the café: the coffee lands beside it, and its flower turns toward them --------------------------------------
AVA_AT, MILO_AT = (760, 800, 1.35), (230, 1035, 1.53)
COUNTER_TOP = 1236  # the counter's surface, where the cup and the cactus stand
ava, milo = cast.Barista(cv), cast.Customer(cv)


def on_counter(g):
    cup = props.coffee_cup(cv, g, 600, 1187, 1.0)
    cv.gate(cup, [(CUP - 0.25, DURATION)])
    cv.keys(cup, "y", [(CUP - 0.25, 1120), (CUP, 1187)], hold=False)


cafe = ep.setup(
    locations.cafe,
    t.shots({"cafe"}),
    behind_counter=lambda g: ep.perform(
        ava,
        g,
        *AVA_AT,
        name=None,
        mouth=ep.mouth("ava"),
        blinks=[(P(2).end + 0.10, P(2).end + 0.24)],
        nods=[(0, 0), (CUP, 0), (CUP + 0.3, 6), (P(3).start, 6), (P(3).start + 0.3, -3)],  # down at it, then at him
    ),
    on_counter=on_counter,
    at_counter=lambda g: ep.perform(
        milo,
        g,
        *MILO_AT,
        mouth=ep.mouth("milo"),
        blinks=[(TURN + 0.70, TURN + 1.00)],  # the flower turns; a slow blink
        nods=[(0, 0), (P(2).start, 0), (P(2).start + 0.3, 4), (P(3).end, 4), (P(3).end + 0.3, -5)],
    ),
    cactus=performer(450, COUNTER_TOP, 1.1),
)

# -- 4. the park: it is on the bench before him; the pigeon looks at it and leaves ----------------------------------
SEATED = 1.25
glance = PARK + 0.30  # Milo's first look at the cactus beside him, then the double take, before "I bought a coffee!"
MILO_BENCH = (330, locations.park_seat_y(300, SEATED), SEATED)  # the seated café rig ends its torso at 300
BIRD = (640, 1500, 0.9)  # on the path in front of the bench, facing the cactus
PARK_FRAME = 1.4  # about the bench's left end: the park sign (x 785 and right) lands past x 1080
milo_park = cast.Customer(cv, seated=True)


def pigeon(g):
    x, y, s = BIRD
    away = cv.group(g, "pigeon-leaving")
    cv.gate(away, [(0, FLUTTER + 1.2)])
    cv.keys(away, "y", [(FLUTTER, 0), (FLUTTER + 1.1, -1000)], kind="sine-in")  # up past the bench, on camera
    cv.keys(away, "x", [(FLUTTER, 0), (FLUTTER + 1.1, 260)], kind="sine-in")
    nods = [(0, 0), (PARK + 0.6, 0), (PARK + 0.75, 18), (PARK + 1.3, 18), (PARK + 1.45, 0)]  # a look at the cactus
    cast.pigeon(cv, away, x, y, s, flip=True, nods=nods, id="park-pigeon")


park = ep.setup(
    locations.park,
    t.shots({"park"}),
    on_bench=lambda g: ep.perform(
        milo_park,
        g,
        *MILO_BENCH,
        mouth=ep.mouth("milo"),
        blinks=[(FLUTTER + 0.3, FLUTTER + 0.44)],
        nods=[(0, -6), (glance + 0.55, -6), (glance + 0.65, 9), (P(4).end, 9), (P(4).end + 0.3, -4)],  # the snap
    ),
    beside_bench=pigeon,
    cactus=performer(560, 1270, 1.0),
    sign_lettering=False,  # the sign is off frame at PARK_FRAME, and SA01 measures text layers off frame too
)
cv.keys(milo_park.eyes, "x", [(0, 0), (glance, 0), (glance + 0.12, 13), (glance + 0.30, 13), (glance + 0.40, 0),
                              (glance + 0.55, 0), (glance + 0.65, 15)], hold=False)  # fmt: skip  # the double take
camera.anchor(park, 0, 1268, place=True)
for axis in ("scaleX", "scaleY"):
    cv.keys(park, axis, [(0, PARK_FRAME)])

# -- 5. the executive chair creaks round with the cactus in it; the push-in on its pot; the bloom -------------------
CODE_AT = (SEAT[0], SEAT[1] + (-30 + signature.POT_CODE / 2) * SEAT[2])  # the code's centre, the push's fixed point
holder: dict = {}


def executive_chair(g):
    turn = cv.group(g, "executive-turn")
    camera.anchor(turn, SEAT[0], 900, place=True)
    front, back = cv.group(turn, "executive-turn-front"), cv.group(turn, "executive-turn-back")
    props.chair(cv, front)
    props.chair_back(cv, back, head=None)
    holder["front"] = front  # the cactus is drawn into the chair by the location's hand-off, at its own depth
    middle = SWIVEL + SWING / 2
    cv.keys(turn, "scaleX", [(0, 1), (SWIVEL, 1), (middle, camera.EDGE_ON), (SWIVEL + SWING, 1)], kind="sine-in-out")
    cv.keys(front, "opacity", [(0, 0), (middle, 1)])
    cv.keys(back, "opacity", [(0, 1), (middle, 0)])


desk = ep.setup(
    locations.office_desk,
    t.shots({"chair", "code", "bloom"}),
    chair=False,
    behind_desk=executive_chair,
    cactus=lambda g: signature.cactus(cv, holder["front"], *SEAT, act=ACT),
)
camera.anchor(desk, *CODE_AT, place=True)
cv.keys(desk, "y", [(0, CODE_AT[1]), (PUSH, PUSH_Y), (REACTION, CODE_AT[1])])  # hold keys: on the cuts
cv.keys(
    desk,
    "scaleX",
    framing := [
        (0, 1.0),
        (PUSH - 0.001, 1.0),
        (PUSH, 1.8),
        (PUSH + 1.4, PUSH_TO),  # the slow push until the code fills the frame
        (REACTION - 0.001, PUSH_TO),
        (REACTION, 1.5),  # the bloom, framed on the cactus in the chair
    ],
    kind="sine-in-out",
)
cv.keys(desk, "scaleY", framing, kind="sine-in-out")

# -- 6. the reverse again: he says "No." standing, then sits in the applicant's chair to ask it ---------------------
standing, seated = cast.Manager(cv, tag="manager-standing"), cast.Manager(cv, tag="manager-applicant")


def interviewer(g):
    up = cv.group(g, "interviewer-standing")
    cv.gate(up, [(0, SIT)])
    ep.perform(standing, up, 540, 560, 2.07, legs="standing", arms="articulated",
               blinks=[(P(5).end + 0.2, P(5).end + 0.34)], nods=[(0, 0), (NO, 0), (NO + 0.2, -4)],
               brows=([(0, 0), (NO - 0.35, 0), (NO - 0.2, 12)],
                      [(0, 0), (NO - 0.35, 0), (NO - 0.2, -12)]),  # raised clear of the popped eyes
               pupils=[(0, -31), (NO - 0.35, -31), (NO - 0.2, -36)])  # fmt: skip
    for axis in ("scaleX", "scaleY"):  # the widest the rig goes: eyes popped as he sees it
        cv.keys(standing.eyes, axis, [(0, 1.0), (NO - 0.35, 1.0), (NO - 0.2, 1.10)], hold=False)
    down = cv.group(g, "interviewer-applicant")
    cv.gate(down, [(SIT, DURATION)])
    ep.perform(seated, down, 540, 737, 2.07, arms="articulated", pupils=[(0, -31)],
               blinks=[(SIT + 0.3, SIT + 0.44)], nods=[(0, 0), (P(8).start, 0), (P(8).start + 0.3, 3)],
               brows=([(0, 0), (P(8).start + 0.4, 6)], [(0, 0), (P(8).start + 0.4, -6)]))  # fmt: skip


applicant = ep.setup(
    locations.office_reverse,
    t.shots({"manager", "applicant"}),
    id="applicant-reverse-angle",
    in_chair=interviewer,
    cactus=performer(200, 2150, 4.0),  # over its shoulder: the cactus in the executive chair, nearest the lens
)
camera.reframe(cv, applicant, [(c.time, *close((540, 640), 1.9)) if c.angle == "manager" else (c.time, 1.0, 0, 0)
                               for c in t.cuts if c.angle in ("manager", "applicant")])  # fmt: skip

hook = graphics.location_slate(
    cv, ep.comp, "THE CACTUS", show=(0, P(1).start - 0.1), x=90, y=235, id="hook-slate", text_id="hook-title"
)
specs = []
for i, p in enumerate(t.phrases):
    nxt = t.phrases[i + 1].start - 0.02 if i + 1 < len(t.phrases) else REACTION
    cut = min((c.time for c in t.cuts if c.time > p.end), default=REACTION)
    specs.append((max(0.0, p.start - 0.05), min(nxt, cut), p.caption, f"dialogue-{i + 1}"))  # off on the next cut
spoken = ep.captions(
    specs,
    x=80,
    y=1240,
    width=840,
    highlights={
        "dialogue-2": [("It came with ", False), ("the chair.", True)],
        "dialogue-8": [("That's its\n", False), ("employee number.", True)],
        "dialogue-9": [("So… where do you see\nyourself in ", False), ("five years?", True)],
    },
)
ep.hide_on_cover(hook, *spoken)
ep.markers(
    extra=[
        ("marker-cafe", CAFE_AT, "The café: it is by the coffee"),
        ("marker-park", PARK, "The park: it is on the bench"),
        ("marker-chair", SWIVEL, "The executive chair turns"),
        ("marker-code", PUSH, "SR-1028"),
        ("marker-bloom", BLOOM, "It blooms"),
    ]
)
ep.instagram(POSTS["the-cactus"])
out = ep.finish()
ep.check_overlays(out, [hook.id])

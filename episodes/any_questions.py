#!/usr/bin/env python3
"""Any Questions, built with srstudio: the interview's last question, and the one nobody asks.

    srstudio record any-questions PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build any-questions PROJECT    # → PROJECT/any-questions.scene.xml

A slow push: the manager tall behind the desk, the candidate small in front of it. "Do you have any questions for us?"
"Just one. Are you happy here?" The smile holds, and goes on one side only. A clock. "We have free fruit." "When was
your last vacation?" "What year is it?" The candidate slides the water across, the manager drinks with both hands.
"It's just bananas. Since March." Cut: same room, the chairs swapped, the manager small, the tie down. "What's your
greatest weakness?" "I stayed." The folder shuts. "We'll be in touch." A slow push on the small man. "Will you?"

The camera moves from the first frame (arm B of the ``sp-hook_motion`` test), the first line at 0.5 s. No music: the
clock, the glass and the folder are foley synthesized here. It declares no engine safe area, so captions are placed
inside x 80–920 by hand.
"""

import os

from _common import project_root
from any_questions_audio import INTERVIEW
from instagram_posts import POSTS
from srstudio import OFFICE, Episode, EpisodeSpec, cast, cutout_handed, cutout_hiring, foley, locations, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="any-questions",
        title=INTERVIEW.title,
        description="Job-hunting comedy: asked if he has any questions, a candidate asks the only honest one, and the "
        "two of them end up in each other's chairs. Native vector animation; ElevenLabs dialogue, synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=31212,
        background="#66798B",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
t, cv = ep.t, ep.cv
FALL, GONE = float(t.meta["fall"]), float(t.meta["smile_gone"])
SLIDE, DRINK, DRUNK = float(t.meta["slide"]), float(t.meta["drink"]), float(t.meta["drunk"])
SWAP, CLOSES, STANDS = float(t.meta["swap"]), float(t.meta["closes"]), float(t.meta["stands"])
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
EPS = 1 / 120
TALL = (420, 470, 2.2)  # whoever holds the desk: the elbows sit on its edge, so the arms end there
SEEN_LOW = (540, 737, 2.07)  # the candidate in the gray chair
SUNK = (540, 972, 1.46)  # the manager in the same chair: smaller, and lower in it
FOLDER = (640, 1230)

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))

ticks = [L[1].end + 0.2 + 0.5 * n for n in range(int((L[2].start - L[1].end - 0.3) / 0.5))]
foley.write_bursts(ROOT / "assets" / "tick.wav", ticks, DURATION, foley.REMOTE_CLICK, seed=31213)
foley.write_bursts(ROOT / "assets" / "slide.wav", [SLIDE + 0.05], DURATION, foley.SCRAPE, seed=31214)
foley.write_bursts(ROOT / "assets" / "shut.wav", [CLOSES], DURATION, foley.THUD, seed=31215)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("tick", "assets/tick.wav", {"role": "effects", "gain": -8}),
        ("slide", "assets/slide.wav", {"role": "effects", "gain": -6}),
        ("shut", "assets/shut.wav", {"role": "effects", "gain": -7}),
    ],
    loudness="-14",
)


def manager_at_desk(g):
    """The tall one. The smile is held through the question, and goes on one side only at ``GONE``."""
    cv.gate(g, spans["desk"])
    who = cast.Manager(cv, tag="boss-character")
    states = ep.mouth("manager", smile=[(0.0, L[0].start), (L[0].end, GONE)])
    mouth = [(at, "gone" if GONE <= at < L[2].start else state) for at, state in states]
    ep.perform(
        who,
        g,
        *TALL,
        mouth=mouth,
        blinks=[(L[0].end + 0.5, L[0].end + 0.64), (GONE + 0.2, GONE + 0.34), (L[4].end + 0.05, L[4].end + 0.19)],
        nods=[(0, 0), (L[0].start, 0), (L[0].start + 0.3, 3), (L[0].end, 0), (GONE, 0), (GONE + 0.3, -3),
              (L[2].start + 0.3, -3), (L[3].end, 0), (L[4].start + 0.3, -6), (DRINK, 0), (L[6].start + 0.3, 6)],
        brows=(
            [(0, 0), (GONE, 0), (GONE + 0.2, 6), (L[6].start, 6), (L[6].end, 10)],
            [(0, 0), (GONE, 0), (GONE + 0.2, -3), (L[6].start, -3), (L[6].end, -6)],
        ),
    )  # fmt: skip
    half = cv.group(who.head, "half-smile")
    cv.gate(half, [(GONE, L[2].start)])
    cv.path(half, "M-23 37 Q-6 58 8 50 Q16 47 24 52", stroke=cv.ink, sw=3.6)
    held = cv.group(who.group, "drinking")  # in his own units: a glass to the mouth, a hand on each side
    cv.gate(held, [(DRINK, DRUNK)])
    cv.keys(held, "y", [(DRINK, 150.0), (DRINK + 0.3, 0.0), (DRUNK - 0.2, 0.0), (DRUNK, 150.0)], hold=False)
    cv.path(held, "M-87 235 L-42 96 M87 235 L42 96", stroke=cv.ink, sw=5)
    cv.path(held, "M-30 14 L-24 110 Q0 118 24 110 L30 14Z", "#E3E8E1", cv.ink, 3)
    cv.path(held, "M-28 40 Q0 50 28 40 L24 106 Q0 114 -24 106Z", "#9FC0CA", "#557480", 1.5, opacity=0.75)
    cv.ellipse(held, -30, 6, 60, 16, "#E4E9E4", cv.ink, 2)
    cv.ellipse(held, -56, 58, 34, 44, cv.white, cv.ink, 2.5)
    cv.ellipse(held, 22, 58, 34, 44, cv.white, cv.ink, 2.5)


def candidate_at_desk(g):
    """The same place, the same size: he reads the folder, shuts it, and is up before his line."""
    cv.gate(g, spans["desk-after"])
    who = cast.Candidate(cv, tag="desk-character")
    node = ep.perform(
        who,
        g,
        *TALL,
        mouth=ep.mouth("candidate"),
        blinks=[(SWAP + 0.5, SWAP + 0.64), (CLOSES + 0.3, CLOSES + 0.44)],
        nods=[(0, 3), (L[7].start, 3), (L[7].start + 0.3, -2), (L[7].end, 3), (STANDS, 0)],
    )
    cv.keys(who.eyes, "y", [(0, 12), (L[7].start, 12), (L[7].start + 0.1, 0), (L[7].end, 0), (L[7].end + 0.1, 12),
                            (STANDS, 12), (STANDS + 0.1, 0)], hold=False)  # fmt: skip
    cv.keys(node, "y", [(0, TALL[1]), (STANDS, TALL[1]), (STANDS + 0.3, TALL[1] - 130)], hold=False)


def on_desk(g):
    cutout_handed.cv_folder(cv, g, *FOLDER, open_spans=[(SWAP, CLOSES)], scale=1.0)
    before = cv.group(g, "candidate-low", y=590, x=-40, scaleX=0.72, scaleY=0.72)
    cv.gate(before, spans["desk"])
    props.candidate_back(cv, before)
    cv.path(before, "M600 1330 L840 1300 L880 1610 L640 1640Z", "#FBFAF2", cv.ink, 5)  # his list
    for k in range(4):
        cv.line(before, 650, 1380 + k * 62, 830, 1356 + k * 62, "#8C8C8C", 11)
    cv.ellipse(before, 570, 1560, 110, 120, cv.white, cv.ink, 5)


def behind_desk(g):
    manager_at_desk(cv.group(g, "before-the-swap"))
    candidate_at_desk(cv.group(g, "after-the-swap"))


def in_chair(g):
    low = cv.group(g, "candidate-in-the-chair")
    cv.gate(low, spans["chair"])
    ep.perform(
        cast.Candidate(cv, tag="low-character"),
        low,
        *SEEN_LOW,
        mouth=ep.mouth("candidate"),
        blinks=[(L[1].end - 0.1, L[1].end + 0.04), (L[3].end - 0.1, L[3].end + 0.04)],
        nods=[(0, 0), (L[1].start + 0.5, 0), (L[1].start + 0.8, 3), (L[3].start, 3), (L[3].start + 0.3, 0)],
    )
    sunk = cv.group(g, "manager-in-the-chair")
    cv.gate(sunk, spans["chair-after"])
    ep.perform(
        cast.Manager(cv, tag="sunk-character"),
        sunk,
        *SUNK,
        mouth=ep.mouth("manager"),
        blinks=[(L[8].end + 0.3, L[8].end + 0.5)],
        nods=[(0, 6), (L[8].start, 6), (L[8].start + 0.3, 2), (L[10].start, 2), (L[10].start + 0.3, -4)],
        tie="loose",
    )


finish = locations.finish(cv, ep.comp)
office = cutout_hiring.hiring_office(cv, finish, behind_desk=behind_desk, on_desk=on_desk,
                                     shots=spans["desk"] + spans["desk-after"])  # fmt: skip
backing = cv.group(finish, "backing")  # the frame's edge, where the wall's blur thins out
cv.gate(backing, spans["chair"] + spans["chair-after"])
cv.rect(backing, -10, -10, 1100, 1940, props.office_paints(cv)["warm_wall"])
reverse = locations.office_reverse(cv, finish, in_chair=in_chair, shots=spans["chair"] + spans["chair-after"], depth=6)

glass = cv.group(finish, "glass-crossing")  # it comes off the candidate's side of the desk, towards the lens
cv.gate(glass, [(SLIDE, DRINK)])
cv.keys(glass, "x", [(SLIDE, -470.0), (DRINK, -640.0)], hold=False)
cv.keys(glass, "y", [(SLIDE, 0.0), (DRINK, 300.0)], hold=False)
cv.keys(glass, "scaleX", [(SLIDE, 1.0), (DRINK, 1.5)], hold=False)
cv.keys(glass, "scaleY", [(SLIDE, 1.0), (DRINK, 1.5)], hold=False)
props.water_glass(cv, glass)

# The camera: moving from the first frame, one slow push on the manager through the hold, and it stays there until the
# chairs swap.
at, size = (TALL[0], TALL[1] + 40), 1.32
x, y = 540 - at[0] * size, 700 - at[1] * size
EARLY = 0.14  # how much of the push is done by the fall of the smile: the first, slow part
for prop, values in (
    ("scaleX", [(0.0, 1.0), (FALL, 1 + (size - 1) * EARLY), (L[2].start, size), (SWAP - EPS, size), (SWAP, 1.0)]),
    ("scaleY", [(0.0, 1.0), (FALL, 1 + (size - 1) * EARLY), (L[2].start, size), (SWAP - EPS, size), (SWAP, 1.0)]),
    ("x", [(0.0, 0.0), (FALL, x * EARLY), (L[2].start, x), (SWAP - EPS, x), (SWAP, 0.0)]),
    ("y", [(0.0, 0.0), (FALL, y * EARLY), (L[2].start, y), (SWAP - EPS, y), (SWAP, 0.0)]),
):
    cv.keys(office, prop, values, hold=False)
PUSH = (SUNK[0], SUNK[1] + 40)
LAST = spans["chair-after"][-1][0]
for prop, values in (
    ("scaleX", [(0.0, 1.0), (LAST, 1.0), (DURATION, 1.22)]),
    ("scaleY", [(0.0, 1.0), (LAST, 1.0), (DURATION, 1.22)]),
    ("x", [(0.0, 0.0), (LAST, 0.0), (DURATION, PUSH[0] * -0.22)]),
    ("y", [(0.0, 0.0), (LAST, 0.0), (DURATION, PUSH[1] * -0.22)]),
):
    cv.keys(reverse, prop, values, hold=False)

spoken = ep.captions(ep.spoken_captions(), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-smile", GONE, "The smile"), ("marker-swap", SWAP, "The swap")])
ep.instagram(POSTS["any-questions"])
ep.finish()

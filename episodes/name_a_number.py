#!/usr/bin/env python3
"""Comedy Cut 24 — Name a Number, built with srstudio: the salary talk, where whoever names a number first loses.

    srstudio record name-a-number PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build name-a-number PROJECT    # → PROJECT/name-a-number.scene.xml

The job ad on the desk: "Salary: competitive." "So. What number did you have in mind?" "What's the range?" "What would
make you happy?" "What would make you happy?" "I asked first." "The ad said competitive." "Extremely competitive."
"Competitive with what?" "Other ads." "Tell you what. We both write it down." Two pens scribble; two papers slap face
up: the offer says LESS THAN YOURS, the ask says MORE THAN YOURS. "Great. We're aligned." "Are we?"
"Competitively."

The first second is still (arm A of the ``sp-hook_motion`` test): the ad lies on the desk, drawn still, and the
interviewer's question is heard over it from :data:`name_a_number_audio.LEAD`, its caption no earlier than 1.0 s.
The office angles blur their far wall (``depth=``) under the Cutout grade (``locations.finish``); the inserts take
one light from the top left, with each sheet's shadow falling down and to the right.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from name_a_number_audio import INTERVIEW
from srstudio import Episode, EpisodeSpec, cast, layout, locations, look, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="name-a-number",
        number="24",
        title="Name a Number — Comedy Cut 24",
        description="Interview comedy: a salary talk where neither side will name a number first, until both write "
        "one down. Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        **iv_audio.spec_font(INTERVIEW.font, project_root(__file__)),  # the pinned Google caption face
        seed=24052,
        background="#D5DFDF",
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # text and captions held inside x 80–920, y 220–1420 by the engine
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv = ep.t, ep.cv
SCRIBBLE, FLIP, REACTION, DURATION = t.scribble_start, t.flip_start, t.reaction, t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
DEPTH = 4.0  # px of blur on the office's far wall
MANAGER_AT, CANDIDATE_AT = (560, 724, 1.45), (540, 737, 2.07)
EPS = 0.001
DESK, GRAIN, PAPER, INK = "#B9875A", "#A47548", "#FBF8EF", "#2C2A26"
SHADE = "#3B2A1E"  # every shadow: the one light is top left, so shadows fall down and to the right
world = locations.finish(cv, ep.comp)  # the Cutout grade over every angle; the camera moves inside it


def desk_insert(id: str, shots):
    """A close-up of the desk top: woodgrain, the light's warm pool from the top left."""
    g = cv.group(world, id)
    cv.gate(g, shots)
    cv.rect(g, 0, 0, 1080, 1920, DESK)
    props.woodgrain(cv, g, 0, 1920, 26)
    look.pool(cv, g, f"{id}-light", "#FFE9C2", -380, -420, 1300, 1300, opacity=0.55)
    look.fade(cv, g, f"{id}-foot", "#3B2A1E55", 1920, 1300, 1080)
    return g


def sheet(g, id: str, x, y, w, h, rotation, heading: str, body: str | None, *, lines: int = 6):
    """A sheet of paper centred on (x, y), its shadow down and to the right, a printed heading and, when given, a
    handwritten ``body``; returns its group."""
    s = cv.group(g, id, x=x, y=y, rotation=rotation)
    cv.rect(s, -w / 2 + 14, -h / 2 + 20, w, h, SHADE, radius=6, opacity=0.28)  # the contact shadow
    cv.rect(s, -w / 2, -h / 2, w, h, PAPER, cv.ink, 3, radius=4)
    cv.text(s, f"{id}-heading", heading, -w / 2 + 30, -h / 2 + 34, w - 60, 56, 40, "#5C625D", weight="700")
    cv.line(s, -w / 2 + 30, -h / 2 + 100, w / 2 - 30, -h / 2 + 100, "#9AA3A0", 3)
    if body is None:
        for k in range(lines):
            cv.line(
                s, -w / 2 + 34, -h / 2 + 140 + 34 * k, w / 2 - 34 - (k % 3) * 60, -h / 2 + 140 + 34 * k, "#C9CDCB", 6
            )
    else:
        cv.text(s, f"{id}-body", body, -w / 2 + 20, -h / 2 + 140, w - 40, 170, 56, "#1F3E8A", weight="700")
    return s


# -- the ad: still on the desk for the first second, his question over it -------------------------------------------
ad = desk_insert("shot-ad", t.shots({"ad"}))
ad_sheet = sheet(ad, "job-ad", 540, 700, 760, 820, -4, "NOW HIRING", None, lines=0)
cv.text(ad_sheet, "job-ad-role", "Senior Analyst", -330, -260, 660, 80, 62, INK, weight="700")
for k, w in enumerate((560, 600, 500, 580)):
    cv.line(ad_sheet, -300, -130 + 40 * k, -300 + w, -130 + 40 * k, "#C9CDCB", 7)
cv.rect(ad_sheet, -330, 60, 660, 150, "#FFF1A8", radius=8, opacity=0.9)  # someone highlighted it
cv.text(ad_sheet, "job-ad-salary", "Salary: competitive", -320, 85, 640, 100, 60, INK, weight="700")
pen = cv.group(ad, "ad-pen", x=300, y=1120, rotation=-28)
cv.rect(pen, 6, 8, 300, 22, SHADE, radius=11, opacity=0.25)
cv.rect(pen, 0, 0, 300, 22, "#24324A", cv.ink, 2.5, radius=11)
cv.rect(pen, 240, -4, 22, 30, "#C9CDCB", cv.ink, 2, radius=4)
cv.ellipse(ad, 772, 1690, 180, 44, SHADE, opacity=0.22)  # the mug's contact shadow, down and right
props.coffee_cup(cv, ad, 820, 1560, 2.4)


# -- the office: the interviewer behind the desk, the applicant's back in the foreground ----------------------------
def manager_slot(g):
    return ep.perform(
        cast.Manager(cv),
        g,
        *MANAGER_AT,
        smile=[(L[2].start, L[2].end + 0.2), (L[10].start, DURATION)],
        blinks=[
            (L[1].end + 0.05, L[1].end + 0.19),
            (L[3].end + 0.10, L[3].end + 0.40),  # the echo lands: a slow blink
            (L[7].end + 0.05, L[7].end + 0.19),
            (L[11].end + 0.05, L[11].end + 0.19),
        ],
        nods=[
            (0, 0),
            (L[2].start, 0),
            (L[2].start + 0.3, -4),  # warmly: what would make you happy
            (L[4].start, -4),
            (L[4].start + 0.25, 4),  # "I asked first": chin down
            (L[6].start, 4),
            (L[6].start + 0.3, -6),  # "Extremely competitive": chin up, proud
            (L[8].start, -6),
            (L[8].start + 0.25, 2),
            (SCRIBBLE, 2),
            (SCRIBBLE + 0.25, 12),  # head down, writing
            (FLIP - 0.1, 12),
            (FLIP + 0.1, 0),
            (L[10].start, 0),
            (L[10].start + 0.3, -4),
            (L[12].start, -4),
            (L[12].start + 0.35, 6),  # "Competitively": one satisfied nod
            (L[12].end + 0.3, -2),
        ],
        arms="articulated",
        brows=(
            [
                (0, 0),
                (L[4].start, 0),
                (L[4].start + 0.15, -7),
                (L[5].start, -7),
                (L[5].start + 0.2, 0),
                (L[11].start, 0),
                (L[11].start + 0.15, 8),
                (L[12].end, 8),
            ],
            [
                (0, 0),
                (L[4].start, 0),
                (L[4].start + 0.15, 7),
                (L[5].start, 7),
                (L[5].start + 0.2, 0),
                (L[11].start, 0),
                (L[11].start + 0.15, -8),
                (L[12].end, -8),
            ],
        ),  # fmt: skip
        pupils=[(0, -31), (SCRIBBLE, -31), (SCRIBBLE + 0.2, -10), (FLIP, -10), (FLIP + 0.2, -31)],
    )


office = locations.office_wide(cv, world, at_desk=manager_slot, shots=t.shots({"manager", "wide"}), depth=DEPTH)


def framing(at, scale, to):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


WIDE = (1.0, 0.0, 0.0)
CLOSE = framing(MANAGER_AT[:2], 1.55, (540, 820))
PUSH = framing((560, 900), 1.18, (540, 880))  # the end: a slow push on the two of them
rows = [(c.time, *(CLOSE if c.angle == "manager" else WIDE)) for c in t.cuts if c.angle in {"manager", "wide"}]
for prop, column in [("scaleX", 1), ("scaleY", 1), ("x", 2), ("y", 3)]:
    values = [(0.0, rows[0][column])]
    for prev, row in zip(rows, rows[1:], strict=False):
        values += [(row[0] - EPS, prev[column]), (row[0], row[column])]
    last = rows[-1]
    values += [(REACTION, last[column]), (DURATION, PUSH[column - 1])]
    cv.keys(office, prop, values, hold=False)


# -- the reverse: the applicant -----------------------------------------------------------------------------------
def candidate_slot(g):
    candidate = cast.Candidate(cv)
    node = ep.perform(
        candidate,
        g,
        *CANDIDATE_AT,
        smile=[(L[3].start, L[3].end + 0.1), (L[5].start, L[5].end)],
        blinks=[
            (L[0].end + 0.40, L[0].end + 0.54),
            (L[4].end + 0.05, L[4].end + 0.19),
            (L[8].end + 0.10, L[8].end + 0.55),  # "Other ads.": the slow blink
            (L[10].end + 0.10, L[10].end + 0.24),
        ],
        nods=[
            (0, 0),
            (L[1].start, 0),
            (L[1].start + 0.25, -3),
            (L[3].start, -3),
            (L[3].start + 0.3, 3),  # the echo, sweetly
            (L[5].start, 3),
            (L[5].start + 0.3, -2),
            (L[7].start, -2),
            (L[7].start + 0.25, 5),  # "Competitive with what?"
            (L[11].start, 5),
            (L[11].start + 0.3, -4),  # "Are we?"
        ],
        arms="articulated",
        forearm=[(0, 0), (L[5].start + 0.2, 0), (L[5].start + 0.45, 180), (L[6].start, 180), (L[6].start + 0.2, 0)],
        pointing=[(L[5].start + 0.35, L[6].start)],
    )
    cv.keys(
        candidate.eyes,
        "x",
        [(0, 0), (L[7].start, 0), (L[7].start + 0.15, -9), (L[8].end + 0.2, -9), (L[8].end + 0.4, 0)],
        hold=False,
    )
    return node


reverse = locations.office_reverse(cv, world, in_chair=candidate_slot, shots=t.shots({"candidate"}), depth=DEPTH)

# -- the papers: slapped face up at the flip ----------------------------------------------------------------------
papers = desk_insert("shot-papers", t.shots({"papers"}))
offer = sheet(papers, "offer", 290, 660, 370, 520, -5, "OFFER", "LESS THAN\nYOURS")
ask = sheet(papers, "ask", 700, 690, 370, 520, 4, "MY ASK", "MORE THAN\nYOURS")
for s in (offer, ask):
    cv.keys(s, "scaleY", [(0, 0.03), (FLIP, 0.03), (FLIP + 0.10, 1.06), (FLIP + 0.18, 1.0)], hold=False)
for k, (x, r) in enumerate(((180, 20), (600, -16))):
    pen = cv.group(papers, f"papers-pen-{k}", x=x, y=1080, rotation=r)
    cv.rect(pen, 6, 8, 260, 20, SHADE, radius=10, opacity=0.25)
    cv.rect(pen, 0, 0, 260, 20, ("#24324A", "#8A2E2E")[k], cv.ink, 2.5, radius=10)

spoken = ep.captions(
    x=80,
    y=1240,
    width=840,
    highlights={"dialogue-9": [("Other ads.", True)], "dialogue-13": [("Competitively.", True)]},
)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-flip", FLIP, "The papers"), ("marker-end", L[12].start, "Competitively")])
ep.instagram(POSTS["name-a-number"])
ep.finish()

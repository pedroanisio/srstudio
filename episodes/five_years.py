#!/usr/bin/env python3
"""Episode 06 — Five Years, built with srstudio.

    python3 five_years_audio.py PROJECT --key-stdin < key   # generated clips, resolved and pinned by the engine
    python3 five_years.py PROJECT                            # → PROJECT/five-years.scene.xml

"Where do you see yourself in five years?" "In your chair." "Bold. You want my job?"
"No. Just the chair." The applicant's chair squeaks; the interviewer's does not. The end card
has the applicant spinning in the executive chair under a five-year plan.
"""

import os
import shutil
from pathlib import Path

from _common import project_root
from instagram_posts import POSTS
from srstudio import Episode, EpisodeSpec, camera, cast, graphics, layout, locations, props

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="five-years",
        number="06",
        title="Five Years — The Interview 06",
        description="Interview comedy: a squeaky chair, an ambitious answer and a spin in the executive chair. "
        "Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        seed=52028,
        background="#D5DFDF",
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # text and captions held inside x 80–920, y 220–1420 by the engine
    )
)
# Dialogue and effects as the engine resolved them (dialogue.json "clips"); mouths follow these clips.
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
REACTION, ENDING, DURATION = t.reaction, t.ending, t.duration
SQUEAK_SOFT, SQUEAK_LOUD, SPIN = t.squeak_soft_start, t.squeak_loud_start, t.spin_start
C = [c.time for c in t.cuts]
WIDE = t.shots({"wide", "manager-reaction"})
CLOSE = t.shots({"candidate", "candidate-punchline"})
END = t.shots({"candidate-ending"})
FX = {s.name: s for s in t.sound_effects}

# -- wide: the interviewer asks, raises his brows at "In your chair", then freezes -----------------------
manager = cast.Manager(cv)
wide = ep.setup(
    locations.office_wide,
    WIDE,
    at_desk=lambda g: ep.perform(
        manager,
        g,
        560,
        724,
        1.45,
        blinks=[
            (P(0).start - 0.30, P(0).start - 0.16),
            (P(2).end + 0.10, P(2).end + 0.24),
            (REACTION + 0.42, REACTION + 0.78),
        ],  # a slow, deadpan blink
        nods=[
            (0, 0),
            (P(2).start - 0.05, 0),
            (P(2).start + 0.30, 5),
            (P(2).end, 5),
            (P(2).end + 0.2, 2),
            (REACTION, 2),
            (REACTION + 0.35, -6),
        ],  # leans back, then tilts
        arms="articulated",
        brows=(
            [(0, 0), (P(2).start - 0.1, 0), (P(2).start + 0.15, 9), (P(2).end, 9), (REACTION, 2), (REACTION + 0.3, -6)],
            [
                (0, 0),
                (P(2).start - 0.1, 0),
                (P(2).start + 0.15, -9),
                (P(2).end, -9),
                (REACTION, -2),
                (REACTION + 0.3, 6),
            ],
        ),
        pupils=[(0, -31), (REACTION, -31), (REACTION + 0.25, -22)],
    ),
)
camera.anchor(wide, 560, 724)
camera.push_in(
    cv,
    wide,
    x=[(0, 560), (REACTION, 540)],
    y=[(0, 724), (REACTION, 850)],
    scale=[(0, 1), (REACTION - 0.001, 1), (REACTION, 1.62), (REACTION + 0.9, 1.74)],
)
# The applicant's chair squeaks in the foreground before anyone speaks.
graphics.squeak_mark(
    cv,
    ep.comp,
    "squeak",
    show=(SQUEAK_SOFT, SQUEAK_SOFT + FX["chair-squeak"].duration + 0.08),
    x=330,
    y=1320,
    w=300,
    h=90,
    size=50,
    rotation=-10,
    id="squeak-soft",
)

# -- close: the applicant answers, eyes on the boss's chair; his own chair betrays him -------------------
candidate = cast.Candidate(cv)
close = ep.setup(
    locations.office_reverse,
    CLOSE,
    in_chair=lambda g: ep.perform(
        candidate,
        g,
        540,
        737,
        2.07,
        smile=[(P(1).end + 0.04, C[2]), (P(3).end + 0.04, REACTION)],
        blinks=[(P(1).start - 0.12, P(1).start + 0.02), (SQUEAK_LOUD - 0.10, SQUEAK_LOUD + 0.06)],
        nods=[
            (0, 0),
            (P(1).start, 0),
            (P(1).start + 0.25, -3),
            (P(1).end, 0),
            (P(3).start, 0),
            (P(3).start + 0.25, 3),
            (P(3).end, 4),
        ],
        arms="articulated",
        forearm=[(0, 0), (P(3).start + 0.30, 0), (P(3).start + 0.55, 180), (REACTION, 180)],
        pointing=[(P(3).start + 0.45, REACTION)],
    ),
)
# His eyes slide toward the interviewer's chair while he says it.
cv.keys(
    candidate.eyes,
    "x",
    [(0, 0), (P(1).start + 0.05, 0), (P(1).start + 0.22, 11), (P(1).end + 0.30, 11), (P(1).end + 0.50, 0)],
    hold=False,
)
# The loud squeak jolts him in his seat.
cv.keys(
    candidate.group,
    "rotation",
    [
        (0, 0),
        (SQUEAK_LOUD, 0),
        (SQUEAK_LOUD + 0.05, -3),
        (SQUEAK_LOUD + 0.12, 2.5),
        (SQUEAK_LOUD + 0.20, -1.5),
        (SQUEAK_LOUD + 0.30, 0),
    ],
    hold=False,
)
camera.anchor(close, 540, 737, place=True)
camera.zoom_holds(cv, close, [(0, 1), (C[3], 1.07)])
graphics.squeak_mark(
    cv,
    ep.comp,
    "SQUEAK!",
    show=(SQUEAK_LOUD, SQUEAK_LOUD + FX["chair-squeak-loud"].duration + 0.10),
    x=640,
    y=1300,
    w=310,
    h=100,
    size=60,
    rotation=10,
    id="squeak-loud",
)


# -- end card: the applicant spins in the executive chair -------------------------------------------------
def spinning_chair(g):
    spinner = cv.group(g, "executive-spin")
    camera.anchor(spinner, 560, 900, place=True)
    front, back = cv.group(spinner, "executive-spin-front"), cv.group(spinner, "executive-spin-back")
    props.chair(cv, front)
    ep.perform(
        cast.Candidate(cv, tag="candidate-spin-character"),
        front,
        560,
        724,
        1.45,
        smile=[(0, DURATION)],
        blinks=[(ENDING + 2.10, ENDING + 2.24)],
    )
    props.chair_back(cv, back, head=(560, 724, 145))
    facing = camera.spin(cv, spinner, start=SPIN, turns=2, period=FX["swivel-spin"].duration / 2)
    camera.show_facing(cv, front, back, facing)


ep.setup(locations.office_desk, END, chair=False, behind_desk=spinning_chair)

graphics.episode_slate(cv, ep.comp, "06", "FIVE YEARS", x=90, y=235)
graphics.scorecard(
    cv,
    ep.comp,
    "FIVE-YEAR PLAN",
    [("JOB", "NO THANKS", "#E6AA92"), ("CHAIR", "ACQUIRED", "#AAD6BD")],
    show=(ENDING + 0.45, DURATION),
    x=90,
    y=235,
    w=820,
    prefix="plan",
)
ep.captions(
    x=80,
    y=1240,
    width=840,
    highlights={
        "dialogue-2": [("In your ", False), ("chair.", True)],
        "dialogue-4": [("No. Just ", False), ("the chair.", True)],
    },
)
ep.markers(extra=[("marker-squeak", SQUEAK_LOUD, "Loud squeak"), ("marker-spin", SPIN, "Executive spin")])
ep.instagram(POSTS["five-years"])
out = ep.finish()
# The engine does not measure vector graphics against the safe area; srstudio checks the overlays.
engine = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
if engine is None:
    raise SystemExit("no scene-render engine: set SRSTUDIO_ENGINE to check the overlays against the safe area")
OVERLAYS = ["episode-slate", "squeak-soft", "squeak-loud", "final-scorecard"]
layout.check_overlays(out, OVERLAYS, engine=Path(engine), strict=True)

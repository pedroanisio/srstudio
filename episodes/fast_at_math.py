#!/usr/bin/env python3
"""Episode 03 — Fast at Math, rebuilt with srstudio."""

from _common import VOICES_CREDIT, office_shots, project_root
from instagram_posts import POSTS
from srstudio import Episode, EpisodeSpec, camera, cast, graphics, locations

ep = Episode(
    EpisodeSpec(
        slug="fast-at-math",
        number="03",
        title="Fast at Math — The Interview 03",
        description=(
            "Enhanced workplace comedy: expressive vector characters, hand gestures, "
            "facepalm, math graphics, scorecard and original sound effects."
        ),
        signature=False,  # shipped before ADR 0001; the package must reproduce element for element
        root=project_root(__file__),
        seed=52023,
        background="#D5DFDF",
        audio_credit=VOICES_CREDIT,
    )
)
t, cv, P = ep.t, ep.cv, ep.P
REACTION, ENDING, DURATION = t.reaction, t.ending, t.duration
C = [c.time for c in t.cuts]
WIDE, CLOSE = office_shots(t)

# The manager behind the desk, articulated arm, raised brows and a facepalm on the reaction.
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
        blinks=[(P(2).start - 0.27, P(2).start - 0.12), (REACTION + 0.22, ENDING)],
        nods=[
            (0, 0),
            (P(4).start - 0.1, 0),
            (P(4).start + 0.24, -4),
            (P(5).start, 0),
            (REACTION, 0),
            (REACTION + 0.26, 5),
        ],
        arms="articulated",
        hide_right_arm_at=REACTION + 0.06,
        brows=(
            [(0, 0), (P(4).start - 0.1, 0), (P(4).start + 0.12, 8), (REACTION, 2)],
            [(0, 0), (P(4).start - 0.1, 0), (P(4).start + 0.12, -8), (REACTION, -2)],
        ),
        pupils=[(0, -31), (P(2).start - 0.1, -31), (P(2).start + 0.1, -25), (P(2).end, -25), (P(3).start, -31)],
        facepalm=(REACTION + 0.06, ENDING),
    ),
)
camera.anchor(wide, 560, 724)
camera.push_in(
    cv,
    wide,
    x=[(0, 560), (REACTION, 540)],
    y=[(0, 724), (REACTION, 850)],
    scale=[(0, 1), (REACTION - 0.001, 1), (REACTION, 1.62), (REACTION + 0.8, 1.72)],
)

# The candidate in the reverse angle; the forearm rotates at the elbow to raise one finger.
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
        smile=[(P(1).end + 0.03, C[2]), (P(3).end + 0.03, C[4]), (P(5).end + 0.03, DURATION)],
        blinks=[
            (P(1).start + 0.30, P(1).start + 0.45),
            (P(5).start - 0.23, P(5).start - 0.10),
            (ENDING + 0.65, ENDING + 0.80),
        ],
        nods=[
            (0, 0),
            (P(1).start, 0),
            (P(1).start + 0.25, -3),
            (P(1).end, 0),
            (P(3).start - 0.05, 0),
            (P(3).start + 0.12, -5),
            (P(3).end + 0.15, 0),
            (P(5).start, 0),
            (P(5).end, -4),
            (ENDING, -4),
            (ENDING + 0.35, 0),
        ],
        arms="articulated",
        forearm=[(0, 0), (P(5).start - 0.05, 0), (P(5).start + 0.22, 180), (REACTION, 180), (ENDING, 0)],
        pointing=[(P(5).start + 0.13, REACTION)],
    ),
)
camera.anchor(close, 540, 737, place=True)
camera.zoom_holds(cv, close, [(0, 1), (C[3], 1.10), (C[4], 1), (C[5], 1.04), (ENDING, 1)])

graphics.episode_slate(cv, ep.comp, "03", "FAST AT MATH")
graphics.quiz_card(
    cv,
    ep.comp,
    "QUICK MATH",
    "17 × 19 = ?",
    show=(P(2).start - 0.08, P(4).end + 0.12),
    verdict="NOPE.",
    verdict_span=(P(4).start - 0.21, P(4).end + 0.12),
)
graphics.answer_bubble(cv, ep.comp, "42!", show=(P(3).start - 0.015, P(4).start - 0.07))
graphics.scorecard(
    cv,
    ep.comp,
    "INTERVIEW SCORE",
    [("SPEED", "10 / 10", "#AAD6BD"), ("ACCURACY", "0 / 10", "#E6AA92")],
    show=(ENDING + 0.06, DURATION),
)
ep.captions(highlights={"dialogue-6": [("But it was ", False), ("fast.", True)]})
ep.audio()
ep.markers()
ep.instagram(POSTS["fast-at-math"])
ep.finish()

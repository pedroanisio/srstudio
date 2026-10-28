#!/usr/bin/env python3
"""Episode 02 — Pressure, rebuilt with srstudio."""

from _common import VOICES_CREDIT, office_shots, project_root
from instagram_posts import POSTS
from srstudio import Episode, EpisodeSpec, camera, cast, locations, props

ep = Episode(
    EpisodeSpec(
        slug="pressure-interview",
        number="02",
        title="How do you handle pressure? — The Interview 02",
        description=(
            "Original workplace comedy. Native paths, gradients, captions and animation; two generic synthetic voices."
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

manager = cast.Manager(cv)
wide = ep.setup(
    locations.office_wide,
    WIDE,
    at_desk=lambda g: ep.perform(
        manager, g, 560, 724, 1.45, blinks=[(P(2).start - 0.27, P(2).start - 0.12), (REACTION + 0.33, REACTION + 0.51)]
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
        smile=[(P(1).end + 0.04, C[2]), (P(3).end + 0.04, DURATION)],
        blinks=[
            (P(1).start + 0.30, P(1).start + 0.45),
            (P(3).start - 0.25, P(3).start - 0.10),
            (ENDING + 0.33, ENDING + 0.48),
        ],
    ),
)
# A silent phone makes the applicant's interpretation visible.
phone = props.silent_phone(cv, close)
cv.gate(phone, [(P(1).end - 0.08, DURATION)])

ep.captions()
ep.audio()
ep.markers()
ep.instagram(POSTS["pressure-interview"])
ep.finish()

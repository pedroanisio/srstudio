#!/usr/bin/env python3
"""Episode 04 — Multitasking, rebuilt with srstudio."""

from _common import VOICES_CREDIT, office_shots, project_root
from instagram_posts import POSTS
from srstudio import Episode, EpisodeSpec, camera, cast, graphics, locations

ep = Episode(
    EpisodeSpec(
        slug="multitasking",
        number="04",
        title="Multitasking — The Interview 04",
        description=(
            "Workplace comedy with expressive vector characters, a facepalm, status "
            "notifications, dashboard and ElevenLabs dialogue."
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
        manager,
        g,
        560,
        724,
        1.45,
        blinks=[(P(2).start - 0.27, P(2).start - 0.12), (REACTION + 0.22, ENDING)],
        nods=[
            (0, 0),
            (P(2).start - 0.1, 0),
            (P(2).start + 0.24, -4),
            (P(3).start, 0),
            (REACTION, 0),
            (REACTION + 0.26, 5),
        ],
        arms="articulated",
        hide_right_arm_at=REACTION + 0.06,
        brows=(
            [(0, 0), (P(2).start - 0.1, 0), (P(2).start + 0.12, 8), (REACTION, 2)],
            [(0, 0), (P(2).start - 0.1, 0), (P(2).start + 0.12, -8), (REACTION, -2)],
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
        smile=[(P(1).end + 0.03, C[2]), (P(3).end + 0.03, DURATION)],
        blinks=[
            (P(1).start + 0.30, P(1).start + 0.45),
            (P(3).start - 0.23, P(3).start - 0.10),
            (ENDING + 0.65, ENDING + 0.80),
        ],
        nods=[
            (0, 0),
            (P(1).start, 0),
            (P(1).start + 0.25, -3),
            (P(1).end, 0),
            (P(3).start, 0),
            (P(3).start + 0.30, -3),
            (P(3).end, -4),
            (ENDING, -4),
            (ENDING + 0.35, 0),
        ],
        arms="articulated",
        forearm=[(0, 0), (P(3).start - 0.05, 0), (P(3).start + 0.22, 180), (REACTION, 180), (ENDING, 0)],
        pointing=[(P(3).start + 0.13, REACTION)],
    ),
)
camera.anchor(close, 540, 737, place=True)
camera.zoom_holds(cv, close, [(0, 1), (C[3], 1.04), (ENDING, 1)])

graphics.episode_slate(cv, ep.comp, "04", "MULTITASKING")
# Character timestamps delay the visual reveal until 'several' is spoken.
REVEAL = t.word_time(3, "several")
for i, (x, y, who, status) in enumerate(
    [(70, 228, "MANAGER", "DEADLINE MISSED"), (395, 278, "CLIENT", "STILL WAITING"), (720, 228, "TEAM", "LEFT ON READ")]
):
    graphics.notification(cv, ep.comp, i, who, status, show=(REVEAL + i * 0.12, REACTION), x=x, y=y)
graphics.dashboard(
    cv,
    ep.comp,
    "MULTITASKING: ACTIVE",
    [("DEADLINES", "MISSED"), ("EMAILS", "IGNORED"), ("PEOPLE", "DISAPPOINTED")],
    show=(ENDING + 0.06, DURATION),
)
specs = ep.default_captions()
p3 = P(3)
specs[3:4] = [
    (p3.start - 0.06, REVEAL, "I can disappoint...", "punchline-setup"),
    (REVEAL, specs[3][1], "several people at once.", "punchline-finish"),
]
ep.captions(specs, highlights={"punchline-finish": [("several people ", False), ("at once.", True)]})
ep.audio_mix()
ep.markers()
ep.instagram(POSTS["multitasking"])
ep.finish()

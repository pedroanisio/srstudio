#!/usr/bin/env python3
"""Episode 01 — Honesty, rebuilt with srstudio."""

from _common import office_shots, project_root
from instagram_posts import POSTS
from srstudio import Episode, EpisodeSpec, camera, cast, locations

ep = Episode(
    EpisodeSpec(
        slug="honesty-interview",
        number="01",
        title="The honesty interview — ElevenLabs VO",
        description=(
            "The original native-vector interview rebuilt with new ElevenLabs Eric and Will "
            "voices. Original reaction and repeat structure retained."
        ),
        signature=False,  # shipped before ADR 0001; the package must reproduce element for element
        root=project_root(__file__),
        seed=52023,
        background="#D5DFDF",
        output="renders/honesty-interview-recreated.mp4",
        audio_credit="New dialogue generated with ElevenLabs premade voices Eric and Will.",
    )
)
t, cv, P = ep.t, ep.cv, ep.P
REACTION, REACTION_END, DURATION = t.reaction, t.reaction_end, t.duration
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
        blinks=[
            (P(2).start + 0.45, P(2).start + 0.60),
            (REACTION + 0.25, REACTION + 0.40),
            (P(4).start + 0.60, P(4).start + 0.75),
            (P(6).start + 0.25, P(6).start + 0.40),
        ],
    ),
)
camera.anchor(wide, 560, 724)
# The reaction push-in returns to the normal framing on the next line.
camera.push_in(
    cv,
    wide,
    x=[(0, 560), (REACTION, 540), (REACTION_END, 560)],
    y=[(0, 724), (REACTION, 850), (REACTION_END, 724)],
    scale=[(0, 1), (REACTION, 1.45), (REACTION_END, 1)],
    hold_scale=True,
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
        smile=[(P(1).end, C[2]), (P(5).end, C[6])],
        blinks=[
            (P(1).start + 0.10, P(1).start + 0.25),
            (P(3).start + 0.60, P(3).start + 0.75),
            (P(5).start + 0.10, P(5).start + 0.25),
        ],
    ),
)

specs = []
for i, p in enumerate(ep.phrases):
    end = C[i + 1] if i < 3 else REACTION if i == 3 else C[i + 1] if i < 6 else DURATION
    specs.append((max(0, p.start - 0.04), end, p.caption, f"dialogue-{i + 1}"))
ep.captions(specs)
ep.audio(track_id="elevenlabs-dialogue")
ep.markers()
ep.instagram(POSTS["honesty-interview"])
ep.finish()

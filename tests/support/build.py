"""What test_build.py shares with other test modules."""

from srstudio import Episode, EpisodeSpec, camera, cast, graphics, locations, props


def office_episode(project, out):
    ep = Episode(
        EpisodeSpec(
            slug="t-office",
            title="t",
            description="t",
            root=project,
            seed=1,
            background="#D5DFDF",
            signature_code="SR-1028",
        )
    )
    t, P = ep.t, ep.P
    wide = ep.setup(
        locations.office_wide,
        t.shots({"wide"}),
        at_desk=lambda g: ep.perform(
            cast.Manager(ep.cv),
            g,
            560,
            724,
            1.45,
            blinks=[(1, 1.15)],
            arms="articulated",
            hide_right_arm_at=t.reaction,
            facepalm=(t.reaction, t.ending),
            brows=([(0, 0), (1, 8)], [(0, 0), (1, -8)]),
            pupils=[(0, -31)],
        ),
    )
    camera.anchor(wide, 560, 724)
    camera.push_in(ep.cv, wide, x=[(0, 560), (t.reaction, 540)], scale=[(0, 1), (t.reaction, 1.6)])
    close = ep.setup(
        locations.office_reverse,
        t.shots({"close"}),
        in_chair=lambda g: ep.perform(
            cast.Candidate(ep.cv),
            g,
            540,
            737,
            2.07,
            smile=[(P(1).end, P(2).start)],
            arms="articulated",
            forearm=[(0, 0), (P(3).start, 180)],
            pointing=[(P(3).start, t.reaction)],
        ),
    )
    phone = props.silent_phone(ep.cv, close)
    ep.cv.gate(phone, [(P(1).end, t.duration)])
    graphics.episode_slate(ep.cv, ep.comp, "T1", "TEST")
    graphics.quiz_card(
        ep.cv,
        ep.comp,
        "QUICK MATH",
        "17 × 19 = ?",
        show=(P(2).start, P(3).end),
        verdict="NOPE.",
        verdict_span=(P(3).start, P(3).end),
    )
    graphics.scorecard(ep.cv, ep.comp, "SCORE", [("SPEED", "10 / 10", "#AAD6BD")], show=(t.ending, t.duration))
    ep.captions(highlights={"dialogue-4": [("Forty-", False), ("two.", True)]})
    ep.audio_mix()
    ep.markers()
    return ep, ep.finish(out / "t-office.scene.xml")

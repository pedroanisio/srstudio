#!/usr/bin/env python3
"""Entry Level, built with srstudio: the ad says ten years, and the applicants get younger.

    srstudio record entry-level PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build entry-level PROJECT    # → PROJECT/entry-level.scene.xml

Held frame: the interviewer, and the ad on his desk: ENTRY LEVEL, 10 YEARS' EXPERIENCE. "It's entry level, so just ten
years." "I'm 22." "Have you tried starting earlier?" The bell. A crayon CV, small shoes swinging under it: "Been in
the role since nursery." "Promising." Milo: "This software came out in 2024." "We need twenty years in it." A crib:
"I've been networking since the womb." "Overqualified. We'd lose you." "Who actually got it?" The blind snaps up: Rosa
at a desk in a paper hat. "She's still on probation."

The first second is still (arm A of the ``sp-hook_motion`` test). The toddler and the baby are heard and never drawn.
It declares no engine safe area, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from entry_level_audio import INTERVIEW
from instagram_posts import POSTS
from srstudio import OFFICE, Episode, EpisodeSpec, cast, cutout_hiring, locations, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="entry-level",
        title="Entry Level",
        description="Job-hunting comedy: an entry-level job that asks for ten years, applicants who start ever "
        "earlier, and the person who has it. Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        **iv_audio.spec_font(INTERVIEW.font, project_root(__file__)),
        seed=26132,
        background="#66798B",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv = ep.t, ep.cv
SNAP = float(t.meta["snap"])
RATTLE = tuple(float(x) for x in t.meta["rattle"])
REACTION, DURATION = t.reaction, t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
EPS = 1 / 120
BOSS_AT = (320, 700, 1.55)
ROSA_AT = (825, 640, 0.95)
CHAIR_AT = (540, 737, 2.07)

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))


def boss(g):
    manager = cast.Manager(cv, tag="boss-character")
    ep.perform(
        manager,
        g,
        *BOSS_AT,
        arms="articulated",
        mouth=ep.mouth("manager"),
        blinks=[(L[0].end + 0.08, L[0].end + 0.22), (L[4].end + 0.05, L[4].end + 0.19)],
        nods=[
            (0, 0),
            (1.2, 0),
            (1.5, 3),
            (L[2].start, 0),
            (L[2].start + 0.3, 4),
            (L[4].start, 0),
            (L[4].start + 0.2, 7),  # "Promising."
            (L[4].end, 0),
            (L[8].start, 0),
            (L[8].start + 0.25, -4),  # "Overqualified."
            (L[8].end, 0),
        ],
    )
    cv.keys(
        manager.forearm,
        "rotation",
        [(0, 0), (L[9].end + 0.2, 0), (SNAP - 0.25, -100), (SNAP, -70), (SNAP + 0.3, -70), (SNAP + 0.5, 0)],
        hold=False,
    )


def next_room(g):
    trainee = cast.Rosa(cv, tag="trainee-character")
    ep.perform(trainee, g, *ROSA_AT, mouth=[(0, "rest")], blinks=[(REACTION + 0.5, REACTION + 0.66)], stitch=None)
    cv.rect(g, 690, 830, 270, 130, "#8E6340", cv.ink, 4)
    cutout_hiring.paper_hat(cv, g, ROSA_AT[0], ROSA_AT[1] - 82, scale=0.95, id="trainee-hat")


def on_desk(g):
    cutout_hiring.job_ad(cv, g, 540, 1370)


finish = locations.finish(cv, ep.comp)
office = cutout_hiring.hiring_office(cv, finish, behind_desk=boss, on_desk=on_desk, next_room=next_room, snap=SNAP,
                                     shots=spans["desk"] + spans["glass"])  # fmt: skip


def framing(at, scale, to):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


GLASS_FROM = framing(ROSA_AT[:2], 1.9, (540, 760))
GLASS_TO = framing(ROSA_AT[:2], 2.15, (540, 760))
start = spans["glass"][0][0]
for prop, k in (("scaleX", 0), ("scaleY", 0), ("x", 1), ("y", 2)):
    rest = 1.0 if k == 0 else 0.0
    cv.keys(
        office, prop, [(0.0, rest), (start - EPS, rest), (start, GLASS_FROM[k]), (DURATION, GLASS_TO[k])], hold=False
    )


def applicant(angle: str, slot):
    backing = cv.group(finish, f"backing-{angle}")  # the frame's edge, where the wall's blur thins out
    cv.gate(backing, spans[angle])
    cv.rect(backing, -10, -10, 1100, 1940, props.office_paints(cv)["warm_wall"])
    locations.office_reverse(cv, finish, in_chair=slot, id=f"chair-{angle}", shots=spans[angle], depth=6)


def young(g):
    ep.perform(
        cast.Candidate(cv, tag="young-character"),
        g,
        *CHAIR_AT,
        mouth=ep.mouth("candidate"),
        blinks=[(L[1].end + 0.05, L[1].end + 0.19)],
        nods=[(0, 0), (L[1].start, 0), (L[1].start + 0.3, 3)],
    )


def door(g):
    ep.perform(
        cast.Candidate(cv, tag="door-character"),
        g,
        540,
        737,
        2.07,
        mouth=ep.mouth("candidate"),
        nods=[(0, 3), (L[9].start, 3), (L[9].start + 0.3, -4)],
    )


def tech(g):
    milo = cast.Customer(cv, tag="tech-character", seated=True)
    ep.perform(milo, g, 540, 700, 1.9, mouth=ep.mouth("milo"), blinks=[(L[5].end + 0.05, L[5].end + 0.2)])


applicant("applicant", young)
applicant("toddler", lambda g: cutout_hiring.crayon_cv(cv, g, 540, 640, swings=(spans["toddler"][0],), scale=1.08))
applicant("tech", tech)
applicant("door", door)
applicant("crib", lambda g: cutout_hiring.crib(cv, g, 540, 1400, rattles=((RATTLE[0], L[7].end),), scale=1.05))

spoken = ep.captions(ep.spoken_captions(), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(
    extra=[("marker-toddler", spans["toddler"][0][0], "The second applicant"), ("marker-blind", SNAP, "The blind")]
)
ep.instagram(POSTS["entry-level"])
ep.finish()

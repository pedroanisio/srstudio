#!/usr/bin/env python3
"""Episode 11 — Day Off, the fourth Soft episode.

    python3 day_off_audio.py PROJECT --key-stdin < key   # the music, Pip's lines and effects → dialogue.json
    python3 day_off.py PROJECT                            # → PROJECT/day-off.scene.xml

Saturday on the sofa, and Pip's body is still at work: his hands type on nothing, he agrees with the lamp, and
he swears he can stop any time. He can only rest once resting is a meeting: a calendar invite with the sofa,
accepted. When the meeting ends he is typing again before the chime stops, until he extends it.
The calendar badge (``soft-status-badge``) shows what the invite says. Every pose lands on the beat.
"""

import os
from dataclasses import replace
from functools import partial

from _common import project_root
from day_off_audio import GROOVE
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, camera, foley, layout, soft_props
from srstudio.blob import SCALE, SOFA_SEAT
from srstudio.soft_props import BadgeState

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="day-off",
        number="11",
        title="Day Off — Pip 04",
        description="Pose-to-pose comedy on a beat: Pip's Saturday on the sofa, with hands that keep typing until "
        "he books a meeting with the sofa. Native vector animation; music composed by ElevenLabs Music, Pip and "
        "effects by ElevenLabs.",
        root=project_root(__file__),
        seed=93100,
        style=SOFT,
        safe_area=layout.VERTICAL,  # captions and the badge stay inside x 80–920, y 220–1420
    )
)
t, cv, at = ep.t, ep.cv, GROOVE.at
P, DURATION = t.phrases, t.duration
SING = "sing"
BEAT, EIGHTH = 0.3, 0.125  # in-between time before a pose lands on the beat (four drawings) or the eighth (two)
FPS = 15
POP = 0.08

# The hands type on nothing three times: the keyboard is heard on every eighth they hit.
TYPING = [(at(1, 2), at(4)), (at(6, 3), at(8)), (at(10), at(11, 1))]
eighths = [w for a, b in TYPING for w in GROOVE.beats(0, 13, every=0.25) if a <= w < b]
foley.write_typing(ep.root / "assets" / "typing.wav", foley.taps(eighths, seed=11), DURATION, seed=11, peak=0.5)
ep.audio(
    extra=[
        ("music", "assets/music.wav", {"role": "music", "gain": -6}),
        ("typing", "assets/typing.wav", {"role": "effects", "gain": -4}),
    ],
    duck=-8,
)

cue = partial(blob.cue, scale=SCALE, ease=BEAT)


def typing(a: float, b: float, eyes: str, mouth: str = "flat") -> list:
    return [
        cue(w, "type-a" if i % 2 == 0 else "type-b", SOFA_SEAT, ease=EIGHTH, eyes=eyes, mouth=mouth)
        for i, w in enumerate(GROOVE.beats(0, 13, every=0.5))
        if a <= w < b
    ]


cues = [
    # Bar 0: Saturday. Eyes closed.
    cue(0, "lounge", SOFA_SEAT, eyes="closed", mouth="smile"),
    cue(P[0].end + 0.05, "lounge", SOFA_SEAT, ease=0, eyes="closed", mouth="smile"),
    # Bars 1-3: the hands lift off his lap on their own and type; he looks down at them.
    *typing(at(1, 2), at(2), "closed", "smile"),
    *typing(at(2), at(4), "wide"),
    # Bars 4-5: agreeing with the lamp, on the beat.
    *(
        cue(
            w,
            "nod" if i % 2 == 0 else "sit",
            SOFA_SEAT,
            ease=EIGHTH,
            eyes="squint",
            mouth=SING if P[2].start <= w < P[2].end else "smile",
        )
        for i, w in enumerate(GROOVE.beats(4, 6))
    ),  # fmt: skip
    # Bars 6-7: back to the sofa. He can stop any time. The hands go up again.
    cue(at(6), "lounge", SOFA_SEAT, eyes="closed", mouth="smile"),
    cue(at(6, 3), "type-a", SOFA_SEAT, ease=0.45, eyes="closed", mouth="smile"),
    *typing(at(7), at(8), "wide"),
    # Bar 8: the invite. Booked. Accepted. Bar 9: nothing moves.
    cue(at(8), "type-a", SOFA_SEAT, ease=0, eyes="look", mouth="o"),
    cue(P[4].start, "sit", SOFA_SEAT, ease=EIGHTH, eyes="happy", mouth="smile"),
    cue(P[4].end + 0.05, "lounge", SOFA_SEAT, ease=0.5, eyes="closed", mouth="smile"),
    # Bar 10: the meeting ended. Typing before the chime is over.
    cue(at(10), "type-a", SOFA_SEAT, ease=0, eyes="wide", mouth="o"),
    *typing(at(10, 0.5), at(11, 1), "wide"),
    # Bar 11: extend? Tap. Gone.
    cue(at(11, 1), "type-a", SOFA_SEAT, ease=EIGHTH, eyes="look", mouth="flat"),
    cue(t.tap_start, "type-b", SOFA_SEAT, ease=0, eyes="squint", mouth="smile"),
    cue(t.tap_start + 0.25, "lounge", SOFA_SEAT, ease=0.3, eyes="closed", mouth="smile"),
]
# One cue per time (the later in the list wins), then the speaking mouth on every hold that overlaps a line.
cues = list({round(c.time, 6): c for c in sorted(cues, key=lambda c: c.time)}.values())
holds = zip(cues, [c.time for c in cues[1:]] + [DURATION], strict=True)
cues = [replace(c, mouth=SING) if any(p.start < until and c.time < p.end for p in P) else c for c, until in holds]
cues = blob.settle(cues, FPS, published_full_gap_ease=True)
mouths = ep.mouth("pip")

room = blob.home(
    cv,
    ep.comp,
    on_sofa=lambda g: blob.pip(cv, g, cues, end=DURATION, scale=SCALE, mouth_states=mouths, fps=FPS, shadow=True),
)

# The calendar invite: pending, accepted, ended, the offer to extend, extended.
GREY, GREEN, RED, AMBER = "#9A938C", "#4CB36B", "#E0503F", "#E3A33B"
ACCEPT = P[4].end - 0.3

# Crash zooms onto Pip's face: the frozen stare at the invite, the snap back to work when it ends. Each cuts back
# to the wide shot on a beat so the lounge and the extend tap read as whole-body gags.
SNAP, CUT = 0.2, 1 / FPS
camera.anchor(room, 552, 860, place=True)
# Each zoom also drops the frame so the sprout clears the calendar badge.
zoomed = [
    (0.0, 0),
    (t.ping_start, 0),
    (t.ping_start + SNAP, 1),
    (ACCEPT, 1),
    (ACCEPT + CUT, 0),
    (t.ended_start, 0),
    (t.ended_start + SNAP, 1),
    (at(11, 1), 1),
    (at(11, 1) + CUT, 0),
]
cv.keys(room, "y", [(time, 860 + 150 * on) for time, on in zoomed], hold=False)
camera.push_in(
    cv,
    room,
    scale=[
        (0.0, 1.0),
        (t.ping_start, 1.0),
        (t.ping_start + SNAP, 1.6),
        (ACCEPT, 1.6),
        (ACCEPT + CUT, 1.0),
        (t.ended_start, 1.0),
        (t.ended_start + SNAP, 1.4),
        (at(11, 1), 1.4),
        (at(11, 1) + CUT, 1.0),
    ],
)
soft_props.status_badge(
    cv,
    ep.comp,
    [
        BadgeState("invite", "SOFA SYNC", GREY, t.ping_start, ACCEPT),
        BadgeState("accepted", "ACCEPTED", GREEN, ACCEPT, t.ended_start),
        BadgeState("ended", "ENDED", RED, t.ended_start, at(11, 1), struck=True),
        BadgeState("extend", "EXTEND?", AMBER, at(11, 1), t.tap_start),
        BadgeState("extended", "EXTENDED", GREEN, t.tap_start, DURATION),
    ],
    (520, 520, 380, 92),
    id="calendar",
)

specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.02 if i + 1 < len(P) else DURATION
    specs.append((max(0.0, p.start - 0.05), min(until, p.end + 1.2), p.caption, f"caption-{i + 1}"))
ep.captions(
    specs, x=80, y=250, width=840, height=180, size=58, color="#1A1714", stroke="#FFFFFF", stroke_width=7, shadow=None
)
ep.markers(
    extra=[
        ("marker-ping", t.ping_start, "Invite: the sofa"),
        ("marker-ended", t.ended_start, "Meeting ended"),
        ("marker-tap", t.tap_start, "Extended"),
    ]
)
ep.instagram(POSTS["day-off"])
out = ep.finish()
ep.check_overlays(out, ["calendar"])

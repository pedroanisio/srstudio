#!/usr/bin/env python3
"""Episode 13 — Unlimited PTO, the fifth Soft episode and Bo's first on screen.

    python3 unlimited_pto_audio.py PROJECT --key-stdin < key   # the music, the lines and effects → dialogue.json
    python3 unlimited_pto.py PROJECT                            # → PROJECT/unlimited-pto.scene.xml

A one-on-one in the meeting room. Bo has big news: unlimited vacation. Pip asks for Friday, then Friday
afternoon, then lunch, and each request is declined before Bo has finished explaining why. So how many days is
unlimited? Unlimited: that's why nobody needs one. Then Bo's own request is approved: Bali, three weeks. The request
badge (``soft-status-badge``) shows every ask and its answer. Every pose lands on the beat.
"""

import os
from dataclasses import replace
from functools import partial

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, layout, soft_props
from srstudio.blob import FLOOR, SCALE, SEAT
from srstudio.soft_props import BadgeState
from unlimited_pto_audio import GROOVE

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="unlimited-pto",
        number="13",
        title="Unlimited PTO — Comedy Cut 13",
        description="Pose-to-pose comedy on a beat: Bo announces unlimited vacation and declines every day of it, "
        "then approves his own. Native vector animation; music composed by ElevenLabs Music, voices and effects "
        "by ElevenLabs.",
        root=project_root(__file__),
        seed=13100,
        style=SOFT,
        safe_area=layout.VERTICAL,  # captions and the badge stay inside x 80–920, y 220–1420
    )
)
t, cv, at = ep.t, ep.cv, GROOVE.at
P, DURATION = t.phrases, t.duration
SING = "sing"
BEAT, EIGHTH = 0.3, 0.125  # in-between time before a pose lands on the beat (four drawings) or the eighth (two)
FPS = 15
BO_AT = (300.0, FLOOR)  # left of the table's end, in front of the screen, mirrored to face Pip across the room
EXIT = -260.0  # off the left edge
ASK = (700.0, FLOOR)  # Pip stands up in front of his chair to ask
RISE = 40.0

ep.audio(extra=[("music", "assets/music.wav", {"role": "music", "gain": -6})], duck=-8)
cue = partial(blob.cue, scale=SCALE, ease=BEAT)


def speaking(cues: list, role: str) -> list:
    """One cue per time (the later in the list wins), then the speaking mouth on every hold that overlaps one of
    ``role``'s lines."""
    cues = list({round(c.time, 6): c for c in sorted(cues, key=lambda c: c.time)}.values())
    holds = zip(cues, [c.time for c in cues[1:]] + [DURATION], strict=True)
    lines = [p for p in P if p.role == role]
    out = [
        replace(c, mouth=SING) if any(p.start < until and c.time < p.end for p in lines) else c for c, until in holds
    ]
    return blob.settle(out, FPS)


bo_cues = speaking(
    [
        # Bar 0: the big news, cheering on the beat.
        *(
            cue(w, "cheer-a" if i % 2 == 0 else "cheer-b", BO_AT, ease=EIGHTH, eyes="happy", mouth="grin")
            for i, w in enumerate(GROOVE.beats(0, 1))
        ),  # fmt: skip
        cue(at(1), "stand", BO_AT, eyes="happy", mouth="smile"),
        # Each ask: declined before he has finished explaining.
        cue(P[2].start, "lean", BO_AT, eyes="squint", mouth="flat"),
        cue(P[2].end + 0.1, "stand", BO_AT, eyes="happy", mouth="smile"),
        cue(P[4].start, "stand", BO_AT, ease=EIGHTH, eyes="closed", mouth="flat"),
        cue(P[4].end + 0.2, "stand", BO_AT, eyes="happy", mouth="smile"),
        cue(P[6].start, "clasp", BO_AT, eyes="happy", mouth="smile"),
        # The question, the hold, the answer.
        cue(P[7].start, "stand", BO_AT, eyes="look", mouth="smile"),
        cue(P[7].end + 0.1, "stand", BO_AT, eyes="closed", mouth="flat"),
        cue(P[8].start, "lean", BO_AT, eyes="happy", mouth="grin"),
        # The button: approved. Waving, and gone.
        cue(t.approved_start, "cheer-a", BO_AT, ease=EIGHTH, eyes="happy", mouth="grin"),
        *(
            cue(w, "wave-a" if i % 2 == 0 else "wave-b", BO_AT, ease=EIGHTH, eyes="happy", mouth="grin")
            for i, w in enumerate(GROOVE.beats(10, 11, every=0.5))
            if w > t.approved_start
        ),  # fmt: skip
        *(
            cue(
                at(11) + i * 0.25,
                ("walk-a", "stride", "walk-b", "stride")[i % 4],
                (BO_AT[0] + (EXIT - BO_AT[0]) * (i + 1) / 8, FLOOR),
                ease=0.2,
                eyes="happy",
                mouth="smile",
            )
            for i in range(8)
        ),  # fmt: skip
    ],
    "bo",
)
pip_cues = speaking(
    [
        cue(0, "sit", SEAT, eyes="look", mouth="smile"),
        cue(at(0, 2), "nod", SEAT, ease=EIGHTH, eyes="wide", mouth="o"),
        # Friday, Friday afternoon, lunch: hands clasped, the ask a little smaller each time.
        cue(P[1].start, "clasp", ASK, eyes="wide", mouth="smile", lift=RISE),
        cue(t.decline1_start, "sit", SEAT, ease=0.2, eyes="wide", mouth="o", lift=RISE),
        cue(P[3].start, "clasp", ASK, eyes="look", mouth="small", lift=RISE),
        cue(t.decline2_start, "sit", SEAT, ease=0.2, eyes="squint", mouth="flat", lift=RISE),
        cue(P[5].start, "clasp", ASK, ease=EIGHTH, eyes="look", mouth="small", lift=RISE),
        cue(t.decline3_start, "sit", SEAT, ease=0.2, eyes="closed", mouth="flat", lift=RISE),
        cue(P[7].start, "nod", SEAT, eyes="squint", mouth="flat"),
        cue(P[7].end + 0.1, "sit", SEAT, eyes="look", mouth="flat"),
        cue(P[8].end + 0.1, "sit", SEAT, ease=0, eyes="wide", mouth="o"),
        cue(t.approved_start + 0.3, "sit", SEAT, eyes="squint", mouth="flat"),
        cue(at(11, 2), "type-a", SEAT, eyes="closed", mouth="flat"),  # back to work
        *(
            cue(w, "type-a" if i % 2 == 0 else "type-b", SEAT, ease=EIGHTH, eyes="closed", mouth="flat")
            for i, w in enumerate(GROOVE.beats(11, 13, every=0.5))
            if w > at(11, 2) and w < DURATION
        ),  # fmt: skip
    ],
    "pip",
)
mouths = {role: ep.mouth(role) for role in ("bo", "pip")}

room = blob.meeting_room(cv, ep.comp)
blob.bo(
    cv,
    room,
    [replace(c, flip=True) for c in bo_cues],
    end=DURATION,
    scale=SCALE,
    mouth_states=mouths["bo"],
    fps=FPS,
    shadow=True,
)
blob.pip(cv, room, pip_cues, end=DURATION, scale=SCALE, mouth_states=mouths["pip"], fps=FPS, shadow=True)

# The request badge: each ask pending, then declined; Bo's own approved.
AMBER, RED, GREEN = "#E3A33B", "#E0503F", "#4CB36B"
d1, d2, d3, ok = t.decline1_start, t.decline2_start, t.decline3_start, t.approved_start
soft_props.status_badge(
    cv,
    ep.comp,
    [
        BadgeState("ask-1", "PTO: FRIDAY", AMBER, P[1].start, d1),
        BadgeState("no-1", "DECLINED", RED, d1, P[3].start, struck=True),
        BadgeState("ask-2", "PTO: FRI PM", AMBER, P[3].start, d2),
        BadgeState("no-2", "DECLINED", RED, d2, P[5].start, struck=True),
        BadgeState("ask-3", "LUNCH: 30 MIN", AMBER, P[5].start, d3),
        BadgeState("no-3", "DECLINED", RED, d3, ok, struck=True),
        BadgeState("bo", "BO: BALI 3 WK", GREEN, ok, DURATION),
    ],
    (460, 470, 450, 92),  # the pop-in overshoots: the right edge stays 10 px inside the safe area
    id="requests",
)

specs, boss = [], []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.02 if i + 1 < len(P) else DURATION
    (boss if p.role == "bo" else specs).append(
        (max(0.0, p.start - 0.05), min(until, p.end + 1.2), p.caption, f"caption-{i + 1}")
    )
caption_style = dict(x=80, y=250, width=840, height=180, size=58, stroke="#FFFFFF", stroke_width=7, shadow=None)
spoken = ep.captions(specs, color="#1A1714", **caption_style)
spoken += ep.captions(boss, color="#2F5D8C", **caption_style)
ep.hide_on_cover(*spoken)
ep.markers(
    extra=[
        ("marker-decline-1", d1, "Friday: declined"),
        ("marker-decline-3", d3, "Lunch: declined"),
        ("marker-approved", ok, "Bo: Bali, approved"),
    ]
)
ep.instagram(POSTS["unlimited-pto"])
out = ep.finish()
ep.check_overlays(out, ["requests"])

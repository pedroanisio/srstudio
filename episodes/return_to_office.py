#!/usr/bin/env python3
"""Episode 15 — Return to Office, the sixth Soft episode: Pip back in the meeting room, Bo on the wall screen.

    python3 return_to_office_audio.py PROJECT --key-stdin < key   # the music, the lines and effects → dialogue.json
    python3 return_to_office.py PROJECT                            # → PROJECT/return-to-office.scene.xml

Day one of the return to office. Pip has spent two hours on a train to stand in an empty meeting room. The wall
screen chimes: Bo welcomes the team back, from a beach. "I'm the only one here." "And we can all see you. Wave!"
Where is he? Bali: leadership is hybrid. So why is Pip here? Someone has to be the culture. The call ends, and the
motion-sensor lights decide nobody is in: Pip waves them back on, and the moment he stops, they go off again.
"""

import math
import os
from dataclasses import replace
from functools import partial

from _common import project_root
from instagram_posts import POSTS
from return_to_office_audio import GROOVE
from srstudio import SOFT, Episode, EpisodeSpec, blob, camera, layout, soft_props
from srstudio.blob import FLOOR, SCALE, SEAT
from srstudio.soft_props import BadgeState

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="return-to-office",
        number="15",
        title="Return to Office — Comedy Cut 15",
        description="Pose-to-pose comedy on a beat: day one back in the office, an empty meeting room, and the boss "
        "on the wall screen from a beach. Native vector animation; music composed by ElevenLabs Music, voices and "
        "effects by ElevenLabs.",
        root=project_root(__file__),
        seed=15100,
        style=SOFT,
        safe_area=layout.VERTICAL,  # captions and the badge stay inside x 80–920, y 220–1420
    )
)
t, cv, at = ep.t, ep.cv, GROOVE.at
P, DURATION = t.phrases, t.duration
JOIN, GULL, ENDED = t.join_start, t.seagull_start, t.call_end_start
DARK, LIGHT, DARK2 = t.dark_start, t.light_start, t.dark2_start
SING = "sing"
BEAT, EIGHTH = 0.3, 0.125  # in-between time before a pose lands on the beat (four drawings) or the eighth (two)
FPS = 15
SNAP, CUT = 0.2, 1 / FPS
STAND = (700.0, FLOOR)  # Pip stands in front of the swivel chair, facing the screen
(SX, SY), SW, SH, SKEW = blob.meeting_screen()
BO_SCALE = 0.45
BO_AT = (SW * 0.42, SH + 20)  # in the call's flat frame: head and shoulders in the picture, the rest below it

ep.audio(extra=[("music", "assets/music.wav", {"role": "music", "gain": -6})], duck=-8)
cue = partial(blob.cue, scale=SCALE, ease=BEAT)
bo_cue = partial(blob.cue, scale=BO_SCALE, ease=BEAT)


def speaking(cues: list, role: str) -> list:
    """One cue per time (the later in the list wins), then the speaking mouth on every hold that overlaps one of
    ``role``'s lines."""
    cues = list({round(c.time, 6): c for c in sorted(cues, key=lambda c: c.time)}.values())
    holds = zip(cues, [c.time for c in cues[1:]] + [DURATION], strict=True)
    lines = [p for p in P if p.role == role]
    out = [
        replace(c, mouth=SING) if any(p.start < until and c.time < p.end for p in lines) else c for c, until in holds
    ]
    return blob.settle(out, FPS, published_full_gap_ease=True)


bo_cues = speaking(
    [
        bo_cue(0, "stand", BO_AT, eyes="happy", mouth="smile"),
        *(
            bo_cue(w, "cheer-a" if i % 2 == 0 else "cheer-b", BO_AT, ease=EIGHTH, eyes="happy", mouth="grin")
            for i, w in enumerate(GROOVE.beats(1, 2))
            if w >= JOIN
        ),  # fmt: skip
        bo_cue(at(2, 2), "stand", BO_AT, eyes="happy", mouth="smile"),
        bo_cue(P[3].start, "lean", BO_AT, eyes="happy", mouth="grin"),
        *(
            bo_cue(w, "wave-a" if i % 2 == 0 else "wave-b", BO_AT, ease=EIGHTH, eyes="happy", mouth="grin")
            for i, w in enumerate(GROOVE.beats(4, 5, every=0.5))
        ),  # fmt: skip
        bo_cue(at(5), "stand", BO_AT, eyes="happy", mouth="smile"),
        *(  # Bali: grooving to the steel drums
            bo_cue(
                w,
                ("groove-a", "groove-b", "groove-c", "groove-b")[i % 4],
                BO_AT,
                ease=EIGHTH,
                eyes="happy",
                mouth="grin",
            )
            for i, w in enumerate(GROOVE.beats(6, 8))
        ),  # fmt: skip
        bo_cue(P[6].start, "stand", BO_AT, eyes="look", mouth="smile"),
        bo_cue(P[6].end + 0.1, "stand", BO_AT, eyes="closed", mouth="flat"),
        bo_cue(P[7].start, "lean", BO_AT, eyes="happy", mouth="grin"),
        bo_cue(P[8].start, "cheer-a", BO_AT, ease=EIGHTH, eyes="happy", mouth="grin"),
        *(
            bo_cue(w, "wave-a" if i % 2 == 0 else "wave-b", BO_AT, ease=EIGHTH, eyes="happy", mouth="grin")
            for i, w in enumerate(GROOVE.beats(10, 11, every=0.5))
            if w > P[8].start
        ),  # fmt: skip
    ],
    "bo",
)
pip_cues = speaking(
    [
        cue(0, "stand", STAND, eyes="look", mouth="flat"),
        cue(at(0, 2), "lean", STAND, eyes="wide", mouth="o"),  # for THIS?
        cue(JOIN, "stand", STAND, ease=EIGHTH, eyes="wide", mouth="o"),
        cue(P[2].start, "clasp", STAND, eyes="look", mouth="small"),
        # Wave! Everyone is watching: a stiff wave on the beat.
        *(
            cue(w, "wave-a" if i % 2 == 0 else "wave-b", STAND, ease=EIGHTH, eyes="happy", mouth="smile")
            for i, w in enumerate(GROOVE.beats(4, 5, every=0.5))
            if w > P[3].end
        ),  # fmt: skip
        cue(at(5, 1), "stand", STAND, eyes="squint", mouth="flat"),
        cue(P[4].start, "lean", STAND, eyes="look", mouth="small"),
        cue(GULL, "stand", STAND, ease=EIGHTH, eyes="wide", mouth="o"),
        cue(P[6].start, "clasp", STAND, eyes="look", mouth="small"),
        cue(P[6].end + 0.1, "stand", STAND, eyes="look", mouth="flat"),
        cue(P[7].end + 0.15, "sit", SEAT, ease=0.2, eyes="wide", mouth="o"),  # the culture sinks into the chair
        cue(ENDED, "sit", SEAT, eyes="closed", mouth="flat"),
        cue(DARK + 0.1, "sit", SEAT, ease=0, eyes="wide", mouth="o"),
        *(  # waving the lights back on
            cue(w, "wave-a" if i % 2 == 0 else "wave-b", STAND, ease=EIGHTH, eyes="wide", mouth="grin")
            for i, w in enumerate(GROOVE.beats(11, 13, every=0.25))
            if DARK + 0.4 < w < LIGHT + 0.5
        ),  # fmt: skip
        cue(LIGHT + 0.5, "stand", STAND, eyes="happy", mouth="smile"),
        cue(DARK2 + 0.1, "stand", STAND, ease=0, eyes="closed", mouth="flat"),
    ],
    "pip",
)
mouths = {role: ep.mouth(role) for role in ("bo", "pip")}


def call(frame):
    """Bo's call from the beach, from the join; dark after it ends."""
    live = cv.group(frame, "bo-call")
    cv.gate(live, [(JOIN, DURATION)])
    cv.pop_in(live, JOIN)
    soft_props.beach_call(
        cv,
        live,
        SW,
        SH,
        name="BO · CEO",
        tag=(60.0, SH - 48),  # clear of the safe area's left edge
        guest=lambda g: blob.bo(
            cv, g, bo_cues, end=DURATION, scale=BO_SCALE, mouth_states=mouths["bo"], fps=FPS, id="bo-on-call"
        ),
    )
    off = cv.group(frame, "call-off")
    cv.gate(off, [(ENDED, DURATION)])
    cv.rect(off, 0, 0, SW, SH, "#15171C")


room = blob.meeting_room(cv, ep.comp, on_screen=call)
blob.pip(cv, room, pip_cues, end=DURATION, scale=SCALE, mouth_states=mouths["pip"], fps=FPS, shadow=True)

# Crash zooms onto the wall screen: the welcome, and Bali. Each cuts back to the wide shot on a beat.
CX = SX + SW / 2  # the picture's centre, down the wall's slope from the frame's top-left corner
CY = SY + SH / 2 + SW / 2 * math.tan(math.radians(SKEW))
camera.anchor(room, CX, CY, place=True)
ZOOM, TO = 2.4, (540.0, 900.0)
spans = [(JOIN, P[2].start - 0.1), (GULL, P[6].start - 0.1)]
keys = {"x": [(0.0, CX)], "y": [(0.0, CY)], "s": [(0.0, 1.0)]}
for a, b in spans:
    keys["x"] += [(a, CX), (a + SNAP, TO[0]), (b, TO[0]), (b + CUT, CX)]
    keys["y"] += [(a, CY), (a + SNAP, TO[1]), (b, TO[1]), (b + CUT, CY)]
    keys["s"] += [(a, 1.0), (a + SNAP, ZOOM), (b, ZOOM), (b + CUT, 1.0)]
cv.keys(room, "x", keys["x"], hold=False)
cv.keys(room, "y", keys["y"], hold=False)
camera.push_in(cv, room, scale=keys["s"])

# The motion-sensor lights: off when nobody moves, back on for a wave.
dark = cv.group(ep.comp, "room-dark")
cv.gate(dark, [(DARK, LIGHT), (DARK2, DURATION)])
cv.rect(dark, 0, 0, 1080, 1920, "#141A2E", opacity=0.72)

AMBER, RED, GREEN, GREY = "#E3A33B", "#E0503F", "#4CB36B", "#9AA3AD"
soft_props.status_badge(
    cv,
    ep.comp,
    [
        BadgeState("rto", "RTO: DAY 1", AMBER, 0.0, JOIN),
        BadgeState("live", "ON CALL", GREEN, JOIN, P[3].start),
        BadgeState("watching", "312 WATCHING", RED, P[3].start, ENDED),
        BadgeState("ended", "CALL ENDED", GREY, ENDED, DARK, struck=True),
        BadgeState("no-motion", "NO MOTION", AMBER, DARK, LIGHT),
        BadgeState("motion", "MOTION: PIP", GREEN, LIGHT, DARK2),
        BadgeState("no-motion-2", "NO MOTION", AMBER, DARK2, DURATION),
    ],
    (460, 470, 450, 92),  # the pop-in overshoots: the right edge stays 10 px inside the safe area
    id="room-status",
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
        ("marker-join", JOIN, "Bo joins from the beach"),
        ("marker-dark", DARK, "Lights off: no motion"),
        ("marker-dark-2", DARK2, "Lights off again"),
    ]
)
ep.instagram(POSTS["return-to-office"])
out = ep.finish()
ep.check_overlays(out, ["room-status"])

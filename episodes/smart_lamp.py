#!/usr/bin/env python3
"""Episode 17 — Smart Lamp, built with srstudio: Pip, Juno and the floor lamp from Day Off, which now listens.

    python3 smart_lamp_audio.py PROJECT --key-stdin < key   # the music, three voices and four effects → dialogue.json
    python3 smart_lamp.py PROJECT                            # → PROJECT/smart-lamp.scene.xml

At home, Juno tells Pip he never listens. He always listens! The lamp wakes: he doesn't, it has recordings. It has
ordered flowers, and the card says sorry. Then a ring. Pip cancels the ring; the lamp says she said yes, and Juno
does. Who is she marrying? The lamp did not catch that. The shade glows while the lamp talks (``home(lamp_talk=)``)
and its badge (``soft-status-badge``) shows what it is doing. Every pose lands on the beat.
"""

import os
from dataclasses import replace
from functools import partial

from _common import project_root
from instagram_posts import POSTS
from smart_lamp_audio import GROOVE
from srstudio import SOFT, Episode, EpisodeSpec, blob, camera, layout, soft_props
from srstudio.blob import LAMP_SHADE, SCALE, SOFA_SEAT
from srstudio.soft_props import BadgeState

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="smart-lamp",
        number="17",
        title="Smart Lamp — Comedy Cut 17",
        description="Pose-to-pose comedy on a beat: Juno says Pip never listens, and the smart lamp agrees, orders "
        "flowers and then a ring. Native vector animation; music composed by ElevenLabs Music, voices and effects "
        "by ElevenLabs.",
        root=project_root(__file__),
        seed=17100,
        style=SOFT,
        safe_area=layout.VERTICAL,  # captions and the badge stay inside x 80–920, y 220–1420
    )
)
t, cv, at = ep.t, ep.cv, GROOVE.at
P, DURATION = t.phrases, t.duration
WAKE, FLOWERS, RING, ERROR = t.wake_start, t.flowers_start, t.ring_start, t.error_start
SING = "sing"
BEAT, EIGHTH = 0.3, 0.125  # in-between time before a pose lands on the beat (four drawings) or the eighth (two)
FPS = 15
JUNO_SPOT = (215.0, 1590.0)  # standing on the rug in front of the sofa's far end
ep.audio(extra=[("music", "assets/music.wav", {"role": "music", "gain": -6})], duck=-8)

pip_cue = partial(blob.cue, spot=SOFA_SEAT, scale=SCALE, ease=BEAT)
juno_cue = partial(blob.cue, spot=JUNO_SPOT, scale=SCALE, ease=BEAT)


def spoken(cues: list, role: str) -> list:
    """One cue per time (the later wins), then the singing mouth on every hold that overlaps a line of ``role``."""
    cues = list({round(c.time, 6): c for c in sorted(cues, key=lambda c: c.time)}.values())
    holds = zip(cues, [c.time for c in cues[1:]] + [DURATION], strict=True)
    mine = [p for p in P if p.role == role]
    cues = [
        replace(c, mouth=SING) if any(p.start < until and c.time < p.end for p in mine) else c for c, until in holds
    ]
    return blob.settle(cues, FPS)


pip_cues = spoken(
    [
        pip_cue(0, "lounge", eyes="look", mouth="flat"),
        pip_cue(P[1].start, "sit", eyes="wide", mouth="smile"),  # "I always listen!"
        pip_cue(WAKE, "sit", ease=EIGHTH, eyes="look", mouth="o"),  # the lamp wakes behind him
        pip_cue(P[3].start, "nod", eyes="squint", mouth="flat"),  # "Nobody asked you!"
        pip_cue(at(5), "sit", eyes="look", mouth="flat"),
        pip_cue(P[6].start, "nod", ease=EIGHTH, eyes="squint", mouth="flat"),  # "I'm not sorry!"
        pip_cue(P[7].start, "sit", ease=EIGHTH, eyes="wide", mouth="o"),  # "And a ring."
        pip_cue(P[8].start, "nod", ease=EIGHTH, eyes="squint", mouth="grin"),  # "Cancel the ring!"
        pip_cue(P[9].start, "sit", ease=0, eyes="wide", mouth="o"),  # "She said yes."
        pip_cue(P[11].start, "sit", eyes="look", mouth="flat"),  # "Who is she marrying?"
        pip_cue(ERROR, "lounge", ease=0.5, eyes="closed", mouth="flat"),
    ],
    "pip",
)
juno_cues = spoken(
    [
        juno_cue(0, "clasp", eyes="squint", mouth="flat"),  # "You never listen to me."
        juno_cue(WAKE, "stand", ease=EIGHTH, eyes="look", mouth="o"),
        juno_cue(P[4].start, "clasp", ease=EIGHTH, eyes="happy", mouth="smile"),  # "See? It gets me."
        juno_cue(at(6), "clasp", eyes="happy", mouth="smile"),
        juno_cue(RING, "stand", ease=EIGHTH, eyes="wide", mouth="o"),
        juno_cue(P[10].start, "cheer-a", ease=EIGHTH, eyes="happy", mouth="grin"),  # "Yes!"
        *(
            juno_cue(w, "cheer-b" if i % 2 == 0 else "cheer-a", ease=EIGHTH, eyes="happy", mouth="grin")
            for i, w in enumerate(GROOVE.beats(11, 13, every=0.5))
            if w > P[10].start
        ),
        juno_cue(ERROR, "clasp", eyes="squint", mouth="flat"),
    ],
    "juno",
)
LAMP_TALK = [(p.start, p.end) for p in P if p.role == "lamp"]
room = blob.home(
    cv,
    ep.comp,
    lamp_talk=LAMP_TALK,
    on_sofa=lambda g: blob.pip(
        cv, g, pip_cues, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=True
    ),
)
blob.juno(cv, room, juno_cues, end=DURATION, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=True)

# Push in on the lamp for "She said yes." and for the last line; the lamp stays put, the room grows around it.
camera.anchor(room, *LAMP_SHADE, place=True)
SNAP, CUT = 0.2, 1 / FPS
camera.push_in(
    cv,
    room,
    scale=[
        (0.0, 1.0),
        (P[9].start - 0.1, 1.0),
        (P[9].start + SNAP - 0.1, 1.35),
        (P[10].start, 1.35),
        (P[10].start + CUT, 1.0),
        (P[12].start - 0.1, 1.0),
        (P[12].start + SNAP - 0.1, 1.5),
        (ERROR + 0.3, 1.5),
        (ERROR + 0.3 + CUT, 1.0),
    ],
)
GREY, GREEN, RED, AMBER = "#9A938C", "#4CB36B", "#E0503F", "#E3A33B"
soft_props.status_badge(
    cv,
    ep.comp,
    [
        BadgeState("listening", "LISTENING", GREY, WAKE, FLOWERS),
        BadgeState("flowers", "+ FLOWERS", GREEN, FLOWERS, RING),
        BadgeState("ring", "+ RING", AMBER, RING, P[9].start),
        BadgeState("yes", "ENGAGED", GREEN, P[9].start, ERROR),
        BadgeState("error", "PARDON?", RED, ERROR, DURATION),
    ],
    (520, 470, 380, 92),
    id="lamp-badge",
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
        ("marker-wake", WAKE, "The lamp wakes"),
        ("marker-flowers", FLOWERS, "Ordered: flowers"),
        ("marker-ring", RING, "Ordered: ring"),
        ("marker-error", ERROR, "Didn't catch that"),
    ]
)
ep.instagram(POSTS["smart-lamp"])
out = ep.finish()
ep.check_overlays(out, ["lamp-badge"])

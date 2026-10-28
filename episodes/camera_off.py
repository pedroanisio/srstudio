#!/usr/bin/env python3
"""Episode 08 — Camera Off, the second Soft episode.

    python3 camera_off_audio.py PROJECT --key-stdin < key   # Pip's song, the boss and effects → dialogue.json
    python3 camera_off.py PROJECT                            # → PROJECT/camera-off.scene.xml

Pip is on a video call, nodding along, very professional. The boss announces forty slides. Click: camera
off, and the song kicks in: hips, cheers, a wave at the camera nobody is watching. A chime: "Pip, can you
share your screen?" Frozen mid-cheer, he scrambles back to the chair and types like mad: "I was taking notes."
The badge over the laptop says what the call sees. Every pose lands on the beat.

Pip sings inside the composed song (ElevenLabs Music), so his mouth follows the song's loudness over the words
the speech-to-text check heard there: any cue held while he sings shows the sung mouth.
"""

import json
import os
from dataclasses import replace

from _common import project_root
from camera_off_audio import GROOVE
from srstudio import SOFT, Episode, EpisodeSpec, blob, layout
from srstudio.blob import FLOOR, SCALE, SEAT, Cue
from srstudio.soundtrack import SOFT_MOUTH, Soundtrack, mouth_states

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="camera-off",
        number="08",
        title="Camera Off — Pip 02",
        description="Pose-to-pose comedy on a beat: Pip turns his camera off in a meeting and dances, until the boss "
        "asks him to share his screen. Native vector animation; the song composed by ElevenLabs Music, the boss and "
        "effects by ElevenLabs.",
        root=project_root(__file__),
        seed=82028,
        style=SOFT,
        safe_area=layout.VERTICAL,  # captions and the call badge stay inside x 80–920, y 220–1420
    )
)
ep.audio(extra=[("music", "assets/music.wav", {"role": "music"})])
t, cv, at = ep.t, ep.cv, GROOVE.at
SING = "sing"
BEAT, EIGHTH = 0.3, 0.125  # in-between time before a pose lands on the beat (four drawings) or the eighth (two)
FPS = 15  # drawings a second in a move
RISE = 45  # how high a sit-down or stand-up arcs, in rig units
POP = 0.08  # overshoot of a landing on the beat
STAND, DANCE = (700.0, FLOOR), (660.0, FLOOR)
L = {i + 1: p for i, p in enumerate(t.phrases)}


def cue(when, pose, spot=None, ease=BEAT, **kw):
    """A cue at a spot in output pixels; Pip is drawn at ``SCALE``, so the rig's units are pixels / SCALE."""
    at_spot = {} if spot is None else {"x": spot[0] / SCALE, "y": spot[1] / SCALE}
    return Cue(when, pose, ease=ease if when else 0.0, **at_spot, **kw)


# Bars 0–1: camera on. Nodding along on the beat, very professional.
cues = [cue(0, "sit", SEAT, eyes="look")]
cues += [
    cue(when, "nod" if i % 2 == 0 else "sit", SEAT, ease=EIGHTH, eyes="look", mouth="smile")
    for i, when in enumerate(GROOVE.beats(0, 2)[1:6])
]
cues += [
    cue(at(1, 2), "sit", SEAT, ease=EIGHTH, eyes="squint", mouth="smile", turn=-3),
    cue(at(1, 3), "nod", SEAT, ease=EIGHTH, eyes="squint", mouth="smile"),
]
# Bar 2: the boss. Forty slides.
cues += [
    cue(at(2), "sit", SEAT, eyes="look", mouth="smile"),
    cue(at(2, 2.5), "nod", SEAT, ease=EIGHTH, eyes="wide", mouth="o"),
]
# Bar 3: reach for the laptop, click, camera off; up out of the chair.
cues += [
    cue(at(3), "type-a", SEAT, eyes="squint", mouth="grin"),
    cue(at(3, 1), "type-b", SEAT, ease=EIGHTH, eyes="squint", mouth="grin"),
    cue(at(3, 3), "stand", STAND, eyes="happy", mouth="grin", lift=RISE),
]
# Bar 4: hips on every beat. Bar 5: cheers. Bar 6: waving at the camera nobody is watching. Bar 7: both.
cues += [
    cue(
        when,
        ("groove-a", "groove-c", "groove-b", "groove-c")[i % 4],
        DANCE,
        eyes="closed",
        mouth="grin",
        turn=(-4, 0, 4, 0)[i % 4],
        overshoot=POP,
    )
    for i, when in enumerate(GROOVE.beats(4, 5))
]
cues += [
    cue(
        when,
        "cheer-a" if i % 2 == 0 else "cheer-b",
        DANCE,
        eyes="happy",
        mouth="grin",
        overshoot=POP if i % 2 == 0 else 0,
    )
    for i, when in enumerate(GROOVE.beats(5, 6))
]
cues += [
    cue(when, "wave-a" if i % 2 == 0 else "wave-b", DANCE, ease=EIGHTH, eyes="happy", mouth="grin", turn=-8)
    for i, when in enumerate(GROOVE.beats(6, 7, every=0.5))
]
cues += [
    cue(
        when,
        ("cheer-a", "groove-c", "cheer-a", "cheer-b")[i % 4],
        DANCE,
        eyes="closed",
        mouth="grin",
        overshoot=POP if i % 2 == 0 else 0,
    )
    for i, when in enumerate(GROOVE.beats(7, 8))
]
# Bar 8: the chime cuts the move (no in-betweens): frozen mid-cheer while the boss asks.
cues += [
    cue(at(8), "cheer-a", DANCE, ease=0, eyes="wide", mouth="flat"),
    cue(at(8, 3), "cheer-a", DANCE, ease=0, eyes="look", mouth="o", turn=-5),
]
# Bars 9–10: back in the chair, typing like mad on the eighths.
cues += [
    cue(at(9), "sit", SEAT, eyes="wide", mouth="flat", lift=RISE),
    *(
        cue(when, "type-a" if i % 2 == 0 else "type-b", SEAT, ease=EIGHTH, eyes="wide", mouth="grin")
        for i, when in enumerate(GROOVE.beats(9, 11, every=0.5)[2:])
    ),
]
# Bar 11: very professional again.
cues += [
    cue(at(11), "nod", SEAT, eyes="squint", mouth="smile"),
    cue(at(11, 1), "sit", SEAT, ease=EIGHTH, eyes="look", mouth="smile"),
    cue(at(11, 2), "nod", SEAT, ease=EIGHTH, eyes="look", mouth="smile"),
    cue(at(11, 3), "sit", SEAT, ease=EIGHTH, eyes="squint", mouth="grin"),
]

# A move cannot start before the previous pose has landed (and settled, after an overshoot): each ease is capped
# to the time left before its cue.
settled = [c.time + (1 / FPS + 1e-3 if c.overshoot else 0) for c in cues]
cues = [replace(c, ease=min(c.ease, c.time - s)) for s, c in zip([0.0, *settled], cues, strict=False)]

# Pip's words, as heard in the composed song. A cue whose hold overlaps a sung word shows the sung mouth.
dialogue = json.loads((ep.root / "dialogue.json").read_text())
words = [(w[1], w[2]) for p in dialogue["phrases"] if p.get("sung") for w in p["words"]]
holds = zip(cues, [c.time for c in cues[1:]] + [t.duration], strict=True)
cues = [replace(c, mouth=SING) if any(a < until and c.time < b for a, b in words) else c for c, until in holds]
music = Soundtrack(ep.root / "assets" / "music.wav")

blob.office(cv, ep.comp)
blob.pip(
    cv,
    ep.comp,
    cues,
    end=t.duration,
    scale=SCALE,
    mouth_states=mouth_states(music, t, "pip", ep.spec.fps, style=SOFT_MOUTH, speaking=words),
    fps=FPS,
    shadow=True,
)

# The call badge over the laptop: what the meeting sees.
BADGE = (150, 830, 380, 92)  # x, y, width, height in output pixels (text sizes are integers)
GREEN, GREY, AMBER, RED = "#4CB36B", "#9A938C", "#E3A33B", "#E0503F"
SHARE = L[9].end
STATES = [
    ("cam-on", "CAM ON", GREEN, 0.0, t.click_start),
    ("cam-off", "CAM OFF", GREY, t.click_start, t.chime_start),
    ("share-ask", "SHARE?", AMBER, t.chime_start, SHARE),
    ("sharing", "SHARING", RED, SHARE, t.duration),
]
badge = cv.group(ep.comp, "call-badge")
x, y, w, h = BADGE
for name, label, dot, start, end in STATES:
    g = cv.group(badge, f"badge-{name}", x=x + w / 2, y=y + h / 2)
    cv.gate(g, [(start, end)])
    cv.pop_in(g, start)
    cv.rect(g, -w / 2, -h / 2, w, h, cv.white, stroke=cv.ink, sw=4, radius=h / 2)
    cv.ellipse(g, -w / 2 + 36, -17, 34, 34, dot, stroke=cv.ink, sw=3)
    if name == "cam-off":  # the camera dot is struck through
        cv.line(g, -w / 2 + 35, 18, -w / 2 + 71, -18, cv.ink, 4)
    cv.text(g, f"badge-{name}-text", label, -w // 2 + 88, -h // 2, w - 104, h, 46, color=cv.ink)

specs, boss = [], []
for i, p in enumerate(t.phrases):
    until = t.phrases[i + 1].start if i + 1 < len(t.phrases) else at(12)
    if i + 1 == 7:
        until = at(8)  # "Best meeting ever!" holds until the chime
    (boss if p.role == "boss" else specs).append((max(0.0, p.start - 0.05), until, p.caption, f"lyric-{i + 1}"))
caption_style = dict(x=80, y=250, width=840, height=180, size=58, stroke="#FFFFFF", stroke_width=7, shadow=None)
ep.captions(specs, color="#1A1714", **caption_style)
ep.captions(boss, color="#2F5D8C", **caption_style)
ep.markers(
    extra=[("marker-click", t.click_start, "Camera off"), ("marker-chime", t.chime_start, "Screen-share request")]
)
ep.finish()

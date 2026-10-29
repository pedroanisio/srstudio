#!/usr/bin/env python3
"""Episode 07 — Focus Mode, the first episode in the Soft style.

    python3 focus_mode_audio.py PROJECT --key-stdin < key   # lines, scratch and composed music → dialogue.json
    python3 focus_mode.py PROJECT                            # → PROJECT/focus-mode.scene.xml

Pip sits down to work, types for one bar, and the groove wins: a happy sway, a wiggle against the
chair, hands behind the head. A record scratch, "Hold on. The deadline." He sits, eyes wide: "Focus."
He checks the screen: "Wait. It was yesterday." A frozen beat, and the music drops back in: nothing left
to lose, he dances bigger ("Shake it to the beat!") and side-steps out of frame. Every pose lands on the beat.
"""

import os
from functools import partial

from _common import project_root
from focus_mode_audio import GROOVE, MUSIC_GAIN, PLAYS, music_spans
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, layout
from srstudio.blob import FLOOR, SCALE, SEAT

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="focus-mode",
        number="07",
        title="Focus Mode — Pip 01",
        description="Pose-to-pose comedy on a beat: Pip tries to work and dances instead. Native vector animation; "
        "ElevenLabs voice and scratch, music composed with ElevenLabs Music.",
        root=project_root(__file__),
        seed=72028,
        style=SOFT,
        safe_area=layout.VERTICAL,  # the top captions stay inside x 80–920, y 220–1420
    )
)
t, cv, at = ep.t, ep.cv, GROOVE.at
# The composed song is heard only in its bars (the cut, not the take, makes the silence), its beats on the grid.
music = t.meta["music"]
(first, *rest) = music_spans(music["tempo"]["phase"], music["duration"])
s0, in0, out0 = first
mix = ep.audio(
    extra=[
        ("music", music["file"], dict(role="music", start=s0, clipIn=in0, clipOut=out0, gain=MUSIC_GAIN, fadeOut=0.03))
    ]  # fmt: skip
)
if mix is None:
    raise SystemExit("focus-mode: dialogue.json has no clips; run focus_mode_audio.py first")
for n, (start, clip_in, clip_out) in enumerate(rest, 2):
    mix.add_audioTrack(id=f"track-music-{n}", asset="music", role="music", start=start, clipIn=clip_in,
                       clipOut=clip_out, gain=MUSIC_GAIN, fadeOut=0.3)  # fmt: skip
SING = "sing"
BEAT, EIGHTH = 0.3, 0.125  # in-between time before a pose lands on the beat (four drawings) or the eighth (two)
FPS = 15  # drawings a second in a move
RISE = 45  # how high a sit-down or stand-up arcs, in rig units
POP = 0.08  # overshoot of a landing on the beat
# Standing spots sit in front of the chair (lower on screen = nearer the viewer), so Pip never stands inside it.
STAND, LEAN, DANCE = (700.0, FLOOR), (720.0, FLOOR - 10), (660.0, FLOOR)


cue = partial(blob.cue, scale=SCALE, ease=BEAT)  # spots in output pixels; Pip is drawn at SCALE


cues = [
    cue(0, "stand", STAND),
    cue(at(0, 0.5), "stand", STAND, ease=0, mouth=SING),
    cue(at(0, 2), "sit", SEAT, mouth=SING, lift=RISE),
]
# Bar 1: typing, the hands swapping every eighth note.
cues += [
    cue(when, "type-a" if i % 2 == 0 else "type-b", SEAT, ease=EIGHTH, mouth=SING)
    for i, when in enumerate(GROOVE.beats(1, 2, every=0.5))
]
# Bar 2: up from the chair, a happy sway; bar 3: wiggling against the chair back.
cues += [
    cue(
        when,
        "clasp",
        STAND,
        eyes="squint",
        mouth=SING,
        turn=5 if i % 2 else -5,
        lift=RISE if i == 0 else 0,
        overshoot=POP,
    )
    for i, when in enumerate(GROOVE.beats(2, 3))
]
cues += [
    cue(when, "lean", (LEAN[0], LEAN[1] - (14 if i % 2 else 0)), eyes="squint", mouth=SING, turn=-6 if i % 2 else 0)
    for i, when in enumerate(GROOVE.beats(3, 4))
]
# Bars 4–5: hands behind the head, the hips on every beat.
for i, when in enumerate(GROOVE.beats(4, 6)):
    sung = when < t.phrases[4].end
    cues.append(
        cue(
            when,
            ("groove-a", "groove-c", "groove-b", "groove-c")[i % 4],
            DANCE,
            eyes="closed" if sung else "happy",
            mouth=SING if sung else "grin",
            turn=(-4, 0, 4, 0)[i % 4],
            overshoot=POP,
        )
    )
# Bars 6–7: the scratch cuts the move (no in-betweens); frozen, then back in the chair.
P5, P6 = t.phrases[5], t.phrases[6]
cues += [
    cue(at(6), "stand", STAND, ease=0, eyes="wide", mouth="flat"),
    cue(P5.start, "stand", STAND, ease=0, eyes="look", mouth=SING),
    cue(at(7), "sit", SEAT, eyes="wide", mouth=SING, lift=RISE),
    cue(P6.end + 0.1, "type-a", SEAT, ease=EIGHTH, eyes="wide", mouth="o"),
]
# Bar 8: a look at the screen, "Wait. It was yesterday.", then a frozen stare until the drop.
P7 = t.phrases[7]
cues += [
    cue(at(8), "type-a", SEAT, ease=0, eyes="wide", mouth=SING),
    cue(P7.end + 0.1, "sit", SEAT, ease=0, eyes="wide", mouth="flat"),
]
# Bars 9–10: nothing left to lose. Up on the drop and the groove again, bigger; the callback sung on the way up.
DROP, OUT = PLAYS[1][0], PLAYS[1][1] - 1
for i, when in enumerate(GROOVE.beats(DROP, OUT)):
    sung = when < t.phrases[8].end
    cues.append(
        cue(
            when,
            ("groove-a", "groove-c", "groove-b", "groove-c")[i % 4],
            DANCE,
            eyes="happy" if sung else "closed",
            mouth=SING if sung else "grin",
            turn=(-6, 0, 6, 0)[i % 4],
            lift=RISE if i == 0 else 0,
            overshoot=POP * 1.5,
        )
    )
# Bar 11: eyes shut, he side-steps out of frame on the eighths, one foot always planted.
cues.append(cue(at(OUT), "stand", (760.0, FLOOR), eyes="closed", mouth="grin"))
WALK = (("walk-a", "leg_l"), ("stride", "leg_l"), ("walk-b", "leg_r"), ("stand", "leg_r"))
cues += [
    cue(when, WALK[i % 4][0], ease=EIGHTH, eyes="closed", pin=WALK[i % 4][1])
    for i, when in enumerate(GROOVE.beats(OUT, OUT + 1, every=0.5)[1:] + [at(OUT + 1)])
]

cues = blob.settle(cues, FPS, published_full_gap_ease=True)  # no move starts before the previous pose has landed

blob.office(cv, ep.comp)
blob.pip(cv, ep.comp, cues, end=t.duration, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=True)

specs = []
for i, p in enumerate(t.phrases):
    until = t.phrases[i + 1].start if i + 1 < len(t.phrases) else at(OUT)
    if i == 4:
        until = at(6)  # "Shake it to the beat!" holds through the dance, until the scratch
    specs.append((max(0.0, p.start - 0.05), until, p.caption, f"lyric-{i + 1}"))
ep.captions(
    specs, x=80, y=250, width=840, height=180, size=58, color="#1A1714", stroke="#FFFFFF", stroke_width=7, shadow=None
)
ep.markers(extra=[("marker-scratch", t.scratch_start, "Record scratch"), ("marker-return", at(DROP), "The drop")])
ep.instagram(POSTS["focus-mode"])
ep.finish()

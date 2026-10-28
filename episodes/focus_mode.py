#!/usr/bin/env python3
"""Episode 07 — Focus Mode, the first episode in the Soft style.

    python3 focus_mode_audio.py PROJECT --key-stdin < key   # sung lines, scratch and groove → dialogue.json
    python3 focus_mode.py PROJECT                            # → PROJECT/focus-mode.scene.xml

Pip sits down to work, types for one bar, and the groove wins: a happy sway, a wiggle against the
chair, hands behind the head. A record scratch, "Hold on. The deadline." He sits, eyes wide: "Focus."
The groove creeps back, his eyes close, and he side-steps out of frame. Every pose lands on the beat.
"""

import os
from dataclasses import replace

from _common import project_root
from focus_mode_audio import GROOVE
from srstudio import SOFT, Episode, EpisodeSpec, blob, layout
from srstudio.blob import FLOOR, SCALE, SEAT, Cue

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="focus-mode",
        number="07",
        title="Focus Mode — Pip 01",
        description="Pose-to-pose comedy on a beat: Pip tries to work and dances instead. Native vector animation; "
        "ElevenLabs vocals and scratch, music synthesised by srstudio.",
        root=project_root(__file__),
        seed=72028,
        style=SOFT,
        safe_area=layout.VERTICAL,  # the top captions stay inside x 80–920, y 220–1420
    )
)
ep.audio(extra=[("groove", "assets/groove.wav", {"role": "music"})])
t, cv, at = ep.t, ep.cv, GROOVE.at
SING = "sing"
BEAT, EIGHTH = 0.3, 0.125  # in-between time before a pose lands on the beat (four drawings) or the eighth (two)
FPS = 15  # drawings a second in a move
RISE = 45  # how high a sit-down or stand-up arcs, in rig units
POP = 0.08  # overshoot of a landing on the beat
# Standing spots sit in front of the chair (lower on screen = nearer the viewer), so Pip never stands inside it.
STAND, LEAN, DANCE = (700.0, FLOOR), (720.0, FLOOR - 10), (660.0, FLOOR)


def cue(when, pose, spot=None, ease=BEAT, **kw):
    """A cue at a spot in output pixels (none for a pinned cue); Pip is drawn at ``SCALE``, so the rig's units are
    pixels / SCALE."""
    at_spot = {} if spot is None else {"x": spot[0] / SCALE, "y": spot[1] / SCALE}
    return Cue(when, pose, ease=ease if when else 0.0, **at_spot, **kw)


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
# Bars 8–9: the groove creeps back; eyes shut, he side-steps out of frame on the eighths, one foot always planted.
cues += [
    cue(at(8), "type-a", SEAT, eyes="closed", mouth="smile"),
    cue(at(8, 2), "sit", SEAT, eyes="closed", mouth="smile", turn=4),
    cue(at(9), "stand", (760.0, FLOOR), eyes="closed", lift=RISE),
]
WALK = (("walk-a", "leg_l"), ("stride", "leg_l"), ("walk-b", "leg_r"), ("stand", "leg_r"))
cues += [
    cue(when, WALK[i % 4][0], ease=EIGHTH, eyes="closed", pin=WALK[i % 4][1])
    for i, when in enumerate(GROOVE.beats(9, 10, every=0.5)[1:] + [at(10)])
]

# A move cannot start before the previous pose has landed (and settled, after an overshoot): each ease is capped
# to the time left before its cue.
settled = [c.time + (1 / FPS + 1e-3 if c.overshoot else 0) for c in cues]
cues = [replace(c, ease=min(c.ease, c.time - s)) for s, c in zip([0.0, *settled], cues, strict=False)]

blob.office(cv, ep.comp)
blob.pip(cv, ep.comp, cues, end=t.duration, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=True)

specs = []
for i, p in enumerate(t.phrases):
    until = t.phrases[i + 1].start if i + 1 < len(t.phrases) else at(8)
    if i == 4:
        until = at(6)  # "Shake it to the beat!" holds through the dance, until the scratch
    specs.append((max(0.0, p.start - 0.05), until, p.caption, f"lyric-{i + 1}"))
ep.captions(
    specs, x=80, y=250, width=840, height=180, size=58, color="#1A1714", stroke="#FFFFFF", stroke_width=7, shadow=None
)
ep.markers(extra=[("marker-scratch", t.scratch_start, "Record scratch"), ("marker-return", at(8), "Groove returns")])
ep.finish()

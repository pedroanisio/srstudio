#!/usr/bin/env python3
"""Episode 10 — Off and On, Pip 03: Juno, Remy and Pip in the polished meeting room and break room.

    python3 off_and_on_audio.py PROJECT --key-stdin < key   # Remy's composed jingle, three voices, six effects
    python3 off_and_on.py PROJECT                            # → PROJECT/off-and-on.scene.xml

Juno smacks the blinking coffee machine: "Remy! The coffee machine is broken!" Remy, from IT, spins to camera like
an infomercial host and sings his one fix: "Turn it off and on again!" Click, click: green light, coffee. Pip, slumped
on the stool: "It's Monday. I'm broken." Remy, again: "Lights off!" (the room goes dark; two pairs of eyes) "Lights
on!" Pip sits bolt upright and does not blink: "Hello. I love Mondays." Juno backs away. Then Remy's own screen dies.
He calls the IT hotline, which plays hold music and asks: "Have you tried turning it off and on again?" He tries
the keys, sighs, and belts the finale: "Somebody reboot me!" He shuts down, the room goes dark, REBOOTING... and he
starts up again, grinning, with his screen back on.
"""

import os
from functools import partial

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, graphics, layout
from srstudio.blob import BREAK_STAND, FLOOR, SCALE, SEAT, WALL_DECOR, room_point, wall_quad

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="off-and-on",
        number="10",
        title="Off and On — Pip 03",
        description="Pose-to-pose comedy on a beat: IT support's one fix, sung as an infomercial jingle, applied to "
        "a coffee machine, a colleague and finally himself. Native vector animation in the polished Soft meeting "
        "room and break room; music and Remy's vocal from the ElevenLabs Music API, voices and effects from "
        "ElevenLabs.",
        root=project_root(__file__),
        seed=102028,
        style=SOFT,
        safe_area=layout.VERTICAL,  # the top captions and the marks stay inside x 80–920, y 220–1420
    )
)
t = ep.t
P, DURATION = t.phrases, t.duration
# The composed master is dense: without ducking it masks every spoken line (speech spans measured -18.8 dB against
# -19.2 dB for the music alone), so it dips under the spoken tracks; Remy's sung lines are in the music itself.
ep.audio(extra=[("music", "assets/music.wav", {"role": "music", "gain": -8})], duck=-8)  # under the spoken lines
cv = ep.cv
RESET, BREW, DARK, LIGHT = t.reset_start, t.brew_start, t.dark_start, t.light_start
DIES, STARTUP = t.screen_dies_start, t.startup_start
SING = "sing"
EIGHTH = 0.125  # in-between time before a pose lands on the eighth (two drawings)
BEAT = 0.3  # ... or on the beat (four drawings)
FPS = 15
POP = 0.08  # overshoot of a landing on the beat


MEETING, BREAK, BLACKOUT = t.shots({"meeting"}), t.shots({"break"}), t.shots({"dark"})


cue = partial(blob.cue, scale=SCALE, ease=BEAT)  # spots in output pixels; the cast is drawn at SCALE


def perform(make, parent, cues, mouths, id):
    make(
        cv, parent, blob.settle(cues, FPS), end=DURATION, scale=SCALE, mouth_states=mouths, id=id, fps=FPS, shadow=True
    )


def beats(start, end, every=0.5):
    """Beat times from ``start`` (on the grid) up to ``end``."""
    out, k = [], 0
    while start + k * every < end - 1e-6:
        out.append(start + k * every)
        k += 1
    return out


# -- the meeting room: Remy, the wall screen, the reboot -------------------------------------------------------
meeting = cv.group(ep.comp, "meeting")
cv.gate(meeting, MEETING)
blob.meeting_room(cv, meeting)
_, a0, a1, u0, u1 = WALL_DECOR["meeting-screen"]
dead = cv.group(meeting, "screen-dead")
cv.gate(dead, [(DIES + 0.12, STARTUP)])
pts = wall_quad("back", a0 + 16, a1 - 16, u0 + 16, u1 - 16)
cv.path(dead, "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z", "#15171D")

remy = [
    cue(0, "type-a", SEAT, eyes="look"),
    # The jingle's intro: he stops typing, swivels to camera and becomes an infomercial host.
    cue(3.0, "sit", SEAT, ease=EIGHTH, eyes="look", mouth="small", turn=-4),
    cue(3.5, "sit", SEAT, eyes="open", mouth="smile"),
    cue(4.0, "clasp", SEAT, eyes="squint", mouth="grin", overshoot=POP),
    cue(5.0, "wave-a", SEAT, eyes="happy", mouth="grin", overshoot=POP),
]
remy += [
    cue(w, ("cheer-a", "cheer-b")[i % 2], SEAT, ease=EIGHTH, eyes="happy", mouth=SING, overshoot=POP)
    for i, w in enumerate(beats(6.0, P[1].end))
]
remy += [
    cue(P[1].end + 0.05, "clasp", SEAT, eyes="happy", mouth="grin"),
    # Back for round two: he has heard about Pip.
    cue(12.0, "type-a", SEAT, ease=0, eyes="look", mouth="smile"),
    cue(12.5, "sit", SEAT, eyes="open", mouth="smile"),
    cue(13.0, "clasp", SEAT, eyes="squint", mouth="grin", overshoot=POP),
    cue(P[3].start, "wave-a", SEAT, ease=EIGHTH, eyes="happy", mouth=SING, lift=20, overshoot=POP),
    # His own screen dies; he calls the hotline; he tries the keys; he sighs.
    cue(19.25, "type-a", SEAT, ease=0, eyes="look", mouth="smile"),
    cue(DIES + 0.12, "type-a", SEAT, ease=0, eyes="wide", mouth="o"),
    cue(P[5].start - 0.3, "sit", SEAT, ease=0.2, eyes="look", mouth="flat", turn=-4),  # on the line to IT
    cue(P[5].end + 0.15, "sit", SEAT, ease=0.2, eyes="open", mouth="flat"),  # the stare
]
remy += [
    cue(w, ("type-a", "type-b")[i % 2], SEAT, ease=EIGHTH, eyes="squint", mouth="flat")
    for i, w in enumerate(beats(23.0, 24.0, 0.25))
]
remy += [
    cue(24.0, "sit", SEAT, ease=0.2, eyes="closed", mouth="flat", turn=6),  # the sigh
    cue(25.5, "clasp", SEAT, eyes="closed", mouth="flat"),
]
remy += [
    cue(w, ("cheer-a", "cheer-b")[i % 2], SEAT, ease=EIGHTH, eyes="closed", mouth=SING, overshoot=POP)
    for i, w in enumerate(beats(26.0, P[6].end))
]
remy += [
    cue(P[6].end + 0.05, "sit", SEAT, ease=0.25, eyes="closed", mouth="flat", turn=10),  # shut down
    cue(STARTUP, "cheer-a", SEAT, ease=0, eyes="happy", mouth="grin", overshoot=POP),  # started up
    cue(STARTUP + 0.5, "cheer-b", SEAT, ease=EIGHTH, eyes="happy", mouth="grin"),
]
perform(blob.remy, meeting, remy, ep.mouth("remy"), "remy")

shutdown = cv.group(meeting, "remy-shutdown")
cv.gate(shutdown, [(P[6].end + 0.3, STARTUP)])
cv.rect(shutdown, 0, 0, 1080, 1920, "#11131C", opacity=0.82)

# -- the break room: the machine, the stool, the reboot --------------------------------------------------------
brk = cv.group(ep.comp, "break")
cv.gate(brk, BREAK)
blob.break_room(cv, brk)

machine = cv.group(brk, "machine-state")
lx, ly = room_point(-186, 116, 547)  # the machine's status light
broken = cv.ellipse(machine, lx - 9, ly - 9, 18, 18, "#E8574A", cv.ink, 2)
cv.gate(broken, [(0, RESET + 0.18)])
cv.expression(broken, "opacity", ".55+.45*Math.sign(Math.sin(time*14))")  # a blinking red light: broken
gx, gy = room_point(-233, 106, 368)  # the carafe's mouth
pour = cv.rect(machine, gx - 4, gy - 120, 8, 104, "#5A3420", radius=4)
cv.gate(pour, [(BREW, BREW + 0.9)])
steam = cv.group(machine, "machine-steam")
cv.gate(steam, [(BREW + 0.3, DURATION)])
for i, dx in enumerate((-16, 4, 22)):
    wisp = cv.path(steam, f"M {gx + dx:.1f} {gy - 130:.1f} q -14 -24 0 -48 q 14 -24 0 -48", None, "#FFFFFF", 6)
    cv.expression(wisp, "opacity", f".2+.5*Math.abs(Math.sin(time*2.4+{i * 1.3:.1f}))")

JUNO = (BREAK_STAND[0] - 40, FLOOR)
juno = [
    cue(0, "wave-a", JUNO, eyes="squint", mouth="flat", turn=-10)  # smack
]
juno += [
    cue(w, ("wave-b", "wave-a")[i % 2], JUNO, ease=EIGHTH, eyes="wide", mouth=SING, turn=(0, -10)[i % 2])
    for i, w in enumerate(beats(P[0].start, P[0].end))
]
juno += [
    cue(P[0].end + 0.1, "stand", JUNO, ease=EIGHTH, eyes="look", mouth="o"),
    # Round one: the fix, clicked twice, and coffee.
    cue(8.0, "stand", JUNO, ease=0, eyes="squint", mouth="flat", turn=-6),
    cue(RESET, "wave-a", JUNO, ease=0.15, eyes="squint", mouth="flat", turn=-10, overshoot=POP),
    cue(RESET + 0.25, "wave-b", JUNO, ease=EIGHTH, eyes="squint", mouth="flat", turn=-10),
    cue(BREW, "clasp", JUNO, eyes="wide", mouth="o", overshoot=POP),
    cue(BREW + 0.5, "cheer-a", JUNO, ease=EIGHTH, eyes="happy", mouth="grin", lift=30, overshoot=POP),
    cue(P[2].start - 0.2, "stand", JUNO, ease=0.2, eyes="look", mouth="small", flip=True),
    cue(P[2].end + 0.2, "clasp", JUNO, eyes="squint", mouth="small", flip=True),
    # Lights on: she has not moved. Then the robot speaks, and she backs away.
    cue(LIGHT, "clasp", JUNO, ease=0, eyes="wide", mouth="small", flip=True),
    cue(P[4].start + 0.6, "clasp", JUNO, ease=0, eyes="wide", mouth="o", flip=True),
    cue(P[4].end + 0.05, "step", (JUNO[0] - 70, FLOOR), ease=0.3, eyes="wide", mouth="flat", flip=True),
]
perform(blob.juno, brk, juno, ep.mouth("juno"), "juno")


def spliced(before, after, at):
    """``before``'s mouth states until ``at``, then ``after``'s (Pip's own voice, then the rebooted one)."""
    head = [s for s in before if s[0] < at]
    lead = [(at, state) for when, state in after if when < at][-1:]
    return head + lead + [s for s in after if s[0] >= at]


pip = [
    cue(0, "lounge", SEAT, eyes="closed", mouth="flat"),
    cue(BREW + 0.2, "lounge", SEAT, ease=0, eyes="look", mouth="flat"),
    cue(P[2].start, "lounge", SEAT, ease=0, eyes="look", mouth=SING, turn=-3),
    cue(P[2].end + 0.1, "lounge", SEAT, ease=0, eyes="closed", mouth="flat", turn=-6),
    # Rebooted: bolt upright, unblinking, a head that snaps rather than turns.
    cue(LIGHT, "sit", SEAT, ease=0, eyes="wide", mouth="flat"),
    cue(P[4].start, "sit", SEAT, ease=0, eyes="wide", mouth=SING),
    cue(P[4].start + 0.9, "sit", SEAT, ease=0, eyes="wide", mouth=SING, turn=8),
    cue(P[4].end + 0.05, "sit", SEAT, ease=0, eyes="wide", mouth="grin", turn=8),
]
perform(blob.pip, brk, pip, spliced(ep.mouth("pip"), ep.mouth("robot"), LIGHT), "pip")

# -- the dark: two pairs of eyes while Remy sings "Lights on!" ------------------------------------------------
dark = cv.group(ep.comp, "dark")
cv.gate(dark, BLACKOUT)
cv.rect(dark, 0, 0, 1080, 1920, "#11131C")
for name, (ex, ey), blink in (("juno", (282, 870), 0.35), ("pip", (713, 865), 0.6)):
    pair = cv.group(dark, f"eyes-{name}", x=ex, y=ey)
    for dx in (-48, 48):
        cv.ellipse(pair, dx - 17, -22, 34, 44, "#FFFFFF")
        cv.ellipse(pair, dx - 7 + (-6 if name == "pip" else 6), -8, 14, 18, "#11131C")
    b = DARK + blink
    cv.keys(pair, "scaleY", [(0, 1), (b, 1), (b + 0.07, 0.1), (b + 0.14, 1)], hold=False)

graphics.squeak_mark(
    cv,
    ep.comp,
    "REBOOTING...",
    show=(P[6].end + 0.3, STARTUP),
    x=540,
    y=1150,
    w=440,
    h=100,
    size=56,
    rotation=-4,
    id="reboot-mark",
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
        ("marker-reset", RESET, "Machine reset"),
        ("marker-dark", DARK, "Lights off"),
        ("marker-light", LIGHT, "Lights on"),
        ("marker-screen", DIES, "Remy's screen dies"),
        ("marker-startup", STARTUP, "Remy reboots"),
    ]
)
ep.instagram(POSTS["off-and-on"])
out = ep.finish()
ep.check_overlays(out, ["reboot-mark"])

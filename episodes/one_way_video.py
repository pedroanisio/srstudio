#!/usr/bin/env python3
"""One Way Video, built with srstudio: a recording that asks for a person and picks the wrong one.

    srstudio record one-way-video PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build one-way-video PROJECT    # → PROJECT/one-way-video.scene.xml

From the laptop: his face, huge, smiling at the lens with a countdown running. "Why are you the right person? Thirty
seconds." "Hi! Hello. There's nobody there. Hi." "Eye contact: low." He stares at the dot, and the door opens behind
him: Milo, cereal. "I'm a people person." "Smile: forty percent sincere." Milo comes closer, chewing. "Milo, go away,"
through his teeth, still smiling. "Who are you talking to?" "Second candidate detected." "No. No, no." Another
spoonful, straight into the lens, a wave of the spoon. "Hey." "Confidence: excellent." Chewing, and a green tick.
"Congratulations, Milo." "For what?"

The whole reel is the invented window. The room is the home study pushed in, so that its desk runs along the foot of
the shot under the two of them. No music: the foley is synthesized here. It declares no engine safe area, so captions
are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from one_way_video_audio import INTERVIEW
from srstudio import (
    OFFICE,
    Episode,
    EpisodeSpec,
    cast,
    cutout_arm,
    cutout_home,
    cutout_key,
    cutout_recording,
    foley,
    locations,
    look,
    signature,
)
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="one-way-video",
        title=INTERVIEW.title,
        description="Job-hunting comedy: a one-way video interview scores a candidate's smile while his housemate "
        "walks in behind him with a bowl of cereal. Native vector animation; ElevenLabs dialogue, synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=3315,
        background="#14171C",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        bleed=True,
    )
)
t, cv = ep.t, ep.cv
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
DOOR, NEAR, SPOON, TICK = (float(t.meta[k]) for k in ("door", "near", "spoon", "tick"))

ROOM = 1.6  # the study pushed in: its desk at 1536, below the shoulders
CANDIDATE = (360.0, 700.0, 3.0)
FAR = (832.0, 870.0, 1.36)  # Milo in the door, frame pixels
MID = (860.0, 760.0, 1.62)
CLOSE = (800.0, 670.0, 2.1)
ARRIVE = DOOR + 0.2
STEPS = (L[3].start + 0.2, L[4].end - 0.2)  # into the room
OVER = (NEAR, L[5].start + 0.5)  # over his shoulder
SPOONFULS = (DOOR + 0.55, L[4].start + 0.1, SPOON)
BOWL_GRIP = (2.0, 276.0)
CHEW_STEP = 0.17

CHEWS = [(SPOONFULS[0] + 0.55, L[6].start - 0.1), (L[6].end + 0.1, L[9].start - 0.05),
         (L[9].end + 0.1, L[12].start - 0.05), (L[12].end + 0.1, DURATION)]  # fmt: skip
chew_times = [a + 0.34 * n for a, b in CHEWS for n in range(int((b - a) / 0.34))]

foley.write_bursts(ROOT / "assets" / "door.wav", [DOOR + 0.02], DURATION, foley.SCRAPE, seed=3316)
foley.write_bursts(
    ROOT / "assets" / "chew.wav",
    chew_times,
    DURATION,
    foley.Burst(0.1, 3200.0, attack=0.002, decay=0.3, tone_hz=240.0, tone_end_hz=190.0, tone=0.2),
    seed=3317,
)
foley.write_bursts(ROOT / "assets" / "spoon.wav", [s + 0.05 for s in SPOONFULS], DURATION, foley.PLATES, seed=3318)
foley.write_bursts(ROOT / "assets" / "tick.wav", [TICK], DURATION, foley.CHIRP, seed=3319)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("door", "assets/door.wav", {"role": "effects", "gain": -14}),
        ("chew", "assets/chew.wav", {"role": "effects", "gain": -16}),
        ("spoon", "assets/spoon.wav", {"role": "effects", "gain": -18}),
        ("tick", "assets/tick.wav", {"role": "effects", "gain": -12}),
    ],
    loudness="-14",
)


def chewing(states):
    """Milo's lines as spoken, and between them his mouth working on the cereal."""
    kept = [(at, state) for at, state in states if not any(a <= at < b for a, b in CHEWS)]
    for a, b in CHEWS:
        for n in range(int((b - a) / CHEW_STEP)):
            kept.append((a + n * CHEW_STEP, "small" if n % 2 else "rest"))
        kept.append((b, "rest"))
    return sorted(kept)


def through_teeth(states):
    """ "Milo, go away." with the smile held: his mouth never moves off it."""
    a, b = L[5].start, L[5].end
    return sorted([(at, state) for at, state in states if not a <= at < b] + [(a, "smile")])


def keep_at(track, loc=True):
    """Milo's walk, as keys on (x, y, scale); frame pixels, or the room's units with ``loc``."""
    scale = ROOM if loc else 1.0
    return ([(at, x / scale) for at, x, _, _ in track], [(at, y / scale) for at, _, y, _ in track],
            [(at, s / scale) for at, _, _, s in track])  # fmt: skip


WALK = [(0.0, *FAR), (STEPS[0], *FAR), (STEPS[1], *MID), (OVER[0], *MID), (OVER[1], *CLOSE)]


def milo(g):
    door = look.depth(cv, g, "door-depth", 3.0)
    cutout_recording.room_door(cv, door, 520, 960, opens=DOOR, scale=1.0)
    walking = cv.group(g, "milo-walks")
    cv.gate(walking, [(ARRIVE, DURATION)])
    xs, ys, sizes = keep_at(WALK)
    cv.keys(walking, "x", xs, hold=False)
    cv.keys(walking, "y", ys, hold=False)
    cv.keys(walking, "scaleX", sizes, hold=False)
    cv.keys(walking, "scaleY", sizes, hold=False)
    who = cast.Customer(cv, tag="milo-behind")
    node = ep.perform(
        who,
        walking,
        0,
        0,
        1.0,
        mouth=chewing(ep.mouth("customer")),
        blinks=[(L[7].start, L[7].start + 0.14), (L[12].end + 0.3, L[12].end + 0.44)],
        nods=[(0, 0), (L[12].start, 0), (L[12].start + 0.2, 3), (L[12].end, 0)],
        free_arms=("left", "right"),
    )
    look_at = [(0, -6), (OVER[0], -6), (OVER[1], -11), (SPOON, -11), (SPOON + 0.25, 0)]
    cv.keys(who.eyes, "x", look_at, hold=False)
    hold = cutout_arm.arm(
        cv, node, "milo-bowl-arm", (-68, 140), [(0.0, *BOWL_GRIP)], upper=92, fore=92, bend=-1, skin=who.skin, width=4
    )
    cutout_recording.cereal_bowl(cv, hold.grip, 0, -8, scale=0.66, id="milo-bowl")
    up, down = (12.0, 62.0), (10.0, 190.0)
    track = [(0.0, *down)]
    for at in SPOONFULS:
        track += [(at, *down), (at + 0.3, *up), (at + 0.5, *up), (at + 0.8, *down)]
    wave = L[9].start - 0.12
    high = (62.0, 196.0)
    track = [k for k in track if k[0] < wave - 0.25]
    track += [(wave, *high)] + [(wave + 0.18 * n, high[0] + (16 if n % 2 else -16), high[1]) for n in range(1, 9)]
    track += [(wave + 0.18 * 9, *down)]
    feed = cutout_arm.arm(
        cv, node, "milo-spoon-arm", (68, 141), track, upper=92, fore=92, bend=-1, skin=who.skin, width=4
    )
    cutout_recording.spoon(cv, feed.grip, 0, 0, scale=0.56, rotation=-20, id="milo-spoon")


def on_desk(g):
    signature.code(cv, g, 480, 985, 11, color="#5C625D")


def the_candidate(g):
    who = cast.Candidate(cv, tag="candidate-lens")
    x, y, size = CANDIDATE
    stare = [(L[0].end + 0.2, L[0].end + 0.34), (L[1].end - 0.4, L[1].end - 0.26), (L[8].end + 0.1, L[8].end + 0.24),
             (L[10].end + 0.5, L[10].end + 0.64)]  # fmt: skip
    smile = [(0.0, L[8].start)]
    node = ep.perform(
        who,
        g,
        x,
        y,
        size,
        mouth=through_teeth(ep.mouth("candidate", smile=smile)),
        blinks=stare,
        nods=[(0.0, -1.5), (0.5, 1.2), (1.0, -1.0), (1.5, 1.0), (2.2, 0.0), (L[8].start, 0.0), (L[8].start + 0.15, 2.5),
              (L[8].start + 0.3, -2.5), (L[8].start + 0.45, 2.0), (L[8].end, 0.0)],
    )  # fmt: skip
    cv.keys(node, "y", [(0.0, y + 18), (0.7, y), (DURATION, y)], hold=False, kind="sine-out")
    side = [(0, 0), (L[5].start, 0), (L[5].start + 0.12, 9), (L[8].end + 0.7, 9), (L[8].end + 0.9, 0)]
    cv.keys(who.eyes, "x", side, hold=False)


finish = locations.finish(cv, ep.comp)
video = cv.group(finish, "video")
screen = cv.group(ep.comp, "the-recording")
room = cv.group(video, "room", scaleX=ROOM, scaleY=ROOM)


def cactus(g):
    signature.cactus(cv, g, 603, 960, 0.62)  # far enough in that the slow push keeps it inside the recording


cutout_home.home_study(cv, room, behind_desk=milo, on_desk=on_desk, cactus=cactus)
the_candidate(cv.group(video, "candidate-at-the-lens"))
for prop, a, b in (("scaleX", 1.0, 1.05), ("scaleY", 1.0, 1.05), ("x", 0.0, -27.0), ("y", 0.0, -40.0)):
    cv.keys(video, prop, [(0.0, a), (DURATION, b)], hold=False)  # the slow push in

cutout_recording.face_box(cv, screen, CANDIDATE[0], CANDIDATE[1] - 8, 318, spans=[(0.0, TICK)], id="face-candidate")
milo_box = cv.group(screen, "face-milo-follows")
cv.gate(milo_box, [(L[7].start, DURATION)])
cutout_recording.face_box(cv, milo_box, 809, 665, 226, id="face-milo")
# A white shirt under white captions: the scrim stops short of the desk's right end, where the marks are.
shirt_scrim = cv.grad("shirt-scrim", [(0, "#14171C"), (0.75, "#14171C"), (1, "#14171C00")], (0, 0, 1, 0))
cv.rect(screen, 40, 1404, 720, 236, shirt_scrim, opacity=0.8)
cutout_recording.recording_window(cv, screen, seconds=30, end=DURATION, stop=TICK)
cutout_recording.meter_panel(
    cv,
    screen,
    80,
    1250,
    (
        ("EYES", ((0.0, 0.7), (L[2].start, 0.7), (L[2].start + 0.3, 0.15))),
        ("SMILE", ((0.0, 0.95), (L[4].start, 0.95), (L[4].start + 0.3, 0.4))),
        ("CONFIDENCE", ((0.0, 0.5), (L[8].start, 0.5), (L[8].start + 0.3, 0.08), (L[10].start, 0.08),
                        (L[10].start + 0.5, 1.0))),
    ),
)  # fmt: skip
cutout_recording.green_tick(cv, screen, 950, 430, at=TICK)

hook = cutout_key.key_line(
    cv, ep.comp, "NOBODY IS THERE", 0.0, min(3.0, L[1].start - 0.02), top=300, font=(ROOT / ep.spec.font).read_bytes()
)
spoken = ep.captions(ep.spoken_captions(min_seconds=0.84), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(hook, *spoken)
ep.markers(extra=[("marker-door", DOOR, "The door"), ("marker-tick", TICK, "The tick")])
ep.instagram(POSTS["one-way-video"])
ep.finish()

#!/usr/bin/env python3
"""Early Night, built with srstudio: bed by ten, and then a man restoring a shovel.

    srstudio record early-night PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build early-night PROJECT    # → PROJECT/early-night.scene.xml

"Tonight: bed by ten." Juno is in bed, lit by the phone, the thumb going. The narrator goes on as if nothing were wrong
while the hour card runs: 11:40, a man restoring a rusty shovel; 1:15, Bulgarian beekeepers; 2:30, she has opinions and
types one out; 3:47, she explains sanding to nobody, sunk to the nose in the duvet. "She has work at seven." The phone
goes down, the room goes black, and the alarm goes off on one open eye.

The first frame already moves (arm B of the ``sp-hook_motion`` test): the thumb and the phone's light never rest.
"""

import os

from _common import project_root
from early_night_audio import INTERVIEW
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, layout, soft_props, soft_sets
from srstudio.soft_props import TimeState
from srstudio.soft_sets import Light, Shot

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="early-night",
        title=INTERVIEW.title,
        description="Everyday-tech comedy: a narrator announces an early night over a woman who is watching a stranger "
        "repair a shovel at 3 a.m. Native vector animation; ElevenLabs dialogue, synthesised foley, no music.",
        root=ROOT,
        seed=41602,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions, the hour card and the phone's lettering stay inside x 80–920
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
ELEVEN, ONE, TWO, FOUR = (float(h) for h in t.meta["hours"])
COMMENT, DOWN, ALARM = t.comment_start, t.down_start, t.alarm_start
BLACK = DOWN + 0.45  # the phone is down and the light goes with it
FPS = 15
SCALE = 2.8
UP, SLID, SUNK = (540.0, 2260.0), (514.0, 2360.0), (440.0, 2480.0)  # she sinks down the headboard hour by hour
EYE = (502.0, 1258.0)  # her left eye, sunk: the last shot centres on it
EYE_ZOOM = 4.6
SCREEN = (221, 463, 638, 1274)  # the phone's glass in the insert, in frame pixels
PHONE_AT, PHONE_SCALE = (540.0, 1100.0), 4.9
PANEL = 1216  # the player under a video starts here, so its lettering stays above the safe area's bottom edge

sands = [ELEVEN + 0.1 + 0.26 * n for n in range(int((ONE - ELEVEN) / 0.26))]
taps = [COMMENT + 0.15 + 0.09 * n + (0.1 if n % 7 == 3 else 0.0) for n in range(int(0.8 / 0.09))]
beeps = [ALARM + 0.28 * n for n in range(int((DURATION - ALARM - 0.2) / 0.28) + 1)]
foley.write_whoosh(ROOT / "assets" / "sand.wav", sands, DURATION, length=0.14, seed=41603)
foley.write_buzz(ROOT / "assets" / "bees.wav", [ONE + 0.32 * n for n in range(int((TWO - ONE) / 0.32))], DURATION)
foley.write_typing(ROOT / "assets" / "typing.wav", taps, DURATION, seed=41604)
foley.write_tones(ROOT / "assets" / "alarm.wav", beeps, DURATION, ((1760.0, 1760.0, 0.09), (1760.0, 1760.0, 0.09)))
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("sand", "assets/sand.wav", {"role": "effects", "gain": -9}),
        ("bees", "assets/bees.wav", {"role": "effects", "gain": -14}),
        ("typing", "assets/typing.wav", {"role": "effects", "gain": -5}),
        ("alarm", "assets/alarm.wav", {"role": "effects", "gain": -4}),
    ]
)


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


juno = blob.speaking(
    [
        cue(0, "clasp", UP, eyes="look", mouth="smile"),
        cue(1.1, "clasp", UP, eyes="look", mouth="grin"),
        cue(TWO, "clasp", SLID, eyes="squint", mouth="flat", turn=-5),
        cue(FOUR, "clasp", SUNK, eyes="wide", mouth="small", turn=7),
        cue(DOWN, "clasp", SUNK, ease=0.3, eyes="closed", mouth="flat", turn=7),
        cue(ALARM, "clasp", SUNK, eyes="wide", mouth="flat", turn=7),
    ],
    [(p.start, p.end) for p in P if p.role == "juno"],
    DURATION,
    FPS,
)


def lying(g):
    blob.juno(cv, g, juno, end=DURATION, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=False)


def phone_and_thumb(g):
    """The phone over the duvet, its back to us, the thumb working its edge; it drops when she gives up."""
    hold = cv.group(g, "held-phone", x=540, y=1660)
    cv.keys(hold, "x", [(0.0, 540.0), (TWO, 540.0), (FOUR, 300.0)])
    cv.keys(hold, "y", [(0.0, 1660.0), (TWO, 1600.0), (FOUR, 1540.0)])
    cv.gate(hold, [(0.0, DOWN + 0.3)])
    cv.keys(hold, "rotation", [(0.0, 0.0), (TWO, -4.0), (FOUR, 9.0)])
    soft_props.phone(cv, hold, scale=1.7, id="in-hand")
    for side in (-1, 1):
        cv.rect(hold, side * 128 - 40, 60, 80, 170, blob.JUNO_FILL, cv.ink, 4, radius=38)
    thumb = cv.group(hold, "thumb")
    cv.keys(thumb, "y", [(0.13 * n, 0.0 if n % 2 else -62.0) for n in range(int(DURATION / 0.13))], False)
    cv.ellipse(thumb, -170, -30, 84, 150, blob.JUNO_FILL, cv.ink, 4)


graded = soft_sets.finish(cv, ep.comp)
soft_sets.bedroom(
    cv,
    graded,
    lights=[
        Light(0.0, "phone", 540, 1080),
        Light(TWO, "phone", 520, 1160),
        Light(FOUR, "phone", 590, 1240),
        Light(BLACK, "dark"),
        Light(ALARM, "day"),
    ],
    shots=[Shot(0.0), Shot(ALARM, EYE_ZOOM, *EYE)],
    cast=lying,
    held=phone_and_thumb,
)


def glass(g, id: str, fill: str):
    """An insert's screen: the phone at full frame over the dark room, and a group for what it shows."""
    soft_props.phone(cv, g, x=PHONE_AT[0], y=PHONE_AT[1], scale=PHONE_SCALE, screen=lambda s: None, id=f"{id}-phone")
    cv.rect(g, *SCREEN, fill, radius=68)


def panel(g, id: str, title: str, part: str, progress: float) -> None:
    """The player under a video: its title, its absurd length, and how far in she is."""
    x, y, w, h = SCREEN
    bottom = y + h - PANEL
    cv.rect(g, x, PANEL, w, bottom - 80, "#FFFFFF")
    cv.rect(g, x, PANEL + 160, w, bottom - 160, "#FFFFFF", radius=68)
    cv.rect(g, x + 50, PANEL + 26, w - 100, 12, "#D9DCE2", radius=6)
    cv.rect(g, x + 50, PANEL + 26, (w - 100) * progress, 12, "#E2503F", radius=6)
    cv.text(g, f"{id}-title", title, x + 40, PANEL + 50, w - 80, 70, 40, color=cv.ink)
    cv.text(g, f"{id}-part", part, x + 40, PANEL + 122, w - 80, 50, 32, color="#6B7078")
    for k in range(2):  # what the player will offer her next
        cv.rect(g, x + 44, PANEL + 214 + k * 150, 230, 126, "#C9CED6", radius=18)
        cv.rect(g, x + 300, PANEL + 236 + k * 150, 280, 24, "#DDE0E6", radius=12)
        cv.rect(g, x + 300, PANEL + 280 + k * 150, 190, 24, "#DDE0E6", radius=12)


def backdrop(id: str, spans):
    g = cv.group(ep.comp, id)
    cv.gate(g, spans)
    cv.rect(g, 0, 0, 1080, 1920, "#0B1026")
    return g


shovel_clip = backdrop("insert-shovel", [(ELEVEN, ONE)])
glass(shovel_clip, "shovel", "#D9C3A0")
for k in range(5):
    for j in range(7):
        cv.ellipse(shovel_clip, 262 + j * 92, 500 + k * 92, 12, 12, "#B79F7A")
sanding = [
    blob.cue(n * 0.26, "type-a" if n % 2 else "type-b", (540.0, 1440.0), scale=1.55, eyes="look", mouth="smile")
    for n in range(int((DURATION) / 0.26))
]
blob.bo(cv, shovel_clip, sanding, end=DURATION, scale=1.55, fps=FPS, shadow=False, id="restorer")
cv.rect(shovel_clip, SCREEN[0], 1040, SCREEN[2], 190, "#8A6242", cv.ink, 4)
soft_props.shovel(cv, shovel_clip, 540, 1050, scale=0.95, angle=84)
block = cv.group(shovel_clip, "sanding-block", x=340, y=1030)
cv.keys(block, "x", [(ELEVEN + n * 0.26, 300.0 if n % 2 else 400.0) for n in range(12)], False)
cv.rect(block, -44, -30, 88, 56, "#E2B64E", cv.ink, 4, radius=10)
panel(shovel_clip, "shovel", "Restoring a rusty shovel", "Part 3 of 14 · 2:41:07", 0.08)

bees_clip = backdrop("insert-bees", [(ONE, TWO)])
glass(bees_clip, "bees", "#BFDDEE")
cv.rect(bees_clip, SCREEN[0], 880, SCREEN[2], 350, "#8FBB7C")
soft_props.hive(cv, bees_clip, 400, 1170, scale=1.15, id="clip-hive")
soft_props.hive(cv, bees_clip, 720, 1060, scale=0.72, id="clip-hive-far")
for k, (x, y) in enumerate(((590, 900), (620, 1040), (330, 680), (700, 780), (470, 640), (790, 930), (560, 740))):
    bee = cv.group(bees_clip, f"bee-{k + 1}", x=x, y=y)
    steps = int(DURATION / 0.2)
    cv.keys(bee, "x", [(n * 0.2, x + (26 if (n + k) % 2 else -26)) for n in range(steps)], False)
    cv.keys(bee, "y", [(n * 0.2, y + (-18 if (n + k) % 3 else 16)) for n in range(steps)], False)
    cv.ellipse(bee, -13, -10, 26, 20, "#F2B632", cv.ink, 3)
    cv.ellipse(bee, -8, -24, 12, 18, "#FFFFFF", cv.ink, 2)
panel(bees_clip, "bees", "Beekeepers of Bulgaria", "Part 6 of 11 · 52:40", 0.71)

comment_clip = backdrop("insert-comment", [(COMMENT, FOUR)])
glass(comment_clip, "comment", "#FFFFFF")
x0, y0 = SCREEN[0] + 44, 800
cv.rect(comment_clip, SCREEN[0], SCREEN[1], SCREEN[2], 230, "#BFDDEE", radius=68)
cv.rect(comment_clip, SCREEN[0], 610, SCREEN[2], 90, "#8FBB7C")
soft_props.hive(cv, comment_clip, 720, 684, scale=0.42, id="clip-hive-small")
cv.text(comment_clip, "comment-count", "2 comments", x0, y0 - 84, 500, 60, 36, color="#6B7078", align="start")
cv.ellipse(comment_clip, x0, y0, 92, 92, "#E2503F")
cv.text(comment_clip, "comment-name", "juno · now", x0 + 112, y0 + 18, 400, 56, 34, color="#6B7078", align="start")
TYPED = (
    ("Stoyan,", 0.0, 0.35),
    ("Stoyan, you\nare smoking", 0.35, 0.8),
    ("Stoyan, you\nare smoking\nthem too early.", 0.8, 99.0),
)
for k, (words, a, b) in enumerate(TYPED):
    stage = cv.group(comment_clip, f"typed-{k + 1}")
    cv.gate(stage, [(COMMENT + a, COMMENT + b)])
    cv.text(stage, f"typed-{k + 1}-text", words, x0, y0 + 112, 560, 240, 62, color=cv.ink, align="start")
cv.rect(comment_clip, x0 + 370, y0 + 372, 180, 76, "#E2503F", radius=38)
cv.text(comment_clip, "comment-post", "Post", x0 + 370, y0 + 372, 180, 76, 38)

soft_props.time_card(
    cv,
    ep.comp,
    [
        TimeState("10:00", 0.0, ELEVEN),
        TimeState("11:40", ELEVEN, ONE),
        TimeState("1:15", ONE, TWO),
        TimeState("2:30", TWO, FOUR),
        TimeState("3:47", FOUR, DOWN),
        TimeState("7:00", ALARM, DURATION),
    ],
    (380, 452, 320, 118),
)

CUTS = [ELEVEN, ONE, TWO, COMMENT, FOUR, DOWN, ALARM]
spoken = {"narrator": [], "juno": []}
for i, p in enumerate(P):
    until = P[i + 1].start - 0.02 if i + 1 < len(P) else ALARM
    cut = min(c for c in CUTS if c > p.start)  # a line's caption leaves with its shot
    spoken[p.role].append((max(0.0, p.start - 0.05), min(until, cut, p.end + 0.5), p.caption, f"caption-{i + 1}"))
ep.captions(spoken["narrator"], **{**soft_sets.CAPTIONS, "color": "#2F5D8C"})
ep.captions(spoken["juno"], **soft_sets.CAPTIONS)
ep.markers(extra=[("marker-comment", COMMENT, "The comment"), ("marker-alarm", ALARM, "The alarm")])
ep.instagram(POSTS["early-night"])
out = ep.finish()
ep.check_overlays(out, ["soft-time-card"])

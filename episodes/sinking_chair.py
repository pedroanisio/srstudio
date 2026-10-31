#!/usr/bin/env python3
"""Sinking Chair, built with srstudio: every claim about rising costs him another inch.

    srstudio record sinking-chair PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build sinking-chair PROJECT    # → PROJECT/sinking-chair.scene.xml

Across the desk, level with the Boss, the chair sighs and he drops. "Let's talk about your growth." "I've really grown
this year." Another drop: "I'm ready to step up." His shoulders reach the desk: "I've risen to every challenge." He
pulls the lever, smiling. It clicks. Nothing. Pssht. The Boss has not looked up: "And long term?" Only his eyes and his
quiff clear the desk: "I see myself... higher." The Boss looks over the edge, down: "Three years in that chair. You've
never said a word." "Is there a raise?" Back to his notes: "Your salary works the same way." The last of the quiff
slides below the desk, one long pssht, a soft clunk. The Boss writes on over an empty desk edge.

The first frame already moves (arm B of the ``sp-hook_motion`` test): the chair is letting go. It declares no engine
safe area, so captions are placed inside x 80–920 by hand, on the desk, in the band of the approved Cutout look.
"""

import dataclasses
import os

from _common import project_root
from instagram_posts import POSTS
from sinking_chair_audio import INTERVIEW, SINK
from srstudio import OFFICE, Episode, EpisodeSpec, cast, cutout_odds, foley, graphics, locations, props
from srstudio import interview as iv_audio
from srstudio.cutout_reach import reach

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="sinking-chair",
        title=INTERVIEW.title,
        description="Office comedy: a man asks for a promotion while his chair sinks another inch at every claim. "
        "Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=26431,
        background="#E9D7BC",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
t, cv = ep.t, ep.cv
P = t.phrases
DURATION = t.duration
DROPS = [float(d) for d in t.meta["drops"]]
LEVER, LOW, SINKS = float(t.meta["lever"]), float(t.meta["low"]), float(t.meta["sink"])
HEAD = (540.0, 737.0, 2.07)
DEPTHS = [53.0, 130.0, 120.0, 90.0, 255.0]  # his head from y 737 to 1385: chin, chest, chin on the desk, eyes
LAST = 355.0  # the last of the quiff goes under
CLUNK = SINKS + SINK
BOSS = (540.0, 724.0, 1.45)

D1 = (P[3].end + 0.25 + 0.55 + 0.5, DROPS[4])  # the Boss, writing, until the next drop
D2 = (P[8].start - 0.35, SINKS)
HIGH = (LOW, D2[0])
R = [(0.0, D1[0]), (D1[1], HIGH[0]), (D2[1], DURATION)]

drops = [(at, 0.42, depth) for at, depth in zip(DROPS, DEPTHS, strict=True)]
drops.append((SINKS, SINK, LAST))
LONG = dataclasses.replace(foley.GAS_LIFT, seconds=SINK)
foley.write_bursts(ROOT / "assets" / "pssht.wav", DROPS, DURATION, foley.GAS_LIFT, seed=26432)
foley.write_bursts(ROOT / "assets" / "long-pssht.wav", [SINKS], DURATION, LONG, seed=26433)
foley.write_bursts(ROOT / "assets" / "lever.wav", [LEVER], DURATION, foley.REMOTE_CLICK, seed=26434)
foley.write_bursts(ROOT / "assets" / "clunk.wav", [CLUNK], DURATION, foley.THUD, seed=26435)
nib = [D1[0] + 0.1, D1[0] + 0.75, D2[0] + 0.15, D2[0] + 0.8, CLUNK + 0.25]
foley.write_bursts(ROOT / "assets" / "pen.wav", nib, DURATION, foley.PEN, seed=26436)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("pssht", "assets/pssht.wav", {"role": "effects", "gain": -6}),
        ("long-pssht", "assets/long-pssht.wav", {"role": "effects", "gain": -6}),
        ("lever", "assets/lever.wav", {"role": "effects", "gain": -4}),
        ("clunk", "assets/clunk.wav", {"role": "effects", "gain": -10}),
        ("pen", "assets/pen.wav", {"role": "effects", "gain": -14}),
    ]
)


def in_chair(g):
    seat = cv.group(g, "seat")
    cutout_odds.gas_lift(cv, seat, drops)
    props.chair(cv, seat, "gray")
    cutout_odds.chair_lever(cv, seat, 868, 1040, pulls=[LEVER], scale=1.5)
    actor = cast.Candidate(cv, tag="candidate-character")
    smile = [(P[3].start, LEVER + 0.45)]
    blinks = [(1.9, 2.04), (LEVER + 0.1, LEVER + 0.24), (LOW - 0.9, LOW - 0.76), (LOW - 0.5, LOW - 0.36)]
    ep.perform(actor, seat, *HEAD, mouth=ep.mouth("candidate", smile=smile), blinks=blinks, free_arms=("right",))
    away = [(0.0, 0.0), (LEVER - 0.3, 0.0), (LEVER - 0.2, 12.0), (LEVER + 0.5, 12.0), (LEVER + 0.6, 0.0)]
    cv.keys(actor.eyes, "x", away, hold=False)
    up = [(0.0, 0.0), (P[5].end - 0.1, 0.0), (P[5].end, -10.0)]
    cv.keys(actor.eyes, "y", up, hold=False)
    hands = cv.group(seat, "candidate-hands", x=HEAD[0], y=HEAD[1], scaleX=HEAD[2], scaleY=HEAD[2])
    rest = (77.0, 330.0)
    lever = (193.0, 132.0)
    pull = (193.0, 150.0)
    track = [(0.0, *rest), (P[3].start + 0.5, *rest), (LEVER - 0.05, *lever), (LEVER + 0.08, *pull)]
    track += [(LEVER + 0.42, *lever), (LEVER + 0.8, *rest)]
    reach(cv, hands, "candidate-right-arm", (67, 148), track, width=5.0, hand=34.0)


def boss_behind_desk(g):
    actor = cast.Manager(cv, tag="boss-character")
    blinks = [(D1[0] + 0.5, D1[0] + 0.64), (D2[0] + 0.3, D2[0] + 0.44)]
    ep.perform(actor, g, *BOSS, mouth=ep.mouth("manager"), blinks=blinks, pupils=[(0.0, -18.0)], free_arms=("right",))


def boss_writing(g):
    """His hand and pen, over the desk: he writes the whole time and never looks up."""
    writes = cv.group(g, "boss-writing")
    cv.gate(writes, [D1, D2])
    hands = cv.group(writes, "boss-hands", x=BOSS[0], y=BOSS[1], scaleX=BOSS[2], scaleY=BOSS[2])
    track = []
    at, n = 0.0, 0
    while at < DURATION:
        track.append((at, 34.0 + 12.0 * (n % 3), 356.0 + (4.0 if n % 2 else -4.0)))
        at += 0.17
        n += 1
    _, grip = reach(cv, hands, "boss-right-arm", (67, 148), track, width=3.5, hand=30.0)
    cutout_odds.ballpoint(cv, grip, -8, 12, scale=0.55)


def from_below(g):
    """The Boss, from the chair: over the edge of his desk, looking down at where a man used to be."""
    low = cv.group(g, "from-below")
    cv.gate(low, [HIGH])
    paints = props.office_paints(cv)
    cv.rect(low, -10, -10, 1100, 1940, paints["warm_wall"])
    actor = cast.Manager(cv, tag="boss-from-below")
    ep.perform(
        actor,
        low,
        540,
        1080,
        2.4,
        mouth=ep.mouth("manager"),
        blinks=[(P[6].end - 0.2, P[6].end - 0.06)],
        nods=[(0.0, 6.0)],
        pupils=[(0.0, -16.0)],
    )
    cv.rect(low, -10, 1330, 1100, 620, paints["desk"], cv.ink, 4)
    cv.rect(low, -10, 1600, 1100, 340, paints["desk_front"], cv.ink, 4)


finish = locations.finish(cv, ep.comp)
locations.office_reverse(cv, finish, in_chair=in_chair, shots=R, chair=False)
boss_shot = cv.group(finish, "boss-shot", x=-216, y=-330, scaleX=1.4, scaleY=1.4)
locations.office_desk(cv, boss_shot, behind_desk=boss_behind_desk, shots=[D1, D2], id="boss-desk")
boss_writing(boss_shot)
from_below(finish)
for n, at in enumerate(DROPS):
    graphics.squeak_mark(cv, finish, "pssht", (at, at + 0.7), x=860, y=420, id=f"pssht-{n}")
graphics.squeak_mark(cv, finish, "psssssht", (SINKS, CLUNK), x=540, y=1000, id="pssht-long")

spoken = ep.captions(ep.spoken_captions(), x=80, y=1440, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-lever", LEVER, "The lever"), ("marker-sink", SINKS, "The last of the quiff")])
ep.instagram(POSTS["sinking-chair"])
ep.finish()

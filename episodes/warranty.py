#!/usr/bin/env python3
"""Warranty, built with srstudio: a man tries to kill his washing machine before the warranty ends.

    srstudio record warranty PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build warranty PROJECT    # → PROJECT/warranty.scene.xml

Pip feeds the machine bricks while it is still free to break, then a bowling ball, and Juno joins in with a sack of
coins and a shovel. It purrs. It finishes its cycle with a little tune. On the stroke of midnight it stops, and then
the lamp, the TV and the fridge go, one at a time. When did they buy the house? Same day. Something creaks overhead.

The first frame already moves (arm B of the ``sp-hook_motion`` test): the brick is going in and the drum is turning.
"""

import os
from dataclasses import replace

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, camera, foley, layout, soft_odds, soft_props, soft_sets
from warranty_audio import INTERVIEW

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="warranty",
        title=INTERVIEW.title,
        description="Domestic comedy: a man has until midnight to kill his washing machine while it is still under "
        "warranty. Native vector animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        seed=INTERVIEW.seed,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions stay inside x 80–920
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
SECOND, BALL, FEEDING, ON_FLOOR = t.second_start, t.ball_start, t.feeding_start, t.floor_start
CHIME, MIDNIGHT, LAMP, CREAK = t.chime_start, t.midnight_start, t.lamp_start, t.creak_start
TV_OFF, FRIDGE_OFF = LAMP + 0.8, LAMP + 1.6
FPS = 15
SCALE = 1.2
FLOOR = 1730.0
WASHER_AT = (285.0, FLOOR - 20)
WASHER = 1.25
PIP_AT, JUNO_AT, PIP_BACK = (695.0, FLOOR), (935.0, FLOOR - 70), (905.0, FLOOR)
PIP_DOWN, JUNO_DOWN = (640.0, 1775.0), (880.0, 1775.0)
FIRST_IN = 0.3
SECOND_IN = SECOND + 0.3
BALL_IN = BALL + 0.5
COINS_IN, SHOVEL_IN = FEEDING + 0.5, FEEDING + 1.05
PUNCH = BALL + 0.6
PUSH_TO = 1.1

SLAMS = [FIRST_IN + 0.1, SECOND_IN + 0.1, BALL_IN + 0.1, SHOVEL_IN + 0.15]
COINS = [FEEDING + 0.1 + 0.05 * n + (0.02 if n % 3 == 1 else 0.0) for n in range(9)]


def bed(sound: foley.Burst, last: float) -> list[float]:
    """Cues that lay a looping ``sound`` end to end so that it stops at ``last``."""
    return [*(n * 3.9 for n in range(int((last - sound.seconds) / 3.9) + 1)), last - sound.seconds]


foley.write_bursts(ROOT / "assets" / "purr.wav", bed(foley.PURR, MIDNIGHT), DURATION, foley.PURR, seed=3131)
foley.write_bursts(ROOT / "assets" / "hum.wav", bed(foley.HUM, FRIDGE_OFF), DURATION, foley.HUM, seed=3132)
foley.write_bursts(ROOT / "assets" / "thud.wav", SLAMS, DURATION, foley.THUD, seed=3133)
foley.write_bursts(ROOT / "assets" / "coins.wav", COINS, DURATION, foley.CLINK, seed=3134)
foley.write_bursts(ROOT / "assets" / "clicks.wav", [MIDNIGHT, LAMP, TV_OFF, FRIDGE_OFF], DURATION, foley.REMOTE_CLICK)
foley.write_tones(ROOT / "assets" / "chime.wav", [CHIME], DURATION, foley.CYCLE_DONE)
foley.write_air(ROOT / "assets" / "sigh.wav", [MIDNIGHT + 0.08], DURATION, 1.1, seed=3135)
foley.write_bursts(ROOT / "assets" / "creak.wav", [CREAK], DURATION, foley.CREAK, seed=3136)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("purr", "assets/purr.wav", {"role": "ambience", "gain": -17}),
        ("hum", "assets/hum.wav", {"role": "ambience", "gain": -26}),
        ("thud", "assets/thud.wav", {"role": "effects", "gain": -9}),
        ("coins", "assets/coins.wav", {"role": "effects", "gain": -14}),
        ("clicks", "assets/clicks.wav", {"role": "effects", "gain": -9}),
        ("chime", "assets/chime.wav", {"role": "effects", "gain": -12}),
        ("sigh", "assets/sigh.wav", {"role": "effects", "gain": -18}),
        ("creak", "assets/creak.wav", {"role": "effects", "gain": -8}),
    ]
)


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def spans(role: str) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role]


def quiet(cues, lines):
    """``cues`` that talk on ``lines`` and go back to their own mouth the moment a line stops."""
    later = []
    for start, stop in lines:
        for edge in (start, stop):
            held = [c for c in cues if c.time <= edge][-1]
            if held.time != edge:
                later.append(replace(held, time=edge, ease=0.0, lift=0.0))
    return blob.speaking([*cues, *later], lines, DURATION, FPS)


pip = quiet(
    [
        cue(0, "step", PIP_AT, eyes="squint", mouth="flat"),
        cue(FIRST_IN + 0.15, "stand", PIP_AT, ease=0.12, eyes="open", mouth="flat", flip=True),
        cue(SECOND, "step", PIP_AT, ease=0.12, eyes="squint", mouth="flat"),
        cue(SECOND_IN + 0.15, "stand", PIP_AT, ease=0.12, eyes="open", mouth="flat", flip=True),
        cue(P[3].start, "clasp", PIP_AT, ease=0.12, eyes="squint", mouth="flat", flip=True),
        cue(P[4].start, "stand", PIP_AT, ease=0.12, eyes="open", mouth="smile"),
        cue(BALL, "step", PIP_AT, ease=0.15, eyes="squint", mouth="flat"),
        cue(BALL_IN + 0.15, "lean", PIP_AT, ease=0.12, eyes="squint", mouth="flat"),
        cue(FEEDING, "stand", PIP_BACK, eyes="wide", mouth="flat"),
        cue(ON_FLOOR, "sit", PIP_DOWN, eyes="open", mouth="flat"),
        cue(MIDNIGHT, "sit", PIP_DOWN, eyes="wide", mouth="flat"),
        cue(P[7].end + 0.1, "sit", PIP_DOWN, eyes="squint", mouth="flat"),
        cue(P[8].end, "sit", PIP_DOWN, eyes="open", mouth="flat"),
        cue(CREAK + 0.25, "sit", PIP_DOWN, ease=0.15, eyes="wide", mouth="o", turn=7),
    ],
    spans("pip"),
)
juno = quiet(
    [
        cue(0, "stand", JUNO_AT, eyes="look", mouth="flat"),
        cue(FEEDING, "step", PIP_AT, eyes="happy", mouth="smile"),
        cue(SHOVEL_IN + 0.15, "stand", PIP_AT, ease=0.12, eyes="open", mouth="smile"),
        cue(ON_FLOOR, "sit", JUNO_DOWN, eyes="look", mouth="flat"),
        cue(MIDNIGHT, "sit", JUNO_DOWN, eyes="wide", mouth="flat"),
        cue(LAMP, "sit", JUNO_DOWN, eyes="look", mouth="flat"),
        cue(P[8].end + 0.1, "sit", JUNO_DOWN, eyes="squint", mouth="flat"),
        cue(CREAK + 0.25, "sit", JUNO_DOWN, ease=0.15, eyes="wide", mouth="o", turn=7),
    ],
    spans("juno"),
)


def carried(name: str, cues, draw, spans_shown) -> None:
    """Something in the hand on the left of the frame, through ``spans_shown``."""
    hand = soft_odds.in_hand(cv, room, cues, "left", end=DURATION, scale=SCALE, fps=FPS, id=f"{name}-hand")
    cv.gate(hand, spans_shown)
    draw(hand)


graded = soft_sets.finish(cv, ep.comp)
world = cv.group(graded, "world")
pivot = cv.group(world, "push", x=540, y=1300)
cv.keys(pivot, "scaleX", [(0.0, 1.0), (MIDNIGHT, 1.0), (LAMP, PUSH_TO)], False)
cv.keys(pivot, "scaleY", [(0.0, 1.0), (MIDNIGHT, 1.0), (LAMP, PUSH_TO)], False)
room = cv.group(pivot, "room", x=-540, y=-1300)
soft_odds.home_fridge(cv, room, 900, 1180, end=DURATION, off=FRIDGE_OFF, scale=0.8)
soft_odds.tv(cv, room, 190, 1090, end=DURATION, off=TV_OFF, scale=0.8)
blob.home(cv, room, lamp_talk=[(0.0, LAMP)])
soft_odds.washer(
    cv,
    room,
    *WASHER_AT,
    end=DURATION,
    stop=MIDNIGHT,
    scale=WASHER,
    open_at=[(0.0, FIRST_IN + 0.08), (SECOND, SECOND_IN + 0.08), (BALL, BALL_IN + 0.08), (FEEDING, SHOVEL_IN + 0.12)],
    loads=[(FIRST_IN, "brick"), (SECOND_IN, "brick"), (BALL_IN, "ball"), (COINS_IN, "coins"), (SHOVEL_IN, "shovel")],
)
soft_odds.smoke(
    cv,
    room,
    WASHER_AT[0] + 110,
    WASHER_AT[1] - 690,
    ((0.0, 0), (MIDNIGHT + 0.3, 2)),
    end=DURATION,
    scale=0.45,
    id="thread",
)
blob.juno(cv, room, juno, end=DURATION, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, id="juno")
blob.pip(cv, room, pip, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, id="pip")
carried(
    "pip-bricks",
    pip,
    lambda h: soft_odds.brick(cv, h, 0, 0, scale=0.72, angle=-12, id="pip-brick"),
    [(0.0, FIRST_IN), (SECOND, SECOND_IN)],
)
carried("pip-ball", pip, lambda h: soft_odds.bowling_ball(cv, h, 0, 0, scale=0.72, id="pip-ball"), [(BALL, BALL_IN)])
carried(
    "juno-coins", juno, lambda h: soft_odds.coin_bag(cv, h, 0, 0, scale=0.68, id="juno-coins"), [(FEEDING, COINS_IN)]
)
carried(
    "juno-shovel",
    juno,
    lambda h: soft_props.shovel(cv, h, -60, 0, scale=0.62, angle=-72, id="juno-shovel"),
    [(COINS_IN, SHOVEL_IN)],
)
soft_odds.dust(cv, room, PIP_DOWN[0], 760, CREAK + 0.2, end=DURATION, width=170, fall=520)


def frame(scale: float, x: float, y: float) -> tuple[float, float, float]:
    return scale, 540 - x * scale, 960 - y * scale


camera.reframe(cv, world, [(0.0, 1.0, 0.0, 0.0), (PUNCH, *frame(1.4, 500.0, 1230.0)), (FEEDING, 1.0, 0.0, 0.0)])
soft_odds.dimmer(cv, graded, ((0.0, 0.0), (LAMP, 0.3), (TV_OFF, 0.48), (FRIDGE_OFF, 0.66)))
soft_props.time_card(
    cv,
    graded,
    [
        soft_props.TimeState("11:41", 0.0, FEEDING),
        soft_props.TimeState("11:56", FEEDING, ON_FLOOR),
        soft_props.TimeState("11:59", ON_FLOOR, MIDNIGHT),
        soft_props.TimeState("12:00", MIDNIGHT, LAMP),
    ],
    (90, 452, 280, 118),
)

specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    end = min(until, p.end + 0.6) if i + 1 < len(P) else min(DURATION, p.end + 1.0)
    specs.append((max(0.0, p.start - 0.05), end, p.caption, f"caption-{i + 1}"))
ep.captions(specs, **soft_sets.CAPTIONS)
ep.markers(extra=[("marker-midnight", MIDNIGHT, "Midnight"), ("marker-creak", CREAK, "The creak")])
ep.instagram(POSTS["warranty"])
out = ep.finish()
ep.check_overlays(out, [])

#!/usr/bin/env python3
"""Two Percent, built with srstudio: the friend who is always on 2% and has never once worried about it.

    srstudio record two-percent PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build two-percent PROJECT    # → PROJECT/two-percent.scene.xml

A bench at the edge of the park, at night, after a night out. Her screen says 2%, and has since Tuesday. She asks him
for the ride, a photo of them and a text to her mom, and he says yes to each, and his battery pays: 41, 33, 12, 2. He
shows her. She looks at his phone, then at him, concerned and kind: "You should really charge your phone." The cut lands
on "phone".
"""

import os
from functools import partial

from _common import project_root
from instagram_posts import POSTS
from srstudio import SOFT, Episode, EpisodeSpec, blob, foley, fonts, layout, opener, soft_inbox, soft_props, soft_sets
from srstudio.interview import said
from srstudio.soft_inbox import Level
from srstudio.soft_sets import BENCH_SEAT, Shot
from two_percent_audio import INTERVIEW, OPENER_TOP, OPENING, STEP, UNDER_OPENER

os.umask(0o077)  # generated outputs are private: folders 700, files 600

SLUG = "two-percent"
ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug=SLUG,
        title=INTERVIEW.title,
        description="Everyday-tech comedy: the friend who is always on 2% ends the night on yours. Native vector "
        "animation; ElevenLabs dialogue, synthesized foley, no music.",
        root=ROOT,
        seed=INTERVIEW.seed,
        style=SOFT,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # the captions and the phone's lettering stay inside x 80–920
        bleed=True,  # the park's far plane is out of focus
    )
)
t, cv = ep.t, ep.cv
P, DURATION = t.phrases, t.duration
RIDE, RIDE_END, DRAIN, DRAIN_END = t.ride_start, t.ride_end, t.drain_start, t.drain_end
FPS = 15
SCALE = 2.2
PIP_SEAT, JUNO_SEAT = (178.0, BENCH_SEAT), (902.0, BENCH_SEAT)
LEANED = (JUNO_SEAT[0] - 86.0, BENCH_SEAT)  # she leans into his selfie
AWAY = (PIP_SEAT[0] - 34.0, BENCH_SEAT)  # he leans away from her 2%
PHONE_SCALE = 1.2  # both phones up at the chest, their numbers inside the safe area
INSERT_AT, INSERT_SCALE = (540.0, 1125.0), 3.4
CAPTION_LEAD = 0.03  # a caption comes up this long before its line, and a cut to a new line lands with it
CAPTION_TAIL = 0.3  # a caption stays up this long past its line
FLASH = said(ep.root, P[3], "photo")
RIDE_TICK = RIDE + STEP
DRAIN_TICKS = (DRAIN + STEP, DRAIN + 2 * STEP)
FONT = (ROOT / ep.spec.font).read_bytes()
MEASURE = partial(fonts.text_width, FONT)  # a battery number's box is as wide as the number: at the frame edge it fits
LOOKS_AT_HIM = DRAIN_END + 0.65  # the hold: she looks at his phone, then at him
CLOSE = (P[1].start - CAPTION_LEAD, P[2].start - CAPTION_LEAD)  # the close on her for "Since Tuesday."
CLOSER = P[4].start - CAPTION_LEAD  # the last close on her; his phone at the frame edge still reads 2%: both phones do

CRICKETS = [0.9, 1.05, 4.3, 4.45, 8.2, 8.35, 12.1, 12.25]
foley.write_bursts(
    ROOT / "assets" / "crickets.wav", [c for c in CRICKETS if c < DURATION], DURATION, foley.CHIRP, seed=5321
)
foley.write_bursts(ROOT / "assets" / "tick.wav", [RIDE_TICK, *DRAIN_TICKS], DURATION, foley.REMOTE_CLICK, seed=5322)
foley.write_bursts(ROOT / "assets" / "tap.wav", [RIDE + 0.25], DURATION, foley.REMOTE_CLICK, seed=5323)
foley.write_bursts(ROOT / "assets" / "shutter.wav", [FLASH], DURATION, foley.CHIRP, seed=5324)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("crickets", "assets/crickets.wav", {"role": "ambience", "gain": -30}),
        ("tick", "assets/tick.wav", {"role": "effects", "gain": -16}),
        ("tap", "assets/tap.wav", {"role": "effects", "gain": -20}),
        ("shutter", "assets/shutter.wav", {"role": "effects", "gain": -18}),
    ],
    loudness="-14",
)


def cue(time: float, pose: str, spot=None, **kw):
    return blob.cue(time, pose, spot, scale=SCALE, **kw)


def spans(role: str) -> list[tuple[float, float]]:
    return [(p.start, p.end) for p in P if p.role == role]


pip = blob.quieted(
    [
        cue(0, "phone-a", PIP_SEAT, eyes="look", mouth="flat", flip=True),
        cue(P[0].start, "phone-a", AWAY, eyes="wide", mouth="flat", flip=True, turn=-5.0, ease=0.3),
        cue(P[2].start, "phone-a", AWAY, eyes="open", mouth="flat", flip=True, turn=-5.0),
        cue(RIDE, "phone-b", AWAY, eyes="look", mouth="flat", flip=True, turn=-5.0, ease=0.14),
        cue(P[3].start, "phone-a", PIP_SEAT, eyes="open", mouth="flat", flip=True, ease=0.2),
        cue(FLASH + 0.08, "phone-a", PIP_SEAT, eyes="squint", mouth="flat", flip=True),
        cue(P[3].end, "phone-a", PIP_SEAT, eyes="look", mouth="flat", flip=True),
        cue(DRAIN_END, "phone-a", PIP_SEAT, eyes="wide", mouth="flat", flip=True),
        cue(LOOKS_AT_HIM, "phone-a", PIP_SEAT, eyes="open", mouth="flat", flip=True),
    ],
    spans("pip"),
    DURATION,
    FPS,
)
SCROLLS = [k * 0.42 for k in range(int((P[3].start - 0.3) / 0.42))]  # her thumbs never stop until she leans in
juno = blob.quieted(
    [
        *[
            cue(at, "phone-a" if k % 2 == 0 else "phone-b", JUNO_SEAT, eyes="look", mouth="smile")
            for k, at in enumerate(SCROLLS)
        ],
        cue(P[3].start, "phone-a", LEANED, eyes="happy", mouth="smile", ease=0.26),
        cue(P[3].end, "phone-a", JUNO_SEAT, eyes="look", mouth="smile", ease=0.2),
        cue(DRAIN_END, "phone-a", JUNO_SEAT, eyes="look", mouth="flat"),
        cue(LOOKS_AT_HIM, "phone-a", JUNO_SEAT, eyes="open", mouth="flat"),
    ],
    spans("juno"),
    DURATION,
    FPS,
)


def world(g):
    blob.pip(cv, g, pip, end=DURATION, scale=SCALE, mouth_states=ep.mouth("pip"), fps=FPS, shadow=False)
    blob.juno(cv, g, juno, end=DURATION, scale=SCALE, mouth_states=ep.mouth("juno"), fps=FPS, shadow=False)
    in_his = blob.held(cv, g, pip, end=DURATION, scale=SCALE, fps=FPS, id="pip-hands")
    soft_props.phone(
        cv,
        in_his,
        scale=PHONE_SCALE,
        screen=lambda s: soft_inbox.battery_screen(
            cv,
            s,
            levels=(
                Level(41, 0.0, CLOSE[0]),
                Level(41, CLOSE[0], CLOSE[1], number=False),  # at the frame edge in her close: the charge alone
                Level(41, CLOSE[1], RIDE),
                Level(33, RIDE_END, DRAIN),
                Level(2, DRAIN_END, DURATION + 1.0),
            ),
            measure=MEASURE,
            id="pip-battery",
        ),
        id="pip-phone",
    )
    in_hers = blob.held(cv, g, juno, end=DURATION, scale=SCALE, fps=FPS, id="juno-hands")
    soft_props.phone(
        cv,
        in_hers,
        scale=PHONE_SCALE,
        screen=lambda s: soft_inbox.battery_screen(
            cv,
            s,
            levels=(Level(2, 0.0, RIDE), Level(2, RIDE_END, DRAIN), Level(2, DRAIN_END, DURATION + 1.0)),
            measure=MEASURE,
            id="juno-battery",
        ),
        id="juno-phone",
    )


TWO = Shot(0.0)
JUNO_CLOSE = (1.35, 680.0, 1042.0)  # her bun clears the caption, her number the safe area, and the set the frame
BOTH_PHONES = (1.25, 540.0, 1150.0)  # two phones, two 2%, two faces
shots = [TWO, Shot(CLOSE[0], *JUNO_CLOSE), Shot(CLOSE[1]), Shot(DRAIN_END, *BOTH_PHONES), Shot(CLOSER, *JUNO_CLOSE)]
graded = soft_sets.finish(cv, ep.comp)
soft_sets.park(cv, graded, seated=[(0, DURATION)], cast=world, shots=shots, night=True)

flash = cv.group(ep.comp, "selfie-flash")
cv.gate(flash, [(FLASH, FLASH + 0.2)])
pop = cv.group(flash, "selfie-flash-pop")
cv.rect(pop, 0, 0, 1080, 1920, "#FFFFFF")
cv.keys(pop, "opacity", [(FLASH, 0.5), (FLASH + 0.2, 0.0)], False)


def inserted(name: str, span: tuple[float, float]):
    g = cv.group(ep.comp, name)
    cv.gate(g, [span])
    cv.rect(g, 0, 0, 1080, 1920, "#10142C", opacity=0.82)
    return g


ride = inserted("ride-insert", (RIDE, RIDE_END))
rise = cv.group(ride, "ride-rise")
cv.keys(rise, "y", [(RIDE, 70.0), (RIDE + 0.3, 0.0)], False)
soft_props.phone(
    cv,
    rise,
    x=INSERT_AT[0],
    y=INSERT_AT[1],
    scale=INSERT_SCALE,
    screen=lambda s: soft_inbox.battery_screen(
        cv, s, levels=(Level(41, RIDE, RIDE_TICK), Level(33, RIDE_TICK, RIDE_END)), measure=MEASURE, id="ride-battery"
    ),
    id="ride-phone",
)
drain = inserted("drain-insert", (DRAIN, DRAIN_END))
soft_props.phone(
    cv,
    drain,
    x=INSERT_AT[0],
    y=INSERT_AT[1],
    scale=INSERT_SCALE,
    screen=lambda s: soft_inbox.battery_screen(
        cv,
        s,
        levels=(
            Level(33, DRAIN, DRAIN_TICKS[0]),
            Level(12, DRAIN_TICKS[0], DRAIN_TICKS[1]),
            Level(2, DRAIN_TICKS[1], DRAIN_END),
        ),
        measure=MEASURE,
        id="drain-battery",
    ),
    id="drain-phone",
)

HELD = max(P[0].end, opener.seconds(OPENING))  # to the end of his line, held on if it ends before it can be read
line = opener.draw(cv, ep.comp, OPENING, HELD, measure=MEASURE, top=OPENER_TOP, names=("juno", "pip"))

# A caption spaced so its outlined words stay apart is wider than the line was: the fourth splits at its second
# sentence, each window the words of one sentence, the second from when she says its "and".
SPLIT, PARTS = 3, ("And a photo of us.", "And text my mom\nI'm alive.")
if " ".join(PARTS).split() != P[SPLIT].caption.split():
    raise SystemExit(f"caption {SPLIT + 1} splits into other words than {P[SPLIT].caption!r}: {PARTS!r}")
SECOND = said(ep.root, P[SPLIT], "and", 1) - CAPTION_LEAD

specs = []
for i, p in enumerate(P):
    until = P[i + 1].start - 0.05 if i + 1 < len(P) else DURATION
    held = min(until, max(p.end + CAPTION_TAIL, p.start + 0.87))
    if i == 2:
        held = min(held, RIDE)
    if i == 3:
        held = min(held, DRAIN)
    start = max(0.0, p.start - CAPTION_LEAD)
    if i == SPLIT:
        specs += [(start, SECOND - 0.05, PARTS[0]), (SECOND, held, PARTS[1])]
    else:
        specs.append((start, held, p.caption))
specs = [(a, b, text, f"caption-{k + 1}") for k, (a, b, text) in enumerate(specs)]
look = soft_sets.caption_look(FONT, [text for _, _, text, _ in specs])  # the Soft caption layer: words kept apart
under = [s for s in specs if s[0] < HELD]  # up with the opening line: set below its pill, which is read first
captions = [*ep.captions(under, **{**look, "y": UNDER_OPENER}), *ep.captions(specs[len(under) :], **look)]
ep.hide_on_cover(line, flash, *captions)
ep.markers(
    extra=[
        ("marker-ride", RIDE, "The ride"),
        ("marker-drain", DRAIN, "His battery"),
        ("marker-hold", DRAIN_END, "The hold"),
    ]
)
if SLUG in POSTS:
    ep.instagram(POSTS[SLUG])
ep.finish()

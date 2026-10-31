"""The scale: the sketch as data. Gary at the doctor's strips everything that could weigh something before he will step
on: shoes, belt, a three-pound watch, gum. Two-oh-one. Is that with the clipboard? Five nine. I'm five eleven. Not any
more. He takes up one shoe and holds it to his chest. It's in the shoes.

Collage (ADR 0026), ElevenLabs premade Chris (Gary) and Sarah (Priya). It opens on a held frame (arm a of
``sp-hook_motion``). :func:`dress` draws the scale, the pile and the reading.
"""

from __future__ import annotations

from srstudio import collage, collage_group, collage_odds, collage_sets, foley
from srstudio.collage_group import Place
from srstudio.collage_sketch import TINTS, CastDrawer, Sound, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Line, Mouths, events

SEED = 4125
SLUG = "the-scale"
TITLE = "The scale - Gary (Collage)"
NAMES = ("gary", "priya")
ROOM = "therapy"
STILL = 1.0
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
DESCRIPTION = "A man prepares to be weighed by a nurse. It takes some time."
ACCESSIBILITY = (
    "A paper cut-out man stands over a clinic scale and takes off his shoes, belt, watch, wallet and keys and piles "
    "them on a chair, while a nurse waits with a clipboard. He hands her his gum, breathes out and steps on. "
    "Two-oh-one. Is that with the clipboard? She lowers the height bar. Five nine. Not any more. He picks up one shoe "
    "and holds it to his chest."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised foley."
NOTE = "ElevenLabs premade voices Chris and Sarah at their natural pace; no reference-voice cloning."
PLACES = {"gary": Place(330.0, 1920.0, 0.78), "priya": Place(830.0, 1920.0, 0.72)}
ITEMS = (
    ("#5a4632", 150),
    ("#5a4632", 150),
    ("#3b3128", 190),
    ("#d0a23a", 90),
    ("#7a4a2a", 120),
    ("#8d939a", 80),
    ("#1f2933", 110),
)
PILE = (640.0, 1846.0)
SCALE_X = 330.0
THUD = foley.THUD
EXHALE = foley.Burst(1.2, 1800.0, attack=0.1, decay=0.5)
BEEP = foley.Burst(0.16, 2200.0, attack=0.002, decay=0.4, tone_hz=1760.0, tone_end_hz=1760.0, tone=0.9)
CLINK = foley.Burst(0.1, 3400.0, attack=0.001, decay=0.5, tone_hz=2400.0, tone_end_hz=2300.0, tone=0.6)

LINES = (
    Line("priya", "Hop on."),
    Line("gary", "One second."),
    Line("priya", "You can leave those on."),
    Line("gary", "Shoes are heavy."),
    Line("gary", "This watch is three pounds."),
    Line("priya", "Can you see the number?"),
    Line("gary", "I don't want to."),
    Line("priya", "Two hundred and one."),
    Line("gary", "Is that with the clipboard?"),
    Line("priya", "Five nine."),
    Line("gary", "I'm five eleven."),
    Line("priya", "Not any more."),
    Line("gary", "It's in the shoes."),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "gary", "", "half", "flat", "down"),
        (0.9, "priya", 0, "open", "flat", "hold"),
        (1.2, "gary", 1, "open", "flat", "shrug"),
        (1.7, "priya", 2, "half", "flat", "hold", "reveal:item"),
        (1.4, "gary", 3, "open", "flat", "down", "reveal:item"),
        (2.2, "gary", 4, "side", "smug", "point", "reveal:item"),
        (1.0, "gary", "", "side", "flat", "down", "reveal:item"),
        (1.6, "priya", 5, "half", "flat", "hold", "reveal:item"),
        (1.4, "gary", 6, "closed", "frown", "down", "reveal:item"),
        (2.0, "gary", "", "closed", "o", "down", "reveal:gum"),
        (1.2, "priya", 7, "half", "flat", "hold", "reveal:weigh"),
        (1.9, "gary", 8, "side", "smile", "shrug"),
        (0.8, "priya", "", "half", "flat", "point", "reveal:bar"),
        (1.0, "priya", 9, "half", "flat", "hold"),
        (1.3, "gary", 10, "wide", "smile", "shrug", "zoom"),
        (2.4, "priya", 11, "half", "smug", "hold", "sting"),
        (1.0, "gary", "", "sad", "frown", "down"),
        (0.0, "gary", 12, "closed", "flat", "hold", "reveal:shoe"),
    ),
    tail=2.0,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def moments(beats, name: str) -> list[float]:
    return [t for t, what in events(beats, "reveal") if what == name]


def casting(beats, end: float) -> CastDrawer:
    lineup = collage_group.pair(PLACES, (STILL, end), listening=("half", "flat", "hold"))

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        return lineup(cv, parent, app, mouths)

    return draw


def dress(shot) -> None:
    """The scale at his feet, the pile on the chair, the reading on her clipboard, the shoe he takes back."""
    cv, front, app, beats = shot.cv, shot.front, shot.app, shot.beats
    items, weigh, shoe = moments(beats, "item"), moments(beats, "weigh")[0], moments(beats, "shoe")[0]
    bar = moments(beats, "bar")[0]
    if app.start < STILL:
        return
    collage_odds.doctor_scale(cv, shot.back, SCALE_X, 1880.0, bar, 1112.0, shot.end)
    cv.rect(front, PILE[0] - 170.0, PILE[1], 340.0, 30.0, "#7a4a2a", collage.INK, 4.0, radius=8.0)
    for k, (t, (colour, width)) in enumerate(zip(items, ITEMS, strict=False)):
        if t < app.end:
            g = cv.group(front, cv.uid("g"), start=t)
            if k == 0 and shoe < app.end:
                cv.gate(g, [(t, shoe)])
            cv.rect(
                g,
                PILE[0] - width / 2 + (k % 3 - 1) * 40.0,
                PILE[1] - 40.0 - k * 26.0,
                width,
                34.0,
                colour,
                collage.INK,
                4.0,
                radius=14.0,
            )
    collage_sets.sign(cv, cv.group(front, cv.uid("g"), start=weigh), "201 LB", 690, 1450, 280, 110, size=58)
    if app.end > shoe:
        held = cv.group(front, cv.uid("g"), start=shoe)
        cv.rect(held, 230.0, 1590.0, 200.0, 70.0, ITEMS[0][0], collage.INK, 4.0, radius=26.0)
        cv.rect(held, 216.0, 1652.0, 228.0, 20.0, "#2b2119", collage.INK, 4.0, radius=8.0)
        for lace in (290.0, 330.0, 370.0):
            cv.rect(held, lace, 1596.0, 14.0, 34.0, "#fffaf0", collage.INK, 2.0, radius=4.0)


def sounds(beats, end: float) -> list[Sound]:
    """A thud or a clink for each thing he takes off, the long breath, the beep, the bar."""
    items = moments(beats, "item")
    return [
        Sound("thud", THUD, tuple(items[:2]), -6.0),
        Sound("clink", CLINK, tuple(items[2:]), -9.0),
        Sound("exhale", EXHALE, tuple(moments(beats, "gum")), -11.0),
        Sound("beep", BEEP, tuple(moments(beats, "weigh")), -8.0),
        Sound("bar", foley.REMOTE_CLICK, tuple(moments(beats, "bar")), -5.0),
    ]


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": ROOM, "priya": ROOM},
    dress=dress,
    cast=casting,
    still=STILL,
    bitrate=BITRATE,
    sounds=sounds,
)

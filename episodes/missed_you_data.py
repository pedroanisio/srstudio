"""Missed You — the sketch as data: a frog drags a chair to her front door for a delivery, today, 8am to 8pm. The clock
jumps and she does not blink. At 7:59 a dog tiptoes up with no box and a note. The slip comes under the door. She tears
it open on an empty street and a van leaving. Day 2 she sits outside and blinks once. Day 3 they stand nose to nose in
the open door, and he sticks the note on her forehead and backs away.

One voice (ElevenLabs premade Charlie as Rex), heard over her face at the end; Fern does not speak. It opens on movement
(the ``sp-hook_motion`` test's arm B): the chair is hauled across the hall from the first frame. ``SKETCH`` is checked
by :func:`srstudio.sketch.check`; :func:`validate` checks the days and the note; :func:`push` is the haul, the tiptoe,
the tightening stare and the pull back as he leaves, and :func:`sounds` is the foley.
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

from srstudio import camera, foley, scripting, sketch, toon_flat, toon_props, toon_redrawn, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 2424
SLUG = "missed-you"
TITLE = "Missed You — a delivery window and a woman who sat through it (Toon)"
DESCRIPTION = "Delivery: today, 8am to 8pm. She took a chair to the door. He took a note."
ACCESSIBILITY = (
    "A cartoon: a frog hauls a chair to her front door and sits, staring, as the clock jumps from eight in the morning "
    "to 7:59 at night. Outside a dog tiptoes up with no parcel, only a note. A slip slides under the door: sorry we "
    "missed you. She tears the door open on an empty street and a van driving off. On day two she sits outside and "
    "blinks once. On day three they stare at each other in the open door and, without looking away, he slowly sticks "
    "the note on her forehead and backs off."
)
NARRATION = "Voiced with ElevenLabs premade voice Charlie (Rex); synthesised foley."
NOTE = "ElevenLabs premade voice Charlie at its natural pace; no reference-voice cloning."
REX = Speaker("rex", Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie"), VoiceSettings(0.4, 0.75, 0.4), "dog")
FERN = Speaker(
    "fern", Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"), VoiceSettings(0.5, 0.75, 0.3), "frog"
)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
TINTS = {"rex": "#f6dcb8", "fern": "#d5f0c8"}
PROMISE = "Delivery: today, 8am–8pm."
SORRY = "Sorry we missed you."
STAGES = ("hall", "slip", "street", "step", "stare")
HOURS = ((0.0, "08:00", "8:00 AM"), (1.05, "14:00", "2:00 PM"), (2.0, "19:59", "7:59 PM"))
HAUL = (0.0, 0.3, 0.6, 0.9)  # each heave of the chair, and the second it comes to rest
HAUL_END = 1.2
HAUL_FROM, HAUL_ZOOM, HAUL_TILT = 70.0, 1.24, 1.5  # output pixels, scale, degrees
CLOCK_AT = (500, 165)
BADGE = 44
STONE = ("#b9b4a8", "#8f8a7e", "#55524a")
ZOOM_AT = (1000.0, 1420.0)
TIGHTEN = (1.06, 1.1, 1.16)  # the stare's close-ups, by cut; past this the code leaves the frame
DUSK, DUSK_AT = "#1d2b53", 0.32
BROW = 590.0  # where the note lands: under her eyes, which sit on top of a frog's head
STICK_RISE = 1.9  # seconds his arm takes to arrive
END = 16.9

LINES = (Line("rex", SORRY),)

SCRIPT = scripting.Script(LINES)
say, hold = SCRIPT.say, SCRIPT.hold
BEATS = (
    hold(0.0, "frog", PROMISE, "wide", "flat", "desk"),
    hold(2.9, "dog", "", "side", "flat", "desk", "tiptoe"),
    hold(4.3, "frog", "", "wide", "flat", "desk", "stage:slip"),
    hold(6.3, "frog", "", "shock", "grimace", "desk", "stage:street"),
    hold(7.7, "frog", PROMISE, "wide", "flat", "desk", "stage:step"),
    hold(8.9, "frog", "", "closed", "flat", "desk", "blink"),
    hold(9.15, "frog", "", "wide", "flat", "desk"),
    hold(10.1, "frog", PROMISE, "wide", "flat", "desk", "stage:stare"),
    hold(11.1, "dog", "", "wide", "flat", "desk", "day3"),
    hold(11.7, "frog", "", "wide", "flat", "desk"),
    hold(12.3, "dog", "", "wide", "flat", "desk"),
    hold(12.9, "frog", "", "wide", "flat", "desk", "stick"),
    say(14.95, "frog", 0, "wide", "flat", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (REX, FERN), LINES, BEATS, END)


def stages(beats) -> list[tuple[float, str]]:
    """Where the frog is, from 0."""
    return scripting.changes(beats, "stage", STAGES[0])


def event(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, opens on her and the promise, runs its days in order, she blinks once and the note
    lands before the one line is heard."""
    sketch.check(sk)
    first = sk.beats[0]
    if first.who != "frog" or first.caption != PROMISE or first.spoken:
        raise sketch.SketchError("the sketch opens silent on the frog under the promise")
    if len(sk.lines) != 1 or sk.lines[0].text != SORRY:
        raise sketch.SketchError(f"the only line is {SORRY!r}")
    if [name for _, name in stages(sk.beats)] != list(STAGES):
        raise sketch.SketchError("the stages run in the sheet's order")
    for kind in ("tiptoe", "blink", "day3", "stick"):
        scripting.exactly_once(sk.beats, kind, f"one {kind}")
    if sum(b.eyes == "closed" for b in sk.beats) != 1:
        raise sketch.SketchError("she blinks once, on the second day")
    if not sk.beats[0].start < HAUL_END <= event(sk.beats, "tiptoe"):
        raise sketch.SketchError("the chair is in place before he tiptoes up")
    if not event(sk.beats, "stick") + STICK_RISE < next(b.start for b in sk.beats if b.spoken):
        raise sketch.SketchError("the note lands before the line is heard")
    if sk.beats[-1].who != "frog" or not sk.beats[-1].spoken:
        raise sketch.SketchError("it stops on her, on the line")
    scripting.only_events(sk.beats, {"stage", "tiptoe", "blink", "day3", "stick"})


def _hall(cv, back, *, door: bool = True, dusk: float | None = None) -> None:
    toon_world.wall(cv, back)
    if door:
        toon_flat.front_door(cv, back, 1000.0)
    toon_world.hall_chair(cv, back)
    if dusk is not None:
        cv.rect(cv.group(back, cv.uid("g"), start=dusk), 0, 0, cv.width, cv.height, DUSK, opacity=DUSK_AT)


def dress(shot) -> None:
    """Every place she waited has its own wall and the same ledge with the marks; the dog stands on the mat."""
    cv, app = shot.cv, shot.app
    if app.who == "dog":
        _rex(shot)
        return
    for a, b, name in scripting.spans(stages(shot.beats), app.start, app.end):
        back = cv.group(shot.back, cv.uid("g"), start=a, end=b)
        front = cv.group(shot.front, cv.uid("g"), start=a, end=b)
        _fern(shot, name, back, front, a, b)


def _rex(shot) -> None:
    cv, app = shot.cv, shot.app
    if app.start == event(shot.beats, "tiptoe"):
        toon_world.porch(cv, shot.back)
        toon_world.paw(
            cv, shot.back, ((app.start, app.end + 0.2),), coat=toon_redrawn.DOG.coat, side=-1.0, y=660.0, reach=330.0,
            holding="note",
        )  # fmt: skip
    else:
        toon_world.yard(cv, shot.back, sign=None, table=False)
    toon_world.ledge(cv, shot.front, *STONE)


def _fern(shot, name: str, back, front, a: float, b: float) -> None:
    cv = shot.cv
    measure = partial(shot.measure, size=BADGE)
    if name == "hall":
        _hall(cv, back, dusk=HOURS[-1][0])
        toon_props.clock(cv, back, [(t, clock) for t, clock, _ in HOURS], at=CLOCK_AT, r=70)
        for (start, _, said), stop in zip(HOURS, (*(t for t, _, _ in HOURS[1:]), b), strict=True):
            toon_props.badge(cv, front, said, start, stop, measure, BADGE)
    elif name == "slip":
        toon_world.missed_slip(cv, front, SORRY, a, b)
    elif name == "street":
        toon_world.yard(cv, back, sign=None, table=False)
        toon_world.van(cv, back, a, a + 1.3)
    elif name == "step":
        toon_world.porch(cv, back)
        toon_props.badge(cv, front, "DAY 2", a, b, measure, BADGE)
        toon_world.stuck_note(cv, front, SORRY, a, at=(262.0, 735.0))
    else:
        _hall(cv, back, door=False)  # the door stands open between them
        toon_props.clock(cv, back, [(0.0, HOURS[0][1])], at=CLOCK_AT, r=70)
        if a == stages(shot.beats)[-1][0]:
            toon_props.badge(cv, front, "DAY 3", a, b, measure, BADGE)
    toon_world.ledge(cv, front, *(STONE if name == "step" else ()))
    if name == "stare" and event(shot.beats, "stick") == a:
        coat = toon_redrawn.DOG.coat
        toon_world.stuck_note(cv, front, SORRY, a, a + STICK_RISE, (185.0, BROW))
        toon_world.paw(
            cv, front, ((a, a + 2 * STICK_RISE),), coat=coat, y=BROW, reach=350.0, holding="", slide=STICK_RISE
        )


def push(shot, setup) -> None:
    """The opening hauls the chair in, heave by heave; his tiptoe bobs; each cut of the stare is closer; he leaves on
    a slow pull back."""
    cv, app = shot.cv, shot.app
    camera.anchor(setup, *ZOOM_AT, place=True)
    x, y = ZOOM_AT
    if app.start == 0.0:
        _haul(cv, setup, x)
    elif app.start == event(shot.beats, "tiptoe"):
        _tiptoe(cv, setup, app.start, app.end, x, y)
    elif app.start >= stages(shot.beats)[-1][0]:
        if app.start >= event(shot.beats, "stick"):
            scale = ((app.start, TIGHTEN[-1]), (app.start + STICK_RISE, TIGHTEN[-1]), (app.start + 3.4, 1.0))
            camera.push_in(cv, setup, scale=scale)
        else:
            cuts = [b.start for b in shot.beats if b.start >= stages(shot.beats)[-1][0]]
            close = TIGHTEN[min(cuts.index(app.start), len(TIGHTEN) - 1)]
            camera.push_in(cv, setup, scale=((app.start, close), (app.end, close)))


def _haul(cv, setup, x: float) -> None:
    """Each heave lurches the hall and her a step across the frame, tipping as it goes; the zoom covers the edge the
    lurch would show and keeps the marks in frame."""
    steps = len(HAUL)
    across, zoom, tilt = [(0.0, x + HAUL_FROM)], [(0.0, HAUL_ZOOM)], [(0.0, 0.0)]
    for i, t in enumerate(HAUL):
        left = 1 - (i + 1) / steps
        across += [(t + 0.2, x + HAUL_FROM * left), (t + 0.3, x + HAUL_FROM * left)]
        zoom += [(t + 0.2, 1 + (HAUL_ZOOM - 1) * left), (t + 0.3, 1 + (HAUL_ZOOM - 1) * left)]
        tilt += [(t + 0.1, HAUL_TILT * (-1) ** i), (t + 0.2, 0.0)]
    cv.keys(setup, "x", across, hold=False)
    cv.keys(setup, "rotation", tilt, hold=False)
    for prop in ("scaleX", "scaleY"):
        cv.keys(setup, prop, zoom, hold=False)


def _tiptoe(cv, setup, start: float, end: float, x: float, y: float) -> None:
    """Up on each step, down between, and arriving at the door."""
    steps = [round(start + i * 0.38, 3) for i in range(int((end - start - 0.3) / 0.38))]
    cv.keys(setup, "y", [k for t in steps for k in ((t, y), (t + 0.19, y - 34.0))], hold=False)
    cv.keys(setup, "x", [(start, x + 150.0), (end - 0.3, x)], hold=False)
    for prop in ("scaleX", "scaleY"):
        cv.keys(setup, prop, [(start, 1.14), (end, 1.14)], hold=False)


def sounds(beats, end: float) -> list[Sound]:
    """The chair's heaves, his steps, the slip, the door, the van, the blink, the note going on."""
    tiptoe = event(beats, "tiptoe")
    named = dict((name, at) for at, name in stages(beats))
    stick = event(beats, "stick")
    return [
        Sound("scrape", foley.SCRAPE, HAUL, -2.0),
        Sound("step", foley.KNOCK, tuple(round(tiptoe + i * 0.38, 3) for i in range(3)), -16.0),
        Sound("slip", foley.SWISH, (named["slip"],), -6.0),
        Sound("door", foley.THUD, (named["street"],), 0.0),
        Sound("van", foley.ROAD, (named["street"],), -10.0),
        Sound("blink", foley.REMOTE_CLICK, (event(beats, "blink"),), -8.0),
        Sound("note", foley.KNOCK, (stick + STICK_RISE,), -8.0),
    ]

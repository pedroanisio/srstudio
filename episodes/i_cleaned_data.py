"""I Cleaned — the sketch as data: a proud roommate spins in. I cleaned! Where's the laundry? The closet bursts and pins
him. Where are the dishes? The oven door drops and the plates slide out. The shower curtain: the bins. A last, tiny
drawer, opened in terror: one sock, and relief. The front door opens, the hall comes through it and buries the
landlord. From under the pile: I cleaned.

Two voices (ElevenLabs premade Will as the raccoon, Jessica as the hedgehog); the landlord does not speak. It opens on
movement (the ``sp-hook_motion`` test's arm B): a whirl crosses the frame from the first frame and he is in it. Each
reveal stands behind a character on a counter that holds the signature and the tiny drawer; :func:`dress` draws the
pile before the counter, so the marks stay on top. ``SKETCH`` is checked by :func:`srstudio.sketch.check`;
:func:`validate` checks what the events ask of the props; :func:`push` shakes the shots the pile lands in and
:func:`sounds` is the foley.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley, scripting, sketch, toon_cast, toon_flat, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 2418
SLUG = "i-cleaned"
TITLE = "I Cleaned — roommates and the rest of the flat (Toon)"
DESCRIPTION = "He cleaned. Everything is out of sight. Nobody should open anything."
ACCESSIBILITY = (
    "A cartoon: a raccoon spins into a spotless flat and says he cleaned. A hedgehog asks about the laundry and the "
    "closet buries him to the chin. She opens the oven and plates slide out, pulls the shower curtain on a stack of "
    "bins, and opens a tiny drawer in terror on one sock. The landlord, a goat, is buried by the hall behind the "
    "front door. The raccoon, from under the clothes, says he cleaned."
)
NARRATION = "Voiced with ElevenLabs premade voices Will (the raccoon) and Jessica (the hedgehog); synthesised foley."
NOTE = "ElevenLabs premade voices Will and Jessica at their natural pace; no reference-voice cloning."
PROUD = Speaker(
    "proud", Voice(role="proud", id="bIHbv24MWmeRgasZH58o", name="Will"), VoiceSettings(0.4, 0.75, 0.5), "raccoon"
)
ASKER = Speaker(
    "asker", Voice(role="asker", id="cgSgspJ2msm6clMCkdW9", name="Jessica"), VoiceSettings(0.5, 0.75, 0.3), "hedgehog"
)
LANDLORD = Speaker(
    "landlord", Voice(role="landlord", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"), VoiceSettings(0.5, 0.75, 0.3), "goat"
)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
TINTS = {"proud": "#dfe5ec", "asker": "#f7e0cc"}
HER = dict(coat=toon_cast.HEDGEHOG.coat, y=706.0, reach=150.0, holding="")
CHIN, OVER = 668.0, 300.0  # the pile's top: at his chin, over the landlord's head
COUNTER = ("#fbfbf8", "#dfe5ec", "#7f8a96")
STAGES = ("closet", "oven", "shower", "drawer", "door")
SPARKLES = ((420.0, 400.0), (540.0, 580.0), (470.0, 720.0), (360.0, 520.0))
WHIRLED = 0.7
PLATES, PLATE_STEP = 5, 0.22  # slow enough not to flash
BURY_LEAD = 0.35  # seconds from the bury beat to the pile's rise
END = 15.2

LINES = (
    Line("proud", "I cleaned!"),
    Line("asker", "Where's the laundry?"),
    Line("asker", "Where are the dishes?"),
    Line("proud", "I cleaned."),
)

SCRIPT = scripting.Script(LINES)
say, hold = SCRIPT.say, SCRIPT.hold
BEATS = (
    hold(0.0, "raccoon", "", "wide", "grin", "desk"),  # the whirl hides him
    say(0.75, "raccoon", 0, "wide", "grin", "desk"),
    say(1.9, "hedgehog", 1, "narrow", "flat", "crossed"),
    hold(3.2, "raccoon", "", "side", "grimace", "desk", "closet", wear=("sweat",)),
    hold(4.6, "raccoon", "", "wince", "grimace", "desk", wear=("sweat",)),
    say(5.0, "hedgehog", 2, "narrow", "flat", "crossed", "stage:oven"),
    hold(6.3, "hedgehog", "", "half", "flat", "crossed", "oven"),
    hold(7.9, "hedgehog", "", "half", "flat", "crossed", "stage:shower"),
    hold(8.4, "hedgehog", "", "wide", "flat", "crossed", "pull"),
    hold(9.4, "hedgehog", "", "shock", "grimace", "desk", "stage:drawer", wear=("sweat",)),
    hold(9.9, "hedgehog", "", "shock", "grimace", "desk", "drawer", wear=("sweat",)),
    hold(10.7, "hedgehog", "", "closed", "smirk", "sigh"),  # one sock
    hold(11.5, "goat", "", "half", "flat", "crossed", "stage:door"),
    hold(12.0, "goat", "", "wide", "flat", "crossed", "bury"),
    say(13.4, "raccoon", 3, "half", "smirk", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (PROUD, ASKER, LANDLORD), LINES, BEATS, END)


def stages(beats) -> list[tuple[float, str]]:
    """What stands behind the hedgehog and the goat, from 0."""
    return scripting.changes(beats, "stage", STAGES[0])


def event(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, opens in the whirl, has each reveal once and in the sheet's order, no others."""
    sketch.check(sk)
    if sk.beats[0].who != "raccoon" or sk.beats[0].spoken or sk.beats[1].start < WHIRLED:
        raise sketch.SketchError("the sketch opens on the whirl: a silent beat the raccoon spins in on")
    for kind in ("closet", "oven", "pull", "drawer", "bury"):
        scripting.exactly_once(sk.beats, kind, f"one {kind}")
    order = [event(sk.beats, kind) for kind in ("closet", "oven", "pull", "drawer", "bury")]
    if order != sorted(order):
        raise sketch.SketchError("the reveals run closet, oven, shower, drawer, door")
    if [name for _, name in stages(sk.beats)] != list(STAGES):
        raise sketch.SketchError("the stages run in order")
    if not max(b.start for b in sk.beats if b.spoken) > event(sk.beats, "bury"):
        raise sketch.SketchError("he has the last word, from under the pile")
    scripting.only_events(sk.beats, {"stage", "closet", "oven", "pull", "drawer", "bury"})


def _counter(shot, front, drawer: bool = False) -> None:
    cv = shot.cv
    toon_world.ledge(cv, front, *COUNTER)
    if drawer:
        toon_flat.tiny_drawer(cv, front, event(shot.beats, "drawer"), shot.end, y=801.0)


def dress(shot) -> None:
    """Behind each character the place it went; over them the pile; over the pile the counter with the marks."""
    cv, app = shot.cv, shot.app
    toon_flat.flat(cv, shot.back)
    if app.who == "raccoon":
        _proud(shot)
    elif app.who == "hedgehog":
        for a, b, name in scripting.spans(stages(shot.beats), app.start, app.end):
            back = cv.group(shot.back, cv.uid("g"), start=a, end=b)
            front = cv.group(shot.front, cv.uid("g"), start=a, end=b)
            _asker(shot, name, back, front, a, b)
    else:
        toon_flat.front_door(cv, shot.back, stages(shot.beats)[-1][0] + 0.1)
        toon_flat.pile(cv, shot.front, OVER, event(shot.beats, "bury") + BURY_LEAD, shot.end)
        _counter(shot, shot.front)


def _proud(shot) -> None:
    cv, app = shot.cv, shot.app
    burst = event(shot.beats, "closet")
    toon_flat.closet(cv, shot.back, burst + 0.15)
    if app.start < burst:
        toon_flat.sparkles(cv, shot.back, WHIRLED, app.end, SPARKLES)
        toon_flat.whirl(cv, shot.front, 0.0, WHIRLED)
    elif app.start < burst + 0.2 < app.end:
        toon_flat.pile(cv, shot.front, CHIN, burst + 0.2, shot.end)
    else:
        toon_flat.pile(cv, shot.front, CHIN, None, shot.end)
    _counter(shot, shot.front)


def _asker(shot, name: str, back, front, a: float, b: float) -> None:
    cv = shot.cv
    if name == "closet":
        toon_flat.closet(cv, back, 0.0)
    elif name == "oven":
        at = event(shot.beats, "oven")
        toon_flat.oven(cv, back, at)
        toon_flat.plates(cv, front, at + 0.25, PLATES, PLATE_STEP, end=b + 0.1)
    elif name == "shower":
        toon_flat.shower(cv, back, event(shot.beats, "pull"))
    _counter(shot, front, drawer=name == "drawer")
    if name == "drawer":
        at = event(shot.beats, "drawer")
        toon_world.paw(cv, front, ((at - 0.2, at + 0.55),), **HER)


def push(shot, setup) -> None:
    """The shots a pile lands in shake as it lands."""
    cv = shot.cv
    for kind, lead in (("closet", 0.2), ("bury", BURY_LEAD)):
        at = event(shot.beats, kind) + lead
        if shot.app.start <= at and at + 0.7 < shot.app.end:
            t, keys = at + toon_flat.RISE * 0.7, []
            for i in range(7):
                keys.append((round(t + i * 0.05, 3), fy_shake(i)))
            keys.append((round(t + 0.35, 3), 0.0))
            cv.keys(setup, "y", keys)


def fy_shake(i: int) -> float:
    return (-1) ** i * (14.0 - 2.0 * i)


def sounds(beats, end: float) -> list[Sound]:
    """The whirl, the two avalanches, the plates, the curtain, the drawer, the sock's small ding."""
    oven = event(beats, "oven") + 0.25
    drawer = event(beats, "drawer")
    return [
        Sound("swish", foley.SWISH, (0.0,), -4.0),
        Sound("rumble", foley.RUMBLE, (event(beats, "closet") + 0.15, event(beats, "bury") + BURY_LEAD), -2.0),
        Sound("plates", foley.PLATES, tuple(round(oven + i * PLATE_STEP, 3) for i in range(PLATES)), -6.0),
        Sound("curtain", foley.SWISH, (event(beats, "pull"),), -8.0),
        Sound("drawer", foley.KNOCK, (drawer,), -4.0),
        Sound("ding", foley.BELL, (drawer + 0.3,), -10.0),
    ]

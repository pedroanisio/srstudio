"""Loaded Right — the sketch as data: a father who has hated every boyfriend can be won over in one move, at the
dishwasher. Dad grills Lewis about the bus while Lewis clears the table and, behind Dad's back, loads the machine. Dad
turns. The rows are perfect, the mugs are on a slant, and Lewis's father taught him.

Three voices (ElevenLabs premade Brian as Dad, Matilda as Fern, Will as Lewis). One kitchen: Dad at the front, Lewis
behind him at the open dishwasher, filling it dish by dish (``load`` events, :func:`srstudio.toon_homeware.dishwasher`);
the rack insert rolls out on ``roll`` and a mug is tipped on ``tip``. The camera moves from the first frame (the
``sp-hook_motion`` test's arm B). :func:`validate` checks the events; :func:`dress` draws each shot, :func:`lens` its
camera and :func:`foley` its sound.
"""

from __future__ import annotations

from srstudio import camera, scripting, sketch, toon_extras, toon_homeware, toon_house, toon_sets, toon_world
from srstudio import foley as synth
from srstudio.foley import Burst
from srstudio.sketch import Line, Sketch
from srstudio.toon_voices import speaker, tinted

SEED = 3102
SLUG = "loaded-right"
TITLE = "Loaded Right — Dad and the Dishwasher (Toon)"
DESCRIPTION = (
    "A Toon sketch: Dad has hated every boyfriend. Then Lewis, saying nothing, loads the dishwasher behind his back."
)
ACCESSIBILITY = (
    "An old cartoon goat in a kitchen questions a young raccoon about taking the bus. Behind him the raccoon quietly "
    "loads an open dishwasher, dish by dish. The goat turns. Close on the top rack: perfect rows of mugs, all on a "
    "slant. He puts on his reading glasses and tips one with a finger. Told who taught him, his chin goes, and a paw "
    "lands on the raccoon's shoulder. His daughter, a frog, reminds him what he said. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Brian (Dad), Matilda (Fern) and Will (Lewis)."
NOTE = "ElevenLabs premade voices Brian, Matilda and Will at their natural pace; no reference-voice cloning."
DAD = speaker("dad", "Brian", "goat", "deadpan")
FERN = speaker("fern", "Matilda", "frog")
LEWIS = speaker("lewis", "Will", "raccoon", "deadpan")
TINTS = tinted(DAD, FERN, LEWIS)
BARE = ("hamster",)  # the rack's insert
FIGURES = {"goat": (1.06, -6.0)}
PIVOT = (980.0, 1420.0)
LOADER = (462.0, 668.0)  # Lewis behind the machine
WASHER = dict(at=(452.0, 838.0), scale=0.96)
ROLL = Burst(1.6, 900.0, attack=0.1, decay=1.4, tone_hz=170.0, tone_end_hz=210.0, tone=0.25, flutter_hz=26.0)
CLINK = Burst(0.16, 7000.0, attack=0.001, decay=0.3, tone_hz=2600.0, tone_end_hz=2500.0, tone=0.5)
END = 27.0

LINES = (
    Line("dad", "So you take the bus."),
    Line("lewis", "Yes, sir."),
    Line("dad", "The last one had a car. He's gone too."),
    Line("fern", "Dad."),
    Line("dad", "Hey. Nobody touches that."),
    Line("dad", "Mugs on a slant."),
    Line("lewis", "So they drain."),
    Line("dad", "Who taught you?"),
    Line("lewis", "My father."),
    Line("dad", "My son."),
    Line("fern", "You said he had dead eyes."),
    Line("dad", "Don't you mess this up."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "goat", "", "narrow", "flat", "crossed", "load"),
    say(0.2, "goat", 0, "narrow", "flat", "crossed"),
    say(1.8, "goat", 1, "narrow", "none", "crossed", "load"),
    first(3.0, "goat", 2, "The last one had a car.", "narrow", "flat", "crossed", "load"),
    part(4.5, "goat", 2, 6, "He's gone too.", "half", "smirk", "crossed", "load"),
    say(5.9, "frog", 3, "narrow", "flat", "crossed"),
    hold(6.5, "goat", "", "half", "none", "crossed", "load"),
    hold(7.0, "goat", "", "half", "none", "crossed", "load"),
    hold(7.4, "goat", "", "side", "none", "crossed", "load"),
    say(8.0, "goat", 4, "shock", "open", "lean", "load"),
    hold(9.7, "hamster", "", "half", "none", "desk", "roll"),  # two seconds of the rows, rolling out
    hold(11.8, "goat", "", "narrow", "none", "lean", wear=("glasses",)),
    hold(12.8, "hamster", "", "half", "none", "desk", "tip"),
    say(14.0, "goat", 5, "narrow", "flat", "lean", wear=("glasses",)),
    say(15.5, "raccoon", 6, "half", "flat", "desk"),
    hold(16.7, "goat", "", "narrow", "none", "lean", wear=("glasses",)),
    say(18.0, "goat", 7, "wide", "flat", "lean", wear=("glasses",)),
    say(19.4, "raccoon", 8, "half", "flat", "desk"),
    hold(20.3, "goat", "", "teary", "frown", "lean", wear=("glasses",)),  # two seconds: his chin goes
    hold(21.4, "raccoon", "", "wide", "flat", "desk", "paw"),
    say(22.3, "raccoon", 9, "wide", "flat", "desk"),
    say(23.2, "frog", 10, "narrow", "flat", "crossed"),
    hold(24.8, "goat", "", "teary", "flat", "lean", wear=("glasses",)),
    say(25.3, "goat", 11, "narrow", "flat", "lean", wear=("glasses",)),
)
SKETCH = Sketch(SLUG, TITLE, (DAD, FERN, LEWIS), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, rolls the rack once and tips the mug once after it, lands the paw
    once on Lewis's shot, and the machine is full before Dad turns."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    for kind, message in (
        ("roll", "the rack rolls once"),
        ("tip", "the mug is tipped once"),
        ("paw", "one hand lands"),
    ):
        scripting.exactly_once(sk.beats, kind, message)
    if sketch.events(sk.beats, "tip")[0][0] <= sketch.events(sk.beats, "roll")[0][0]:
        raise sketch.SketchError("the mug is tipped after the rack has rolled")
    loads = sketch.events(sk.beats, "load")
    if len(loads) > 12 or loads[-1][0] >= sketch.events(sk.beats, "roll")[0][0]:
        raise sketch.SketchError("every dish is in before the rack rolls")
    scripting.only_events(sk.beats, {"load", "roll", "tip", "paw"})


def dress(shot) -> None:
    """The kitchen; Lewis behind Dad at the filling machine until Dad turns, then the rack insert, Lewis's close-up with
    the hand that lands on his shoulder, and Fern across the table."""
    cv, app = shot.cv, shot.app
    if app.who == "hamster":
        roll = sketch.events(shot.beats, "roll")[0][0]
        if app.start == roll:
            toon_homeware.rack(cv, shot.back, roll=(roll, roll + 1.3), start=app.start, end=app.end)
        else:
            tip = sketch.events(shot.beats, "tip")[0][0]
            toon_homeware.rack(cv, shot.back, (app.start - 0.5, app.start - 0.01), (tip + 0.1, tip + 0.9),
                               start=app.start - 0.5, end=app.end)  # fmt: skip
        toon_house.ledge(cv, shot.front, "white")
        return
    toon_sets.kitchen(cv, shot.back)
    if app.who == "goat":
        loads = [t for t, _ in sketch.events(shot.beats, "load")]
        turned = sketch.events(shot.beats, "roll")[0][0]
        if app.start < turned:
            at = [(0.0, "half", "flat", "desk")]
            for i, (a, _) in enumerate(sketch.events(shot.beats, "load")):
                at.append((a + 0.02, "down" if i % 2 else "half", "flat", "desk"))
            toon_extras.figure(shot, shot.back, "raccoon", LOADER, 0.76, tuple(at), mirror=True)
            toon_homeware.dishwasher(cv, shot.back, loads=loads, end=shot.end, **WASHER)
        else:
            toon_homeware.dishwasher(cv, shot.back, loads=loads, end=shot.end, **WASHER)
    elif app.who == "raccoon":
        for t, _ in sketch.events(shot.beats, "paw"):
            if app.start <= t < app.end:
                toon_world.paw(cv, shot.front, ((t, app.end),), coat="#b39ddb", side=-1.0, y=770.0, reach=170.0,
                               holding="")  # fmt: skip
    toon_house.ledge(cv, shot.front, "oak")


def lens(shot, setup) -> None:
    """A slow push from the first frame; still after that but for the last word."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.start == 0.0:
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (3.0, 1.05)])
    last = [b for b in shot.beats if b.line == 11][0].start
    if shot.app.who == "goat" and shot.app.start <= last < shot.app.end:
        camera.push_in(shot.cv, setup, scale=[(last - 0.6, 1.0), (last + 1.4, 1.1)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """A clink for every dish, the rack rolling out and the mug's small knock on the wire."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    tip = sketch.events(beats, "tip")[0][0]
    clink = [t + 0.05 for t, _ in sketch.events(beats, "load")] + [tip + 0.5]
    roll = synth.write_bursts(audio / "roll.wav", [t for t, _ in sketch.events(beats, "roll")], end, ROLL, seed=seed)
    dish = synth.write_bursts(audio / "clink.wav", clink, end, CLINK, seed=seed)
    return [sketch.effect("roll", 0.0, -10.0, root, roll), sketch.effect("clink", 0.0, -16.0, root, dish)]

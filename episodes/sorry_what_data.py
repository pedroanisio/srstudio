"""Sorry, What — the sketch as data: after two "sorry?" you are not allowed a third, so you say yes to something you
never heard. Gil says yes over a mower and gets a horse till spring. Then he says no over a leaf blower, twice.

Four voices (ElevenLabs premade Chris as Gil, Roger as the neighbor, Jessica across the road). Words nobody catches are
a scribble where the caption would be (``scrawl`` events in pairs, :func:`srstudio.toon_homeware.scribble`), the mouth
moving under it. The first frame is held (the ``sp-hook_motion`` test's arm A). :func:`validate` checks the events;
:func:`dress` draws each shot, :func:`lens` its camera and :func:`foley` its sound.
"""

from __future__ import annotations

from srstudio import camera, scripting, sketch, toon_cars, toon_homeware, toon_house, toon_world
from srstudio import foley as synth
from srstudio.foley import Burst
from srstudio.sketch import Line, Sketch
from srstudio.toon import fh, fx, fy
from srstudio.toon_voices import speaker, tinted

SEED = 3107
SLUG = "sorry-what"
TITLE = "Sorry, What — Gil and Keith (Toon)"
DESCRIPTION = "A Toon sketch: after two sorrys you are not allowed a third, so Gil says yes to a horse."
ACCESSIBILITY = (
    "A sloth talks over a fence while a mower roars; his words are a scribble in a pill. A cartoon frog says sorry "
    "twice, then yes, definitely. The mower stops. On Saturday the sloth brings a horse with a small suitcase. Later "
    "the frog holds the horse's rope in the street while a hedgehog with a leaf blower says something, also a "
    "scribble. He says no, absolutely not. The blower stops: his horse is on her car. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Chris (Gil), Roger (the neighbor) and Jessica (across the road)."
NOTE = "ElevenLabs premade voices Chris, Roger and Jessica at their natural pace; no reference-voice cloning."
GIL = speaker("gil", "Chris", "frog")
NEIGHBOR = speaker("neighbor", "Roger", "sloth", "deadpan")
ACROSS = speaker("across", "Jessica", "hedgehog")
TINTS = tinted(GIL, NEIGHBOR, ACROSS)
BARE = ("hamster",)  # the car, with Keith on it
PIVOT = (980.0, 1420.0)
STILL = 0.45
ENGINE = Burst(1.3, 620.0, attack=0.02, decay=4.0, tone_hz=82.0, tone_end_hz=86.0, tone=0.35, flutter_hz=33.0)
HISS = Burst(1.3, 5200.0, attack=0.02, decay=4.0, tone_hz=240.0, tone_end_hz=250.0, tone=0.1, flutter_hz=23.0)
SUITCASE = "#b3734a"
ROPE_OUT = [(300, 790), (380, 730), (470, 760), (620, 700)]
HORSE_DOOR = dict(at=(462, 486), scale=0.92)
END = 31.8

LINES = (
    Line("gil", "Sorry?"),
    Line("gil", "Sorry, what?"),
    Line("gil", "Ha! Yeah. Definitely."),
    Line("neighbor", "You have no idea what this means to me. Saturday, then."),
    Line("neighbor", "His name is Keith. He's yours till spring."),
    Line("gil", "No."),
    Line("gil", "No! Absolutely not!"),
    Line("across", "I said your horse is on my car."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold


def mumble(start: float, stop: float, who: str, eyes: str, extra: str = "") -> tuple:
    """A mouth moving with no words: the scribble on at ``start``, off at the next spoken beat's hold."""
    out = []
    t, open_ = start, True
    while t < stop - 0.2:
        out.append(
            hold(round(t, 2), who, "", eyes, "open" if open_ else "flat", "desk", "scrawl" if t == start else "")
        )
        t, open_ = t + 0.26, not open_
    return tuple(out)


BEATS = (
    hold(0.0, "sloth", "", "half", "open", "desk", "mower"),  # the held frame: the mower already roaring
    *mumble(STILL, 2.0, "sloth", "half"),
    hold(2.05, "frog", "", "half", "flat", "desk", "scrawl"),
    say(2.25, "frog", 0, "half", "open", "lean"),
    *mumble(3.0, 4.3, "sloth", "half"),
    hold(4.35, "frog", "", "narrow", "flat", "lean", "scrawl"),
    say(4.55, "frog", 1, "narrow", "open", "lean"),
    *mumble(5.8, 8.3, "sloth", "wide"),
    hold(8.35, "frog", "", "wide", "grimace", "desk", "scrawl"),
    say(8.7, "frog", 2, "half", "grin", "desk"),
    hold(10.6, "sloth", "", "wide", "flat", "desk", "quiet"),  # the mower cuts out
    first(11.1, "sloth", 3, "You have no idea", "teary", "flat", "desk"),
    part(12.2, "sloth", 3, 4, "what this means to me.", "teary", "flat", "desk"),
    part(13.6, "sloth", 3, 9, "Saturday, then.", "teary", "grin", "desk"),
    hold(15.2, "frog", "", "shock", "grimace", "desk"),
    hold(16.2, "sloth", "", "half", "flat", "desk", "bell"),  # SATURDAY: the door
    first(17.2, "sloth", 4, "His name is Keith.", "half", "flat", "desk"),
    part(18.6, "sloth", 4, 4, "He's yours till spring.", "half", "flat", "desk"),
    hold(20.0, "frog", "", "half", "flat", "desk", "keith"),  # two seconds with Keith
    hold(21.0, "frog", "", "down", "flat", "desk"),
    *mumble(22.0, 23.4, "hedgehog", "half"),
    hold(23.45, "frog", "", "half", "flat", "desk", "scrawl"),
    say(23.65, "frog", 5, "half", "flat", "crossed"),
    *mumble(24.4, 25.5, "hedgehog", "wide"),
    hold(25.55, "frog", "", "narrow", "flat", "crossed", "scrawl"),
    say(25.75, "frog", 6, "narrow", "open", "crossed"),
    hold(27.4, "hedgehog", "", "half", "flat", "desk", "calm"),  # the blower stops
    say(27.8, "hedgehog", 7, "half", "flat", "desk"),
    hold(29.7, "frog", "", "down", "flat", "desk"),  # he looks down the rope
    hold(30.5, "hamster", "", "half", "none", "desk", "hangup"),  # stop on Keith
)
SKETCH = Sketch(SLUG, TITLE, (GIL, NEIGHBOR, ACROSS), LINES, BEATS, END)


def scrawls(beats) -> list[tuple[float, float]]:
    """The scribble's spans: ``scrawl`` events, on then off."""
    times = [t for t, _ in sketch.events(beats, "scrawl")]
    return list(zip(times[::2], times[1::2], strict=True))


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent; the first frame is held; every scribble ends; each machine stops once, after it
    started; no other events."""
    sketch.check(sk)
    if sk.beats[1].start < STILL:
        raise sketch.SketchError(f"the first frame is held {STILL} s")
    if len(sketch.events(sk.beats, "scrawl")) % 2:
        raise sketch.SketchError("every scribble ends")
    for kind in ("mower", "quiet", "calm", "keith", "bell", "hangup"):
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    scripting.only_events(sk.beats, {"mower", "quiet", "calm", "keith", "bell", "hangup", "scrawl"})


def _first(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def dress(shot) -> None:
    """The fence and the mower, the door with Keith, the street and the blower, and the car."""
    cv, app = shot.cv, shot.app
    bell, keith, quiet = (_first(shot.beats, k) for k in ("bell", "keith", "quiet"))
    calm = _first(shot.beats, "calm")
    spans = [s for s in scrawls(shot.beats) if app.start <= s[0] < app.end]
    if app.who == "hamster":
        toon_world.yard(cv, shot.back, sign=None, table=False)
        toon_house.horse(cv, shot.back, start=app.start, end=app.end, at=(296, 372), scale=0.66, id=cv.uid("horse"))
        toon_cars.side_car(cv, shot.back, at=(296.0, 800.0), scale=1.7)
        for x in (250, 342):
            cv.rect(shot.back, fx(x - 22), fy(590), fh(44), fh(34), "#2b2d35", cv.ink, 5.0, radius=fh(8))
        toon_house.ledge(cv, shot.front, "white")
    elif bell <= app.start < keith + 2:
        toon_house.hallway(cv, shot.back, door="open")
        toon_house.horse(cv, shot.back, start=app.start, end=app.end, id=cv.uid("horse"), **HORSE_DOOR)
        if app.start >= keith:
            toon_house.rope(cv, shot.front, [(292, 790), (346, 716), (404, 712), (462, 600)])
        else:
            cv.rect(shot.back, cv.width * 0.64, cv.height * 0.56, 150, 104, SUITCASE, cv.ink, 5.0, radius=10)
            cv.rect(shot.back, cv.width * 0.64 + 50, cv.height * 0.56 - 18, 50, 20, cv.clear, cv.ink, 5.0, radius=8)
        toon_house.ledge(cv, shot.front, "white")
    else:
        toon_world.yard(cv, shot.back, sign=None, table=False)
        if app.who == "frog" and app.start < quiet:
            toon_homeware.mower(cv, shot.back, at=(392.0, 838.0), scale=1.3, running=((app.start, app.end),))
        if app.who == "hedgehog" and app.start < calm:
            toon_homeware.blower(cv, shot.front, at=(290.0, 790.0), running=((app.start, app.end),))
        if app.who == "frog" and app.start >= keith + 2:
            toon_house.rope(cv, shot.front, ROPE_OUT)
        toon_house.ledge(cv, shot.front, "white")
    if spans:
        toon_homeware.scribble(cv, shot.front, spans)
    if app.who == "sloth" and app.start >= bell - 0.01 and app.start == bell:
        toon_house.key_line(cv, shot.front, "SATURDAY", app.start, app.start + 1.4, measure=shot.measure)
    three = scrawls(shot.beats)[2]
    if app.start <= three[0] < app.end:
        toon_house.key_line(cv, shot.front, "You only get two.", three[0] + 0.3, three[1], measure=shot.measure)


def lens(shot, setup) -> None:
    """Still; a slow push onto Keith."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.who == "hamster":
        camera.anchor(setup, 540.0, 800.0, place=True)
        camera.push_in(shot.cv, setup, scale=[(shot.app.start, 1.0), (shot.app.start + 1.3, 1.08)])


def _bed(start: float, stop: float, step: float = 0.65) -> list[float]:
    out, t = [], start
    while t < stop:
        out.append(round(t, 3))
        t += step
    return out


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The mower to ``quiet``, the blower to ``calm``, the doorbell."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    mower = _bed(0.0, _first(beats, "quiet") - 1.0)
    blower = _bed(next(b.start for b in beats if b.who == "hedgehog"), _first(beats, "calm") - 1.0)
    engine = synth.write_bursts(audio / "mower.wav", mower, end, ENGINE, seed=seed)
    hiss = synth.write_bursts(audio / "blower.wav", blower, end, HISS, seed=seed)
    bell = synth.write_tones(
        audio / "bell.wav", [_first(beats, "bell")], end, ((659.0, 659.0, 0.34), (523.0, 523.0, 0.7))
    )
    return [sketch.effect("mower", 0.0, -9.0, root, engine), sketch.effect("blower", 0.0, -9.0, root, hiss),
            sketch.effect("bell", 0.0, -8.0, root, bell)]  # fmt: skip

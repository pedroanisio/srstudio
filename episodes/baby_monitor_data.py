"""Baby Monitor — the sketch as data: hosts fight in the kitchen in a hiss and smile the instant the door opens, sure
the guests cannot tell. Mae and Bruno agree his mother's lasagna tastes like a wet ceiling. The other half of the baby
monitor is on the dining table.

Three voices (ElevenLabs premade Sarah as Mae, Bill as Bruno, Laura as his mother). The door is the metronome (``door``
events in pairs, :func:`srstudio.toon_homeware.swing_door`) and moves from the first frame (the ``sp-hook_motion``
test's arm B); the monitor sits on the worktop the whole time. :func:`validate` checks the events; :func:`dress` draws
each shot, :func:`lens` its camera and :func:`foley` its sound.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    camera,
    scripting,
    sketch,
    toon_cast,
    toon_dinner,
    toon_extras,
    toon_homeware,
    toon_house,
    toon_sets,
)
from srstudio import foley as synth
from srstudio.sketch import Line, Sketch
from srstudio.toon_voices import speaker, tinted

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3108
SLUG = "baby-monitor"
TITLE = "Baby Monitor — Mae, Bruno and the Lasagna (Toon)"
DESCRIPTION = "A Toon sketch: Mae and Bruno say what they think of the lasagna, in the kitchen, in a hiss, on the air."
ACCESSIBILITY = (
    "A cartoon rabbit and a cartoon bear stand in a kitchen with a swing door behind them and a small white baby "
    "monitor on the worktop, its green light on. Each time the door opens they beam; each time it shuts they "
    "hiss. They "
    "agree his mother's lasagna tastes like a wet ceiling. They carry it out. At the dining table three guests sit "
    "still; in the middle of the table the monitor's receiver pulses with Bruno's footsteps. Lines appear in pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae), Bill (Bruno) and Laura (his mother)."
NOTE = "ElevenLabs premade voices Sarah, Bill and Laura at their natural pace; no reference-voice cloning."
MAE = speaker("mae", "Sarah", "rabbit")
BRUNO = speaker("bruno", "Bill", "bear")
MOTHER = speaker("mother", "Laura", "goat", "deadpan")
TINTS = tinted(MAE, BRUNO, MOTHER)
PIVOT = (980.0, 1420.0)
MONITOR = dict(at=(37.0, 500.0), scale=0.82)  # on the counter by the frame's left edge, clear of every ear
DISH = dict(at=(190.0, 850.0), scale=1.0)
ARMS = (((196.0, 1120.0), (8.0, 1330.0), -1), ((488.0, 1120.0), (690.0, 1330.0), 1))  # shoulder, mitt, side; screen px
ARM_W, ARM_INK = 66.0, 7.0
BRUNO_AT = (470.0, 806.0)
BRUNO_SCALE = 0.86
DOOR = dict(at=(346.0, 90.0), size=(210.0, 700.0), legs=True)
GUESTS = (("dog", (64.0, 816.0), 0.74), ("hedgehog", (470.0, 816.0), 0.74))
STEP = synth.KNOCK
GULP = synth.Burst(0.22, 300.0, attack=0.02, decay=0.4, tone_hz=210.0, tone_end_hz=120.0, tone=0.7)
SWING = synth.Burst(0.34, 1400.0, attack=0.02, decay=0.5, tone_hz=240.0, tone_end_hz=170.0, tone=0.3)
END = 26.6

LINES = (
    Line("mae", "Two more minutes! She's finally asleep!"),
    Line("mae", "Your mother called my curtains brave."),
    Line("bruno", "She likes them."),
    Line("bruno", "Just serve her lasagna."),
    Line("mae", "It tastes like a wet ceiling."),
    Line("bruno", "It's always tasted like a wet ceiling."),
    Line("mae", "Really?"),
    Line("bruno", "My whole childhood."),
    Line("mother", "The baby's fine."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "rabbit", "", "wide", "grin", "desk", "door"),  # the door is open, she beams through it
    first(0.2, "rabbit", 0, "Two more minutes!", "wide", "grin", "desk"),
    part(1.5, "rabbit", 0, 3, "She's finally asleep!", "wide", "grin", "desk"),
    hold(2.9, "rabbit", "", "narrow", "flat", "crossed", "door"),  # it swings shut, her smile drops like a blind
    first(3.3, "rabbit", 1, "Your mother called", "narrow", "flat", "crossed"),
    part(4.4, "rabbit", 1, 3, "my curtains brave.", "narrow", "flat", "crossed"),
    say(5.8, "rabbit", 2, "half", "flat", "crossed"),
    hold(7.0, "rabbit", "", "wide", "grin", "desk", "door"),  # open: a guest passes, both beam
    hold(7.8, "rabbit", "", "narrow", "flat", "crossed", "door"),
    say(8.2, "rabbit", 3, "narrow", "flat", "crossed"),
    say(9.9, "rabbit", 4, "narrow", "flat", "crossed"),
    say(11.8, "rabbit", 5, "half", "flat", "desk"),
    say(14.1, "rabbit", 6, "wide", "open", "desk"),
    say(14.9, "rabbit", 7, "wide", "grin", "desk"),
    hold(16.3, "rabbit", "", "closed", "kiss", "desk"),  # they nearly laugh; she kisses his cheek
    hold(17.0, "rabbit", "", "wide", "grin", "desk", "door"),  # they beam; the door opens
    hold(17.8, "goat", "", "half", "flat", "desk", "step"),  # hard cut: the table, forks down, the monitor pulsing
    hold(18.4, "goat", "", "half", "flat", "desk", "step"),
    hold(19.0, "goat", "", "half", "flat", "desk", "step"),
    hold(19.7, "bear", "", "wide", "grin", "desk"),  # the beam: he has seen it
    hold(20.7, "bear", "", "wide", "grimace", "desk", "gulp"),  # the monitor plays his swallow
    say(22.3, "goat", 8, "half", "flat", "desk"),
    hold(23.9, "rabbit", "", "wide", "grin", "desk", "hangup"),  # stop on Mae and the dish
    hold(24.6, "rabbit", "", "shock", "grimace", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (MAE, BRUNO, MOTHER), LINES, BEATS, END)


def opens(beats, end: float) -> list[tuple[float, float]]:
    """The door's open spans: ``door`` events, open then shut; the last one stays open."""
    times = [t for t, _ in sketch.events(beats, "door")]
    if len(times) % 2:
        times.append(end)
    return list(zip(times[::2], times[1::2], strict=True))


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s; the door is open on the first frame; the monitor is on screen in
    every kitchen shot (:func:`dress`); the sting is once, after the last line."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    if sketch.events(sk.beats, "door")[0][0] != 0.0:
        raise sketch.SketchError("the door is open on the first frame")
    scripting.exactly_once(sk.beats, "gulp", "he swallows once")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays once")
    if sketch.events(sk.beats, "hangup")[0][0] < max(b.start for b in sk.beats if b.spoken):
        raise sketch.SketchError("the sting comes after the last line")
    scripting.only_events(sk.beats, {"door", "step", "gulp", "hangup"})


def _arms(cv, parent) -> None:
    """Hers to the mitts, in her coat: the outline starts short of the shoulder, so the arm grows out of her body."""
    coat = toon_cast.LOOKS["rabbit"].coat
    for (sx, sy), (hx, hy), _ in ARMS:
        cv.line(parent, sx + (hx - sx) * 0.22, sy + (hy - sy) * 0.22, hx, hy, cv.ink, ARM_W + 2 * ARM_INK)
        cv.line(parent, sx, sy, hx, hy, coat, ARM_W)


def dress(shot) -> None:
    """The kitchen with the door and the monitor, both of them in it; the table with the guests and the receiver; each
    of them at the door with the dish."""
    cv, app = shot.cv, shot.app
    steps = [t for t, _ in sketch.events(shot.beats, "step")]
    gulp = sketch.events(shot.beats, "gulp")[0][0]
    if app.who == "goat":
        toon_sets.home(cv, shot.back, shot.end)
        for who, at, scale in GUESTS:
            toon_extras.figure(shot, shot.back, who, at, scale, ((0.0, "wide", "flat", "desk"),))
        toon_dinner.table(cv, shot.front)
        pulses = [*steps, gulp, gulp + 0.2]
        toon_homeware.monitor_receiver(cv, shot.front, at=(300.0, 846.0), scale=1.5, pulses=pulses, end=shot.end)
        return
    toon_sets.kitchen(cv, shot.back)
    toon_homeware.swing_door(cv, shot.back, opens(shot.beats, shot.end), end=shot.end, **DOOR)
    toon_homeware.baby_monitor(cv, shot.back, **MONITOR)
    if app.who == "rabbit" and app.start < steps[0]:
        talk = [(b.start, "half", "flat", "desk") for b in shot.beats if b.line in (2, 3, 5, 7)]
        beam = [(t, "wide", "grin", "desk") for t, _ in sketch.events(shot.beats, "door")[::2]]
        hiss = [(t, "narrow", "flat", "crossed") for t, _ in sketch.events(shot.beats, "door")[1::2]]
        poses = sorted([(0.0, "wide", "grin", "desk"), *talk, *beam[1:], *hiss], key=lambda p: p[0])
        toon_extras.figure(shot, shot.back, "bear", BRUNO_AT, BRUNO_SCALE, tuple(poses), mirror=True)
    toon_house.ledge(cv, shot.front, "oak")
    if app.who == "rabbit" and app.start > steps[0]:
        _arms(cv, shot.front)
        toon_homeware.lasagna(cv, shot.front, **DISH)


def lens(shot, setup) -> None:
    """Still, with a push on the table while the receiver pulses."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.who == "goat" and shot.app.start < sketch.events(shot.beats, "gulp")[0][0]:
        a = shot.app.start
        camera.push_in(shot.cv, setup, scale=[(a, 1.0), (a + 1.8, 1.06)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The door, Bruno's footsteps and his swallow, both over the monitor."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    door = synth.write_bursts(audio / "door.wav", [t for t, _ in sketch.events(beats, "door")], end, SWING, seed=seed)
    step = synth.write_bursts(audio / "step.wav", [t for t, _ in sketch.events(beats, "step")], end, STEP, seed=seed)
    gulp = synth.write_bursts(audio / "gulp.wav", [t for t, _ in sketch.events(beats, "gulp")], end, GULP, seed=seed)
    return [sketch.effect("door", 0.0, -12.0, root, door), sketch.effect("step", 0.0, -14.0, root, step),
            sketch.effect("gulp", 0.0, -6.0, root, gulp)]  # fmt: skip

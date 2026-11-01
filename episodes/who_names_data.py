"""Who Names — the sketch as data: the drive home is where couples review the dinner party, and it only works if the
call has really ended. Otto and Mae take the party apart in the dark while the dashboard chip, dim and unremarked from
the first frame, keeps counting, until Mae looks down.

Two voices in the car (ElevenLabs premade Daniel as Otto, Sarah as Mae) and one on its speaker, heard only (Jessica as
Dana), on a held medium two-shot in the dark cabin (:func:`srstudio.toon_pair.figure`), streetlights crossing their
faces. ``ROWS`` act both characters per beat; one cut, to the chip, lands the reveal in the held silence; :func:`dress`
draws each shot and :func:`lens` its camera; :func:`validate` checks the events.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, foley, passing_light, scripting, sketch, toon_cars, toon_house, toon_night, toon_pair
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3310
SLUG = "who-names"
TITLE = "Who Names — Otto, Mae and the Call (Toon)"
DESCRIPTION = (
    "A Toon sketch in a car at night: a couple take last night's dinner party apart on the drive home, until she "
    "glances at the dashboard and sees the call never ended."
)
ACCESSIBILITY = (
    "A cartoon bear drives a car at night with a cartoon rabbit beside him, streetlights crossing their faces. They "
    "mock the dinner party they just left: the risotto, the four hours about a sourdough, the slideshow. A dim chip "
    "on the dashboard counts up all the while. She laughs, glances down and stops: the chip reads Call: Dana, "
    "fourteen minutes twenty-two. Her finger creeps towards it. A woman's voice on the car speaker says Hi. Nobody "
    "breathes. He asks how long she has been there. Dana says: his name is Clive. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Daniel (Otto), Sarah (Mae) and Jessica (Dana)."
NOTE = "ElevenLabs premade voices Daniel, Sarah and Jessica at their natural pace; no reference-voice cloning."
PLAIN = VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3)
DEADPAN = VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15)
OTTO = Speaker("otto", Voice(role="otto", id="onwK4e9ZLuTAKqWW03F9", name="Daniel"), PLAIN, "bear")
MAE = Speaker("mae", Voice(role="mae", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"), PLAIN, "rabbit")
DANA = Speaker("dana", Voice(role="dana", id="cgSgspJ2msm6clMCkdW9", name="Jessica"), DEADPAN)
TINTS = {"otto": "#d9e8ff", "mae": "#ffd9e4", "dana": "#d4f5e0"}
PAIR = "hamster"  # never seen: the name of the two-shot, a shot the dress draws whole
CHIP_SHOT = "frog"  # never seen: the name of the close shot on the chip
BARE = (PAIR, CHIP_SHOT)
LIT = True
SEATS = {"rabbit": (146.0, 840.0), "bear": (424.0, 840.0)}
WHEEL = dict(at=(424.0, 862.0), radius=104.0)
NIGHT = "#55638f"
NIGHT_SHADE = 0.72
CALLER = "Dana"
READS = 14 * 60 + 22  # what the timer reads as the chip fills the frame
BIG = dict(at=(296.0, 660.0), scale=2.2)
FINGER_FROM, FINGER_TO = (330.0, 1130.0), (312.0, 770.0)
CREEP_STEP = 0.22
HOOK = "LEAVING THE DINNER PARTY"
HOOK_END = 3.0
PIVOT = (980.0, 1420.0)  # the marks stay where they are as the camera comes in
END = 24.3
ROAD_EVERY = 2.7
ROAD_GAIN_DB = -20.0

LINES = (
    Line("mae", "Never again."),
    Line("otto", "Worst risotto of my life."),
    Line("mae", "Four hours about his sourdough."),
    Line("otto", "He gave it a name."),
    Line("mae", "Who names a sourdough?"),
    Line("otto", "There was a slideshow."),
    Line("mae", "Of the sourdough!"),
    Line("mae", "We should have them back."),
    Line("otto", "Absolutely not."),
    Line("dana", "Hi.", phone=True),
    Line("otto", "How long have you..."),
    Line("dana", "His name is Clive.", phone=True),
)

script = scripting.Script(LINES)
say, first, part, hold = script.say, script.first, script.part, script.hold
AHEAD = Act("half", "flat", "desk")
GRIN = Act("half", "grin", "desk")
AT_HIM = Act("side", "smirk", "desk")
AT_HER = Act("left", "smirk", "desk")
LAUGH = Act("closed", "grin", "desk")
DOWN = Act("down", "grin", "desk")
FROZEN = Act("down", "flat", "desk")
FOLLOW = Act("down", "grin", "desk")
STILL = Act("wide", "flat", "desk", ("sweat",))
TOP = ("half", "flat", "desk")

ROWS = (
    (hold(0.0, PAIR, "", *TOP), AHEAD, AHEAD),
    (say(0.3, PAIR, 0, *TOP), AHEAD, AHEAD),
    (say(1.5, PAIR, 1, *TOP), AT_HIM, AHEAD),
    (say(3.25, PAIR, 2, *TOP), AT_HIM, GRIN),
    (say(5.75, PAIR, 3, *TOP), AT_HIM, AT_HER),
    (say(7.05, PAIR, 4, *TOP), GRIN, AHEAD),
    (say(8.8, PAIR, 5, *TOP), AT_HIM, GRIN),
    (say(10.4, PAIR, 6, *TOP), LAUGH, GRIN),
    (say(12.0, PAIR, 7, *TOP), AT_HIM, AHEAD),
    (say(13.7, PAIR, 8, *TOP), AT_HIM, GRIN),
    (hold(14.8, PAIR, "", *TOP), LAUGH, GRIN),  # she laughs
    (hold(15.3, PAIR, "", *TOP), DOWN, GRIN),  # she glances down
    (hold(15.7, PAIR, "", *TOP, "lit"), FROZEN, GRIN),  # the laugh stops
    (hold(16.2, CHIP_SHOT, "", *TOP, "chip"), FROZEN, GRIN),  # the chip, her finger creeping to it
    (hold(17.7, PAIR, "", *TOP, "back"), FROZEN, FOLLOW),  # he follows her eyes, still smiling
    (say(18.5, PAIR, 9, *TOP), STILL, STILL),
    (hold(19.1, PAIR, "", *TOP, "crossing"), STILL, STILL),  # two seconds: nobody breathes, a light crosses
    (say(20.9, PAIR, 10, *TOP), STILL, STILL),
    (say(22.2, PAIR, 11, *TOP), STILL, STILL),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = {"rabbit": tuple(row[1] for row in ROWS), "bear": tuple(row[2] for row in ROWS)}
SKETCH = Sketch(SLUG, TITLE, (OTTO, MAE, DANA), LINES, BEATS, END, bare=BARE)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, and the reveal happens once, after every line of the review."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    for kind in ("lit", "chip", "back", "crossing"):
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    scripting.only_events(sk.beats, {"lit", "chip", "back", "crossing"})


def sounds(beats, end) -> tuple[Sound, ...]:
    """The road, low, the whole way home: it is all the silence has in it."""
    last = end - foley.ROAD.seconds
    at = tuple(round(i * ROAD_EVERY, 3) for i in range(int(end / ROAD_EVERY)) if i * ROAD_EVERY < last)
    return (Sound("road", foley.ROAD, at, ROAD_GAIN_DB),)


def _lights(shot) -> tuple[float, ...]:
    """A streetlight every few seconds through the review, then none until the one in the pause."""
    crossing = sketch.events(shot.beats, "crossing")[0][0]
    spoken_end = sketch.events(shot.beats, "lit")[0][0]
    every = [0.2 + 2.9 * i for i in range(int(spoken_end / 2.9))]
    times = [*every, crossing + 0.5]
    app = shot.app
    return tuple(round(t, 3) for t in times if app.start <= t and t + passing_light.CROSSING <= app.end)


def _creep(start: float, end: float) -> tuple[tuple[float, float, float], ...]:
    """Her finger towards the chip, a little at a time, and it does not get there."""
    steps = int((end - start) / CREEP_STEP)
    x0, y0 = FINGER_FROM
    x1, y1 = FINGER_TO
    return tuple(
        (round(start + i * CREEP_STEP, 3), x0 + (x1 - x0) * (i + 1) / steps, y0 + (y1 - y0) * (i + 1) / steps)
        for i in range(steps)
    )


def dress(shot) -> None:
    """The cabin in the dark, the two of them and the chip; the chip alone, large, as she sees it."""
    cv, app = shot.cv, shot.app
    lit, chip_at = sketch.events(shot.beats, "lit")[0][0], sketch.events(shot.beats, "chip")[0][0]
    reads = (chip_at, READS)
    chip = dict(measure=shot.measure, lit_from=lit, id=cv.uid("chip"))
    if app.who == PAIR:
        toon_night.night_cabin(cv, shot.back)
        for who in ("rabbit", "bear"):
            toon_pair.figure(shot, shot.back, who, SEATS[who], ACTS[who])
        passing_light.shade(cv, shot.light, NIGHT, NIGHT_SHADE)
        passing_light.bands(cv, shot.light, _lights(shot))
        toon_cars.steering_wheel(cv, shot.front, **WHEEL)
        toon_night.night_dash(cv, shot.front)
        toon_night.call_chip(cv, shot.front, CALLER, reads, app.start, app.end, **chip)
    else:
        toon_night.night_dash(cv, shot.front, close=True)
        toon_night.call_chip(cv, shot.front, CALLER, reads, app.start, app.end, **chip, **BIG)
        toon_house.finger(cv, shot.front, tip=FINGER_FROM, angle=-6.0, colour="#f4eef2", sleeve="#d9cfe0",
                          moves=_creep(app.start + 0.1, app.end - 0.05), start=app.start, end=app.end,
                          id=cv.uid("finger"))  # fmt: skip
    if app.start == 0.0:
        toon_house.key_line(cv, shot.front, HOOK, 0.0, HOOK_END, measure=shot.measure)


def lens(shot, setup) -> None:
    """A slow push on the two-shot from the first frame, and closer in the pause."""
    camera.anchor(setup, *PIVOT, place=True)
    app = shot.app
    if app.start == 0.0:
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (4.0, 1.03)])
    elif app.who == PAIR:
        camera.push_in(shot.cv, setup, scale=[(app.start, 1.03), (app.end, 1.08)])

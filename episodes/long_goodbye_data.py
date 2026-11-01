"""Long Goodbye — the sketch as data: leaving your mother takes an hour: the hall, the porch, the car window. Then she
is level with him on the highway, and then she is on his sofa.

Two voices (ElevenLabs premade Liam as the son, Laura as Mom). A clock card for each stop (``toon_house.key_line``),
the tubs of soup piling up in his arms (:func:`srstudio.toon_homeware.soup_tubs`). The scene moves from the first frame
(the ``sp-hook_motion`` test's arm B). :func:`validate` checks the stops; :func:`dress` draws each shot, :func:`lens`
its camera and :func:`foley` its sound.
"""

from __future__ import annotations

from srstudio import camera, scripting, sketch, toon_cars, toon_homeware, toon_house, toon_rooms, toon_world
from srstudio import foley as synth
from srstudio.sketch import Line, Sketch
from srstudio.toon_voices import speaker, tinted

SEED = 3106
SLUG = "long-goodbye"
TITLE = "Long Goodbye — Mom and the Soup (Toon)"
DESCRIPTION = "A Toon sketch: leaving Mom's takes an hour, four tubs of soup and part of the highway."
ACCESSIBILITY = (
    "A cartoon fox with his coat on tries to leave his mother, a cartoon cat, in the hall at 7:02. On the "
    "porch at 7:41 "
    "he holds one tub of soup. In the car at 8:15 he has three, and she talks through the window. The car "
    "rolls and she "
    "keeps pace, then keeps pace on the highway, her head level with his window, holding out a fourth tub. At home at "
    "night he shuts his door and breathes. A lamp clicks on: she is on his sofa. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Liam (the son) and Laura (Mom)."
NOTE = "ElevenLabs premade voices Liam and Laura at their natural pace; no reference-voice cloning."
SON = speaker("son", "Liam", "fox")
MOM = speaker("mom", "Laura", "cat", "big")
TINTS = tinted(MOM, SON)
LIT = True
PIVOT = (980.0, 1420.0)
STOPS = ("hall", "porch", "car", "road", "home")  # the stage: each has a clock card
CARD = {"hall": "7:02 PM", "porch": "7:41 PM", "car": "8:15 PM", "road": "8:31 PM, 70 MPH", "home": "9:40 PM"}
TUBS = {"porch": 1, "car": 3, "road": 3}
CAR_GREEN = "#6fa8dc"
CLICK = synth.REMOTE_CLICK
END = 28.2

LINES = (
    Line("son", "Well, we should get going."),
    Line("mom", "Go, go! Did I tell you about Linda's hip?"),
    Line("son", "Okay. Bye, Mom."),
    Line("mom", "Bye! Take the soup. So the doctor says..."),
    Line("son", "Love you. Bye."),
    Line("mom", "Text me when you're home. So, Linda..."),
    Line("mom", "They took out the whole hip."),
    Line("son", "Mom, this is the highway."),
    Line("mom", "Did you eat?"),
    Line("mom", "You didn't text."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "fox", "", "half", "flat", "desk", "stop:hall"),
    say(0.2, "fox", 0, "half", "flat", "desk"),
    first(2.2, "cat", 1, "Go, go!", "half", "flat", "desk"),
    part(3.1, "cat", 1, 2, "Did I tell you about Linda's hip?", "wide", "flat", "desk"),
    say(5.8, "fox", 2, "half", "flat", "desk", "stop:porch"),
    first(7.2, "cat", 3, "Bye! Take the soup.", "half", "flat", "desk"),
    part(8.8, "cat", 3, 4, "So the doctor says...", "wide", "flat", "desk"),
    say(10.8, "fox", 4, "half", "flat", "desk", "stop:car"),
    first(12.2, "cat", 5, "Text me when you're home.", "half", "flat", "desk"),
    part(14.0, "cat", 5, 5, "So, Linda...", "wide", "flat", "desk"),
    hold(15.1, "fox", "", "side", "flat", "desk", "stop:road"),  # the car rolls; she does not stop
    say(15.9, "cat", 6, "wide", "flat", "desk"),
    say(18.0, "fox", 7, "shock", "open", "lean"),
    say(19.8, "cat", 8, "half", "flat", "desk"),
    hold(21.2, "fox", "", "half", "none", "sigh", "stop:home"),  # home: he shuts the door, drops the keys
    hold(21.9, "fox", "", "closed", "flat", "sigh", "keys"),
    hold(23.4, "cat", "", "half", "flat", "desk", "lamp"),  # the lamp clicks on behind him
    say(24.2, "cat", 9, "half", "flat", "desk"),
    hold(25.6, "fox", "", "shock", "drop", "lean", "hangup"),  # stop on him
)
SKETCH = Sketch(SLUG, TITLE, (SON, MOM), LINES, BEATS, END)


def stop_at(beats, t: float) -> str:
    """The stop in force at ``t``."""
    return [name for at, name in sketch.events(beats, "stop") if at <= t + 1e-6][-1]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s and visits every stop once, in order; the lamp clicks once, on the
    last stop, and the sting comes last."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    if tuple(name for _, name in sketch.events(sk.beats, "stop")) != STOPS:
        raise sketch.SketchError(f"the stops are {STOPS}, in order")
    scripting.exactly_once(sk.beats, "lamp", "the lamp clicks once")
    scripting.exactly_once(sk.beats, "keys", "the keys drop once")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays once")
    scripting.only_events(sk.beats, {"stop", "lamp", "keys", "hangup"})


def _lights(shot) -> dict:
    return {"lamp": [[0, "off"], [sketch.events(shot.beats, "lamp")[0][0], "on"]]}


def dress(shot) -> None:
    """Each stop's set; the road scrolls, and its tubs sit in his lap or in her hands."""
    cv, app = shot.cv, shot.app
    stop = stop_at(shot.beats, app.start)
    if stop == "hall":
        toon_house.hallway(cv, shot.back, door="shut")
        toon_house.ledge(cv, shot.front, "white")
    elif stop == "porch":
        toon_world.porch(cv, shot.back)
        toon_house.ledge(cv, shot.front, "white")
    elif stop == "road" and app.who == "fox":
        toon_cars.car_inside(cv, shot.back, app.start, app.end + 0.1)
        toon_world.ledge(cv, shot.front, top=CAR_GREEN, front="#4a7fb0")
    elif stop == "car":
        toon_world.yard(cv, shot.back, sign=None, table=False)
        toon_world.ledge(cv, shot.front, top=CAR_GREEN, front="#4a7fb0")
    elif stop == "road":
        toon_world.road(cv, shot.back, app.start, app.end + 0.1, cab=False)
        toon_world.ledge(cv, shot.front, top=CAR_GREEN, front="#4a7fb0")
        if any(b.line == 8 and app.start <= b.start < app.end for b in shot.beats):
            toon_homeware.soup_tubs(cv, shot.front, [(app.start, 1)], at=(330, 838), end=app.end)
    else:
        toon_rooms.dress(shot, "lounge", _lights(shot))
        toon_house.ledge(cv, shot.front, "oak")
    if app.who == "fox" and stop in TUBS:
        toon_homeware.soup_tubs(cv, shot.front, [(app.start, TUBS[stop])], at=(340, 838), end=app.end)
    arrived = dict((name, at) for at, name in sketch.events(shot.beats, "stop"))[stop]
    if app.start == arrived:
        toon_house.key_line(cv, shot.front, CARD[stop], app.start, app.start + 1.7, measure=shot.measure)


def lens(shot, setup) -> None:
    """A slow push from the first frame; on the road she bobs, at a jog."""
    camera.anchor(setup, *PIVOT, place=True)
    app = shot.app
    if app.start == 0.0:
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (2.2, 1.05)])
    if app.who == "cat" and stop_at(shot.beats, app.start) == "road":
        keys = []
        t = app.start
        while t < app.end:
            keys.append((round(t, 3), PIVOT[1] + (10.0 if len(keys) % 2 else -10.0)))
            t += 0.16
        shot.cv.keys(setup, "y", keys, hold=False)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The keys, the lamp's click and the wind and tires of the road."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    stops = dict((name, at) for at, name in sketch.events(beats, "stop"))
    road = [t + stops["road"] for t in (0.0, 1.5, 3.0, 4.2)]
    click = synth.write_bursts(audio / "click.wav", [t for t, _ in sketch.events(beats, "lamp")], end, CLICK, seed=seed)
    drop = synth.write_bursts(
        audio / "keys.wav", [t for t, _ in sketch.events(beats, "keys")], end, synth.KNOCK, seed=seed
    )
    wind = synth.write_bursts(audio / "road.wav", road, end, synth.ROAD, seed=seed)
    return [sketch.effect("click", 0.0, -8.0, root, click), sketch.effect("keys", 0.0, -12.0, root, drop),
            sketch.effect("road", 0.0, -16.0, root, wind)]  # fmt: skip

"""Slept wrong: the sketch as data. Two old friends in a booth trade injuries like veterans. A young waiter laughs and
asks if it was rugby. I slept, says the goat. On my side. The waiter bends for a napkin and does not come back up.

Toon, ElevenLabs premade Brian (the sloth), George (the goat) and Liam (the waiter). It opens on a held frame, the
``sp-hook_motion`` test's arm a. The booth's two-shot is a held medium cut on the line; the waiter's bend is
:func:`bend`, a :attr:`srstudio.toon_sketch.Staging.moves` body move, so the room stays put and he does not.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley, scripting, sketch, toon_dinner, toon_house, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon import fh
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3109
SLUG = "slept-wrong"
TITLE = "Slept wrong (Toon)"
DESCRIPTION = "Two old friends compare injuries from sneezing, socks and sleeping."
ACCESSIBILITY = (
    "A cartoon sloth and goat sit in a booth like men back from a war: he lost his left side to a sneeze; the goat "
    "bent down for a sock and it is still down there. A young hamster waiter asks if it was rugby. I slept, says the "
    "goat, on my side. The waiter laughs, bends for a napkin, clicks and stops halfway down. Sit down, son."
)
NARRATION = "Voiced with ElevenLabs premade voices Brian, George and Liam; synthesised foley."
NOTE = "ElevenLabs premade voices Brian, George and Liam at their natural pace; no reference-voice cloning."
SLOTH = Speaker(
    "sloth", Voice(role="sloth", id="nPczCjzI2devNBz1zQrb", name="Brian"), VoiceSettings(0.6, 0.75, 0.15), "sloth"
)
GOAT = Speaker(
    "goat", Voice(role="goat", id="JBFqnCBsd6RMkjVDRZzb", name="George"), VoiceSettings(0.6, 0.75, 0.15), "goat"
)
WAITER = Speaker(
    "waiter", Voice(role="waiter", id="TX3LPaxmHKxFdv7VOQHJ", name="Liam"), VoiceSettings(0.4, 0.75, 0.4), "hamster"
)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
TINTS = {"sloth": "#d3e3cf", "goat": "#e9e2d0", "waiter": "#f7e0b5"}
KEY_LINE = "Lost the whole left side."
GLASS_RAISE = 130.0
BEND = 62.0  # degrees, as far as he gets
BEND_SECONDS = 0.45
CLICK = foley.Burst(0.05, 2400.0, attack=0.001, decay=0.5)
EVENTS = {"glass", "bend"}
ICE = foley.Burst(0.12, 3600.0, attack=0.002, decay=0.5, tone_hz=1900.0, tone_end_hz=2300.0, tone=0.4)
END = 23.9

LINES = (
    Line("sloth", "Sneezed. Tuesday. Lost the whole left side."),
    Line("goat", "I bent down for a sock."),
    Line("sloth", "Did you get it?"),
    Line("goat", "It's still down there."),
    Line("waiter", "What happened to you guys? Rugby?"),
    Line("sloth", "Tell him."),
    Line("goat", "I slept."),
    Line("sloth", "You slept?"),
    Line("goat", "On my side."),
    Line("waiter", "Ow."),
    Line("goat", "Sock?"),
    Line("waiter", "Napkin."),
    Line("sloth", "Sit down, son."),
)
SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold
BEATS = (
    first(0.0, "sloth", 0, "Sneezed. Tuesday.", "half", "flat", "desk"),
    part(1.5, "sloth", 0, 2, "Lost the whole left side.", "half", "flat", "desk"),
    say(3.7, "goat", 1, "half", "flat", "desk"),
    say(5.6, "sloth", 2, "half", "flat", "desk"),
    say(6.7, "goat", 3, "closed", "flat", "desk"),
    first(8.3, "hamster", 4, "What happened to you guys?", "wide", "grin", "desk"),
    part(9.6, "hamster", 4, 5, "Rugby?", "wide", "grin", "desk"),
    say(11.2, "sloth", 5, "side", "flat", "desk"),
    say(12.1, "goat", 6, "down", "flat", "desk"),
    say(13.5, "sloth", 7, "shock", "flat", "desk"),
    say(14.4, "goat", 8, "closed", "flat", "desk"),
    hold(16.2, "sloth", "", "closed", "flat", "desk", "glass"),
    hold(17.1, "hamster", "", "wide", "grin", "desk", "bend"),
    say(18.5, "hamster", 9, "closed", "grimace", "desk"),
    say(20.1, "goat", 10, "half", "flat", "desk"),
    say(20.9, "hamster", 11, "wince", "grimace", "desk"),
    say(21.8, "sloth", 12, "half", "flat", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (SLOTH, GOAT, WAITER), LINES, BEATS, END)


def event(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """One glass raised, one bend, and the waiter speaks only after he has stopped halfway."""
    sketch.check(sk)
    scripting.only_events(sk.beats, EVENTS)
    for kind in EVENTS:
        scripting.exactly_once(sk.beats, kind, f"one {kind}")
    if not event(sk.beats, "bend") + BEND_SECONDS < 18.5:
        raise sketch.SketchError("he stops halfway before he says ow")


def bend(cv, body, app, beats) -> None:
    """The waiter goes over at the bend and stays over: every later shot of him holds the angle."""
    at = event(beats, "bend")
    if app.end > at:
        keys = [(at + 0.35, 0.0), (at + 0.35 + BEND_SECONDS, BEND)]
        cv.keys(body, "rotation", keys, hold=False, kind="cubic-out", local=False)


def dress(shot) -> None:
    """The restaurant, a table with the drinks on it, one glass raised."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    toon_dinner.restaurant(cv, shot.back, ("SOUP", "OF THE\nDAY"), lettering=False)
    toon_dinner.table(cv, shot.front)
    if app.who != "hamster":
        at = event(beats, "glass")
        table = shot.front
        if app.who == "sloth" and app.start <= at < app.end:  # the glass goes up, very slowly, and the paw with it
            table = cv.group(shot.front, cv.uid("g"))
            cv.keys(table, "y", [(at, 0.0), (at + 0.8, -fh(GLASS_RAISE))], hold=False, kind="sine-in-out", local=False)
            toon_dinner.dishes(cv, table, (("water", 400),), id=f"drink-{int(app.start * 10)}")
            toon_world.paw(cv, table, ((at, app.end),), "#8d9460", y=760.0, reach=230.0, holding="")
        else:
            toon_dinner.dishes(cv, table, (("water", 400),), id=f"drink-{int(app.start * 10)}")
    if app.start == 0:
        toon_house.key_line(cv, shot.front, KEY_LINE, 1.5, 3.6, measure=shot.measure)


def sounds(beats, end: float) -> list[Sound]:
    """Ice in a glass, a far chair as if the room had stood, one small click."""
    return [
        Sound("ice", ICE, (6.2, event(beats, "glass")), -9.0),
        Sound("chair", foley.SCRAPE, (event(beats, "glass") + 0.3,), -14.0),
        Sound("click", CLICK, (event(beats, "bend") + 0.35 + BEND_SECONDS,), -2.0),
    ]


STAGING_ARGS = dict(
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
    desk=toon_world.no_desk,
    moves={"hamster": bend},
)

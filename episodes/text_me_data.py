"""Text Me — the sketch as data: a 34-year-old leaves work with his mother on speaker. Text me when you get home. He
lives four minutes away. He gets home, the phone is dead, and six minutes later a neighbour is at the door with a
flashlight: you're alive, she's holding line two. A helicopter finds the window. On the news, Mom at a podium: he said
four minutes. He plugs it in, 112 missed calls, and sends "home". Every phone in the search crowd dings and they all go
home. Mom, reading it out on live television: who's home? Text me when you get home. Stop on the son.

Three voices (ElevenLabs premade Liam as the son, Laura as Mom, Brian as the neighbour). Mom is heard over the son's
shots until she is on television. The son's shots change place on ``stage:`` events; ``phone`` lays the charging phone
over him. It opens on movement (the ``sp-hook_motion`` test's arm B): the keys swing and the phone rings from the
first frame. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the
props; :func:`dress` draws each shot, :func:`push` the opening's camera and :func:`sounds` the foley.
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

from srstudio import (
    camera,
    foley,
    scripting,
    sketch,
    toon,
    toon_everyday,
    toon_inked,
    toon_props,
    toon_sets,
    toon_world,
)
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_everyday import Screen
from srstudio.toon_sketch import BADGE_SIZE, Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 2414
SLUG = "text-me"
TITLE = "Text Me — a son, four minutes and his mother (Toon)"
DESCRIPTION = (
    "A grown son lives four minutes away. His phone dies. Six minutes later his mother is holding a press conference."
)
ACCESSIBILITY = (
    "A cartoon: a fox leaves his desk swinging his keys, his mother on speaker. At home his phone is dead. A sloth "
    "with a flashlight tells him he is alive and she is holding line two. A helicopter lights his window; his "
    "mother, a cat, speaks at a podium on live news. He sends one word, home. Every phone in the search crowd lights "
    "and they walk away; his mother reads it out and asks who that is."
)
NARRATION = (
    "Voiced with ElevenLabs premade voices Liam (the son), Laura (Mom) and Brian (the neighbour); synthesised foley."
)
NOTE = "ElevenLabs premade voices Liam, Laura and Brian at their natural pace; no reference-voice cloning."
SON = Speaker("son", Voice(role="son", id="TX3LPaxmHKxFdv7VOQHJ", name="Liam"), VoiceSettings(0.5, 0.75, 0.3), "fox")
MOM = Speaker("mom", Voice(role="mom", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"), VoiceSettings(0.45, 0.75, 0.45), "cat")
NEIGHBOUR = Speaker(
    "neighbour",
    Voice(role="neighbour", id="nPczCjzI2devNBz1zQrb", name="Brian"),
    VoiceSettings(0.6, 0.75, 0.2),
    "sloth",
)
TINTS = {"son": "#f8dcc0", "mom": "#e6dcf6", "neighbour": "#dcebd2"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
LATER = "Six minutes later"
STAGES = ("office", "home", "chopper", "plug", "stare")
CALLER = dict(at=(438.0, 826.0), scale=1.0)  # Mom on speaker on the desk, clear of the marks
KEYS = dict(coat=toon_inked.FOX_INKED.coat, y=520.0, reach=270.0, holding="keys")
TORCH = dict(coat="#b6a388", y=610.0, reach=210.0, holding="torch")
INSERT, THUMB = "#2b2147", toon_inked.FOX_INKED.coat
BIG_PHONE = dict(at=(296.0, 880.0), scale=2.0)
ZOOM = (1.07, (1000.0, 1420.0))  # the opening's push: both signature marks stay in frame
STRAPS = ("MISSING: SON, 34. NOT TEXTING.", "UPDATE: SOMEONE IS 'HOME'")
SEARCHERS = 7
DING_STEP = 0.1  # seconds between one searcher's phone and the next
END = 18.5

LINES = (
    Line("mom", "Text me when you get home."),
    Line("son", "I live four minutes away."),
    Line("neighbour", "You're alive. She's holding line two."),
    Line("mom", "He said four minutes."),
    Line("mom", "Who's home? Text me when you get home."),
)

SCRIPT = scripting.Script(LINES)
say, hold, first, part = SCRIPT.say, SCRIPT.hold, SCRIPT.first, SCRIPT.part
BEATS = (
    hold(0.0, "fox", "", "half", "flat", "desk"),
    say(0.15, "fox", 0, "half", "flat", "desk"),
    say(1.6, "fox", 1, "roll", "flat", "desk"),
    hold(3.1, "fox", "", "wide", "flat", "desk", "stage:home"),  # home, the phone dead
    hold(3.7, "fox", "", "side", "flat", "desk", "knock"),
    say(4.3, "sloth", 2, "sleepy", "flat", "desk"),
    hold(6.3, "fox", "", "wide", "grimace", "desk", "stage:chopper"),
    say(7.7, "cat", 3, "half", "flat", "desk"),
    hold(9.2, "fox", "", "wide", "grimace", "desk", "stage:plug"),
    hold(11.95, "sloth", "", "sleepy", "flat", "desk", "ding"),  # the street empties
    hold(14.15, "cat", "", "side", "flat", "desk"),  # she reads it
    first(14.65, "cat", 4, "Who's home?", "half", "flat", "desk"),
    part(15.55, "cat", 4, 2, "Text me when you get home.", "half", "flat", "desk"),
    hold(16.95, "fox", "", "half", "flat", "desk", "stage:stare"),  # stop on the son
)
SKETCH = Sketch(SLUG, TITLE, (SON, MOM, NEIGHBOUR), LINES, BEATS, END)


def stages(beats) -> list[tuple[float, str]]:
    """What the son's shots show, from 0."""
    return scripting.changes(beats, "stage", STAGES[0])


def dings(beats) -> list[float]:
    """Each searcher's phone, one after the other from the ``ding``."""
    at = sketch.events(beats, "ding")[0][0] + 0.35
    return [round(at + i * DING_STEP, 3) for i in range(SEARCHERS)]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, moves from the first frame with Mom's line within half a second, runs the son's stages
    in order on his shots, knocks once before the neighbour, dings once after the phone; no other events."""
    sketch.check(sk)
    if sk.beats[0].who != "fox" or next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the sketch opens on the son with Mom's first line inside half a second")
    names = [name for _, name in stages(sk.beats)]
    if names != list(STAGES):
        raise sketch.SketchError(f"the stages run in order, got {names}")
    who_at = {b.start: b.who for b in sk.beats}
    if any(who_at[at] != "fox" for at, _ in sketch.events(sk.beats, "stage")):
        raise sketch.SketchError("a stage changes on the son's shot")
    scripting.exactly_once(sk.beats, "knock", "one knock")
    scripting.exactly_once(sk.beats, "ding", "one send")
    named = dict((name, at) for at, name in stages(sk.beats))
    if not sketch.events(sk.beats, "ding")[0][0] > named["plug"]:
        raise sketch.SketchError("the phones ding after he sends")
    scripting.only_events(sk.beats, {"stage", "knock", "ding"})
    if len(dings(sk.beats)) != SEARCHERS or dings(sk.beats)[-1] + toon_world.LEAVE >= sk.end:
        raise sketch.SketchError("every searcher leaves before the end")


def dress(shot) -> None:
    """The son's shots change place; the neighbour stands in the street, Mom at the podium."""
    if shot.app.who == "fox":
        for a, b, name in scripting.spans(stages(shot.beats), shot.app.start, shot.app.end):
            _son(shot, name, a, b)
    elif shot.app.who == "sloth":
        _street(shot)
    else:
        _podium(shot)


def _son(shot, name: str, a: float, b: float) -> None:
    cv = shot.cv
    back = cv.group(shot.back, cv.uid("g"), start=a, end=b)
    front = cv.group(shot.front, cv.uid("g"), start=a, end=b)
    if name == "office":
        toon.room(cv, back)
        toon.desk(cv, front)
        screens = [Screen(0.0, "notify", "Mom", "On speaker", "6:00")]
        toon_everyday.phone(cv, front, screens, measure=shot.measure, id=cv.uid("phone"), **CALLER)
        toon_world.paw(cv, front, ((a, b + 0.2),), **KEYS)
        return
    toon_sets.home(cv, back, end=shot.end)
    toon_props.clock(cv, back, [(0.0, "06:06")], at=(90, 380))
    if name != "plug":
        toon.desk(cv, front)
    dead = [Screen(0.0, "off")]
    last = [Screen(0.0, "notify", "Mom", "113 missed calls", "6:11")]
    if name == "home":
        toon_everyday.phone(cv, front, dead, measure=shot.measure, id=cv.uid("phone"), **CALLER)
        spoken = partial(shot.measure, size=BADGE_SIZE)
        toon_props.badge(cv, front, LATER, a, b, spoken, BADGE_SIZE)
    elif name == "chopper":
        toon_everyday.phone(cv, front, dead, measure=shot.measure, id=cv.uid("phone"), **CALLER)
        toon_world.chopper(cv, back, a, b, over=front)
    elif name == "plug":
        _insert(shot, front, a)
    else:
        toon_everyday.phone(cv, front, last, measure=shot.measure, id=cv.uid("phone"), **CALLER)


def _insert(shot, front, a: float) -> None:
    """The phone comes up over him as it wakes, the desk and its marks still under it: the missed calls, the word."""
    cv = shot.cv
    cv.rect(front, 0, 0, cv.width, cv.height, INSERT)
    toon_world.ledge(cv, front, toon.DESK_TOP, toon.DESK_FRONT, toon.DESK_CODE)
    screens = [
        Screen(0.0, "off"),
        Screen(a + 0.2, "notify", "Mom", "112 missed calls", "6:09"),
        Screen(a + 1.05, "code", "To: Mom", "home"),
        Screen(a + 1.9, "loading", "Sent", "1 word"),
    ]
    toon_everyday.phone(cv, front, screens, measure=shot.measure, hand=THUMB, id=cv.uid("phone"), **BIG_PHONE)


def _street(shot) -> None:
    cv, app = shot.cv, shot.app
    ding = sketch.events(shot.beats, "ding")[0][0]
    leave = dings(shot.beats) if app.start <= ding < app.end else ()
    toon_world.night_street(cv, shot.back, leave, shot.end)
    toon_world.ledge(cv, shot.front, "#3a3f5c", "#2a2e45", "#7f86a6")
    if not leave:
        toon_world.paw(cv, shot.front, ((app.start, app.end + 0.2),), **TORCH)


def _podium(shot) -> None:
    cv, app = shot.cv, shot.app
    first = min(app.start for app in sketch.appearances(shot.beats, shot.end) if app.who == "cat")
    flashes = () if app.start > first else tuple(round(app.start + 0.2 + i * 0.32, 2) for i in range(5))
    toon_world.press_room(cv, shot.back, flashes)
    toon_world.ledge(cv, shot.front, "#22315c", "#2b3e74", "#8ea2d4")
    toon_world.mics(cv, shot.front)
    strap = STRAPS[0] if app.start == first else STRAPS[1]
    if app.start != first:
        reading = [Screen(0.0, "notify", "Son", "home", "6:10")]
        toon_everyday.phone(cv, shot.front, reading, measure=shot.measure, id=cv.uid("phone"), **CALLER)
    toon_world.lower_third(cv, shot.front, [(app.start, app.end, strap)], shot.measure, 58)


def push(shot, setup) -> None:
    """The opening pushes in on him from the first frame; the set after the stage change holds."""
    if shot.app.start != 0.0:
        return
    at = dict((name, t) for t, name in stages(shot.beats))["home"]
    scale, (x, y) = ZOOM
    camera.anchor(setup, x, y, place=True)
    camera.push_in(shot.cv, setup, scale=((0.0, 1.0), (at - 0.04, scale), (at, 1.0)))


def sounds(beats, end: float) -> list[Sound]:
    """The phone ringing under Mom, the keys, the knock, the rotor, the searchers' phones."""
    named = dict((name, at) for at, name in stages(beats))
    knock = sketch.events(beats, "knock")[0][0]
    sent = sketch.events(beats, "ding")[0][0] - 0.3
    return [
        Sound("knock", foley.KNOCK, (knock, knock + 0.2, knock + 0.4), 0.0),
        Sound("chopper", foley.CHOPPER, (named["chopper"],), -8.0),
        Sound("sent", foley.REMOTE_CLICK, (sent,), -2.0),
        Sound("ding", foley.BELL, tuple(dings(beats)), -6.0),
    ]

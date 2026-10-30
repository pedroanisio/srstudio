"""Who Touched It — the sketch as data: Dad knows at once when the thermostat moves. A teenager's finger, an inch from
68. Click: 69. Upstairs, Dad's eyes open. Then he is in the hallway. One degree. He licks a finger; he sniffs the vent;
he knows about the fan as well. The kid nudges it back, and Dad, already in bed, says thank you.

Two voices (ElevenLabs premade River as the kid, Brian as Dad). The kid at the thermostat
(:func:`srstudio.toon_house.thermostat`), Dad in bed (:func:`srstudio.toon_house.bedroom`) and Dad in the hallway. The
sketch opens on a still first second (the ``sp-hook_motion`` test's arm A). ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress` draws each
shot's set and props, :func:`lens` its camera and :func:`foley` its sound.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, scripting, sketch, toon_house
from srstudio import foley as synth
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 2403
SLUG = "who-touched-it"
TITLE = "Who Touched It — Dad and the Thermostat (Toon)"
DESCRIPTION = (
    "A Toon sketch at home: a teenager moves the thermostat one degree while Dad is asleep upstairs. Dad's eyes open. "
    "He is in the hallway before the kid has lowered his finger."
)
ACCESSIBILITY = (
    "A cartoon hedgehog teenager holds a finger an inch from a wall thermostat reading 68, under the line Dad is "
    "asleep upstairs. He clicks it to 69. In a dark bedroom a goat in bed opens his eyes. Then the goat is in the "
    "hallway. He licks a finger, holds it up, sniffs the vent. The kid clicks it back to 68. The goat is back in bed "
    "with his eyes shut, saying thank you. The kid stands alone, staring. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices River (the kid) and Brian (Dad); synthesised click and floorboard."
NOTE = "ElevenLabs premade voices River and Brian at their natural pace; no reference-voice cloning."
KID = Speaker(
    "kid",
    Voice(role="kid", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35),
    "hedgehog",
)
DAD = Speaker(
    "dad",
    Voice(role="dad", id="nPczCjzI2devNBz1zQrb", name="Brian"),
    VoiceSettings(stability=0.70, similarity_boost=0.75, style=0.15),
    "goat",
)
TINTS = {"kid": "#d9f0e3", "dad": "#f3e3c3"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

KEY_LINE = "Dad is asleep upstairs."
STILL = 1.0  # seconds of the held first frame
FIGURES = {"hedgehog": (1.3, 0.0), "goat": (1.2, 0.0)}
THERMOSTAT = {"at": (452, 452), "scale": 1.3}
TIP, ANGLE = (440, 610), -8.0  # an inch below the dial
PRESS = (444, 574)
SKIN, GOAT_COAT = "#e9c79a", "#a78fd3"
LICKED = (398, 700)  # Dad's finger comes up beside his face
LICK_RISE = (398, 520)
BEDROOM_DIM = ("#141c3d", 0.34)
PIVOT, PUNCH = (980, 1200), 1.12
FLOORBOARD = ((96.0, 74.0, 0.32),)
THANKS = 4  # the line Dad says from the bed
END = 15.0

LINES = (
    Line("dad", "Who touched it."),
    Line("kid", "Touched what?"),
    Line("dad", "One degree."),
    Line("dad", "This morning you moved the fan as well."),
    Line("dad", "Thank you."),
)

script = scripting.Script(LINES)
hold, say, first, part = script.hold, script.say, script.first, script.part

BEATS = (
    hold(0.0, "hedgehog", "", "side", "flat", "desk"),  # the still: the finger an inch away
    hold(1.3, "hedgehog", "", "side", "smirk", "desk", "click"),  # 69
    hold(2.5, "goat", "", "closed", "flat", "desk"),  # Dad, asleep
    hold(3.05, "goat", "", "wide", "flat", "desk", "board"),  # his eyes open, and nothing else moves
    hold(3.85, "hedgehog", "", "half", "smirk", "desk"),  # the kid, pleased with himself
    say(4.95, "goat", 0, "narrow", "flat", "desk"),
    say(5.8, "hedgehog", 1, "side", "grimace", "desk", wear=("sweat",)),
    hold(6.7, "goat", "", "narrow", "tongue", "desk", "lick"),
    say(7.4, "goat", 2, "narrow", "flat", "desk"),
    hold(8.3, "goat", "", "closed", "o", "desk", "sniff"),
    first(9.1, "goat", 3, "This morning", "narrow", "flat", "desk"),
    part(9.9, "goat", 3, 2, "you moved the fan as well.", "narrow", "flat", "desk"),
    hold(11.1, "hedgehog", "", "shock", "grimace", "desk", wear=("sweat",)),
    hold(12.0, "hedgehog", "", "down", "grimace", "desk", "click", wear=("sweat",)),  # back to 68
    say(13.0, "goat", 4, "closed", "flat", "desk"),  # already in bed
    hold(13.9, "hedgehog", "", "shock", "none", "desk", wear=("sweat",)),  # alone: stop on the kid
)
SKETCH = Sketch(SLUG, TITLE, (KID, DAD), LINES, BEATS, END)


def readings(beats) -> list[tuple[float, str]]:
    """The dial: 68, then 69 at the first click, then 68 at the second."""
    (first, _), (second, _) = sketch.events(beats, "click")
    return [(0.0, "68"), (first, "69"), (second, "68")]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the first beat is the still (silent,
    uncaptioned, held at least :data:`STILL`); the kid clicks twice; the floorboard, the lick and the sniff each
    happen once, in that order; no other events."""
    sketch.check(sk)
    opening, second = sk.beats[0], sk.beats[1]
    if opening.spoken or opening.caption or second.start < STILL:
        raise sketch.SketchError(f"the sketch opens on a still of the kid: silent, uncaptioned, held {STILL} s")
    if len(sketch.events(sk.beats, "click")) != 2:
        raise sketch.SketchError("the kid clicks the dial twice: up, and back")
    for event in ("board", "lick", "sniff"):
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    order = [sketch.events(sk.beats, e)[0][0] for e in ("board", "lick", "sniff")]
    if order != sorted(order):
        raise sketch.SketchError("the floorboard, then the lick, then the sniff")
    scripting.only_events(sk.beats, {"click", "board", "lick", "sniff"})


def no_desk(cv, parent) -> None:
    """Each shot lays its own surface: see :func:`dress`."""


def in_bed(app, beats) -> bool:
    """Dad's first shot, with the floorboard in it, and his last, with the thank you; the others are in the hallway."""
    inside = [b for b in beats if app.start <= b.start < app.end]
    return app.who == "goat" and any(b.event == "board" or b.line == THANKS for b in inside)


def dress(shot) -> None:
    """The kid at the thermostat, in every one of his shots; Dad in bed, dimmed; Dad in the hallway by the vent."""
    cv, app = shot.cv, shot.app
    end = shot.end
    if app.who == "hedgehog":
        clicks = [t for t, _ in sketch.events(shot.beats, "click")]
        toon_house.hallway(cv, shot.back, door="none")
        toon_house.ledge(cv, shot.front, "oak")
        toon_house.thermostat(cv, shot.back, readings(shot.beats), end, id=cv.uid("thermostat"), **THERMOSTAT)
        moves = [
            (clicks[0] - 0.12, *PRESS),
            (clicks[0] + 0.1, *TIP),
            (clicks[1] - 0.12, *PRESS),
            (clicks[1] + 0.1, *TIP),
        ]
        toon_house.finger(cv, shot.back, TIP, ANGLE, SKIN, SKIN, moves=moves, end=end, id=cv.uid("finger"))
        if app.start == 0:
            toon_house.key_line(cv, shot.front, KEY_LINE, 0.0, app.end, measure=shot.measure)
    elif in_bed(app, shot.beats):
        toon_house.bedroom(cv, shot.back)
        toon_house.quilt(cv, shot.front, "plum")
        colour, opacity = BEDROOM_DIM
        cv.rect(shot.light, 0, 0, cv.width, cv.height, colour, opacity=opacity)
    else:
        toon_house.hallway(cv, shot.back, door="none")
        toon_house.vent(cv, shot.back)
        toon_house.ledge(cv, shot.front, "oak")
        lick = sketch.events(shot.beats, "lick")[0][0]
        if not app.start <= lick < app.end:
            return
        toon_house.finger(
            cv, shot.back, LICKED, 0.0, GOAT_COAT, GOAT_COAT, moves=[(lick + 0.5, *LICK_RISE)],
            start=lick, end=sketch.events(shot.beats, "sniff")[0][0], id=cv.uid("finger"),
        )  # fmt: skip


def lens(shot, setup) -> None:
    """Still for the first shot; a small step in on Dad as he says what else he knows."""
    if shot.app.who == "goat" and not in_bed(shot.app, shot.beats):
        camera.anchor(setup, *PIVOT, place=True)
        starts = {b.line: b.start for b in reversed(shot.beats) if b.line is not None}
        camera.zoom_holds(shot.cv, setup, [(0.0, 1.0), (starts[3], PUNCH)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The dial's click, one floorboard, and the sniff."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    click = synth.write_typing(audio / "click.wav", [at for at, _ in sketch.events(beats, "click")], end)
    board = synth.write_tones(audio / "board.wav", [at for at, _ in sketch.events(beats, "board")], end, FLOORBOARD)
    sniff = synth.write_whoosh(audio / "sniff.wav", [at for at, _ in sketch.events(beats, "sniff")], end)
    return [
        sketch.effect("click", 0.0, -4.0, root, click),
        sketch.effect("board", 0.0, -3.0, root, board),
        sketch.effect("sniff", 0.0, -12.0, root, sniff),
    ]

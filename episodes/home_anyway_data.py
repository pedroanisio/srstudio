"""Home Anyway — the sketch as data: while you look for a job, the person you live with thinks you are simply at home,
and home is where the plumber goes.

Bruno is at the kitchen table on day 41 of a job hunt, and Mae, on her way out, hands him the day one note at a time:
the plumber, the car, her mother at the airport. Every note lands on his laptop, over the listing. He has one card
left, a final interview at three, and she is thrilled, and she has one more note: can he move it? He's home anyway.

Two voices (ElevenLabs premade Sarah as Mae, Bill as Bruno), their own flat: the kitchen
(:func:`srstudio.toon_sets.kitchen`) and the hall by the front door (:func:`srstudio.toon_house.hallway`). The
laptop faces us (:func:`srstudio.toon_laptop.open_laptop`), so the notes are the gag on screen. ``ROWS`` act them per
beat; her arm is rooted on her own shoulder, past the frame's edge when she is out of shot
(:func:`srstudio.toon_pair.reach`), and :func:`dress` draws the six framings, :func:`lens` the push and :func:`sounds`
the room.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, foley, scripting, sketch, toon_house, toon_laptop, toon_pair, toon_sets
from srstudio.scripting import at, times
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon import fh
from srstudio.toon_laptop import Note, Quad
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3406
SLUG = "home-anyway"
TITLE = "Home Anyway — Mae and Bruno (Toon)"
DESCRIPTION = (
    "A Toon sketch at a kitchen table: he is job hunting, she is on her way out, and every errand of her day lands on "
    "his laptop as a note, because he's home anyway."
)
ACCESSIBILITY = (
    "A cartoon bear types at a laptop on a kitchen table. A white paw comes in and slaps a yellow note on the screen. "
    "A cartoon rabbit walks past and slaps on two more as she goes, then looks for her bag. He points at what is left "
    "of the page. She speaks from the front door, then comes back with one more note. He looks at the screen: all "
    "notes, one bare corner. He tells her he has a final interview at three. She lights up and puts a paw on his "
    "cheek, peels back one note, reads it and presses it down again, and sticks the last note on the bare corner. The "
    "last frame is his face. Lines appear in tinted pills and a bar says it is day 41 of the job hunt."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae) and Bill (Bruno)."
NOTE = "ElevenLabs premade voices Sarah and Bill at their natural pace; no reference-voice cloning."
MAE = Speaker(
    "mae", Voice(role="mae", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"), VoiceSettings(0.6, 0.75, 0.2), "rabbit"
)
BRUNO = Speaker(
    "bruno", Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"), VoiceSettings(0.5, 0.75, 0.3), "bear"
)
TINTS = {"mae": "#f9dbe6", "bruno": "#eccfae"}
MEDIUM, TWO, DOOR, HERS, SCREEN, CLOSE = "hamster", "goat", "sloth", "fox", "dog", "frog"  # never seen: shots' names
BARE = (MEDIUM, TWO, DOOR, HERS, SCREEN, CLOSE)
RABBIT_COAT = "#efe8ee"
OVERLAY = "JOB HUNT, DAY 41"

SEAT_AT = (165.0, 840.0)  # Bruno at the table, the laptop at his right hand, in the medium
PAIR_SCALE = 0.72
HIS_AT, HER_AT = (95.0, 876.0), (430.0, 876.0)  # the two-shot: low enough that the table takes both pairs of paws
CLOSE_AT, CLOSE_SCALE = (190.0, 900.0), 1.3
HER_MEDIUM_AT = (400.0, 850.0)
HALL_AT = (210.0, 850.0)
FAR_QUAD = Quad((214.0, 664.0), (340.0, 646.0), (346.0, 776.0), (214.0, 768.0))
NEAR_QUAD = toon_laptop.THREE_QUARTER
FULL_QUAD = Quad((42.0, 344.0), (548.0, 330.0), (552.0, 742.0), (42.0, 732.0))
SPOTS = ((0.23, 0.29, -3.0), (0.63, 0.27, 2.0), (0.22, 0.75, 2.0), (0.56, 0.74, -2.0), (0.83, 0.75, 3.0))
HIS_CHEEK = (214.0, 712.0)
HER_ARM_AT = (
    HER_AT[0] + 36.0,
    HER_AT[1] + 31.0,
)  # the arm's root in her flank and under the table's edge, never its end
OFF_ARM_AT = (740.0, 876.0)  # her out of the medium: the arm comes from a shoulder past the frame's right edge
PEEL = 1  # the note she peels back: the second, top right
OFF = 300.0  # reference pixels off frame, to her right
NOTE_AFTER = (0.16, 0.5, 0.16, 0.5, 0.16)  # seconds from each note's beat to its landing: two wait for her walk in
LAST_WORD = 1.0  # seconds from the last word's start to the end: the last pat of the note lands on it
ARM_STAY = 0.55
ARM_GONE = 0.16  # seconds an arm takes to leave

LINES = (
    Line("mae", "You're home anyway, so the plumber's coming."),
    Line("bruno", "Babe, I'm job hunting."),
    Line("mae", "Totally. Between ten and four."),
    Line("mae", "And the car needs an oil change."),
    Line("bruno", "When do I write applications?"),
    Line("mae", "You're home anyway."),
    Line("mae", "Oh! My mom lands at two o'clock."),
    Line("bruno", "The airport's an hour away."),
    Line("mae", "Right, but you're home anyway."),
    Line("bruno", "I have a final interview at three."),
    Line("mae", "Babe! That's amazing!"),
    Line("mae", "Can you move it? You're home anyway."),
)
script = scripting.Script(LINES)
say, first, part, hold = script.say, script.first, script.part, script.hold
TOP = ("up", "flat", "desk")
# Mae: fast, kind, already somewhere else; she never looks at him for long
OFF_SHOT = Act("half", "flat", "desk")
AT_LAPTOP = Act("left", "grin", "desk")
FOR_BAG = Act("up", "flat", "desk")
KIND = Act("left", "grin", "desk")
OH = Act("wide", "flat", "desk")
PATIENT = Act("half", "smirk", "desk")
THRILLED = Act("wide", "grin", "desk")
READING = Act("left", "flat", "desk")
# Bruno: slow, reasonable, losing
TYPING = Act("side", "flat", "type")
UP = Act("side", "flat", "desk")
POINTS = Act("side", "frown", "lean")
TIRED = Act("half", "frown", "desk")
CARD = Act("wide", "flat", "desk")
ALMOST = Act("side", "smirk", "desk")
GONE = Act("wide", "flat", "desk")
BLANK = Act("half", "flat", "desk")

ROWS = (
    (hold(0.0, MEDIUM, "", *TOP), OFF_SHOT, TYPING),
    (first(0.3, MEDIUM, 0, "You're home anyway,", *TOP, "note:1"), OFF_SHOT, UP),
    (part(1.6, MEDIUM, 0, 3, "so the plumber's coming.", *TOP), OFF_SHOT, UP),
    (say(2.8, MEDIUM, 1, *TOP), OFF_SHOT, UP),
    (say(4.2, TWO, 2, *TOP, "note:2"), AT_LAPTOP, UP),
    (say(6.2, TWO, 3, *TOP, "note:3"), FOR_BAG, UP),
    (hold(8.33, TWO, "", *TOP, "out"), FOR_BAG, TIRED),
    (say(8.7, MEDIUM, 4, *TOP), OFF_SHOT, POINTS),
    (say(10.4, DOOR, 5, *TOP), KIND, TIRED),
    (say(11.8, TWO, 6, *TOP, "note:4"), OH, TIRED),
    (say(14.2, MEDIUM, 7, *TOP), OFF_SHOT, TIRED),
    (say(15.8, HERS, 8, *TOP), PATIENT, TIRED),
    (hold(17.62, SCREEN, "", *TOP, "hum"), PATIENT, TIRED),  # the held silence: the page is gone
    (say(19.05, CLOSE, 9, *TOP, "card"), PATIENT, CARD),
    (say(21.0, TWO, 10, *TOP, "cheek"), THRILLED, ALMOST),
    (hold(22.74, TWO, "", *TOP, "peel"), READING, ALMOST),  # the held silence: he almost smiles, she reads
    (first(23.95, MEDIUM, 11, "Can you move it?", *TOP, "note:5"), READING, GONE),
    (part(25.1, CLOSE, 11, 4, "You're home anyway.", *TOP, "face"), READING, BLANK),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = {"rabbit": tuple(row[1] for row in ROWS), "bear": tuple(row[2] for row in ROWS)}
ONCE = ("out", "hum", "card", "cheek", "peel", "face")
END = 26.5
SKETCH = Sketch(SLUG, TITLE, (MAE, BRUNO), LINES, BEATS, END, tail=0.3, bare=BARE)
SLAP = foley.Burst(0.09, 2600.0, attack=0.001, decay=0.3, tone_hz=240.0, tone_end_hz=120.0, tone=0.4)
PAT = foley.Burst(0.08, 1300.0, attack=0.002, decay=0.3, tone_hz=180.0, tone_end_hz=110.0, tone=0.4)
HUM = replace(foley.HUM, seconds=1.4)
PEELED = foley.Burst(0.22, 5200.0, attack=0.02, decay=0.6, flutter_hz=40.0)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, five notes land in order and the events run in the script's order."""
    sketch.check(sk)
    scripting.speaks_by(sk.beats, 0.5)
    scripting.only_events(sk.beats, {*ONCE, "note"})
    for kind in ONCE:
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    if [n for _, n in sketch.events(sk.beats, "note")] != ["1", "2", "3", "4", "5"]:
        raise sketch.SketchError("the notes run from one to five")
    order = [at(sk.beats, kind) for kind in ONCE]
    if order != sorted(order):
        raise sketch.SketchError("the events run in the script's order")


def lands(beats) -> list[float]:
    """When each note lands, after its beat: a paw's reach, or her walk in and then the reach."""
    return [t + after for t, after in zip(times(beats, "note"), NOTE_AFTER, strict=True)]


def notes(beats) -> tuple[Note, ...]:
    """The five notes, in the order they land; the second lifts through the held silence."""
    peel = at(beats, "peel")
    out = []
    for i, ((u, v, tilt), on) in enumerate(zip(SPOTS, lands(beats), strict=True)):
        out.append(Note(u, v, on, tilt, (peel + 0.25, peel + 1.05) if i == PEEL else None))
    return tuple(out)


def overlay(cv, parent, beats, end, measure) -> None:
    """The day of the job hunt, once, over the opening; never the line's words."""
    toon_house.key_line(cv, parent, OVERLAY, 0.0, 3.2, measure=measure)


def sounds(beats, end) -> tuple[Sound, ...]:
    """A slap on every note, the keys on her way through, the fridge through the hold, the peel, the last pat."""
    slaps = tuple(round(t, 3) for t in lands(beats))
    door, peel, hum = at(beats, "out"), at(beats, "peel"), at(beats, "hum")
    return (
        Sound("slap", SLAP, slaps, -8.0),
        Sound("keys", foley.CLINK, (0.42, 0.5, round(door + 0.05, 3), round(door + 0.14, 3)), -20.0),
        Sound("hum", HUM, (hum,), -20.0),
        Sound("peel", PEELED, (round(peel + 0.25, 3), round(peel + 0.9, 3)), -18.0),
        Sound("pat", PAT, (round(end - LAST_WORD, 3),), -7.0),
    )


def _laptop(shot, quad: Quad, **options) -> None:
    toon_laptop.open_laptop(shot.cv, shot.front, notes(shot.beats), quad=quad, **options)


def _arm(shot, parent, at, target, start, end, scale, away) -> None:
    """Her arm on ``target`` from ``start`` to ``end``, leaving by ``away`` (px on x and y) instead of popping off."""
    cv = shot.cv
    g = cv.group(parent, cv.uid("g"))
    for prop, by in zip(("x", "y"), away, strict=True):
        cv.keys(g, prop, [(end - ARM_GONE, 0.0), (end, by)], hold=False, kind="sine-in-out", local=False)
    toon_pair.reach(cv, g, at, target, RABBIT_COAT, start, end, scale=scale)


def _medium(shot) -> None:
    """Bruno at the table, the laptop at his right hand. Mae is out of frame; her arm is, from past the right edge."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    toon_sets.kitchen(cv, shot.back)
    toon_pair.figure(shot, shot.back, "bear", SEAT_AT, ACTS["bear"])
    _laptop(shot, NEAR_QUAD)
    for spot, t, after in zip(SPOTS, lands(beats), NOTE_AFTER, strict=True):
        if app.start <= t - after < app.end:
            stay = min(t + ARM_STAY, app.end)
            _arm(
                shot,
                shot.front,
                OFF_ARM_AT,
                NEAR_QUAD.at(spot[0], spot[1]),
                t - toon_pair.LAND,
                stay,
                1.0,
                (fh(300.0), 0.0),
            )
    toon_house.ledge(cv, shot.front)


def _walks(cv, parent, app, beats):
    """A group that walks what is in it: in from the right as the shot opens, and out on ``out``."""
    g = cv.group(parent, cv.uid("g"))
    far = fh(OFF)
    keys = [(app.start, far), (app.start + 0.34, 0.0)]
    out = [t for t in times(beats, "out") if app.start < t < app.end]
    if out:
        keys += [(out[0], 0.0), (out[0] + 0.36, far)]
    cv.keys(g, "x", keys, hold=False, kind="sine-in-out", local=False)
    return g


def _two(shot) -> None:
    """The two of them either side of the laptop. Her arm is rooted on her own shoulder and walks with her."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    toon_sets.kitchen(cv, shot.back)
    toon_pair.figure(shot, shot.back, "bear", HIS_AT, ACTS["bear"], scale=PAIR_SCALE)
    toon_pair.figure(shot, _walks(cv, shot.back, app, beats), "rabbit", HER_AT, ACTS["rabbit"], scale=PAIR_SCALE)
    _laptop(shot, FAR_QUAD, foot=22.0, shift=-26.0)
    arms = _walks(cv, shot.front, app, beats)
    down = (0.0, fh(260.0))
    for spot, t, after in zip(SPOTS, lands(beats), NOTE_AFTER, strict=True):
        if app.start <= t - after < app.end:
            target = FAR_QUAD.at(spot[0], spot[1])
            _arm(shot, arms, HER_ARM_AT, target, t - toon_pair.LAND, t + ARM_STAY, PAIR_SCALE, down)
    if app.start <= at(beats, "cheek") < app.end:
        cheek, peel = at(beats, "cheek"), at(beats, "peel")
        _arm(shot, arms, HER_ARM_AT, HIS_CHEEK, cheek + 0.5, peel, PAIR_SCALE, down)
        target = FAR_QUAD.at(*SPOTS[PEEL][:2])
        _arm(shot, arms, HER_ARM_AT, target, peel + 0.1, peel + 1.15, PAIR_SCALE, down)
    toon_house.ledge(cv, shot.front)


def _door(shot) -> None:
    """Mae at the front door, already going, turning back to him off to the left."""
    cv = shot.cv
    toon_house.hallway(cv, shot.back)
    toon_pair.figure(shot, shot.back, "rabbit", HALL_AT, ACTS["rabbit"])
    toon_house.ledge(cv, shot.front)


def _hers(shot) -> None:
    """Mae on her side of the kitchen, as in the two-shot, closer, his empty side out of it."""
    cv = shot.cv
    toon_sets.kitchen(cv, shot.back, chair=False)
    toon_pair.figure(shot, shot.back, "rabbit", HER_MEDIUM_AT, ACTS["rabbit"])
    toon_house.ledge(cv, shot.front)


def _screen(shot) -> None:
    """What he is looking at: the page, gone, but for one corner."""
    cv = shot.cv
    toon_sets.kitchen(cv, shot.back, chair=False)
    _laptop(shot, FULL_QUAD, foot=46.0, shift=-40.0)
    toon_house.ledge(cv, shot.front)


def _close(shot) -> None:
    """His face. The marks stay where the table has them, so no push loses them."""
    cv = shot.cv
    toon_sets.kitchen(cv, shot.back)
    toon_pair.figure(shot, shot.back, "bear", CLOSE_AT, ACTS["bear"], scale=CLOSE_SCALE)
    toon_house.ledge(cv, shot.front)


def dress(shot) -> None:
    """The kitchen in five framings and the hall by the door."""
    {MEDIUM: _medium, TWO: _two, DOOR: _door, HERS: _hers, SCREEN: _screen, CLOSE: _close}[shot.app.who](shot)


def lens(shot, setup) -> None:
    """One slow push, on his one card, its pivot low and right so both marks stay whole in the frame."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    if app.who == CLOSE and app.start <= at(beats, "card") < app.end:
        camera_push(cv, setup, app.start, app.end)


def camera_push(cv, setup, start: float, end: float) -> None:
    camera.anchor(setup, 880.0, 1200.0, place=True)
    scale = [(start, 1.0), (end, 1.07)]
    cv.keys(setup, "scaleX", scale, hold=False, kind="sine-in-out", local=False)
    cv.keys(setup, "scaleY", scale, hold=False, kind="sine-in-out", local=False)

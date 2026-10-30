"""Representative — the sketch as data: everyone has shouted one word at a phone menu, and the menu has heard another.
Gus, on speaker with a calm menu at night, says representative. The menu hears reservation: party of seven, a travel
agent to Lisbon, a horse, a human added to the horse. Did that solve your problem today? No. Great! The doorbell. A
man at the door with a horse: "Hi. Reservation?"

Three voices (ElevenLabs premade Liam as Gus, Alice as the menu, heard only, Bill as the man), one shot per place:
Gus at his table in the living room at night, the phone on speaker and the booking filling in on a clipboard beside
it (``book:`` events) until it is stamped on "Great!" (``stamp``); the man at the open front door with the horse
(:func:`srstudio.toon_house.horse`). The sketch opens on a still first second (the ``sp-hook_motion`` test's arm A):
Gus, already furious, under the premise line, before anyone speaks. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress` draws each
shot's set and props, :func:`lens` its camera and :func:`foley` its sound.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, scripting, sketch, toon_everyday, toon_house, toon_rooms
from srstudio import foley as synth
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 2401
SLUG = "representative"
TITLE = "Representative — Gus and the Menu (Toon)"
DESCRIPTION = (
    "A Toon sketch on the phone: Gus shouts representative at a calm phone menu, which books a party of seven, a "
    "trip to Lisbon, one horse and a human for the horse. Then the doorbell rings."
)
ACCESSIBILITY = (
    "A furious cartoon hamster shouts at a phone on speaker on a table in a living room at night, beside a clipboard "
    "titled Your Booking. As he shouts, a calm voice fills it in: party of seven, Lisbon, one horse, one human, then "
    "a red stamp reads Booked. The doorbell rings. At the open front door a cartoon bear stands with a horse in "
    "a halter, which looks straight at the camera. Lines appear in tinted pills; the calm voice is heard only."
)
NARRATION = "Voiced with ElevenLabs premade voices Liam (Gus), Alice (the menu) and Bill (the man); synthesised bell."
NOTE = "ElevenLabs premade voices Liam, Alice and Bill at their natural pace; no reference-voice cloning."
GUS = Speaker(
    "gus",
    Voice(role="gus", id="TX3LPaxmHKxFdv7VOQHJ", name="Liam"),
    VoiceSettings(stability=0.32, similarity_boost=0.75, style=0.55),
    "hamster",
)
MENU = Speaker(
    "menu",
    Voice(role="menu", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    VoiceSettings(stability=0.75, similarity_boost=0.75, style=0.10),
)
MAN = Speaker(
    "man",
    Voice(role="man", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.20),
    "bear",
)
TINTS = {"gus": "#ffd9c7", "menu": "#d9e8ff", "man": "#ecdcc4"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
KEY_LINE = "Say what you're calling about."
STILL = 1.0  # the still first second: the sp-hook_motion test's arm a
LIGHTS = {"lamp": [[0, "on"]], "tv": [[0, "on", "blue"]]}
BOOKING = ("Party", "To", "Horse", "Human")  # the clipboard's rows, filled by the book: events, in this order
BOARD = dict(at=(414, 826), scale=1.2)
PHONE = dict(at=(196, 838), scale=0.9)
PHONE_SCREEN = toon_everyday.Screen(0.0, "code", "ON THE LINE", "2:47:13")  # he has been at this a while
HORSE = dict(at=(462, 486), scale=0.92)
ROPE = [(292, 790), (346, 716), (404, 712), (462, 600)]  # from the man's paw to the halter's ring
FIGURES = {"hamster": (1.42, 6.0)}  # he is small: close on his face
PUNCH = ((3, 1.1), (9, 1.22))  # (line, scale): the camera steps in on the shouts
PIVOT = (980.0, 1420.0)  # both signature marks stay in frame
PUSH = (1.0, 1.42, 1.6, (1030.0, 1000.0))  # the last push onto the horse: from, to, over, pivot
END = 26.2
DING_DONG = ((659.0, 659.0, 0.34), (523.0, 523.0, 0.7))

LINES = (
    Line("menu", "In a few words, why are you calling?"),
    Line("gus", "Representative."),
    Line("menu", "I heard: reservation. For how many?"),
    Line("gus", "REPRESENTATIVE."),
    Line("menu", "Party of seven. Lovely."),
    Line("gus", "No! Agent!"),
    Line("menu", "Travel agent. Booking Lisbon."),
    Line("gus", "Stop!"),
    Line("menu", "Horse. One horse."),
    Line("gus", "Human! I want a human!"),
    Line("menu", "Adding a human to your horse."),
    Line("menu", "Did that solve your problem today?"),
    Line("gus", "No."),
    Line("menu", "Great!"),
    Line("man", "Hi. Reservation?"),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "hamster", "", "narrow", "grimace", "crossed"),  # the still: furious, the premise, nobody speaking
    first(STILL, "hamster", 0, "In a few words,", "narrow", "flat", "crossed"),
    part(1.9, "hamster", 0, 4, "why are you calling?", "narrow", "flat", "crossed"),
    say(3.0, "hamster", 1, "narrow", "frown", "lean"),
    first(4.0, "hamster", 2, "I heard: reservation.", "wide", "flat", "lean"),  # the first laugh
    part(5.4, "hamster", 2, 3, "For how many?", "wide", "flat", "lean"),
    say(6.6, "hamster", 3, "shock", "scream", "lean"),
    say(7.8, "hamster", 4, "shock", "drop", "lean", "book:7"),
    say(9.4, "hamster", 5, "narrow", "scream", "face2"),
    first(10.4, "hamster", 6, "Travel agent.", "wince", "grimace", "face2"),
    part(11.4, "hamster", 6, 2, "Booking Lisbon.", "wince", "grimace", "face2", "book:Lisbon"),
    say(12.6, "hamster", 7, "shock", "scream", "lean"),
    say(13.2, "hamster", 8, "shock", "drop", "lean"),
    sketch.Beat(
        13.9, "hamster", LINES[8].text, "shock", "drop", "lean", 8, 1, "book:1"
    ),  # one caption: too short apart
    say(15.2, "hamster", 9, "narrow", "scream", "lean", wear=("sweat",)),
    say(17.0, "hamster", 10, "wide", "drop", "face", "book:1", wear=("sweat",)),
    hold(19.0, "hamster", "", "wide", "none", "face", wear=("sweat",)),  # the hold: he reads the clipboard
    say(19.8, "hamster", 11, "down", "flat", "sigh"),
    say(21.6, "hamster", 12, "half", "flat", "sigh"),
    say(22.2, "hamster", 13, "half", "flat", "sigh", "stamp"),
    hold(23.0, "hamster", "", "side", "none", "sigh", "bell"),  # the doorbell; he looks
    say(24.2, "bear", 14, "half", "grin", "desk"),
    hold(25.4, "bear", "", "half", "smirk", "desk", "hangup"),  # stop on the horse
)
SKETCH = Sketch(SLUG, TITLE, (GUS, MENU, MAN), LINES, BEATS, END)


def fields(beats) -> list[toon_everyday.Field]:
    """The clipboard's rows, each written on its ``book:`` event."""
    booked = sketch.events(beats, "book")
    return [toon_everyday.Field(label, value, at) for label, (at, value) in zip(BOOKING, booked, strict=True)]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the first beat is the still (silent,
    uncaptioned, held at least :data:`STILL`); every row of the booking is written once, on Gus's shot; the stamp
    lands once, after the last row; the bell rings once, after every line of Gus's, before the man speaks; the sting
    comes after the last line; no other events."""
    sketch.check(sk)
    opening, second = sk.beats[0], sk.beats[1]
    if opening.spoken or opening.caption or second.start < STILL:
        raise sketch.SketchError(f"the sketch opens on a still of Gus: silent, uncaptioned, held {STILL} s")
    if len(sketch.events(sk.beats, "book")) != len(BOOKING):
        raise sketch.SketchError(f"the booking has {len(BOOKING)} rows, one book: event each")
    scripting.exactly_once(sk.beats, "stamp", "the booking is stamped once")
    scripting.exactly_once(sk.beats, "bell", "the doorbell rings once")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays exactly once")
    bell = sketch.events(sk.beats, "bell")[0][0]
    if bell < sketch.events(sk.beats, "stamp")[0][0]:
        raise sketch.SketchError("the doorbell rings after the stamp")
    if sketch.events(sk.beats, "hangup")[0][0] < max(b.start for b in sk.beats if b.spoken):
        raise sketch.SketchError("the sting comes after the last line")
    scripting.only_events(sk.beats, {"book", "stamp", "bell", "hangup"})


def no_desk(cv, parent) -> None:
    """Each shot lays its own surface: see :func:`dress`."""


def dress(shot) -> None:
    """Gus's shot: the living room at night, a table with the phone on speaker and the clipboard filling in, the
    premise over the first seconds. The man's: the open front door, the horse in it on a rope, a shoe bench in front."""
    cv, app = shot.cv, shot.app
    if app.who == "hamster":
        toon_rooms.dress(shot, "lounge", LIGHTS, blink_from=STILL)
        toon_house.ledge(cv, shot.front, "oak")
        stamp_at = sketch.events(shot.beats, "stamp")[0][0]
        toon_everyday.phone(cv, shot.front, [PHONE_SCREEN], measure=shot.measure, **PHONE)
        toon_everyday.clipboard(
            cv, shot.front, "YOUR BOOKING", fields(shot.beats), measure=shot.measure,
            stamp=(stamp_at, "BOOKED", "deep"), **BOARD,
        )  # fmt: skip
        toon_house.key_line(cv, shot.front, KEY_LINE, 0.0, shot.beats[4].start, measure=shot.measure)
    else:
        toon_house.hallway(cv, shot.back, door="open")
        toon_house.horse(cv, shot.back, start=app.start, end=app.end, **HORSE)
        toon_house.ledge(cv, shot.front, "white")
        toon_house.rope(cv, shot.front, ROPE)


def lens(shot, setup) -> None:
    """The camera: still through the first seconds, stepping in on Gus's shouts; a slow push onto the horse at the
    end, keeping both signature marks in frame."""
    app = shot.app
    if app.who == "hamster":
        camera.anchor(setup, *PIVOT, place=True)
        starts = {b.line: b.start for b in reversed(shot.beats) if b.line is not None}
        camera.zoom_holds(shot.cv, setup, [(0.0, 1.0)] + [(starts[line], s) for line, s in PUNCH])
    else:
        a, b, over, (x, y) = PUSH
        camera.anchor(setup, x, y, place=True)
        sting = sketch.events(shot.beats, "hangup")[0][0]
        camera.push_in(shot.cv, setup, scale=[(0.0, a), (sting, a), (sting + over, b)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The doorbell on ``bell`` and a horse's breath after the man's line, on ``hangup``."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    bell = synth.write_tones(audio / "bell.wav", [at for at, _ in sketch.events(beats, "bell")], end, DING_DONG)
    breath = synth.write_whoosh(audio / "breath.wav", [at + 0.5 for at, _ in sketch.events(beats, "hangup")], end)
    return [sketch.effect("bell", 0.0, -6.0, root, bell), sketch.effect("breath", 0.0, -8.0, root, breath)]

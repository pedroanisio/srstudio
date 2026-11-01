"""Arrive Early — the sketch as data: a clinic charges you for ten minutes late and sees you two hours late for free,
so the patient takes out a card reader. Then the framing swaps: she is behind the glass, the receptionist waits in her
chair with a clipboard, and when the doctor comes out, late, she bills him too.

Three voices (ElevenLabs premade Matilda as the patient, Will as the receptionist, Charlie as the doctor). It opens on
her first line over a moving second hand's room (the ``sp-hook_motion`` test's arm B). ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress` draws each shot
and :func:`sounds` the reader.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    foley,
    scripting,
    sketch,
    toon,
    toon_dinner,
    toon_everyday,
    toon_house,
    toon_inserts,
    toon_props,
    toon_rooms,
    toon_world,
)
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3110
SLUG = "arrive-early"
TITLE = "Arrive Early — The Waiting Room (Toon)"
DESCRIPTION = (
    "A Toon sketch at a clinic: a patient kept waiting bills the receptionist by the same policy, swaps places with "
    "him and charges the doctor for being late."
)
ACCESSIBILITY = (
    "A cartoon frog in a waiting room tells a cartoon raccoon behind a glass that her nine o'clock appointment is "
    "running late, and that she was charged twenty dollars for being ten minutes late. She sets a card reader on the "
    "counter and charges him two hundred. She gives him a clipboard and tells him to take a seat. Then she is behind "
    "the glass and he waits on a chair. A cartoon dog, the doctor, comes out and she charges him twenty dollars."
)
NARRATION = (
    "Voiced with ElevenLabs premade voices Matilda (the patient), Will (the receptionist) and Charlie (the doctor); "
    "synthesized effects."
)
NOTE = "ElevenLabs premade voices Matilda, Will and Charlie at their natural pace; no reference-voice cloning."
FROG = Speaker(
    "frog",
    Voice(role="frog", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.2),
    "frog",
)
RACCOON = Speaker(
    "raccoon",
    Voice(role="raccoon", id="bIHbv24MWmeRgasZH58o", name="Will"),
    VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.15),
    "raccoon",
)
DOG = Speaker(
    "dog",
    Voice(role="dog", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.2),
    "dog",
)
TINTS = {"frog": "#d6f0c8", "raccoon": "#dfe3e8", "dog": "#ffe3c2", "hamster": "#ffffff"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

WIDE = "hamster"  # never seen: the name of the shot the dress draws whole
FIGURES: dict[str, tuple[float, float]] = {"frog": (1.0, 0.0), "raccoon": (1.0, 0.0), "dog": (1.0, 0.0)}
READER_AT = (440.0, 838.0)
READER_SCALE = 1.7  # large enough that the bill reads
FORM = {"at": (420.0, 826.0), "scale": 1.0}
CHAIR = ((130.0, 806.0), 0.72)  # him, small, on the waiting room's chair
LIGHTS = {"tubes": ((0, "on"),), "board": ((0, "on", "red"),)}
TIME = ((0.0, "10:40"), (2.0, "10:41"), (4.0, "10:42"))  # it does not stop for anyone
BIT = 0.25  # seconds the reader or the form takes to land
BEEP = foley.Burst(0.14, 200.0, attack=0.001, decay=0.12, tone_hz=2100.0, tone_end_hz=2100.0, tone=1.0)
END = 28.18

LINES = (
    Line("frog", "My appointment was at nine."),
    Line("raccoon", "Doctor is running behind."),
    Line("frog", "Last time I was 10 minutes late, you charged me $20."),
    Line("raccoon", "That's our policy."),
    Line("frog", "Then that's two hundred."),
    Line("raccoon", "Excuse me?"),
    Line("frog", "Cash or card?"),
    Line("frog", "And fill this in. Both sides."),
    Line("raccoon", "We already have your..."),
    Line("frog", "Take a seat. Someone will be with you shortly."),
    Line("dog", "Who's next?"),
    Line(  # accepted by arc4d3, Slack 1793499862.755999: the recognizer drops the dollars
        "frog", "You're late. That's $20.", heard=("You're late. That's 20",)
    ),
)

script = scripting.Script(LINES)
hold, say, first, part = script.hold, script.say, script.first, script.part

BEATS = (
    say(0.0, "frog", 0, "half", "flat", "desk"),
    say(1.5, "raccoon", 1, "half", "flat", "desk"),
    first(3.03, "frog", 2, "Last time I was 10 minutes late,", "narrow", "flat", "desk"),
    part(4.93, "frog", 2, 7, "you charged me $20.", "narrow", "flat", "desk"),
    say(8.1, "raccoon", 3, "half", "smirk", "desk"),
    hold(9.53, "frog", "", "narrow", "flat", "desk"),  # she looks at him for a while
    hold(10.53, "frog", "", "narrow", "smirk", "desk", "reader"),
    say(11.13, "frog", 4, "narrow", "smirk", "desk"),
    say(12.46, "raccoon", 5, "wide", "o", "desk"),
    say(13.34, "frog", 6, "half", "flat", "desk"),
    hold(14.57, "frog", "", "half", "flat", "desk", "form"),
    say(15.07, "frog", 7, "half", "flat", "desk"),
    say(17.13, "raccoon", 8, "shock", "open", "desk"),
    first(18.39, "frog", 9, "Take a seat.", "half", "smirk", "desk"),
    part(19.39, "frog", 9, 3, "Someone will be with you shortly.", "half", "smirk", "desk"),
    hold(21.97, WIDE, "", "down", "flat", "desk", "flip"),  # smash cut: the room has changed hands
    say(23.77, "dog", 10, "wide", "grin", "desk"),
    hold(24.49, "frog", "", "down", "flat", "desk"),  # she does not look up
    say(25.49, "frog", 11, "half", "smirk", "desk", "turn"),
)
SKETCH = Sketch(SLUG, TITLE, (FROG, RACCOON, DOG), LINES, BEATS, END, bare=(WIDE,))


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks within 0.3 s, and the reader, the form, the swap and the second bill come once
    each and in order, the swap on the shot drawn whole."""
    sketch.check(sk)
    if sk.beats[0].line != 0 or sk.beats[0].start > 0.3:
        raise sketch.SketchError("the sketch's first line is spoken within 0.3 s")
    order = ("reader", "form", "flip", "turn")
    for event in order:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    times = [sketch.events(sk.beats, event)[0][0] for event in order]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {order}")
    scripting.only_events(sk.beats, set(order))
    if next(b for b in sk.beats if b.event == "flip").who != WIDE:
        raise sketch.SketchError("the swap is the shot drawn whole")


def waiting_room(shot) -> None:
    """The patients' side: the hallway and a chair, and the counter's near edge."""
    toon_house.hallway(shot.cv, shot.back)
    toon_house.ledge(shot.cv, shot.front)


def staff_side(shot) -> None:
    """Behind the glass: the counter room, the clock, the ledge and the glass over whoever is sitting there."""
    toon_rooms.dress(shot, "counter", LIGHTS)
    toon_props.clock(shot.cv, shot.back, TIME, at=(322.0, 392.0), r=40.0)
    toon_inserts.reception_glass(shot.cv, shot.front)
    toon_house.ledge(shot.cv, shot.front)


def reader(shot, screens, landed: float) -> None:
    """The card reader, thrown down at ``landed``: it drops the last of the way onto the ledge."""
    cv = shot.cv
    drop = cv.group(shot.front, cv.uid("g"), start=landed, x=0.0, y=0.0)
    cv.keys(drop, "y", [(landed, -toon.fh(60)), (landed + BIT, 0.0)], kind="cubic-out", local=False)

    def draw(g) -> None:
        toon_dinner.card_reader(cv, g, screens, at=READER_AT, id=cv.uid("reader"))

    toon_world.placed(cv, drop, READER_AT, READER_SCALE, draw, pivot=READER_AT)


def form(shot, landed: float, slides: bool = True, at=None, scale: float | None = None) -> None:
    """The clipboard she slides across, from the frame's edge onto the ledge, or already lying there."""
    cv = shot.cv
    fields = [toon_everyday.Field("Side", "1 of 2", 0.0)]
    place = {"at": at or FORM["at"], "scale": scale or FORM["scale"]}
    slide = cv.group(shot.front, cv.uid("g"), start=landed, x=0.0, y=0.0)
    if slides:
        cv.keys(slide, "x", [(landed, toon.fh(400)), (landed + BIT * 1.6, 0.0)], kind="cubic-out", local=False)
    toon_everyday.clipboard(cv, slide, "NEW PATIENT", fields, measure=shot.measure, id=cv.uid("board"), **place)


def flipped(shot) -> None:
    """The swap: the waiting room, and him small on its chair with the clipboard before him, filling in both sides."""
    cv, app = shot.cv, shot.app
    toon_house.hallway(cv, shot.back)
    toon_world.hall_chair(cv, shot.back)
    poses = toon.parse_poses([{"start": 0.0, "eyes": "down", "mouth": "flat", "arms": "desk"}], "him on the chair")
    at, scale = CHAIR

    def draw(g) -> None:
        sketch.drawer("raccoon", shot.versions)(cv, g, poses, app.end, (), enter=app.start)

    toon_world.placed(cv, shot.front, at, scale, draw)
    toon_house.ledge(cv, shot.front)
    form(shot, app.start, slides=False, at=(350.0, 826.0), scale=0.9)


def dress(shot) -> None:
    """Before the swap she stands on the patients' side and he sits behind the glass; after it, the other way."""
    app = shot.app
    swap = sketch.events(shot.beats, "flip")[0][0]
    if app.who == WIDE:
        flipped(shot)
    elif app.who == "raccoon" or (app.who == "frog" and app.start >= swap):
        staff_side(shot)
    elif app.who == "dog":
        toon_house.hallway(shot.cv, shot.back)
        toon_house.ledge(shot.cv, shot.front)
    else:
        waiting_room(shot)
    bill = sketch.events(shot.beats, "reader")[0][0]
    if app.who == "frog":
        turn = sketch.events(shot.beats, "turn")[0][0]
        if app.start < swap and app.end > bill:
            reader(shot, [(0.0, "$200.00", "bad")], bill)
        if app.start >= swap:
            reader(shot, [(0.0, "$20.00", "bad")], turn if app.start >= turn else app.start)
    laid = sketch.events(shot.beats, "form")[0][0]
    if app.who == "frog" and app.start < swap and app.end > laid:
        form(shot, laid)


def sounds(beats, end) -> tuple[Sound, ...]:
    """The reader's beep when it lands and at the very end, the clipboard's slide, and the hit of the smash cut."""
    reader_at = sketch.events(beats, "reader")[0][0]
    turn = sketch.events(beats, "turn")[0][0]
    laid = sketch.events(beats, "form")[0][0]
    flip = sketch.events(beats, "flip")[0][0]
    return (
        Sound("thud", foley.THUD, (reader_at,), -6.0),
        Sound("beep", BEEP, (reader_at + 0.25, end - 0.9), -6.0),
        Sound("slide", foley.SCRAPE, (laid,), -6.0),
        Sound("cut", foley.KNOCK, (flip,), -4.0),
        Sound("turn", foley.SCRAPE, (turn,), -12.0),
    )

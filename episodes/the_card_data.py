"""The Card — the sketch as data: there is a leaving card in the office kitchen. Fern signs it without asking whose
it is: good luck out there. Rex wrote: you'll be missed. Then she reads the front. It says Fern. She is not
leaving. Has she checked her calendar? There's a meeting with HR. Rex has advice: bring it with you.

Two voices (ElevenLabs premade Matilda as Fern, Charlie as Rex), one shot per speaker: Fern in the office kitchen,
the note on the fridge asking everyone to sign the card, until the card's front is cut in full frame (a ``note:``
event); Rex in the meeting room, setting up the farewell drinks on the board behind him. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress` draws each
shot's set and props (``_toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import sketch, toon_props, toon_sets
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1314
SLUG = "the-card"
TITLE = "The Card — Fern and Rex (Toon)"
DESCRIPTION = (
    "A Toon sketch in the office kitchen: Fern signs the leaving card without asking whose it is. Good luck out "
    "there. Then she reads the front: it says Fern. She is not leaving. There's a meeting with HR. Bring it with you."
)
ACCESSIBILITY = (
    "A cartoon frog in an office kitchen and a cartoon dog in a meeting room. The note on the fridge says SIGN THE "
    "CARD, then the card fills the frame: FAREWELL FERN!. The board behind the dog says FAREWELL DRINKS. Their "
    "lines appear in tinted pills and their mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda (Fern) and Charlie (Rex); synthesised keyboard and sting."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
FERN = Speaker(
    "fern",
    Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.40),
    "frog",
)
REX = Speaker(
    "rex",
    Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.45),
    "dog",
)
TINTS = {"fern": "#d5f0c8", "rex": "#f6dcb8"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
FIRST_NOTE = "SIGN THE CARD"
BOARD = "FAREWELL DRINKS 5PM"
BOARD_SIZE = 56
END = 30.0

LINES = (
    Line("fern", "Rex, whose card is this?"),
    Line("rex", "Someone's leaving. Just sign it."),
    Line("fern", "Who's leaving?"),
    Line("rex", "No idea. I wrote, you'll be missed."),
    Line("fern", "I'm writing, good luck out there."),
    Line("rex", "Nice. Warm, but distant."),
    Line("fern", "Rex. It says Fern."),
    Line("rex", "Huh. Congratulations."),
    Line("fern", "I'm not leaving."),
    Line("rex", "Did you check your calendar?"),
    Line("fern", "There's a meeting with HR."),
    Line("rex", "Bring it with you."),
)


def say(start: float, who: str, line: int, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, LINES[line].text, eyes, mouth, arms, line, 0, event)


def hold(start: float, who: str, caption: str, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, caption, eyes, mouth, arms, None, None, event)


BEATS = (
    say(0.0, "frog", 0, "half", "flat", "desk"),  # the hook: the question, the note already on the fridge
    say(2.0, "dog", 1, "half", "smirk", "lean"),
    say(3.8, "frog", 2, "narrow", "flat", "crossed"),
    say(5.0, "dog", 3, "closed", "grin", "lean"),
    say(7.2, "frog", 4, "half", "grin", "type"),  # she signs it
    say(9.2, "dog", 5, "side", "smirk", "crossed"),
    hold(10.8, "frog", "", "down", "flat", "desk"),  # she turns the card over
    hold(11.6, "frog", "", "down", "none", "desk", "note:FAREWELL FERN!"),  # the insert: the front of the card
    say(13.0, "frog", 6, "shock", "o", "face2"),
    say(14.4, "dog", 7, "half", "flat", "lean"),
    say(15.8, "frog", 8, "narrow", "flat", "crossed"),
    say(17.2, "dog", 9, "side", "flat", "crossed"),
    hold(18.8, "frog", LINES[9].text, "down", "flat", "type"),  # she looks
    say(19.8, "frog", 10, "shock", "drop", "face"),
    hold(21.4, "dog", LINES[10].text, "half", "flat", "crossed"),  # the hold before the punchline
    hold(22.6, "dog", "", "closed", "none", "crossed"),
    say(23.8, "dog", 11, "half", "smirk", "lean"),  # the punchline
    hold(25.4, "frog", "", "closed", "none", "face", "hangup"),  # the sting
    hold(27.0, "frog", "", "down", "flat", "sigh"),  # the button: she picks it up
)
SKETCH = Sketch(SLUG, TITLE, (FERN, REX), LINES, BEATS, END)


def notes_by_time(beats) -> list[tuple[float, str]]:
    """The fridge note through the sketch: the first note from 0, then every ``note:`` event."""
    return [(0.0, FIRST_NOTE)] + sketch.events(beats, "note")


def note_spans(beats, start: float, end: float) -> list[tuple[float, float, str]]:
    """The notes on the fridge between ``start`` and ``end``, each until the next one is written."""
    notes = notes_by_time(beats)
    ends = [at for at, _ in notes[1:]] + [end]
    return [
        (max(a, start), min(b, end), text) for (a, text), b in zip(notes, ends, strict=True) if a < end and b > start
    ]


def inserts(beats, start: float, end: float) -> list[tuple[float, float, str]]:
    """The close-ups of the note in a shot: from each ``note:`` beat to the next beat (or the shot's end)."""
    starts = [b.start for b in beats] + [end]
    return [
        (at, min(end, next(t for t in starts if t > at)), text)
        for at, text in sketch.events(beats, "note")
        if start <= at < end
    ]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: every note fits the fridge and is
    written in Fern's shot (the fridge is behind her), each one new; exactly one hangup; no other events."""
    sketch.check(sk)
    notes = notes_by_time(sk.beats)
    for at, text in notes:
        if len(text) > toon_sets.NOTE_MAX:
            raise sketch.SketchError(f"the note {text!r} at {at} s does not fit the fridge ({toon_sets.NOTE_MAX})")
        if at > 0 and next(b for b in sk.beats if b.start == at).who != "frog":
            raise sketch.SketchError(f"the note at {at} s changes off screen: the fridge is in Fern's shot")
    texts = [text for _, text in notes]
    if len(set(texts)) != len(texts):
        raise sketch.SketchError(f"a note is written twice: {texts}")
    if len(sketch.events(sk.beats, "hangup")) != 1:
        raise sketch.SketchError("the sting plays exactly once")
    unknown = {b.event.split(":")[0] for b in sk.beats if b.event} - {"note", "hangup"}
    if unknown:
        raise sketch.SketchError(f"unknown events {sorted(unknown)}")


def dress(shot) -> None:
    """Fern's shots: the office kitchen with the note on the fridge, swapped when the card is turned over, and the
    card's front cut in full frame for its beat; Rex's: the meeting room with the farewell drinks on the board."""
    cv, app = shot.cv, shot.app
    if app.who == "frog":
        for a, b, text in note_spans(shot.beats, app.start, app.end):
            toon_sets.kitchen(cv, cv.group(shot.back, cv.uid("g"), start=a, end=b), note=text)
        for a, b, text in inserts(shot.beats, app.start, app.end):
            toon_sets.note_insert(cv, shot.front, text, a, b)
    else:
        toon_props.meeting(cv, shot.back)
        toon_props.board_text(cv, shot.back, BOARD, size=BOARD_SIZE)

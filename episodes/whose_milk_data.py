"""Whose Milk? — the sketch as data: Fern finds the milk in the office fridge labelled "Rex, 2019". It has
survived two reorgs, more than Dave did. Then it moved. It is not milk anymore: it is yogurt, and it got promoted.
Fern has been here six years. Rex has a career tip.

Two voices (ElevenLabs premade Matilda as Fern, Charlie as Rex), one shot per speaker, both in the office kitchen:
Fern's shots carry the note on the fridge, which changes (``note:`` events, each cut in full frame) until it asks
whose yogurt it is; Rex's coffee brews behind him the whole time. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress` draws each
shot's set and props (``_toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import sketch, toon_sets
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1042
SLUG = "whose-milk"
TITLE = "Whose Milk? — Fern and Rex (Toon)"
DESCRIPTION = (
    "A Toon sketch in the office kitchen: the milk in the fridge says Rex, 2019. It has survived two reorgs. It "
    "moved. It is yogurt now, and it got promoted. Fern has been here six years."
)
ACCESSIBILITY = (
    "A cartoon frog and a cartoon dog talk in an office kitchen with a fridge, tiled wall and a coffee machine "
    "that drips behind the dog. The note on the fridge changes between the frog's shots, from Whose milk? to It "
    "moved, then Whose yogurt?. Their lines appear in tinted pills and their mouths move with their words."
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
FIRST_NOTE = "WHOSE MILK?"
END = 31.0

LINES = (
    Line("fern", "Rex. Whose milk is this?"),
    Line("rex", "Mine. It's labeled."),
    Line("fern", "It says Rex, 2019."),
    Line("rex", "Vintage."),
    Line("fern", "It has survived two reorgs."),
    Line("rex", "More than Dave did."),
    Line("fern", "Rex. It moved."),
    Line("rex", "Yeah. It's not milk anymore."),
    Line("rex", "It's yogurt. It got promoted."),
    Line("fern", "I've been here six years."),
    Line("rex", "Have you tried curdling?"),
)


def say(start: float, who: str, line: int, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, LINES[line].text, eyes, mouth, arms, line, 0, event)


def hold(start: float, who: str, caption: str, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, caption, eyes, mouth, arms, None, None, event)


BEATS = (
    say(0.0, "frog", 0, "narrow", "flat", "crossed"),  # the hook: the question, the note already on the fridge
    say(2.0, "dog", 1, "half", "smirk", "lean"),
    say(3.6, "frog", 2, "narrow", "flat", "crossed"),
    say(5.8, "dog", 3, "closed", "grin", "lean"),
    say(7.0, "frog", 4, "half", "flat", "sigh"),
    say(9.0, "dog", 5, "side", "smirk", "crossed"),
    hold(10.4, "frog", "", "side", "flat", "crossed"),  # she glances at the fridge
    hold(11.0, "frog", "", "side", "none", "crossed", "note:IT MOVED."),  # the insert: the note has moved
    say(12.4, "frog", 6, "shock", "o", "face2"),
    say(13.4, "dog", 7, "half", "flat", "lean"),
    hold(15.4, "dog", LINES[7].text, "closed", "none", "desk"),  # the hold: he lets it land
    say(16.8, "dog", 8, "wide", "grin", "lean"),
    hold(18.8, "frog", LINES[8].text, "shock", "drop", "desk"),
    say(20.2, "frog", 9, "down", "flat", "sigh"),
    hold(22.0, "dog", LINES[9].text, "side", "flat", "crossed"),  # the hold before the punchline
    hold(23.0, "dog", LINES[9].text, "half", "none", "crossed"),
    say(24.2, "dog", 10, "half", "smirk", "lean"),  # the punchline
    hold(26.0, "frog", "", "closed", "none", "face", "hangup"),  # the sting
    hold(27.6, "frog", "", "narrow", "flat", "crossed", "note:WHOSE YOGURT?"),  # the button: the note follows it
)
SKETCH = Sketch(SLUG, TITLE, (FERN, REX), LINES, BEATS, END)


def notes_by_time(beats) -> list[tuple[float, str]]:
    """The fridge note through the sketch: the first note from 0, then every ``note:`` event."""
    return [(0.0, FIRST_NOTE)] + sketch.events(beats, "note")


def note_at(beats, at: float) -> str:
    """The note on the fridge at ``at``: the last one written at or before it."""
    return [text for start, text in notes_by_time(beats) if start <= at][-1]


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
    out = []
    for at, text in sketch.events(beats, "note"):
        if start <= at < end:
            out.append((at, min(end, next(t for t in starts if t > at)), text))
    return out


def dress(shot) -> None:
    """Both shots are the office kitchen. Fern's carries the fridge note, swapped when a new one is written (the
    kitchen is drawn once per note, each copy shown until the next), and the new note cut in full frame
    (:func:`srstudio.toon_sets.note_insert`) for its beat; Rex's carries the coffee machine, brewing through the
    whole shot."""
    cv, app = shot.cv, shot.app
    if app.who == "frog":
        for a, b, text in note_spans(shot.beats, app.start, app.end):
            toon_sets.kitchen(cv, cv.group(shot.back, cv.uid("g"), start=a, end=b), note=text)
        for a, b, text in inserts(shot.beats, app.start, app.end):
            toon_sets.note_insert(cv, shot.front, text, a, b)
    else:
        toon_sets.kitchen(cv, shot.back)
        toon_sets.coffee_machine(cv, shot.back, brewing=[(app.start, app.end)])

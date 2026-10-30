"""On My Way — the sketch as data: Pip has been waiting at the restaurant for forty minutes. Gil is on the bus, five
minutes away. The map on her phone says he is at home; then that he is in the bathroom. The map is very good. Then
Gil checks his map: she just got there. The map is wrong. They settle on forty minutes, and he goes back to bed.

Two voices (ElevenLabs premade Alice as Pip, Chris as Gil), one shot per speaker: Pip in the bistro booth at a laid
table, the chip under the captions saying where Gil's dot is; Gil in his home office at night, his own chip saying
where hers is once he looks. The sketch opens on a still first second (the ``sp-hook_motion`` test's arm A): Pip,
arms crossed, under "Gil is at home", nothing captioned, nothing moving, until her first word. Gil's dot moves on
``map:`` events, her arrival shows in his shot on ``spy``, and the sting plays on ``hangup`` with a crash zoom onto
her. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the
props; :func:`dress` draws each shot's set, table or desk and chips, and :func:`push` its camera
(``toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

from srstudio import camera, scripting, sketch, toon, toon_dinner, toon_props, toon_sets
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import BADGE_SIZE
from srstudio.voice import Voice, VoiceSettings

SEED = 1303
SLUG = "on-my-way"
TITLE = "On My Way — Pip and Gil (Toon)"
DESCRIPTION = (
    "A Toon sketch over the phone: Pip has waited forty minutes; Gil is on the bus, five minutes away. The map says "
    "he is at home, then in the bathroom. Then his map says she just got there."
)
ACCESSIBILITY = (
    "A cartoon rabbit sits at a laid restaurant table in a bistro booth under a dark chip that reads Gil is at home. "
    "A cartoon frog answers from his desk in a home office at night. Her chip changes to Gil is in the bathroom. "
    "Then a chip in his room reads Pip arrived 1 min ago. At the end her chip reads Gil is back in bed and the camera "
    "snaps onto her. Their lines appear in tinted pills and their mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Alice (Pip) and Chris (Gil); synthesised sting."
NOTE = "ElevenLabs premade voices Alice and Chris at their natural pace; no reference-voice cloning."
PIP = Speaker(
    "pip",
    Voice(role="pip", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.50),
    "rabbit",
)
GIL = Speaker(
    "gil",
    Voice(role="gil", id="iP95p4xoKVk53GoZ742B", name="Chris"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35),
    "frog",
)
TINTS = {"pip": "#fbd3e0", "gil": "#d5f0c8"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
GIL_AT = ("Gil is at home", "Gil is in the bathroom", "Gil is back in bed")  # Pip's chip: where his dot is
PIP_AT = "Pip arrived 1 min ago"  # Gil's chip, once he looks
SPECIAL = ("SOUP", "OF THE\nDAY")
LAID = (("water", 130), ("empty", 450))  # her water and his empty glass, reference x on the cloth
ZOOM = (1.2, (1000.0, 1420.0))  # the crash zoom's scale and pivot (frame px): both signature marks stay in frame
END = 26.3

LINES = (
    Line("pip", "Where are you? I've been here forty minutes."),
    Line("gil", "On the bus! Five minutes away."),
    Line("pip", "The map says you're at home."),
    Line("gil", "The map is wrong."),
    Line("pip", "Now it says you're in the bathroom."),
    Line("gil", "The map is very good."),
    Line("gil", "Hang on. The map says you just got there."),
    Line("pip", "The map is wrong."),
    Line("gil", "So, forty minutes?"),
    Line("pip", "Forty minutes."),
)


SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold


BEATS = (
    hold(0.0, "rabbit", "", "narrow", "flat", "crossed"),  # the still: Pip, waiting, and where his dot is
    first(1.1, "rabbit", 0, "Where are you?", "narrow", "flat", "crossed"),
    part(2.2, "rabbit", 0, 3, "I've been here forty minutes.", "narrow", "flat", "crossed"),
    say(3.9, "frog", 1, "wide", "grin", "lean"),
    say(5.9, "rabbit", 2, "half", "flat", "crossed"),
    say(7.8, "frog", 3, "side", "flat", "lean"),
    hold(9.0, "rabbit", "", "down", "flat", "crossed", "map:1"),  # the dot moves
    say(9.6, "rabbit", 4, "narrow", "o", "crossed"),
    hold(11.6, "frog", "", "wide", "flat", "desk"),  # caught: the hold before his answer
    say(13.1, "frog", 5, "closed", "smirk", "lean"),
    hold(14.5, "frog", "", "down", "flat", "desk", "spy"),  # he looks at his own map
    first(15.0, "frog", 6, "Hang on.", "wide", "flat", "desk"),
    part(15.8, "frog", 6, 2, "The map says you just got there.", "narrow", "smirk", "crossed"),
    hold(17.5, "rabbit", "", "wide", "flat", "crossed"),  # caught: the same hold, on her
    say(18.7, "rabbit", 7, "side", "flat", "face2"),  # the callback
    say(20.1, "frog", 8, "half", "smirk", "lean"),
    say(21.5, "rabbit", 9, "closed", "smirk", "crossed"),
    hold(22.9, "rabbit", "", "half", "grin", "desk", "map:2"),  # back to bed; she relaxes too
    hold(23.9, "rabbit", "", "closed", "grin", "desk", "hangup"),  # the sting and the snap
)
SKETCH = Sketch(SLUG, TITLE, (PIP, GIL), LINES, BEATS, END)


def gil_spans(beats, start: float, end: float) -> list[tuple[float, float, str]]:
    """Pip's chip between ``start`` and ``end``: where Gil's dot is, from "at home", moved on every ``map:``."""
    shown = scripting.changes(beats, "map", "0")
    return [(a, b, GIL_AT[int(arg)]) for a, b, arg in scripting.spans(shown, start, end)]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the first beat is the still (silent,
    uncaptioned, no event, held at least 1 s, on Pip); the dot moves through ``GIL_AT`` in order, each move in Pip's
    shot (her chip); Gil looks once, in his shot, before he says she just got there; exactly one hangup, after the
    last spoken line, on Pip; no other events."""
    sketch.check(sk)
    opening = sk.beats[0]
    if opening.spoken or opening.caption or opening.event or opening.who != "rabbit" or sk.beats[1].start < 1.0:
        raise sketch.SketchError("the sketch opens on a still of Pip: a silent, uncaptioned beat held at least 1 s")
    who_at = {b.start: b.who for b in sk.beats}
    moves = sketch.events(sk.beats, "map")
    if [arg for _, arg in moves] != [str(i) for i in range(1, len(GIL_AT))]:
        raise sketch.SketchError(f"the dot moves once to each of {GIL_AT[1:]}, in order")
    if any(who_at[at] != "rabbit" for at, _ in moves):
        raise sketch.SketchError("the dot moves on Pip's chip, in her shot")
    scripting.exactly_once(sk.beats, "spy", "Gil looks at his map exactly once")
    spy = sketch.events(sk.beats, "spy")[0][0]
    reveal = next(b.start for b in sk.beats if b.spoken and b.line == 6)
    if who_at[spy] != "frog" or spy >= reveal:
        raise sketch.SketchError("Gil looks at his map in his shot, before he says she just got there")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays exactly once")
    sting = sketch.events(sk.beats, "hangup")[0][0]
    if sting < max(b.start for b in sk.beats if b.spoken) or who_at[sting] != "rabbit":
        raise sketch.SketchError("the sting comes after the last line, on Pip")
    scripting.only_events(sk.beats, {"map", "spy", "hangup"})


def dress(shot) -> None:
    """Pip's shots: the bistro booth and her laid table, Gil's whereabouts on her chip. Gil's: the home office at
    night (still), his desk, and, from the moment he looks, her arrival on his chip."""
    cv, app = shot.cv, shot.app
    measure = partial(shot.measure, size=BADGE_SIZE)
    if app.who == "rabbit":
        toon_dinner.restaurant(cv, shot.back, special=SPECIAL)
        toon_dinner.table(cv, shot.front)
        toon_dinner.dishes(cv, shot.front, LAID, id=cv.uid("dish"))
        for a, b, text in gil_spans(shot.beats, app.start, app.end):
            toon_props.badge(cv, shot.front, text, a, b, measure, BADGE_SIZE)
    else:
        toon_sets.home(cv, shot.back)
        toon.desk(cv, shot.front)
        spy = sketch.events(shot.beats, "spy")[0][0]
        if spy < app.end:
            toon_props.badge(cv, shot.front, PIP_AT, max(spy, app.start), app.end, measure, BADGE_SIZE)


def no_desk(cv, parent) -> None:
    """The staging's desk: none, each shot lays its own (Pip's table, Gil's desk) in :func:`dress`."""


def push(shot, setup) -> None:
    """The camera: still everywhere but the last shot of Pip, which snaps in on the sting."""
    sting = sketch.events(shot.beats, "hangup")[0][0]
    if shot.app.start <= sting < shot.app.end:
        scale, (x, y) = ZOOM
        camera.anchor(setup, x, y, place=True)
        camera.crash_zoom(shot.cv, setup, sting, scale)

"""Book Report — the sketch as data: Kai's teacher asks why his book report is about a toilet. His dad Gary
defends it: Flush has a whole arc, season two is basically a whale novel with plungers. Kai got a D. Gary would
like to speak to the manager of that D. Priya is worried about him. Flush would understand.

Collage style (ADR 0026): a parent-teacher meeting in the classroom; two ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from _collage_sketch import TINTS, Staging, make_sketch, timed, voices_note
from srstudio import collage_sets
from srstudio.sketch import Line

SEED = 2602
SLUG = "book-report"
TITLE = "Book Report — Priya and Gary (Collage)"
NAMES = ("priya", "gary")
DESCRIPTION = (
    "A Collage sketch: a teacher asks why the book report is about a toilet. The dad defends the lore. The kid "
    "got a D; the dad wants to speak to the manager of that D."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a classroom with a chalkboard: a teacher in glasses holds up a card that says "
    "GRADE: D; a balding dad holds a card that says FLUSH: A LIFE. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Sarah and Chris at their natural pace; no reference-voice cloning."

LINES = (
    Line("priya", "Gary, why is Kai's book report about a toilet?"),
    Line("gary", "It's not a toilet. It's Flush. He has a whole arc."),
    Line("priya", "The assignment was a classic novel."),
    Line("gary", "Season two is basically Moby Dick. With plungers."),
    Line("priya", "He got a D."),
    Line("gary", "Then I'd like to speak to the manager of that D."),
    Line("priya", "Gary. I'm worried about you."),
    Line("gary", "Flush would understand."),
)
BEATS, END = timed(
    LINES,
    (
        (3.0, "priya", 0, "half", "flat", "hold"),  # the hook, the D already on her card
        (3.4, "gary", 1, "angry", "frown", "point"),
        (2.4, "priya", 2, "half", "flat", "hold"),
        (3.2, "gary", 3, "up", "smile", "shrug"),
        (1.6, "priya", 4, "open", "flat", "hold"),
        (2.8, "gary", 5, "angry", "grin", "fist"),
        (1.6, "priya", "", "half", "flat", "down"),  # the pause
        (2.4, "priya", 6, "sad", "frown", "down", "zoom"),
        (1.6, "gary", "", "wide", "o", "down"),
        (1.8, "gary", 7, "sad", "smug", "face", "sting"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """The grade on Priya's card; the essay's title on Gary's."""
    cv = shot.cv
    if shot.app.who == "priya":
        collage_sets.sign(cv, shot.back, "GRADE: D", 640, 530, 360, 150, size=66, color="#c1121f", tilt=4)
    else:
        collage_sets.sign(cv, shot.back, "FLUSH: A LIFE", 600, 530, 440, 150, size=58, fill="#ffe066", tilt=-4)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"priya": "classroom", "gary": "classroom"},
    dress=dress,
)

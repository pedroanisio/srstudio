"""Graded Date — the sketch as data: a first date with Priya, a teacher who grades everything. Gary hikes
("Where?" "Outside. Mostly."): C. He is reading a book about a toilet who learns to sing: D. Ignored, he does the
toilet's voice: F. Then, under the F, in red pen: SEE ME FRIDAY. "Is that a second date?" "Bring a real book."

Collage style (ADR 0026), cast cards of ADR 0036: Priya's red pen comes out mid-sentence, Gary performs Flush when
ignored. Two of the cast across one café table, Gary framed left and Priya right; the reel opens on a still first
second (the sp-hook_motion test's arm a): Priya's test paper, before anyone speaks. ElevenLabs premade voices,
lip-synced.
"""

from __future__ import annotations

from srstudio import collage_sets
from srstudio.collage_sketch import (
    TINTS,
    ZOOM_SCALE,
    CastDrawer,
    Staging,
    make_sketch,
    solo,
    stilled,
    timed,
    until,
    voices_note,
)
from srstudio.sketch import Line

SEED = 3911
SLUG = "graded-date"
TITLE = "Graded Date — Priya and Gary (Collage)"
NAMES = ("gary", "priya")
SET = "cafe"
DESCRIPTION = (
    "A Collage sketch: a first date with a teacher who grades every answer in red pen. Hiking gets a C. The book "
    "about a toilet gets a D. Then he does the toilet's voice."
)
ACCESSIBILITY = (
    "Paper cut-out characters across a café table: a woman in glasses with a ponytail holds up a paper reading DATE: "
    "GARY while red letter grades appear beside it, C, then D, then F, then SEE ME FRIDAY; a balding man in a green "
    "sweater answers her questions. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Chris and Sarah at their natural pace; no reference-voice cloning."
STILL = 1.0  # the still first second: the sp-hook_motion test's arm a
BITRATE = 5_800_000  # two passes: a master under 20 MB, and a still opening that stays still

# across the table: Gary on the left, Priya on the right, so the zoom on her keeps the café's shelf in frame
SHIFT = {"gary": -110.0, "priya": 150.0}
RED = "#c1121f"
PAPER_CARD = dict(x=120, y=575, w=330, h=110)  # the test paper, top left, clear of the shelf and the pill
GRADE = dict(x=470, y=565, w=150, h=150)  # the grade, beside it
FRIDAY = dict(x=400, y=735, w=290, h=120)  # the note under the grade, above Priya's head

LINES = (
    Line("gary", "What do I do for fun? Oh, I hike!"),
    Line("priya", "Where?"),
    Line("gary", "Outside. Mostly."),
    Line("priya", "What are you reading right now?"),
    Line("gary", "A book about a toilet who learns to sing."),
    Line("gary", "Flush, flush, yeah!"),
    Line("gary", "Wait. Is that a second date?"),
    Line("priya", "Bring a real book."),
)
BEATS, END = timed(
    LINES,
    (
        (1.2, "priya", "", "half", "smug", "hold"),  # the still: her test paper, his name on it
        (2.6, "gary", 0, "wide", "grin", "shrug"),
        (1.0, "priya", 1, "half", "flat", "hold"),
        (1.5, "gary", 2, "side", "grin", "shrug"),
        (1.2, "priya", "", "half", "frown", "point"),  # the red pen: C
        (2.0, "priya", 3, "open", "flat", "hold"),
        (2.8, "gary", 4, "open", "smile", "point"),  # proud of it
        (1.6, "priya", "", "half", "flat", "point"),  # D, and nothing said: the pause
        (1.6, "gary", 5, "wide", "grin", "shrug"),  # ignored, he does the toilet's voice
        (1.2, "priya", "", "angry", "flat", "point", "zoom"),  # F
        (1.6, "priya", "", "half", "smile", "hold", "reveal"),  # and under it: SEE ME FRIDAY
        (1.9, "gary", 6, "wide", "o", "point"),
        (1.8, "priya", 7, "half", "smug", "hold", "sting"),  # the button
        (0.0, "gary", "", "closed", "grin", "fist"),  # Gary, after: a second date
    ),
    tail=1.4,
)
GRADES = ((4, "C"), (7, "D"), (9, "F"))  # the beats the red pen marks, and what it writes
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def shifted(draw: CastDrawer) -> CastDrawer:
    """``draw`` with each character moved to its side of the table; returns the pivot of a zoom on its face that
    keeps the café's signature in frame."""

    def cast(cv, parent, app, mouths):
        dx = SHIFT[app.who]
        fx, fy = draw(cv, cv.group(parent, cv.uid("g"), x=dx), app, mouths)
        return collage_sets.zoom_pivot(SET, (fx + dx, fy), ZOOM_SCALE)

    return cast


def dress(shot) -> None:
    """Priya's test paper from the first frame; the grade the red pen gives after each answer, then the note."""
    cv, app = shot.cv, shot.app
    if app.who != "priya":
        return
    collage_sets.sign(cv, shot.back, "DATE: GARY", **PAPER_CARD, size=46, tilt=-3)
    starts = [shot.beats[i].start for i, _ in GRADES] + [shot.end]
    for (_, grade), a, b in zip(GRADES, starts, starts[1:], strict=False):
        if a < app.end and b > app.start:
            card = cv.group(shot.back, cv.uid("g"))
            collage_sets.sign(cv, card, grade, **GRADE, size=120, color=RED, tilt=6)
            cv.gate(card, [(max(a, app.start), min(b, app.end))])
    spans = until(shot.beats, "reveal", app, before=False)
    if spans:
        note = cv.group(shot.back, cv.uid("g"))
        collage_sets.sign(cv, note, "SEE ME FRIDAY", **FRIDAY, size=44, color=RED, tilt=-2)
        cv.gate(note, spans)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": SET, "priya": SET},
    dress=dress,
    cast=lambda beats, end: shifted(solo),
    still=STILL,
    bitrate=BITRATE,
    opening=shifted(stilled),
)

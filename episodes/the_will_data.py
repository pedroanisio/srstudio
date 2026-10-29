"""The Will — the sketch as data: Rosa reads her will to the family while she is still alive, to watch their faces.
Gary gets the house if he finishes one book that isn't about a toilet. Kai gets everything else if he can name one
thing that isn't a toilet. His headset beeps. He thinks. "Grandma?" "Close enough."

Collage style (ADR 0026): three of the cast in the boardroom, read like a lawyer's office; ElevenLabs premade
voices, lip-synced.
"""

from __future__ import annotations

from _collage_sketch import TINTS, Staging, make_sketch, timed, until, voices_note
from srstudio import collage_sets
from srstudio.sketch import Line

SEED = 2611
SLUG = "the-will"
TITLE = "The Will — Rosa, Gary and Kai (Collage)"
NAMES = ("rosa", "gary", "kai")
DESCRIPTION = (
    "A Collage sketch: Rosa reads her will early, so she can watch their faces. The house comes with a reading list. "
    "Everything else comes with one question."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a glass boardroom: an older woman with a cane and pearls holding a card reading "
    "LAST WILL, her balding son, and her grandson in a hoodie with a headset. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh, beeps and sting."
NOTE = "ElevenLabs premade voices Matilda, Chris and River at their natural pace; no reference-voice cloning."

LINES = (
    Line("rosa", "Why wait until I'm dead to read my will?"),
    Line("gary", "Mom, you're not dying."),
    Line("rosa", "No. I just want to watch your faces."),
    Line("rosa", "To my son Gary, the house."),
    Line("gary", "Mom."),
    Line("rosa", "If you finish one book that isn't about a toilet."),
    Line("gary", "Define finish."),
    Line("rosa", "To Kai, everything else. If he can name one thing that isn't a toilet."),
    Line("kai", "Grandma?"),
    Line("rosa", "Close enough."),
)
BEATS, END = timed(
    LINES,
    (
        (2.6, "rosa", 0, "half", "smug", "hold", "reveal"),
        (1.8, "gary", 1, "sad", "frown", "shrug"),
        (2.6, "rosa", 2, "open", "grin", "hold"),
        (2.2, "rosa", 3, "half", "smile", "point"),
        (1.4, "gary", 4, "up", "smile", "face"),
        (3.0, "rosa", 5, "half", "smug", "point", "zoom"),
        (1.6, "gary", 6, "side", "flat", "shrug"),
        (4.2, "rosa", 7, "open", "flat", "point"),
        (1.0, "kai", "", "wide", "o", "hold", "beep"),  # a new episode drops, right now
        (1.8, "kai", "", "up", "flat", "face"),  # the pause: he thinks, hard
        (1.4, "kai", 8, "open", "smile", "shrug"),
        (2.4, "rosa", 9, "closed", "smile", "hold", "sting"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """Rosa holds up the will from the first line."""
    cv = shot.cv
    if shot.app.who != "rosa":
        return
    spans = until(shot.beats, "reveal", shot.app, before=False)
    if spans:
        card = cv.group(shot.back, cv.uid("g"))
        collage_sets.sign(cv, card, "LAST WILL", 90, 540, 300, 120, size=56, fill="#fefae0", tilt=-4)
        cv.gate(card, spans)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"rosa": "boardroom", "gary": "boardroom", "kai": "boardroom"},
    dress=dress,
)

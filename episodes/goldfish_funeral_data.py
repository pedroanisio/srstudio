"""Goldfish Funeral — the sketch as data: Gary and Kai say goodbye to Bubbles over the toilet. It's what he would have
wanted. Then the toilet answers: Flush, from the show, is in every toilet. Gary asks for a selfie. Bubbles says hi.

Collage style (ADR 0026): the family bathroom (a new set); Flush steps out of the screen into the real toilet;
ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from srstudio import collage_sets
from srstudio.collage_sketch import TINTS, Staging, make_sketch, timed, until, voices_note
from srstudio.sketch import Line

SEED = 2613
SLUG = "goldfish-funeral"
TITLE = "Goldfish Funeral — Gary, Kai and Flush (Collage)"
NAMES = ("gary", "kai", "flush")
DESCRIPTION = (
    "A Collage sketch: a dad and his kid say goodbye to the goldfish over the toilet. The toilet has a few words too."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a tiled family bathroom: a balding dad, a kid in a hoodie holding a card reading "
    "R.I.P. BUBBLES, and a glossy cartoon toilet with a paper head. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Chris, River and Charlie at their natural pace; no reference-voice cloning."

LINES = (
    Line("gary", "Kai, do you want to say a few words for Bubbles?"),
    Line("kai", "He was a good fish."),
    Line("gary", "He was a great fish."),
    Line("kai", "Do we have to flush him?"),
    Line("gary", "It's what he would have wanted."),
    Line("flush", "I'll take it from here."),
    Line("kai", "Dad. The toilet is talking."),
    Line("gary", "Are you Flush? From the show?"),
    Line("flush", "I'm in every toilet, Gary."),
    Line("gary", "Can I get a selfie?"),
    Line("flush", "Bubbles says hi."),
)
BEATS, END = timed(
    LINES,
    (
        (2.8, "gary", 0, "sad", "frown", "hold"),
        (1.8, "kai", 1, "sad", "frown", "hold", "reveal"),
        (1.6, "gary", 2, "closed", "frown", "face"),
        (1.8, "kai", 3, "up", "flat", "hold"),
        (2.2, "gary", 4, "closed", "smile", "hold"),
        (1.6, "flush", 5, "half", "smug", "down", "zoom"),
        (2.0, "kai", 6, "wide", "o", "point"),
        (2.2, "gary", 7, "wide", "o", "face"),
        (2.0, "flush", 8, "half", "smug", "down"),
        (1.6, "gary", "", "wide", "flat", "hold"),  # the pause: he takes that in
        (1.6, "gary", 9, "up", "grin", "point"),
        (2.4, "flush", 10, "open", "grin", "down", "sting"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """Kai's card for Bubbles, from his first line."""
    cv = shot.cv
    if shot.app.who != "kai":
        return
    spans = until(shot.beats, "reveal", shot.app, before=False)
    if spans:
        card = cv.group(shot.back, cv.uid("g"))
        collage_sets.sign(cv, card, "R.I.P. BUBBLES", 330, 540, 340, 120, size=50, fill="#fff1e6", tilt=-3)
        cv.gate(card, spans)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": "bathroom", "kai": "bathroom", "flush": "bathroom"},
    dress=dress,
)

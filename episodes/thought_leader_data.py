"""Thought Leader — the sketch as data: Brent reads Jun his new post before it goes live: what a singing toilet
taught him about leadership. Always be flushing. Let go of what weighs you down. Jun wrote the show. Then he will
love lesson four: never credit the writer.

Collage style (ADR 0026): the café, two of the cast at a table; ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from _collage_sketch import TINTS, Staging, make_sketch, timed, voices_note
from srstudio import collage_sets
from srstudio.sketch import Line

SEED = 2614
SLUG = "thought-leader"
TITLE = "Thought Leader — Brent and Jun (Collage)"
NAMES = ("brent", "jun")
DESCRIPTION = (
    "A Collage sketch: a marketing chief reads his leadership post to the man who wrote the toilet show it is "
    "about. Lesson four is about the writer."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a brick café: a marketing chief in a blazer with cards for each lesson of his post, "
    "and a showrunner in a beanie. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Brian and Will at their natural pace; no reference-voice cloning."

LINES = (
    Line("brent", "Can I read you my post before it goes live?"),
    Line("jun", "Is it about synergy?"),
    Line("brent", "It's what a singing toilet taught me about leadership."),
    Line("brent", "Lesson one. Always be flushing."),
    Line("brent", "Lesson two. Let go of what weighs you down."),
    Line("brent", "Lesson three. Know when to go."),
    Line("jun", "I wrote that show."),
    Line("brent", "Then you'll love lesson four."),
    Line("brent", "Never credit the writer."),
    Line("jun", "I'm gonna like it anyway."),
)
BEATS, END = timed(
    LINES,
    (
        (2.4, "brent", 0, "open", "grin", "hold"),
        (1.6, "jun", 1, "half", "flat", "hold"),
        (3.0, "brent", 2, "up", "smile", "point"),
        (2.2, "brent", 3, "closed", "smug", "fist"),
        (2.8, "brent", 4, "up", "smile", "hold"),
        (2.0, "brent", 5, "half", "smug", "point"),
        (1.8, "jun", 6, "half", "frown", "point", "zoom"),  # the snap: the writer is in the room
        (1.6, "brent", "", "side", "flat", "hold"),  # the pause: he did not know that
        (1.8, "brent", 7, "open", "grin", "hold"),
        (2.0, "brent", 8, "half", "smug", "point"),  # held wide: the card is the joke
        (2.6, "jun", 9, "closed", "flat", "face", "sting"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)
CARDS = {
    3: "LESSON 1\nALWAYS BE FLUSHING",
    4: "LESSON 2\nLET IT GO",
    5: "LESSON 3\nKNOW WHEN TO GO",
    8: "LESSON 4\n???",
}
REVEALED = "LESSON 4\nNEVER CREDIT\nTHE WRITER"


def card_spans(beats, start: float, end: float) -> list[tuple[float, float, str]]:
    """Each lesson card from its line until the next lesson's line (the last until ``end``), clipped to the shot."""
    starts = [(b.start, CARDS[b.line]) for b in beats if b.line in CARDS]
    ends = [t for t, _ in starts[1:]] + [end]
    out = []
    for (a, text), b in zip(starts, ends, strict=True):
        if a < end and b > start:
            out.append((max(a, start), min(b, end), REVEALED if text.endswith("???") else text))
    return out


def dress(shot) -> None:
    """Brent's lesson cards, each from its line; lesson four is the one he means."""
    cv = shot.cv
    if shot.app.who != "brent":
        return
    for a, b, text in card_spans(shot.beats, shot.app.start, shot.app.end):
        card = cv.group(shot.back, cv.uid("g"))
        collage_sets.sign(cv, card, text, 300, 530, 380, 170, size=36, fill="#fefae0", tilt=-3)
        cv.gate(card, [(a, b)])


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"brent": "cafe", "jun": "cafe"},
    dress=dress,
)

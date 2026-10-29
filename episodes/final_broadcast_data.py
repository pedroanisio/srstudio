"""Final Broadcast — the sketch as data: after thirty years, Omar's last night at the desk. Jun found a younger
anchor: Flush. He tested great with young people. He can't read the news. Neither can the viewers. And
now, the weather.

Collage style (ADR 0026): the newsroom; Flush takes the anchor's desk; ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from srstudio import collage_sets
from srstudio.collage_sketch import TINTS, Staging, make_sketch, timed, until, voices_note
from srstudio.sketch import Line

SEED = 2615
SLUG = "final-broadcast"
TITLE = "Final Broadcast — Omar, Jun and Flush (Collage)"
NAMES = ("omar", "jun", "flush")
DESCRIPTION = (
    "A Collage sketch: after thirty years at the desk, the anchor meets his replacement. It tested well with "
    "younger viewers. It is a toilet."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a blue TV newsroom: a veteran anchor with a moustache, a producer in a beanie, and "
    "a glossy cartoon toilet with a paper head behind the anchor desk under a card reading NEW ANCHOR. Lines appear "
    "in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Daniel, Will and Charlie at their natural pace; no reference-voice cloning."

LINES = (
    Line("omar", "After thirty years, is this really my last broadcast?"),
    Line("jun", "Yes. We found a younger anchor."),
    Line("omar", "Who?"),
    Line("flush", "Good evening!"),
    Line("omar", "He's a toilet."),
    Line("jun", "He tested great with young people."),
    Line("omar", "He can't even read the news."),
    Line("jun", "Neither can our viewers."),
    Line("flush", "And now, the weather. It's wet."),
)
BEATS, END = timed(
    LINES,
    (
        (3.0, "omar", 0, "sad", "frown", "hold"),
        (2.2, "jun", 1, "half", "smile", "shrug"),
        (1.2, "omar", 2, "wide", "o", "down"),
        (1.6, "flush", 3, "open", "grin", "down", "reveal"),
        (1.6, "omar", 4, "half", "flat", "point"),
        (2.8, "jun", 5, "up", "smile", "hold"),
        (2.2, "omar", 6, "angry", "frown", "fist"),
        (1.8, "jun", 7, "half", "smug", "shrug", "zoom"),
        (1.6, "omar", "", "wide", "flat", "down"),  # the pause: thirty years
        (2.8, "flush", 8, "open", "grin", "down", "sting"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """The station's card over the new anchor, from his first words."""
    cv = shot.cv
    if shot.app.who != "flush":
        return
    spans = until(shot.beats, "reveal", shot.app, before=False)
    if spans:
        card = cv.group(shot.back, cv.uid("g"))
        collage_sets.sign(cv, card, "NEW ANCHOR", 600, 540, 340, 120, size=52, fill="#ffd166", tilt=3)
        cv.gate(card, spans)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"omar": "newsroom", "jun": "newsroom", "flush": "newsroom"},
    dress=dress,
)

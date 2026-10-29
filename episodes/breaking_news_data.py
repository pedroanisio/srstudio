"""Breaking News — the sketch as data: Omar asks if a singing toilet is rotting your child's brain. Experts say
yes. Experts also say it gets ten times the ratings. So tonight's weather is brought to you by Flush. Our ratings
just tripled. Back after this: flush flush.

Collage style (ADR 0026): the anchor in the newsroom, Flush on his stage; two ElevenLabs premade voices,
lip-synced.
"""

from __future__ import annotations

from _collage_sketch import TINTS, Staging, make_sketch, timed, until, voices_note
from srstudio import collage_sets
from srstudio.sketch import Line

SEED = 2606
SLUG = "breaking-news"
TITLE = "Breaking News — Omar and Flush (Collage)"
NAMES = ("omar", "flush")
DESCRIPTION = (
    "A Collage sketch: the news warns that a singing toilet is rotting kids' brains, then finds out how well it rates."
)
ACCESSIBILITY = (
    "A paper cut-out news anchor with a moustache in a blue newsroom under a card reading BREAKING, then RATINGS UP; "
    "a glossy cartoon toilet with a paper head sings the weather on a candy-coloured stage. Lines appear in tinted "
    "pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Daniel and Charlie at their natural pace; no reference-voice cloning."

LINES = (
    Line("omar", "Is a singing toilet rotting your child's brain?"),
    Line("omar", "Experts say yes."),
    Line("omar", "Experts also say it gets ten times our ratings."),
    Line("omar", "So tonight's weather is brought to you by Flush."),
    Line("flush", "Flush flush, rain tomorrow, yeah!"),
    Line("omar", "Our ratings just tripled."),
    Line("omar", "Back after this. Flush flush."),
)
BEATS, END = timed(
    LINES,
    (
        (3.0, "omar", 0, "angry", "frown", "point"),
        (1.6, "omar", 1, "half", "flat", "down"),
        (3.0, "omar", 2, "side", "o", "down"),
        (2.8, "omar", 3, "open", "smile", "hold", "zoom"),
        (2.8, "flush", 4, "open", "grin", "down"),
        (1.4, "omar", "", "half", "flat", "down", "reveal"),  # the pause, the new banner
        (2.4, "omar", 5, "wide", "grin", "fist"),
        (2.2, "omar", 6, "half", "smug", "point", "sting"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """The anchor's banner: BREAKING until the reveal, RATINGS UP from it."""
    cv = shot.cv
    if shot.app.who != "omar":
        return
    for text, fill, before in (("BREAKING", "#d62828", True), ("RATINGS UP", "#ffb703", False)):
        spans = until(shot.beats, "reveal", shot.app, before)
        if spans:
            card = cv.group(shot.back, cv.uid("g"))
            collage_sets.sign(cv, card, text, 600, 540, 420, 140, size=64, fill=fill, color="#ffffff", tilt=-3)
            cv.gate(card, spans)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"omar": "newsroom", "flush": "stage"},
    dress=dress,
)

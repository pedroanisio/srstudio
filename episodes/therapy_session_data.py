"""Therapy Session — the sketch as data: Dr. Feld asks Jun why he's here. He made a show about a toilet; it is his
most successful work. He went to film school for this. That's two hundred dollars. Can he pay in exposure? How
much exposure? Thirty billion views. Same time next week; bring the toilet.

Collage style (ADR 0026): therapist and patient in her office; two ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from srstudio import collage_sets
from srstudio.collage_sketch import TINTS, Staging, make_sketch, timed, until, voices_note
from srstudio.sketch import Line

SEED = 2607
SLUG = "therapy-session"
TITLE = "Therapy Session — Dr. Feld and Jun (Collage)"
NAMES = ("feld", "jun")
DESCRIPTION = (
    "A Collage sketch: the creator of a toilet show in therapy. He can't pay. He offers exposure. She asks how much."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a therapist's office with books and a diploma: an older therapist in glasses "
    "with a card reading $200, and a burnt-out showrunner in a beanie. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Alice and Will at their natural pace; no reference-voice cloning."

LINES = (
    Line("feld", "So. Why are you here today?"),
    Line("jun", "I made a show about a toilet. It's my most successful work."),
    Line("feld", "And how does that make you feel?"),
    Line("jun", "I went to film school. For this."),
    Line("feld", "That's two hundred dollars."),
    Line("jun", "Can I pay in exposure?"),
    Line("feld", "How much exposure?"),
    Line("jun", "Thirty billion views."),
    Line("feld", "Same time next week. Bring the toilet."),
)
BEATS, END = timed(
    LINES,
    (
        (2.2, "feld", 0, "open", "smile", "hold"),
        (3.6, "jun", 1, "sad", "flat", "shrug"),
        (2.2, "feld", 2, "half", "flat", "hold"),
        (2.4, "jun", 3, "sad", "frown", "face"),
        (2.0, "feld", 4, "open", "smile", "point", "reveal"),
        (1.8, "jun", 5, "up", "smile", "shrug"),
        (1.6, "feld", "", "half", "flat", "hold"),  # the pause
        (1.6, "feld", 6, "side", "smug", "hold", "zoom"),
        (1.8, "jun", 7, "open", "grin", "point"),
        (2.6, "feld", 8, "open", "grin", "fist", "sting"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """Her fee on a card, from the moment she names it."""
    cv = shot.cv
    if shot.app.who != "feld":
        return
    spans = until(shot.beats, "reveal", shot.app, before=False)
    if spans:
        card = cv.group(shot.back, cv.uid("g"))
        collage_sets.sign(cv, card, "$200", 730, 540, 260, 140, size=80, fill="#d8f3dc", tilt=5)
        cv.gate(card, spans)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"feld": "therapy", "jun": "therapy"},
    dress=dress,
)

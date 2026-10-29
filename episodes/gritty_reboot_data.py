"""Gritty Reboot — the sketch as data: Jun is taking Bowlheads prestige and asks Flush for pain. Flush flush, yeah?
Be sadder: your father was a urinal. Now look at the camera like you've lost everything. Flush. The best acting Jun
has seen all year.

Collage style (ADR 0026): the showrunner and his star on the BOWLHEADS stage; two ElevenLabs premade voices,
lip-synced.
"""

from __future__ import annotations

from _collage_sketch import TINTS, Staging, make_sketch, timed, voices_note
from srstudio import collage_sets
from srstudio.sketch import Line

SEED = 2605
SLUG = "gritty-reboot"
TITLE = "Gritty Reboot — Jun and Flush (Collage)"
NAMES = ("jun", "flush")
DESCRIPTION = (
    "A Collage sketch: the toilet show goes prestige. The showrunner asks his singing toilet for pain, and gets it."
)
ACCESSIBILITY = (
    "On a candy-coloured stage, a paper cut-out showrunner in a beanie, beside a card reading PRESTIGE ERA, directs "
    "a glossy cartoon toilet with a paper head, which turns from grinning to tragic. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Will and Charlie at their natural pace; no reference-voice cloning."

LINES = (
    Line("jun", "Flush, this season is prestige. Can you give me pain?"),
    Line("flush", "Flush flush, yeah?"),
    Line("jun", "Be sadder. Your father was a urinal."),
    Line("flush", "Flush. Flush. Yeah."),
    Line("jun", "Now look at the camera like you've lost everything."),
    Line("flush", "Flush."),
    Line("jun", "That's the best acting I've seen all year."),
)
BEATS, END = timed(
    LINES,
    (
        (3.4, "jun", 0, "open", "smile", "point"),
        (1.6, "flush", 1, "open", "grin", "down"),
        (2.6, "jun", 2, "half", "flat", "shrug"),
        (2.4, "flush", 3, "sad", "frown", "down"),
        (3.0, "jun", 4, "wide", "o", "point"),
        (1.6, "flush", "", "sad", "frown", "down", "zoom"),  # the look
        (1.4, "flush", 5, "sad", "frown", "down"),
        (1.4, "jun", "", "sad", "o", "face", "sting"),  # the pause: he is moved
        (2.6, "jun", 6, "sad", "smile", "face"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """The season's pitch on a card behind Jun."""
    if shot.app.who == "jun":
        collage_sets.sign(
            shot.cv, shot.back, "PRESTIGE ERA", 60, 540, 420, 140, size=58, fill="#2b2d42", color="#ffe066", tilt=-4
        )


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"jun": "stage", "flush": "stage"},
    dress=dress,
)

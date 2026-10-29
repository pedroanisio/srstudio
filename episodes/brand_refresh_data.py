"""Brand Refresh — the sketch as data: the board chair asks why the bank's logo is a toilet. Brent, the CMO, has
rebranded it for Gen Alpha: it is a bowl now, and the quarterly report is a song. Flush sings it. Profits are down.
Rosa has one note: play it again.

Collage style (ADR 0026): Rosa and Brent in the boardroom, Flush on the BOWLHEADS stage; three ElevenLabs premade
voices, lip-synced. ``STAGING`` is checked by :func:`_collage_sketch.check_staging`.
"""

from __future__ import annotations

from _collage_sketch import TINTS, Staging, make_sketch, timed, voices_note
from srstudio import collage_sets
from srstudio.sketch import Line

SEED = 2601
SLUG = "brand-refresh"
TITLE = "Brand Refresh — Rosa, Brent and Flush (Collage)"
NAMES = ("rosa", "brent", "flush")
DESCRIPTION = (
    "A Collage sketch: the board asks why the bank's logo is a toilet. The CMO rebranded it for Gen Alpha, and "
    "the quarterly report is a song."
)
ACCESSIBILITY = (
    "Paper cut-out board members in a glass boardroom at dusk: an older woman with a cane and pearls, a CMO in a "
    "blazer holding up a card that reads BOWL BANK; a falling bar chart. A glossy cartoon toilet with a paper head "
    "sings the quarterly results on a candy-coloured stage. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Matilda, Brian and Charlie at their natural pace; no reference-voice cloning."

LINES = (
    Line("rosa", "Brent. Why is our logo a toilet?"),
    Line("brent", "Gen Alpha doesn't trust banks. They trust toilets."),
    Line("rosa", "We are a bank."),
    Line("brent", "We were a bank. Now we're a bowl."),
    Line("rosa", "And the quarterly report?"),
    Line("brent", "It's a song."),
    Line("flush", "Flush flush, yeah! Profits down, yeah!"),
    Line("rosa", "Play it again."),
)
BEATS, END = timed(
    LINES,
    (
        (2.4, "rosa", 0, "angry", "frown", "point"),  # the hook: the question, the logo already on his card
        (3.2, "brent", 1, "open", "smile", "hold"),
        (1.6, "rosa", 2, "half", "flat", "down"),
        (2.4, "brent", 3, "side", "smug", "shrug"),
        (1.8, "rosa", 4, "half", "flat", "down"),
        (1.4, "brent", 5, "wide", "grin", "point", "zoom"),
        (3.0, "flush", 6, "open", "grin", "down"),
        (1.8, "rosa", "", "wide", "o", "down", "sting"),  # the pause: the board chair has heard the song
        (1.0, "rosa", "", "half", "flat", "down"),
        (1.6, "rosa", 7, "half", "smug", "point"),  # the button
        (1.0, "flush", "", "wide", "grin", "down"),
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """Brent holds up the new logo; behind Rosa the results fall; on the stage a card names the report."""
    cv, who = shot.cv, shot.app.who
    if who == "brent":
        collage_sets.sign(cv, shot.back, "BOWL BANK", 80, 530, 400, 170, size=70, fill="#ffe066", tilt=-5)
    elif who == "rosa":
        collage_sets.chart(cv, shot.back, 70, 500, 340, 230, (0.95, 0.6, 0.22))
    else:
        collage_sets.sign(cv, shot.back, "Q3 REPORT", 70, 540, 360, 140, size=60, fill="#ffffff", tilt=6)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"rosa": "boardroom", "brent": "boardroom", "flush": "stage"},
    dress=dress,
)

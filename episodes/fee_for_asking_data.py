"""Fee for Asking — the sketch as data: Deb orders one small coffee. Four dollars, plus the cup fee, which Brent calls
a cup experience; then the lid, the sleeve and the service, the service being Brent saying the fees. "What's this last
one?" "That's the fee for asking." "How much to leave?" "Ask me."

Collage style (ADR 0026), cast cards of ADR 0036: Brent renames whatever he does not want to explain; Deb keeps
smiling while she plans her exit. Two of the cast across one café counter, Deb framed right and Brent left, the till's
receipt growing card by card above them; the reel opens on a still first second (the sp-hook_motion test's arm a):
Brent at the till, the coffee rung up, before anyone speaks. ElevenLabs premade voices, lip-synced.
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
    voices_note,
)
from srstudio.sketch import Line

SEED = 3913
SLUG = "fee-for-asking"
TITLE = "Fee for Asking — Deb and Brent (Collage)"
NAMES = ("deb", "brent")
SET = "cafe"
DESCRIPTION = (
    "A Collage sketch: one small coffee, then a cup fee, a lid fee, a sleeve fee and a service fee. The last line on "
    "the receipt is the fee for asking."
)
ACCESSIBILITY = (
    "Paper cut-out characters across a café counter: a man in a blazer and tie rings up a small coffee while paper "
    "receipt cards pile up above the counter, coffee four dollars, cup, lid, sleeve, service, and last, in red, "
    "asking, two dollars; a woman in an orange top asks about each one. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Jessica and Brian at their natural pace; no reference-voice cloning."
STILL = 1.0  # the still first second: the sp-hook_motion test's arm a
BITRATE = 5_800_000  # two passes: a master under 20 MB, and a still opening that stays still

# across the counter: Brent at the till on the left, Deb on the right, so the zoom on her keeps the café's shelf
SHIFT = {"brent": -110.0, "deb": 150.0}
RED = "#c1121f"
CARD_W, CARD_H = 330, 84
COLUMNS, ROWS = (20, 360), (530, 625, 720)  # the receipt: two columns, left of the shelf, under a two-line pill
STAMP = dict(x=130, y=630, w=560, h=120)  # the last line, stamped across the receipt

LINES = (
    Line("deb", "Just a small coffee, please."),
    Line("brent", "Four dollars. Plus the cup fee."),
    Line("deb", "The cup costs extra?"),
    Line("brent", "It's not a fee. It's a cup experience."),
    Line("brent", "Then the lid fee, the sleeve fee, and service."),
    Line("deb", "What service?"),
    Line("brent", "This. Me, telling you the fees."),
    Line("deb", "What's this last one?"),
    Line("brent", "That's the fee for asking."),
    Line("deb", "How much is it to leave?"),
    Line("brent", "Ask me."),
)
BEATS, END = timed(
    LINES,
    (
        (1.2, "brent", "", "half", "smug", "hold"),  # the still: Brent at the till, the coffee rung up
        (2.0, "deb", 0, "open", "smile", "hold"),
        (2.4, "brent", 1, "half", "smug", "point"),  # the cup
        (1.4, "deb", 2, "wide", "o", "shrug"),
        (2.4, "brent", 3, "closed", "smug", "shrug"),  # renamed
        (3.0, "brent", 4, "half", "smile", "point"),  # lid, sleeve, service: one card each
        (1.2, "deb", 5, "half", "frown", "hold"),
        (2.4, "brent", 6, "open", "grin", "hold"),
        (1.0, "deb", "", "half", "flat", "hold"),  # the pause: she reads down the receipt
        (1.6, "deb", 7, "angry", "flat", "point", "zoom"),
        (2.0, "brent", 8, "half", "smug", "point", "reveal"),  # the last card, in red: asking
        (1.8, "deb", 9, "half", "smile", "hold"),  # still smiling, planning her exit
        (1.4, "brent", 10, "closed", "smug", "hold", "sting"),  # the button
        (0.0, "deb", "", "closed", "frown", "face"),  # Deb, after
    ),
    tail=1.4,
)
# the receipt, card by card: (beat, fraction of that beat, text); each card stays once it is rung up
RECEIPT = (
    (0, 0.0, "COFFEE $4.00"),
    (2, 0.5, "CUP $1.50"),
    (5, 0.1, "LID $0.75"),
    (5, 0.33, "SLEEVE $0.75"),
    (5, 0.56, "SERVICE $3.00"),
)
ASKING = (10, 0.4, "ASKING $2.00")  # rung up as he says it
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def shifted(draw: CastDrawer) -> CastDrawer:
    """``draw`` with each character moved to its side of the counter; returns the pivot of a zoom on its face that
    keeps the café's signature in frame."""

    def cast(cv, parent, app, mouths):
        dx = SHIFT[app.who]
        fx, fy = draw(cv, cv.group(parent, cv.uid("g"), x=dx), app, mouths)
        return collage_sets.zoom_pivot(SET, (fx + dx, fy), ZOOM_SCALE)

    return cast


def rung(beats, i: int, fraction: float, end: float) -> float:
    """When a receipt card is rung up: ``fraction`` of the way through beat ``i``."""
    nxt = beats[i + 1].start if i + 1 < len(beats) else end
    return round(beats[i].start + fraction * (nxt - beats[i].start), 6)


def dress(shot) -> None:
    """The till's receipt over the counter in every shot, each card from the moment it is rung up."""
    cv, app = shot.cv, shot.app
    for n, (i, fraction, text) in enumerate(RECEIPT):
        at = rung(shot.beats, i, fraction, shot.end)
        if at >= app.end:
            continue
        card = cv.group(shot.back, cv.uid("g"))
        x, y = COLUMNS[n // len(ROWS)], ROWS[n % len(ROWS)]
        tilt = (-2, 1.5, -1)[n % 3]
        collage_sets.sign(cv, card, text, x, y, CARD_W, CARD_H, size=42, tilt=tilt)
        cv.gate(card, [(max(at, app.start), app.end)])
    i, fraction, text = ASKING
    at = rung(shot.beats, i, fraction, shot.end)
    if at < app.end:
        stamp = cv.group(shot.back, cv.uid("g"))
        collage_sets.sign(cv, stamp, text, **STAMP, size=70, color=RED, tilt=-6)
        cv.gate(stamp, [(max(at, app.start), app.end)])


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"deb": SET, "brent": SET},
    dress=dress,
    cast=lambda beats, end: shifted(solo),
    still=STILL,
    bitrate=BITRATE,
    opening=shifted(stilled),
)

"""Fee for Asking — the sketch as data: Deb buys one concert ticket at the box office: forty dollars, plus the
convenience fee, convenient for Brent; then the facility fee, a fee to print it at home and the service, the service
being Brent saying the fees. "What's this last one?" "That's the fee for asking." "How much is it to leave?" "Ask me."

Collage style (ADR 0026), cast cards of ADR 0036: Brent renames whatever he does not want to explain; Deb keeps
smiling while she plans her exit. Two of the cast across one box-office window, Deb framed right and Brent left, the
order's lines growing card by card above them; the reel opens on a still first second (the sp-hook_motion test's arm
a): Brent at the window, the ticket rung up, before anyone speaks. ElevenLabs premade voices, lip-synced.
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
SET = "boardroom"
DESCRIPTION = (
    "A Collage sketch: one concert ticket, then a convenience fee, a facility fee, a fee to print it at home and a "
    "service fee. The last line on the order is the fee for asking."
)
ACCESSIBILITY = (
    "Paper cut-out characters at a box-office window with a city view: a man in a blazer and tie sells one ticket "
    "while paper cards pile up beside him, ticket forty dollars, convenience, facility, home print, service, and "
    "last, in red, asking, two dollars; a woman in an orange top asks about each one. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Jessica and Brian at their natural pace; no reference-voice cloning."
STILL = 1.0  # the still first second: the sp-hook_motion test's arm a
BITRATE = 5_800_000  # two passes: a master under 20 MB, and a still opening that stays still

# across the window: Brent selling on the left, Deb on the right, so the zoom on her keeps the office's shelf
SHIFT = {"brent": -110.0, "deb": 150.0}
RED = "#c1121f"
CARD_W, CARD_H = 330, 84
COLUMNS, ROWS = (20, 360), (530, 625, 720)  # the order: two columns, left of the shelf, under a two-line pill
STAMP = dict(x=130, y=630, w=560, h=120)  # the last line, stamped across the order

LINES = (
    Line("deb", "One ticket for Saturday, please."),
    Line("brent", "Sure. Plus the convenience fee."),
    Line("deb", "Convenient for who?"),
    Line("brent", "For us. It's very convenient."),
    Line("brent", "Then the facility fee, a fee to print it at home, and service."),
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
        (1.2, "brent", "", "half", "smug", "hold"),  # the still: Brent at the window, the ticket rung up
        (2.0, "deb", 0, "open", "smile", "hold"),
        (2.2, "brent", 1, "half", "smug", "point"),  # convenience
        (1.6, "deb", 2, "wide", "o", "shrug"),
        (2.4, "brent", 3, "closed", "smug", "shrug"),  # convenient, for him
        (3.4, "brent", 4, "half", "smile", "point"),  # facility, home print, service: one card each
        (1.2, "deb", 5, "half", "frown", "hold"),
        (2.4, "brent", 6, "open", "grin", "hold"),
        (1.0, "deb", "", "half", "flat", "hold"),  # the pause: she reads down the order
        (1.6, "deb", 7, "angry", "flat", "point", "zoom"),
        (2.0, "brent", 8, "half", "smug", "point", "reveal"),  # the last card, in red: asking
        (1.8, "deb", 9, "half", "smile", "hold"),  # still smiling, planning her exit
        (1.4, "brent", 10, "closed", "smug", "hold", "sting"),  # the button
        (0.0, "deb", "", "closed", "frown", "face"),  # Deb, after
    ),
    tail=1.4,
)
# the order, card by card: (beat, fraction of that beat, text); each card stays once it is rung up
ORDER = (
    (0, 0.0, "TICKET $40"),
    (2, 0.5, "CONVENIENCE $9"),
    (5, 0.1, "FACILITY $7"),
    (5, 0.35, "HOME PRINT $5"),
    (5, 0.65, "SERVICE $12"),
)
ASKING = (10, 0.4, "ASKING $2")  # rung up as he says it
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def shifted(draw: CastDrawer) -> CastDrawer:
    """``draw`` with each character moved to its side of the counter; returns the pivot of a zoom on its face that
    keeps the office's signature in frame."""

    def cast(cv, parent, app, mouths):
        dx = SHIFT[app.who]
        fx, fy = draw(cv, cv.group(parent, cv.uid("g"), x=dx), app, mouths)
        return collage_sets.zoom_pivot(SET, (fx + dx, fy), ZOOM_SCALE)

    return cast


def rung(beats, i: int, fraction: float, end: float) -> float:
    """When an order card is rung up: ``fraction`` of the way through beat ``i``."""
    nxt = beats[i + 1].start if i + 1 < len(beats) else end
    return round(beats[i].start + fraction * (nxt - beats[i].start), 6)


def dress(shot) -> None:
    """The order beside the window in every shot, each card from the moment it is rung up."""
    cv, app = shot.cv, shot.app
    for n, (i, fraction, text) in enumerate(ORDER):
        at = rung(shot.beats, i, fraction, shot.end)
        if at >= app.end:
            continue
        card = cv.group(shot.back, cv.uid("g"))
        x, y = COLUMNS[n // len(ROWS)], ROWS[n % len(ROWS)]
        tilt = (-2, 1.5, -1)[n % 3]
        collage_sets.sign(cv, card, text, x, y, CARD_W, CARD_H, size=38, tilt=tilt)
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

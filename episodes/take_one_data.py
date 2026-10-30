"""Take One — the sketch as data: Omar, a serious news anchor, is in the booth to voice one word for the toilet show.
Jun directs: again, but happier; like he just lost his dad; sad, but he just found a hat. Forty-seven takes. "Perfect.
We'll use the first one." Omar mutters it once more. "Ooh. Wait. Do that one again."

Collage style (ADR 0026), cast cards of ADR 0036: Jun explains his work to anyone, unprompted, and wants it taken
seriously; Omar reads the next line whatever it says. The voice booth on the BOWLHEADS stage, a take counter over the
picture; the narrower, insider reel of the batch: a director's notes, a session that ends on take one. The reel opens
on a still first second (the sp-hook_motion test's arm a): Omar at the microphone, take one. ElevenLabs premade
voices, lip-synced.
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

SEED = 3915
SLUG = "take-one"
TITLE = "Take One — Jun and Omar (Collage)"
NAMES = ("jun", "omar")
SET = "stage"
DESCRIPTION = (
    "A Collage sketch: a director gives a news anchor forty-seven notes on one word, then keeps the first take."
)
ACCESSIBILITY = (
    "Paper cut-out characters on a studio stage: a news anchor with a moustache and tie stands at the microphone "
    "while a take counter beside him climbs from take 1 to 9, 23 and 47; a young director in a beanie gives him notes. "
    "After the director keeps the first take the counter shows take 1 in red, and then take 48. Lines appear in "
    "tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Will and Daniel at their natural pace; no reference-voice cloning."
STILL = 1.0  # the still first second: the sp-hook_motion test's arm a
BITRATE = 5_800_000  # two passes: a master under 20 MB, and a still opening that stays still

# Omar at the microphone right of centre, so the zoom on him keeps the stage's shelf (right) in frame; Jun left
SHIFT = {"jun": -110.0, "omar": 150.0}
RED = "#c1121f"
SLATE = dict(x=40, y=560, w=400, h=150)  # the take counter, over the picture: a zoom leaves it whole
REC = dict(x=470, y=590, w=170, h=90)  # the booth's recording light beside it

LINES = (
    Line("jun", "Okay, Omar. Just the one word."),
    Line("omar", "Flush."),
    Line("jun", "Lovely. Again, but happier."),
    Line("omar", "Flush it!"),
    Line("jun", "Now like he just lost his dad."),
    Line("omar", "Oh. Flush."),
    Line("jun", "Sad, but he just found a hat."),
    Line("omar", "Flush? Flush!"),
    Line("jun", "Perfect. We'll use the first one."),
    Line("omar", "Flush."),
    Line("jun", "Ooh. Wait. Do that one again."),
)
BEATS, END = timed(
    LINES,
    (
        (1.2, "omar", "", "half", "flat", "hold"),  # the still: Omar at the microphone, take one
        (2.2, "jun", 0, "open", "smile", "point"),
        (1.2, "omar", 1, "half", "flat", "hold"),
        (2.0, "jun", 2, "closed", "grin", "shrug"),
        (1.2, "omar", 3, "wide", "grin", "fist"),  # take 9
        (2.2, "jun", 4, "sad", "frown", "face"),
        (1.4, "omar", 5, "sad", "frown", "down"),  # take 23
        (2.2, "jun", 6, "open", "smile", "point"),
        (1.6, "omar", 7, "wide", "o", "shrug"),  # take 47
        (2.6, "jun", 8, "closed", "smug", "hold", "reveal"),
        (1.4, "omar", "", "angry", "flat", "hold", "zoom"),  # the pause: take one, in red
        (1.4, "omar", 9, "half", "flat", "down"),  # muttered: take 48
        (1.8, "jun", 10, "wide", "grin", "point", "sting"),  # the button
        (0.0, "omar", "", "closed", "frown", "face"),  # Omar, after
    ),
    tail=1.4,
)
# the counter: (beat from which it shows, text, colour)
TAKES = (
    (0, "TAKE 1", None),
    (4, "TAKE 9", None),
    (6, "TAKE 23", None),
    (8, "TAKE 47", None),
    (10, "TAKE 1", RED),
    (11, "TAKE 48", None),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def shifted(draw: CastDrawer) -> CastDrawer:
    """``draw`` with each character moved to its side of the stage; returns the pivot of a zoom on its face that
    keeps the stage's signature in frame."""

    def cast(cv, parent, app, mouths):
        dx = SHIFT[app.who]
        fx, fy = draw(cv, cv.group(parent, cv.uid("g"), x=dx), app, mouths)
        return collage_sets.zoom_pivot(SET, (fx + dx, fy), ZOOM_SCALE)

    return cast


def dress(shot) -> None:
    """The take counter and the recording light over every shot of Omar's, the counter on the take he is on."""
    cv, app = shot.cv, shot.app
    if app.who != "omar":
        return
    light = cv.group(cv.comp, cv.uid("g"), start=app.start, end=app.end)
    collage_sets.sign(cv, light, "REC", **REC, size=60, fill=RED, color="#ffffff", tilt=4)
    starts = [shot.beats[i].start for i, _, _ in TAKES] + [shot.end]
    for n, (_, text, colour) in enumerate(TAKES):
        a, b = max(starts[n], app.start), min(starts[n + 1], app.end)
        if a >= b:
            continue
        slate = cv.group(cv.comp, cv.uid("g"), start=a, end=b)
        collage_sets.sign(cv, slate, text, **SLATE, size=96, tilt=-3, **({"color": colour} if colour else {}))


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"jun": SET, "omar": SET},
    dress=dress,
    cast=lambda beats, end: shifted(solo),
    still=STILL,
    bitrate=BITRATE,
    opening=shifted(stilled),
)

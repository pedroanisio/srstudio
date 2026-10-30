"""The Boxes — the sketch as data: Rosa walks Priya through a job application. Upload your work history. Now type it
all again into the boxes; the boxes can't read files. And a cover letter, two pages. Submitted! "Unfortunately, we've
moved forward with other candidates." "It's been one second. Who read it?" "The boxes."

Collage style (ADR 0026), cast cards of ADR 0036: Rosa can't resist a cutting line even when she's already winning;
Priya grades everything, here the form. A phone call between Rosa's boardroom and Priya's classroom after school, the
form's demands pinned up beside Priya; the reel opens moving (the sp-hook_motion test's arm b): Rosa sweeps in,
already talking. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from srstudio import collage_sets
from srstudio.collage_sketch import TINTS, ZOOM_SCALE, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Line

SEED = 3918
SLUG = "the-boxes"
TITLE = "The Boxes — Rosa and Priya (Collage)"
NAMES = ("rosa", "priya")
SETS = {"rosa": "boardroom", "priya": "classroom"}
DESCRIPTION = (
    "A Collage sketch: upload your work history, then type it all again into the boxes, then a two-page cover letter. "
    "The rejection comes one second after submit."
)
ACCESSIBILITY = (
    "Paper cut-out characters on a phone call: an older woman in pearls walks a candidate through a job application "
    "from a glass boardroom; the teacher in glasses answers from her classroom, beside a list that grows from upload "
    "file to type it again and a two-page cover letter. After she submits, a red card across the picture reads "
    "REJECTED, one second later. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Matilda and Sarah at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits

ENTER = (-760.0, 0.7)  # the opening: Rosa sweeps in from this far left, landing after this many seconds
# Rosa left of her boardroom's shelf (right); Priya near her classroom's shelf (left), so her zoom keeps it and her face
SHIFT = {"rosa": -110.0, "priya": -60.0}
RED = "#c1121f"
TASK = dict(x=450, w=600, h=90)  # the form's list beside Priya, under a two-line pill
ROWS = (540, 640, 740)
# over the picture, so a zoom leaves it whole, on the side of each room away from its shelf
STAMP = {"priya": dict(x=420, y=560, w=620, h=170), "rosa": dict(x=30, y=560, w=620, h=170)}

LINES = (
    Line("rosa", "Upload your work history."),
    Line("priya", "Done."),
    Line("rosa", "Now type it all again into the boxes."),
    Line("priya", "It's in the file I just uploaded."),
    Line("rosa", "The boxes can't read files."),
    Line("priya", "Fine. Typed."),
    Line("rosa", "And a cover letter. Two pages."),
    Line("priya", "Submitted!"),
    Line("rosa", "Unfortunately, we've moved forward with other candidates."),
    Line("priya", "It's been one second. Who read it?"),
    Line("rosa", "The boxes."),
)
BEATS, END = timed(
    LINES,
    (
        (2.0, "rosa", 0, "wide", "smile", "point"),  # sweeping in
        (1.0, "priya", 1, "open", "smile", "hold"),
        (2.4, "rosa", 2, "half", "smug", "point"),  # + type it again
        (2.5, "priya", 3, "half", "flat", "hold"),
        (1.9, "rosa", 4, "closed", "smile", "shrug"),
        (1.6, "priya", 5, "side", "frown", "hold"),
        (2.1, "rosa", 6, "half", "smug", "point"),  # + cover letter
        (1.2, "priya", 7, "wide", "grin", "fist"),  # submitted
        (3.2, "rosa", 8, "closed", "smile", "down", "reveal"),  # REJECTED, at once
        (1.2, "priya", "", "angry", "flat", "hold", "zoom"),  # the pause: the red pen comes out
        (2.4, "priya", 9, "half", "flat", "point"),
        (1.2, "rosa", 10, "half", "smug", "down", "sting"),  # the button
        (0.0, "priya", "", "closed", "frown", "face"),  # Priya, after
    ),
    tail=1.4,
)
# the form's demands as Rosa adds them: (beat, text)
ITEMS = ((0, "1. UPLOAD FILE"), (2, "2. TYPE IT AGAIN"), (6, "3. 2-PAGE LETTER"))
REJECTED_BEAT = 8  # the beat the answer comes
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def casting(beats, end) -> CastDrawer:
    """Each character on her side of her room; Rosa's first shot sweeps in from the left. Returns the pivot of a zoom
    on the face that keeps the room's signature in frame."""

    def cast(cv, parent, app, mouths):
        dx = SHIFT[app.who]
        moved = cv.group(parent, cv.uid("g"), x=dx)
        if app.start == 0.0:
            cv.keys(moved, "x", [(0.0, dx + ENTER[0]), (ENTER[1], dx)], kind="cubic-out")
        fx, fy = solo(cv, moved, app, mouths)
        return collage_sets.zoom_pivot(SETS[app.who], (fx + dx, fy), ZOOM_SCALE)

    return cast


def dress(shot) -> None:
    """Priya's list, an item for each of the form's demands, until her zoom; and the answer, in red, over the picture
    from the beat it comes."""
    cv, app = shot.cv, shot.app
    if app.who == "priya":
        zoom = next(b.start for b in shot.beats if b.event == "zoom")
        for n, (i, text) in enumerate(ITEMS):
            a, b = max(shot.beats[i].start, app.start), min(app.end, zoom)
            if a >= b:
                continue
            card = cv.group(shot.back, cv.uid("g"))
            collage_sets.sign(cv, card, text, y=ROWS[n], **TASK, size=52, tilt=(-2, 1.5, -1)[n])
            cv.gate(card, [(a, b)])
    answer = next(b.start for b in shot.beats if b.event == "reveal")
    if answer < app.end:
        stamp = cv.group(cv.comp, cv.uid("g"), start=max(answer, app.start), end=app.end)
        collage_sets.sign(cv, stamp, "REJECTED", **STAMP[app.who], size=110, color=RED, tilt=-6)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets=SETS,
    dress=dress,
    cast=casting,
    bitrate=BITRATE,
)

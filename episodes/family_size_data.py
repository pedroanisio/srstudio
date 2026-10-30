"""Family Size — the sketch as data: Rosa tears open a huge bag and it breathes out for three seconds. One chip. A
store clerk who sees nothing wrong with this explains the family it was sized for. A bigger bag holds half a chip and
a certificate, a bigger one a photograph of a chip, and the biggest, tipped out, one crumb and a note.

Collage style (ADR 0026), cast cards of ADR 0036: Rosa's manners are spent one bag at a time, Brent rebrands whatever
is in front of him. Each bag is drawn bigger than the last and each thing in it smaller. The reel opens moving (the
sp-hook_motion test's arm b): the bag's top is already leaving it. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from srstudio import collage, collage_everyday, collage_sets
from srstudio.collage_sketch import TINTS, ZOOM_SCALE, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 4104
SLUG = "family-size"
TITLE = "Family Size — Rosa and Brent (Collage)"
NAMES = ("rosa", "brent")
AISLE = "supermarket"
DESCRIPTION = (
    "A Collage sketch: a bag the size of a pillow breathes out for three seconds and holds one chip, and each bigger "
    "bag holds less."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a supermarket aisle: an old woman tears open a huge red chip bag and air rushes out "
    "until it is flat. One chip slides out. A man in a suit with a HERE TO HELP badge explains. A bigger bag holds "
    "half a chip and a certificate, a bigger one a photograph of a chip. The biggest is tipped out: one crumb and a "
    "note reading NOW WITH LESS. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised air, a sting and reveal stings."
NOTE = "ElevenLabs premade voices Matilda and Brian at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits

SHIFT = {"rosa": -190.0, "brent": 150.0}  # Rosa at the bags, near the shelf a zoom keeps; Brent across the aisle
RED, ORANGE, BLUE, PURPLE = "#e63946", "#f4a261", "#457b9d", "#7b2cbf"
# each bag: centre x, y, width, height, label, colour, label size. Each is drawn bigger than the one before
FIRST = (640.0, 1400.0, 500.0, 620.0, "FAMILY SIZE", RED, 60)
SECOND = (700.0, 1290.0, 540.0, 760.0, "FAMILY SIZE+", ORANGE, 60)
THIRD = (730.0, 1270.0, 600.0, 900.0, "VALUE PACK", BLUE, 76)
LAST = (690.0, 1290.0, 760.0, 1000.0, "MEGA VALUE", PURPLE, 86)
EMPTY = (0.84, 0.42)  # the first bag's scale once its air has gone
ZOOMED = -70.0  # Brent's crash zoom: nearer the shelf, so it keeps his face and the signature
LEAN = -46.0  # how far Rosa is pushed back by the gust
SHAKE = 14.0  # the bag's shudder as its top tears off, in px
HELD_CHIP = (392.0, 1440.0)  # the chip in Rosa's hands

LINES = (
    Line("rosa", "New! Family size!"),
    Line("brent", "Family size."),
    Line("rosa", "Which family?"),
    Line("brent", "A small one. They've had a hard year."),
    Line("rosa", "It says forty percent more."),
    Line("brent", "More bag."),
)
BEATS, END = timed(
    LINES,
    (
        (1.4, "rosa", 0, "wide", "smile", "hold"),  # the bag already tearing
        (3.0, "rosa", "", "wide", "flat", "hold", "hiss:3.0"),  # the three full seconds
        (1.4, "rosa", "", "half", "flat", "hold", "reveal:chip"),
        (1.2, "brent", 1, "open", "smile", "down"),
        (1.2, "rosa", 2, "half", "flat", "hold"),
        (2.6, "brent", 3, "sad", "smile", "shrug"),
        (1.7, "rosa", "", "open", "flat", "hold", "hiss:0.8"),  # the second bag: half a chip, certified
        (1.8, "rosa", "", "half", "flat", "hold", "hiss:0.6"),  # the third: a photo of a chip
        (1.7, "rosa", 4, "angry", "flat", "point"),
        (1.1, "brent", 5, "open", "smile", "down", "zoom"),
        (1.2, "rosa", "", "half", "flat", "hold"),  # she looks at him for as long as she can stand
        (1.5, "rosa", "", "half", "flat", "hold", "hiss:0.4"),  # the biggest bag, tipped out; each breathes less
        (0.0, "rosa", "", "half", "flat", "hold", "sting"),  # the note
    ),
    tail=2.0,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _reveal(beats: list[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def casting(beats, end: float) -> CastDrawer:
    """Rosa at the bags and pushed back by the air, Brent across the aisle, each close on one side."""
    hiss, seconds = events(beats, "hiss")[0]
    zoom = events(beats, "zoom")[0][0]

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        dx = ZOOMED if app.start <= zoom < app.end else SHIFT[app.who]
        moved = cv.group(parent, cv.uid("g"), x=dx)
        if app.start <= hiss < app.end:
            stop = hiss + float(seconds)
            cv.keys(
                moved,
                "x",
                [(hiss, dx), (hiss + 0.3, dx + LEAN), (stop, dx + LEAN), (stop + 0.3, dx)],
                kind="cubic-out",
                local=False,
            )
        fx, fy = solo(cv, moved, app, mouths)
        return collage_sets.zoom_pivot(AISLE, (fx + dx, fy), ZOOM_SCALE)

    return draw


def _bag(cv, parent, spec: tuple):
    x, y, w, h, label, colour, size = spec
    return collage_everyday.chip_bag(cv, parent, x, y, w, h, label, colour, size=size)


def _gated(cv, parent, a: float, b: float):
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(a, b)])
    return g


def _opening(cv, front, app: Appearance, hiss: float, seconds: float, chip_at: float) -> None:
    """The first bag: its top torn off from the first frame, the air leaving it, then the one chip."""
    g = _gated(cv, front, app.start, app.end)
    bag = _bag(cv, g, FIRST)
    x, y, w, h = FIRST[:4]
    top = y - h / 2
    stop = hiss + seconds
    cv.keys(
        bag,
        "x",
        [(0.0, x - SHAKE), (0.08, x + SHAKE), (0.16, x - SHAKE), (0.24, x + SHAKE), (0.32, x)],
        hold=False,
        local=False,
    )
    for prop, emptied in zip(("scaleX", "scaleY"), EMPTY, strict=True):
        cv.keys(bag, prop, [(hiss, 1.0), (stop, emptied)], hold=False, local=False)
    cv.keys(bag, "rotation", [(chip_at, 0.0), (chip_at + 0.3, 120.0)], kind="cubic-out", local=False)
    strip = cv.group(g, cv.uid("g"), x=x, y=top, start=0.0, end=0.6)
    cv.rect(strip, -w / 2, -22, w, 44, FIRST[5], collage.INK, 4)
    cv.keys(strip, "y", [(0.0, top), (0.6, top - 520)], hold=False, local=False)
    cv.keys(strip, "x", [(0.0, x), (0.6, x + 360)], hold=False, local=False)
    cv.keys(strip, "rotation", [(0.0, 0.0), (0.6, 70.0)], hold=False, local=False)
    collage_everyday.gust(cv, g, (x, top + 40), (150.0, 1060.0), hiss, stop, lines=9)
    chip = collage_everyday.chip(cv, _gated(cv, g, chip_at + 0.2, app.end), x + 120, y, size=230)
    cv.keys(chip, "x", [(chip_at + 0.2, x + 120), (chip_at + 0.7, x + 180)], hold=False, local=False)
    cv.keys(chip, "y", [(chip_at + 0.2, y), (chip_at + 0.7, y + 190)], hold=False, local=False)


def dress(shot) -> None:
    """Each bag on its reveal, bigger than the last, and what came out of it; Brent's badge; the note."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    if app.who == "brent":
        dx = ZOOMED if app.start <= events(beats, "zoom")[0][0] < app.end else SHIFT["brent"]
        collage_sets.sign(cv, shot.front, "HERE TO HELP", 300 + dx, 1500, 300, 96, size=40, tilt=-3)
        return
    hiss, seconds = events(beats, "hiss")[0]
    chip_at = _reveal(beats, "chip")
    half, photo, last = (t for t, _ in events(beats, "hiss")[1:])
    note = events(beats, "sting")[0][0]
    if app.start == 0.0:
        _opening(cv, shot.front, app, hiss, float(seconds), chip_at)
    elif app.start <= half < app.end:
        g = _gated(cv, shot.front, half, photo)
        _bag(cv, g, SECOND)
        collage_everyday.certificate(cv, g, "CERTIFICATE OF AUTHENTICITY", 300, 1450, 660, 400, size=58, tilt=-4)
        collage_everyday.chip(cv, g, 300, 1420, "half", size=290, tilt=-12)
        third = _gated(cv, shot.front, photo, app.end)
        _bag(cv, third, THIRD)
        collage_sets.sign(cv, third, "40% MORE!", 500, 880, 460, 150, size=74, color="#c1121f", tilt=6)
        collage_everyday.snapshot(cv, third, 190, 1380, 400, tilt=5)
    elif app.start <= last < app.end:
        g = _gated(cv, shot.front, last, note)
        bag = _bag(cv, g, LAST)
        cv.keys(bag, "rotation", [(last, 0.0), (last + 0.45, 150.0)], kind="cubic-out", local=False)
        crumb = collage_everyday.chip(cv, _gated(cv, g, last + 0.4, note), 900, 1640, "crumb", size=150)
        cv.keys(crumb, "y", [(last + 0.4, 1640.0), (note, 1860.0)], hold=False, local=False)
        ending = _gated(cv, shot.front, note, app.end)
        collage_sets.sign(cv, ending, "NOW WITH LESS.", 130, 1300, 820, 330, size=104, tilt=-3)
        collage_everyday.chip(cv, ending, 840, 1264, "crumb", size=190)
    elif app.start < photo:
        collage_everyday.chip(cv, shot.front, *HELD_CHIP, size=230)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"rosa": AISLE, "brent": AISLE},
    dress=dress,
    cast=casting,
    bitrate=BITRATE,
)

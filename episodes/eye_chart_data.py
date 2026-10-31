"""Eye chart: the sketch as data. Better with one or two? Deb's eye test sharpens rows that say things she has spent
years not reading: call your sister, he is not going to change, your mother was right. She asks to go back to one.

Collage (ADR 0026), ElevenLabs premade Jessica (Deb) and Alice (Dr. Feld). It opens on a held frame (arm a of
``sp-hook_motion``). :func:`dress` draws the chart and the lens frame.
"""

from __future__ import annotations

from srstudio import collage, collage_group, collage_odds, foley
from srstudio.collage_group import Place
from srstudio.collage_sketch import TINTS, CastDrawer, Sound, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Line, Mouths, events

SEED = 4121
SLUG = "eye-chart"
TITLE = "Eye chart - Deb (Collage)"
NAMES = ("deb", "feld")
ROOM = "therapy"
STILL = 1.0
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
DESCRIPTION = "An eye test sharpens until the bottom line says what Deb has been avoiding."
ACCESSIBILITY = (
    "A paper cut-out woman sits behind a clinic lens frame in front of a blurred eye chart. Each click of the dial "
    "snaps one row sharp: call your sister, not a small mistake, he is not going to change, your mother was right. "
    "She reads them out, voice dropping. Can I go back to one? Click, the chart melts to a blur and she smiles."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised foley."
NOTE = "ElevenLabs premade voices Jessica and Alice at their natural pace; no reference-voice cloning."
PLACES = {"deb": Place(290.0, 1920.0, 0.72), "feld": Place(810.0, 1920.0, 0.72)}
ROWS = ("CALL YOUR SISTER", "NOT A SMALL MISTAKE", "HE IS NOT GOING TO CHANGE", "YOUR MOTHER WAS RIGHT")
CHART = (230.0, 480.0)

LINES = (
    Line("feld", "Better with one? Or two?"),
    Line("deb", "They're the same."),
    Line("feld", "Read me that line."),
    Line("deb", "Call... your... sister."),
    Line("deb", "That was not... a small mistake."),
    Line("feld", "Good. Next line."),
    Line("deb", "He is not... going to change."),
    Line("feld", "Bottom line."),
    Line("deb", "Your mother... was right."),
    Line("feld", "Better? Or worse?"),
    Line("deb", "Can I go back to one?"),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "deb", "", "open", "flat", "down"),
        (1.7, "feld", 0, "open", "flat", "hold"),
        (1.2, "deb", 1, "side", "flat", "down"),
        (1.4, "feld", 2, "open", "flat", "hold", "reveal:row"),
        (2.2, "deb", 3, "open", "frown", "down"),
        (2.4, "deb", 4, "sad", "frown", "down", "reveal:row"),
        (1.3, "feld", 5, "open", "flat", "hold"),
        (2.5, "deb", 6, "sad", "flat", "down", "reveal:row"),
        (1.8, "feld", 7, "open", "flat", "point", "reveal:row"),
        (3.6, "deb", 8, "sad", "flat", "down"),
        (1.5, "feld", 9, "open", "smug", "hold"),
        (1.8, "deb", 10, "wide", "flat", "down"),
        (0.0, "deb", "", "closed", "smile", "down", "reveal:blur"),
    ),
    tail=2.0,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def moments(beats, name: str) -> list[float]:
    return [t for t, what in events(beats, "reveal") if what == name]


def casting(beats, end: float) -> CastDrawer:
    lineup = collage_group.pair(PLACES, (STILL, end))

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        return lineup(cv, parent, app, mouths)

    return draw


def dress(shot) -> None:
    """The chart on the wall behind them, the frame on Deb's face; each row keeps its place through every shot."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    collage_odds.eye_chart(
        cv, shot.back, *CHART, ROWS, moments(beats, "row"), end=shot.end, blur_at=moments(beats, "blur")[0]
    )
    if app.start >= STILL:
        x, y = collage_group.place_of(PLACES["deb"], collage.face(collage.LOOKS["deb"]))
        collage_odds.lens_frame(cv, shot.front, x, y - 34.0, 130.0)


def sounds(beats, end: float) -> list[Sound]:
    """The dial's click on every change."""
    return [Sound("click", foley.REMOTE_CLICK, (*moments(beats, "row"), *moments(beats, "blur")), -4.0)]


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"deb": ROOM, "feld": ROOM},
    dress=dress,
    cast=casting,
    still=STILL,
    bitrate=BITRATE,
    sounds=sounds,
)

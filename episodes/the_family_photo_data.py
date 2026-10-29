"""The Family Photo — the sketch as data: Gary sets the phone's ten-second timer for a natural family photo, then
directs every face on the sofa until nobody looks natural. With seconds left he does Flush's voice. Rosa and Kai
crack up; the flash fires; the print shows the only natural photo they will ever take, with Gary a blur. "That's the
Christmas card."

Collage style (ADR 0026), the group shot and the photo's props of ADR 0036: Gary, Rosa and Kai on one sofa in the
living room, the same framing in every group shot; ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from srstudio import collage, collage_photo
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, appearances, events

SEED = 3907
SLUG = "the-family-photo"
TITLE = "The Family Photo — Gary, Rosa and Kai (Collage)"
NAMES = ("gary", "rosa", "kai")
DESCRIPTION = (
    "A Collage sketch: Gary wants a natural family photo and directs every face until nobody is natural. Then he "
    "does the toilet's voice."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a living room: a balding dad props his phone on a stack of books and runs to the "
    "sofa, where his mother in pearls and his son in a headset sit stiffly inside the camera's frame lines while a "
    "countdown runs. A white flash, then the printed photo: grandmother and grandson laughing, the dad a blur. Lines "
    "appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh, beep, shutter and sting."
NOTE = "ElevenLabs premade voices Chris, Matilda and River at their natural pace; no reference-voice cloning."

# the sofa, as the phone sees it: Gary on the left, Rosa in the middle, Kai on the right
PLACES = {"gary": Place(260.0, 1800.0, 0.55), "rosa": Place(560.0, 1800.0, 0.6), "kai": Place(865.0, 1800.0, 0.56)}
PHONE = (820.0, 1900.0, 1.3)  # the timer prop in Gary's setup shot: the books' bottom centre and its scale
PRINT = dict(x=100.0, y=560.0, width=840.0, tilt=-3.0)
LAUGH = {"gary": ("wide", "o", "shrug"), "rosa": ("closed", "grin", "hold"), "kai": ("closed", "grin", "hold")}
FLASH_HOLD, FLASH_FADE = 1 / 24, 0.3  # one white frame, then the room comes back

LINES = (
    Line("gary", "Ten seconds! Natural!"),
    Line("gary", "Mom, chin down."),
    Line("rosa", "It is down."),
    Line("gary", "Kai, headset off."),
    Line("kai", "It's off."),
    Line("gary", "Everyone, just be normal!"),
    Line("gary", "Flushy-flush!"),
    Line("rosa", "That's the Christmas card."),
)
CHIN, NORMAL, FLUSHY = 1, 5, 6  # the lines the listeners react to
BEATS, END = timed(
    LINES,
    (
        (1.6, "gary", 0, "wide", "grin", "point", "timer"),  # at the phone: the timer is set
        (0.9, "rosa", "", "half", "grin", "hold"),  # the frame: three on the sofa, smiling too hard
        (1.4, "gary", 1, "open", "grin", "point"),
        (1.1, "rosa", 2, "angry", "grin", "hold"),
        (1.4, "gary", 3, "open", "grin", "point"),
        (0.9, "kai", "", "wide", "o", "hold", "beep"),  # a new episode drops
        (1.0, "kai", 4, "half", "flat", "hold", "zoom"),  # it is not off
        (1.8, "gary", 5, "wide", "grin", "shrug"),
        (1.3, "rosa", "", "angry", "grin", "hold"),  # the pause: three stiff smiles, the count running out
        (1.2, "gary", 6, "wide", "o", "shrug"),  # Flush's voice, the last resort
        (0.6, "gary", "", "wide", "o", "shrug", "flash"),
        (1.6, "rosa", "", "closed", "smile", "hold", "reveal"),  # the print, alone on screen
        (2.0, "rosa", 7, "closed", "smile", "hold", "sting"),  # the button, over the print
        (0.0, "gary", "", "sad", "flat", "down"),  # Gary, after
    ),
    tail=1.6,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(max(start, 0.0), 6), "eyes": eyes, "mouth": mouth, "arms": arms}


@dataclass(frozen=True)
class Plan:
    """The staging made from the beats the build draws: the lineup on the sofa, the self-timer's count (from
    ``start``, ``seconds`` long, reaching zero on the shutter) and the ``reveal`` that cuts to the print."""

    lineup: Lineup
    start: float
    seconds: int
    flash: float
    reveal: float


def plan(beats: Sequence[Beat], end: float) -> Plan:
    """The group shots, the listeners' reactions and the countdown, timed from the beats' events and lines, so a
    recording's timing moves them with it."""
    timer, flash, reveal = (events(beats, e)[0][0] for e in ("timer", "flash", "reveal"))

    def said(line: int) -> float:
        return next(b.start for b in beats if b.line == line)

    chin, normal, flushy = said(CHIN), said(NORMAL), said(FLUSHY)
    reactions = {
        "gary": [_pose(0, "wide", "grin", "point"), _pose(normal, "sad", "grin", "shrug")],
        "rosa": [
            _pose(0, "half", "grin", "hold"),
            _pose(chin + 0.5, "angry", "grin", "hold"),
            _pose(flushy + 0.3, "closed", "grin", "hold"),
        ],
        "kai": [
            _pose(0, "side", "flat", "down"),
            _pose(normal, "half", "flat", "down"),
            _pose(flushy + 0.3, "closed", "grin", "hold"),
        ],
    }
    spans = tuple(
        (a.start, a.end) for a in appearances(beats, end) if timer < a.start < reveal and a.who != "kai"
    )  # every shot between the setup and the print, but Kai's close
    seconds = max(1, min(collage_photo.MAX_SECONDS, round(flash - timer)))
    return Plan(Lineup(PLACES, reactions, spans), round(flash - seconds, 6), seconds, flash, reveal)


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """The lineup in the group shots, the speaker alone in the singles, and nobody in front of the print."""
    p = plan(beats, end)

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start == p.reveal:
            return collage.face(collage.LOOKS[app.who])  # no one drawn: no zoom lands here
        if p.lineup.staged(app):
            return p.lineup(cv, parent, app, mouths)
        return solo(cv, parent, app, mouths)

    return draw


def dress(shot) -> None:
    """The phone counting on its books in Gary's setup; the sofa, the viewfinder and the flash over the group; the
    print, darkened room behind it, from the reveal."""
    cv, app = shot.cv, shot.app
    p = plan(shot.beats, shot.end)
    if app.start == 0.0:
        x, y, scale = PHONE
        collage_photo.timer(cv, shot.front, x, y, start=p.start, seconds=p.seconds, scale=scale)
    elif p.lineup.staged(app):
        collage_photo.sofa(cv, shot.front)
        collage_photo.viewfinder(cv, shot.front, start=p.start, seconds=p.seconds)
        if app.start <= p.flash < app.end:
            collage_photo.flash(cv, shot.front, p.flash, hold=FLASH_HOLD, fade=FLASH_FADE)
    elif app.start == p.reveal:
        cv.rect(shot.front, 0, 0, cv.width, cv.height, "#2b1838", opacity=0.55)
        collage_photo.print_photo(cv, shot.front, PLACES, LAUGH, blur=("gary",), **PRINT)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": "living-room", "rosa": "living-room", "kai": "living-room"},
    dress=dress,
    cast=casting,
)

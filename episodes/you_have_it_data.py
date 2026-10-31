"""You have it: the sketch as data. Two friends, one slice of cake, and neither will take the last of it. Each halves
it. It gets to a speck, a pin, a ping and a blast. The smoke clears, the table is gone, the speck is still on the plate.

Collage (ADR 0026), ElevenLabs premade Sarah (Priya) and Jessica (Deb). It opens on a held frame (arm a of
``sp-hook_motion``). The blast is one flash of the frame, never a strobe. :func:`dress` draws the table and the slice.
"""

from __future__ import annotations

from srstudio import collage, collage_everyday, collage_group, collage_odds, collage_photo, foley
from srstudio.collage_group import Place
from srstudio.collage_sketch import TINTS, CastDrawer, Sound, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Line, Mouths, events

SEED = 4120
SLUG = "you-have-it"
TITLE = "You have it - Priya and Deb (Collage)"
NAMES = ("priya", "deb")
ROOM = "cafe"
STILL = 1.0
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
DESCRIPTION = "Two friends, one slice of cake, and neither will take the last of it."
ACCESSIBILITY = (
    "Two paper cut-out friends sit at a cafe table with one slice of cake. You have it, no, you have it. Each cuts it "
    "in half and eats a half, until only a speck is left, parted with tweezers and a pin. A ping. A hum. The frame "
    "flashes white once and blows back. The smoke clears, the table is gone, both faces are sooty, and Priya still "
    "holds the plate with the speck on it. You have it."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised foley."
NOTE = "ElevenLabs premade voices Sarah and Jessica at their natural pace; no reference-voice cloning."
PLACES = {"priya": Place(285.0, 1920.0, 0.74), "deb": Place(800.0, 1920.0, 0.74)}
PLATE = (540.0, 1560.0)
SOOT = "#2a2526"
BOOM = foley.Burst(2.0, 180.0, attack=0.002, decay=0.45)
PING = foley.Burst(0.5, 4200.0, attack=0.001, decay=0.7, tone_hz=3100.0, tone_end_hz=3100.0, tone=0.9)
HUM = foley.Burst(0.9, 300.0, attack=0.6, decay=0.15, tone_hz=70.0, tone_end_hz=240.0, tone=0.9)
KNIFE = foley.Burst(0.12, 2800.0, attack=0.002, decay=0.5, tone_hz=1500.0, tone_end_hz=1300.0, tone=0.5)

LINES = (
    Line("priya", "You have it."),
    Line("deb", "No, you have it."),
    Line("priya", "I'll just even it up."),
    Line("deb", "You have it."),
    Line("deb", "Just a sliver."),
    Line("priya", "You have it."),
    Line("priya", "Careful."),
    Line("deb", "I couldn't possibly."),
    Line("deb", "Half?"),
    Line("priya", "You have it."),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "deb", "", "open", "flat", "down"),
        (1.4, "priya", 0, "open", "smile", "down"),
        (1.5, "deb", 1, "open", "smile", "down"),
        (1.7, "priya", 2, "side", "smile", "point", "reveal:cut"),
        (1.3, "deb", 3, "half", "flat", "down"),
        (1.5, "deb", 4, "side", "smile", "point", "reveal:cut"),
        (1.3, "priya", 5, "half", "flat", "down"),
        (1.0, "priya", 6, "wide", "o", "down"),
        (1.7, "deb", 7, "side", "flat", "hold", "reveal:cut"),
        (2.2, "deb", 8, "wide", "flat", "point", "reveal:pin"),
        (0.8, "priya", "", "wide", "flat", "down", "reveal:ping"),
        (0.9, "priya", "", "wide", "o", "down", "reveal:blast"),
        (1.6, "deb", "", "wide", "o", "down", "reveal:smoke"),
        (0.0, "priya", 9, "half", "flat", "hold"),
    ),
    tail=2.2,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def moments(beats, name: str) -> list[float]:
    return [t for t, what in events(beats, "reveal") if what == name]


def casting(beats, end: float) -> CastDrawer:
    """The two of them at the table after the still opening; the listener keeps her eyes on the plate."""
    lineup = collage_group.pair(PLACES, (STILL, end))

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        return lineup(cv, parent, app, mouths)

    return draw


def dress(shot) -> None:
    """The table and the slice until the blast; afterwards no table, soot, smoke, and the plate in her hand."""
    cv, front, app, beats = shot.cv, shot.front, shot.app, shot.beats
    blast, smoke = moments(beats, "blast")[0], moments(beats, "smoke")[0]
    if app.start < blast:
        table = cv.group(front, cv.uid("g"), end=app.end)
        collage_everyday.tablecloth(cv, table, 1500.0)
        collage_odds.cake_slice(cv, table, *PLATE, moments(beats, "cut") + moments(beats, "pin"), size=280.0)
        pin = moments(beats, "pin")[0]
        if app.start <= pin < app.end:
            cv.rect(table, PLATE[0] - 3, 1270.0, 6.0, 230.0, "#7c8691", collage.INK, 1.5)
    if app.start <= blast < app.end:
        collage_photo.flash(cv, front, blast, hold=0.25, fade=0.6)
        collage_everyday.gust(cv, front, (540.0, 900.0), (540.0, 1900.0), blast, app.end)
    if app.start >= smoke:
        for name, place in PLACES.items():
            x, y = collage_group.place_of(place, collage.face(collage.LOOKS[name]))
            for dx, dy, r in ((-90, -40, 70), (40, 30, 84), (-40, 96, 60), (70, -70, 48)):
                cv.ellipse(front, x + dx, y + dy, r, r * 0.7, SOOT, opacity=0.88)
        collage_odds.cake_slice(cv, front, 330.0, 1720.0, (0.0, 0.01, 0.02), size=120.0)


def sounds(beats, end: float) -> list[Sound]:
    """A knife per cut, the ping, the hum, one blast."""
    return [
        Sound("knife", KNIFE, tuple(moments(beats, "cut")), -9.0),
        Sound("ping", PING, tuple(moments(beats, "ping")), -8.0),
        Sound("hum", HUM, tuple(t + 0.1 for t in moments(beats, "ping")), -12.0),
        Sound("boom", BOOM, tuple(moments(beats, "blast")), -1.0),
    ]


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"priya": ROOM, "deb": ROOM},
    dress=dress,
    cast=casting,
    still=STILL,
    bitrate=BITRATE,
    sounds=sounds,
)

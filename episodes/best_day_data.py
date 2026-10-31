"""Best day: the sketch as data. Deb narrates the best day of her life with her lips shut: strangers smile, Brent cannot
look away. Evening, the mirror, her biggest smile, and across both front teeth a whole leaf of spinach. Next morning
Brent has one too. She says nothing. He's magnetic.

Collage (ADR 0026), ElevenLabs premade Jessica (Deb); Gary and Brent are silent. Her voice is over the picture, so no
shot lip-syncs. It opens on a held frame (arm a of ``sp-hook_motion``). :func:`dress` draws the leaf.
"""

from __future__ import annotations

from srstudio import collage, collage_group, collage_odds, collage_sets, foley
from srstudio.collage_group import Place
from srstudio.collage_sketch import TINTS, CastDrawer, Sound, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Line, Mouths, events

SEED = 4124
SLUG = "best-day"
TITLE = "Best day - Deb (Collage)"
NAMES = ("deb", "gary", "brent")
STOP, ROOM, BATH = "bus-stop", "boardroom", "bathroom"
STILL = 1.0
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
DESCRIPTION = "The best day of Deb's life, as told by someone who has not yet looked in a mirror."
ACCESSIBILITY = (
    "A paper cut-out woman narrates, lips shut: today I am magnetic. Strangers smile at her at the bus stop. In a "
    "meeting Brent cannot look away and slides her a note. In the bathroom mirror that evening she gives her biggest "
    "smile, and a wide spinach leaf is stuck across her front teeth. The bus, she says, in a tiny voice. Next morning "
    "Brent beams with a leaf on his teeth. She smiles and says nothing."
)
NARRATION = f"Voiced with ElevenLabs premade voice {voices_note(('deb',))}; synthesised foley."
NOTE = "ElevenLabs premade voice Jessica at her natural pace; no reference-voice cloning."
PAIR = {"deb": Place(290.0, 1920.0, 0.78), "gary": Place(800.0, 1920.0, 0.78)}
TABLE = {"deb": Place(290.0, 1920.0, 0.78), "brent": Place(800.0, 1920.0, 0.78)}
MOUTH_Y = 1216.0  # of a bust at full scale: where the teeth are
BUS = foley.Burst(1.6, 300.0, attack=0.5, decay=0.3)
DRIP = foley.Burst(0.14, 1200.0, attack=0.002, decay=0.6, tone_hz=800.0, tone_end_hz=1300.0, tone=0.7)
PLOP = foley.Burst(0.5, 200.0, attack=0.01, decay=0.5, tone_hz=330.0, tone_end_hz=120.0, tone=0.8)

LINES = (
    Line("deb", "Today, I am magnetic."),
    Line("deb", "Strangers smile at me."),
    Line("deb", "Brent could not look away."),
    Line("deb", "He gave me his number."),
    Line("deb", "Best day of my life."),
    Line("deb", "The bus."),
    Line("deb", "He's magnetic."),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "gary", "", "open", "smile", "down"),
        (2.0, "deb", 0, "open", "flat", "down", "reveal:stop"),
        (2.4, "deb", 1, "open", "flat", "down"),
        (2.4, "brent", 2, "wide", "grin", "down", "reveal:room"),
        (2.3, "brent", 3, "wide", "grin", "point", "reveal:note"),
        (2.2, "deb", 4, "open", "flat", "down", "reveal:bath"),
        (2.4, "deb", "", "wide", "grin", "down", "zoom"),
        (1.6, "deb", 5, "wide", "grin", "down"),
        (2.3, "brent", 6, "wide", "grin", "down", "reveal:morning"),
    ),
    tail=2.1,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def moments(beats, name: str) -> list[float]:
    return [t for t, what in events(beats, "reveal") if what == name]


def leafed(beats) -> float:
    """The mirror's zoom, when she sees it."""
    return next(t for t, _ in events(beats, "zoom"))


def setting(beats, app: Appearance) -> str:
    """Stop, room, bathroom, stop: the place of the shot's first beat."""
    if app.start >= moments(beats, "morning")[0]:
        return STOP
    if app.start >= moments(beats, "bath")[0]:
        return BATH
    return ROOM if app.start >= moments(beats, "room")[0] else STOP


def casting(beats, end: float) -> CastDrawer:
    """Her voice is over the picture, so nobody's lips move until the mirror; she is alone only in the mirror."""
    room, bath, morning = (moments(beats, n)[0] for n in ("room", "bath", "morning"))
    gary = collage_group.pair(PAIR, (STILL, room), listening=("open", "smile", "down"))
    brent = collage_group.pair(TABLE, (room, bath), (morning, end), listening=("half", "smile", "down"))

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        silent: Mouths = {}
        if app.start >= bath and app.start < morning:
            return solo(cv, parent, app, silent)
        return (gary if app.start < room else brent)(cv, parent, app, silent)

    return draw


def _leaf(cv, parent, place: Place) -> None:
    x, y = collage_group.place_of(place, (540.0, MOUTH_Y))
    collage_odds.spinach(cv, parent, x, y, 104.0 * place.scale)


def dress(shot) -> None:
    """The note on the table, and the leaf: hers from the mirror, his next morning; the bus goes by behind."""
    cv, front, app, beats = shot.cv, shot.front, shot.app, shot.beats
    note, bath, morning = (moments(beats, n)[0] for n in ("note", "bath", "morning"))
    leaf = leafed(beats)
    if app.start <= note < app.end:
        collage_sets.sign(cv, cv.group(front, cv.uid("g"), start=note), "555-0147", 350, 1480, 380, 110, size=52)
    if app.start >= bath and app.start < morning:
        collage_odds.spinach(cv, cv.group(front, cv.uid("g"), start=leaf), 540.0, MOUTH_Y, 104.0)
    if app.start >= morning:
        _leaf(cv, front, TABLE["brent"])


def sounds(beats, end: float) -> list[Sound]:
    """A bus, the paper sliding, the tap's drip and the one low note."""
    return [
        Sound("bus", BUS, (moments(beats, "stop")[0] + 1.5,), -15.0),
        Sound("slide", foley.SWISH, tuple(moments(beats, "note")), -11.0),
        Sound("drip", DRIP, (moments(beats, "bath")[0] + 0.2,), -9.0),
        Sound("note", PLOP, (leafed(beats),), -6.0),
    ]


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"deb": STOP, "gary": STOP, "brent": ROOM},
    setting=setting,
    dress=dress,
    cast=casting,
    still=STILL,
    bitrate=BITRATE,
    sounds=sounds,
)

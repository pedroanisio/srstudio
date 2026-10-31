"""Sensor: the sketch as data. Jun cannot make a sensor tap see him. Nor the soap, nor the dryer, nor the light. At the
next sink Omar waves one slow hand: it doesn't see you. He came in to wash his hands in 1987. Kai walks through and
everything works. The door shuts an inch from Jun's fingers.

Collage (ADR 0026), ElevenLabs premade Will (Jun) and Daniel (Omar); Kai is silent. It opens on a held frame (arm a of
``sp-hook_motion``). :func:`dress` draws the sink, the dark and the door.
"""

from __future__ import annotations

from srstudio import collage, collage_everyday, collage_group, collage_odds, foley
from srstudio.collage_group import Place
from srstudio.collage_sketch import TINTS, CastDrawer, Sound, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Line, Mouths, events

SEED = 4122
SLUG = "sensor"
TITLE = "Sensor - Jun and Omar (Collage)"
NAMES = ("jun", "omar", "kai")
ROOM = "bathroom"
STILL = 1.0  # the recording's silent head, the first shot
PUSH = 1.06  # that shot moves: the first second opens on movement, arm b
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
DESCRIPTION = "A sensor tap that cannot see one man, and the man at the next sink who knows why."
ACCESSIBILITY = (
    "A paper cut-out man waves at a sensor tap that will not run. Nothing else in the bathroom sees him either, and "
    "the light clicks off. At the next sink an older man waves one slow hand: it doesn't see you, he says, he came in "
    "to wash his hands in 1987. A third man walks in and everything works at once. The door shuts an inch from the "
    "first man's fingers. Every time."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(('jun', 'omar'))}; synthesised foley."
NOTE = "ElevenLabs premade voices Will and Daniel at their natural pace; no reference-voice cloning."
PLACES = {"omar": Place(270.0, 1920.0, 0.76), "jun": Place(740.0, 1920.0, 0.76)}
SINKS = (270.0, 740.0)
RIM = 1720.0
DOOR = (956.0, 300.0, 124.0, 1400.0)
HUM = foley.Burst(1.5, 240.0, attack=0.3, decay=0.2, tone_hz=120.0, tone_end_hz=120.0, tone=0.6)
ROAR = foley.Burst(0.9, 2200.0, attack=0.02, decay=0.25)
DARK = ("#0b0e1a", 0.74)

LINES = (
    Line("jun", "Hello? I'm right here."),
    Line("jun", "Oh, come on."),
    Line("omar", "It doesn't see you."),
    Line("jun", "It's just broken."),
    Line("omar", "How long have you been in here?"),
    Line("jun", "Ten minutes."),
    Line("omar", "I came in to wash my hands in 1987."),
    Line("jun", "No. Wait. Wait!"),
    Line("omar", "Every time."),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "omar", "", "half", "flat", "hold"),
        (1.8, "jun", 0, "wide", "grin", "fist"),
        (1.0, "jun", "", "side", "flat", "point", "reveal:off"),
        (1.2, "jun", 1, "angry", "frown", "fist", "reveal:on"),
        (2.2, "omar", 2, "half", "flat", "fist"),
        (1.4, "jun", 3, "open", "grin", "shrug"),
        (1.9, "omar", 4, "half", "flat", "fist"),
        (1.2, "jun", 5, "open", "smile", "shrug"),
        (3.8, "omar", 6, "closed", "flat", "fist"),
        (1.1, "kai", "", "open", "smile", "down", "reveal:kai"),
        (1.5, "jun", 7, "wide", "o", "down", "reveal:shut"),
        (0.0, "omar", 8, "half", "smile", "fist"),
    ),
    tail=2.0,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def moments(beats, name: str) -> list[float]:
    return [t for t, what in events(beats, "reveal") if what == name]


def casting(beats, end: float) -> CastDrawer:
    """The two sinks; Omar's slow wave is his listening pose, so it never stops; Kai alone for his walk through."""
    lineup = collage_group.pair(PLACES, (STILL, moments(beats, "kai")[0]), (moments(beats, "shut")[0], end))
    lineup.reactions["omar"][0].update(arms="fist")

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        return lineup(cv, parent, app, mouths)

    return draw


def dress(shot) -> None:
    """Two basins, the dark while the light is off, the door that opens for Kai and shuts on Jun."""
    cv, front, app, beats = shot.cv, shot.front, shot.app, shot.beats
    shut = moments(beats, "shut")[0]
    x, y, w, h = DOOR
    if app.who == "kai":
        collage_odds.sensor_tap(cv, front, 540.0, RIM, ((app.start + 0.15, app.end),))
        collage_everyday.gust(cv, front, (900.0, 1300.0), (560.0, 1400.0), app.start + 0.4, app.end, lines=3)
        cv.rect(shot.back, x, y, 40.0, h, "#7a6a55", collage.INK, 4.0)
    elif app.start < STILL:
        collage_odds.sensor_tap(cv, front, 540.0, RIM, ())
    else:
        for at in SINKS:
            collage_odds.sensor_tap(cv, front, at, RIM, ())
    if app.start >= shut:
        collage_everyday.arm(cv, front, "jun", (800.0, 1500.0), (936.0, 1180.0), width=64.0)
        cv.rect(front, x, y, w, h, "#7a6a55", collage.INK, 5.0)
    off, on = moments(beats, "off")[0], moments(beats, "on")[0]
    if app.start <= off < app.end:
        shade = cv.group(front, cv.uid("g"), start=off, end=min(on, app.end))
        cv.rect(shade, 0, 0, cv.width, cv.height, DARK[0], opacity=DARK[1])


def sounds(beats, end: float) -> list[Sound]:
    """The room's hum, the light's click, and everything at once for Kai."""
    kai = moments(beats, "kai")[0]
    return [
        Sound("hum", HUM, (0.0,), -24.0),
        Sound("switch", foley.REMOTE_CLICK, (*moments(beats, "off"), *moments(beats, "on")), -6.0),
        Sound("tap", foley.SWISH, (kai + 0.15,), -11.0),
        Sound("roar", ROAR, (kai + 0.4,), -12.0),
        Sound("door", foley.KNOCK, tuple(moments(beats, "shut")), -7.0),
    ]


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"jun": ROOM, "omar": ROOM, "kai": ROOM},
    dress=dress,
    cast=casting,
    push=PUSH,
    bitrate=BITRATE,
    sounds=sounds,
)

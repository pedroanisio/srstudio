"""The Boat — the sketch as data: four strangers at a bus stop, facing front. Deb's earbuds die and her show plays out
loud. She gets it paused, and for two seconds nobody moves. Then Omar, eyes front: what dentist? They make her press
play. The bus comes, Brent asks if they are getting on, the whole stop shushes him, and he comes down to watch. Then
the phone shows one percent and goes black, and four heads turn to Deb.

Collage style (ADR 0026): people who would never speak to her, until she has the only thing they want, and then until
she has run out of it. The reel opens frozen (the sp-hook_motion test's arm a): the four strangers, silent, uncaptioned
and unmoving for the first STILL seconds. ElevenLabs premade voices, lip-synced; the show on the phone is a voice
with no mouth.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_everyday, sketch
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import SPEAKERS, TINTS, CastDrawer, Staging, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events
from srstudio.voice import Voice, VoiceSettings

SEED = 3119
SLUG = "the-boat"
TITLE = "The Boat — Deb, Omar, Priya, Jun and Brent (Collage)"
NAMES = ("deb", "omar", "priya", "jun", "brent")
STOP = "bus-stop"
SHOW = sketch.Speaker(
    "phone", Voice(role="phone", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"), VoiceSettings(0.3, 0.75, 0.6)
)
DESCRIPTION = (
    "A Collage sketch: earbuds die at a bus stop, a show plays out loud, and four strangers who have never spoken "
    "need to know what the dentist did."
)
ACCESSIBILITY = (
    "Paper cut-out characters: four strangers at a bus stop, facing front. A phone starts shouting about a boat and a "
    "dentist. The woman holding it pauses it. Nobody moves. Then a man, eyes front, asks what dentist, and they tell "
    "her to press play. They huddle round the phone. A bus pulls up behind them, the driver asks if they are getting "
    "on and they shush him, and he comes down and joins them. The phone shows one percent and goes black. Four heads "
    "turn to her. Lines appear in tinted pills."
)
NARRATION = (
    f"Voiced with ElevenLabs premade voices {voices_note(NAMES)} and Laura (the phone);"
    " a synthesized bus, whoosh and sting."
)
NOTE = "ElevenLabs premade voices Jessica, Daniel, Sarah, Will, Brian and Laura at their natural pace; no cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB

STILL = 1.2  # the seconds the four hold, frozen and silent, before the phone goes off
WIDE = {
    "omar": Place(170.0, 1960.0, 0.56),
    "deb": Place(430.0, 1960.0, 0.56),
    "priya": Place(690.0, 1960.0, 0.56),
    "jun": Place(925.0, 1960.0, 0.56),
}
HUDDLE = {
    "omar": Place(165.0, 2000.0, 0.68),
    "jun": Place(945.0, 2000.0, 0.68),
    "priya": Place(725.0, 2020.0, 0.72),
    "deb": Place(445.0, 2020.0, 0.72),
}
TURNED = {
    "brent": Place(210.0, 1700.0, 0.62),
    "jun": Place(470.0, 1700.0, 0.62),
    "omar": Place(150.0, 2080.0, 0.72),
    "priya": Place(460.0, 2080.0, 0.72),
    "deb": Place(860.0, 2040.0, 0.78),
}
JOINS = Place(835.0, 1620.0, 0.62)  # where Brent comes to in the huddle
JOIN_FROM = 1300.0  # and where he comes from
JOIN = 0.45  # the seconds it takes him
TURN = 0.7  # the seconds into the last shot that the heads turn
HELD = dict(x=355.0, y=1560.0, w=150.0, h=250.0, tilt=-6.0)  # the phone as Deb holds it at the stop
HUDDLED = dict(x=350.0, y=1600.0, w=190.0, h=320.0, tilt=-4.0)
LAST = dict(x=750.0, y=1610.0, w=220.0, h=380.0, tilt=-4.0)
SCREEN_LIT = "#bfe3ff"
CLOSE = dict(x=390.0, y=1330.0, w=300.0, h=520.0, tilt=-8.0)  # the phone, close on her
BUS_TOP, BUS_H = 810.0, 760.0  # the side of the bus behind them
BUS_FROM, BUS_PARKED = 1300.0, -200.0  # its x as it comes in and where it stops
BUS_ROLL = 0.9  # the seconds it rolls in
BATTERY = dict(x=190.0, y=420.0, w=700.0, h=1200.0)

LINES = (
    Line("phone", "Darren! I know about the boat!"),
    Line("phone", "The boat, Darren! And the dentist!"),
    Line("omar", "What dentist?"),
    Line("deb", "Sorry?"),
    Line("priya", "Was it the sister's dentist?"),
    Line("jun", "Press play."),
    Line("brent", "You getting on?"),
    Line("priya", "Shh!"),
    Line("brent", "Is this the boat one?"),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "omar", "", "half", "flat", "down"),
        (1.95, "priya", 0, "half", "flat", "down", "beep"),
        (2.3, "deb", 1, "wide", "o", "hold", "reveal:close"),
        (2.0, "omar", "", "half", "flat", "down", "reveal:air"),
        (1.1, "omar", 2, "half", "flat", "down"),
        (0.75, "deb", 3, "wide", "flat", "hold", "zoom"),
        (1.95, "priya", 4, "half", "flat", "down"),
        (1.0, "jun", 5, "half", "flat", "down"),
        (1.0, "deb", "", "wide", "flat", "hold", "reveal:huddle"),
        (1.6, "jun", "", "wide", "flat", "down", "hiss:0.8"),
        (1.0, "brent", 6, "open", "flat", "point", "reveal:door"),
        (0.7, "priya", 7, "angry", "o", "point", "reveal:shh"),
        (1.0, "brent", "", "half", "flat", "down", "reveal:told"),
        (0.6, "omar", "", "wide", "flat", "down", "reveal:comes"),
        (1.4, "brent", 8, "wide", "flat", "down", "reveal:joined"),
        (1.3, "deb", "", "wide", "flat", "hold", "reveal:battery"),
        (1.2, "deb", "", "wide", "flat", "hold", "reveal:dead"),
        (1.2, "omar", "", "open", "flat", "down", "reveal:turn"),
        (1.0, "omar", "", "open", "flat", "down", "sting"),
    ),
    tail=2.2,
)
SKETCH = sketch.Sketch(SLUG, TITLE, (*(SPEAKERS[n] for n in NAMES), SHOW), LINES, tuple(BEATS), END, cast=collage.CAST)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": start, "eyes": eyes, "mouth": mouth, "arms": arms}


def _shows(cv, parent, name: str, place: Place, poses: list[dict], app: Appearance, **kw) -> object:
    x, y = place.transform()
    g = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=place.scale, scaleY=place.scale)
    collage.DRAWERS[name](
        cv, g, collage.parse_poses(poses, f"{name} at {app.start}"), app.end, (), enter=app.start, **kw
    )
    return g


def opening(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
    """Four people at a bus stop, facing front: nobody breathes, blinks or looks at anybody."""
    for name, place in WIDE.items():
        arms = "hold" if name == "deb" else "down"
        _shows(cv, parent, name, place, [_pose(0.0, "half", "flat", arms)], app, still=True)
    return WIDE["omar"].x, 1500.0


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """The stop in wide, Deb close, the huddle, Brent at his door, the phone alone, and the heads that turn."""
    close, air, huddle, door = (_at(beats, n) for n in ("close", "air", "huddle", "door"))
    shh, told, comes, joined = (_at(beats, n) for n in ("shh", "told", "comes", "joined"))
    battery, turn = _at(beats, "battery"), _at(beats, "turn")
    front = [_pose(0.0, "half", "flat", "down")]
    stop = Lineup(
        WIDE,
        {
            "omar": front,
            "priya": front,
            "jun": front,
            "deb": [_pose(0.0, "wide", "frown", "hold"), _pose(air, "side", "flat", "hold")],
        },
        ((STILL, close), (air, huddle)),
    )
    glued = [_pose(0.0, "wide", "flat", "down"), _pose(shh, "angry", "o", "down"), _pose(told, "wide", "flat", "down")]
    crowd = Lineup(
        HUDDLE,
        {name: [{**p, "arms": "hold" if name == "deb" else "down"} for p in glued] for name in HUDDLE},
        ((huddle, door), (shh, told), (comes, joined)),
    )
    ahead = [_pose(0.0, "wide", "flat", "down"), _pose(turn + TURN, "side", "flat", "down")]
    last = Lineup(
        TURNED,
        {"brent": ahead, "jun": ahead, "omar": ahead, "priya": ahead, "deb": [_pose(0.0, "wide", "frown", "hold")]},
        ((turn, end),),
    )

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start == joined:
            x, _ = JOINS.transform()
            him = _shows(cv, parent, "brent", JOINS, [dict(p) for p in app.poses], app, mouths=mouths.get("brent", ()))
            cv.keys(him, "x", [(joined, JOIN_FROM), (joined + JOIN, x)], kind="sine-out", hold=False, local=False)
            for name, place in HUDDLE.items():
                arms = "hold" if name == "deb" else "down"
                _shows(cv, parent, name, place, [_pose(0.0, "wide", "flat", arms)], app)
            return JOINS.x, 1400.0
        if battery <= app.start < turn:
            return 540.0, 1000.0
        for group in (stop, crowd, last):
            if group.staged(app):
                return group(cv, parent, app, mouths)
        return solo(cv, parent, app, mouths)

    return draw


def _bus(cv, parent, *, rolls_at: float | None = None) -> None:
    """The side of the bus, parked, or rolling in from ``rolls_at``."""
    g = cv.group(parent, cv.uid("g"), x=BUS_PARKED)
    if rolls_at is not None:
        cv.keys(
            g, "x", [(rolls_at, BUS_FROM), (rolls_at + BUS_ROLL, BUS_PARKED)], kind="sine-out", hold=False, local=False
        )
    cv.rect(g, 0.0, BUS_TOP, 1520.0, BUS_H, "#f2c14e", collage.INK, 7.0, radius=40.0)
    cv.rect(g, 0.0, BUS_TOP + 540.0, 1520.0, 44.0, "#c1121f")
    for i in range(5):
        cv.rect(g, 60.0 + i * 290.0, BUS_TOP + 90.0, 240.0, 300.0, "#9bd4e4", collage.INK, 6.0, radius=20.0)
    for x in (300.0, 1180.0):
        cv.ellipse(g, x - 95.0, BUS_TOP + BUS_H - 90.0, 190.0, 190.0, "#23202b", collage.INK, 6.0)


def dress(shot) -> None:
    """The phone at each size, the bus behind the huddle, and its open door round Brent."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    if app.start < STILL:
        collage_everyday.phone(cv, shot.front, screen=SCREEN_LIT, **HELD)
        return
    close, air, huddle, door = (_at(beats, n) for n in ("close", "air", "huddle", "door"))
    told = _at(beats, "told")
    battery, dead, turn = (_at(beats, n) for n in ("battery", "dead", "turn"))
    if app.start < close or air <= app.start < huddle:
        collage_everyday.phone(cv, shot.front, screen=SCREEN_LIT, **HELD)
    elif app.start == close:
        screen = collage_everyday.phone(cv, shot.front, screen=SCREEN_LIT, **CLOSE)
        for x in (84.0, 150.0):  # it is still playing
            cv.rect(screen, x, 170.0, 44.0, 130.0, collage.INK, radius=8.0)
    elif app.start == door or app.start == told:
        cv.rect(shot.back, 0.0, 780.0, cv.width, 1140.0, "#f2c14e")
        cv.rect(shot.back, 200.0, 800.0, 680.0, 1120.0, "#2b2d42", collage.INK, 8.0)
        cv.rect(shot.back, 880.0, 800.0, 120.0, 1120.0, "#9bd4e4", collage.INK, 8.0)
    elif app.start == battery:
        collage_everyday.battery_insert(cv, shot.front, **BATTERY, levels=((0.0, 1),), dead=dead)
    elif app.start >= turn:
        _bus(cv, shot.back)
        collage_everyday.phone(cv, shot.front, screen=collage_everyday.DEAD_SCREEN, **LAST)
    elif app.start >= huddle:
        rolling = app.start < door
        _bus(cv, shot.back, rolls_at=huddle + 0.4 if rolling else None)
        collage_everyday.phone(cv, shot.front, screen=SCREEN_LIT, **HUDDLED)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints={**TINTS, "phone": "#ffd6e0"},
    sets=dict.fromkeys(NAMES, STOP),
    dress=dress,
    cast=casting,
    bitrate=BITRATE,
    keep_signature=True,
    still=STILL,
    opening=opening,
)

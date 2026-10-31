"""It's Gone — the sketch as data: Rosa's internet is gone, all of it. Gary leaves a meeting and drives forty minutes,
presses one button, the light comes on green. She says it only works when he is here. He kisses her and goes. The door
shuts. The smile goes. She walks to the router, looks back at the door, and pulls the plug. Then, small again: Gary?
It's gone.

Collage style (ADR 0026): Rosa's helplessness is an act, seen once, without a sting. The reel opens moving (the
sp-hook_motion test's arm b): Rosa arrives in frame, already on the phone. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import camera, collage, collage_everyday, collage_sets
from srstudio.collage_group import Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 3102
SLUG = "its-gone"
TITLE = "It's Gone — Rosa and Gary (Collage)"
NAMES = ("rosa", "gary")
HOME = "living-room"
OFFICE = "boardroom"
DESCRIPTION = (
    "A Collage sketch: Rosa's internet is gone again, Gary drives forty minutes to press one button, and when the door "
    "shuts she walks to the router and pulls the plug."
)
ACCESSIBILITY = (
    "Paper cut-out characters: an old woman on the phone says the internet is gone. Her son answers from a meeting. "
    "He crouches at her router and presses a button, and its light turns green. He leaves and the door "
    "shuts. Her smile fades. She walks to the router, looks back at the door and pulls out the plug, and the light "
    "dies. She picks up the phone and says in a small voice that it is gone. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; a synthesized beep and door."
NOTE = "ElevenLabs premade voices Matilda and Chris at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB

ROSA, GARY = Place(280.0, 1920.0, 0.82), Place(850.0, 1960.0, 0.74)
ARRIVE = (360.0, 0.4)  # the opening: Rosa slides in from this far right, landing after this many seconds
WALK = 150.0  # how far she crosses to the router
BEND = 7.0  # degrees she leans to it
ROUTER = dict(x=600.0, y=1575.0, w=300.0)
PLUG = (832.0, 1583.0)  # the socket, where her hand ends
ELBOW = (520.0, 1490.0)
HELD = dict(w=150.0, h=270.0)
TABLE = "#a0683f"
CLOSE = 1.5  # the last shot's cut in

LINES = (
    Line("rosa", "The internet is gone."),
    Line("gary", "Gone where?"),
    Line("rosa", "All of it."),
    Line("gary", "I drove forty minutes. What did you touch?"),
    Line("rosa", "Nothing."),
    Line("gary", "There. It's fine."),
    Line("rosa", "It only works when you're here."),
    Line("gary", "Stop pressing things, Mom."),
    Line("rosa", "Gary? It's gone."),
)
BEATS, END = timed(
    LINES,
    (
        (1.35, "rosa", 0, "wide", "frown", "hold"),  # arriving, already on the phone
        (0.95, "gary", 1, "side", "flat", "hold"),
        (0.9, "rosa", 2, "wide", "frown", "hold"),
        (2.2, "gary", 3, "angry", "frown", "down", "reveal:home"),  # coat on, at the router, the light off
        (1.05, "rosa", 4, "up", "smile", "hold"),
        (0.9, "gary", "", "half", "flat", "point", "beep"),  # the button: the light comes on
        (1.2, "gary", 5, "open", "smile", "point"),
        (1.75, "rosa", 6, "open", "smile", "hold"),
        (1.45, "gary", 7, "open", "smile", "shrug"),
        (0.8, "gary", "", "closed", "smile", "down", "reveal:leave"),  # he goes
        (1.2, "rosa", "", "side", "smile", "down", "thud"),  # the door; she looks at it
        (0.9, "rosa", "", "side", "flat", "down"),  # the smile goes
        (1.8, "rosa", "", "half", "flat", "down", "reveal:walk"),  # slowly
        (0.9, "rosa", "", "side", "flat", "down"),  # back at the door
        (1.1, "rosa", "", "half", "flat", "down", "reveal:plug"),  # no sting
        (0.8, "rosa", "", "half", "flat", "hold", "reveal:close"),  # the phone
        (1.5, "rosa", 8, "sad", "frown", "hold"),
    ),
    tail=1.6,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def setting(beats: Sequence[Beat], app: Appearance) -> str:
    """Gary answers from a meeting; everything from his arrival is at hers."""
    return OFFICE if app.who == "gary" and app.start < _at(beats, "home") else HOME


def _place(cv, parent, who: str, app: Appearance, mouths: Mouths, place: Place):
    """``who`` in ``place`` on its own group, which the casting keys; drawn on the speaker's poses or a held one."""
    x, y = place.transform()
    g = cv.group(parent, cv.uid(f"home-{who}"), x=x, y=y, scaleX=place.scale, scaleY=place.scale)
    poses = app.poses if who == app.who else [{"start": 0.0, "eyes": "open", "mouth": "smile", "arms": "hold"}]
    collage.DRAWERS[who](cv, g, collage.parse_poses(poses, f"{who} at {app.start}"), app.end, (), enter=app.start,
                         mouths=mouths.get(who, ()))  # fmt: skip
    return g


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Each alone on the phone; the two of them at the router; then Rosa, who walks to it and leans over it."""
    home, leave, walk, close = (_at(beats, n) for n in ("home", "leave", "walk", "close"))
    plug = _at(beats, "plug")

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start < home:
            shift = -60.0 if app.who == "rosa" else 60.0
            moved = cv.group(parent, cv.uid("g"), x=shift)
            if app.start == 0.0:
                cv.keys(moved, "x", [(0.0, shift + ARRIVE[0]), (ARRIVE[1], shift)], kind="cubic-out", local=False)
            collage.DRAWERS[app.who](cv, moved, collage.parse_poses(app.poses, "the calls"), app.end, (),
                                     enter=app.start, mouths=mouths.get(app.who, ()))  # fmt: skip
            return collage.face(collage.LOOKS[app.who])
        rosa = _place(cv, parent, "rosa", app, mouths, ROSA)
        if app.start < leave + 0.5 and app.end > home:
            gary = _place(cv, parent, "gary", app, mouths, GARY)
            if app.start <= leave < app.end:
                x = GARY.transform()[0]
                cv.keys(gary, "x", [(leave, x), (leave + 0.8, x + 700.0)], kind="sine-in-out", local=False)
        if app.start <= walk < app.end:
            x = ROSA.transform()[0]
            cv.keys(rosa, "x", [(walk, x), (walk + 1.6, x + WALK)], kind="sine-in-out", local=False)
            cv.keys(rosa, "rotation", [(plug - 0.3, 0.0), (plug, BEND)], kind="sine-in-out", local=False)
            if close < app.end:
                pivot = collage_sets.zoom_pivot(HOME, (ROSA.x + WALK, 1120.0), CLOSE)
                camera.anchor(parent, *pivot, place=True)
                for channel in ("scaleX", "scaleY"):
                    cv.keys(parent, channel, [(0.0, 1.0), (close, CLOSE)], local=False)
        return ROSA.x, 1100.0

    return draw


def dress(shot) -> None:
    """The phones of the two calls, the router and what happens to its light, her hand on the plug, the last phone."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    home = _at(beats, "home")
    if app.start < home:
        collage_everyday.phone(cv, shot.front, 400.0, 1300.0, tilt=-8, **HELD)
        return
    press, plug = events(beats, "beep")[0][0], _at(beats, "plug")
    cv.rect(shot.front, ROUTER["x"] - 180.0, ROUTER["y"] + 42.0, 360.0, 400.0, TABLE, collage.INK, 7.0, radius=8.0)
    collage_everyday.router(cv, shot.front, light=((0.0, "off"), (press, "green"), (plug, "off")), unplugged=plug,
                            **ROUTER)  # fmt: skip
    if app.start <= plug < app.end:
        close = _at(beats, "close")
        reach = cv.group(shot.front, cv.uid("g"))
        cv.gate(reach, [(plug, close)])
        collage_everyday.arm(cv, reach, "rosa", ELBOW, PLUG)
        held = cv.group(shot.front, cv.uid("g"))
        cv.gate(held, [(close, app.end)])
        collage_everyday.arm(cv, held, "rosa", (460.0, 1480.0), (640.0, 1385.0))
        collage_everyday.phone(cv, held, 570.0, 1120.0, tilt=-6, **HELD)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"rosa": HOME, "gary": HOME},
    dress=dress,
    cast=casting,
    setting=setting,
    bitrate=BITRATE,
)

"""Book a Table — the sketch as data: Priya rehearses a two-line phone call like a title fight, with Deb in her corner,
and the first question off script ends her. Then the restaurant calls back.

Collage style (ADR 0026), the living room with a boxer's corner in it; the group shot of ADR 0036 for the two of them,
two heads above the sofa at the end. The restaurant is a voice through the phone (``Line.phone``). The reel opens on a
held first frame (the sp-hook_motion test's arm a). ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_everyday, collage_photo, collage_sets, collage_things
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, ZOOM_SCALE, CastDrawer, Staging, make_sketch, solo, timed
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 3131
SLUG = "book-a-table"
TITLE = "Book a Table — Priya and Deb (Collage)"
NAMES = ("priya", "deb", "feld")
ROOM = "living-room"
DESCRIPTION = (
    "A Collage sketch: two lines, one phone call, trained for like a title fight, and the restaurant asks a question "
    "that was not in the plan."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a living room set up as a boxer's corner, with ropes, a stool and a towel. A woman "
    "on the stool rehearses a phone booking with her trainer behind her, then calls. The restaurant asks one question "
    "and she ends the call saying love you, and throws the phone on the sofa. It rings. The last shot is two heads "
    "above the sofa, the phone on its seat. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Priya), Jessica (Deb) and Alice (the restaurant)."
NOTE = "ElevenLabs premade voices Sarah, Jessica and Alice at their natural pace; no reference-voice cloning."
BITRATE = 5_300_000  # two passes: a master under 20 MB, and a still opening that stays still

STILL = 0.45  # the held first frame: the sp-hook_motion test's arm a
PLACES = {"deb": Place(720.0, 1600.0, 0.66), "priya": Place(390.0, 1730.0, 0.74)}
HIDING = {"priya": Place(370.0, 1790.0, 0.72), "deb": Place(730.0, 1790.0, 0.72)}
STOOL = (390.0, 1700.0, 460.0)
PHONE = dict(x=305.0, y=1290.0, w=170.0, h=300.0)
TOWEL = dict(x=835.0, y=1215.0, w=150.0, h=340.0, tilt=-4.0)
POST = dict(x=1000.0, y=840.0, h=780.0)
BACKREST = (1270.0, "#588157", "#a3b18a", "#3a5a40")  # the sofa's back, its top and its seams, seen from the front
SEAT_PHONE = dict(x=470.0, y=1560.0, w=150.0, h=250.0)
SHAKE = 18.0  # px of a head saying no
THROW = 0.45  # seconds the phone is in the air
WOBBLE, WOBBLE_STEP = 12.0, 0.06  # a ringing phone's shake: px and seconds
RING_SHAKE = 0.8

LINES = (
    Line("deb", "Again."),
    Line("priya", "Table for two, Friday, seven."),
    Line("deb", "Shoulders down. You've got this."),
    Line("feld", "Hello, Bella Roma.", phone=True),
    Line("priya", "Table for two, Friday, seven."),
    Line("feld", "Inside or outside?", phone=True),
    Line("priya", "...Yes."),
    Line("feld", "Sorry?", phone=True),
    Line("priya", "Thanks. Love you."),
    Line("deb", "Love you?"),
    Line("feld", "Hi, it's Bella Roma. Love you too. Inside or outside?", phone=True),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "priya", "", "open", "frown", "hold"),  # the corner: stool, towel, ropes, a phone
        (0.85, "deb", 0, "angry", "flat", "hold"),
        (1.95, "priya", 1, "wide", "flat", "hold"),
        (1.75, "deb", 2, "open", "smile", "fist"),
        (0.6, "priya", "", "wide", "flat", "hold", "ding"),  # seconds out
        (1.1, "priya", "", "wide", "flat", "hold", "reveal:dial"),  # she dials; nobody breathes
        (1.5, "priya", 3, "wide", "flat", "hold"),
        (1.95, "priya", 4, "wide", "o", "hold"),
        (0.55, "deb", "", "angry", "grin", "fist", "reveal:fists"),
        (1.6, "priya", 5, "wide", "flat", "hold", "zoom"),
        (1.0, "priya", "", "wide", "flat", "hold"),
        (1.0, "deb", "", "sad", "frown", "down", "reveal:shake"),  # we never trained for this
        (0.7, "priya", 6, "wide", "flat", "hold"),
        (0.7, "priya", 7, "wide", "flat", "hold"),
        (1.3, "priya", 8, "open", "grin", "hold"),
        (2.3, "priya", "", "wide", "flat", "down", "reveal:throw"),
        (0.8, "deb", 9, "wide", "flat", "down"),
        (0.8, "deb", "", "wide", "o", "down", "ring"),
        (1.0, "priya", "", "wide", "flat", "down", "ring"),  # behind the sofa before the second ring
        (3.95, "priya", 10, "wide", "flat", "down"),
        (0.5, "priya", "", "wide", "flat", "down", "sting"),
    ),
    tail=0.6,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def _sofa_at(beats: Sequence[Beat]) -> float:
    """The cut to the sofa: the second ring."""
    return events(beats, "ring")[1][0]


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(start, 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """The two of them in the corner, the trainer's face changing with the fight; Deb alone for the no; heads last."""
    dial, fists, shake, throw = (_at(beats, n) for n in ("dial", "fists", "shake", "throw"))
    sofa, zoom = _sofa_at(beats), events(beats, "zoom")[0][0]
    corner = Lineup(
        PLACES,
        {
            "priya": [_pose(0, "wide", "flat", "hold")],
            "deb": [
                _pose(0, "open", "smile", "hold"),
                _pose(dial, "wide", "flat", "hold"),
                _pose(fists, "angry", "grin", "fist"),
                _pose(zoom, "wide", "flat", "hold"),
                _pose(shake, "sad", "frown", "down"),
                _pose(throw, "wide", "flat", "down"),
            ],
        },
        ((0.0, shake), (shake + 0.01, sofa)),
    )
    hiding = Lineup(
        HIDING, {"priya": [_pose(0, "wide", "flat", "down")], "deb": [_pose(0, "wide", "flat", "down")]}, ((sofa, end),)
    )

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start == shake:
            head = cv.group(parent, cv.uid("g"))
            steps = [(shake + 0.2 + i * 0.22, (SHAKE if i % 2 else -SHAKE) if 0 < i < 4 else 0.0) for i in range(5)]
            cv.keys(head, "x", steps, kind="sine-in-out", local=False)
            return solo(cv, head, app, mouths)
        if hiding.staged(app):
            return hiding(cv, parent, app, mouths)
        face = corner(cv, parent, app, mouths)
        if app.start <= zoom < app.end:
            return collage_sets.zoom_pivot(ROOM, face, ZOOM_SCALE)
        return face

    return draw


def _phone_in_hand(shot) -> None:
    """Her phone, up to the throw: it leaves the frame turning, towards the sofa out of shot."""
    cv, app, beats, front = shot.cv, shot.app, shot.beats, shot.front
    throw = _at(beats, "throw")
    phone = cv.group(front, cv.uid("g"))
    collage_everyday.phone(cv, phone, **PHONE)
    if app.start <= throw < app.end:
        start = throw + 0.2
        cv.keys(phone, "x", [(start, 0.0), (start + THROW, 1100.0)], kind="cubic-in", local=False)
        cv.keys(phone, "y", [(start, 0.0), (start + THROW, -420.0)], kind="sine-out", local=False)


def _sofa(shot) -> None:
    """The sofa between us and them, its back up to their noses; the phone on the seat, shaking through the rings."""
    cv, beats, front = shot.cv, shot.beats, shot.front
    top, colour, slab, seam = BACKREST
    collage_things.counter(cv, front, top, colour, slab, seam)
    collage_photo.sofa(cv, front)
    sofa = _sofa_at(beats)
    seat = cv.group(front, cv.uid("g"))
    steps = int(RING_SHAKE / WOBBLE_STEP)
    keys = [
        (round(sofa + i * WOBBLE_STEP, 6), (WOBBLE if i % 2 else -WOBBLE) if i < steps else 0.0)
        for i in range(steps + 1)
    ]
    cv.keys(seat, "x", keys, hold=False, local=False)
    collage_everyday.phone(cv, seat, **SEAT_PHONE, tilt=8.0)


def dress(shot) -> None:
    """The boxer's corner behind them and the stool under her; the sofa at the end."""
    cv, app, beats, back, front = shot.cv, shot.app, shot.beats, shot.back, shot.front
    if app.start >= _sofa_at(beats):
        _sofa(shot)
        return
    collage_things.ring_corner(cv, back, **POST)
    if app.start == _at(beats, "shake"):
        collage_things.towel(cv, front, **TOWEL)
        return
    collage_things.stool(cv, front, *STOOL)
    collage_things.towel(cv, front, **TOWEL)
    if app.start <= _at(beats, "throw"):
        _phone_in_hand(shot)


_FIRST = _pose(0, "open", "frown", "hold")
_HELD = Lineup(PLACES, {"priya": [_FIRST], "deb": [_pose(0, "open", "smile", "hold")]}, ((0.0, STILL),))
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
    opening=_HELD.held,
    bitrate=BITRATE,
    loudness="-14",
)

"""Two Weeks — the sketch as data: a contractor's "two weeks" has no end, and after a year he is more family than your
family. Omar looks at the hole in the wall. Two weeks, tops. Day 90, day 200, day 400: the hole never changes, and
everything else does, up to the chair at the head of the table.

Collage style (ADR 0026), the group frame of ADR 0036 held from cut to cut, the dining room with a hole in it. The
reel opens on the held image (STILL, L7 as adopted): nothing moves until Omar speaks. ElevenLabs premade voices,
lip-synced.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from srstudio import collage, collage_everyday, collage_home, collage_photo
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, appearances

SEED = 3320
SLUG = "two-weeks"
TITLE = "Two Weeks — Omar, Gary and Deb (Collage)"
NAMES = ("omar", "gary", "deb")
ROOM = "dining-room"
DESCRIPTION = (
    "A Collage sketch: a contractor's two weeks has no end, and after a year he is more family than your family."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a dining room with a hole in the wall. A contractor in a hard hat promises two "
    "weeks. Cards count day 90, day 200 and day 400. The hole never changes, but the window fills with snow, he comes "
    "to the table, his toothbrush appears, and the family photo now has him in it. He sits in the chair at the head "
    "of the table and unfolds his napkin. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; a synthesized sting."
NOTE = "ElevenLabs premade voices Daniel, Chris and Jessica at their natural pace; no reference-voice cloning."
BITRATE = 5_600_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
HOOK = "THE WALL: DAY 1"
HOOK_SECONDS = 3.0
DAY_SECONDS = 2.4
DAYS = ("DAY 90", "DAY 200", "DAY 400")
STILL = 0.45  # the held first frame

GARY = Place(860.0, 1860.0, 0.62)  # on the shelf's side, where a zoom onto him keeps the signature in frame
DEB = Place(220.0, 1860.0, 0.62)
STANDING = {"gary": GARY, "deb": DEB, "omar": Place(540.0, 1800.0, 0.72)}
SEATED = {"gary": GARY, "deb": DEB, "omar": Place(540.0, 1920.0, 0.72)}
TABLE = 1590
HOLE = (535.0, 900.0, 230.0, 300.0)
WINDOW = (110.0, 800.0, 300.0, 400.0)
FLAKES = ((0.15, 0.2), (0.4, 0.1), (0.7, 0.25), (0.25, 0.5), (0.6, 0.55), (0.85, 0.6), (0.3, 0.8), (0.75, 0.85))
PHOTO = {"x": 750.0, "y": 776.0, "width": 170.0, "tilt": 2.0, "room": ROOM}
FAMILY = {"gary": Place(380.0, 1800.0, 0.7), "deb": Place(700.0, 1800.0, 0.7)}
WITH_OMAR = {"gary": Place(230.0, 1800.0, 0.6), "deb": Place(540.0, 1800.0, 0.7), "omar": Place(800.0, 1800.0, 0.7)}
PHOTO_ARM = (858.0, 893.0, -56.0, 2.0)  # from Omar's shoulder in the print, round Deb
PHOTO_HAND = 0.24

LINES = (
    Line("omar", "Two weeks. Tops."),
    Line("gary", "Great."),
    Line("deb", "It's been three months."),
    Line("omar", "Two weeks."),
    Line("gary", "How's the wall?"),
    Line("omar", "Waiting on a part."),
    Line("deb", "From where?"),
    Line("omar", "Italy. Pass the salt."),
    Line("gary", "That's my chair."),
    Line("omar", "Two weeks."),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "gary", "", "open", "flat", "hold"),  # the held image: the hole, and a man looking at it
        (1.5, "omar", 0, "up", "smile", "hold"),
        (1.1, "gary", 1, "open", "smile", "down"),
        (1.7, "deb", 2, "angry", "frown", "hold"),
        (1.4, "omar", 3, "up", "smile", "down"),
        (1.3, "gary", 4, "open", "flat", "down"),
        (1.4, "omar", 5, "side", "smile", "hold"),
        (1.0, "deb", 6, "half", "flat", "hold"),
        (2.0, "omar", 7, "open", "smile", "hold"),
        (1.0, "deb", "", "half", "flat", "hold"),  # day 400: the photo, the toothbrush, the empty chair
        (1.2, "gary", "", "wide", "flat", "hold"),  # Omar sits down at the head of the table
        (1.4, "gary", 8, "angry", "frown", "point", "zoom"),
        (1.5, "omar", "", "side", "smile", "hold"),  # kind; he unfolds his napkin
        (1.2, "omar", 9, "open", "smile", "down", "sting"),
    ),
    tail=1.6,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(max(start, 0.0), 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def _said(beats: Sequence[Beat], line: int) -> float:
    return next(b.start for b in beats if b.line == line)


def _cuts(beats: Sequence[Beat]) -> tuple[float, float, float]:
    """Where days 90, 200 and 400 start."""
    return _said(beats, 2), _said(beats, 4), next(b.start for b in beats if b.who == "deb" and b.line is None)


def _day(beats: Sequence[Beat], at: float) -> int:
    """Which of the four days the shot at ``at`` is on: every cut falls between shots."""
    return sum(at >= cut for cut in _cuts(beats))


def _sits(beats: Sequence[Beat]) -> float:
    return next(b.start for b in beats if b.who == "gary" and b.line is None and b.start > _cuts(beats)[2])


def _unfolds(beats: Sequence[Beat]) -> float:
    return next(b.start for b in beats if b.who == "omar" and b.line is None)


def lineup(beats: Sequence[Beat], end: float, places: Mapping[str, Place] = STANDING) -> Lineup:
    """Everyone in one frame, always: Omar on his feet, or (with ``SEATED``) at the table."""
    ninety, two_hundred, four_hundred = _cuts(beats)
    reactions = {
        "gary": [
            _pose(0, "open", "smile", "hold"),
            _pose(ninety, "side", "flat", "down"),
            _pose(two_hundred, "open", "flat", "down"),
            _pose(_unfolds(beats), "wide", "frown", "hold"),
        ],
        "deb": [
            _pose(0, "open", "smile", "hold"),
            _pose(two_hundred, "half", "flat", "hold"),
            _pose(four_hundred, "side", "smile", "hold"),
        ],
        "omar": [
            _pose(0, "up", "smile", "hold"),
            _pose(ninety, "side", "smile", "down"),
            _pose(two_hundred, "open", "smile", "hold"),
        ],
    }
    spans = tuple((a.start, a.end) for a in appearances(beats, end))
    return Lineup(dict(places), {k: reactions[k] for k in places}, spans)


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """On his feet to day 200; at the table on 200; gone from the frame at the cut to 400; then in, and down."""
    standing, seated = lineup(beats, end), lineup(beats, end, SEATED)
    two_hundred, four_hundred = _cuts(beats)[1:]
    sits = _sits(beats)
    family = lineup(beats, end, {k: v for k, v in SEATED.items() if k != "omar"})

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start < two_hundred:
            return standing(cv, parent, app, mouths)
        if not four_hundred <= app.start <= sits:
            return seated(cv, parent, app, mouths)
        face = family(cv, parent, app, mouths)
        if app.end > sits:
            walk = cv.group(parent, cv.uid("g"))
            cv.keys(walk, "x", [(sits, 760.0), (sits + 0.55, 0.0)], kind="cubic-out", local=False)
            cv.keys(walk, "y", [(sits + 0.55, -120.0), (sits + 1.0, 0.0)], kind="sine-in-out", local=False)
            place = SEATED["omar"]
            x, y = place.transform()
            g = cv.group(walk, cv.uid("g"), x=x, y=y, scaleX=place.scale, scaleY=place.scale)
            poses = collage.parse_poses(seated.poses("omar", app), "Omar sitting down")
            collage.DRAWERS["omar"](cv, g, poses, app.end, (), enter=app.start, mouths=mouths.get("omar", ()))
        return face

    return draw


def _photo(cv, back, day: int) -> None:
    """The family photo on the wall, which by day 400 has Omar in it, an arm round Deb."""
    if day < 3:
        poses = {"gary": ("open", "smile", "down"), "deb": ("open", "smile", "down")}
        collage_photo.print_photo(cv, back, FAMILY, poses, **PHOTO)
        return
    poses = {k: ("open", "grin" if k == "omar" else "smile", "down") for k in WITH_OMAR}
    collage_photo.print_photo(cv, back, WITH_OMAR, poses, **PHOTO)
    k = PHOTO_HAND
    arm = cv.group(back, cv.uid("g"), x=PHOTO_ARM[0], y=PHOTO_ARM[1], scaleX=k, scaleY=k)
    collage_everyday.arm(cv, arm, "omar", (0.0, 0.0), (PHOTO_ARM[2] / k, PHOTO_ARM[3] / k))


def _table(cv, front, day: int) -> None:
    cv.rect(front, 0, TABLE, cv.width, cv.height - TABLE, "#f4ecd8", collage.INK, 4)
    if day < 2:
        return
    for x, w, dish in ((200.0, 300.0, "salad"), (540.0, 340.0, "steak"), (880.0, 300.0, "sauce")):
        collage_home.plate(cv, front, x, 1740, w, dish)
    collage_everyday.salt_shaker(cv, front, 720, 1680, 120)


def _napkin(cv, front, beats: Sequence[Beat], app: Appearance, day: int) -> None:
    """Tucked in on day 200; on day 400 it opens, on the hold after Gary's line."""
    if day == 2:
        collage_home.napkin(cv, front, 540, 1440, 190)
    unfolds = _unfolds(beats)
    if day == 3 and app.who == "omar":
        g = cv.group(front, cv.uid("g"), x=540.0)
        cv.keys(g, "scaleX", [(unfolds + 0.3, 0.2), (unfolds + 1.0, 1.0)], kind="sine-in-out", local=False)
        collage_home.napkin(cv, g, 0, 1440, 190)


def dress(shot) -> None:
    """The hole, always and the same; everything else by the day."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    day = _day(beats, app.start)
    collage_home.wall_hole(cv, shot.back, *HOLE)
    if day == 2:
        collage_home.snowy_window(cv, shot.back, *WINDOW, flakes=FLAKES)
    _photo(cv, shot.back, day)
    if day == 3:
        collage_home.chair_back(cv, shot.back, 540, 1060, 420, 640)
        collage_home.toothbrush_mug(cv, shot.back, 960, 1120, 130)
    if day == 2:
        collage_home.hard_hat(cv, shot.back, 680, 1120, 170)  # off his head, on the sideboard
    if day < 2:
        collage_home.hard_hat(cv, shot.front, 540, 1060, 330)
    _table(cv, shot.front, day)
    _napkin(cv, shot.front, beats, app, day)
    if app.start < HOOK_SECONDS:
        collage_home.hook_card(cv, shot.front, HOOK, ROOM, shot.measure, start=0.0, seconds=HOOK_SECONDS)
    for text, cut in zip(DAYS, _cuts(beats), strict=True):
        if app.start < cut + DAY_SECONDS and cut < app.end:
            collage_home.hook_card(cv, shot.front, text, ROOM, shot.measure, start=cut, seconds=DAY_SECONDS)


CAST = lineup(BEATS, END)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"omar": ROOM, "gary": ROOM, "deb": ROOM},
    dress=dress,
    cast=casting,
    bleed=True,
    still=STILL,
    opening=CAST.held,
    bitrate=BITRATE,
    keep_signature=True,
    loudness="-14",
)

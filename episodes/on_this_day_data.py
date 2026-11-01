"""On This Day — the sketch as data: Priya casts one photo to the big TV with her new boyfriend on the sofa, and her
phone makes a tender film of her ex, unprompted. It only gets better, and Jun takes it worst of all.

Collage style (ADR 0026), the group of ADR 0036. Omar is on the TV only, the same drawing and name as in two-weeks,
and every shot of the film is invented. The piano is the only music, and it is the film's. The reel moves from its
first second (L7): Priya is already stabbing her phone at the TV. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_everyday, collage_home, collage_photo, foley
from srstudio.collage_group import Lineup, Place
from srstudio.collage_home import Screen
from srstudio.collage_sketch import TINTS, CastDrawer, Sound, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, appearances, events

SEED = 3302
SLUG = "on-this-day"
TITLE = "On This Day — Priya, Jun and Rosa (Collage)"
NAMES = ("priya", "jun", "rosa")
ROOM = "living-room"
DESCRIPTION = (
    "A Collage sketch: Priya casts one photo to the TV, and her phone makes a tender little film of her ex, who "
    "turns out to be very hard not to like."
)
ACCESSIBILITY = (
    "Paper cut-out characters on a sofa in a living room: a woman stabs her phone at the TV while her boyfriend and "
    "an old woman watch. The TV plays a photo film of a smiling man with a moustache: on a beach with her, in a red "
    "kayak, in a hard hat among children's desks, and carrying the old woman up a staircase under the title TWO "
    "YEARS OF JOY. The boyfriend cries. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; a synthesized piano in the film."
NOTE = "ElevenLabs premade voices Sarah, Will and Matilda at their natural pace; no reference-voice cloning."
BITRATE = 5_600_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
HOOK = "CASTING TO TV"
HOOK_SECONDS = 3.0

PLACES = {"priya": Place(240.0, 1800.0, 0.62), "jun": Place(570.0, 1800.0, 0.6), "rosa": Place(870.0, 1800.0, 0.58)}
TV = (40.0, 800.0, 1000.0)  # under the shelf, which stays in every shot
STRIP = 92  # the height of the film's title strip

LINES = (
    Line("priya", "One sec, it's just one photo."),
    Line("rosa", "Omar!"),
    Line("jun", "Who's Omar?"),
    Line("priya", "Nobody! It picks them itself!"),
    Line("rosa", "He fixed my sink."),
    Line("jun", "Is he building a school?"),
    Line("priya", "Make it stop!"),
    Line("jun", "You look so happy."),
    Line("rosa", "Play it again."),
    Line("jun", "Is he seeing anyone?", gain=-4.0),
)
OMAR, WHO, NOBODY, SINK, SCHOOL, STOP, HAPPY, AGAIN, SEEING = range(1, 10)
BEATS, END = timed(
    LINES,
    (
        (1.9, "priya", 0, "wide", "smile", "point"),  # already jabbing the phone at the TV
        (1.5, "kai", "", "open", "flat", "down", "reveal:beach"),  # the TV: nobody asked for this
        (0.9, "rosa", OMAR, "wide", "grin", "hold"),
        (1.1, "jun", WHO, "side", "flat", "down"),
        (2.0, "priya", NOBODY, "wide", "grin", "shrug"),
        (0.9, "kai", "", "open", "flat", "down", "reveal:kayak"),
        (0.9, "kai", "", "open", "flat", "down", "reveal:school"),
        (1.3, "rosa", SINK, "closed", "smile", "hold"),
        (1.5, "kai", SCHOOL, "open", "flat", "down"),  # Jun, off, at the TV
        (1.0, "priya", STOP, "wide", "o", "point", "zoom"),
        (0.8, "kai", "", "open", "flat", "down", "reveal:stairs"),  # the piano swells
        (0.9, "kai", "", "open", "flat", "down", "sting"),  # the title lands
        (2.2, "jun", "", "sad", "frown", "down"),  # wet-eyed
        (1.3, "jun", HAPPY, "sad", "frown", "down"),
        (1.0, "rosa", AGAIN, "closed", "smile", "hold"),
        (0.7, "priya", "", "angry", "flat", "point", "beep"),  # stabs at the phone; the piano stops
        (1.6, "jun", SEEING, "side", "flat", "down"),  # quietly, not looking at her
    ),
    tail=2.3,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(max(start, 0.0), 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def _reveal(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def lineup(beats: Sequence[Beat], end: float) -> Lineup:
    """The sofa in every shot but the TV's and Jun's own close, the listeners on the project clock."""
    beach, stairs = _reveal(beats, "beach"), _reveal(beats, "stairs")
    who = next(b.start for b in beats if b.line == WHO)
    school = _reveal(beats, "school")
    reactions = {
        "priya": [_pose(0, "wide", "smile", "point"), _pose(beach, "side", "frown", "hold")],
        "jun": [
            _pose(0, "open", "smile", "down"),
            _pose(beach, "side", "flat", "down"),
            _pose(school, "wide", "o", "down"),
            _pose(stairs, "sad", "frown", "down"),
        ],
        "rosa": [_pose(0, "open", "smile", "hold"), _pose(who, "up", "smile", "hold")],
    }
    close = next(b.start for b in beats if b.who == "jun" and b.start > stairs)
    last = next(b.start for b in beats if b.line == SEEING)
    spans = tuple(
        (a.start, a.end)
        for a in appearances(beats, end)
        if a.who != "kai" and not (a.who == "jun" and a.start in (close, last))
    )
    return Lineup(PLACES, reactions, spans)


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """The group on the sofa, Jun alone when it reaches him, and nobody in front of the TV."""
    group = lineup(beats, end)

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.who == "kai":
            return collage.CX, collage.HEAD_Y
        return group(cv, parent, app, mouths) if group.staged(app) else solo(cv, parent, app, mouths)

    return draw


def _bust(cv, parent, who: str, x: float, base: float, k: float, eyes: str, mouth: str, arms: str, app: Appearance):
    """A held drawing of ``who`` in the film, through :data:`srstudio.collage.DRAWERS`, so the part is the one on
    record: its centre line at ``x``, its cut-off bottom on ``base`` of the screen."""
    g = cv.group(parent, cv.uid("g"), x=x - collage.CX * k, y=base - 1920.0 * k, scaleX=k, scaleY=k)
    poses = collage.parse_poses([_pose(0, eyes, mouth, arms)], f"{who} in the film")
    collage.DRAWERS[who](cv, g, poses, app.end, (), enter=app.start, still=True)
    return g


def _strip(cv, parent, tv: Screen, text: str, size: int) -> None:
    cv.rect(parent, 0, tv.h - STRIP, tv.w, STRIP, "#1b1621e6")
    cv.text(parent, cv.uid("film"), text, 0, round(tv.h - STRIP), round(tv.w), STRIP, size, color="#fff3b0")


def _beach(cv, g, tv: Screen, app: Appearance) -> None:
    cv.rect(g, 0, 0, tv.w, tv.h * 0.55, cv.grad("film-beach", [(0, "#8ecae6"), (1, "#ffe8a3")], (0, 0, 0, 1)))
    cv.rect(g, 0, tv.h * 0.45, tv.w, tv.h * 0.2, "#219ebc")
    cv.rect(g, 0, tv.h * 0.6, tv.w, tv.h * 0.4, "#f2d9a0")
    cv.ellipse(g, 730, 40, 130, 130, "#ffd166")
    _bust(cv, g, "omar", 340.0, tv.h, 0.5, "closed", "grin", "down", app)
    _bust(cv, g, "priya", 640.0, tv.h, 0.47, "closed", "grin", "down", app)
    _strip(cv, g, tv, "ON THIS DAY: YOU AND OMAR", 54)


def _on_the_water(cv, g, tv: Screen, app: Appearance) -> None:
    cv.rect(g, 0, 0, tv.w, tv.h * 0.5, cv.grad("film-lake", [(0, "#a2d2ff"), (1, "#e0f2ff")], (0, 0, 0, 1)))
    cv.path(g, f"M0 {tv.h * 0.5:g} L220 150 L420 {tv.h * 0.5:g} L640 110 L956 {tv.h * 0.5:g} Z", "#588157")
    cv.rect(g, 0, tv.h * 0.5, tv.w, tv.h * 0.5, "#2a7f9e")
    _bust(cv, g, "omar", 470.0, tv.h * 0.92, 0.4, "closed", "grin", "down", app)
    collage_home.kayak(cv, g, 470, tv.h * 0.8, 820, -3)


def _school(cv, g, tv: Screen, app: Appearance) -> None:
    cv.rect(g, 0, 0, tv.w, tv.h, "#d9d2c5")
    cv.rect(g, 0, tv.h * 0.72, tv.w, tv.h * 0.28, "#a98467")
    for x in (120, 720):
        cv.rect(g, x, 0, 26, tv.h * 0.72, "#b08355", collage.INK, 3)
    cx, base, k = 470.0, tv.h + 10.0, 0.42
    _bust(cv, g, "omar", cx, base, k, "closed", "grin", "down", app)
    collage_home.hard_hat(cv, g, cx, base - (1920.0 - collage.HEAD_Y + collage.HEAD_RY * 0.42) * k, 290)
    for x, y in ((120, tv.h - 16), (820, tv.h - 16), (250, tv.h - 66), (690, tv.h - 66)):
        collage_home.school_desk(cv, g, x, y, 170)


def _stairs(cv, g, tv: Screen, app: Appearance) -> None:
    cv.rect(g, 0, 0, tv.w, tv.h, cv.grad("film-stairs", [(0, "#ffd6a5"), (1, "#ffadad")], (0, 0, 0, 1)))
    collage_home.staircase(cv, g, 150, tv.h, 800, 400)
    k = 0.46
    _bust(cv, g, "omar", 470.0, tv.h - 20.0, k, "closed", "grin", "down", app)
    held = cv.group(g, cv.uid("g"), x=400.0, y=tv.h - 226.0, rotation=-78.0)
    look = collage.LOOKS["rosa"]
    for dx in (-52, 28):  # her legs over his arm, so the bust's cut edge is the hem of her skirt
        cv.rect(held, dx, 300, 26, 130, look.skin, collage.INK, 3)
        cv.rect(held, dx - 8, 420, 44, 26, "#23202b", collage.INK, 3)
    cv.rect(held, -96, 214, 192, 100, look.top, collage.INK, 4, radius=14)
    _bust(cv, held, "rosa", 0.0, 240.0, 0.38, "closed", "grin", "hold", app)


FILM = {"beach": _beach, "kayak": _on_the_water, "school": _school, "stairs": _stairs}


def film(cv, tv: Screen, app: Appearance, beats: Sequence[Beat], end: float) -> None:
    """The slides this shot sees, each up from its reveal to the next, each pushing in slowly as a phone's film does."""
    cuts = [(t, what) for t, what in events(beats, "reveal")]
    for i, (at, what) in enumerate(cuts):
        to = cuts[i + 1][0] if i + 1 < len(cuts) else end
        if not (at < app.end and to > app.start):
            continue
        slide = cv.group(tv.image, cv.uid("g"))
        cv.gate(slide, [(at, to)])
        push = cv.group(slide, cv.uid("g"))
        for prop, start, stop in (
            ("scaleX", 1.0, 1.06),
            ("scaleY", 1.0, 1.06),
            ("x", 0.0, -0.03 * tv.w),
            ("y", 0.0, -0.03 * tv.h),
        ):
            cv.keys(push, prop, [(at, start), (to, stop)], hold=False, local=False)
        FILM[what](cv, push, tv, app)
        if what == "stairs":
            title = cv.group(slide, cv.uid("g"))
            cv.gate(title, [(events(beats, "sting")[0][0], to)])
            _strip(cv, title, tv, "TWO YEARS OF JOY", 62)


def _phone(cv, front, app: Appearance, beats: Sequence[Beat]) -> None:
    """Priya's phone, jabbed at the TV in the first second and again when she tries to kill the film."""
    stab = events(beats, "beep")[0][0]
    hand = cv.group(front, cv.uid("g"))
    jabs = [(0.0, 0.0), (0.2, -44.0), (0.4, 0.0), (0.6, -44.0), (0.8, 0.0)]
    jabs += [(stab + d, y) for d, y in ((0.0, 0.0), (0.12, -44.0), (0.24, 0.0), (0.36, -44.0), (0.48, 0.0))]
    cv.keys(hand, "y", jabs, hold=False, local=False)
    collage_everyday.phone(cv, hand, 330, 1440, 120, 214, tilt=10.0)


def _remote(cv, front, app: Appearance, beats: Sequence[Beat]) -> None:
    """Priya's arm from the sofa, off the frame's foot, pointing her phone at the TV the whole film long."""
    hand = cv.group(front, cv.uid("g"))
    cv.keys(hand, "y", [(app.start, 26.0), (app.start + 0.3, 0.0)], kind="cubic-out", local=False)
    collage_everyday.arm(cv, hand, "priya", (120.0, 1990.0), (420.0, 1690.0))
    collage_everyday.phone(cv, hand, 360, 1500, 130, 230, tilt=8.0)


def dress(shot) -> None:
    """The TV and its film; the sofa, and Priya's phone in her group shots; Jun's tear; the hook while it is up."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    if app.who == "kai":
        tv = collage_home.wall_tv(cv, shot.back, *TV)
        cv.rect(shot.back, 0, 1410, cv.width, 170, "#7f5539", collage.INK, 4)
        for x in (270, 810):
            cv.ellipse(shot.back, x - 15, 1480, 30, 30, "#ffca3a", collage.INK, 3)
        film(cv, tv, app, beats, shot.end)
        _remote(cv, shot.front, app, beats)
    elif app.who == "jun" and app.start > _reveal(beats, "stairs"):
        drop = cv.group(shot.front, cv.uid("g"))
        cv.ellipse(drop, 596, 1170, 26, 40, "#a2d2ff", collage.INK, 3)
        cv.keys(drop, "y", [(app.start, 0.0), (app.end, 150.0)], hold=False, local=False)
    else:
        collage_photo.sofa(cv, shot.front)
        _phone(cv, shot.front, app, beats)
    if app.start < HOOK_SECONDS:
        collage_home.hook_card(cv, shot.front, HOOK, ROOM, shot.measure, start=0.0, seconds=HOOK_SECONDS)


def sounds(beats: Sequence[Beat], end: float) -> Sequence[Sound]:
    """The film's piano: a small arpeggio from the first slide, a swell on the staircase, dead on Priya's stab."""
    beach, stairs = _reveal(beats, "beach"), _reveal(beats, "stairs")
    stab = events(beats, "beep")[0][0] - RING
    soft = int((stairs - beach) / SOFT_STEP)
    swell = int((stab - stairs) / SWELL_STEP)
    out = []
    quiet = [SOFT[i % len(SOFT)] for i in range(soft)]
    loud = [SWELL[i % len(SWELL)] for i in range(swell)]
    for note, at in foley.phrase(quiet, beach, SOFT_STEP).items():
        out.append(Sound(f"piano-{note}", foley.piano(note, ring=RING), at, -17.0))
    for note, at in foley.phrase(loud, stairs, SWELL_STEP).items():
        out.append(Sound(f"swell-{note}", foley.piano(note, ring=RING), at, -9.0))
    return out


SOFT, SOFT_STEP = ("C4", "G4", "E4", "G4"), 0.6
SWELL, SWELL_STEP = ("C4", "E4", "G4", "C5", "E5", "G5", "E5", "C5"), 0.36
RING = 1.1  # short enough that the last note has died when Priya's stab lands

STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"priya": ROOM, "jun": ROOM, "rosa": ROOM, "kai": ROOM},
    dress=dress,
    cast=casting,
    bleed=True,
    bitrate=BITRATE,
    keep_signature=True,
    sounds=sounds,
    loudness="-14",
)

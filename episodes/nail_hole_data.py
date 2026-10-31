"""Nail Hole — the sketch as data: an eye behind a huge magnifying glass, then a tiny hole in a wall. Aha. Feld has
been in the flat four seconds; the heating took her eleven months. Two hundred dollars, plus paint, plus filler, plus
her time, which is exactly the deposit. It always is. Deb leaves the keys and goes. Alone, Feld raises her phone to
the hole, tenderly: new listing, charming, original features. Gallery wall. Two hundred more a month.

Collage style (ADR 0026): what she charged Deb for, she sells as a feature. The reel opens moving (the sp-hook_motion
test's arm b): the glass is already traveling on frame one. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_everyday, collage_sets
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 3118
SLUG = "nail-hole"
TITLE = "Nail Hole — Feld and Deb (Collage)"
NAMES = ("feld", "deb")
FLAT = "living-room"
DESCRIPTION = (
    "A Collage sketch: a landlord who took eleven months over the heating finds a nail hole in four seconds, bills "
    "the exact deposit, and lists the hole as an original feature."
)
ACCESSIBILITY = (
    "Paper cut-out characters: a huge magnifying glass with an eye behind it, then a tiny hole in a wall. A landlord "
    "and a tenant in an empty flat with boxes. The tenant says the heating took eleven months. Bills drop in one at "
    "a time until they equal the deposit. The tenant leaves the keys and goes. The landlord photographs the hole "
    "and lists it as a charming original feature for two hundred more a month. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; a synthesized camera flash and door."
NOTE = "ElevenLabs premade voices Alice and Jessica at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB

GLASS = dict(size=620.0, tilt=-30.0)
GLASS_FROM, GLASS_AT = (1180.0, 1780.0), (540.0, 1100.0)
GLASS_FLIGHT = 0.95  # the seconds it travels from frame one
HOLE = (540.0, 1100.0)
FELD, DEB = Place(300.0, 1920.0, 0.74), Place(820.0, 1960.0, 0.7)
BILLS = (("$200", 300.0, 960.0), ("PAINT", 610.0, 900.0), ("FILLER", 830.0, 1040.0), ("MY TIME", 520.0, 1120.0))
MORE = (0.0, 0.85, 1.75)  # how far into her line "plus paint", "plus filler" and "plus my time" fall
LISTING = dict(x=120.0, y=500.0, w=840.0, h=1260.0)
CARD = "#c9a26a"

LINES = (
    Line("feld", "Aha."),
    Line("deb", "You've been here four seconds."),
    Line("feld", "A nail hole."),
    Line("deb", "The heating took you eleven months."),
    Line("feld", "Two hundred dollars."),
    Line("deb", "It's a tiny hole!"),
    Line("feld", "Plus paint. Plus filler. Plus my time."),
    Line("deb", "That's exactly my deposit."),
    Line("feld", "It always is."),
    Line("feld", "New listing. Charming. Original features."),
    Line("feld", "Gallery wall. Two hundred more a month."),
)
BEATS, END = timed(
    LINES,
    (
        (1.1, "feld", "", "open", "flat", "down"),  # the eye, the glass arriving
        (0.7, "feld", 0, "open", "smug", "down"),
        (1.45, "deb", 1, "angry", "flat", "hold", "reveal:wide"),
        (1.0, "feld", 2, "half", "smug", "hold"),
        (1.6, "deb", 3, "angry", "frown", "hold"),
        (1.3, "feld", 4, "open", "smile", "hold", "reveal:bill"),
        (1.15, "deb", 5, "wide", "frown", "shrug"),
        (2.8, "feld", 6, "open", "smile", "point", "reveal:more"),
        (1.4, "deb", 7, "angry", "flat", "hold"),
        (1.0, "feld", 8, "half", "smug", "hold"),
        (1.0, "deb", "", "sad", "flat", "down", "reveal:leave"),
        (1.3, "feld", "", "side", "flat", "hold", "thud"),  # alone
        (0.5, "feld", "", "half", "smile", "point", "flash"),
        (2.7, "feld", 9, "half", "smile", "point"),
        (0.5, "feld", "", "half", "grin", "point"),  # with love
        (2.2, "feld", 10, "half", "smug", "point"),
        (1.4, "feld", "", "half", "smile", "point", "reveal:listing"),
    ),
    tail=0.3,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": start, "eyes": eyes, "mouth": mouth, "arms": arms}


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Nobody behind the glass; the two of them in the flat; then Feld, close, alone with the hole."""
    wide, leave = _at(beats, "wide"), _at(beats, "leave")
    alone = events(beats, "thud")[0][0]
    flat = Lineup(
        {"feld": FELD, "deb": DEB},
        {
            "feld": [_pose(0.0, "half", "smug", "hold")],
            "deb": [_pose(0.0, "angry", "flat", "hold"), _pose(leave, "sad", "flat", "down")],
        },
        ((wide, alone),),
    )

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start < wide:
            return HOLE
        if app.start == leave:
            x, y = DEB.transform()
            feld = cv.group(
                parent, cv.uid("g"), x=FELD.transform()[0], y=FELD.transform()[1], scaleX=FELD.scale, scaleY=FELD.scale
            )
            collage.DRAWERS["feld"](
                cv,
                feld,
                collage.parse_poses([_pose(0.0, "half", "smug", "hold")], "feld stays"),
                app.end,
                (),
                enter=app.start,
            )
            deb = cv.group(parent, cv.uid("g"), x=x, y=y, scaleX=DEB.scale, scaleY=DEB.scale)
            cv.keys(deb, "x", [(leave + 0.3, x), (leave + 0.9, x + 760.0)], kind="sine-in", hold=False, local=False)
            collage.DRAWERS["deb"](cv, deb, collage.parse_poses(app.poses, "deb goes"), app.end, (), enter=app.start)
            return DEB.x, 1200.0
        if app.start < alone:
            return flat(cv, parent, app, mouths)
        return solo(cv, parent, app, mouths)

    return draw


def _gated(cv, parent, a: float, b: float):
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(a, b)])
    return g


def _eye(cv, parent) -> None:
    """Hers, close, behind the lens."""
    cv.ellipse(parent, HOLE[0] - 230.0, HOLE[1] - 150.0, 460.0, 300.0, "#fffaf0", collage.INK, 8.0)
    cv.ellipse(parent, HOLE[0] - 100.0, HOLE[1] - 100.0, 200.0, 200.0, "#5b3a29", collage.INK, 6.0)
    cv.ellipse(parent, HOLE[0] - 50.0, HOLE[1] - 50.0, 100.0, 100.0, "#14141c")
    cv.ellipse(parent, HOLE[0] + 10.0, HOLE[1] - 44.0, 34.0, 34.0, "#ffffff")


def _boxes(cv, parent) -> None:
    for x, y, w, h in ((30.0, 1620.0, 260.0, 300.0), (240.0, 1700.0, 230.0, 220.0), (70.0, 1420.0, 190.0, 210.0)):
        cv.rect(parent, x, y, w, h, CARD, collage.INK, 6.0)
        cv.rect(parent, x + w / 2 - 14.0, y, 28.0, h, "#e8d3a8")


def _keys(cv, parent, t: float) -> None:
    g = _gated(cv, parent, t, 86400.0)
    cv.ellipse(g, 640.0, 1800.0, 46.0, 46.0, "#ffffff00", "#d4a017", 10.0)
    cv.rect(g, 680.0, 1816.0, 90.0, 14.0, "#d4a017", collage.INK, 3.0)


def _listing(cv, parent) -> None:
    """The phone, the hole in its photo, and the arrow."""
    screen = collage_everyday.phone(cv, parent, **LISTING)
    w = LISTING["w"] - 2 * collage_everyday.BEZEL
    cv.rect(screen, 0.0, 0.0, w, 620.0, "#ffe5d9")
    cv.ellipse(screen, w / 2 - 12.0, 300.0, 24.0, 24.0, "#2b2d42")
    cv.path(screen, f"M{w - 80} 90 L{w / 2 + 40} 280", stroke="#ef3340", sw=26)
    cv.path(screen, f"M{w / 2 + 30} 200 L{w / 2 + 22} 300 L{w / 2 + 120} 290", stroke="#ef3340", sw=26)
    collage_sets.sign(cv, screen, "ORIGINAL FEATURES", 34, 650, 720, 130, size=64)
    collage_sets.sign(cv, screen, "GALLERY WALL", 34, 800, 720, 130, size=64)
    collage_sets.sign(cv, screen, "+ $200 A MONTH", 34, 950, 720, 130, size=64, color="#c1121f")


def dress(shot) -> None:
    """The glass, the eye and the hole; the door, boxes, bills and keys of the flat; her phone, and the listing."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    wide, bill, more, leave, listing = (_at(beats, n) for n in ("wide", "bill", "more", "leave", "listing"))
    alone = events(beats, "thud")[0][0]
    if app.start < wide:
        cv.ellipse(shot.back, HOLE[0] - 16.0, HOLE[1] - 16.0, 32.0, 32.0, "#2b2d42")
        eye = _gated(cv, shot.front, 0.0, GLASS_FLIGHT + 0.15)
        glass = collage_everyday.magnifying_glass(cv, shot.front, x=GLASS_AT[0], y=GLASS_AT[1], **GLASS)
        _eye(cv, eye)
        for node in (eye, glass):
            base = (0.0, 0.0) if node is eye else GLASS_AT
            frm = (GLASS_FROM[0] - GLASS_AT[0] + base[0], GLASS_FROM[1] - GLASS_AT[1] + base[1])
            cv.keys(node, "x", [(0.0, frm[0]), (GLASS_FLIGHT, base[0])], kind="cubic-out", hold=False, local=False)
            cv.keys(node, "y", [(0.0, frm[1]), (GLASS_FLIGHT, base[1])], kind="cubic-out", hold=False, local=False)
        return
    if app.start < alone:
        cv.rect(shot.back, 590.0, 820.0, 470.0, 1100.0, "#5b4636", collage.INK, 8.0)
        cv.rect(shot.back, 620.0, 850.0, 410.0, 1070.0, "#2b2d42")
        cv.ellipse(shot.back, 470.0, 1200.0, 18.0, 18.0, "#2b2d42")
        _boxes(cv, shot.front)
        times = (bill, *(more + d for d in MORE))
        for (text, x, y), t in zip(BILLS, times, strict=True):
            if t < app.end:
                slip = collage_everyday.bill(cv, shot.front, text, x, y, w=280.0, h=190.0, size=50)
                cv.keys(slip, "y", [(t - 0.01, -300.0), (t + 0.3, y)], kind="cubic-out", hold=False, local=False)
        if app.end > leave:
            _keys(cv, shot.front, leave + 0.3)
        return
    if app.start <= listing < app.end:
        phone = _gated(cv, shot.front, alone + 0.9, listing)
        collage_everyday.phone(cv, phone, 730.0, 1000.0, 190.0, 340.0, tilt=8)
        _listing(cv, _gated(cv, shot.front, listing, app.end))


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"feld": FLAT, "deb": FLAT},
    dress=dress,
    cast=casting,
    bitrate=BITRATE,
)

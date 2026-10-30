"""Anything's Fine — the sketch as data: "What do you want for dinner?" "Anything's fine." Then Gary refuses Thai,
pizza (they had it in March), tacos, sushi, soup and the place, swatting each one out of the air. The delivery app
asks if they are still there, the clock jumps to 11:40, Priya says she will choose, and Gary refuses that too before
she has said anything. In bed, in the dark, they eat dry cereal from the box. "This is nice." "...I wanted Thai."

Collage style (ADR 0026), cast cards of ADR 0036: Priya's patience is graded, Gary performs a refusal nobody asked
for. Two closes across the sofa, then one two-shot in bed; the reel opens moving (the sp-hook_motion test's arm b):
Priya leans in, already asking. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_everyday, collage_sets
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, ZOOM_SCALE, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 4102
SLUG = "anythings-fine"
TITLE = "Anything's Fine — Gary and Priya (Collage)"
NAMES = ("gary", "priya")
SOFA = "living-room"
BED = "bedroom"
DESCRIPTION = (
    "A Collage sketch: he says anything's fine, then refuses everything, and swats each dinner out of the air until "
    "the delivery app asks if they are still there."
)
ACCESSIBILITY = (
    "Paper cut-out characters: a woman in glasses asks a balding man in a green sweater what he wants for dinner. "
    "Paper tacos, sushi, soup and a card reading THE PLACE fly at him and he swats each away. A phone asks ARE YOU "
    "STILL THERE and a clock jumps to 11:40. Then the two of them sit up in a dark bedroom eating cereal from the box. "
    "Lines appear in tinted pills."
)
NARRATION = (
    f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised swats, a ding, crunching and a sting."
)
NOTE = "ElevenLabs premade voices Chris and Sarah at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits

SHIFT = {"gary": -120.0, "priya": 140.0}  # Gary on the left, facing the flying dinners; Priya on the right
ZOOMED = -70.0  # Priya's reaction: nearer the shelf, so the crash zoom on her keeps her face and the signature
ENTER = (420.0, 0.45)  # the opening: Priya leans in from this far right, landing after this many seconds
BED_PLACES = {"gary": Place(790.0, 1870.0, 0.8), "priya": Place(300.0, 1870.0, 0.8)}
HIT = (800.0, 1000.0)  # where a dinner meets Gary's raised hand
THROWN_FROM = (1240.0, 1300.0)  # off the frame's right, Priya's side
KNOCKED_TO = (1320.0, 280.0)  # off the frame's top right
FLIGHT = 0.3  # seconds a knocked dinner takes to leave
CARD_FROM = (860.0, 1320.0)  # already in frame: its words are read from its first frame
CARD_FLIGHT = 0.65  # the last thing thrown is a word: in the air long enough to be read
RED = "#c1121f"
REFUSED = ("THAI", "PIZZA", "TACOS", "SUSHI", "SOUP", "THE PLACE")  # the app's list, struck out
# the phone's insert, the clock above it, Priya's phone in her hands
APP = dict(x=170.0, y=800.0, w=740.0, h=1010.0)
CLOCK = dict(x=450.0, y=560.0, w=440.0)
HELD = dict(x=570.0, y=1400.0, w=210.0, h=340.0)

LINES = (
    Line("priya", "What do you want for dinner?"),
    Line("gary", "Anything's fine."),
    Line("priya", "Thai food?"),
    Line("gary", "Not Thai."),
    Line("priya", "Pizza?"),
    Line("gary", "We had pizza."),
    Line("priya", "In March."),
    Line("priya", "Tacos? Sushi? Soup? The place?"),
    Line("gary", "Not that place."),
    Line("priya", "Fine. I'll choose."),
    Line("gary", "...Not there."),
    Line("priya", "This is nice."),
    Line("gary", "...I wanted Thai."),
)
BEATS, END = timed(
    LINES,
    (
        (1.7, "priya", 0, "open", "smile", "shrug"),  # leaning in, already asking
        (1.1, "gary", 1, "closed", "smile", "down"),  # generous, eyes shut
        (0.7, "priya", 2, "open", "smile", "point"),
        (0.8, "gary", 3, "side", "flat", "down"),
        (0.7, "priya", 4, "open", "smile", "point"),
        (0.9, "gary", 5, "half", "frown", "shrug"),
        (0.9, "priya", 6, "angry", "flat", "hold"),  # March
        (0.6, "gary", (7, 0, "Tacos?"), "side", "flat", "down"),
        (0.6, "gary", (7, 1, "Sushi?"), "side", "flat", "fist", "swat"),
        (0.5, "gary", (7, 2, "Soup? The place?"), "side", "flat", "shrug", "swat"),
        (0.7, "gary", "Soup? The place?", "side", "flat", "fist", "swat"),  # the last swat, on the end of her list
        (1.2, "gary", 8, "angry", "frown", "fist", "swat"),
        (1.3, "priya", "", "half", "flat", "hold", "reveal:app"),  # the app, and the time on the wall
        (2.3, "priya", "", "half", "flat", "hold", "ding"),  # the clock jumps; the next line waits for the recording
        (1.2, "priya", 9, "half", "flat", "hold", "reveal:phone"),
        (1.7, "priya", "", "side", "flat", "hold"),  # the long hold: she scrolls, and says nothing at all
        (1.0, "gary", 10, "closed", "flat", "down"),  # he has not looked up
        (1.1, "priya", "", "wide", "flat", "hold", "zoom"),  # she never said where
        (1.0, "gary", "", "half", "flat", "hold", "reveal:bed"),  # dark, dry cereal, chewing
        (1.2, "priya", 11, "half", "flat", "hold"),
        (1.6, "gary", "", "half", "flat", "hold", "crunch"),  # the hold
        (1.3, "gary", 12, "sad", "flat", "hold"),
        (0.0, "priya", "", "side", "flat", "hold", "sting"),  # she stops chewing
    ),
    tail=1.1,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)
DINNERS = ("taco", "sushi", "soup")


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(max(start, 0.0), 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def _bed_from(beats: Sequence[Beat]) -> float:
    return next(t for t, what in events(beats, "reveal") if what == "bed")


def setting(beats: Sequence[Beat], app: Appearance) -> str:
    """The sofa until the bed's reveal, the bedroom from it."""
    return BED if app.start >= _bed_from(beats) else SOFA


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Each close on its side of the sofa, the two-shot in bed; both chew until the line that stops them."""
    bed = _bed_from(beats)
    last = next(b.start for b in beats if b.line == len(LINES) - 1)
    hers = next(b.start for b in beats if b.line == len(LINES) - 2)
    after_hers = next(b.start for b in beats if b.event == "crunch")
    reactions = {
        "gary": [_pose(0, "half", "flat", "hold"), _pose(after_hers, "half", "flat", "hold")],
        "priya": [
            _pose(0, "half", "flat", "hold"),
            _pose(after_hers, "open", "flat", "hold"),
            _pose(last, "side", "flat", "hold"),
        ],
    }
    lineup = Lineup(BED_PLACES, reactions, ((bed, end),))
    zoom = events(beats, "zoom")[0][0]

    def zoomed(app: Appearance) -> bool:
        return app.start <= zoom < app.end

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start >= bed:
            chewing = dict(mouths)
            chewing["gary"] = collage_everyday.chew(mouths.get("gary", []), bed, last - 0.1)
            track = collage_everyday.chew(mouths.get("priya", []), bed, hers - 0.05)
            chewing["priya"] = collage_everyday.chew(track, after_hers, last)
            return lineup(cv, parent, app, chewing)
        dx = ZOOMED if zoomed(app) else SHIFT[app.who]
        moved = cv.group(parent, cv.uid("g"), x=dx)
        if app.start == 0.0:
            cv.keys(moved, "x", [(0.0, dx + ENTER[0]), (ENTER[1], dx)], kind="cubic-out", local=False)
        fx, fy = solo(cv, moved, app, mouths)
        return collage_sets.zoom_pivot(SOFA, (fx + dx, fy), ZOOM_SCALE)

    return draw


def _thrown(cv, parent, make, a: float, hit: float, gone: float, *, frm: tuple[float, float] = THROWN_FROM) -> None:
    """A dinner in from Priya's side until ``hit``, knocked off the frame by ``gone``; ``make`` draws it at 0, 0."""
    g = cv.group(parent, cv.uid("g"), start=round(a, 6), end=round(gone, 6))
    make(g)
    (x0, y0), (x1, y1), (x2, y2) = frm, HIT, KNOCKED_TO
    cv.keys(g, "x", [(a, x0), (hit, x1), (gone, x2)], hold=False, local=False)
    cv.keys(g, "y", [(a, y0), (hit, y1), (gone, y2)], hold=False, local=False)
    cv.keys(g, "rotation", [(a, -40), (hit, 20), (gone, 400)], hold=False, local=False)


def dress(shot) -> None:
    """The dinners thrown at Gary, each knocked away on the next swat; the app and the clock; Priya's phone; the
    duvet, the cereal and the dark."""
    cv, app = shot.cv, shot.app
    swats = [t for t, _ in events(shot.beats, "swat")]
    named = [b.start for b in shot.beats if b.line == 7]
    bed = _bed_from(shot.beats)
    if app.who == "gary" and app.start < bed:
        for a, hit, kind in zip(named, swats, DINNERS, strict=False):
            if app.start <= a < app.end:
                _thrown(
                    cv, shot.front, lambda g, k=kind: collage_everyday.food(cv, g, k, 0, 0, 340), a, hit, hit + FLIGHT
                )
        a, hit = swats[3] - CARD_FLIGHT, swats[3]
        if app.start <= a < app.end:

            def card(g):
                collage_sets.sign(cv, g, "THE PLACE", -190, -60, 380, 120, size=62, tilt=-4)

            _thrown(cv, shot.front, card, a, hit, hit + FLIGHT, frm=CARD_FROM)
    if app.who == "priya" and app.start < bed:
        at = next((t for t, what in events(shot.beats, "reveal") if what == "app"), None)
        ding = events(shot.beats, "ding")[0][0]
        said = next(b.start for b in shot.beats if b.line == 9)
        if at is not None and app.start <= at < app.end:
            shown = _gated(cv, shot.front, at, said)
            collage_everyday.phone(cv, shown, **APP, screen="#fff3e6")
            left, top = APP["x"] + collage_everyday.BEZEL, APP["y"] + collage_everyday.BEZEL
            for i, row in enumerate(REFUSED):
                collage_sets.sign(cv, shown, row, left + 60, top + 30 + i * 80, 568, 68, size=42)
                cv.line(shown, left + 200, top + 64 + i * 80, left + 488, top + 64 + i * 80, RED, 4)
            collage_sets.sign(
                cv, shown, "ARE YOU STILL THERE?", left + 34, top + 545, 620, 300, size=84, color=RED, tilt=-2
            )
            early = _gated(cv, shot.front, at, ding)
            collage_everyday.alarm_clock(cv, early, **CLOCK, text="7:42")
            late = _gated(cv, shot.front, ding, said)
            collage_everyday.alarm_clock(cv, late, **CLOCK, text="11:40")
        phone_at = next((t for t, what in events(shot.beats, "reveal") if what == "phone"), None)
        if phone_at is not None and app.start <= phone_at < app.end:
            collage_everyday.phone(cv, _gated(cv, shot.front, phone_at, app.end), **HELD, screen="#cfe1ff")
    if app.start >= bed:
        collage_everyday.duvet(cv, shot.front)
        collage_everyday.cereal_box(cv, shot.front, 425, 1395, 230, 330, tilt=-5)
        dark = cv.grad("collage-anythings-dark", [(0, "#141a3a00"), (0.3, "#141a3a55"), (1, "#141a3a88")], (0, 0, 0, 1))
        cv.rect(shot.front, 0, 790, cv.width, 1130, dark)


def _gated(cv, parent, a: float, b: float):
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(a, b)])
    return g


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": SOFA, "priya": SOFA},
    dress=dress,
    cast=casting,
    setting=setting,
    bitrate=BITRATE,
)

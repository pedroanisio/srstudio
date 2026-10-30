"""Payday — the sketch as data: the salary lands, Deb punches the air, and the bills march up and bite the phone one
after another while she keeps smiling. The confetti turns and falls back up. Eleven seconds after it arrived the balance
is $3.12, and the bank tells her she has earned a treat. She catches the last piece of confetti in her mouth
and eats it.

Collage style (ADR 0026), cast cards of ADR 0036: Deb's smile is the one thing that does not move. One close at a bus
stop, the phone beside her. The reel opens moving (the sp-hook_motion test's arm b): Deb is in the air, the confetti
mid-fall. ElevenLabs premade voice, lip-synced.
"""

from __future__ import annotations

from srstudio import collage, collage_everyday, collage_sets
from srstudio.collage_sketch import TINTS, ZOOM_SCALE, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Line, Mouths, events

SEED = 4112
SLUG = "payday"
TITLE = "Payday — Deb (Collage)"
NAMES = ("deb",)
STOP = "bus-stop"
DESCRIPTION = "A Collage sketch: the salary lands, the bills eat it in eleven seconds, and the bank suggests a treat."
ACCESSIBILITY = (
    "A paper cut-out woman punches the air at a bus stop, her phone showing a balance of $2,940 under falling "
    "confetti. Paper bills with jagged mouths march up and bite the phone: rent, phone, electric, BRKL*SVC, a closed "
    "gym, a dentist. The confetti turns and falls upwards. The balance reaches $3.12. The phone says You've earned a "
    "treat. Smiling, she eats one piece of confetti. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voice {voices_note(NAMES)}; synthesised dings, a crunch and a sting."
NOTE = "ElevenLabs premade voice Jessica at her natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits

DX = -190.0  # Deb on the left, the phone beside her
JUMP = (80.0, 0.25)  # the punch in the air: she springs up from this far below, in this many seconds
PHONE = dict(x=610.0, y=800.0, w=430.0, h=500.0)
INSIDE = (PHONE["x"] + collage_everyday.BEZEL, PHONE["y"] + collage_everyday.BEZEL)
BILLS = (  # the bill's text and the balance after its bite, in the order of the dings
    ("RENT", "$1,090.00"),
    ("PHONE", "$995.00"),
    ("ELECTRIC", "$783.00"),
    ("BRKL*SVC 9.99", "$773.01"),
    ("GYM (CLOSED 2023) $40", "$733.01"),
    ("DENTIST (MARCH)", "$3.12"),
)
START = "$2,940.00"
TICKS = 11  # the seconds on the phone's counter when the money has gone
WALK = (0.5, 0.55)  # seconds a bill walks up before its ding, and leaves after it
WALK_FROM = (880.0, 1740.0)
BITE_AT = (825.0, 1430.0)  # just under the phone
WALK_TO = (925.0, 1620.0)
RED = "#c1121f"
CHEER = (395.0, 742.0, 320.0, 168.0)  # the bank's message: above her, inside what the crash zoom keeps
DRIFT = 800.0  # how high the last piece of confetti is when she looks up
MOUTH = (350.0, 1168.0)  # where it lands

LINES = (
    Line("deb", "Payday!"),
    Line("deb", "The rent."),
    Line("deb", "Phone."),
    Line("deb", "Electric."),
    Line("deb", "What's that?"),
    Line("deb", "That gym closed."),
    Line("deb", "From March?"),
)
BEATS, END = timed(
    LINES,
    (
        (0.95, "deb", 0, "wide", "grin", "fist"),  # already in the air
        (1.05, "deb", "Payday!", "wide", "grin", "fist", "ding"),  # the money lands: the phone comes up
        (1.1, "deb", 1, "open", "smile", "down", "ding"),
        (1.1, "deb", 2, "open", "smile", "down", "ding"),
        (1.2, "deb", 3, "open", "smile", "down", "ding"),
        (1.2, "deb", "", "side", "smile", "down", "ding"),  # BRKL*SVC, and nobody says a word
        (1.2, "deb", 4, "side", "smile", "shrug"),
        (1.4, "deb", 5, "open", "smile", "down", "ding"),
        (1.2, "deb", 6, "open", "smile", "down", "ding"),
        (1.5, "deb", "", "half", "smile", "down", "reveal:broke"),
        (1.2, "deb", "", "side", "smile", "down", "ding"),  # the bank is pleased for her
        (1.1, "deb", "", "half", "smile", "down", "zoom"),  # she reads it
        (0.9, "deb", "", "up", "o", "down", "reveal:treat"),  # the last piece falls, and she opens her mouth
        (1.0, "deb", "", "half", "smile", "down", "crunch"),
        (0.0, "deb", "", "half", "smile", "down", "sting"),
    ),
    tail=1.1,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _moment(beats, name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def casting(beats, end: float) -> CastDrawer:
    """Deb in the air on the first frame, then at the stop; she chews from the bite until the sting."""
    bite = events(beats, "crunch")[0][0]
    swallow = events(beats, "sting")[0][0]

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        moved = cv.group(parent, cv.uid("g"), x=DX)
        cv.keys(moved, "y", [(0.0, JUMP[0]), (JUMP[1], 0.0)], kind="cubic-out", local=False)
        chewing = dict(mouths)
        chewing["deb"] = collage_everyday.chew(mouths.get("deb", []), bite, swallow)
        fx, fy = solo(cv, moved, app, chewing)
        return collage_sets.zoom_pivot(STOP, (fx + DX, fy), ZOOM_SCALE)

    return draw


def _gated(cv, parent, a: float, b: float):
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(a, b)])
    return g


def _bill(cv, front, text: str, at: float) -> None:
    """One bill up to the phone for its bite, and away."""
    before, after = WALK
    g = _gated(cv, front, at - before, at + after)
    bill = collage_everyday.bill(cv, g, text, *WALK_FROM, w=430.0, h=240.0, size=46)
    (x0, y0), (x1, y1), (x2, y2) = WALK_FROM, BITE_AT, WALK_TO
    cv.keys(bill, "x", [(at - before, x0), (at, x1), (at + after, x2)], hold=False, local=False)
    cv.keys(bill, "y", [(at - before, y0), (at, y1), (at + after, y2)], hold=False, local=False)


def dress(shot) -> None:
    """The confetti, the phone with its balance and its counter, the bills, the bank's cheer, the piece she eats."""
    cv, front, app, beats = shot.cv, shot.front, shot.app, shot.beats
    dings = [t for t, _ in events(beats, "ding")]
    bills, cheer = dings[1:-1], dings[-1]
    broke = _moment(beats, "broke")
    reach, bite = _moment(beats, "treat"), events(beats, "crunch")[0][0]
    close = events(beats, "zoom")[0][0]  # the zoom crops the phone, so its lettering ends on the cut in
    collage_everyday.confetti(cv, shot.back, 0.0, reach, turn=bills[2])
    step = broke / TICKS  # the phone comes up on the counter's first second, clear of the punch
    held = _gated(cv, front, step, app.end)
    collage_everyday.phone(cv, held, **PHONE, screen="#fffaf0")
    left, top = INSIDE
    for a, b, money in zip([step, *bills], [*bills, close], [START, *(b for _, b in BILLS)], strict=True):
        colour = RED if money == BILLS[-1][1] else collage.INK
        collage_sets.sign(cv, _gated(cv, front, a, b), money, left + 14, top + 150, 350, 130, size=60, color=colour)
    collage_sets.sign(cv, _gated(cv, front, step, close), "BALANCE", left + 84, top + 80, 210, 60, size=36)
    for n in range(1, TICKS + 1):
        a, b = n * step, close if n == TICKS else (n + 1) * step
        collage_sets.sign(cv, _gated(cv, front, a, b), f"PAID 0:{n:02d} AGO", left + 34, top + 310, 310, 66, size=36)
    for (text, _), at in zip(BILLS, bills, strict=True):
        _bill(cv, front, text, at)
    collage_everyday.bubble(cv, _gated(cv, front, cheer, app.end), "You've earned a treat!", *CHEER, size=40)
    piece = cv.group(_gated(cv, front, reach, bite), cv.uid("g"), x=MOUTH[0], y=DRIFT, rotation=20.0)
    cv.rect(piece, -26, -16, 52, 32, "#f2c14e", collage.INK, 3)
    cv.keys(piece, "y", [(reach, DRIFT), (bite, MOUTH[1])], hold=False, local=False)
    cv.keys(piece, "rotation", [(reach, 20.0), (bite, 320.0)], hold=False, local=False)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"deb": STOP},
    dress=dress,
    cast=casting,
    bitrate=BITRATE,
)

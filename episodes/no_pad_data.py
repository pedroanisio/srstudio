"""No Pad — the sketch as data: a waiter who won't write your order down is a high-wire act, and a man who remembers
everything is a threat. Jun remembers Gary's order, as always, and the two spoons of the tiramisu. Priya doesn't eat
dessert. For the first time, he takes out a pad.

Collage style (ADR 0026), the two-shot of ADR 0036, the cafe set as a restaurant. The reel opens on a held two-shot
(STILL, L7 as adopted): nothing moves until the first whisper. The pad stays unseen until the last beat. ElevenLabs
premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_everyday, collage_home
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, appearances, events

SEED = 3316
SLUG = "no-pad"
TITLE = "No Pad — Gary, Priya and Jun (Collage)"
NAMES = ("gary", "priya", "jun")
ROOM = "cafe"
DESCRIPTION = (
    "A Collage sketch: a waiter who won't write your order down is a high-wire act, and a man who remembers "
    "everything is a threat."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a restaurant: a man and a woman whisper behind tall menus while a waiter in a "
    "beanie waits with his hands behind his back. He taps his temple and leaves. Plates land one at a time. He names "
    "the man's usual order, then the tiramisu with two spoons. The woman stares. The waiter looks at her, looks at "
    "him, slowly takes out an order pad and writes. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesized dings and a sting."
NOTE = "ElevenLabs premade voices Chris, Sarah and Will at their natural pace; no reference-voice cloning."
BITRATE = 5_600_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
HOOK = "NO PAD"
HOOK_SECONDS = 3.0
STILL = 0.45  # the held first frame

PLACES = {"gary": Place(290.0, 1800.0, 0.72), "priya": Place(800.0, 1800.0, 0.72)}
ZOOM_X = 1265.0  # Priya's zoom lands with the shelf and its code left of the bug, Gary out of the frame
TABLE = 1580
PIVOT = (540.0, 1900.0)  # Jun's eyes are under the hat: his looks read as the lean of his whole body
LEAN = 6.0
PLATES = ((230.0, 1720.0, 400.0, "steak"), (480.0, 1660.0, 200.0, "sauce"), (760.0, 1720.0, 380.0, "salad"))

LINES = (
    Line("gary", "He's not writing it down.", gain=-3.0),
    Line("priya", "Don't look at him.", gain=-3.0),
    Line("jun", "And for you, sir?"),
    Line("gary", "Steak, medium rare, no onions, sauce on the side, and a salad, but not that salad."),
    Line("priya", "He's incredible."),
    Line("jun", "No onions, sauce on the side. As always."),
    Line("priya", "As always?"),
    Line("jun", "And the tiramisu, sir? With the two spoons?"),
    Line("priya", "I don't eat dessert."),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "priya", "", "half", "flat", "hold"),  # the held two-shot, menus up
        (1.7, "gary", 0, "side", "flat", "hold"),
        (1.3, "priya", 1, "half", "flat", "hold"),
        (1.4, "jun", 2, "open", "smile", "down"),
        (2.6, "gary", (3, 0, "Steak, medium rare, no onions,"), "up", "flat", "hold"),
        (1.3, "gary", (3, 5, "sauce on the side,"), "up", "flat", "hold"),
        (1.3, "gary", (3, 9, "and a salad, but not that salad."), "side", "flat", "hold"),
        (0.8, "jun", "", "closed", "smile", "face"),  # taps his temple, once
        (0.5, "jun", "", "open", "smile", "down"),  # and leaves
        (1.5, "gary", "", "side", "flat", "hold"),  # a hand with a spoon stops at the edge of the frame
        (0.6, "priya", "", "wide", "smile", "hold", "ding"),  # the plates, one at a time
        (0.6, "priya", "", "wide", "smile", "hold", "ding"),
        (0.6, "priya", "", "wide", "smile", "hold", "ding"),
        (1.4, "priya", 4, "wide", "grin", "hold"),
        (2.6, "jun", 5, "open", "smile", "down"),
        (1.2, "priya", 6, "wide", "o", "hold", "zoom"),
        (2.8, "jun", 7, "open", "smile", "down"),
        (1.5, "priya", 8, "angry", "flat", "hold", "sting"),
        (1.0, "jun", "", "side", "smile", "down"),  # he looks at Priya
        (1.0, "jun", "", "side", "flat", "down"),  # he looks at Gary
        (1.3, "jun", "", "half", "flat", "hold"),  # very slowly, a pad
    ),
    tail=2.6,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(max(start, 0.0), 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def _said(beats: Sequence[Beat], line: int) -> float:
    return next(b.start for b in beats if b.line == line)


def _silent(beats: Sequence[Beat], arms: str = "face") -> float:
    """The temple tap: Jun's silent beat with his hand at his head."""
    return next(b.start for b in beats if b.who == "jun" and b.line is None and b.arms == arms)


def _hand(beats: Sequence[Beat]) -> float:
    """The held beat after Jun leaves."""
    return next(b.start for b in beats if b.who == "gary" and b.line is None)


def _looks(beats: Sequence[Beat]) -> tuple[float, float, float]:
    """After the last line: he looks at Priya, at Gary, and the pad."""
    after = _said(beats, 8)
    return tuple(b.start for b in beats if b.who == "jun" and b.start > after)[:3]


def lineup(beats: Sequence[Beat], end: float) -> Lineup:
    """Gary and Priya in one frame, everywhere Jun is not on his own."""
    tap = _silent(beats)
    tiramisu = _said(beats, 7)
    dings = [t for t, _ in events(beats, "ding")]
    reactions = {
        "gary": [
            _pose(0, "side", "flat", "hold"),
            _pose(dings[0], "open", "smile", "hold"),
            _pose(tiramisu, "wide", "frown", "hold"),
        ],
        "priya": [_pose(0, "half", "flat", "hold"), _pose(tap, "open", "flat", "hold")],
    }
    return Lineup(PLACES, reactions, tuple((a.start, a.end) for a in appearances(beats, end) if a.who != "jun"))


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """The two at the table, or Jun at it: he walks off after the tap, and turns from Priya to Gary at the end."""
    group = lineup(beats, end)
    tap = _silent(beats)
    at_priya, at_gary, rise = _looks(beats)

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if group.staged(app):
            return ZOOM_X, group(cv, parent, app, mouths)[1]
        lean = cv.group(parent, cv.uid("g"), x=PIVOT[0], y=PIVOT[1])
        moved = cv.group(lean, cv.uid("g"), x=-PIVOT[0], y=-PIVOT[1])
        if app.start <= tap < app.end:
            walk = [(app.end - 0.45, PIVOT[0]), (app.end, PIVOT[0] + 900.0)]
            cv.keys(lean, "x", walk, kind="cubic-in", local=False)
        if app.start <= at_gary < app.end:
            turns = ((at_priya, -LEAN), (at_gary, LEAN), (rise, 0.0))
            keys = [(0.0, 0.0)]
            for at, to in turns:
                keys += [(at, keys[-1][1]), (at + 0.3, to)]
            cv.keys(lean, "rotation", keys, kind="sine-in-out", local=False)
        return solo(cv, moved, app, mouths)

    return draw


def _plates(cv, front, beats: Sequence[Beat], end: float) -> None:
    """Each plate drops onto the table on its ding."""
    for (x, y, w, dish), (at, _) in zip(PLATES, events(beats, "ding"), strict=True):
        put = cv.group(front, cv.uid("g"), y=y)
        collage_home.land(cv, put, at=at, y=y)
        collage_home.plate(cv, put, x, 0, w, dish)


def _pad(cv, front, app: Appearance, beats: Sequence[Beat]) -> None:
    """The pad, unseen until now, rising slowly in his hand; then the pen in the other, and a first line of scrawl."""
    _, _, rise = _looks(beats)
    write = rise + 1.3
    pad = cv.group(front, cv.uid("g"))
    cv.keys(pad, "y", [(rise, 660.0), (write, 0.0)], kind="sine-in-out", local=False)
    collage_home.order_pad(cv, pad, 540, 1490, 300, lines=0)
    done = cv.group(pad, cv.uid("g"))
    cv.gate(done, [(write + 0.3, app.end)])
    collage_home.order_pad(cv, done, 540, 1490, 300, lines=2)
    hand = cv.group(pad, cv.uid("g"), x=470.0, y=1520.0)
    keys = [(write + i * 0.15, 470.0 + (i % 2) * 28.0) for i in range(6)]
    cv.keys(hand, "x", keys, hold=False, local=False)
    collage_home.pen(cv, hand, 0, 0, 240, 20.0)
    collage_everyday.arm(cv, hand, "jun", (490.0, 470.0), (52.0, -76.0))
    collage_everyday.arm(cv, pad, "jun", (140.0, 2040.0), (404.0, 1644.0))


def _spoon(cv, front, beats: Sequence[Beat], app: Appearance) -> None:
    """A hand with a spoon, in from the edge of the frame, and stopped there."""
    at = _hand(beats)
    reach = cv.group(front, cv.uid("g"))
    cv.gate(reach, [(max(at, app.start), min(_said(beats, 4), app.end))])
    cv.keys(reach, "x", [(at, 240.0), (at + 0.4, 0.0)], kind="cubic-out", local=False)
    collage_everyday.arm(cv, reach, "jun", (1180.0, 1530.0), (960.0, 1540.0), width=60.0)
    collage_home.spoon(cv, reach, 950, 1540, 220, -96.0)


def dress(shot) -> None:
    """The table in every shot; menus until Jun leaves; plates once they land; the pad at the very end."""
    cv, app, beats, end = shot.cv, shot.app, shot.beats, shot.end
    tap = _silent(beats)
    if app.who != "jun" and app.start < tap:
        for x in (PLACES["gary"].x, PLACES["priya"].x):
            collage_home.menu_card(cv, shot.front, x, 1540, 300, 420, -4.0)
    cv.rect(shot.front, 0, TABLE, cv.width, cv.height - TABLE, "#fffaf0", collage.INK, 4)
    if app.who != "jun" and app.start < _said(beats, 4) and app.end > _hand(beats):
        _spoon(cv, shot.front, beats, app)
    _plates(cv, shot.front, beats, end)
    if app.who == "jun" and app.end >= end:
        _pad(cv, shot.front, app, beats)
    if app.start < HOOK_SECONDS:
        collage_home.hook_card(cv, shot.front, HOOK, ROOM, shot.measure, start=0.0, seconds=HOOK_SECONDS)


CAST = lineup(BEATS, END)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": ROOM, "priya": ROOM, "jun": ROOM},
    dress=dress,
    cast=casting,
    bleed=True,
    still=STILL,
    opening=CAST.held,
    bitrate=BITRATE,
    keep_signature=True,
    loudness="-14",
)

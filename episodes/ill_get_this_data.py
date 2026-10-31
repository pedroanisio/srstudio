"""I'll Get This — the sketch as data: two grown men wrestle over a restaurant bill neither of them wants to pay, run
for the till, and find it paid. Their mother paid it, with the card that should be in Gary's wallet.

Collage style (ADR 0026), the cafe as a restaurant; a group shot at the table, one at the counter with a whip pan
between them. The reel moves from its first frame (the sp-hook_motion test's arm b). ElevenLabs premade voices,
lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from srstudio import collage, collage_everyday, collage_sets, collage_things
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, ZOOM_SCALE, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 3126
SLUG = "ill-get-this"
TITLE = "I'll Get This — Gary, Omar, Jun and Rosa (Collage)"
NAMES = ("gary", "omar", "jun", "rosa")
ROOM = "cafe"
DESCRIPTION = (
    "A Collage sketch: two men fight over a restaurant bill all the way to the till, where it is already paid. Their "
    "mother has a card to return."
)
ACCESSIBILITY = (
    "Paper cut-out characters at a restaurant table. Two men slam their hands on one bill while an older woman "
    "between them chews. They run to the counter, cards out, and the waiter says it is already paid. The woman, "
    "across the room, lifts a tiny cup and flicks a card that spins to a stop on the counter with GARY on it. Gary "
    "opens his wallet and one slot is empty. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}."
NOTE = "ElevenLabs premade voices Chris, Daniel, Will and Matilda at their natural pace; no reference-voice cloning."
BITRATE = 5_500_000  # two passes: a master under 20 MB

TABLE = {"rosa": Place(540.0, 1500.0, 0.6), "gary": Place(215.0, 1640.0, 0.72), "omar": Place(865.0, 1640.0, 0.72)}
TABLE_TOP = 1340.0
BILL = (540.0, 1640.0)
SLAM = (0.0, 0.12)  # the two hands land on the bill: the first frames of the reel
TUG = 46.0  # px the bill goes each way
BACK = {"jun": Place(540.0, 1530.0, 0.6)}
FRONT = {"gary": Place(215.0, 1790.0, 0.74), "omar": Place(865.0, 1790.0, 0.74)}
COUNTER_TOP = 1300.0
ROSA_ELBOW = (262.0, 1590.0)  # just over the table, the arm with the cup
CARD_Y = 1390.0  # the cards, in the hands of the brothers' shrug
BOB = (10.0, 0.32)  # out of breath: px and seconds
HIS_CARD, HER_CARD, OMAR_CARD = "#2a9d8f", "#1d3557", "#e63946"  # the one he brandishes, the one she flicks
INSERT_CARD = dict(w=640.0)

LINES = (
    Line("gary", "I've got this."),
    Line("omar", "Put your wallet away, Gary."),
    Line("gary", "Your money's no good here."),
    Line("omar", "It's a restaurant."),
    Line("jun", "Sir, should I..."),
    Line("gary", "Take his and you're dead to me."),
    Line("omar", "I need the bathroom."),
    Line("gary", "He's going to the till!"),
    Line("jun", "It's already paid."),
    Line("gary", "Mom. You didn't have to."),
    Line("rosa", "I didn't."),
)
BEATS, END = timed(
    LINES,
    (
        (1.0, "gary", 0, "angry", "grin", "hold", "swat"),
        (1.55, "omar", 1, "angry", "smug", "hold"),
        (1.35, "gary", 2, "angry", "grin", "hold"),
        (1.25, "omar", 3, "half", "flat", "hold"),
        (1.4, "rosa", "", "half", "smile", "down", "crunch"),  # the bill tears; she chews
        (1.15, "jun", 4, "wide", "o", "hold"),
        (1.4, "gary", 5, "angry", "frown", "point"),
        (0.9, "omar", "", "open", "smile", "down", "reveal:rise"),  # too calmly
        (1.25, "omar", 6, "open", "smile", "down"),
        (1.25, "gary", 7, "wide", "o", "point", "zoom"),
        (0.75, "jun", "", "open", "o", "hold", "whip"),  # they hit the counter together
        (1.1, "jun", 8, "half", "smile", "hold"),
        (1.5, "jun", "", "half", "smile", "hold", "reveal:turn"),  # nobody breathes, then they turn
        (1.2, "rosa", "", "half", "smug", "down", "reveal:cup"),
        (1.3, "gary", 9, "sad", "frown", "shrug"),
        (0.8, "rosa", 10, "half", "smug", "down"),
        (1.0, "rosa", "", "half", "smug", "down", "reveal:hold"),
        (0.7, "rosa", "", "half", "smile", "point", "swat"),  # the flick
        (1.6, "jun", "", "open", "flat", "hold", "reveal:insert"),
        (1.0, "gary", "", "wide", "frown", "hold", "sting"),
    ),
    tail=1.0,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(start, 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Everyone at the table until Jun comes over; three at the counter after the whip, Jun behind it, the brothers in
    front, panting; alone otherwise."""
    tear = events(beats, "crunch")[0][0]
    jun_first = next(b.start for b in beats if b.who == "jun")
    whip = events(beats, "whip")[0][0]
    rise, turn, insert, cup = (_at(beats, n) for n in ("rise", "turn", "insert", "cup"))
    zoom = events(beats, "zoom")[0][0]
    table = Lineup(
        TABLE,
        {
            "gary": [_pose(0, "angry", "flat", "hold"), _pose(tear, "angry", "frown", "hold")],
            "omar": [_pose(0, "angry", "flat", "hold"), _pose(tear, "angry", "frown", "hold")],
            "rosa": [_pose(0, "half", "smile", "down")],
        },
        ((0.0, jun_first),),
    )
    behind = Lineup(BACK, {"jun": [_pose(0, "open", "flat", "hold")]}, ((whip, end),))
    gasping = [_pose(0, "wide", "o", "shrug"), _pose(turn, "wide", "flat", "shrug")]
    ahead = Lineup(FRONT, {"gary": gasping, "omar": gasping}, ((whip, end),))

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start == insert:
            return collage.face(collage.LOOKS[app.who])
        if app.start > insert:  # his forearms go behind the wallet whatever the recording's poses say
            return solo(cv, parent, replace(app, poses=[{**p, "arms": "hold"} for p in app.poses]), mouths)
        if app.start == rise:
            up = cv.group(parent, cv.uid("g"))
            cv.keys(up, "y", [(rise + 0.1, 330.0), (rise + 0.8, 0.0)], kind="sine-in-out", local=False)
            return solo(cv, up, app, mouths)
        if app.start == whip:
            face = behind(cv, parent, app, mouths)
            collage_things.counter(cv, parent, COUNTER_TOP)
            collage_things.till(cv, parent, 700.0, COUNTER_TOP + 8.0, 240.0)
            panting = cv.group(parent, cv.uid("g"))
            depth, seconds = BOB
            count = int((turn - whip) / seconds)
            cv.keys(
                panting,
                "y",
                [(whip + i * seconds, depth if i % 2 else 0.0) for i in range(count + 1)],
                kind="sine-in-out",
                local=False,
            )
            ahead(cv, panting, replace(app, who="gary", poses=ahead.poses("gary", replace(app, who="jun"))), mouths)
            collage_things.bank_card(cv, panting, 463.0, CARD_Y, 230.0, colour=HIS_CARD, tilt=-8.0)
            collage_things.bank_card(cv, panting, 617.0, CARD_Y, 230.0, colour=OMAR_CARD, tilt=8.0)
            return face
        if app.who == "rosa" and app.start >= cup:  # the arm with the cup is the shot's; the flick stays hers
            poses = [{**p, "arms": "free" if p["arms"] == "down" else p["arms"]} for p in app.poses]
            return solo(cv, parent, replace(app, poses=poses), mouths)
        if table.staged(app):
            chewing = collage_everyday.chew(mouths.get("rosa", ()), tear, tear + 1.3)
            return table(cv, parent, app, {**mouths, "rosa": chewing})
        face = solo(cv, parent, app, mouths)
        if app.start <= zoom < app.end:
            return collage_sets.zoom_pivot(ROOM, face, ZOOM_SCALE)
        return face

    return draw


def _table(shot) -> None:
    """The bill between them, their two hands on it: they land on the first frames and it goes back and forth on each
    line until it tears."""
    cv, app, beats, front = shot.cv, shot.app, shot.beats, shot.front
    tear = events(beats, "crunch")[0][0]
    collage_everyday.tablecloth(cv, front, TABLE_TOP, "#f4ecd8")
    collage_things.tiny_cup(cv, front, 540.0, TABLE_TOP + 110.0, 110.0)
    tug = cv.group(front, cv.uid("tug"))
    pulls = [(0.0, 0.0)]
    for b in beats:
        if b.line is not None and b.start < tear:
            pulls += [(b.start + 0.05, pulls[-1][1]), (b.start + 0.25, -TUG if b.who == "gary" else TUG)]
    cv.keys(tug, "x", pulls, kind="sine-in-out", local=False)
    collage_things.receipt(cv, tug, *BILL, 250.0, 300.0, torn=app.start >= tear)
    hands = cv.group(tug, cv.uid("g"))
    if app.start < SLAM[1]:
        cv.keys(hands, "y", [(SLAM[0], 520.0), (SLAM[1], 0.0)], kind="cubic-in", local=False)
    collage_everyday.arm(cv, hands, "gary", (-60.0, 1980.0), (BILL[0] - 110.0, BILL[1] + 40.0))
    collage_everyday.arm(cv, hands, "omar", (1140.0, 1980.0), (BILL[0] + 110.0, BILL[1] + 40.0))


def _cup(shot) -> None:
    """Rosa alone at the table, the tiny cup coming up in one hand and staying there; then the flick from the other."""
    cv, app, beats, front = shot.cv, shot.app, shot.beats, shot.front
    cup = _at(beats, "cup")
    collage_everyday.arm(cv, front, "rosa", collage_everyday.shoulder("rosa"), ROSA_ELBOW, hand=False)
    lifted = cv.group(front, cv.uid("g"))
    if app.start == cup:
        cv.keys(lifted, "y", [(cup + 0.15, 420.0), (cup + 0.75, 0.0)], kind="sine-in-out", local=False)
    collage_everyday.arm(cv, lifted, "rosa", ROSA_ELBOW, (310.0, 1340.0))
    collage_things.tiny_cup(cv, lifted, 310.0, 1310.0, 120.0)
    collage_everyday.tablecloth(cv, front)  # over the arm: the cup comes up from behind the table
    flick = events(beats, "swat")[-1][0]
    if app.start <= flick < app.end:
        card = cv.group(front, cv.uid("g"))
        cv.gate(card, [(flick, app.end)])
        paper = collage_things.bank_card(cv, card, 875.0, 1170.0, 200.0, colour=HER_CARD)
        cv.keys(paper, "x", [(flick + 0.05, 875.0), (flick + 0.45, 1400.0)], kind="cubic-in", local=False)
        cv.keys(paper, "rotation", [(flick + 0.05, 0.0), (flick + 0.45, 540.0)], local=False, hold=False)


def _insert(shot) -> None:
    """Nobody: the counter close, and the card spinning to a stop on it with his name up."""
    cv, app, front = shot.cv, shot.app, shot.front
    collage_things.counter(cv, front, 980.0)
    spin = (app.start + 0.05, app.start + 0.65)
    card = collage_things.bank_card(cv, front, 540.0, 1320.0, name="GARY", colour=HER_CARD, tilt=-6.0, **INSERT_CARD)
    cv.keys(card, "x", [(spin[0], 1500.0), (spin[1], 540.0)], kind="cubic-out", local=False)
    cv.keys(card, "rotation", [(spin[0], 1074.0), (spin[1], -6.0)], kind="cubic-out", local=False)


def _wallet(shot) -> None:
    """Gary with his wallet open: the slot it should be in."""
    cv, front = shot.cv, shot.front
    collage_things.wallet(cv, front, 540.0, 1590.0, 640.0, cards=(HIS_CARD, OMAR_CARD))
    collage_everyday.arm(cv, front, "gary", (206.0, 1630.0), (262.0, 1640.0))  # from the elbows of his "hold" pose
    collage_everyday.arm(cv, front, "gary", (874.0, 1630.0), (818.0, 1640.0))


def dress(shot) -> None:
    """Each shot's props, by where it stands in the story."""
    app, beats = shot.app, shot.beats
    jun_first = next(b.start for b in beats if b.who == "jun")
    whip, cup, insert = events(beats, "whip")[0][0], _at(beats, "cup"), _at(beats, "insert")
    if app.start < jun_first:
        _table(shot)
    elif app.start == insert:
        _insert(shot)
    elif app.start > insert:
        _wallet(shot)
    elif app.who == "rosa" and app.start >= cup:
        _cup(shot)
    elif app.who == "gary" and app.start > whip:
        collage_things.counter(shot.cv, shot.front, 1660.0)
    elif app.start < whip:
        collage_everyday.tablecloth(shot.cv, shot.front)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets=dict.fromkeys(NAMES, ROOM),
    dress=dress,
    cast=casting,
    bitrate=BITRATE,
    loudness="-14",
)

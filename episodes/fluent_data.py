"""Fluent — the sketch as data: Deb's CV says she is fluent in French, and Brent checks. She is not, and nor is he: two
adults trade the only two words they have, and close the deal. Then the desk phone that has been between them since
the first shot rings, and the screen says Paris.

Collage style (ADR 0026), the boardroom; the group shot of ADR 0036 for the two of them, a close for each when a word
lands. The reel opens on a slow push (the sp-hook_motion test's arm b). ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from srstudio import collage, collage_everyday, collage_things
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 3123
SLUG = "fluent"
TITLE = "Fluent — Brent and Deb (Collage)"
NAMES = ("brent", "deb")
ROOM = "boardroom"
DESCRIPTION = (
    "A Collage sketch: a CV says fluent in French, the interviewer checks, and neither of them gets past croissant. "
    "Then the phone rings."
)
ACCESSIBILITY = (
    "Paper cut-out characters across a boardroom table, a CV and a desk phone between them: a man in a blazer and a "
    "woman with long hair. He says bonjour and one of her eyes twitches. He turns the CV over and the back is blank. "
    "They nod gravely over the word croissant. The desk phone rings, its screen reading PARIS OFFICE, and he slides "
    "it across to her with one finger. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; a synthesized phone ring."
NOTE = "ElevenLabs premade voices Brian and Jessica at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB

LEAD = 0.45  # the silence before the first word
PUSHED, PUSH = 2.0, 1.06  # the opening's slow push: until when, and how far
PLACES = {"brent": Place(285.0, 1565.0, 0.72), "deb": Place(800.0, 1565.0, 0.72)}
DESK = (1465.0, "#4a2f1f", "#6f4e37", "#3b2a1e")  # the table's edge, front, slab and seams, before the two of them
PHONE_Y = 1600.0
NEAR_BRENT, NEAR_DEB = 500.0, 690.0  # the phone's x before and after the slide
PHONE_W = 300.0
SHEET = dict(x=190.0, y=1680.0, w=230.0, tilt=-8.0)  # the CV on the table
HELD = dict(x=540.0, y=1520.0, w=430.0)  # the CV in his hands
INSERT = dict(x=540.0, y=1560.0, w=920.0, display="PARIS OFFICE", size=92)
WOBBLE, WOBBLE_STEP = 3.0, 0.06  # a ringing phone's shake: degrees and seconds
RING_SHAKE = 0.9  # seconds a ring shakes the phone
NOD = (24.0, 0.45)  # the grave nod: px down, seconds
EAR_NEAR = (646.0, 985.0)  # the handset at Deb's ear in the two-shot
SHOULDER_NEAR = (626.0, 1215.0)  # her shoulder there
SHOULDER_CLOSE = (286.0, 1390.0)  # and in her close
ELBOW_NEAR = (572.0, 1377.0)  # the arm with the handset: the elbow, in the two-shot
ELBOW_CLOSE = (160.0, 1500.0)  # and in her close
RISE = (0.3, 0.95)  # the handset comes up, after the lift
EAR_CLOSE = (336.0, 1090.0)  # and in her close

LINES = (
    Line("brent", "Fluent in French, is that right?"),
    Line("deb", "Completely."),
    Line("brent", "Bonjour."),
    Line("deb", "...Bonjour."),
    Line("brent", "Croissant."),
    Line("deb", "Croissant."),
    Line("brent", "Incredible. That's all of mine too."),
    Line("brent", "Welcome aboard."),
    Line("deb", "...Croissant?"),
)
BEATS, END = timed(
    LINES,
    (
        (LEAD, "deb", "", "open", "smile", "hold"),  # the table, the CV, the phone
        (2.2, "brent", 0, "open", "smile", "hold"),
        (0.85, "deb", 1, "open", "grin", "hold"),
        (1.05, "brent", 2, "open", "smile", "hold"),
        (2.0, "deb", "", "open", "smile", "hold", "reveal:close"),  # her smile does not move; one eye does
        (1.0, "deb", 3, "open", "smile", "hold", "zoom"),
        (2.0, "brent", "", "half", "flat", "hold", "reveal:sheet"),  # he turns it over: nothing
        (1.2, "brent", 4, "half", "flat", "hold"),
        (0.95, "deb", 5, "half", "flat", "hold"),
        (1.3, "brent", "", "half", "flat", "hold", "reveal:nod"),  # closing a deal
        (2.3, "brent", 6, "open", "grin", "shrug"),
        (0.7, "brent", "", "closed", "smile", "down"),  # the breath out
        (0.4, "brent", "", "wide", "o", "down", "ring"),
        (1.3, "deb", "", "open", "flat", "hold", "reveal:insert"),
        (1.5, "brent", "", "open", "smile", "down", "ring"),  # one finger
        (1.2, "brent", 7, "open", "smile", "down", "ring"),
        (1.5, "brent", "", "open", "smile", "down", "reveal:lift"),
        (1.1, "deb", 8, "wide", "smile", "down", "reveal:ear"),
        (0.8, "deb", "", "wide", "smile", "down", "sting"),
    ),
    tail=0.6,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(start, 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def _lineup(beats: Sequence[Beat], end: float) -> Lineup:
    """The two of them at the table: from the top to her close, from the nod to the insert, from the slide to her
    last close. The listener's face changes with the news."""
    close, nod, insert, lift, ear = (_at(beats, n) for n in ("close", "nod", "insert", "lift", "ear"))
    slide = next(b.start for b in beats if b.start > insert)
    breath = next(b.start for b in beats if b.eyes == "closed")
    ring = events(beats, "ring")[0][0]
    reactions = {
        "brent": [_pose(0, "open", "smile", "hold"), _pose(nod, "half", "flat", "hold")],
        "deb": [
            _pose(0, "open", "smile", "hold"),
            _pose(nod, "half", "flat", "hold"),
            _pose(breath, "closed", "smile", "hold"),
            _pose(ring, "wide", "o", "hold"),
            _pose(slide, "wide", "flat", "hold"),
            _pose(lift, "wide", "flat", "down"),
            _pose(lift + RISE[1] - 0.1, "wide", "flat", "free"),
        ],
    }
    return Lineup(PLACES, reactions, ((0.0, close), (nod, insert), (slide, ear)))


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """The lineup, nodding on the nod; the speaker alone in a close; nobody over the insert."""
    lineup = _lineup(beats, end)
    nod, insert, ear = _at(beats, "nod"), _at(beats, "insert"), _at(beats, "ear")

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start == insert:
            return collage.face(collage.LOOKS[app.who])
        if not lineup.staged(app):
            if app.start >= ear:  # the arm with the handset is the shot's, whatever the recording's poses say
                app = replace(app, poses=[{**p, "arms": "free"} for p in app.poses])
            return solo(cv, parent, app, mouths)
        if app.start != nod:
            return lineup(cv, parent, app, mouths)
        depth, seconds = NOD
        both = cv.group(parent, cv.uid("g"))
        cv.keys(
            both,
            "y",
            [(nod + i * seconds / 2, depth if i % 2 else 0.0) for i in range(5)],
            kind="sine-in-out",
            local=False,
        )
        return lineup(cv, both, app, mouths)

    return draw


def _shaken(cv, phone, rings: Sequence[float], stop: float) -> None:
    """The phone shaking through each ring, before ``stop``."""
    keys = [(0.0, 0.0)]
    for at in rings:
        steps = int(RING_SHAKE / WOBBLE_STEP)
        keys += [
            (round(at + i * WOBBLE_STEP, 6), (WOBBLE if i % 2 else -WOBBLE) if i < steps else 0.0)
            for i in range(steps + 1)
            if at + i * WOBBLE_STEP < stop
        ]
    cv.keys(phone, "rotation", keys, hold=False, local=False)


def dress(shot) -> None:
    """The desk in every two-shot, with the CV and the phone on it; the CV in his hands, the screen, the handset."""
    cv, app, beats, front = shot.cv, shot.app, shot.beats, shot.front
    close, sheet, nod, insert, lift, ear = (_at(beats, n) for n in ("close", "sheet", "nod", "insert", "lift", "ear"))
    slide = next(b.start for b in beats if b.start > insert)
    rings = [t for t, _ in events(beats, "ring")]
    if app.start == insert:
        collage_things.counter(cv, front, 1240.0, *DESK[1:])
        _shaken(cv, collage_things.desk_phone(cv, front, **INSERT), rings, lift)
        return
    if app.start >= ear:
        collage_everyday.arm(cv, front, "deb", SHOULDER_CLOSE, ELBOW_CLOSE, hand=False)
        collage_everyday.arm(cv, front, "deb", ELBOW_CLOSE, (EAR_CLOSE[0] - 10, EAR_CLOSE[1] + 110))
        collage_things.handset(cv, front, *EAR_CLOSE, 420.0, 96.0)
        return
    if app.start == close:
        collage_things.twitch(cv, front, "deb", (close + 0.7, close + 1.0, close + 1.5))
        return
    if app.start == sheet:
        collage_things.resume(cv, front, **HELD, turn=sheet + 0.8)
        return
    if app.start > sheet and app.start < nod:
        return  # her close on the word
    collage_things.counter(cv, front, *DESK)
    collage_things.resume(cv, front, **SHEET)
    if app.start < slide:
        _shaken(cv, collage_things.desk_phone(cv, front, NEAR_BRENT, PHONE_Y, PHONE_W), rings, insert)
        return
    # the slide: one finger, the phone across the table, ringing, until she lifts the handset off it
    speed = (slide + 0.2, slide + 1.3)
    on_hook = cv.group(front, cv.uid("g"))
    cv.gate(on_hook, [(slide, lift)])
    phone = collage_things.desk_phone(cv, on_hook, NEAR_BRENT, PHONE_Y, PHONE_W)
    cv.keys(phone, "x", [(speed[0], NEAR_BRENT), (speed[1], NEAR_DEB)], kind="sine-in-out", local=False)
    _shaken(cv, phone, rings[1:], lift)
    arm = cv.group(front, cv.uid("g"))
    cv.gate(arm, [(slide, speed[1] + 0.25)])
    fingertip = (NEAR_BRENT - PHONE_W * 0.42, PHONE_Y - 60.0)
    collage_everyday.arm(cv, arm, "brent", (160.0, 1980.0), (fingertip[0] - 80.0, fingertip[1] + 20.0), width=60.0)
    cv.rect(
        arm, fingertip[0] - 60.0, fingertip[1] - 2.0, 74.0, 28.0, collage.LOOKS["brent"].skin, collage.INK, 3, radius=14
    )
    cv.keys(arm, "x", [(speed[0], 0.0), (speed[1], NEAR_DEB - NEAR_BRENT)], kind="sine-in-out", local=False)
    off_hook = cv.group(front, cv.uid("g"))
    cv.gate(off_hook, [(lift, app.end)])
    collage_things.desk_phone(cv, off_hook, NEAR_DEB, PHONE_Y, PHONE_W, off_hook=True)
    rest = (NEAR_DEB, PHONE_Y - PHONE_W * 0.56)
    hand = collage_things.handset(cv, off_hook, *rest, PHONE_W * 0.86)
    rise = (lift + RISE[0], lift + RISE[1])
    cv.keys(hand, "x", [(rise[0], rest[0]), (rise[1], EAR_NEAR[0])], kind="sine-in-out", local=False)
    cv.keys(hand, "y", [(rise[0], rest[1]), (rise[1], EAR_NEAR[1])], kind="sine-in-out", local=False)
    cv.keys(hand, "rotation", [(rise[0], 0.0), (rise[1], 96.0)], kind="sine-in-out", local=False)
    reach = cv.group(off_hook, cv.uid("g"))
    cv.gate(reach, [(rise[1] - 0.1, app.end)])
    collage_everyday.arm(cv, reach, "deb", SHOULDER_NEAR, ELBOW_NEAR, width=52.0, hand=False)
    collage_everyday.arm(cv, reach, "deb", ELBOW_NEAR, (EAR_NEAR[0] - 8.0, EAR_NEAR[1] + 70.0), width=52.0)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"brent": ROOM, "deb": ROOM},
    dress=dress,
    cast=casting,
    push=(PUSHED, PUSH),
    bitrate=BITRATE,
    loudness="-14",
)

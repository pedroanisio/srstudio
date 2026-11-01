"""Exciting Opportunity — the sketch as data: a recruiter calls Priya with an amazing job he cannot describe, and Deb
stops chewing. Priya asks why the job is open. Cut to a windowless booth: the job is his. She asks the salary, and the
hard cut on the word finds him holding his own sealed pay envelope. Six years. Nobody has told him.

Collage style (ADR 0026), the two-shot of ADR 0036; the booth is kept out of frame until the reveal. Brent is heard
through the phone's speaker until we see him. The envelope shows no figure. The reel moves from its first second (L7):
Deb is already eating. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_everyday, collage_home, collage_photo
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, appearances, events

SEED = 3305
SLUG = "exciting-opportunity"
TITLE = "Exciting Opportunity — Priya, Deb and Brent (Collage)"
NAMES = ("priya", "deb", "brent")
ROOM, BOOTH = "living-room", "booth"
DESCRIPTION = (
    "A Collage sketch: a recruiter calls with an amazing opportunity and cannot say the company, the pay or the job. "
    "Then Priya asks why it is open."
)
ACCESSIBILITY = (
    "Paper cut-out characters on a sofa: a woman holds up her phone on speaker while her friend eats cereal. The "
    "spoon stops. Cut to a man in a headset in a tiny windowless booth with one lamp and a dead plant. He holds a "
    "sealed pay envelope stamped CONFIDENTIAL and turns it over. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesized crunching and a sting."
NOTE = "ElevenLabs premade voices Sarah, Jessica and Brian at their natural pace; no reference-voice cloning."
BITRATE = 5_600_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
HOOK = "UNKNOWN CALLER"
HOOK_SECONDS = 3.0

PLACES = {"priya": Place(290.0, 1800.0, 0.72), "deb": Place(790.0, 1800.0, 0.7)}
BOWL = (800.0, 1740.0, 300.0)  # on Deb's knees
PHONE = (330.0, 1400.0, 130.0, 230.0)
ENVELOPE = (540.0, 1560.0, 620.0)
LAMP, PLANT = (150.0, 1660.0, 330.0), (930.0, 1660.0, 300.0)

LINES = (
    Line("brent", "Priya! I have an exciting opportunity.", phone=True),
    Line("priya", "What's the company?"),
    Line("brent", "Can't say.", phone=True),
    Line("priya", "What's the salary?"),
    Line("brent", "Can't say.", phone=True),
    Line("priya", "What's the job?"),
    Line("brent", "It's very exciting.", phone=True),
    Line("deb", "Is this a recruiter or a kidnapper?"),
    Line("brent", "Do you have a passport?", phone=True),
    Line("priya", "Why is it open?"),
    Line("brent", "It's this job. It's my job. Please.", gain=-5.0),
    Line("priya", "What's the salary?"),
    Line("brent", "Six years. Nobody's told me."),
)
BEATS, END = timed(
    LINES,
    (
        (2.0, "priya", 0, "open", "smile", "hold"),  # in mid-sentence, the phone on speaker, Deb eating
        (1.6, "priya", 1, "open", "flat", "hold"),
        (0.9, "priya", 2, "half", "flat", "hold", "crunch"),
        (1.2, "priya", 3, "open", "flat", "hold"),
        (0.9, "priya", 4, "half", "flat", "hold", "crunch"),
        (1.1, "priya", 5, "side", "flat", "hold"),
        (1.3, "priya", 6, "half", "flat", "hold", "crunch"),
        (2.0, "deb", 7, "half", "flat", "point"),
        (1.5, "priya", 8, "wide", "o", "hold", "zoom"),  # the spoon stops
        (0.3, "deb", "", "wide", "o", "point"),  # she mouths it: hang up
        (0.3, "deb", "", "wide", "flat", "point"),
        (0.4, "deb", "", "wide", "o", "point"),
        (1.2, "priya", 9, "half", "flat", "hold"),
        (1.0, "brent", "", "side", "flat", "down"),  # the booth at last; he checks behind him
        (0.8, "brent", "", "wide", "flat", "down"),
        (3.0, "brent", 10, "sad", "frown", "down"),
        (0.8, "priya", (11, 0, "What's the"), "half", "flat", "hold"),
        (1.4, "brent", (11, 2, "salary?"), "half", "frown", "hold", "sting"),  # the hard cut on the word
        (0.8, "brent", "", "half", "frown", "hold"),  # turning the envelope over
        (2.6, "brent", 12, "sad", "flat", "hold"),  # looks up from it
    ),
    tail=2.8,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(max(start, 0.0), 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def _said(beats: Sequence[Beat], line: int) -> float:
    return next(b.start for b in beats if b.line == line)


def lineup(beats: Sequence[Beat], end: float) -> Lineup:
    """The sofa from the first second until Priya's close, each listening on the project clock."""
    stop = _said(beats, 8)
    close = _said(beats, 11)
    reactions = {
        "priya": [_pose(0, "open", "flat", "hold"), _pose(_said(beats, 7), "side", "flat", "hold")],
        "deb": [_pose(0, "half", "smile", "hold"), _pose(stop, "wide", "flat", "hold")],
    }
    return Lineup(
        PLACES,
        reactions,
        tuple((a.start, a.end) for a in appearances(beats, end) if a.who != "brent" and a.end <= close),
    )


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """The two on the sofa, then each alone: Brent in the booth, Priya close."""
    group = lineup(beats, end)

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        return group(cv, parent, app, mouths) if group.staged(app) else solo(cv, parent, app, mouths)

    return draw


def _spoon(cv, front, beats: Sequence[Beat]) -> None:
    """Deb's spoon, up and down from the first frame, and stopped dead in the air on the word passport."""
    stop = _said(beats, 8)
    hand = cv.group(front, cv.uid("g"))
    keys, t, up = [], 0.0, False
    while t < stop:
        keys.append((round(t, 6), -175.0 if up else 0.0))
        t, up = t + 0.8, not up
    keys.append((round(stop, 6), -120.0))
    cv.keys(hand, "y", keys, hold=False, local=False)
    collage_everyday.arm(cv, hand, "deb", (1120.0, 2300.0), (830.0, 1720.0), width=58.0)
    collage_home.spoon(cv, hand, 826, 1710, 250, -14.0)


def _sofa(cv, front, beats: Sequence[Beat]) -> None:
    collage_photo.sofa(cv, front)
    collage_home.cereal_bowl(cv, front, *BOWL)
    _spoon(cv, front, beats)
    x, y, w, h = PHONE
    screen = collage_everyday.phone(cv, front, x, y, w, h, screen="#17151f", tilt=-7.0)
    cv.rect(screen, 16, 150, w - 56, 36, "#2a9d8f", radius=10)  # the call, running, nothing to read


def _booth(cv, shot, cut: float | None) -> None:
    """One lamp, a dead plant, his phone; the headset on him; from the hard cut, his own sealed envelope."""
    collage_home.desk_lamp(cv, shot.front, *LAMP)
    collage_home.dead_plant(cv, shot.front, *PLANT)
    collage_home.headset(cv, shot.front, collage.CX, collage.HEAD_Y, collage.HEAD_RX, collage.HEAD_RY)
    if cut is not None:
        x, y, w = ENVELOPE
        turn = cv.group(shot.front, cv.uid("g"), x=x, y=y)
        keys = [(cut, 1.0), (cut + 0.9, 1.0), (cut + 1.2, 0.06), (cut + 1.5, 1.0)]
        cv.keys(turn, "scaleX", keys, kind="sine-in-out", local=False)
        collage_home.pay_envelope(cv, turn, 0, 0, w)


def dress(shot) -> None:
    """The room, the booth, and Priya's phone at her ear in her close."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    close = _said(beats, 11)
    if app.who == "brent":
        cut = events(beats, "sting")[0][0]
        _booth(cv, shot, cut if app.start >= cut else None)
    elif app.start < close:
        _sofa(cv, shot.front, beats)
    else:
        collage_everyday.phone(cv, shot.front, 730, 1110, 150, 270, screen="#17151f", tilt=9.0)
    if app.start < HOOK_SECONDS:
        collage_home.hook_card(cv, shot.front, HOOK, ROOM, shot.measure, start=0.0, seconds=HOOK_SECONDS)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"priya": ROOM, "deb": ROOM, "brent": BOOTH},
    dress=dress,
    cast=casting,
    bleed=True,
    bitrate=BITRATE,
    keep_signature=True,
    loudness="-14",
)

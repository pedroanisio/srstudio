"""Your Lasagna — the sketch as data: Gary told a widow he was sorry for her lasagna. He fixes it; the phone fixes it
worse: he was a great lasagna. She wrote back: bring him Saturday. So he does, an enormous lasagna on both arms, to a
silent table. Deb takes it, looks down, and says he looks so peaceful.

Collage style (ADR 0026): the mistake turns real, and the widow takes it further than he did. The reel opens on
Gary alone, silent and uncaptioned, the shot drifting in on his face for the first STILL seconds.
ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import camera, collage, collage_everyday, collage_sets
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 3105
SLUG = "your-lasagna"
TITLE = "Your Lasagna — Gary, Priya and Deb (Collage)"
NAMES = ("gary", "priya", "deb")
HOME = "living-room"
WAKE = "dining-room"
DESCRIPTION = (
    "A Collage sketch: Gary's condolence autocorrects to lasagna, the fix makes it worse, the widow answers, and on "
    "Saturday he carries an enormous lasagna into the wake."
)
ACCESSIBILITY = (
    "Paper cut-out characters: a man sits frozen on a sofa. A woman reads from his phone that he is sorry for a "
    "widow's lasagna. He sends a correction, which comes out worse. A reply arrives: thank you, bring him Saturday. "
    "At a silent wake, he stands with an enormous lasagna and everyone looks at him. A woman takes it, looks down "
    "and says he looks so peaceful. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; a synthesized whoosh and ping."
NOTE = "ElevenLabs premade voices Chris, Sarah and Jessica at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB

STILL = 1.2  # the seconds of Gary alone, silent, before the cut
DRIFT = 1.06  # the opening drifts in this far on his face
SOFA_PLACES = {"priya": Place(300.0, 1900.0, 0.8), "gary": Place(790.0, 1900.0, 0.8)}
WAKE_PLACES = {
    "jun": Place(150.0, 1800.0, 0.5),
    "omar": Place(350.0, 1800.0, 0.5),
    "deb": Place(550.0, 1800.0, 0.5),
    "gary": Place(840.0, 1820.0, 0.68),
}
SOFA = dict(w=170.0, h=300.0)  # the phone as Priya holds it
SCREEN = dict(x=190.0, y=560.0, w=700.0, h=1200.0)
KEYBOARD = 860.0  # how far down the screen its keyboard starts  # the phone as we read it
CARRIED = dict(x=800.0, y=1580.0, w=540.0, tilt=-3.0)
HANDED = dict(x=540.0, y=1590.0, w=720.0, tilt=2.0)
TEARS = (0.0, 4.0, -3.0, 5.0, -4.0, 3.0, 0.0)  # how far Deb's chin trembles

LINES = (
    Line("priya", "So sorry for your lasagna."),
    Line("gary", "Loss. I typed loss."),
    Line("priya", "To a widow, Gary."),
    Line("gary", "I'll fix it."),
    Line("priya", "I meant lasagna. He was a great lasagna."),
    Line("gary", "I did not type that!"),
    Line("priya", "She wrote back."),
    Line("gary", "What does she say?"),
    Line("priya", "Thank you. Bring him Saturday."),
    Line("deb", "He looks so peaceful."),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "gary", "", "wide", "frown", "hold"),
        (1.8, "priya", 0, "side", "flat", "hold"),
        (1.3, "gary", 1, "angry", "frown", "shrug"),
        (1.8, "priya", 2, "side", "flat", "hold"),
        (0.8, "gary", 3, "open", "smile", "point"),
        (0.7, "gary", "", "half", "flat", "point", "swat"),  # one finger; sent
        (2.6, "priya", 4, "wide", "flat", "hold", "reveal:insert"),
        (1.15, "gary", 5, "wide", "frown", "shrug"),
        (1.2, "gary", "", "side", "flat", "down", "ding"),  # they both look at it
        (1.05, "priya", 6, "side", "flat", "hold", "reveal:wrote"),
        (0.85, "gary", 7, "wide", "frown", "down"),
        (2.0, "priya", 8, "side", "flat", "hold", "reveal:reply"),
        (1.2, "gary", "", "wide", "frown", "down", "reveal:face"),
        (1.0, "omar", "", "half", "flat", "down", "reveal:wake"),
        (1.4, "omar", "", "side", "flat", "down"),  # the table turns
        (1.6, "deb", 9, "sad", "frown", "hold", "reveal:medium"),
        (1.5, "gary", "", "wide", "flat", "down"),
    ),
    tail=0.3,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": start, "eyes": eyes, "mouth": mouth, "arms": arms}


def setting(beats: Sequence[Beat], app: Appearance) -> str:
    """The sofa, until Saturday."""
    return WAKE if app.start >= _at(beats, "wake") else HOME


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Two on the sofa, Gary's face alone, then the wake's table turning to him; Deb and Gary alone after it."""
    face, wake, medium = (_at(beats, n) for n in ("face", "wake", "medium"))
    turned = wake + 1.0
    sofa = Lineup(
        SOFA_PLACES,
        {
            "priya": [_pose(0.0, "side", "flat", "hold")],
            "gary": [_pose(0.0, "wide", "frown", "down"), _pose(events(beats, "ding")[0][0], "side", "flat", "down")],
        },
        ((STILL, face),),
    )
    room = {
        name: [_pose(0.0, "half", "flat", "down"), _pose(turned, "side", "flat", "down")]
        for name in ("jun", "omar", "deb")
    }
    table = Lineup(WAKE_PLACES, {**room, "gary": [_pose(0.0, "wide", "flat", "hold")]}, ((wake, medium),))

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start < STILL:
            head = solo(cv, parent, app, mouths)
            camera.anchor(parent, *head, place=True)
            camera.push_in(cv, parent, scale=[(0.0, 1.0), (app.end, DRIFT)])
            return head
        if app.start >= wake and app.start < medium:
            return table(cv, parent, app, mouths)
        if app.start < face:
            return sofa(cv, parent, app, mouths)
        if app.who == "deb":
            shaken = cv.group(parent, cv.uid("g"))
            step = (app.end - app.start) / (len(TEARS) - 1)
            cv.keys(shaken, "y", [(app.start + i * step, y) for i, y in enumerate(TEARS)], local=False)
            return solo(cv, shaken, app, mouths)
        return solo(cv, parent, app, mouths)

    return draw


def _gated(cv, parent, a: float, b: float):
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(a, b)])
    return g


def _screen(cv, parent, *messages: tuple[str, float, bool]) -> None:
    """The phone, close, with ``(text, top, mine)`` for each message on it."""
    screen = collage_everyday.phone(cv, parent, **SCREEN)
    for text, top, mine in messages:
        collage_everyday.bubble(cv, screen, text, 30.0 if not mine else 78.0, top, 540.0, 230.0, size=52, mine=mine)
    cv.rect(screen, 0.0, KEYBOARD, SCREEN["w"] - 2 * collage_everyday.BEZEL, 288.0, "#e6e2ec")
    for row in range(3):
        cv.rect(screen, 40.0, KEYBOARD + 32.0 + row * 84.0, 568.0, 60.0, "#fffaf0", radius=12.0)


def dress(shot) -> None:
    """The sofa and Priya's phone, the phone read close, the wake and what Gary carried to it."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    if app.start < STILL:
        return
    face, wake, medium = (_at(beats, n) for n in ("face", "wake", "medium"))
    if app.start < wake:
        cv.rect(shot.back, 30.0, 1400.0, 1020.0, 520.0, "#7a4b3a", collage.INK, 7.0, radius=70.0)
    if app.start < face:
        collage_everyday.phone(cv, shot.front, 215.0, 1425.0, tilt=-6, **SOFA)
        sorry = ("So sorry for your lasagna.", 30.0, True)
        worse = ("I meant lasagna. He was a great lasagna.", 290.0, True)
        insert = _at(beats, "insert")
        if app.start <= insert < app.end:
            _screen(cv, _gated(cv, shot.front, insert, app.end), sorry, worse)
        reply = _at(beats, "reply")
        if app.start <= reply < app.end:
            answer = ("Thank you. Bring him Saturday.", 570.0, False)
            _screen(cv, _gated(cv, shot.front, reply, app.end), sorry, worse, answer)
    if wake <= app.start < medium:
        collage_sets.sign(
            cv, shot.back, "IN LOVING MEMORY", 240, 800, 600, 110, size=52, fill="#2b2d42", color="#fffaf0"
        )
        collage_everyday.tablecloth(cv, shot.front, top=1640.0)
        collage_everyday.lasagna(cv, shot.front, **CARRIED)
    if app.who == "deb":
        collage_everyday.lasagna(cv, shot.front, **HANDED)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": HOME, "priya": HOME, "deb": WAKE, "omar": WAKE},
    dress=dress,
    cast=casting,
    setting=setting,
    bitrate=BITRATE,
)

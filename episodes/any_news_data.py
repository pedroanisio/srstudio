"""Any News — the sketch as data: family dinner is a press conference about Brent's life, with a gravy boat for a
podium, and the only way out is to give them a sibling. The boat travels down the table to whoever has been sold out.

Collage style (ADR 0026), the dining room; a single for each of them across the table, a two-shot for the last word.
One flash per question, never a strobe (``collage_sketch.check_flashes``). The reel moves from its first frame (the
sp-hook_motion test's arm b). ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_everyday, collage_photo, collage_sets, collage_things
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import (
    TINTS,
    ZOOM_SCALE,
    CastDrawer,
    Staging,
    make_sketch,
    solo,
    stilled,
    timed,
    voices_note,
)
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 3130
SLUG = "any-news"
TITLE = "Any News — Brent, Gary, Rosa and Deb (Collage)"
NAMES = ("deb", "brent", "rosa", "gary")
ROOM = "dining-room"
DESCRIPTION = (
    "A Collage sketch: family dinner as a press conference, forks taped round a gravy boat, and the only way out is "
    "to give them your sibling."
)
ACCESSIBILITY = (
    "Paper cut-out characters at a dinner table. A gravy boat with forks taped round it sits under a man's chin like "
    "a bank of microphones, and a camera flash goes off as his aunt and mother question him. He gives up his brother, "
    "and the boat slides down the table to him; he gives up his mother, and it slides to her. She does not blink. "
    "She puts down her glass and tells them what happened to the dog. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}."
NOTE = "ElevenLabs premade voices Jessica, Brian, Matilda and Chris at their natural pace; no reference-voice cloning."
BITRATE = 5_500_000  # two passes: a master under 20 MB

BOAT = dict(y=1800.0, size=430.0)
BOAT_X, OFF_LEFT, OFF_RIGHT = 540.0, -460.0, 1540.0
ARRIVE = 0.3  # seconds a boat takes to land in front of someone
FLASH_HOLD, FLASH_FADE = 0.04, 0.22  # a flashbulb: a frame of white, gone in a quarter of a second
LEAN = (46.0, 0.4)  # px and seconds of leaning into the forks
GLASS_HELD, GLASS_DROP = (300.0, 1330.0), 290.0  # where her glass is, how far down the table is
TWO = {"brent": Place(285.0, 1640.0, 0.72), "gary": Place(800.0, 1640.0, 0.72)}
TWO_TABLE = 1340.0
LOWERED = 300.0  # px the forks come down

LINES = (
    Line("deb", "Are you seeing anyone?"),
    Line("brent", "No comment."),
    Line("rosa", "Follow-up. Why not?"),
    Line("brent", "Next question."),
    Line("deb", "How much do they pay you?"),
    Line("brent", "We're not discussing that at this time."),
    Line("rosa", "Your cousin has twins."),
    Line("brent", "Gary quit his job."),
    Line("rosa", "Gary?"),
    Line("gary", "Mom's selling the house."),
    Line("rosa", "The dog did not go to a farm."),
    Line("brent", "Rufus?"),
)
BEATS, END = timed(
    LINES,
    (
        (0.6, "brent", (0, 0, "Are you seeing"), "wide", "flat", "hold"),  # off screen, her voice; the boat arrives
        (1.1, "brent", (0, 3, "anyone?"), "wide", "flat", "hold", "flash"),
        (1.2, "brent", 1, "half", "flat", "hold"),
        (0.8, "rosa", (2, 0, "Follow-up."), "half", "smile", "hold"),
        (0.6, "brent", (2, 1, "Why not?"), "wide", "frown", "hold", "flash"),
        (1.0, "brent", 3, "half", "flat", "hold"),
        (1.2, "deb", 4, "open", "smile", "hold"),
        (1.8, "brent", 5, "half", "flat", "hold", "flash"),
        (1.45, "rosa", 6, "half", "smile", "hold"),
        (1.95, "brent", "", "side", "flat", "hold", "reveal:slide"),  # his eyes go down the table
        (1.4, "brent", 7, "open", "smile", "hold"),
        (0.55, "brent", "", "open", "smug", "down", "hiss:0.4"),
        (0.3, "gary", "", "open", "flat", "hold", "zoom"),  # mouth full
        (0.7, "gary", "", "wide", "flat", "hold", "flash"),
        (0.75, "rosa", 8, "wide", "o", "hold"),
        (0.7, "gary", "", "half", "flat", "hold", "reveal:swallow"),
        (1.3, "gary", 9, "open", "smug", "hold"),
        (0.5, "gary", "", "open", "smug", "down", "hiss:0.4"),
        (0.3, "rosa", "", "open", "flat", "hold", "reveal:still"),
        (2.6, "rosa", "", "open", "flat", "hold", "flash"),  # she does not blink
        (1.85, "rosa", 10, "half", "flat", "hold"),
        (1.7, "brent", "", "wide", "frown", "hold", "reveal:forks"),
        (0.9, "brent", 11, "wide", "frown", "hold"),
        (0.7, "brent", "", "wide", "frown", "hold", "sting"),
    ),
    tail=0.7,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(start, 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """A single each; Gary chewing until he has swallowed; Rosa frozen until she speaks; the brothers side by side."""
    slide, still, forks = _at(beats, "slide"), _at(beats, "still"), _at(beats, "forks")
    swallow, zoom = _at(beats, "swallow"), events(beats, "zoom")[0][0]
    speak = next(b.start for b in beats if b.line == 10)
    two = Lineup(
        TWO, {"brent": [_pose(0, "wide", "frown", "hold")], "gary": [_pose(0, "wide", "flat", "hold")]}, ((forks, end),)
    )

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if two.staged(app):
            return two(cv, parent, app, mouths)
        if app.start == still:
            frozen = cv.group(parent, cv.uid("g"))
            cv.gate(frozen, [(still, speak)])
            stilled(cv, frozen, Appearance(app.who, still, speak, app.poses), mouths)
            talking = cv.group(parent, cv.uid("g"))
            cv.gate(talking, [(speak, app.end)])
            return solo(cv, talking, app, mouths)
        if app.start <= slide < app.end:
            leaning = cv.group(parent, cv.uid("g"))
            line = next(b.start for b in beats if b.line == 7)
            cv.keys(leaning, "y", [(line - LEAN[1], 0.0), (line, LEAN[0])], kind="sine-in-out", local=False)
            return solo(cv, leaning, app, mouths)
        if app.start <= zoom < app.end:
            chewing = {**mouths, "gary": collage_everyday.chew(mouths.get("gary", ()), app.start, app.end)}
            return collage_sets.zoom_pivot(ROOM, solo(cv, parent, app, chewing), ZOOM_SCALE)
        if app.start < swallow < app.end:
            chewing = {**mouths, "gary": collage_everyday.chew(mouths.get("gary", ()), app.start, swallow + 0.3)}
            return solo(cv, parent, app, chewing)
        return solo(cv, parent, app, mouths)

    return draw


def _boat(shot, enter: tuple[float, float] | None, leave: float | None) -> None:
    """The boat under this shot's chin: sliding in from one side when ``enter`` gives where and when, and out the
    other at ``leave``."""
    cv, app, front = shot.cv, shot.app, shot.front
    keys = [(app.start, BOAT_X)]
    if enter is not None:
        keys = [(enter[1], enter[0]), (enter[1] + ARRIVE, BOAT_X)]
    if leave is not None:
        keys += [(leave, BOAT_X), (leave + 0.4, OFF_RIGHT)]
    boat = collage_things.gravy_boat(cv, front, BOAT_X, **BOAT)
    cv.keys(boat, "x", keys, kind="sine-in-out", local=False)


def _holding(shot, who: str, thing: str) -> None:
    """One hand up at the table, with a fork or a wine glass in it."""
    cv, front = shot.cv, shot.front
    collage_everyday.arm(cv, front, who, (170.0, 2060.0), (GLASS_HELD[0] + 10.0, GLASS_HELD[1] + 40.0))
    if thing == "fork":
        collage_things.fork(cv, front, GLASS_HELD[0] + 10.0, GLASS_HELD[1] + 40.0, 300.0, tilt=-6.0)
    else:
        collage_things.wine_glass(cv, front, *GLASS_HELD, 300.0)


def _glass_down(shot, at: float) -> None:
    """Rosa's glass, put down: nothing else in the reel is as slow."""
    cv, front = shot.cv, shot.front
    hand = cv.group(front, cv.uid("g"))
    cv.keys(hand, "y", [(at, 0.0), (at + 0.8, GLASS_DROP)], kind="sine-in-out", local=False)
    collage_everyday.arm(cv, hand, "rosa", (170.0, 2060.0), (GLASS_HELD[0] + 10.0, GLASS_HELD[1] + 40.0))
    collage_things.wine_glass(cv, hand, *GLASS_HELD, 300.0)


def _forks(shot) -> None:
    """The table in the two-shot, and two forks stopped halfway up, coming down."""
    cv, app, front = shot.cv, shot.app, shot.front
    collage_everyday.tablecloth(cv, front, TWO_TABLE)
    down = (app.start + 0.5, app.start + 1.4)
    both = cv.group(front, cv.uid("g"))
    cv.keys(both, "y", [(down[0], 0.0), (down[1], LOWERED)], kind="sine-in-out", local=False)
    collage_everyday.arm(cv, both, "brent", (40.0, 2040.0), (430.0, 1400.0), width=60.0)
    collage_things.fork(cv, both, 430.0, 1400.0, 260.0)
    collage_everyday.arm(cv, both, "gary", (1040.0, 2040.0), (650.0, 1400.0), width=60.0)
    collage_things.fork(cv, both, 650.0, 1400.0, 260.0)


def dress(shot) -> None:
    """The table, the boat and whatever each of them holds; a flash on each flash beat of the shot."""
    cv, app, beats, front = shot.cv, shot.app, shot.beats, shot.front
    hisses = [t for t, _ in events(beats, "hiss")]
    still, forks = _at(beats, "still"), _at(beats, "forks")
    zoom = events(beats, "zoom")[0][0]
    leaving = next((t for t in hisses if app.start <= t < app.end), None)
    if app.start == forks:
        _forks(shot)
        return
    collage_everyday.tablecloth(cv, front)
    if app.who == "brent":
        _boat(shot, (OFF_RIGHT, 0.0) if app.start == 0.0 else None, leaving)
    elif app.who == "gary":
        _boat(shot, (OFF_LEFT, app.start) if app.start == zoom else None, leaving)
    elif app.who == "deb":
        _holding(shot, "deb", "fork")
    elif app.start == still:
        flash = next(t for t, _ in events(beats, "flash") if t >= still)
        _boat(shot, (OFF_LEFT, still), None)
        _glass_down(shot, flash + 0.7)
    else:
        _holding(shot, "rosa", "glass")
    for t, _ in events(beats, "flash"):
        if app.start <= t < app.end:
            collage_photo.flash(cv, front, t, hold=FLASH_HOLD, fade=FLASH_FADE)


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

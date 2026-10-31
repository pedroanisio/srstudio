"""Fitted sheet: the sketch as data. Mae asks her mother how to fold a fitted sheet. Her mother asks who sent her, takes
the key from round her neck and opens the closet. Balled sheets bury Mae to the waist. Every woman she has ever met.
Bruno comes in with a perfectly square sheet. Who sent you?

Toon, ElevenLabs premade Sarah (Mae), Lily (her mother) and Bill (Bruno). It opens moving: the sheet is already
winning. :func:`dress` draws the hall, the closet and the sheets.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley, scripting, sketch, toon_flat, toon_house, toon_odds, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3107
SLUG = "fitted-sheet"
TITLE = "Fitted sheet (Toon)"
DESCRIPTION = "A daughter asks how to fold a fitted sheet, and is told the truth at last."
ACCESSIBILITY = (
    "A cartoon rabbit fights a fitted sheet and asks her mother, a hedgehog, how to fold it. Her mother asks who sent "
    "her, takes a key from her neck and unlocks a closet. Balled-up sheets pour out and bury the rabbit to the waist. "
    "Every woman you have ever met, says her mother. A bear walks in holding a perfectly square folded sheet. Her "
    "mother turns: who sent you?"
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae), Lily (her mother) and Bill (Bruno); synthesised foley."
NOTE = "ElevenLabs premade voices Sarah, Lily and Bill at their natural pace; no reference-voice cloning."
MAE = Speaker(
    "mae", Voice(role="mae", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"), VoiceSettings(0.6, 0.75, 0.2), "rabbit"
)
MOM = Speaker(
    "mom", Voice(role="mom", id="pFZP5JQG7iQjIQuC4Bku", name="Lily"), VoiceSettings(0.65, 0.75, 0.15), "hedgehog"
)
BRUNO = Speaker(
    "bruno", Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"), VoiceSettings(0.5, 0.75, 0.3), "bear"
)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
TINTS = {"mae": "#f9dbe6", "mom": "#e5d9c9", "bruno": "#eccfae"}
KEY_LINE = "How do you fold a fitted sheet?"
HEDGEHOG_COAT = "#c9a88a"
FLAP = foley.Burst(0.22, 1800.0, attack=0.01, decay=0.5)
AVALANCHE = foley.Burst(2.2, 500.0, attack=0.15, decay=0.5)
EVENTS = {"wrestle", "latch", "key", "open", "bruno"}
SHEET_TOP = 700.0
BRUNO_SHEETS = 800.0
END = 21.6

LINES = (
    Line("mae", "Mom, how do you fold a fitted sheet?"),
    Line("mom", "Who sent you?"),
    Line("mae", "Nobody. There's a video."),
    Line("mom", "You're thirty-four. It's time."),
    Line("mom", "My mother showed me. Her mother showed her."),
    Line("mom", "We ball it up. We shove it in."),
    Line("mae", "All of them?"),
    Line("mom", "Every woman you have ever met."),
    Line("bruno", "Hey, I folded the sheet."),
    Line("mom", "Who sent you?"),
)
SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold
BEATS = (
    first(0.0, "rabbit", 0, "Mom, how do you fold", "wince", "grimace", "desk", "wrestle"),
    part(1.2, "rabbit", 0, 5, "a fitted sheet?", "wince", "grimace", "desk"),
    say(2.4, "hedgehog", 1, "narrow", "flat", "desk"),
    say(3.5, "rabbit", 2, "side", "flat", "desk"),
    hold(5.0, "hedgehog", "", "narrow", "flat", "desk", "latch"),
    say(5.8, "hedgehog", 3, "half", "flat", "desk"),
    first(7.8, "hedgehog", 4, "My mother showed me.", "closed", "flat", "desk"),
    part(9.1, "hedgehog", 4, 4, "Her mother showed her.", "half", "flat", "desk"),
    hold(10.6, "hedgehog", "", "half", "flat", "desk", "key"),
    hold(12.0, "hedgehog", "", "half", "flat", "desk", "open"),
    say(12.5, "hedgehog", 5, "half", "smirk", "desk"),
    say(14.5, "rabbit", 6, "shock", "flat", "desk"),
    say(15.5, "hedgehog", 7, "closed", "flat", "desk"),
    hold(17.4, "bear", "", "wide", "grin", "desk", "bruno"),
    say(17.6, "bear", 8, "wide", "grin", "desk"),
    hold(19.1, "rabbit", "", "side", "flat", "desk"),
    say(19.9, "hedgehog", 9, "narrow", "flat", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (MAE, MOM, BRUNO), LINES, BEATS, END)


def event(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """The key before the door, the door before the avalanche's line, Bruno after all of it."""
    sketch.check(sk)
    scripting.only_events(sk.beats, EVENTS)
    for kind in EVENTS:
        scripting.exactly_once(sk.beats, kind, f"one {kind}")
    if not event(sk.beats, "key") < event(sk.beats, "open") < event(sk.beats, "bruno"):
        raise sketch.SketchError("the key, the door, then Bruno")


def dress(shot) -> None:
    """The hall; the sheet she is fighting; the closet behind her mother; the sheets once it opens."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    opened, key = event(beats, "open"), event(beats, "key")
    toon_house.hallway(cv, shot.back, door="none")
    if app.who == "hedgehog":
        toon_flat.closet(cv, shot.back, opened if opened > app.start else 0.5)
    toon_house.ledge(cv, shot.front, "oak")
    if app.who == "rabbit" and app.end <= opened:
        toon_odds.wrestled_sheet(cv, shot.front, app.start, app.end)
    if app.who == "hedgehog" and app.start < opened:
        toon_odds.padlock(cv, shot.back, (372.0, 560.0), app.start, min(opened, app.end), app.end)
        if app.start <= key < app.end:
            toon_world.paw(cv, shot.front, ((key, opened + 0.3),), HEDGEHOG_COAT, y=590.0, reach=240.0, holding="keys")
    if app.who == "bear":
        toon_odds.balled_sheets(cv, shot.front, BRUNO_SHEETS, None, app.end)
        toon_odds.folded_sheet(cv, shot.front, (190.0, 830.0), "#a9744f", app.start, app.end)
    if app.who != "bear" and app.end > opened:
        rise = opened if app.start <= opened < app.end - toon_odds.SHEETS_RISE else None
        toon_odds.balled_sheets(cv, shot.front, SHEET_TOP, rise, app.end)
    if app.start == 0:
        toon_house.key_line(cv, shot.front, KEY_LINE, 0.0, 2.3, measure=shot.measure)


def sounds(beats, end: float) -> list[Sound]:
    """Cloth while she fights it, the latch, the padlock, the sheets, the door and a small sting."""
    return [
        Sound("flap", FLAP, (0.3, 1.0, 1.7), -9.0),
        Sound("latch", foley.REMOTE_CLICK, (event(beats, "latch"), event(beats, "key") + 1.0), -6.0),
        Sound("avalanche", AVALANCHE, (event(beats, "open"),), -7.0),
        Sound("door", foley.KNOCK, (event(beats, "bruno"),), -9.0),
    ]


STAGING_ARGS = dict(
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
    desk=toon_world.no_desk,
)

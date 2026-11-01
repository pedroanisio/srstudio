"""Full Coverage — the sketch as data: a rental agent makes you feel you are endangering your family by declining
twenty-nine dollars a day, and he does it by being allowed to say nothing. "I was told about the seagull." The customer
caves. In the lot, one small car, and on its roof one gull, facing him.

Two voices (ElevenLabs premade Brian as the agent, Bill as the customer). It opens on the agent's question under a
tube already flickering (the ``sp-hook_motion`` test's arm B). ``SKETCH`` is checked by :func:`srstudio.sketch.check`;
:func:`validate` checks what the events ask of the props; :func:`dress` draws each shot and :func:`sounds` the room.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    foley,
    scripting,
    sketch,
    toon,
    toon_cars,
    toon_everyday,
    toon_house,
    toon_inserts,
    toon_rooms,
    toon_world,
)
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3112
SLUG = "full-coverage"
TITLE = "Full Coverage — The Rental Counter (Toon)"
DESCRIPTION = (
    "A Toon sketch at a car rental counter: the customer declines full coverage, and the agent, who is not allowed "
    "to say why, tells him about the gull."
)
ACCESSIBILITY = (
    "A cartoon goat at a rental counter under a flickering light asks a cartoon bear about full coverage. The bear "
    "says no thanks. The goat stares, writes something down, says he is not allowed to say what happens, and asks "
    "him to initial that he was told about the gull. A light goes out and the goat says twenty nine a day. The bear "
    "buys it. In the sunny lot a small car waits with one gull on its roof. Close on the gull, it turns its head "
    "until one yellow eye looks straight at him."
)
NARRATION = "Voiced with ElevenLabs premade voices Brian (the agent) and Bill (the customer); synthesized effects."
NOTE = "ElevenLabs premade voices Brian and Bill at their natural pace; no reference-voice cloning."
VOICE_GOAT = Voice(role="goat", id="nPczCjzI2devNBz1zQrb", name="Brian")
GOAT = Speaker("goat", VOICE_GOAT, VoiceSettings(stability=0.7, similarity_boost=0.75, style=0.1), "goat")
GOAT_LOW = Speaker("goat-low", VOICE_GOAT, VoiceSettings(stability=0.9, similarity_boost=0.75, style=0.0, speed=0.85))
BEAR = Speaker(
    "bear",
    Voice(role="bear", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.2),
    "bear",
)
TINTS = {"goat": "#e6e0d0", "goat-low": "#e6e0d0", "bear": "#ead2b8", "hamster": "#ffffff"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

WIDE = "hamster"  # never seen: the name of the shots the dress draws whole
FIGURES = {"goat": (1.1, 30.0), "bear": (1.0, 0.0)}
BOARD = {"at": (424, 826), "scale": 1.1, "hand": "#e6e0d0"}
CAR = {"at": (320.0, 905.0), "scale": 1.3}
ROOF = (330.0, 745.0)  # where the gull stands on it
LOT = "#b8b2a6"
FLICKER = 1.3  # seconds of one stutter
KEY = "#c9a23c"
SETTLE = 0.3  # seconds the keys take to slide over
END = 28.85

LINES = (
    Line("goat", "Full coverage?"),
    Line("bear", "No thanks."),
    Line("goat", "Sure."),
    Line("goat", "Will you be driving it?"),
    Line("bear", "Yes?"),
    Line("bear", "Why, what happens?"),
    Line("goat", "I'm not allowed to say."),
    Line("goat", "Initial here. I was told about the seagull."),
    Line("bear", "What seagull?"),
    Line("goat-low", "$29 a day."),
    Line("bear", "Full coverage."),
    Line("goat", "Smart."),
)

script = scripting.Script(LINES)
hold, say, first, part = script.hold, script.say, script.first, script.part

BEATS = (
    say(0.0, "goat", 0, "half", "flat", "desk"),
    say(1.15, "bear", 1, "half", "grin", "desk"),
    say(2.11, "goat", 2, "half", "flat", "desk"),
    hold(2.85, "goat", "", "narrow", "flat", "desk", "stare"),  # he does not move
    say(4.85, "goat", 3, "narrow", "flat", "desk"),
    say(6.15, "bear", 4, "wide", "flat", "desk"),
    hold(6.93, "goat", "", "down", "flat", "desk", "write"),  # slowly
    say(8.43, "bear", 5, "wide", "o", "desk"),
    say(9.87, "goat", 6, "half", "flat", "desk"),
    first(11.22, "goat", 7, "Initial here.", "down", "flat", "desk", "form"),
    part(12.22, "goat", 7, 2, "I was told about the seagull.", "half", "flat", "desk"),
    say(14.53, "bear", 8, "shock", "open", "desk", wear=("sweat",)),
    hold(15.61, "goat", "", "narrow", "flat", "lean", "out"),  # half the counter goes dark, he leans into what is left
    say(17.01, "goat", 9, "narrow", "flat", "lean"),
    hold(18.62, "bear", "", "down", "flat", "desk", wear=("sweat",)),  # he looks at the pen
    say(20.12, "bear", 10, "wince", "flat", "desk", wear=("sweat",)),
    say(21.15, "goat", 11, "half", "smirk", "desk"),
    hold(21.85, "bear", "", "down", "flat", "desk", "keys", wear=("sweat",)),
    hold(22.85, WIDE, "", "wide", "flat", "desk", "lot"),
    hold(25.25, WIDE, "", "wide", "flat", "desk", "turn"),
)
SKETCH = Sketch(SLUG, TITLE, (GOAT, GOAT_LOW, BEAR), LINES, BEATS, END, bare=(WIDE,))
ORDER = ("stare", "write", "form", "out", "keys", "lot", "turn")


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks within 0.3 s, and the room's steps come once each and in order."""
    sketch.check(sk)
    if sk.beats[0].line != 0 or sk.beats[0].start > 0.3:
        raise sketch.SketchError("the sketch's first line is spoken within 0.3 s")
    for event in ORDER:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    times = [sketch.events(sk.beats, event)[0][0] for event in ORDER]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {ORDER}")
    scripting.only_events(sk.beats, set(ORDER))


def at(shot, event: str) -> float:
    return sketch.events(shot.beats, event)[0][0]


def lights(shot) -> dict:
    """The tube stutters from the first frame, settles, stutters through his stare, and goes for good."""
    stare, out = at(shot, "stare"), at(shot, "out")
    tubes = ((0, "flicker"), (1.3, "on"), (stare, "flicker"), (stare + 2 * FLICKER, "on"), (out, "flicker"),
             (out + FLICKER, "dim"))  # fmt: skip
    return {"tubes": tubes, "board": ((0, "on", "red"),)}


def counter(shot) -> None:
    cv, app = shot.cv, shot.app
    toon_rooms.dress(shot, "counter", lights(shot))
    toon_house.ledge(cv, shot.front)
    if app.who == "goat":
        fields = [
            toon_everyday.Field("Driver", "Yes?", at(shot, "write")),
            toon_everyday.Field("Told", "gull", at(shot, "form")),
        ]
        toon_everyday.clipboard(cv, shot.front, "RENTAL", fields, measure=shot.measure, id=cv.uid("board"), **BOARD)
    if app.start <= at(shot, "keys") < app.end:
        keys(shot, at(shot, "keys"))


def keys(shot, start: float) -> None:
    """The keys come in along the counter from the right and stop by his hand."""
    cv = shot.cv
    slide = cv.group(shot.front, cv.uid("g"), start=start, x=0.0, y=0.0)
    cv.keys(slide, "x", [(start, toon.fh(300)), (start + SETTLE, 0.0)], kind="cubic-out", local=False)
    x, y = toon.fx(340.0), toon.fy(822.0)
    cv.ellipse(slide, x, y, toon.fh(34), toon.fh(34), "#00000000", cv.ink, 5.0)
    cv.rect(
        slide,
        x + toon.fh(30),
        y + toon.fh(10),
        toon.fh(60),
        toon.fh(14),
        KEY,
        cv.ink,
        toon.FINE_W / 2,
        radius=toon.fh(3),
    )


def lot(shot) -> None:
    """The lot in daylight: one small car, one gull on its roof, facing him, and him in the near corner, stopped."""
    cv, app = shot.cv, shot.app
    toon_world.yard(cv, shot.back, sign=None, table=False)
    cv.rect(shot.back, toon.fx(-10), toon.fy(896), toon.fh(612), toon.fh(320), LOT, cv.ink, toon.FINE_W, radius=0)
    toon_world.marks(cv, shot.back)
    toon_cars.side_car(cv, shot.front, **CAR)
    toon_world.gull(cv, shot.front, at=ROOF, land=app.start, end=shot.end)
    poses = toon.parse_poses([{"start": 0.0, "eyes": "wide", "mouth": "flat", "arms": "desk"}], "him in the lot")

    def draw(g) -> None:
        sketch.drawer("bear", shot.versions)(cv, g, poses, app.end, (), enter=app.start)

    toon_world.placed(cv, shot.front, (90.0, 1130.0), 0.8, draw)


def close(shot) -> None:
    """The gull's head against the sky, the roof under it, and the turn."""
    cv = shot.cv
    turn = at(shot, "turn")
    toon_world.yard(cv, shot.back, sign=None, table=False)
    cv.rect(
        shot.back, toon.fx(-10), toon.fy(838), toon.fh(612), toon.fh(380), toon_cars.BODY, cv.ink, toon.FINE_W, radius=0
    )
    toon_world.marks(cv, shot.back)
    toon_inserts.gull_stare(cv, shot.front, at=(296.0, 560.0), turn=turn + 0.7, seconds=2.0, end=shot.end)


def dress(shot) -> None:
    """The counter, then the two shots drawn whole."""
    if shot.app.who != WIDE:
        counter(shot)
        return
    turn = at(shot, "turn")
    back, front = shot.back, shot.front
    cv = shot.cv
    wide_back, wide_front = cv.group(back, cv.uid("g"), end=turn), cv.group(front, cv.uid("g"), end=turn)
    close_back, close_front = cv.group(back, cv.uid("g"), start=turn), cv.group(front, cv.uid("g"), start=turn)
    shot_wide = replace(shot, back=wide_back, front=wide_front)
    shot_close = replace(shot, back=close_back, front=close_front)
    lot(shot_wide)
    close(shot_close)


def sounds(beats, end) -> tuple[Sound, ...]:
    """The tube's tick as it dies, the pen, the keys, and the one call the gull has been saving."""
    out = sketch.events(beats, "out")[0][0]
    write = sketch.events(beats, "write")[0][0]
    keys_at = sketch.events(beats, "keys")[0][0]
    turn = sketch.events(beats, "turn")[0][0]
    return (
        Sound("tube", foley.REMOTE_CLICK, (out, out + 0.3, out + 0.36, out + 0.9), -6.0),
        Sound("pen", foley.SCRAPE, (write + 0.2, write + 0.7), -10.0),
        Sound("keys", foley.PLATES, (keys_at,), -8.0),
        Sound("gull", foley.GULL, (turn + 3.0,), -6.0),
    )

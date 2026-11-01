"""It Autoplayed — the sketch as data: one person in every couple has watched ahead on the show you promised to watch
together, and gives it away by reacting too soon.

Mae and Bruno are on the sofa, two episodes in. He gasps before the door. He raises his hands late at the sting,
comforts her before anything has happened, and tells her the dog is fine. There has been no dog. She clicks to the TV's
own menu, and it convicts him.

Two voices (ElevenLabs premade Sarah as Mae, Bill as Bruno). They face us, so the TV is on our side of the frame: the
lounge's own TV is taken out of the room and its light falls on the shot (:func:`srstudio.toon_rooms.front_screen`),
one cue per thing that happens on a show we never see. ``ROWS`` act them per beat; :func:`dress` draws the framings and
the menu (:func:`srstudio.toon_everyday.tv_menu`), :func:`overlay` the bar and :func:`sounds` the room.
"""

from __future__ import annotations

from dataclasses import replace
from math import ceil

from srstudio import (
    foley,
    look,
    scripting,
    signature,
    sketch,
    toon_bed,
    toon_everyday,
    toon_house,
    toon_pair,
    toon_rooms,
    toon_voices,
    toon_world,
)
from srstudio.scripting import at
from srstudio.sketch import Line, Sketch
from srstudio.toon import fy
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound

MOUTH = toon_voices.MOUTH
SEED = 3422
SLUG = "it-autoplayed"
TITLE = "It Autoplayed — Mae and Bruno (Toon)"
DESCRIPTION = (
    "A Toon sketch on a sofa at night: two episodes into a show they agreed to watch together, Bruno keeps reacting "
    "before anything has happened, and the TV's own menu says why."
)
ACCESSIBILITY = (
    "On a sofa in a dark living room a cartoon rabbit and a cartoon bear face us, lit blue by a TV we cannot see. The "
    "bear jerks and gasps. The light flashes white, the rabbit jumps, and the bear raises his paws late. She turns to "
    "him, then he takes her hand as the light dims. She lifts a remote and the room goes still. He tells her the dog "
    "is fine, she asks what dog, and only his eyes move. She clicks. The frame is a TV menu that reads CONTINUE "
    "WATCHING and EPISODE 8 with a door on its tile and a bar nearly full. Back on the sofa both face front in the "
    "menu's white light. Lines appear in tinted pills and a bar says OUR SHOW: EPISODE 2."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae) and Bill (Bruno)."
NOTE = "ElevenLabs premade voices Sarah and Bill at their natural pace; no reference-voice cloning."
MAE = toon_voices.speaker("mae", "Sarah", "rabbit")
BRUNO = toon_voices.speaker("bruno", "Bill", "bear")
TINTS = toon_voices.tinted(MAE, BRUNO)
TWO, MAE_C, BRUNO_C, MENU = (
    "hamster",
    "goat",
    "sloth",
    "dog",
)  # never seen: the names of the shots the dress draws whole
BARE = (TWO, MAE_C, BRUNO_C, MENU)
RABBIT_COAT, BEAR_COAT = "#efe8ee", "#a8764f"
OVERLAY = "OUR SHOW: EPISODE 2"
MENU_LABEL, MENU_SEEN = "EPISODE 8", 0.92
MAE_AT, BRUNO_AT, PAIR_SCALE = (84.0, 850.0), (258.0, 850.0), 0.66
MAE_CLOSE, BRUNO_CLOSE = (165.0, 880.0), (235.0, 880.0)
TILE_CACTUS, TILE_CODE, TILE_CODE_INK = (860.0, 1322.0), (112.0, 1346.0), "#b7bed2"  # canvas pixels, on the menu's tile
FAR_BLUR = 5.0
LIGHTS = {"lamp": ((0, "off"),)}
FROM_MAE, FROM_BRUNO = (108.0, 760.0), (219.0, 772.0)  # the two-shot's shoulders that meet on the cushion
WOW_HANDS = (((222.0, 800.0), (168.0, 640.0)), ((322.0, 800.0), (374.0, 640.0)))
WOW_LATE, WOW_DOWN = 0.5, 1.15  # seconds after the sting that his hands go up, and come down
REMOTE_ROOT, REMOTE_HAND = (-14.0, 800.0), (36.0, 752.0)
PAT_ROOT, PAT_PAW = (172.0, 736.0), (92.0, 800.0)  # his shoulder, and where his paw comes down on hers
HER_PAW_ROOT, HER_PAW_LEN = (-28.0, 812.0), 118.0  # her arm, in from the frame's edge along the sofa's front
PAT_RISE, PAT_EVERY = 13.0, 0.1  # degrees his paw lifts and seconds to each lift and fall: three pats
JUMP = 34.0  # reference pixels, a full inch of rabbit
GASP_LIFT, GASP_TILT = 70.0, -5.0  # canvas pixels up and degrees back: the first frame's jerk
GASP_SNAPS, GASP_HOLDS, GASP_ENDS = 0.08, 0.36, 1.0  # up, held on the breath in, then the breath out
STING_GLOW = 0.4  # seconds the white flash lasts
PAUSE_TAKES = 0.5  # seconds from the start of the hold to the click

LINES = (
    Line("mae", "Why did you gasp?"),
    Line("bruno", "The door."),
    Line("mae", "It's a door."),
    Line("bruno", "Wow."),
    Line("mae", "You gasped before the door."),
    Line("bruno", "It was a tense door."),
    Line("mae", "You've never seen this."),
    Line("bruno", "I have an instinct for doors."),
    Line("bruno", "You okay?"),
    Line("mae", "Nothing's happened."),
    Line("bruno", "Not yet."),
    Line("bruno", "Relax. The dog's fine."),
    Line("mae", "What dog?"),
    Line("bruno", "There's going to be a dog."),
    Line("mae", "We're on episode two, Bruno."),
    Line("bruno", "It autoplayed."),
)
script = scripting.Script(LINES)
say, first, part, hold = script.say, script.first, script.part, script.hold
TOP = ("up", "flat", "desk")
# Mae is mirrored, so her "left" is at Bruno
M_FRONT = Act("wide", "flat", "desk")
M_AT_HIM = Act("left", "flat", "desk")
M_NARROW = Act("narrow", "flat", "desk")
M_HAND = Act("down", "flat", "desk")
M_STILL = Act("half", "flat", "desk")
# Bruno
B_FRONT = Act("wide", "flat", "desk")
B_GASP = Act("wide", "o", "desk")
B_FIXED = Act("narrow", "flat", "desk")
B_SMUG = Act("half", "smirk", "desk")
B_KIND = Act("left", "smirk", "desk")
B_SIDE = Act("left", "flat", "desk")
B_CAUGHT = Act("wide", "flat", "desk")
B_DEAD = Act("half", "flat", "desk")

ROWS = (
    (hold(0.0, TWO, "", *TOP, "gasp"), M_FRONT, B_GASP),
    (say(0.3, TWO, 0, *TOP), M_AT_HIM, B_FIXED),
    (say(1.7, TWO, 1, *TOP), M_AT_HIM, B_FIXED),  # he does not look away
    (say(2.5, TWO, 2, *TOP), M_FRONT, B_FIXED),
    (say(3.75, TWO, 3, *TOP, "sting"), M_FRONT, B_FRONT),
    (say(4.6, MAE_C, 4, *TOP, "change"), M_AT_HIM, B_FRONT),
    (say(6.65, BRUNO_C, 5, *TOP), M_AT_HIM, B_FIXED),
    (say(7.95, MAE_C, 6, *TOP), M_NARROW, B_FIXED),
    (say(9.6, BRUNO_C, 7, *TOP, "back"), M_NARROW, B_SMUG),  # he nods, a professional
    (hold(11.4, TWO, "", *TOP, "hand"), M_HAND, B_KIND),  # the glow dims and he takes her hand
    (say(11.95, TWO, 8, *TOP), M_HAND, B_KIND),
    (say(12.8, MAE_C, 9, *TOP), M_FRONT, B_KIND),
    (say(14.15, BRUNO_C, 10, *TOP, "pat"), M_FRONT, B_KIND),
    (hold(14.85, TWO, "", *TOP, "pause"), M_AT_HIM, B_SIDE),  # the held silence: she pauses it
    (say(15.75, BRUNO_C, 11, *TOP), M_AT_HIM, B_KIND),
    (say(17.55, MAE_C, 12, *TOP), M_AT_HIM, B_KIND),  # she does not move
    (hold(18.3, BRUNO_C, "", *TOP, "hears"), M_AT_HIM, B_FRONT),  # the held silence: nothing moves but his eyes
    (say(19.2, BRUNO_C, 13, *TOP), M_AT_HIM, B_CAUGHT),
    (say(20.7, MENU, 14, *TOP, "menu"), M_AT_HIM, B_CAUGHT),
    (hold(22.7, TWO, "", *TOP, "light"), M_STILL, B_DEAD),  # the held silence: both face front
    (say(24.1, TWO, 15, *TOP), M_STILL, B_DEAD),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = {"rabbit": tuple(row[1] for row in ROWS), "bear": tuple(row[2] for row in ROWS)}
ONCE = ("gasp", "sting", "change", "back", "hand", "pat", "pause", "hears", "menu", "light")
END = 25.15
SKETCH = Sketch(SLUG, TITLE, (MAE, BRUNO), LINES, BEATS, END, tail=0.15, bare=BARE)
BREATH = foley.Burst(0.3, 2600.0, attack=0.14, decay=0.3)
TICK = foley.Burst(0.05, 3200.0, attack=0.001, decay=0.2, tone_hz=1400.0, tone_end_hz=1400.0, tone=0.5)
ROOM_AIR = foley.Burst(4.0, 240.0, attack=0.3, decay=8.0)  # the room once the TV stops: never digital silence
NOTE_STING = foley.Burst(0.5, 260.0, attack=0.004, decay=0.55, tone_hz=196.0, tone_end_hz=165.0, tone=0.9)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s and every event comes once, in the script's order."""
    sketch.check(sk)
    scripting.speaks_by(sk.beats, 0.5)
    scripting.only_events(sk.beats, set(ONCE))
    for kind in ONCE:
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    order = [at(sk.beats, kind) for kind in ONCE]
    if order != sorted(order):
        raise sketch.SketchError("the events run in the script's order")


def glow(beats) -> tuple:
    """What the show we never see does to the room: one cue per thing that happens, and none after she pauses it,
    until the menu's white light."""
    sting = at(beats, "sting")
    return (
        (0, "on", "blue"),
        (sting, "on", "white"),
        (round(sting + STING_GLOW, 3), "on", "blue"),
        (at(beats, "change"), "on", "purple"),
        (at(beats, "back"), "on", "blue"),
        (at(beats, "hand"), "dim"),
        (at(beats, "pat"), "dim", "purple"),
        (at(beats, "light"), "dim", "white"),
    )


def overlay(cv, parent, beats, end, measure) -> None:
    """Where they are in the show, once, over the opening; never the line's words."""
    toon_house.key_line(cv, parent, OVERLAY, 0.0, 3.2, measure=measure)


def sounds(beats, end) -> tuple[Sound, ...]:
    """His breath, the sting, the TV's hum until she pauses it, the room's air under the holds after, her clicks, the
    menu's tick."""
    pause, menu = at(beats, "pause"), at(beats, "menu")
    click = round(pause + PAUSE_TAKES, 3)
    whole = int(click // foley.HUM.seconds)
    last = round(click - whole * foley.HUM.seconds, 3)  # the hum's last piece stops on her click
    return (
        Sound("breath", BREATH, (0.03,), -14.0),
        Sound("sting", NOTE_STING, (at(beats, "sting"),), -12.0),
        Sound("hum", foley.HUM, tuple(k * foley.HUM.seconds for k in range(whole)), -32.0),
        Sound("hum-end", replace(foley.HUM, seconds=last, decay=0.1), (click - last,), -32.0),
        Sound("room", ROOM_AIR, tuple(round(click + k * 3.6, 3) for k in range(ceil((end - click) / 3.6))), -34.0),
        Sound("click", foley.REMOTE_CLICK, (click, round(menu - 0.3, 3), round(menu - 0.12, 3)), -12.0),
        Sound("tick", TICK, (round(menu + 0.06, 3),), -20.0),
    )


def _room(shot) -> None:
    """The lounge out of focus behind the sofa, whose back stays sharp with the people on it, and no TV in it: theirs
    is on our side of the frame."""
    cv = shot.cv
    far = look.depth(cv, shot.back, "it-autoplayed-far", FAR_BLUR, overscan=True)
    light = cv.group(far, cv.uid("g"))
    toon_rooms.stage(cv, far, light, "lounge", LIGHTS, shot.end, blink=False, bare=("tv",))
    toon_world.sofa_back(cv, shot.back)


def _lifted(cv, g, rest: tuple[float, float], t: float, by: float, rise: float, fall: float) -> None:
    """Key the figure ``g`` up ``by`` from ``t`` and back, on the sketch's clock."""
    y = fy(rest[1])
    keys = [(t, y), (t + rise, y - by), (t + rise + fall, y)]
    cv.keys(g, "y", keys, hold=False, kind="sine-out", local=False)


def _gasps(cv, g, rest: tuple[float, float]) -> None:
    """His jerk back on the first frame, the breath held, and let out through the first second."""
    y = fy(rest[1])
    for name, off, on in (("y", y, y - GASP_LIFT), ("rotation", 0.0, GASP_TILT)):
        keys = [(0.0, off), (GASP_SNAPS, on), (GASP_HOLDS, on), (GASP_ENDS, off)]
        cv.keys(g, name, keys, hold=False, kind="sine-out", local=False)


def _two(shot) -> None:
    """Both of them on the sofa: the jump, his late hands, the hand he takes, her remote."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    sting, hand, pause, menu = (at(beats, k) for k in ("sting", "hand", "pause", "menu"))
    mae = toon_pair.figure(shot, shot.back, "rabbit", MAE_AT, ACTS["rabbit"], scale=PAIR_SCALE, mirror=True)
    if app.start <= sting < app.end:  # behind him, so a raised arm grows out of him
        for root, target in WOW_HANDS:
            degrees, length = toon_pair.aim(root, target)
            swing = [(sting + WOW_LATE, degrees + 40.0), (sting + WOW_LATE + 0.14, degrees)]
            toon_bed.swung_arm(cv, shot.back, root, BEAR_COAT, swing, sting + WOW_LATE, sting + WOW_DOWN, length=length,
                               width=toon_bed.ARM_WIDTH * PAIR_SCALE)  # fmt: skip
    bruno = toon_pair.figure(shot, shot.back, "bear", BRUNO_AT, ACTS["bear"], scale=PAIR_SCALE)
    if app.start <= 0.0 < app.end:
        _gasps(cv, bruno, BRUNO_AT)
    if app.start <= sting < app.end:
        _lifted(cv, mae, MAE_AT, sting, JUMP, 0.1, 0.24)
    if hand <= app.start < menu:
        toon_bed.swung_arm(cv, shot.back, FROM_MAE, RABBIT_COAT, [(app.start, 15.0)], app.start, app.end, length=66.0,
                           width=34.0)  # fmt: skip
        toon_bed.swung_arm(cv, shot.back, FROM_BRUNO, BEAR_COAT, [(app.start + 0.2, 150.0), (app.start + 0.5, 176.0)],
                           app.start, app.end, length=50.0, width=34.0)  # fmt: skip
    if pause <= app.start:
        toon_bed.swung_arm(cv, shot.back, REMOTE_ROOT, RABBIT_COAT, [(app.start, -38.0)], app.start, app.end,
                           length=60.0, width=30.0)  # fmt: skip
        toon_everyday.remote(cv, shot.back, REMOTE_HAND, scale=0.42, tilt=14.0, id=cv.uid("remote"))
    toon_world.sofa(cv, shot.front, "rug")


def _mae(shot) -> None:
    """Mae alone."""
    toon_pair.figure(shot, shot.back, "rabbit", MAE_CLOSE, ACTS["rabbit"], scale=1.0, mirror=True)
    toon_world.sofa(shot.cv, shot.front, "rug")


def pat_swing(pat: float) -> list[tuple[float, float]]:
    """His arm's angles over the line: down on her paw, up, three times."""
    degrees, _ = toon_pair.aim(PAT_ROOT, PAT_PAW)
    return [(round(pat + 0.04 + k * PAT_EVERY, 3), degrees + (PAT_RISE if k % 2 else 0.0)) for k in range(7)]


def _pat(cv, parent, pat: float, start: float, end: float) -> tuple:
    """Her paw along the sofa's front, in from the frame's edge, and his arm patting it, in front of the sofa."""
    her = toon_bed.swung_arm(cv, parent, HER_PAW_ROOT, RABBIT_COAT, [(start, 2.0)], start, end, length=HER_PAW_LEN,
                             width=46.0)  # fmt: skip
    _, length = toon_pair.aim(PAT_ROOT, PAT_PAW)
    him = toon_bed.swung_arm(cv, parent, PAT_ROOT, BEAR_COAT, pat_swing(pat), start, end, length=length, width=52.0)
    return her, him


def _bruno(shot) -> None:
    """Bruno alone, and on the pat her paw and the arm that pats it."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    toon_pair.figure(shot, shot.back, "bear", BRUNO_CLOSE, ACTS["bear"], scale=1.0)
    toon_world.sofa(cv, shot.front, "rug")
    pat = at(beats, "pat")
    if app.start <= pat < app.end:
        _pat(cv, shot.front, pat, app.start, app.end)


def mark_the_tile(cv, parent) -> None:
    """The marks in the show's own still: a pot on the floor by the door, the code along the floor."""
    signature.cactus(cv, parent, *TILE_CACTUS, 0.62)
    signature.code(cv, parent, *TILE_CODE, 20, color=TILE_CODE_INK, opacity=0.9)


def _menu(shot) -> None:
    """The TV, full frame, with the marks on its tile."""
    toon_everyday.tv_menu(shot.cv, shot.front, MENU_LABEL, MENU_SEEN, measure=shot.measure, id=shot.cv.uid("menu"))
    mark_the_tile(shot.cv, shot.front)


def dress(shot) -> None:
    """The lounge behind, then the shot, and the TV's light over all of it but its own menu."""
    who = shot.app.who
    if who == MENU:
        _menu(shot)
        return
    _room(shot)
    {TWO: _two, MAE_C: _mae, BRUNO_C: _bruno}[who](shot)
    toon_rooms.front_screen(shot.cv, shot.front, glow(shot.beats), shot.end)

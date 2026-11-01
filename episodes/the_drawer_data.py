"""The Drawer — the sketch as data: every home has a drawer of forty cables nobody can name and nobody dares throw out.
Mae throws one out. The hum stops, the fridge goes dark, and down the hill the streetlights go out one at a time.

Two voices (ElevenLabs premade Sarah as Mae, Bill as Bruno), held on a medium two-shot in the kitchen
(:func:`srstudio.toon_pair.figure`), the drawer in the front of the counter. Two cuts to the window for the street
going out and coming back. ``ROWS`` act both characters per beat; :func:`validate` checks the events; :func:`dress`
draws each shot, :func:`lens` its camera and :func:`sounds` the room and the town.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, foley, scripting, sketch, toon_cables, toon_house, toon_pair, toon_sets
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3312
SLUG = "the-drawer"
TITLE = "The Drawer — Mae, Bruno and the Cable (Toon)"
DESCRIPTION = (
    "A Toon sketch in a kitchen: she wants the cable drawer gone, he says one of them is important and nobody knows "
    "why, and she drops it in the bin."
)
ACCESSIBILITY = (
    "A cartoon rabbit yanks open a kitchen drawer on a knot of cables while a cartoon bear half stands. She says "
    "it's forty cables; he says that one's important, and nobody knows what it's for. She holds a gray cable over the "
    "bin, looks at him and lets go. A low hum stops and the fridge light goes off. Through the window, the "
    "streetlights go out one after another down the hill. A car alarm, far away, then barking. She takes the cable "
    "out of the bin and puts it back. All the lights come on. She shuts the drawer with one finger: We'll get a "
    "bigger drawer. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae) and Bill (Bruno)."
NOTE = "ElevenLabs premade voices Sarah and Bill at their natural pace; no reference-voice cloning."
PLAIN = VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3)
DEADPAN = VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15)
MAE = Speaker("mae", Voice(role="mae", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"), PLAIN, "rabbit")
BRUNO = Speaker("bruno", Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"), DEADPAN, "bear")
TINTS = {"mae": "#ffd9e4", "bruno": "#d9e8ff"}
PAIR = "hamster"  # never seen: the name of the two-shot, a shot the dress draws whole
WINDOW = "frog"  # never seen: the name of the shot of the window
BARE = (PAIR, WINDOW)
SEATS = {"rabbit": (160.0, 840.0), "bear": (432.0, 840.0)}
RISE = 40.0  # reference units Bruno comes up off his seat
HOOK = "THE CABLE DRAWER"
HOOK_END = 3.0
PIVOT = (980.0, 1420.0)
OUT_STEP = 0.28  # seconds between one streetlight going out and the next
OUT_FROM = 0.3  # after the cut to the window
FINGER = dict(colour="#f4eef2", sleeve="#d9cfe0")
OVER_BIN = (96.0, 720.0)
TIP_ANGLE = 112.0  # degrees: her hand comes in from the left
DRAWER = (300.0, 1056.0)
DRAWER_TOP = (296.0, 920.0)
FALLEN = (96.0, 930.0)
END = 25.6

LINES = (
    Line("mae", "We're throwing these out."),
    Line("bruno", "You can't."),
    Line("mae", "It's forty cables."),
    Line("bruno", "That one's important."),
    Line("mae", "What's it for?"),
    Line("bruno", "Nobody knows. That's why."),
    Line("bruno", "What did you do?"),
    Line("mae", "Nothing. It's a cable."),
    Line("mae", "We'll get a bigger drawer."),
)

script = scripting.Script(LINES)
say, first, part, hold = script.say, script.first, script.part, script.hold
FLAT = Act("half", "flat", "desk")
AT_HIM = Act("side", "flat", "desk")
AT_HER = Act("left", "flat", "desk")
FIRM = Act("narrow", "flat", "desk")
ALARMED = Act("wide", "flat", "desk", ("sweat",))
PLEAD = Act("left", "frown", "desk")
BLANK = Act("half", "flat", "desk")
DOWN = Act("down", "flat", "desk")
UP = Act("up", "flat", "desk")
SMALL = Act("half", "smirk", "desk")
TOP = ("half", "flat", "desk")

ROWS = (
    (hold(0.0, PAIR, "", *TOP, "yank"), FIRM, FLAT),
    (say(0.3, PAIR, 0, *TOP), FIRM, ALARMED),
    (say(2.0, PAIR, 1, *TOP, "rise"), AT_HIM, PLEAD),
    (say(3.0, PAIR, 2, *TOP), FIRM, PLEAD),
    (say(4.6, PAIR, 3, *TOP, "cable"), DOWN, PLEAD),
    (say(5.9, PAIR, 4, *TOP), AT_HIM, PLEAD),
    (say(7.2, PAIR, 5, *TOP), AT_HIM, FLAT),
    (hold(9.0, PAIR, "", *TOP, "over"), AT_HIM, ALARMED),  # she holds it over the bin
    (hold(9.9, PAIR, "", *TOP, "look"), FIRM, ALARMED),  # looks at him
    (hold(10.7, PAIR, "", *TOP, "drop"), DOWN, ALARMED),  # lets go; it lands
    (hold(11.6, PAIR, "", *TOP, "dead"), UP, UP),  # the hum stops, the fridge goes dark
    (say(12.9, PAIR, 6, *TOP), AT_HIM, ALARMED),
    (say(14.1, PAIR, 7, *TOP), BLANK, ALARMED),
    (hold(15.9, WINDOW, "", *TOP, "window"), BLANK, ALARMED),  # lights go out, then two seconds of the town
    (hold(20.3, PAIR, "", *TOP, "take"), DOWN, ALARMED),  # she takes it back out of the bin
    (hold(21.8, WINDOW, "", *TOP, "on"), DOWN, ALARMED),  # far off, all the lights come on
    (hold(22.7, PAIR, "", *TOP, "close"), BLANK, BLANK),  # one finger
    (say(23.6, PAIR, 8, *TOP), SMALL, BLANK),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = {"rabbit": tuple(row[1] for row in ROWS), "bear": tuple(row[2] for row in ROWS)}
EVENTS = ("yank", "rise", "cable", "over", "look", "drop", "dead", "window", "take", "on", "close")
SKETCH = Sketch(SLUG, TITLE, (MAE, BRUNO), LINES, BEATS, END, bare=BARE)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, and every event comes once, in the script's order."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    for kind in EVENTS:
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [when(sk.beats, kind) for kind in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError("the events run in the script's order")


def when(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def out_times(beats) -> tuple[float, ...]:
    """When each streetlight goes out, from the top of the hill down."""
    start = when(beats, "window") + OUT_FROM
    return tuple(round(start + k * OUT_STEP, 3) for k in range(len(toon_cables.STREET)))


def sounds(beats, end) -> tuple[Sound, ...]:
    """The room's hum until the cable lands and from when it is back, the drawer, the far town in the silence."""
    dead, on, gone = when(beats, "dead"), when(beats, "on") + 0.15, out_times(beats)[-1]
    first_hum = min(dead, 8.0)
    alarm = foley.far_alarm(round(gone + 0.3, 3), 1.3)
    out = [
        Sound("yank", foley.THUD, (when(beats, "yank") + 0.05,), -8.0),
        Sound("land", foley.KNOCK, (when(beats, "drop") + 0.32,), -10.0),
        Sound("hum-a", foley.hum(first_hum), (0.0,), -19.0),
        Sound("alarm-high", foley.ALARM_HIGH, alarm[foley.ALARM_HIGH], -20.0),
        Sound("alarm-low", foley.ALARM_LOW, alarm[foley.ALARM_LOW], -20.0),
        Sound("bark", foley.FAR_BARK, foley.far_barks(round(gone + 1.6, 3), 3), -18.0),
        Sound("hum-c", foley.hum(min(end - on, 8.0)), (round(on, 3),), -19.0),
        Sound("shut", foley.KNOCK, (when(beats, "close") + 0.45,), -14.0),
    ]
    if dead > first_hum:
        out.append(Sound("hum-b", foley.hum(dead - first_hum), (first_hum,), -19.0))
    return tuple(out)


def _bruno_rises(cv, g, beats, y: float) -> None:
    rise, take = when(beats, "rise"), when(beats, "window")
    cv.keys(g, "y", [(rise, y), (rise + 0.2, y - toon_house.fh(RISE)), (take, y - toon_house.fh(RISE)), (take, y)],
            hold=False, local=False)  # fmt: skip


def _cable(shot) -> None:
    """Her hand and the cable: up out of the drawer, over the bin, let go; then back out and into the drawer."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    lift, over, drop, take = (when(beats, k) for k in ("cable", "over", "drop", "take"))
    x, y = OVER_BIN
    kept = take + 1.2
    tracks = (
        (lift, drop + 0.34, ((lift, 240.0, 760.0), (over, 240.0, 760.0), (over + 0.2, x, y), (drop, x, y),
                             (drop + 0.34, *FALLEN))),
        (take, kept, ((take, *FALLEN), (take + 0.4, x, y), (take + 0.8, DRAWER_TOP[0], y), (kept, *DRAWER_TOP))),
    )  # fmt: skip
    hands = (
        (lift, drop + 0.5, ((over, x + 6.0, y - 4.0),)),
        (take, kept, ((take + 0.3, x + 6.0, y - 4.0), (take + 0.8, DRAWER_TOP[0] + 6.0, y - 4.0))),
    )
    for (a, b, moves), (c, d, reach) in zip(tracks, hands, strict=True):
        if app.start <= a < app.end:
            toon_cables.gray_cable(cv, shot.front, moves, a, min(b, app.end))
            toon_house.finger(cv, shot.front, tip=(246.0, 756.0), angle=TIP_ANGLE, moves=reach, start=c,
                              end=min(d, app.end), id=cv.uid("finger"), **FINGER)  # fmt: skip


def dress(shot) -> None:
    """The kitchen with the fridge's light, the counter and the drawer; the window on the hill."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    dead, on = when(beats, "dead"), when(beats, "on") + 0.15
    if app.who == WINDOW:
        toon_cables.hill_window(cv, shot.back, out_times(beats), on)
        toon_house.ledge(cv, shot.front, "white")
    else:
        toon_sets.kitchen(cv, shot.back)
        toon_cables.fridge_light(cv, shot.back, dead, on)
        for who in ("rabbit", "bear"):
            g = toon_pair.figure(shot, shot.back, who, SEATS[who], ACTS[who])
            if who == "bear":
                _bruno_rises(cv, g, beats, toon_house.fy(SEATS[who][1]))
        toon_house.ledge(cv, shot.front, "oak")
        toon_cables.cable_drawer(cv, shot.front, when(beats, "yank") + 0.05, when(beats, "close"), at=DRAWER)
        _cable(shot)
        toon_cables.kitchen_bin(cv, shot.front)
        close = when(beats, "close")
        if app.start == close:
            toon_house.finger(cv, shot.front, tip=(300.0, 1125.0), moves=((close + 0.02, 300.0, 1062.0),), start=close,
                              end=close + 1.2, id=cv.uid("finger"), **FINGER)  # fmt: skip
    if app.start == 0.0:
        toon_house.key_line(cv, shot.front, HOOK, 0.0, HOOK_END, measure=shot.measure)


def lens(shot, setup) -> None:
    """A slow push from the first frame; held after that, so the room going quiet is the only thing that moves."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.start == 0.0:
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (3.0, 1.04)])

"""Mosquito: the sketch as data. One whine in a dark bedroom and Bruno is awake. Light on: nothing. Light off: there it
is. He stands to it with a rolled towel, hits himself twice, and it lands on his own forehead. Mae, face in the pillow
and not waking, reaches over and flattens it. Got him. The light goes out. One whine.

Toon, ElevenLabs premade Bill (Bruno) and Sarah (Mae). It opens moving (the ``sp-hook_motion`` test's arm b): the
mosquito is flying from the first frame. :func:`dress` draws the bed, the dark and the mosquito.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley, scripting, sketch, toon_house, toon_odds, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound, opening_push
from srstudio.voice import Voice, VoiceSettings

SEED = 3106
SLUG = "mosquito"
TITLE = "Mosquito (Toon)"
DESCRIPTION = "One mosquito, two in the morning, a grown bear with a rolled towel."
ACCESSIBILITY = (
    "A cartoon bear lies awake in a dark bedroom as a mosquito passes his ear. He turns the light on and it is gone; "
    "off, and it is back. He raises a rolled towel and hits himself. The mosquito lands on his own forehead and his "
    "eyes turn up. His wife, a rabbit asleep with her face in the pillow, reaches over and slaps it flat, saying Got "
    "him, and does not wake. The light goes off. One whine. His eyes open."
)
NARRATION = "Voiced with ElevenLabs premade voices Bill (Bruno) and Sarah (Mae); synthesised foley."
NOTE = "ElevenLabs premade voices Bill and Sarah at their natural pace; no reference-voice cloning."
BRUNO = Speaker(
    "bruno", Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"), VoiceSettings(0.5, 0.75, 0.3), "bear"
)
MAE = Speaker(
    "mae", Voice(role="mae", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"), VoiceSettings(0.6, 0.75, 0.2), "rabbit"
)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
TINTS = {"bruno": "#eccfae", "mae": "#f9dbe6"}
KEY_LINE = "It's two in the morning."
WHINE = foley.Burst(1.3, 900.0, attack=0.2, decay=1.4, tone_hz=640.0, tone_end_hz=720.0, tone=0.7, flutter_hz=23.0)
SLAP = foley.Burst(0.16, 3200.0, attack=0.001, decay=0.3, tone_hz=210.0, tone_end_hz=110.0, tone=0.4)
FOREHEAD = (190.0, 545.0)
DARK = ("#0d1430", 0.66)
EVENTS = {"on", "off", "slap", "towel", "swing", "land", "reach", "whack", "again"}
END = 14.0

LINES = (
    Line("bruno", "It's in here."),
    Line("mae", "It's two in the morning."),
    Line("bruno", "It's him or me."),
    Line("bruno", "He's laughing."),
    Line("mae", "Got him."),
)
SCRIPT = scripting.Script(LINES)
say, hold = SCRIPT.say, SCRIPT.hold
BEATS = (
    say(0.0, "bear", 0, "side", "flat", "desk"),
    hold(0.9, "bear", "", "wince", "grimace", "desk", "slap"),
    hold(1.5, "bear", "", "wide", "flat", "desk", "on"),
    hold(2.3, "bear", "", "side", "flat", "desk", "off"),
    hold(3.1, "bear", "", "wide", "flat", "desk", "on"),
    say(3.6, "rabbit", 1, "closed", "flat", "desk"),
    say(4.8, "bear", 2, "narrow", "grimace", "desk", "towel"),
    hold(5.9, "bear", "", "wince", "grimace", "desk", "swing"),
    say(6.8, "bear", 3, "narrow", "frown", "desk"),
    hold(7.8, "bear", "", "up", "flat", "desk", "land"),  # the whine stops, his eyes go up
    hold(9.3, "rabbit", "", "closed", "flat", "desk", "reach"),
    hold(9.8, "bear", "", "shock", "o", "desk", "whack"),
    say(10.3, "rabbit", 4, "closed", "smirk", "desk"),
    hold(11.5, "bear", "", "half", "flat", "desk", "off"),
    hold(12.3, "bear", "", "half", "flat", "desk", "again"),
    hold(12.9, "bear", "", "wide", "flat", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (BRUNO, MAE), LINES, BEATS, END)


def event(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """Dark and light alternate, the mosquito lands before the whack, and the last sound is one whine."""
    sketch.check(sk)
    scripting.only_events(sk.beats, EVENTS)
    for kind in ("towel", "swing", "land", "reach", "whack", "again"):
        scripting.exactly_once(sk.beats, kind, f"one {kind}")
    if not event(sk.beats, "land") < event(sk.beats, "reach") < event(sk.beats, "whack") < event(sk.beats, "again"):
        raise sketch.SketchError("it lands, she reaches, she hits it, then the last whine")


def dark_spans(beats, end: float) -> list[tuple[float, float]]:
    """When the light is off: from 0 to the first on, and from every off to the next on or the end."""
    marks = sorted((t, name) for name in ("on", "off") for t, _ in sketch.events(beats, name))
    spans, start = [], 0.0
    for t, name in marks:
        if name == "on" and start is not None:
            spans.append((start, t))
            start = None
        elif name == "off" and start is None:
            start = t
    if start is not None:
        spans.append((start, end))
    return spans


def _flight(start: float, stop: float) -> list[tuple[float, float, float]]:
    """A jittery loop round his head between two seconds."""
    step, keys, t, k = 0.17, [], start, 0
    while t < stop:
        keys.append((round(t, 3), 260.0 + 130.0 * ((k * 7) % 5 - 2) / 2.0, 470.0 + 40.0 * ((k * 3) % 5 - 2)))
        t, k = t + step, k + 1
    keys.append((round(stop, 3), 260.0, 470.0))
    return keys


def dress(shot) -> None:
    """The bed under each character, the dark over it, the mosquito in the dark, the towel, her paw."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    toon_house.bedroom(cv, shot.back)
    land, whack = event(beats, "land"), event(beats, "whack")
    if app.who == "bear":
        towel, swing = event(beats, "towel"), event(beats, "swing")
        if app.start <= towel < app.end or towel <= app.start < land:
            toon_odds.rolled_towel(
                cv, shot.front, (480.0, 880.0), ((towel, 0.0), (swing, 0.0), (swing + 0.14, -46.0), (swing + 0.5, 6.0)),
                max(app.start, towel), min(app.end, land),
            )  # fmt: skip
    toon_house.quilt(cv, shot.front, "plum")
    if app.who == "bear":
        again = event(beats, "again")
        for a, b in dark_spans(beats, shot.end):
            a, b = max(a if a < land else again, app.start), min(b, app.end, land if a < land else b)
            if b - a > 0.3:
                toon_odds.mosquito(cv, shot.front, _flight(a, b), b, id="flying")
        lands = max(app.start, land - 0.5)
        if lands < land < app.end:
            toon_odds.mosquito(
                cv, shot.front, [(lands, 330.0, 470.0), (land, *FOREHEAD), (min(whack, app.end), *FOREHEAD)],
                min(whack, app.end), id="landing",
            )  # fmt: skip
        if app.start <= whack < app.end:
            toon_world.paw(
                cv, shot.front, ((whack - 0.16, whack + 0.9),), "#efe8ee", y=FOREHEAD[1], reach=420.0, holding=""
            )
    elif app.start <= event(beats, "reach") < app.end:
        at = event(beats, "reach")
        toon_world.paw(cv, shot.front, ((at, app.end),), "#efe8ee", y=640.0, reach=330.0, holding="")
    for a, b in dark_spans(beats, shot.end):
        a, b = max(a, app.start), min(b, app.end)
        if b > a:
            shade = cv.group(shot.front, cv.uid("g"), start=a, end=b)
            cv.rect(shade, 0, 0, cv.width, cv.height, DARK[0], opacity=DARK[1])
    if app.start == 0:
        toon_house.key_line(cv, shot.front, KEY_LINE, 0.0, 1.5, measure=shot.measure)


def sounds(beats, end: float) -> list[Sound]:
    """The whine in every dark stretch before it lands, the switch, the slaps, the whine at the end."""
    land = event(beats, "land")
    whines = [
        round(a + k * 1.1, 3) for a, b in dark_spans(beats, land) for k in range(int((min(b, land) - a) / 1.1) + 1)
    ]
    switch = [t for name in ("on", "off") for t, _ in sketch.events(beats, name)]
    return [
        Sound("whine", WHINE, (*[t for t in whines if t < land - 1.0], event(beats, "again")), -13.0),
        Sound("switch", foley.REMOTE_CLICK, tuple(sorted(switch)), -5.0),
        Sound("slap", SLAP, (event(beats, "slap"), event(beats, "swing") + 0.2), -5.0),
        Sound("whack", SLAP, (event(beats, "whack"),), 0.0),
    ]


STAGING_ARGS = dict(
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
    camera=opening_push(),
    desk=toon_world.no_desk,
)

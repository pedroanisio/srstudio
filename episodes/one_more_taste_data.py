"""One more taste: the sketch as data. A fox works through the whole case on tiny spoons, with a hill of them growing
on the counter and a line out of the door. Eleven flavors. She is actually pretty full, thanks. Bruno, who begged her
to stop, steps up. Can I try the pistachio?

Toon, ElevenLabs premade Alice (the fox), Liam (the server), Bill (Bruno) and George (the goat). It opens moving, the
``sp-hook_motion`` test's arm b. :func:`dress` draws the parlour either side of the case and the spoons.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley, scripting, signature, sketch, toon_house, toon_odds, toon_parlour, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon import fx, fy
from srstudio.toon_sketch import Sound, opening_push
from srstudio.voice import Voice, VoiceSettings

SEED = 3110
SLUG = "one-more-taste"
TITLE = "One more taste (Toon)"
DESCRIPTION = "Someone at the ice cream counter tries every flavor. Someone behind them is next."
ACCESSIBILITY = (
    "A cartoon fox at an ice cream counter asks to try flavor after flavor while tiny pink spoons pile up and a line "
    "grows behind her. A bear behind her whispers please. She raises a finger, says she is actually pretty full, and "
    "leaves. The bear steps up to the case. What can I get you, says the hamster server. Can I try the pistachio?"
)
NARRATION = "Voiced with ElevenLabs premade voices Alice, Liam, Bill and George; synthesised foley."
NOTE = "ElevenLabs premade voices Alice, Liam, Bill and George at their natural pace; no reference-voice cloning."
FOX = Speaker("fox", Voice(role="fox", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"), VoiceSettings(0.45, 0.75, 0.35), "fox")
SERVER = Speaker(
    "server", Voice(role="server", id="TX3LPaxmHKxFdv7VOQHJ", name="Liam"), VoiceSettings(0.4, 0.75, 0.3), "hamster"
)
BRUNO = Speaker(
    "bruno", Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"), VoiceSettings(0.5, 0.75, 0.3), "bear"
)
GOAT = Speaker(
    "goat", Voice(role="goat", id="JBFqnCBsd6RMkjVDRZzb", name="George"), VoiceSettings(0.6, 0.75, 0.15), "goat"
)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
TINTS = {"fox": "#fbdcbc", "server": "#f7e0b5", "bruno": "#eccfae", "goat": "#e9e2d0"}
KEY_LINE = "Can I try the pistachio?"
CLINK = foley.Burst(0.09, 3800.0, attack=0.001, decay=0.5, tone_hz=2600.0, tone_end_hz=2500.0, tone=0.6)
EVENTS = {"finger", "leaves"}
SPOONS = tuple(round(0.8 + k * 0.55, 2) for k in range(22))
END = 21.8

LINES = (
    Line("fox", "Can I try the pistachio?"),
    Line("fox", "Can I try the mango? The other mango?"),
    Line("goat", "Is she buying a house?"),
    Line("server", "We have eleven flavors."),
    Line("fox", "Can I try the first one again?"),
    Line("bruno", "Please."),
    Line("fox", "You know what?"),
    Line("fox", "I'm actually pretty full. Thanks!"),
    Line("server", "What can I get you?"),
    Line("bruno", "Can I try the pistachio?"),
)
SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold
BEATS = (
    say(0.0, "fox", 0, "wide", "grin", "desk"),
    first(1.6, "fox", 1, "Can I try the mango?", "up", "grin", "desk"),
    part(2.9, "fox", 1, 5, "The other mango?", "side", "grin", "desk"),
    say(4.4, "goat", 2, "half", "flat", "desk"),
    say(5.9, "hamster", 3, "half", "flat", "desk"),
    say(7.4, "fox", 4, "wide", "grin", "desk"),
    hold(9.2, "hamster", "", "closed", "flat", "desk"),
    say(10.4, "bear", 5, "teary", "wave", "desk"),
    say(11.4, "fox", 6, "up", "smirk", "desk", "finger"),
    hold(12.4, "bear", "", "wide", "o", "desk"),
    hold(13.3, "goat", "", "wide", "o", "desk"),
    say(14.0, "fox", 7, "closed", "grin", "desk", "leaves"),
    hold(16.0, "hamster", "", "half", "flat", "desk"),
    say(16.9, "hamster", 8, "half", "smirk", "desk"),
    hold(18.1, "bear", "", "down", "flat", "desk"),
    say(19.3, "bear", 9, "up", "grin", "desk"),
    hold(20.7, "hamster", "", "closed", "frown", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (FOX, SERVER, BRUNO, GOAT), LINES, BEATS, END)


def event(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """She leaves after the finger, and the last spoon falls before she does."""
    sketch.check(sk)
    scripting.only_events(sk.beats, EVENTS)
    for kind in EVENTS:
        scripting.exactly_once(sk.beats, kind, f"one {kind}")
    if max(SPOONS) >= event(sk.beats, "leaves"):
        raise sketch.SketchError("the last spoon falls before she leaves")


def dress(shot) -> None:
    """The customer's side of the case for the line, the server's side for the server, the spoons on the counter."""
    cv, app = shot.cv, shot.app
    if app.who == "hamster":
        toon_parlour.parlour_back(cv, shot.back)
    else:
        toon_parlour.parlour_front(cv, shot.back, 0.0, shot.end)
    toon_parlour.case(cv, shot.front)
    signature.cactus(cv, shot.front, fx(548), fy(900), 0.7)
    signature.code(cv, shot.front, fx(580), fy(928), 14, color="#6b5a4d", opacity=0.9, align="end")
    fallen = tuple(t for t in SPOONS if t < app.end)
    if fallen:
        toon_odds.tasting_spoons(cv, shot.front, fallen, at=(395.0, 880.0), end=app.end)
    if app.start == 0:
        toon_house.key_line(cv, shot.front, KEY_LINE, 0.0, 1.5, measure=shot.measure)


def sounds(beats, end: float) -> list[Sound]:
    """Every spoon clinks; the door's bell as she leaves."""
    return [Sound("clink", CLINK, SPOONS, -12.0), Sound("bell", foley.BELL, (event(beats, "leaves") + 1.6,), -11.0)]


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

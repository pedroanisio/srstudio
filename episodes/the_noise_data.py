"""The Noise — the sketch as data: the car rattled all week and goes quiet the moment a mechanic listens, so Fox stands
in a yard doing the noise with his mouth. Clunk is two thousand dollars. He talks it down, sound by sound, to a squeak
at forty bucks, they shake on it, he pats the car, and the real clunk takes a wheel off. It rolls away past them both.

Two voices (ElevenLabs premade Liam as the customer, Roger as the mechanic), both standing behind the car. It opens on
a wide of two people waiting for a car to speak, the car shaking at idle as the shot drifts in. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress` draws each shot,
:func:`lens` the one punch-in and :func:`sounds` the clunk.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, foley, scripting, sketch, toon, toon_cars, toon_everyday, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3101
SLUG = "the-noise"
TITLE = "The Noise — Fox at the Garage (Toon)"
DESCRIPTION = (
    "A Toon sketch at a garage: the car goes quiet for the mechanic, so the customer does the noise with his mouth "
    "and talks the repair down from a clunk to a squeak, until the real clunk takes a wheel off."
)
ACCESSIBILITY = (
    "A cartoon fox and a cartoon goat stand behind a parked car, waiting. The car makes no sound. The fox imitates "
    "the noise and the goat writes a price on a clipboard for each sound, two thousand dollars for a clunk, eight "
    "hundred for a rattle, forty for a squeak. The fox pats the car, it clunks, a wheel falls off and rolls slowly "
    "away. The goat turns to look at him and he says squeak in a very small voice."
)
NARRATION = "Voiced with ElevenLabs premade voices Liam (Fox) and Roger (the mechanic); synthesized effects."
NOTE = "ElevenLabs premade voices Liam and Roger at their natural pace; no reference-voice cloning."
VOICE_FOX = Voice(role="fox", id="TX3LPaxmHKxFdv7VOQHJ", name="Liam")
FOX = Speaker("fox", VOICE_FOX, VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35), "fox")
GOAT = Speaker(
    "goat",
    Voice(role="goat", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
    VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15),
    "goat",
)
# His last word, as small as a word gets, through a fixed mouth: the character plays no lip sync for it.
FOX_LOW = Speaker("fox-low", VOICE_FOX, VoiceSettings(stability=0.85, similarity_boost=0.75, style=0.0))
TINTS = {"fox": "#ffd9b8", "fox-low": "#ffd9b8", "goat": "#e6e0d0", "hamster": "#ffffff"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

STILL = 1.3  # seconds of the opening wide before anyone speaks
DRIFT = 1.05  # the opening wide drifts in this far
SHAKE = ((0.0, 0.0), (0.2, -0.8), (0.4, 0.6), (0.6, -0.7), (0.8, 0.5), (1.0, -0.4), (1.2, 0.0))  # s, degrees: at idle
WIDE = "hamster"  # never seen: the name of the wide, a shot the dress draws whole
FIGURES = {"fox": (1.1, 30.0), "goat": (1.1, 20.0)}
CAR_FRONT = {"at": (210.0, 975.0), "scale": 1.9}  # the car close, between the viewer and whoever is talking
CAR_WIDE = {"at": (300.0, 905.0), "scale": 1.3}
BEHIND = {
    "fox": ((200.0, 842.0), 0.62),
    "goat": ((394.0, 842.0), 0.62),
}  # low enough that the dropped car hides the fox
DRIVE = "#b8b2a6"  # the concrete in front of the yard
BOARD = {"at": (424, 824), "scale": 1.1}  # stood on the boot, against the rear window
PRICES = (("Clunk", "$2,000", "clunk-price"), ("Rattle", "$800", "rattle-price"), ("Squeak", "$40", "squeak-price"))
ROLL = 3.2  # seconds the wheel takes to leave the frame
SLUMP = -5.0  # degrees the car drops onto its bare axle
PUNCH = 1.14
PIVOT = (340.0, 880.0)
OPENING_PIVOT = (900.0, 1000.0)  # right of the code on the concrete's edge, which the drift keeps in frame
END = 31.2
THE_CLUNK = foley.Burst(0.7, 240.0, attack=0.003, decay=0.4, tone_hz=70.0, tone_end_hz=38.0, tone=0.9)
WHEEL_RATTLE = foley.Burst(0.12, 900.0, attack=0.002, decay=0.5, tone_hz=210.0, tone_end_hz=170.0, tone=0.3)

LINES = (
    Line("fox", "It makes a noise."),
    Line("goat", "What kind of noise?"),
    Line("fox", "It won't do it now."),
    Line("goat", "They never do. Do the noise."),
    Line("fox", "Clunk. Clunk clunk."),
    Line("goat", "That's two thousand dollars."),
    Line("fox", "Or more of a rattle."),
    Line("goat", "That's 800."),
    Line("fox", "Rattle rattle. Yes."),
    Line("goat", "You sure?"),
    Line("fox", "What's cheaper than a rattle?"),
    Line("goat", "Squeak. Forty bucks."),
    Line("fox", "Squeak squeak."),
    Line("goat", "Forty bucks."),
    Line("fox-low", "Squeak."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say

BEATS = (
    hold(0.0, WIDE, "", "wide", "flat", "desk"),  # the car shakes and says nothing
    say(1.3, "fox", 0, "wide", "grin", "desk"),
    say(2.57, "goat", 1, "half", "flat", "desk"),
    hold(3.83, "fox", "", "left", "flat", "desk"),  # he looks at the car: nothing
    say(4.83, "fox", 2, "side", "grimace", "desk"),
    say(6.05, "goat", 3, "half", "flat", "desk"),
    say(7.78, "fox", 4, "side", "grimace", "desk", "punch", wear=("sweat",)),
    say(9.51, "goat", 5, "down", "flat", "desk", "clunk-price"),
    hold(11.04, "fox", "", "down", "flat", "desk"),  # his eyes go to the clipboard
    say(12.04, "fox", 6, "side", "grin", "desk"),
    say(13.43, "goat", 7, "down", "flat", "desk", "rattle-price"),
    say(14.57, "fox", 8, "wide", "grin", "desk"),
    say(16.3, "goat", 9, "half", "flat", "desk"),
    say(17.07, "fox", 10, "down", "flat", "desk"),
    say(18.61, "goat", 11, "half", "flat", "desk"),
    hold(20.01, "fox", "", "up", "flat", "desk"),  # he looks at the sky
    say(21.41, "fox", 12, "side", "grin", "desk"),
    say(22.51, "goat", 13, "down", "smirk", "desk", "squeak-price"),
    hold(23.51, WIDE, "", "wide", "flat", "desk", "clunk"),
    hold(28.11, "goat", "", "left", "flat", "desk"),  # he is still watching the wheel
    hold(28.71, "goat", "", "narrow", "flat", "desk"),  # then his eyes come round
    say(29.81, "fox", 14, "wince", "grimace", "sigh", wear=("sweat",)),
)
SKETCH = Sketch(SLUG, TITLE, (FOX, GOAT, FOX_LOW), LINES, BEATS, END, bare=(WIDE,))


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, opens on a silent uncaptioned wide of at least 1 s, prices each sound
    once and in order, and the clunk comes once, on the wide, after the last price."""
    sketch.check(sk)
    opening = sk.beats[0]
    if opening.line is not None or opening.caption or sk.beats[1].start < 1.0:
        raise sketch.SketchError("the sketch opens on a silent, uncaptioned wide of at least 1 s")
    order = tuple(name for _, _, name in PRICES) + ("clunk",)
    for event in order:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    times = [sketch.events(sk.beats, event)[0][0] for event in order]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {order}")
    scripting.only_events(sk.beats, {*order, "punch"})
    if next(b for b in sk.beats if b.event == "clunk").who != WIDE:
        raise sketch.SketchError("the clunk happens on the wide")


def behind(shot, parent, who: str, keys) -> None:
    """``who`` standing behind the car in a wide, one ``(project second, eyes, mouth)`` for each change of look."""
    cv, app = shot.cv, shot.app
    poses = toon.parse_poses(
        [{"start": max(0.0, at - app.start), "eyes": e, "mouth": m, "arms": "desk"} for at, e, m in keys],
        f"{who} behind the car",
    )
    at, scale = BEHIND[who]

    def draw(g) -> None:
        sketch.drawer(who, shot.versions)(cv, g, poses, app.end, (), enter=app.start)

    toon_world.placed(cv, parent, at, scale, draw)


def shaking(shot):
    """A group about the car's rear wheel that shakes at idle, for the opening wide."""
    cv, (x, y) = shot.cv, CAR_WIDE["at"]
    pivot = {"x": toon.fx(x + 98 * CAR_WIDE["scale"]), "y": toon.fy(y)}
    car = cv.group(shot.front, cv.uid("g"), anchorX=pivot["x"], anchorY=pivot["y"], **pivot)
    cv.keys(car, "rotation", SHAKE, hold=False, local=False)
    return car


def yard(shot) -> None:
    """The yard, the concrete in front of it, and the marks on the concrete's edge."""
    cv = shot.cv
    toon_world.yard(cv, shot.back, sign=None, table=False)
    cv.rect(shot.back, toon.fx(-10), toon.fy(896), toon.fh(612), toon.fh(320), DRIVE, cv.ink, toon.FINE_W, radius=0)
    toon_world.marks(cv, shot.back)


def wide(shot) -> None:
    """The yard. Before the clunk, two people behind a whole car; at it, the car drops onto its axle and the wheel
    rolls away to the left, and both of them watch it go."""
    cv, app = shot.cv, shot.app
    yard(shot)
    clunks = [at for at, _ in sketch.events(shot.beats, "clunk") if app.start <= at < app.end]
    if not clunks:
        behind(shot, shot.front, "fox", ((app.start, "wide", "flat"),))
        behind(shot, shot.front, "goat", ((app.start, "half", "flat"),))
        toon_cars.side_car(cv, shaking(shot), **CAR_WIDE)
        return
    clunk = clunks[0]
    behind(shot, shot.front, "fox", ((app.start, "wide", "grin"), (clunk + 0.5, "shock", "flat"),
                                     (clunk + 1.4, "left", "flat")))  # fmt: skip
    behind(shot, shot.front, "goat", ((app.start, "half", "smirk"), (clunk + 0.5, "shock", "flat"),
                                      (clunk + 1.4, "left", "flat")))  # fmt: skip
    x, y = CAR_WIDE["at"]
    pivot = {"x": toon.fx(x + 98 * CAR_WIDE["scale"]), "y": toon.fy(y)}
    car = cv.group(shot.front, cv.uid("g"), anchorX=pivot["x"], anchorY=pivot["y"], **pivot)
    cv.keys(car, "rotation", [(0.0, 0.0), (clunk, 0.0), (clunk + 0.12, SLUMP)], hold=False, local=False)
    whole, short = cv.group(car, cv.uid("g"), end=clunk), cv.group(car, cv.uid("g"), start=clunk)
    toon_cars.side_car(cv, whole, **CAR_WIDE)
    toon_cars.side_car(cv, short, wheels=("rear",), **CAR_WIDE)
    toon_cars.loose_wheel(cv, cv.group(shot.front, cv.uid("g"), start=clunk), start=clunk, to=-60.0, seconds=ROLL,
                          **CAR_WIDE)  # fmt: skip


def dress(shot) -> None:
    """The yard behind everyone. The wide is drawn whole; in a close shot the car stands between the viewer and the
    speaker, and the mechanic holds the clipboard, a price written in for each sound as he names it."""
    cv, app = shot.cv, shot.app
    if app.who == WIDE:
        wide(shot)
        return
    yard(shot)
    toon_cars.side_car(cv, shot.front, **CAR_FRONT)
    if app.who == "goat":
        fields = [
            toon_everyday.Field(label, value, sketch.events(shot.beats, cue)[0][0]) for label, value, cue in PRICES
        ]
        toon_everyday.clipboard(cv, shot.front, "NOISES", fields, measure=shot.measure, id=cv.uid("board"), **BOARD)


def lens(shot, setup) -> None:
    """The opening wide drifts in; one punch-in, on the shot where he has to make the noise."""
    if shot.app.start == 0:
        camera.anchor(setup, *OPENING_PIVOT, place=True)
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (shot.app.end, DRIFT)])
    punches = [at for at, _ in sketch.events(shot.beats, "punch") if shot.app.start <= at < shot.app.end]
    if punches:
        camera.anchor(setup, *PIVOT, place=True)
        camera.crash_zoom(shot.cv, setup, punches[0], PUNCH)


def sounds(beats, end) -> tuple[Sound, ...]:
    """The clunk, the real one, and the wheel's rattle dying away as it rolls off."""
    clunk = sketch.events(beats, "clunk")[0][0]
    rattle = tuple(clunk + 0.45 * k for k in range(1, int(ROLL / 0.45)))
    return (Sound("clunk", THE_CLUNK, (clunk,), 0.0), Sound("rattle", WHEEL_RATTLE, rattle, -16.0))

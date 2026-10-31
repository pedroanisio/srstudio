"""Voice Note — the sketch as data: a friend sends twelve minutes of voice note instead of two lines of text. He plays
it at double speed through the chores, through the night and into the morning, and the news is not in it. At 11:44 of
11:47 she says it is easier if she calls, and he lowers the ringing phone into the sink.

One voice heard (ElevenLabs premade Jessica, the friend, off screen; the fast lines at the highest speed the voice
takes, 1.2), and the hedgehog never speaks. The bar is on screen from the first frame to the last, and the reel opens
on it held still, on a still of him at the sink (the ``sp-hook_motion`` test's arm A). ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the order of the night; :func:`dress` draws each scene in the
one long appearance he has, :func:`lens` the push and :func:`sounds` the phone.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    camera,
    foley,
    scripting,
    sketch,
    toon,
    toon_everyday,
    toon_house,
    toon_inserts,
    toon_sets,
    toon_world,
)
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3111
SLUG = "voice-note"
TITLE = "Voice Note — Eleven Minutes Forty-Seven (Toon)"
DESCRIPTION = (
    "A Toon sketch at a kitchen sink: a friend's voice note runs eleven minutes and forty-seven seconds, through the "
    "chores and the night, without the news, until she decides it is easier to call."
)
ACCESSIBILITY = (
    "A cartoon hedgehog at a sink listens to a voice note on his phone, its progress bar shown large. He sets it to "
    "double speed. He does the laundry, brushes his teeth, waters a plant and lies awake in bed while the friend "
    "talks about someone called Dave. In the morning at the same sink she reaches the big news, breathes, and says "
    "it is easier if she calls. The phone rings. He looks at it and lowers it into the sink."
)
NARRATION = "Voiced with the ElevenLabs premade voice Jessica (the friend, off screen); synthesized effects."
NOTE = "The ElevenLabs premade voice Jessica, the fast lines at speed 1.2; no reference-voice cloning."
VOICE_FRIEND = Voice(role="friend", id="cgSgspJ2msm6clMCkdW9", name="Jessica")
FRIEND = Speaker("friend", VOICE_FRIEND, VoiceSettings(stability=0.35, similarity_boost=0.75, style=0.45))
FAST = Speaker("friend-fast", VOICE_FRIEND, VoiceSettings(stability=0.35, similarity_boost=0.75, style=0.45, speed=1.2))
TINTS = {"friend": "#ffe9a8", "friend-fast": "#ffe9a8", "hamster": "#ffffff"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

STILL = 1.2  # seconds the bar holds before she speaks
WIDE = "hamster"  # never seen: the name of the first shot, a still drawn whole
FIGURES: dict[str, tuple[float, float]] = {"hedgehog": (1.1, 0.0)}
SEAT = (165.0, 840.0)
PHONE_AT = (400.0, 830.0)
PHONE_SCALE = 1.3
HAND = "#e4c79e"
TOTAL = "11:47"
STOPS = {  # the event, the time on the bar, how much of it has played
    "tap": ("0:31", 0.05),
    "laundry": ("4:10", 0.35),
    "teeth": ("6:52", 0.58),
    "water": ("8:20", 0.71),
    "bed": ("9:47", 0.83),
    "morning": ("11:31", 0.977),
    "last": ("11:44", 0.996),
    "ring": ("11:47", 1.0),
}
PUSH = 1.12
MARKS_IN = 44.0  # how far in the sink's marks sit so that the push keeps them in frame
SINK_FALL = 1.1  # seconds the phone takes to go down
SINK_DROP = 340.0  # reference pixels it goes
RING = foley.Burst(0.9, 300.0, attack=0.01, decay=0.5, tone_hz=880.0, tone_end_hz=880.0, tone=0.8, flutter_hz=20.0)
BLUB = foley.Burst(0.7, 500.0, attack=0.02, decay=0.5, tone_hz=240.0, tone_end_hz=520.0, tone=0.8, flutter_hz=9.0)
END = 29.6

LINES = (
    Line("friend", "Hey! Quick one. Okay, not quick. Hang on. Oat milk, please. Sorry."),
    Line("friend-fast", "So you remember Dave. Not that Dave. The other Dave, whose sister had the van."),
    Line("friend-fast", "Anyway that's not the point. Where was I?"),
    Line("friend-fast", "Which is why I said to Dave..."),
    Line("friend", "So. The big news is."),
    Line("friend", "Actually, it's easier if I call you."),
)

script = scripting.Script(LINES)
hold, say, first, part = script.hold, script.say, script.first, script.part

BEATS = (
    hold(0.0, WIDE, "", "half", "flat", "desk"),  # the still: the bar and his face
    first(1.2, "hedgehog", 0, "Hey! Quick one.", "half", "flat", "desk"),
    part(3.48, "hedgehog", 0, 3, "Okay, not quick.", "half", "flat", "desk"),
    part(5.31, "hedgehog", 0, 6, "Hang on. Oat milk, please. Sorry.", "down", "flat", "desk"),
    hold(7.7, "hedgehog", "", "down", "flat", "desk"),  # he looks at the bar
    hold(8.5, "hedgehog", "", "narrow", "flat", "desk", "tap"),
    first(9.2, "hedgehog", 1, "So you remember Dave.", "half", "flat", "desk"),
    part(10.7, "hedgehog", 1, 4, "Not that Dave.", "half", "flat", "desk"),
    part(11.84, "hedgehog", 1, 7, "The other Dave,", "up", "flat", "desk"),
    part(12.5, "hedgehog", 1, 10, "whose sister had the van.", "up", "flat", "desk"),
    hold(13.65, "hedgehog", "", "half", "flat", "desk", "laundry"),
    first(14.35, "hedgehog", 2, "Anyway that's not the point.", "half", "flat", "desk"),
    part(15.25, "hedgehog", 2, 5, "Where was I?", "half", "o", "desk", "teeth"),
    hold(16.1, "hedgehog", "", "up", "flat", "desk", "water"),
    hold(17.1, "hedgehog", "", "wide", "flat", "desk", "bed"),
    say(18.1, "hedgehog", 3, "wide", "flat", "desk"),
    hold(19.5, "hedgehog", "", "sleepy", "flat", "desk", "morning"),
    say(20.4, "hedgehog", 4, "wide", "flat", "desk", wear=("sweat",)),
    hold(22.0, "hedgehog", "", "wide", "flat", "desk", "last", wear=("sweat",)),  # she breathes
    say(23.6, "hedgehog", 5, "wide", "flat", "desk", wear=("sweat",)),
    hold(25.6, "hedgehog", "", "half", "flat", "desk", "ring", wear=("sweat",)),
    hold(27.0, "hedgehog", "", "down", "flat", "desk", "down", wear=("sweat",)),
    hold(28.4, "hedgehog", "", "half", "flat", "desk", wear=("sweat",)),
)
SKETCH = Sketch(SLUG, TITLE, (FRIEND, FAST), LINES, BEATS, END, bare=(WIDE,))
ORDER = (*STOPS, "down")


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, opens on a silent uncaptioned still of at least 1 s, and the night runs in order, each
    step once."""
    sketch.check(sk)
    opening = sk.beats[0]
    if opening.line is not None or opening.caption or sk.beats[1].start < 1.0:
        raise sketch.SketchError("the sketch opens on a silent, uncaptioned still held at least 1 s")
    for event in ORDER:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    times = [sketch.events(sk.beats, event)[0][0] for event in ORDER]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {ORDER}")
    scripting.only_events(sk.beats, set(ORDER))


def at(shot, event: str) -> float:
    return sketch.events(shot.beats, event)[0][0]


def bar(shot) -> None:
    """The player, over the wood, in every shot: the time steps at each scene."""
    stops = [(0.0, "0:04", 0.01), *((at(shot, e), shown, part) for e, (shown, part) in STOPS.items())]
    toon_inserts.voice_note_bar(
        shot.cv, shot.front, stops, TOTAL, end=shot.end, doubled=(at(shot, "tap"), at(shot, "morning"))
    )


def phone(shot, parent, ring: float | None = None, at_: tuple[float, float] = PHONE_AT) -> None:
    screens = [toon_everyday.Screen(0.0, "off")]
    if ring is not None:
        screens.append(toon_everyday.Screen(ring, "notify", "JESS", "Calling", "12:04"))
    cv = shot.cv
    toon_everyday.phone(cv, parent, screens, measure=shot.measure, at=at_, scale=PHONE_SCALE, id=cv.uid("phone"))


def opening(shot) -> None:
    """The still: the sink, him, the phone and the bar, none of it moving."""
    cv, app = shot.cv, shot.app
    toon_sets.kitchen(cv, shot.back)
    poses = toon.parse_poses([{"start": 0.0, "eyes": "half", "mouth": "flat", "arms": "desk"}], "the still")

    def draw(g) -> None:
        with cv.frozen():
            sketch.drawer("hedgehog", shot.versions)(cv, g, poses, app.end, (), enter=app.start)

    toon_world.placed(cv, shot.back, SEAT, FIGURES["hedgehog"][0], draw, pivot=SEAT)
    phone(shot, shot.front)
    toon_house.sink(cv, shot.front, id=cv.uid("sink"), inset=MARKS_IN)
    bar(shot)


def scene(shot, start: float, end: float):
    """A pair of groups, behind and in front of him, shown from ``start`` to ``end``."""
    cv = shot.cv
    return cv.group(shot.back, cv.uid("g"), start=start, end=end), cv.group(
        shot.front, cv.uid("g"), start=start, end=end
    )


def bubbles(shot, start: float) -> None:
    """What comes up from the sink when the phone has gone."""
    cv = shot.cv
    x, y = PHONE_AT
    for k, (dx, delay, r) in enumerate(((-40, 0.0, 20), (6, 0.25, 14), (44, 0.5, 18), (-10, 0.8, 12))):
        g = cv.group(shot.front, cv.uid("g"), start=start + delay, end=start + delay + 0.8, x=0.0, y=0.0)
        cv.keys(
            g, "y", [(start + delay, 0.0), (start + delay + 0.8, -toon.fh(120 + 20 * k))], kind="cubic-out", local=False
        )
        cv.ellipse(
            g, toon.fx(x + dx - r), toon.fy(y - r), toon.fh(2 * r), toon.fh(2 * r), "#d7eef2", cv.ink, toon.FINE_W / 2
        )


def dress(shot) -> None:
    """The reel is one long appearance of him; each stretch of it is a scene of its own, cut on its event."""
    cv, app = shot.cv, shot.app
    if app.who == WIDE:
        opening(shot)
        return
    laundry, teeth, water, bed = (at(shot, e) for e in ("laundry", "teeth", "water", "bed"))
    morning, ring, down = at(shot, "morning"), at(shot, "ring"), at(shot, "down")

    back, front = scene(shot, app.start, laundry)  # the sink, last night
    toon_sets.kitchen(cv, back)
    phone(shot, front)
    toon_house.sink(cv, front, id=cv.uid("sink"), inset=MARKS_IN)

    back, front = scene(shot, laundry, teeth)  # the laundry: the shirt he is folding, held up
    toon_sets.home(cv, back)
    toon_house.ledge(cv, front)
    toon_house.tee(cv, front, (172.0, 610.0), scale=1.3, id=cv.uid("tee"))

    back, front = scene(shot, teeth, water)  # his teeth
    toon_sets.home(cv, back)
    toon_house.ledge(cv, front)
    toon_house.suds(cv, front, (280.0, 640.0), 0.6, id=cv.uid("suds"))

    back, front = scene(shot, water, bed)  # the plant
    toon_sets.home(cv, back)
    toon_sets.plant(cv, front, at=(430.0, 838.0), scale=1.2)
    toon_house.watering_can(cv, front, at=(390.0, 610.0), start=water, end=bed, pour=water + 0.2, id=cv.uid("can"))
    toon_house.ledge(cv, front)

    back, front = scene(shot, bed, morning)  # the night, the phone on the quilt
    toon_house.bedroom(cv, back)
    toon_house.quilt(cv, front)
    phone(shot, front, at_=(420.0, 760.0))

    back, front = scene(shot, morning, app.end)  # the same sink
    toon_sets.kitchen(cv, back)
    sinking = cv.group(front, cv.uid("g"), x=0.0, y=0.0)
    cv.keys(sinking, "y", [(down, 0.0), (down + SINK_FALL, toon.fh(SINK_DROP))], kind="sine-in-out", local=False)
    phone(shot, sinking, ring=ring)
    toon_house.sink(cv, front, id=cv.uid("sink"), inset=MARKS_IN)
    bubbles(shot, down + SINK_FALL - 0.2)
    bar(shot)


def lens(shot, setup) -> None:
    """A slow push on him, from the big news to where the news does not come."""
    if shot.app.who == WIDE:
        return
    keys = [(at(shot, "morning"), 1.0), (at(shot, "ring"), PUSH)]
    camera.anchor(setup, toon.fx(296.0), toon.fy(900.0), place=True)
    shot.cv.keys(setup, "scaleX", keys, kind="sine-in-out", local=False)
    shot.cv.keys(setup, "scaleY", keys, kind="sine-in-out", local=False)


def sounds(beats, end) -> tuple[Sound, ...]:
    """The 2x tap, the phone ringing until it goes under, and what comes up."""
    tap = sketch.events(beats, "tap")[0][0]
    ring = sketch.events(beats, "ring")[0][0]
    down = sketch.events(beats, "down")[0][0]
    rings = tuple(ring + 1.0 * k for k in range(int((down + SINK_FALL - ring) / 1.0) + 1))
    return (
        Sound("tap", foley.REMOTE_CLICK, (tap,), -4.0),
        Sound("ring", RING, rings, -8.0),
        Sound("blub", BLUB, (down + SINK_FALL - 0.2,), -2.0),
    )

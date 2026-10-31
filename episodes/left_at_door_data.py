"""Left at Door — the sketch as data: the delivery app says delivered and shows a door nobody has ever seen, and a
sloth in slippers takes the photo and hits the streets. Told hard-boiled. He finds it. He orders again.

Two voices (ElevenLabs premade Brian as the narrator, Matilda as the neighbor). It opens on the narrator over rain
already falling (the ``sp-hook_motion`` test's arm B). ``SKETCH`` is checked by :func:`srstudio.sketch.check`;
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
    toon_sets,
    toon_world,
)
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3116
SLUG = "left-at-door"
TITLE = "Left at Door — The Gnome (Toon)"
DESCRIPTION = (
    "A Toon sketch told like a detective story: the app says delivered and shows a green door and a gnome, and a "
    "sloth in slippers goes out into the rain to find them."
)
ACCESSIBILITY = (
    "A cartoon sloth stands at a rainy window at night, lit by his phone. A photo shows noodles on a doorstep, a "
    "green door and one gnome. He owns no gnome. He walks a rainy street holding the photo up like a badge, past a "
    "green door with no gnome, a red door with a gnome and a blue door with the wrong gnome. At last he reaches the "
    "gnome. The door opens and a cartoon frog with a fork eats his noodles, half gone. She asks if he is the driver, "
    "says he is late, gives him two stars and shuts the door. Back at his window, he orders again. The phone pings: "
    "delivered, and a photo of the gnome."
)
NARRATION = (
    "Voiced with ElevenLabs premade voices Brian (the narrator) and Matilda (the neighbor); synthesized effects."
)
NOTE = "ElevenLabs premade voices Brian and Matilda at their natural pace; no reference-voice cloning."
NARRATOR = Speaker(
    "narrator",
    Voice(role="narrator", id="nPczCjzI2devNBz1zQrb", name="Brian"),
    VoiceSettings(stability=0.7, similarity_boost=0.75, style=0.1, speed=0.92),
)
FROG = Speaker(
    "frog",
    Voice(role="frog", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.2),
    "frog",
)
WIDE = "hamster"  # never seen: the name of the shots the dress draws whole
TINTS = {"narrator": "#dfe3e8", "frog": "#d6f0c8", WIDE: "#ffffff"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

FIGURES = {"sloth": (1.1, 0.0), "frog": (0.8, 215.0)}
SEAT = (165.0, 840.0)
STEP = 800.0  # where the porch's floor starts
INSIDE = "#18222e"
FRAME = "#5a4634"
NIGHT = "#0b1a3a"
GLOW = "#a9d4ff"
GREEN = "#3f7d4f"
RED = "#a33b35"
BLUE = "#3a5f9a"
WARM = "#e8b45a"
HAND = "#9c8a6c"
PUSH = 1.14  # how far the camera goes in on the gnome
END = 30.96

LINES = (
    Line("narrator", "9:00 PM. The app said delivered."),
    Line("narrator", "Nice doorstep. Green door. One gnome."),
    Line("narrator", "I don't own a gnome."),
    Line("narrator", "I took the photo and hit the streets."),
    Line("narrator", "Green door. No gnome. Gnome. Wrong gnome."),
    Line("narrator", "Four blocks. Slippers. Rain."),
    Line("frog", "You the driver? You're late."),
    Line("frog", "Two stars."),
    Line("narrator", "9:40. I ordered again."),
)

script = scripting.Script(LINES)
hold, say, first, part = script.hold, script.say, script.first, script.part

BEATS = (
    say(0.0, "sloth", 0, "half", "flat", "desk"),
    first(2.3, WIDE, 1, "Nice doorstep.", "wide", "flat", "desk", "photo"),
    part(3.46, WIDE, 1, 2, "Green door. One gnome.", "wide", "flat", "desk"),
    hold(6.42, "sloth", "", "down", "flat", "desk"),  # his own doorstep: nothing
    say(7.42, "sloth", 2, "half", "flat", "desk"),
    first(8.88, "sloth", 3, "I took the photo", "narrow", "flat", "desk", "street"),
    part(9.83, "sloth", 3, 4, "and hit the streets.", "narrow", "flat", "desk"),
    first(12.05, WIDE, 4, "Green door.", "wide", "flat", "desk", "door-green"),
    part(12.74, WIDE, 4, 2, "No gnome.", "wide", "flat", "desk"),
    part(13.61, WIDE, 4, 4, "Gnome.", "wide", "flat", "desk", "door-red"),
    part(14.03, WIDE, 4, 5, "Wrong gnome.", "wide", "flat", "desk", "door-blue"),
    say(15.0, "sloth", 5, "half", "flat", "desk"),
    hold(17.21, WIDE, "", "wide", "flat", "desk", "gnome"),  # slowly in
    hold(19.81, "frog", "", "half", "flat", "desk", "open"),  # the sting, and the door
    say(20.31, "frog", 6, "half", "flat", "desk"),
    hold(22.16, "frog", "", "down", "puff", "desk"),  # she looks at the noodles and chews
    say(23.36, "frog", 7, "half", "flat", "desk"),
    hold(24.51, WIDE, "", "wide", "flat", "desk", "shut"),  # rain, 2 s
    say(26.71, "sloth", 8, "half", "flat", "desk", "again"),
    hold(28.36, WIDE, "", "wide", "flat", "desk", "ping"),
)
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, FROG), LINES, BEATS, END, bare=(WIDE,))
ORDER = ("photo", "street", "door-green", "door-red", "door-blue", "gnome", "open", "shut", "again", "ping")


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks within 0.3 s, and the search comes once and in order."""
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


def still(who: str, eyes: str, mouth: str = "flat"):
    return toon.parse_poses([{"start": 0.0, "eyes": eyes, "mouth": mouth, "arms": "desk"}], f"{who} on the porch")


def door(cv, parent, colour: str) -> None:
    """The porch with its door painted, its floor drawn by whoever stands on it."""
    toon_world.porch(cv, parent)
    cv.rect(parent, toon.fx(362), toon.fy(274), toon.fh(240), toon.fh(528), colour, cv.ink, toon.FINE_W, radius=0)
    cv.rect(parent, toon.fx(396), toon.fy(320), toon.fh(170), toon.fh(180), colour, cv.ink, toon.FINE_W / 2, radius=0)
    cv.ellipse(parent, toon.fx(376), toon.fy(540), toon.fh(22), toon.fh(22), "#c9a23c", cv.ink, toon.FINE_W / 2)


def floor(cv, parent) -> None:
    cv.rect(parent, toon.fx(-10), toon.fy(STEP), toon.fh(612), toon.fh(360), "#6b5a48", cv.ink, toon.FINE_W, radius=0)


def night(cv, parent) -> None:
    """The grade over a street shot, and the marks over the grade."""
    cv.rect(parent, 0, 0, cv.width, cv.height, NIGHT, cv.clear, 0, radius=0, opacity=0.5)
    toon_world.marks(cv, parent)


def photo(cv, parent, banner: str) -> None:
    """The courier's photo: green door, one gnome, the noodles, and the app's word across the top."""
    door(cv, parent, GREEN)
    floor(cv, parent)
    toon_inserts.gnome(cv, parent, at=(225.0, 860.0), scale=1.1)
    toon_inserts.noodle_box(cv, parent, at=(420.0, 870.0), scale=1.0)
    toon_world.marks(cv, parent)
    cv.rect(
        parent, toon.fx(60), toon.fy(120), toon.fh(472), toon.fh(96), "#ffffff", cv.ink, toon.FINE_W, radius=toon.fh(20)
    )
    cv.text(
        parent,
        cv.uid("left-banner"),
        banner,
        toon.fx(60),
        toon.fy(132),
        int(toon.fh(472)),
        int(toon.fh(72)),
        72,
        GREEN,
        "center",
    )


def window(shot, start: float, stop: float) -> None:
    """Seen from outside: the dark room, then the frame, his phone's light and the rain on the glass."""
    cv = shot.cv
    back, front = cv.group(shot.back, cv.uid("g"), end=stop), cv.group(shot.front, cv.uid("g"), end=stop)
    cv.rect(back, 0, 0, cv.width, cv.height, INSIDE, cv.clear, 0, radius=0)
    toon_sets._glow(cv, cv.group(front, cv.uid("g"), opacity=0.4), "left-phone-glow", 300, 700, 300, GLOW)
    toon_inserts.rain(cv, front, start=start, end=stop, opacity=0.7)
    for x, y, w, h in ((-10, -140, 44, 1300), (558, -140, 44, 1300), (-10, -140, 612, 150)):
        cv.rect(front, toon.fx(x), toon.fy(y), toon.fh(w), toon.fh(h), FRAME, cv.ink, toon.FINE_W, radius=0)
    toon_house.ledge(cv, front)
    again = start >= at(shot, "again")
    state = ("Order placed", "9:40") if again else ("Delivered", "9:00")
    screen = toon_everyday.Screen(0.0, "notify", "Noodle App", *state)
    toon_everyday.phone(
        cv, front, [screen], measure=shot.measure, at=(330, 838), scale=0.9, hand=HAND, id=cv.uid("phone")
    )


def street(shot, start: float, stop: float) -> None:
    """The street, a parked car hiding his slippers, the phone up like a badge."""
    cv = shot.cv
    back, front = (
        cv.group(shot.back, cv.uid("g"), start=start, end=stop),
        cv.group(shot.front, cv.uid("g"), start=start, end=stop),
    )
    toon_world.night_street(cv, back, end=stop)
    toon_cars.side_car(cv, front, at=(200.0, 1040.0), scale=2.0, colour="#30445c")
    screen = toon_everyday.Screen(0.0, "notify", "Delivered", "Green door", "9:06")
    toon_everyday.phone(
        cv, front, [screen], measure=shot.measure, at=(440, 800), scale=0.9, hand=HAND, id=cv.uid("phone")
    )
    toon_inserts.rain(cv, front, start=start, end=stop)
    night(cv, front)


def doors(shot) -> None:
    """Door, door, door: three porches cut on the words."""
    cv = shot.cv
    green, red, blue = at(shot, "door-green"), at(shot, "door-red"), at(shot, "door-blue")
    for colour, start, stop, gnome in (
        (GREEN, green, red, None),
        (RED, red, blue, ((230.0, 860.0), 1.1)),
        (BLUE, blue, shot.app.end, ((230.0, 860.0), 0.55)),
    ):
        g = cv.group(shot.back, cv.uid("g"), start=start, end=stop)
        door(cv, g, colour)
        floor(cv, g)
        if gnome:
            toon_inserts.gnome(cv, g, at=gnome[0], scale=gnome[1])
        toon_inserts.rain(cv, g, start=start, end=stop)
        night(cv, g)


def arrival(shot, stop: float) -> None:
    """The green door, and the camera going in on the gnome."""
    cv = shot.cv
    start = at(shot, "gnome")
    cx, cy = toon.fx(225.0), toon.fy(760.0)
    root = cv.group(shot.back, cv.uid("g"), start=start, end=stop)
    g = cv.group(root, cv.uid("g"), x=cx, y=cy, anchorX=cx, anchorY=cy)
    for prop in ("scaleX", "scaleY"):
        cv.keys(g, prop, [(start, 1.0), (stop, PUSH)], hold=False, local=False)
    door(cv, g, GREEN)
    floor(cv, g)
    toon_inserts.gnome(cv, g, at=(225.0, 860.0), scale=1.1)
    toon_inserts.rain(cv, root, start=start, end=stop)
    night(cv, root)


def doorway(shot) -> None:
    """The door open, her in it with his noodles, him on the mat with the photo."""
    cv, app = shot.cv, shot.app
    door(cv, shot.back, GREEN)
    cv.rect(shot.back, toon.fx(362), toon.fy(274), toon.fh(240), toon.fh(528), WARM, cv.ink, toon.FINE_W, radius=0)
    front = shot.front
    floor(cv, front)
    toon_inserts.gnome(cv, front, at=(262.0, 860.0), scale=0.8)
    toon_inserts.noodle_box(cv, front, at=(470.0, 830.0), scale=0.9, full=0.5)

    def draw(g) -> None:
        sketch.drawer("sloth", shot.versions)(cv, g, still("sloth", "wide"), app.end, (), enter=app.start)

    toon_world.placed(cv, front, (120.0, 1190.0), 1.05, draw, pivot=SEAT)
    toon_inserts.rain(cv, front, start=app.start, end=app.end, right=330.0)
    night(cv, front)


def shut(shot, start: float, stop: float) -> None:
    """The door closed, the gnome, and him, in the rain."""
    cv = shot.cv
    g = cv.group(shot.back, cv.uid("g"), start=start, end=stop)
    door(cv, g, GREEN)
    floor(cv, g)
    toon_inserts.gnome(cv, g, at=(262.0, 860.0), scale=0.8)

    def draw(p) -> None:
        sketch.drawer("sloth", shot.versions)(cv, p, still("sloth", "half"), stop, (), enter=shot.app.start)

    toon_world.placed(cv, g, (120.0, 1190.0), 1.05, draw, pivot=SEAT)
    toon_inserts.rain(cv, g, start=start, end=stop)
    night(cv, g)


def dress(shot) -> None:
    """Each shot by what it holds: the sloth's window or street, the frog's door, or one drawn whole."""
    app = shot.app
    if app.who == "frog":
        doorway(shot)
    elif app.who == "sloth":
        outside = at(shot, "street")
        if app.start >= at(shot, "again") or app.end <= outside or app.start < outside:
            window(shot, app.start, min(app.end, outside) if app.start < outside else app.end)
        if app.start < outside < app.end:
            street(shot, outside, app.end)
        elif at(shot, "door-green") < app.start < at(shot, "again"):
            street(shot, app.start, app.end)
    elif app.start <= at(shot, "photo") < app.end:
        photo(shot.cv, shot.cv.group(shot.back, shot.cv.uid("g")), "Delivered")
    elif app.start <= at(shot, "door-green") < app.end:
        doors(shot)
    elif app.start <= at(shot, "gnome") < app.end:
        arrival(shot, app.end)
    elif app.start <= at(shot, "shut") < app.end:
        shut(shot, app.start, app.end)
    else:
        photo(shot.cv, shot.cv.group(shot.back, shot.cv.uid("g")), "Delivered")


def sounds(beats, end) -> tuple[Sound, ...]:
    """The rain under everything, the sting on the gnome, the door, and one small ping."""
    gnome = sketch.events(beats, "gnome")[0][0]
    shut_at = sketch.events(beats, "shut")[0][0]
    open_at = sketch.events(beats, "open")[0][0]
    ping = sketch.events(beats, "ping")[0][0]
    rain = foley.Burst(8.0, 5200.0, attack=0.05, decay=40.0)
    return (
        Sound("rain", rain, tuple(k * 8.0 for k in range(int(end // 8.0) + 1)), -14.0),
        Sound("sting", foley.THUD, (gnome + 1.6,), 0.0),
        Sound("open", foley.KNOCK, (open_at,), -6.0),
        Sound("shut", foley.THUD, (shut_at,), -2.0),
        Sound("ping", foley.BELL, (ping,), -4.0),
    )

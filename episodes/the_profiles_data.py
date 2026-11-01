"""The Profiles — the sketch as data: a breakup is not over until someone removes the other from the streaming
account, and nobody ever does. Mia and Brock meet to do it. Kyle and Tess are on the same TV, on episode nine.

Two voices (ElevenLabs premade River as Mia, Roger as Brock). The first frame holds the profile screen (the
``sp-hook_motion`` test's arm A); two inserts carry the reveal (:func:`srstudio.toon_homeware.profiles`,
``device_list``);
the end puts them on one side of the table. :func:`validate` checks the events; :func:`dress` draws each shot and
:func:`lens` its camera.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, scripting, sketch, toon_dinner, toon_everyday, toon_extras, toon_homeware, toon_house
from srstudio.sketch import Line, Sketch
from srstudio.toon_voices import speaker, tinted

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3113
SLUG = "the-profiles"
TITLE = "The Profiles — Mia and Brock (Toon)"
DESCRIPTION = "A Toon sketch: two exes meet to end a shared streaming account, and find a worse betrayal."
ACCESSIBILITY = (
    "A streaming screen asks who's on the couch, listing Mia, Brock, Brock's mom, Kyle and Tess. Two "
    "cartoon exes, a "
    "rabbit and a bear, sit at a restaurant table with a phone between them. She opens the device list: Kyle and Tess, "
    "their new partners, are both on the Living Room TV. They lean in, on one side of the table. It is episode nine, "
    "the one the two of them were saving. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices River (Mia) and Roger (Brock)."
NOTE = "ElevenLabs premade voices River and Roger at their natural pace; no reference-voice cloning."
MIA = speaker("mia", "River", "rabbit")
BROCK = speaker("brock", "Roger", "bear", "deadpan")
TINTS = tinted(MIA, BROCK)
BARE = ("hamster",)  # the screens
PIVOT = (980.0, 1420.0)
STILL = 0.45
NAMES = ("Mia", "Brock", "Brock's Mom", "Kyle", "Tess")
DEVICES = (("Kyle", "Living Room TV", "Now watching"), ("Tess", "Living Room TV", "Now watching"))
PHONE = dict(at=(98, 846), scale=0.9)  # at the table's left end, under the near one's shoulder: no face behind it
BROCK_AT = (392.0, 816.0)
END = 26.6

LINES = (
    Line("mia", "Three years, Brock. It's time."),
    Line("brock", "I know."),
    Line("mia", "You're on my account."),
    Line("brock", "My mom's on season five. Give her till Christmas."),
    Line("mia", "Who's Tess?"),
    Line("brock", "My girlfriend. Who's Kyle?"),
    Line("mia", "My boyfriend."),
    Line("brock", "Same TV."),
    Line("mia", "Same episode."),
    Line("mia", "That's episode nine. We were saving that."),
    Line("brock", "Monsters."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "hamster", "", "half", "none", "desk"),  # the held frame: Who's on the couch?
    say(STILL, "hamster", 0, "half", "none", "desk"),
    say(2.7, "bear", 1, "half", "flat", "desk"),
    say(3.6, "rabbit", 2, "half", "flat", "crossed"),
    first(5.1, "bear", 3, "My mom's on season five.", "half", "flat", "desk"),
    part(6.7, "bear", 3, 5, "Give her till Christmas.", "half", "flat", "desk"),
    say(8.5, "rabbit", 4, "narrow", "flat", "crossed"),
    first(9.6, "bear", 5, "My girlfriend.", "half", "flat", "desk"),
    part(10.6, "bear", 5, 2, "Who's Kyle?", "narrow", "flat", "crossed"),
    say(11.8, "rabbit", 6, "half", "flat", "crossed"),
    hold(13.0, "hamster", "", "half", "none", "desk", "devices"),  # two seconds on the list
    say(15.0, "rabbit", 7, "wide", "flat", "lean", "together"),
    say(16.2, "rabbit", 8, "wide", "open", "lean"),
    hold(17.4, "rabbit", "", "narrow", "flat", "lean"),  # she looks closer
    hold(18.2, "rabbit", "", "shock", "drop", "lean"),
    first(18.9, "rabbit", 9, "That's episode nine.", "shock", "open", "lean"),
    part(20.3, "rabbit", 9, 3, "We were saving that.", "teary", "frown", "lean"),
    hold(22.0, "bear", "", "wide", "flat", "lean"),
    hold(22.6, "bear", "", "teary", "frown", "lean"),  # three years of grief and only this
    say(23.3, "bear", 10, "narrow", "flat", "lean"),
)
SKETCH = Sketch(SLUG, TITLE, (MIA, BROCK), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent; the first frame is held and a line starts by 0.5 s; the list and the move come
    once, the move after the list."""
    sketch.check(sk)
    if sk.beats[0].spoken or sk.beats[1].start > 0.5:
        raise sketch.SketchError("the first frame is held, a line by 0.5 s")
    scripting.exactly_once(sk.beats, "devices", "the list opens once")
    scripting.exactly_once(sk.beats, "together", "they move to one side once")
    scripting.only_events(sk.beats, {"devices", "together"})


def dress(shot) -> None:
    """The screens, the table; from ``together`` both of them on one side of it."""
    cv, app = shot.cv, shot.app
    listing = sketch.events(shot.beats, "devices")[0][0]
    together = sketch.events(shot.beats, "together")[0][0]
    if app.who == "hamster":
        if app.start < listing:
            toon_homeware.profile_list(cv, shot.back, NAMES, app.start, app.end)
        else:
            toon_homeware.device_list(cv, shot.back, DEVICES, app.start, app.end, paints=toon_homeware.LIGHT_SCREEN)
        toon_house.ledge(cv, shot.front, "white")
        return
    toon_dinner.restaurant(cv, shot.back)
    if app.start >= together:
        other = "bear" if app.who == "rabbit" else "rabbit"
        look = ((0.0, "wide", "flat", "lean"),)
        toon_extras.figure(shot, shot.back, other, BROCK_AT, 0.9, look, mirror=True)
    toon_dinner.table(cv, shot.front)
    screen = toon_everyday.Screen(0.0, "code", "WATCHING", "S3 E9", "")
    if app.start >= together:
        toon_everyday.phone(cv, shot.front, [screen], measure=shot.measure, id=cv.uid("phone"), **PHONE)


def lens(shot, setup) -> None:
    """Held; a slow push on the two of them."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.start >= sketch.events(shot.beats, "together")[0][0] and shot.app.who == "bear":
        a = shot.app.start
        camera.push_in(shot.cv, setup, scale=[(a, 1.0), (a + 2.4, 1.08)])

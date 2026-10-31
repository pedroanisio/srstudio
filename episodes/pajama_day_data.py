"""Pajama Day — the sketch as data: the school parents' group chat is so gripping that nobody can leave it, even long
after they should. Mae is following pajama day. Her son is in college. Thirty cupcakes wait behind her.

Two voices (ElevenLabs premade Sarah as Mae, Bill as Bruno). The phone walks itself across the table from the first
frame (the ``sp-hook_motion`` test's arm B), its count climbing; the insert is the worktop
(:func:`srstudio.toon_homeware.cupcakes`). :func:`validate` checks the events; :func:`dress` draws each shot,
:func:`lens` its camera and :func:`foley` its sound.
"""

from __future__ import annotations

from srstudio import camera, scripting, sketch, toon_everyday, toon_homeware, toon_house, toon_sets
from srstudio import foley as synth
from srstudio.sketch import Line, Sketch
from srstudio.toon import fh
from srstudio.toon_voices import speaker, tinted

SEED = 3120
SLUG = "pajama-day"
TITLE = "Pajama Day — Mae and the Class Chat (Toon)"
DESCRIPTION = "A Toon sketch: Mae is deep in the class chat about pajama day. Her son is in college."
ACCESSIBILITY = (
    "A phone buzzes itself across a kitchen table, its message count climbing from 214. A cartoon bear asks who keeps "
    "texting; a cartoon rabbit, not looking up, reports a chat about pajama day, a man who left the group and "
    "a poll about "
    "nuts. He tells her their son is in college. She says she knows. He looks past her. The worktop behind her "
    "holds thirty "
    "cupcakes, each with a tiny flag. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae) and Bill (Bruno)."
NOTE = "ElevenLabs premade voices Sarah and Bill at their natural pace; no reference-voice cloning."
MAE = speaker("mae", "Sarah", "rabbit")
BRUNO = speaker("bruno", "Bill", "bear", "deadpan")
TINTS = tinted(MAE, BRUNO)
BARE = ("hamster",)  # the worktop
PIVOT = (980.0, 1420.0)
PHONE = dict(at=(452, 838), scale=0.9)
COUNTS = (214, 231, 262, 298, 344, 389)
END = 25.6

LINES = (
    Line("bruno", "Who keeps texting you?"),
    Line("mae", "Class chat. Is tomorrow pajama day?"),
    Line("bruno", "Is it?"),
    Line("mae", "Nobody knows. Denise says Thursday. Tom left the group. His wife added him back."),
    Line("mae", "There's a poll about nuts."),
    Line("bruno", "Honey."),
    Line("mae", "Shh. Denise is typing."),
    Line("bruno", "Honey. Our son is in college."),
    Line("mae", "I know."),
    Line("bruno", "So who are those for?"),
    Line("mae", "Thursday."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "bear", "", "side", "flat", "desk", "buzz"),  # the phone walking across the table
    say(0.2, "bear", 0, "side", "flat", "desk"),
    first(1.8, "rabbit", 1, "Class chat.", "down", "flat", "lean", "buzz"),
    part(2.8, "rabbit", 1, 2, "Is tomorrow pajama day?", "down", "flat", "lean"),
    say(4.6, "bear", 2, "half", "flat", "desk"),
    first(5.4, "rabbit", 3, "Nobody knows.", "down", "flat", "lean"),
    part(6.3, "rabbit", 3, 2, "Denise says Thursday.", "down", "flat", "lean", "buzz"),
    part(7.7, "rabbit", 3, 5, "Tom left the group.", "narrow", "flat", "lean"),
    part(9.0, "rabbit", 3, 9, "His wife added him back.", "wide", "flat", "lean", "buzz"),
    say(10.8, "rabbit", 4, "wide", "flat", "lean"),
    say(12.5, "bear", 5, "half", "flat", "desk"),
    say(13.2, "rabbit", 6, "narrow", "flat", "lean", "buzz"),
    first(15.0, "bear", 7, "Honey.", "half", "flat", "desk"),
    part(15.8, "bear", 7, 1, "Our son is in college.", "half", "flat", "desk"),
    hold(17.6, "rabbit", "", "down", "none", "lean", "buzz"),  # two seconds; she does not look up
    say(19.6, "rabbit", 8, "down", "flat", "lean"),
    hold(20.4, "bear", "", "side", "flat", "desk"),  # he looks past her
    say(21.4, "bear", 9, "side", "flat", "desk"),
    hold(22.9, "hamster", "", "half", "none", "desk", "tray"),  # the reverse
    say(23.5, "hamster", 10, "half", "none", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (MAE, BRUNO), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s; one count per buzz; the tray comes once, last."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    if len(sketch.events(sk.beats, "buzz")) != len(COUNTS):
        raise sketch.SketchError(f"{len(COUNTS)} counts, one per buzz")
    scripting.exactly_once(sk.beats, "tray", "the tray is seen once")
    scripting.only_events(sk.beats, {"buzz", "tray"})


def dress(shot) -> None:
    """The kitchen with the phone on the table, walking and climbing; the worktop insert."""
    cv, app = shot.cv, shot.app
    if app.who == "hamster":
        toon_homeware.cupcakes(cv, shot.back, app.start, app.end)
        toon_house.ledge(cv, shot.front, "white")
        return
    toon_sets.kitchen(cv, shot.back)
    toon_house.ledge(cv, shot.front, "oak")
    buzzes = [t for t, _ in sketch.events(shot.beats, "buzz")]
    screens = [
        toon_everyday.Screen(t, "notify", "Class Chat", "new messages", str(n))
        for t, n in zip(buzzes, COUNTS, strict=True)
    ]
    walk = cv.group(shot.front, cv.uid("g"))
    toon_everyday.phone(cv, walk, screens, measure=shot.measure, id=cv.uid("phone"), **PHONE)
    if app.start == 0.0:
        cv.keys(walk, "x", [(0.0, fh(130)), (app.end, 0.0)], hold=False)


def lens(shot, setup) -> None:
    """Still, with a push on Mae when she does not look up."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.who == "rabbit":
        stare = [b for b in shot.beats if b.line == 8][0].start
        if shot.app.start <= stare < shot.app.end:
            camera.push_in(shot.cv, setup, scale=[(stare - 2.0, 1.0), (stare + 0.6, 1.08)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The phone buzzing on the wood."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    buzz = synth.write_buzz(audio / "buzz.wav", [t for t, _ in sketch.events(beats, "buzz")], end, seed=seed)
    return [sketch.effect("buzz", 0.0, -10.0, root, buzz)]

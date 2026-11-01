"""Call Your Mother — the sketch as data: interviewing from your parents' house, your mother will walk in, and she
negotiates harder than you ever would. She takes the laptop, says nothing for a while, and fifty-five becomes seventy.

Three voices (ElevenLabs premade Jessica as Dana, Liam as the son, Laura as his mother): Dana in the meeting room with
her phone on the desk, the son in his childhood bedroom, Mom's face filling the laptop. The first shot pushes in from
its first frame (the ``sp-hook_motion`` test's arm B). :func:`validate` checks the events; :func:`dress` draws each
shot, :func:`lens` its camera and :func:`foley` its sound.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, scripting, sketch, toon, toon_everyday, toon_homeware, toon_house, toon_props
from srstudio import foley as synth
from srstudio.sketch import Line, Sketch
from srstudio.toon_voices import speaker, tinted

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3111
SLUG = "call-your-mother"
TITLE = "Call Your Mother — Dana and Mom (Toon)"
DESCRIPTION = "A Toon sketch: an interview from your childhood bedroom, until your mother takes the laptop."
ACCESSIBILITY = (
    "A cartoon dog in a meeting room asks a young fox on a video call about salary. His mother, a cartoon cat, "
    "walks in "
    "with a plate of toast, sits down and turns the laptop to herself, her face filling the call. She stares into the "
    "lens without blinking while the offer rises. She shuts the laptop. Alone, the dog looks at her phone and calls "
    "her own mother. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Jessica (Dana), Liam (the son) and Laura (Mom)."
NOTE = "ElevenLabs premade voices Jessica, Liam and Laura at their natural pace; no reference-voice cloning."
DANA = speaker("dana", "Jessica", "dog")
SON = speaker("son", "Liam", "fox")
MOM = speaker("mom", "Laura", "cat", "deadpan")
TINTS = tinted(DANA, SON, MOM)
FIGURES = {"cat": (1.0, 66.0)}  # at her traced size, her base on the ledge's edge; moved in to fill his bedroom
PLATE_AT = (400.0, 838.0)  # the toast, on the ledge, clear of the cactus
LEAD = 0.45  # the silence before the first word
PIVOT = (980.0, 1420.0)
PHONE = dict(at=(452, 838), scale=0.9)
KEY_LINE = "Interviewing from your mom's."
END = 27.0

LINES = (
    Line("dana", "And what salary are you looking for?"),
    Line("son", "Oh, I'm really flexible."),
    Line("mom", "He is not flexible."),
    Line("son", "Mom!"),
    Line("mom", "Is this the job? What's the dental?"),
    Line("dana", "We're offering fifty-five."),
    Line("dana", "Seventy."),
    Line("dana", "And dental."),
    Line("mom", "He starts Monday. You look tired. Call your mother."),
    Line("dana", "Hi, Mom."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "dog", "", "half", "flat", "desk"),
    first(LEAD, "dog", 0, "And what salary", "half", "open", "desk"),
    part(1.5, "dog", 0, 3, "are you looking for?", "half", "open", "desk"),
    say(2.8, "fox", 1, "half", "grin", "desk"),
    hold(4.6, "fox", "", "side", "flat", "desk", "door"),
    say(5.1, "cat", 2, "half", "flat", "desk"),
    say(6.6, "fox", 3, "shock", "open", "lean"),
    first(7.4, "cat", 4, "Is this the job?", "half", "flat", "desk"),
    part(8.6, "cat", 4, 4, "What's the dental?", "narrow", "flat", "desk"),
    say(10.2, "dog", 5, "half", "grin", "desk"),
    hold(12.0, "cat", "", "narrow", "flat", "desk"),  # two and a half seconds into the lens
    hold(13.3, "dog", "", "left", "flat", "desk"),
    hold(13.9, "dog", "", "side", "flat", "desk", "tick"),
    say(14.6, "dog", 6, "wide", "flat", "desk", wear=("sweat",)),
    hold(15.5, "cat", "", "narrow", "flat", "desk"),  # she does not blink
    say(17.0, "dog", 7, "wide", "flat", "desk", wear=("sweat",)),
    first(17.9, "cat", 8, "He starts Monday.", "half", "flat", "desk"),
    part(19.3, "cat", 8, 3, "You look tired.", "half", "flat", "desk"),
    part(20.4, "cat", 8, 6, "Call your mother.", "narrow", "flat", "desk"),
    hold(21.9, "dog", "", "wide", "flat", "desk", "shut"),  # the lid; alone in the room
    hold(23.0, "dog", "", "down", "flat", "desk"),
    hold(23.7, "dog", "", "half", "flat", "lean"),
    say(24.6, "dog", 9, "half", "frown", "lean", wear=("sweat",)),
)
SKETCH = Sketch(SLUG, TITLE, (DANA, SON, MOM), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent; it opens silent, a line by 0.5 s; the door opens once, the lid shuts once, on
    Dana's shot, after every line but hers."""
    sketch.check(sk)
    if sk.beats[0].spoken or sk.beats[1].start > 0.5:
        raise sketch.SketchError("it opens silent, a line by 0.5 s")
    for kind in ("door", "shut", "tick"):
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    scripting.only_events(sk.beats, {"door", "shut", "tick"})


def dress(shot) -> None:
    """The meeting room and its desk with her phone; his bedroom; Mom filling the same bedroom."""
    cv, app = shot.cv, shot.app
    if app.who == "dog":
        toon_props.meeting(cv, shot.back)
        toon.desk(cv, shot.front)
        shut = sketch.events(shot.beats, "shut")[0][0]
        screens = [
            toon_everyday.Screen(0.0, "off"),
            toon_everyday.Screen(shut, "notify", "Mom", "Missed call (3)", "9:04"),
        ]
        toon_everyday.phone(cv, shot.front, screens, measure=shot.measure, id=cv.uid("phone"), **PHONE)
    else:
        toon_house.bedroom(cv, shot.back)
        toon_house.ledge(cv, shot.front, "oak")
        if app.who == "cat":
            toon_homeware.toast(cv, shot.front, at=PLATE_AT)
    if app.start == 0.0:
        toon_house.key_line(cv, shot.front, KEY_LINE, 0.0, 2.6, measure=shot.measure)


def lens(shot, setup) -> None:
    """A slow push from the first frame; a slow push on Mom through the silence."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.start == 0.0:
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (shot.app.end, 1.05)])
    if shot.app.who == "cat":
        a = shot.app.start
        camera.push_in(shot.cv, setup, scale=[(a, 1.0), (a + 2.0, 1.05)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The bedroom door, a tick in the silence and the lid."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    door = synth.write_bursts(
        audio / "door.wav", [t for t, _ in sketch.events(beats, "door")], end, synth.KNOCK, seed=seed
    )
    lid = synth.write_bursts(
        audio / "lid.wav", [t for t, _ in sketch.events(beats, "shut")], end, synth.THUD, seed=seed
    )
    return [sketch.effect("door", 0.0, -12.0, root, door), sketch.effect("lid", 0.0, -8.0, root, lid)]

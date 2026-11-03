"""One symptom: the sketch as data. A patient reads a doctor his own diagnosis off a phone. The doctor takes the phone
to prove a point, reads the symptoms, and looks at his left thumb. They swap chairs, and the patient has the glasses.

Toon, ElevenLabs premade Callum (the patient) and Brian (the doctor). Its first shot pushes in, the ``sp-hook_motion``
test's arm b. Each shot holds one character; the two-shot of the script is a held medium cut on the line. :func:`dress`
draws the surgery, the phone and the thumb.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley, scripting, sketch, toon_everyday, toon_house, toon_surgery, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_everyday import Screen
from srstudio.toon_sketch import Sound, opening_push
from srstudio.voice import Voice, VoiceSettings

SEED = 3108
SLUG = "one-symptom"
TITLE = "One symptom (Toon)"
DESCRIPTION = "A patient diagnoses himself online. The doctor takes the phone to prove a point."
ACCESSIBILITY = (
    "A cartoon hedgehog tells his doctor, a sloth, he has late-stage tongue rot. The doctor says it is a headache and "
    "takes the phone to read the symptoms aloud. He stops at tingling left thumb, looks at his thumb, and it twitches. "
    "How long have I got, he asks. They have swapped places: the hedgehog wears the glasses now and reads from the "
    "phone. Four days, but there's a forum. They're very supportive."
)
NARRATION = "Voiced with ElevenLabs premade voices Callum (the patient) and Brian (the doctor); synthesised foley."
NOTE = "ElevenLabs premade voices Callum and Brian at their natural pace; no reference-voice cloning."
PATIENT = Speaker(
    "patient",
    Voice(role="patient", id="N2lVS1w4EtoT3dr4eOWO", name="Callum"),
    VoiceSettings(0.45, 0.75, 0.35),
    "hedgehog",
)
DOCTOR = Speaker(
    "doctor", Voice(role="doctor", id="nPczCjzI2devNBz1zQrb", name="Brian"), VoiceSettings(0.6, 0.75, 0.15), "sloth"
)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
TINTS = {"patient": "#e5d9c9", "doctor": "#d3e3cf"}
TONGUE = "LATE-STAGE TONGUE ROT"
SWALLOW = foley.Burst(0.1, 900.0, attack=0.005, decay=0.4, tone_hz=240.0, tone_end_hz=140.0, tone=0.5)
TWITCHES = 3
EVENTS = {"takes", "thumb", "sting", "swap"}
THUMB = (420.0, 720.0)
END = 23.1

LINES = (
    Line("patient", "It's late-stage tongue rot. Eleven known cases."),
    Line("doctor", "You have a headache."),
    Line("patient", "That's how it starts."),
    Line("doctor", "Did you look this up?"),
    Line("patient", "At one in the morning. I've written a will."),
    Line("doctor", "Give me that. Headache. Dry mouth. Tingling left thumb."),
    Line("doctor", "How long have I got?"),
    Line("patient", "Four days. But there's a forum.", gain=-4.0),
    Line("doctor", "Is it a good forum?", gain=-7.0),
    Line("patient", "They're very supportive."),
)
SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold
BEATS = (
    first(0.0, "hedgehog", 0, "It's late-stage tongue rot.", "wide", "flat", "desk"),
    part(1.9, "hedgehog", 0, 4, "Eleven known cases.", "wide", "flat", "desk"),
    say(3.5, "sloth", 1, "half", "flat", "desk"),
    say(4.5, "hedgehog", 2, "narrow", "flat", "desk"),
    say(6.0, "sloth", 3, "half", "flat", "desk"),
    first(7.2, "hedgehog", 4, "At one in the morning.", "wide", "flat", "desk"),
    part(8.5, "hedgehog", 4, 5, "I've written a will.", "wide", "flat", "desk"),
    first(10.2, "sloth", 5, "Give me that.", "half", "flat", "desk", "takes"),
    part(10.95, "sloth", 5, 3, "Headache. Dry mouth.", "down", "flat", "desk"),
    part(12.1, "sloth", 5, 6, "Tingling left thumb.", "down", "flat", "desk"),
    hold(13.3, "sloth", "", "down", "flat", "desk", "thumb"),
    say(15.2, "sloth", 6, "wide", "o", "desk", "sting"),
    hold(16.2, "hedgehog", "", "half", "flat", "desk", "swap"),
    say(16.6, "hedgehog", 7, "half", "flat", "desk"),
    say(19.2, "sloth", 8, "teary", "flat", "desk"),
    say(20.3, "hedgehog", 9, "half", "smirk", "desk"),
    hold(21.7, "sloth", "", "teary", "wave", "desk"),
)
SWAP = 16.2
BEATS = tuple(  # whoever has the doctor's seat has the doctor's glasses
    replace(b, wear=("glasses",)) if (b.who == "sloth") == (b.start < SWAP) else b for b in BEATS
)
SKETCH = Sketch(SLUG, TITLE, (PATIENT, DOCTOR), LINES, BEATS, END)


def event(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """He takes the phone, finds the thumb, asks, and only then do they swap."""
    sketch.check(sk)
    scripting.only_events(sk.beats, EVENTS)
    for kind in EVENTS:
        scripting.exactly_once(sk.beats, kind, f"one {kind}")
    if not event(sk.beats, "takes") < event(sk.beats, "thumb") < event(sk.beats, "swap"):
        raise sketch.SketchError("the phone, the thumb, then the swap")


def dress(shot) -> None:
    """The patient's seat is the chair, the doctor's the cupboards, until they swap. The phone goes with the reader."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    takes, thumb, swap = event(beats, "takes"), event(beats, "thumb"), event(beats, "swap")
    after = app.start >= swap
    chair = (app.who == "hedgehog") != after
    toon_surgery.surgery(cv, shot.back, "chair" if chair else "cupboards")
    toon_house.ledge(cv, shot.front, "oak")
    reading = app.who == "hedgehog" if app.end <= takes or after else app.start >= takes
    if reading:
        hand = cv.group(
            shot.front, cv.uid("g"), start=app.start, end=min(app.end, thumb if thumb > app.start else app.end)
        )
        screen = (Screen(0.0, "notify", title="Tongue rot", text="11 known cases"),)
        at = (440.0, 790.0)
        toon_everyday.phone(cv, hand, screen, measure=shot.measure, at=at, scale=1.0, id=f"phone-{int(app.start * 10)}")
    if app.who == "sloth" and app.start <= thumb < app.end:
        keys = []
        for k in range(TWITCHES):
            keys += [(thumb + 0.3 + k * 0.42, *THUMB), (thumb + 0.42 + k * 0.42, THUMB[0] + 22, THUMB[1] - 6)]
        toon_house.finger(cv, shot.front, THUMB, 25.0, "#c5a77a", "#c5a77a", keys, thumb, app.end, id="thumb")


def sounds(beats, end: float) -> list[Sound]:
    """The taps on the phone, the swallow and a low note as he asks."""
    return [
        Sound("tap", foley.REMOTE_CLICK, (event(beats, "takes"), event(beats, "swap") + 0.4), -9.0),
        Sound("swallow", SWALLOW, (event(beats, "thumb") + 1.4,), -6.0),
        Sound("sting", foley.THUD, (event(beats, "sting"),), -8.0),
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

"""It's Soaking — the sketch as data: everyone has lived with a pan that is soaking. Day 1: a pan in the sink, and the
roommate, passing, says it's soaking. Day 9: a skin. Day 23: a plant. Day 41: the pan gets mail. Day 60: a tiny frog
waves, and the roommate waters the plant. The landlord counts three occupants, and says it'll need its own deposit.

Two voices (ElevenLabs premade Will as the roommate, Roger as the landlord); the first person, a rabbit, never speaks.
The sink (:func:`srstudio.toon_house.sink`) stands in for the desk in every shot, the day counts on a card on the
fridge (:func:`srstudio.toon_house.day_card`). The sketch opens on a still first second (the ``sp-hook_motion`` test's
arm A). ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the
props; :func:`dress` draws each shot's set and props, and :func:`foley` its sound.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley as synth
from srstudio import scripting, sketch, toon_everyday, toon_house, toon_sets
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 2407
SLUG = "its-soaking"
TITLE = "It's Soaking — the Pan (Toon)"
DESCRIPTION = (
    "A Toon sketch in a shared kitchen: a pan left in the sink is soaking on day one, and still soaking on day sixty, "
    "by which point it has a plant, a mailbox and a resident."
)
ACCESSIBILITY = (
    "A cartoon rabbit stares down at a pan in a kitchen sink, a card on the fridge reading Day 1. A raccoon says it's "
    "soaking. The card counts up: on day 9 the water has a skin, on day 23 a plant grows from it, on day 41 it has a "
    "small mailbox, on day 60 a tiny frog waves from it. The raccoon waters the plant. A sloth landlord with a "
    "clipboard asks about three occupants. The raccoon beams. The rabbit stares. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Will (the roommate) and Roger (the landlord); synthesised effects."
NOTE = "ElevenLabs premade voices Will and Roger at their natural pace; no reference-voice cloning."
ROOMMATE = Speaker(
    "roommate",
    Voice(role="roommate", id="bIHbv24MWmeRgasZH58o", name="Will"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.25),
    "raccoon",
)
LANDLORD = Speaker(
    "landlord",
    Voice(role="landlord", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
    VoiceSettings(stability=0.75, similarity_boost=0.75, style=0.10),
    "sloth",
)
TINTS = {"roommate": "#ffe0b8", "landlord": "#d9e8ff"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

STILL = 1.0  # seconds of the held first frame
FIGURES = {"rabbit": (1.12, 0.0), "raccoon": (1.12, 0.0), "sloth": (1.12, 0.0)}
STAGE_OF = {9: "skin", 23: "plant", 41: "mail", 60: "frog"}
LEASE_AT = {"at": (414, 790), "scale": 1.2}
CAN_AT = (262, 700)  # the rose above the plant
CROAK = ((420.0, 300.0, 0.14), (440.0, 310.0, 0.14))
END = 18.4

LINES = (
    Line("roommate", "It's soaking."),
    Line("roommate", "It's soaking."),
    Line("roommate", "It's soaking."),
    Line("roommate", "Don't touch it, it's soaking."),
    Line("landlord", "Three occupants?"),
    Line("landlord", "It'll need its own deposit."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say

BEATS = (
    hold(0.0, "rabbit", "", "down", "flat", "desk"),  # the still: day 1
    say(1.2, "raccoon", 0, "half", "smirk", "desk"),
    hold(2.5, "rabbit", "", "down", "flat", "desk", "day:9"),
    say(3.5, "raccoon", 1, "half", "smirk", "desk"),
    hold(4.8, "rabbit", "", "down", "frown", "desk", "day:23"),
    say(5.8, "raccoon", 2, "half", "smirk", "desk"),
    hold(7.1, "rabbit", "", "wide", "flat", "desk", "day:41"),
    hold(8.3, "rabbit", "", "shock", "flat", "desk", "day:60"),
    say(9.7, "raccoon", 3, "half", "grin", "desk", "water"),
    say(11.7, "sloth", 4, "half", "flat", "desk"),
    hold(13.2, "rabbit", "", "side", "grin", "desk"),  # hope, for the first time
    say(14.2, "sloth", 5, "half", "flat", "desk", "lease"),
    hold(16.1, "raccoon", "", "closed", "grin", "desk", wear=("flush",)),  # proud
    hold(17.1, "rabbit", "", "half", "flat", "desk"),  # stop on the face
)
SKETCH = Sketch(SLUG, TITLE, (ROOMMATE, LANDLORD), LINES, BEATS, END)


def days(beats) -> list[tuple[float, int]]:
    """Day 1 from the top, then each ``day:`` event."""
    return [(0.0, 1), *((at, int(day)) for at, day in sketch.events(beats, "day"))]


def stages(beats) -> list[tuple[float, str]]:
    """What the pan has grown by each ``day:`` event."""
    return [(at, STAGE_OF[int(day)]) for at, day in sketch.events(beats, "day")]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the first beat is the still (silent,
    uncaptioned, held at least :data:`STILL`); the days are the four the pan grows on, rising; the roommate waters the
    plant once, after the frog; the lease is marked once; no other events."""
    sketch.check(sk)
    opening, second = sk.beats[0], sk.beats[1]
    if opening.spoken or opening.caption or second.start < STILL:
        raise sketch.SketchError(f"the sketch opens on a still of the rabbit: silent, uncaptioned, held {STILL} s")
    if [int(day) for _, day in sketch.events(sk.beats, "day")] != sorted(STAGE_OF):
        raise sketch.SketchError(f"the days are {sorted(STAGE_OF)}, in order")
    for event in ("water", "lease"):
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    if sketch.events(sk.beats, "water")[0][0] < sketch.events(sk.beats, "day")[-1][0]:
        raise sketch.SketchError("the roommate waters the plant after the frog")
    scripting.only_events(sk.beats, {"day", "water", "lease"})


def no_desk(cv, parent) -> None:
    """Each shot lays its own surface: see :func:`dress`."""


def dress(shot) -> None:
    """The kitchen and the sink in every shot, with the pan as it stands by then; the day card on the rabbit's shots;
    the can on the raccoon's shot with the water in it; the lease on the sloth's."""
    cv, app = shot.cv, shot.app
    end = shot.end
    toon_sets.kitchen(cv, shot.back)
    toon_house.sink(cv, shot.front, stages(shot.beats), end, id=cv.uid("sink"))
    if app.who == "rabbit":
        toon_house.day_card(cv, shot.back, days(shot.beats), end, id=cv.uid("day-card"))
    water = sketch.events(shot.beats, "water")[0][0]
    if app.who == "raccoon" and app.start <= water < app.end:
        toon_house.watering_can(
            cv, shot.front, CAN_AT, start=app.start, end=app.end, pour=water + 0.3, id=cv.uid("can")
        )
    if app.who == "sloth":
        at = sketch.events(shot.beats, "lease")[0][0]
        fields = [toon_everyday.Field("Occupants", "3", 0.0), toon_everyday.Field("Deposit", "+1 pan", at)]
        toon_everyday.clipboard(cv, shot.front, "LEASE", fields, measure=shot.measure, id=cv.uid("lease"), **LEASE_AT)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """A page turning on each day, a pour, and the tiny frog."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    day_times = [at for at, _ in sketch.events(beats, "day")]
    page = synth.write_typing(audio / "page.wav", day_times, end)
    pour = synth.write_whoosh(audio / "pour.wav", [at for at, _ in sketch.events(beats, "water")], end)
    croak = synth.write_tones(audio / "croak.wav", [day_times[-1] + 0.35], end, CROAK)
    return [
        sketch.effect("page", 0.0, -5.0, root, page),
        sketch.effect("pour", 0.0, -14.0, root, pour),
        sketch.effect("croak", 0.0, -8.0, root, croak),
    ]

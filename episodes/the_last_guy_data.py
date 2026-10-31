"""The Last Guy: the sketch as data. A plumber breathes in through his teeth at the state of the pipe. A child did
this. He photographs it for the guys. Fern lays his own invoice beside him. Anyone can type Rex. He hands her a card.

Toon, two voices (ElevenLabs premade Charlie as Rex, Matilda as Fern). The first second is held (the
``sp-hook_motion`` test's arm a). :func:`validate` checks the events; :func:`dress` draws each shot's kitchen, the pipe
and the inserts; :func:`sounds` is the foley.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley, scripting, sketch, toon_house, toon_odds, toon_sets, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3101
SLUG = "the-last-guy"
TITLE = "The Last Guy (Toon)"
DESCRIPTION = "A plumber is appalled by the last guy's work. The last guy was him."
ACCESSIBILITY = (
    "A cartoon dog in a kitchen looks at a dripping pipe and asks who did this to you. A frog with folded arms asks if "
    "it is bad. He says a child did this and photographs it. She shows him the invoice: Rex's Plumbing, March, signed "
    "Rex. He says anyone can type Rex and hands her a card reading We fix what the last guy did. The pipe sprays "
    "behind the frog, who does not move."
)
NARRATION = "Voiced with ElevenLabs premade voices Charlie (Rex) and Matilda (Fern); synthesised foley."
NOTE = "ElevenLabs premade voices Charlie and Matilda at their natural pace; no reference-voice cloning."
REX = Speaker(
    "rex", Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie"), VoiceSettings(0.45, 0.75, 0.35), "dog"
)
FERN = Speaker(
    "fern", Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"), VoiceSettings(0.55, 0.75, 0.25), "frog"
)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
TINTS = {"rex": "#fbe0b8", "fern": "#d9f0e3"}
KEY_LINE = "The last guy did this."
DRIP = foley.Burst(0.07, 1800.0, attack=0.001, decay=0.12, tone_hz=1250.0, tone_end_hz=1900.0, tone=0.8)
DRIP_EVERY = 1.3
EVENTS = {"shutter", "invoice", "back", "card", "spray", "hangup"}
END = 18.8

LINES = (
    Line("rex", "Oh, no. Who did this to you?"),
    Line("fern", "Is it bad?"),
    Line("rex", "A child did this. A child, in the dark."),
    Line("rex", "Whoever did this should not own a wrench."),
    Line("rex", "I'm sending this to the guys. They'll want to see this."),
    Line("fern", "You did this."),
    Line("rex", "Anyone can type Rex."),
    Line("rex", "You need a specialist."),
)
SCRIPT = scripting.Script(LINES)
say, hold, first, part = SCRIPT.say, SCRIPT.hold, SCRIPT.first, SCRIPT.part
BEATS = (
    first(0.0, "dog", 0, "Oh, no.", "wide", "frown", "desk"),
    part(1.2, "dog", 0, 2, "Who did this to you?", "narrow", "frown", "desk"),
    say(1.9, "frog", 1, "wide", "flat", "crossed"),
    first(2.8, "dog", 2, "A child did this.", "narrow", "flat", "sigh"),
    part(3.9, "dog", 2, 4, "A child, in the dark.", "half", "flat", "sigh"),
    first(5.4, "dog", 3, "Whoever did this", "narrow", "grimace", "crossed"),
    part(6.1, "dog", 3, 3, "should not own a wrench.", "narrow", "grimace", "crossed"),
    first(7.4, "dog", 4, "I'm sending this to the guys.", "side", "smirk", "type", "shutter"),
    part(8.7, "dog", 4, 6, "They'll want to see this.", "side", "grin", "type"),
    hold(10.3, "frog", "", "half", "flat", "crossed", "invoice"),
    say(10.7, "frog", 5, "half", "flat", "crossed"),
    hold(12.6, "dog", "", "shock", "grimace", "desk", "back"),
    say(13.4, "dog", 6, "side", "smirk", "desk"),
    hold(14.7, "dog", "", "wide", "grin", "desk", "card"),
    say(15.0, "dog", 7, "wide", "grin", "desk"),
    hold(16.9, "frog", "", "half", "flat", "crossed", "spray"),
    hold(17.2, "frog", "", "half", "flat", "crossed", "hangup"),
)
SKETCH = Sketch(SLUG, TITLE, (REX, FERN), LINES, BEATS, END)


def event(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """Each event once, the invoice before the card, the spray last, nothing spoken after it."""
    sketch.check(sk)
    for kind in sorted(EVENTS):
        scripting.exactly_once(sk.beats, kind, f"one {kind}")
    scripting.only_events(sk.beats, EVENTS)
    if not event(sk.beats, "invoice") < event(sk.beats, "card") < event(sk.beats, "spray"):
        raise sketch.SketchError("the invoice, then the card, then the spray")
    if max(b.start for b in sk.beats if b.spoken) > event(sk.beats, "spray"):
        raise sketch.SketchError("nobody speaks after the spray: it is the peak")


def dress(shot) -> None:
    """The kitchen with its pipe behind whoever is on; the two inserts over their shots."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    toon_sets.kitchen(cv, shot.back)
    spray = event(beats, "spray")
    drips = [t * DRIP_EVERY + 0.2 for t in range(int(spray / DRIP_EVERY))]
    here = [t - 0.0 for t in drips if app.start <= t < app.end - 0.4]
    toon_odds.pipe(cv, shot.back, (470.0, 610.0), here, spray if app.start <= spray < app.end else None, shot.end)
    toon_house.ledge(cv, shot.front, "oak")
    if app.start == 0:
        toon_house.key_line(cv, shot.front, KEY_LINE, 0.0, 2.6, measure=shot.measure)
    invoice, back, card = event(beats, "invoice"), event(beats, "back"), event(beats, "card")
    if app.start <= invoice < app.end:
        toon_odds.paper_insert(cv, shot.front, "REX'S PLUMBING", ("March. Paid.", "Signed: Rex."), invoice, back)
    if app.start <= card < app.end:
        toon_odds.paper_insert(
            cv, shot.front, "REX", ("We fix what the", "last guy did."), card, event(beats, "spray"), paper="#ffffff"
        )


def sounds(beats, end: float) -> list[Sound]:
    """The drips, the phone's shutter, the paper on the floor, the spray."""
    spray = event(beats, "spray")
    return [
        Sound("drip", DRIP, tuple(round(t * DRIP_EVERY + 0.32, 3) for t in range(int(spray / DRIP_EVERY))), -9.0),
        Sound("shutter", foley.REMOTE_CLICK, (event(beats, "shutter"),), -4.0),
        Sound("paper", foley.SWISH, (event(beats, "invoice"), event(beats, "card")), -10.0),
        Sound("spray", foley.SWISH, (spray,), -4.0),
    ]


STAGING_ARGS = dict(
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
    desk=toon_world.no_desk,
)

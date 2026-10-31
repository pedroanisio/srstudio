"""Get Your Mother — the sketch as data: Dad answers the phone only to say he will get your mother, so calling him on
purpose breaks him. Fern calls him. He asks what's wrong; nothing is. They manage the car. He gets her mother, then
goes out to the fence, the phone in his hand, to tell the neighbor.

Four voices (ElevenLabs premade Brian as Dad, Matilda as Fern, Laura as Mom, heard only, Roger as the neighbor): Dad
in the kitchen with the phone on the worktop, Fern at home, then Dad at the fence with the sloth and his hose. The
sketch opens silent on a slow push with the phone ringing (the ``sp-hook_motion`` test's arm B). ``SKETCH`` is checked
by :func:`srstudio.sketch.check`; :func:`validate` checks the events; :func:`dress` draws each shot, :func:`lens` its
camera and :func:`foley` its sound.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, scripting, sketch, toon_everyday, toon_extras, toon_house, toon_sets, toon_world
from srstudio import foley as synth
from srstudio.foley import Burst
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 3101
SLUG = "get-your-mother"
TITLE = "Get Your Mother — Dad and the Phone (Toon)"
DESCRIPTION = (
    "A Toon sketch: Dad only ever answers the phone to fetch Mom. Fern calls him on purpose. It breaks him, then it "
    "makes his week."
)
ACCESSIBILITY = (
    "An old cartoon goat in a kitchen stands over a ringing phone on the worktop. His daughter, a cartoon frog, says "
    "she called him, not her mother; he looks behind him, then asks what's wrong. They discuss the car in one word "
    "each, and sit in the silence. He hands her over. Her mother's voice says he is outside telling the neighbors. "
    "At the fence he holds the phone and beams at a sloth with a hose. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Brian (Dad), Matilda (Fern), Laura (Mom) and Roger (the neighbor)."
NOTE = "ElevenLabs premade voices Brian, Matilda, Laura and Roger at their natural pace; no reference-voice cloning."
DAD = Speaker(
    "dad",
    Voice(role="dad", id="nPczCjzI2devNBz1zQrb", name="Brian"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.25),
    "goat",
)
FERN = Speaker(
    "fern",
    Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35),
    "frog",
)
MOM = Speaker(
    "mom",
    Voice(role="mom", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"),
    VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3),
)
NEIGHBOR = Speaker(
    "neighbor",
    Voice(role="neighbor", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
    VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15),
    "sloth",
)
TINTS = {"dad": "#ecdcc4", "fern": "#d6f0c8", "mom": "#ffd9e4", "neighbor": "#d9e8ff"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
KEY_LINE = "Calling Dad on purpose."
LEAD = 0.45  # the silence before the first word, the phone ringing
PHONE = dict(at=(432, 838), scale=0.9)
HELD = dict(at=(330, 838), scale=0.9, hand="#d9d2c7")
HOSE = [(610, 792), (556, 830), (512, 770), (478, 778)]
NEIGHBOR_AT = (452, 806)
PIVOT = (980.0, 1420.0)
RING = ((1319.0, 1319.0, 0.3),)
DRIP = Burst(0.09, 900.0, attack=0.002, decay=0.25, tone_hz=1500.0, tone_end_hz=2300.0, tone=0.8)
END = 30.3

LINES = (
    Line("dad", "Hello?"),
    Line("fern", "Hi, Dad!"),
    Line("dad", "I'll get your mother."),
    Line("fern", "No, Dad, wait. I called you."),
    Line("dad", "What's wrong?"),
    Line("fern", "Nothing. I just wanted to talk."),
    Line("dad", "How's the car?"),
    Line("fern", "Good."),
    Line("dad", "Good."),
    Line("dad", "Okay. I'll get your mother."),
    Line("mom", "What did you say to him?"),
    Line("fern", "Nothing! Why?"),
    Line("mom", "He's outside telling the neighbors."),
    Line("dad", "She called me."),
    Line("neighbor", "What about?"),
    Line("dad", "Nothing."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "goat", "", "half", "flat", "sigh", "ring"),  # the held frame: the phone rings, he has reached it
    say(LEAD, "goat", 0, "half", "flat", "sigh"),
    say(1.4, "frog", 1, "half", "grin", "desk"),
    say(2.3, "goat", 2, "half", "flat", "sigh"),
    first(3.7, "frog", 3, "No, Dad, wait.", "wide", "open", "lean"),
    part(4.7, "frog", 3, 3, "I called you.", "half", "grin", "lean"),
    hold(5.8, "goat", "", "down", "none", "sigh"),  # he looks at the phone
    hold(6.8, "goat", "", "side", "none", "sigh"),  # then behind him, for whoever she means
    say(7.8, "goat", 4, "wide", "open", "lean", wear=("sweat",)),
    say(9.0, "frog", 5, "half", "grin", "desk"),
    hold(11.0, "goat", "", "wide", "none", "lean", "drip", wear=("sweat",)),
    hold(12.0, "goat", "", "side", "flat", "lean", "drip", wear=("sweat",)),
    say(13.1, "goat", 6, "half", "open", "desk"),
    say(14.2, "frog", 7, "half", "flat", "desk"),
    say(15.0, "goat", 8, "half", "flat", "desk"),
    hold(15.7, "frog", "", "side", "flat", "desk"),  # both of them sit in it, cut between the faces once
    hold(16.9, "goat", "", "side", "flat", "desk", "drip"),
    say(18.2, "goat", 9, "half", "flat", "sigh"),
    say(20.2, "frog", 10, "half", "flat", "desk"),
    say(21.7, "frog", 11, "wide", "open", "lean"),
    say(22.9, "frog", 12, "wide", "flat", "lean"),
    say(25.1, "goat", 13, "half", "grin", "desk", "fence"),
    say(26.4, "goat", 14, "half", "grin", "desk"),
    hold(27.4, "goat", "", "half", "grin", "desk"),
    say(28.6, "goat", 15, "half", "grin", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (DAD, FERN, MOM, NEIGHBOR), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent; it opens silent with the phone ringing, speaks by 0.5 s; the fence comes
    once, after every line on the phone; the drip falls only in the silences; no other events."""
    sketch.check(sk)
    if sk.beats[0].spoken or sk.beats[0].caption or sk.beats[1].start > 0.5:
        raise sketch.SketchError("the sketch opens silent and speaks by 0.5 s")
    scripting.exactly_once(sk.beats, "ring", "the phone rings once")
    scripting.exactly_once(sk.beats, "fence", "Dad goes to the fence once")
    fence = sketch.events(sk.beats, "fence")[0][0]
    if any(b.spoken and b.start < fence and b.line is not None and b.line > 12 for b in sk.beats):
        raise sketch.SketchError("the fence comes before its lines")
    if any(b.line == 12 and b.start >= fence for b in sk.beats):
        raise sketch.SketchError("the fence comes after Mom's last line")
    scripting.only_events(sk.beats, {"ring", "fence", "drip"})


def dress(shot) -> None:
    """Dad's kitchen with the phone on the worktop, Fern at home with hers, and the fence: Dad holding the phone, the
    sloth behind his hose."""
    cv, app = shot.cv, shot.app
    fence = sketch.events(shot.beats, "fence")[0][0]
    if app.who == "frog":
        toon_sets.home(cv, shot.back, shot.end)
        toon_house.ledge(cv, shot.front, "oak")
    elif app.start >= fence:
        toon_world.yard(cv, shot.back, sign=None, table=False)
        talk = [b for b in shot.beats if b.line == 14][0].start
        poses = ((0.0, "half", "flat", "desk"), (talk, "half", "flat", "desk"), (talk + 1.2, "sleepy", "flat", "desk"))
        toon_extras.figure(shot, shot.back, "sloth", NEIGHBOR_AT, 0.84, poses, mirror=True)
        toon_house.rope(cv, shot.back, HOSE, colour="#3f8d5a")
        toon_house.ledge(cv, shot.front, "white")
        toon_everyday.phone(
            cv,
            shot.front,
            [toon_everyday.Screen(0.0, "notify", "Fern", "Call ended", "7:13")],
            measure=shot.measure,
            id=cv.uid("phone"),
            **HELD,
        )
    else:
        toon_sets.kitchen(cv, shot.back)
        toon_house.ledge(cv, shot.front, "oak")
        screen = toon_everyday.Screen(0.0, "notify", "Fern", "Calling", "7:12")
        toon_everyday.phone(cv, shot.front, [screen], measure=shot.measure, id=cv.uid("phone"), **PHONE)
        if app.start == 0.0:
            toon_house.key_line(cv, shot.front, KEY_LINE, 0.0, 3.5, measure=shot.measure)


def lens(shot, setup) -> None:
    """A slow push from the first frame, then a slow push onto Dad's face at the fence for his last word."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.start == 0.0:
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (shot.app.end, 1.05)])
    if shot.app.start >= sketch.events(shot.beats, "fence")[0][0]:
        last = [b for b in shot.beats if b.line == 15][0].start
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (last - 1.2, 1.0), (last + 1.0, 1.12)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The phone's ring from the first frame and the tap's drip in the silences."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    ring = synth.write_tones(audio / "ring.wav", [0.0, 0.42], end, RING)
    drip = synth.write_bursts(audio / "drip.wav", [at for at, _ in sketch.events(beats, "drip")], end, DRIP, seed=seed)
    return [sketch.effect("ring", 0.0, -12.0, root, ring), sketch.effect("drip", 0.0, -9.0, root, drip)]

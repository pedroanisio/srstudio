"""Since I Was Six — the sketch as data: every job makes you claim a lifelong passion for a company that sells grout,
and one day the man across the desk needs it to be true.

Two voices (ElevenLabs premade Charlie as Rex, Matilda as Fern). One interview room: the two-shot across the desk, held
still until the first line (the reel opens STILL), then Rex alone, then Fern with Rex behind her closing up the room
(``blind``), then the two of them cut close, and the two-shot again for the tissue box (``slide``). :func:`validate`
checks the events; :func:`dress` draws each shot, :func:`lens` its camera, :func:`sounds` its foley and :func:`tear` the
tear on Rex's face.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    camera,
    foley,
    scripting,
    sketch,
    toon,
    toon_cast,
    toon_house,
    toon_interview,
    toon_pair,
    toon_parlour,
    toon_redrawn,
)
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3309
SLUG = "since-i-was-six"
TITLE = "Since I Was Six — Rex and the Grout (Toon)"
DESCRIPTION = "A Toon sketch: she says she has loved grout since she was six, and the man across the desk needs it."
ACCESSIBILITY = (
    "A cartoon dog interviews a cartoon frog under a sign that reads Dunmore Grout Supply. She says she has loved "
    "grout since she was six. He gets up, closes the door, lowers the blind and sits down, and begs her to tell him "
    "why. She picks up a sample and makes it up: it goes between the tiles, it keeps them apart, and together. A tear "
    "runs down his face. That's my marriage, he says. She slides a box of tissues across the desk with one finger. "
    "Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Charlie (Rex) and Matilda (Fern); synthesized door, blind and box."
NOTE = "ElevenLabs premade voices Charlie and Matilda at their natural pace; no reference-voice cloning."
REX = Speaker(
    "rex",
    Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.2),
    "dog",
)
FERN = Speaker(
    "fern",
    Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3),
    "frog",
)
TINTS = {"rex": "#f6dcb8", "fern": "#d6f0c8"}
BARE = ("hamster", "sloth")  # the two-shot; its opening, heads stone still, long enough to read the sign
HEADS = ("dog", "frog")
FIGURES = {"dog": (1.1, 16.0), "frog": (1.0, 0.0)}
PIVOT = (980.0, 1420.0)
FERN_SEAT, REX_SEAT = (108.0, 856.0), (356.0, 852.0)  # the two-shot
TWO_SCALE = 0.9
TRAY_AT, TISSUES_AT, PAPER_AT = (462.0, 838.0), (92.0, 838.0), (340.0, 832.0)
FROG_COAT, FROG_HAND = toon_redrawn.FROG.coat, toon_cast.FROG.coat
STILL = 0.45  # the opening's stone-still seconds
SLIDE = 2.6  # the seconds the box takes to cross the desk
SLIDE_TO = 165.0  # how far it goes, reference pixels
DIM = 0.14  # how far the blind darkens the room
WALK_FROM, WALK_AT, WALK_Y = 760.0, 452.0, 838.0
END = 31.0

LINES = (
    Line("rex", "Why do you want to work at Dunmore Grout?"),
    Line("fern", "Honestly? Passion. Since I was six."),
    Line("rex", "For grout."),
    Line("fern", "For grout."),
    Line("rex", "Thirty years I've been here. Tell me why.", gain=-3.0),
    Line("fern", "Sorry?"),
    Line("rex", "Why grout? Please.", gain=-3.0),
    Line("fern", "It goes between the tiles."),
    Line("rex", "Go on.", gain=-3.0),
    Line("fern", "It keeps them apart."),
    Line("rex", "And?", gain=-3.0),
    Line("fern", "And together?"),
    Line("rex", "That's my marriage.", gain=-3.0),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "sloth", "", "half", "none", "desk"),
    first(STILL, "sloth", 0, "Why do you want to work", "half", "flat", "desk"),
    part(1.6, "hamster", 0, 6, "at Dunmore Grout?", "half", "flat", "desk"),
    first(3.0, "hamster", 1, "Honestly? Passion.", "wide", "grin", "desk"),
    part(4.2, "hamster", 1, 2, "Since I was six.", "wide", "grin", "desk"),
    say(5.5, "hamster", 2, "half", "flat", "desk"),
    say(6.4, "hamster", 3, "wide", "grin", "desk"),
    hold(7.4, "dog", "", "half", "flat", "desk"),  # a second and a half: he looks at her
    hold(8.9, "frog", "", "side", "grin", "desk", "up"),  # he has got up: the door, behind her eyes
    hold(9.8, "frog", "", "side", "flat", "desk", "blind"),  # the blind comes down
    hold(10.9, "frog", "", "left", "flat", "desk"),
    hold(11.4, "dog", "", "wide", "flat", "desk"),  # he sits
    first(11.9, "dog", 4, "Thirty years I've been here.", "half", "flat", "desk"),
    part(13.4, "dog", 4, 5, "Tell me why.", "wide", "frown", "desk"),
    say(14.6, "frog", 5, "wide", "flat", "desk"),
    say(15.3, "dog", 6, "wide", "frown", "desk"),
    hold(16.8, "frog", "", "down", "flat", "desk", "pick"),  # she looks at the tray
    say(17.7, "frog", 7, "half", "flat", "desk"),
    say(19.2, "dog", 8, "wide", "flat", "desk"),
    say(20.0, "frog", 9, "half", "flat", "desk"),
    say(21.3, "dog", 10, "wide", "frown", "desk"),
    say(22.0, "frog", 11, "up", "flat", "desk"),
    hold(23.0, "dog", "", "wide", "frown", "desk", "tear"),  # two seconds: it reaches his chin
    say(25.1, "dog", 12, "teary", "frown", "desk"),
    hold(26.6, "hamster", "", "teary", "none", "desk", "slide"),  # the box crosses the desk
)
SKETCH = Sketch(SLUG, TITLE, (REX, FERN), LINES, BEATS, END, tail=2.8, bare=BARE)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, holds still to the first line by 0.5 s, and every event comes once, in order."""
    sketch.check(sk)
    spoken = next(b for b in sk.beats if b.spoken)
    if spoken.start > 0.5 or spoken is sk.beats[0]:
        raise sketch.SketchError("it opens on a held frame, the first line by 0.5 s")
    order = ("up", "blind", "pick", "tear", "slide")
    for kind in order:
        scripting.exactly_once(sk.beats, kind, f"{kind} happens once")
    at = [sketch.events(sk.beats, kind)[0][0] for kind in order]
    if at != sorted(at):
        raise sketch.SketchError(f"the events run in the order {order}")
    scripting.only_events(sk.beats, set(order))


def at(shot, kind: str) -> float:
    return sketch.events(shot.beats, kind)[0][0]


def _room(shot) -> None:
    """The room: its sign, its window and its blind, the same on every shot; dim once the blind is down."""
    cv = shot.cv
    toon.room(cv, shot.back)
    toon_interview.wall_sign(cv, shot.back)
    t = at(shot, "blind")
    toon_interview.blind(cv, shot.back, drop=(t, t + BLIND_FALL))
    dim = cv.group(shot.back, cv.uid("g"), start=t + BLIND_FALL)
    cv.rect(dim, 0, 0, cv.width, cv.height, "#1b1430", opacity=DIM)


BLIND_FALL = 0.7


def _acts(shot, who: str, speaker: str, listen: Act) -> list[Act]:
    """One act per beat for a character of a two-shot: its own lines as written, its listening between them, and the
    state the last shot leaves it in."""
    out = []
    late = at(shot, "tear")
    names = {line.speaker for line in LINES}
    assert speaker in names
    for b in shot.beats:
        if b.line is not None and LINES[b.line].speaker == speaker:
            out.append(Act(b.eyes, b.mouth, b.arms))
        elif b.start >= late:
            out.append(Act("teary", "frown", "desk") if who == "dog" else Act("half", "flat", "desk"))
        else:
            out.append(listen)
    return out


def _two_shot(shot) -> None:
    """The desk with both of them behind it; the tissues at her elbow, crossing to him on ``slide``."""
    cv, app = shot.cv, shot.app
    _room(shot)
    moving = app.who != "sloth"
    frog = _acts(shot, "frog", "fern", Act("side", "grin", "desk"))
    dog = _acts(shot, "dog", "rex", Act("left", "flat", "desk"))
    toon_pair.figure(shot, shot.back, "frog", FERN_SEAT, frog, scale=TWO_SCALE, moving=moving)
    toon_pair.figure(shot, shot.back, "dog", REX_SEAT, dog, scale=TWO_SCALE, moving=moving)
    toon_house.ledge(cv, shot.front, "oak")
    toon_interview.paper(cv, shot.front, PAPER_AT, 0.9)
    toon_interview.sample_tray(cv, shot.front, TRAY_AT, missing=(1, 0.0) if app.start > at(shot, "pick") else None)
    slider = cv.group(shot.front, cv.uid("g"))
    toon_interview.tissue_box(cv, slider, TISSUES_AT, 0.9)
    if app.start >= at(shot, "slide"):
        t = at(shot, "slide") + 0.5
        cv.keys(slider, "x", [(t, 0.0), (t + SLIDE, toon.fh(SLIDE_TO))], hold=False, local=False)
        tip = (TISSUES_AT[0] - 47.0, 806.0)
        hand = cv.group(slider, cv.uid("g"), anchorX=toon.fx(tip[0]), anchorY=toon.fy(tip[1]), x=toon.fx(tip[0]),
                        y=toon.fy(tip[1]), scaleX=0.5, scaleY=0.5)  # fmt: skip
        toon_house.finger(cv, hand, tip, 90.0, FROG_COAT, FROG_COAT, id=cv.uid("g"))


def _walk(shot) -> None:
    """Rex behind her, in from the door at the right, to the window and its cord, and out again."""
    cv, app = shot.cv, shot.app
    up, down = at(shot, "up"), at(shot, "blind")
    n = len(shot.beats)
    g = toon_pair.figure(shot, shot.back, "dog", (WALK_AT, WALK_Y), [Act("half", "flat", "desk")] * n, scale=0.84,
                         moving=False)  # fmt: skip
    near, gone = toon.fx(WALK_AT), toon.fx(WALK_FROM)
    leave = down + BLIND_FALL + 0.1
    cv.keys(g, "x", [(up + 0.1, gone), (down - 0.05, near), (leave, near), (app.end, gone)], hold=False, local=False)
    bob, t, keys = toon.fy(WALK_Y), up + 0.1, []
    while t < down:
        keys += [(round(t, 3), bob), (round(t + 0.13, 3), bob - 10.0)]
        t += 0.26
    keys += [(round(down, 3), bob), (round(leave, 3), bob)]
    t = leave
    while t < app.end:
        keys += [(round(t, 3), bob), (round(t + 0.13, 3), bob - 10.0)]
        t += 0.26
    cv.keys(g, "y", keys, hold=False, local=False)


def dress(shot) -> None:
    """The two-shot, or one of them close, the tray before her, and Rex at the blind behind her."""
    cv, app = shot.cv, shot.app
    if app.who in BARE:
        _two_shot(shot)
        return
    _room(shot)
    if app.who == "frog":
        if app.start <= at(shot, "blind") < app.end:
            _walk(shot)
        pick = at(shot, "pick")
        if app.end > pick:
            a = max(app.start, pick + 0.3)
            arm = toon_parlour.held(
                cv, shot.front, (), (262.0, 784.0), (352.0, 668.0), FROG_COAT, FROG_HAND, a, app.end
            )
            cv.rect(arm, toon.fx(342.0), toon.fy(620.0), toon.fh(24.0), toon.fh(50.0), toon_interview.GROUTS[1], cv.ink,
                    toon.FINE_W * 0.6, radius=toon.fh(3.0))  # fmt: skip
    toon_house.ledge(cv, shot.front, "oak")
    if app.who == "frog" and app.start > at(shot, "blind"):
        toon_interview.sample_tray(cv, shot.front, (420.0, 838.0), missing=(1, at(shot, "pick") + 0.3))


def tear(cv, app, beats, face) -> None:
    """One tear, from under his eye to his chin, over the ``tear`` hold."""
    t = sketch.events(beats, "tear")[0][0]
    if not app.start <= t < app.end:
        return
    g = cv.group(face, cv.uid("g"), start=t + 0.2)
    cv.keys(g, "y", [(t + 0.2, 0.0), (t + 1.9, toon.fh(TEAR_RUN))], hold=False, local=False, kind="sine-in")
    cv.keys(g, "x", [(t + 0.2, 0.0), (t + 1.9, toon.fh(TEAR_DRIFT))], hold=False, local=False)
    x, y = TEAR_AT
    cv.path(g, toon._d("M", (x, y - 16), "C", (x - 12, y + 2), (x - 6, y + 12), (x, y + 12), "C", (x + 6, y + 12),
                       (x + 12, y + 2), (x, y - 16), "Z"), fill="#8fd0f5", stroke=cv.ink, sw=2.5)  # fmt: skip


TEAR_AT, TEAR_RUN, TEAR_DRIFT = (140.0, 566.0), 84.0, 30.0


def lens(shot, setup) -> None:
    """Held, but for one slow push on him through his first hold and one through the tear."""
    camera.anchor(setup, *PIVOT, place=True)
    a = shot.app.start
    if shot.app.who == "dog" and a <= at(shot, "tear") < shot.app.end:
        t = at(shot, "tear")
        camera.push_in(shot.cv, setup, scale=[(t, 1.0), (t + 2.0, 1.06)], hold_scale=True)


def sounds(beats, end) -> list[Sound]:
    """His chair, the door's latch, the blind's rattle and the box on the desk."""
    up = sketch.events(beats, "up")[0][0]
    blind = sketch.events(beats, "blind")[0][0]
    slide = sketch.events(beats, "slide")[0][0]
    return [
        Sound("latch", foley.KNOCK, (up + 0.1,), -10.0),
        Sound("rattle", foley.SCRAPE, tuple(round(blind + k * 0.14, 3) for k in range(5)), -14.0),
        Sound("box", foley.SCRAPE, tuple(round(slide + 0.5 + k * 0.5, 3) for k in range(5)), -20.0),
    ]

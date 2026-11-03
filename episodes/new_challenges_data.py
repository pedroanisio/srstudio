"""New Challenges — the sketch as data: everyone has a polite reason for leaving the last job, and it is never the
reason, until the woman across the desk wants the skill.

Two voices (ElevenLabs premade Jessica as Dana, Chris as Gil). One room with a smoke detector on its ceiling in every
shot, small and green. Dana close and smiling, tapping her pen until she puts it down on ``pen``; Gil close; the folder
from above (``slide``, ``open``); the two of them on the last lines, Gil's nod on ``nod``, and the light going red on
``red`` with one beep. :func:`validate` checks the events; :func:`dress` draws each shot, :func:`lens` its camera and
:func:`sounds` its foley.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    camera,
    foley,
    scripting,
    sketch,
    toon,
    toon_alarm,
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
SEED = 3321
SLUG = "new-challenges"
TITLE = "New Challenges — Dana Hires Gil (Toon)"
DESCRIPTION = "A Toon sketch: he left his last job through a window, and she is very well insured."
ACCESSIBILITY = (
    "A smiling cartoon dog taps a pen on a resume across a desk from a cartoon frog. He answers every question "
    "politely: he wanted new challenges, the fire marshal found them, he left through a window. She puts the pen down, "
    "glances at the door and asks how big the fire was. She slides a folder across the desk with a photograph of this "
    "building in it, ringed in red. We're very well insured, she says. He nods. When can you start, she asks. I "
    "already have, he says. The small light on the smoke detector over their heads turns red, and it beeps once. "
    "Neither of them looks up. Lines appear in tinted pills."
)
NARRATION = (
    "Voiced with ElevenLabs premade voices Jessica (Dana) and Chris (Gil); synthesized pen, folder and detector."
)
NOTE = "ElevenLabs premade voices Jessica and Chris at their natural pace; no reference-voice cloning."
DANA = Speaker(
    "dana",
    Voice(role="dana", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3),
    "dog",
)
GIL = Speaker(
    "gil",
    Voice(role="gil", id="iP95p4xoKVk53GoZ742B", name="Chris"),
    VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15),
    "frog",
)
TINTS = {"dana": "#f6dcb8", "gil": "#d6f0c8"}
BARE = ("hamster", "sloth")  # the two-shot, and the desk from above
HEADS = ("dog", "frog")
FIGURES = {"dog": (1.1, 16.0), "frog": (1.0, 0.0)}
PIVOT = (980.0, 1420.0)
HOOK, HOOK_END = "REASON FOR LEAVING", 4.0  # to the cut after her answer
DOG_COAT, DOG_HAND = toon_redrawn.DOG.coat, toon_cast.DOG.coat
ARM_ROOT, FIST = (262.0, 784.0), (336.0, 700.0)
GIL_SEAT, DANA_SEAT = (112.0, 856.0), (352.0, 852.0)
TWO_SCALE = 0.9
TAP = 0.46  # seconds between the pen's taps
OAK = "#b98a55"
FOLDER_AT = (306.0, 440.0)
END = 28.9

LINES = (
    Line("dana", "Why did you leave your last job?"),
    Line("gil", "I wanted new challenges."),
    Line("dana", "And did you find them?"),
    Line("gil", "The fire marshal did."),
    Line("dana", "It says you left on good terms."),
    Line("gil", "I left through a window."),
    Line("dana", "Would your old boss give a reference?"),
    Line("gil", "When he's allowed visitors."),
    Line("dana", "How big was the fire?", gain=-3.0),
    Line("gil", "Sorry?"),
    Line("dana", "We're very well insured.", gain=-2.0),
    Line("dana", "When can you start?"),
    Line("gil", "I already have."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "dog", "", "wide", "grin", "desk"),
    say(0.25, "dog", 0, "wide", "grin", "desk"),
    say(2.3, "frog", 1, "half", "flat", "desk"),
    say(4.0, "dog", 2, "wide", "grin", "desk"),
    say(5.4, "frog", 3, "half", "flat", "desk"),
    hold(6.9, "dog", "", "wide", "grin", "desk"),  # 1.2 s: the smile does not move
    say(8.1, "dog", 4, "wide", "grin", "desk"),
    say(10.0, "frog", 5, "half", "flat", "desk"),
    first(11.6, "dog", 6, "Would your old boss", "wide", "grin", "desk"),
    part(12.6, "dog", 6, 4, "give a reference?", "wide", "grin", "desk"),
    say(13.8, "frog", 7, "half", "flat", "desk"),
    hold(15.4, "dog", "", "half", "grin", "desk", "pen"),  # 2 s: down goes the pen
    hold(16.0, "dog", "", "side", "grin", "desk"),  # the door
    hold(16.8, "dog", "", "wide", "grin", "desk", "lean"),
    say(17.4, "dog", 8, "wide", "grin", "desk"),
    say(18.9, "frog", 9, "wide", "flat", "desk"),
    hold(19.7, "sloth", "", "half", "none", "desk", "slide"),
    hold(20.7, "sloth", "", "half", "none", "desk", "open"),
    say(21.5, "sloth", 10, "half", "grin", "desk"),
    hold(23.2, "hamster", "", "down", "flat", "desk", "nod"),  # 1.5 s: he reads, and nods, a professional
    say(24.7, "hamster", 11, "wide", "grin", "desk"),
    say(26.0, "hamster", 12, "half", "flat", "desk"),
    hold(27.2, "hamster", "", "half", "none", "desk", "red"),
)
SKETCH = Sketch(SLUG, TITLE, (DANA, GIL), LINES, BEATS, END, tail=1.6, bare=BARE)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, and every event comes once and in the story's order."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    order = ("pen", "lean", "slide", "open", "nod", "red")
    for kind in order:
        scripting.exactly_once(sk.beats, kind, f"{kind} happens once")
    at = [sketch.events(sk.beats, kind)[0][0] for kind in order]
    if at != sorted(at):
        raise sketch.SketchError(f"the events run in the order {order}")
    scripting.only_events(sk.beats, set(order))


def at(shot, kind: str) -> float:
    return sketch.events(shot.beats, kind)[0][0]


def taps(beats) -> list[float]:
    """The pen's taps: through her first question, and through the hold after the fire marshal."""
    second_dog = next(b.start for b in beats if b.line == 1)
    out, t = [], 0.2
    while t < second_dog - 0.2:
        out.append(round(t, 3))
        t += TAP
    held = next(k for k, b in enumerate(beats) if b.line == 3) + 1
    t, stop = beats[held].start + 0.1, beats[held + 1].start - 0.1
    while t < stop:
        out.append(round(t, 3))
        t += TAP
    return out


def _room(shot) -> None:
    """The room with its detector, in every shot, green until ``red``."""
    toon.room(shot.cv, shot.back)
    toon_alarm.smoke_detector(shot.cv, shot.back, red=at(shot, "red"), scale=1.3)


def _pen_arm(shot) -> None:
    """Her arm and pen: on every shot of hers until the pen goes down, the arm swung down behind the desk."""
    cv, app = shot.cv, shot.app
    down = at(shot, "pen")
    if app.start >= down + 0.5:
        return
    keys: list[tuple[float, float]] = [(app.start, 0.0)]
    for t in taps(shot.beats):
        if app.start < t < app.end - 0.2 and t < down:
            keys += [(t - 0.07, 0.0), (t - 0.02, -5.0), (t + 0.05, 0.0)]
    if app.start <= down < app.end:
        keys += [(down, 0.0), (down + 0.4, 48.0)]
    end = min(app.end, down + 0.45)
    arm = toon_parlour.held(cv, shot.front, (), ARM_ROOT, FIST, DOG_COAT, DOG_HAND, app.start, end, swings=keys)
    x, y = toon.fx(FIST[0]), toon.fy(FIST[1])
    cv.rect(arm, x - 7, y - 50, 16, 160, "#2f4b8f", cv.ink, toon.FINE_W * 0.7, radius=6)
    cv.rect(arm, x - 7, y + 110, 16, 18, "#d9d4c5", cv.ink, toon.FINE_W * 0.7, radius=3)


def _hook(shot) -> None:
    cv, app = shot.cv, shot.app
    if app.start < HOOK_END:
        toon_house.key_line(cv, shot.front, HOOK, app.start, min(app.end, HOOK_END), measure=shot.measure)


def _acts(shot, who: str, speaker: str, listen: Act) -> list[Act]:
    out = []
    for b in shot.beats:
        if b.line is not None and LINES[b.line].speaker == speaker:
            out.append(Act(b.eyes, b.mouth, b.arms))
        elif who == "frog" and b.event == "nod":
            out.append(Act("down", "flat", "desk"))
        else:
            out.append(listen)
    return out


def _two_shot(shot) -> None:
    """The two of them; the folder between them, open; Gil nods on ``nod``."""
    cv = shot.cv
    _room(shot)
    frog = _acts(shot, "frog", "gil", Act("half", "flat", "desk"))
    dog = _acts(shot, "dog", "dana", Act("wide", "grin", "desk"))
    g = toon_pair.figure(shot, shot.back, "frog", GIL_SEAT, frog, scale=TWO_SCALE)
    toon_pair.figure(shot, shot.back, "dog", DANA_SEAT, dog, scale=TWO_SCALE)
    t, y = at(shot, "nod") + 0.3, toon.fy(GIL_SEAT[1])
    cv.keys(g, "y", [(t + k * 0.2, y + (14.0 if k % 2 else 0.0)) for k in range(5)], hold=False, local=False)
    toon_house.ledge(cv, shot.front, "oak")
    toon_interview.paper(cv, shot.front, (250.0, 832.0), 0.9)


def _insert(shot) -> None:
    """The desk from above: the folder slides in under her finger and opens on the photograph."""
    cv = shot.cv
    cv.rect(shot.back, 0, 0, cv.width, cv.height, OAK)
    t, o = at(shot, "slide"), at(shot, "open")
    slider = cv.group(shot.front, cv.uid("g"))
    toon_alarm.folder(cv, slider, FOLDER_AT, opened=o)
    cv.keys(slider, "x", [(t, cv.width * 0.9), (t + 0.7, 0.0)], hold=False, local=False, kind="cubic-out")
    hand = cv.group(shot.front, cv.uid("g"))
    tip = (534.0, 470.0)
    toon_house.finger(cv, hand, tip, -90.0, DOG_HAND, DOG_COAT, id=cv.uid("g"))
    away = [(t, cv.width * 0.9), (t + 0.7, 0.0), (o + 0.2, 0.0), (o + 0.6, cv.width * 0.9)]
    cv.keys(hand, "x", away, hold=False, local=False, kind="cubic-out")
    toon_house.ledge(cv, shot.front, "oak")


def dress(shot) -> None:
    """One of them close, the two of them, or the folder from above; the detector on the ceiling of each."""
    cv, app = shot.cv, shot.app
    if app.who == "sloth":
        _insert(shot)
        return
    if app.who == "hamster":
        _two_shot(shot)
        return
    _room(shot)
    if app.who == "dog":
        _pen_arm(shot)
    toon_house.ledge(cv, shot.front, "oak")
    if app.who == "dog":
        toon_interview.paper(cv, shot.front, (336.0, 832.0), 1.1)
    _hook(shot)


def lens(shot, setup) -> None:
    """Held, but for her leaning in on ``lean``."""
    camera.anchor(setup, *PIVOT, place=True)
    t = at(shot, "lean")
    if shot.app.start <= t < shot.app.end:
        camera.push_in(shot.cv, setup, scale=[(t, 1.0), (t + 0.5, 1.1)], hold_scale=True)


def sounds(beats, end) -> list[Sound]:
    """Her pen on the desk, the pen put down, the folder on the wood, and one beep."""
    pen = sketch.events(beats, "pen")[0][0]
    slide = sketch.events(beats, "slide")[0][0]
    red = sketch.events(beats, "red")[0][0]
    return [
        Sound("tap", foley.REMOTE_CLICK, tuple(taps(beats)), -20.0),
        Sound("down", foley.KNOCK, (round(pen + 0.3, 3),), -14.0),
        Sound("folder", foley.SCRAPE, (round(slide + 0.1, 3), round(slide + 0.35, 3)), -16.0),
        Sound("beep", foley.CHIRP, (round(red + 0.05, 3),), -12.0),
    ]

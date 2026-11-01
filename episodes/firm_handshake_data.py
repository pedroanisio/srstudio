"""Firm Handshake — the sketch as data: a father still believes you get a job by putting on a tie and asking for the
manager. He goes to prove it, and comes back with a lanyard while the portal rejects his daughter.

Two voices (ElevenLabs premade Brian as Dad, Matilda as Fern). One kitchen and the front door seen from inside: Dad at
the front with the tie held up, then on his chest (``wear``); Fern at her laptop, its lid shutting on ``shut``; the door
slamming on ``out`` and opening on ``back``; the portal's answer as a notice on ``ping``, never a voice. The camera
moves
from the first frame. :func:`validate` checks the events; :func:`dress` draws each shot, :func:`lens` its camera and
:func:`sounds` its foley.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    camera,
    foley,
    scripting,
    sketch,
    toon_critters,
    toon_house,
    toon_pair,
    toon_parlour,
    toon_screens,
    toon_sets,
    toon_tie,
)
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3301
SLUG = "firm-handshake"
TITLE = "Firm Handshake — Dad and the Tie (Toon)"
DESCRIPTION = "A Toon sketch: Dad says just put on a tie and ask for the manager, so he goes and does it."
ACCESSIBILITY = (
    "An old cartoon goat in a kitchen holds up a striped tie while his daughter, a frog, types at a laptop. She tells "
    "him it is all online. He puts the tie on and leaves by the front door. A card comes up: application 213, "
    "rejected. She does not look up. He comes back with a company lanyard over the tie. He is the regional manager. "
    "She shuts the laptop and asks in a small voice if they need anyone else. He pats her shoulder and tells her there is a portal. "
    "Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Brian (Dad) and Matilda (Fern); synthesized door, ping and lid."
NOTE = "ElevenLabs premade voices Brian and Matilda at their natural pace; no reference-voice cloning."
DAD = Speaker(
    "dad",
    Voice(role="dad", id="nPczCjzI2devNBz1zQrb", name="Brian"),
    VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15),
    "goat",
)
FERN = Speaker(
    "fern",
    Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3),
    "frog",
)
TINTS = {"dad": "#ecdcc4", "fern": "#d6f0c8"}
BARE = ("hamster",)  # the door, and the last two-shot
HEADS = ("goat", "frog")
FIGURES = {"goat": (1.06, -6.0)}
PIVOT = (980.0, 1420.0)
GOAT_COAT, GOAT_HOOF = toon_critters.GOAT.coat, toon_critters.GOAT_HOOF
ARM_ROOT, FIST = (262.0, 784.0), (428.0, 560.0)
WORN_KNOT, WORN_SCALE = (178.0, 690.0), 0.9
CARD_AT, LANYARD_NECK = (176.0, 728.0), ((128.0, 674.0), (224.0, 674.0))
PAT_ROOT, PAT_HOOF = (212.0, 790.0), (296.0, 692.0)
HOOK = "APPLICATION 212"
END = 28.9

LINES = (
    Line("dad", "In my day, you put on a tie and ask for the manager."),
    Line("fern", "Dad, it's all online."),
    Line("dad", "Firm handshake. Look him in the eye."),
    Line("fern", "There's a portal. There is no him."),
    Line("dad", "Watch and learn."),
    Line("fern", "What happened?"),
    Line("dad", "Regional manager."),
    Line("fern", "You're seventy-four!"),
    Line("dad", "Firm handshake."),
    Line("fern", "Do they need anyone else?", gain=-5.0),
    Line("dad", "There's a portal."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "goat", "", "half", "flat", "desk"),
    first(0.2, "goat", 0, "In my day, you put on a tie", "half", "flat", "desk"),
    part(1.9, "goat", 0, 8, "and ask for the manager.", "narrow", "smirk", "desk"),
    say(3.5, "frog", 1, "half", "flat", "type"),
    first(4.9, "goat", 2, "Firm handshake.", "narrow", "flat", "desk"),
    part(6.0, "goat", 2, 2, "Look him in the eye.", "wide", "flat", "desk"),
    first(7.4, "frog", 3, "There's a portal.", "half", "flat", "type"),
    part(8.5, "frog", 3, 3, "There is no him.", "narrow", "flat", "desk"),
    hold(9.7, "goat", "", "side", "none", "desk"),  # looks at the laptop
    hold(10.3, "goat", "", "down", "none", "desk"),  # looks at the tie
    hold(10.9, "goat", "", "narrow", "flat", "desk", "wear"),  # puts it on
    say(11.5, "goat", 4, "narrow", "smirk", "desk"),
    hold(12.9, "hamster", "", "half", "none", "desk", "out"),  # the door shuts
    hold(13.9, "frog", "", "down", "none", "type"),
    hold(14.9, "frog", "", "down", "none", "type", "ping"),  # she does not look up
    hold(16.4, "hamster", "", "half", "none", "desk", "back"),  # the door opens
    hold(17.1, "goat", "", "half", "grin", "desk"),
    say(17.7, "frog", 5, "wide", "flat", "desk"),
    say(18.8, "goat", 6, "half", "smirk", "desk"),
    say(20.2, "frog", 7, "shock", "open", "desk"),
    say(21.6, "goat", 8, "narrow", "smirk", "desk"),
    hold(22.8, "frog", "", "half", "none", "desk"),  # a second and a half
    hold(23.9, "frog", "", "down", "none", "desk", "shut"),
    say(24.7, "frog", 9, "down", "frown", "desk"),
    hold(26.3, "hamster", "", "half", "none", "desk", "pat"),  # the two-shot: his hoof on her shoulder
    say(27.1, "hamster", 10, "half", "none", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (DAD, FERN), LINES, BEATS, END, tail=1.0)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, and every event comes once and in the story's order."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    order = ("wear", "out", "ping", "back", "shut", "pat")
    for kind in order:
        scripting.exactly_once(sk.beats, kind, f"{kind} happens once")
    at = [sketch.events(sk.beats, kind)[0][0] for kind in order]
    if at != sorted(at):
        raise sketch.SketchError(f"the events run in the order {order}")
    scripting.only_events(sk.beats, set(order))


def at(shot, kind: str) -> float:
    return sketch.events(shot.beats, kind)[0][0]


def _door(shot) -> None:
    """The front door from inside: open with him gone through it, then shut; or shut, then open."""
    cv, app = shot.cv, shot.app
    if app.start < at(shot, "ping"):
        cut = app.start + 0.35
        before, after = "open", "shut"
    else:
        cut = app.start + 0.3
        before, after = "shut", "open"
    toon_house.hallway(cv, cv.group(shot.back, cv.uid("g"), start=app.start, end=cut), before)
    toon_house.hallway(cv, cv.group(shot.back, cv.uid("g"), start=cut, end=app.end), after)
    toon_house.ledge(cv, shot.front, "oak")


ACT_DAD = Act("half", "smirk", "desk")
ACT_FERN = Act("down", "flat", "desk")


def _pat(shot) -> None:
    """The last shot: Fern at the shut laptop, Dad over her, his hoof coming down on her shoulder."""
    cv, app = shot.cv, shot.app
    toon_sets.kitchen(cv, shot.back)
    n = len(shot.beats)
    toon_pair.figure(shot, shot.back, "goat", (130.0, 836.0), [ACT_DAD] * n, scale=0.9)
    toon_pair.figure(shot, shot.back, "frog", (372.0, 856.0), [ACT_FERN] * n, scale=0.92)
    pat = at(shot, "pat")
    swings = ((pat, -28.0), (pat + 0.35, 0.0))
    toon_parlour.held(cv, shot.front, (), PAT_ROOT, PAT_HOOF, GOAT_COAT, GOAT_HOOF, app.start, app.end, 0.9, swings)
    toon_house.ledge(cv, shot.front, "oak")


def dress(shot) -> None:
    """The kitchen; Dad's tie, held up, then worn, then under the lanyard; Fern's laptop and the portal's answer."""
    cv, app = shot.cv, shot.app
    if app.who == "hamster":
        _door(shot) if app.start < at(shot, "pat") else _pat(shot)
        return
    toon_sets.kitchen(cv, shot.back)
    if app.who == "goat":
        wear = at(shot, "wear")
        if app.start < wear:
            until = min(app.end, wear + 0.2)
            arm = toon_parlour.held(cv, shot.front, (), ARM_ROOT, FIST, GOAT_COAT, GOAT_HOOF, app.start, until)
            toon_tie.necktie(cv, arm, (FIST[0], FIST[1] + 18.0), 0.8, swinging=(app.start, until))
        if app.end > wear:
            a = max(app.start, wear + 0.2)
            toon_tie.necktie(cv, shot.front, WORN_KNOT, WORN_SCALE, 150.0, start=a, end=app.end)
        if app.start >= at(shot, "back"):
            toon_tie.lanyard(cv, shot.front, CARD_AT, 0.72, LANYARD_NECK)
    else:
        toon_screens.lid(cv, shot.front, shut=at(shot, "shut") if app.end > at(shot, "shut") else None)
    toon_house.ledge(cv, shot.front, "oak")
    ping = at(shot, "ping")
    if app.who == "frog" and app.start <= ping < app.end:
        toon_screens.notice(cv, shot.front, "APPLICATION 213", "REJECTED", ping, app.end)
    if app.start == 0.0:
        toon_house.key_line(cv, shot.front, HOOK, 0.0, app.end, measure=shot.measure)


def lens(shot, setup) -> None:
    """A slow push from the first frame, and on the last line."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.start == 0.0:
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (shot.app.end, 1.05)])


def sounds(beats, end) -> list[Sound]:
    """The door, the portal's ping, the lid and the hoof."""
    return [
        Sound("slam", foley.SLAM, tuple(t + 0.3 for t, _ in sketch.events(beats, "out")), -6.0),
        Sound("ping", foley.BELL, tuple(t for t, _ in sketch.events(beats, "ping")), -12.0),
        Sound("latch", foley.KNOCK, tuple(t + 0.2 for t, _ in sketch.events(beats, "back")), -10.0),
        Sound("lid", foley.THUD, tuple(t + 0.2 for t, _ in sketch.events(beats, "shut")), -8.0),
        Sound("pat", foley.KNOCK, tuple(t + 0.15 for t, _ in sketch.events(beats, "pat")), -14.0),
    ]

"""My Machine — the sketch as data: the site is down and everyone is waiting. Rex: works on my machine. Have they
tried his machine? Great idea, says Mia: she is shipping it to them. A courier is two minutes away. Rex fixes it at
once. What was it? No idea; cancel the courier. Too late: the courier is at his door.

Two voices (ElevenLabs premade River as Mia, Charlie as Rex), one shot per speaker: Mia at her desk in the office,
the chip under the captions counting the calls waiting, higher every time we see her until the fix, then none; Rex
at his desk in his home office at night. The sketch opens moving (the ``sp-hook_motion`` test's arm B): Mia talking
from the first frame while the camera pushes in on her. The courier's notices arrive as toasts (``toast:`` events)
on Rex's screen, the fix comes on ``fixed``, and the sting plays on ``hangup`` with a crash zoom onto him. ``SKETCH``
is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props;
:func:`dress` draws each shot's set and props and :func:`push` its camera (``toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

from srstudio import camera, scripting, sketch, toon, toon_props, toon_sets
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import BADGE_SIZE
from srstudio.voice import Voice, VoiceSettings

SEED = 1306
SLUG = "my-machine"
TITLE = "My Machine — Mia and Rex (Toon)"
DESCRIPTION = (
    "A Toon sketch over a site outage: it works on Rex's machine, so Mia is shipping his machine to the customers "
    "waiting. He fixes it at once. The courier comes anyway."
)
ACCESSIBILITY = (
    "A cartoon rabbit at her office desk under a dark chip that reads calls waiting, 1,140, then more every time we "
    "see her. A cartoon dog answers from his desk in a home office at night. A notification from a courier slides in "
    "over his window: arriving in 2 minutes. He fixes the site and her chip reads calls waiting, 0. Then a second "
    "notification: I'm at your door, and the camera snaps onto him. Their lines appear in tinted pills and their "
    "mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices River (Mia) and Charlie (Rex); synthesised buzz and sting."
NOTE = "ElevenLabs premade voices River and Charlie at their natural pace; no reference-voice cloning."
MIA = Speaker(
    "mia",
    Voice(role="mia", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.30),
    "rabbit",
)
REX = Speaker(
    "rex",
    Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "dog",
)
TINTS = {"mia": "#f6d6e4", "rex": "#ffe3b3"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SENDER = "Courier"
TOASTS = ("Arriving in 2 minutes", "I'm at your door")
# Mia's chip: calls waiting at 0 s, calls added per second, a step's spacing (s), and the least time (s) a step stays
# on screen: the engine's legibility check wants each count drawn at least 0.83 s
WAITING = (1140, 20.0, 1.0, 0.9)
MOST = 9999  # the chip counts in four digits at most
PUSH = (1.0, 1.08, 1.45, (900.0, 1000.0))  # the opening push in: from, to, over seconds, pivot (frame px)
HIDDEN = 0.125  # seconds of a toast's slide left unseen: its lettering is still off the frame's right edge
ZOOM = (1.2, (1000.0, 1420.0))  # the crash zoom's scale and pivot (frame px): both signature marks stay in frame
END = 20.5

LINES = (
    Line("mia", "Rex, the site is down."),
    Line("rex", "Works on my machine."),
    Line("mia", "Everyone is waiting."),
    Line("rex", "Have they tried my machine?"),
    Line("mia", "Great idea. I'm shipping it to them."),
    Line("rex", "Shipping what?"),
    Line("mia", "Your machine."),
    Line("rex", "Fixed it! It's fixed!"),
    Line("mia", "What was it?"),
    Line("rex", "No idea. Cancel the courier."),
    Line("mia", "Too late."),
)


SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold


BEATS = (
    say(0.0, "rabbit", 0, "narrow", "flat", "crossed"),  # the hook: talking, the push in
    say(1.45, "dog", 1, "closed", "smirk", "lean"),
    say(3.0, "rabbit", 2, "wide", "flat", "face2"),
    say(4.25, "dog", 3, "half", "smirk", "lean"),
    first(5.9, "rabbit", 4, "Great idea.", "half", "grin", "crossed"),
    part(6.75, "rabbit", 4, 2, "I'm shipping it to them.", "half", "grin", "crossed"),
    say(8.1, "dog", 5, "wide", "o", "desk"),
    say(9.15, "rabbit", 6, "narrow", "smirk", "crossed"),
    hold(10.5, "dog", "", "down", "flat", "desk", "toast:0"),  # the courier is coming
    hold(11.3, "dog", "", "shock", "drop", "face"),
    say(12.2, "dog", 7, "wide", "grin", "type", "fixed"),  # at once
    say(13.8, "rabbit", 8, "narrow", "flat", "crossed"),  # nobody waiting
    say(14.8, "dog", 9, "side", "flat", "sigh"),
    say(16.7, "rabbit", 10, "closed", "smirk", "crossed"),
    hold(17.6, "dog", "", "down", "flat", "desk", "toast:1"),  # the courier is here
    hold(18.4, "dog", "", "shock", "drop", "face2", "hangup"),  # the sting and the snap
)
SKETCH = Sketch(SLUG, TITLE, (MIA, REX), LINES, BEATS, END)


def calls(beats, at: float) -> int:
    """The calls waiting at project second ``at``: climbing from 0 s until the ``fixed`` beat, none after it."""
    count, per_second, _, _ = WAITING
    fixed = sketch.events(beats, "fixed")[0][0]
    return 0 if at >= fixed else count + round(per_second * at)


def waiting_through(beats, start: float, end: float) -> list[tuple[float, float, str]]:
    """Mia's chip through one shot, ``(start, end, text)``: the calls waiting as the shot opens, then a step every
    spacing while the next step can stay on screen its least time."""
    _, _, spacing, least = WAITING
    steps = [start]
    while steps[-1] + spacing <= end - least:
        steps.append(round(steps[-1] + spacing, 6))
    return [(a, b, f"Calls waiting: {calls(beats, a):,}") for a, b in zip(steps, steps[1:] + [end], strict=True)]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the first beat is spoken, captioned
    and on Mia from 0 s (the moving opening); toasts index ``TOASTS``, once each in order, on Rex's screen, the
    first after Mia says what she is shipping, the second after she says it is too late; the fix comes once, on
    Rex, after the first toast and before Mia asks what it was; the calls stay within the chip's four digits; exactly
    one hangup, after the last spoken line, on Rex; no other events."""
    sketch.check(sk)
    opening = sk.beats[0]
    if not (opening.spoken and opening.caption and opening.who == "rabbit" and opening.start == 0.0):
        raise sketch.SketchError("the sketch opens moving: Mia talking from 0 s")
    who_at = {b.start: b.who for b in sk.beats}
    spoken = {b.line: b.start for b in sk.beats if b.spoken}
    shown = sketch.events(sk.beats, "toast")
    if [arg for _, arg in shown] != [str(i) for i in range(len(TOASTS))]:
        raise sketch.SketchError(f"the toasts land once each, in order: {len(TOASTS)} of them")
    if any(who_at[at] != "dog" for at, _ in shown):
        raise sketch.SketchError("the toasts land on Rex's screen, in his shot")
    if not spoken[6] < shown[0][0] or not spoken[10] < shown[1][0]:
        raise sketch.SketchError("the courier sets out after 'your machine' and arrives after 'too late'")
    scripting.exactly_once(sk.beats, "fixed", "the fix comes exactly once")
    fixed = sketch.events(sk.beats, "fixed")[0][0]
    if who_at[fixed] != "dog" or not shown[0][0] < fixed < spoken[8]:
        raise sketch.SketchError("Rex fixes it after the courier's first notice, before Mia asks what it was")
    if any(calls(sk.beats, b.start) > MOST for b in sk.beats) or calls(sk.beats, sk.end) > MOST:
        raise sketch.SketchError(f"the calls waiting stay within the chip's {MOST}")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays exactly once")
    sting = sketch.events(sk.beats, "hangup")[0][0]
    if sting < max(b.start for b in sk.beats if b.spoken) or who_at[sting] != "dog":
        raise sketch.SketchError("the sting comes after the last line, on Rex")
    scripting.only_events(sk.beats, {"toast", "fixed", "hangup"})


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that land during one appearance, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], SENDER, TOASTS[idx]))
    return out


def dress(shot) -> None:
    """Mia's shots: her office, a plant swaying on the desk, the calls waiting on her chip. Rex's: his home office at
    night, the courier's notices on his screen."""
    cv, app = shot.cv, shot.app
    if app.who == "rabbit":
        measure = partial(shot.measure, size=BADGE_SIZE)
        toon.room(cv, shot.back)
        toon_sets.plant(cv, shot.front, end=shot.end)
        for a, b, text in waiting_through(shot.beats, app.start, app.end):
            toon_props.badge(cv, shot.front, text, a, b, measure, BADGE_SIZE)
    else:
        toon_sets.home(cv, shot.back, end=shot.end)
        for toast in toasts_in(shot.beats, app):
            # each toast is shown from HIDDEN into its slide, once its lettering has entered the frame: the
            # engine's contrast check measures a text wholly off frame as 1:1 against itself
            shown = cv.group(shot.front, cv.uid("g"), start=round(toast.start + HIDDEN, 6), end=toast.end)
            toon_props.toasts(cv, shown, [toast])


def push(shot, setup) -> None:
    """The camera: a push in on Mia over the opening shot from its first frame, a crash zoom onto Rex on the sting,
    still everywhere else."""
    app = shot.app
    if app.start == 0.0:
        a, b, over, (x, y) = PUSH
        camera.anchor(setup, x, y, place=True)
        camera.push_in(shot.cv, setup, scale=[(0.0, a), (min(over, app.end), b)])
    sting = sketch.events(shot.beats, "hangup")[0][0]
    if app.start <= sting < app.end:
        scale, (x, y) = ZOOM
        camera.anchor(setup, x, y, place=True)
        camera.crash_zoom(shot.cv, setup, sting, scale)
